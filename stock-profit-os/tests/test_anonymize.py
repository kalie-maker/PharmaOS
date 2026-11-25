from __future__ import annotations

import json
import re

import pytest

from engine.anonymize import Anonymizer, _letters
from engine.compare import compare
from engine.pipeline import run_analysis
from engine.report import render_html, render_markdown

REAL_NAME = "Farmacia Ldo. Pérez Calle Mayor 12"


@pytest.fixture(scope="module")
def plain(small_mock_paths, farmatic, thresholds):
    return run_analysis(small_mock_paths, farmatic, thresholds, REAL_NAME).results


def _outputs(results) -> list[str]:
    return [json.dumps(results, ensure_ascii=False), render_html(results), render_markdown(results)]


def _originals(small_mock):
    stock = small_mock.stock
    labs = set(stock["Laboratorio"]) | set(small_mock.sales["Laboratorio"]) | set(small_mock.purchases["Laboratorio"])
    return labs, set(stock["Código"]), set(stock["Descripción"])


def test_letters() -> None:
    assert [_letters(i) for i in (0, 1, 25, 26, 27, 701)] == ["A", "B", "Z", "AA", "AB", "ZZ"]


def test_plain_report_contains_originals(plain, small_mock) -> None:
    labs, codes, _ = _originals(small_mock)
    text = "\n".join(_outputs(plain))
    assert REAL_NAME in text
    assert any(lab in text for lab in labs)
    assert any(code in text for code in codes)


@pytest.mark.parametrize("scale", [False, True])
def test_no_original_identifiers_in_anonymized_output(plain, small_mock, scale) -> None:
    labs, codes, descriptions = _originals(small_mock)
    anon = Anonymizer(scale=scale, seed=3).apply(plain)
    for text in _outputs(anon):
        assert REAL_NAME not in text and "Pérez" not in text
        assert "Farmacia Demo" in text
        for lab in labs:
            assert lab not in text, lab
        for code in codes:
            assert not re.search(rf"(?<![\d.,]){code}(?![\d])", text), code
        for desc in descriptions:
            assert desc not in text, desc


def test_labs_consistent_across_report(plain) -> None:
    anon = Anonymizer().apply(plain)
    lab_actions = [a for a in anon["acciones"] + anon["anexo_acciones"] if a["type"] == "revisar_laboratorio"]
    table = {row["laboratorio"] for row in anon["laboratorios"]}
    for action in lab_actions:
        name = action["facts"]["laboratorio"]
        assert re.fullmatch(r"Laboratorio [A-Z]+", name)
        assert name in table
        assert name in action["titulo"]
        assert action["key"] == f"revisar_laboratorio:{name}"
    original = {a["facts"]["laboratorio"] for a in plain["acciones"] + plain["anexo_acciones"]
                if a["type"] == "revisar_laboratorio"}
    assert len({a["facts"]["laboratorio"] for a in lab_actions}) == len(original)


def test_products_become_family_plus_internal_code(plain) -> None:
    anon = Anonymizer().apply(plain)
    for ref in anon["acciones"][0]["references"]:
        assert re.fullmatch(r"REF-\d{4}", ref["codigo_nacional"])
        assert ref["descripcion"].endswith(f"· {ref['codigo_nacional']}")
    assert all(re.fullmatch(r"REF-\d{4}", k) for k in anon["referencias"])


def test_scaling_keeps_proportions(plain) -> None:
    anonymizer = Anonymizer(scale=True, seed=11)
    anon = anonymizer.apply(plain)
    f = anonymizer.factor
    assert 0.7 <= f <= 1.3 and f != 1.0
    assert anon["cifras_escaladas"] is True
    assert "factor" not in json.dumps(anon)
    assert anon["totales"]["valor_stock"] == pytest.approx(plain["totales"]["valor_stock"] * f, abs=0.01)
    for a, b in zip(anon["acciones"], plain["acciones"]):
        assert a["impact_eur"] == pytest.approx(b["impact_eur"] * f, abs=0.01)
    # Porcentajes, ratios, días y recuentos no cambian.
    assert anon["totales"]["margen_bruto_anual_pct"] == plain["totales"]["margen_bruto_anual_pct"]
    assert anon["totales"]["sin_movimiento_critico_refs"] == plain["totales"]["sin_movimiento_critico_refs"]
    assert [l["ratio_compras_ventas"] for l in anon["laboratorios"]] == \
        [l["ratio_compras_ventas"] for l in plain["laboratorios"]]
    # Los textos usan las cifras escaladas.
    first = anon["acciones"][0]
    from engine.formatting import eur0
    assert eur0(first["facts"]["total_eur"]) in first["titulo"] + first["explicacion"]


def test_unscaled_amounts_are_identical(plain) -> None:
    anon = Anonymizer(scale=False).apply(plain)
    assert anon["totales"] == plain["totales"]
    assert anon["cifras_escaladas"] is False


def test_original_results_not_modified(plain) -> None:
    before = json.dumps(plain, sort_keys=True)
    Anonymizer(scale=True, seed=1).apply(plain)
    assert json.dumps(plain, sort_keys=True) == before


def test_same_anonymizer_keeps_reports_comparable(plain, thresholds) -> None:
    later = json.loads(json.dumps(plain))
    later["periodo"]["fecha_referencia"] = "2099-01-01"
    anonymizer = Anonymizer(scale=True, seed=5)
    a, b = anonymizer.apply(plain), anonymizer.apply(later)
    assert a["referencias"].keys() == b["referencias"].keys()
    c = compare(a, b, thresholds.comparison)
    assert c["reduccion_total_eur"] == 0
