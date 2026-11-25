# Stock Profit OS

Motor determinista que analiza las exportaciones del programa de gestión de una farmacia
(Farmatic, Nixfarma…) y genera un informe semanal con acciones concretas valoradas en euros.

> Estado: **Fase 5** — kit de piloto: comando `piloto` (todo en uno), escenario de demo
> semana 0 / semana 3, anonimización real y documentación en `docs/piloto/`.

## Reto: chat genérico vs PharmaOS

Prueba manual para las visitas: el mismo problema resuelto por un chat genérico y por el motor.

```bash
python -m engine.cli reto-chat --salida retos/reto_01
```

Genera los 3 ficheros de una farmacia ficticia (semilla `reto.semilla` de `config.yaml`), `prompt.md`
(texto exacto para pegar en el chat, con las definiciones de cálculo y un formato de respuesta fijo),
`respuestas_esperadas.json` (cifras del motor) y `plantilla_respuesta_chat.yaml`. Copia la plantilla
(p. ej. `respuesta_chatgpt.yaml`), rellénala a mano con lo que conteste el chat y puntúa:

```bash
python -m engine.cli puntuar-reto --reto retos/reto_01 --respuesta retos/reto_01/respuesta_chatgpt.yaml
```

Compara cifra a cifra (error en € y %; correcta ≤ 2 %, aproximada ≤ 10 %, configurable en
`reto:`) y genera `puntuacion_<respuesta>.html` ("Chat genérico vs PharmaOS", A4) y `.json`.
Un test recalcula las cifras siguiendo literalmente las definiciones del prompt, sin el motor,
para garantizar que el reto es justo.

## Kit de piloto

- `docs/piloto/guia-exportacion.md`: qué exportar desde Farmatic/Nixfarma y qué columnas NO incluir.
- `docs/piloto/acuerdo-piloto.md`: plantilla de acuerdo (revisar con un abogado).
- `docs/piloto/checklist-piloto.md`: pasos internos de la semana 0 a la semana 3.

Todo de una vez para cada farmacia (carpeta con ficheros que contengan `ventas`, `stock` y
`compras` en el nombre; si no, se identifican por su contenido):

```bash
python -m engine.cli piloto --carpeta entradas/farmacia_1 --programa farmatic --nombre "Farmacia X"
```

Inspecciona, para si hay datos personales, si el mapeo no existe (crea un borrador), está en
borrador o incompleto, o si la calidad es baja (`--ignorar-calidad` para forzar). Deja el informe en
`output/<id>/<fecha>/` y, si ya hay un informe anterior de la misma farmacia (`--id`), compara
automáticamente. Códigos de salida: `0` OK, `1` error, `2` privacidad, `3` parado (mapeo o calidad).

Demo para una visita (datos ficticios):

```bash
python -m engine.cli generar-mock --escenario semana3 --salida data/demo
python -m engine.cli piloto --carpeta data/demo/semana0 --programa farmatic --nombre "Farmacia Demo" --id demo
python -m engine.cli piloto --carpeta data/demo/semana3 --programa farmatic --nombre "Farmacia Demo" --id demo
```

Informe de ejemplo anónimo: `analizar ... --anonimizar [--escalar-cifras]` (farmacia → "Farmacia Demo",
laboratorios → "Laboratorio A, B…", productos → "familia · REF-0001", € × factor aleatorio 0,7–1,3).
`comparar --anonimizar` aplica los mismos alias y factor a los dos informes.

## Instalación

Requiere Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Datos de prueba

```bash
python -m engine.cli generar-mock --salida data/sample
```

Genera una farmacia ficticia (semilla fija 42, 3.000 referencias): `ventas.csv` (12 meses),
`stock.csv` y `compras.csv` (6 meses) con columnas "estilo Farmatic", separador `;`, decimales
con coma y codificación cp1252. Opciones: `--semilla`, `--referencias`, `--fecha-fin AAAA-MM-DD`.
Los CSV generados no se versionan (ventas ≈ 14 MB); se regeneran igual con la misma semilla.

## Flujo con una farmacia piloto

