"""Redacción del informe a partir del JSON de resultados.

`TemplateNarrator` usa plantillas fijas. Una futura capa de IA podrá implementar
el protocolo `Narrator`: recibirá SOLO el diccionario de resultados (ya calculado)
y devolverá textos. Nunca calculará cifras. No está implementada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from engine.formatting import eur0, number


@dataclass(frozen=True)
class ActionText:
    title: str
    explanation: str


class Narrator(Protocol):
    def action_text(self, action: dict[str, Any]) -> ActionText: ...

    def summary(self, results: dict[str, Any]) -> str: ...


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{number(n)} {singular if n == 1 else plural}"


class TemplateNarrator:
    """Textos deterministas por tipo de acción."""

    def action_text(self, action: dict[str, Any]) -> ActionText:
        f = action["facts"]
        kind = action["type"]
        if kind == "devolver_sin_movimiento":
            refs = _plural(f["referencias"], "referencia", "referencias")
            first = (f" Devuelve estas {f['top_referencias']} primero ({eur0(f['top_eur'])})."
                     if f["top_referencias"] < f["referencias"] else " Devuélvelas o liquídalas.")
            return ActionText(
                f"Devuelve o liquida stock sin ventas en {f['dias']} días",
                f"Tienes {eur0(f['total_eur'])} en {refs} sin ventas en {f['dias']} días.{first}",
            )
        if kind == "reducir_pedido":
            refs = _plural(f["referencias"], "referencia supera", "referencias superan")
            return ActionText(
                f"Reduce el próximo pedido: {eur0(f['total_eur'])} de sobrestock",
                f"{refs} su cobertura objetivo. No repongas estas {f['top_referencias']} hasta "
                f"volver a su nivel ({eur0(f['top_eur'])} de exceso).",
            )
        if kind == "promocionar_caducidad":
            refs = _plural(f["referencias"], "referencia caduca", "referencias caducan")
            return ActionText(
                f"Promociona antes de que caduque: {eur0(f['total_eur'])} en riesgo",
                f"{refs} en {f['ventana_dias']} días o menos y no se venderán a tiempo al ritmo actual "
                f"({eur0(f['ventana_corta_eur'])} en los próximos {f['ventana_corta_dias']} días). "
                "Ponlas en promoción o pide el cambio al proveedor.",
            )
        if kind == "reponer_rotura":
            refs = _plural(f["referencias"], "referencia", "referencias")
            return ActionText(
                f"Repón {refs} con riesgo de rotura",
                f"Se venden con frecuencia y su stock está por debajo del punto de pedido. "
                f"Si se agotan, puedes perder unos {eur0(f['total_eur'])} en ventas en "
                f"{number(f['horizonte_dias'])} días.",
            )
        if kind == "revisar_laboratorio":
            if f["ratio"] is None:
                detail = (f"En los últimos {f['meses']} meses le has comprado {eur0(f['compras_eur'])} "
                          "a coste sin ventas registradas.")
            else:
                detail = (f"En los últimos {f['meses']} meses le has comprado {eur0(f['compras_eur'])} a coste "
                          f"y has vendido {eur0(f['coste_ventas_eur'])}: "
                          f"compras/ventas = {number(f['ratio'], 2)}.")
            return ActionText(
                f"Revisa las compras a {f['laboratorio']}",
                f"{detail} Exceso de compra: {eur0(f['exceso_eur'])}. Ajusta el próximo pedido u oferta.",
            )
        raise ValueError(f"Tipo de acción sin plantilla: {kind}")

    def summary(self, results: dict[str, Any]) -> str:
        actions = results["acciones"]
        if not actions:
            return "Esta semana no hay acciones con impacto relevante."
        total = sum(a["impact_eur"] for a in actions)
        return (
            f"{_plural(len(actions), 'acción priorizada', 'acciones priorizadas')} con un impacto "
            f"estimado de {eur0(total)}. Empieza por la primera: {actions[0]['titulo'].lower()}."
        )


def narrate(results: dict[str, Any], narrator: Narrator | None = None) -> dict[str, Any]:
    """Añade 'titulo' y 'explicacion' a cada acción y un 'resumen'. Modifica y devuelve results."""
    narrator = narrator or TemplateNarrator()
    for action in [*results["acciones"], *results["anexo_acciones"]]:
        text = narrator.action_text(action)
        action["titulo"], action["explicacion"] = text.title, text.explanation
    results["resumen"] = narrator.summary(results)
    return results
