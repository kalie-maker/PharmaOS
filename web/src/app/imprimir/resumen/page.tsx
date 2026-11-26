import type { Metadata } from "next";
import { ResumenPrint } from "@/features/imprimir/ResumenPrint";

export const metadata: Metadata = { title: "Resumen semanal" };

export default function Page() {
  return <ResumenPrint />;
}
