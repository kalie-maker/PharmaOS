"""Generadores de ficheros de exportación "sucios" para tests de la Fase 4."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from engine.mock.generate import MockData

SALES_ROWS = [
    # Fecha, Código, Descripción, Laboratorio, Familia, Unidades, Importe, Coste
    ("03/02/2026", "654321", "Crema hidratante, 50 ml", "Lab Ñandú", "Dermofarmacia", "2", "1.234,50", "300,25"),
    ("04/02/2026", "700100", "Paracetamol 1 g 40 comp", "Lab Ébano", "Especialidad con receta", "1", "2,50", "1,80"),
    ("05/02/2026", "700100", "Paracetamol 1 g 40 comp", "Lab Ébano", "Especialidad con receta", "3", "7,50", "1,80"),
]
SALES_HEADER = ["Fecha", "Código", "Descripción", "Laboratorio", "Familia", "Unidades", "Importe s/IVA", "P.Coste"]


def write_text(path: Path, lines: list[str], encoding: str) -> Path:
    path.write_bytes("\r\n".join(lines).encode(encoding))
    return path


def latin1_tab_with_title(path: Path) -> Path:
    """Latin-1, tabulador, dos líneas de título, línea en blanco y fila de totales."""
    lines = ["Farmatic - Listado de ventas", "Periodo: 01/02/2026 - 28/02/2026", "", "\t".join(SALES_HEADER)]
    lines += ["\t".join(row) for row in SALES_ROWS]
    lines += ["\t".join(["TOTAL", "", "", "", "", "6", "1.244,50", ""])]
    return write_text(path, lines, "latin-1")


def utf8_bom_comma_dot_decimal(path: Path) -> Path:
    """UTF-8 con BOM, separador coma, decimales con punto, campos entrecomillados con comas."""
    def q(v: str) -> str:
        return f'"{v}"' if "," in v else v
    rows = [(f, c, d, lab, fam, u, imp.replace(".", "").replace(",", "."), cost.replace(",", "."))
            for f, c, d, lab, fam, u, imp, cost in SALES_ROWS]
    lines = [",".join(SALES_HEADER)] + [",".join(q(v) for v in row) for row in rows]
    return write_text(path, lines, "utf-8-sig")


def cp1252_short_dates(path: Path) -> Path:
    """Windows-1252 con '€', punto y coma, fechas dd-mm-aa e importes con símbolo de euro."""
    lines = [";".join(SALES_HEADER)]
    for f, c, d, lab, fam, u, imp, cost in SALES_ROWS:
        day, month, year = f.split("/")
        lines.append(";".join([f"{day}-{month}-{year[2:]}", c, d, lab, fam, u, f"{imp} €", cost]))
    return write_text(path, lines, "cp1252")


def multi_sheet_xlsx(path: Path, ambiguous: bool = False) -> Path:
    """Excel con hoja de resumen, hoja de datos (cabecera en la fila 3) y hoja de notas."""
    data = pd.DataFrame(
        [[pd.Timestamp(f[6:] + "-" + f[3:5] + "-" + f[:2]), int(c), d, lab, fam, int(u),
          float(imp.replace(".", "").replace(",", ".")), float(cost.replace(",", "."))]
         for f, c, d, lab, fam, u, imp, cost in SALES_ROWS],
        columns=SALES_HEADER,
    )
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([["Resumen de ventas"], ["Total", 1244.5]]).to_excel(
            writer, sheet_name="Resumen", header=False, index=False)
        title = pd.DataFrame([["Listado de ventas"], [None]])
        title.to_excel(writer, sheet_name="Datos", header=False, index=False)
        data.to_excel(writer, sheet_name="Datos", startrow=2, index=False)
        if ambiguous:
            data.to_excel(writer, sheet_name="Datos 2025", index=False)
        pd.DataFrame([["Exportado desde el programa de gestión"]]).to_excel(
            writer, sheet_name="Notas", header=False, index=False)
    return path


def degrade_mock(mock: MockData) -> MockData:
    """Copia del mock con problemas de calidad: costes vacíos, stock negativo, fechas imposibles,
    descripciones vacías y duplicados."""
    sales, stock, purchases = mock.sales.copy(), mock.stock.copy(), mock.purchases.copy()
    n = len(stock)
    stock.loc[stock.index[: n // 10], "P.Coste"] = None  # 10 % sin coste
    stock.loc[stock.index[n // 10 : n // 10 + n // 20], "Stock Actual"] = -2  # 5 % negativo
    stock.loc[stock.index[-(n // 5):], "Descripción"] = ""  # 20 % sin descripción
    stock = pd.concat([stock, stock.head(n // 20)], ignore_index=True)  # códigos duplicados
    future = sales.sample(frac=0.03, random_state=1).index
    sales.loc[future, "Fecha"] = "15/06/2031"
    sales = pd.concat([sales, sales.head(len(sales) // 25)], ignore_index=True)  # filas duplicadas
    return MockData(sales, stock, purchases, mock.overbought_labs)


def simulate_after(mock: MockData, days: int, dead_codes: list[str], overstock_codes: list[str]) -> MockData:
    """Situación `days` días después: se devuelven referencias sin movimiento, se baja el sobrestock
    a la mitad y se repiten las últimas ventas desplazadas en el tiempo."""
    sales = mock.sales.copy()
    dates = pd.to_datetime(sales["Fecha"], format="%d/%m/%Y")
    last = dates.max()
    recent = sales[dates > last - pd.Timedelta(days=days)].copy()
    recent["Fecha"] = (pd.to_datetime(recent["Fecha"], format="%d/%m/%Y") + pd.Timedelta(days=days)).dt.strftime(
        "%d/%m/%Y")
    sales = pd.concat([sales, recent], ignore_index=True)

    stock = mock.stock.copy()
    stock.loc[stock["Código"].isin(dead_codes), "Stock Actual"] = 0
    over = stock["Código"].isin(overstock_codes)
    stock.loc[over, "Stock Actual"] = (stock.loc[over, "Stock Actual"] // 2).astype(int)
    return MockData(sales, stock, mock.purchases.copy(), mock.overbought_labs)
