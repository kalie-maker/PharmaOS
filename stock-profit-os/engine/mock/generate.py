"""Generador de una farmacia ficticia realista y reproducible.

Produce ventas.csv (12 meses), stock.csv y compras.csv (6 meses) con columnas
"estilo Farmatic" (ver config/mappings/farmatic.yaml): separador ';', decimales
con coma, fechas dd/mm/aaaa y codificación cp1252.

Incluye a propósito los problemas que el motor debe detectar:
- 8–15 % de referencias con stock y sin ventas en 180+ días.
- Laboratorios sobrecomprados (compras > ventas a coste).
- Referencias con sobrestock y otras de alta rotación con rotura.
- Caducidades próximas.
- Estacionalidad: solares en verano, antigripales en invierno.

Laboratorios y marcas son inventados. No se generan datos de pacientes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from engine.schemas import Family

# Etiquetas de familia tal y como (suponemos) las exporta Farmatic.
FARMATIC_FAMILY_LABELS: dict[Family, str] = {
    Family.PRESCRIPTION: "Especialidad con receta",
    Family.OTC: "EFP / Publicitarios",
    Family.DERMOCOSMETICS: "Dermofarmacia",
    Family.NUTRITION: "Dietética y Nutrición",
    Family.HYGIENE: "Higiene",
    Family.ORTHOPEDICS: "Ortopedia",
    Family.SUNCARE: "Solares",
}

SALES_COLUMNS = ["Fecha", "Código", "Descripción", "Laboratorio", "Familia", "Unidades", "Importe s/IVA", "P.Coste"]
STOCK_COLUMNS = ["Código", "Descripción", "Laboratorio", "Familia", "Stock Actual", "P.Coste", "PVP", "Caducidad"]
PURCHASE_COLUMNS = ["Fecha Albarán", "Código", "Laboratorio", "Unidades Recibidas", "Importe Coste"]


@dataclass(frozen=True)
class FamilySpec:
    weight: float  # proporción de referencias
    vat: float
    margin: tuple[float, float]  # margen sobre PVP sin IVA
    cost_log_mean: float  # coste unitario ~ lognormal
    rate_log_mean: float  # unidades/día ~ lognormal
    coverage_days: tuple[float, float]  # cobertura habitual de una farmacia bien gestionada


FAMILY_SPECS: dict[Family, FamilySpec] = {
    Family.PRESCRIPTION: FamilySpec(0.44, 0.04, (0.24, 0.29), 1.8, -1.7, (7, 30)),
    Family.OTC: FamilySpec(0.15, 0.04, (0.30, 0.38), 1.5, -2.1, (15, 45)),
    Family.DERMOCOSMETICS: FamilySpec(0.15, 0.21, (0.35, 0.45), 2.4, -2.7, (20, 60)),
    Family.NUTRITION: FamilySpec(0.06, 0.10, (0.30, 0.40), 2.3, -2.7, (20, 60)),
    Family.HYGIENE: FamilySpec(0.10, 0.21, (0.30, 0.40), 1.3, -2.3, (15, 45)),
    Family.ORTHOPEDICS: FamilySpec(0.04, 0.10, (0.35, 0.45), 2.6, -3.1, (30, 90)),
    Family.SUNCARE: FamilySpec(0.06, 0.21, (0.35, 0.45), 2.4, -2.5, (20, 60)),
}

_ACTIVES = [
    "Omeprazol", "Atorvastatina", "Enalapril", "Metformina", "Amlodipino", "Simvastatina",
    "Losartán", "Bisoprolol", "Levotiroxina", "Pantoprazol", "Amoxicilina", "Lorazepam",
    "Alprazolam", "Sertralina", "Escitalopram", "Tramadol", "Furosemida", "Ramipril",
    "Acenocumarol", "Clopidogrel", "Salbutamol", "Budesonida", "Prednisona", "Metamizol",
    "Gabapentina", "Pregabalina", "Tamsulosina", "Rosuvastatina", "Valsartán", "Hidroclorotiazida",
]
_FORMS = ["comprimidos", "cápsulas", "comprimidos recubiertos", "sobres"]
_OTC_ITEMS = [
    "Ibuprofeno 400 mg 20 comp", "Paracetamol 1 g 40 comp", "Paracetamol 650 mg 20 comp",
    "Loratadina 10 mg 20 comp", "Antiácido 30 sobres", "Lactulosa jarabe 800 ml",
    "Cetirizina 10 mg 20 comp", "Pastillas garganta miel limón 24 uds", "Colirio hidratante 10 ml",
    "Probiótico intestinal 20 cáps", "Gel antiinflamatorio 100 g", "Spray nasal agua de mar 100 ml",
]
_FLU_ITEMS = [
    "Antigripal sobres 10 uds", "Antigripal día y noche 16 comp", "Jarabe tos seca 200 ml",
    "Jarabe tos productiva 200 ml", "Descongestivo nasal 15 ml", "Caramelos balsámicos 50 g",
]
_BRAND_WORDS = [
    "Aqualis", "Dermaven", "Lumière", "Nativa", "Purell", "Sebora", "Cutis", "Hydrel",
    "Velvia", "Aurea", "Bioderm", "Calmea", "Floris", "Kerat", "Lenis", "Mirela",
]
_ITEMS = {
    Family.DERMOCOSMETICS: ["crema hidratante 50 ml", "sérum vitamina C 30 ml", "contorno de ojos 15 ml",
                            "gel limpiador 200 ml", "crema antiedad 50 ml", "bálsamo atópico 400 ml"],
    Family.NUTRITION: ["leche infantil 1 800 g", "leche infantil 2 800 g", "batido proteico 400 g",
                       "multivitamínico 30 comp", "magnesio 60 comp", "colágeno 300 g"],
    Family.HYGIENE: ["pasta dentífrica 125 ml", "colutorio 500 ml", "gel íntimo 250 ml",
                     "cepillo dental suave", "champú suave 400 ml", "desodorante 50 ml"],
    Family.ORTHOPEDICS: ["rodillera elástica talla M", "muñequera ferulizada", "plantillas gel",
                         "medias compresión normal", "faja lumbar talla L", "collarín blando"],
    Family.SUNCARE: ["fotoprotector SPF50 50 ml", "spray solar SPF30 200 ml", "after sun 200 ml",
                     "fotoprotector infantil SPF50+ 250 ml", "solar facial color 50 ml", "stick labial SPF50"],
}
_LAB_PREFIX = ["Alba", "Bio", "Cantabria", "Delta", "Euro", "Faro", "Galen", "Hesper", "Iber", "Lumen",
               "Medi", "Norte", "Orion", "Pharma", "Quimi", "Rial", "Sana", "Tera", "Vita", "Zenit"]
_LAB_SUFFIX = ["farma", "lab", " Pharma", " Salud", "ven", "derm", "gen", "med"]


@dataclass(frozen=True)
class MockConfig:
    n_refs: int = 3000
    seed: int = 42
    end_date: date = date(2026, 11, 20)
    sales_days: int = 365
    purchase_days: int = 182
    n_labs: int = 50
    dead_share: float = 0.10  # sin ventas en 180+ días
    slow_share: float = 0.04  # sin ventas entre 90 y 180 días
    overstock_share: float = 0.04
    stockout_share: float = 0.025
    near_expiry_share: float = 0.05
    n_overbought_labs: int = 3


@dataclass
class MockData:
    sales: pd.DataFrame
    stock: pd.DataFrame
    purchases: pd.DataFrame
    overbought_labs: list[str]

    def write(self, out_dir: Path | str, encoding: str = "cp1252") -> dict[str, Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = {"ventas": out / "ventas.csv", "stock": out / "stock.csv", "compras": out / "compras.csv"}
        for frame, key in ((self.sales, "ventas"), (self.stock, "stock"), (self.purchases, "compras")):
            frame.to_csv(paths[key], sep=";", decimal=",", index=False, encoding=encoding, float_format="%.2f")
        return paths


def _seasonality(day_of_year: np.ndarray, center: float, width: float, base: float, peak: float) -> np.ndarray:
    dist = np.abs(day_of_year - center)
    dist = np.minimum(dist, 365 - dist)
    return base + peak * np.exp(-0.5 * (dist / width) ** 2)


def _lab_names(n: int, rng: np.random.Generator) -> list[str]:
    combos = [p + s for p in _LAB_PREFIX for s in _LAB_SUFFIX]
    picked = rng.choice(len(combos), size=n, replace=False)
    return [f"Laboratorios {combos[i]}" if i % 3 == 0 else combos[i] for i in picked]


def _description(family: Family, is_flu: bool, rng: np.random.Generator) -> str:
    if family is Family.PRESCRIPTION:
        dose = rng.choice([5, 10, 20, 25, 40, 50, 100, 500])
        units = rng.choice([14, 28, 30, 56, 60])
        return f"{rng.choice(_ACTIVES)} {dose} mg {units} {rng.choice(_FORMS)}"
    if family is Family.OTC:
        return str(rng.choice(_FLU_ITEMS if is_flu else _OTC_ITEMS))
    return f"{rng.choice(_BRAND_WORDS)} {rng.choice(_ITEMS[family])}"


def generate(config: MockConfig = MockConfig()) -> MockData:
    rng = np.random.default_rng(config.seed)
    n = config.n_refs
    families = list(FAMILY_SPECS)
    weights = np.array([FAMILY_SPECS[f].weight for f in families])
    fam_idx = rng.choice(len(families), size=n, p=weights / weights.sum())
    ref_family = [families[i] for i in fam_idx]

    # --- Laboratorios: cada uno trabaja una familia principal ----------------
    labs = _lab_names(config.n_labs, rng)
    lab_family = [families[i % len(families)] for i in range(config.n_labs)]
    ref_lab = np.empty(n, dtype=object)
    for f in families:
        candidates = [labs[i] for i in range(config.n_labs) if lab_family[i] is f]
        zipf = 1.0 / np.arange(1, len(candidates) + 1)
        mask = np.array([rf is f for rf in ref_family])
        ref_lab[mask] = rng.choice(candidates, size=int(mask.sum()), p=zipf / zipf.sum())

    lab_sizes = pd.Series(ref_lab).value_counts()
    # Laboratorios medianos (no los dos mayores): sobrecompra visible pero no dominante.
    overbought = [str(lab) for lab in lab_sizes.index[2 : 2 + config.n_overbought_labs]]
    is_overbought = np.isin(ref_lab, overbought)

    # --- Productos -------------------------------------------------------------
    is_flu = np.array([f is Family.OTC for f in ref_family]) & (rng.random(n) < 0.25)
    codes = rng.choice(np.arange(600000, 999999), size=n, replace=False).astype(str)
    descriptions = [_description(f, bool(flu), rng) for f, flu in zip(ref_family, is_flu)]
    vat = np.array([FAMILY_SPECS[f].vat for f in ref_family])
    margin = np.array([rng.uniform(*FAMILY_SPECS[f].margin) for f in ref_family])
    cost = np.round(np.exp(np.array([FAMILY_SPECS[f].cost_log_mean for f in ref_family]) + 0.7 * rng.standard_normal(n)), 2)
    cost = np.clip(cost, 0.5, 400.0)
    price_ex_vat = np.round(cost / (1 - margin), 2)
    pvp = np.round(price_ex_vat * (1 + vat), 2)

    # --- Ventas diarias ----------------------------------------------------------
    days = pd.date_range(end=pd.Timestamp(config.end_date), periods=config.sales_days, freq="D")
    doy = days.dayofyear.to_numpy().astype(float)
    weekday = np.select([days.weekday == 6, days.weekday == 5], [0.12, 0.7], 1.0)

    base_rate = np.exp(np.array([FAMILY_SPECS[f].rate_log_mean for f in ref_family]) + 1.1 * rng.standard_normal(n))
    base_rate = np.clip(base_rate, 0.03, 15.0)
    season = np.ones((n, len(days)))
    sun_mask = np.array([f is Family.SUNCARE for f in ref_family])
    season[sun_mask] = _seasonality(doy, center=196, width=32, base=0.1, peak=3.0)
    season[is_flu] = _seasonality(doy, center=15, width=35, base=0.3, peak=2.5)
    expected = base_rate[:, None] * season * weekday[None, :]

    # Referencias sin movimiento: ventas cortadas a partir de una fecha.
    dead_w = np.where(np.array([f is Family.PRESCRIPTION for f in ref_family]), 1.0, 1.6) / (1 + base_rate)
    n_dead = int(round(config.dead_share * n))
    dead_idx = rng.choice(n, size=n_dead, replace=False, p=dead_w / dead_w.sum())
    remaining = np.setdiff1d(np.arange(n), dead_idx)
    slow_idx = rng.choice(remaining, size=int(round(config.slow_share * n)), replace=False)
    days_ago = (len(days) - 1) - np.arange(len(days))
    for idx, low, high in ((dead_idx, 181, 500), (slow_idx, 91, 179)):
        cutoff = rng.integers(low, high, size=len(idx))
        expected[idx] *= (days_ago[None, :] >= cutoff[:, None])

    units = rng.poisson(expected)
    day_i, ref_i = np.nonzero(units.T)  # orden cronológico
    qty = units[ref_i, day_i]
    promo = np.where(
        (vat[ref_i] > 0.04) & (rng.random(len(ref_i)) < 0.15), 0.10, 0.0
    )
    sales = pd.DataFrame({
        "Fecha": days[day_i].strftime("%d/%m/%Y"),
        "Código": codes[ref_i],
        "Descripción": np.array(descriptions, dtype=object)[ref_i],
        "Laboratorio": ref_lab[ref_i],
        "Familia": [FARMATIC_FAMILY_LABELS[ref_family[i]] for i in ref_i],
        "Unidades": qty.astype(int),
        "Importe s/IVA": np.round(qty * price_ex_vat[ref_i] * (1 - promo), 2),
        "P.Coste": cost[ref_i],
    })

    # --- Stock -------------------------------------------------------------------
    recent_rate = expected[:, -30:].mean(axis=1)
    low = np.array([FAMILY_SPECS[f].coverage_days[0] for f in ref_family])
    high = np.array([FAMILY_SPECS[f].coverage_days[1] for f in ref_family])
    coverage = rng.uniform(low, high)
    overstock_idx = rng.choice(remaining, size=int(round(config.overstock_share * n)), replace=False)
    coverage[overstock_idx] = rng.uniform(75, 150, size=len(overstock_idx))
    coverage[is_overbought] *= rng.uniform(1.5, 2.2, size=int(is_overbought.sum()))
    stock_units = np.maximum(np.round(recent_rate * coverage), 1)
    stock_units[dead_idx] = rng.integers(1, 13, size=len(dead_idx))

    fast = np.setdiff1d(np.where(base_rate >= np.quantile(base_rate, 0.75))[0], dead_idx)
    stockout_idx = rng.choice(fast, size=min(len(fast), int(round(config.stockout_share * n))), replace=False)
    stock_units[stockout_idx] = rng.integers(0, 2, size=len(stockout_idx))

    expiry = np.array([pd.Timestamp(config.end_date) + pd.Timedelta(days=int(d)) for d in rng.integers(120, 1000, size=n)])
    has_expiry = rng.random(n) < 0.7
    slow_like = np.union1d(np.union1d(dead_idx, slow_idx), overstock_idx)
    near_idx = rng.choice(slow_like, size=min(len(slow_like), int(round(config.near_expiry_share * n))), replace=False)
    has_expiry[near_idx] = True
    for i, d in zip(near_idx, rng.integers(5, 90, size=len(near_idx))):
        expiry[i] = pd.Timestamp(config.end_date) + pd.Timedelta(days=int(d))
    expiry_text = np.where(has_expiry, [e.strftime("%d/%m/%Y") for e in expiry], "")

    stock = pd.DataFrame({
        "Código": codes,
        "Descripción": descriptions,
        "Laboratorio": ref_lab,
        "Familia": [FARMATIC_FAMILY_LABELS[f] for f in ref_family],
        "Stock Actual": stock_units.astype(int),
        "P.Coste": cost,
        "PVP": pvp,
        "Caducidad": expiry_text,
    })

    # --- Compras (últimos 6 meses) ------------------------------------------------
    p_days = config.purchase_days
    window_units = units[:, -p_days:]
    window_dates = days[-p_days:]
    factor = np.where(is_overbought, rng.uniform(1.45, 1.7, size=n), rng.uniform(0.9, 1.1, size=n))
    factor[overstock_idx] = np.maximum(factor[overstock_idx], 1.3)
    rows: list[tuple[str, str, str, int, float]] = []
    for i in range(n):
        interval = int(rng.integers(5, 22))
        start = int(rng.integers(0, interval))
        for s in range(start, p_days, interval):
            sold = int(window_units[i, s : s + interval].sum())
            bought = int(round(sold * factor[i]))
            if bought <= 0:
                continue
            discount = rng.uniform(0.0, 0.08)
            rows.append((
                window_dates[s].strftime("%d/%m/%Y"), codes[i], str(ref_lab[i]),
                bought, round(bought * cost[i] * (1 - discount), 2),
            ))
    purchases = pd.DataFrame(rows, columns=PURCHASE_COLUMNS)

    return MockData(
        sales=sales[SALES_COLUMNS],
        stock=stock[STOCK_COLUMNS],
        purchases=purchases,
        overbought_labs=overbought,
    )


def generate_to(out_dir: Path | str, config: MockConfig = MockConfig()) -> dict[str, Path]:
    return generate(config).write(out_dir)
