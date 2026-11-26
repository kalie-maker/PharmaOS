import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, type TestInfo } from "@playwright/test";

export const isMobile = (testInfo: TestInfo) => testInfo.project.name === "movil";

export async function startDemo(page: Page) {
  await page.goto("/demo");
  await page.waitForURL("**/lunes");
  await expect(page.getByTestId("recuperable")).toBeVisible();
}

/** Sin infracciones de accesibilidad graves ni críticas (WCAG 2.1 AA). */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.nodes.length} nodos · ${v.help}`)).toEqual([]);
}
