from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from engine import challenge as reto
from engine.cli import EXIT_INPUT_ERROR, EXIT_OK, main

TODAY = date(2026, 11, 25)
TYPE_TO_CHAT = {v: k for k, v in reto.CHAT_TYPES.items()}


@pytest.fixture(scope="module")
def challenge(tmp_path_factory, thresholds):
    out = tmp_path_factory.mktemp("reto")
    files = reto.create_challenge(out, thresholds, seed=31, n_refs=400, today=TODAY)
    return out, files, reto.load_expected(out)


def _perfect(expected: dict) -> dict:
    c = expected["cifras"]
    return {
        "chat": "Chat perfecto",
        "cifras": {
            "stock_total_eur": c["stock_total_eur"],
            "sin_movimiento_eur": f"{reto.number(c['sin_movimiento_eur'], 2)} €",  # formato español
            "sin_movimiento_referencias": c["sin_movimiento_referencias"],
            "caducidad_90_eur": str(c["caducidad_90_eur"]),  # formato punto
            "laboratorio_mayor_ratio": c["laboratorio_mayor_ratio"].upper(),
            "laboratorio_mayor_ratio_valor": c["laboratorio_mayor_ratio_valor"],
        },
        "acciones": [
            {"tipo": TYPE_TO_CHAT[a["tipo"]], "laboratorio": a["laboratorio"], "descripcion": a["titulo"],
             "importe_eur": a["importe_eur"]}
            for a in reversed(expected["acciones"])  # el orden no importa
        ],
    }


def test_files_generated(challenge) -> None:
    out, files, expected = challenge
    names = {p.name for p in out.iterdir()}
    assert {"ventas.csv", "stock.csv", "compras.csv", "prompt.md", "respuestas_esperadas.json",
            "plantilla_respuesta_chat.yaml"} <= names
    assert len(expected["acciones"]) == reto.TOP_ACTIONS
    impacts = [a["importe_eur"] for a in expected["acciones"]]
    assert impacts == sorted(impacts, reverse=True)
    prompt = files["prompt"].read_text(encoding="utf-8")
    for token in ("STOCK_TOTAL_EUR", "SIN_MOVIMIENTO_EUR", "SIN_MOVIMIENTO_REFERENCIAS", "CADUCIDAD_90_EUR",
                  "LABORATORIO_MAYOR_RATIO", "ACCION_5", "180 días", "Windows-1252"):
        assert token in prompt
    # El prompt no revela las respuestas.
    assert expected["cifras"]["laboratorio_mayor_ratio"] not in prompt
    assert reto.number(expected["cifras"]["stock_total_eur"], 2) not in prompt


def test_template_is_valid_yaml_and_scores_as_empty(challenge, thresholds) -> None:
    out, files, expected = challenge
    template = yaml.safe_load(files["plantilla"].read_text(encoding="utf-8"))
    assert set(template["cifras"]) == {*reto.FIGURES, reto.LAB_KEY, "laboratorio_mayor_ratio_valor"}
    assert len(template["acciones"]) == reto.TOP_ACTIONS
    score = reto.score_response(expected, template, thresholds.challenge)
    assert score["resumen"]["sin_respuesta"] == 5
    assert score["resumen"]["acciones_detectadas"] == 0


def test_perfect_response(challenge, thresholds) -> None:
    _, _, expected = challenge
    score = reto.score_response(expected, _perfect(expected), thresholds.challenge)
    s = score["resumen"]
    assert s["cifras_correctas"] == s["cifras_total"] == 5
    assert s["acciones_correctas"] == 5
    assert s["error_absoluto_eur"] == 0
    assert all(f["error"] in (0, None) for f in score["cifras"])
    assert score["acciones_extra_chat"] == []


