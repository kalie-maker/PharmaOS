"use client";

import type { ReactNode } from "react";
import { ToastProvider } from "@/components/Toast";
import { AppStateProvider } from "@/lib/appState";
import { ReportProvider } from "@/lib/report";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ReportProvider>
      <AppStateProvider>
        <ToastProvider>{children}</ToastProvider>
      </AppStateProvider>
    </ReportProvider>
  );
}
