# Checklist del piloto (uso interno)

Una copia por farmacia. Identificador: `farmacia_N` · Programa: [Farmatic / Nixfarma / otro]

## Antes de empezar

- [ ] Acuerdo de piloto firmado (`acuerdo-piloto.md`) y criterio de éxito anotado.
- [ ] Guía de exportación enviada (`guia-exportacion.md`).
- [ ] Carpeta `entradas/farmacia_N/` creada (fuera de git, cifrada).

## Semana 0: del fichero al informe

1. **Recibir los ficheros**
   - [ ] Guardar en `entradas/farmacia_N/` con `ventas`, `stock` y `compras` en el nombre.
   - [ ] Borrar el `.zip` y los adjuntos del correo.

2. **Inspeccionar**
   ```bash
   python -m engine.cli inspeccionar --fichero entradas/farmacia_N/ventas.csv --nombre farmacia_N
   python -m engine.cli inspeccionar --fichero entradas/farmacia_N/stock.csv --nombre farmacia_N
   python -m engine.cli inspeccionar --fichero entradas/farmacia_N/compras.csv --nombre farmacia_N
   ```
   - [ ] Sin columnas con datos personales. Si las hay: **parar**, borrar el fichero y pedir
         una nueva exportación.
   - [ ] Formato detectado razonable (codificación, separador, decimales, fechas, hoja).

3. **Revisar el mapeo** `config/mappings/farmacia_N.yaml`
   - [ ] Cada línea `REVISAR` comprobada contra el fichero real.
   - [ ] Familias sin coincidencia asignadas a mano.
   - [ ] `borrador: false`.

4. **Calidad de datos**
   ```bash
   python -m engine.cli analizar --programa farmacia_N --ventas ... --stock ... --compras ... \
     --farmacia "Farmacia N" --solo-calidad
   ```
   - [ ] Nivel `buena` o `aceptable`. Si es `baja`: pedir a la farmacia que corrija la exportación
         (costes vacíos, stock negativo, fechas raras…) antes de seguir.

5. **Analizar** (todo en uno, equivalente a los pasos 2–4 + informe):
   ```bash
   python -m engine.cli piloto --carpeta entradas/farmacia_N --programa farmacia_N --nombre "Farmacia N"
   ```
   Informe en `output/farmacia_N/<fecha>/informe.html` (+ `.md`, `.json`, `calidad.md`).

6. **Revisar a mano** (15–30 min)
   - [ ] Las 3 cifras clave tienen sentido para el tamaño de la farmacia.
   - [ ] Mirar las 5 primeras referencias de cada acción: ¿son productos reales con ese problema?
   - [ ] Descartar falsos positivos evidentes (productos de temporada, encargos, novedades).
   - [ ] Laboratorios señalados: ¿hubo una compra de campaña justificada?
   - [ ] Si algo no cuadra, ajustar `config/config.yaml` (umbrales) y repetir. Anotar el cambio.

7. **Entregar**
   - [ ] Imprimir o enviar el PDF del HTML (imprimir en A4 desde el navegador).
   - [ ] Repasar las acciones con el titular en 15 minutos, en persona o por llamada.
   - [ ] Anotar qué acciones se compromete a ejecutar.

## Semana 3: revisión con comparar

1. - [ ] Pedir una nueva exportación (mismo formato) y guardarla en `entradas/farmacia_N_s3/`.
2. - [ ] Ejecutar el piloto con el **mismo `--id`**: compara solo con el informe anterior.
   ```bash
   python -m engine.cli piloto --carpeta entradas/farmacia_N_s3 --programa farmacia_N \
     --nombre "Farmacia N" --id farmacia_N
   ```
   O, a mano: `python -m engine.cli comparar --antes output/farmacia_N/<fecha0>/informe.json
   --despues output/farmacia_N/<fecha3>/informe.json --salida output/farmacia_N/`.
3. - [ ] Revisar `comparacion_<fecha0>.md`: € liberados, acciones ejecutadas, parciales y sin avance.
4. - [ ] Contrastar con el titular: ¿lo que parece ejecutado lo hizo él o son ventas normales?
5. - [ ] Comparar con el criterio de éxito pactado.
6. - [ ] Proponer la continuidad (149 €/mes) o cerrar el piloto.

## Al terminar el piloto

- [ ] Si **no continúa**: borrar `entradas/farmacia_N*`, `output/farmacia_N/` y
      `config/mappings/farmacia_N.yaml` en ≤ [15] días y confirmarlo por escrito.
- [ ] Si autorizó usarlo como ejemplo: generar la versión anónima
      (`analizar ... --anonimizar --escalar-cifras`) y revisar que no queda nada identificable.
- [ ] Anotar aprendizajes: rutas de menú reales, umbrales ajustados, falsos positivos.

## Demo para visitas (sin datos reales)

```bash
python -m engine.cli generar-mock --escenario semana3 --salida data/demo
python -m engine.cli piloto --carpeta data/demo/semana0 --programa farmatic --nombre "Farmacia Demo" --id demo
python -m engine.cli piloto --carpeta data/demo/semana3 --programa farmatic --nombre "Farmacia Demo" --id demo
```
