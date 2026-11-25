"""Métricas deterministas por referencia, laboratorio y familia.

Convenciones:
- Fecha de referencia = config.analisis.fecha_referencia o la última fecha con ventas.
- Las ventanas incluyen la fecha de referencia: [ref - (N-1) días, ref].
- Si el histórico es más corto que la ventana, el consumo se divide por los días disponibles.
- Stock negativo se valora como 0 (la calidad de datos lo señala aparte).
- Coste unitario <= 0 o vacío se sustituye por: último coste en ventas -> coste medio de
  compras. Si no hay ninguno, la referencia se valora a 0 y se marca coste_desconocido.
- Una referencia que nunca se vende en el histórico cuenta "días sin venta" como mínimo
  igual a la longitud del histórico.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from engine.config import Thresholds
from engine.schemas import Family

UNKNOWN_LAB = "Sin laboratorio"


class MetricsError(ValueError):
    """No se pueden calcular métricas con los datos recibidos."""


@dataclass
class MetricsResult:
    reference_date: pd.Timestamp
    sales_start: pd.Timestamp
    history_days: int
    refs: pd.DataFrame  # índice: codigo_nacional
    labs: pd.DataFrame  # índice: laboratorio
    families: pd.DataFrame  # índice: familia
    totals: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Preparación
# ---------------------------------------------------------------------------


def consolidate_stock(stock: pd.DataFrame) -> pd.DataFrame:
    """Una fila por código: suma unidades, coste medio ponderado, caducidad más próxima."""
    df = stock.copy()
    df["stock_unidades"] = df["stock_unidades"].fillna(0.0)
    valid_cost = df["coste_unitario"].where(df["coste_unitario"] > 0)
    weight = df["stock_unidades"].clip(lower=0).where(valid_cost.notna(), 0.0)
    df["_cw"] = (valid_cost.fillna(0.0) * weight)
    df["_w"] = weight
    df["_cost"] = valid_cost
    grouped = df.groupby("codigo_nacional", sort=False)
    out = grouped.agg(
        descripcion=("descripcion", "first"),
        laboratorio=("laboratorio", "first"),
        familia=("familia", "first"),
        stock_unidades=("stock_unidades", "sum"),
        pvp=("pvp", "first"),
        fecha_caducidad=("fecha_caducidad", "min"),
        _cw=("_cw", "sum"),
        _w=("_w", "sum"),
        _cost_mean=("_cost", "mean"),
        _rows=("stock_unidades", "size"),
    )
    weighted = out["_cw"] / out["_w"].where(out["_w"] > 0)
    out["coste_unitario"] = weighted.fillna(out["_cost_mean"])
    out["filas_stock"] = out["_rows"]
    return out.drop(columns=["_cw", "_w", "_cost_mean", "_rows"])


def _window(df: pd.DataFrame, ref: pd.Timestamp, days: int) -> pd.DataFrame:
    start = ref - pd.Timedelta(days=days - 1)
    return df[(df["fecha"] >= start) & (df["fecha"] <= ref)]


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.where(den > 0)


# ---------------------------------------------------------------------------
# Cálculo
# ---------------------------------------------------------------------------


def compute_metrics(
    sales: pd.DataFrame,
    stock: pd.DataFrame,
    purchases: pd.DataFrame,
    t: Thresholds,
) -> MetricsResult:
    if sales.empty and t.reference_date is None:
        raise MetricsError("No hay ventas: no se puede fijar la fecha de referencia del análisis")
    ref = pd.Timestamp(t.reference_date) if t.reference_date else sales["fecha"].max()
    sales = sales[sales["fecha"] <= ref].copy()
    purchases = purchases[purchases["fecha"] <= ref].copy()
    sales_start = sales["fecha"].min() if not sales.empty else ref
    history_days = int((ref - sales_start).days) + 1

    stock_c = consolidate_stock(stock)
    refs = _build_reference_master(sales, stock_c, purchases, ref, t)
    refs = _add_sales_metrics(refs, sales, ref, history_days, t)
    refs = _add_stock_metrics(refs, t)
    refs = _add_expiry(refs, ref, t)
    refs = _add_abc(refs, t)

    labs = _lab_metrics(sales, purchases, refs, ref, t)
    families = _family_metrics(sales, refs, ref, history_days, t)
    totals = _totals(refs, labs, t)
    return MetricsResult(ref, sales_start, history_days, refs, labs, families, totals)


def _build_reference_master(
    sales: pd.DataFrame,
    stock_c: pd.DataFrame,
    purchases: pd.DataFrame,
    ref: pd.Timestamp,
    t: Thresholds,
) -> pd.DataFrame:
    recent_sales = _window(sales, ref, t.long_window_days)
    codes = stock_c.index.union(pd.Index(recent_sales["codigo_nacional"].unique()))
    refs = pd.DataFrame(index=pd.Index(codes, name="codigo_nacional"))

    sales_sorted = sales.sort_values("fecha")
    sales_info = sales_sorted.groupby("codigo_nacional").agg(
        descripcion=("descripcion", "last"),
        laboratorio=("laboratorio", "last"),
        familia=("familia", "last"),
    )
    with_cost = sales_sorted[sales_sorted["coste_unitario"] > 0]
    sales_cost = with_cost.groupby("codigo_nacional")["coste_unitario"].last()

    valid_p = purchases[(purchases["unidades"] > 0) & (purchases["coste_total"] > 0)]
    p_grouped = valid_p.groupby("codigo_nacional")
    purchase_cost = p_grouped["coste_total"].sum() / p_grouped["unidades"].sum()
    purchase_lab = purchases.dropna(subset=["laboratorio"]).groupby("codigo_nacional")["laboratorio"].last()

    for column in ("descripcion", "laboratorio", "familia"):
        refs[column] = stock_c[column].reindex(codes)
        refs[column] = refs[column].fillna(sales_info[column].reindex(codes))
    refs["laboratorio"] = refs["laboratorio"].fillna(purchase_lab.reindex(codes)).fillna(UNKNOWN_LAB)
    refs["familia"] = refs["familia"].fillna(Family.OTHER.value)
    refs["en_fichero_stock"] = refs.index.isin(stock_c.index)

    refs["stock_unidades"] = stock_c["stock_unidades"].reindex(codes).fillna(0.0)
    refs["stock_negativo"] = refs["stock_unidades"] < 0
    refs["stock_valorable"] = refs["stock_unidades"].clip(lower=0)
    refs["pvp"] = stock_c["pvp"].reindex(codes)
    refs["fecha_caducidad"] = stock_c["fecha_caducidad"].reindex(codes)

    stock_cost = stock_c["coste_unitario"].reindex(codes)
    stock_cost = stock_cost.where(stock_cost > 0)
    fallback_sales = sales_cost.reindex(codes)
    fallback_purchase = purchase_cost.reindex(codes)
    refs["coste_unitario"] = stock_cost.fillna(fallback_sales).fillna(fallback_purchase)
    refs["coste_fuente"] = np.select(
        [stock_cost.notna(), fallback_sales.notna(), fallback_purchase.notna()],
        ["stock", "ventas", "compras"],
        default="desconocido",
    )
    refs["coste_desconocido"] = refs["coste_unitario"].isna()
    refs["valor_stock"] = (refs["stock_valorable"] * refs["coste_unitario"]).fillna(0.0)
    return refs


def _add_sales_metrics(
    refs: pd.DataFrame, sales: pd.DataFrame, ref: pd.Timestamp, history_days: int, t: Thresholds
) -> pd.DataFrame:
    codes = refs.index
    line_cost = sales["coste_unitario"].where(sales["coste_unitario"] > 0)
    line_cost = line_cost.fillna(sales["codigo_nacional"].map(refs["coste_unitario"]))
    sales = sales.assign(_coste=(sales["unidades"] * line_cost).fillna(0.0))

    for label, days in (("corta", t.short_window_days), ("larga", t.long_window_days)):
        window = _window(sales, ref, days)
        effective = max(1, min(days, history_days))
        grouped = window.groupby("codigo_nacional")
        units = grouped["unidades"].sum().reindex(codes).fillna(0.0)
        refs[f"unidades_{label}"] = units
        refs[f"consumo_diario_{label}"] = units.clip(lower=0) / effective
        refs[f"ventas_eur_{label}"] = grouped["importe_venta_sin_iva"].sum().reindex(codes).fillna(0.0)
        refs[f"coste_ventas_{label}"] = grouped["_coste"].sum().reindex(codes).fillna(0.0)

    short = _window(sales, ref, t.short_window_days)
    sale_days = short[short["unidades"] > 0].groupby("codigo_nacional")["fecha"].nunique()
    refs["dias_con_venta_corta"] = sale_days.reindex(codes).fillna(0).astype(int)

    last_sale = sales[sales["unidades"] > 0].groupby("codigo_nacional")["fecha"].max()
    refs["ultima_venta"] = last_sale.reindex(codes)
    refs["dias_sin_venta"] = (ref - refs["ultima_venta"]).dt.days
    lower_bound = refs["dias_sin_venta"].fillna(history_days)
    has_stock = refs["stock_valorable"] > 0
    refs["sin_movimiento_aviso"] = has_stock & (lower_bound >= t.no_movement_warning_days)
    refs["sin_movimiento_critico"] = has_stock & (lower_bound >= t.no_movement_critical_days)

    price = _safe_div(refs["ventas_eur_corta"], refs["unidades_corta"])
    refs["precio_medio_venta"] = price.fillna(_safe_div(refs["ventas_eur_larga"], refs["unidades_larga"]))

    annual_cost = refs["coste_ventas_larga"] / max(1, min(t.long_window_days, history_days)) * 365
    refs["rotacion_anual"] = _safe_div(annual_cost, refs["valor_stock"])
    refs["cobertura_dias"] = _safe_div(refs["stock_valorable"], refs["consumo_diario_corta"])
    return refs


def _add_stock_metrics(refs: pd.DataFrame, t: Thresholds) -> pd.DataFrame:
    target_days = refs["familia"].map(lambda f: t.coverage_for(f)).astype(float)
    refs["cobertura_objetivo_dias"] = target_days
    target_units = np.ceil(refs["consumo_diario_corta"] * target_days)
    excess = (refs["stock_valorable"] - target_units).clip(lower=0)
    excess = excess.where(~refs["sin_movimiento_critico"], 0.0)
    refs["sobrestock_unidades"] = excess
    refs["sobrestock_eur"] = (excess * refs["coste_unitario"]).fillna(0.0)

    horizon = t.replenishment_days + t.safety_days
    refs["punto_pedido"] = refs["consumo_diario_corta"] * horizon
    frequent = refs["dias_con_venta_corta"] >= t.frequent_min_sale_days
    refs["riesgo_rotura"] = frequent & (refs["stock_valorable"] < refs["punto_pedido"])
    lost_units = (refs["punto_pedido"] - refs["stock_valorable"]).clip(lower=0)
    refs["unidades_en_riesgo_rotura"] = lost_units.where(refs["riesgo_rotura"], 0.0)
    refs["ventas_perdidas_eur"] = (
        refs["unidades_en_riesgo_rotura"] * refs["precio_medio_venta"]
    ).fillna(0.0)
    return refs


def _add_expiry(refs: pd.DataFrame, ref: pd.Timestamp, t: Thresholds) -> pd.DataFrame:
    days_left = (refs["fecha_caducidad"] - ref).dt.days
    refs["dias_hasta_caducidad"] = days_left
    sellable = refs["consumo_diario_corta"] * days_left.clip(lower=0)
    at_risk_units = (refs["stock_valorable"] - sellable).clip(lower=0).where(days_left.notna(), 0.0)
    refs["unidades_riesgo_caducidad"] = at_risk_units
    risk_eur = (at_risk_units * refs["coste_unitario"]).fillna(0.0)
    refs["caducado"] = days_left < 0
    max_window = max(t.expiry_windows_days)
    refs["riesgo_caducidad_eur"] = risk_eur.where(days_left <= max_window, 0.0)
    for window in t.expiry_windows_days:
        refs[f"caduca_{window}d_eur"] = risk_eur.where(days_left <= window, 0.0)
    return refs


def _add_abc(refs: pd.DataFrame, t: Thresholds) -> pd.DataFrame:
    sales = refs["ventas_eur_larga"].clip(lower=0)
    total = sales.sum()
    refs["abc"] = "C"
    if total <= 0:
        return refs
    ordered = sales.sort_values(ascending=False, kind="mergesort")
    share = ordered / total
    previous = share.cumsum() - share
    classes = pd.Series(
        np.select([previous < t.abc_a_cut, previous < t.abc_b_cut], ["A", "B"], default="C"),
        index=ordered.index,
    )
    classes[ordered <= 0] = "C"
    refs["abc"] = classes.reindex(refs.index)
    return refs


def _lab_metrics(
    sales: pd.DataFrame, purchases: pd.DataFrame, refs: pd.DataFrame, ref: pd.Timestamp, t: Thresholds
) -> pd.DataFrame:
    start = ref - pd.DateOffset(months=t.lab_window_months) + pd.Timedelta(days=1)
    s = sales[sales["fecha"] >= start].copy()
    p = purchases[purchases["fecha"] >= start].copy()

    ref_lab = refs["laboratorio"]
    s["lab"] = s["codigo_nacional"].map(ref_lab).fillna(s["laboratorio"]).fillna(UNKNOWN_LAB)
    p["lab"] = p["laboratorio"].fillna(p["codigo_nacional"].map(ref_lab)).fillna(UNKNOWN_LAB)
    cost = s["coste_unitario"].where(s["coste_unitario"] > 0)
    cost = cost.fillna(s["codigo_nacional"].map(refs["coste_unitario"]))
    s["coste"] = (s["unidades"] * cost).fillna(0.0)

    sold = s.groupby("lab").agg(ventas_eur=("importe_venta_sin_iva", "sum"), coste_ventas=("coste", "sum"))
    bought = p.groupby("lab").agg(compras_coste=("coste_total", "sum"))
    labs = sold.join(bought, how="outer").fillna(0.0)
    labs.index.name = "laboratorio"
    labs["ratio_compras_ventas"] = _safe_div(labs["compras_coste"], labs["coste_ventas"])
    labs["margen_bruto_eur"] = labs["ventas_eur"] - labs["coste_ventas"]
    labs["margen_bruto_pct"] = _safe_div(labs["margen_bruto_eur"], labs["ventas_eur"]) * 100
    labs["exceso_compra_eur"] = (labs["compras_coste"] - labs["coste_ventas"]).clip(lower=0)
    high_ratio = labs["ratio_compras_ventas"].isna() | (labs["ratio_compras_ventas"] > t.lab_high_ratio)
    labs["compra_alta"] = high_ratio & (labs["compras_coste"] >= t.lab_min_purchases_eur)
    labs["valor_stock"] = refs.groupby("laboratorio")["valor_stock"].sum().reindex(labs.index).fillna(0.0)
    return labs.sort_values("compras_coste", ascending=False)


def _family_metrics(
    sales: pd.DataFrame, refs: pd.DataFrame, ref: pd.Timestamp, history_days: int, t: Thresholds
) -> pd.DataFrame:
    window = _window(sales, ref, t.long_window_days).copy()
    window["fam"] = window["codigo_nacional"].map(refs["familia"]).fillna(window["familia"])
    window["fam"] = window["fam"].fillna(Family.OTHER.value)
    cost = window["coste_unitario"].where(window["coste_unitario"] > 0)
    cost = cost.fillna(window["codigo_nacional"].map(refs["coste_unitario"]))
    window["coste"] = (window["unidades"] * cost).fillna(0.0)
    fams = window.groupby("fam").agg(ventas_eur=("importe_venta_sin_iva", "sum"), coste_ventas=("coste", "sum"))
    fams.index.name = "familia"
    fams["valor_stock"] = refs.groupby("familia")["valor_stock"].sum().reindex(fams.index).fillna(0.0)
    fams["margen_bruto_eur"] = fams["ventas_eur"] - fams["coste_ventas"]
    fams["margen_bruto_pct"] = _safe_div(fams["margen_bruto_eur"], fams["ventas_eur"]) * 100
    total = fams["ventas_eur"].sum()
    fams["peso_ventas_pct"] = fams["ventas_eur"] / total * 100 if total > 0 else 0.0
    return fams.sort_values("ventas_eur", ascending=False)


def _totals(refs: pd.DataFrame, labs: pd.DataFrame, t: Thresholds) -> dict[str, float]:
    def total(column: str, mask: pd.Series | None = None) -> float:
        series = refs[column] if mask is None else refs.loc[mask, column]
        value = float(series.sum())
        return 0.0 if math.isnan(value) else round(value, 2)

    warn, crit = refs["sin_movimiento_aviso"], refs["sin_movimiento_critico"]
    totals: dict[str, float] = {
        "valor_stock": total("valor_stock"),
        "referencias_con_stock": int((refs["stock_valorable"] > 0).sum()),
        "referencias_total": int(len(refs)),
        "sin_movimiento_aviso_eur": total("valor_stock", warn),
        "sin_movimiento_aviso_refs": int(warn.sum()),
        "sin_movimiento_critico_eur": total("valor_stock", crit),
        "sin_movimiento_critico_refs": int(crit.sum()),
        "sobrestock_eur": total("sobrestock_eur"),
        "sobrestock_refs": int((refs["sobrestock_eur"] > 0).sum()),
        "riesgo_caducidad_eur": total("riesgo_caducidad_eur"),
        "riesgo_caducidad_refs": int((refs["riesgo_caducidad_eur"] > 0).sum()),
        "riesgo_rotura_refs": int(refs["riesgo_rotura"].sum()),
        "ventas_perdidas_eur": total("ventas_perdidas_eur"),
        "ventas_anuales_eur": total("ventas_eur_larga"),
        "coste_ventas_anual_eur": total("coste_ventas_larga"),
        "referencias_coste_desconocido": int((refs["coste_desconocido"] & (refs["stock_valorable"] > 0)).sum()),
        "laboratorios_compra_alta": int(labs["compra_alta"].sum()),
    }
    for window in t.expiry_windows_days:
        totals[f"caduca_{window}d_eur"] = total(f"caduca_{window}d_eur")
    sales_total = totals["ventas_anuales_eur"]
    totals["margen_bruto_anual_pct"] = (
        round((sales_total - totals["coste_ventas_anual_eur"]) / sales_total * 100, 2) if sales_total > 0 else 0.0
    )
    return totals
