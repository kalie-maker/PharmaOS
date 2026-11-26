import type { ButtonHTMLAttributes, ReactNode } from "react";
import Link from "next/link";

type Variant = "primary" | "secondary" | "ghost";

const BASE =
  "inline-flex items-center justify-center gap-1.5 rounded-ctl text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink-soft px-3.5 h-9",
  secondary: "border border-line bg-white text-ink hover:bg-line-soft px-3.5 h-9 shadow-soft",
  ghost: "text-ink-soft hover:bg-line-soft hover:text-ink px-2.5 h-8",
};

export function Button({
  variant = "secondary",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; children: ReactNode }) {
  return (
    <button type="button" className={`${BASE} ${VARIANTS[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function ButtonLink({
  href,
  variant = "secondary",
  className = "",
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={`${BASE} ${VARIANTS[variant]} ${className}`}>
      {children}
    </Link>
  );
}
