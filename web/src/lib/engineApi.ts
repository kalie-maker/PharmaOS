// Cliente de la API local del motor (stock-profit-os/engine/api.py).
import type { Report } from "./types";

export const MOTOR_URL = (process.env.NEXT_PUBLIC_MOTOR_URL ?? "http://localhost:8000").replace(/\/$/, "");

export interface PrivacyHit {
  fichero: string;
  columna: string;
  categoria: string;
  motivo: string;
  coincidencias: number;
}

export class EngineError extends Error {
  constructor(
    public readonly kind:
      "conexion" | "privacidad" | "datos" | "fichero" | "configuracion" | "sin_informe" | "desconocido",
    message: string,
    public readonly hits: PrivacyHit[] = [],
  ) {
    super(message);
  }
}

export interface AnalyzeResult {
  farmacia: Report["farmacia"];
  resumen: Report["resumen"];
  calidad: { nivel: "buena" | "aceptable" | "baja"; mensaje: string };
  avisos: string[];
}

type Fetch = typeof fetch;

async function request(
  path: string,
  init: RequestInit = {},
  fetchImpl: Fetch = fetch,
  timeoutMs = 120_000,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchImpl(`${MOTOR_URL}${path}`, { ...init, signal: controller.signal });
  } catch {
    throw new EngineError(
      "conexion",
      "No se puede conectar con el motor local. ¿Está arrancado (npm run motor)?",
    );
  } finally {
    clearTimeout(timer);
  }
}

async function fail(res: Response): Promise<never> {
  let body: { tipo?: string; mensaje?: string; hallazgos?: PrivacyHit[] } = {};
  try {
    body = await res.json();
  } catch {
    /* respuesta sin JSON */
  }
  const kinds = ["privacidad", "datos", "fichero", "configuracion", "sin_informe"] as const;
  const kind = kinds.find((k) => k === body.tipo) ?? "desconocido";
  throw new EngineError(kind, body.mensaje ?? `Error del motor (${res.status})`, body.hallazgos ?? []);
}

export async function isEngineUp(fetchImpl: Fetch = fetch): Promise<boolean> {
  try {
    const res = await request("/salud", {}, fetchImpl, 1500);
    return res.ok;
  } catch {
    return false;
  }
}

export async function analyzeFiles(
  files: { ventas: File; stock: File; compras: File },
  programa: string,
  farmacia: string,
  fetchImpl: Fetch = fetch,
): Promise<AnalyzeResult> {
  const form = new FormData();
  form.append("ventas", files.ventas);
  form.append("stock", files.stock);
  form.append("compras", files.compras);
  form.append("programa", programa);
  form.append("farmacia", farmacia);
  const res = await request("/analizar", { method: "POST", body: form }, fetchImpl);
  if (!res.ok) return fail(res);
  return (await res.json()) as AnalyzeResult;
}

export async function fetchEngineReport(core: boolean, fetchImpl: Fetch = fetch): Promise<Report> {
  const res = await request(`/informe${core ? "?nucleo=true" : ""}`, { cache: "no-store" }, fetchImpl);
  if (!res.ok) return fail(res);
  return (await res.json()) as Report;
}

export async function deleteEngineReport(fetchImpl: Fetch = fetch): Promise<void> {
  const res = await request("/informe", { method: "DELETE" }, fetchImpl);
  if (!res.ok) return fail(res);
}
