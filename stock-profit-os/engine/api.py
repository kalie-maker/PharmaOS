"""API local del motor para la web (Fase 13).

    python -m engine.cli servir            # http://localhost:8000  (docs: /docs)

Endpoints:
- GET    /salud                   estado y si hay un informe guardado
- GET    /programas               mapeos disponibles (farmatic, nixfarma…)
- POST   /analizar                ventas + stock + compras (multipart) -> analiza y guarda el informe
- GET    /informe[?nucleo=true]   último informe (report.json o su núcleo ligero)
- DELETE /informe                 borra el informe guardado

Privacidad: los ficheros subidos se escriben en un directorio temporal y se borran siempre al
terminar, haya error o no. Solo se guarda el informe resultante (datos de producto, sin
pacientes) en `out/api/`. Los errores de privacidad nunca incluyen valores de celdas.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from engine import __version__
from engine.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MAPPINGS_DIR,
    PROJECT_ROOT,
    ConfigError,
    load_mapping,
    load_thresholds,
)
from engine.ingest import IngestError
from engine.metrics import MetricsError
from engine.pipeline import analyze_loaded, load_and_check
from engine.privacy import PrivacyError
from engine.web_export import build_report, core_report

MAX_BYTES = 50 * 1024 * 1024
ALLOWED_SUFFIXES = {".csv", ".txt", ".tsv", ".xlsx", ".xlsm"}
DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3100"


def data_dir() -> Path:
    return Path(os.environ.get("PHARMAOS_DATA_DIR", PROJECT_ROOT / "out" / "api"))


def mappings_dir() -> Path:
    return Path(os.environ.get("PHARMAOS_MAPPINGS_DIR", DEFAULT_MAPPINGS_DIR))


app = FastAPI(title="PharmaOS · motor local", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("PHARMAOS_CORS", DEFAULT_ORIGINS).split(",") if o.strip()],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def _error(status: int, kind: str, message: str, **extra: Any) -> JSONResponse:
    return JSONResponse(status_code=status, content={"tipo": kind, "mensaje": message, **extra})


@app.get("/salud")
def health() -> dict[str, Any]:
    return {"estado": "ok", "version": __version__, "informe": (data_dir() / "report.json").exists()}


@app.get("/programas")
def programs() -> list[str]:
    names = []
    for path in sorted(mappings_dir().glob("*.yaml")):
        try:
            if not load_mapping(path.stem, mappings_dir()).draft:
                names.append(path.stem)
        except ConfigError:
            continue
    return names


def _save_upload(upload: UploadFile, target_dir: Path, name: str) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"{upload.filename}: formato no admitido (usa CSV o XLSX)")
    path = target_dir / f"{name}{suffix}"  # nunca se usa el nombre original como ruta
    size = 0
    with path.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, f"{upload.filename}: supera 50 MB")
            out.write(chunk)
    return path


@app.post("/analizar")
def analyze(
    ventas: UploadFile = File(...),
    stock: UploadFile = File(...),
    compras: UploadFile = File(...),
    programa: str = Form("farmatic"),
    farmacia: str = Form("Mi farmacia"),
) -> Any:
    tmp = Path(tempfile.mkdtemp(prefix="pharmaos_subida_"))
    try:
        try:
            thresholds = load_thresholds(DEFAULT_CONFIG_PATH)
            mapping = load_mapping(programa, mappings_dir())
        except ConfigError as exc:
            return _error(400, "configuracion", str(exc))
        try:
            paths = {name: _save_upload(f, tmp, name) for name, f in
                     (("ventas", ventas), ("stock", stock), ("compras", compras))}
        except HTTPException as exc:
            return _error(exc.status_code, "fichero", str(exc.detail))
        try:
            ingest, quality = load_and_check(paths, mapping, thresholds)
            analysis = analyze_loaded(ingest, quality, mapping, thresholds, farmacia.strip() or "Mi farmacia")
        except PrivacyError as exc:
            findings = [{"fichero": exc.label, "columna": f.column, "categoria": f.category, "motivo": f.reason,
                         "coincidencias": f.matches} for f in exc.findings]
            return _error(422, "privacidad", "Fichero rechazado: contiene datos personales.", hallazgos=findings)
        except (IngestError, MetricsError) as exc:
            return _error(400, "datos", str(exc))

        report = build_report(analysis.metrics, ingest["ventas"].data, thresholds, farmacia.strip() or "Mi farmacia",
                              mapping.program, fictitious=False)
        store = data_dir()
        store.mkdir(parents=True, exist_ok=True)
        (store / "report.json").write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")), "utf-8")
        (store / "report-core.json").write_text(
            json.dumps(core_report(report), ensure_ascii=False, separators=(",", ":")), "utf-8")
        return {
            "farmacia": report["farmacia"],
            "resumen": report["resumen"],
            "calidad": quality.to_dict(),
            "avisos": [w for r in ingest.values() for w in r.warnings],
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@app.get("/informe")
def report(nucleo: bool = False) -> Any:
    path = data_dir() / ("report-core.json" if nucleo else "report.json")
    if not path.exists():
        return _error(404, "sin_informe", "Todavía no hay ningún análisis. Sube tus ficheros en /subir.")
    return FileResponse(path, media_type="application/json")


@app.delete("/informe")
def delete_report() -> dict[str, bool]:
    for name in ("report.json", "report-core.json"):
        (data_dir() / name).unlink(missing_ok=True)
    return {"borrado": True}
