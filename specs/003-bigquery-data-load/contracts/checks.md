# Contract: chequeos de calidad

## Contrato común de salida

Cada chequeo devuelve 0 filas si la regla se cumple. Si no, devuelve una fila por incumplimiento con
estas columnas, todas `STRING` (`CAST` explícito de los números y fechas):

| Columna | Contenido |
|---|---|
| `CHEQUEO` | Nombre de la regla, igual al nombre del archivo sin prefijo ni extensión |
| `OBJETO` | `TABLA` o `TABLA.COLUMNA` |
| `DETALLE` | Qué se midió (por ejemplo, "filas", "nulos", "PIEZAS <= 0") |
| `ESPERADO` | Valor o cota esperada |
| `OBTENIDO` | Valor medido |

Reglas de estilo comunes (principio II y `.sqlfluff`): comentario de cabecera en inglés con la regla
que comprueba, `INNER JOIN ... ON` explícito como único join (sin `LEFT JOIN`, `CROSS JOIN` ni
comas en el `FROM`, tampoco con `UNNEST`) y con `COMPRAS` primero, `NOT EXISTS` para los huérfanos,
`UNPIVOT` para pasar conteos por columna a filas, alias de
tabla semánticos (`compras`, `clue_cat`, `cuadro_basico`), `AS` siempre, sin `SELECT *`, `GROUP BY`
por nombre, `SAFE_DIVIDE` en cocientes, sin `ORDER BY` salvo en la consulta externa, referencias
`farma_analytics.<TABLA>` sin ID de proyecto.

## Chequeos SQL (`sql/checks/`)

| Archivo | Regla (principio IV) | Parámetros | Cómo mide |
|---|---|---|---|
| `01_conteo_filas.sql` | Filas por tabla = manifiesto | `filas_compras`, `filas_clue_cat`, `filas_cuadro_basico` (`INT64`) | `COUNT(*)` por tabla frente al parámetro; una fila por tabla distinta |
| `02_unicidad_claves.sql` | `CLUE` única en `CLUE_CAT`, `CLAVE` única en `CUADRO_BASICO` | ninguno | `GROUP BY` la llave con `HAVING COUNT(*) > 1`; una fila por llave repetida |
| `03_nulos.sql` | Sin nulos en claves, `FECHA`, `PIEZAS`, `IMPORTE` | ninguno | `COUNTIF(<col> IS NULL)` por columna obligatoria (8 columnas en total) en una fila, pasada a filas con `UNPIVOT`; una fila por columna con nulos |
| `04_dominios.sql` | `PIEZAS > 0`, `IMPORTE >= 0`, `FECHA` en el periodo | `fecha_inicio`, `fecha_fin` (`DATE`) | `COUNTIF` de cada violación en `COMPRAS`, pasado a filas con `UNPIVOT`; una fila por dominio violado con el conteo y el mínimo o máximo encontrado |
| `05_reconciliacion_join.sql` | Filas e importe de `COMPRAS` = `INNER JOIN` + huérfanos; huérfanos = manifiesto | `huerfanos_clue`, `huerfanos_clave` (`INT64`) | CTE con totales de `COMPRAS`, CTE con el `INNER JOIN` de los dos catálogos, CTE que marca cada fila sin correspondencia con `NOT EXISTS` sobre cada catálogo; una fila por cuadre que no se cumple (filas, importe, huérfanos de `CLUE`, huérfanos de `CLAVE`) |
| `06_precio_unitario.sql` | `IMPORTE / PIEZAS` plausible por `CLAVE` del catálogo | `precio_minimo`, `precio_maximo`, `dispersion_maxima` (`NUMERIC`) | Mínimo y máximo de `SAFE_DIVIDE(IMPORTE, PIEZAS)` por clave con `INNER JOIN` a `CUADRO_BASICO`; una fila por clave fuera de cota o con dispersión excesiva, con un centavo de margen (research R9) |

Notas:

- El chequeo de nulos se mantiene aunque el modo `REQUIRED` ya impida nulos, para detectar un
  cambio de esquema (FR-021).
