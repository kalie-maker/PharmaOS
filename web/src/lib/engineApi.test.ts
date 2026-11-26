import { analyzeFiles, EngineError, fetchEngineReport, isEngineUp } from "./engineApi";
import { SAMPLE } from "@/test/fixtures";

const json = (status: number, body: unknown) =>
  Promise.resolve(
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
const files = () => ({
  ventas: new File(["a"], "v.csv"),
  stock: new File(["b"], "s.csv"),
  compras: new File(["c"], "c.csv"),
});

describe("cliente del motor local", () => {
  it("salud: true si responde, false si no hay conexión", async () => {
    expect(await isEngineUp(() => json(200, { estado: "ok" }))).toBe(true);
    expect(await isEngineUp(() => Promise.reject(new TypeError("fetch failed")))).toBe(false);
  });
  it("envía los 3 ficheros, el programa y la farmacia", async () => {
    let sent: FormData | null = null;
    const result = await analyzeFiles(files(), "nixfarma", "Farmacia Prueba", (url, init) => {
      expect(String(url)).toMatch(/\/analizar$/);
      sent = init?.body as FormData;
      return json(200, {
        farmacia: SAMPLE.farmacia,
        resumen: SAMPLE.resumen,
        calidad: { nivel: "buena", mensaje: "" },
        avisos: [],
      });
    });
    expect(result.resumen.acciones_total).toBe(5);
    const form = sent as unknown as FormData;
    expect(form.get("programa")).toBe("nixfarma");
    expect(form.get("farmacia")).toBe("Farmacia Prueba");
    expect((form.get("compras") as File).name).toBe("c.csv");
  });
  it("traduce el rechazo de privacidad con sus columnas", async () => {
    const error = await analyzeFiles(files(), "farmatic", "X", () =>
      json(422, {
        tipo: "privacidad",
        mensaje: "Fichero rechazado",
        hallazgos: [
          { fichero: "stock", columna: "DNI", categoria: "identidad", motivo: "documento", coincidencias: 0 },
        ],
      }),
    ).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(EngineError);
    expect((error as EngineError).kind).toBe("privacidad");
    expect((error as EngineError).hits[0]!.columna).toBe("DNI");
  });
  it("errores de conexión y de datos con mensaje claro", async () => {
    await expect(
      analyzeFiles(files(), "farmatic", "X", () => Promise.reject(new TypeError("x"))),
    ).rejects.toMatchObject({ kind: "conexion" });
    await expect(
      fetchEngineReport(true, () => json(404, { tipo: "sin_informe", mensaje: "Todavía no hay" })),
    ).rejects.toMatchObject({
      kind: "sin_informe",
      message: "Todavía no hay",
    });
    await expect(fetchEngineReport(true, () => json(500, "boom"))).rejects.toMatchObject({
      kind: "desconocido",
    });
  });
  it("pide el núcleo o el informe completo", async () => {
    const urls: string[] = [];
    const f = (url: RequestInfo | URL) => {
      urls.push(String(url));
      return json(200, SAMPLE);
    };
    await fetchEngineReport(true, f);
    await fetchEngineReport(false, f);
    expect(urls.map((u) => u.replace(/^.*\/informe/, "/informe"))).toEqual([
      "/informe?nucleo=true",
      "/informe",
    ]);
  });
});
