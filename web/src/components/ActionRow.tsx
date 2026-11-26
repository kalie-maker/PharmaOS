"use client";

import { forwardRef } from "react";
import type { ActionStatus } from "@/lib/actionStore";
import { formatEur } from "@/lib/format";
import type { Action } from "@/lib/types";
import { TypeBadge, UrgencyBadge } from "./Badge";
import { Icon } from "./Icon";

interface Props {
  action: Action;
  status: ActionStatus;
  selected: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onStatus: (status: ActionStatus) => void;
}

export const ActionRow = forwardRef<HTMLLIElement, Props>(function ActionRow(
  { action, status, selected, onSelect, onOpen, onStatus },
  ref,
) {
  const resolved = status === "hecha" || status === "descartada";
  return (
    <li
      ref={ref}
      data-action-id={action.id}
      data-selected={selected || undefined}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`group relative grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 border-b border-line-soft px-4 py-3.5 last:border-b-0 sm:grid-cols-[1fr_120px_110px_auto] sm:items-center ${
        selected ? "bg-brand-soft/50" : "hover:bg-line-soft/50"
      }`}
    >
      {selected ? (
        <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-brand" aria-hidden="true" />
      ) : null}
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <TypeBadge type={action.tipo} />
          {!resolved ? <UrgencyBadge urgency={action.urgencia} /> : null}
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
            onOpen();
          }}
          className={`mt-1.5 block max-w-full truncate text-left text-sm font-semibold hover:underline ${
            resolved ? "text-ink-muted line-through decoration-ink-faint" : "text-ink"
          }`}
        >
          {action.titulo}
        </button>
        <p className="mt-0.5 truncate text-xs text-ink-muted">{action.motivo_1_linea}</p>
      </div>
      <div className="hidden text-xs text-ink-soft sm:block">
        <span className="inline-flex items-center gap-1">
          <Icon name="clock" size={13} className="text-ink-faint" />
          {action.plazo_texto}
        </span>
      </div>
      <div
        className={`col-start-2 row-start-1 text-right text-sm font-semibold tabular-nums sm:col-start-auto sm:row-start-auto ${
          status === "hecha" ? "text-brand" : resolved ? "text-ink-faint" : "text-ink"
        }`}
      >
        {formatEur(action.importe_eur)}
      </div>
      <div className="col-span-2 flex items-center justify-end gap-1 sm:col-span-1">
        <span className="mr-auto text-xs text-ink-muted sm:hidden">{action.plazo_texto}</span>
        {status === "pendiente" || status === "pospuesta" ? (
          <>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onStatus("hecha");
              }}
              className="inline-flex h-8 items-center gap-1 rounded-ctl border border-line bg-white px-2.5 text-xs font-medium text-ink shadow-soft hover:border-brand hover:text-brand-dark"
              aria-label={`Marcar como hecha: ${action.titulo}`}
            >
              <Icon name="check" size={14} /> Hecho
            </button>
            {status === "pendiente" ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onStatus("pospuesta");
                }}
                className="inline-flex h-8 items-center gap-1 rounded-ctl px-2 text-xs text-ink-muted hover:bg-line-soft hover:text-ink"
                aria-label={`Posponer: ${action.titulo}`}
                title="Posponer (P)"
              >
                <Icon name="clock" size={14} />
                <span className="hidden md:inline">Posponer</span>
              </button>
            ) : null}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onStatus("descartada");
              }}
              className="inline-flex h-8 items-center gap-1 rounded-ctl px-2 text-xs text-ink-muted hover:bg-line-soft hover:text-ink"
              aria-label={`Descartar: ${action.titulo}`}
              title="Descartar (D)"
            >
              <Icon name="x" size={14} />
              <span className="hidden md:inline">Descartar</span>
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onStatus("pendiente");
            }}
            className="inline-flex h-8 items-center gap-1 rounded-ctl px-2 text-xs text-ink-muted hover:bg-line-soft hover:text-ink"
            aria-label={`Deshacer: ${action.titulo}`}
          >
            <Icon name="undo" size={14} /> Deshacer
          </button>
        )}
      </div>
    </li>
  );
});
