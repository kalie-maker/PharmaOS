import type { Metadata } from "next";
import { DemoStart } from "@/features/onboarding/DemoStart";

export const metadata: Metadata = { title: "Demo" };

export default function DemoPage() {
  return <DemoStart />;
}
