import { detectColumns, normalizeLabel } from "./columns";

describe("detección de columnas con los mapeos del motor", () => {
  it("normaliza como el motor", () => {
    expect(normalizeLabel("Importe s/IVA")).toBe("importe s iva");
    expect(normalizeLabel("Cód. Nacional")).toBe("cod nacional");
    expect(normalizeLabel(" Nº  Receta ")).toBe("no receta");
  });
  it("reconoce ventas de Farmatic", () => {
    const d = detectColumns([
      "Fecha",
      "Código",
      "Descripción",
      "Laboratorio",
      "Familia",
      "Unidades",
      "Importe s/IVA",
      "P.Coste",
    ]);
    expect(d.dataset).toBe("ventas");
    expect(d.program).toBe("farmatic");
    expect(d.missingRequired).toEqual([]);
    expect(d.matches.find((m) => m.canonical === "importe_venta_sin_iva")?.column).toBe("Importe s/IVA");
  });
  it("reconoce stock de Nixfarma", () => {
    const d = detectColumns(["COD_NACIONAL", "DESCRIPCION", "STOCK", "PRECIO_COSTE", "PVP"]);
    expect(d.dataset).toBe("stock");
    expect(d.program).toBe("nixfarma");
  });
  it("reconoce compras y avisa de lo que falta", () => {
    expect(
      detectColumns(["Fecha Albarán", "Código", "Laboratorio", "Unidades Recibidas", "Importe Coste"])
        .dataset,
    ).toBe("compras");
    const d = detectColumns(["Código", "Stock Actual"], "stock.csv");
    expect(d.dataset).toBe("stock");
    expect(d.missingRequired).toEqual(["coste_unitario"]);
  });
});
