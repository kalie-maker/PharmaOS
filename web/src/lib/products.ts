import { normalizeText } from "./actions";
import type { Action, Product, Report } from "./types";

export type ProductSort = "valor" | "cobertura" | "sin_venta" | "nombre";

export interface ProductQuery {
  query: string;
  family: string; // "" = todas
  sort: ProductSort;
  onlyWithAction: boolean;
}

export function families(report: Report): string[] {
  return [...new Set(Object.values(report.productos).map((p) => p.familia))].sort((a, b) =>
    a.localeCompare(b, "es"),
  );
}

export function actionsByProduct(report: Report): Map<string, Action> {
  return new Map(report.acciones.map((a) => [a.producto_id, a]));
}

export function filterProducts(report: Report, q: ProductQuery, withAction: Map<string, Action>): Product[] {
  const words = normalizeText(q.query).split(/\s+/).filter(Boolean);
  const list = Object.values(report.productos).filter((p) => {
    if (q.family && p.familia !== q.family) return false;
    if (q.onlyWithAction && !withAction.has(p.codigo)) return false;
    if (!words.length) return true;
    const hay = normalizeText(`${p.nombre ?? ""} ${p.codigo} ${p.laboratorio ?? ""}`);
    return words.every((w) => hay.includes(w));
  });
  const by: Record<ProductSort, (a: Product, b: Product) => number> = {
    valor: (a, b) => (b.valor_stock ?? 0) - (a.valor_stock ?? 0),
    cobertura: (a, b) =>
      (b.dias_cobertura ?? Number.POSITIVE_INFINITY) - (a.dias_cobertura ?? Number.POSITIVE_INFINITY),
    sin_venta: (a, b) => (a.ultima_venta ?? "").localeCompare(b.ultima_venta ?? ""),
    nombre: (a, b) => (a.nombre ?? "").localeCompare(b.nombre ?? "", "es"),
  };
  return list.sort((a, b) => by[q.sort](a, b) || a.codigo.localeCompare(b.codigo));
}
