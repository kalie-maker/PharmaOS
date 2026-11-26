"""La configuración generada para la web está al día con los YAML y el validador del motor."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "export_web_config.py"
spec = importlib.util.spec_from_file_location("export_web_config", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)  # type: ignore[union-attr]


def test_generated_file_is_up_to_date() -> None:
    if not module.DEFAULT_OUT.exists():
        pytest.skip("web no generada")
    assert module.main(["--comprobar"]) == 0


def test_config_contents() -> None:
    config = module.build()
    assert {"farmatic", "nixfarma"} <= set(config["mappings"])
    assert "codigo_nacional" in config["schemas"]["stock"]["required"]
    categories = {r["category"] for r in config["privacyHeaderRules"]}
    assert {"identidad", "tarjeta_sanitaria", "receta", "paciente", "telefono", "direccion"} <= categories
    # Los patrones Python son compatibles con RegExp de JavaScript (sin construcciones exclusivas de Python).
    for pattern in [r["pattern"] for r in config["privacyHeaderRules"]] + list(config["privacyContent"].values()):
        assert "(?P<" not in pattern and "\\A" not in pattern and "\\Z" not in pattern
        re.compile(pattern)
