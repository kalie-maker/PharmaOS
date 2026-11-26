import type { Metadata } from "next";
import { SubirView } from "@/features/subir/SubirView";

export const metadata: Metadata = { title: "Subir datos" };

export default function SubirPage() {
  return <SubirView />;
}
