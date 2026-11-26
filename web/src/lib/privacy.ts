// Validador de privacidad en cliente: mismas reglas que engine/privacy.py (generadas).
import { ENGINE_CONFIG } from "@/generated/engineConfig";
import { normalizeLabel } from "./columns";

export interface PrivacyFinding {
  column: string;
  category: string;
  reason: string;
  source: "cabecera" | "contenido";
  matches: number;
}

const HEADER_RULES = ENGINE_CONFIG.privacyHeaderRules.map((r) => ({ ...r, regex: new RegExp(r.pattern) }));
const full = (p: string) => new RegExp(`^(?:${p})$`, "i");
const DNI = full(ENGINE_CONFIG.privacyContent.dni);
const NIE = full(ENGINE_CONFIG.privacyContent.nie);
const EMAIL = full(ENGINE_CONFIG.privacyContent.email);
const PHONE = full(ENGINE_CONFIG.privacyContent.phone);
export const PHONE_MIN_RATIO = 0.2; // igual que config.yaml > privacidad.ratio_minimo_telefono

export function checkHeaders(headers: string[]): PrivacyFinding[] {
  const out: PrivacyFinding[] = [];
  for (const header of headers) {
    const norm = normalizeLabel(header);
    const rule = HEADER_RULES.find((r) => r.regex.test(norm));
    if (rule)
      out.push({
        column: header,
        category: rule.category,
        reason: rule.reason,
        source: "cabecera",
        matches: 0,
      });
  }
  return out;
}

/** Busca DNI/NIE, emails o teléfonos en los valores. Nunca devuelve los valores, solo recuentos. */
export function checkContent(
  headers: string[],
  rows: unknown[][],
  skip: Set<string> = new Set(),
): PrivacyFinding[] {
  const out: PrivacyFinding[] = [];
  headers.forEach((header, col) => {
    if (skip.has(header)) return;
    const values: string[] = [];
    for (const row of rows) {
      const v = row[col];
      if (typeof v === "string" && v.trim()) values.push(v.trim());
    }
    if (!values.length) return;
    const ids = values.filter((v) => DNI.test(v) || NIE.test(v)).length;
    if (ids)
      return void out.push({
        column: header,
        category: "dni_nie",
        reason: "posible documento de identidad",
        source: "contenido",
        matches: ids,
      });
    const emails = values.filter((v) => EMAIL.test(v)).length;
    if (emails)
      return void out.push({
        column: header,
        category: "email",
        reason: "posible correo electrónico",
        source: "contenido",
        matches: emails,
      });
    const phones = values.filter((v) => PHONE.test(v)).length;
    if (phones && phones / values.length >= PHONE_MIN_RATIO)
      out.push({
        column: header,
        category: "telefono",
        reason: "posible número de teléfono",
        source: "contenido",
        matches: phones,
      });
  });
  return out;
}

export function validatePrivacy(headers: string[], rows: unknown[][]): PrivacyFinding[] {
  const byHeader = checkHeaders(headers);
  return [...byHeader, ...checkContent(headers, rows, new Set(byHeader.map((f) => f.column)))];
}
