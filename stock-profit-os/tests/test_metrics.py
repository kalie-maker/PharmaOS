from __future__ import annotations

import math

import pandas as pd
import pytest

from engine.metrics import MetricsError, compute_metrics, consolidate_stock
from tests.factories import REF, daily_sales, purchases, sales, stock, with_ref


def _run(t, s, st, p=None):
    return compute_metrics(sales(s), stock(st), purchases(p or []), with_ref(t))


def test_basic_consumption_coverage_and_value(thresholds) -> None:
    s = daily_sales("000001", 365, units=2, price=10, cost=6, familia="otc")
    st = [{"codigo_nacional": "000001", "stock_unidades": 60, "coste_unitario": 6, "familia": "otc"}]
    r = _run(thresholds, s, st).refs.loc["000001"]
    assert r["valor_stock"] == pytest.approx(360)
    assert r["consumo_diario_corta"] == pytest.approx(2)
    assert r["consumo_diario_larga"] == pytest.approx(2)
    assert r["cobertura_dias"] == pytest.approx(30)
    assert r["rotacion_anual"] == pytest.approx(365 * 2 * 6 / 360)
    assert r["dias_sin_venta"] == 0
    assert not r["sin_movimiento_aviso"]
    assert r["sobrestock_unidades"] == 0  # objetivo otc 45 días = 90 uds > 60


def test_overstock_above_target(thresholds) -> None:
    s = daily_sales("000001", 365, units=1, familia="medicamento_receta")
    st = [{"codigo_nacional": "000001", "stock_unidades": 100, "coste_unitario": 5,
           "familia": "medicamento_receta"}]
    r = _run(thresholds, s, st).refs.loc["000001"]
    assert r["sobrestock_unidades"] == 70  # objetivo 30 días x 1 ud/día
    assert r["sobrestock_eur"] == pytest.approx(350)


def test_no_movement_flags_and_never_sold(thresholds) -> None:
    s = daily_sales("000001", 400, every=1, end=REF - pd.Timedelta(days=100))  # última venta hace 100 días
    s += daily_sales("000003", 365)  # fija histórico de 365 días
    st = [
        {"codigo_nacional": "000001", "stock_unidades": 3, "coste_unitario": 10},
        {"codigo_nacional": "000002", "stock_unidades": 2, "coste_unitario": 50},  # nunca vendida
        {"codigo_nacional": "000003", "stock_unidades": 5, "coste_unitario": 1},
    ]
    res = _run(thresholds, s, st)
    a, b = res.refs.loc["000001"], res.refs.loc["000002"]
    assert a["dias_sin_venta"] == 100
    assert a["sin_movimiento_aviso"] and not a["sin_movimiento_critico"]
    assert math.isnan(b["dias_sin_venta"])
    assert b["sin_movimiento_critico"]
    assert res.totals["sin_movimiento_critico_eur"] == pytest.approx(100)
    assert res.totals["sin_movimiento_critico_refs"] == 1
    # Sin movimiento crítico no cuenta como sobrestock (evita doble conteo).
    assert b["sobrestock_eur"] == 0


def test_zero_stock_is_never_dead_and_can_be_stockout(thresholds) -> None:
    s = daily_sales("000001", 365, units=3, price=4)
    st = [{"codigo_nacional": "000001", "stock_unidades": 0, "coste_unitario": 2}]
    r = _run(thresholds, s, st).refs.loc["000001"]
    assert r["valor_stock"] == 0
    assert not r["sin_movimiento_critico"]
    assert r["riesgo_rotura"]
    horizon = thresholds.replenishment_days + thresholds.safety_days
    assert r["punto_pedido"] == pytest.approx(3 * horizon)
    assert r["ventas_perdidas_eur"] == pytest.approx(3 * horizon * 4)
    assert r["cobertura_dias"] == 0


def test_infrequent_sales_are_not_stockout_risk(thresholds) -> None:
    s = daily_sales("000001", 90, every=30)  # 3 días con venta
    st = [{"codigo_nacional": "000001", "stock_unidades": 0, "coste_unitario": 2}]
    assert not _run(thresholds, s, st).refs.loc["000001", "riesgo_rotura"]


def test_negative_stock_valued_as_zero(thresholds) -> None:
    st = [{"codigo_nacional": "000001", "stock_unidades": -4, "coste_unitario": 3}]
    r = _run(thresholds, daily_sales("000009", 10), st).refs.loc["000001"]
    assert r["stock_negativo"]
    assert r["valor_stock"] == 0


