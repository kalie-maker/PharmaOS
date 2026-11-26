import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${PORT}`, trace: "off" },
  projects: [
    {
      name: "escritorio",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 },
    },
    { name: "movil", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      // Motor local con un directorio de datos temporal (no toca out/api).
      command:
        "cd ../stock-profit-os && PHARMAOS_DATA_DIR=$(mktemp -d) python3 -m engine.cli servir --puerto 8100",
      url: "http://127.0.0.1:8100/salud",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: `NEXT_PUBLIC_MOTOR_URL=http://127.0.0.1:8100 npm run build && npx next start -p ${PORT}`,
      url: `http://localhost:${PORT}`,
      reuseExistingServer: true,
      timeout: 240_000,
    },
  ],
});
