from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine.cli import EXIT_INPUT_ERROR, EXIT_OK, EXIT_PRIVACY, main
from engine.config import DEFAULT_CONFIG_PATH, ConfigError, load_mapping, load_thresholds


def test_thresholds_load(thresholds) -> None:
    assert thresholds.no_movement_critical_days == 180
    assert thresholds.coverage_for("ortopedia") == 90
    assert thresholds.coverage_for(None) == thresholds.target_coverage_days
    assert thresholds.expiry_windows_days == (30, 60, 90)


def test_invalid_thresholds_rejected(tmp_path: Path) -> None:
    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["sin_movimiento"]["dias_aviso"] = 200
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_thresholds(path)


def test_unknown_program_lists_available() -> None:
    with pytest.raises(ConfigError, match="farmatic"):
        load_mapping("inexistente")


def test_cli_generate_and_analyze(tmp_path: Path, capsys) -> None:
    out = tmp_path / "sample"
    assert main(["generar-mock", "--salida", str(out), "--referencias", "150"]) == EXIT_OK
    code = main([
        "analizar", "--programa", "farmatic", "--ventas", str(out / "ventas.csv"),
        "--stock", str(out / "stock.csv"), "--compras", str(out / "compras.csv"),
        "--farmacia", "Farmacia Demo", "--salida", str(tmp_path / "output"),
    ])
    assert code == EXIT_OK
    assert "ingesta validada" in capsys.readouterr().out


def test_cli_privacy_rejection_exit_code(tmp_path: Path, capsys) -> None:
    out = tmp_path / "sample"
    main(["generar-mock", "--salida", str(out), "--referencias", "100"])
    stock = pd.read_csv(out / "stock.csv", sep=";", encoding="cp1252", dtype=str)
    stock["DNI"] = "12345678Z"
    stock.to_csv(out / "stock.csv", sep=";", index=False, encoding="cp1252")
    code = main([
        "analizar", "--programa", "farmatic", "--ventas", str(out / "ventas.csv"),
        "--stock", str(out / "stock.csv"), "--compras", str(out / "compras.csv"), "--farmacia", "X",
    ])
    assert code == EXIT_PRIVACY
    err = capsys.readouterr().err
    assert "privacidad" in err and "12345678Z" not in err


def test_cli_missing_file_exit_code(tmp_path: Path) -> None:
    code = main([
        "analizar", "--programa", "farmatic", "--ventas", str(tmp_path / "a.csv"),
        "--stock", str(tmp_path / "b.csv"), "--compras", str(tmp_path / "c.csv"), "--farmacia", "X",
    ])
    assert code == EXIT_INPUT_ERROR