def test_response_with_errors(challenge, thresholds) -> None:
    _, _, expected = challenge
    r = _perfect(expected)
    c = expected["cifras"]
    r["cifras"]["stock_total_eur"] = c["stock_total_eur"] * 1.15          # +15 % -> incorrecta
    r["cifras"]["sin_movimiento_eur"] = c["sin_movimiento_eur"] * 0.95    # -5 % -> aproximada
    r["cifras"]["sin_movimiento_referencias"] = c["sin_movimiento_referencias"] + 1  # pequeño -> correcta/aprox.
    r["cifras"]["laboratorio_mayor_ratio"] = "Laboratorio Inventado"
    r["acciones"][0]["importe_eur"] = r["acciones"][0]["importe_eur"] * 1.30
    r["acciones"][1] = {"tipo": "otra", "laboratorio": None, "descripcion": "Negociar con el mayorista",
                        "importe_eur": 5000}
    score = reto.score_response(expected, r, thresholds.challenge)
    figures = {f["clave"]: f for f in score["cifras"]}
    assert figures["stock_total_eur"]["estado"] == "incorrecta"
    assert figures["stock_total_eur"]["error_pct"] == pytest.approx(15.0, abs=0.1)
    assert figures["stock_total_eur"]["error"] == pytest.approx(c["stock_total_eur"] * 0.15, abs=0.02)
    assert figures["sin_movimiento_eur"]["estado"] == "aproximada"
    assert figures["sin_movimiento_eur"]["error_pct"] == pytest.approx(-5.0, abs=0.1)
    assert figures["laboratorio_mayor_ratio"]["estado"] == "incorrecta"
    assert figures["caducidad_90_eur"]["estado"] == "correcta"
    states = [a["estado"] for a in score["acciones"]]
    assert states.count("incorrecta") == 1 and states.count("no_detectada") == 1
    assert score["acciones_extra_chat"][0]["descripcion"] == "Negociar con el mayorista"
    assert score["resumen"]["error_absoluto_eur"] > 0


def test_incomplete_response(challenge, thresholds) -> None:
    _, _, expected = challenge
    r = _perfect(expected)
    r["cifras"]["caducidad_90_eur"] = None
    r["cifras"]["laboratorio_mayor_ratio"] = ""
    del r["cifras"]["sin_movimiento_referencias"]
    r["acciones"] = r["acciones"][:2]
    r["acciones"][0]["importe_eur"] = None
    score = reto.score_response(expected, r, thresholds.challenge)
    figures = {f["clave"]: f["estado"] for f in score["cifras"]}
    assert figures["caducidad_90_eur"] == "sin_respuesta"
    assert figures["sin_movimiento_referencias"] == "sin_respuesta"
    assert figures["laboratorio_mayor_ratio"] == "sin_respuesta"
    assert figures["stock_total_eur"] == "correcta"
    assert score["resumen"]["acciones_detectadas"] == 2
    assert score["resumen"]["acciones_correctas"] == 1  # la otra no tiene importe
    assert [a["estado"] for a in score["acciones"]].count("no_detectada") == 3


def test_lab_actions_require_same_lab(challenge, thresholds) -> None:
    _, _, expected = challenge
    lab_actions = [a for a in expected["acciones"] if a["tipo"] == "revisar_laboratorio"]
    if not lab_actions:
        pytest.skip("Este reto no tiene acciones de laboratorio en el top 5")
    r = _perfect(expected)
    for a in r["acciones"]:
        if a["tipo"] == "revisar_laboratorio":
            a["laboratorio"] = "Otro Lab"
    score = reto.score_response(expected, r, thresholds.challenge)
    assert all(a["estado"] == "no_detectada" for a in score["acciones"] if a["tipo"] == "revisar_laboratorio")


@pytest.mark.parametrize(("raw", "value"), [("12.345,67 €", 12345.67), ("12345.67", 12345.67), (1234, 1234.0),
                                            ("1.234", 1234.0), ("", None), (None, None), ("n/d", None)])
def test_to_number(raw, value) -> None:
    assert reto.to_number(raw) == value


def test_html_report(challenge, thresholds) -> None:
    out, _, expected = challenge
    r = _perfect(expected)
    r["cifras"]["stock_total_eur"] = 1
    score = reto.score_response(expected, r, thresholds.challenge)
    paths = reto.write_score(score, out, "respuesta_test")
    html = paths["html"].read_text(encoding="utf-8")
    assert "Chat genérico vs PharmaOS" in html
    assert "Incorrecta" in html and "Correcta" in html
    assert "@page" in html  # mismo estilo imprimible que el informe semanal
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["resumen"]["cifras_correctas"] == 4


