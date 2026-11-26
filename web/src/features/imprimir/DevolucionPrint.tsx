"use client";

import { ReportGate } from "@/components/ReportGate";
import { useAppState } from "@/lib/appState";
import { returnLines, returnTotal } from "@/lib/exports";
import { formatEur, formatNumber } from "@/lib/format";
import type { Report } from "@/lib/types";
import { PrintLayout } from "./PrintLayout";

function Content({ report }: { report: Report }) {
  const { records } = useAppState();
  const lines = returnLines(report, records);
  const byLab = new Map<string, typeof lines>();
  for (const l of lines) byLab.set(l.laboratorio, [...(byLab.get(l.laboratorio) ?? []), l]);
  return (
    <PrintLayout report={report} title="Lista de devolución">
      {lines.length === 0 ? (
        <p className="mt-6 text-ink-muted">No hay devoluciones esta semana.</p>
      ) : (
        <table className="mt-5 w-full border-collapse" data-testid="tabla-devolucion">
          <thead>
            <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-muted">
              <th className="py-1.5 pr-2 font-semibold">CN</th>
              <th className="py-1.5 pr-2 font-semibold">Producto</th>
              <th className="py-1.5 pr-2 text-right font-semibold">Uds.</th>
              <th className="py-1.5 pr-2 text-right font-semibold">Importe a coste</th>
              <th className="py-1.5 text-center font-semibold">✓</th>
            </tr>
          </thead>
          {[...byLab.entries()].map(([lab, items]) => (
            <tbody key={lab} className="break-inside-avoid">
              <tr>
                <td colSpan={5} className="pb-1 pt-3 text-[12px] font-semibold">
                  {lab}
                </td>
              </tr>
              {items.map((l) => (
                <tr key={l.codigo} className="border-b border-line-soft">
                  <td className="py-1.5 pr-2 tabular-nums">{l.codigo}</td>
                  <td className="py-1.5 pr-2">{l.producto}</td>
                  <td className="py-1.5 pr-2 text-right tabular-nums">{formatNumber(l.unidades)}</td>
                  <td className="py-1.5 pr-2 text-right tabular-nums">{formatEur(l.importe, 2)}</td>
                  <td className="py-1.5 text-center">
                    <span className="inline-block h-3.5 w-3.5 border border-ink-faint" aria-hidden="true" />
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
          <tfoot>
            <tr className="border-t-2 border-ink font-semibold">
              <td className="py-2" colSpan={2}>
                Total ({lines.length} referencias)
              </td>
              <td className="py-2 pr-2 text-right tabular-nums">
                {formatNumber(lines.reduce((s, l) => s + l.unidades, 0))}
              </td>
              <td className="py-2 pr-2 text-right tabular-nums" data-testid="total-devolucion">
                {formatEur(returnTotal(lines), 2)}
              </td>
              <td />
            </tr>
          </tfoot>
        </table>
      )}
      <div className="mt-12 grid grid-cols-3 gap-6 text-[11px] text-ink-muted">
        {["Firma de la farmacia", "Recibido por (proveedor)", "Fecha de recogida"].map((label) => (
          <div key={label}>
            <div className="h-12 border-b border-ink-faint" />
            <div className="mt-1">{label}</div>
          </div>
        ))}
      </div>
      <p className="mt-8 text-[10px] text-ink-faint">
        Importes a precio de coste calculados por PharmaOS con los datos del programa de gestión. Sin datos de
        pacientes.
      </p>
    </PrintLayout>
  );
}

export function DevolucionPrint() {
  return <ReportGate>{(report) => <Content report={report} />}</ReportGate>;
}
