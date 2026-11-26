from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from engine import api

SCHEMA = json.loads((Path(__file__).resolve().parent.parent / "docs" / "report-schema.json").read_text("utf-8"))


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("PHARMAOS_DATA_DIR", str(tmp_path / "datos"))
    return TestClient(api.app)


def _files(paths: dict[str, Path]) -> dict:
    return {name: (p.name, p.read_bytes(), "text/csv") for name, p in paths.items()}


def test_health_and_programs(client) -> None:
    r = client.get("/salud")
    assert r.status_code == 200 and r.json()["estado"] == "ok" and r.json()["informe"] is False
    assert {"farmatic", "nixfarma"} <= set(client.get("/programas").json())


def test_analyze_stores_report(client, small_mock_paths, tmp_path) -> None:
    r = client.post("/analizar", files=_files(small_mock_paths), data={"programa": "farmatic", "farmacia": "Farmacia Prueba"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["farmacia"]["nombre"] == "Farmacia Prueba" and body["farmacia"]["ficticia"] is False
    assert body["resumen"]["acciones_total"] > 0
    assert body["calidad"]["nivel"] in {"buena", "aceptable", "baja"}
    full = client.get("/informe").json()
    core = client.get("/informe?nucleo=true").json()
    jsonschema.validate(full, SCHEMA)
    jsonschema.validate(core, SCHEMA)
    assert core["acciones"] == full["acciones"] and len(core["productos"]) <= len(full["acciones"])
    assert client.get("/salud").json()["informe"] is True
    # Ningún fichero subido queda en disco: solo el informe.
    assert sorted(p.name for p in (tmp_path / "datos").iterdir()) == ["report-core.json", "report.json"]


def test_privacy_rejection_has_no_values(client, small_mock, tmp_path) -> None:
    stock = small_mock.stock.copy()
    stock["DNI"] = "12345678Z"
    folder = tmp_path / "pac"
    paths = small_mock.write(folder)
    stock.to_csv(paths["stock"], sep=";", index=False, encoding="cp1252")
    r = client.post("/analizar", files=_files(paths))
    assert r.status_code == 422
    body = r.json()
    assert body["tipo"] == "privacidad" and body["hallazgos"][0]["columna"] == "DNI"
    assert "12345678Z" not in r.text
    assert client.get("/salud").json()["informe"] is False


def test_bad_inputs(client, small_mock_paths, tmp_path) -> None:
    r = client.post("/analizar", files=_files(small_mock_paths), data={"programa": "inexistente"})
    assert r.status_code == 400 and r.json()["tipo"] == "configuracion"
    bad = dict(_files(small_mock_paths))
    bad["compras"] = ("compras.pdf", b"%PDF", "application/pdf")
    r = client.post("/analizar", files=bad)
    assert r.status_code == 400 and r.json()["tipo"] == "fichero"
    swapped = dict(_files(small_mock_paths))
    swapped["stock"] = swapped["ventas"]
    r = client.post("/analizar", files=swapped)
    assert r.status_code == 400 and r.json()["tipo"] == "datos" and "stock" in r.json()["mensaje"]


def test_report_missing_and_delete(client, small_mock_paths) -> None:
    assert client.get("/informe").status_code == 404
    client.post("/analizar", files=_files(small_mock_paths))
    assert client.delete("/informe").json() == {"borrado": True}
    assert client.get("/informe").status_code == 404


def test_cors_allows_local_web(client) -> None:
    r = client.options("/analizar", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    r = client.options("/analizar", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
