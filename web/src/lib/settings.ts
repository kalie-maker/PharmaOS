import { STORAGE_PREFIX, readJson, writeJson } from "./storage";

export interface Settings {
  pharmacyName: string | null; // null = la del informe
  monthlyCost: number;
  onboarded: boolean;
  source: "demo" | "subido" | null;
}

export const DEFAULT_SETTINGS: Settings = {
  pharmacyName: null,
  monthlyCost: 149,
  onboarded: false,
  source: null,
};
const KEY = `${STORAGE_PREFIX}ajustes`;

export function loadSettings(): Settings {
  const stored = readJson<Partial<Settings>>(KEY, {});
  const cost = Number(stored.monthlyCost);
  return {
    ...DEFAULT_SETTINGS,
    ...stored,
    monthlyCost: Number.isFinite(cost) && cost > 0 ? cost : DEFAULT_SETTINGS.monthlyCost,
  };
}

export function saveSettings(settings: Settings): void {
  writeJson(KEY, settings);
}
