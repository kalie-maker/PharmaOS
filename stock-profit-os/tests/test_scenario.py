from __future__ import annotations

from datetime import date

import pytest

from engine.compare import compare, headline
from engine.mock.generate import MockConfig
from engine.mock.scenario import generate_week3_scenario
from engine.pipeline import run_analysis


@pytest.fixture(scope="module")
def scenario(tmp_path_factory, farmatic, thresholds):
    out = tmp_path_factory.mktemp("demo")
    info = generate_week3_scenario(out, MockConfig(n_refs=800, seed=21, end_date=date(2026, 11, 20)))
    r0 = run_analysis(info["semana0"], farmatic, thresholds, "Farmacia Demo", today=date(2026, 11, 25)).results
    r3 = run_analysis(info["semana3"], farmatic, thresholds, "Farmacia Demo", today=date(2026, 11, 25)).results
    return out, info, r0, r3


def test_files_and_dates(scenario) -> None:
    out, info, r0, r3 = scenario
    for week in ("semana0", "semana3"):
        assert {p.name for p in (out / week).iterdir()} == {"ventas.csv", "stock.csv", "compras.csv"}
    assert (out / "LEEME.md").exists()
    assert r0["periodo"]["fecha_referencia"] == "2026-10-30"
    assert r3["periodo"]["fecha_referencia"] == "2026-11-20"


def test_week3_has_good_quality(scenario) -> None:
    _, _, r0, r3 = scenario
    assert r0["calidad"]["nivel"] == "buena"
    assert r3["calidad"]["nivel"] == "buena"


def test_comparison_is_credible(scenario, thresholds) -> None:
    _, info, r0, r3 = scenario
    c = compare(r0, r3, thresholds.comparison)
    assert c["dias"] == 21
    assert c["stock_liberado_eur"] > 0
    # Creíble: se libera una parte del stock, no todo.
    assert c["stock_liberado_eur"] < 0.35 * r0["totales"]["valor_stock"]
    states = {a["tipo"]: a["estado"] for a in c["acciones"]}
    assert states["devolver_sin_movimiento"] == "ejecutada"
    assert states["promocionar_caducidad"] in {"ejecutada", "parcial"}
    assert states["reducir_pedido"] in {"parcial", "pendiente"}
    all_states = [a["estado"] for a in c["acciones"]]
    assert "ejecutada" in all_states and any(s != "ejecutada" for s in all_states)
    assert "has liberado" in headline(c)
    assert info["resumen"]["referencias_devueltas"] > 0


def test_scenario_is_reproducible(tmp_path) -> None:
    cfg = MockConfig(n_refs=200, seed=4)
    generate_week3_scenario(tmp_path / "a", cfg)
    generate_week3_scenario(tmp_path / "b", cfg)
    for week in ("semana0", "semana3"):
        for name in ("ventas.csv", "stock.csv", "compras.csv"):
            assert (tmp_path / "a" / week / name).read_bytes() == (tmp_path / "b" / week / name).read_bytes()
