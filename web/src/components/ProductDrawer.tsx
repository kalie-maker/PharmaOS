"use client";

import { daysBetween, formatDate, formatEur, formatNumber, formatShortDate } from "@/lib/format";
import { useEffect } from "react";
import type { ActionStatus } from "@/lib/actionStore";
import type { Action, Product, Report } from "@/lib/types";
import { TYPE_LABEL } from "@/lib/types";
import { TypeBadge, UrgencyBadge } from "./Badge";
import { Drawer } from "./Drawer";
import { MiniChart } from "./MiniChart";

function weekLabels(report: Report, weeks: number): string[] {
  const end = report.farmacia.fecha_datos;
  return Array.from({ length: weeks }, (_, i) => {
    const d = new Date(`${end}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() - 7 * (weeks - 1 - i));
    return i === weeks - 1 ? "Esta semana" : `Sem. ${formatShortDate(d.toISOString())}`;
  });
}

function Fact({ label, value, tone }: { label: string; value: string; tone?: "urgent" | "warn" }) {
  return (
    <div className="rounded-ctl bg-line-soft/60 px-3 py-2.5">
      <dt className="text-2xs font-medium text-ink-muted">{label}</dt>
      <dd
        className={`mt-0.5 text-sm font-semibold tabular-nums ${tone === "urgent" ? "text-urgent-text" : tone === "warn" ? "text-warn" : "text-ink"}`}
      >
        {value}
      </dd>
    </div>
  );
}

export function ProductDrawer({
  report,
  productId,
  action,
  onClose,
  status,
  onStatus,
}: {
  report: Report;
  productId: string | null;
  action?: Action;
  onClose: () => void;
  status?: ActionStatus;
  onStatus?: (status: ActionStatus) => void;
}) {
  const product: Product | undefined = productId ? report.productos[productId] : undefined;
  const ref = report.farmacia.fecha_datos;
  const daysSince = product?.ultima_venta ? daysBetween(product.ultima_venta, ref) : null;
  const daysToExpiry = product?.caducidad ? daysBetween(ref, product.caducidad) : null;
  const canAct = !!action && !!onStatus && (status === "pendiente" || status === "pospuesta");

  // Atajos dentro de la ficha: H hecho, P posponer, D descartar (cierran la ficha).
  useEffect(() => {
    if (!canAct || !onStatus) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const map: Record<string, ActionStatus> = { h: "hecha", p: "pospuesta", d: "descartada" };
      const next = map[e.key.toLowerCase()];
      if (!next || (next === "pospuesta" && status === "pospuesta")) return;
      e.preventDefault();
      onStatus(next);
      onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [canAct, onStatus, onClose, status]);

  return (
    <Drawer
      open={!!product}
      onClose={onClose}
      title={product?.nombre ?? "Producto"}
      subtitle={
        product
          ? `CN ${product.codigo} · ${product.familia} · ${product.laboratorio ?? "Sin laboratorio"}`
          : undefined
      }
    >
      {product ? (
        <div className="space-y-6">
          {action ? (
            <div className="flex flex-wrap items-center gap-2">
              <TypeBadge type={action.tipo} />
              <UrgencyBadge urgency={action.urgencia} />
              <span className="ml-auto text-lg font-semibold tabular-nums text-ink">
                {formatEur(action.importe_eur, 2)}
              </span>
            </div>
          ) : null}

          <section aria-labelledby="ventas-12">
            <h3 id="ventas-12" className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Ventas de las últimas 12 semanas
            </h3>
            <MiniChart
              values={product.ventas_semanales_12}
              labels={weekLabels(report, product.ventas_semanales_12.length)}
              title="Unidades vendidas por semana"
            />
          </section>

          <dl className="grid grid-cols-2 gap-2">
            <Fact label="Stock" value={`${formatNumber(product.stock)} uds`} />
            <Fact label="Coste inmovilizado" value={formatEur(product.valor_stock, 2)} />
            <Fact
              label="Días de cobertura"
              value={
                product.dias_cobertura === null
                  ? "Sin ventas"
                  : `${formatNumber(product.dias_cobertura)} días`
              }
            />
            <Fact
              label="Última venta"
              value={
                product.ultima_venta
                  ? `${formatDate(product.ultima_venta)} (hace ${daysSince} d)`
                  : "Nunca en 12 meses"
              }
              tone={
                daysSince !== null && daysSince >= report.resumen.umbral_sin_movimiento_dias
                  ? "warn"
                  : undefined
              }
            />
            <Fact
              label="Caducidad"
              value={
                product.caducidad
                  ? `${formatDate(product.caducidad)}${daysToExpiry !== null ? ` (${daysToExpiry} d)` : ""}`
                  : "Sin fecha"
              }
              tone={
                daysToExpiry !== null && daysToExpiry <= 30
                  ? "urgent"
                  : daysToExpiry !== null && daysToExpiry <= 90
                    ? "warn"
                    : undefined
              }
            />
            <Fact
              label="Coste / PVP"
              value={`${formatEur(product.coste, 2)} / ${formatEur(product.pvp, 2)}`}
            />
          </dl>

          {action ? (
            <section aria-labelledby="por-que" className="rounded-card border border-line">
              <div className="border-b border-line px-4 py-3">
                <h3 id="por-que" className="text-sm font-semibold text-ink">
                  Por qué esta acción · {TYPE_LABEL[action.tipo]}
                </h3>
                <p className="mt-0.5 text-xs text-ink-muted">
                  Cálculo con los datos reales de tu programa de gestión. Sin estimaciones de un chat.
                </p>
              </div>
              <ol className="divide-y divide-line-soft">
                {action.calculo_explicado.pasos.map((step, i) => (
                  <li key={step.concepto} className="flex gap-3 px-4 py-2.5 text-sm">
                    <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-line-soft text-2xs font-semibold text-ink-soft">
                      {i + 1}
                    </span>
                    <span className="min-w-0 flex-1 text-ink-soft">{step.concepto}</span>
                    <span className="text-right font-medium tabular-nums text-ink">{step.valor}</span>
                  </li>
                ))}
              </ol>
              <div className="border-t border-line bg-brand-soft/60 px-4 py-3 text-sm">
                <div className="text-2xs font-medium uppercase tracking-wide text-ink-muted">
                  Fórmula: {action.calculo_explicado.formula}
                </div>
                <p className="mt-1 font-medium text-ink">{action.calculo_explicado.resultado}</p>
              </div>
            </section>
          ) : (
            <p className="text-sm text-ink-muted">Este producto no tiene acciones esta semana.</p>
          )}

          {canAct ? (
            <div className="sticky bottom-0 -mx-5 -mb-5 flex gap-2 border-t border-line bg-white px-5 py-3">
              <button
                type="button"
                onClick={() => {
                  onStatus!("hecha");
                  onClose();
                }}
                className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-ctl bg-ink text-sm font-medium text-white hover:bg-ink-soft"
              >
                Marcar como hecha{" "}
                <kbd className="border-white/30 bg-transparent text-white/80 shadow-none">H</kbd>
              </button>
              {status === "pendiente" ? (
                <button
                  type="button"
                  onClick={() => {
                    onStatus!("pospuesta");
                    onClose();
                  }}
                  className="inline-flex h-9 items-center rounded-ctl border border-line px-3 text-sm text-ink-soft hover:bg-line-soft"
                >
                  Posponer
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => {
                  onStatus!("descartada");
                  onClose();
                }}
                className="inline-flex h-9 items-center rounded-ctl border border-line px-3 text-sm text-ink-soft hover:bg-line-soft"
              >
                Descartar
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </Drawer>
  );
}
