# Stock Profit OS

Motor determinista que analiza las exportaciones del programa de gestión de una farmacia
(Farmatic, Nixfarma…) y genera un informe semanal con acciones concretas valoradas en euros.

> Estado: **Fase 1** (estructura, configuración, datos mock, ingesta con mapeo y validador de
> privacidad). Métricas (Fase 2) y acciones + informe (Fase 3) pendientes.

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

## Análisis

```bash
python -m engine.cli analizar --programa farmatic \
  --ventas data/sample/ventas.csv --stock data/sample/stock.csv --compras data/sample/compras.csv \
  --farmacia "Farmacia Demo" --salida output/
```

Admite CSV y XLSX. Códigos de salida: `0` OK, `1` error de fichero/configuración,
`2` fichero rechazado por privacidad.

## Configuración

- `config/config.yaml`: umbrales (días sin movimiento, cobertura objetivo, reposición, ABC…).
  **Todos son hipótesis ajustables**.
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
