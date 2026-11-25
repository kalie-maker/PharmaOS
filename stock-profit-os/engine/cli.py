"""CLI de Stock Profit OS.

    python -m engine.cli generar-mock --salida data/sample
    python -m engine.cli analizar --programa farmatic --ventas ... --stock ... --compras ... \
        --farmacia "Farmacia Demo" --salida output/
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from engine.config import DEFAULT_CONFIG_PATH, DEFAULT_MAPPINGS_DIR, ConfigError, load_mapping, load_thresholds
from engine.ingest import IngestError, load_all
from engine.mock.generate import MockConfig, generate_to
from engine.privacy import PrivacyError

EXIT_OK = 0
EXIT_INPUT_ERROR = 1
EXIT_PRIVACY = 2


def _cmd_generate_mock(args: argparse.Namespace) -> int:
    config = MockConfig(n_refs=args.referencias, seed=args.semilla, end_date=args.fecha_fin)
    paths = generate_to(args.salida, config)
    print(f"Datos mock generados (semilla {config.seed}, {config.n_refs} referencias):")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return EXIT_OK


def _cmd_analyze(args: argparse.Namespace) -> int:
    try:
        thresholds = load_thresholds(args.config)
        mapping = load_mapping(args.programa, args.mapeos)
        results = load_all(
            {"ventas": args.ventas, "stock": args.stock, "compras": args.compras}, mapping, thresholds
        )
    except PrivacyError as exc:
        print(exc.message(), file=sys.stderr)
        return EXIT_PRIVACY
    except (ConfigError, IngestError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    print(f"{args.farmacia} — ingesta validada (programa: {mapping.program})")
    for name, result in results.items():
        print(f"  {name}: {len(result.data):,} filas".replace(",", "."))
        if result.ignored_columns:
            print(f"    columnas ignoradas: {', '.join(result.ignored_columns)}")
        for warning in result.warnings:
            print(f"    aviso: {warning}")
    # Fase 2 y 3: métricas, acciones e informe.
    print("Métricas, acciones e informe: pendientes (fases 2 y 3).")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stock-profit-os", description="Stock Profit OS")
    sub = parser.add_subparsers(dest="command", required=True)

    mock = sub.add_parser("generar-mock", help="Genera datos de prueba de una farmacia ficticia")
    mock.add_argument("--salida", type=Path, default=Path("data/sample"))
    mock.add_argument("--semilla", type=int, default=MockConfig.seed)
    mock.add_argument("--referencias", type=int, default=MockConfig.n_refs)
    mock.add_argument("--fecha-fin", type=date.fromisoformat, default=MockConfig.end_date,
                      help="Último día de ventas (AAAA-MM-DD)")
    mock.set_defaults(func=_cmd_generate_mock)

    analyze = sub.add_parser("analizar", help="Analiza las exportaciones y genera el informe")
    analyze.add_argument("--programa", required=True, help="Programa de gestión (nombre del mapeo)")
    analyze.add_argument("--ventas", required=True, type=Path)
    analyze.add_argument("--stock", required=True, type=Path)
    analyze.add_argument("--compras", required=True, type=Path)
    analyze.add_argument("--farmacia", required=True)
    analyze.add_argument("--salida", type=Path, default=Path("output"))
    analyze.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    analyze.add_argument("--mapeos", type=Path, default=DEFAULT_MAPPINGS_DIR)
    analyze.set_defaults(func=_cmd_analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
