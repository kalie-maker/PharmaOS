"""Orquestación del análisis completo: ingesta -> calidad -> métricas -> acciones -> resultados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from engine.actions import ActionPlan, build_actions
from engine.config import Mapping, Thresholds
from engine.ingest import IngestResult, SheetChooser, load_all
from engine.metrics import MetricsResult, compute_metrics
from engine.quality import QualityReport, assess_quality
from engine.report import build_results


@dataclass
class AnalysisOutput:
    ingest: dict[str, IngestResult]
    quality: QualityReport
    metrics: MetricsResult
    plan: ActionPlan
    results: dict[str, Any]


def load_and_check(
    paths: dict[str, Path | str],
    mapping: Mapping,
    thresholds: Thresholds,
    sheets: dict[str, str | None] | None = None,
    chooser: SheetChooser | None = None,
    today: date | None = None,
) -> tuple[dict[str, IngestResult], QualityReport]:
    ingest = load_all(paths, mapping, thresholds, sheets, chooser)
    return ingest, assess_quality(ingest, thresholds, today)


def run_analysis(
    paths: dict[str, Path | str],
    mapping: Mapping,
    thresholds: Thresholds,
    pharmacy: str,
    anonymize: bool = False,
    sheets: dict[str, str | None] | None = None,
    chooser: SheetChooser | None = None,
    today: date | None = None,
) -> AnalysisOutput:
    ingest, quality = load_and_check(paths, mapping, thresholds, sheets, chooser, today)
    data = {name: result.data for name, result in ingest.items()}
    metrics = compute_metrics(data["ventas"], data["stock"], data["compras"], thresholds)
    plan = build_actions(metrics, thresholds)
    results = build_results(
        metrics, plan, thresholds, pharmacy,
        program=mapping.program, quality=quality.to_dict(), anonymize=anonymize,
    )
    return AnalysisOutput(ingest, quality, metrics, plan, results)
