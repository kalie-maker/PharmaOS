from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from engine.cli import EXIT_OK, main
from engine.pipeline import run_analysis
from engine.privacy import check_content, check_headers
from engine.web_export import ACTION_TYPES, build_report, weekly_sales

SCHEMA = json.loads((Path(__file__).resolve().parent.parent / "docs" / "report-schema.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def analysis(small_mock_paths, farmatic, thresholds):
    return run_analysis(small_mock_paths, farmatic, thresholds, "Farmacia Demo")


@pytest.fixture(scope="module")
def report(analysis, thresholds):
    return build_report(analysis.metrics, analysis.ingest["ventas"].data, thresholds, "Farmacia Demo", "farmatic")


def test_schema_validates(report) -> None:
    jsonschema.validate(report, SCHEMA, format_checker=jsonschema.FormatChecker())
    json.dumps(report, allow_nan=False)  # sin NaN/Infinity


def test_schema_rejects_bad_report(report) -> None:
    broken = json.loads(json.dumps(report))
    broken["acciones"][0]["tipo"] = "INVENTADO"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, SCHEMA)
    broken = json.loads(json.dumps(report))
    broken["productos"][next(iter(broken["productos"]))]["dni"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, SCHEMA)


def test_amounts_match_engine_metrics(report, analysis) -> None:
    refs = analysis.metrics.refs
    column = {"DEVOLVER": "valor_stock", "BAJAR_PEDIDO": "sobrestock_eur", "REPONER": "ventas_perdidas_eur",
              "CADUCA_PRONTO": "riesgo_caducidad_eur"}
    for action in report["acciones"]:
        expected = refs.loc[action["producto_id"], column[action["tipo"]]]
        assert action["importe_eur"] == pytest.approx(expected, abs=0.01)
        assert action["producto_id"] in report["productos"]
    s = report["resumen"]
    assert s["recuperable_semana_eur"] == pytest.approx(sum(a["importe_eur"] for a in report["acciones"]), abs=0.05)
    assert s["capital_inmovilizado_eur"] == pytest.approx(analysis.metrics.totals["sin_movimiento_critico_eur"])
    assert s["stock_total_eur"] == pytest.approx(analysis.metrics.totals["valor_stock"])
    assert sum(s["acciones_por_tipo"].values()) == s["acciones_total"] == len(report["acciones"])


def test_actions_sorted_unique_and_limited(report, thresholds) -> None:
    amounts = [a["importe_eur"] for a in report["acciones"]]
    assert amounts == sorted(amounts, reverse=True)
    ids = [a["id"] for a in report["acciones"]]
    products = [a["producto_id"] for a in report["acciones"]]
    assert len(set(ids)) == len(ids) and len(set(products)) == len(products)
    for kind in ACTION_TYPES:
        n = sum(1 for a in report["acciones"] if a["tipo"] == kind)
        assert n <= thresholds.web.actions_per_type[kind]
    assert all(a["importe_eur"] >= thresholds.web.min_amount_eur for a in report["acciones"])


def test_explanation_uses_real_numbers(report) -> None:
    from engine.formatting import eur

    for action in report["acciones"]:
        steps = action["calculo_explicado"]["pasos"]
        assert len(steps) >= 4
        assert eur(action["importe_eur"]) in steps[-1]["valor"]


def test_weekly_sales_shape(analysis, report, thresholds) -> None:
    sales = analysis.ingest["ventas"].data
    weekly = weekly_sales(sales, analysis.metrics.reference_date, thresholds.web.sales_weeks)
    code, values = next(iter(weekly.items()))
    assert len(values) == 12
    ref = analysis.metrics.reference_date
    last_week = sales[(sales["codigo_nacional"] == code) & ((ref - sales["fecha"]).dt.days < 7)]["unidades"].sum()
    assert values[-1] == round(last_week)
    assert all(len(p["ventas_semanales_12"]) == 12 for p in report["productos"].values())


def test_history(report, thresholds) -> None:
    h = report["historico_semanas"]
    assert report["historico_simulado"] is True
    assert len(h) == thresholds.web.history_weeks
    assert [w["fecha_inicio"] for w in h] == sorted(w["fecha_inicio"] for w in h)
    for w in h:
        assert w["recuperado_eur"] <= w["ejecutado_eur"] <= w["encontrado_eur"]


def _walk(value, keys: list[str], strings: list[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            keys.append(k)
            _walk(v, keys, strings)
    elif isinstance(value, list):
        for v in value:
            _walk(v, keys, strings)
    elif isinstance(value, str):
        strings.append(value)


def test_no_sensitive_fields(report) -> None:
    import pandas as pd

    keys: list[str] = []
    strings: list[str] = []
    _walk(report, keys, strings)
    assert check_headers(sorted(set(keys))) == []
    assert check_content(pd.DataFrame({"valores": strings})) == []


def test_cli_export_json(small_mock_paths, tmp_path) -> None:
    out = tmp_path / "out" / "report.json"
    code = main(["exportar-json", "--programa", "farmatic", "--ventas", str(small_mock_paths["ventas"]),
                 "--stock", str(small_mock_paths["stock"]), "--compras", str(small_mock_paths["compras"]),
                 "--salida", str(out)])
    assert code == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["farmacia"]["ficticia"] is False
    jsonschema.validate(data, SCHEMA)
    assert main(["exportar-json", "--salida", str(out)]) != EXIT_OK  # ni --mock ni ficheros


def test_cli_export_json_mock(tmp_path) -> None:
    out = tmp_path / "report.json"
    assert main(["exportar-json", "--mock", "--referencias", "600", "--salida", str(out)]) == EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["farmacia"]["ficticia"] is True
    assert len(data["productos"]) == 600
    jsonschema.validate(data, SCHEMA)
