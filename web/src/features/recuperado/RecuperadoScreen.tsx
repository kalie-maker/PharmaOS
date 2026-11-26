"use client";

import { ReportGate } from "@/components/ReportGate";
import { RecuperadoView } from "./RecuperadoView";

export function RecuperadoScreen() {
  return <ReportGate>{(report) => <RecuperadoView report={report} />}</ReportGate>;
}
