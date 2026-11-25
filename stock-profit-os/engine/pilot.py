"""Comando `piloto`: todo el flujo de una farmacia de una vez.

carpeta con exportaciones -> identificar ficheros -> inspeccionar (formato y privacidad)
-> comprobar mapeo -> calidad de datos -> análisis -> output/<id>/<fecha>/
-> si hay un informe anterior de la misma farmacia, comparación automática.

Se para con un mensaje claro (PilotStop) si hay datos personales, el mapeo falta,
está en borrador o incompleto, o la calidad de datos es baja.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from engine import compare as cmp
from engine.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MAPPINGS_DIR,
    DEFAULT_SYNONYMS_PATH,
    ConfigError,
    load_mapping,
    load_thresholds,
)
from engine.ingest import IngestError, SheetChooser
from engine.inspection import FILENAME_HINTS, Inspection, inspect_file, write_draft
from engine.metrics import MetricsError
from engine.pipeline import analyze_loaded, load_and_check
from engine.report import write_reports
from engine.schemas import DATASETS

SUPPORTED_SUFFIXES = {".csv", ".txt", ".tsv", ".xlsx", ".xlsm"}
REPORT_PREFIX = "informe"

STOP_PRIVACY = "privacidad"
STOP_MAPPING = "mapeo"
STOP_QUALITY = "calidad"
STOP_FILES = "ficheros"


class PilotStop(Exception):
    """El flujo se detiene por un motivo que requiere intervención humana."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(message)


@dataclass
class PilotOutcome:
    out_dir: Path
    reports: dict[str, Path]
    results: dict[str, Any]
    comparison: dict[str, Any] | None = None
    files: dict[str, Path] = field(default_factory=dict)


def find_input_files(folder: Path, log: Callable[[str], None] = print,
                     mappings_dir: Path = DEFAULT_MAPPINGS_DIR,
                     synonyms_path: Path = DEFAULT_SYNONYMS_PATH) -> dict[str, Path]:
    """Asigna cada fichero de la carpeta a ventas/stock/compras (por nombre o por contenido)."""
    if not folder.is_dir():
        raise PilotStop(STOP_FILES, f"No existe la carpeta {folder}")
    files = sorted(p for p in folder.iterdir()
                   if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES and not p.name.startswith("."))
    if not files:
        raise PilotStop(STOP_FILES, f"{folder} no contiene ficheros CSV, TXT o XLSX")

    assigned: dict[str, list[Path]] = {d: [] for d in DATASETS}
    for path in files:
        stem = path.stem.lower()
        by_name = [d for d, words in FILENAME_HINTS.items() if any(w in stem for w in words)]
        if len(by_name) == 1:
            assigned[by_name[0]].append(path)
            continue
        guess = inspect_file(path, mappings_dir=mappings_dir, synonyms_path=synonyms_path).dataset
        log(f"  {path.name}: identificado por su contenido como {guess}")
        assigned[guess].append(path)

    problems = []
    for dataset, paths in assigned.items():
        if not paths:
            problems.append(f"falta el fichero de {dataset}")
        elif len(paths) > 1:
            problems.append(f"hay varios ficheros de {dataset}: {', '.join(p.name for p in paths)}")
    if problems:
        raise PilotStop(STOP_FILES, f"{folder}: " + "; ".join(problems) +
                        ". Deja un único fichero por tipo y nómbralos con 'ventas', 'stock' y 'compras'.")
    return {dataset: paths[0] for dataset, paths in assigned.items()}


def _privacy_stop(inspections: dict[str, Inspection]) -> None:
    lines = []
    for dataset, ins in inspections.items():
        for f in ins.privacy_findings:
            lines.append(f"- {ins.path.name} ({dataset}), columna '{f.column}': {f.reason}.")
    if lines:
        raise PilotStop(STOP_PRIVACY, "Datos personales detectados. No se ha analizado nada.\n" + "\n".join(lines)
                        + "\nPide a la farmacia que vuelva a exportar sin esas columnas "
                          "(ver docs/piloto/guia-exportacion.md).")


def _previous_report(pilot_root: Path, current: date) -> Path | None:
    candidates = []
    for path in pilot_root.glob(f"*/{REPORT_PREFIX}.json"):
        try:
            report_date = date.fromisoformat(path.parent.name)
        except ValueError:
            continue
        if report_date < current:
            candidates.append((report_date, path))
    return max(candidates)[1] if candidates else None


