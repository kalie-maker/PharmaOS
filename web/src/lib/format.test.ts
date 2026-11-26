import { daysBetween, formatDate, formatEur, formatLongDate, formatNumber } from "./format";

describe("formato español", () => {
  it("agrupa miles con punto y decimales con coma", () => {
    expect(formatEur(1234.56, 2)).toBe("1.234,56 €");
    expect(formatEur(5790.2)).toBe("5.790 €");
    expect(formatNumber(1234567)).toBe("1.234.567");
    expect(formatNumber(999)).toBe("999");
    expect(formatNumber(-1500)).toBe("−1.500");
  });
  it("trata valores vacíos", () => {
    expect(formatEur(null)).toBe("—");
    expect(formatNumber(Number.NaN)).toBe("—");
    expect(formatDate(null)).toBe("—");
  });
  it("fechas", () => {
    expect(formatDate("2026-11-20")).toBe("20/11/2026");
    expect(formatLongDate("2026-11-20")).toBe("20 de noviembre de 2026");
    expect(daysBetween("2026-11-20", "2026-12-01")).toBe(11);
  });
});
