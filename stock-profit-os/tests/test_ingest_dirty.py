from __future__ import annotations

from pathlib import Path

import pytest

from engine.ingest import SheetChoiceError, load_dataset
from tests import dirty


def _check_sales(result) -> None:
    data = result.data
    assert len(data) == 3
    assert list(data["codigo_nacional"]) == ["654321", "700100", "700100"]
    assert data.loc[0, "importe_venta_sin_iva"] == pytest.approx(1234.50)
    assert data.loc[0, "coste_unitario"] == pytest.approx(300.25)
    assert data.loc[0, "descripcion"] == "Crema hidratante, 50 ml"
    assert data.loc[0, "laboratorio"] == "Lab Ñandú"
    assert str(data.loc[0, "fecha"].date()) == "2026-02-03"
    assert data.loc[1, "familia"] == "medicamento_receta"


def test_latin1_tab_with_titles_and_totals(tmp_path: Path, farmatic) -> None:
    result = load_dataset(dirty.latin1_tab_with_title(tmp_path / "v.txt"), "ventas", farmatic)
    _check_sales(result)
    assert result.format["codificacion"] in {"cp1252", "latin-1"}
    assert result.format["separador"] == "tabulador"
    assert result.format["fila_cabecera"] == 4
    assert result.dropped_rows == 1  # la fila TOTAL no tiene fecha válida
    assert any("descartada" in w for w in result.warnings)


def test_utf8_bom_comma_separated_dot_decimal(tmp_path: Path, farmatic) -> None:
    result = load_dataset(dirty.utf8_bom_comma_dot_decimal(tmp_path / "v.csv"), "ventas", farmatic)
    _check_sales(result)
    assert result.format["codificacion"] == "utf-8-sig"
    assert result.format["separador"] == "coma"
    assert result.format["decimal"]["importe_venta_sin_iva"] == "punto"


def test_cp1252_short_dates_and_euro_sign(tmp_path: Path, farmatic) -> None:
    result = load_dataset(dirty.cp1252_short_dates(tmp_path / "v.csv"), "ventas", farmatic)
    _check_sales(result)
    assert result.format["codificacion"] == "cp1252"
    assert result.format["formato_fecha"]["fecha"] == "%d-%m-%y"


def test_xlsx_picks_data_sheet_and_header_row(tmp_path: Path, farmatic) -> None:
    result = load_dataset(dirty.multi_sheet_xlsx(tmp_path / "v.xlsx"), "ventas", farmatic)
    _check_sales(result)
    assert result.format["hoja"] == "Datos"
    assert result.format["fila_cabecera"] == 3


def test_xlsx_ambiguous_sheets_ask_or_fail(tmp_path: Path, farmatic) -> None:
    path = dirty.multi_sheet_xlsx(tmp_path / "v.xlsx", ambiguous=True)
    with pytest.raises(SheetChoiceError) as info:
        load_dataset(path, "ventas", farmatic)
    assert {c.name for c in info.value.candidates} >= {"Datos", "Datos 2025"}
    assert "--hoja-ventas" in str(info.value)

    asked = []

    def chooser(p, candidates):
        asked.append([c.name for c in candidates])
        return "Datos 2025"

    result = load_dataset(path, "ventas", farmatic, chooser=chooser)
    assert asked and result.format["hoja"] == "Datos 2025"
    assert load_dataset(path, "ventas", farmatic, sheet="Datos").format["hoja"] == "Datos"


def test_xlsx_unknown_sheet(tmp_path: Path, farmatic) -> None:
    from engine.ingest import IngestError

    with pytest.raises(IngestError, match="no tiene la hoja"):
        load_dataset(dirty.multi_sheet_xlsx(tmp_path / "v.xlsx"), "ventas", farmatic, sheet="Nope")


def test_legacy_xls_is_rejected_clearly(tmp_path: Path, farmatic) -> None:
    from engine.ingest import IngestError

    path = tmp_path / "v.xls"
    path.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(IngestError, match="xlsx"):
        load_dataset(path, "ventas", farmatic)


def test_inconsistent_lines_are_reported(tmp_path: Path, farmatic) -> None:
    lines = [";".join(dirty.SALES_HEADER)] + [";".join(r) for r in dirty.SALES_ROWS]
    lines.append("01/03/2026;111111;X;Y;Z;1;2;3;columna;de;mas")
    result = load_dataset(dirty.write_text(tmp_path / "v.csv", lines, "utf-8"), "ventas", farmatic)
    assert len(result.data) == 3
    assert any("ignorada" in w for w in result.warnings)
