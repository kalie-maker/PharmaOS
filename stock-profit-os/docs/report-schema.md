# Contrato de datos `report.json` (versión 1)

Fichero que el motor entrega a la web. Lo genera:

```bash
python -m engine.cli exportar-json --mock --salida out/report.json            # farmacia ficticia (8.000 refs)
python -m engine.cli exportar-json --programa farmatic --ventas v.csv --stock s.csv --compras c.csv \
  --farmacia "Farmacia X" --salida out/report.json                             # ficheros reales
```

JSON Schema (draft 2020-12): [`report-schema.json`](report-schema.json). Fechas en ISO `AAAA-MM-DD`,
importes en euros (2 decimales), sin formato: el formato español lo aplica la web.
**No contiene datos de pacientes** (lo comprueban los tests con el validador de privacidad).

## Raíz

| Campo | Tipo | Descripción |
|---|---|---|
| `version` | 1 | Versión del contrato |
| `generado_por` | string | Motor y versión |
| `farmacia` | objeto | `nombre`, `fecha_datos` (última venta), `semana` (ISO, `2026-W47`), `programa`, `ficticia` |
| `resumen` | objeto | Cifras de cabecera (ver abajo) |
| `acciones` | array | Acciones de la semana, ordenadas por `importe_eur` descendente |
| `productos` | objeto | Ficha de cada producto, indexada por `producto_id` (código nacional) |
| `historico_simulado` | bool | `true` si `historico_semanas` es simulado (mock) |
| `historico_semanas` | array | Semanas anteriores del piloto, de la más antigua a la más reciente |

## `resumen`

| Campo | Definición (calculada por el motor) |
|---|---|
| `capital_inmovilizado_eur` | Valor a coste del stock sin ventas en `umbral_sin_movimiento_dias` (180) días |
| `referencias_inmovilizadas` | Nº de referencias en esa situación |
| `stock_total_eur` | Valor a coste de todo el stock (stock negativo = 0) |
| `recuperable_semana_eur` | Suma de `importe_eur` de las acciones de la semana |
| `acciones_total`, `acciones_por_tipo`, `importe_por_tipo` | Recuento e importe por tipo |

## `acciones[]`

| Campo | Descripción |
|---|---|
| `id` | `<tipo en minúsculas>-<producto_id>`, estable entre ejecuciones con los mismos datos |
| `tipo` | `DEVOLVER` · `BAJAR_PEDIDO` · `REPONER` · `CADUCA_PRONTO` |
| `producto_id` | Clave en `productos` |
| `titulo`, `motivo_1_linea` | Texto por plantilla |
| `importe_eur` | Ver tabla de tipos |
| `cantidad_sugerida` | Unidades a devolver / no pedir / pedir / promocionar |
| `urgencia` | `alta` solo con plazo real (caduca en ≤ 30 días o stock 0 en venta frecuente); `media` / `baja` según importe |
| `plazo`, `plazo_texto`, `plazo_fecha?` | `hoy` · `esta_semana` · `proximo_pedido` · `antes_de` (+ fecha) |
| `calculo_explicado` | `pasos[{concepto, valor}]`, `formula`, `resultado`, con los números reales |

| Tipo | Selección | `importe_eur` (columna del motor) |
|---|---|---|
| `CADUCA_PRONTO` | Caduca en ≤ 90 días y no se venderá a tiempo (sin incluir stock sin movimiento) | `riesgo_caducidad_eur` |
| `DEVOLVER` | Sin ventas en 180 días | `valor_stock` |
| `BAJAR_PEDIDO` | Stock por encima de la cobertura objetivo de su familia | `sobrestock_eur` |
| `REPONER` | Venta frecuente y stock bajo el punto de pedido | `ventas_perdidas_eur` |

Por tipo se toman las acciones de más € (`web.acciones_por_tipo` en `config.yaml`), con importe
mínimo `web.importe_minimo_eur`. Un producto aparece como máximo en una acción (prioridad:
caducidad → devolver → bajar pedido → reponer).

## `productos{}`

`codigo`, `nombre`, `familia` (etiqueta legible), `laboratorio`, `stock`, `coste`, `pvp`, `valor_stock`,
`ventas_semanales_12` (12 enteros, la última = semana de `fecha_datos`), `dias_cobertura` (null si no
hay ventas), `ultima_venta`, `caducidad`, `abc`.

## `historico_semanas[]`

`semana`, `fecha_inicio`, `encontrado_eur`, `ejecutado_eur`, `recuperado_eur`, `acciones_encontradas`,
`acciones_ejecutadas`. En el mock es **simulado** (`historico_simulado: true`): más acciones
pendientes al principio del piloto y ejecución creciente (32 % → 68 %).
