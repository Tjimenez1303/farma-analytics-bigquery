# Data Model: Carga de datos en BigQuery

Define los objetos que crea la sección 1 y 2 de `sql/farma_analytics.sql` y las estructuras que usa
el programa de carga. Los textos de descripción son la propuesta inicial; la redacción final se
revisó en la implementación (español, sin `;` ni comillas simples dentro del texto, y cortos para
que cada línea del `.sql` quede en 100 caracteres o menos, como pide el principio II).

## Dataset `farma_analytics`

| Atributo | Valor |
|---|---|
| Location | `US` (igual a `--location` de `.bigqueryrc`; prueba local y validación de BigQuery) |
| Descripción | "Compras públicas de medicamentos en México con datos sintéticos." |
| Labels | `project = farma-analytics`, `env = dev`, `owner = bi` |
| Expiración por defecto | ninguna (prohibida en `farma_analytics`) |
| Sensible a mayúsculas | sí (valor por defecto, `is_case_insensitive` no se declara) |

## Tabla `COMPRAS` (hechos)

- **Grano**: una línea de compra (una entrega de una clave a una unidad médica, por un proveedor,
  con una marca y un fabricante, en una fecha).
- **Llave**: no tiene llave única. Dos líneas pueden coincidir en todos los campos.
- **Relaciones**: `CLUE` → `CLUE_CAT.CLUE` y `CLAVE` → `CUADRO_BASICO.CLAVE`, sin claves foráneas
  declaradas porque hay huérfanos deliberados (750 de cada tipo según el manifiesto).
- **Descripción de tabla**: "Líneas de compra de medicamentos. Grano: una línea de compra. Sin llave
  única."

| # | Columna | Tipo | Modo | Descripción |
|---|---|---|---|---|
| 1 | `CLUE` | `STRING` | `REQUIRED` | Clave CLUES de la unidad médica que compra. |
| 2 | `CLAVE` | `STRING` | `REQUIRED` | Clave del insumo comprado en el Compendio Nacional de Insumos. |
| 3 | `COD_PROVEEDOR` | `STRING` | `REQUIRED` | Código del proveedor que entrega el insumo. |
| 4 | `MARCA` | `STRING` | `NULLABLE` | Marca comercial del producto entregado. |
| 5 | `FABRICANTE` | `STRING` | `NULLABLE` | Fabricante del producto entregado, que puede diferir del de CUADRO_BASICO. |
| 6 | `PIEZAS` | `INT64` | `REQUIRED` | Número de piezas (envases) entregadas. Medida aditiva. |
| 7 | `IMPORTE` | `NUMERIC` | `REQUIRED` | Importe de la línea en pesos mexicanos. Medida aditiva. |
| 8 | `FECHA` | `DATE` | `REQUIRED` | Fecha de la compra. |

## Tabla `CLUE_CAT` (dimensión de unidades médicas)

- **Grano**: una unidad médica.
- **Llave**: `CLUE`, única (chequeo `02_unicidad_claves`). No se declara `PRIMARY KEY`.
- **Descripción de tabla**: "Catálogo de unidades médicas. Grano: una unidad médica. Llave: CLUE."

| # | Columna | Tipo | Modo | Descripción |
|---|---|---|---|---|
| 1 | `CLUE` | `STRING` | `REQUIRED` | Clave CLUES de la unidad médica. Llave del catálogo. |
| 2 | `ENTIDAD` | `STRING` | `NULLABLE` | Entidad federativa con su nombre oficial del INEGI. |
| 3 | `INSTITUCION` | `STRING` | `NULLABLE` | Institución pública de salud a la que pertenece la unidad. |
| 4 | `DELEGACION` | `STRING` | `NULLABLE` | Delegación u órgano administrativo de la institución en la entidad. |
| 5 | `GRUPO_INSTITUCIONAL` | `STRING` | `NULLABLE` | Agrupación de instituciones por tipo de población atendida. |
| 6 | `NIVEL_ATENCION` | `STRING` | `NULLABLE` | Nivel de atención de la unidad: primero, segundo o tercero. |
| 7 | `MUNICIPIO` | `STRING` | `NULLABLE` | Municipio o alcaldía donde está la unidad. |

## Tabla `CUADRO_BASICO` (dimensión de insumos)

- **Grano**: una presentación de una molécula.
- **Llave**: `CLAVE`, única (chequeo `02_unicidad_claves`). No se declara `PRIMARY KEY`.
- **Descripción de tabla**: "Catálogo de insumos. Grano: una presentación de una molécula. Llave:
  CLAVE."

