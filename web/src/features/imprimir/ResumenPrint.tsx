"use client";

import { ReportGate } from "@/components/ReportGate";
import { statusOf } from "@/lib/actionStore";
import { useAppState } from "@/lib/appState";
import { weeklySummary } from "@/lib/exports";
import { formatEur } from "@/lib/format";
import type { Report } from "@/lib/types";
import { ACTION_TYPES, TYPE_LABEL } from "@/lib/types";
import { PrintLayout } from "./PrintLayout";

const STATUS = {
  pendiente: "Pendiente",
  hecha: "Hecha",
  pospuesta: "Pospuesta",
  descartada: "Descartada",
} as const;

function Content({ report }: { report: Report }) {
  const { records } = useAppState();
  const { progress, top } = weeklySummary(report, records);
  const kpis = [
    ["Recuperable esta semana", formatEur(progress.recoverable)],
    ["Recuperado (hechas)", formatEur(progress.recovered)],
    ["Acciones hechas", `${progress.done} de ${progress.total}`],
    ["Capital inmovilizado (+180 días)", formatEur(report.resumen.capital_inmovilizado_eur)],
  ];
  return (
    <PrintLayout report={report} title="Resumen semanal">
      <section className="mt-5 grid grid-cols-4 gap-3">
        {kpis.map(([label, value]) => (
          <div key={label} className="rounded-ctl border border-line px-3 py-2.5">
            <div className="text-[10px] text-ink-muted">{label}</div>
            <div className="mt-0.5 text-[17px] font-semibold tabular-nums">{value}</div>
          </div>
        ))}
      </section>
      <h2 className="mt-6 text-[13px] font-semibold">Por tipo de acción</h2>
      <table className="mt-2 w-full border-collapse">
        <thead>
          <tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-ink-muted">
            <th className="py-1.5 font-semibold">Tipo</th>
            <th className="py-1.5 text-right font-semibold">Acciones</th>
            <th className="py-1.5 text-right font-semibold">Hechas</th>
            <th className="py-1.5 text-right font-semibold">Importe</th>
          </tr>
        </thead>
        <tbody>
          {ACTION_TYPES.map((t) => {
            const items = report.acciones.filter((a) => a.tipo === t);
            const done = items.filter((a) => statusOf(records, a.id) === "hecha").length;
            return (
              <tr key={t} className="border-b border-line-soft">
                <td className="py-1.5">{TYPE_LABEL[t]}</td>
                <td className="py-1.5 text-right tabular-nums">{items.length}</td>
                <td className="py-1.5 text-right tabular-nums">{done}</td>
                <td className="py-1.5 text-right tabular-nums">
                  {formatEur(report.resumen.importe_por_tipo[t])}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <h2 className="mt-6 text-[13px] font-semibold">Las 10 acciones de más importe</h2>
      <table className="mt-2 w-full border-collapse">
        <tbody>
          {top.map((a, i) => (
            <tr key={a.id} className="border-b border-line-soft align-top">
              <td className="w-6 py-1.5 text-ink-muted">{i + 1}</td>
              <td className="py-1.5 pr-2">
                <div className="font-medium">{a.titulo}</div>
                <div className="text-[11px] text-ink-muted">{a.motivo_1_linea}</div>
              </td>
              <td className="py-1.5 pr-2 text-[11px] text-ink-muted">{STATUS[statusOf(records, a.id)]}</td>
              <td className="py-1.5 text-right font-semibold tabular-nums">{formatEur(a.importe_eur)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-8 text-[10px] text-ink-faint">
        Cálculos deterministas de PharmaOS a partir de las exportaciones del programa de gestión. Sin datos de
        pacientes.
      </p>
    </PrintLayout>
  );
}

export function ResumenPrint() {
  return <ReportGate>{(report) => <Content report={report} />}</ReportGate>;
}
