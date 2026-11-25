"""Ingesta: lectura CSV/XLSX, validación de privacidad, mapeo y normalización.

Orden fijo: leer -> validar privacidad (columnas originales) -> mapear -> normalizar.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from engine import privacy
from engine.config import Mapping, ReadOptions, Thresholds, normalize_label
from engine.schemas import SCHEMAS, ColumnType, DatasetSchema, Family

EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xls"}
FALLBACK_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")
_MAX_LISTED = 10


class IngestError(ValueError):
    """El fichero no se puede leer o no encaja con el mapeo."""


@dataclass
class IngestResult:
    dataset: str
    data: pd.DataFrame
    source_path: Path
    column_map: dict[str, str]  # columna original -> canónica
    ignored_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dropped_rows: int = 0


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------


def read_raw(path: Path | str, read: ReadOptions) -> pd.DataFrame:
    """Lee el fichero sin interpretar tipos (CSV como texto; XLSX con tipos nativos)."""
    path = Path(path)
    if not path.exists():
        raise IngestError(f"No existe el fichero: {path}")

    if path.suffix.lower() in EXCEL_SUFFIXES:
        try:
            df = pd.read_excel(path, sheet_name=0)
        except Exception as exc:  # noqa: BLE001 - se re-lanza con mensaje claro
            raise IngestError(f"No se pudo leer el Excel {path.name}: {exc}") from exc
    else:
        df = _read_csv(path, read)

    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise IngestError(f"El fichero {path.name} no contiene filas")
    return df


def _read_csv(path: Path, read: ReadOptions) -> pd.DataFrame:
    # utf-8 estricto primero: si el fichero es cp1252 falla y pasamos al siguiente.
    encodings = list(dict.fromkeys(("utf-8-sig", read.encoding, *FALLBACK_ENCODINGS)))
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(
                path,
                sep=read.separator,
                dtype=str,
                encoding=encoding,
                keep_default_na=False,
                na_values=[""],
                skipinitialspace=True,
            )
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.ParserError as exc:
            raise IngestError(f"No se pudo leer {path.name} como CSV: {exc}") from exc
    raise IngestError(f"No se pudo decodificar {path.name}: {last_error}")


# ---------------------------------------------------------------------------
# Mapeo
# ---------------------------------------------------------------------------


def resolve_columns(
    raw_columns: list[str], aliases: dict[str, list[str]], schema: DatasetSchema
) -> dict[str, str]:
    """Devuelve {columna_original: canónica}. Lanza IngestError si falta una obligatoria."""
    by_norm: dict[str, str] = {}
    for col in raw_columns:
        by_norm.setdefault(normalize_label(col), col)

    resolved: dict[str, str] = {}
    used: set[str] = set()
    missing: list[str] = []
    for canonical in schema.column_names:
        match = None
        for alias in aliases.get(canonical, []):
            candidate = by_norm.get(normalize_label(alias))
            if candidate is not None and candidate not in used:
                match = candidate
                break
        if match is None:
            if canonical in schema.required:
                tried = ", ".join(f"'{a}'" for a in aliases.get(canonical, [])) or "ninguno"
                missing.append(f"'{canonical}' (alias probados: {tried})")
            continue
        resolved[match] = canonical
        used.add(match)

    if missing:
        raise IngestError(
            f"Al fichero de {schema.name} le faltan columnas obligatorias: "
            + "; ".join(missing)
            + f". Columnas encontradas: {', '.join(raw_columns)}. "
            "Revisa los alias en config/mappings/<programa>.yaml."
        )
    return resolved


# ---------------------------------------------------------------------------
# Normalización de valores
# ---------------------------------------------------------------------------

_CURRENCY = re.compile(r"[€\s ]")


def parse_number(value: object, decimal: str = ",", thousands: str = ".") -> float:
    """Convierte '1.234,56 €', '12,5', '12.5' o números nativos en float (NaN si no se puede)."""
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    text = _CURRENCY.sub("", str(value))
    if not text:
        return math.nan
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if thousands and decimal in text:
        text = text.replace(thousands, "").replace(decimal, ".")
    elif thousands and thousands in text:
        # Sin separador decimal: "1.234" (miles) frente a "12.5" (decimal ya en formato punto).
        tail = text.rsplit(thousands, 1)[1]
        text = text.replace(thousands, "") if len(tail) == 3 else text.replace(thousands, ".")
    elif decimal != ".":
        text = text.replace(decimal, ".")
    try:
        number = float(text)
    except ValueError:
        return math.nan
    return -number if negative else number


def parse_numbers(series: pd.Series, decimal: str, thousands: str) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    uniques = series.dropna().unique()
    lookup = {u: parse_number(u, decimal, thousands) for u in uniques}
    return series.map(lookup).astype(float)


def parse_dates(series: pd.Series, date_format: str) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series).dt.normalize()
    text = series.astype("string").str.strip()
    parsed = pd.to_datetime(text, format=date_format, errors="coerce")
    pending = parsed.isna() & text.notna() & (text != "")
    if pending.any():
        # Respaldo 1: ISO (Excel exportado como texto). Respaldo 2: día primero, formato libre.
        parsed.loc[pending] = pd.to_datetime(text[pending], format="ISO8601", errors="coerce")
        pending = parsed.isna() & text.notna() & (text != "")
    if pending.any():
        parsed.loc[pending] = pd.to_datetime(
            text[pending], dayfirst=True, errors="coerce", format="mixed"
        )
    return parsed.dt.normalize()


def normalize_code(value: object) -> str | None:
    """Código nacional como texto: sin espacios ni '.0'; numéricos rellenos a 6 dígitos."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip().upper()
    if text.endswith(".0"):
        text = text[:-2]
    text = re.sub(r"[^0-9A-Z]", "", text)
    if not text:
        return None
    return text.zfill(6) if text.isdigit() else text


