import { toCsv } from "./csv";

describe("CSV para Excel en español", () => {
  it("usa ; coma decimal, BOM y escapa comillas", () => {
    const csv = toCsv(
      ["A", "B"],
      [
        ["x;y", 1.5],
        ['dice "hola"', null],
      ],
    );
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv).toContain('"x;y";1,5');
    expect(csv).toContain('"dice ""hola""";');
  });
});
