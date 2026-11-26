import { checkContent, checkHeaders, validatePrivacy } from "./privacy";

// Mismos casos que stock-profit-os/tests/test_privacy.py: las reglas vienen generadas del motor.
const SAFE = [
  "Fecha",
  "Código",
  "Descripción",
  "Laboratorio",
  "Familia",
  "Unidades",
  "Importe s/IVA",
  "P.Coste",
  "Stock Actual",
  "PVP",
  "Caducidad",
  "Fecha Albarán",
  "COD_NACIONAL",
  "IMP_NETO",
  "Stock mínimo",
  "Margen",
];
const UNSAFE: [string, string][] = [
  ["Nombre Paciente", "paciente"],
  ["Apellidos", "paciente"],
  ["Cód. Cliente", "paciente"],
  ["DNI", "identidad"],
  ["N.I.E.", "identidad"],
  ["CIP", "tarjeta_sanitaria"],
  ["Tarjeta Sanitaria", "tarjeta_sanitaria"],
  ["Nº Receta", "receta"],
  ["Teléfono", "telefono"],
  ["E-mail", "email"],
  ["Dirección", "direccion"],
  ["Fecha de nacimiento", "datos_personales"],
  ["Diagnóstico", "datos_sanitarios"],
];

describe("privacidad en cliente", () => {
  it.each(SAFE)("acepta la cabecera de producto %s", (h) => expect(checkHeaders([h])).toEqual([]));
  it.each(UNSAFE)("bloquea %s (%s)", (h, category) => {
    const f = checkHeaders([h]);
    expect(f).toHaveLength(1);
    expect(f[0]!.category).toBe(category);
  });
  it("detecta DNI/NIE, email y teléfono por contenido sin devolver valores", () => {
    const headers = ["Ref", "Contacto", "Otro", "Descripción"];
    const rows = [
      ["12345678Z", "a@b.es", "612345678", "Ibuprofeno 400 mg"],
      ["X1234567L", "", "+34 912 345 678", "Crema 50 ml"],
      ["ok", "x", "699111222", "Gel"],
    ];
    const found = checkContent(headers, rows);
    expect(Object.fromEntries(found.map((f) => [f.column, f.category]))).toEqual({
      Ref: "dni_nie",
      Contacto: "email",
      Otro: "telefono",
    });
    expect(JSON.stringify(found)).not.toContain("12345678Z");
  });
  it("no confunde códigos nacionales ni importes", () => {
    expect(
      checkContent(
        ["Código", "Importe"],
        [
          ["654321", "612,50"],
          ["700001", "1.234,56"],
        ],
      ),
    ).toEqual([]);
  });
  it("combina cabecera y contenido", () => {
    expect(validatePrivacy(["DNI", "Notas"], [["", "a@b.es"]]).map((f) => f.column)).toEqual([
      "DNI",
      "Notas",
    ]);
  });
});