- La reconciliación compara importes `NUMERIC` sin redondeo: la igualdad es exacta.
- El programa pasa a cada archivo solo los parámetros que aparecen en su texto como `@nombre`. Una
  prueba local comprueba que todos los `@nombre` usados están en la tabla de
  [data-model.md](../data-model.md#expectations-cifras-esperadas).
- Un chequeo fallido no se corrige con `DISTINCT`, filtros ad hoc ni umbrales cambiados (FR-025).

## Verificación de metadatos (FR-026, sin consulta)

Compara la DDL analizada con `bq show --format=json` del dataset y de cada tabla. Informa con el
mismo contrato (`CHEQUEO = esquema_ddl`):

| Objeto | Qué compara |
|---|---|
| Dataset | existe; `location` igual a la de la DDL y `.bigqueryrc`; `description`; `labels` |
| Tabla | existe; `description` |
| Columna | nombre y posición; tipo (`INT64` = `INTEGER`); modo (sin modo = `NULLABLE`); `description` |

Una columna de más o de menos en la tabla publicada es una diferencia. Si falta el dataset o una
tabla, el mensaje indica ejecutar `make bq-schema`. Si un texto de descripción cambió en la DDL
después de crear la tabla, `CREATE TABLE IF NOT EXISTS` no lo actualiza: la diferencia aparece aquí
y se corrige con `ALTER TABLE ... SET OPTIONS` o `ALTER TABLE ... ALTER COLUMN ... SET OPTIONS`
(fuera de esta feature).

## Casos negativos (FR-033)

Cada chequeo SQL tiene en `sql/checks/negativos/<mismo nombre>.json` unas pocas filas con un error
preparado a propósito:

```json
{
  "esperado": {"CHEQUEO": "unicidad_claves", "OBJETO": "CLUE_CAT.CLUE"},
  "tablas": {
    "COMPRAS": [{"CLUE": "ASIMS000001", "CLAVE": "010.000.0001.00", "...": "..."}],
    "CLUE_CAT": [{"CLUE": "ASIMS000001", "...": "..."}, {"CLUE": "ASIMS000001", "...": "..."}],
    "CUADRO_BASICO": [{"CLAVE": "010.000.0001.00", "...": "..."}]
  }
}
```

| Caso | Error preparado | Objeto esperado |
|---|---|---|
| `01_conteo_filas` | 2 filas en `COMPRAS` frente a las del manifiesto | `COMPRAS` |
| `02_unicidad_claves` | una `CLUE` repetida en `CLUE_CAT` | `CLUE_CAT.CLUE` |
| `03_nulos` | una fila de `COMPRAS` con `CLUE` nula | `COMPRAS.CLUE` |
| `04_dominios` | una fila con `PIEZAS` 0 | `COMPRAS.PIEZAS` |
| `05_reconciliacion_join` | una `CLUE` de `COMPRAS` que no está en `CLUE_CAT` | `COMPRAS` |
| `06_precio_unitario` | una `CLAVE` con precios de 10.00 y 100.00 por pieza (dispersión 10 > 4.4) | `CUADRO_BASICO.CLAVE` |

El programa sustituye en memoria cada `farma_analytics.<TABLA> AS <alias>` del chequeo por
`(SELECT <columnas> FROM UNNEST(ARRAY<STRUCT<...>>[...])) AS <alias>`, con los tipos de la DDL y
`CAST` explícito de cada valor. El archivo `.sql` versionado no cambia, así que se prueba el mismo
texto que corre sobre las tablas reales. Como la consulta no lee tablas, el dry run estima 0 bytes.
Un caso pasa si el chequeo devuelve al menos una fila con el `CHEQUEO` y el `OBJETO` esperados; puede
devolver otras filas (por ejemplo, el conteo también falla con pocas filas) sin que eso cuente.

## Huella de contenido (`sql/ops/huella_contenido.sql`)

No es un chequeo. Devuelve una fila por tabla con `TABLA`, `FILAS` (`INT64`) y `HUELLA`
(`BIGNUMERIC`, suma de `FARM_FINGERPRINT(TO_JSON_STRING(<fila>))`). Dos cargas de los mismos CSV
devuelven las mismas cifras (SC-004).
