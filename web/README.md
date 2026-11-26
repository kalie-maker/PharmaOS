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

### Análisis real con el motor local (opcional)

En otra terminal, con Python 3.11+:

```bash
cd ../stock-profit-os && pip install -e ".[api]"
```

```bash
npm run motor        # API en http://localhost:8000 (documentación en /docs)
```

Con el motor arrancado, en **/subir** sube ventas, stock y compras y pulsa **Analizar**: el informe real
sustituye a la demo en todas las pantallas. Ajustes → "Origen de los datos" permite volver a la demo o
borrar el análisis. Sin motor, /subir valida los ficheros y simula el análisis con la demo.
URL del motor configurable con `NEXT_PUBLIC_MOTOR_URL`.

## Comprobaciones

| Comando              | Qué hace                                                                                           |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| `npm run check`      | Tipos + ESLint + Prettier + Vitest                                                                 |
| `npm run e2e`        | Playwright (escritorio y móvil) con auditoría axe; regenera `../docs/screenshots/`                 |
| `npm run motor`      | API local del motor (`stock-profit-os/engine/api.py`); los e2e la arrancan solos en el puerto 8100 |
| `npm run gen:mock`   | Regenera `public/mock/report.json` y `report-core.json` con el motor Python                        |
| `npm run gen:config` | Regenera los mapeos y reglas de privacidad desde el motor (`src/generated/`)                       |

## Estructura

- `src/app/` — rutas: `/` (onboarding), `/demo`, `/lunes`, `/productos`, `/recuperado`, `/subir`, `/ajustes`,
  `/imprimir/devolucion`, `/imprimir/resumen`.
- `src/features/` — una carpeta por pantalla.
- `src/components/` — sistema de diseño (AppShell, ActionRow, Drawer, DataTable virtualizada, MiniChart…).
- `src/lib/` — lógica pura y testeada: acciones, `ActionStore` (localStorage, sustituible por Supabase),
  exportaciones, privacidad, detección de columnas, lectura de ficheros.
- `public/mock/` — contrato `report.json` (ver `../stock-profit-os/docs/report-schema.md`).
