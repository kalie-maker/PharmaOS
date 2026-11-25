from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from engine.actions import ActionType, build_actions, priority_label
from engine.metrics import compute_metrics
from tests.factories import REF, daily_sales, purchases, sales, stock, with_ref


def _plan(t, s, st, p=None):
    t = with_ref(t)
    m = compute_metrics(sales(s), stock(st), purchases(p or []), t)
    return m, build_actions(m, t)


def _scenario():
    s = daily_sales("FAST", 365, units=3, price=5, cost=3, laboratorio="Lab A")
    s += daily_sales("OVER", 365, units=1, price=20, cost=10, laboratorio="Lab A", familia="otc")
    s += daily_sales("EXP", 365, units=1, price=4, cost=2, laboratorio="Lab B")
    s += daily_sales("OLD", 30, end=REF - pd.Timedelta(days=250), laboratorio="Lab B")
    st = [
        {"codigo_nacional": "FAST", "stock_unidades": 0, "coste_unitario": 3, "laboratorio": "Lab A"},
        {"codigo_nacional": "OVER", "stock_unidades": 245, "coste_unitario": 10, "laboratorio": "Lab A",
         "familia": "otc"},
        {"codigo_nacional": "EXP", "stock_unidades": 80, "coste_unitario": 2, "laboratorio": "Lab B",
         "fecha_caducidad": REF + pd.Timedelta(days=10)},
        {"codigo_nacional": "OLD", "stock_unidades": 30, "coste_unitario": 40, "laboratorio": "Lab B",
         "descripcion": "Viejo"},
    ]
    p = [{"fecha": REF - pd.Timedelta(days=20), "codigo_nacional": "OVER", "laboratorio": "Lab A",
          "unidades": 600, "coste_total": 6000}]
    return s, st, p


def test_each_action_type_is_built_with_expected_impact(thresholds) -> None:
    m, plan = _plan(thresholds, *_scenario())
    by_type = {a.type: a for a in plan.all}
    assert by_type[ActionType.RETURN_DEAD_STOCK].impact_eur == pytest.approx(1200)
    assert by_type[ActionType.RETURN_DEAD_STOCK].affected_codes == ["OLD"]
    assert by_type[ActionType.REDUCE_ORDER].impact_eur == pytest.approx(m.totals["sobrestock_eur"])
    assert by_type[ActionType.PROMOTE_BEFORE_EXPIRY].impact_eur == pytest.approx((80 - 10) * 2)
    assert by_type[ActionType.REPLENISH].impact_eur == pytest.approx(3 * 7 * 5)
    lab = by_type[ActionType.REVIEW_LAB]
    assert lab.subject == "Lab A"
    assert lab.facts["exceso_eur"] == pytest.approx(lab.impact_eur)


def test_actions_sorted_by_impact_with_priorities(thresholds) -> None:
    _, plan = _plan(thresholds, *_scenario())
    impacts = [a.impact_eur for a in plan.all]
    assert impacts == sorted(impacts, reverse=True)
    assert [a.priority for a in plan.all] == list(range(1, len(plan.all) + 1))


def test_dead_stock_not_double_counted(thresholds) -> None:
    _, plan = _plan(thresholds, *_scenario())
    for action in plan.all:
        if action.type in (ActionType.REDUCE_ORDER, ActionType.PROMOTE_BEFORE_EXPIRY):
            assert "OLD" not in action.affected_codes


def test_top_n_and_annex_split(thresholds) -> None:
    t = replace(thresholds, max_main_actions=2, max_refs_per_action=1, min_action_impact_eur=0)
    _, plan = _plan(t, *_scenario())
    assert len(plan.main) == 2
    assert len(plan.annex) >= 1
    assert all(len(a.references) <= 1 for a in plan.all)


def test_min_impact_filters_actions(thresholds) -> None:
    t = replace(thresholds, min_action_impact_eur=1_000_000)
    _, plan = _plan(t, *_scenario())
    assert plan.all == []


def test_no_problems_no_actions(thresholds) -> None:
    s = daily_sales("A", 365, units=1)
    st = [{"codigo_nacional": "A", "stock_unidades": 20, "coste_unitario": 5}]
    _, plan = _plan(thresholds, s, st)
    assert plan.all == []


@pytest.mark.parametrize(("rank", "label"), [(1, "Alta"), (3, "Alta"), (4, "Media"), (8, "Baja")])
def test_priority_label(rank: int, label: str) -> None:
    assert priority_label(rank) == label
