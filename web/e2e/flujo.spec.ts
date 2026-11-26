import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { expectAccessible, isMobile, startDemo } from "./helpers";

test("flujo completo: demo → lunes → 3 acciones → ficha → exportar → recuperado", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page.getByTestId("ver-demo").click();
  await page.waitForURL("**/lunes");
  await expect(page.getByTestId("recuperable")).toHaveText(/€/);
  await expect(page.getByTestId("progreso")).toContainText("0 de 40 hechas");

  // Marcar 3 acciones: con teclado en escritorio, con botones en móvil.
  const titles: string[] = [];
  for (let i = 0; i < 3; i++) {
    const first = page.getByTestId("lista-acciones").locator("li[data-action-id]").first();
    titles.push((await first.locator("button").first().textContent()) ?? "");
    if (isMobile(testInfo)) await first.getByRole("button", { name: /Marcar como hecha/ }).click();
    else await page.keyboard.press("h");
    await expect(page.getByTestId("progreso")).toContainText(`${i + 1} de 40 hechas`);
  }
  await expect(page.getByRole("status")).toContainText("Deshacer");
  await expect(page.getByTestId("recuperado")).not.toHaveText("0 €");

  // Deshacer desde el aviso y volver a marcar.
  await page.getByRole("button", { name: "Deshacer" }).last().click();
  await expect(page.getByTestId("progreso")).toContainText("2 de 40 hechas");
  await page
    .getByTestId("lista-acciones")
    .locator("li[data-action-id]")
    .first()
    .getByRole("button", { name: /Marcar como hecha/ })
    .click();
  await expect(page.getByTestId("progreso")).toContainText("3 de 40 hechas");

  // Ficha con el cálculo explicado.
  const next = page.getByTestId("lista-acciones").locator("li[data-action-id]").first();
  await next.locator("button").first().click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByText(/Por qué esta acción/)).toBeVisible();
  await expect(drawer.getByRole("img", { name: /Unidades vendidas por semana/ })).toBeVisible();
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();

  // Exportar: CSV de devolución y vista imprimible.
  await page.getByRole("button", { name: /Exportar/ }).click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("menuitem", { name: "Descargar CSV" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^lista_devolucion_\d{4}-\d{2}-\d{2}\.csv$/);
  const csv = readFileSync((await download.path())!, "utf-8");
  expect(csv).toContain("Código nacional;Producto;Laboratorio;Unidades;Importe a coste (€);Estado");
  await page.getByRole("button", { name: /Exportar/ }).click();
  const [pedido] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("menuitem", { name: /Pedido corregido/ }).click(),
  ]);
  expect(readFileSync((await pedido.path())!, "utf-8")).toMatch(/No pedir|Pedir/);
  await page.getByRole("button", { name: /Exportar/ }).click();
  await page.getByRole("menuitem", { name: /Imprimir A4/ }).click();
  await page.waitForURL("**/imprimir/devolucion");
  await expect(page.getByTestId("total-devolucion")).toHaveText(/€/);
  await page.getByRole("link", { name: /Volver a la lista/ }).click();

  // Recuperado: las 3 acciones ejecutadas aparecen con fecha e importe.
  await page.goto("/recuperado");
  await expect(page.getByTestId("tabla-ejecutadas").locator("tbody tr")).toHaveCount(3);
  await expect(page.getByTestId("multiplo")).toHaveText(/×\d/);
  await expectAccessible(page);

  // El estado sobrevive a recargar (localStorage).
  await page.goto("/lunes");
  await expect(page.getByTestId("progreso")).toContainText("3 de 40 hechas");
  expect(titles.every(Boolean)).toBe(true);
});

test("atajos de teclado y ayuda", async ({ page }, testInfo) => {
  test.skip(isMobile(testInfo), "Atajos solo en escritorio");
  await startDemo(page);
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog", { name: "Atajos de teclado" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("j");
  await page.keyboard.press("p");
  await expect(page.getByText(/Pospuestas · 1/)).toBeVisible();
  await page.keyboard.press("/");
  await page.keyboard.type("omeprazol");
  await expect(page.getByTestId("lista-acciones").locator("li[data-action-id]").first()).toContainText(
    /Omeprazol/i,
  );
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /^Caduca pronto/ }).click();
  const rows = page.getByTestId("lista-acciones").locator("li[data-action-id]");
  await expect(rows.first()).toContainText("Caduca pronto");
});

