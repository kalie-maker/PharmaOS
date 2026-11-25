from __future__ import annotations

import pandas as pd
import pytest

from engine.privacy import PrivacyError, check_content, check_headers, validate

SAFE_HEADERS = [
    "Fecha", "Código", "Descripción", "Laboratorio", "Familia", "Unidades", "Importe s/IVA",
    "P.Coste", "Stock Actual", "PVP", "Caducidad", "Fecha Albarán", "Unidades Recibidas",
    "Importe Coste", "COD_NACIONAL", "IMP_NETO", "PRECIO_COSTE", "Stock mínimo", "Margen",
]


@pytest.mark.parametrize("header", SAFE_HEADERS)
def test_product_headers_are_accepted(header: str) -> None:
    assert check_headers([header]) == []


@pytest.mark.parametrize(
    ("header", "category"),
    [
        ("Nombre Paciente", "paciente"),
        ("PACIENTE", "paciente"),
        ("Apellidos", "paciente"),
        ("Cód. Cliente", "paciente"),
        ("DNI", "identidad"),
        ("N.I.E.", "identidad"),
        ("NIF/CIF", "identidad"),
        ("CIP", "tarjeta_sanitaria"),
        ("CIP Autonómico", "tarjeta_sanitaria"),
        ("Tarjeta Sanitaria", "tarjeta_sanitaria"),
        ("Nº Seguridad Social", "tarjeta_sanitaria"),
        ("Nº Receta", "receta"),
        ("num_receta", "receta"),
        ("Teléfono", "telefono"),
        ("Tlf. móvil", "telefono"),
        ("E-mail", "email"),
        ("Correo electrónico", "email"),
        ("Dirección", "direccion"),
        ("Código Postal", "direccion"),
        ("Fecha de nacimiento", "datos_personales"),
        ("Diagnóstico", "datos_sanitarios"),
    ],
)
def test_personal_headers_are_detected(header: str, category: str) -> None:
    findings = check_headers([header])
    assert len(findings) == 1
    assert findings[0].category == category
    assert findings[0].source == "cabecera"


def test_content_detects_dni_nie_email_and_phone() -> None:
    df = pd.DataFrame(
        {
            "Ref": ["12345678Z", "X1234567L", "ok", "ok"],
            "Contacto": ["a@b.es", None, "x", "y"],
            "Otro": ["612345678", "+34 912 345 678", "699111222", "600000000"],
            "Descripción": ["Ibuprofeno 400 mg", "Crema 50 ml", "Gel", "Solar SPF50"],
        }
    )
    found = {f.column: f.category for f in check_content(df)}
    assert found == {"Ref": "dni_nie", "Contacto": "email", "Otro": "telefono"}


def test_content_ignores_product_codes_and_amounts() -> None:
    df = pd.DataFrame(
        {
            "Código": ["654321", "700001", "8470001234567"],
            "Importe": ["612,50", "1.234,56", "7"],
            "Fecha": ["01/02/2026", "02/02/2026", "03/02/2026"],
        }
    )
    assert check_content(df) == []


def test_phone_below_ratio_is_not_flagged() -> None:
    df = pd.DataFrame({"Notas": ["612345678"] + ["texto"] * 99})
    assert check_content(df, phone_min_ratio=0.2) == []


def test_validate_raises_with_spanish_explanation_and_no_values() -> None:
    df = pd.DataFrame({"Código": ["654321"], "Nombre Paciente": ["Juana Pérez"], "Notas": ["12345678Z"]})
    with pytest.raises(PrivacyError) as info:
        validate(df, label="ventas (ventas.csv)")
    message = str(info.value)
    assert "rechazado por privacidad" in message
    assert "Nombre Paciente" in message and "Notas" in message
    assert "Juana" not in message and "12345678Z" not in message
    assert "vuelve a exportar" in message


def test_validate_passes_clean_frame() -> None:
    validate(pd.DataFrame({"Código": ["654321"], "Unidades": ["2"]}), label="ok")
