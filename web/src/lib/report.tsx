"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Report } from "./types";

/** Origen de los datos. Hoy: mock estático. Mañana: API local del motor o Supabase. */
export interface ReportSource {
  load(): Promise<Report>;
}

async function fetchReport(url: string): Promise<Report> {
  const res = await fetch(url, { cache: "force-cache" });
  if (!res.ok) throw new Error(`No se pudo cargar el informe (${res.status})`);
  const data = (await res.json()) as Report;
  if (data.version !== 1) throw new Error("Versión de informe no compatible");
  return data;
}

/** Núcleo ligero (acciones + sus productos) para todas las pantallas; catálogo completo bajo demanda. */
export const mockReportSource: ReportSource & { loadFull(): Promise<Report> } = {
  load: () => fetchReport("/mock/report-core.json"),
  loadFull: () => fetchReport("/mock/report.json"),
};

let fullCache: Promise<Report> | null = null;

/** Catálogo completo de productos (8.000 referencias). Solo lo pide /productos. */
export function useFullReport():
  { status: "loading" } | { status: "ready"; report: Report } | { status: "error"; message: string } {
  const [state, setState] = useState<
    { status: "loading" } | { status: "ready"; report: Report } | { status: "error"; message: string }
  >({
    status: "loading",
  });
  useEffect(() => {
    let alive = true;
    fullCache ??= mockReportSource.loadFull();
    fullCache
      .then((report) => alive && setState({ status: "ready", report }))
      .catch((e: unknown) => {
        fullCache = null;
        if (alive)
          setState({ status: "error", message: e instanceof Error ? e.message : "Error desconocido" });
      });
    return () => {
      alive = false;
    };
  }, []);
  return state;
}

type State =
  { status: "loading" } | { status: "ready"; report: Report } | { status: "error"; message: string };

const ReportContext = createContext<State>({ status: "loading" });

let cache: Promise<Report> | null = null;

export function ReportProvider({
  children,
  source = mockReportSource,
}: {
  children: ReactNode;
  source?: ReportSource;
}) {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    let alive = true;
    cache ??= source.load();
    cache
      .then((report) => alive && setState({ status: "ready", report }))
      .catch((e: unknown) => {
        cache = null;
        if (alive)
          setState({ status: "error", message: e instanceof Error ? e.message : "Error desconocido" });
      });
    return () => {
      alive = false;
    };
  }, [source]);
  return <ReportContext.Provider value={state}>{children}</ReportContext.Provider>;
}

export function useReportState(): State {
  return useContext(ReportContext);
}
