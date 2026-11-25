from __future__ import annotations

from datetime import date

import pytest

from engine.ingest import load_all
from engine.pipeline import run_analysis
from engine.quality import assess_quality
from engine.report import render_html, render_markdown
from tests import dirty

TODAY = date(2026, 11, 25)


@pytest.fixture(scope="module")
def dirty_paths(small_mock, tmp_path_factory):
    return dirty.degrade_mock(small_mock).write(tmp_path_factory.mktemp("dirty"))


def _by_id(report):
    return {c.id: c for c in report.comprobaciones}


def test_clean_mock_is_good(small_mock_paths, farmatic, thresholds) -> None:
    report = assess_quality(load_all(small_mock_paths, farmatic, thresholds), thresholds, TODAY)
    assert report.nivel == "buena"
    assert all(c.estado == "ok" for c in report.comprobaciones)


def test_dirty_mock_is_low_and_explains(dirty_paths, farmatic, thresholds) -> None:
    report = assess_quality(load_all(dirty_paths, farmatic, thresholds), thresholds, TODAY)
    checks = _by_id(report)
    assert report.nivel == "baja"
    assert checks["costes_vacios"].estado == "mal" and checks["costes_vacios"].porcentaje > 5
    assert checks["stock_negativo"].estado == "mal"
    assert checks["fechas_fuera_rango"].estado == "mal"
    assert checks["sin_descripcion"].estado == "mal"
    assert checks["duplicados_stock"].estado == "mal"
    assert checks["filas_duplicadas"].estado == "mal"
    assert checks["ventas_sin_stock"].estado == "ok"
    assert any("Calidad de datos: BAJA" in line for line in report.lines())


def test_old_dates_are_out_of_range(small_mock, farmatic, thresholds, tmp_path) -> None:
    from dataclasses import replace

    mock = dirty.MockData(small_mock.sales.copy(), small_mock.stock, small_mock.purchases, [])
    mock.sales.loc[mock.sales.index[:100], "Fecha"] = "01/01/2019"
    report = assess_quality(load_all(mock.write(tmp_path), farmatic, thresholds), thresholds, TODAY)
    assert _by_id(report)["fechas_fuera_rango"].afectados >= 100
    strict = replace(thresholds, quality=replace(thresholds.quality, max_age_days=10_000))
    report = assess_quality(load_all(mock.write(tmp_path), farmatic, strict), strict, TODAY)
    assert _by_id(report)["fechas_fuera_rango"].afectados == 0


def test_warning_level(small_mock, farmatic, thresholds, tmp_path) -> None:
    mock = dirty.MockData(small_mock.sales, small_mock.stock.copy(), small_mock.purchases, [])
    n = len(mock.stock)
    mock.stock.loc[mock.stock.index[: int(n * 0.03)], "P.Coste"] = None  # 3 %: > 50 % del límite (5 %)
    report = assess_quality(load_all(mock.write(tmp_path), farmatic, thresholds), thresholds, TODAY)
    assert report.nivel == "aceptable"
    assert _by_id(report)["costes_vacios"].estado == "aviso"


def test_low_quality_banner_at_top_of_report(dirty_paths, farmatic, thresholds) -> None:
    out = run_analysis(dirty_paths, farmatic, thresholds, "Farmacia Demo", today=TODAY)
    assert out.results["calidad"]["nivel"] == "baja"
    html = render_html(out.results)
    banner = html.index("Calidad de datos baja")
    assert banner < html.index("Acciones de la semana")
    assert banner < html.index("Stock total a coste")
    md = render_markdown(out.results)
    assert md.index("Calidad de datos baja") < md.index("## Acciones de la semana")


def test_good_quality_has_no_banner(small_mock_paths, farmatic, thresholds) -> None:
    out = run_analysis(small_mock_paths, farmatic, thresholds, "Farmacia Demo", today=TODAY)
    assert "Calidad de datos" not in render_html(out.results)
