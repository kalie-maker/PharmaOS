import { countOpenByType, groupActions, matchesQuery, sortActions, weekProgress } from "./actions";
import { withStatus } from "./actionStore";
import { SAMPLE } from "@/test/fixtures";

describe("ordenación", () => {
  it("ordena por € desc y desempata por urgencia e id", () => {
    const ids = sortActions(SAMPLE.acciones).map((a) => a.id);
    expect(ids).toEqual([
      "bajar_pedido-100002",
      "devolver-100005",
      "devolver-100001",
      "caduca_pronto-100004",
      "reponer-100003",
    ]);
  });
  it("no modifica el array original", () => {
    const before = SAMPLE.acciones.map((a) => a.id);
    sortActions(SAMPLE.acciones);
    expect(SAMPLE.acciones.map((a) => a.id)).toEqual(before);
  });
});

describe("filtros y búsqueda", () => {
  it("filtra por tipo", () => {
    const g = groupActions(SAMPLE, {}, { type: "DEVOLVER", query: "" });
    expect(g.pending.map((a) => a.tipo)).toEqual(["DEVOLVER", "DEVOLVER"]);
  });
  it("busca sin tildes ni mayúsculas, por título, CN o laboratorio", () => {
    expect(matchesQuery(SAMPLE.acciones[1]!, SAMPLE, "CREMA spf")).toBe(true);
    expect(matchesQuery(SAMPLE.acciones[0]!, SAMPLE, "100001")).toBe(true);
    expect(matchesQuery(SAMPLE.acciones[0]!, SAMPLE, "lab 100001")).toBe(true);
    expect(matchesQuery(SAMPLE.acciones[0]!, SAMPLE, "inexistente")).toBe(false);
  });
  it("agrupa por estado", () => {
    let r = withStatus({}, "devolver-100001", "hecha");
    r = withStatus(r, "reponer-100003", "pospuesta");
    r = withStatus(r, "caduca_pronto-100004", "descartada");
    const g = groupActions(SAMPLE, r, { type: "TODAS", query: "" });
    expect(g.pending).toHaveLength(2);
    expect(g.postponed.map((a) => a.id)).toEqual(["reponer-100003"]);
    expect(g.done.map((a) => a.id)).toEqual(["devolver-100001"]);
    expect(g.dismissed.map((a) => a.id)).toEqual(["caduca_pronto-100004"]);
  });
  it("cuenta abiertas por tipo (pendientes + pospuestas)", () => {
    const r = withStatus(withStatus({}, "devolver-100001", "hecha"), "reponer-100003", "pospuesta");
    const c = countOpenByType(SAMPLE, r, "");
    expect(c).toEqual({ TODAS: 4, DEVOLVER: 1, BAJAR_PEDIDO: 1, REPONER: 1, CADUCA_PRONTO: 1 });
  });
});

describe("progreso semanal", () => {
  it("suma lo recuperado de las hechas", () => {
    const r = withStatus(withStatus({}, "devolver-100001", "hecha"), "bajar_pedido-100002", "descartada");
    const p = weekProgress(SAMPLE, r);
    expect(p).toMatchObject({
      total: 5,
      done: 1,
      dismissed: 1,
      open: 3,
      recovered: 250,
      openAmount: 450,
      recoverable: 1100,
    });
  });
});
