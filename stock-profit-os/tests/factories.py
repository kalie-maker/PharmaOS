"""Constructores de DataFrames canónicos para tests."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pandas as pd

from engine.config import Thresholds
from engine.schemas import PURCHASES, SALES, STOCK, DatasetSchema

REF = pd.Timestamp("2026-06-30")


def frame(schema: DatasetSchema, rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=schema.column_names)
    for column in schema.columns:
        if column.type.value == "date":
            df[column.name] = pd.to_datetime(df[column.name])
        elif column.type.value == "number":
            df[column.name] = df[column.name].astype(float)
        else:
            df[column.name] = df[column.name].astype(object)
    return df


def sales(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return frame(SALES, rows)


def stock(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return frame(STOCK, rows)


def purchases(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return frame(PURCHASES, rows)


def daily_sales(code: str, days: int, units: float = 1.0, price: float = 10.0, cost: float = 6.0,
                end: pd.Timestamp = REF, every: int = 1, **extra: Any) -> list[dict[str, Any]]:
    """Una venta cada `every` días durante los últimos `days` días hasta `end`."""
    return [
        {"fecha": end - pd.Timedelta(days=d), "codigo_nacional": code, "unidades": units,
         "importe_venta_sin_iva": units * price, "coste_unitario": cost, **extra}
        for d in range(0, days, every)
    ]


def with_ref(t: Thresholds, ref: pd.Timestamp = REF) -> Thresholds:
    return replace(t, reference_date=ref.date())
