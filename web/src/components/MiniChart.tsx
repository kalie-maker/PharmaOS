import { formatNumber } from "@/lib/format";

/** Barras SVG propias (sin librerías). La última barra (semana actual) va resaltada. */
export function MiniChart({
  values,
  labels,
  height = 96,
  title,
  unit = "uds",
}: {
  values: number[];
  labels?: string[];
  height?: number;
  title: string;
  unit?: string;
}) {
  const max = Math.max(1, ...values);
  const width = 100;
  const gap = 1.6;
  const barW = (width - gap * (values.length - 1)) / Math.max(values.length, 1);
  const total = values.reduce((s, v) => s + v, 0);
  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="block h-24 w-full"
        role="img"
        aria-label={`${title}: ${values.map((v) => formatNumber(v)).join(", ")} ${unit}`}
      >
        <line
          x1="0"
          y1={height - 0.5}
          x2={width}
          y2={height - 0.5}
          stroke="#E7E5E4"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
        />
        {values.map((v, i) => {
          const h = v === 0 ? 1.5 : Math.max(3, (v / max) * (height - 6));
          const last = i === values.length - 1;
          return (
            <rect
              key={i}
              x={i * (barW + gap)}
              y={height - h}
              width={barW}
              height={h}
              rx={1.2}
              fill={last ? "#168C6C" : v === 0 ? "#E7E5E4" : "#A1A1AA"}
            >
              <title>{`${labels?.[i] ?? `Semana ${i + 1}`}: ${formatNumber(v)} ${unit}`}</title>
            </rect>
          );
        })}
      </svg>
      <figcaption className="mt-1.5 flex justify-between text-2xs text-ink-muted">
        <span>{labels?.[0] ?? "Hace 12 semanas"}</span>
        <span>
          Total {formatNumber(total)} {unit} · máx. {formatNumber(max)}
        </span>
        <span>{labels?.[labels.length - 1] ?? "Esta semana"}</span>
      </figcaption>
    </figure>
  );
}
