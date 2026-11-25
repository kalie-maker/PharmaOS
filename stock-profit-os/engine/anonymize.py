"""Anonimización de resultados para enseñar un informe como ejemplo.

Se aplica sobre el JSON de resultados (antes de redactar los textos):
- Farmacia -> "Farmacia Demo".
- Laboratorios -> "Laboratorio A, B, C…", de forma consistente en todo el informe.
- Productos -> "<familia> · REF-0001": sin código nacional ni descripción original.
- Opcional: todas las cifras en € multiplicadas por un factor aleatorio (0,7–1,3) que no
  se guarda en ningún sitio. Porcentajes, ratios, días y nº de referencias no cambian,
  así que las proporciones se mantienen.

Un mismo `Anonymizer` aplicado a dos informes (antes/después) usa los mismos alias y el
mismo factor, de modo que siguen siendo comparables.
"""

from __future__ import annotations

import copy
import random
import re
from typing import Any

from engine.metrics import UNKNOWN_LAB
from engine.narrative import Narrator, narrate
from engine.schemas import FAMILY_LABELS, Family

DEMO_PHARMACY = "Farmacia Demo"
SCALE_RANGE = (0.7, 1.3)
_MONEY_KEY = re.compile(r"(_eur$|^valor_stock$|^compras_coste$|^coste_ventas$)")


def _letters(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA…"""
    out = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def family_label(family: str | None) -> str:
    try:
        return FAMILY_LABELS[Family(family)]
    except ValueError:
        return FAMILY_LABELS[Family.OTHER]


class Anonymizer:
    def __init__(self, scale: bool = False, seed: int | None = None, pharmacy: str = DEMO_PHARMACY):
        self.pharmacy = pharmacy
        self.scale = scale
        # Sin semilla: factor impredecible. La semilla solo existe para tests.
        self.factor = random.Random(seed).uniform(*SCALE_RANGE) if scale else 1.0
        self.labs: dict[str, str] = {}
        self.codes: dict[str, str] = {}

    def lab(self, name: str | None) -> str | None:
        if name is None or name == UNKNOWN_LAB:
            return name
        if name not in self.labs:
            self.labs[name] = f"Laboratorio {_letters(len(self.labs))}"
        return self.labs[name]

    def code(self, cn: str) -> str:
        if cn not in self.codes:
            self.codes[cn] = f"REF-{len(self.codes) + 1:04d}"
        return self.codes[cn]

    def product(self, cn: str, family: str | None) -> str:
        return f"{family_label(family)} · {self.code(cn)}"

    # -----------------------------------------------------------------------

    def apply(self, results: dict[str, Any], narrator: Narrator | None = None) -> dict[str, Any]:
        r = copy.deepcopy(results)
        snapshot: dict[str, dict[str, Any]] = r.get("referencias") or {}
        families = {cn: ref.get("familia") for cn, ref in snapshot.items()}

        def ref_row(row: dict[str, Any]) -> None:
            cn = row.get("codigo_nacional")
            if cn is None:
                return
            family = row.get("familia", families.get(cn))
            row["codigo_nacional"] = self.code(cn)
            if "descripcion" in row:
                row["descripcion"] = self.product(cn, family)
            if "laboratorio" in row:
                row["laboratorio"] = self.lab(row["laboratorio"])

        r["farmacia"] = self.pharmacy
        r["anonimizado"] = True
        r["cifras_escaladas"] = self.scale

        for action in [*r.get("acciones", []), *r.get("anexo_acciones", [])]:
            if action.get("subject"):
                action["subject"] = self.lab(action["subject"]) if action["type"] == "revisar_laboratorio" \
                    else action["subject"]
            if "laboratorio" in action.get("facts", {}):
                action["facts"]["laboratorio"] = self.lab(action["facts"]["laboratorio"])
            action["key"] = f"{action['type']}:{action['subject']}" if action.get("subject") else action["type"]
            for ref in action.get("references", []):
                ref_row(ref)
            action["affected_codes"] = [self.code(cn) for cn in action.get("affected_codes", [])]

        for rows in (r.get("anexo") or {}).values():
            for row in rows:
                ref_row(row)
        for row in r.get("laboratorios", []):
            row["laboratorio"] = self.lab(row["laboratorio"])

        new_snapshot = {}
        for cn, ref in snapshot.items():
            ref = dict(ref)
            ref["descripcion"] = self.product(cn, ref.get("familia"))
            ref["laboratorio"] = self.lab(ref.get("laboratorio"))
            new_snapshot[self.code(cn)] = ref
        r["referencias"] = new_snapshot

        if self.scale:
            r = _scale(r, self.factor)
        return narrate(r, narrator)


def _scale(value: Any, factor: float, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: _scale(v, factor, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_scale(v, factor, key) for v in value]
    if key and _MONEY_KEY.search(key) and isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value * factor, 2)
    return value
