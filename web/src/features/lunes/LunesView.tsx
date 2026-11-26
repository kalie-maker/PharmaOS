"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActionRow } from "@/components/ActionRow";
import { Icon } from "@/components/Icon";
import { ProductDrawer } from "@/components/ProductDrawer";
import { ProgressBar } from "@/components/ProgressBar";
import { ShortcutsHelp } from "@/components/ShortcutsHelp";
import { useToast } from "@/components/Toast";
import { EmptyState } from "@/components/EmptyState";
import { ButtonLink } from "@/components/Button";
import type { ActionStatus } from "@/lib/actionStore";
import { statusOf } from "@/lib/actionStore";
import { countOpenByType, groupActions, weekProgress, type TypeFilter } from "@/lib/actions";
import { useAppState } from "@/lib/appState";
import { formatDate, formatEur, weekNumber } from "@/lib/format";
import type { Action, Report } from "@/lib/types";
import { ACTION_TYPES, TYPE_LABEL } from "@/lib/types";
import { ExportMenu } from "./ExportMenu";
import { useShortcuts } from "./useShortcuts";

const STATUS_TOAST: Record<ActionStatus, string> = {
  hecha: "Hecha",
  pospuesta: "Pospuesta",
  descartada: "Descartada",
  pendiente: "Vuelve a pendientes",
};

