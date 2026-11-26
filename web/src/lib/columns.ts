// Detección de columnas con los mapeos del motor (generados desde los YAML, sin duplicarlos a mano).
import { ENGINE_CONFIG } from "@/generated/engineConfig";

export type Dataset = keyof typeof ENGINE_CONFIG.schemas; // "ventas" | "stock" | "compras"
export const DATASETS = Object.keys(ENGINE_CONFIG.schemas) as Dataset[];
export const DATASET_LABEL: Record<Dataset, string> = {
  ventas: "Ventas",
  stock: "Stock",
  compras: "Compras",
};

/** Igual que engine.config.normalize_label: minúsculas, sin tildes ni puntuación. */
export function normalizeLabel(text: unknown): string {
  return String(text ?? "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

type Aliases = Record<string, readonly string[]>;

function rawAliases(dataset: Dataset, program: string): Set<string> {
  const mapping = ENGINE_CONFIG.mappings[program as keyof typeof ENGINE_CONFIG.mappings];
  const files = mapping?.ficheros as Record<string, Aliases> | undefined;
  return new Set(Object.values(files?.[dataset] ?? {}).flat());
}

function aliasesFor(dataset: Dataset, program?: string): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  const add = (canonical: string, labels: readonly string[]) => {
    const set = out.get(canonical) ?? new Set<string>();
    labels.forEach((l) => set.add(normalizeLabel(l)));
    out.set(canonical, set);
  };
  const programs = program ? [program] : Object.keys(ENGINE_CONFIG.mappings);
  for (const name of programs) {
    const mapping = ENGINE_CONFIG.mappings[name as keyof typeof ENGINE_CONFIG.mappings];
    const files = mapping?.ficheros as Record<string, Aliases> | undefined;
    for (const [canonical, labels] of Object.entries(files?.[dataset] ?? {})) add(canonical, labels);
  }
  if (!program) {
    const syn = ENGINE_CONFIG.synonyms as Aliases;
    for (const canonical of ENGINE_CONFIG.schemas[dataset].columns) add(canonical, syn[canonical] ?? []);
  }
  return out;
}

export interface ColumnMatch {
  canonical: string;
  column: string | null;
  required: boolean;
}

export interface Detection {
  dataset: Dataset;
  program: string | null; // programa cuyo mapeo encaja mejor
  matches: ColumnMatch[];
  missingRequired: string[];
  score: number;
}

function matchDataset(headers: string[], dataset: Dataset, program?: string): ColumnMatch[] {
  const aliases = aliasesFor(dataset, program);
  const normalized = headers.map((h) => normalizeLabel(h));
  const used = new Set<number>();
  const schema = ENGINE_CONFIG.schemas[dataset];
  return schema.columns.map((canonical) => {
    const accepted = aliases.get(canonical) ?? new Set();
    const index = normalized.findIndex((h, i) => !used.has(i) && accepted.has(h));
    if (index >= 0) used.add(index);
    return {
      canonical,
      column: index >= 0 ? headers[index]! : null,
      required: (schema.required as readonly string[]).includes(canonical),
    };
  });
}

function scoreOf(matches: ColumnMatch[]): number {
  const req = matches.filter((m) => m.required);
  return (
    req.filter((m) => m.column).length / req.length +
    0.01 * matches.filter((m) => !m.required && m.column).length
  );
}

/** Elige tipo de fichero y programa por cobertura de columnas obligatorias (y el nombre del fichero si empata). */
export function detectColumns(headers: string[], filename = ""): Detection {
  const name = normalizeLabel(filename);
  const hint: Dataset | undefined = name.includes("venta")
    ? "ventas"
    : /stock|existencia|inventario/.test(name)
      ? "stock"
      : /compra|albaran|entrada/.test(name)
        ? "compras"
        : undefined;
  let best: Detection | null = null;
  for (const dataset of DATASETS) {
    for (const program of [...Object.keys(ENGINE_CONFIG.mappings), undefined]) {
      const matches = matchDataset(headers, dataset, program);
      // Desempate entre programas: cabeceras escritas exactamente como en su mapeo.
      const literal = program ? headers.filter((h) => rawAliases(dataset, program).has(h)).length : 0;
      const score =
        scoreOf(matches) + (dataset === hint ? 0.05 : 0) + (program ? 0.001 + 0.0001 * literal : 0);
      if (!best || score > best.score) {
        best = {
          dataset,
          program: program ?? null,
          matches,
          missingRequired: matches.filter((m) => m.required && !m.column).map((m) => m.canonical),
          score,
        };
      }
    }
  }
  return best!;
}

/** Etiquetas conocidas (para encontrar la fila de cabecera). */
export function knownLabels(): Set<string> {
  const out = new Set<string>();
  for (const dataset of DATASETS) aliasesFor(dataset).forEach((set) => set.forEach((l) => out.add(l)));
  return out;
}
