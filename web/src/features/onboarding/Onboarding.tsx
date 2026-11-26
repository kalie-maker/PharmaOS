"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/AppShell";
import { Button } from "@/components/Button";
import { Icon, type IconName } from "@/components/Icon";
import { useAppState } from "@/lib/appState";

const STEPS: { icon: IconName; title: string; text: string; detail: string[] }[] = [
  {
    icon: "upload",
    title: "Sube tu export",
    text: "Ventas, stock y compras tal como salen de Farmatic, Nixfarma u otro programa. CSV o Excel.",
    detail: ["Sin rellenar nada", "Se lee en tu ordenador", "Columnas detectadas automáticamente"],
  },
  {
    icon: "shield",
    title: "Revisamos la privacidad",
    text: "Si un fichero trae datos de pacientes, se bloquea antes de leerlo. Solo trabajamos con producto, unidades e importes.",
    detail: ["Sin nombres ni DNI", "Sin CIP ni recetas", "Sin teléfonos ni direcciones"],
  },
  {
    icon: "list",
    title: "Tu lista del lunes",
    text: "Cada semana, las acciones que más dinero liberan: devolver, bajar pedido, reponer y promocionar antes de caducar.",
    detail: ["Ordenadas por euros", "Con el cálculo explicado", "10 minutos y listo"],
  },
];

export function Onboarding() {
  const { hydrated, settings } = useAppState();
  const router = useRouter();
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (hydrated && settings.onboarded) router.replace("/lunes");
  }, [hydrated, settings.onboarded, router]);

  if (!hydrated || settings.onboarded) return <div className="min-h-screen bg-canvas" aria-busy="true" />;
  const current = STEPS[step]!;

  return (
    <main className="min-h-screen bg-canvas">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-5 py-6 sm:px-8">
        <header className="flex items-center justify-between">
          <Logo />
          <Link href="/demo" className="text-sm font-medium text-ink-soft hover:text-ink">
            Ver demo →
          </Link>
        </header>

        <div className="grid flex-1 items-center gap-10 py-10 lg:grid-cols-[1.05fr_1fr]">
          <section>
            <p className="text-sm font-medium text-brand">Copiloto de rentabilidad para farmacias</p>
            <h1 className="mt-3 text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
              Tu lista de acciones del lunes, con euros.
            </h1>
            <p className="mt-4 max-w-lg text-base text-ink-soft">
              PharmaOS lee las exportaciones de tu programa de gestión y te dice qué devolver, qué no pedir,
              qué reponer y qué promocionar antes de que caduque. Cálculos verificados, cero datos de
              pacientes.
            </p>
            <div className="mt-8 flex flex-wrap gap-2">
              <Button
                variant="primary"
                onClick={() => router.push("/demo")}
                className="h-10 px-4"
                data-testid="ver-demo"
              >
                <Icon name="play" /> Ver demo
              </Button>
              <Button onClick={() => router.push("/subir")} className="h-10 px-4">
                <Icon name="upload" /> Subir mis datos
              </Button>
            </div>
          </section>

          <section
            aria-label="Cómo funciona"
            className="rounded-card border border-line bg-white p-6 shadow-lift sm:p-8"
          >
            <ol className="flex gap-2" aria-label="Pasos">
              {STEPS.map((s, i) => (
                <li key={s.title} className="flex-1">
                  <button
                    type="button"
                    onClick={() => setStep(i)}
                    aria-current={i === step ? "step" : undefined}
                    aria-label={`Paso ${i + 1}: ${s.title}`}
                    className={`h-1.5 w-full rounded-full transition-colors ${i <= step ? "bg-ink" : "bg-line"}`}
                  />
                </li>
              ))}
            </ol>
            <div className="mt-7" aria-live="polite">
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-ctl bg-line-soft text-ink">
                  <Icon name={current.icon} size={18} />
                </span>
                <span className="text-xs font-medium text-ink-muted">
                  Paso {step + 1} de {STEPS.length}
                </span>
              </div>
              <h2 className="mt-4 text-xl font-semibold tracking-tight text-ink">{current.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{current.text}</p>
              <ul className="mt-5 space-y-2">
                {current.detail.map((d) => (
                  <li key={d} className="flex items-center gap-2 text-sm text-ink">
                    <Icon name="check" className="text-brand" /> {d}
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-8 flex items-center justify-between">
              <Button
                variant="ghost"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
              >
                Atrás
              </Button>
              {step < STEPS.length - 1 ? (
                <Button variant="primary" onClick={() => setStep((s) => s + 1)}>
                  Siguiente <Icon name="arrowRight" />
                </Button>
              ) : (
                <Button variant="primary" onClick={() => router.push("/demo")}>
                  Ver la lista de ejemplo <Icon name="arrowRight" />
                </Button>
              )}
            </div>
          </section>
        </div>
        <footer className="text-xs text-ink-faint">
          Versión de demostración con una farmacia ficticia. Ningún dato sale de este navegador.
        </footer>
      </div>
    </main>
  );
}
