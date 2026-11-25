"""Ingesta: lectura CSV/XLSX, validación de privacidad, mapeo y normalización.

Orden fijo: leer -> validar privacidad (columnas originales) -> mapear -> normalizar.
"""

from __future__ import annotations

import io
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from engine import privacy
from engine.config import Mapping, ReadOptions, Thresholds, normalize_label
from engine.schemas import SCHEMAS, ColumnType, DatasetSchema, Family
from engine.sniff import describe_separator, detect_csv_format, detect_date_format, detect_decimal, find_header_row

EXCEL_SUFFIXES = {".xlsx", ".xlsm"}
_MAX_LISTED = 10


class IngestError(ValueError):
    """El fichero no se puede leer o no encaja con el mapeo."""


@dataclass(frozen=True)
class SheetCandidate:
    name: str
    rows: int
    columns: list[str]
    score: int  # columnas que coinciden con alias conocidos


class SheetChoiceError(IngestError):
    """El Excel tiene varias hojas plausibles y no se puede decidir sola."""

    def __init__(self, path: Path, candidates: list[SheetCandidate], option: str = "--hoja"):
        self.path = path
        self.candidates = candidates
        listed = "; ".join(f"'{c.name}' ({c.rows} filas, {c.score} columnas reconocidas)" for c in candidates)
        super().__init__(
            f"{path.name} tiene varias hojas con datos y no se puede elegir con seguridad: {listed}. "
            f"Indica cuál usar con {option} <nombre>."
        )


# Recibe el fichero y las hojas candidatas; devuelve el nombre elegido.
SheetChooser = Callable[[Path, list[SheetCandidate]], str]


@dataclass
class RawTable:
    df: pd.DataFrame
    raw_rows: int
    format: dict[str, object] = field(default_factory=dict)


@dataclass
class IngestResult:
    dataset: str
    data: pd.DataFrame
    source_path: Path
    column_map: dict[str, str]  # columna original -> canónica
    ignored_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dropped_rows: int = 0
    raw_rows: int = 0
    format: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------


