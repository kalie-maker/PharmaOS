// Lógica de /recuperado: semanas del piloto + semana en curso, totales y múltiplo frente al coste.
import type { ActionRecords } from "./actionStore";
import { round2, weekProgress } from "./actions";
import type { Action, Report } from "./types";

export const GUARANTEE_MULTIPLE = 3;
const DAYS_PER_MONTH = 30.44;

export interface WeekRow {
  semana: string;
  fecha_inicio: string;
  encontrado: number;
  ejecutado: number;
  recuperado: number;
  enCurso: boolean;
}

export function weeks(report: Report, records: ActionRecords): WeekRow[] {
  const history = report.historico_semanas.map((w) => ({
    semana: w.semana,
    fecha_inicio: w.fecha_inicio,
    encontrado: w.encontrado_eur,
    ejecutado: w.ejecutado_eur,
    recuperado: w.recuperado_eur,
    enCurso: false,
  }));
  const p = weekProgress(report, records);
  // Semana en curso: lo marcado como hecho cuenta como ejecutado y recuperado (se confirma con la semana siguiente).
  return [
    ...history,
    {
      semana: report.farmacia.semana,
      fecha_inicio: report.farmacia.fecha_datos,
      encontrado: p.recoverable,
      ejecutado: p.recovered,
      recuperado: p.recovered,
      enCurso: true,
    },
  ];
}

export interface Totals {
  encontrado: number;
  ejecutado: number;
  recuperado: number;
  semanas: number;
  meses: number;
  coste: number;
  multiplo: number;
  cumpleGarantia: boolean;
}

export function totals(rows: WeekRow[], monthlyCost: number): Totals {
  const sum = (k: "encontrado" | "ejecutado" | "recuperado") => round2(rows.reduce((s, r) => s + r[k], 0));
  const meses = (rows.length * 7) / DAYS_PER_MONTH;
  const coste = round2(Math.max(0, monthlyCost) * meses);
  const recuperado = sum("recuperado");
  const multiplo = coste > 0 ? Math.round((recuperado / coste) * 10) / 10 : 0;
  return {
    encontrado: sum("encontrado"),
    ejecutado: sum("ejecutado"),
    recuperado,
    semanas: rows.length,
    meses: Math.round(meses * 10) / 10,
    coste,
    multiplo,
    cumpleGarantia: multiplo >= GUARANTEE_MULTIPLE,
  };
}

export interface ExecutedAction {
  action: Action;
  at: string;
}

export function executedThisWeek(report: Report, records: ActionRecords): ExecutedAction[] {
  return report.acciones
    .filter((a) => records[a.id]?.status === "hecha")
    .map((a) => ({ action: a, at: records[a.id]!.at }))
    .sort((x, y) => y.at.localeCompare(x.at));
}
