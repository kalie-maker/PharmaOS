import { withStatus } from "./actionStore";
import { executedThisWeek, totals, weeks } from "./recovered";
import { SAMPLE } from "@/test/fixtures";

describe("recuperado", () => {
  it("añade la semana en curso con lo marcado como hecho", () => {
    const records = withStatus({}, "bajar_pedido-100002", "hecha", new Date("2026-11-23T10:00:00Z"));
    const rows = weeks(SAMPLE, records);
    expect(rows).toHaveLength(2);
    expect(rows[1]).toMatchObject({
      semana: "2026-W47",
      encontrado: 1100,
      ejecutado: 400,
      recuperado: 400,
      enCurso: true,
    });
  });
  it("calcula el múltiplo frente al coste del periodo y la garantía ×3", () => {
    const rows = weeks(SAMPLE, withStatus({}, "bajar_pedido-100002", "hecha"));
    const t = totals(rows, 149);
    expect(t.recuperado).toBe(900);
    expect(t.coste).toBeCloseTo(149 * (14 / 30.44), 1);
    expect(t.multiplo).toBeCloseTo(900 / t.coste, 1);
    expect(t.cumpleGarantia).toBe(true);
    expect(totals(rows, 2000).cumpleGarantia).toBe(false);
    expect(totals(rows, 0).multiplo).toBe(0);
  });
  it("lista las acciones hechas esta semana, la más reciente primero", () => {
    let r = withStatus({}, "devolver-100001", "hecha", new Date("2026-11-23T09:00:00Z"));
    r = withStatus(r, "reponer-100003", "hecha", new Date("2026-11-23T11:00:00Z"));
    r = withStatus(r, "caduca_pronto-100004", "pospuesta");
    expect(executedThisWeek(SAMPLE, r).map((e) => e.action.id)).toEqual([
      "reponer-100003",
      "devolver-100001",
    ]);
  });
});
