# Data Model: Vista modelada y consultas analíticas

Las tablas base no cambian: su modelo está en
[../003-bigquery-data-load/data-model.md](../003-bigquery-data-load/data-model.md).

## Vista `farma_analytics.v_compras_farma_completa`

- **Tipo**: vista lógica en GoogleSQL (`type = VIEW`, `view.useLegacySql = false`), sin expiración.
- **Grano**: una línea de `COMPRAS` con correspondencia en `CLUE_CAT` (por `CLUE`) y en
  `CUADRO_BASICO` (por `CLAVE`). No tiene llave única, igual que `COMPRAS`.
- **Filas esperadas**: filas de `COMPRAS` menos las filas huérfanas, hoy 300 000 − 750 − 750 =
  298 500.
- **Descripción**: "Compras públicas de medicamentos con los datos de su unidad médica (CLUE_CAT)
  y de su insumo (CUADRO_BASICO). Grano: una fila por línea de COMPRAS cuya CLUE y cuya CLAVE existen
  en los catálogos, así que las líneas huérfanas quedan fuera. Es la fuente del dashboard y de las
  consultas analíticas. Datos sintéticos." En la DDL se escribe con `CONCAT` de varias cadenas para
  que ninguna línea pase de 100 caracteres (la referencia DDL admite funciones escalares en el valor
  de `OPTIONS`).

| # | Columna | Tipo | Origen | Descripción (borrador) |
|---|---|---|---|---|
| 1 | `CLUE` | `STRING` | `compras.CLUE` | Clave CLUES de la unidad médica que compra. |
| 2 | `CLAVE` | `STRING` | `compras.CLAVE` | Clave del insumo comprado en el Compendio Nacional de Insumos. |
| 3 | `COD_PROVEEDOR` | `STRING` | `compras.COD_PROVEEDOR` | Código del proveedor que entrega el insumo. |
| 4 | `MARCA` | `STRING` | `compras.MARCA` | Marca comercial del producto entregado. |
| 5 | `FABRICANTE_COMPRA` | `STRING` | `compras.FABRICANTE` | Fabricante del producto entregado en la línea (FABRICANTE de COMPRAS). |
| 6 | `PIEZAS` | `INT64` | `compras.PIEZAS` | Piezas (envases) entregadas. Medida aditiva. |
| 7 | `IMPORTE` | `NUMERIC` | `compras.IMPORTE` | Importe de la línea en pesos mexicanos. Medida aditiva. |
| 8 | `FECHA` | `DATE` | `compras.FECHA` | Fecha de la compra. |
| 9 | `ENTIDAD` | `STRING` | `clue_cat.ENTIDAD` | Entidad federativa de la unidad médica, con su nombre oficial del INEGI. |
| 10 | `INSTITUCION` | `STRING` | `clue_cat.INSTITUCION` | Institución pública de salud de la unidad médica. |
| 11 | `DELEGACION` | `STRING` | `clue_cat.DELEGACION` | Delegación u órgano administrativo de la institución en la entidad. |
| 12 | `GRUPO_INSTITUCIONAL` | `STRING` | `clue_cat.GRUPO_INSTITUCIONAL` | Agrupación de instituciones por tipo de población atendida. |
| 13 | `NIVEL_ATENCION` | `STRING` | `clue_cat.NIVEL_ATENCION` | Nivel de atención de la unidad médica. |
| 14 | `MUNICIPIO` | `STRING` | `clue_cat.MUNICIPIO` | Municipio o alcaldía de la unidad médica. |
| 15 | `DESCRIPCION` | `STRING` | `cuadro_basico.DESCRIPCION` | Descripción completa del insumo. |
| 16 | `MOLECULA` | `STRING` | `cuadro_basico.MOLECULA` | Denominación genérica del principio activo. |
| 17 | `GRUPO_TERAPEUTICO` | `STRING` | `cuadro_basico.GRUPO_TERAPEUTICO` | Grupo terapéutico del Cuadro Básico. |
| 18 | `PRESENTACION` | `STRING` | `cuadro_basico.PRESENTACION` | Forma farmacéutica, concentración y envase. |
| 19 | `FABRICANTE_CATALOGO` | `STRING` | `cuadro_basico.FABRICANTE` | Fabricante de referencia de la molécula (FABRICANTE de CUADRO_BASICO). |
| 20 | `ANIO` | `INT64` | `EXTRACT(YEAR FROM compras.FECHA)` | Año de FECHA, para comparar año contra año. |
| 21 | `MES` | `DATE` | `DATE_TRUNC(compras.FECHA, MONTH)` | Primer día del mes de FECHA, para series mensuales. |
| 22 | `ENTIDAD_ISO` | `STRING` | `CASE clue_cat.ENTIDAD ...` | Código ISO 3166-2 de la entidad (MX-XXX), para mapas. |

Reglas de validación (FR-002 a FR-008, [contracts/vista.md](contracts/vista.md)):

