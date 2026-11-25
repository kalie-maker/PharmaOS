"""Reto "chat genérico vs PharmaOS".

`create_challenge` genera una farmacia ficticia, el prompt exacto para pegar en un chat
genérico, las respuestas correctas (calculadas por el motor) y un formulario YAML para
copiar a mano lo que conteste el chat.

`score_response` compara cifra a cifra y `render_score_html` produce una página
"Chat genérico vs PharmaOS" con el estilo del informe semanal.

No se llama a ninguna API: la prueba con el chat la hace una persona.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from engine.config import ChallengeLimits, Thresholds, load_mapping, normalize_label
from engine.formatting import eur, number, spanish_date
from engine.ingest import parse_number
from engine.mock.generate import FARMATIC_FAMILY_LABELS, MockConfig, generate
from engine.pipeline import run_analysis
from engine.report import _env
from engine.sniff import detect_decimal

TOP_ACTIONS = 5
CHAT_TYPES = {
    "devolver": "devolver_sin_movimiento",
    "reducir_pedido": "reducir_pedido",
    "promocionar_caducidad": "promocionar_caducidad",
    "reponer": "reponer_rotura",
    "revisar_laboratorio": "revisar_laboratorio",
}
TYPE_LABELS = {
    "devolver_sin_movimiento": "Devolver o liquidar stock sin movimiento",
    "reducir_pedido": "Reducir el próximo pedido (sobrestock)",
    "promocionar_caducidad": "Promocionar antes de caducar",
    "reponer_rotura": "Reponer referencias con riesgo de rotura",
    "revisar_laboratorio": "Revisar compras a un laboratorio",
}
# Cifras numéricas: clave -> (nombre, es dinero)
FIGURES: dict[str, tuple[str, bool]] = {
    "stock_total_eur": ("Stock total a coste", True),
    "sin_movimiento_eur": ("Stock sin movimiento (180 días)", True),
    "sin_movimiento_referencias": ("Referencias sin movimiento", False),
    "caducidad_90_eur": ("Riesgo de caducidad (90 días)", True),
}
LAB_KEY = "laboratorio_mayor_ratio"
STATE_LABELS = {"correcta": "Correcta", "aproximada": "Aproximada", "incorrecta": "Incorrecta",
                "sin_respuesta": "Sin respuesta", "no_detectada": "No detectada"}
STATE_CLASS = {"correcta": "ok", "aproximada": "warn", "incorrecta": "bad", "sin_respuesta": "bad",
               "no_detectada": "bad"}


class ChallengeError(ValueError):
    """Reto o respuesta inválidos."""


# ---------------------------------------------------------------------------
# Generación del reto
# ---------------------------------------------------------------------------


def _top_lab(labs: pd.DataFrame, t: Thresholds) -> tuple[str, float]:
    eligible = labs[(labs["compras_coste"] >= t.lab_min_purchases_eur) & (labs["coste_ventas"] > 0)]
    if eligible.empty:
        raise ChallengeError("Ningún laboratorio cumple las condiciones para el ratio compras/ventas")
    name = str(eligible["ratio_compras_ventas"].idxmax())
    return name, round(float(eligible.loc[name, "ratio_compras_ventas"]), 2)


def expected_answers(analysis: Any, t: Thresholds, seed: int) -> dict[str, Any]:
    r = analysis.results
    lab, ratio = _top_lab(analysis.metrics.labs, t)
    actions = []
    for i, a in enumerate(r["acciones"][:TOP_ACTIONS], start=1):
        actions.append({
            "posicion": i,
            "tipo": a["type"],
            "laboratorio": a["facts"].get("laboratorio"),
            "titulo": a["titulo"],
            "importe_eur": a["impact_eur"],
        })
    return {
        "reto": "chat genérico vs PharmaOS",
        "semilla": seed,
        "fecha_referencia": r["periodo"]["fecha_referencia"],
        "cifras": {
            "stock_total_eur": r["cifras_clave"]["valor_stock_eur"],
            "sin_movimiento_eur": r["cifras_clave"]["sin_movimiento_eur"],
            "sin_movimiento_referencias": r["cifras_clave"]["sin_movimiento_refs"],
            "caducidad_90_eur": r["cifras_clave"]["riesgo_caducidad_eur"],
            LAB_KEY: lab,
            "laboratorio_mayor_ratio_valor": ratio,
        },
        "acciones": actions,
    }


def build_prompt(t: Thresholds) -> str:
    coverage = "\n".join(
        f"   - {label}: {t.coverage_for(fam.value)} días" for fam, label in FARMATIC_FAMILY_LABELS.items()
    )
    horizon = number(t.replenishment_days + t.safety_days)
    return f"""Eres un analista experto en gestión de stock de farmacias. Te adjunto tres ficheros CSV
