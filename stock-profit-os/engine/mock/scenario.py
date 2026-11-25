"""Escenario de demo "semana 3": la misma farmacia ficticia antes y después de actuar.

Semana 0: el mock base, analizado con el propio motor.
Semana 3 (21 días después), siguiendo las acciones de la semana 0:
- Devoluciones: se devuelve la mayor parte del stock sin movimiento (las referencias de más valor).
- Pedidos reducidos: en parte del sobrestock no se repone y se devuelve parte del exceso.
- Promociones: se venden con descuento la mayoría de las unidades en riesgo de caducidad.
- Roturas: solo se repone una parte.
- Los laboratorios sobrecomprados que no se tocan siguen comprando de más.
El resto de referencias vende y repone con normalidad. Todo es determinista (semilla).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from engine.config import load_mapping, load_thresholds
from engine.mock.generate import PURCHASE_COLUMNS, MockConfig, MockData, generate

WEEKS = 3


@dataclass(frozen=True)
class ExecutionPlan:
    """Fracción de referencias (las de más impacto primero) en las que se actúa."""

    returned_share: float = 0.5
    reduced_share: float = 0.4
    excess_returned_share: float = 0.1
    promoted_share: float = 0.4
    promo_sold_share: tuple[float, float] = (0.5, 0.9)
    promo_discount: float = 0.15
    replenished_share: float = 0.3
    overbought_factor: float = 1.6


def _top(metrics_refs: pd.DataFrame, codes: list[str], column: str, share: float) -> list[str]:
    if not codes:
        return []
    subset = metrics_refs.loc[codes].sort_values(column, ascending=False, kind="mergesort")
    return list(subset.index[: math.ceil(len(subset) * share)])


def _fmt(dates: pd.Series) -> pd.Series:
    return dates.dt.strftime("%d/%m/%Y")


def build_week3(
    week0: MockData,
    refs: pd.DataFrame,
    actions: list[dict[str, Any]],
    end0: pd.Timestamp,
    plan: ExecutionPlan,
    seed: int,
) -> tuple[MockData, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    days = 7 * WEEKS
    by_type: dict[str, list[dict[str, Any]]] = {}
    for action in actions:
        by_type.setdefault(action["type"], []).append(action)

    def codes(kind: str) -> list[str]:
        return sorted({c for a in by_type.get(kind, []) for c in a["affected_codes"]})

    returned = _top(refs, codes("devolver_sin_movimiento"), "valor_stock", plan.returned_share)
    lab_actions = by_type.get("revisar_laboratorio", [])
    reviewed_labs = [a["facts"]["laboratorio"] for a in lab_actions][:1]
    ignored_labs = {a["facts"]["laboratorio"] for a in lab_actions} - set(reviewed_labs)
    # En los laboratorios que no se revisan se sigue comprando de más: no se reduce su pedido.
    reducible = [c for c in codes("reducir_pedido") if refs.loc[c, "laboratorio"] not in ignored_labs]
    reduced = _top(refs, reducible, "sobrestock_eur", plan.reduced_share)
    promoted = _top(refs, codes("promocionar_caducidad"), "riesgo_caducidad_eur", plan.promoted_share)
    replenished = _top(refs, codes("reponer_rotura"), "ventas_perdidas_eur", plan.replenished_share)

    stock = week0.stock.copy().set_index("Código")
    sales0 = week0.sales
    dates0 = pd.to_datetime(sales0["Fecha"], format="%d/%m/%Y")

    # --- Ventas de las 3 semanas: se repite el ritmo de las 3 anteriores ------------
    recent = sales0[dates0 > end0 - pd.Timedelta(days=days)].copy()
    recent["Fecha"] = _fmt(pd.to_datetime(recent["Fecha"], format="%d/%m/%Y") + pd.Timedelta(days=days))

    # --- Promociones de caducidad -----------------------------------------------------
    promo_rows = []
    unit_price = (sales0.groupby("Código")["Importe s/IVA"].sum() / sales0.groupby("Código")["Unidades"].sum())
    for code in promoted:
        units = int(round(refs.loc[code, "unidades_riesgo_caducidad"] * rng.uniform(*plan.promo_sold_share)))
        if units <= 0:
            continue
        price = unit_price.get(code, stock.loc[code, "P.Coste"] * 1.4) * (1 - plan.promo_discount)
        row = stock.loc[code]
        day = end0 + pd.Timedelta(days=int(rng.integers(1, days + 1)))
        promo_rows.append({
            "Fecha": day.strftime("%d/%m/%Y"), "Código": code, "Descripción": row["Descripción"],
            "Laboratorio": row["Laboratorio"], "Familia": row["Familia"], "Unidades": units,
            "Importe s/IVA": round(units * price, 2), "P.Coste": row["P.Coste"],
        })
    new_sales = pd.concat([recent, pd.DataFrame(promo_rows, columns=recent.columns)], ignore_index=True)
    sold = new_sales.groupby("Código")["Unidades"].sum()

    # --- Compras y stock ---------------------------------------------------------------
    regular_sold = recent.groupby("Código")["Unidades"].sum()
    purchases = []
    stock_units = stock["Stock Actual"].astype(float)
    for code in stock.index:
        base = float(regular_sold.get(code, 0.0))
        lab = stock.loc[code, "Laboratorio"]
        if code in returned or code in reduced or code in promoted:
            bought = 0.0
        elif code in replenished:
            bought = base + math.ceil(refs.loc[code, "punto_pedido"] * 2)
        elif lab in ignored_labs:
            bought = round(base * plan.overbought_factor)
        else:
            bought = base
        units = stock_units[code] - float(sold.get(code, 0.0)) + bought
        if code in returned:
            units = 0.0
        elif code in reduced:
            units -= math.floor(refs.loc[code, "sobrestock_unidades"] * plan.excess_returned_share)
        stock_units[code] = max(0.0, units)
        if bought > 0:
            day = end0 + pd.Timedelta(days=int(rng.integers(1, days + 1)))
            discount = rng.uniform(0.0, 0.08)
            purchases.append((day.strftime("%d/%m/%Y"), code, lab, int(bought),
                              round(bought * float(stock.loc[code, "P.Coste"]) * (1 - discount), 2)))

    stock["Stock Actual"] = stock_units.round().astype(int)
    week3 = MockData(
        sales=pd.concat([sales0, new_sales], ignore_index=True),
        stock=stock.reset_index()[week0.stock.columns],
        purchases=pd.concat([week0.purchases, pd.DataFrame(purchases, columns=PURCHASE_COLUMNS)],
                            ignore_index=True),
        overbought_labs=week0.overbought_labs,
    )
    summary = {
        "referencias_devueltas": len(returned),
        "referencias_pedido_reducido": len(reduced),
        "referencias_promocionadas": len(promoted),
        "referencias_repuestas": len(replenished),
        "laboratorio_revisado": reviewed_labs[0] if reviewed_labs else None,
    }
    return week3, summary


def generate_week3_scenario(
    out_dir: Path | str, config: MockConfig = MockConfig(), plan: ExecutionPlan = ExecutionPlan()
) -> dict[str, Any]:
    """Escribe <out_dir>/semana0 y <out_dir>/semana3. Devuelve rutas y resumen de lo ejecutado."""
    from engine.pipeline import run_analysis  # import local: evita ciclo mock <-> pipeline

    out = Path(out_dir)
    days = 7 * WEEKS
    week0 = generate(replace(config, end_date=config.end_date - timedelta(days=days)))
    paths0 = week0.write(out / "semana0")
    analysis = run_analysis(paths0, load_mapping("farmatic"), load_thresholds(), "Farmacia Demo",
                            today=config.end_date)
    results = analysis.results
    week3, summary = build_week3(
        week0,
        analysis.metrics.refs,
        [*results["acciones"], *results["anexo_acciones"]],
        analysis.metrics.reference_date,
        plan,
        seed=config.seed + 1,
    )
    paths3 = week3.write(out / "semana3")
    (out / "LEEME.md").write_text(_readme(out, summary), encoding="utf-8")
    return {"semana0": paths0, "semana3": paths3, "resumen": summary}


def _readme(out: Path, summary: dict[str, Any]) -> str:
    return f"""# Escenario de demo: semana 0 y semana 3

Farmacia ficticia (datos inventados, columnas estilo Farmatic). Entre la semana 0 y la 3:

- Se devuelve el stock sin movimiento de {summary['referencias_devueltas']} referencias (las de más valor).
- No se repone y se devuelve parte del exceso en {summary['referencias_pedido_reducido']} referencias con sobrestock.
- Se promocionan {summary['referencias_promocionadas']} referencias en riesgo de caducidad.
- Solo se reponen {summary['referencias_repuestas']} referencias con riesgo de rotura.
- Se revisan las compras de {summary['laboratorio_revisado'] or 'ningún laboratorio'}; el resto sigue comprando de más.

Para la demo:

```bash
python -m engine.cli piloto --carpeta {out / 'semana0'} --programa farmatic --nombre "Farmacia Demo" --id demo
python -m engine.cli piloto --carpeta {out / 'semana3'} --programa farmatic --nombre "Farmacia Demo" --id demo
```

La segunda ejecución compara automáticamente con la primera ("en 21 días has liberado X €").
"""
