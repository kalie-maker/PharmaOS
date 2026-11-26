import type { ActionType, Urgency } from "@/lib/types";
import { TYPE_LABEL } from "@/lib/types";

const DOT: Record<ActionType, string> = {
  CADUCA_PRONTO: "bg-warn",
  DEVOLVER: "bg-ink",
  BAJAR_PEDIDO: "bg-ink-muted",
  REPONER: "bg-brand",
};

export function TypeBadge({ type }: { type: ActionType }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-line bg-white px-2 py-0.5 text-2xs font-medium text-ink-soft">
      <span className={`h-1.5 w-1.5 rounded-full ${DOT[type]}`} aria-hidden="true" />
      {TYPE_LABEL[type]}
    </span>
  );
}

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  if (urgency !== "alta") return null;
  return (
    <span className="whitespace-nowrap rounded-full bg-urgent-soft px-2 py-0.5 text-2xs font-semibold text-urgent-text">
      Urgente
    </span>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "brand" | "warn" | "urgent";
}) {
  const tones = {
    neutral: "bg-line-soft text-ink-soft",
    brand: "bg-brand-soft text-brand-dark",
    warn: "bg-warn-soft text-warn",
    urgent: "bg-urgent-soft text-urgent-text",
  };
  return (
    <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-2xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  );
}
