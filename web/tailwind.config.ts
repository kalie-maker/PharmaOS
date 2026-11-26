import type { Config } from "tailwindcss";

// Tokens de marca. Verde solo para acentos y € positivos; rojo solo para urgencias.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#FAFAF9",
        ink: { DEFAULT: "#18181B", soft: "#3F3F46", muted: "#71717A", faint: "#A1A1AA" },
        line: { DEFAULT: "#E7E5E4", soft: "#F0EFED" },
        brand: { DEFAULT: "#168C6C", dark: "#0F6E54", soft: "#E8F5F0" },
        urgent: { DEFAULT: "#DC4A3C", soft: "#FDEDEB" },
        warn: { DEFAULT: "#B45309", soft: "#FEF5E1" },
      },
      fontFamily: {
        sans: [
          '"Inter Variable"',
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
      },
      borderRadius: { card: "14px", ctl: "10px" },
      boxShadow: {
        soft: "0 1px 2px rgba(24,24,27,0.04), 0 1px 3px rgba(24,24,27,0.06)",
        lift: "0 8px 24px rgba(24,24,27,0.08), 0 2px 6px rgba(24,24,27,0.05)",
        drawer: "-12px 0 32px rgba(24,24,27,0.10)",
      },
      fontSize: { "2xs": ["11px", "16px"] },
    },
  },
  plugins: [],
};

export default config;