def normalize_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().replace("", pd.NA)
    return text.astype(object).where(text.notna(), None)


def normalize_family(series: pd.Series, mapping: Mapping) -> tuple[pd.Series, list[str]]:
    uniques = series.dropna().unique()
    lookup: dict[object, str] = {}
    unknown: list[str] = []
    for label in uniques:
        family = mapping.map_family(label)
        if family is None:
            unknown.append(str(label))
            family = Family.OTHER
        lookup[label] = family.value
    result = series.map(lookup).fillna(Family.OTHER.value).astype(object)
    return result, sorted(unknown)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def normalize(raw: pd.DataFrame, schema: DatasetSchema, mapping: Mapping) -> tuple[pd.DataFrame, list[str], int]:
    """Aplica tipos canónicos. Devuelve (df, avisos, filas_descartadas)."""
    warnings: list[str] = []
    out = pd.DataFrame(index=raw.index)
    read = mapping.read

    for column in schema.columns:
        if column.name not in raw.columns:
            out[column.name] = None if column.type is not ColumnType.NUMBER else math.nan
            if column.type is ColumnType.DATE:
                out[column.name] = pd.NaT
            continue
        src = raw[column.name]
        if column.type is ColumnType.NUMBER:
            values = parse_numbers(src, read.decimal, read.thousands)
            bad = int((values.isna() & src.notna()).sum())
            if bad:
                warnings.append(f"{schema.name}.{column.name}: {bad} valor(es) no numérico(s) -> vacío")
        elif column.type is ColumnType.DATE:
            values = parse_dates(src, read.date_format)
            bad = int((values.isna() & src.notna()).sum())
            if bad:
                warnings.append(f"{schema.name}.{column.name}: {bad} fecha(s) no reconocida(s) -> vacío")
        elif column.type is ColumnType.CODE:
            uniques = src.dropna().unique()
            lookup = {u: normalize_code(u) for u in uniques}
            values = src.map(lookup).astype(object)
        elif column.type is ColumnType.FAMILY:
            values, unknown = normalize_family(src, mapping)
            if unknown:
                listed = ", ".join(unknown[:_MAX_LISTED]) + (" …" if len(unknown) > _MAX_LISTED else "")
                warnings.append(
                    f"{schema.name}.familia: {len(unknown)} etiqueta(s) sin mapear clasificadas como "
                    f"'otros': {listed}"
                )
        else:
            values = normalize_text(src)
        out[column.name] = values

    keys_null = out[list(schema.row_keys)].isna().any(axis=1)
    dropped = int(keys_null.sum())
    if dropped:
        warnings.append(
            f"{schema.name}: {dropped} fila(s) descartada(s) por no tener {', '.join(schema.row_keys)}"
        )
        out = out.loc[~keys_null]

    for column in schema.columns:
        if column.type is ColumnType.NUMBER and column.required:
            nulls = int(out[column.name].isna().sum())
            if nulls:
                warnings.append(f"{schema.name}.{column.name}: {nulls} fila(s) sin valor")

    if schema.name == "stock":
        dups = int(out["codigo_nacional"].duplicated().sum())
        if dups:
            warnings.append(f"stock: {dups} código(s) nacional(es) repetido(s)")

    return out.reset_index(drop=True), warnings, dropped


def load_dataset(
    path: Path | str,
    dataset: str,
    mapping: Mapping,
    thresholds: Thresholds | None = None,
) -> IngestResult:
    if dataset not in SCHEMAS:
        raise IngestError(f"Tipo de fichero desconocido: {dataset}")
    schema = SCHEMAS[dataset]
    path = Path(path)

    raw = read_raw(path, mapping.read)
    privacy.validate(
        raw,
        label=f"{dataset} ({path.name})",
        scan_content=thresholds.privacy_scan_content if thresholds else True,
        phone_min_ratio=thresholds.privacy_phone_min_ratio if thresholds else 0.2,
    )

    column_map = resolve_columns(list(raw.columns), mapping.columns[dataset], schema)
    ignored = [c for c in raw.columns if c not in column_map]
    mapped = raw[list(column_map)].rename(columns=column_map)
    data, warnings, dropped = normalize(mapped, schema, mapping)
    if data.empty:
        raise IngestError(f"El fichero de {dataset} no tiene filas válidas tras la normalización")

    return IngestResult(
        dataset=dataset,
        data=data,
        source_path=path,
        column_map=column_map,
        ignored_columns=ignored,
        warnings=warnings,
        dropped_rows=dropped,
    )


def load_all(
    paths: dict[str, Path | str],
    mapping: Mapping,
    thresholds: Thresholds | None = None,
) -> dict[str, IngestResult]:
    """Carga ventas, stock y compras. Valida privacidad de todos antes de devolver nada."""
    return {name: load_dataset(path, name, mapping, thresholds) for name, path in paths.items()}
