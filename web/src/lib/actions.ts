// Lógica pura de la lista del lunes: ordenación, filtros, búsqueda y resumen.
import type { ActionRecords, ActionStatus } from "./actionStore";
import { statusOf } from "./actionStore";
import type { Action, ActionType, PerType, Report } from "./types";
import { ACTION_TYPES } from "./types";

export type TypeFilter = ActionType | "TODAS";

const URGENCY_RANK = { alta: 0, media: 1, baja: 2 } as const;

/** Orden por € descendente; desempate por urgencia e id (estable y determinista). */
export function sortActions(actions: Action[]): Action[] {
  return [...actions].sort(
    (a, b) =>
      b.importe_eur - a.importe_eur ||
      URGENCY_RANK[a.urgencia] - URGENCY_RANK[b.urgencia] ||
      a.id.localeCompare(b.id),
  );
}

export function normalizeText(text: string): string {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

export function matchesQuery(action: Action, report: Report, query: string): boolean {
  const q = normalizeText(query);
  if (!q) return true;
  const product = report.productos[action.producto_id];
  const haystack = normalizeText(
    [
      action.titulo,
      action.motivo_1_linea,
      action.producto_id,
      product?.laboratorio ?? "",
      product?.familia ?? "",
    ].join(" "),
  );
  return q.split(/\s+/).every((word) => haystack.includes(word));
}

export interface ListState {
  type: TypeFilter;
  query: string;
}

export interface Grouped {
  pending: Action[];
  postponed: Action[];
  done: Action[];
  dismissed: Action[];
}

export function groupActions(report: Report, records: ActionRecords, state: ListState): Grouped {
  const out: Grouped = { pending: [], postponed: [], done: [], dismissed: [] };
  const key: Record<ActionStatus, keyof Grouped> = {
    pendiente: "pending",
    pospuesta: "postponed",
    hecha: "done",
    descartada: "dismissed",
  };
  for (const action of sortActions(report.acciones)) {
    if (state.type !== "TODAS" && action.tipo !== state.type) continue;
    if (!matchesQuery(action, report, state.query)) continue;
    out[key[statusOf(records, action.id)]].push(action);
  }
  return out;
}

/** Contador por tipo de las acciones aún abiertas (pendientes + pospuestas), respetando la búsqueda. */
export function countOpenByType(
  report: Report,
  records: ActionRecords,
  query: string,
): PerType<number> & { TODAS: number } {
  const counts = { TODAS: 0, CADUCA_PRONTO: 0, DEVOLVER: 0, BAJAR_PEDIDO: 0, REPONER: 0 };
  for (const a of report.acciones) {
    const s = statusOf(records, a.id);
    if (s === "hecha" || s === "descartada" || !matchesQuery(a, report, query)) continue;
    counts[a.tipo] += 1;
    counts.TODAS += 1;
  }
  return counts;
}

export interface WeekProgress {
  total: number;
  done: number;
  dismissed: number;
  open: number;
  recoverable: number; // todo lo encontrado esta semana
  recovered: number; // importe de las hechas
  openAmount: number;
}

export function weekProgress(report: Report, records: ActionRecords): WeekProgress {
  let done = 0;
  let dismissed = 0;
  let recovered = 0;
  let openAmount = 0;
  for (const a of report.acciones) {
    const s = statusOf(records, a.id);
    if (s === "hecha") {
      done += 1;
      recovered += a.importe_eur;
    } else if (s === "descartada") dismissed += 1;
    else openAmount += a.importe_eur;
  }
  const total = report.acciones.length;
  return {
    total,
    done,
    dismissed,
    open: total - done - dismissed,
    recoverable: report.resumen.recuperable_semana_eur,
    recovered: round2(recovered),
    openAmount: round2(openAmount),
  };
}

export function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export { ACTION_TYPES };
