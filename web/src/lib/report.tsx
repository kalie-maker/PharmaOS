"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Report } from "./types";

/** Origen de los datos. Hoy: mock estático. Mañana: API local del motor o Supabase. */
export interface ReportSource {
  load(): Promise<Report>;
}

export const mockReportSource: ReportSource = {
  async load() {
    const res = await fetch("/mock/report.json", { cache: "force-cache" });
    if (!res.ok) throw new Error(`No se pudo cargar el informe (${res.status})`);
    const data = (await res.json()) as Report;
    if (data.version !== 1) throw new Error("Versión de informe no compatible");
    return data;
  },
};

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
