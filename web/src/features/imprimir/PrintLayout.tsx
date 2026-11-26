"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { useAppState } from "@/lib/appState";
import { formatDate, weekNumber } from "@/lib/format";
import type { Report } from "@/lib/types";

export function PrintLayout({
  report,
  title,
  children,
}: {
  report: Report;
  title: string;
  children: ReactNode;
}) {
  const { settings } = useAppState();
  const name = settings.pharmacyName ?? report.farmacia.nombre;
  return (
    <div className="min-h-screen bg-canvas py-6 print:bg-white print:py-0">
      <div className="no-print mx-auto mb-4 flex max-w-[210mm] items-center justify-between px-4">
        <Link href="/lunes" className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-ink">
          ← Volver a la lista
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex h-9 items-center gap-1.5 rounded-ctl bg-ink px-3.5 text-sm font-medium text-white hover:bg-ink-soft"
        >
          <Icon name="print" /> Imprimir
        </button>
      </div>
      <article className="mx-auto max-w-[210mm] bg-white px-[12mm] py-[12mm] text-[12px] leading-relaxed shadow-soft print:max-w-none print:p-0 print:shadow-none">
        <header className="flex items-end justify-between border-b-2 border-ink pb-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            <p className="text-ink-muted">
              {name} · Semana {weekNumber(report.farmacia.semana)} · datos hasta{" "}
              {formatDate(report.farmacia.fecha_datos)}
            </p>
          </div>
          <span className="text-xs font-semibold text-ink-muted">PharmaOS</span>
        </header>
        {children}
      </article>
    </div>
  );
}
