"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  width: string; // ancho CSS de la columna (grid)
  align?: "left" | "right";
  render: (row: T) => ReactNode;
  hideOnMobile?: boolean;
}

/**
 * Tabla virtualizada sin dependencias: solo pinta las filas visibles (altura fija).
 * Fluida con decenas de miles de filas.
 */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  onRowClick,
  rowHeight = 44,
  height = 560,
  label,
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  rowHeight?: number;
  height?: number;
  label: string;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewport, setViewport] = useState(height);
  const overscan = 8;

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const update = () => setViewport(el.clientHeight);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
    setScrollTop(0);
  }, [rows]);

  const onScroll = useCallback(() => setScrollTop(scroller.current?.scrollTop ?? 0), []);
  const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const end = Math.min(rows.length, Math.ceil((scrollTop + viewport) / rowHeight) + overscan);
  const visible = rows.slice(start, end);
  const template = columns.map((c) => c.width).join(" ");
  const mobileTemplate = columns
    .filter((c) => !c.hideOnMobile)
    .map((c) => c.width)
    .join(" ");

  return (
    <div
      className="overflow-hidden rounded-card border border-line bg-white shadow-soft"
      role="table"
      aria-label={label}
      aria-rowcount={rows.length + 1}
    >
      <style>{`.dt-grid{grid-template-columns:${mobileTemplate}}@media(min-width:768px){.dt-grid{grid-template-columns:${template}}}`}</style>
      <div role="rowgroup" className="border-b border-line bg-line-soft/60">
        <div
          role="row"
          aria-rowindex={1}
          className="dt-grid grid items-center gap-3 px-4 py-2.5 text-2xs font-semibold uppercase tracking-wide text-ink-muted"
        >
          {columns.map((c) => (
            <div
              key={c.key}
              role="columnheader"
              className={`${c.align === "right" ? "text-right" : ""} ${c.hideOnMobile ? "hidden md:block" : ""} truncate`}
            >
              {c.header}
            </div>
          ))}
        </div>
      </div>
      <div
        ref={scroller}
        onScroll={onScroll}
        style={{ height }}
        className="overflow-y-auto"
        role="rowgroup"
        tabIndex={0}
        aria-label={`${label}: filas`}
      >
        <div style={{ height: rows.length * rowHeight, position: "relative" }}>
          {visible.map((row, i) => {
            const index = start + i;
            return (
              <div
                key={rowKey(row)}
                role="row"
                aria-rowindex={index + 2}
                tabIndex={onRowClick ? 0 : -1}
                onClick={() => onRowClick?.(row)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && onRowClick) onRowClick(row);
                }}
                style={{ position: "absolute", top: index * rowHeight, height: rowHeight, left: 0, right: 0 }}
                className={`dt-grid grid items-center gap-3 border-b border-line-soft px-4 text-sm ${onRowClick ? "cursor-pointer hover:bg-line-soft/60 focus-visible:bg-brand-soft" : ""}`}
              >
                {columns.map((c) => (
                  <div
                    key={c.key}
                    role="cell"
                    className={`truncate ${c.align === "right" ? "text-right tabular-nums" : ""} ${c.hideOnMobile ? "hidden md:block" : ""}`}
                  >
                    {c.render(row)}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