def test_missing_cost_fallbacks(thresholds) -> None:
    s = daily_sales("000001", 30, cost=7) + daily_sales("000002", 30, cost=float("nan"))
    st = [
        {"codigo_nacional": "000001", "stock_unidades": 2, "coste_unitario": None},
        {"codigo_nacional": "000002", "stock_unidades": 2, "coste_unitario": 0},
        {"codigo_nacional": "000003", "stock_unidades": 2, "coste_unitario": None},
    ]
    p = [{"fecha": REF, "codigo_nacional": "000002", "unidades": 4, "coste_total": 20}]
    refs = _run(thresholds, s, st, p).refs
    assert refs.loc["000001", "coste_unitario"] == 7 and refs.loc["000001", "coste_fuente"] == "ventas"
    assert refs.loc["000002", "coste_unitario"] == 5 and refs.loc["000002", "coste_fuente"] == "compras"
    assert refs.loc["000003", "coste_desconocido"] and refs.loc["000003", "valor_stock"] == 0


def test_duplicate_stock_rows_are_consolidated(thresholds) -> None:
    st = stock([
        {"codigo_nacional": "000001", "stock_unidades": 2, "coste_unitario": 10, "descripcion": "A",
         "fecha_caducidad": "2027-01-01"},
        {"codigo_nacional": "000001", "stock_unidades": 6, "coste_unitario": 14, "descripcion": None,
         "fecha_caducidad": "2026-09-01"},
    ])
    c = consolidate_stock(st).loc["000001"]
    assert c["stock_unidades"] == 8
    assert c["coste_unitario"] == pytest.approx(13)
    assert c["descripcion"] == "A"
    assert c["fecha_caducidad"] == pd.Timestamp("2026-09-01")
    assert c["filas_stock"] == 2


def test_sold_but_not_in_stock_is_included(thresholds) -> None:
    refs = _run(thresholds, daily_sales("000001", 60, descripcion="X"), []).refs
    assert "000001" in refs.index
    assert not refs.loc["000001", "en_fichero_stock"]
    assert refs.loc["000001", "descripcion"] == "X"


def test_short_history_divides_by_available_days(thresholds) -> None:
    s = daily_sales("000001", 30, units=1)
    st = [{"codigo_nacional": "000001", "stock_unidades": 1, "coste_unitario": 1}]
    r = _run(thresholds, s, st).refs.loc["000001"]
    assert r["consumo_diario_larga"] == pytest.approx(1)
    assert r["consumo_diario_corta"] == pytest.approx(1)


def test_returns_net_against_sales(thresholds) -> None:
    s = daily_sales("000001", 10, units=1)
    s.append({"fecha": REF, "codigo_nacional": "000001", "unidades": -20, "importe_venta_sin_iva": -200,
              "coste_unitario": 6})
    st = [{"codigo_nacional": "000001", "stock_unidades": 1, "coste_unitario": 6}]
    r = _run(thresholds, s, st).refs.loc["000001"]
    assert r["consumo_diario_corta"] == 0  # nunca negativo


def test_expiry_risk_uses_sellable_units(thresholds) -> None:
    s = daily_sales("000001", 365, units=1)
    st = [
        {"codigo_nacional": "000001", "stock_unidades": 50, "coste_unitario": 2,
         "fecha_caducidad": REF + pd.Timedelta(days=20)},
        {"codigo_nacional": "000002", "stock_unidades": 5, "coste_unitario": 3,
         "fecha_caducidad": REF + pd.Timedelta(days=200)},
        {"codigo_nacional": "000003", "stock_unidades": 4, "coste_unitario": 1, "fecha_caducidad": None},
    ]
    res = _run(thresholds, s, st)
    r = res.refs.loc["000001"]
    assert r["unidades_riesgo_caducidad"] == 30  # 50 - 20 días x 1 ud/día
    assert r["caduca_30d_eur"] == pytest.approx(60)
    assert r["caduca_90d_eur"] == pytest.approx(60)
    assert res.refs.loc["000002", "riesgo_caducidad_eur"] == 0  # fuera de la ventana
    assert res.refs.loc["000003", "riesgo_caducidad_eur"] == 0
    assert res.totals["caduca_30d_eur"] == pytest.approx(60)


