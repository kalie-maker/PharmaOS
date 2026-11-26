"use client";

import { ReportGate } from "@/components/ReportGate";
import { AjustesView } from "./AjustesView";

export function AjustesScreen() {
  return <ReportGate>{(report) => <AjustesView report={report} />}</ReportGate>;
}
