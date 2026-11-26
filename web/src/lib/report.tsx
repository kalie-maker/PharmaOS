"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchEngineReport } from "./engineApi";
import { loadSettings } from "./settings";
import type { Report } from "./types";

/** Origen de los datos: mock estático (demo) o API local del motor. Mañana: Supabase. */
export interface ReportSource {
  id: "demo" | "motor";
  load(): Promise<Report>; // núcleo ligero: acciones + sus productos
  loadFull(): Promise<Report>; // catálogo completo (solo /productos)
}

async function fetchMock(url: string): Promise<Report> {
  const res = await fetch(url, { cache: "force-cache" });
  if (!res.ok) throw new Error(`No se pudo cargar el informe (${res.status})`);
  const data = (await res.json()) as Report;
  if (data.version !== 1) throw new Error("Versión de informe no compatible");
  return data;
}

export const mockReportSource: ReportSource = {
  id: "demo",
  load: () => fetchMock("/mock/report-core.json"),
  loadFull: () => fetchMock("/mock/report.json"),
};

export const engineReportSource: ReportSource = {
  id: "motor",
  load: () => fetchEngineReport(true),
  loadFull: () => fetchEngineReport(false),
};

/** El origen activo sale de los ajustes guardados (`source: "motor"` tras un análisis real). */
export function activeSource(): ReportSource {
  return loadSettings().source === "motor" ? engineReportSource : mockReportSource;
}

type State =
  { status: "loading" } | { status: "ready"; report: Report } | { status: "error"; message: string };

interface Ctx {
  state: State;
  sourceId: ReportSource["id"];
  reload: () => void;
}

const ReportContext = createContext<Ctx>({
  state: { status: "loading" },
  sourceId: "demo",
  reload: () => undefined,
});

const cache = new Map<string, Promise<Report>>();
function cached(key: string, load: () => Promise<Report>): Promise<Report> {
  let p = cache.get(key);
  if (!p) {
    p = load().catch((e: unknown) => {
      cache.delete(key);
      throw e;
    });
    cache.set(key, p);
  }
  return p;
}

const message = (e: unknown) => (e instanceof Error ? e.message : "Error desconocido");

export function ReportProvider({ children, source }: { children: ReactNode; source?: ReportSource }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [version, setVersion] = useState(0);
  const [sourceId, setSourceId] = useState<ReportSource["id"]>("demo");

  useEffect(() => {
    let alive = true;
    const src = source ?? activeSource();
    setSourceId(src.id);
    setState({ status: "loading" });
    cached(`${src.id}:core:${version}`, src.load)
      .then((report) => alive && setState({ status: "ready", report }))
      .catch((e: unknown) => alive && setState({ status: "error", message: message(e) }));
    return () => {
      alive = false;
    };
  }, [source, version]);

  const reload = useCallback(() => {
    cache.clear();
    setVersion((v) => v + 1);
  }, []);

  return <ReportContext.Provider value={{ state, sourceId, reload }}>{children}</ReportContext.Provider>;
}

export function useReportState(): State {
  return useContext(ReportContext).state;
}

export function useReportControls(): { sourceId: ReportSource["id"]; reload: () => void } {
  const { sourceId, reload } = useContext(ReportContext);
  return { sourceId, reload };
}

/** Catálogo completo de productos del origen activo. Solo lo pide /productos. */
export function useFullReport(): State {
  const { sourceId } = useContext(ReportContext);
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    let alive = true;
    const src = sourceId === "motor" ? engineReportSource : mockReportSource;
    cached(`${src.id}:full`, src.loadFull)
      .then((report) => alive && setState({ status: "ready", report }))
      .catch((e: unknown) => alive && setState({ status: "error", message: message(e) }));
    return () => {
      alive = false;
    };
  }, [sourceId]);
  return state;
}