def run_pilot(
    folder: Path | str,
    program: str,
    pharmacy: str,
    out_root: Path | str = Path("output"),
    pilot_id: str | None = None,
    mappings_dir: Path = DEFAULT_MAPPINGS_DIR,
    config_path: Path = DEFAULT_CONFIG_PATH,
    synonyms_path: Path = DEFAULT_SYNONYMS_PATH,
    ignore_quality: bool = False,
    chooser: SheetChooser | None = None,
    today: date | None = None,
    log: Callable[[str], None] = print,
) -> PilotOutcome:
    folder = Path(folder)
    pilot_id = pilot_id or folder.name
    thresholds = load_thresholds(config_path)

    # 1. Ficheros e inspección (formato + privacidad), antes de tocar ningún dato.
    log(f"1/5 Ficheros en {folder}")
    files = find_input_files(folder, log, mappings_dir, synonyms_path)
    inspections: dict[str, Inspection] = {}
    for dataset, path in files.items():
        ins = inspect_file(path, dataset, chooser=chooser, mappings_dir=mappings_dir, synonyms_path=synonyms_path)
        inspections[dataset] = ins
        fmt = ", ".join(f"{k}: {v}" for k, v in ins.format.items() if k in ("codificacion", "separador", "hoja"))
        log(f"  {dataset}: {path.name} · {ins.rows} filas · {fmt}")
    _privacy_stop(inspections)

    # 2. Mapeo.
    log(f"2/5 Mapeo '{program}'")
    if not (Path(mappings_dir) / f"{program}.yaml").exists():
        draft = None
        for ins in inspections.values():
            draft = write_draft(ins, program, mappings_dir)
        raise PilotStop(STOP_MAPPING, f"No existía el mapeo '{program}'. Se ha creado un borrador en {draft}. "
                                      "Revisa las líneas REVISAR, pon `borrador: false` y vuelve a ejecutar.")
    try:
        mapping = load_mapping(program, mappings_dir)
    except ConfigError as exc:
        raise PilotStop(STOP_MAPPING, f"Mapeo incompleto: {exc}") from exc
    if mapping.draft:
        raise PilotStop(STOP_MAPPING, f"El mapeo '{program}' sigue en borrador. Revísalo y pon `borrador: false`.")

    # 3. Lectura y calidad.
    log("3/5 Calidad de datos")
    try:
        ingest, quality = load_and_check(files, mapping, thresholds, chooser=chooser, today=today)
    except IngestError as exc:
        raise PilotStop(STOP_MAPPING, f"Los ficheros no encajan con el mapeo '{program}': {exc}") from exc
    for line in quality.lines():
        log(f"  {line}")
    if quality.nivel == "baja" and not ignore_quality:
        raise PilotStop(STOP_QUALITY, "Calidad de datos BAJA: no se genera el informe. Corrige la exportación "
                                      "o usa --ignorar-calidad si quieres el informe con el aviso.")

    # 4. Análisis e informe.
    log("4/5 Análisis")
    try:
        analysis = analyze_loaded(ingest, quality, mapping, thresholds, pharmacy)
    except MetricsError as exc:
        raise PilotStop(STOP_FILES, str(exc)) from exc
    ref_date = date.fromisoformat(analysis.results["periodo"]["fecha_referencia"])
    pilot_root = Path(out_root) / pilot_id
    out_dir = pilot_root / ref_date.isoformat()
    reports = write_reports(analysis.results, out_dir, REPORT_PREFIX)
    (out_dir / "calidad.md").write_text(
        "# Calidad de datos\n\n" + "\n".join(f"- {line}" for line in quality.lines()) + "\n", encoding="utf-8")
    log(f"  {analysis.results['resumen']}")
    log(f"  Informe: {reports['html']}")

    # 5. Comparación con el informe anterior de la misma farmacia, si existe.
    log("5/5 Comparación")
    comparison = None
    previous = _previous_report(pilot_root, ref_date)
    if previous is None:
        log("  Primer informe de esta farmacia: no hay nada con qué comparar todavía.")
    else:
        comparison = cmp.compare(cmp.load_results(previous), analysis.results, thresholds.comparison)
        stem = out_dir / f"comparacion_{previous.parent.name}"
        stem.with_suffix(".md").write_text(cmp.render_markdown(comparison), encoding="utf-8")
        stem.with_suffix(".json").write_text(json.dumps(comparison, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  {cmp.headline(comparison)}")
        log(f"  Comparación: {stem.with_suffix('.md')}")
    return PilotOutcome(out_dir, reports, analysis.results, comparison, files)
