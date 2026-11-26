# Lighthouse 12.8.2 (móvil emulado, build de producción, 26/11/2026)

| Pantalla | Rendimiento | Accesibilidad | Buenas prácticas | LCP |
|---|---:|---:|---:|---:|
| `/` (onboarding) | 99 | 100 | 96 | 2,1 s |
| `/lunes` | 98 | 100 | 96 | 2,3 s |
| `/productos` (8.000 refs) | 99 | 100 | 96 | 1,8 s |
| `/recuperado` | 96 | 100 | 96 | 2,7 s |
| `/subir` | 98 | 100 | 96 | 2,2 s |
| `/ajustes` | 96 | 100 | 96 | 2,4 s |

Reproducir: `npm run build && npx next start -p 3100` y
`CHROME_PATH=<chrome> npx lighthouse@12.8.2 http://localhost:3100/lunes --chrome-flags="--headless=new"`.
