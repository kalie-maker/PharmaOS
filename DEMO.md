# Guion de demo (3 minutos)

Para enseñar PharmaOS a un farmacéutico titular en la rebotica. Datos de una farmacia **ficticia**.

## Antes de la visita (1 minuto)

```bash
cd web && npm install && npm run build && npm start   # o npm run dev
```

Abre **http://localhost:3000/demo** (deja la demo limpia en cualquier ordenador). Ventana a pantalla
completa, zoom 100 %. Si vas a enseñar el bloqueo de privacidad, ten a mano
`web/public/ejemplos/ejemplo_bloqueado.csv`.

## 0:00 — El problema (portada, 20 s)

- Si empiezas en `/`: "Su programa de gestión tiene todos los datos, pero nadie le dice qué hacer el lunes".
- Pulsa **Ver demo**.

## 0:20 — La lista del lunes (`/lunes`, 60 s)

- **Señala el número grande: "Recuperable esta semana: 5.790 €"**. "Esto es lo que esta farmacia puede
  liberar o dejar de perder esta semana, en 40 acciones concretas".
- "Están ordenadas por euros. La primera vale 363 €: devolver una muñequera que lleva 225 días sin venderse".
- Pulsa **Hecho** en la primera. Señala **"Ya recuperado"** y la barra de progreso. Pulsa **Deshacer** en el
  aviso para enseñar que no hay miedo a equivocarse.
- Pulsa el filtro **Caduca pronto**: "Lo que caduca antes de venderse, con fecha límite".
- (Opcional) Teclado: `J` `K` para moverse, `H` hecho. "Se resuelve en 10 minutos".

## 1:20 — Por qué (ficha, 40 s) ← lo que nos diferencia de un chat

- Pulsa el título de una acción de **Bajar pedido** (o `Enter`).
- Señala el gráfico de 12 semanas y luego **"Por qué esta acción"**: "Ventas de 90 días, cobertura objetivo
  de su familia, stock actual, exceso y euros. Con sus números, paso a paso. Un chat le daría consejos
  generales; esto es un cálculo que puede comprobar".

## 2:00 — Lo que se lleva (exportar, 20 s)

- **Exportar e imprimir → Imprimir A4** de la lista de devolución: "Para el proveedor, agrupada por
  laboratorio, con total y firma". Vuelve con *Volver a la lista*.
- Menciona el **pedido corregido** en CSV: "Qué no pedir y qué reponer, con unidades".

## 2:20 — El resultado (`/recuperado`, 25 s)

- **Señala las tres cifras: Encontrado / Ejecutado / Recuperado** y el gráfico por semanas.
- "El servicio cuesta 149 €/mes y garantizamos recuperar al menos 3 veces eso". Señala el **múltiplo**.

## 2:45 — Privacidad (`/subir`, 15 s)

- Arrastra `ejemplo_bloqueado.csv`: "Si una exportación trae datos de pacientes, como un DNI, se bloquea
  antes de leerla. Solo trabajamos con producto, unidades e importes".
- Cierre: "¿Probamos 4 semanas gratis con sus datos?"

## Si algo falla

- Pantalla en blanco o datos raros: abre `/demo` otra vez.
- Sin conexión: la demo funciona en local, no necesita internet.
- Preguntas sobre cifras: el histórico de semanas anteriores es de demostración; los cálculos de la
  semana salen del motor con la farmacia ficticia.
