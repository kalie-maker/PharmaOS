"use client";

import { useMemo } from "react";
import { TypeBadge } from "@/components/Badge";
import { ButtonLink } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Card, PageHeader } from "@/components/PageHeader";
import { WeekChart } from "@/components/WeekChart";
import { useAppState } from "@/lib/appState";
import { formatDate, formatEur, formatNumber, weekNumber } from "@/lib/format";
import { GUARANTEE_MULTIPLE, executedThisWeek, totals, weeks } from "@/lib/recovered";
import type { Report } from "@/lib/types";

function Big({ label, value, hint, tone }: { label: string; value: string; hint: string; tone?: "brand" }) {
  return (
    <div className="min-w-0 py-1 sm:px-6 sm:first:pl-0">
      <div className="text-xs font-medium text-ink-muted">{label}</div>
      <div
        className={`mt-1 text-3xl font-semibold tabular-nums tracking-tight sm:text-4xl ${tone === "brand" ? "text-brand-text" : "text-ink"}`}
      >
        {value}
      </div>
      <div className="mt-1 text-xs text-ink-muted">{hint}</div>
    </div>
  );
}

function GuaranteeMeter({ multiple }: { multiple: number }) {
  const scale = 10; // escala fija: la marca ×3 siempre en el mismo sitio; por encima de ×10 la barra se llena
  const pct = Math.min(100, (multiple / scale) * 100);
  const mark = (GUARANTEE_MULTIPLE / scale) * 100;
  return (
    <div>
      <div
        className="relative h-2.5 rounded-full bg-line"
        role="meter"
        aria-label="Múltiplo frente al coste"
        aria-valuemin={0}
        aria-valuemax={scale}
        aria-valuenow={multiple}
      >
        <div
          className={`h-full rounded-full ${multiple >= GUARANTEE_MULTIPLE ? "bg-brand" : "bg-warn"}`}
          style={{ width: `${pct}%` }}
        />
        <div className="absolute -top-1.5 h-5 w-0.5 bg-ink" style={{ left: `${mark}%` }} aria-hidden="true" />
      </div>
      <div className="relative mt-1.5 h-4 text-2xs text-ink-muted" aria-hidden="true">
        <span className="absolute left-0">×0</span>
        <span className="absolute -translate-x-1/2 font-semibold text-ink" style={{ left: `${mark}%` }}>
          Garantía ×{GUARANTEE_MULTIPLE}
        </span>
        <span className="absolute right-0">×{scale}+</span>
      </div>
    </div>
  );
}

