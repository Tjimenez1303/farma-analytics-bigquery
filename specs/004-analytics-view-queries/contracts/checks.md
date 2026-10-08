# Contract: chequeo de la vista y metadatos (cambios sobre la feature 003)

El contrato común de salida (`CHEQUEO`, `OBJETO`, `DETALLE`, `ESPERADO`, `OBTENIDO`; 0 filas si todo
está bien) no cambia: ver
[../../003-bigquery-data-load/contracts/checks.md](../../003-bigquery-data-load/contracts/checks.md).

## Chequeo 07: `sql/checks/07_reconciliacion_vista.sql`

| DETALLE | ESPERADO | OBTENIDO |
|---|---|---|
| `filas: vista frente a COMPRAS menos huérfanas` | filas de `COMPRAS` − filas con `CLUE` o `CLAVE` sin catálogo | `COUNT(*)` de la vista |
| `IMPORTE: vista frente a INNER JOIN` | `SUM(IMPORTE)` del `INNER JOIN` de las tablas base | `SUM(IMPORTE)` de la vista |
| `PIEZAS: vista frente a INNER JOIN` | `SUM(PIEZAS)` del `INNER JOIN` | `SUM(PIEZAS)` de la vista |
| `ENTIDAD_ISO nulos` | 0 | `COUNTIF(ENTIDAD_ISO IS NULL)` |
| `ANIO nulos` | 0 | `COUNTIF(ANIO IS NULL)` |
| `MES nulos` | 0 | `COUNTIF(MES IS NULL)` |

- `CHEQUEO = 'reconciliacion_vista'`, `OBJETO = 'v_compras_farma_completa'`.
- Sin parámetros. Las huérfanas se cuentan con `NOT EXISTS`, sin joins externos.
- Lee la vista y las tablas base con los alias `vista`, `compras`, `clue_cat` y `cuadro_basico`.
- Es el único chequeo que referencia la vista, y eso lo marca como chequeo "de vista" (research R9).

## Caso negativo: `sql/checks/negativos/07_reconciliacion_vista.json`

- `tablas` incluye `COMPRAS`, `CLUE_CAT`, `CUADRO_BASICO` y `v_compras_farma_completa`.
- Las tablas base tienen dos líneas que casan y una huérfana. La vista tiene tres filas: las dos
  líneas (una duplicada) y una fila con `ENTIDAD_ISO` nulo.
- `esperado = {"CHEQUEO": "reconciliacion_vista", "OBJETO": "v_compras_farma_completa"}`.
- `checks.inline_tables` sustituye las cuatro referencias con los tipos de `TableSpec` y `ViewSpec`.

## Verificación de metadatos de la vista (FR-018)

Con `bq show --format=json farma_analytics.v_compras_farma_completa` (sin job ni costo), diferencias
con `OBJETO = 'v_compras_farma_completa'` o `v_compras_farma_completa.<COLUMNA>`:

| DETALLE | ESPERADO | Fuente esperada |
|---|---|---|
| `Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'` | existe | — |
| `tipo de objeto` | `VIEW` | — |
| `dialecto de la vista` | `useLegacySql = false` | — |
| `descripción de la vista` | descripción de la sección 3 | `ViewSpec.description` |
| `nombre en la posición N` / `columna` (falta o sobra) | nombre de la lista | `ViewSpec.columns` |
| `tipo` | tipo derivado | `ViewSpec.columns[].type` |
| `descripción` | descripción de la lista | `ViewSpec.columns[].description` |

El modo no se compara, porque los campos de una vista no lo declaran.

## Ejecución por objetivo

| Objetivo | Metadatos | Chequeos 01 a 06 | Chequeo 07 | Si falta la vista |
|---|---|---|---|---|
| `bq-schema` | dataset y tablas | no | no | no aplica |
| `bq-load` | dataset, tablas y vista si existe | sí | solo si la vista existe | aviso, sin fallar |
| `bq-vista` | completa | sí | sí | no aplica (la acaba de crear) |
| `bq-checks` | completa | sí | sí | falla |
| `bq-checks-negativos` | no | sí (con su caso) | sí (con su caso) | no aplica |
| `bq-consultas` | solo existencia de la vista | no | no | falla antes de ejecutar (también si la vista tiene 0 filas) |
