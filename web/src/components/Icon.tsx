import type { SVGProps } from "react";

// Iconos de trazo fino, 16 px por defecto. Solo los que se usan.
const PATHS = {
  check: "M3.5 8.5l3 3 6-7",
  clock: "M8 4.5V8l2.5 1.5M14 8A6 6 0 112 8a6 6 0 0112 0z",
  x: "M4 4l8 8M12 4l-8 8",
  search: "M7 12A5 5 0 107 2a5 5 0 000 10zM14 14l-3.5-3.5",
  download: "M8 2.5v8m0 0l-3-3m3 3l3-3M3 13.5h10",
  print: "M4.5 6V2.5h7V6M4.5 11.5h-2v-5h11v5h-2M4.5 9.5h7v4h-7z",
  upload: "M8 10.5v-8m0 0l-3 3m3-3l3 3M3 13.5h10",
  list: "M5.5 4h8M5.5 8h8M5.5 12h8M2.5 4h.01M2.5 8h.01M2.5 12h.01",
  chart: "M2.5 13.5h11M4.5 11V8M8 11V4.5M11.5 11V6.5",
  settings:
    "M8 10a2 2 0 100-4 2 2 0 000 4zM13 8l1.3-.8-1-1.8-1.5.3-.9-.9.3-1.5-1.8-1-.8 1.3H7.4l-.8-1.3-1.8 1 .3 1.5-.9.9-1.5-.3-1 1.8L3 8l-1.3.8 1 1.8 1.5-.3.9.9-.3 1.5 1.8 1 .8-1.3h1.2l.8 1.3 1.8-1-.3-1.5.9-.9 1.5.3 1-1.8z",
  box: "M2.5 5L8 2l5.5 3v6L8 14l-5.5-3zM2.5 5L8 8m0 0l5.5-3M8 8v6",
  undo: "M5 6.5H10a3 3 0 010 6H6M5 6.5L7.5 4M5 6.5L7.5 9",
  keyboard: "M2 4.5h12v7H2zM4.5 7h.01M7 7h.01M9.5 7h.01M12 7h.01M5 9.5h6",
  chevronRight: "M6 3.5L10.5 8 6 12.5",
  shield: "M8 1.8l5 2v4c0 3.2-2.2 5.4-5 6.4-2.8-1-5-3.2-5-6.4v-4z M5.8 8l1.6 1.6 3-3",
  info: "M8 14A6 6 0 108 2a6 6 0 000 12zM8 7.2v3.8M8 5h.01",
  arrowRight: "M3 8h10m0 0L9 4m4 4l-4 4",
  file: "M4 1.8h5l3 3V14H4zM9 1.8V5h3",
  alert: "M8 2l6.5 11.5h-13zM8 6.5v3M8 11.5h.01",
  play: "M5 3.5l7 4.5-7 4.5z",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 16,
  ...props
}: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