export function RecuperadoView({ report }: { report: Report }) {
  const { records, settings } = useAppState();
  const rows = useMemo(() => weeks(report, records), [report, records]);
  const t = useMemo(() => totals(rows, settings.monthlyCost), [rows, settings.monthlyCost]);
  const executed = useMemo(() => executedThisWeek(report, records), [report, records]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recuperado"
        description={`${t.semanas} semanas de piloto, desde el ${formatDate(rows[0]?.fecha_inicio)}.${report.historico_simulado ? " Histórico de demostración." : ""}`}
      />

      <Card>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 sm:divide-x sm:divide-line">
          <Big label="Encontrado" value={formatEur(t.encontrado)} hint="Acciones con importe detectadas" />
          <Big
            label="Ejecutado"
            value={formatEur(t.ejecutado)}
            hint={`${formatNumber(t.encontrado ? (t.ejecutado / t.encontrado) * 100 : 0)} % de lo encontrado`}
          />
          <Big
            label="Recuperado"
            value={formatEur(t.recuperado)}
            hint="Capital liberado y ventas salvadas"
            tone="brand"
          />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <h2 className="mb-4 text-sm font-semibold text-ink">Por semana</h2>
          <WeekChart
            data={rows.map((r) => ({
              label: r.enCurso ? "Esta" : `S${weekNumber(r.semana)}`,
              encontrado: r.encontrado,
              ejecutado: r.ejecutado,
              recuperado: r.recuperado,
              enCurso: r.enCurso,
            }))}
          />
        </Card>
        <Card>
          <h2 className="text-sm font-semibold text-ink">Múltiplo frente al coste</h2>
          <p
            className="mt-3 text-4xl font-semibold tabular-nums tracking-tight text-ink"
            data-testid="multiplo"
          >
            ×{formatNumber(t.multiplo, 1)}
          </p>
          <p className="mt-1 text-xs text-ink-muted">
            {formatEur(t.recuperado)} recuperados frente a {formatEur(t.coste)} de coste (
            {formatEur(settings.monthlyCost)}/mes × {formatNumber(t.meses, 1)} meses)
          </p>
          <div className="mt-5">
            <GuaranteeMeter multiple={t.multiplo} />
          </div>
          <p
            className={`mt-4 rounded-ctl px-3 py-2 text-sm font-medium ${t.cumpleGarantia ? "bg-brand-soft text-brand-dark" : "bg-warn-soft text-warn"}`}
          >
            {t.cumpleGarantia
              ? `Garantía cumplida: recuperas ${formatNumber(t.multiplo, 1)} veces lo que cuesta.`
              : `Aún por debajo de la garantía ×${GUARANTEE_MULTIPLE}.`}
          </p>
          <p className="mt-2 text-2xs text-ink-muted">El coste se cambia en Ajustes.</p>
        </Card>
      </div>

      <Card className="p-0">
        <div className="border-b border-line px-5 py-4">
          <h2 className="text-sm font-semibold text-ink">Acciones ejecutadas esta semana</h2>
        </div>
        {executed.length ? (
          <div
            className="overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Acciones ejecutadas esta semana"
          >
            <table className="w-full text-sm" data-testid="tabla-ejecutadas">
              <thead className="text-left text-2xs uppercase tracking-wide text-ink-muted">
                <tr className="border-b border-line">
                  <th scope="col" className="px-5 py-2 font-semibold">
                    Fecha
                  </th>
                  <th scope="col" className="px-2 py-2 font-semibold">
                    Acción
                  </th>
                  <th scope="col" className="hidden px-2 py-2 font-semibold sm:table-cell">
                    Tipo
                  </th>
                  <th scope="col" className="px-5 py-2 text-right font-semibold">
                    Importe
                  </th>
                </tr>
              </thead>
              <tbody>
                {executed.map(({ action, at }) => (
                  <tr key={action.id} className="border-b border-line-soft last:border-0">
                    <td className="whitespace-nowrap px-5 py-2.5 tabular-nums text-ink-muted">
                      <span className="sm:hidden">{formatDate(at).slice(0, 5)}</span>
                      <span className="hidden sm:inline">{formatDate(at)}</span>
                    </td>
                    <td className="px-2 py-2.5 text-ink">{action.titulo}</td>
                    <td className="hidden px-2 py-2.5 sm:table-cell">
                      <TypeBadge type={action.tipo} />
                    </td>
                    <td className="whitespace-nowrap px-5 py-2.5 text-right font-semibold tabular-nums text-brand-text">
                      {formatEur(action.importe_eur, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-5">
            <EmptyState
              title="Todavía no has marcado ninguna acción como hecha"
              action={<ButtonLink href="/lunes">Ir a la lista del lunes</ButtonLink>}
            >
              Cada acción que marques como hecha suma aquí, con su fecha e importe.
            </EmptyState>
          </div>
        )}
      </Card>

      <Card className="p-0">
        <div className="border-b border-line px-5 py-4">
          <h2 className="text-sm font-semibold text-ink">Semanas anteriores</h2>
        </div>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Semanas anteriores">
          <table className="w-full text-sm">
            <thead className="text-left text-2xs uppercase tracking-wide text-ink-muted">
              <tr className="border-b border-line">
                <th scope="col" className="px-5 py-2 font-semibold">
                  Semana
                </th>
                <th scope="col" className="hidden px-2 py-2 text-right font-semibold sm:table-cell">
                  Encontrado
                </th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  Ejecutado
                </th>
                <th scope="col" className="px-5 py-2 text-right font-semibold">
                  Recuperado
                </th>
              </tr>
            </thead>
            <tbody>
              {report.historico_semanas.map((w) => (
                <tr key={w.semana} className="border-b border-line-soft last:border-0">
                  <td className="px-5 py-2.5 text-ink">
                    <span className="whitespace-nowrap">Semana {weekNumber(w.semana)}</span>
                    <span className="block text-xs text-ink-muted sm:ml-1 sm:inline">
                      {formatDate(w.fecha_inicio)}
                    </span>
                  </td>
                  <td className="hidden px-2 py-2.5 text-right tabular-nums sm:table-cell">
                    {formatEur(w.encontrado_eur)}
                  </td>
                  <td className="px-2 py-2.5 text-right tabular-nums">
                    <span className="whitespace-nowrap">{formatEur(w.ejecutado_eur)}</span>
                    <span className="block text-2xs text-ink-muted sm:ml-1 sm:inline">
                      {w.acciones_ejecutadas} de {w.acciones_encontradas} acciones
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-right font-semibold tabular-nums text-brand-text">
                    {formatEur(w.recuperado_eur)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
