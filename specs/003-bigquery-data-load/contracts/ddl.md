# Contract: secciones 1 y 2 de `sql/farma_analytics.sql`

El archivo es el entregable y la única definición del esquema. Esta feature escribe sus dos primeras
secciones; las features de la vista y de las consultas añaden la 3 y la 4 a continuación.

## Estructura

```text
-- <header: purpose, how to run it (console or make), synthetic data, section list>

-- Section 1: dataset.
CREATE SCHEMA IF NOT EXISTS farma_analytics
OPTIONS (location = 'US', description = '...', labels = [...]);

-- Section 2: tables.
-- <one line: no partitioning or clustering (about 32 MB), no foreign keys (deliberate orphans)>
CREATE TABLE IF NOT EXISTS farma_analytics.COMPRAS (...) OPTIONS (description = '...');
CREATE TABLE IF NOT EXISTS farma_analytics.CLUE_CAT (...) OPTIONS (description = '...');
CREATE TABLE IF NOT EXISTS farma_analytics.CUADRO_BASICO (...) OPTIONS (description = '...');
```

## Reglas que comprueban las pruebas locales

1. Hay exactamente una sentencia `CREATE SCHEMA` y tres `CREATE TABLE`, en este orden, antes de
   cualquier otra sentencia.
2. Las sentencias `CREATE SCHEMA` y `CREATE TABLE` no usan `AS SELECT`, `PARTITION BY`, `CLUSTER BY`,
   `PRIMARY KEY`, `FOREIGN KEY`, `expiration_timestamp` ni `default_table_expiration_days`. La regla
   se limita a esas sentencias porque la sección 3 tendrá `AS SELECT` en la vista y la 4, `PARTITION
   BY` en funciones de ventana. En todo el archivo, fuera de comentarios, no hay `OR REPLACE TABLE`
   ni referencias con ID de proyecto.
3. `location` del dataset es igual a `--location` de `.bigqueryrc` (sin distinguir mayúsculas).
4. Las labels `project` y `env` del dataset son iguales a las de `BQ_LABELS` del `Makefile`; existe
   la label `owner`; claves y valores en minúsculas.
5. Cada tabla tiene exactamente las columnas de [data-model.md](../data-model.md), en ese orden, que
   es el de `generator.pipeline.HEADERS`.
6. Tipos: `FECHA DATE`, `PIEZAS INT64`, `IMPORTE NUMERIC` sin parámetros, el resto `STRING`.
7. `NOT NULL` exactamente en `CLUE`, `CLAVE`, `COD_PROVEEDOR`, `FECHA`, `PIEZAS` e `IMPORTE` de cada
   tabla donde aparecen.
8. El dataset, cada tabla y cada columna tienen `description` no vacía. Las descripciones no
   contienen comillas simples ni `;`.
9. Los comentarios están en inglés, y el de cada sentencia dice qué es el objeto y para qué existe
   (principio II); revisión manual, porque el lint de prosa ya no mira `.sql`.
10. SQLFluff no informa violaciones (pre-commit).

## Derivación del esquema de carga

Para cada `CREATE TABLE`, el programa genera:

```json
[
  {"name": "CLUE", "type": "STRING", "mode": "REQUIRED", "description": "..."},
  ...
]
```

con `mode = REQUIRED` si la columna tiene `NOT NULL` y `NULLABLE` si no. El archivo vive solo
durante la carga, en un directorio temporal.