exportados del programa de gestión de una farmacia española:

- ventas.csv: una línea por día y producto (últimos 12 meses). Columnas: Fecha, Código, Descripción,
  Laboratorio, Familia, Unidades, Importe s/IVA, P.Coste (coste unitario).
- stock.csv: una línea por producto, foto de hoy. Columnas: Código, Descripción, Laboratorio, Familia,
  Stock Actual, P.Coste, PVP, Caducidad.
- compras.csv: una línea por albarán y producto (últimos 6 meses). Columnas: Fecha Albarán, Código,
  Laboratorio, Unidades Recibidas, Importe Coste.

Formato: separador punto y coma, coma decimal, fechas dd/mm/aaaa, codificación Windows-1252.

Calcula EXACTAMENTE estas cifras con estas definiciones:

Fecha de referencia = la última fecha que aparece en ventas.csv.

1. Stock total a coste: suma de (Stock Actual × P.Coste) en stock.csv; el stock negativo cuenta como 0.

2. € sin movimiento a {t.no_movement_critical_days} días: valor a coste del stock (Stock Actual > 0) de las
   referencias cuya última venta fue hace {t.no_movement_critical_days} días o más respecto a la fecha de
   referencia, o que no se han vendido nunca en ventas.csv.

3. Nº de referencias sin movimiento: cuántas referencias cumplen la condición del punto 2.

4. € en riesgo de caducidad a {max(t.expiry_windows_days)} días: para cada referencia con Caducidad a
   {max(t.expiry_windows_days)} días o menos de la fecha de referencia (incluidas las ya caducadas):
   consumo diario = unidades vendidas en los últimos {t.short_window_days} días / {t.short_window_days};
   unidades en riesgo = máx(0, Stock Actual − consumo diario × días hasta caducar);
   riesgo = unidades en riesgo × P.Coste. Suma de todas las referencias.

5. Laboratorio con mayor ratio compras/ventas en los últimos {t.lab_window_months} meses:
   ratio = (suma de Importe Coste en compras) / (suma de Unidades × P.Coste en ventas), ambos en los
   últimos {t.lab_window_months} meses hasta la fecha de referencia. Solo laboratorios con compras de al
   menos {number(t.lab_min_purchases_eur)} € y con ventas. Indica el nombre y el ratio.

6. Las {TOP_ACTIONS} acciones más rentables, ordenadas por importe, elegidas entre estos tipos:
   a) devolver: devolver o liquidar el stock sin movimiento del punto 2 (importe = su valor a coste).
   b) reducir_pedido: sobrestock a coste, excluyendo las referencias del punto 2. Por referencia:
      unidades objetivo = redondeo hacia arriba de (consumo diario de {t.short_window_days} días × días
      objetivo de su familia); exceso = máx(0, Stock Actual − unidades objetivo); importe = exceso × P.Coste.
      Días objetivo por familia:
{coverage}
   c) promocionar_caducidad: el riesgo del punto 4, excluyendo las referencias del punto 2.
   d) reponer: referencias con venta en al menos {t.frequent_min_sale_days} días distintos de los últimos
      {t.short_window_days} y Stock Actual < consumo diario × {horizon}; importe = (consumo diario × {horizon}
      − Stock Actual) × precio medio de venta sin IVA de los últimos {t.short_window_days} días.
   e) revisar_laboratorio: una acción por cada laboratorio con ratio del punto 5 mayor que
      {number(t.lab_high_ratio, 2)} y compras de al menos {number(t.lab_min_purchases_eur)} €;
      importe = compras − coste de ventas de los últimos {t.lab_window_months} meses.

Responde SOLO con este formato, sin explicaciones adicionales:

STOCK_TOTAL_EUR: <número>
SIN_MOVIMIENTO_EUR: <número>
SIN_MOVIMIENTO_REFERENCIAS: <número>
CADUCIDAD_90_EUR: <número>
LABORATORIO_MAYOR_RATIO: <nombre> (<ratio>)
ACCION_1: <tipo> | <laboratorio si aplica> | <importe en €>
ACCION_2: <tipo> | <laboratorio si aplica> | <importe en €>
ACCION_3: <tipo> | <laboratorio si aplica> | <importe en €>
ACCION_4: <tipo> | <laboratorio si aplica> | <importe en €>
ACCION_5: <tipo> | <laboratorio si aplica> | <importe en €>
"""


TEMPLATE = """# Respuesta del chat genérico al reto. Copia aquí, a mano, lo que conteste el chat.
# Deja `null` lo que no conteste. Los importes valen como 12345.67 o "12.345,67 €".
chat: ""          # p. ej. "ChatGPT-5 (web)" o "Claude (web)"
fecha: ""         # fecha de la prueba
intentos: 1       # nº de veces que hubo que repetir la pregunta

