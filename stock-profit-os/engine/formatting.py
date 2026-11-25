"""Formato español para cifras y fechas: 1.234,56 €."""

from __future__ import annotations

import math
from datetime import date, datetime


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def number(value: object, decimals: int = 0) -> str:
    if _is_missing(value):
        return "—"
    text = f"{float(value):,.{decimals}f}"  # 1,234.56
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def eur(value: object, decimals: int = 2) -> str:
    return "—" if _is_missing(value) else f"{number(value, decimals)} €"


def eur0(value: object) -> str:
    return eur(value, 0)


def pct(value: object, decimals: int = 1) -> str:
    return "—" if _is_missing(value) else f"{number(value, decimals)} %"


def spanish_date(value: object) -> str:
    if _is_missing(value) or value == "":
        return "—"
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")  # type: ignore[union-attr]


FILTERS = {"eur": eur, "eur0": eur0, "num": number, "pct": pct, "fecha": spanish_date}
