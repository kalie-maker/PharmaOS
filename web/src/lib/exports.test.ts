import { withStatus } from "./actionStore";
import { exportFilename, orderCsv, orderLines, returnCsv, returnLines, returnTotal } from "./exports";
import { SAMPLE } from "@/test/fixtures";

describe("lista de devolución", () => {
  it("incluye solo DEVOLVER no descartadas, agrupadas por laboratorio", () => {
    const records = withStatus(withStatus({}, "devolver-100005", "descartada"), "devolver-100001", "hecha");
    const lines = returnLines(SAMPLE, records);
    expect(lines.map((l) => l.codigo)).toEqual(["100001"]);
    expect(lines[0]).toMatchObject({ laboratorio: "Lab 100001", unidades: 3, importe: 250, estado: "Hecha" });
    expect(returnTotal(returnLines(SAMPLE, {}))).toBe(500);
  });
  it("CSV con cabecera, filas y total", () => {
    const csv = returnCsv(SAMPLE, {});
    const rows = csv.replace("﻿", "").trim().split("\r\n");
    expect(rows[0]).toBe("Código nacional;Producto;Laboratorio;Unidades;Importe a coste (€);Estado");
    expect(rows).toHaveLength(4);
    expect(rows[3]).toBe(";TOTAL;;6;500;");
  });
});

describe("pedido corregido", () => {
  it("marca No pedir (sobrestock) y Pedir (rotura) con unidades", () => {
    const lines = orderLines(SAMPLE, {});
    expect(lines.map((l) => [l.codigo, l.accion])).toEqual([
      ["100002", "No pedir"],
      ["100003", "Pedir"],
    ]);
    expect(orderCsv(SAMPLE, {})).toContain("100003;Producto 100003;Lab 100003;Pedir;3;Motivo de prueba");
  });
  it("nombre de fichero con la fecha de los datos", () => {
    expect(exportFilename("pedido_corregido", SAMPLE)).toBe("pedido_corregido_2026-11-20.csv");
  });
});
