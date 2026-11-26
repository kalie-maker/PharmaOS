"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

interface ToastItem {
  id: number;
  message: string;
  action?: { label: string; onClick: () => void };
}

interface ToastApi {
  show: (message: string, action?: ToastItem["action"]) => void;
}

const Ctx = createContext<ToastApi>({ show: () => undefined });
const DURATION_MS = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const show = useCallback((message: string, action?: ToastItem["action"]) => {
    const id = nextId.current++;
    setToasts((t) => [...t.slice(-2), { id, message, action }]);
  }, []);

  return (
    <Ctx.Provider value={{ show }}>
      {children}
      <div
        aria-live="polite"
        role="status"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6"
      >
        {toasts.map((t) => (
          <Toast key={t.id} item={t} onDone={() => dismiss(t.id)} />
        ))}
      </div>
    </Ctx.Provider>
  );
}

function Toast({ item, onDone }: { item: ToastItem; onDone: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDone, DURATION_MS);
    return () => clearTimeout(timer);
  }, [onDone]);
  return (
    <div className="pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-ctl bg-ink px-4 py-2.5 text-sm text-white shadow-lift">
      <span className="min-w-0 flex-1 truncate">{item.message}</span>
      {item.action ? (
        <button
          type="button"
          className="rounded px-1.5 py-0.5 font-semibold text-white underline-offset-2 hover:underline focus-visible:outline-white"
          onClick={() => {
            item.action?.onClick();
            onDone();
          }}
        >
          {item.action.label}
        </button>
      ) : null}
    </div>
  );
}

export function useToast(): ToastApi {
  return useContext(Ctx);
}
