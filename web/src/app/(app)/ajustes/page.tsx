import type { Metadata } from "next";
import { AjustesScreen } from "@/features/ajustes/AjustesScreen";

export const metadata: Metadata = { title: "Ajustes" };

export default function AjustesPage() {
  return <AjustesScreen />;
}
