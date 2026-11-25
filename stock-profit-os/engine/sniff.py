"""Detección automática de formato: codificación, separador, fila de cabecera,
separador decimal y formato de fecha (español, día primero).

Funciones puras y deterministas. Las opciones del mapeo solo actúan como
preferencia cuando la detección es ambigua.
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pandas as pd

from engine.config import normalize_label

SEPARATORS = (";", "\t", ",", "|")
SEPARATOR_NAMES = {";": "punto y coma", "\t": "tabulador", ",": "coma", "|": "barra vertical"}

# Solo formatos con día antes que mes (España) o ISO.
DATE_FORMATS = (
    "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S",
)
_HEADER_SCAN_ROWS = 30
_SAMPLE_LINES = 200
_SAMPLE_VALUES = 500
# Bytes indefinidos en cp1252: si aparecen, el fichero no es Windows-1252.
_CP1252_UNDEFINED = {0x81, 0x8D, 0x8F, 0x90, 0x9D}


@dataclass(frozen=True)
class CsvFormat:
    encoding: str
    separator: str
    header_row: int  # índice 0 de la fila de cabecera en el fichero


def detect_encoding(data: bytes) -> str:
    """utf-8 (con o sin BOM) -> Windows-1252 -> Latin-1."""
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    if not _CP1252_UNDEFINED.intersection(data):
        return "cp1252"
    return "latin-1"


def _split(lines: Sequence[str], sep: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO("\n".join(lines)), delimiter=sep))


def detect_separator(lines: Sequence[str], preferred: str | None = None) -> str:
    """Elige el separador que produce más columnas de forma consistente."""
    sample = [line for line in lines[:_SAMPLE_LINES] if line.strip()]
    if not sample:
        return preferred or ";"
    scored: list[tuple[float, int, bool, int, str]] = []
    for order, sep in enumerate(SEPARATORS):
        counts = [len(row) for row in _split(sample, sep)]
        mode, freq = Counter(counts).most_common(1)[0]
        if mode < 2:
            continue
        consistency = round(freq / len(counts), 2)
        scored.append((consistency, mode, sep == preferred, -order, sep))
    return max(scored)[-1] if scored else (preferred or ";")


def _is_numberish(text: str) -> bool:
    return bool(re.fullmatch(r"[-+(]?[\d.,\s€%]+\)?", text.strip())) if text.strip() else False


def find_header_row(rows: Sequence[Sequence[object]], known_labels: Iterable[str] = ()) -> int:
    """Índice de la fila de cabecera entre las primeras filas.

    Con etiquetas conocidas (alias del mapeo) gana la fila con más coincidencias.
    Si no, la primera fila "ancha" (≥ 60 % de la anchura habitual) con mayoría de texto.
    """
    scan = [[("" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)).strip() for v in row]
            for row in rows[:_HEADER_SCAN_ROWS]]
    if not scan:
        return 0
    known = {normalize_label(label) for label in known_labels}
    if known:
        matches = [sum(1 for cell in row if cell and normalize_label(cell) in known) for row in scan]
        best = max(matches)
        if best >= 2:
            return matches.index(best)
    widths = [sum(1 for cell in row if cell) for row in scan]
    usual = Counter(w for w in widths if w > 0).most_common(1)
    usual_width = max(usual[0][0], max(widths) * 0.6) if usual else 0
    for i, row in enumerate(scan):
        filled = [cell for cell in row if cell]
        if len(filled) >= max(2, 0.6 * usual_width):
            texty = sum(1 for cell in filled if not _is_numberish(cell))
            if texty / len(filled) >= 0.6:
                return i
    return 0


def detect_csv_format(data: bytes, preferred_sep: str | None = None,
                      known_labels: Iterable[str] = ()) -> tuple[CsvFormat, str]:
    encoding = detect_encoding(data)
    text = data.decode(encoding)
    lines = text.splitlines()
    sep = detect_separator(lines, preferred_sep)
    rows = _split([line for line in lines[:_HEADER_SCAN_ROWS]], sep)
    header = find_header_row(rows, known_labels)
    # find_header_row trabaja sobre líneas; las líneas vacías cuentan igual en read_csv(skiprows).
    return CsvFormat(encoding, sep, header), text


def detect_decimal(values: Iterable[object], default: tuple[str, str] = (",", ".")) -> tuple[str, str]:
    """Devuelve (decimal, miles) para una columna numérica en texto."""
    texts = [str(v).strip() for v in values if isinstance(v, str) and v.strip()][:_SAMPLE_VALUES]
    both = [t for t in texts if "," in t and "." in t]
    if both:
        comma_last = sum(1 for t in both if t.rfind(",") > t.rfind("."))
        return (",", ".") if comma_last >= len(both) / 2 else (".", ",")
    commas = [t for t in texts if "," in t]
    dots = [t for t in texts if "." in t]
    if commas and not dots:
        if all(re.fullmatch(r"-?\d{1,3}(,\d{3})+", t) for t in commas) and default[0] == ".":
            return (".", ",")
        return (",", ".")
    if dots and not commas:
        if all(re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t) for t in dots):
            return default  # "1.234": ambiguo, decide el mapeo
        return (".", "")
    return default


def detect_date_format(values: Iterable[object], preferred: str | None = None) -> str | None:
    """Formato que interpreta más valores (solo día-primero o ISO)."""
    texts = list(dict.fromkeys(str(v).strip() for v in values if isinstance(v, str) and str(v).strip()))
    texts = texts[:_SAMPLE_VALUES]
    if not texts:
        return None
    series = pd.Series(texts)
    candidates = list(dict.fromkeys([*( [preferred] if preferred else []), *DATE_FORMATS]))
    best_fmt, best_ok = None, 0
    for fmt in candidates:
        ok = int(pd.to_datetime(series, format=fmt, errors="coerce").notna().sum())
        if ok > best_ok:
            best_fmt, best_ok = fmt, ok
    return best_fmt if best_ok / len(texts) >= 0.5 else None


def describe_separator(sep: str) -> str:
    return SEPARATOR_NAMES.get(sep, repr(sep))
