"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import { Card, PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { useAppState } from "@/lib/appState";
import { DATASET_LABEL } from "@/lib/columns";
import { formatDate, formatNumber } from "@/lib/format";
import { analyzeParsed, FileError, parseFile, type FileAnalysis } from "@/lib/parseFile";

const PREVIEW_ROWS = 20;
const ACCEPT = ".csv,.txt,.tsv,.xlsx,.xlsm";

function cellText(v: unknown): string {
  if (v instanceof Date) return formatDate(v.toISOString());
  return String(v ?? "");
}

function FileCard({ a, onRemove }: { a: FileAnalysis; onRemove: () => void }) {
  const blocked = a.privacy.length > 0;
  const { file, detection, summary } = a;
  const format = file.kind === "xlsx" ? `Excel · hoja «${file.sheet}»` : `CSV · ${file.encoding}`;
  return (
    <Card className="p-0">
      <div className="flex items-start gap-3 border-b border-line px-5 py-4">
        <Icon name="file" size={18} className="mt-0.5 text-ink-muted" />
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-ink">{file.name}</div>
          <div className="mt-0.5 text-xs text-ink-muted">
            {format} · cabecera en la fila {file.headerRow} · {file.headers.length} columnas
          </div>
        </div>
        <button
          type="button"
          onClick={onRemove}
          className="rounded-ctl p-1.5 text-ink-muted hover:bg-line-soft"
          aria-label={`Quitar ${file.name}`}
        >
          <Icon name="x" />
        </button>
      </div>

      {blocked ? (
        <div
          role="alert"
          className="m-5 rounded-ctl border border-urgent/30 bg-urgent-soft px-4 py-3.5 text-sm"
          data-testid="bloqueo-privacidad"
        >
          <div className="flex items-center gap-2 font-semibold text-urgent-text">
            <Icon name="shield" /> Fichero bloqueado: contiene datos personales
          </div>
          <ul className="mt-2 space-y-1 text-ink">
            {a.privacy.map((f) => (
              <li key={f.column}>
                Columna <strong>«{f.column}»</strong>: {f.reason}
                {f.source === "contenido" ? ` (${f.matches} celdas)` : ""}.
              </li>
            ))}
          </ul>
          <p className="mt-2 text-ink-soft">
            PharmaOS no trabaja con datos de pacientes. Vuelve a exportar el fichero sin esas columnas (solo
            producto, fechas, unidades e importes). No se ha mostrado ni guardado nada.
          </p>
        </div>
      ) : (
        <div className="space-y-4 px-5 py-4">
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <span>
              <span className="text-ink-muted">Tipo: </span>
              <strong>{DATASET_LABEL[detection.dataset]}</strong>
              {detection.program ? (
                <span className="text-ink-muted"> · mapeo {detection.program}</span>
              ) : null}
            </span>
            <span>
              <span className="text-ink-muted">Filas: </span>
              <strong className="tabular-nums">{formatNumber(summary.rows)}</strong>
            </span>
            <span>
              <span className="text-ink-muted">Productos: </span>
              <strong className="tabular-nums" data-testid="resumen-productos">
                {formatNumber(summary.products)}
              </strong>
            </span>
            {summary.dateFrom ? (
              <span>
                <span className="text-ink-muted">Fechas: </span>
                <strong>
                  {formatDate(summary.dateFrom)} – {formatDate(summary.dateTo)}
                </strong>
              </span>
            ) : null}
          </div>
          {detection.missingRequired.length ? (
            <p className="rounded-ctl bg-warn-soft px-3 py-2 text-sm text-warn">
              Faltan columnas obligatorias: {detection.missingRequired.join(", ")}. Revisa el mapeo antes del
              análisis real.
            </p>
          ) : null}
          <details className="text-sm">
            <summary className="cursor-pointer text-ink-soft hover:text-ink">Columnas detectadas</summary>
            <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
              {detection.matches.map((m) => (
                <div key={m.canonical} className="flex justify-between gap-3 border-b border-line-soft py-1">
                  <dt className="text-ink-muted">{m.canonical}</dt>
                  <dd className={m.column ? "text-ink" : m.required ? "text-warn" : "text-ink-muted"}>
                    {m.column ?? (m.required ? "falta" : "—")}
                  </dd>
                </div>
              ))}
            </dl>
          </details>
          <div>
            <div className="mb-1.5 text-xs text-ink-muted">
              Primeras {Math.min(PREVIEW_ROWS, file.rows.length)} filas
            </div>
            <div
              className="max-h-80 overflow-auto rounded-ctl border border-line"
              tabIndex={0}
              role="region"
              aria-label={`Vista previa de ${file.name}`}
            >
              <table className="w-full border-collapse text-xs" data-testid="vista-previa">
                <thead className="sticky top-0 bg-line-soft">
                  <tr>
                    {file.headers.map((h) => (
                      <th
                        key={h}
                        scope="col"
                        className="whitespace-nowrap px-2.5 py-1.5 text-left font-semibold text-ink-soft"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {file.rows.slice(0, PREVIEW_ROWS).map((row, i) => (
                    <tr key={i} className="border-t border-line-soft">
                      {file.headers.map((h, j) => (
                        <td key={h} className="whitespace-nowrap px-2.5 py-1 tabular-nums text-ink">
                          {cellText(row[j])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

export function SubirView() {
  const [analyses, setAnalyses] = useState<FileAnalysis[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const toast = useToast();
  const { updateSettings } = useAppState();

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    setBusy(true);
    const nextErrors: string[] = [];
    const results: FileAnalysis[] = [];
    for (const file of Array.from(files)) {
      try {
        results.push(analyzeParsed(await parseFile(file)));
      } catch (e) {
        nextErrors.push(
          `${file.name}: ${e instanceof FileError ? e.message : "no se ha podido leer el fichero."}`,
        );
      }
    }
    setAnalyses((prev) => [
      ...prev.filter((p) => !results.some((r) => r.file.name === p.file.name)),
      ...results,
    ]);
    setErrors(nextErrors);
    setBusy(false);
  }, []);

  const blocked = analyses.some((a) => a.privacy.length > 0);
  const ready = analyses.length > 0 && !blocked;

  const analyze = () => {
    updateSettings({ source: "subido", onboarded: true });
    toast.show("Análisis simulado: se muestra la farmacia de demostración con tus columnas validadas.");
    router.push("/lunes");
  };

  return (
    <div>
      <PageHeader
        title="Subir datos"
        description="Arrastra las exportaciones de ventas, stock y compras de tu programa de gestión. Se leen en este ordenador: no se envían a ningún servidor."
      />
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFiles(e.dataTransfer.files);
        }}
        className={`rounded-card border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging ? "border-brand bg-brand-soft/60" : "border-line bg-white"
        }`}
      >
        <Icon name="upload" size={22} className="mx-auto text-ink-muted" />
        <p className="mt-3 text-sm font-medium text-ink">Arrastra aquí tus ficheros CSV o Excel</p>
        <p className="mt-1 text-xs text-ink-muted">
          Farmatic, Nixfarma u otro programa · hasta 50 MB por fichero
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Button variant="primary" onClick={() => input.current?.click()} disabled={busy}>
            {busy ? "Leyendo…" : "Elegir ficheros"}
          </Button>
        </div>
        <input
          ref={input}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          aria-label="Elegir ficheros de exportación"
          data-testid="input-ficheros"
          onChange={(e) => {
            if (e.target.files?.length) void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <p className="mt-4 text-xs text-ink-muted">
          ¿Sin ficheros a mano? Prueba con{" "}
          <a className="underline hover:text-ink" href="/ejemplos/ventas_ejemplo.csv" download>
            ventas de ejemplo
          </a>
          ,{" "}
          <a className="underline hover:text-ink" href="/ejemplos/stock_ejemplo.csv" download>
            stock de ejemplo
          </a>{" "}
          o un{" "}
          <a className="underline hover:text-ink" href="/ejemplos/ejemplo_bloqueado.csv" download>
            fichero que se bloquea
          </a>
          .
        </p>
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-ctl bg-line-soft/70 px-4 py-3 text-xs text-ink-soft">
        <Icon name="shield" className="mt-0.5 shrink-0 text-brand-text" />
        <span>
          Antes de nada revisamos la privacidad: si un fichero trae nombres de pacientes, DNI, CIP o tarjeta
          sanitaria, nº de receta, teléfono, email o dirección, se bloquea y no se muestra.
        </span>
      </div>

      {errors.length ? (
        <div
          role="alert"
          className="mt-4 rounded-ctl border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn"
        >
          {errors.map((e) => (
            <div key={e}>{e}</div>
          ))}
        </div>
      ) : null}

      <div className="mt-6 space-y-4">
        {analyses.map((a) => (
          <FileCard
            key={a.file.name}
            a={a}
            onRemove={() => setAnalyses((prev) => prev.filter((p) => p !== a))}
          />
        ))}
      </div>

      {analyses.length ? (
        <div className="sticky bottom-20 mt-6 flex flex-col gap-3 rounded-card border border-line bg-white/95 p-4 shadow-lift backdrop-blur sm:flex-row sm:items-center sm:justify-between lg:bottom-4">
          <p className="text-sm text-ink-soft">
            {blocked
              ? "Hay ficheros bloqueados por privacidad. Quítalos o vuelve a exportarlos."
              : `${analyses.length} fichero${analyses.length > 1 ? "s" : ""} validado${analyses.length > 1 ? "s" : ""}. En esta versión el análisis se simula con la farmacia de demostración.`}
          </p>
          <Button variant="primary" onClick={analyze} disabled={!ready} data-testid="analizar">
            Analizar <Icon name="arrowRight" />
          </Button>
        </div>
      ) : null}
    </div>
  );
}
