import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  devIndicators: false,
  // Raíz del proyecto fija: evita el aviso si hay otro package-lock.json fuera del repo (p. ej. en ~).
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
