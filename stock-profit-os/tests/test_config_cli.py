from __future__ import annotations

from pathlib import Path

import json

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
    out_text = capsys.readouterr().out
    assert "análisis completado" in out_text
    assert list((tmp_path / "output").glob("informe_*.html"))


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


# ---------------------------------------------------------------------------
# Fase 4: CLI
# ---------------------------------------------------------------------------


def _analyze_args(out: Path, *extra: str) -> list[str]:
    return ["analizar", "--programa", "farmatic", "--ventas", str(out / "ventas.csv"),
            "--stock", str(out / "stock.csv"), "--compras", str(out / "compras.csv"),
            "--farmacia", "Farmacia Real Calle Mayor", *extra]


def test_cli_anonymize_removes_pharmacy_name(tmp_path: Path, small_mock_paths) -> None:
    sample = small_mock_paths["ventas"].parent
    report_dir = tmp_path / "out"
    assert main(_analyze_args(sample, "--salida", str(report_dir), "--prefijo", "ejemplo", "--anonimizar",
                              "--no-interactivo")) == EXIT_OK
    for path in report_dir.glob("ejemplo.*"):
        text = path.read_text(encoding="utf-8")
        assert "Calle Mayor" not in text
        assert "Farmacia Demo" in text
    data = json.loads((report_dir / "ejemplo.json").read_text(encoding="utf-8"))
    assert data["anonimizado"] is True


def test_cli_quality_only(tmp_path: Path, small_mock_paths, capsys) -> None:
    sample = small_mock_paths["ventas"].parent
    assert main(_analyze_args(sample, "--solo-calidad", "--salida", str(tmp_path))) == EXIT_OK
    assert "Calidad de datos" in capsys.readouterr().out
    assert not list(tmp_path.glob("*.html"))


def test_cli_inspect_writes_draft(tmp_path: Path, small_mock_paths, capsys) -> None:
    mappings = tmp_path / "mappings"
    for name, path in small_mock_paths.items():
        code = main(["inspeccionar", "--fichero", str(path), "--nombre", "piloto", "--mapeos", str(mappings),
                     "--no-interactivo"])
        assert code == EXIT_OK
    out = capsys.readouterr().out
    assert "Tipo de fichero: compras" in out and "Borrador guardado" in out
    sample = small_mock_paths["ventas"].parent
    args = _analyze_args(sample, "--salida", str(tmp_path / "r"), "--mapeos", str(mappings))
    args[2] = "piloto"
    assert main(args) == EXIT_OK
    assert "BORRADOR" in capsys.readouterr().err


def test_cli_inspect_no_save_and_errors(tmp_path: Path, small_mock_paths) -> None:
    mappings = tmp_path / "m"
    assert main(["inspeccionar", "--fichero", str(small_mock_paths["stock"]), "--no-guardar",
                 "--mapeos", str(mappings)]) == EXIT_OK
    assert not mappings.exists() or not list(mappings.glob("*.yaml"))
    assert main(["inspeccionar", "--fichero", str(tmp_path / "nope.csv")]) == EXIT_INPUT_ERROR


def test_cli_compare(tmp_path: Path, small_mock, capsys) -> None:
    from datetime import date as _date

    from engine.config import load_mapping as _lm, load_thresholds as _lt
    from engine.pipeline import run_analysis
    from engine.report import write_reports
    from tests import dirty

    t, m = _lt(), _lm("farmatic")
    r0 = run_analysis(small_mock.write(tmp_path / "s0"), m, t, "Demo", today=_date(2027, 1, 1)).results
    dead = next(a for a in r0["acciones"] + r0["anexo_acciones"] if a["type"] == "devolver_sin_movimiento")
    after = dirty.simulate_after(small_mock, 21, dead["affected_codes"], [])
    r3 = run_analysis(after.write(tmp_path / "s3"), m, t, "Demo", today=_date(2027, 1, 1)).results
    p0 = write_reports(r0, tmp_path, "semana0")["json"]
    p3 = write_reports(r3, tmp_path, "semana3")["json"]
    code = main(["comparar", "--antes", str(p0), "--despues", str(p3), "--salida", str(tmp_path / "cmp")])
    assert code == EXIT_OK
    out = capsys.readouterr().out
    assert "Parece ejecutada" in out
    assert list((tmp_path / "cmp").glob("comparacion_*.md"))
    assert main(["comparar", "--antes", str(p3), "--despues", str(p0)]) == EXIT_INPUT_ERROR


def test_cli_ambiguous_excel_without_tty_fails_with_hint(tmp_path: Path, small_mock_paths, capsys) -> None:
    from tests import dirty

    sample = small_mock_paths["ventas"].parent
    xlsx = dirty.multi_sheet_xlsx(tmp_path / "ventas.xlsx", ambiguous=True)
    args = _analyze_args(sample, "--no-interactivo", "--salida", str(tmp_path / "r"))
    args[args.index("--ventas") + 1] = str(xlsx)
    assert main(args) == EXIT_INPUT_ERROR
    assert "--hoja-ventas" in capsys.readouterr().err
