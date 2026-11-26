# Stock Profit OS — reglas del proyecto

Motor que analiza exportaciones del programa de gestión de una farmacia (Farmatic, Nixfarma…)
y genera un informe semanal con 5–10 acciones priorizadas por impacto en €.

## Reglas obligatorias
1. **Motor determinista.** Todas las cifras las calcula código Python testeado. Nada de IA en cálculos.
2. **Texto por plantillas (Jinja2).** Existe una interfaz para una futura capa de IA que solo redacte
   a partir del JSON de resultados. No implementarla ni llamar a APIs externas.
3. **Privacidad.** Nunca se procesan datos de pacientes. `engine/privacy.py` rechaza cualquier fichero
   con columnas (cabecera o contenido) que parezcan datos personales o sanitarios y explica por qué.
   La validación se hace sobre las columnas ORIGINALES, antes del mapeo. Nunca mostrar valores
   sospechosos en mensajes ni logs: solo nombre de columna, categoría y nº de coincidencias.
4. **Formatos desconocidos.** La ingesta usa mapeos YAML por programa (`config/mappings/*.yaml`).
   No asumir nombres de columna en el código: solo en los mapeos y en `config/sinonimos.yaml`.
5. **Umbrales en `config/config.yaml`**, marcados como hipótesis ajustables. Nada de números mágicos.
6. Código modular, tipado y con tests. Textos de usuario en español; identificadores en inglés.
   Los nombres de columna canónicos (`codigo_nacional`, `unidades`…) siguen el modelo de datos.

## Datos reales
- `entradas/`, `data/demo/`, `retos/` y `config/mappings/farmacia_*.yaml` están en .gitignore. Nunca subir datos de farmacias.

## No hacer
- Base de datos o autenticación. La web (`../web`, Next.js) solo consume `report.json` (contrato en
  `docs/report-schema.md`), del mock o de la API local (`engine/api.py`); no recalcula cifras.
- Llamadas a modelos de IA o APIs externas.
- Cifras de mercado inventadas en el informe: solo resultados calculados.
- Dependencias nuevas sin justificar (actuales: pandas, pyyaml, jinja2, openpyxl; api: fastapi, uvicorn, python-multipart; dev: pytest, jsonschema, httpx).

## Comandos
- Tests: `pytest`
- Datos mock: `python -m engine.cli generar-mock --salida data/sample`
- Inspección: `python -m engine.cli inspeccionar --fichero <export> --nombre <mapeo>`
- Piloto (todo en uno): `python -m engine.cli piloto --carpeta entradas/farmacia_1 --programa farmatic --nombre "Farmacia X"`
- Demo: `python -m engine.cli generar-mock --escenario semana3 --salida data/demo`
- Reto: `python -m engine.cli reto-chat --salida retos/reto_01` y `puntuar-reto --reto retos/reto_01 --respuesta <yaml>`
- API local para la web: `python -m engine.cli servir` (http://localhost:8000/docs)
- Contrato web: `python -m engine.cli exportar-json --mock --salida ../web/public/mock/report.json`
- Comparación: `python -m engine.cli comparar --antes output/semana0.json --despues output/semana3.json`
- Análisis: `python -m engine.cli analizar --programa farmatic --ventas data/sample/ventas.csv --stock data/sample/stock.csv --compras data/sample/compras.csv --farmacia "Farmacia Demo" --salida output/`

## Mapa del código
- `engine/schemas.py` — columnas canónicas, tipos y familias.
- `engine/config.py` — carga de `config.yaml` y mapeos.
- `engine/privacy.py` — validador de datos personales.
- `engine/sniff.py` — detección de codificación, separador, cabecera, decimales y fechas.
- `engine/ingest.py` — lectura CSV/XLSX (elección de hoja), mapeo y normalización.
- `engine/inspection.py` — `inspeccionar`: perfil de columnas, mapeo aproximado y borrador YAML.
- `engine/quality.py` — informe de calidad de datos previo al análisis.
- `engine/metrics.py`, `engine/actions.py` — cálculos y acciones con impacto en €.
- `engine/narrative.py` — textos por plantilla; protocolo `Narrator` para una futura capa de IA.
- `engine/report.py` + `engine/templates/` — JSON (fuente única), HTML A4 y Markdown.
- `engine/compare.py` — `comparar`: evolución entre dos JSON y acciones que parecen ejecutadas.
- `engine/anonymize.py` — anonimización de resultados (farmacia, laboratorios, productos, escala de €).
- `engine/pilot.py` — comando `piloto`: flujo completo por farmacia con paradas claras.
- `engine/mock/scenario.py` — escenario de demo semana 0 / semana 3.
- `engine/challenge.py` + `templates/challenge.html.j2` — reto "chat genérico vs PharmaOS" (`reto-chat`, `puntuar-reto`).
- `engine/templates/_styles.css.j2` — estilos compartidos por todos los HTML.
- `docs/piloto/` — guía de exportación, plantilla de acuerdo y checklist.
- `engine/web_export.py` + `docs/report-schema.{md,json}` — contrato `report.json` para la web.
- `engine/api.py` — API local (FastAPI): `/analizar`, `/informe`, `/salud`, `/programas`.
- `engine/pipeline.py` — orquestación ingesta -> calidad -> métricas -> acciones -> resultados.
- `engine/mock/generate.py` — farmacia ficticia reproducible (semilla fija).
