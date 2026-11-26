// Lectura de CSV/XLSX en el navegador. El fichero no sale del ordenador.
import Papa from "papaparse";
import { detectColumns, knownLabels, normalizeLabel, type Detection } from "./columns";
import { validatePrivacy, type PrivacyFinding } from "./privacy";

export interface ParsedFile {
  name: string;
  kind: "csv" | "xlsx";
  encoding?: string;
  sheet?: string;
  headerRow: number; // 1-based
  headers: string[];
  rows: unknown[][];
}

export interface FileAnalysis {
  file: ParsedFile;
  privacy: PrivacyFinding[];
  detection: Detection;
  summary: { rows: number; products: number; dateFrom: string | null; dateTo: string | null };
}

export class FileError extends Error {}

const MAX_BYTES = 50 * 1024 * 1024;

export function decodeText(buffer: ArrayBuffer): { text: string; encoding: string } {
  try {
    return {
      text: new TextDecoder("utf-8", { fatal: true }).decode(buffer).replace(/^﻿/, ""),
      encoding: "UTF-8",
    };
  } catch {
    return { text: new TextDecoder("windows-1252").decode(buffer), encoding: "Windows-1252" };
  }
}

/** Fila de cabecera: la que más coincide con etiquetas conocidas; si no, la primera "ancha" con texto. */
export function findHeaderRow(rows: unknown[][]): number {
  const known = knownLabels();
  const scan = rows.slice(0, 30);
  let best = -1;
  let bestScore = 1;
  scan.forEach((row, i) => {
    const score = row.filter((c) => known.has(normalizeLabel(c))).length;
    if (score > bestScore) {
      best = i;
      bestScore = score;
    }
  });
  if (best >= 0) return best;
  const width = Math.max(0, ...scan.map((r) => r.filter((c) => String(c ?? "").trim()).length));
  const index = scan.findIndex((r) => {
    const filled = r.filter((c) => String(c ?? "").trim());
    return (
      filled.length >= Math.max(2, width * 0.6) &&
      filled.filter((c) => Number.isNaN(Number(String(c).replace(",", ".")))).length / filled.length >= 0.6
    );
  });
  return Math.max(0, index);
}

function table(raw: unknown[][]): { headerRow: number; headers: string[]; rows: unknown[][] } {
  const nonEmpty = (r: unknown[]) => r.some((c) => String(c ?? "").trim() !== "");
  const headerRow = findHeaderRow(raw);
  const headers = (raw[headerRow] ?? []).map((h, i) => String(h ?? "").trim() || `Columna ${i + 1}`);
  const rows = raw.slice(headerRow + 1).filter(nonEmpty);
  return { headerRow: headerRow + 1, headers, rows };
}

function readBuffer(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === "function") return file.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(new FileError("No se ha podido leer el fichero."));
    reader.readAsArrayBuffer(file);
  });
}

export async function parseFile(file: File): Promise<ParsedFile> {
  if (file.size > MAX_BYTES) throw new FileError("El fichero supera 50 MB. Exporta un periodo más corto.");
  const lower = file.name.toLowerCase();
  if (lower.endsWith(".xls")) throw new FileError("Formato .xls antiguo: guárdalo como .xlsx o CSV.");
  const buffer = await readBuffer(file);
  if (lower.endsWith(".xlsx") || lower.endsWith(".xlsm")) {
    const XLSX = await import("xlsx");
    const wb = XLSX.read(buffer, { type: "array", cellDates: true });
    let best: { sheet: string; t: ReturnType<typeof table>; score: number } | null = null;
    const known = knownLabels();
    for (const sheet of wb.SheetNames) {
      const ws = wb.Sheets[sheet];
      if (!ws) continue;
      const raw = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, raw: true, defval: "" });
      const t = table(raw);
      const score = t.headers.filter((h) => known.has(normalizeLabel(h))).length * 1000 + t.rows.length;
      if (!best || score > best.score) best = { sheet, t, score };
    }
    if (!best || best.t.rows.length === 0) throw new FileError("El Excel no tiene ninguna hoja con datos.");
    return { name: file.name, kind: "xlsx", sheet: best.sheet, ...best.t };
  }
  const { text, encoding } = decodeText(buffer);
  const parsed = Papa.parse<unknown[]>(text, {
    delimitersToGuess: [";", "\t", ",", "|"],
    skipEmptyLines: false,
  });
  if (!parsed.data.length) throw new FileError("El fichero está vacío.");
  return { name: file.name, kind: "csv", encoding, ...table(parsed.data) };
}

const DATE_RE = [/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})/, /^(\d{4})-(\d{2})-(\d{2})/];

export function toIsoDate(value: unknown): string | null {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value.toISOString().slice(0, 10);
  const text = String(value ?? "").trim();
  const es = DATE_RE[0]!.exec(text);
  if (es) {
    const [, d, m, y] = es;
    const year = y!.length === 2 ? 2000 + Number(y) : Number(y);
    if (Number(m) >= 1 && Number(m) <= 12 && Number(d) >= 1 && Number(d) <= 31)
      return `${year}-${m!.padStart(2, "0")}-${d!.padStart(2, "0")}`;
  }
  const iso = DATE_RE[1]!.exec(text);
  return iso ? `${iso[1]}-${iso[2]}-${iso[3]}` : null;
}

export function analyzeParsed(file: ParsedFile): FileAnalysis {
  const privacy = validatePrivacy(file.headers, file.rows);
  const detection = detectColumns(file.headers, file.name);
  const col = (canonical: string) => {
    const name = detection.matches.find((m) => m.canonical === canonical)?.column;
    return name ? file.headers.indexOf(name) : -1;
  };
  const codeCol = col("codigo_nacional");
  const dateCol = col("fecha");
  const products =
    codeCol >= 0 ? new Set(file.rows.map((r) => String(r[codeCol] ?? "").trim()).filter(Boolean)).size : 0;
  let dateFrom: string | null = null;
  let dateTo: string | null = null;
  if (dateCol >= 0) {
    for (const r of file.rows) {
      const iso = toIsoDate(r[dateCol]);
      if (!iso) continue;
      if (!dateFrom || iso < dateFrom) dateFrom = iso;
      if (!dateTo || iso > dateTo) dateTo = iso;
    }
  }
  return { file, privacy, detection, summary: { rows: file.rows.length, products, dateFrom, dateTo } };
}
