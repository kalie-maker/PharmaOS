import { DEFAULT_SETTINGS, loadSettings, saveSettings } from "./settings";

describe("ajustes", () => {
  beforeEach(() => window.localStorage.clear());
  it("por defecto 149 €/mes y sin onboarding", () => {
    expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
    expect(DEFAULT_SETTINGS.monthlyCost).toBe(149);
  });
  it("guarda y recupera", () => {
    saveSettings({ ...DEFAULT_SETTINGS, monthlyCost: 199, pharmacyName: "Farmacia Prueba" });
    expect(loadSettings()).toMatchObject({ monthlyCost: 199, pharmacyName: "Farmacia Prueba" });
  });
  it("ignora valores inválidos", () => {
    window.localStorage.setItem("pharmaos:ajustes", JSON.stringify({ monthlyCost: -5 }));
    expect(loadSettings().monthlyCost).toBe(149);
    window.localStorage.setItem("pharmaos:ajustes", "{roto");
    expect(loadSettings()).toEqual(DEFAULT_SETTINGS);
  });
});