- 22 columnas, en este orden, con nombres únicos sin distinguir mayúsculas;
- ninguna columna de precio, cociente ni agregado: el precio promedio se calcula al consumir;
- `PIEZAS` e `IMPORTE` sin transformar;
- `ANIO`, `MES` y `ENTIDAD_ISO` nunca nulos (chequeo 07).

### Mapeo `ENTIDAD` → `ENTIDAD_ISO`

Una rama por cada uno de los 32 nombres de `generator/reference/entidades.csv`:

| ENTIDAD | ISO | ENTIDAD | ISO |
|---|---|---|---|
| Aguascalientes | MX-AGU | Morelos | MX-MOR |
| Baja California | MX-BCN | Nayarit | MX-NAY |
| Baja California Sur | MX-BCS | Nuevo León | MX-NLE |
| Campeche | MX-CAM | Oaxaca | MX-OAX |
| Coahuila de Zaragoza | MX-COA | Puebla | MX-PUE |
| Colima | MX-COL | Querétaro | MX-QUE |
| Chiapas | MX-CHP | Quintana Roo | MX-ROO |
| Chihuahua | MX-CHH | San Luis Potosí | MX-SLP |
| Ciudad de México | MX-CMX | Sinaloa | MX-SIN |
| Durango | MX-DUR | Sonora | MX-SON |
| Guanajuato | MX-GUA | Tabasco | MX-TAB |
| Guerrero | MX-GRO | Tamaulipas | MX-TAM |
| Hidalgo | MX-HID | Tlaxcala | MX-TLA |
| Jalisco | MX-JAL | Veracruz de Ignacio de la Llave | MX-VER |
| México | MX-MEX | Yucatán | MX-YUC |
| Michoacán de Ocampo | MX-MIC | Zacatecas | MX-ZAC |

## Cobertura: qué columnas de la vista usa cada pregunta y cada visual

Ninguna pregunta ni ningún visual necesita una columna que la vista no tenga. Las medidas no
aditivas (precio promedio, participación) se calculan al consumir y no son columnas.

| Consumidor | Columnas de la vista que usa | Cálculo al consumir |
|---|---|---|
| P1, 5 moléculas con más importe | `MOLECULA`, `IMPORTE`, `PIEZAS` | `SUM`, `AVG(IMPORTE)`, participación |
| P2, institución y entidad con mayor volumen | `INSTITUCION`, `ENTIDAD`, `IMPORTE`, `PIEZAS` | `SUM`, líder con `RANK`, participación |
| P3, precio por molécula y fabricante | `MOLECULA`, `FABRICANTE_COMPRA` (o `FABRICANTE_CATALOGO`), `IMPORTE`, `PIEZAS` | `SAFE_DIVIDE(SUM(IMPORTE), SUM(PIEZAS))` |
| Dashboard, controles | `FECHA`, `ENTIDAD`, `INSTITUCION`, `GRUPO_INSTITUCIONAL`, `GRUPO_TERAPEUTICO`, `MOLECULA` | Ninguno |
| Dashboard, KPIs | `IMPORTE`, `PIEZAS`, `FECHA` (periodo de comparación) | Monto, piezas y precio promedio como campo calculado |
| Dashboard, gasto por entidad | `ENTIDAD`, `ENTIDAD_ISO` (mapa), `IMPORTE` | `SUM(IMPORTE)` |
| Dashboard, participación por institución | `INSTITUCION`, `IMPORTE` | Porcentaje del total |
| Dashboard, top 10 | `MOLECULA`, `FABRICANTE_COMPRA`, `PIEZAS`, `IMPORTE` | Precio promedio como campo calculado |
| Dashboard, series y comparación anual | `MES`, `ANIO`, `FECHA` | Ninguno |

La columna "Fabricante/Proveedor" del top 10 usa `FABRICANTE_COMPRA`. `COD_PROVEEDOR` está en la vista,
pero es un código sin nombre, así que no sirve como etiqueta legible.

## Glosario de métricas (principio VII)

| Métrica | Definición | Dónde se usa |
|---|---|---|
| Monto Total | `SUM(IMPORTE)` | P1, P2 (medida principal), P3, dashboard |
| Piezas | `SUM(PIEZAS)` | P1, P2 (medida alternativa), P3, dashboard |
| Precio Promedio | `SAFE_DIVIDE(SUM(IMPORTE), SUM(PIEZAS))` | P1, P3, dashboard (campo calculado) |
| Importe promedio por línea | `AVG(IMPORTE)` | P1 |
| Participación | `100 × valor / total de la vista` | P1, P2 |

## Definiciones de las ambigüedades (FR-015)

