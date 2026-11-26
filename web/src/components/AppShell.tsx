"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAppState } from "@/lib/appState";
import { useReportState } from "@/lib/report";
import { Icon, type IconName } from "./Icon";

const NAV: { href: string; label: string; short: string; icon: IconName }[] = [
  { href: "/lunes", label: "Lista del lunes", short: "Lunes", icon: "list" },
  { href: "/productos", label: "Productos", short: "Productos", icon: "box" },
  { href: "/recuperado", label: "Recuperado", short: "Recuperado", icon: "chart" },
  { href: "/subir", label: "Subir datos", short: "Subir", icon: "upload" },
  { href: "/ajustes", label: "Ajustes", short: "Ajustes", icon: "settings" },
];

export function Logo() {
  return (
    <span className="flex items-center gap-2 text-[15px] font-semibold tracking-tight text-ink">
      <span
        className="grid h-6 w-6 place-items-center rounded-[7px] bg-ink text-[11px] font-bold text-white"
        aria-hidden="true"
      >
        P
      </span>
      PharmaOS
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { settings } = useAppState();
  const state = useReportState();
  const name = settings.pharmacyName ?? (state.status === "ready" ? state.report.farmacia.nombre : "");
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Saltar al contenido
      </a>
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-line bg-white/70 px-3 py-5 backdrop-blur lg:flex">
        <div className="px-2">
          <Link href="/lunes" aria-label="PharmaOS, ir a la lista del lunes">
            <Logo />
          </Link>
        </div>
        <nav aria-label="Principal" className="mt-8 flex flex-col gap-0.5">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive(item.href) ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-ctl px-2.5 py-2 text-sm transition-colors ${
                isActive(item.href)
                  ? "bg-line-soft font-medium text-ink"
                  : "text-ink-muted hover:bg-line-soft/70 hover:text-ink"
              }`}
            >
              <Icon name={item.icon} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto rounded-ctl border border-line bg-white px-3 py-2.5">
          <div className="truncate text-xs font-medium text-ink">{name || "—"}</div>
          <div className="mt-0.5 flex items-center gap-1 text-2xs text-ink-muted">
            <Icon name="shield" size={12} /> Sin datos de pacientes
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-line bg-canvas/90 px-4 backdrop-blur lg:hidden">
        <Logo />
        <span className="max-w-[50%] truncate text-xs text-ink-muted">{name}</span>
      </header>

      <main id="contenido" className="px-4 pb-28 pt-5 sm:px-6 lg:ml-60 lg:px-10 lg:pb-12 lg:pt-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>

      <nav
        aria-label="Principal móvil"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
      >
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive(item.href) ? "page" : undefined}
            className={`flex flex-col items-center gap-1 py-2 text-[11px] ${isActive(item.href) ? "font-semibold text-ink" : "text-ink-muted"}`}
          >
            <Icon name={item.icon} size={18} />
            {item.short}
          </Link>
        ))}
      </nav>
    </div>
  );
}
