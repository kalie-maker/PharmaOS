// Informe mínimo y ficticio para tests unitarios (sin datos de pacientes).
import type { Action, Product, Report } from "@/lib/types";

export function product(codigo: string, extra: Partial<Product> = {}): Product {
  return {
    codigo,
    nombre: `Producto ${codigo}`,
    familia: "OTC",
    laboratorio: "Laboratorio Demo",
    stock: 10,
    coste: 5,
    pvp: 9,
    valor_stock: 50,
    ventas_semanales_12: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    dias_cobertura: 30,
    ultima_venta: "2026-11-19",
    caducidad: null,
    abc: "B",
    ...extra,
  };
}

export function action(
  id: string,
  tipo: Action["tipo"],
  importe: number,
  extra: Partial<Action> = {},
): Action {
  const code = id.split("-")[1] ?? id;
  return {
    id,
    tipo,
    producto_id: code,
    titulo: `${tipo} ${code}`,
    motivo_1_linea: "Motivo de prueba",
    importe_eur: importe,
    cantidad_sugerida: 3,
    urgencia: "media",
    plazo: "esta_semana",
    plazo_texto: "Esta semana",
    calculo_explicado: { pasos: [{ concepto: "Paso", valor: "1" }], formula: "f", resultado: "r" },
    ...extra,
  };
}

export function makeReport(actions: Action[]): Report {
  const productos: Record<string, Product> = {};
  for (const a of actions)
    productos[a.producto_id] = product(a.producto_id, { laboratorio: `Lab ${a.producto_id}` });
  const total = actions.reduce((s, a) => s + a.importe_eur, 0);
  return {
    version: 1,
    generado_por: "test",
    farmacia: {
      nombre: "Farmacia Test",
      fecha_datos: "2026-11-20",
      semana: "2026-W47",
      programa: "farmatic",
      ficticia: true,
    },
    resumen: {
      capital_inmovilizado_eur: 1000,
      referencias_inmovilizadas: 10,
      stock_total_eur: 5000,
      recuperable_semana_eur: total,
      acciones_total: actions.length,
      acciones_por_tipo: { DEVOLVER: 0, BAJAR_PEDIDO: 0, REPONER: 0, CADUCA_PRONTO: 0 },
      importe_por_tipo: { DEVOLVER: 0, BAJAR_PEDIDO: 0, REPONER: 0, CADUCA_PRONTO: 0 },
      umbral_sin_movimiento_dias: 180,
    },
    acciones: actions,
    productos,
    historico_simulado: true,
    historico_semanas: [
      {
        semana: "2026-W46",
        fecha_inicio: "2026-11-13",
        encontrado_eur: 1000,
        ejecutado_eur: 600,
        recuperado_eur: 500,
        acciones_encontradas: 10,
        acciones_ejecutadas: 6,
      },
    ],
  };
}

export const SAMPLE = makeReport([
  action("devolver-100001", "DEVOLVER", 250),
  action("bajar_pedido-100002", "BAJAR_PEDIDO", 400, { titulo: "Bajar pedido de Crema solar SPF50" }),
  action("reponer-100003", "REPONER", 80, { urgencia: "alta", plazo: "hoy", plazo_texto: "Hoy" }),
  action("caduca_pronto-100004", "CADUCA_PRONTO", 120),
  action("devolver-100005", "DEVOLVER", 250, { urgencia: "alta" }),
]);
