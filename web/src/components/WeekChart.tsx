import { formatEur } from "@/lib/format";

export interface WeekBar {
  label: string;
  encontrado: number;
  ejecutado: number;
  recuperado: number;
  enCurso?: boolean;
}

const SERIES = [
  { key: "encontrado", label: "Encontrado", color: "#E7E5E4" },
  { key: "ejecutado", label: "Ejecutado", color: "#A1A1AA" },
  { key: "recuperado", label: "Recuperado", color: "#168C6C" },
] as const;

/** Barras agrupadas por semana, SVG propio. Incluye una tabla accesible para lectores de pantalla. */
export function WeekChart({ data }: { data: WeekBar[] }) {
  const max = Math.max(1, ...data.map((d) => d.encontrado));
  const H = 180;
  const groupW = 100 / Math.max(data.length, 1);
  const barW = (groupW * 0.72) / 3;
  return (
    <figure className="m-0">
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-ink-soft" aria-hidden="true">
        {SERIES.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
      <svg
        viewBox={`0 0 100 ${H}`}
        preserveAspectRatio="none"
        className="block h-48 w-full"
        aria-hidden="true"
      >
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1="0"
            x2="100"
            y1={H * f}
            y2={H * f}
            stroke="#F0EFED"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {data.map((d, i) =>
          SERIES.map((s, j) => {
            const v = d[s.key];
            const h = (v / max) * (H - 4);
            return (
              <rect
                key={`${i}-${s.key}`}
                x={i * groupW + groupW * 0.14 + j * barW}
                y={H - h}
                width={barW * 0.9}
                height={Math.max(h, v > 0 ? 1 : 0)}
                rx={0.6}
                fill={s.color}
                opacity={d.enCurso && s.key !== "encontrado" ? 0.75 : 1}
              />
            );
          }),
        )}
      </svg>
      <div
        className="mt-1.5 grid text-center text-2xs text-ink-muted"
        style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0,1fr))` }}
        aria-hidden="true"
      >
        {data.map((d) => (
          <span key={d.label} className={d.enCurso ? "font-semibold text-ink" : ""}>
            {d.label}
          </span>
        ))}
      </div>
      <table className="sr-only">
        <caption>Euros por semana</caption>
        <thead>
          <tr>
            <th scope="col">Semana</th>
            {SERIES.map((s) => (
              <th key={s.key} scope="col">
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.label}>
              <th scope="row">{d.label}</th>
              {SERIES.map((s) => (
                <td key={s.key}>{formatEur(d[s.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
