"""Orquestación del análisis completo: ingesta -> métricas -> acciones -> resultados."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.actions import ActionPlan, build_actions
from engine.config import Mapping, Thresholds
from engine.ingest import IngestResult, load_all
from engine.metrics import MetricsResult, compute_metrics
from engine.report import build_results


@dataclass
class AnalysisOutput:
    ingest: dict[str, IngestResult]
    metrics: MetricsResult
    plan: ActionPlan
    results: dict[str, Any]


def run_analysis(
    paths: dict[str, Path | str],
    mapping: Mapping,
    thresholds: Thresholds,
    pharmacy: str,
    anonymize: bool = False,
) -> AnalysisOutput:
    ingest = load_all(paths, mapping, thresholds)
    data = {name: result.data for name, result in ingest.items()}
    metrics = compute_metrics(data["ventas"], data["stock"], data["compras"], thresholds)
    plan = build_actions(metrics, thresholds)
    results = build_results(metrics, plan, thresholds, pharmacy, program=mapping.program, anonymize=anonymize)
    return AnalysisOutput(ingest, metrics, plan, results)
