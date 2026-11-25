from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine.config import ConfigError, load_mapping
from engine.ingest import load_dataset
from engine.inspection import InspectError, inspect_file, name_score, write_draft
from tests import dirty
from tests.conftest import write_csv

MAPPINGS = Path(__file__).resolve().parent.parent / "config" / "mappings"


@pytest.fixture
def mappings_dir(tmp_path: Path) -> Path:
    target = tmp_path / "mappings"
    target.mkdir()
    for f in MAPPINGS.glob("*.yaml"):
        (target / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_name_score() -> None:
    assert name_score("Código", {"codigo"}) == 1.0
    assert name_score("Cód. Nacional", {"cod nacional"}) == 1.0
    assert name_score("Unidades vendidas hoy", {"unidades vendidas"}) == 0.9
    assert name_score("Zzz", {"fecha"}) < 0.5


def test_inspect_unknown_program_export(tmp_path: Path, mappings_dir: Path) -> None:
    df = pd.DataFrame({
        "Día": ["01/10/2026", "02/10/2026"],
        "Cod. Artículo": ["654321", "700100"],
        "Denominación": ["Crema", "Gel"],
        "Proveedor": ["Lab A", "Lab B"],
        "Sección": ["Dermocosmética", "Veterinaria"],
        "Cant.": ["1", "2"],
        "Venta Neta": ["10,50", "3,20"],
        "Observaciones": ["", ""],
    })
    path = write_csv(tmp_path / "ventas_octubre.csv", df, encoding="cp1252")
    ins = inspect_file(path, mappings_dir=mappings_dir)
    assert ins.dataset == "ventas"
    proposed = {m.canonical: m.column for m in ins.matches}
    assert proposed["fecha"] == "Día"
    assert proposed["codigo_nacional"] == "Cod. Artículo"
    assert proposed["descripcion"] == "Denominación"
    assert proposed["laboratorio"] == "Proveedor"
    assert proposed["familia"] == "Sección"
    assert proposed["unidades"] == "Cant."
    assert proposed["importe_venta_sin_iva"] == "Venta Neta"
    assert ins.missing_required == []
    assert ins.families == {"Dermocosmética": "dermocosmetica", "Veterinaria": None}
    assert "Observaciones" not in {c.name for c in ins.columns}  # columna vacía descartada


def test_inspect_flags_personal_columns_without_values(tmp_path: Path, mappings_dir: Path) -> None:
    df = pd.DataFrame({"Código": ["654321"], "Stock": ["3"], "P.Coste": ["1"],
                       "Nombre Paciente": ["Ana Ruiz"], "Notas": ["ana@correo.es"]})
    ins = inspect_file(write_csv(tmp_path / "stock.csv", df), mappings_dir=mappings_dir)
    flagged = {f.column for f in ins.privacy_findings}
    assert flagged == {"Nombre Paciente", "Notas"}
    assert all(m.column not in flagged for m in ins.matches)
    path = write_draft(ins, "piloto", mappings_dir)
    text = path.read_text(encoding="utf-8")
    assert "Ana" not in text and "correo" not in text and "Paciente" not in text


def test_draft_is_valid_and_merges_datasets(tmp_path: Path, mappings_dir: Path, small_mock_paths) -> None:
    for dataset, path in small_mock_paths.items():
        ins = inspect_file(path, mappings_dir=mappings_dir)
        assert ins.dataset == dataset
        write_draft(ins, "piloto", mappings_dir)
    raw = yaml.safe_load((mappings_dir / "piloto.yaml").read_text(encoding="utf-8"))
    assert raw["borrador"] is True
    assert set(raw["ficheros"]) == {"ventas", "stock", "compras"}
    mapping = load_mapping("piloto", mappings_dir)
    assert mapping.draft
    result = load_dataset(small_mock_paths["ventas"], "ventas", mapping)
    assert len(result.data) > 0
    assert set(result.data["familia"]) - {"otros"}


def test_incomplete_draft_explains_next_step(tmp_path: Path, mappings_dir: Path, small_mock_paths) -> None:
    write_draft(inspect_file(small_mock_paths["ventas"], mappings_dir=mappings_dir), "solo_ventas", mappings_dir)
    with pytest.raises(ConfigError, match="inspeccionar"):
        load_mapping("solo_ventas", mappings_dir)


def test_missing_required_is_commented_for_review(tmp_path: Path, mappings_dir: Path) -> None:
    df = pd.DataFrame({"Código": ["654321"], "Existencias": ["3"]})
    ins = inspect_file(write_csv(tmp_path / "s.csv", df), dataset="stock", mappings_dir=mappings_dir)
    assert ins.missing_required == ["coste_unitario"]
    text = write_draft(ins, "x", mappings_dir).read_text(encoding="utf-8")
    assert "# coste_unitario: []  # REVISAR: obligatoria" in text


def test_does_not_overwrite_reviewed_mapping(tmp_path: Path, mappings_dir: Path, small_mock_paths) -> None:
    ins = inspect_file(small_mock_paths["stock"], mappings_dir=mappings_dir)
    with pytest.raises(InspectError, match="no es un borrador"):
        write_draft(ins, "farmatic", mappings_dir)
    write_draft(ins, "farmatic", mappings_dir, force=True)


def test_invalid_draft_name(tmp_path: Path, mappings_dir: Path, small_mock_paths) -> None:
    ins = inspect_file(small_mock_paths["stock"], mappings_dir=mappings_dir)
    with pytest.raises(InspectError):
        write_draft(ins, "../fuera", mappings_dir)


def test_inspect_xlsx_multi_sheet(tmp_path: Path, mappings_dir: Path) -> None:
    ins = inspect_file(dirty.multi_sheet_xlsx(tmp_path / "ventas.xlsx"), mappings_dir=mappings_dir)
    assert ins.format["hoja"] == "Datos"
    assert ins.dataset == "ventas"
    assert {m.canonical: m.column for m in ins.matches}["fecha"] == "Fecha"


def test_inspect_dirty_latin1(tmp_path: Path, mappings_dir: Path) -> None:
    ins = inspect_file(dirty.latin1_tab_with_title(tmp_path / "export.txt"), mappings_dir=mappings_dir)
    assert ins.dataset == "ventas"
    assert ins.format["fila_cabecera"] == 4
    assert ins.read_options["separador"] == "\t"
    assert ins.read_options["decimal"] == ","
