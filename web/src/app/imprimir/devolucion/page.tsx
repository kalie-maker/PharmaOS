import type { Metadata } from "next";
import { DevolucionPrint } from "@/features/imprimir/DevolucionPrint";

export const metadata: Metadata = { title: "Lista de devolución" };

export default function Page() {
  return <DevolucionPrint />;
}
