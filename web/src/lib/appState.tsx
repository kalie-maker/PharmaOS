"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { ActionRecords, ActionStatus, ActionStore } from "./actionStore";
import { createLocalStorageActionStore, statusOf, withStatus } from "./actionStore";
import { useReportState } from "./report";
import { DEFAULT_SETTINGS, loadSettings, saveSettings, type Settings } from "./settings";
import { STORAGE_PREFIX, removeKeys } from "./storage";

interface AppState {
  hydrated: boolean;
  settings: Settings;
  updateSettings: (patch: Partial<Settings>) => void;
  records: ActionRecords;
  /** Cambia el estado y devuelve el anterior (para deshacer). */
  setStatus: (id: string, status: ActionStatus) => ActionStatus;
  resetDemo: () => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children, store }: { children: ReactNode; store?: ActionStore }) {
  const reportState = useReportState();
  const week = reportState.status === "ready" ? reportState.report.farmacia.semana : null;
  const actionStore = useMemo(() => store ?? createLocalStorageActionStore(), [store]);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [records, setRecords] = useState<ActionRecords>({});
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (week) setRecords(actionStore.load(week));
  }, [week, actionStore]);

  const updateSettings = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveSettings(next);
      return next;
    });
  }, []);

  const setStatus = useCallback(
    (id: string, status: ActionStatus): ActionStatus => {
      const previous = statusOf(records, id);
      const next = withStatus(records, id, status);
      setRecords(next);
      if (week) actionStore.save(week, next);
      return previous;
    },
    [records, week, actionStore],
  );

  const resetDemo = useCallback(() => {
    actionStore.clear();
    removeKeys(STORAGE_PREFIX);
    setRecords({});
    setSettings(DEFAULT_SETTINGS);
  }, [actionStore]);

  const value = useMemo(
    () => ({ hydrated, settings, updateSettings, records, setStatus, resetDemo }),
    [hydrated, settings, updateSettings, records, setStatus, resetDemo],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAppState fuera de AppStateProvider");
  return ctx;
}
