"use client";

import type { ReactNode } from "react";
import { PageHeader } from "@/components/PageHeader";
import { useFullReport } from "@/lib/report";
import { ProductosView } from "./ProductosView";

function Frame({ children }: { children: ReactNode }) {
  return (
    <div>
      <PageHeader
        title="Productos"
        description="Todas las referencias del programa de gestión. Ordena por capital inmovilizado para ver dónde está el dinero parado."
      />
      {children}
    </div>
  );
}

export function ProductosScreen() {
  return (
    <Frame>
      <Catalog />
    </Frame>
  );
}

function Catalog() {
  const state = useFullReport();
  if (state.status === "error")
    return (
      <div role="alert" className="rounded-card border border-urgent/30 bg-urgent-soft px-5 py-4 text-sm">
        No se ha podido cargar el catálogo: {state.message}
      </div>
    );
  if (state.status === "loading")
    return (
      <div aria-busy="true" className="space-y-3">
        <span className="sr-only">Cargando el catálogo de productos…</span>
        <div className="h-7 w-48 animate-pulse rounded bg-line" />
        <div className="h-[600px] animate-pulse rounded-card bg-line/60" />
      </div>
    );
  return <ProductosView report={state.report} />;
}
