"use client";

import type { ReactNode } from "react";
import { useReportState } from "@/lib/report";
import type { Report } from "@/lib/types";

/** Pinta los hijos solo cuando el informe está cargado; muestra carga y error de forma sobria. */
export function ReportGate({ children }: { children: (report: Report) => ReactNode }) {
  const state = useReportState();
  if (state.status === "loading") {
    return (
      <div aria-busy="true" aria-live="polite" className="space-y-3">
        <span className="sr-only">Cargando datos de la farmacia…</span>
        <div className="h-7 w-64 animate-pulse rounded bg-line" />
        <div className="h-24 animate-pulse rounded-card bg-line/70" />
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-card bg-line/50" />
        ))}
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div
        role="alert"
        className="rounded-card border border-urgent/30 bg-urgent-soft px-5 py-4 text-sm text-ink"
      >
        <strong className="font-semibold">No se han podido cargar los datos.</strong> {state.message}. Recarga
        la página; si sigue fallando, regenera el mock con <code>npm run gen:mock</code>.
      </div>
    );
  }
  return <>{children(state.report)}</>;
}