export function LunesView({ report }: { report: Report }) {
  const { records, setStatus } = useAppState();
  const toast = useToast();
  const [type, setType] = useState<TypeFilter>("TODAS");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [showDone, setShowDone] = useState(false);
  const search = useRef<HTMLInputElement>(null);
  const rowRefs = useRef(new Map<string, HTMLLIElement>());

  const groups = useMemo(
    () => groupActions(report, records, { type, query }),
    [report, records, type, query],
  );
  const counts = useMemo(() => countOpenByType(report, records, query), [report, records, query]);
  const progress = useMemo(() => weekProgress(report, records), [report, records]);
  const navigable = useMemo(() => [...groups.pending, ...groups.postponed], [groups]);
  const openAction = openId ? report.acciones.find((a) => a.id === openId) : undefined;

  // Mantiene una selección válida al cambiar filtros o estados.
  useEffect(() => {
    if (navigable.length === 0) return setSelectedId(null);
    if (!selectedId || !navigable.some((a) => a.id === selectedId)) setSelectedId(navigable[0]!.id);
  }, [navigable, selectedId]);

  useEffect(() => {
    if (selectedId) rowRefs.current.get(selectedId)?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  const change = useCallback(
    (action: Action, status: ActionStatus) => {
      const index = navigable.findIndex((a) => a.id === action.id);
      const previous = setStatus(action.id, status);
      if (status !== "pendiente" && index >= 0) {
        const nextAction = navigable[index + 1] ?? navigable[index - 1];
        setSelectedId(nextAction && nextAction.id !== action.id ? nextAction.id : null);
      }
      const amount = status === "hecha" ? ` · ${formatEur(action.importe_eur)}` : "";
      toast.show(`${STATUS_TOAST[status]}: ${action.titulo}${amount}`, {
        label: "Deshacer",
        onClick: () => setStatus(action.id, previous),
      });
    },
    [navigable, setStatus, toast],
  );

  const move = (delta: number) => {
    if (navigable.length === 0) return;
    const i = navigable.findIndex((a) => a.id === selectedId);
    const next = navigable[Math.min(navigable.length - 1, Math.max(0, (i < 0 ? 0 : i) + delta))];
    if (next) setSelectedId(next.id);
  };
  const selected = navigable.find((a) => a.id === selectedId);

  useShortcuts(
    {
      next: () => move(1),
      prev: () => move(-1),
      done: () => selected && change(selected, "hecha"),
      postpone: () =>
        selected && statusOf(records, selected.id) === "pendiente" && change(selected, "pospuesta"),
      dismiss: () => selected && change(selected, "descartada"),
      open: () => selected && setOpenId(selected.id),
      search: () => search.current?.focus(),
      help: () => setHelpOpen(true),
    },
    !openId && !helpOpen,
  );

  const renderRows = (items: Action[]) =>
    items.map((a) => (
      <ActionRow
        key={a.id}
        ref={(el) => {
          if (el) rowRefs.current.set(a.id, el);
          else rowRefs.current.delete(a.id);
        }}
        action={a}
        status={statusOf(records, a.id)}
        selected={a.id === selectedId}
        onSelect={() => setSelectedId(a.id)}
        onOpen={() => setOpenId(a.id)}
        onStatus={(s) => change(a, s)}
      />
    ));

  const allResolved = progress.open === 0;
  const filtersActive = type !== "TODAS" || query.trim() !== "";

  return (
    <div>
      <header className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-muted">
          <span>
            Semana {weekNumber(report.farmacia.semana)} · datos hasta{" "}
            {formatDate(report.farmacia.fecha_datos)}
          </span>
          <button
            type="button"
            onClick={() => setHelpOpen(true)}
            className="no-print hidden items-center gap-1.5 hover:text-ink lg:inline-flex"
          >
            <Icon name="keyboard" size={14} /> Atajos <kbd>?</kbd>
          </button>
        </div>
        <div className="mt-3 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-sm font-medium text-ink-soft">Recuperable esta semana</h1>
            <p
              className="mt-1 text-4xl font-semibold tabular-nums tracking-tight text-ink sm:text-5xl"
              data-testid="recuperable"
            >
              {formatEur(progress.recoverable)}
            </p>
          </div>
          <div className="sm:text-right">
            <div className="text-xs text-ink-muted">Ya recuperado</div>
            <div className="text-xl font-semibold tabular-nums text-brand-text" data-testid="recuperado">
              {formatEur(progress.recovered)}
            </div>
          </div>
        </div>
        <div className="mt-4">
          <ProgressBar value={progress.done} max={progress.total} label="Acciones hechas esta semana" />
          <div className="mt-1.5 flex justify-between text-xs text-ink-muted">
            <span data-testid="progreso">
              {progress.done} de {progress.total} hechas
              {progress.dismissed ? ` · ${progress.dismissed} descartadas` : ""}
            </span>
            <span>{formatEur(progress.openAmount)} pendientes</span>
          </div>
        </div>
      </header>

      {allResolved ? (
        <div
          className="mb-6 rounded-card border border-brand/25 bg-brand-soft px-6 py-8 text-center"
          data-testid="semana-resuelta"
        >
          <div className="mx-auto grid h-10 w-10 place-items-center rounded-full bg-brand text-white">
            <Icon name="check" size={20} />
          </div>
          <h2 className="mt-3 text-xl font-semibold text-ink">
            Semana resuelta: {formatEur(progress.recovered)} recuperables
          </h2>
          <p className="mx-auto mt-1 max-w-md text-sm text-ink-soft">
            Has cerrado las {progress.total} acciones. Imprime la lista de devolución y el pedido corregido, y
            hasta el lunes que viene.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <ExportMenu report={report} records={records} />
            <ButtonLink href="/recuperado">Ver lo recuperado</ButtonLink>
          </div>
        </div>
      ) : null}

      <div className="no-print mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div
          role="group"
          aria-label="Filtrar por tipo"
          className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:pb-0"
        >
          {(["TODAS", ...ACTION_TYPES] as TypeFilter[]).map((t) => (
            <button
              key={t}
              type="button"
              aria-pressed={type === t}
              onClick={() => setType(t)}
              className={`inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors ${
                type === t
                  ? "border-ink bg-ink text-white"
                  : "border-line bg-white text-ink-soft hover:border-ink-faint"
              }`}
            >
              {t === "TODAS" ? "Todas" : TYPE_LABEL[t]}
              <span className={`tabular-nums ${type === t ? "text-white/80" : "text-ink-muted"}`}>
                {counts[t]}
              </span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="relative block flex-1 lg:w-72 lg:flex-none">
            <span className="sr-only">Buscar acciones</span>
            <Icon
              name="search"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
            />
            <input
              ref={search}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  setQuery("");
                  e.currentTarget.blur();
                }
              }}
              placeholder="Buscar producto, laboratorio o CN"
              className="h-9 w-full rounded-ctl border border-line bg-white pl-9 pr-9 text-sm placeholder:text-ink-faint focus:border-ink-faint focus:outline-none"
            />
            <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 lg:inline-flex">
              /
            </kbd>
          </label>
          {!allResolved ? <ExportMenu report={report} records={records} compact /> : null}
        </div>
      </div>

      {navigable.length > 0 ? (
        <section
          aria-label="Acciones pendientes"
          className="overflow-hidden rounded-card border border-line bg-white shadow-soft"
        >
          <ul data-testid="lista-acciones">
            {renderRows(groups.pending)}
            {groups.postponed.length ? (
              <>
                <li
                  className="border-y border-line bg-line-soft/60 px-4 py-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-muted"
                  aria-hidden="true"
                >
                  Pospuestas · {groups.postponed.length}
                </li>
                {renderRows(groups.postponed)}
              </>
            ) : null}
          </ul>
        </section>
      ) : !allResolved ? (
        <EmptyState title={filtersActive ? "Nada coincide con el filtro" : "No hay acciones pendientes"}>
          {filtersActive ? "Prueba con otro tipo o borra la búsqueda." : null}
        </EmptyState>
      ) : null}

      {groups.done.length + groups.dismissed.length > 0 ? (
        <section className="mt-6">
          <button
            type="button"
            onClick={() => setShowDone((v) => !v)}
            aria-expanded={showDone}
            className="flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink"
          >
            <Icon name="chevronRight" className={`transition-transform ${showDone ? "rotate-90" : ""}`} />
            Resueltas · {groups.done.length} hechas
            {groups.dismissed.length ? `, ${groups.dismissed.length} descartadas` : ""}
          </button>
          {showDone ? (
            <ul className="mt-2 overflow-hidden rounded-card border border-line bg-white">
              {renderRows([...groups.done, ...groups.dismissed])}
            </ul>
          ) : null}
        </section>
      ) : null}

      <ProductDrawer
        report={report}
        productId={openAction?.producto_id ?? null}
        action={openAction}
        onClose={() => setOpenId(null)}
      />
      <ShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
