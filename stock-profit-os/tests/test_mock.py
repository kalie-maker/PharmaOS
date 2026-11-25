from __future__ import annotations

import pandas as pd

from engine.mock.generate import PURCHASE_COLUMNS, SALES_COLUMNS, STOCK_COLUMNS, MockConfig, generate
from engine.privacy import check_content, check_headers


def _dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%d/%m/%Y")


def test_reproducible_with_same_seed() -> None:
    a, b = generate(MockConfig(n_refs=200, seed=1)), generate(MockConfig(n_refs=200, seed=1))
    pd.testing.assert_frame_equal(a.sales, b.sales)
    pd.testing.assert_frame_equal(a.stock, b.stock)
    pd.testing.assert_frame_equal(a.purchases, b.purchases)
    c = generate(MockConfig(n_refs=200, seed=2))
    assert not a.stock.equals(c.stock)


def test_farmatic_style_columns(small_mock) -> None:
    assert list(small_mock.sales.columns) == SALES_COLUMNS
    assert list(small_mock.stock.columns) == STOCK_COLUMNS
    assert list(small_mock.purchases.columns) == PURCHASE_COLUMNS


def test_mock_contains_no_personal_data(small_mock) -> None:
    for frame in (small_mock.sales, small_mock.stock, small_mock.purchases):
        assert check_headers(frame.columns) == []
        assert check_content(frame) == []


def test_full_mock_shape_and_periods(full_mock) -> None:
    stock, sales, purchases = full_mock.stock, full_mock.sales, full_mock.purchases
    assert len(stock) == 3000
    assert stock["Código"].is_unique
    sale_dates, buy_dates = _dates(sales["Fecha"]), _dates(purchases["Fecha Albarán"])
    assert (sale_dates.max() - sale_dates.min()).days >= 360
    assert 170 <= (buy_dates.max() - buy_dates.min()).days <= 182
    families = set(stock["Familia"])
    assert {"Especialidad con receta", "EFP / Publicitarios", "Dermofarmacia", "Dietética y Nutrición",
            "Higiene", "Ortopedia", "Solares"} <= families


def test_full_mock_dead_stock_share(full_mock) -> None:
    sales, stock = full_mock.sales, full_mock.stock
    dates = _dates(sales["Fecha"])
    last_sale = dates.groupby(sales["Código"]).max()
    days_since = (dates.max() - stock["Código"].map(last_sale)).dt.days
    dead = (stock["Stock Actual"] > 0) & (days_since.isna() | (days_since > 180))
    assert 0.08 <= dead.mean() <= 0.15


def test_full_mock_seasonality(full_mock) -> None:
    sales = full_mock.sales
    month = _dates(sales["Fecha"]).dt.month
    sun = sales["Familia"] == "Solares"
    assert sales.loc[sun & month.isin([6, 7, 8]), "Unidades"].sum() > 5 * sales.loc[sun & month.isin([12, 1, 2]), "Unidades"].sum()
    flu = sales["Descripción"].str.contains(r"\bantigripal\b|\btos\b", case=False)
    assert sales.loc[flu & month.isin([12, 1, 2]), "Unidades"].sum() > 2 * sales.loc[flu & month.isin([6, 7, 8]), "Unidades"].sum()


def test_full_mock_overbought_labs(full_mock) -> None:
    sales, purchases = full_mock.sales, full_mock.purchases
    buy_dates, sale_dates = _dates(purchases["Fecha Albarán"]), _dates(sales["Fecha"])
    since = buy_dates.min()
    recent = sales[sale_dates >= since]
    sold_cost = (recent["Unidades"] * recent["P.Coste"]).groupby(recent["Laboratorio"]).sum()
    bought = purchases.groupby("Laboratorio")["Importe Coste"].sum()
    ratio = (bought / sold_cost).dropna()
    for lab in full_mock.overbought_labs:
        assert ratio[lab] > 1.3
    assert ratio.median() < 1.15


def test_full_mock_has_stockouts_and_near_expiry(full_mock) -> None:
    stock = full_mock.stock
    assert (stock["Stock Actual"] == 0).sum() >= 20
    expiry = pd.to_datetime(stock["Caducidad"].replace("", None), format="%d/%m/%Y")
    days_left = (expiry - pd.Timestamp(MockConfig().end_date)).dt.days
    assert ((days_left >= 0) & (days_left <= 90)).sum() >= 50
