// El mock versionado cumple el contrato (JSON Schema del motor) y el núcleo es coherente con el completo.
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Report } from "./types";

const read = (p: string) => JSON.parse(readFileSync(resolve(__dirname, p), "utf-8"));
const schema = read("../../../stock-profit-os/docs/report-schema.json");
const full = read("../../public/mock/report.json") as Report;
const core = read("../../public/mock/report-core.json") as Report;

describe("mock de la web", () => {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validate = ajv.compile(schema);
  it.each([
    ["completo", full],
    ["núcleo", core],
  ])("el informe %s valida contra el JSON Schema", (_, report) => {
    expect(validate(report), JSON.stringify(validate.errors?.slice(0, 3))).toBe(true);
  });
  it("el núcleo tiene todas las acciones y sus productos, y es mucho más ligero", () => {
    expect(core.acciones).toEqual(full.acciones);
    expect(core.resumen).toEqual(full.resumen);
    for (const a of core.acciones)
      expect(core.productos[a.producto_id]).toEqual(full.productos[a.producto_id]);
    expect(Object.keys(core.productos).length).toBeLessThan(Object.keys(full.productos).length / 50);
  });
});