| # | Columna | Tipo | Modo | Descripción |
|---|---|---|---|---|
| 1 | `CLAVE` | `STRING` | `REQUIRED` | Clave del insumo en el Compendio Nacional de Insumos. Llave del catálogo. |
| 2 | `DESCRIPCION` | `STRING` | `NULLABLE` | Descripción completa del insumo con el estilo del Cuadro Básico. |
| 3 | `MOLECULA` | `STRING` | `NULLABLE` | Denominación genérica del principio activo. |
| 4 | `GRUPO_TERAPEUTICO` | `STRING` | `NULLABLE` | Grupo terapéutico del Cuadro Básico al que pertenece la molécula. |
| 5 | `PRESENTACION` | `STRING` | `NULLABLE` | Forma farmacéutica, concentración y envase. |
| 6 | `FABRICANTE` | `STRING` | `NULLABLE` | Fabricante de referencia de la molécula, que puede diferir del de COMPRAS. |

El orden de columnas de las tres tablas es el de `generator.pipeline.HEADERS` y el de los encabezados
de los CSV (prueba local), porque la carga CSV empareja por posición.

## Estructuras del programa `warehouse`

### `DatasetSpec` y `TableSpec` (análisis de la DDL)

- `DatasetSpec`: `name`, `location`, `description`, `labels` (dict). Sale de la sentencia `CREATE
  SCHEMA`.
- `TableSpec`: `name`, `description`, `columns` (lista ordenada de `ColumnSpec`). Sale de cada
  `CREATE TABLE`.
- `ColumnSpec`: `name`, `type` (`STRING`, `INT64`, `NUMERIC` o `DATE`), `mode` (`REQUIRED` si hay
  `NOT NULL`, si no `NULLABLE`), `description`.
- Derivados: el JSON de esquema de carga (`[{"name", "type", "mode", "description"}]`) y el esperado
  para la verificación de metadatos (con `INT64` normalizado a `INTEGER`).

### `Expectations` (cifras esperadas)

| Parámetro | Tipo | Origen | Valor actual |
|---|---|---|---|
| `filas_compras` | `INT64` | `generator/manifest.json`, `files[COMPRAS.csv].rows` | 300000 |
| `filas_clue_cat` | `INT64` | ídem, `CLUE_CAT.csv` | 2000 |
| `filas_cuadro_basico` | `INT64` | ídem, `CUADRO_BASICO.csv` | 161 |
| `huerfanos_clue` | `INT64` | `orphans.CLUE` | 750 |
| `huerfanos_clave` | `INT64` | `orphans.CLAVE` | 750 |
| `fecha_inicio` | `DATE` | `config.toml`, `periodo.inicio` | 2024-01-01 |
| `fecha_fin` | `DATE` | `config.toml`, `periodo.fin` | 2025-12-31 |
| `precio_minimo` | `NUMERIC` | `precios`, R9 | 6.75 |
| `precio_maximo` | `NUMERIC` | `precios`, R9 | 17820 |
| `dispersion_maxima` | `NUMERIC` | `precios`, R9 | 4.4 |

El manifiesto que se usa es el versionado (`generator/manifest.json`), el mismo contra el que
`make bq-load` comprueba `data/` antes de cargar.

### `CheckResult` (fila de un chequeo fallido)

Contrato común de los chequeos SQL y de la verificación de metadatos; ver
[contracts/checks.md](contracts/checks.md).

| Campo | Tipo | Contenido |
|---|---|---|
| `CHEQUEO` | `STRING` | Nombre de la regla (`conteo_filas`, `unicidad_claves`...) |
| `OBJETO` | `STRING` | Tabla o tabla.columna afectada |
| `DETALLE` | `STRING` | Qué falló, en una frase corta |
| `ESPERADO` | `STRING` | Valor esperado |
| `OBTENIDO` | `STRING` | Valor encontrado |

### Caso negativo (`sql/checks/negativos/*.json`)

| Campo | Contenido |
|---|---|
| `esperado.CHEQUEO` | Nombre del chequeo que tiene que fallar |
| `esperado.OBJETO` | Objeto que el chequeo tiene que informar |
| `tablas.<TABLA>` | Lista de filas; cada fila tiene todas las columnas de la tabla según la DDL, con valores como cadenas y `null` para nulo |

Ver [contracts/checks.md](contracts/checks.md#casos-negativos-fr-033).

## Estados

Las tablas no tienen ciclo de vida propio. El recorrido del entorno es:

1. sin dataset (`make doctor`: B03 omitido);
2. esquema creado y tablas vacías (`make bq-schema`; B03 en OK; fallarían `conteo_filas` y
   `reconciliacion_join`);
3. tablas cargadas (`make bq-load`; chequeos en 0 filas);
4. recargadas (`make bq-load` otra vez; misma huella de contenido).

Una recarga fallida deja la tabla en el estado 3 anterior, porque el job de carga es atómico.
