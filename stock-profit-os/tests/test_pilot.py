from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from engine.cli import EXIT_OK, EXIT_PRIVACY, EXIT_STOPPED, main
from engine.mock.generate import MockConfig
from engine.mock.scenario import generate_week3_scenario
from engine.pilot import STOP_FILES, STOP_MAPPING, STOP_PRIVACY, STOP_QUALITY, PilotStop, run_pilot
from tests import dirty

MAPPINGS = Path(__file__).resolve().parent.parent / "config" / "mappings"
TODAY = date(2026, 11, 25)


@pytest.fixture
def mappings_dir(tmp_path: Path) -> Path:
    target = tmp_path / "mappings"
    shutil.copytree(MAPPINGS, target)
    return target


@pytest.fixture(scope="module")
def demo(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("pilot_demo")
    generate_week3_scenario(out, MockConfig(n_refs=400, seed=9))
    return out


def _quiet(*_: object) -> None:
    pass


def _copy(src: Path, dst: Path, names: dict[str, str] | None = None) -> Path:
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        shutil.copy(f, dst / (names or {}).get(f.name, f.name))
    return dst


def test_full_flow_and_automatic_comparison(demo: Path, tmp_path: Path, mappings_dir: Path) -> None:
    out = tmp_path / "output"
    first = run_pilot(demo / "semana0", "farmatic", "Farmacia Demo", out, "demo", mappings_dir, today=TODAY,
                      log=_quiet)
    assert first.out_dir == out / "demo" / "2026-10-30"
    assert {p.name for p in first.out_dir.iterdir()} == {"informe.html", "informe.md", "informe.json", "calidad.md"}
    assert first.comparison is None
    second = run_pilot(demo / "semana3", "farmatic", "Farmacia Demo", out, "demo", mappings_dir, today=TODAY,
                       log=_quiet)
    assert second.comparison is not None and second.comparison["stock_liberado_eur"] > 0
    assert (second.out_dir / "comparacion_2026-10-30.md").exists()


def test_files_identified_by_content(demo: Path, tmp_path: Path, mappings_dir: Path) -> None:
    folder = _copy(demo / "semana0", tmp_path / "in",
                   {"ventas.csv": "export1.csv", "stock.csv": "export2.csv", "compras.csv": "export3.csv"})
    out = run_pilot(folder, "farmatic", "X", tmp_path / "o", mappings_dir=mappings_dir, today=TODAY, log=_quiet)
    assert out.files["stock"].name == "export2.csv"
    assert out.out_dir.parent.name == "in"  # id por defecto = carpeta


def test_missing_file_stops(demo: Path, tmp_path: Path, mappings_dir: Path) -> None:
    folder = _copy(demo / "semana0", tmp_path / "in")
    (folder / "compras.csv").unlink()
    with pytest.raises(PilotStop) as info:
        run_pilot(folder, "farmatic", "X", tmp_path / "o", mappings_dir=mappings_dir, log=_quiet)
    assert info.value.reason == STOP_FILES and "compras" in str(info.value)


def test_new_program_creates_draft_and_stops(demo: Path, tmp_path: Path, mappings_dir: Path) -> None:
    with pytest.raises(PilotStop) as info:
        run_pilot(demo / "semana0", "farmacia_9", "X", tmp_path / "o", mappings_dir=mappings_dir, log=_quiet)
    assert info.value.reason == STOP_MAPPING and "borrador" in str(info.value)
    assert (mappings_dir / "farmacia_9.yaml").exists()
    # Sigue parado mientras sea borrador.
    with pytest.raises(PilotStop, match="borrador"):
        run_pilot(demo / "semana0", "farmacia_9", "X", tmp_path / "o", mappings_dir=mappings_dir, log=_quiet)
    # Revisado -> funciona.
    path = mappings_dir / "farmacia_9.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("borrador: true", "borrador: false"), encoding="utf-8")
    run_pilot(demo / "semana0", "farmacia_9", "X", tmp_path / "o", mappings_dir=mappings_dir, today=TODAY,
              log=_quiet)


def test_incomplete_mapping_stops(demo: Path, tmp_path: Path, mappings_dir: Path) -> None:
    text = (mappings_dir / "farmatic.yaml").read_text(encoding="utf-8")
    (mappings_dir / "roto.yaml").write_text(
        text.replace('coste_unitario: ["P.Coste", "PVC", "Precio Coste"]', 'coste_unitario: ["No existe"]'),
        encoding="utf-8")
    with pytest.raises(PilotStop) as info:
        run_pilot(demo / "semana0", "roto", "X", tmp_path / "o", mappings_dir=mappings_dir, log=_quiet)
    assert info.value.reason == STOP_MAPPING and "coste_unitario" in str(info.value)


def test_low_quality_stops_unless_forced(small_mock, tmp_path: Path, mappings_dir: Path) -> None:
    folder = tmp_path / "bad"
    dirty.degrade_mock(small_mock).write(folder)
    with pytest.raises(PilotStop) as info:
        run_pilot(folder, "farmatic", "X", tmp_path / "o", mappings_dir=mappings_dir, today=TODAY, log=_quiet)
    assert info.value.reason == STOP_QUALITY
    assert not list((tmp_path / "o").rglob("informe.html"))
    forced = run_pilot(folder, "farmatic", "X", tmp_path / "o", mappings_dir=mappings_dir, today=TODAY,
                       ignore_quality=True, log=_quiet)
    assert "Calidad de datos baja" in forced.reports["html"].read_text(encoding="utf-8")


def test_personal_data_stops_before_analysis(demo: Path, tmp_path: Path, mappings_dir: Path) -> None:
    folder = _copy(demo / "semana0", tmp_path / "in")
    sales = pd.read_csv(folder / "ventas.csv", sep=";", encoding="cp1252", dtype=str)
    sales["CIP"] = "ABCD1234567890"
    sales.to_csv(folder / "ventas.csv", sep=";", index=False, encoding="cp1252")
    with pytest.raises(PilotStop) as info:
        run_pilot(folder, "farmatic", "X", tmp_path / "o", mappings_dir=mappings_dir, log=_quiet)
    assert info.value.reason == STOP_PRIVACY
    assert "CIP" in str(info.value) and "ABCD" not in str(info.value)
    assert not (tmp_path / "o").exists()


def test_cli_pilot_exit_codes(demo: Path, tmp_path: Path, mappings_dir: Path, capsys) -> None:
    base = ["piloto", "--programa", "farmatic", "--nombre", "Farmacia Demo", "--mapeos", str(mappings_dir),
            "--salida", str(tmp_path / "o"), "--no-interactivo"]
    assert main([*base, "--carpeta", str(demo / "semana0"), "--id", "demo"]) == EXIT_OK
    assert "Revisa a mano" in capsys.readouterr().out
    bad = _copy(demo / "semana0", tmp_path / "pac")
    stock = pd.read_csv(bad / "stock.csv", sep=";", encoding="cp1252", dtype=str)
    stock["Teléfono"] = "612345678"
    stock.to_csv(bad / "stock.csv", sep=";", index=False, encoding="cp1252")
    assert main([*base, "--carpeta", str(bad)]) == EXIT_PRIVACY
    assert main([*base, "--carpeta", str(tmp_path / "vacia_no_existe")]) == EXIT_STOPPED
    assert "PARADO" in capsys.readouterr().err


def test_cli_generate_scenario(tmp_path: Path, capsys) -> None:
    assert main(["generar-mock", "--escenario", "semana3", "--salida", str(tmp_path), "--referencias", "150"]) == 0
    assert (tmp_path / "semana3" / "stock.csv").exists()
    assert "LEEME.md" in capsys.readouterr().out


def test_cli_scale_requires_anonymize(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["analizar", "--programa", "farmatic", "--ventas", "a", "--stock", "b", "--compras", "c",
              "--farmacia", "X", "--escalar-cifras"])


def test_cli_compare_anonymized(demo: Path, tmp_path: Path, mappings_dir: Path, capsys) -> None:
    out = tmp_path / "o"
    for week in ("semana0", "semana3"):
        run_pilot(demo / week, "farmatic", "Farmacia Real", out, "demo", mappings_dir, today=TODAY, log=_quiet)
    capsys.readouterr()
    labs = set(pd.read_csv(demo / "semana0" / "stock.csv", sep=";", encoding="cp1252")["Laboratorio"])
    code = main(["comparar", "--antes", str(out / "demo" / "2026-10-30" / "informe.json"),
                 "--despues", str(out / "demo" / "2026-11-20" / "informe.json"), "--anonimizar", "--escalar-cifras"])
    assert code == EXIT_OK
    text = capsys.readouterr().out
    assert "Farmacia Demo" in text and "Farmacia Real" not in text
    assert not any(lab in text for lab in labs)
