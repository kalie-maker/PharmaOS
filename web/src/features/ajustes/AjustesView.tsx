"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/Button";
import { Dialog } from "@/components/Dialog";
import { Icon } from "@/components/Icon";
import { Card, PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { ENGINE_CONFIG } from "@/generated/engineConfig";
import { useAppState } from "@/lib/appState";
import { DATASETS, DATASET_LABEL } from "@/lib/columns";
import { formatDate } from "@/lib/format";
import type { Report } from "@/lib/types";

const COLUMN_LABEL: Record<string, string> = {
  fecha: "Fecha",
  codigo_nacional: "Código nacional",
  descripcion: "Descripción",
  laboratorio: "Laboratorio",
  familia: "Familia",
  unidades: "Unidades",
  importe_venta_sin_iva: "Importe sin IVA",
  coste_unitario: "Coste unitario",
  stock_unidades: "Stock",
  pvp: "PVP",
  fecha_caducidad: "Caducidad",
  coste_total: "Coste total",
};

const PROCESSED = [
  "Código nacional, descripción, laboratorio y familia del producto",
  "Fechas de venta y de albarán",
  "Unidades vendidas, compradas y en stock",
  "Importes sin IVA, costes y PVP",
  "Fecha de caducidad",
];

const NEVER = [
  "Nombre o apellidos de pacientes y clientes",
  "DNI, NIE, NIF o pasaporte",
  "CIP, tarjeta sanitaria o nº de la Seguridad Social",
  "Número de receta o datos de prescripción",
  "Teléfono, email o dirección",
  "Fecha de nacimiento, sexo, diagnósticos o alergias",
];

type Program = keyof typeof ENGINE_CONFIG.mappings;
const PROGRAMS = Object.keys(ENGINE_CONFIG.mappings) as Program[];

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-[240px_1fr]">
        <div>
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {description ? <p className="mt-1 text-xs text-ink-muted">{description}</p> : null}
        </div>
        <div className="min-w-0">{children}</div>
      </div>
    </Card>
  );
}

const INPUT =
  "h-9 w-full rounded-ctl border border-line bg-white px-3 text-sm focus:border-ink-faint focus:outline-none";

