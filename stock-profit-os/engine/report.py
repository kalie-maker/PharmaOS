"""Construcción del JSON de resultados y renderizado HTML/Markdown.

Flujo: métricas + acciones (+ calidad) -> build_results() -> narrate() -> render/escritura.
El JSON es la fuente única: HTML y Markdown se generan desde él.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from engine import __version__
from engine.actions import ActionPlan, priority_label
from engine.anonymize import Anonymizer
from engine.config import Thresholds
from engine.formatting import FILTERS
from engine.metrics import MetricsResult
from engine.narrative import Narrator, narrate
from engine.schemas import FAMILY_LABELS, Family

SCHEMA_VERSION = 1
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
ANNEX_ROWS = 25

SNAPSHOT_COLUMNS = (
    "descripcion", "laboratorio", "familia", "stock_unidades", "valor_stock", "sin_movimiento_critico",
    "sobrestock_eur", "riesgo_caducidad_eur", "riesgo_rotura", "ventas_perdidas_eur",
)


def clean(value: Any) -> Any:
    """Convierte a tipos JSON: NaN -> None, numpy -> Python, fechas -> ISO, floats a 2 decimales."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (pd.Timestamp, date)):
        return None if pd.isna(value) else value.isoformat()[:10]
    if value is pd.NaT or value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    return value


def _table(df: pd.DataFrame, columns: list[str], index_name: str, limit: int | None = None) -> list[dict[str, Any]]:
    data = df.head(limit) if limit else df
    rows = []
    for idx, row in data[columns].iterrows():
        rows.append(clean({index_name: idx, **row.to_dict()}))
    return rows


def _top(refs: pd.DataFrame, mask: pd.Series, sort_col: str, columns: list[str]) -> list[dict[str, Any]]:
    subset = refs[mask & (refs[sort_col] > 0)].sort_values(sort_col, ascending=False, kind="mergesort")
    return _table(subset, columns, "codigo_nacional", ANNEX_ROWS)


def build_results(
    metrics: MetricsResult,
    plan: ActionPlan,
    t: Thresholds,
    pharmacy: str,
    program: str | None = None,
    quality: dict[str, Any] | None = None,
    anonymizer: Anonymizer | None = None,
    narrator: Narrator | None = None,
) -> dict[str, Any]:
    refs = metrics.refs
    totals = metrics.totals
    base = ["descripcion", "laboratorio", "familia"]

    def actions(items: list) -> list[dict[str, Any]]:
        out = []
        for action in items:
            data = clean(action.to_dict())
            data["prioridad"] = priority_label(action.priority)
            out.append(data)
        return out

    snapshot_mask = (refs["stock_unidades"] != 0) | refs["riesgo_rotura"]
    snapshot = {
        str(code): clean(row.to_dict())
        for code, row in refs.loc[snapshot_mask, list(SNAPSHOT_COLUMNS)].iterrows()
    }

    families = metrics.families.copy()
    families["nombre"] = [FAMILY_LABELS.get(Family(f), f) if f in Family._value2member_map_ else f
                          for f in families.index]

    results: dict[str, Any] = {
        "version_esquema": SCHEMA_VERSION,
        "motor": f"stock-profit-os {__version__}",
        "farmacia": pharmacy,
        "anonimizado": False,
        "cifras_escaladas": False,
        "programa": program,
        "periodo": {
            "fecha_referencia": clean(metrics.reference_date),
            "inicio_ventas": clean(metrics.sales_start),
            "dias_historico": metrics.history_days,
        },
        "cifras_clave": clean({
            "valor_stock_eur": totals["valor_stock"],
            "sin_movimiento_eur": totals["sin_movimiento_critico_eur"],
            "sin_movimiento_refs": totals["sin_movimiento_critico_refs"],
            "sin_movimiento_dias": t.no_movement_critical_days,
            "riesgo_caducidad_eur": totals["riesgo_caducidad_eur"],
            "riesgo_caducidad_dias": max(t.expiry_windows_days),
        }),
        "totales": clean(totals),
        "calidad": quality,
        "acciones": actions(plan.main),
        "anexo_acciones": actions(plan.annex),
        "anexo": {
            "sin_movimiento": _top(refs, refs["sin_movimiento_critico"], "valor_stock",
                                   [*base, "stock_valorable", "valor_stock", "dias_sin_venta"]),
            "sobrestock": _top(refs, ~refs["sin_movimiento_critico"], "sobrestock_eur",
                               [*base, "stock_valorable", "cobertura_dias", "cobertura_objetivo_dias",
                                "sobrestock_eur"]),
            "caducidad": _top(refs, ~refs["sin_movimiento_critico"], "riesgo_caducidad_eur",
                              [*base, "stock_valorable", "dias_hasta_caducidad", "riesgo_caducidad_eur"]),
            "rotura": _top(refs, refs["riesgo_rotura"], "ventas_perdidas_eur",
                           [*base, "stock_valorable", "punto_pedido", "ventas_perdidas_eur"]),
        },
        "laboratorios": _table(
            metrics.labs[metrics.labs["compras_coste"] > 0],
            ["compras_coste", "coste_ventas", "ratio_compras_ventas", "ventas_eur", "margen_bruto_pct",
             "compra_alta"],
            "laboratorio", ANNEX_ROWS,
        ),
        "familias": _table(
            families, ["nombre", "ventas_eur", "margen_bruto_eur", "margen_bruto_pct", "peso_ventas_pct",
                       "valor_stock"], "familia",
        ),
        "umbrales": clean({
            "sin_movimiento_dias": t.no_movement_critical_days,
            "cobertura_objetivo_dias": t.target_coverage_days,
            "cobertura_por_familia": t.target_coverage_by_family,
            "dias_reposicion": t.replenishment_days,
            "dias_seguridad": t.safety_days,
            "ratio_compras_ventas_alto": t.lab_high_ratio,
            "meses_laboratorio": t.lab_window_months,
            "nota": "Umbrales en revisión con las farmacias piloto (hipótesis ajustables).",
        }),
        "referencias": snapshot,
    }
    if anonymizer is not None:
        return anonymizer.apply(results, narrator)
    return narrate(results, narrator)


# ---------------------------------------------------------------------------
# Renderizado
# ---------------------------------------------------------------------------


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(FILTERS)
    return env


def render_html(results: dict[str, Any]) -> str:
    return _env().get_template("report.html.j2").render(r=results)


def render_markdown(results: dict[str, Any]) -> str:
    return _env().get_template("report.md.j2").render(r=results)


def write_reports(results: dict[str, Any], out_dir: Path | str, prefix: str) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"html": out / f"{prefix}.html", "md": out / f"{prefix}.md", "json": out / f"{prefix}.json"}
    paths["html"].write_text(render_html(results), encoding="utf-8")
    paths["md"].write_text(render_markdown(results), encoding="utf-8")
    paths["json"].write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return paths