cifras:
  stock_total_eur: null
  sin_movimiento_eur: null
  sin_movimiento_referencias: null
  caducidad_90_eur: null
  laboratorio_mayor_ratio: null        # nombre del laboratorio
  laboratorio_mayor_ratio_valor: null  # ratio (opcional)

# tipo: devolver | reducir_pedido | promocionar_caducidad | reponer | revisar_laboratorio | otra
acciones:
{actions}
notas: ""         # errores de lectura, cifras inventadas, etc.
"""


def response_template() -> str:
    block = "\n".join(
        "  - tipo: null\n    laboratorio: null\n    descripcion: \"\"\n    importe_eur: null"
        for _ in range(TOP_ACTIONS)
    )
    return TEMPLATE.format(actions=block)


def create_challenge(out_dir: Path | str, t: Thresholds, seed: int | None = None,
                     n_refs: int | None = None, today: date | None = None) -> dict[str, Path]:
    out = Path(out_dir)
    seed = t.challenge.seed if seed is None else seed
    config = MockConfig(seed=seed) if n_refs is None else MockConfig(seed=seed, n_refs=n_refs)
    paths = generate(config).write(out)
    analysis = run_analysis(paths, load_mapping("farmatic"), t, "Farmacia Reto", today=today)
    expected = expected_answers(analysis, t, seed)

    files = {
        "prompt": out / "prompt.md",
        "esperadas": out / "respuestas_esperadas.json",
        "plantilla": out / "plantilla_respuesta_chat.yaml",
    }
    files["prompt"].write_text(build_prompt(t), encoding="utf-8")
    files["esperadas"].write_text(json.dumps(expected, ensure_ascii=False, indent=1), encoding="utf-8")
    files["plantilla"].write_text(response_template(), encoding="utf-8")
    return {**paths, **files}


# ---------------------------------------------------------------------------
# Puntuación
# ---------------------------------------------------------------------------


def to_number(value: object) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    decimal, thousands = detect_decimal([text], default=(",", "."))
    number_value = parse_number(text, decimal, thousands)
    return None if number_value != number_value else number_value  # NaN -> None


@dataclass
class FigureScore:
    clave: str
    nombre: str
    dinero: bool
    esperado: Any
    chat: Any
    error: float | None
    error_pct: float | None
    estado: str


def _state(error_pct: float | None, answered: bool, limits: ChallengeLimits) -> str:
    if not answered:
        return "sin_respuesta"
    if error_pct is None:
        return "incorrecta"
    if abs(error_pct) <= limits.correct_pct:
        return "correcta"
    if abs(error_pct) <= limits.approx_pct:
        return "aproximada"
    return "incorrecta"


def _compare_number(expected: float, chat: float | None, limits: ChallengeLimits) -> tuple[float | None, float | None, str]:
    if chat is None:
        return None, None, "sin_respuesta"
    error = round(chat - expected, 2)
    pct = round(error / expected * 100, 1) if expected else (0.0 if error == 0 else None)
    return error, pct, _state(pct, True, limits)


def _same_lab(a: object, b: object) -> bool:
    if not a or not b:
        return False
    na, nb = normalize_label(a), normalize_label(b)
    return na == nb or (len(min(na, nb, key=len)) >= 4 and (na in nb or nb in na))


def load_response(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ChallengeError(f"No existe la respuesta: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ChallengeError(f"{path.name} no es un YAML válido: {exc}") from exc
    if not isinstance(data, dict) or "cifras" not in data:
        raise ChallengeError(f"{path.name} no sigue la plantilla (falta la sección 'cifras')")
    return data


def load_expected(challenge_dir: Path | str) -> dict[str, Any]:
    path = Path(challenge_dir) / "respuestas_esperadas.json"
    if not path.exists():
        raise ChallengeError(f"No existe {path}. Genera el reto con `reto-chat`.")
    return json.loads(path.read_text(encoding="utf-8"))


def score_response(expected: dict[str, Any], response: dict[str, Any], limits: ChallengeLimits) -> dict[str, Any]:
    exp, got = expected["cifras"], response.get("cifras") or {}

    figures: list[FigureScore] = []
    for key, (name, money) in FIGURES.items():
        chat = to_number(got.get(key))
        error, pct, state = _compare_number(float(exp[key]), chat, limits)
        figures.append(FigureScore(key, name, money, exp[key], chat, error, pct, state))

    chat_lab = got.get(LAB_KEY)
    lab_state = "sin_respuesta" if not chat_lab else ("correcta" if _same_lab(chat_lab, exp[LAB_KEY]) else "incorrecta")
    chat_ratio = to_number(got.get("laboratorio_mayor_ratio_valor"))
    figures.append(FigureScore(LAB_KEY, "Laboratorio con mayor ratio compras/ventas", False,
                               f"{exp[LAB_KEY]} ({number(exp['laboratorio_mayor_ratio_valor'], 2)})",
                               None if not chat_lab else (f"{chat_lab}" + (f" ({number(chat_ratio, 2)})"
                                                                           if chat_ratio is not None else "")),
                               None, None, lab_state))

    chat_actions = [a for a in (response.get("acciones") or []) if isinstance(a, dict) and a.get("tipo")]
    used: set[int] = set()
    actions = []
    for e in expected["acciones"]:
        match_index = None
        for i, a in enumerate(chat_actions):
            if i in used or CHAT_TYPES.get(str(a.get("tipo")).strip()) != e["tipo"]:
                continue
            if e["tipo"] == "revisar_laboratorio" and not _same_lab(a.get("laboratorio"), e["laboratorio"]):
                continue
            match_index = i
            break
        if match_index is None:
            actions.append({**e, "chat_importe": None, "error": None, "error_pct": None,
                            "estado": "no_detectada"})
            continue
        used.add(match_index)
        chat_amount = to_number(chat_actions[match_index].get("importe_eur"))
        error, pct, state = _compare_number(float(e["importe_eur"]), chat_amount, limits)
        actions.append({**e, "chat_importe": chat_amount, "error": error, "error_pct": pct, "estado": state})

    extra = [{"tipo": a.get("tipo"), "laboratorio": a.get("laboratorio"), "descripcion": a.get("descripcion"),
              "importe_eur": to_number(a.get("importe_eur"))}
             for i, a in enumerate(chat_actions) if i not in used]

    money_errors = [abs(f.error) for f in figures if f.dinero and f.error is not None]
    correct_figures = sum(1 for f in figures if f.estado == "correcta")
    correct_actions = sum(1 for a in actions if a["estado"] == "correcta")
    detected_actions = sum(1 for a in actions if a["estado"] != "no_detectada")
    return {
        "chat": response.get("chat") or "Chat genérico",
        "fecha_prueba": response.get("fecha") or "",
        "intentos": response.get("intentos"),
        "notas": response.get("notas") or "",
        "fecha_referencia": expected["fecha_referencia"],
        "tolerancias": {"correcta_pct": limits.correct_pct, "aproximada_pct": limits.approx_pct},
        "cifras": [f.__dict__ for f in figures],
        "acciones": actions,
        "acciones_extra_chat": extra,
        "resumen": {
            "cifras_correctas": correct_figures,
            "cifras_total": len(figures),
            "acciones_correctas": correct_actions,
            "acciones_detectadas": detected_actions,
            "acciones_total": len(actions),
            "error_absoluto_eur": round(sum(money_errors), 2),
            "sin_respuesta": sum(1 for f in figures if f.estado == "sin_respuesta"),
        },
    }


def render_score_html(score: dict[str, Any]) -> str:
    env = _env()
    env.filters["estado"] = lambda s: STATE_LABELS.get(s, s)
    env.filters["clase"] = lambda s: STATE_CLASS.get(s, "")
    env.filters["tipo"] = lambda s: TYPE_LABELS.get(s, s or "—")
    return env.get_template("challenge.html.j2").render(s=score)


def write_score(score: dict[str, Any], challenge_dir: Path | str, stem: str) -> dict[str, Path]:
    out = Path(challenge_dir)
    paths = {"html": out / f"puntuacion_{stem}.html", "json": out / f"puntuacion_{stem}.json"}
    paths["html"].write_text(render_score_html(score), encoding="utf-8")
    paths["json"].write_text(json.dumps(score, ensure_ascii=False, indent=1), encoding="utf-8")
    return paths


def summary_lines(score: dict[str, Any]) -> list[str]:
    s = score["resumen"]
    lines = [f"{score['chat']} vs PharmaOS (datos hasta {spanish_date(score['fecha_referencia'])})",
             f"Cifras correctas: {s['cifras_correctas']}/{s['cifras_total']} · "
             f"Acciones correctas: {s['acciones_correctas']}/{s['acciones_total']} "
             f"(detectadas {s['acciones_detectadas']}) · Error en cifras: {eur(s['error_absoluto_eur'])}"]
    for f in score["cifras"]:
        detail = ""
        if f["error"] is not None:
            detail = f"  error {eur(f['error']) if f['dinero'] else number(f['error'])} ({number(f['error_pct'], 1)} %)"
        lines.append(f"  [{STATE_LABELS[f['estado']]:<13}] {f['nombre']}{detail}")
    for a in score["acciones"]:
        lines.append(f"  [{STATE_LABELS[a['estado']]:<13}] {a['posicion']}. {a['titulo']}")
    return lines
