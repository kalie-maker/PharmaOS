"""Carga de configuración (umbrales) y mapeos de columnas por programa de gestión."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from engine.schemas import DATASETS, SCHEMAS, Family

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_MAPPINGS_DIR = PROJECT_ROOT / "config" / "mappings"
DEFAULT_SYNONYMS_PATH = PROJECT_ROOT / "config" / "sinonimos.yaml"


class ConfigError(ValueError):
    """Configuración o mapeo inválido."""


def normalize_label(text: object) -> str:
    """Normaliza un encabezado/etiqueta: minúsculas, sin tildes, sin puntuación."""
    raw = unicodedata.normalize("NFKD", str(text))
    no_accents = "".join(ch for ch in raw if not unicodedata.combining(ch))
    cleaned = "".join(ch if ch.isalnum() else " " for ch in no_accents.lower())
    return " ".join(cleaned.split())


# ---------------------------------------------------------------------------
# Umbrales
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualityLimits:
    """Límites de calidad de datos (en %). Hipótesis ajustables."""

    max_pct_missing_cost: float
    max_pct_negative_stock: float
    max_pct_dates_out_of_range: float
    max_pct_missing_description: float
    max_pct_duplicates: float
    max_pct_dropped_rows: float
    max_pct_sales_not_in_stock: float
    max_age_days: int
    warning_fraction: float


@dataclass(frozen=True)
class ComparisonLimits:
    done_threshold: float
    partial_threshold: float


@dataclass(frozen=True)
class Thresholds:
    """Umbrales del motor. Todos son hipótesis ajustables (ver config.yaml)."""

    reference_date: date | None
    short_window_days: int
    long_window_days: int
    no_movement_warning_days: int
    no_movement_critical_days: int
    target_coverage_days: int
    target_coverage_by_family: dict[str, int]
    replenishment_days: float
    safety_days: float
    frequent_min_sale_days: int
    expiry_windows_days: tuple[int, ...]
    lab_window_months: int
    lab_high_ratio: float
    lab_min_purchases_eur: float
    abc_a_cut: float
    abc_b_cut: float
    max_main_actions: int
    max_refs_per_action: int
    min_action_impact_eur: float
    privacy_scan_content: bool
    privacy_phone_min_ratio: float
    quality: QualityLimits
    comparison: ComparisonLimits

    def coverage_for(self, family: str | None) -> int:
        if family and family in self.target_coverage_by_family:
            return self.target_coverage_by_family[family]
        return self.target_coverage_days


def _get(data: dict[str, Any], path: str) -> Any:
    node: Any = data
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise ConfigError(f"Falta la clave '{path}' en config.yaml")
        node = node[key]
    return node


def load_thresholds(path: Path | str = DEFAULT_CONFIG_PATH) -> Thresholds:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"No existe el fichero de configuración: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    ref = _get(data, "analisis.fecha_referencia")
    if ref is not None and not isinstance(ref, date):
        try:
            ref = date.fromisoformat(str(ref))
        except ValueError as exc:
            raise ConfigError("analisis.fecha_referencia debe ser AAAA-MM-DD o null") from exc

    by_family = {str(k): int(v) for k, v in (_get(data, "cobertura.por_familia") or {}).items()}
    unknown = set(by_family) - {f.value for f in Family}
    if unknown:
        raise ConfigError(f"Familias desconocidas en cobertura.por_familia: {sorted(unknown)}")

    t = Thresholds(
        reference_date=ref,
        short_window_days=int(_get(data, "consumo.ventana_corta_dias")),
        long_window_days=int(_get(data, "consumo.ventana_larga_dias")),
        no_movement_warning_days=int(_get(data, "sin_movimiento.dias_aviso")),
        no_movement_critical_days=int(_get(data, "sin_movimiento.dias_critico")),
        target_coverage_days=int(_get(data, "cobertura.objetivo_dias")),
        target_coverage_by_family=by_family,
        replenishment_days=float(_get(data, "reposicion.dias_reposicion")),
        safety_days=float(_get(data, "reposicion.dias_seguridad")),
        frequent_min_sale_days=int(_get(data, "reposicion.min_dias_con_venta")),
        expiry_windows_days=tuple(sorted(int(d) for d in _get(data, "caducidad.ventanas_dias"))),
        lab_window_months=int(_get(data, "laboratorios.meses_analisis")),
        lab_high_ratio=float(_get(data, "laboratorios.ratio_compras_ventas_alto")),
        lab_min_purchases_eur=float(_get(data, "laboratorios.compras_minimas_eur")),
        abc_a_cut=float(_get(data, "abc.corte_a")),
        abc_b_cut=float(_get(data, "abc.corte_b")),
        max_main_actions=int(_get(data, "acciones.max_principales")),
        max_refs_per_action=int(_get(data, "acciones.max_referencias_por_accion")),
        min_action_impact_eur=float(_get(data, "acciones.impacto_minimo_eur")),
        privacy_scan_content=bool(_get(data, "privacidad.escanear_contenido")),
        privacy_phone_min_ratio=float(_get(data, "privacidad.ratio_minimo_telefono")),
        quality=QualityLimits(
            max_pct_missing_cost=float(_get(data, "calidad.max_pct_costes_vacios")),
            max_pct_negative_stock=float(_get(data, "calidad.max_pct_stock_negativo")),
            max_pct_dates_out_of_range=float(_get(data, "calidad.max_pct_fechas_fuera_rango")),
            max_pct_missing_description=float(_get(data, "calidad.max_pct_sin_descripcion")),
            max_pct_duplicates=float(_get(data, "calidad.max_pct_duplicados")),
            max_pct_dropped_rows=float(_get(data, "calidad.max_pct_filas_descartadas")),
            max_pct_sales_not_in_stock=float(_get(data, "calidad.max_pct_ventas_sin_stock")),
            max_age_days=int(_get(data, "calidad.antiguedad_maxima_dias")),
            warning_fraction=float(_get(data, "calidad.fraccion_aviso")),
        ),
        comparison=ComparisonLimits(
            done_threshold=float(_get(data, "comparacion.umbral_ejecutada")),
            partial_threshold=float(_get(data, "comparacion.umbral_parcial")),
        ),
    )
    _validate_thresholds(t)
    return t


def _validate_thresholds(t: Thresholds) -> None:
    if t.no_movement_warning_days >= t.no_movement_critical_days:
        raise ConfigError("sin_movimiento.dias_aviso debe ser menor que dias_critico")
    if t.short_window_days > t.long_window_days:
        raise ConfigError("consumo.ventana_corta_dias no puede superar ventana_larga_dias")
    if not 0 < t.abc_a_cut < t.abc_b_cut <= 1:
        raise ConfigError("abc: debe cumplirse 0 < corte_a < corte_b <= 1")
    if not 0 < t.comparison.partial_threshold < t.comparison.done_threshold <= 1:
        raise ConfigError("comparacion: debe cumplirse 0 < umbral_parcial < umbral_ejecutada <= 1")
    if t.max_main_actions < 1:
        raise ConfigError("acciones.max_principales debe ser >= 1")


# ---------------------------------------------------------------------------
# Mapeos
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadOptions:
    separator: str = ";"
    decimal: str = ","
    thousands: str = "."
    encoding: str = "utf-8"
    date_format: str = "%d/%m/%Y"


@dataclass(frozen=True)
class Mapping:
    program: str
    read: ReadOptions
    # dataset -> columna canónica -> alias aceptados (en orden de preferencia)
    columns: dict[str, dict[str, list[str]]]
    # etiqueta normalizada -> familia canónica
    families: dict[str, Family] = field(default_factory=dict)
    draft: bool = False

    def map_family(self, label: object) -> Family | None:
        """Devuelve la familia canónica o None si la etiqueta no está mapeada."""
        key = normalize_label(label)
        if key in self.families:
            return self.families[key]
        # Permite usar directamente el valor canónico en el fichero.
        for fam in Family:
            if key == normalize_label(fam.value):
                return fam
        return None


def load_mapping(program: str, mappings_dir: Path | str = DEFAULT_MAPPINGS_DIR) -> Mapping:
    path = Path(mappings_dir) / f"{program}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in Path(mappings_dir).glob("*.yaml"))
        raise ConfigError(
            f"No hay mapeo para el programa '{program}'. Disponibles: {', '.join(available) or 'ninguno'}"
        )
    return parse_mapping(yaml.safe_load(path.read_text(encoding="utf-8")) or {}, source=str(path))


def parse_mapping(data: dict[str, Any], source: str = "<mapeo>") -> Mapping:
    read_raw = data.get("lectura") or {}
    read = ReadOptions(
        separator=str(read_raw.get("separador", ";")),
        decimal=str(read_raw.get("decimal", ",")),
        thousands=str(read_raw.get("miles", "") or ""),
        encoding=str(read_raw.get("encoding", "utf-8")),
        date_format=str(read_raw.get("formato_fecha", "%d/%m/%Y")),
    )
    if read.thousands and read.thousands == read.decimal:
        raise ConfigError(f"{source}: 'miles' y 'decimal' no pueden ser iguales")

    files = data.get("ficheros") or {}
    columns: dict[str, dict[str, list[str]]] = {}
    for dataset in DATASETS:
        spec = files.get(dataset)
        if not spec:
            raise ConfigError(
                f"{source}: falta la sección ficheros.{dataset}. Genérala con "
                f"`python -m engine.cli inspeccionar --fichero <{dataset}> --tipo {dataset}`"
            )
        schema = SCHEMAS[dataset]
        unknown = set(spec) - set(schema.column_names)
        if unknown:
            raise ConfigError(
                f"{source}: columnas canónicas desconocidas en '{dataset}': {sorted(unknown)}"
            )
        missing = [c for c in schema.required if c not in spec]
        if missing:
            raise ConfigError(f"{source}: '{dataset}' no mapea columnas obligatorias: {missing}")
        columns[dataset] = {
            canonical: [str(a) for a in (aliases if isinstance(aliases, list) else [aliases])]
            for canonical, aliases in spec.items()
        }

    families: dict[str, Family] = {}
    for label, value in (data.get("familias") or {}).items():
        try:
            families[normalize_label(label)] = Family(str(value))
        except ValueError as exc:
            raise ConfigError(f"{source}: familia canónica desconocida '{value}'") from exc

    return Mapping(
        program=str(data.get("programa", Path(source).stem)),
        read=read,
        columns=columns,
        families=families,
        draft=bool(data.get("borrador", False)),
    )
