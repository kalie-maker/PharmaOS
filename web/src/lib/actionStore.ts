// Estado de las acciones (hecha, pospuesta, descartada) detrás de una interfaz,
// para sustituir localStorage por Supabase sin tocar la interfaz de usuario.
import { STORAGE_PREFIX } from "./storage";

export type ActionStatus = "pendiente" | "hecha" | "pospuesta" | "descartada";

export interface ActionRecord {
  status: Exclude<ActionStatus, "pendiente">;
  at: string; // ISO
}

export type ActionRecords = Record<string, ActionRecord>;

export interface ActionStore {
  load(week: string): ActionRecords;
  save(week: string, records: ActionRecords): void;
  clear(): void;
}

const key = (week: string) => `${STORAGE_PREFIX}acciones:${week}`;

export function createMemoryActionStore(): ActionStore {
  const data = new Map<string, ActionRecords>();
  return {
    load: (week) => ({ ...(data.get(week) ?? {}) }),
    save: (week, records) => void data.set(week, { ...records }),
    clear: () => data.clear(),
  };
}

export function createLocalStorageActionStore(storage?: Storage): ActionStore {
  const memory = createMemoryActionStore();
  const get = (): Storage | null => {
    try {
      return storage ?? (typeof window !== "undefined" ? window.localStorage : null);
    } catch {
      return null;
    }
  };
  return {
    load(week) {
      try {
        const raw = get()?.getItem(key(week));
        if (!raw) return memory.load(week);
        const parsed = JSON.parse(raw) as unknown;
        return isRecords(parsed) ? parsed : {};
      } catch {
        return memory.load(week);
      }
    },
    save(week, records) {
      memory.save(week, records);
      try {
        get()?.setItem(key(week), JSON.stringify(records));
      } catch {
        /* sin almacenamiento: queda en memoria */
      }
    },
    clear() {
      memory.clear();
      try {
        const s = get();
        if (!s) return;
        const keys: string[] = [];
        for (let i = 0; i < s.length; i++) {
          const k = s.key(i);
          if (k?.startsWith(`${STORAGE_PREFIX}acciones:`)) keys.push(k);
        }
        keys.forEach((k) => s.removeItem(k));
      } catch {
        /* nada */
      }
    },
  };
}

const VALID = new Set(["hecha", "pospuesta", "descartada"]);

function isRecords(value: unknown): value is ActionRecords {
  if (!value || typeof value !== "object") return false;
  return Object.values(value as Record<string, unknown>).every(
    (r) =>
      !!r &&
      typeof r === "object" &&
      VALID.has((r as ActionRecord).status) &&
      typeof (r as ActionRecord).at === "string",
  );
}

export function statusOf(records: ActionRecords, id: string): ActionStatus {
  return records[id]?.status ?? "pendiente";
}

export function withStatus(
  records: ActionRecords,
  id: string,
  status: ActionStatus,
  now = new Date(),
): ActionRecords {
  const next = { ...records };
  if (status === "pendiente") delete next[id];
  else next[id] = { status, at: now.toISOString() };
  return next;
}
