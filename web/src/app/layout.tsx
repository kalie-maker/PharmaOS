import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "PharmaOS", template: "%s · PharmaOS" },
  description: "Copiloto de rentabilidad para farmacias: tu lista de acciones del lunes, con euros.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: "#FAFAF9", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