def test_prompt_definitions_reproduce_expected_answers(challenge, thresholds) -> None:
    """Calcula las cifras siguiendo literalmente el prompt, sin el motor: el reto es justo."""
    out, _, expected = challenge
    t = thresholds
    read = dict(sep=";", decimal=",", encoding="cp1252", dtype={"Código": str})
    sales = pd.read_csv(out / "ventas.csv", **read)
    stock = pd.read_csv(out / "stock.csv", **read)
    buys = pd.read_csv(out / "compras.csv", **read)
    sales["Fecha"] = pd.to_datetime(sales["Fecha"], format="%d/%m/%Y")
    buys["Fecha Albarán"] = pd.to_datetime(buys["Fecha Albarán"], format="%d/%m/%Y")
    stock["Caducidad"] = pd.to_datetime(stock["Caducidad"], format="%d/%m/%Y")
    ref = sales["Fecha"].max()
    stock["valor"] = stock["Stock Actual"].clip(lower=0) * stock["P.Coste"]

    last = sales[sales["Unidades"] > 0].groupby("Código")["Fecha"].max()
    days_since = (ref - stock["Código"].map(last)).dt.days
    dead = (stock["Stock Actual"] > 0) & (days_since.isna() | (days_since >= t.no_movement_critical_days))

    short = sales[sales["Fecha"] > ref - pd.Timedelta(days=t.short_window_days)]
    daily = stock["Código"].map(short.groupby("Código")["Unidades"].sum()).fillna(0).clip(lower=0) / t.short_window_days
    days_left = (stock["Caducidad"] - ref).dt.days
    at_risk = (stock["Stock Actual"].clip(lower=0) - daily * days_left.clip(lower=0)).clip(lower=0)
    expiry = (at_risk * stock["P.Coste"]).where(days_left <= max(t.expiry_windows_days), 0).sum()

    start = ref - pd.DateOffset(months=t.lab_window_months)
    s6, b6 = sales[sales["Fecha"] > start], buys[buys["Fecha Albarán"] > start]
    sold_cost = (s6["Unidades"] * s6["P.Coste"]).groupby(s6["Laboratorio"]).sum()
    bought = b6.groupby("Laboratorio")["Importe Coste"].sum()
    ratio = (bought / sold_cost)[(bought >= t.lab_min_purchases_eur) & (sold_cost > 0)].dropna()

    c = expected["cifras"]
    assert stock["valor"].sum() == pytest.approx(c["stock_total_eur"], abs=0.05)
    assert stock.loc[dead, "valor"].sum() == pytest.approx(c["sin_movimiento_eur"], abs=0.05)
    assert int(dead.sum()) == c["sin_movimiento_referencias"]
    assert expiry == pytest.approx(c["caducidad_90_eur"], abs=0.05)
    assert ratio.idxmax() == c["laboratorio_mayor_ratio"]
    assert np.round(ratio.max(), 2) == pytest.approx(c["laboratorio_mayor_ratio_valor"])


def test_cli_commands(tmp_path: Path, capsys) -> None:
    out = tmp_path / "reto_01"
    assert main(["reto-chat", "--salida", str(out), "--referencias", "300", "--semilla", "5"]) == EXIT_OK
    expected = reto.load_expected(out)
    answer = out / "respuesta_chatgpt.yaml"
    answer.write_text(yaml.safe_dump(_perfect(expected), allow_unicode=True), encoding="utf-8")
    capsys.readouterr()
    assert main(["puntuar-reto", "--reto", str(out), "--respuesta", str(answer)]) == EXIT_OK
    assert "Cifras correctas: 5/5" in capsys.readouterr().out
    assert (out / "puntuacion_respuesta_chatgpt.html").exists()
    bad = out / "mal.yaml"
    bad.write_text("solo: texto", encoding="utf-8")
    assert main(["puntuar-reto", "--reto", str(out), "--respuesta", str(bad)]) == EXIT_INPUT_ERROR
    assert main(["puntuar-reto", "--reto", str(tmp_path), "--respuesta", str(answer)]) == EXIT_INPUT_ERROR


def test_expected_answers_are_deterministic(tmp_path: Path, thresholds) -> None:
    reto.create_challenge(tmp_path / "a", thresholds, seed=8, n_refs=200, today=TODAY)
    reto.create_challenge(tmp_path / "b", thresholds, seed=8, n_refs=200, today=TODAY)
    a = reto.load_expected(tmp_path / "a")
    b = copy.deepcopy(reto.load_expected(tmp_path / "b"))
    assert a == b
