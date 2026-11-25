from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from engine.config import parse_mapping
from engine.ingest import IngestError, load_all, load_dataset, normalize_code, parse_dates, parse_number
from engine.privacy import PrivacyError
from tests.conftest import write_csv


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", 1234.56),
        ("1.234,56 €", 1234.56),
        ("12,5", 12.5),
        ("12.5", 12.5),  # ya en formato punto (p. ej. Excel)
        ("1.234", 1234.0),
        ("-3", -3.0),
        ("(4,50)", -4.5),
        (7, 7.0),
        (2.25, 2.25),
    ],
)
def test_parse_number_spanish_formats(raw: object, expected: float) -> None:
    assert parse_number(raw, decimal=",", thousands=".") == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", "abc", None])
def test_parse_number_invalid_is_nan(raw: object) -> None:
    assert math.isnan(parse_number(raw))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("654321", "654321"), (" 54321 ", "054321"), (654321.0, "654321"), ("654321.0", "654321"),
     ("65-43-21", "654321"), ("ab12", "AB12"), ("", None), (float("nan"), None)],
)
def test_normalize_code(raw: object, expected: str | None) -> None:
    assert normalize_code(raw) == expected


def test_parse_dates_with_format_and_fallback() -> None:
    parsed = parse_dates(pd.Series(["03/02/2026", "2026-02-04", "basura", None]), "%d/%m/%Y")
    assert parsed.iloc[0] == pd.Timestamp("2026-02-03")
    assert parsed.iloc[1] == pd.Timestamp("2026-02-04")
    assert parsed.iloc[2:].isna().all()


def test_load_mock_with_farmatic_mapping(small_mock_paths: dict[str, Path], farmatic, thresholds) -> None:
    results = load_all(small_mock_paths, farmatic, thresholds)
    sales, stock, purchases = results["ventas"].data, results["stock"].data, results["compras"].data

    assert list(sales.columns) == ["fecha", "codigo_nacional", "descripcion", "laboratorio", "familia",
                                   "unidades", "importe_venta_sin_iva", "coste_unitario"]
    assert pd.api.types.is_datetime64_any_dtype(sales["fecha"])
    assert pd.api.types.is_float_dtype(sales["importe_venta_sin_iva"])
    assert sales["codigo_nacional"].str.fullmatch(r"\d{6}").all()
    assert set(stock["familia"]) <= {"medicamento_receta", "otc", "dermocosmetica", "nutricion",
                                     "higiene", "ortopedia", "solares"}
    assert stock["fecha_caducidad"].notna().any() and stock["fecha_caducidad"].isna().any()
    assert (purchases["coste_total"] > 0).all()
    assert all(not r.warnings for r in results.values())


