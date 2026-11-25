"""El mock versionado de la web (web/public/mock/report.json) cumple el contrato y es coherente."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
MOCK = ROOT.parent / "web" / "public" / "mock" / "report.json"
SCHEMA = json.loads((ROOT / "docs" / "report-schema.json").read_text("utf-8"))

pytestmark = pytest.mark.skipif(not MOCK.exists(), reason="web/public/mock/report.json no generado")


@pytest.fixture(scope="module")
def mock() -> dict:
    return json.loads(MOCK.read_text(encoding="utf-8"))


def test_mock_validates(mock) -> None:
    jsonschema.validate(mock, SCHEMA, format_checker=jsonschema.FormatChecker())


def test_mock_is_realistic(mock) -> None:
    s = mock["resumen"]
    assert mock["farmacia"]["ficticia"] is True
    assert 7500 <= len(mock["productos"]) <= 8500
    assert 35 <= s["acciones_total"] <= 45
    assert 2000 <= s["recuperable_semana_eur"] <= 6000
    assert 30000 <= s["capital_inmovilizado_eur"] <= 50000
    assert len(mock["historico_semanas"]) == 6
    assert all(n > 0 for n in s["acciones_por_tipo"].values())


def test_mock_catalog_variety(mock) -> None:
    names = [p["nombre"] or "" for p in mock["productos"].values()]
    families = {p["familia"] for p in mock["productos"].values()}
    assert {"Solares", "Dermocosmética", "Medicamento con receta", "OTC"} <= families
    assert any("EFG" in n for n in names)
    assert any("ntigripal" in n for n in names)
