"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { TypeBadge } from "@/components/Badge";
import { DataTable, type Column } from "@/components/DataTable";
import { Icon } from "@/components/Icon";
import { ProductDrawer } from "@/components/ProductDrawer";
import { formatDate, formatEur, formatNumber } from "@/lib/format";
import { actionsByProduct, families, filterProducts, type ProductSort } from "@/lib/products";
import type { Product, Report } from "@/lib/types";

const SORTS: { value: ProductSort; label: string }[] = [
  { value: "valor", label: "Más capital inmovilizado" },
  { value: "cobertura", label: "Más días de cobertura" },
  { value: "sin_venta", label: "Más tiempo sin vender" },
  { value: "nombre", label: "Nombre (A-Z)" },
];

export function ProductosView({ report }: { report: Report }) {
  const [query, setQuery] = useState("");
  const [family, setFamily] = useState("");
  const [sort, setSort] = useState<ProductSort>("valor");
  const [onlyWithAction, setOnlyWithAction] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);
  const withAction = useMemo(() => actionsByProduct(report), [report]);
  const familyList = useMemo(() => families(report), [report]);
  const rows = useMemo(
    () => filterProducts(report, { query: deferredQuery, family, sort, onlyWithAction }, withAction),
    [report, deferredQuery, family, sort, onlyWithAction, withAction],
  );
  const total = Object.keys(report.productos).length;
  const value = rows.reduce((s, p) => s + (p.valor_stock ?? 0), 0);

  const columns: Column<Product>[] = [
    {
      key: "nombre",
      header: "Producto",
      width: "minmax(0,1fr)",
      render: (p) => (
        <span className="flex min-w-0 items-center gap-2">
          <span className="truncate font-medium text-ink">{p.nombre ?? "—"}</span>
          {withAction.has(p.codigo) ? <TypeBadge type={withAction.get(p.codigo)!.tipo} /> : null}
        </span>
      ),
    },
    {
      key: "codigo",
      header: "CN",
      width: "72px",
      hideOnMobile: true,
      render: (p) => <span className="tabular-nums text-ink-muted">{p.codigo}</span>,
    },
    {
      key: "familia",
      header: "Familia",
      width: "150px",
      hideOnMobile: true,
      render: (p) => <span className="text-ink-soft">{p.familia}</span>,
    },
    {
      key: "stock",
      header: "Stock",
      width: "64px",
      align: "right",
      hideOnMobile: true,
      render: (p) => formatNumber(p.stock),
    },
    {
      key: "valor",
      header: "Valor",
      width: "88px",
      align: "right",
      render: (p) => formatEur(p.valor_stock, 2),
    },
    {
      key: "cobertura",
      header: "Cobertura",
      width: "84px",
      align: "right",
      hideOnMobile: true,
      render: (p) =>
        p.dias_cobertura === null ? (
          <span className="text-ink-muted">sin ventas</span>
        ) : (
          `${formatNumber(p.dias_cobertura)} d`
        ),
    },
    {
      key: "venta",
      header: "Última venta",
      width: "96px",
      align: "right",
      hideOnMobile: true,
      render: (p) => formatDate(p.ultima_venta),
    },
  ];

  return (
    <div>
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <label className="relative block sm:w-72">
          <span className="sr-only">Buscar productos</span>
          <Icon
            name="search"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nombre, CN o laboratorio"
            className="h-9 w-full rounded-ctl border border-line bg-white pl-9 pr-3 text-sm placeholder:text-ink-faint focus:border-ink-faint focus:outline-none"
          />
        </label>
        <select
          aria-label="Familia"
          value={family}
          onChange={(e) => setFamily(e.target.value)}
          className="h-9 rounded-ctl border border-line bg-white px-2.5 text-sm"
        >
          <option value="">Todas las familias</option>
          {familyList.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <select
          aria-label="Ordenar"
          value={sort}
          onChange={(e) => setSort(e.target.value as ProductSort)}
          className="h-9 rounded-ctl border border-line bg-white px-2.5 text-sm"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <label className="inline-flex items-center gap-2 text-sm text-ink-soft">
          <input
            type="checkbox"
            checked={onlyWithAction}
            onChange={(e) => setOnlyWithAction(e.target.checked)}
            className="h-4 w-4 accent-brand"
          />
          Solo con acción esta semana
        </label>
        <span className="text-xs text-ink-muted sm:ml-auto" data-testid="productos-resumen">
          {formatNumber(rows.length)} productos{rows.length !== total ? ` de ${formatNumber(total)}` : ""} ·{" "}
          {formatEur(value)} a coste
        </span>
      </div>
      <DataTable
        rows={rows}
        columns={columns}
        rowKey={(p) => p.codigo}
        onRowClick={(p) => setOpenId(p.codigo)}
        label="Productos"
        height={600}
      />
      <ProductDrawer
        report={report}
        productId={openId}
        action={openId ? withAction.get(openId) : undefined}
        onClose={() => setOpenId(null)}
      />
    </div>
  );
}
