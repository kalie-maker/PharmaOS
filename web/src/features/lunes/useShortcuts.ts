"use client";

import { useEffect, useRef } from "react";

export type ShortcutHandlers = Partial<
  Record<"next" | "prev" | "done" | "postpone" | "dismiss" | "open" | "search" | "help", () => void>
>;

const KEYMAP: Record<string, keyof ShortcutHandlers> = {
  j: "next",
  k: "prev",
  arrowdown: "next",
  arrowup: "prev",
  h: "done",
  p: "postpone",
  d: "dismiss",
  enter: "open",
  "/": "search",
  "?": "help",
};

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/** Atajos globales de la lista. Se desactivan al escribir o con un diálogo abierto. */
export function useShortcuts(handlers: ShortcutHandlers, enabled: boolean): void {
  const ref = useRef(handlers);
  ref.current = handlers;
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      if (document.querySelector('[aria-modal="true"]')) return;
      const name = KEYMAP[e.key.toLowerCase()] ?? KEYMAP[e.key];
      if (!name) return;
      // Enter sobre un botón o enlace conserva su comportamiento nativo.
      if (name === "open" && e.target instanceof HTMLElement && e.target.closest("button, a")) return;
      const handler = ref.current[name];
      if (!handler) return;
      e.preventDefault();
      handler();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}