def _clean_cell(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _unique_headers(cells: list[object]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for i, cell in enumerate(cells):
        name = _clean_cell(cell)
        if not name or name.startswith("Unnamed:"):
            name = f"Columna {i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        headers.append(name)
    return headers


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Quita filas y columnas completamente vacías y normaliza encabezados."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    as_text = df.apply(lambda col: col.map(_clean_cell))
    df = df.loc[(as_text != "").any(axis=1)]
    empty_cols = [c for c in df.columns if (as_text.loc[df.index, c] == "").all()]
    return df.drop(columns=empty_cols).reset_index(drop=True)


def _sheet_table(frame: pd.DataFrame, known_labels: set[str]) -> tuple[pd.DataFrame, int]:
    rows = frame.values.tolist()
    if not rows:
        return pd.DataFrame(), 0
    header_row = find_header_row(rows, known_labels)
    data = frame.iloc[header_row + 1 :].copy()
    data.columns = _unique_headers(list(frame.iloc[header_row]))
    return _tidy(data), header_row


def _score_columns(columns: list[str], known_labels: set[str]) -> int:
    known = {normalize_label(k) for k in known_labels}
    return sum(1 for c in columns if normalize_label(c) in known)


def read_excel_table(
    path: Path,
    known_labels: set[str],
    sheet: str | None = None,
    chooser: SheetChooser | None = None,
    hint: str | None = None,
    option: str = "--hoja",
) -> RawTable:
    try:
        sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    except Exception as exc:  # noqa: BLE001 - se re-lanza con mensaje claro
        raise IngestError(f"No se pudo leer el Excel {path.name}: {exc}") from exc

    tables = {name: _sheet_table(frame, known_labels) for name, frame in sheets.items()}
    candidates = [
        SheetCandidate(name, len(df), list(df.columns), _score_columns(list(df.columns), known_labels))
        for name, (df, _) in tables.items() if len(df) > 0 and len(df.columns) >= 2
    ]
    if sheet is not None:
        if sheet not in tables:
            raise IngestError(f"{path.name} no tiene la hoja '{sheet}'. Hojas: {', '.join(tables)}")
        chosen = sheet
    elif not candidates:
        raise IngestError(f"El Excel {path.name} no contiene ninguna hoja con datos")
    elif len(candidates) == 1:
        chosen = candidates[0].name
    else:
        chosen = _pick_sheet(candidates, hint)
        if chosen is None:
            if chooser is None:
                raise SheetChoiceError(path, candidates, option)
            chosen = chooser(path, candidates)
            if chosen not in tables:
                raise IngestError(f"Hoja no válida: '{chosen}'")
    df, header_row = tables[chosen]
    return RawTable(df, len(df), {"tipo": "xlsx", "hoja": chosen, "fila_cabecera": header_row + 1})


def _pick_sheet(candidates: list[SheetCandidate], hint: str | None) -> str | None:
    """Elige la hoja con más columnas reconocidas; empate -> nombre parecido al tipo de fichero."""
    best = max(c.score for c in candidates)
    top = [c for c in candidates if c.score == best]
    if best > 0 and len(top) == 1:
        return top[0].name
    if hint:
        stem = normalize_label(hint)[:5]  # "venta", "stock", "compr"
        named = [c for c in (top if best > 0 else candidates) if stem in normalize_label(c.name)]
        if len(named) == 1:
            return named[0].name
    return None


def read_csv_table(path: Path, read: ReadOptions, known_labels: set[str]) -> RawTable:
    data = path.read_bytes()
    if not data.strip():
        raise IngestError(f"El fichero {path.name} está vacío")
    fmt, text = detect_csv_format(data, read.separator, known_labels)
    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=fmt.separator,
            skiprows=fmt.header_row,
            dtype=str,
            keep_default_na=False,
            na_values=[""],
            skipinitialspace=True,
            on_bad_lines="skip",
            skip_blank_lines=True,
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise IngestError(f"No se pudo leer {path.name} como CSV: {exc}") from exc
    data_lines = sum(1 for line in text.splitlines()[fmt.header_row + 1 :] if line.strip())
    unreadable = max(0, data_lines - len(df))
    df.columns = _unique_headers(list(df.columns))
    df = _tidy(df)
    return RawTable(
        df,
        data_lines,
        {
            "tipo": "csv",
            "codificacion": fmt.encoding,
            "separador": describe_separator(fmt.separator),
            "fila_cabecera": fmt.header_row + 1,
            "lineas_ilegibles": unreadable,
        },
    )


def read_table(
    path: Path | str,
    read: ReadOptions,
    known_labels: set[str] | None = None,
    sheet: str | None = None,
    chooser: SheetChooser | None = None,
    hint: str | None = None,
    option: str = "--hoja",
) -> RawTable:
    path = Path(path)
    if not path.exists():
        raise IngestError(f"No existe el fichero: {path}")
    labels = known_labels or set()
    if path.suffix.lower() == ".xls":
        raise IngestError(f"{path.name}: formato .xls antiguo no soportado. Guárdalo como .xlsx o CSV.")
    if path.suffix.lower() in EXCEL_SUFFIXES:
        table = read_excel_table(path, labels, sheet, chooser, hint, option)
    else:
        table = read_csv_table(path, read, labels)
    if table.df.empty:
        raise IngestError(f"El fichero {path.name} no contiene filas")
    return table


def read_raw(path: Path | str, read: ReadOptions) -> pd.DataFrame:
    """Compatibilidad: devuelve solo el DataFrame."""
    return read_table(path, read).df


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


def normalize(
    raw: pd.DataFrame, schema: DatasetSchema, mapping: Mapping, detected: dict[str, object] | None = None
) -> tuple[pd.DataFrame, list[str], int]:
    """Aplica tipos canónicos. Devuelve (df, avisos, filas_descartadas).

    El separador decimal y el formato de fecha se detectan por columna; el mapeo solo
    decide en caso de ambigüedad. Lo detectado se anota en `detected`.
    """
    detected = detected if detected is not None else {}
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
            default = (read.decimal, read.thousands or ("." if read.decimal == "," else ""))
            decimal, thousands = detect_decimal(src.dropna().unique(), default)
            detected.setdefault("decimal", {})[column.name] = "coma" if decimal == "," else "punto"  # type: ignore[index]
            values = parse_numbers(src, decimal, thousands)
            bad = int((values.isna() & src.notna()).sum())
            if bad:
                warnings.append(f"{schema.name}.{column.name}: {bad} valor(es) no numérico(s) -> vacío")
        elif column.type is ColumnType.DATE:
            fmt = detect_date_format(src.dropna().unique(), read.date_format) or read.date_format
            detected.setdefault("formato_fecha", {})[column.name] = fmt  # type: ignore[index]
            values = parse_dates(src, fmt)
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


def known_labels(mapping: Mapping, dataset: str) -> set[str]:
    return {alias for aliases in mapping.columns[dataset].values() for alias in aliases}


def load_dataset(
    path: Path | str,
    dataset: str,
    mapping: Mapping,
    thresholds: Thresholds | None = None,
    sheet: str | None = None,
    chooser: SheetChooser | None = None,
) -> IngestResult:
    if dataset not in SCHEMAS:
        raise IngestError(f"Tipo de fichero desconocido: {dataset}")
    schema = SCHEMAS[dataset]
    path = Path(path)

    table = read_table(path, mapping.read, known_labels(mapping, dataset), sheet, chooser,
                       hint=dataset, option=f"--hoja-{dataset}")
    raw = table.df
    privacy.validate(
        raw,
        label=f"{dataset} ({path.name})",
        scan_content=thresholds.privacy_scan_content if thresholds else True,
        phone_min_ratio=thresholds.privacy_phone_min_ratio if thresholds else 0.2,
    )

    column_map = resolve_columns(list(raw.columns), mapping.columns[dataset], schema)
    ignored = [c for c in raw.columns if c not in column_map]
    mapped = raw[list(column_map)].rename(columns=column_map)
    detected = dict(table.format)
    data, warnings, dropped = normalize(mapped, schema, mapping, detected)
    unreadable = int(detected.get("lineas_ilegibles", 0) or 0)
    if unreadable:
        warnings.insert(0, f"{dataset}: {unreadable} línea(s) con un número de columnas distinto, ignorada(s)")
    if data.empty:
        raise IngestError(f"El fichero de {dataset} no tiene filas válidas tras la normalización")

    return IngestResult(
        dataset=dataset,
        data=data,
        source_path=path,
        column_map=column_map,
        ignored_columns=ignored,
        warnings=warnings,
        dropped_rows=dropped + unreadable,
        raw_rows=max(table.raw_rows, len(raw)),
        format=detected,
    )


def load_all(
    paths: dict[str, Path | str],
    mapping: Mapping,
    thresholds: Thresholds | None = None,
    sheets: dict[str, str | None] | None = None,
    chooser: SheetChooser | None = None,
) -> dict[str, IngestResult]:
    """Carga ventas, stock y compras."""
    sheets = sheets or {}
    return {
        name: load_dataset(path, name, mapping, thresholds, sheets.get(name), chooser)
        for name, path in paths.items()
    }
