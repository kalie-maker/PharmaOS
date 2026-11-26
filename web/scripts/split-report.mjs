// Deriva public/mock/report-core.json (ligero) de public/mock/report.json (completo).
// El núcleo es un report.json válido con solo los productos que tienen acción esta semana:
// lo usan todas las pantallas. El catálogo completo se carga bajo demanda en /productos.
import { readFileSync, writeFileSync } from "node:fs";

const dir = new URL("../public/mock/", import.meta.url);
const full = JSON.parse(readFileSync(new URL("report.json", dir), "utf-8"));
const ids = new Set(full.acciones.map((a) => a.producto_id));
const core = {
  ...full,
  productos: Object.fromEntries(Object.entries(full.productos).filter(([id]) => ids.has(id))),
};
writeFileSync(new URL("report-core.json", dir), JSON.stringify(core));
process.stdout.write(
  `report-core.json: ${Object.keys(core.productos).length} productos (de ${Object.keys(full.productos).length})\n`,
);
