"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useAppState } from "@/lib/appState";

/** /demo: deja el navegador limpio y entra en la lista del lunes con la farmacia ficticia. */
export function DemoStart() {
  const { hydrated, resetDemo, updateSettings } = useAppState();
  const router = useRouter();
  const done = useRef(false);
  useEffect(() => {
    if (!hydrated || done.current) return;
    done.current = true;
    resetDemo();
    updateSettings({ onboarded: true, source: "demo" });
    router.replace("/lunes");
  }, [hydrated, resetDemo, updateSettings, router]);
  return (
    <main className="grid min-h-screen place-items-center bg-canvas">
      <p className="text-sm text-ink-muted" aria-live="polite">
        Preparando la demo…
      </p>
    </main>
  );
}
