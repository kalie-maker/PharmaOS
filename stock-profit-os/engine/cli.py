"""CLI de Stock Profit OS.

    python -m engine.cli generar-mock --salida data/sample
    python -m engine.cli inspeccionar --fichero export.csv [--tipo ventas] [--nombre mi_farmacia]
    python -m engine.cli analizar --programa farmatic --ventas ... --stock ... --compras ... \\
        --farmacia "Farmacia Demo" --salida output/ [--prefijo semana0] [--anonimizar]
    python -m engine.cli comparar --antes output/semana0.json --despues output/semana3.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from engine import compare as cmp
from engine.anonymize import Anonymizer
from engine.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MAPPINGS_DIR,
    DEFAULT_SYNONYMS_PATH,
    ConfigError,
    load_mapping,
    load_thresholds,
)
from engine.formatting import eur, number
from engine.ingest import IngestError, SheetCandidate
from engine.inspection import InspectError, inspect_file, write_draft
from engine.metrics import MetricsError
from engine.mock.generate import MockConfig, generate_to
from engine.mock.scenario import generate_week3_scenario
from engine.pilot import STOP_PRIVACY, PilotStop, run_pilot
from engine.pipeline import load_and_check, run_analysis
from engine.privacy import PrivacyError
from engine.report import write_reports
from engine.schemas import DATASETS

EXIT_OK = 0
EXIT_INPUT_ERROR = 1
EXIT_PRIVACY = 2
EXIT_STOPPED = 3  # piloto detenido: mapeo pendiente o calidad baja


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def interactive_sheet_chooser(path: Path, candidates: list[SheetCandidate]) -> str:
    """Pregunta qué hoja usar. Solo se usa si hay terminal interactiva."""
    print(f"{path.name} tiene varias hojas con datos:")
    for i, c in enumerate(candidates, start=1):
        print(f"  {i}. {c.name} ({number(c.rows)} filas, {c.score} columnas reconocidas)")
    while True:
        answer = input("¿Qué hoja uso? (número): ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1].name
        print("Respuesta no válida.")


def _chooser(args: argparse.Namespace):
    return interactive_sheet_chooser if sys.stdin.isatty() and not getattr(args, "no_interactivo", False) else None


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


def _cmd_generate_mock(args: argparse.Namespace) -> int:
    config = MockConfig(n_refs=args.referencias, seed=args.semilla, end_date=args.fecha_fin)
    if args.escenario == "semana3":
        scenario = generate_week3_scenario(args.salida, config)
        print(f"Escenario de demo generado en {args.salida} (semana 0 y semana 3, misma farmacia ficticia):")
        for week in ("semana0", "semana3"):
            print(f"  {week}: {Path(args.salida) / week}")
        for key, value in scenario["resumen"].items():
            print(f"    {key.replace('_', ' ')}: {value}")
        print(f"Instrucciones: {Path(args.salida) / 'LEEME.md'}")
        return EXIT_OK
    paths = generate_to(args.salida, config)
    print(f"Datos mock generados (semilla {config.seed}, {config.n_refs} referencias):")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return EXIT_OK


def _cmd_analyze(args: argparse.Namespace) -> int:
    paths = {"ventas": args.ventas, "stock": args.stock, "compras": args.compras}
    sheets = {"ventas": args.hoja_ventas, "stock": args.hoja_stock, "compras": args.hoja_compras}
    try:
        thresholds = load_thresholds(args.config)
        mapping = load_mapping(args.programa, args.mapeos)
        if mapping.draft:
            _err(f"Aviso: el mapeo '{args.programa}' es un BORRADOR. Revísalo y pon `borrador: false`.")
        if args.solo_calidad:
            ingest, quality = load_and_check(paths, mapping, thresholds, sheets, _chooser(args))
            _print_ingest(ingest)
            print("\n".join(quality.lines()))
            return EXIT_OK
        anonymizer = Anonymizer(scale=args.escalar_cifras) if args.anonimizar else None
        output = run_analysis(paths, mapping, thresholds, args.farmacia, anonymizer, sheets, _chooser(args))
    except PrivacyError as exc:
        _err(exc.message())
        return EXIT_PRIVACY
    except (ConfigError, IngestError, MetricsError) as exc:
        _err(f"Error: {exc}")
        return EXIT_INPUT_ERROR

    name = output.results["farmacia"]
    print(f"{name} — análisis completado (programa: {mapping.program})")
    _print_ingest(output.ingest)
    print("\n".join(output.quality.lines()))
    print()
    default = "ejemplo" if args.anonimizar else "informe"
    prefix = args.prefijo or f"{default}_{output.results['periodo']['fecha_referencia']}"
    report_paths = write_reports(output.results, args.salida, prefix)
    print(output.results["resumen"])
    for action in output.results["acciones"]:
        print(f"  {action['priority']:>2}. {eur(action['impact_eur']):>14}  {action['titulo']}")
    print("Informe:")
    for kind, path in report_paths.items():
        print(f"  {kind}: {path}")
    return EXIT_OK


def _print_ingest(ingest) -> None:
    for name, result in ingest.items():
        fmt = result.format
        detail = ", ".join(f"{k}: {v}" for k, v in fmt.items() if k in ("codificacion", "separador", "hoja",
                                                                          "fila_cabecera"))
        print(f"  {name}: {number(len(result.data))} filas ({detail})")
        if result.ignored_columns:
            print(f"    columnas ignoradas: {', '.join(result.ignored_columns)}")
        for warning in result.warnings:
            print(f"    aviso: {warning}")


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        ins = inspect_file(args.fichero, None if args.tipo == "auto" else args.tipo, args.hoja,
                           _chooser(args), args.mapeos, args.sinonimos)
    except (IngestError, InspectError, ConfigError) as exc:
        _err(f"Error: {exc}")
        return EXIT_INPUT_ERROR

    fmt = ins.format
    print(f"Fichero: {ins.path.name} · {number(ins.rows)} filas")
    parts = [str(fmt.get("tipo", "")).upper()]
    for key, label in (("hoja", "hoja"), ("codificacion", "codificación"), ("separador", "separador"),
                       ("fila_cabecera", "cabecera en fila")):
        if key in fmt:
            parts.append(f"{label} {fmt[key]}")
    for key, label in (("decimal", "decimal"), ("formato_fecha", "fechas")):
        if key in ins.read_options:
            value = ins.read_options[key]
            parts.append(f"{label} {'coma' if value == ',' else 'punto' if value == '.' else value}")
    print("Formato: " + " · ".join(parts))
    origin = "indicado" if ins.dataset_forced else f"detectado, puntuación {number(ins.dataset_scores[ins.dataset], 2)}"
    print(f"Tipo de fichero: {ins.dataset} ({origin})")

    matched = {m.column: m for m in ins.matches if m.column}
    print(f"\nColumnas ({len(ins.columns)}):")
    width = max((len(c.name) for c in ins.columns), default=10) + 2
    for col in ins.columns:
        if col.privacy:
            target = f"⚠ POSIBLE DATO PERSONAL: {col.privacy.reason}"
        elif col.name in matched:
            m = matched[col.name]
            target = f"-> {m.canonical} ({number(m.score * 100)} %){'  REVISAR' if m.needs_review else ''}"
        else:
            target = "(sin uso)"
        print(f"  {col.name:<{width}}{col.kind:<8}{number(col.filled_pct)} % lleno  {target}")

    if ins.missing_required:
        print(f"\nFaltan columnas obligatorias para {ins.dataset}: {', '.join(ins.missing_required)}")
    if ins.families:
        print("\nFamilias encontradas:")
        for label, fam in ins.families.items():
            print(f"  {label} -> {fam or 'sin coincidencia (REVISAR)'}")
    if ins.privacy_findings:
        cols = ", ".join(f"'{f.column}'" for f in ins.privacy_findings)
        print(f"\n⚠ Columnas con posibles datos personales: {cols}. No se incluyen en el mapeo y "
              "`analizar` rechazará este fichero: vuelve a exportarlo sin ellas.")

    if args.no_guardar:
        return EXIT_OK
    try:
        path = write_draft(ins, args.nombre, args.mapeos, args.forzar)
    except (InspectError, ConfigError) as exc:
        _err(f"Error: {exc}")
        return EXIT_INPUT_ERROR
    print(f"\nBorrador guardado en {path}. Revísalo y úsalo con --programa {args.nombre}.")
    return EXIT_OK


def _cmd_compare(args: argparse.Namespace) -> int:
    try:
        thresholds = load_thresholds(args.config)
        before, after = cmp.load_results(args.antes), cmp.load_results(args.despues)
        if args.anonimizar:
            anonymizer = Anonymizer(scale=args.escalar_cifras)  # mismos alias y factor en ambos
            before, after = anonymizer.apply(before), anonymizer.apply(after)
        result = cmp.compare(before, after, thresholds.comparison)
    except (cmp.CompareError, ConfigError) as exc:
        _err(f"Error: {exc}")
        return EXIT_INPUT_ERROR
    print(cmp.render_text(result))
    if args.salida:
        out = Path(args.salida)
        out.mkdir(parents=True, exist_ok=True)
        stem = f"comparacion_{result['antes']}_{result['despues']}"
        (out / f"{stem}.md").write_text(cmp.render_markdown(result), encoding="utf-8")
        (out / f"{stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nGuardado en {out / stem}.md y .json")
    return EXIT_OK


def _cmd_pilot(args: argparse.Namespace) -> int:
    try:
        outcome = run_pilot(
            args.carpeta, args.programa, args.nombre, args.salida, args.id, args.mapeos, args.config,
            args.sinonimos, args.ignorar_calidad, _chooser(args),
        )
    except PilotStop as exc:
        _err(f"\nPARADO ({exc.reason}): {exc}")
        return EXIT_PRIVACY if exc.reason == STOP_PRIVACY else EXIT_STOPPED
    except (ConfigError, IngestError, InspectError) as exc:
        _err(f"Error: {exc}")
        return EXIT_INPUT_ERROR
    print(f"\nListo. Revisa a mano {outcome.reports['html']} antes de entregarlo.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stock-profit-os", description="Stock Profit OS")
    sub = parser.add_subparsers(dest="command", required=True)

    mock = sub.add_parser("generar-mock", help="Genera datos de prueba de una farmacia ficticia")
    mock.add_argument("--salida", type=Path, default=Path("data/sample"))
    mock.add_argument("--semilla", type=int, default=MockConfig.seed)
    mock.add_argument("--referencias", type=int, default=MockConfig.n_refs)
    mock.add_argument("--fecha-fin", type=date.fromisoformat, default=MockConfig.end_date,
                      help="Último día de ventas (AAAA-MM-DD)")
    mock.add_argument("--escenario", choices=["base", "semana3"], default="base",
                      help="semana3: genera semana0/ y semana3/ de la misma farmacia para la demo de comparar")
    mock.set_defaults(func=_cmd_generate_mock)

    analyze = sub.add_parser("analizar", help="Analiza las exportaciones y genera el informe")
    analyze.add_argument("--programa", required=True, help="Programa de gestión (nombre del mapeo)")
    analyze.add_argument("--ventas", required=True, type=Path)
    analyze.add_argument("--stock", required=True, type=Path)
    analyze.add_argument("--compras", required=True, type=Path)
    analyze.add_argument("--farmacia", required=True)
    analyze.add_argument("--salida", type=Path, default=Path("output"))
    analyze.add_argument("--prefijo", help="Nombre base de los ficheros (por defecto informe_<fecha>)")
    analyze.add_argument("--anonimizar", action="store_true",
                         help="Farmacia, laboratorios y productos anónimos (para enseñar el informe)")
    analyze.add_argument("--escalar-cifras", action="store_true",
                         help="Con --anonimizar: multiplica los € por un factor aleatorio entre 0,7 y 1,3")
    analyze.add_argument("--solo-calidad", action="store_true", help="Solo muestra la calidad de los datos")
    for dataset in DATASETS:
        analyze.add_argument(f"--hoja-{dataset}", help=f"Hoja del Excel de {dataset}")
    analyze.add_argument("--no-interactivo", action="store_true", help="No preguntar nunca (falla si hay dudas)")
    analyze.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    analyze.add_argument("--mapeos", type=Path, default=DEFAULT_MAPPINGS_DIR)
    analyze.set_defaults(func=_cmd_analyze)

    inspect = sub.add_parser("inspeccionar", help="Inspecciona una exportación y propone un mapeo")
    inspect.add_argument("--fichero", required=True, type=Path)
    inspect.add_argument("--tipo", choices=["auto", *DATASETS], default="auto")
    inspect.add_argument("--nombre", default="borrador", help="Nombre del mapeo (config/mappings/<nombre>.yaml)")
    inspect.add_argument("--hoja", help="Hoja del Excel")
    inspect.add_argument("--forzar", action="store_true", help="Sobrescribir un mapeo que no es borrador")
    inspect.add_argument("--no-guardar", action="store_true", help="Solo mostrar, sin escribir el borrador")
    inspect.add_argument("--no-interactivo", action="store_true")
    inspect.add_argument("--mapeos", type=Path, default=DEFAULT_MAPPINGS_DIR)
    inspect.add_argument("--sinonimos", type=Path, default=DEFAULT_SYNONYMS_PATH)
    inspect.set_defaults(func=_cmd_inspect)

    comp = sub.add_parser("comparar", help="Compara dos informes JSON (antes y después)")
    comp.add_argument("--antes", required=True, type=Path)
    comp.add_argument("--despues", required=True, type=Path)
    comp.add_argument("--salida", type=Path, help="Carpeta donde guardar la comparación en MD y JSON")
    comp.add_argument("--anonimizar", action="store_true")
    comp.add_argument("--escalar-cifras", action="store_true")
    comp.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    comp.set_defaults(func=_cmd_compare)

    pilot = sub.add_parser("piloto", help="Flujo completo para una farmacia: inspeccionar, calidad, informe")
    pilot.add_argument("--carpeta", required=True, type=Path, help="Carpeta con las 3 exportaciones")
    pilot.add_argument("--programa", required=True, help="Nombre del mapeo (se crea un borrador si no existe)")
    pilot.add_argument("--nombre", required=True, help="Nombre de la farmacia para el informe")
    pilot.add_argument("--id", help="Identificador de la farmacia en output/ (por defecto, nombre de la carpeta)")
    pilot.add_argument("--salida", type=Path, default=Path("output"))
    pilot.add_argument("--ignorar-calidad", action="store_true", help="Generar el informe aunque la calidad sea baja")
    pilot.add_argument("--no-interactivo", action="store_true")
    pilot.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    pilot.add_argument("--mapeos", type=Path, default=DEFAULT_MAPPINGS_DIR)
    pilot.add_argument("--sinonimos", type=Path, default=DEFAULT_SYNONYMS_PATH)
    pilot.set_defaults(func=_cmd_pilot)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "escalar_cifras", False) and not getattr(args, "anonimizar", False):
        parser.error("--escalar-cifras requiere --anonimizar")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