| Ambigüedad | Definición | Razón | Alternativa mostrada |
|---|---|---|---|
| Volumen de compra | `SUM(IMPORTE)` | Es el monto de la pregunta 1 y el gasto del dashboard | `SUM(PIEZAS)` en la misma consulta P2 |
| Fabricante en P3 | `FABRICANTE_COMPRA` | Es quien vendió a ese precio, y su mezcla explica las diferencias de precio entre instituciones | `FABRICANTE_CATALOGO` en P3 alternativa (una fila por molécula) |
| Institución y entidad | Las tres lecturas: la combinación, la institución sola y la entidad sola | La pregunta admite las tres y cuestan una sola lectura de la vista | Todas en P2 |
| Empates | P1: desempate por `MOLECULA` ascendente. P2: `RANK`, se muestran todos los empatados. P3: orden por molécula, precio y fabricante | P1 tiene que devolver 5 filas exactas; P2 no debe ocultar un empate | Ninguna |

## Respuestas de la sección 4

| Id | Pregunta | Grano del resultado | Columnas de salida |
|---|---|---|---|
| `P1` | 5 moléculas con más `IMPORTE` | Una molécula | `MOLECULA`, `PIEZAS_TOTALES`, `IMPORTE_TOTAL`, `PRECIO_PROMEDIO`, `IMPORTE_PROMEDIO_LINEA`, `PARTICIPACION_PCT` |
| `P2` | Institución y entidad con mayor volumen | Un líder por nivel y medida (6 filas o más si hay empates) | `MEDIDA`, `NIVEL`, `INSTITUCION`, `ENTIDAD`, `VALOR`, `PARTICIPACION_PCT` |
| `P3` | Precio promedio por molécula y fabricante | Molécula y `FABRICANTE_COMPRA` (497 filas hoy) | `MOLECULA`, `FABRICANTE_COMPRA`, `PIEZAS_TOTALES`, `IMPORTE_TOTAL`, `PRECIO_PROMEDIO` |
| `P3_CATALOGO` | Lo mismo con el fabricante de catálogo | Molécula y `FABRICANTE_CATALOGO` (139 filas hoy) | `MOLECULA`, `FABRICANTE_CATALOGO`, `PIEZAS_TOTALES`, `IMPORTE_TOTAL`, `PRECIO_PROMEDIO` |

El orden de las columnas de salida sigue la regla ST06 de SQLFluff (`structure.column_order`):
primero las referencias simples y después las expresiones con `ROUND`.

`NIVEL` toma los valores `INSTITUCION Y ENTIDAD`, `INSTITUCION` y `ENTIDAD`. `MEDIDA` toma `IMPORTE` y
`PIEZAS`. En el nivel `INSTITUCION`, la columna `ENTIDAD` es `NULL` porque no aplica, y al revés en el
nivel `ENTIDAD`.

## Estructuras del programa `warehouse`

### `ViewSpec` (análisis de la sección 3)

| Campo | Tipo | Origen |
|---|---|---|
| `dataset` | `str` | Referencia de la vista |
| `name` | `str` | `v_compras_farma_completa` |
| `description` | `str` | `OPTIONS(description = ...)` de la vista |
| `columns` | `tuple[ColumnSpec, ...]` | Lista de columnas: nombre y descripción de la lista; tipo según R4; `mode = "NULLABLE"` |
| `ref` | propiedad | `farma_analytics.v_compras_farma_completa` |

`Ddl` gana el campo `view: ViewSpec | None` y las sentencias ganan los tipos `create_view` y `query`.
`DERIVED_TYPES = {"ANIO": "INT64", "MES": "DATE", "ENTIDAD_ISO": "STRING"}`.

### `QueryResult` (una respuesta de la sección 4)

| Campo | Tipo | Contenido |
|---|---|---|
| `id` | `str` | `P1`, `P2`, `P3` o `P3_CATALOGO` |
| `rows` | `list[dict]` | Filas JSON de `bq` |
| `estimated_bytes` | `int \| None` | Del dry run |

### Diferencia de cifras cruzadas

Usa el mismo `CheckResult` de la feature 003, con `CHEQUEO = 'cifras_cruzadas'`, `OBJETO` igual a la
regla (`C1` a `C5`) y la consulta afectada en `DETALLE`, para que la salida tenga el formato de los
chequeos.

### Caso negativo de la vista (`sql/checks/negativos/07_reconciliacion_vista.json`)

Mismo formato que los seis existentes, con una clave más en `tablas`: `v_compras_farma_completa`,
con filas que tienen las 22 columnas como texto (o `null`). `esperado` es
`{"CHEQUEO": "reconciliacion_vista", "OBJETO": "v_compras_farma_completa"}`.

## Estados

```text
sin dataset ──bq-schema──▶ tablas vacías ──bq-load──▶ tablas cargadas, sin vista
                                                        │  (6 chequeos; aviso "ejecuta make bq-vista")
                                                        ▼
                                              bq-vista: vista desplegada (7 chequeos)
                                                        │
                    bq-load (recarga): 7 chequeos ◀─────┤──▶ bq-vista (cambio): 7 chequeos
                                                        ▼
                                              bq-consultas: P1, P2, P3, P3_CATALOGO y C1 a C5
```
