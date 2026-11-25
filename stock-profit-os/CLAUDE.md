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

## No hacer
- Web, API, base de datos, autenticación o app.
- Llamadas a modelos de IA o APIs externas.
- Cifras de mercado inventadas en el informe: solo resultados calculados.
- Dependencias nuevas sin justificar (actuales: pandas, pyyaml, jinja2, openpyxl, pytest).

## Comandos
- Tests: `pytest`
- Datos mock: `python -m engine.cli generar-mock --salida data/sample`
- Inspección: `python -m engine.cli inspeccionar --fichero <export> --nombre <mapeo>`
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
- `engine/pipeline.py` — orquestación ingesta -> calidad -> métricas -> acciones -> resultados.
- `engine/mock/generate.py` — farmacia ficticia reproducible (semilla fija).
