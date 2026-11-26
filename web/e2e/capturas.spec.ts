import { test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { startDemo } from "./helpers";

const OUT = "../docs/screenshots";

test("capturas de cada pantalla", async ({ page }, testInfo) => {
  mkdirSync(OUT, { recursive: true });
  const shot = async (name: string, fullPage = false) =>
    page.screenshot({ path: `${OUT}/${name}-${testInfo.project.name}.png`, fullPage });

  await page.goto("/");
  await page.getByTestId("ver-demo").waitFor();
  await shot("01-onboarding");
  await startDemo(page);
  for (let i = 0; i < 3; i++) {
    await page
      .getByTestId("lista-acciones")
      .locator("li[data-action-id]")
      .first()
      .getByRole("button", { name: /Marcar como hecha/ })
      .click();
  }
  await page.waitForTimeout(5500); // deja que desaparezca el aviso
  await shot("02-lunes");
  await page
    .getByTestId("lista-acciones")
    .locator("li[data-action-id]")
    .nth(1)
    .locator("button")
    .first()
    .click();
  await page
    .getByRole("dialog")
    .getByText(/Por qué esta acción/)
    .waitFor();
  await shot("03-ficha-producto");
  await page.keyboard.press("Escape");
  await page.goto("/productos");
  await page.getByTestId("productos-resumen").waitFor();
  await shot("04-productos");
  await page.goto("/recuperado");
  await page.getByTestId("multiplo").waitFor();
  await shot("05-recuperado", true);
  await page.goto("/subir");
  await page
    .getByTestId("input-ficheros")
    .setInputFiles(["public/ejemplos/ejemplo_bloqueado.csv", "public/ejemplos/ventas_ejemplo.csv"]);
  await page.getByTestId("bloqueo-privacidad").waitFor();
  await shot("06-subir", true);
  await page.goto("/ajustes");
  await page.getByTestId("reiniciar-demo").waitFor();
  await shot("07-ajustes");
  await page.goto("/imprimir/devolucion");
  await page.getByTestId("total-devolucion").waitFor();
  await shot("08-lista-devolucion", true);
  await page.goto("/imprimir/resumen");
  await page.getByText("Las 10 acciones de más importe").waitFor();
  await shot("09-resumen-semanal", true);
});
