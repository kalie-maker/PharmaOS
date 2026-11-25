"""Convierte métricas en acciones con impacto en €, ordenadas y priorizadas.

Las acciones solo contienen hechos (cifras y referencias). El texto lo redacta
engine/narrative.py a partir de esos hechos.

Para no contar dos veces el mismo euro entre acciones de stock:
- Stock sin movimiento crítico -> solo "devolver o liquidar".
- Sobrestock y caducidad excluyen las referencias sin movimiento crítico.
La revisión por laboratorio es otra perspectiva (compras futuras) y puede solaparse.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

import pandas as pd

from engine.config import Thresholds
from engine.metrics import MetricsResult


class ActionType(StrEnum):
    RETURN_DEAD_STOCK = "devolver_sin_movimiento"
    REDUCE_ORDER = "reducir_pedido"
    PROMOTE_BEFORE_EXPIRY = "promocionar_caducidad"
    REPLENISH = "reponer_rotura"
    REVIEW_LAB = "revisar_laboratorio"


@dataclass
class ActionReference:
    codigo_nacional: str
    descripcion: str | None
    laboratorio: str | None
    unidades: float
    importe_eur: float
    detalle: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    type: ActionType
    impact_eur: float
    facts: dict[str, Any]
    references: list[ActionReference]  # las primeras N, para el informe
    affected_codes: list[str]  # todas las afectadas, para comparar semanas
    subject: str | None = None  # p. ej. laboratorio
    priority: int = 0

    @property
    def key(self) -> str:
        return f"{self.type.value}:{self.subject}" if self.subject else self.type.value

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type.value
        data["key"] = self.key
        return data


@dataclass
class ActionPlan:
    main: list[Action]
    annex: list[Action]

    @property
    def all(self) -> list[Action]:
        return [*self.main, *self.annex]


def priority_label(rank: int) -> str:
    if rank <= 3:
        return "Alta"
    if rank <= 7:
        return "Media"
    return "Baja"


def _references(df: pd.DataFrame, units_col: str, eur_col: str, limit: int,
                detail_cols: tuple[str, ...] = ()) -> list[ActionReference]:
    top = df.sort_values(eur_col, ascending=False, kind="mergesort").head(limit)
    refs = []
    for code, row in top.iterrows():
        detail = {}
        for col in detail_cols:
            value = row[col]
            detail[col] = None if pd.isna(value) else (int(value) if float(value).is_integer() else round(float(value), 2))
        refs.append(ActionReference(
            codigo_nacional=str(code),
            descripcion=None if pd.isna(row["descripcion"]) else str(row["descripcion"]),
            laboratorio=None if pd.isna(row["laboratorio"]) else str(row["laboratorio"]),
            unidades=round(float(row[units_col]), 2),
            importe_eur=round(float(row[eur_col]), 2),
            detalle=detail,
        ))
    return refs


def _stock_action(action_type: ActionType, df: pd.DataFrame, units_col: str, eur_col: str,
                  t: Thresholds, detail_cols: tuple[str, ...], extra: dict[str, Any]) -> Action | None:
    df = df[df[eur_col] > 0]
    if df.empty:
        return None
    refs = _references(df, units_col, eur_col, t.max_refs_per_action, detail_cols)
    total = round(float(df[eur_col].sum()), 2)
    facts = {
        "referencias": int(len(df)),
        "total_eur": total,
        "top_referencias": len(refs),
        "top_eur": round(sum(r.importe_eur for r in refs), 2),
        **extra,
    }
    return Action(action_type, total, facts, refs, sorted(map(str, df.index)))


def build_actions(m: MetricsResult, t: Thresholds) -> ActionPlan:
    refs = m.refs
    dead = refs["sin_movimiento_critico"]
    candidates: list[Action | None] = []

    candidates.append(_stock_action(
        ActionType.RETURN_DEAD_STOCK, refs[dead], "stock_valorable", "valor_stock", t,
        ("dias_sin_venta",), {"dias": t.no_movement_critical_days},
    ))
    candidates.append(_stock_action(
        ActionType.REDUCE_ORDER, refs[~dead], "sobrestock_unidades", "sobrestock_eur", t,
        ("cobertura_dias", "cobertura_objetivo_dias"), {},
    ))
    max_window = max(t.expiry_windows_days)
    min_window = min(t.expiry_windows_days)
    expiry = refs[~dead]
    candidates.append(_stock_action(
        ActionType.PROMOTE_BEFORE_EXPIRY, expiry, "unidades_riesgo_caducidad", "riesgo_caducidad_eur", t,
        ("dias_hasta_caducidad",),
        {"ventana_dias": max_window, "ventana_corta_dias": min_window,
         "ventana_corta_eur": round(float(expiry[f"caduca_{min_window}d_eur"].sum()), 2)},
    ))
    candidates.append(_stock_action(
        ActionType.REPLENISH, refs[refs["riesgo_rotura"]], "unidades_en_riesgo_rotura", "ventas_perdidas_eur", t,
        ("stock_valorable", "punto_pedido"),
        {"horizonte_dias": t.replenishment_days + t.safety_days},
    ))

    for lab, row in m.labs[m.labs["compra_alta"]].iterrows():
        impact = round(float(row["exceso_compra_eur"]), 2)
        lab_refs = refs[(refs["laboratorio"] == lab) & ~dead]
        ratio = row["ratio_compras_ventas"]
        candidates.append(Action(
            ActionType.REVIEW_LAB,
            impact,
            {
                "laboratorio": str(lab),
                "meses": t.lab_window_months,
                "compras_eur": round(float(row["compras_coste"]), 2),
                "coste_ventas_eur": round(float(row["coste_ventas"]), 2),
                "ratio": None if pd.isna(ratio) else round(float(ratio), 2),
                "ratio_umbral": t.lab_high_ratio,
                "exceso_eur": impact,
                "sobrestock_lab_eur": round(float(lab_refs["sobrestock_eur"].sum()), 2),
            },
            _references(lab_refs[lab_refs["sobrestock_eur"] > 0], "sobrestock_unidades", "sobrestock_eur",
                        t.max_refs_per_action, ("cobertura_dias",)),
            sorted(map(str, lab_refs.index)),
            subject=str(lab),
        ))

    actions = [a for a in candidates if a is not None and a.impact_eur >= t.min_action_impact_eur]
    actions.sort(key=lambda a: (-a.impact_eur, a.key))
    for rank, action in enumerate(actions, start=1):
        action.priority = rank
    return ActionPlan(main=actions[: t.max_main_actions], annex=actions[t.max_main_actions :])
