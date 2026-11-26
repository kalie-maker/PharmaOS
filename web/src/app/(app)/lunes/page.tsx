import type { Metadata } from "next";
import { LunesScreen } from "@/features/lunes/LunesScreen";

export const metadata: Metadata = { title: "Lista del lunes" };

export default function LunesPage() {
  return <LunesScreen />;
}
