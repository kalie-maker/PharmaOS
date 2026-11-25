"""Modelo de datos canónico: columnas, tipos y familias tras el mapeo."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Family(StrEnum):
    """Familias canónicas de producto."""

    PRESCRIPTION = "medicamento_receta"
    OTC = "otc"
    DERMOCOSMETICS = "dermocosmetica"
    NUTRITION = "nutricion"
    HYGIENE = "higiene"
    ORTHOPEDICS = "ortopedia"
    SUNCARE = "solares"
    OTHER = "otros"


FAMILY_LABELS: dict[Family, str] = {
    Family.PRESCRIPTION: "Medicamento con receta",
    Family.OTC: "OTC",
    Family.DERMOCOSMETICS: "Dermocosmética",
    Family.NUTRITION: "Nutrición",
    Family.HYGIENE: "Higiene",
    Family.ORTHOPEDICS: "Ortopedia",
    Family.SUNCARE: "Solares",
    Family.OTHER: "Otros",
}


class ColumnType(StrEnum):
    DATE = "date"
    CODE = "code"  # código nacional: texto normalizado
    TEXT = "text"
    NUMBER = "number"
    FAMILY = "family"


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    required: bool
    description: str


@dataclass(frozen=True)
class DatasetSchema:
    name: str
    columns: tuple[Column, ...]
    # Columnas cuyo valor nulo invalida la fila (se descarta con aviso).
    row_keys: tuple[str, ...]

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def required(self) -> list[str]:
        return [c.name for c in self.columns if c.required]

    def get(self, name: str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(name)


SALES = DatasetSchema(
    name="ventas",
    columns=(
        Column("fecha", ColumnType.DATE, True, "Fecha de la venta"),
        Column("codigo_nacional", ColumnType.CODE, True, "Código nacional del producto"),
        Column("descripcion", ColumnType.TEXT, False, "Descripción del producto"),
        Column("laboratorio", ColumnType.TEXT, False, "Laboratorio"),
        Column("familia", ColumnType.FAMILY, False, "Familia canónica"),
        Column("unidades", ColumnType.NUMBER, True, "Unidades vendidas (negativas = devolución)"),
        Column("importe_venta_sin_iva", ColumnType.NUMBER, True, "Importe de venta sin IVA (€)"),
        Column("coste_unitario", ColumnType.NUMBER, False, "Coste unitario sin IVA (€)"),
    ),
    row_keys=("fecha", "codigo_nacional"),
)

STOCK = DatasetSchema(
    name="stock",
    columns=(
        Column("codigo_nacional", ColumnType.CODE, True, "Código nacional del producto"),
        Column("descripcion", ColumnType.TEXT, False, "Descripción del producto"),
        Column("laboratorio", ColumnType.TEXT, False, "Laboratorio"),
        Column("familia", ColumnType.FAMILY, False, "Familia canónica"),
        Column("stock_unidades", ColumnType.NUMBER, True, "Unidades en stock"),
        Column("coste_unitario", ColumnType.NUMBER, True, "Coste unitario sin IVA (€)"),
        Column("pvp", ColumnType.NUMBER, False, "PVP con IVA (€), informativo"),
        Column("fecha_caducidad", ColumnType.DATE, False, "Fecha de caducidad más próxima"),
    ),
    row_keys=("codigo_nacional",),
)

PURCHASES = DatasetSchema(
    name="compras",
    columns=(
        Column("fecha", ColumnType.DATE, True, "Fecha del albarán"),
        Column("codigo_nacional", ColumnType.CODE, True, "Código nacional del producto"),
        Column("laboratorio", ColumnType.TEXT, False, "Laboratorio"),
        Column("unidades", ColumnType.NUMBER, True, "Unidades recibidas"),
        Column("coste_total", ColumnType.NUMBER, True, "Coste total de la línea sin IVA (€)"),
    ),
    row_keys=("fecha", "codigo_nacional"),
)

SCHEMAS: dict[str, DatasetSchema] = {s.name: s for s in (SALES, STOCK, PURCHASES)}
DATASETS: tuple[str, ...] = tuple(SCHEMAS)
