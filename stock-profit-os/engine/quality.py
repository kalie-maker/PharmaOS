"""Informe de calidad de datos, previo al análisis.

Cada comprobación devuelve afectados, total, porcentaje y estado frente al límite
de config.yaml (calidad.*). Nivel global:
- "baja": alguna comprobación supera su límite -> el informe lo avisa al principio.
- "aceptable": alguna supera `fraccion_aviso` x límite.
- "buena": el resto.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

import pandas as pd

from engine.config import QualityLimits, Thresholds
from engine.formatting import number
from engine.ingest import IngestResult

LEVEL_MESSAGES = {
    "baja": "Las cifras pueden estar distorsionadas. Corrige estos puntos en la exportación antes de actuar.",
    "aceptable": "Hay incidencias menores; las cifras de las referencias afectadas son orientativas.",
    "buena": "Sin incidencias relevantes.",
}
MIN_EXPIRY_YEAR = 2000
MAX_EXPIRY_YEARS_AHEAD = 15


@dataclass(frozen=True)
class QualityCheck:
    id: str
    descripcion: str
    afectados: int
    total: int
    porcentaje: float
    limite: float
    estado: str  # ok | aviso | mal


@dataclass
class QualityReport:
    nivel: str
    mensaje: str
    comprobaciones: list[QualityCheck]
    avisos_ingesta: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nivel": self.nivel,
            "mensaje": self.mensaje,
            "comprobaciones": [asdict(c) for c in self.comprobaciones],
            "avisos_ingesta": self.avisos_ingesta,
        }

    def lines(self) -> list[str]:
        out = [f"Calidad de datos: {self.nivel.upper()}. {self.mensaje}"]
        for c in self.comprobaciones:
            mark = {"ok": "  ok ", "aviso": "  !  ", "mal": "  ✗  "}[c.estado]
            out.append(f"{mark}{c.descripcion}: {number(c.afectados)} de {number(c.total)} "
                       f"({number(c.porcentaje, 1)} %, límite {number(c.limite, 1)} %)")
        return out


def _check(cid: str, text: str, affected: int, total: int, limit: float, warn_fraction: float) -> QualityCheck:
    pct = round(affected / total * 100, 2) if total else 0.0
    if pct > limit:
        state = "mal"
    elif affected and pct > limit * warn_fraction:
        state = "aviso"
    else:
        state = "ok"
    return QualityCheck(cid, text, int(affected), int(total), pct, limit, state)


def assess_quality(
    ingest: dict[str, IngestResult],
    t: Thresholds,
    today: date | None = None,
) -> QualityReport:
    q: QualityLimits = t.quality
    wf = q.warning_fraction
    today_ts = pd.Timestamp(today or date.today())
    sales = ingest["ventas"].data
    stock = ingest["stock"].data
    purchases = ingest["compras"].data
    checks: list[QualityCheck] = []

    # 1. Costes vacíos o <= 0 en referencias con stock.
    stock_codes = stock.groupby("codigo_nacional").agg(
        unidades=("stock_unidades", "sum"),
        coste=("coste_unitario", "max"),
        descripcion=("descripcion", "first"),
    )
    with_stock = stock_codes[stock_codes["unidades"] > 0]
    missing_cost = with_stock["coste"].isna() | (with_stock["coste"] <= 0)
    checks.append(_check("costes_vacios", "Referencias con stock sin coste válido",
                         int(missing_cost.sum()), len(with_stock), q.max_pct_missing_cost, wf))

    # 2. Stock negativo.
    checks.append(_check("stock_negativo", "Referencias con stock negativo",
                         int((stock_codes["unidades"] < 0).sum()), len(stock_codes), q.max_pct_negative_stock, wf))

    # 3. Fechas fuera de rango (futuras o demasiado antiguas) en ventas/compras y caducidades absurdas.
    dated = pd.concat([sales["fecha"], purchases["fecha"]], ignore_index=True)
    oldest = today_ts - pd.Timedelta(days=q.max_age_days)
    out_of_range = int(((dated > today_ts) | (dated < oldest)).sum())
    expiry = stock["fecha_caducidad"].dropna()
    bad_expiry = int(((expiry.dt.year < MIN_EXPIRY_YEAR)
                      | (expiry > today_ts + pd.DateOffset(years=MAX_EXPIRY_YEARS_AHEAD))).sum())
    checks.append(_check("fechas_fuera_rango",
                         f"Fechas futuras, de hace más de {number(q.max_age_days)} días o caducidades imposibles",
                         out_of_range + bad_expiry, len(dated) + len(expiry), q.max_pct_dates_out_of_range, wf))

    # 4. Referencias sin descripción.
    checks.append(_check("sin_descripcion", "Referencias de stock sin descripción",
                         int(stock_codes["descripcion"].isna().sum()), len(stock_codes),
                         q.max_pct_missing_description, wf))

    # 5. Duplicados: códigos repetidos en stock y filas idénticas en ventas/compras.
    checks.append(_check("duplicados_stock", "Códigos repetidos en el fichero de stock",
                         int(stock["codigo_nacional"].duplicated().sum()), len(stock), q.max_pct_duplicates, wf))
    dup_rows = int(sales.duplicated().sum()) + int(purchases.duplicated().sum())
    checks.append(_check("filas_duplicadas", "Filas idénticas repetidas en ventas o compras",
                         dup_rows, len(sales) + len(purchases), q.max_pct_duplicates, wf))

    # 6. Filas descartadas en la ingesta (sin código, sin fecha o ilegibles).
    dropped = sum(r.dropped_rows for r in ingest.values())
    raw_rows = sum(max(r.raw_rows, len(r.data) + r.dropped_rows) for r in ingest.values())
    checks.append(_check("filas_descartadas", "Filas descartadas al leer (sin código, sin fecha o ilegibles)",
                         dropped, raw_rows, q.max_pct_dropped_rows, wf))

    # 7. Importes o unidades vacíos.
    empty_numbers = int(sales[["unidades", "importe_venta_sin_iva"]].isna().any(axis=1).sum())
    empty_numbers += int(purchases[["unidades", "coste_total"]].isna().any(axis=1).sum())
    checks.append(_check("importes_vacios", "Filas de ventas o compras sin unidades o importe",
                         empty_numbers, len(sales) + len(purchases), q.max_pct_dropped_rows, wf))

    # 8. Códigos vendidos que no están en stock (suele indicar un problema de mapeo o de exportación).
    sold = set(sales["codigo_nacional"].dropna())
    not_in_stock = len(sold - set(stock_codes.index))
    checks.append(_check("ventas_sin_stock", "Códigos vendidos que no aparecen en el fichero de stock",
                         not_in_stock, len(sold), q.max_pct_sales_not_in_stock, wf))

    states = {c.estado for c in checks}
    level = "baja" if "mal" in states else "aceptable" if "aviso" in states else "buena"
    warnings = [w for r in ingest.values() for w in r.warnings]
    return QualityReport(level, LEVEL_MESSAGES[level], checks, warnings)