def test_cp1252_file_is_decoded(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({"Código": ["654321"], "Descripción": ["Crema ácido hialurónico"],
                       "Stock Actual": ["3"], "P.Coste": ["12,40"]})
    path = write_csv(tmp_path / "stock.csv", df, encoding="cp1252")
    result = load_dataset(path, "stock", farmatic)
    assert result.data.loc[0, "descripcion"] == "Crema ácido hialurónico"
    assert result.data.loc[0, "coste_unitario"] == pytest.approx(12.40)
    # Columnas opcionales ausentes se crean vacías.
    assert result.data["fecha_caducidad"].isna().all()
    assert result.data["familia"].isna().all()


def test_header_aliases_are_tolerant(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({"CODIGO ": ["1"], "existencias": ["2"], "precio coste": ["1,5"], "Extra": ["x"]})
    result = load_dataset(write_csv(tmp_path / "s.csv", df), "stock", farmatic)
    assert result.data.loc[0, "codigo_nacional"] == "000001"
    assert result.ignored_columns == ["Extra"]


def test_missing_required_column_explains(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({"Código": ["654321"], "Stock Actual": ["3"]})
    with pytest.raises(IngestError) as info:
        load_dataset(write_csv(tmp_path / "s.csv", df), "stock", farmatic)
    msg = str(info.value)
    assert "coste_unitario" in msg and "P.Coste" in msg and "config/mappings" in msg


def test_rows_without_keys_are_dropped_with_warning(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({
        "Fecha": ["01/10/2026", "", "03/10/2026"],
        "Código": ["654321", "654322", ""],
        "Unidades": ["1", "2", "3"],
        "Importe s/IVA": ["10,00", "x", "5"],
    })
    result = load_dataset(write_csv(tmp_path / "v.csv", df), "ventas", farmatic)
    assert len(result.data) == 1
    assert result.dropped_rows == 2
    assert any("descartada" in w for w in result.warnings)


def test_unknown_family_goes_to_otros_with_warning(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({"Código": ["1", "2"], "Stock Actual": ["1", "1"], "P.Coste": ["1", "1"],
                       "Familia": ["Veterinaria", "SOLARES"]})
    result = load_dataset(write_csv(tmp_path / "s.csv", df), "stock", farmatic)
    assert list(result.data["familia"]) == ["otros", "solares"]
    assert any("Veterinaria" in w for w in result.warnings)


def test_duplicate_stock_codes_warn(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({"Código": ["1", "1"], "Stock Actual": ["1", "2"], "P.Coste": ["1", "1"]})
    result = load_dataset(write_csv(tmp_path / "s.csv", df), "stock", farmatic)
    assert len(result.data) == 2  # se conservan; la consolidación es de métricas
    assert any("repetido" in w for w in result.warnings)


def test_xlsx_is_supported(tmp_path: Path, farmatic) -> None:
    df = pd.DataFrame({"Código": [654321, 12345], "Stock Actual": [3, 0], "P.Coste": [2.5, 1.0],
                       "Caducidad": [pd.Timestamp("2027-01-31"), None]})
    path = tmp_path / "stock.xlsx"
    df.to_excel(path, index=False)
    data = load_dataset(path, "stock", farmatic).data
    assert list(data["codigo_nacional"]) == ["654321", "012345"]
    assert data.loc[0, "fecha_caducidad"] == pd.Timestamp("2027-01-31")


def test_privacy_rejects_before_mapping(tmp_path: Path, farmatic) -> None:
    # "Nombre Paciente" no está en el mapeo, pero el fichero se rechaza igualmente.
    df = pd.DataFrame({"Código": ["654321"], "Stock Actual": ["3"], "P.Coste": ["1"],
                       "Nombre Paciente": ["Ana"]})
    with pytest.raises(PrivacyError):
        load_dataset(write_csv(tmp_path / "s.csv", df), "stock", farmatic)


def test_nixfarma_mapping(tmp_path: Path, nixfarma) -> None:
    df = pd.DataFrame({
        "FECHA_VENTA": ["05/11/2026"], "COD_NACIONAL": ["700100"], "DESCRIPCION": ["Fotoprotector"],
        "FAMILIA": ["Fotoprotección"], "CANTIDAD": ["2"], "IMP_NETO": ["30,50"], "PRECIO_COSTE": ["9,1"],
    })
    data = load_dataset(write_csv(tmp_path / "v.csv", df), "ventas", nixfarma).data
    row = data.iloc[0]
    assert row["familia"] == "solares"
    assert row["importe_venta_sin_iva"] == pytest.approx(30.5)
    assert pd.isna(row["laboratorio"])


def test_unknown_dataset_raises(tmp_path: Path, farmatic) -> None:
    with pytest.raises(IngestError):
        load_dataset(tmp_path / "x.csv", "pacientes", farmatic)


def test_missing_file_raises(tmp_path: Path, farmatic) -> None:
    with pytest.raises(IngestError):
        load_dataset(tmp_path / "noexiste.csv", "stock", farmatic)


def test_mapping_validation_rejects_unknown_canonical() -> None:
    from engine.config import ConfigError

    with pytest.raises(ConfigError):
        parse_mapping({"ficheros": {"ventas": {"nombre_paciente": ["X"]}}})
