# PharmaOS · web (MVP)

Copiloto de rentabilidad para farmacias: la lista de acciones del lunes, con euros.
Next.js 15 (App Router) + React 19 + TypeScript estricto + Tailwind. Datos **mock** de una farmacia ficticia;
sin backend, sin autenticación y sin APIs externas.

## Arrancar

```bash
npm install
npm run dev          # http://localhost:3000  (demo limpia: http://localhost:3000/demo)
```

Producción local: `npm run build && npm start`.

## Comprobaciones

| Comando              | Qué hace                                                                           |
| -------------------- | ---------------------------------------------------------------------------------- |
| `npm run check`      | Tipos + ESLint + Prettier + Vitest                                                 |
| `npm run e2e`        | Playwright (escritorio y móvil) con auditoría axe; regenera `../docs/screenshots/` |
| `npm run gen:mock`   | Regenera `public/mock/report.json` y `report-core.json` con el motor Python        |
| `npm run gen:config` | Regenera los mapeos y reglas de privacidad desde el motor (`src/generated/`)       |

## Estructura

- `src/app/` — rutas: `/` (onboarding), `/demo`, `/lunes`, `/productos`, `/recuperado`, `/subir`, `/ajustes`,
  `/imprimir/devolucion`, `/imprimir/resumen`.
- `src/features/` — una carpeta por pantalla.
- `src/components/` — sistema de diseño (AppShell, ActionRow, Drawer, DataTable virtualizada, MiniChart…).
- `src/lib/` — lógica pura y testeada: acciones, `ActionStore` (localStorage, sustituible por Supabase),
  exportaciones, privacidad, detección de columnas, lectura de ficheros.
- `public/mock/` — contrato `report.json` (ver `../stock-profit-os/docs/report-schema.md`).
