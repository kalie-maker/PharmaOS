"use client";

import Link from "next/link";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-xl font-semibold text-ink">Algo ha fallado</h1>
      <p className="mt-2 text-sm text-ink-muted">
        No se ha perdido nada: lo que marcaste está guardado en este navegador. Prueba a reintentar; si sigue
        fallando, abre la demo de nuevo.
      </p>
      <div className="mt-6 flex gap-2">
        <button
          type="button"
          onClick={reset}
          className="inline-flex h-9 items-center rounded-ctl bg-ink px-3.5 text-sm font-medium text-white"
        >
          Reintentar
        </button>
        <Link
          href="/demo"
          className="inline-flex h-9 items-center rounded-ctl border border-line bg-white px-3.5 text-sm text-ink"
        >
          Abrir la demo
        </Link>
      </div>
    </main>
  );
}
