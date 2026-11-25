"""Comparación entre dos informes JSON (antes / después): prueba de valor.

Mide cuántos € de stock sin movimiento, sobrestock y caducidad se han reducido
y estima qué acciones parecen ejecutadas siguiendo las referencias afectadas.
Una reducción también puede deberse a ventas normales: "parece ejecutada" es
una estimación, no una confirmación.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from engine.config import ComparisonLimits
from engine.formatting import eur, eur0, number, pct, spanish_date
from engine.report import SCHEMA_VERSION

INDICATORS = (
    ("sin_movimiento_critico_eur", "Stock sin movimiento"),
    ("sobrestock_eur", "Sobrestock"),
    ("riesgo_caducidad_eur", "Riesgo de caducidad"),
    ("ventas_perdidas_eur", "Ventas en riesgo por rotura"),
    ("valor_stock", "Stock total a coste"),
)
# Campo del snapshot por referencia que mide el problema de cada tipo de acción.
ACTION_FIELD = {
    "devolver_sin_movimiento": "valor_stock",
    "reducir_pedido": "sobrestock_eur",
    "promocionar_caducidad": "riesgo_caducidad_eur",
    "reponer_rotura": "ventas_perdidas_eur",
    "revisar_laboratorio": "sobrestock_eur",
}
STATUS_LABELS = {"ejecutada": "Parece ejecutada", "parcial": "Parcial", "pendiente": "Sin avance",
                 "sin_datos": "Sin datos"}


class CompareError(ValueError):
    """Los informes no se pueden comparar."""


@dataclass
class IndicatorChange:
    id: str
    nombre: str
    antes: float
    despues: float
    reduccion: float
    reduccion_pct: float | None


@dataclass
class ActionProgress:
    key: str
    titulo: str
    tipo: str
    antes_eur: float
    despues_eur: float
    reducido_eur: float
    avance: float | None
    estado: str
    referencias: int


def load_results(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise CompareError(f"No existe el fichero: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CompareError(f"{path.name} no es un JSON válido: {exc}") from exc
    if data.get("version_esquema") != SCHEMA_VERSION or "referencias" not in data:
        raise CompareError(f"{path.name} no es un resultado de Stock Profit OS compatible "
                           f"(versión de esquema {SCHEMA_VERSION})")
    return data


def _status(progress: float | None, limits: ComparisonLimits) -> str:
    if progress is None:
        return "sin_datos"
    if progress >= limits.done_threshold:
        return "ejecutada"
    if progress >= limits.partial_threshold:
        return "parcial"
    return "pendiente"


def _action_value(action: dict[str, Any], snapshot: dict[str, dict[str, Any]], field: str) -> float:
    """Suma del problema en las referencias afectadas. Ausente del snapshot = sin stock ni alerta = 0."""
    total = sum(float((snapshot.get(code) or {}).get(field) or 0.0) for code in action["affected_codes"])
    return round(total, 2)


def compare(before: dict[str, Any], after: dict[str, Any], limits: ComparisonLimits) -> dict[str, Any]:
    d0 = date.fromisoformat(before["periodo"]["fecha_referencia"])
    d1 = date.fromisoformat(after["periodo"]["fecha_referencia"])
    if d1 <= d0:
        raise CompareError(
            f"El informe 'después' ({spanish_date(d1)}) debe ser posterior al de 'antes' ({spanish_date(d0)})"
        )
    warnings: list[str] = []
    if not before.get("anonimizado") and not after.get("anonimizado") and before["farmacia"] != after["farmacia"]:
        warnings.append(f"Los informes son de farmacias distintas: '{before['farmacia']}' y '{after['farmacia']}'.")
    for label, data in (("antes", before), ("después", after)):
        quality = data.get("calidad") or {}
        if quality.get("nivel") == "baja":
            warnings.append(f"La calidad de datos del informe '{label}' es baja: compara con cautela.")

    indicators = []
    for key, name in INDICATORS:
        a = float(before["totales"].get(key) or 0.0)
        b = float(after["totales"].get(key) or 0.0)
        indicators.append(IndicatorChange(key, name, round(a, 2), round(b, 2), round(a - b, 2),
                                          round((a - b) / a * 100, 1) if a > 0 else None))

    progress = []
    for action in [*before["acciones"], *before["anexo_acciones"]]:
        field = ACTION_FIELD.get(action["type"])
        if field is None:
            continue
        a = _action_value(action, before["referencias"], field)
        b = _action_value(action, after["referencias"], field)
        adv = round(max(0.0, min(1.0, (a - b) / a)), 3) if a > 0 else None
        progress.append(ActionProgress(action["key"], action["titulo"], action["type"], a, b,
                                       round(max(0.0, a - b), 2), adv, _status(adv, limits),
                                       len(action["affected_codes"])))

    recovered = sum(i.reduccion for i in indicators if i.id in
                    {"sin_movimiento_critico_eur", "sobrestock_eur", "riesgo_caducidad_eur"} and i.reduccion > 0)
    stock_freed = max(0.0, float(before["totales"]["valor_stock"]) - float(after["totales"]["valor_stock"]))
    return {
        "farmacia": after["farmacia"],
        "stock_liberado_eur": round(stock_freed, 2),
        "antes": before["periodo"]["fecha_referencia"],
        "despues": after["periodo"]["fecha_referencia"],
        "dias": (d1 - d0).days,
        "indicadores": [asdict(i) for i in indicators],
        "acciones": [asdict(p) for p in progress],
        "acciones_ejecutadas": sum(1 for p in progress if p.estado == "ejecutada"),
        "acciones_parciales": sum(1 for p in progress if p.estado == "parcial"),
        "reduccion_total_eur": round(recovered, 2),
        "avisos": warnings,
        "nota": "Una reducción también puede deberse a ventas normales; 'parece ejecutada' es una estimación.",
    }


def headline(c: dict[str, Any]) -> str:
    return (f"En {c['dias']} días has liberado {eur0(c['stock_liberado_eur'])} de stock a coste. "
            f"El stock problemático (sin movimiento, sobrestock y caducidad) ha bajado "
            f"{eur0(c['reduccion_total_eur'])}.")


def render_text(c: dict[str, Any]) -> str:
    lines = [
        f"{c['farmacia']}: del {spanish_date(c['antes'])} al {spanish_date(c['despues'])} ({c['dias']} días)",
        "",
        headline(c),
        "",
        f"{'Indicador':<30}{'Antes':>15}{'Después':>15}{'Reducción':>15}{'%':>9}",
    ]
    for i in c["indicadores"]:
        lines.append(f"{i['nombre']:<30}{eur(i['antes']):>15}{eur(i['despues']):>15}"
                     f"{eur(i['reduccion']):>15}{pct(i['reduccion_pct']):>9}")
    lines += ["", f"Acciones: {c['acciones_ejecutadas']} parecen ejecutadas, {c['acciones_parciales']} parciales "
                  f"de {len(c['acciones'])}."]
    for a in c["acciones"]:
        adv = "—" if a["avance"] is None else f"{number(a['avance'] * 100)} %"
        lines.append(f"  [{STATUS_LABELS[a['estado']]:<16}] {adv:>6}  {a['titulo']} "
                     f"({eur0(a['antes_eur'])} -> {eur0(a['despues_eur'])})")
    for w in c["avisos"]:
        lines.append(f"Aviso: {w}")
    lines += ["", c["nota"]]
    return "\n".join(lines)


def render_markdown(c: dict[str, Any]) -> str:
    out = [
        f"# {c['farmacia']} — Evolución del {spanish_date(c['antes'])} al {spanish_date(c['despues'])}",
        "",
        f"**{headline(c)}**",
        "",
        "| Indicador | Antes | Después | Reducción | % |",
        "|---|---:|---:|---:|---:|",
        *(f"| {i['nombre']} | {eur(i['antes'])} | {eur(i['despues'])} | {eur(i['reduccion'])} "
          f"| {pct(i['reduccion_pct'])} |" for i in c["indicadores"]),
        "",
        "## Acciones",
        "",
        "| Acción | Estado | Avance | Antes | Después |",
        "|---|---|---:|---:|---:|",
        *(f"| {a['titulo']} | {STATUS_LABELS[a['estado']]} | "
          f"{'—' if a['avance'] is None else number(a['avance'] * 100) + ' %'} | {eur(a['antes_eur'])} "
          f"| {eur(a['despues_eur'])} |" for a in c["acciones"]),
        "",
        *(f"> Aviso: {w}" for w in c["avisos"]),
        f"_{c['nota']}_",
    ]
    return "\n".join(out) + "\n"
