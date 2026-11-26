// Formato español: 1.234,56 €. Intl con es-ES no agrupa miles en números de 4 cifras, así que se agrupa a mano.
function group(intPart: string): string {
  return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function formatNumber(value: number | null | undefined, decimals = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const negative = value < 0;
  const [intPart = "0", dec] = Math.abs(value).toFixed(decimals).split(".");
  return `${negative ? "−" : ""}${group(intPart)}${dec ? "," + dec : ""}`;
}

export function formatEur(value: number | null | undefined, decimals = 0): string {
  const n = formatNumber(value, decimals);
  return n === "—" ? n : `${n} €`;
}

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MONTHS_LONG = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

function parseIso(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1));
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = parseIso(iso);
  return `${String(d.getUTCDate()).padStart(2, "0")}/${String(d.getUTCMonth() + 1).padStart(2, "0")}/${d.getUTCFullYear()}`;
}

export function formatShortDate(iso: string): string {
  const d = parseIso(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

export function formatLongDate(iso: string): string {
  const d = parseIso(iso);
  return `${d.getUTCDate()} de ${MONTHS_LONG[d.getUTCMonth()]} de ${d.getUTCFullYear()}`;
}

export function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((parseIso(toIso).getTime() - parseIso(fromIso).getTime()) / 86_400_000);
}

export function weekNumber(isoWeek: string): string {
  return isoWeek.split("-W")[1] ?? isoWeek;
}
