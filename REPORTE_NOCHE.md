# Reporte de la noche — PharmaOS Web MVP

## 1. Qué está hecho

| Fase | Estado | Resultado |
|---|---|---|
| 0 · Plan | ✅ | `PLAN.md`, `DECISIONES.md`, `PENDIENTE.md`. Motor: 242 tests en verde al empezar |
| 1 · Contrato | ✅ | `exportar-json` → `report.json`; esquema en `stock-profit-os/docs/report-schema.{md,json}`; tests: valida, importes = métricas del motor, sin campos sensibles |
| 2 · Mock | ✅ | 8.000 refs, 40 acciones, 6 semanas. **Recuperable 5.790 €/semana · inmovilizado 31.816 €** |
| 3 · Base web | ✅ | Next.js 15 + TS estricto + Tailwind; ESLint, Prettier, Vitest, Playwright; tokens y componentes propios |
| 4 · /lunes | ✅ | Lista por €, filtros con contador, buscador, atajos J/K/H/P/D/Enter///?, deshacer en aviso, `ActionStore` (localStorage), "Semana resuelta" |
| 5 · Ficha | ✅ | Drawer con ventas de 12 semanas, stock, inmovilizado, cobertura, última venta, caducidad y **cálculo paso a paso**. Extra: catálogo `/productos` virtualizado |
| 6 · Exportaciones | ✅ | Lista de devolución CSV + A4 (por laboratorio, total y firma), pedido corregido CSV, resumen semanal A4 |
| 7 · /subir | ✅ | CSV/XLSX en el navegador, mapeos **generados** desde los YAML, privacidad en cliente (bloquea), vista previa de 20 filas, resumen; análisis simulado |
| 8 · /recuperado | ✅ | Encontrado / Ejecutado / Recuperado, gráfico semanal, múltiplo vs coste y garantía ×3, tabla de ejecutadas |
| 9 · /ajustes | ✅ | Farmacia, coste del plan, mapeo de columnas (solo lectura), privacidad, reiniciar demo |
| 10 · Demo | ✅ | Onboarding de 3 pasos con "Ver demo", `/demo` limpia, `DEMO.md` (guion de 3 minutos) |
| 11 · Calidad | ✅ | Vitest 78, Playwright 11 (escritorio + móvil) con axe-core, Lighthouse ≥ 96, capturas |
| 12 · Pulido | ✅ 3 tandas | `PULIDO.md`: urgencias reales, acciones desde la ficha, móvil compacto, textos |

**No hecho / simplificado** (detalle en `PENDIENTE.md`): el análisis real desde `/subir` (se simula con el
mock), el histórico de semanas anteriores es simulado, y no hay exportación a PDF propia (se imprime el
HTML A4 desde el navegador).

## 2. Cómo arrancar

```bash
cd web
npm install
npm run dev
```

Abre http://localhost:3000 (onboarding) o **http://localhost:3000/demo** (demo limpia, recomendado en visitas).

Regenerar datos (opcional, requiere Python 3.11+ con el motor): `npm run gen:mock` y `npm run gen:config`.

## 3. Resultados

| Comprobación | Resultado |
|---|---|
| Motor `pytest` | **257 passed** (242 previos + 15 nuevos) · pyflakes limpio |
| Web `npm run check` (tsc + ESLint + Prettier + Vitest) | **OK · 78 tests** |
| Web `npm run e2e` (Playwright, escritorio + móvil, axe WCAG 2.1 AA) | **11 passed**, 1 omitido (atajos de teclado solo en escritorio) |
| Lighthouse (móvil) | Rendimiento 96–99 · Accesibilidad 100 · Buenas prácticas 96 → `docs/lighthouse/RESUMEN.md` |
| Configuración generada al día | ✅ (`export_web_config.py --comprobar`) |

## 4. Capturas

`docs/screenshots/` (escritorio a 2×, móvil Pixel 7): onboarding, lunes, ficha de producto, productos,
recuperado, subir (con bloqueo), ajustes, lista de devolución y resumen semanal. Ejemplos:
[lunes](docs/screenshots/02-lunes-escritorio.png) · [ficha](docs/screenshots/03-ficha-producto-escritorio.png) ·
[recuperado](docs/screenshots/05-recuperado-escritorio.png) · [subir](docs/screenshots/06-subir-escritorio.png) ·
[lunes móvil](docs/screenshots/02-lunes-movil.png). Se regeneran con `npm run e2e`.

## 5. Decisiones importantes tomadas sin ti (todas en `DECISIONES.md`)

1. **⚠️ No he hecho push** (lo pediste así y el sistema lo bloqueó). Los 15 commits están **solo en local** en la
   rama `claude/pensive-hawking-mx2rld` (no existía `feat/web-mvp`). Este contenedor es efímero: **haz push
   de la rama, o pídemelo, antes de que se recicle**, o se perderá el trabajo.
2. **Acciones por producto** (no por tipo): las de más € de cada tipo, con cupos en `config.yaml > web`.
3. **Urgente (rojo) solo con plazo real**: caduca en ≤ 30 días o rotura de una referencia de venta frecuente.
4. **"Recuperado" = capital liberado + ventas salvadas.** Con los rangos pedidos el múltiplo sale ×75–80 frente a
   149 €/mes. Es caja, no beneficio: hay que decidir sobre qué se mide la garantía ×3 antes de prometerla.
5. **Contraste AA:** verde y rojo de marca solo en rellenos; texto con variantes más oscuras.
6. **JSON núcleo (47 KB)** para todas las pantallas y catálogo completo (2,5 MB) solo en /productos.
7. **SheetJS 0.18.5** de npm (avisos de seguridad conocidos; solo lee ficheros del propio usuario). Cambiar antes de producción.
8. Un commit (fase 11) se hizo con un error de lint que no vi; corregido en la tanda 1 de pulido.

## 6. Siguientes 5 pasos (Fase 13)

1. **API local del motor:** `uvicorn` + FastAPI con `POST /analizar` (recibe los 3 ficheros y devuelve
   `report.json`), reutilizando `pipeline.run_analysis` + `web_export.build_report`. La web la consume con un
   nuevo `ReportSource`, sin tocar pantallas.
2. **Supabase:** auth por email (magic link), tabla `acciones_estado` (farmacia, semana, acción, estado, fecha)
   detrás de `ActionStore`, y `informes` (JSON por semana) para tener histórico **real** en /recuperado.
3. **Subida real:** /subir envía los ficheros ya validados en cliente a la API; la privacidad se vuelve a
   validar en el servidor (el motor ya lo hace) y nunca se guarda el fichero original.
4. **Definir la métrica de la garantía ×3** (caja liberada vs margen) y ajustarla en /recuperado.
5. **Piloto con la primera farmacia:** confirmar rutas de exportación, ajustar umbrales de `config.yaml` con
   sus datos y medir con `comparar` en la semana 3.