export function AjustesView({ report }: { report: Report }) {
  const { settings, updateSettings, resetDemo } = useAppState();
  const toast = useToast();
  const router = useRouter();
  const [program, setProgram] = useState<Program>((report.farmacia.programa as Program) ?? PROGRAMS[0]!);
  const [confirm, setConfirm] = useState(false);
  const mapping = ENGINE_CONFIG.mappings[program].ficheros as Record<
    string,
    Record<string, readonly string[]>
  >;

  return (
    <div className="space-y-5">
      <PageHeader title="Ajustes" description="Datos de la farmacia, plan, columnas y privacidad." />

      <Section title="Farmacia" description="Aparece en la lista, los informes y las impresiones.">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-xs font-medium text-ink-muted">Nombre</span>
            <input
              className={INPUT}
              defaultValue={settings.pharmacyName ?? report.farmacia.nombre}
              onBlur={(e) => {
                const value = e.target.value.trim();
                updateSettings({ pharmacyName: value && value !== report.farmacia.nombre ? value : null });
                toast.show("Nombre guardado");
              }}
            />
          </label>
          <div className="text-sm">
            <span className="mb-1 block text-xs font-medium text-ink-muted">Datos cargados</span>
            <p className="pt-2 text-ink">
              {report.farmacia.programa ?? "—"} · hasta {formatDate(report.farmacia.fecha_datos)}
              {report.farmacia.ficticia ? <span className="ml-1 text-ink-muted">(demostración)</span> : null}
            </p>
          </div>
        </div>
      </Section>

      <Section title="Plan" description="Se usa para calcular el múltiplo frente al coste en Recuperado.">
        <label className="block max-w-xs text-sm">
          <span className="mb-1 block text-xs font-medium text-ink-muted">Coste mensual (€)</span>
          <input
            type="number"
            min={0}
            step={1}
            inputMode="numeric"
            className={INPUT}
            defaultValue={settings.monthlyCost}
            aria-describedby="coste-ayuda"
            onBlur={(e) => {
              const value = Number(e.target.value);
              if (Number.isFinite(value) && value >= 0) {
                updateSettings({ monthlyCost: value });
                toast.show("Coste guardado");
              }
            }}
          />
          <span id="coste-ayuda" className="mt-1 block text-xs text-ink-muted">
            Por defecto 149 €/mes, con garantía de recuperar ×3.
          </span>
        </label>
      </Section>

      <Section
        title="Mapeo de columnas"
        description="Cómo se leen las exportaciones de cada programa. Solo lectura: se edita en el motor (config/mappings)."
      >
        <div
          role="group"
          aria-label="Programa"
          className="mb-4 inline-flex rounded-ctl border border-line bg-line-soft p-0.5"
        >
          {PROGRAMS.map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={program === p}
              onClick={() => setProgram(p)}
              className={`rounded-[8px] px-3 py-1.5 text-xs font-medium capitalize ${program === p ? "bg-white text-ink shadow-soft" : "text-ink-muted"}`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="space-y-4">
          {DATASETS.map((ds) => (
            <div key={ds}>
              <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
                {DATASET_LABEL[ds]}
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  {ENGINE_CONFIG.schemas[ds].columns
                    .filter((canonical) => mapping[ds]?.[canonical])
                    .map((canonical) => [canonical, mapping[ds]![canonical]!] as const)
                    .map(([canonical, aliases]) => (
                      <tr key={canonical} className="border-b border-line-soft">
                        <th scope="row" className="w-40 py-1.5 pr-3 text-left font-medium text-ink">
                          {COLUMN_LABEL[canonical] ?? canonical}
                          {(ENGINE_CONFIG.schemas[ds].required as readonly string[]).includes(canonical) ? (
                            <span className="text-ink-muted"> *</span>
                          ) : null}
                        </th>
                        <td className="py-1.5 text-ink-soft">
                          {aliases.map((a) => (
                            <code
                              key={a}
                              className="mr-1.5 inline-block rounded bg-line-soft px-1.5 py-0.5 text-xs"
                            >
                              {a}
                            </code>
                          ))}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}
          <p className="text-xs text-ink-muted">
            <span>*</span> Obligatoria. Las cabeceras se comparan sin mayúsculas, tildes ni puntuación.
          </p>
        </div>
      </Section>

      <Section
        title="Privacidad"
        description="PharmaOS trabaja con datos de producto, nunca con datos de pacientes."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-ctl border border-line p-4">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
              <Icon name="check" className="text-brand" /> Qué procesamos
            </h3>
            <ul className="mt-2 space-y-1.5 text-sm text-ink-soft">
              {PROCESSED.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-ctl border border-line p-4">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-ink">
              <Icon name="x" className="text-urgent" /> Qué nunca procesamos
            </h3>
            <ul className="mt-2 space-y-1.5 text-sm text-ink-soft">
              {NEVER.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        </div>
        <p className="mt-3 text-xs text-ink-muted">
          Si un fichero trae alguna de esas columnas se bloquea antes de leerlo (
          {ENGINE_CONFIG.privacyHeaderRules.length} reglas, las mismas que el motor). En esta versión todo se
          queda en este navegador.
        </p>
      </Section>

      <Section
        title="Demo"
        description="Vuelve al estado inicial: borra acciones marcadas y ajustes de este navegador."
      >
        <Button onClick={() => setConfirm(true)} data-testid="reiniciar-demo">
          <Icon name="undo" /> Reiniciar la demo
        </Button>
      </Section>

      <Dialog open={confirm} onClose={() => setConfirm(false)} title="¿Reiniciar la demo?">
        <p className="text-sm text-ink-soft">
          Se borrarán las acciones marcadas y los ajustes guardados en este navegador.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button onClick={() => setConfirm(false)}>Cancelar</Button>
          <Button
            variant="primary"
            onClick={() => {
              resetDemo();
              setConfirm(false);
              router.push("/");
            }}
          >
            Reiniciar
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
