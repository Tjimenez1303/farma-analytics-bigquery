# Quickstart: validación del dashboard (Fase 3)

Guía para comprobar la feature de principio a fin. Lo que toca GCP y Data Studio con la cuenta del
dueño lo ejecuta el dueño o lo hace Claude en el navegador del dueño con su confirmación (R14). Lo
local lo puede ejecutar Claude.

## Requisitos previos

- La vista `farma_analytics.v_compras_farma_completa` desplegada con 298 500 filas (feature 004) y
  `make bq-checks` en 0 filas.
- `make doctor` con 22 OK.
- Sesión de Google del dueño iniciada en Chrome con Claude in Chrome conectado.
- `docs/dashboard.md` escrito según
  [contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md).

## V0. Verificaciones locales (Claude)

```bash
make test
```

```bash
make lint
```

```bash
make lint-sql
```

```bash
make lint-prosa
```

Esperado: todo en verde, incluidas las pruebas nuevas de `sql/dashboard/`, de
`python -m warehouse dashboard` y de `docs/dashboard.md`. Antes de `make lint`, los archivos nuevos
están en el índice de git.

## V1. Cifras del estado inicial (dueño)

```bash
make bq-dashboard
```

Esperado: 7 consultas (1 de totales, 2 de KPIs y 4 más) con dry run, y D1 a D4 sin diferencias.
Las cifras coinciden con
[data-model.md](data-model.md#cifras-esperadas-del-estado-inicial): periodo de referencia del
2024-01-01 al 2024-12-31, importe de 2025 de 14 941.7 M (+9.1 %), 28.55 M de piezas (+6.9 %),
precio de 523.42 (+2.1 %), México en primer lugar con 1 731 M e IMSS con el 38.71 %.

## V2. Cifras de un estado filtrado (dueño)

```bash
make bq-dashboard ENTIDAD=Jalisco
```

Esperado: D1 a D4 sin diferencias, una sola entidad en el gasto por entidad y un top 10 distinto del
inicial.

## V3. Construcción del informe (Claude en el Chrome del dueño)

Cada paso termina con una captura que se compara con `docs/dashboard.md`. Los pasos marcados con
"confirmación" esperan el visto bueno del dueño.

1. Crear la fuente reutilizable desde la página de inicio de Data Studio con el conector de
   BigQuery y la vista (confirmación: autorizar el conector y aceptar avisos, si aparecen).
2. Revisar que las credenciales son *Owner's credentials* (confirmación si hay que cambiarlas),
   fijar la frescura en 12 horas y activar "Field Editing in Reports", que el "Percent of total" de
   la tabla de instituciones necesita (R7).
3. Configurar los 22 campos y crear el campo calculado Precio Promedio. Probar `NULLIF` y la moneda
   MXN (R2).
4. Crear el informe con la fuente, fijar el lienzo de 1600 × 900, la rejilla de 10 px y el tema
   (R10). Comprobar si Roboto está disponible.
5. Añadir el título, el subtítulo, los seis controles y el botón (R3, R4).
6. Añadir las tres tarjetas y comprobar las flechas, la comparación y los sufijos compactos (R5,
   R11).
7. Añadir las barras de entidades e instituciones, el mapa y la tabla (R6 a R9). Hacer la prueba de
   `MX-CMX` (R9).
8. Escribir el recuadro de hallazgos con las cifras de V1 (R17).
9. Registrar en `docs/dashboard.md` los comportamientos comprobados en el producto.

## V4. Coincidencia con el SQL (Claude, con la salida de V1 y V2)

- Estado inicial: las tres tarjetas, su comparación, el importe de cada entidad, el porcentaje de
  cada institución y las 10 filas del top 10 coinciden con V1 a la precisión que muestra el tablero.
- Estado filtrado: con Jalisco elegido en el control Entidad, las tarjetas, el top 10 y el gasto por
  entidad coinciden con V2.
- Cada comparación queda en el registro de verificación de `docs/dashboard.md`.

## V5. Controles y cascada (Claude)

- Cada control cambia las tarjetas, las barras, el mapa y la tabla.
- Con Oncología en Grupo terapéutico, la lista Molécula solo ofrece moléculas de Oncología.
- Sin escribir nada, la lista Molécula ofrece las 139 moléculas, sin "All others".
- Un clic en la barra del IMSS filtra los demás componentes y otro clic lo quita.
- El botón Restablecer filtros devuelve el estado inicial, incluido el rango 2025 (o queda
  documentado lo contrario, R4).
- Con el rango 2024-01-01 a 2025-12-31, las tarjetas muestran el equivalente de 28 633.9 millones
  de pesos y 55.25 millones de piezas con su sufijo compacto, y la comparación muestra +109.1 %,
  que no es comparable porque 2023-2024 solo tiene datos de 2024. El subtítulo lo avisa.
- Con el rango 2023-01-01 a 2023-12-31, las tarjetas muestran "-" y ninguna cifra inventada.
- Con la ventana a 1366 px de ancho, las etiquetas de las 32 entidades se leen.

## V6. Diseño y accesibilidad (Claude)

- Recorrer la lista del principio VI en `docs/dashboard.md`: 16:9 sin scroll, pirámide, rejilla,
  sin 3D, sombras ni degradados, barras desde cero, sin doble eje, orden por la métrica, un color
  base y un acento, una familia y tres tamaños, etiquetas directas, sin texto rotado.
- Una captura en escala de grises permite leer los valores, el orden y el sentido de cada cambio.
- Los contrastes de `docs/dashboard.md` pasan su prueba local (V0).

## V7. Compartir y comprobación sin sesión

1. Compartir el informe con "Cualquier persona con el enlace puede ver" (confirmación del dueño).
2. Claude abre el enlace en el navegador integrado de la app, que no tiene sesión de Google, y
   comprueba que la página carga con datos en menos de 10 segundos.
3. El dueño abre el enlace en una ventana de incógnito de Chrome y confirma lo mismo.
4. El enlace queda en el README y en `docs/dashboard.md`.
5. Una persona que no conoce el proyecto responde con el enlace, en menos de 2 minutos, cuál es la
   entidad y la institución con más importe y cuál es el par molécula-fabricante líder (SC-005).

## V8. Documentación

- El README tiene la sección del dashboard y `make lint-prosa` pasa.
- `docs/trazabilidad.md` tiene la sección de la Fase 3 con una fila por control, KPI y
  visualización de los requisitos.
