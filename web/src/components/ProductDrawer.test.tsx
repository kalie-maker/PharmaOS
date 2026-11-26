import { render, screen, within } from "@testing-library/react";
import { ProductDrawer } from "./ProductDrawer";
import { SAMPLE } from "@/test/fixtures";

describe("ProductDrawer", () => {
  it("muestra la ficha, el gráfico y el cálculo explicado paso a paso", () => {
    const action = {
      ...SAMPLE.acciones[0]!,
      calculo_explicado: {
        pasos: [
          { concepto: "Stock actual", valor: "11 uds" },
          { concepto: "Capital inmovilizado", valor: "11 uds × 33,00 € = 363,00 €" },
        ],
        formula: "stock × coste unitario",
        resultado: "Devolverlo libera 363,00 € de capital.",
      },
    };
    render(
      <ProductDrawer
        report={SAMPLE}
        productId={action.producto_id}
        action={action}
        onClose={() => undefined}
      />,
    );
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/Producto 100001/)).toBeTruthy();
    expect(within(dialog).getByRole("img", { name: /Unidades vendidas por semana/ })).toBeTruthy();
    expect(within(dialog).getByText("11 uds × 33,00 € = 363,00 €")).toBeTruthy();
    expect(within(dialog).getByText("Devolverlo libera 363,00 € de capital.")).toBeTruthy();
  });
  it("no se pinta sin producto", () => {
    render(<ProductDrawer report={SAMPLE} productId={null} onClose={() => undefined} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("ProductDrawer con acciones", () => {
  it("permite marcar como hecha desde la ficha (botón y tecla H) y cierra", async () => {
    const { fireEvent } = await import("@testing-library/react");
    const calls: string[] = [];
    let closed = 0;
    const action = SAMPLE.acciones[0]!;
    const { unmount } = render(
      <ProductDrawer
        report={SAMPLE}
        productId={action.producto_id}
        action={action}
        status="pendiente"
        onStatus={(s) => calls.push(s)}
        onClose={() => closed++}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Marcar como hecha/ }));
    expect(calls).toEqual(["hecha"]);
    fireEvent.keyDown(window, { key: "p" });
    expect(calls).toEqual(["hecha", "pospuesta"]);
    expect(closed).toBe(2);
    unmount();
  });
  it("sin ventas muestra un texto en vez de un gráfico vacío", () => {
    const report = structuredClone(SAMPLE);
    report.productos["100001"]!.ventas_semanales_12 = Array(12).fill(0);
    render(<ProductDrawer report={report} productId="100001" onClose={() => undefined} />);
    expect(screen.getByText("Sin ventas en las últimas 12 semanas")).toBeTruthy();
  });
});
