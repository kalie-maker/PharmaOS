// Exportaciones: lista de devolución, pedido corregido y datos del resumen semanal.
import type { ActionRecords } from "./actionStore";
import { statusOf } from "./actionStore";
import { sortActions, round2, weekProgress } from "./actions";
import { toCsv } from "./csv";
import type { Action, Report } from "./types";

export interface ReturnLine {
  codigo: string;
  producto: string;
  laboratorio: string;
  unidades: number;
  importe: number;
  estado: string;
}

/** Devoluciones de la semana (todas salvo las descartadas), agrupables por laboratorio. */
export function returnLines(report: Report, records: ActionRecords): ReturnLine[] {
  return sortActions(report.acciones)
    .filter((a) => a.tipo === "DEVOLVER" && statusOf(records, a.id) !== "descartada")
    .map((a) => {
      const p = report.productos[a.producto_id];
      return {
        codigo: a.producto_id,
        producto: p?.nombre ?? a.titulo,
        laboratorio: p?.laboratorio ?? "Sin laboratorio",
        unidades: a.cantidad_sugerida,
        importe: a.importe_eur,
        estado: statusOf(records, a.id) === "hecha" ? "Hecha" : "Pendiente",
      };
    })
    .sort((x, y) => x.laboratorio.localeCompare(y.laboratorio, "es") || y.importe - x.importe);
}

export function returnTotal(lines: ReturnLine[]): number {
  return round2(lines.reduce((s, l) => s + l.importe, 0));
}

export function returnCsv(report: Report, records: ActionRecords): string {
  const lines = returnLines(report, records);
  return toCsv(
    ["Código nacional", "Producto", "Laboratorio", "Unidades", "Importe a coste (€)", "Estado"],
    [
      ...lines.map((l) => [l.codigo, l.producto, l.laboratorio, l.unidades, round2(l.importe), l.estado]),
      ["", "TOTAL", "", lines.reduce((s, l) => s + l.unidades, 0), returnTotal(lines), ""],
    ],
  );
}

export interface OrderLine {
  codigo: string;
  producto: string;
  laboratorio: string;
  accion: "No pedir" | "Pedir";
  cantidad: number;
  motivo: string;
}

/** Pedido corregido: qué no pedir (sobrestock) y qué pedir (riesgo de rotura). */
export function orderLines(report: Report, records: ActionRecords): OrderLine[] {
  const relevant = (a: Action) =>
    (a.tipo === "BAJAR_PEDIDO" || a.tipo === "REPONER") && statusOf(records, a.id) !== "descartada";
  return sortActions(report.acciones)
    .filter(relevant)
    .map((a) => {
      const p = report.productos[a.producto_id];
      return {
        codigo: a.producto_id,
        producto: p?.nombre ?? a.titulo,
        laboratorio: p?.laboratorio ?? "Sin laboratorio",
        accion: a.tipo === "REPONER" ? ("Pedir" as const) : ("No pedir" as const),
        cantidad: a.cantidad_sugerida,
        motivo: a.motivo_1_linea,
      };
    })
    .sort((x, y) => x.accion.localeCompare(y.accion) || x.laboratorio.localeCompare(y.laboratorio, "es"));
}

export function orderCsv(report: Report, records: ActionRecords): string {
  return toCsv(
    ["Código nacional", "Producto", "Laboratorio", "Acción", "Unidades", "Motivo"],
    orderLines(report, records).map((l) => [
      l.codigo,
      l.producto,
      l.laboratorio,
      l.accion,
      l.cantidad,
      l.motivo,
    ]),
  );
}

export function weeklySummary(report: Report, records: ActionRecords) {
  const progress = weekProgress(report, records);
  const top = sortActions(report.acciones).slice(0, 10);
  return { progress, top };
}

export function exportFilename(base: string, report: Report): string {
  return `${base}_${report.farmacia.fecha_datos}.csv`;
}