test("subir: vista previa y bloqueo por privacidad", async ({ page }) => {
  await startDemo(page);
  await page.goto("/subir");
  await page.getByTestId("input-ficheros").setInputFiles(["public/ejemplos/ventas_ejemplo.csv"]);
  await expect(page.getByTestId("vista-previa").locator("tbody tr")).toHaveCount(20);
  await expect(page.getByTestId("resumen-productos")).not.toHaveText("0");
  await expectAccessible(page);
  await page.getByTestId("input-ficheros").setInputFiles(["public/ejemplos/ejemplo_bloqueado.csv"]);
  await expect(page.getByTestId("bloqueo-privacidad")).toContainText("DNI");
  await expect(page.getByTestId("barra-analisis")).toContainText("bloqueados por privacidad");
  await expect(page.getByTestId("analizar")).toHaveCount(0);
  await page.getByRole("button", { name: /Quitar ejemplo_bloqueado/ }).click();
  // Con solo ventas, el análisis real no se puede hacer: se ofrece la demo simulada.
  await expect(page.getByTestId("barra-analisis")).toContainText("faltan");
  await expect(page.getByTestId("analizar")).toBeDisabled();
  await page.getByTestId("analizar-simulado").click();
  await page.waitForURL("**/lunes");
});

test("subir: análisis real con el motor local y vuelta a la demo", async ({ page }) => {
  await startDemo(page);
  await page.goto("/subir");
  await page
    .getByTestId("input-ficheros")
    .setInputFiles([
      "public/ejemplos/ventas_ejemplo.csv",
      "public/ejemplos/stock_ejemplo.csv",
      "public/ejemplos/compras_ejemplo.csv",
    ]);
  await expect(page.getByTestId("nombre-farmacia")).toBeVisible();
  await page.getByTestId("nombre-farmacia").fill("Farmacia Ejemplo Real");
  await page.getByTestId("analizar").click();
  await page.waitForURL("**/lunes");
  await expect(page.getByRole("status")).toContainText("Análisis completado");
  await expect(page.getByTestId("progreso")).toContainText("0 de");
  await expect(page.getByTestId("progreso")).not.toContainText("de 40");
  // Marcar una acción del análisis real no afecta a la demo.
  await page
    .getByTestId("lista-acciones")
    .locator("li[data-action-id]")
    .first()
    .getByRole("button", { name: /Marcar como hecha/ })
    .click();
  await page.goto("/ajustes");
  await expect(page.getByTestId("origen-datos")).toContainText("Motor local");
  await expect(page.getByTestId("origen-datos")).toContainText("Farmacia Ejemplo Real");
  await expectAccessible(page);
  await page.getByRole("button", { name: "Ver la demo" }).click();
  await expect(page.getByTestId("origen-datos")).toContainText("Demostración");
  await page.goto("/lunes");
  await expect(page.getByTestId("progreso")).toContainText("0 de 40 hechas");
});

test("productos: tabla virtualizada con 8.000 referencias", async ({ page }) => {
  await startDemo(page);
  await page.goto("/productos");
  await expect(page.getByTestId("productos-resumen")).toContainText("8.000 productos");
  const rendered = await page.locator('[role="row"][aria-rowindex]').count();
  expect(rendered).toBeLessThan(80); // solo se pintan las filas visibles
  const t0 = Date.now();
  await page.getByRole("searchbox", { name: "Buscar productos" }).fill("solar");
  await expect(page.getByTestId("productos-resumen")).toContainText("de 8.000");
  expect(Date.now() - t0).toBeLessThan(3000);
  await page.locator('[role="row"][aria-rowindex="2"]').click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("ajustes y reinicio de la demo", async ({ page }) => {
  await startDemo(page);
  await page
    .getByTestId("lista-acciones")
    .locator("li[data-action-id]")
    .first()
    .getByRole("button", { name: /Marcar como hecha/ })
    .click();
  await page.goto("/ajustes");
  await expectAccessible(page);
  await page.getByTestId("reiniciar-demo").click();
  await page.getByRole("dialog").getByRole("button", { name: "Reiniciar" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await expect(page.getByTestId("ver-demo")).toBeVisible();
  await page.goto("/lunes");
  await expect(page.getByTestId("progreso")).toContainText("0 de 40 hechas");
});
