// Contrato report.json (v1). Fuente de verdad: stock-profit-os/docs/report-schema.json
export type ActionType = "DEVOLVER" | "BAJAR_PEDIDO" | "REPONER" | "CADUCA_PRONTO";
export type Urgency = "alta" | "media" | "baja";
export type Deadline = "hoy" | "esta_semana" | "proximo_pedido" | "antes_de";

export interface Step {
  concepto: string;
  valor: string;
}

export interface Action {
  id: string;
  tipo: ActionType;
  producto_id: string;
  titulo: string;
  motivo_1_linea: string;
  importe_eur: number;
  cantidad_sugerida: number;
  urgencia: Urgency;
  plazo: Deadline;
  plazo_fecha?: string;
  plazo_texto: string;
  calculo_explicado: { pasos: Step[]; formula: string; resultado: string };
}

export interface Product {
  codigo: string;
  nombre: string | null;
  familia: string;
  laboratorio: string | null;
  stock: number | null;
  coste: number | null;
  pvp: number | null;
  valor_stock: number | null;
  ventas_semanales_12: number[];
  dias_cobertura: number | null;
  ultima_venta: string | null;
  caducidad: string | null;
  abc: "A" | "B" | "C";
}

export interface WeekHistory {
  semana: string;
  fecha_inicio: string;
  encontrado_eur: number;
  ejecutado_eur: number;
  recuperado_eur: number;
  acciones_encontradas: number;
  acciones_ejecutadas: number;
}

export type PerType<T> = Record<ActionType, T>;

export interface Report {
  version: 1;
  generado_por: string;
  farmacia: {
    nombre: string;
    fecha_datos: string;
    semana: string;
    programa: string | null;
    ficticia: boolean;
  };
  resumen: {
    capital_inmovilizado_eur: number;
    referencias_inmovilizadas: number;
    stock_total_eur: number;
    recuperable_semana_eur: number;
    acciones_total: number;
    acciones_por_tipo: PerType<number>;
    importe_por_tipo: PerType<number>;
    umbral_sin_movimiento_dias: number;
  };
  acciones: Action[];
  productos: Record<string, Product>;
  historico_simulado: boolean;
  historico_semanas: WeekHistory[];
}

export const ACTION_TYPES: ActionType[] = ["CADUCA_PRONTO", "DEVOLVER", "BAJAR_PEDIDO", "REPONER"];

export const TYPE_LABEL: PerType<string> = {
  CADUCA_PRONTO: "Caduca pronto",
  DEVOLVER: "Devolver",
  BAJAR_PEDIDO: "Bajar pedido",
  REPONER: "Reponer",
};
