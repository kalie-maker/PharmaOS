"use client";

import { ReportGate } from "@/components/ReportGate";
import { ProductosView } from "./ProductosView";

export function ProductosScreen() {
  return <ReportGate>{(report) => <ProductosView report={report} />}</ReportGate>;
}
