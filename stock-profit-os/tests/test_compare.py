from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest

from engine.compare import CompareError, compare, load_results, render_markdown, render_text
from engine.pipeline import run_analysis
from engine.report import write_reports
from tests import dirty


@pytest.fixture(scope="module")
def weeks(small_mock, farmatic, thresholds, tmp_path_factory):
    base = tmp_path_factory.mktemp("weeks")
    today = date(2027, 1, 1)  # la semana simulada cae después de la fecha del sistema
    before = run_analysis(small_mock.write(base / "s0"), farmatic, thresholds, "Farmacia Demo", today=today)
    by_type = {a["type"]: a for a in before.results["acciones"] + before.results["anexo_acciones"]}
    dead = by_type["devolver_sin_movimiento"]["affected_codes"]
    over = by_type["reducir_pedido"]["affected_codes"]
    after_mock = dirty.simulate_after(small_mock, 21, dead_codes=dead, overstock_codes=over)
    after = run_analysis(after_mock.write(base / "s3"), farmatic, thresholds, "Farmacia Demo", today=today)
    p0 = write_reports(before.results, base / "out", "semana0")["json"]
    p3 = write_reports(after.results, base / "out", "semana3")["json"]
    return load_results(p0), load_results(p3)


def test_reductions_are_measured(weeks, thresholds) -> None:
    before, after = weeks
    c = compare(before, after, thresholds.comparison)
    ind = {i["id"]: i for i in c["indicadores"]}
    assert c["dias"] == 21
    assert ind["sin_movimiento_critico_eur"]["despues"] < ind["sin_movimiento_critico_eur"]["antes"]
    assert ind["sobrestock_eur"]["reduccion"] > 0
    assert c["reduccion_total_eur"] > 0


def test_executed_actions_are_detected(weeks, thresholds) -> None:
    before, after = weeks
    c = compare(before, after, thresholds.comparison)
    status = {a["tipo"]: a["estado"] for a in c["acciones"]}
    dead = next(a for a in c["acciones"] if a["tipo"] == "devolver_sin_movimiento")
    assert status["devolver_sin_movimiento"] == "ejecutada"
    assert dead["despues_eur"] == 0 and dead["reducido_eur"] == dead["antes_eur"]
    assert status["reducir_pedido"] in {"ejecutada", "parcial"}
    assert c["acciones_ejecutadas"] >= 1


def test_same_week_no_progress(weeks, thresholds) -> None:
    before, _ = weeks
    later = json.loads(json.dumps(before))
    later["periodo"]["fecha_referencia"] = "2099-01-01"
    c = compare(before, later, thresholds.comparison)
    assert all(a["estado"] in {"pendiente", "sin_datos"} for a in c["acciones"])
    assert c["reduccion_total_eur"] == 0


def test_order_and_pharmacy_checks(weeks, thresholds) -> None:
    before, after = weeks
    with pytest.raises(CompareError, match="posterior"):
        compare(after, before, thresholds.comparison)
    other = dict(after, farmacia="Otra farmacia")
    assert any("distintas" in w for w in compare(before, other, thresholds.comparison)["avisos"])
    anon = dict(after, farmacia="Farmacia Demo", anonimizado=True)
    assert not compare(before, anon, thresholds.comparison)["avisos"]


def test_thresholds_change_status(weeks, thresholds) -> None:
    before, after = weeks
    strict = replace(thresholds.comparison, done_threshold=1.0, partial_threshold=0.999)
    c = compare(before, after, strict)
    assert all(a["estado"] != "ejecutada" or a["avance"] == 1.0 for a in c["acciones"])


def test_render(weeks, thresholds) -> None:
    c = compare(*weeks, thresholds.comparison)
    text, md = render_text(c), render_markdown(c)
    assert "has liberado" in text and "Parece ejecutada" in text
    assert md.startswith("# Farmacia Demo")


def test_invalid_files(tmp_path) -> None:
    bad = tmp_path / "x.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(CompareError):
        load_results(bad)
    with pytest.raises(CompareError):
        load_results(tmp_path / "nope.json")
