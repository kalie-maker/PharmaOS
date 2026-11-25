"""Contrato de datos para la web: `report.json` (ver docs/report-schema.md).

A partir de las métricas deterministas del motor genera:
- acciones por PRODUCTO (DEVOLVER, BAJAR_PEDIDO, REPONER, CADUCA_PRONTO) con el cálculo
  explicado paso a paso con los números reales,
- la ficha de cada producto (ventas de 12 semanas, stock, cobertura…),
- el histórico de semanas de piloto (simulado cuando no hay semanas reales).

Todos los importes salen de `MetricsResult.refs`: aquí no se recalcula nada, solo se
seleccionan, redondean y explican. No contiene datos de pacientes.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

import pandas as pd

from engine import __version__
from engine.config import Thresholds
from engine.formatting import eur, number, spanish_date
from engine.metrics import MetricsResult
from engine.mock.generate import MockConfig
from engine.schemas import FAMILY_LABELS, Family

SCHEMA_VERSION = 1
ACTION_TYPES = ("CADUCA_PRONTO", "DEVOLVER", "BAJAR_PEDIDO", "REPONER")
# Ritmo de ejecución simulado del piloto (semana 1 -> 6) y fracción recuperada de lo ejecutado.
_SIM_EXECUTION = (0.32, 0.41, 0.50, 0.58, 0.63, 0.68)
_SIM_RECOVERY = (0.78, 0.81, 0.84, 0.86, 0.88, 0.90)
_SIM_BACKLOG = (1.45, 1.32, 1.22, 1.14, 1.07, 1.02)


def _f(value: Any, digits: int = 2) -> float | None:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(value), digits)


def _iso_week(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def _family_label(family: str) -> str:
    try:
        return FAMILY_LABELS[Family(family)]
    except ValueError:
        return str(family)


def weekly_sales(sales: pd.DataFrame, ref: pd.Timestamp, weeks: int) -> dict[str, list[int]]:
    """Unidades vendidas por producto en las últimas `weeks` semanas (la última = semana de `ref`)."""
    days_back = (ref - sales["fecha"]).dt.days
    recent = sales[(days_back >= 0) & (days_back < weeks * 7)].copy()
    recent["semana"] = weeks - 1 - (days_back[recent.index] // 7)
    pivot = recent.pivot_table(index="codigo_nacional", columns="semana", values="unidades",
                               aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=range(weeks), fill_value=0)
    return {str(code): [int(round(v)) for v in row] for code, row in pivot.iterrows()}


# ---------------------------------------------------------------------------
# Acciones por producto
# ---------------------------------------------------------------------------


def _step(concepto: str, valor: str) -> dict[str, str]:
    return {"concepto": concepto, "valor": valor}


def _units(value: float) -> str:
    return f"{number(value, 0 if float(value).is_integer() else 1)} uds"


def _action_devolver(code: str, r: pd.Series, ref: pd.Timestamp, t: Thresholds) -> dict[str, Any]:
    days = r["dias_sin_venta"]
    last = "nunca en el histórico" if pd.isna(days) else f"{spanish_date(r['ultima_venta'])} (hace {int(days)} días)"
    importe = float(r["valor_stock"])
    stock = float(r["stock_valorable"])
    motivo = (f"Sin ventas desde hace {int(days)} días · {_units(stock)} paradas" if not pd.isna(days)
              else f"Sin ventas en todo el histórico · {_units(stock)} paradas")
    return {
        "titulo": f"Devolver {r['descripcion']}",
        "motivo_1_linea": motivo,
        "importe_eur": importe,
        "cantidad_sugerida": int(stock),
        "urgencia": "alta" if importe >= t.web.high_urgency_eur else "media",
        "plazo": "esta_semana",
        "plazo_texto": "Esta semana",
        "calculo_explicado": {
            "pasos": [
                _step("Stock actual", _units(stock)),
                _step("Coste unitario", eur(r["coste_unitario"])),
                _step("Última venta", last),
                _step("Umbral sin movimiento", f"{t.no_movement_critical_days} días"),
                _step("Capital inmovilizado", f"{_units(stock)} × {eur(r['coste_unitario'])} = {eur(importe)}"),
            ],
            "formula": "stock × coste unitario",
            "resultado": f"Devolverlo al proveedor o liquidarlo libera {eur(importe)} de capital.",
        },
    }


def _action_bajar(code: str, r: pd.Series, ref: pd.Timestamp, t: Thresholds) -> dict[str, Any]:
    daily = float(r["consumo_diario_corta"])
    target_days = float(r["cobertura_objetivo_dias"])
    target_units = math.ceil(daily * target_days)
    stock = float(r["stock_valorable"])
    excess = float(r["sobrestock_unidades"])
    importe = float(r["sobrestock_eur"])
    cover = r["cobertura_dias"]
    cover_text = "sin ventas recientes" if pd.isna(cover) else f"{number(cover)} días"
    motivo = (f"Cobertura de {number(cover)} días frente a {number(target_days)} objetivo"
              if not pd.isna(cover) else f"Sin ventas en {t.short_window_days} días y {_units(stock)} en stock")
    return {
        "titulo": f"Bajar pedido de {r['descripcion']}",
        "motivo_1_linea": motivo,
        "importe_eur": importe,
        "cantidad_sugerida": int(excess),
        "urgencia": "alta" if importe >= t.web.high_urgency_eur else "media",
        "plazo": "proximo_pedido",
        "plazo_texto": "Próximo pedido",
        "calculo_explicado": {
            "pasos": [
                _step(f"Ventas últimos {t.short_window_days} días",
                      f"{_units(r['unidades_corta'])} → {number(daily, 2)} uds/día"),
                _step(f"Cobertura objetivo ({_family_label(r['familia'])})",
                      f"{number(target_days)} días → {_units(target_units)}"),
                _step("Stock actual", f"{_units(stock)} ({cover_text} de cobertura)"),
                _step("Exceso", f"{_units(stock)} − {_units(target_units)} = {_units(excess)}"),
                _step("Exceso a coste", f"{_units(excess)} × {eur(r['coste_unitario'])} = {eur(importe)}"),
            ],
            "formula": "(stock − consumo diario × días objetivo) × coste unitario",
            "resultado": f"No pidas hasta bajar del objetivo: evitas inmovilizar {eur(importe)}.",
        },
    }


def _action_reponer(code: str, r: pd.Series, ref: pd.Timestamp, t: Thresholds) -> dict[str, Any]:
    daily = float(r["consumo_diario_corta"])
    horizon = t.replenishment_days + t.safety_days
    reorder = float(r["punto_pedido"])
    stock = float(r["stock_valorable"])
    importe = float(r["ventas_perdidas_eur"])
    suggested = max(1, math.ceil(reorder * 2 - stock))
    return {
        "titulo": f"Reponer {r['descripcion']}",
        "motivo_1_linea": f"Vende {number(daily, 1)} uds/día y quedan {_units(stock)}",
        "importe_eur": importe,
        "cantidad_sugerida": int(suggested),
        "urgencia": "alta" if stock <= 0 else "media",
        "plazo": "hoy",
        "plazo_texto": "Hoy",
        "calculo_explicado": {
            "pasos": [
                _step(f"Ventas últimos {t.short_window_days} días",
                      f"{_units(r['unidades_corta'])} → {number(daily, 2)} uds/día"),
                _step("Días con venta", f"{int(r['dias_con_venta_corta'])} de {t.short_window_days} "
                                        f"(mínimo {t.frequent_min_sale_days})"),
                _step("Punto de pedido", f"{number(daily, 2)} uds/día × {number(horizon)} días = {_units(round(reorder, 1))}"),
                _step("Stock actual", _units(stock)),
                _step("Ventas en riesgo", f"({_units(round(reorder, 1))} − {_units(stock)}) × "
                                          f"{eur(r['precio_medio_venta'])} = {eur(importe)}"),
            ],
            "formula": "(punto de pedido − stock) × precio medio de venta",
            "resultado": f"Pide {_units(suggested)} hoy para no perder unos {eur(importe)} en ventas.",
        },
    }


def _action_caduca(code: str, r: pd.Series, ref: pd.Timestamp, t: Thresholds) -> dict[str, Any]:
    days_left = int(r["dias_hasta_caducidad"])
    daily = float(r["consumo_diario_corta"])
    stock = float(r["stock_valorable"])
    sellable = daily * max(days_left, 0)
    at_risk = float(r["unidades_riesgo_caducidad"])
    importe = float(r["riesgo_caducidad_eur"])
    expiry = pd.Timestamp(r["fecha_caducidad"])
    deadline = max(ref, expiry - pd.Timedelta(days=7))
    when = "ya caducado" if days_left < 0 else f"{spanish_date(expiry)} (en {days_left} días)"
    return {
        "titulo": f"Promocionar {r['descripcion']} antes de que caduque",
        "motivo_1_linea": f"Caduca el {spanish_date(expiry)} · {_units(at_risk)} no se venderán a tiempo",
        "importe_eur": importe,
        "cantidad_sugerida": int(math.ceil(at_risk)),
        "urgencia": "alta" if days_left <= t.web.expiry_high_days else "media",
        "plazo": "antes_de",
        "plazo_fecha": deadline.date().isoformat(),
        "plazo_texto": f"Antes del {deadline.strftime('%d/%m')}",
        "calculo_explicado": {
            "pasos": [
                _step("Caducidad", when),
                _step(f"Consumo diario (últimos {t.short_window_days} días)", f"{number(daily, 2)} uds/día"),
                _step("Se venderán a tiempo", f"{number(daily, 2)} × {max(days_left, 0)} días = {_units(round(sellable, 1))}"),
                _step("Stock actual", _units(stock)),
                _step("En riesgo", f"({_units(stock)} − {_units(round(sellable, 1))}) × "
                                   f"{eur(r['coste_unitario'])} = {eur(importe)}"),
            ],
            "formula": "(stock − consumo diario × días hasta caducar) × coste unitario",
            "resultado": f"Promociónalo o pide el cambio al proveedor antes del {deadline.strftime('%d/%m')}.",
        },
    }


_BUILDERS = {
    "CADUCA_PRONTO": ("riesgo_caducidad_eur", _action_caduca),
    "DEVOLVER": ("valor_stock", _action_devolver),
    "BAJAR_PEDIDO": ("sobrestock_eur", _action_bajar),
    "REPONER": ("ventas_perdidas_eur", _action_reponer),
}


def _candidates(refs: pd.DataFrame, kind: str) -> pd.DataFrame:
    dead = refs["sin_movimiento_critico"]
    if kind == "DEVOLVER":
        return refs[dead & (refs["valor_stock"] > 0)]
    if kind == "BAJAR_PEDIDO":
        return refs[~dead & (refs["sobrestock_eur"] > 0)]
    if kind == "CADUCA_PRONTO":
        return refs[~dead & (refs["riesgo_caducidad_eur"] > 0)]
    return refs[refs["riesgo_rotura"] & (refs["ventas_perdidas_eur"] > 0)]


def build_actions(m: MetricsResult, t: Thresholds) -> list[dict[str, Any]]:
    """Las acciones de más € de cada tipo; un producto aparece como máximo en una acción."""
    refs = m.refs
    used: set[str] = set()
    actions: list[dict[str, Any]] = []
    for kind in ACTION_TYPES:
        column, builder = _BUILDERS[kind]
        limit = t.web.actions_per_type.get(kind, 0)
        pool = _candidates(refs, kind)
        pool = pool[pool[column] >= t.web.min_amount_eur].sort_values(column, ascending=False, kind="mergesort")
        taken = 0
        for code, row in pool.iterrows():
            if taken >= limit:
                break
            code = str(code)
            if code in used:
                continue
            action = builder(code, row, m.reference_date, t)
            action["importe_eur"] = round(action["importe_eur"], 2)
            actions.append({"id": f"{kind.lower()}-{code}", "tipo": kind, "producto_id": code, **action})
            used.add(code)
            taken += 1
    actions.sort(key=lambda a: (-a["importe_eur"], a["id"]))
    return actions


def web_mock_config(n_refs: int = 8000, seed: int = 7) -> MockConfig:
    """Farmacia ficticia para la web: catálogo grande con facturación realista."""
    return MockConfig(n_refs=n_refs, seed=seed, rate_scale=3000 / max(n_refs, 3000), label_generics=True,
                      cost_scale=0.7, cost_sigma=0.45)


# ---------------------------------------------------------------------------
# Productos e histórico
# ---------------------------------------------------------------------------


def build_products(m: MetricsResult, sales: pd.DataFrame, t: Thresholds) -> dict[str, dict[str, Any]]:
    weekly = weekly_sales(sales, m.reference_date, t.web.sales_weeks)
    empty = [0] * t.web.sales_weeks
    products: dict[str, dict[str, Any]] = {}
    for code, r in m.refs.iterrows():
        code = str(code)
        products[code] = {
            "codigo": code,
            "nombre": None if pd.isna(r["descripcion"]) else str(r["descripcion"]),
            "familia": _family_label(r["familia"]),
            "laboratorio": None if pd.isna(r["laboratorio"]) else str(r["laboratorio"]),
            "stock": _f(r["stock_unidades"], 1),
            "coste": _f(r["coste_unitario"]),
            "pvp": _f(r["pvp"]),
            "valor_stock": _f(r["valor_stock"]),
            "ventas_semanales_12": weekly.get(code, empty),
            "dias_cobertura": _f(r["cobertura_dias"], 0),
            "ultima_venta": None if pd.isna(r["ultima_venta"]) else r["ultima_venta"].date().isoformat(),
            "caducidad": None if pd.isna(r["fecha_caducidad"]) else r["fecha_caducidad"].date().isoformat(),
            "abc": str(r["abc"]),
        }
    return products


def simulated_history(found_now: float, actions_now: int, ref: date, weeks: int) -> list[dict[str, Any]]:
    """Histórico de piloto SIMULADO: más pendiente al principio y ejecución creciente."""
    history = []
    for i in range(weeks):
        k = len(_SIM_BACKLOG) - weeks + i  # alinea con las últimas semanas del patrón
        k = max(0, min(k, len(_SIM_BACKLOG) - 1))
        start = ref - timedelta(days=7 * (weeks - i))
        found = round(found_now * _SIM_BACKLOG[k], 2)
        executed = round(found * _SIM_EXECUTION[k], 2)
        recovered = round(executed * _SIM_RECOVERY[k], 2)
        n_found = int(round(actions_now * _SIM_BACKLOG[k]))
        history.append({
            "semana": _iso_week(start),
            "fecha_inicio": start.isoformat(),
            "encontrado_eur": found,
            "ejecutado_eur": executed,
            "recuperado_eur": recovered,
            "acciones_encontradas": n_found,
            "acciones_ejecutadas": int(round(n_found * _SIM_EXECUTION[k])),
        })
    return history


def build_report(
    m: MetricsResult,
    sales: pd.DataFrame,
    t: Thresholds,
    pharmacy: str,
    program: str | None = None,
    fictitious: bool = True,
) -> dict[str, Any]:
    actions = build_actions(m, t)
    by_type = {kind: [a for a in actions if a["tipo"] == kind] for kind in ACTION_TYPES}
    recoverable = round(sum(a["importe_eur"] for a in actions), 2)
    ref = m.reference_date.date()
    return {
        "version": SCHEMA_VERSION,
        "generado_por": f"stock-profit-os {__version__}",
        "farmacia": {
            "nombre": pharmacy,
            "fecha_datos": ref.isoformat(),
            "semana": _iso_week(ref),
            "programa": program,
            "ficticia": fictitious,
        },
        "resumen": {
            "capital_inmovilizado_eur": round(float(m.totals["sin_movimiento_critico_eur"]), 2),
            "referencias_inmovilizadas": int(m.totals["sin_movimiento_critico_refs"]),
            "stock_total_eur": round(float(m.totals["valor_stock"]), 2),
            "recuperable_semana_eur": recoverable,
            "acciones_total": len(actions),
            "acciones_por_tipo": {kind: len(items) for kind, items in by_type.items()},
            "importe_por_tipo": {kind: round(sum(a["importe_eur"] for a in items), 2)
                                 for kind, items in by_type.items()},
            "umbral_sin_movimiento_dias": t.no_movement_critical_days,
        },
        "acciones": actions,
        "productos": build_products(m, sales, t),
        "historico_simulado": True,
        "historico_semanas": simulated_history(recoverable, len(actions), ref, t.web.history_weeks),
    }