1. **Inspeccionar** cada exportación real (CSV o XLSX) y generar un borrador de mapeo:

   ```bash
   python -m engine.cli inspeccionar --fichero ventas.csv --nombre farmacia_x
   python -m engine.cli inspeccionar --fichero stock.xlsx --nombre farmacia_x
   python -m engine.cli inspeccionar --fichero compras.csv --nombre farmacia_x
   ```

   Muestra formato detectado (codificación, separador, cabecera, decimales, fechas, hoja), tipo de
   fichero probable, columnas con su propuesta de mapeo y confianza, columnas con posibles datos
   personales (sin mostrar valores) y las familias encontradas. Guarda
   `config/mappings/farmacia_x.yaml` con `borrador: true` y líneas `REVISAR`. Revísalo y pon
   `borrador: false`. Nunca sobrescribe un mapeo revisado salvo con `--forzar`.

2. **Comprobar la calidad** antes de analizar:

   ```bash
   python -m engine.cli analizar --programa farmacia_x --ventas ventas.csv --stock stock.xlsx \
     --compras compras.csv --farmacia "Farmacia X" --solo-calidad
   ```

3. **Analizar** y generar el informe (HTML A4, Markdown y JSON):

   ```bash
   python -m engine.cli analizar --programa farmatic \
     --ventas data/sample/ventas.csv --stock data/sample/stock.csv --compras data/sample/compras.csv \
     --farmacia "Farmacia Demo" --salida output/ --prefijo semana0
   ```

   - `--anonimizar`: sustituye el nombre de la farmacia por "Farmacia de ejemplo" (para enseñarlo).
   - `--hoja-ventas/--hoja-stock/--hoja-compras`: hoja de un Excel con varias hojas. Si hay dudas y
     la terminal es interactiva, pregunta; con `--no-interactivo`, falla indicando la opción.
   - Si la calidad de datos es baja, el informe lo indica al principio.

4. **Comparar** semanas para medir el avance (prueba de valor):

   ```bash
   python -m engine.cli comparar --antes output/semana0.json --despues output/semana3.json --salida output/
   ```

   Muestra la reducción en € de stock sin movimiento, sobrestock y caducidad, y qué acciones
   parecen ejecutadas (avance ≥ 70 %), parciales (≥ 25 %) o sin avance. Es una estimación: una
   reducción también puede deberse a ventas normales.

Códigos de salida: `0` OK, `1` error de fichero/configuración, `2` fichero rechazado por privacidad.

## Lectura robusta

- Codificación: UTF-8 (con o sin BOM), Windows-1252 o Latin-1, detectada automáticamente.
- Separador: `;`, `,`, tabulador o `|`. Líneas de título antes de la cabecera y filas de totales
  se toleran (los totales sin fecha/código se descartan con aviso).
- Números: coma o punto decimal detectados por columna (`1.234,56`, `1,234.56`, `12.5`, `5 €`).
- Fechas: formatos españoles (`dd/mm/aaaa`, `dd-mm-aa`, `dd.mm.aaaa`, con hora) e ISO.
- XLSX: elige la hoja cuyas columnas encajan con el mapeo; si hay empate, pregunta o pide `--hoja-*`.
  El formato `.xls` antiguo no se admite: guárdalo como `.xlsx` o CSV.

## Configuración

- `config/config.yaml`: umbrales (días sin movimiento, cobertura objetivo, reposición, ABC,
  límites de calidad de datos y de la comparación). **Todos son hipótesis ajustables**.
- `config/sinonimos.yaml`: sinónimos de encabezados y palabras clave de familias que usa
  `inspeccionar` para proponer mapeos. Añade los encabezados reales que encuentres.
- `config/mappings/<programa>.yaml`: alias de columnas del programa → modelo canónico, opciones
  de lectura y etiquetas de familia. Los nombres reales de Farmatic y Nixfarma **no están
  confirmados**: edita los alias con los encabezados de una exportación real. La comparación
  ignora mayúsculas, tildes y puntuación. Para otro programa, crea `config/mappings/<nombre>.yaml`.

## Privacidad

Antes de mapear, `engine/privacy.py` revisa las columnas originales y rechaza el fichero si
detecta datos personales o sanitarios: por cabecera (paciente, cliente, DNI/NIE, CIP, tarjeta
sanitaria, nº de receta, teléfono, email, dirección, nacimiento, diagnóstico…) o por contenido
(valores con forma de DNI/NIE, email o teléfono). El mensaje explica qué columna y por qué,
sin mostrar nunca los valores.

## Tests

```bash
pytest
```