def test_already_expired_counts_entire_stock(thresholds) -> None:
    st = [{"codigo_nacional": "000001", "stock_unidades": 5, "coste_unitario": 2,
           "fecha_caducidad": REF - pd.Timedelta(days=3)}]
    r = _run(thresholds, daily_sales("000001", 365), st).refs.loc["000001"]
    assert r["caducado"] and r["caduca_30d_eur"] == pytest.approx(10)


def test_abc_classification(thresholds) -> None:
    s = (daily_sales("A", 100, price=80) + daily_sales("B", 100, price=12)
         + daily_sales("C", 100, price=4) + daily_sales("D", 10, units=0, price=0))
    refs = _run(thresholds, s, []).refs
    assert refs.loc["A", "abc"] == "A"
    assert refs.loc["B", "abc"] == "B"
    assert refs.loc["C", "abc"] == "C"


def test_lab_ratio_and_margin(thresholds) -> None:
    s = daily_sales("000001", 100, units=1, price=10, cost=6, laboratorio="Lab Uno")
    p = [{"fecha": REF - pd.Timedelta(days=10), "codigo_nacional": "000001", "laboratorio": "Lab Uno",
          "unidades": 150, "coste_total": 900},
         {"fecha": REF - pd.Timedelta(days=300), "codigo_nacional": "000001", "laboratorio": "Lab Uno",
          "unidades": 999, "coste_total": 9999}]  # fuera de los 6 meses
    labs = _run(thresholds, s, [], p).labs
    lab = labs.loc["Lab Uno"]
    assert lab["coste_ventas"] == pytest.approx(600)
    assert lab["compras_coste"] == pytest.approx(900)
    assert lab["ratio_compras_ventas"] == pytest.approx(1.5)
    assert lab["margen_bruto_pct"] == pytest.approx(40)
    assert lab["exceso_compra_eur"] == pytest.approx(300)
    assert lab["compra_alta"]


def test_lab_with_purchases_and_no_sales_is_high(thresholds) -> None:
    p = [{"fecha": REF, "codigo_nacional": "000002", "laboratorio": "Lab Dos", "unidades": 100,
          "coste_total": 1000}]
    labs = _run(thresholds, daily_sales("000001", 10), [], p).labs
    assert labs.loc["Lab Dos", "compra_alta"]
    assert math.isnan(labs.loc["Lab Dos", "ratio_compras_ventas"])


def test_family_weights_sum_100(thresholds) -> None:
    s = daily_sales("000001", 50, price=10, familia="otc") + daily_sales("000002", 50, price=30, familia="solares")
    fams = _run(thresholds, s, []).families
    assert fams["peso_ventas_pct"].sum() == pytest.approx(100)
    assert fams.loc["solares", "peso_ventas_pct"] == pytest.approx(75)
    assert fams.loc["otc", "margen_bruto_pct"] == pytest.approx(40)


def test_family_falls_back_to_otros(thresholds) -> None:
    refs = _run(thresholds, daily_sales("000001", 5), []).refs
    assert refs.loc["000001", "familia"] == "otros"
    assert refs.loc["000001", "laboratorio"] == "Sin laboratorio"


def test_no_sales_without_reference_date_raises(thresholds) -> None:
    with pytest.raises(MetricsError):
        compute_metrics(sales([]), stock([]), purchases([]), thresholds)


def test_reference_date_defaults_to_last_sale(thresholds) -> None:
    res = compute_metrics(sales(daily_sales("000001", 5)), stock([]), purchases([]), thresholds)
    assert res.reference_date == REF


def test_future_rows_after_reference_are_ignored(thresholds) -> None:
    s = daily_sales("000001", 10) + daily_sales("000001", 5, units=100, end=REF + pd.Timedelta(days=30))
    r = _run(thresholds, s, []).refs.loc["000001"]
    assert r["unidades_corta"] == 10


def test_metrics_on_mock(small_mock_paths, farmatic, thresholds) -> None:
    from engine.ingest import load_all

    data = {k: v.data for k, v in load_all(small_mock_paths, farmatic, thresholds).items()}
    res = compute_metrics(data["ventas"], data["stock"], data["compras"], thresholds)
    assert res.totals["valor_stock"] > 0
    assert 0 < res.totals["sin_movimiento_critico_refs"] < res.totals["referencias_con_stock"]
    assert res.refs.index.is_unique
    assert set(res.refs["abc"]) <= {"A", "B", "C"}
