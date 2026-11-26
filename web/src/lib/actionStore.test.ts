import { createLocalStorageActionStore, createMemoryActionStore, statusOf, withStatus } from "./actionStore";

class FakeStorage implements Storage {
  data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  clear() {
    this.data.clear();
  }
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  key(i: number) {
    return [...this.data.keys()][i] ?? null;
  }
  removeItem(k: string) {
    this.data.delete(k);
  }
  setItem(k: string, v: string) {
    this.data.set(k, v);
  }
}

class BrokenStorage extends FakeStorage {
  override getItem(): string | null {
    throw new Error("bloqueado");
  }
  override setItem(): void {
    throw new Error("cuota");
  }
}

describe("ActionStore", () => {
  it("guarda y recupera por semana", () => {
    const storage = new FakeStorage();
    const store = createLocalStorageActionStore(storage);
    store.save("2026-W47", withStatus({}, "a", "hecha", new Date("2026-11-23T09:00:00Z")));
    expect(createLocalStorageActionStore(storage).load("2026-W47")).toEqual({
      a: { status: "hecha", at: "2026-11-23T09:00:00.000Z" },
    });
    expect(store.load("2026-W48")).toEqual({});
  });
  it("si localStorage falla, sigue funcionando en memoria", () => {
    const store = createLocalStorageActionStore(new BrokenStorage());
    store.save("w", withStatus({}, "a", "pospuesta"));
    expect(statusOf(store.load("w"), "a")).toBe("pospuesta");
  });
  it("ignora datos corruptos", () => {
    const storage = new FakeStorage();
    storage.setItem("pharmaos:acciones:w", JSON.stringify({ a: { status: "rara", at: 1 } }));
    expect(createLocalStorageActionStore(storage).load("w")).toEqual({});
    storage.setItem("pharmaos:acciones:w", "{no es json");
    expect(createLocalStorageActionStore(storage).load("w")).toEqual({});
  });
  it("clear borra solo las acciones", () => {
    const storage = new FakeStorage();
    storage.setItem("pharmaos:ajustes", "{}");
    const store = createLocalStorageActionStore(storage);
    store.save("w", withStatus({}, "a", "hecha"));
    store.clear();
    expect(storage.getItem("pharmaos:acciones:w")).toBeNull();
    expect(storage.getItem("pharmaos:ajustes")).toBe("{}");
  });
  it("volver a pendiente elimina el registro", () => {
    const r = withStatus(withStatus({}, "a", "hecha"), "a", "pendiente");
    expect(r).toEqual({});
    expect(statusOf(r, "a")).toBe("pendiente");
  });
  it("memoria aislada por semana", () => {
    const m = createMemoryActionStore();
    m.save("w1", { a: { status: "hecha", at: "x" } });
    expect(m.load("w2")).toEqual({});
  });
});
