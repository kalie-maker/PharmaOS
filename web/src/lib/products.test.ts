import { actionsByProduct, families, filterProducts } from "./products";
import { SAMPLE } from "@/test/fixtures";

describe("catálogo de productos", () => {
  const withAction = actionsByProduct(SAMPLE);
  it("filtra por texto, familia y con acción", () => {
    expect(
      filterProducts(
        SAMPLE,
        { query: "100003", family: "", sort: "valor", onlyWithAction: false },
        withAction,
      ),
    ).toHaveLength(1);
    expect(
      filterProducts(
        SAMPLE,
        { query: "", family: "Solares", sort: "valor", onlyWithAction: false },
        withAction,
      ),
    ).toHaveLength(0);
    expect(families(SAMPLE)).toEqual(["OTC"]);
  });
  it("es rápido con 8.000 productos", () => {
    const big = structuredClone(SAMPLE);
    for (let i = 0; i < 8000; i++) {
      const code = String(200000 + i);
      big.productos[code] = {
        ...SAMPLE.productos["100001"]!,
        codigo: code,
        nombre: `Producto ${i}`,
        valor_stock: i,
      };
    }
    const t0 = performance.now();
    const rows = filterProducts(
      big,
      { query: "producto 79", family: "", sort: "valor", onlyWithAction: false },
      withAction,
    );
    expect(performance.now() - t0).toBeLessThan(200);
    expect(rows[0]!.nombre).toBe("Producto 7999");
  });
});
