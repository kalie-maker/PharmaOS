"""Validador de privacidad: rechaza ficheros con datos personales o sanitarios.

Se aplica sobre las columnas ORIGINALES del fichero, antes del mapeo, para que
una columna personal no pase desapercibida aunque el mapeo la ignore.

Nunca se incluyen valores de celdas en los mensajes: solo el nombre de la
columna, la categoría y el número de coincidencias.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from engine.config import normalize_label


@dataclass(frozen=True)
class HeaderRule:
    category: str
    pattern: re.Pattern[str]
    reason: str


def _rule(category: str, pattern: str, reason: str) -> HeaderRule:
    # Se evalúa sobre el encabezado normalizado (minúsculas, sin tildes ni puntuación).
    return HeaderRule(category, re.compile(pattern), reason)


HEADER_RULES: tuple[HeaderRule, ...] = (
    _rule(
        "identidad",
        r"\b(dni|nie|nif|d n i|n i e|n i f|pasaporte|documento (de )?identidad|doc identidad)\b",
        "parece un documento de identidad (DNI/NIE/NIF/pasaporte)",
    ),
    _rule(
        "tarjeta_sanitaria",
        r"\b(cip|cipa|cip sns|cip autonomico|sip|tsi|tarjeta sanitaria|tarjeta individual sanitaria"
        r"|seguridad social|nss|naf|n afiliacion|numero afiliacion)\b",
        "parece un identificador sanitario (CIP, tarjeta sanitaria o nº de la Seguridad Social)",
    ),
    _rule(
        "receta",
        r"\b(recetas?|n receta|num receta|numero receta|id receta|codigo receta|prescripcion)\b",
        "parece un número o identificador de receta, ligado a un paciente",
    ),
    _rule(
        "paciente",
        r"\b(pacientes?|apellidos?|clientes?|nombre (del |de la )?(paciente|cliente|titular|usuario"
        r"|persona|comprador))\b",
        "identifica a una persona (paciente o cliente)",
    ),
    _rule(
        "datos_personales",
        r"\b(fecha (de )?nacimiento|f nacimiento|f nac|nacimiento|edad|sexo|genero)\b",
        "contiene datos personales (nacimiento, edad o sexo)",
    ),
    _rule(
        "datos_sanitarios",
        r"\b(diagnostico|patologia|enfermedad|alergias?|historia clinica|hce|tratamiento cronico)\b",
        "contiene datos de salud de una persona",
    ),
    _rule(
        "telefono",
        r"\b(tel|tlf|tfno|telefono|telefonos|movil|celular|phone|fax)\b",
        "parece un número de teléfono",
    ),
    _rule(
        "email",
        r"\b(e mail|email|mail|correo|correo electronico)\b",
        "parece una dirección de correo electrónico",
    ),
    _rule(
        "direccion",
        r"\b(direccion|domicilio|calle|codigo postal|poblacion|localidad)\b",
        "parece una dirección postal",
    ),
)

_DNI = re.compile(r"\d{8}[ -]?[A-HJ-NP-TV-Z]", re.IGNORECASE)
_NIE = re.compile(r"[XYZ][ -]?\d{7}[ -]?[A-HJ-NP-TV-Z]", re.IGNORECASE)
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(\+34|0034)?[ -]?[6789]\d{2}[ -]?\d{3}[ -]?\d{3}")


@dataclass(frozen=True)
class PrivacyFinding:
    column: str
    category: str
    reason: str
    source: Literal["cabecera", "contenido"]
    matches: int = 0

    def describe(self) -> str:
        if self.source == "cabecera":
            return f"- Columna '{self.column}': {self.reason}."
        return (
            f"- Columna '{self.column}': {self.matches} celda(s) con formato de "
            f"{self.category.replace('_', ' ')} ({self.reason})."
        )


class PrivacyError(Exception):
    """El fichero contiene (o parece contener) datos personales o sanitarios."""

    def __init__(self, label: str, findings: list[PrivacyFinding]):
        self.label = label
        self.findings = findings
        super().__init__(self.message())

    def message(self) -> str:
        lines = [
            f"Fichero rechazado por privacidad: {self.label}",
            "Stock Profit OS no procesa datos de pacientes ni datos personales. Motivos:",
            *(f.describe() for f in self.findings),
            "Qué hacer: vuelve a exportar el fichero sin esas columnas (solo producto, "
            "fechas, unidades e importes). No se ha guardado ni analizado ningún dato.",
        ]
        return "\n".join(lines)


def check_headers(columns: Iterable[object]) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for column in columns:
        normalized = normalize_label(column)
        for rule in HEADER_RULES:
            if rule.pattern.search(normalized):
                findings.append(PrivacyFinding(str(column), rule.category, rule.reason, "cabecera"))
                break
    return findings


def check_content(
    df: pd.DataFrame,
    phone_min_ratio: float = 0.2,
    skip_columns: Iterable[str] = (),
) -> list[PrivacyFinding]:
    """Busca valores con forma de DNI/NIE, email o teléfono en columnas de texto."""
    skip = set(skip_columns)
    findings: list[PrivacyFinding] = []
    for column in df.columns:
        if column in skip:
            continue
        series = df[column]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        values = series.dropna().astype(str).str.strip()
        values = values[values != ""]
        if values.empty:
            continue

        ids = int((values.str.fullmatch(_DNI) | values.str.fullmatch(_NIE)).sum())
        if ids:
            findings.append(
                PrivacyFinding(str(column), "dni_nie", "posible documento de identidad", "contenido", ids)
            )
            continue
        emails = int(values.str.fullmatch(_EMAIL).sum())
        if emails:
            findings.append(
                PrivacyFinding(str(column), "email", "posible correo electrónico", "contenido", emails)
            )
            continue
        phones = int(values.str.fullmatch(_PHONE).sum())
        if phones and phones / len(values) >= phone_min_ratio:
            findings.append(
                PrivacyFinding(str(column), "telefono", "posible número de teléfono", "contenido", phones)
            )
    return findings


def validate(
    df: pd.DataFrame,
    label: str,
    scan_content: bool = True,
    phone_min_ratio: float = 0.2,
) -> None:
    """Lanza PrivacyError si el DataFrame (columnas originales) parece contener datos personales."""
    findings = check_headers(df.columns)
    if scan_content:
        flagged = {f.column for f in findings}
        findings += check_content(df, phone_min_ratio=phone_min_ratio, skip_columns=flagged)
    if findings:
        raise PrivacyError(label, findings)
