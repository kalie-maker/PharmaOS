from __future__ import annotations

import pytest

from engine.sniff import detect_date_format, detect_decimal, detect_encoding, detect_separator, find_header_row


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("Descripción;Código".encode("utf-8"), "utf-8"),
        ("﻿Descripción".encode("utf-8"), "utf-8-sig"),
        ("Descripción 5 €".encode("cp1252"), "cp1252"),
        (b"Descripci\xf3n \x81", "latin-1"),  # 0x81 no existe en cp1252
        (b"plain ascii", "utf-8"),
    ],
)
def test_detect_encoding(data: bytes, expected: str) -> None:
    assert detect_encoding(data) == expected


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["a;b;c", "1,5;2;3", "2,5;3;4"], ";"),
        (["a,b,c", "1.5,2,3", '"x, y",3,4'], ","),
        (["a\tb\tc", "1,5\t2\t3"], "\t"),
        (["Listado de ventas", "", "a;b;c", "1;2;3", "4;5;6"], ";"),
        (["a|b|c", "1|2|3"], "|"),
    ],
)
def test_detect_separator(lines, expected) -> None:
    assert detect_separator(lines) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["1.234,56", "2,5"], (",", ".")),
        (["1,234.56", "2.5"], (".", ",")),
        (["12.5", "3"], (".", "")),
        (["12,5", "3"], (",", ".")),
        (["1.234", "5.678"], (",", ".")),  # ambiguo: decide el valor por defecto
        ([], (",", ".")),
    ],
)
def test_detect_decimal(values, expected) -> None:
    assert detect_decimal(values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["03/02/2026", "15/12/2025"], "%d/%m/%Y"),
        (["03-02-26", "15-12-25"], "%d-%m-%y"),
        (["2026-02-03"], "%Y-%m-%d"),
        (["03.02.2026"], "%d.%m.%Y"),
        (["03/02/2026 10:15:00"], "%d/%m/%Y %H:%M:%S"),
        (["texto", "otro"], None),
    ],
)
def test_detect_date_format(values, expected) -> None:
    assert detect_date_format(values) == expected


def test_find_header_row_skips_titles() -> None:
    rows = [["Informe de ventas"], [], ["Fecha", "Código", "Uds"], ["01/01/2026", "123", "1"]]
    assert find_header_row(rows) == 2


def test_find_header_row_uses_known_labels() -> None:
    rows = [["Farmacia", "Demo", "2026"], ["Fecha", "Código", "Uds"], ["01/01/2026", "1", "2"]]
    assert find_header_row(rows, {"Fecha", "Código"}) == 1
