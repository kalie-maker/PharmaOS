# Guía de exportación de datos — Piloto Stock Profit OS

Esta guía explica qué ficheros necesitamos y cómo sacarlos del programa de gestión.
Tardarás unos 15 minutos. Si algo no coincide con lo que ves en pantalla, llámanos y lo
hacemos juntos.

> Las rutas de menú marcadas como **[POR CONFIRMAR]** son aproximadas: todavía no las
> hemos verificado en tu versión del programa. Anota la ruta real para la próxima vez.

## Qué necesitamos

| Fichero | Periodo | Contenido |
|---|---|---|
| `ventas` | Últimos 12 meses | Una línea por venta o por día y producto: fecha, código nacional, descripción, laboratorio, familia, unidades, importe sin IVA y precio de coste |
| `stock` | Foto de hoy | Una línea por producto: código nacional, descripción, laboratorio, familia, stock actual, precio de coste, PVP y fecha de caducidad (si la tienes) |
| `compras` | Últimos 6 meses | Una línea por albarán y producto: fecha, código nacional, laboratorio, unidades recibidas e importe a coste |

Formatos válidos: **CSV**, **TXT** o **Excel (.xlsx)**. No hace falta ordenar ni limpiar nada.
Si el Excel tiene varias hojas, no pasa nada: indícanos cuál es la buena.

Nombra los ficheros con la palabra `ventas`, `stock` y `compras` (por ejemplo `ventas_2026.csv`).

## ⚠️ Columnas que NO deben incluirse

Stock Profit OS **no procesa datos de pacientes**. Si un fichero trae alguna de estas
columnas, el sistema lo rechaza automáticamente y tendrás que exportarlo de nuevo:

- Nombre, apellidos o cualquier dato del **paciente** o **cliente**.
- **DNI / NIE / NIF** o pasaporte.
- **CIP**, código de **tarjeta sanitaria** o número de la Seguridad Social.
- **Número de receta**, código de prescripción o datos del médico prescriptor.
- **Teléfono, email, dirección**, código postal o localidad del cliente.
- Fecha de nacimiento, edad, sexo, diagnóstico, alergias o tratamientos.

Si el informe de ventas de tu programa sale **por ticket o por receta**, elige la opción
**agrupada por artículo y día** o quita esas columnas antes de exportar.

## Farmatic

### Ventas
1. Menú **[POR CONFIRMAR: Listados > Ventas > Ventas por artículo]**.
2. Periodo: desde hace 12 meses hasta ayer.
3. Agrupar por **artículo y día** (no por ticket ni por cliente). **[POR CONFIRMAR]**
4. Columnas: fecha, código, descripción, laboratorio, familia, unidades, importe sin IVA, precio de coste.
5. Exportar a **CSV o Excel**. **[POR CONFIRMAR: botón Exportar / Imprimir a fichero]**

### Stock
1. Menú **[POR CONFIRMAR: Almacén > Inventario valorado]**.
2. Todos los artículos con stock distinto de cero (incluye negativos si los hay).
3. Columnas: código, descripción, laboratorio, familia, stock actual, precio de coste, PVP, caducidad.
4. Exportar a **CSV o Excel**.

### Compras
1. Menú **[POR CONFIRMAR: Compras > Albaranes recibidos > Listado por artículo]**.
2. Periodo: últimos 6 meses.
3. Columnas: fecha del albarán, código, laboratorio, unidades recibidas, importe a coste.
4. Exportar a **CSV o Excel**.

## Nixfarma

### Ventas
1. Menú **[POR CONFIRMAR: Estadísticas > Ventas > Por artículo]**.
2. Periodo: últimos 12 meses. Agrupado por **artículo y día**. **[POR CONFIRMAR]**
3. Columnas: fecha, código nacional, descripción, laboratorio, familia, cantidad, importe neto, precio de coste.
4. Exportar a **CSV o Excel**. **[POR CONFIRMAR]**

### Stock
1. Menú **[POR CONFIRMAR: Almacén > Existencias > Valoración de stock]**.
2. Columnas: código nacional, descripción, laboratorio, familia, existencias, precio de coste, PVP, caducidad.
3. Exportar a **CSV o Excel**.

### Compras
1. Menú **[POR CONFIRMAR: Compras > Entradas / Albaranes > Por artículo]**.
2. Periodo: últimos 6 meses.
3. Columnas: fecha de entrada, código nacional, laboratorio, cantidad, importe a coste.
4. Exportar a **CSV o Excel**.

## Cómo enviarnos los ficheros

- Por el canal acordado en el acuerdo de piloto (nunca por WhatsApp ni redes sociales).
- Comprime los tres ficheros en un único `.zip`, si es posible con contraseña, y envíanos
  la contraseña por un canal distinto.
- Cada semana del piloto, repite solo el fichero de `stock` y las `ventas` y `compras` de los
  últimos días (o los tres completos si te resulta más fácil).

## Checklist antes de enviar

- [ ] Tres ficheros: ventas (12 meses), stock (hoy), compras (6 meses).
- [ ] Ninguna columna de pacientes, recetas, tarjetas sanitarias ni datos de contacto.
- [ ] Nombres de fichero con `ventas`, `stock` y `compras`.
- [ ] Anotadas las rutas de menú reales para sustituir los **[POR CONFIRMAR]**.
