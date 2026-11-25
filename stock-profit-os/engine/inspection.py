"""Inspección de una exportación desconocida y borrador de mapeo.

`inspect_file` detecta formato y columnas, señala posibles datos personales,
propone un mapeo por coincidencia aproximada con el modelo canónico y
`write_draft` lo guarda en config/mappings/<nombre>.yaml para revisión humana.

Nunca se muestran valores de celdas salvo las etiquetas de familia (categorías
de producto), necesarias para mapearlas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from engine.config import (
    DEFAULT_MAPPINGS_DIR,
    DEFAULT_SYNONYMS_PATH,
    ConfigError,
    ReadOptions,
    normalize_label,
)
from engine.ingest import SheetChooser, parse_number, read_table
from engine.privacy import PrivacyFinding, check_content, check_headers
from engine.schemas import DATASETS, SCHEMAS, ColumnType, Family
from engine.sniff import detect_date_format, detect_decimal

MIN_SCORE = 0.60  # por debajo no se propone
REVIEW_SCORE = 0.85  # por debajo se marca REVISAR
_SAMPLE = 2000
_MAX_FAMILY_LABELS = 80
_FILENAME_HINTS = {"ventas": ("venta",), "stock": ("stock", "existencia", "inventario"),
                   "compras": ("compra", "albaran", "entrada", "pedido")}
# Compatibilidad tipo detectado -> tipo canónico.
_TYPE_FACTOR: dict[ColumnType, dict[str, float]] = {
    ColumnType.DATE: {"fecha": 1.0, "texto": 0.6},
    ColumnType.NUMBER: {"numero": 1.0, "codigo": 0.8},
    ColumnType.CODE: {"codigo": 1.0, "numero": 0.8, "texto": 0.75},
    ColumnType.TEXT: {"texto": 1.0, "codigo": 0.5, "numero": 0.3},
    ColumnType.FAMILY: {"texto": 1.0, "codigo": 0.5, "numero": 0.3},
}


class InspectError(ValueError):
    """No se puede inspeccionar o guardar el borrador."""


@dataclass
class ColumnProfile:
    name: str
    kind: str  # fecha | numero | codigo | texto | vacia
    filled_pct: float
    privacy: PrivacyFinding | None = None


@dataclass
class ColumnMatch:
    canonical: str
    column: str | None
    score: float
    required: bool

    @property
    def needs_review(self) -> bool:
        return self.column is None or self.score < REVIEW_SCORE


@dataclass
class Inspection:
    path: Path
    format: dict[str, object]
    rows: int
    columns: list[ColumnProfile]
    dataset: str
    dataset_scores: dict[str, float]
    dataset_forced: bool
    matches: list[ColumnMatch]
    read_options: dict[str, str]
    families: dict[str, str | None] = field(default_factory=dict)

    @property
    def privacy_findings(self) -> list[PrivacyFinding]:
        return [c.privacy for c in self.columns if c.privacy]

    @property
    def missing_required(self) -> list[str]:
        return [m.canonical for m in self.matches if m.required and m.column is None]


# ---------------------------------------------------------------------------
# Sinónimos
# ---------------------------------------------------------------------------


def load_synonyms(
    path: Path = DEFAULT_SYNONYMS_PATH, mappings_dir: Path = DEFAULT_MAPPINGS_DIR
) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    columns: dict[str, set[str]] = {}
    for canonical, words in (data.get("columnas") or {}).items():
        columns.setdefault(canonical, set()).update(normalize_label(w) for w in words)
    # Alias de todos los mapeos existentes que no sean borradores.
    for mapping_file in sorted(Path(mappings_dir).glob("*.yaml")):
        try:
            mapping = yaml.safe_load(mapping_file.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if mapping.get("borrador"):
            continue
        for spec in (mapping.get("ficheros") or {}).values():
            for canonical, aliases in (spec or {}).items():
                aliases = aliases if isinstance(aliases, list) else [aliases]
                columns.setdefault(canonical, set()).update(normalize_label(a) for a in aliases)
    for schema in SCHEMAS.values():
        for col in schema.columns:
            columns.setdefault(col.name, set()).add(normalize_label(col.name))
    families = {str(k): [normalize_label(w) for w in v] for k, v in (data.get("familias") or {}).items()}
    return columns, families


# ---------------------------------------------------------------------------
# Perfil de columnas
# ---------------------------------------------------------------------------


def profile_kind(series: pd.Series) -> str:
    values = series.dropna()
    if pd.api.types.is_datetime64_any_dtype(series):
        return "fecha"
    if values.empty:
        return "vacia"
    if values.map(lambda v: hasattr(v, "year") and hasattr(v, "month")).mean() >= 0.8:
        return "fecha"
    if pd.api.types.is_numeric_dtype(series) or values.map(lambda v: isinstance(v, (int, float))).all():
        numbers = pd.to_numeric(values, errors="coerce").dropna()
        return _number_or_code(numbers, values.astype(str))
    texts = values.astype(str).str.strip()
    texts = texts[texts != ""].head(_SAMPLE)
    if texts.empty:
        return "vacia"
    fmt = detect_date_format(texts.unique())
    if fmt and pd.to_datetime(texts, format=fmt, errors="coerce").notna().mean() >= 0.6:
        return "fecha"
    decimal, thousands = detect_decimal(texts.unique())
    parsed = texts.map(lambda v: parse_number(v, decimal, thousands))
    if parsed.notna().mean() >= 0.9:
        return _number_or_code(parsed.dropna(), texts)
    return "texto"


def _number_or_code(numbers: pd.Series, texts: pd.Series) -> str:
    if numbers.empty:
        return "texto"
    integer = (numbers == numbers.round()).all()
    digits = texts.str.replace(r"\.0$", "", regex=True).str.len()
    if integer and digits.between(6, 13).mean() >= 0.9:
        return "codigo"
    return "numero"


# ---------------------------------------------------------------------------
# Coincidencia aproximada
# ---------------------------------------------------------------------------


def name_score(header: str, synonyms: set[str]) -> float:
    norm = normalize_label(header)
    if not norm:
        return 0.0
    tokens = set(norm.split())
    best = 0.0
    for syn in synonyms:
        if norm == syn:
            return 1.0
        syn_tokens = set(syn.split())
        if syn_tokens and syn_tokens <= tokens:
            best = max(best, 0.9 if len(syn_tokens) > 1 or len(tokens) <= 2 else 0.8)
        best = max(best, SequenceMatcher(None, norm, syn).ratio())
    return round(best, 3)


def match_columns(
    profiles: list[ColumnProfile], dataset: str, synonyms: dict[str, set[str]]
) -> list[ColumnMatch]:
    schema = SCHEMAS[dataset]
    usable = [p for p in profiles if p.privacy is None and p.kind != "vacia"]
    pairs: list[tuple[float, int, str, str]] = []
    for col in schema.columns:
        factor_by_kind = _TYPE_FACTOR[col.type]
        for order, prof in enumerate(usable):
            score = name_score(prof.name, synonyms.get(col.name, set())) * factor_by_kind.get(prof.kind, 0.0)
            if score >= MIN_SCORE:
                pairs.append((round(score, 3), -order, col.name, prof.name))
    pairs.sort(reverse=True)
    chosen: dict[str, tuple[str, float]] = {}
    used: set[str] = set()
    for score, _, canonical, column in pairs:
        if canonical in chosen or column in used:
            continue
        chosen[canonical] = (column, score)
        used.add(column)
    return [
        ColumnMatch(c.name, chosen.get(c.name, (None, 0.0))[0], chosen.get(c.name, (None, 0.0))[1], c.required)
        for c in schema.columns
    ]


def dataset_score(matches: list[ColumnMatch]) -> float:
    required = [m for m in matches if m.required]
    optional = [m for m in matches if not m.required]
    base = sum(m.score for m in required) / len(required)
    return round(base + 0.02 * sum(1 for m in optional if m.column), 3)


def propose_family(label: str, keywords: dict[str, list[str]]) -> str | None:
    norm = normalize_label(label)
    for fam in Family:
        if norm == normalize_label(fam.value):
            return fam.value
    for family, words in keywords.items():
        if any(w and w in norm for w in words):
            return family
    return None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def inspect_file(
    path: Path | str,
    dataset: str | None = None,
    sheet: str | None = None,
    chooser: SheetChooser | None = None,
    mappings_dir: Path = DEFAULT_MAPPINGS_DIR,
    synonyms_path: Path = DEFAULT_SYNONYMS_PATH,
) -> Inspection:
    path = Path(path)
    if dataset is not None and dataset not in DATASETS:
        raise InspectError(f"Tipo desconocido '{dataset}'. Usa: {', '.join(DATASETS)}")
    synonyms, family_keywords = load_synonyms(synonyms_path, mappings_dir)
    labels = {s for words in synonyms.values() for s in words}
    hint = dataset or next((d for d, words in _FILENAME_HINTS.items()
                            if any(w in normalize_label(path.stem) for w in words)), None)
    table = read_table(path, ReadOptions(), labels, sheet, chooser, hint=hint, option="--hoja")
    df = table.df

    header_flags = {f.column: f for f in check_headers(df.columns)}
    content_flags = {f.column: f for f in check_content(df, skip_columns=header_flags)}
    profiles = [
        ColumnProfile(
            name=str(col),
            kind=profile_kind(df[col]),
            filled_pct=round(float(df[col].notna().mean() * 100), 1),
            privacy=header_flags.get(str(col)) or content_flags.get(str(col)),
        )
        for col in df.columns
    ]

    by_dataset = {d: match_columns(profiles, d, synonyms) for d in DATASETS}
    scores = {d: dataset_score(m) for d, m in by_dataset.items()}
    if hint and dataset is None:
        scores[hint] = round(scores[hint] + 0.1, 3)
    chosen = dataset or max(DATASETS, key=lambda d: (scores[d], -DATASETS.index(d)))
    matches = by_dataset[chosen]

    read_options = _detected_read_options(df, matches, table.format)
    families: dict[str, str | None] = {}
    family_col = next((m.column for m in matches if m.canonical == "familia" and m.column), None)
    if family_col:
        labels_found = df[family_col].dropna().astype(str).str.strip()
        for label in sorted(set(labels_found[labels_found != ""]))[:_MAX_FAMILY_LABELS]:
            families[label] = propose_family(label, family_keywords)

    return Inspection(path, table.format, len(df), profiles, chosen, scores, dataset is not None,
                      matches, read_options, families)


def _detected_read_options(df: pd.DataFrame, matches: list[ColumnMatch], fmt: dict[str, object]) -> dict[str, str]:
    options: dict[str, str] = {}
    if fmt.get("tipo") == "csv":
        sep_names = {"punto y coma": ";", "tabulador": "\t", "coma": ",", "barra vertical": "|"}
        options["separador"] = sep_names.get(str(fmt.get("separador")), ";")
        options["encoding"] = str(fmt.get("codificacion", "utf-8")).replace("-sig", "")
    types = {c.name: c.type for s in SCHEMAS.values() for c in s.columns}
    for m in matches:
        if not m.column:
            continue
        kind = types[m.canonical]
        values = df[m.column].dropna()
        texts = values[values.map(lambda v: isinstance(v, str))].unique()
        if kind is ColumnType.NUMBER and "decimal" not in options and len(texts):
            decimal, thousands = detect_decimal(texts)
            options["decimal"], options["miles"] = decimal, thousands
        if kind is ColumnType.DATE and "formato_fecha" not in options and len(texts):
            found = detect_date_format(texts)
            if found:
                options["formato_fecha"] = found
    return options


# ---------------------------------------------------------------------------
# Borrador YAML
# ---------------------------------------------------------------------------


def _q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_draft(
    inspection: Inspection,
    name: str,
    mappings_dir: Path = DEFAULT_MAPPINGS_DIR,
    force: bool = False,
) -> Path:
    if not name or not all(ch.isalnum() or ch in "-_" for ch in name):
        raise InspectError("El nombre del mapeo solo puede tener letras, números, '-' y '_'")
    mappings_dir = Path(mappings_dir)
    mappings_dir.mkdir(parents=True, exist_ok=True)
    path = mappings_dir / f"{name}.yaml"
    existing: dict[str, Any] = {}
    if path.exists():
        existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not existing.get("borrador") and not force:
            raise InspectError(
                f"{path} ya existe y no es un borrador. Usa otro --nombre o --forzar para sobrescribirlo."
            )

    read = {"separador": ";", "decimal": ",", "miles": ".", "encoding": "utf-8", "formato_fecha": "%d/%m/%Y"}
    read.update({k: v for k, v in (existing.get("lectura") or {}).items() if v is not None})
    read.update(inspection.read_options)

    files = {k: v for k, v in (existing.get("ficheros") or {}).items() if k != inspection.dataset}
    families: dict[str, str | None] = dict(existing.get("familias") or {})
    for label, fam in inspection.families.items():
        families.setdefault(label, fam)

    lines = [
        f"# BORRADOR generado por `inspeccionar` el {date.today().isoformat()}.",
        f"# Último fichero inspeccionado: {inspection.path.name} (tipo: {inspection.dataset}).",
        "# Revisa las líneas marcadas REVISAR. Cuando esté validado, cambia `borrador` a false.",
        "# Para completar el mapeo, inspecciona también los demás ficheros con el mismo --nombre.",
        f"programa: {name}",
        "borrador: true",
        "",
        "lectura:  # se detecta automáticamente; estos valores solo deciden en caso de duda",
        *(f"  {key}: {_q(str(value))}" for key, value in read.items()),
        "",
        "ficheros:",
    ]
    for dataset in DATASETS:
        if dataset == inspection.dataset:
            lines.append(f"  {dataset}:")
            for m in inspection.matches:
                if m.column:
                    note = f"confianza {round(m.score * 100)} %"
                    flag = "  # REVISAR: " + note if m.needs_review else "  # " + note
                    lines.append(f"    {m.canonical}: [{_q(m.column)}]{flag}")
                elif m.required:
                    lines.append(f"    # {m.canonical}: []  # REVISAR: obligatoria, sin columna candidata")
                else:
                    lines.append(f"    # {m.canonical}: []  # opcional, sin columna candidata")
        elif dataset in files:
            lines.append(f"  {dataset}:")
            for canonical, aliases in (files[dataset] or {}).items():
                aliases = aliases if isinstance(aliases, list) else [aliases]
                lines.append(f"    {canonical}: [{', '.join(_q(str(a)) for a in aliases)}]")
        else:
            lines.append(f"  # {dataset}: pendiente de inspeccionar")

    lines += ["", "familias:"]
    if not families:
        lines.append("  {}")
    for label, fam in sorted(families.items()):
        if fam:
            lines.append(f"  {_q(label)}: {fam}")
        else:
            lines.append(f"  {_q(label)}: otros  # REVISAR: sin coincidencia")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # El borrador debe ser YAML válido aunque esté incompleto.
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover - defensa
        raise ConfigError(f"El borrador generado no es YAML válido: {exc}") from exc
    return path
