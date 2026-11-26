# Decisiones tomadas sin consultar (modo noche)

Formato: decisión · motivo · cómo revertir.

1. **Rama.** No existe `feat/web-mvp`; la rama actual es `claude/pensive-hawking-mx2rld` y trabajo en ella.
   Nunca se toca `main`.
2. **Sin push.** Tal como pediste, no hago push: todos los commits quedan en local en esta rama.
   ⚠️ Esta sesión corre en un contenedor en la nube: para conservar el trabajo hay que hacer push
   de la rama (o pedírmelo) antes de que el contenedor se recicle.
3. **Ubicación.** Web en `web/` (raíz del repo); contrato en `out/report.json` (generado, en .gitignore);
   mock de la web en `web/public/mock/report.json` (versionado para que `npm run dev` funcione sin Python).
4. **Acciones por producto.** El motor agrupaba acciones por tipo; la web necesita una acción por
   producto. `engine/web_export.py` toma las de más € de cada tipo (cupos en `config.yaml > web`) y un
   producto solo aparece una vez (prioridad caducidad → devolver → bajar pedido → reponer).
   Importes = columnas del motor sin recalcular (test lo comprueba).
5. **Tipos del contrato:** DEVOLVER = sin ventas en 180 días (valor a coste); BAJAR_PEDIDO = sobrestock a
   coste; REPONER = ventas en riesgo (€ de venta, no de coste); CADUCA_PRONTO = riesgo de caducidad a coste.
6. **Histórico de 6 semanas simulado** (`historico_simulado: true`): no hay semanas reales de piloto.
   Patrón determinista: más pendiente al principio y ejecución del 32 % al 68 %.
7. **Esquema** en `stock-profit-os/docs/` (junto al motor), JSON Schema draft 2020-12; `jsonschema`
   añadido como dependencia de desarrollo para validarlo en pytest.
8. **Stack web:** Next.js 15.5 (App Router) + React 19 + TS estricto (`noUncheckedIndexedAccess`) +
   Tailwind 3.4 (v3 por estabilidad del ecosistema). ESLint 9 (config de Next), Prettier, Vitest + jsdom,
   Playwright 1.63 (la misma versión que el Chromium preinstalado).
9. **Fuente Inter local** con `@fontsource-variable/inter` (no depende de Google Fonts en la visita).
10. **Sin librerías de UI ni de gráficos:** componentes propios; tabla virtualizada y MiniChart SVG propios.
11. **Datos en cliente:** `ReportProvider` carga `/mock/report.json` detrás de la interfaz `ReportSource`
    (mañana: API local del motor o Supabase).
12. **Mapeos y privacidad en TS generados** por `stock-profit-os/scripts/export_web_config.py` →
    `web/src/generated/engineConfig.ts` (`npm run gen:config`). Un test de pytest falla si el fichero no
    está al día y otro de Vitest repite los casos de privacidad del motor.
13. **SheetJS `xlsx@0.18.5` de npm** (la última publicada allí; las nuevas solo están en su CDN). Tiene
    avisos de seguridad conocidos para ficheros maliciosos; aquí solo lee ficheros que el propio usuario
    elige en su navegador. Se carga bajo demanda (import dinámico). Ver PENDIENTE.md.
14. **/subir simula el análisis:** valida y previsualiza en el navegador y, al pulsar Analizar, carga la
    farmacia de demostración (lo dice en pantalla y en un aviso).
15. **"Recuperado" = capital liberado + ventas salvadas** (suma de importes de acciones hechas). Con los
    rangos del mock (≈2.500 €/semana frente a 149 €/mes) el múltiplo sale muy alto (×70+). No es beneficio:
    es caja liberada. Conviene decidir si la garantía ×3 se mide sobre caja liberada o sobre margen.
    La semana en curso cuenta lo marcado como hecho como recuperado (se confirmará con la semana siguiente).
    El medidor tiene escala fija ×0–×10 para que la marca ×3 se lea siempre igual.
16. **Accesibilidad:** el verde y el rojo de marca no llegan a AA en texto pequeño (4,0:1 y 3,6:1). Se
    mantienen para rellenos y acentos, y el texto usa variantes oscurecidas (`brand-text` #0F7458,
    `urgent-text` #B42F22). Gris medio ajustado a #66666F. Los e2e pasan axe-core (WCAG 2.1 AA) sin
    infracciones graves en todas las pantallas.
17. **Rendimiento:** las pantallas cargan `report-core.json` (47 KB: acciones + sus productos) y solo
    /productos pide el catálogo completo (2,5 MB). `npm run gen:mock` genera ambos.
