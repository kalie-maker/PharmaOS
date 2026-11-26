import type { ReactNode } from "react";

export function Kpi({
  label,
  value,
  hint,
  tone = "default",
  size = "md",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "brand";
  size?: "md" | "lg";
}) {
  return (
    <div className="min-w-0">
      <div className="text-xs font-medium text-ink-muted">{label}</div>
      <div
        className={`mt-1 font-semibold tabular-nums tracking-tight ${size === "lg" ? "text-3xl sm:text-4xl" : "text-2xl"} ${
          tone === "brand" ? "text-brand" : "text-ink"
        }`}
      >
        {value}
      </div>
      {hint ? <div className="mt-1 text-xs text-ink-muted">{hint}</div> : null}
    </div>
  );
}
