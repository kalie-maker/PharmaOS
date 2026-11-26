"""Genera web/src/generated/engineConfig.ts a partir de la configuración del motor.

Fuente única: config/mappings/*.yaml (sin borradores), config/sinonimos.yaml,
engine/schemas.py (columnas obligatorias) y engine/privacy.py (reglas de privacidad).
Así la web detecta columnas y bloquea datos personales con las mismas reglas que el motor.

Uso: python3 scripts/export_web_config.py [--salida RUTA] [--comprobar]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from engine import privacy  # noqa: E402
from engine.config import DEFAULT_MAPPINGS_DIR, DEFAULT_SYNONYMS_PATH  # noqa: E402
from engine.schemas import FAMILY_LABELS, SCHEMAS  # noqa: E402

DEFAULT_OUT = ROOT.parent / "web" / "src" / "generated" / "engineConfig.ts"


def build() -> dict:
    mappings = {}
    for path in sorted(DEFAULT_MAPPINGS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("borrador"):
            continue
        mappings[data.get("programa", path.stem)] = {
            "lectura": data.get("lectura") or {},
            "ficheros": {ds: {k: (v if isinstance(v, list) else [v]) for k, v in spec.items()}
                         for ds, spec in (data.get("ficheros") or {}).items()},
            "familias": data.get("familias") or {},
        }
    synonyms = yaml.safe_load(DEFAULT_SYNONYMS_PATH.read_text(encoding="utf-8")) or {}
    return {
        "mappings": mappings,
        "synonyms": synonyms.get("columnas") or {},
        "schemas": {name: {"required": s.required, "columns": s.column_names} for name, s in SCHEMAS.items()},
        "familyLabels": {f.value: label for f, label in FAMILY_LABELS.items()},
        "privacyHeaderRules": [
            {"category": r.category, "pattern": r.pattern.pattern, "reason": r.reason} for r in privacy.HEADER_RULES
        ],
        "privacyContent": {
            "dni": privacy._DNI.pattern,
            "nie": privacy._NIE.pattern,
            "email": privacy._EMAIL.pattern,
            "phone": privacy._PHONE.pattern,
        },
    }


def render(config: dict) -> str:
    body = json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        "// GENERADO por stock-profit-os/scripts/export_web_config.py — NO EDITAR A MANO.\n"
        "// Regenerar con: npm run gen:config\n"
        f"export const ENGINE_CONFIG = {body} as const;\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--comprobar", action="store_true", help="Falla si el fichero no está al día")
    args = parser.parse_args(argv)
    text = render(build())
    if args.comprobar:
        current = args.salida.read_text(encoding="utf-8") if args.salida.exists() else ""
        if current != text:
            print(f"{args.salida} no está al día: ejecuta `npm run gen:config`", file=sys.stderr)
            return 1
        return 0
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(text, encoding="utf-8")
    print(f"Generado {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
