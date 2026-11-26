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
