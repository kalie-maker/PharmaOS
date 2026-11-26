"use client";

import { ReportGate } from "@/components/ReportGate";
import { LunesView } from "./LunesView";

export function LunesScreen() {
  return <ReportGate>{(report) => <LunesView report={report} />}</ReportGate>;
}
