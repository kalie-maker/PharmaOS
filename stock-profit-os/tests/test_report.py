from __future__ import annotations

import json
import math

import pytest

from engine.formatting import eur, eur0, number, pct, spanish_date
from engine.narrative import TemplateNarrator, narrate
from engine.pipeline import run_analysis
from engine.report import clean, render_html, render_markdown, write_reports


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1234.56, "1.234,56 €"), (0, "0,00 €"), (-5.5, "-5,50 €"), (1234567.891, "1.234.567,89 €"), (None, "—")],
)
def test_eur(value, expected) -> None:
    assert eur(value) == expected


def test_other_formats() -> None:
    assert eur0(3400.4) == "3.400 €"
    assert number(1234) == "1.234"
    assert pct(12.345) == "12,3 %"
    assert spanish_date("2026-11-20") == "20/11/2026"
    assert eur(float("nan")) == "—"


def test_clean_handles_nan_and_numpy() -> None:
    import numpy as np
    import pandas as pd

    out = clean({"a": np.float64(1.234), "b": float("nan"), "c": pd.Timestamp("2026-01-02"), "d": np.bool_(True)})
    assert out == {"a": 1.23, "b": None, "c": "2026-01-02", "d": True}


@pytest.fixture(scope="module")
def analysis(small_mock_paths, farmatic, thresholds):
    return run_analysis(small_mock_paths, farmatic, thresholds, "Farmacia Demo")


def test_results_structure(analysis, thresholds) -> None:
    r = analysis.results
    assert r["farmacia"] == "Farmacia Demo"
    assert 1 <= len(r["acciones"]) <= thresholds.max_main_actions
    for a in r["acciones"]:
        assert a["titulo"] and a["explicacion"]
        assert a["prioridad"] in {"Alta", "Media", "Baja"}
    assert r["cifras_clave"]["valor_stock_eur"] == pytest.approx(analysis.metrics.totals["valor_stock"])
    json.dumps(r)  # serializable
    assert "NaN" not in json.dumps(r)


def test_numbers_come_from_metrics(analysis) -> None:
    r = analysis.results
    dead = next(a for a in r["acciones"] + r["anexo_acciones"] if a["type"] == "devolver_sin_movimiento")
    assert dead["impact_eur"] == pytest.approx(analysis.metrics.totals["sin_movimiento_critico_eur"], abs=0.01)
    assert eur0(dead["impact_eur"]) in dead["explicacion"]


def test_html_and_markdown_render(analysis) -> None:
    html = render_html(analysis.results)
    md = render_markdown(analysis.results)
    for text in (html, md):
        assert "Farmacia Demo" in text
        assert eur(analysis.results["cifras_clave"]["valor_stock_eur"]) in text
        assert analysis.results["acciones"][0]["titulo"] in text
    assert "@page" in html and "A4" in html


def test_write_reports(analysis, tmp_path) -> None:
    paths = write_reports(analysis.results, tmp_path, "semana0")
    assert {p.name for p in paths.values()} == {"semana0.html", "semana0.md", "semana0.json"}
    loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert loaded["acciones"] == analysis.results["acciones"]


def test_custom_narrator_only_receives_json(analysis) -> None:
    class Upper(TemplateNarrator):
        def summary(self, results):
            assert isinstance(results, dict)
            return "RESUMEN"

    r = narrate(json.loads(json.dumps(analysis.results)), Upper())
    assert r["resumen"] == "RESUMEN"


def test_end_to_end_full_mock(full_mock, farmatic, thresholds, tmp_path) -> None:
    paths = full_mock.write(tmp_path)
    out = run_analysis(paths, farmatic, thresholds, "Farmacia Demo")
    r = out.results
    types = {a["type"] for a in r["acciones"]}
    assert {"devolver_sin_movimiento", "reducir_pedido", "promocionar_caducidad", "reponer_rotura",
            "revisar_laboratorio"} <= types
    flagged = {a["facts"]["laboratorio"] for a in r["acciones"] if a["type"] == "revisar_laboratorio"}
    assert set(full_mock.overbought_labs) <= flagged
    impacts = [a["impact_eur"] for a in r["acciones"]]
    assert impacts == sorted(impacts, reverse=True)
    share_dead = r["cifras_clave"]["sin_movimiento_refs"] / r["totales"]["referencias_con_stock"]
    assert 0.08 <= share_dead <= 0.15
    assert not math.isnan(r["totales"]["valor_stock"])
    write_reports(r, tmp_path / "out", "e2e")
