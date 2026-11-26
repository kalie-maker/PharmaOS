import type { Metadata } from "next";
import { RecuperadoScreen } from "@/features/recuperado/RecuperadoScreen";

export const metadata: Metadata = { title: "Recuperado" };

export default function RecuperadoPage() {
  return <RecuperadoScreen />;
}
