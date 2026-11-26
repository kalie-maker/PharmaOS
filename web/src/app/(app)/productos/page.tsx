import type { Metadata } from "next";
import { ProductosScreen } from "@/features/productos/ProductosScreen";

export const metadata: Metadata = { title: "Productos" };

export default function ProductosPage() {
  return <ProductosScreen />;
}
