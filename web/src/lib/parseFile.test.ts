import { analyzeParsed, decodeText, findHeaderRow, parseFile, toIsoDate } from "./parseFile";

function cp1252File(name: string, text: string): File {
  const bytes = Uint8Array.from(
    [...text].map(
      (c) => ({ á: 0xe1, é: 0xe9, í: 0xed, ó: 0xf3, ú: 0xfa, ñ: 0xf1, "€": 0x80 })[c] ?? c.charCodeAt(0),
    ),
  );
  return new File([bytes], name);
}

describe("lectura de ficheros en el navegador", () => {
  it("detecta Windows-1252 y UTF-8", () => {
    expect(decodeText(new TextEncoder().encode("﻿Código").buffer as ArrayBuffer)).toEqual({
      text: "Código",
      encoding: "UTF-8",
    });
    expect(decodeText(Uint8Array.from([0x43, 0xf3, 0x64]).buffer as ArrayBuffer).encoding).toBe(
      "Windows-1252",
    );
  });
  it("salta líneas de título y lee CSV con ;", async () => {
    const text = [
      "Listado de ventas",
      "",
      "Fecha;Código;Descripción;Unidades;Importe s/IVA",
      "03/02/2026;654321;Crema hidratante;2;12,50",
      "05/02/2026;700100;Paracetamol 1 g;1;2,50",
      "05/02/2026;654321;Crema hidratante;1;6,25",
    ].join("\r\n");
    const parsed = await parseFile(cp1252File("ventas.csv", text));
    expect(parsed.encoding).toBe("Windows-1252");
    expect(parsed.headers).toEqual(["Fecha", "Código", "Descripción", "Unidades", "Importe s/IVA"]);
    expect(parsed.headerRow).toBe(3);
    const a = analyzeParsed(parsed);
    expect(a.privacy).toEqual([]);
    expect(a.detection.dataset).toBe("ventas");
    expect(a.summary).toEqual({ rows: 3, products: 2, dateFrom: "2026-02-03", dateTo: "2026-02-05" });
  });
  it("bloquea un fichero con columna de paciente", async () => {
    const parsed = await parseFile(
      new File(["Código;Stock Actual;P.Coste;DNI\n654321;3;1,5;\n"], "stock.csv"),
    );
    expect(analyzeParsed(parsed).privacy.map((f) => f.category)).toEqual(["identidad"]);
  });
  it("rechaza .xls antiguo y ficheros vacíos con mensaje claro", async () => {
    await expect(parseFile(new File(["x"], "viejo.xls"))).rejects.toThrow(/xlsx/);
    await expect(parseFile(new File([""], "vacio.csv"))).rejects.toThrow(/vacío/);
  });
  it("fechas españolas e ISO", () => {
    expect(toIsoDate("03/02/2026")).toBe("2026-02-03");
    expect(toIsoDate("3-2-26")).toBe("2026-02-03");
    expect(toIsoDate("2026-02-03 10:00")).toBe("2026-02-03");
    expect(toIsoDate("TOTAL")).toBeNull();
    expect(toIsoDate(new Date("2026-02-03T00:00:00Z"))).toBe("2026-02-03");
  });
  it("encuentra la cabecera por etiquetas conocidas", () => {
    expect(
      findHeaderRow([
        ["Farmacia", "Demo"],
        ["Fecha", "Código", "Unidades"],
        ["01/01/2026", "1", "2"],
      ]),
    ).toBe(1);
  });
});
