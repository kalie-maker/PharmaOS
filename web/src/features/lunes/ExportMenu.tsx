"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toast";
import type { ActionRecords } from "@/lib/actionStore";
import { downloadText } from "@/lib/csv";
import { exportFilename, orderCsv, orderLines, returnCsv, returnLines } from "@/lib/exports";
import type { Report } from "@/lib/types";

const ITEM =
  "flex w-full items-start gap-2.5 rounded-ctl px-3 py-2 text-left text-sm text-ink hover:bg-line-soft focus-visible:bg-line-soft";

export function ExportMenu({
  report,
  records,
  compact = false,
}: {
  report: Report;
  records: ActionRecords;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const download = (kind: "devolucion" | "pedido") => {
    const lines =
      kind === "devolucion" ? returnLines(report, records).length : orderLines(report, records).length;
    const csv = kind === "devolucion" ? returnCsv(report, records) : orderCsv(report, records);
    downloadText(
      exportFilename(kind === "devolucion" ? "lista_devolucion" : "pedido_corregido", report),
      csv,
    );
    toast.show(
      `${kind === "devolucion" ? "Lista de devolución" : "Pedido corregido"} descargado · ${lines} líneas`,
    );
    setOpen(false);
  };

  return (
    <div ref={root} className="no-print relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-9 items-center gap-1.5 rounded-ctl border border-line bg-white px-3 text-sm font-medium text-ink shadow-soft hover:bg-line-soft"
      >
        <Icon name="download" />{" "}
        {compact ? <span className="hidden sm:inline">Exportar</span> : "Exportar e imprimir"}
      </button>
      {open ? (
        <div
          role="menu"
          aria-label="Exportaciones"
          className="absolute right-0 z-20 mt-1.5 w-72 rounded-card border border-line bg-white p-1.5 shadow-lift"
        >
          <p className="px-3 pb-1 pt-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-muted">
            Lista de devolución
          </p>
          <Link role="menuitem" href="/imprimir/devolucion" className={ITEM} onClick={() => setOpen(false)}>
            <Icon name="print" className="mt-0.5 text-ink-muted" />
            <span>
              Imprimir A4
              <span className="block text-xs text-ink-muted">Para el proveedor, con total y firma</span>
            </span>
          </Link>
          <button role="menuitem" type="button" className={ITEM} onClick={() => download("devolucion")}>
            <Icon name="download" className="mt-0.5 text-ink-muted" /> Descargar CSV
          </button>
          <p className="px-3 pb-1 pt-2.5 text-2xs font-semibold uppercase tracking-wide text-ink-muted">
            Pedido
          </p>
          <button role="menuitem" type="button" className={ITEM} onClick={() => download("pedido")}>
            <Icon name="download" className="mt-0.5 text-ink-muted" />
            <span>
              Pedido corregido (CSV)
              <span className="block text-xs text-ink-muted">Qué no pedir y qué reponer, con unidades</span>
            </span>
          </button>
          <p className="px-3 pb-1 pt-2.5 text-2xs font-semibold uppercase tracking-wide text-ink-muted">
            Semana
          </p>
          <Link role="menuitem" href="/imprimir/resumen" className={ITEM} onClick={() => setOpen(false)}>
            <Icon name="print" className="mt-0.5 text-ink-muted" /> Resumen semanal (A4)
          </Link>
        </div>
      ) : null}
    </div>
  );
}
