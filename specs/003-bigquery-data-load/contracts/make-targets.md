# Contract: objetivos de `make` y programa `warehouse`

Los cuatro objetivos tocan GCP y los ejecuta el dueño. Todos dependen de `require-venv` y
`require-project`, heredan `BIGQUERYRC=$(CURDIR)/.bigqueryrc` del `Makefile` y llaman a
`uv run python -m warehouse <subcomando>` con `PROJECT_ID` y `BQ_JOB_LABELS` en el entorno.

## Variables de entorno

| Variable | Origen | Uso |
|---|---|---|
| `BIGQUERYRC` | `export` del `Makefile` | Debe apuntar al `.bigqueryrc` del repositorio; si no, el programa sale con código 2 |
| `PROJECT_ID` | `$(PROJECT_ID)` del `Makefile` (`.env` o `gcloud config`) | `bq --project_id=...` en cada llamada |
| `BQ_JOB_LABELS` | `$(BQ_LABELS)` del `Makefile` | Labels de los jobs de consulta |

## `make bq-schema` → `python -m warehouse schema`

1. Analiza `sql/farma_analytics.sql` y toma, en orden, las sentencias `CREATE SCHEMA` y `CREATE
   TABLE`.
2. Para cada sentencia:
   - `bq --project_id=P query --dry_run` con la sentencia en la entrada estándar; si falla, imprime
     el error con el número de sentencia y sale con código 1 sin ejecutarla;
   - `bq --project_id=P query --label=project:farma-analytics --label=env:dev`, también con la
     sentencia en la entrada estándar.

   El SQL viaja siempre por la entrada estándar: la referencia de `bq` indica que una consulta
   pasada como texto no puede llevar comentarios, y la entrada estándar es la otra forma
   documentada (`bq query < query.sql`).
3. Verificación de metadatos (ver [checks.md](checks.md)); sale con 1 si hay diferencias.

Salida esperada (resumida):

```text
[1/4] CREATE SCHEMA farma_analytics: dry run OK (0 bytes estimados), ejecutada
[2/4] CREATE TABLE farma_analytics.COMPRAS: dry run OK (0 bytes estimados), ejecutada
[3/4] CREATE TABLE farma_analytics.CLUE_CAT: dry run OK (0 bytes estimados), ejecutada
[4/4] CREATE TABLE farma_analytics.CUADRO_BASICO: dry run OK (0 bytes estimados), ejecutada
Metadatos: 0 diferencias con la DDL
```

## `make bq-load` → `python -m warehouse load`

1. Verificación local de `data/` contra `generator/manifest.json` con `generator.manifest.verify`.
   Si falta un archivo o no coincide, imprime las diferencias y "Los CSV no coinciden con el
   manifiesto: ejecuta 'make data'." y sale con 1 sin llamar a `bq`.
2. Verificación de metadatos previa. Si falta el dataset o una tabla, sale con 1 y el mensaje "Falta
   <objeto>: ejecuta 'make bq-schema'". Si hay diferencias de esquema, sale con 1 y las lista.
3. Escribe en un directorio temporal un JSON de esquema por tabla derivado de la DDL.
4. Para cada tabla, en el orden de la DDL:

   ```text
   bq --project_id=P load --replace --source_format=CSV --skip_leading_rows=1 --autodetect=false
      --max_bad_records=0 --encoding=UTF-8 farma_analytics.<TABLA> <data_dir>/<TABLA>.csv <tmp>/<TABLA>.json
   ```

   Si una carga falla, imprime la tabla y el error de `bq` y sale con 1 (la tabla conserva su
   contenido anterior).
5. Lo mismo que `bq-checks`: verificación de metadatos (comprueba que la recarga no perdió
   descripciones ni modos) y los seis chequeos SQL. Si algo falla, sale con 1 sin calcular la huella.
6. Huella de contenido (`sql/ops/huella_contenido.sql`, con dry run y labels) impresa por tabla.

Salida esperada al final:

```text
Chequeos: 6 de 6 en 0 filas. Metadatos: 0 diferencias.
TABLA          FILAS   HUELLA
COMPRAS        300000  <número>
CLUE_CAT       2000    <número>
CUADRO_BASICO  161     <número>
```

## `make bq-checks` → `python -m warehouse checks`

1. Verificación de metadatos.
2. Para cada archivo de `sql/checks/` en orden de nombre: dry run con los parámetros que usa (imprime
   los bytes estimados), ejecución con labels, `--format=json` y `--max_rows=1000`, y conteo de
   filas devueltas. Como `bq query` recorta la salida en `--max_rows` (100 por defecto según la
   referencia de `bq`), un chequeo con 1000 filas se informa como "1000 o más".
3. Imprime una línea por chequeo (`OK` o `FALLO` con sus filas) y sale con 1 si alguno devolvió
   filas.

## `make bq-checks-negativos` → `python -m warehouse checks-negativos`

1. Analiza la DDL y lee las cifras esperadas (no verifica metadatos ni lee tablas).
2. Para cada archivo de `sql/checks/`, carga su caso de `sql/checks/negativos/` y sustituye en
   memoria cada `farma_analytics.<TABLA> AS <alias>` por una subconsulta sobre `UNNEST` de un `ARRAY`
   de `STRUCT` tipado con las columnas de la DDL (ver [checks.md](checks.md#casos-negativos-fr-033)).
3. Dry run (los bytes estimados deben ser 0) y ejecución con labels, `--format=json` y los parámetros
   del chequeo.
4. Imprime "detectó el error" si la respuesta tiene al menos una fila con el `CHEQUEO` y el `OBJETO`
   esperados, o "NO detectó el error" si no, y termina con "Casos negativos: N de 6 detectados.".
   Sale con 1 si N es menor que 6.

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | Todo terminó y los chequeos y metadatos están en 0 |
| 1 | Falló un dry run, una ejecución, una carga, un chequeo o la verificación de metadatos |
| 2 | Entorno inválido: `BIGQUERYRC` incorrecto, falta `PROJECT_ID` o `bq` no está en el `PATH` |

## Reglas de construcción de comandos (probadas sin GCP)

- Ningún comando incluye `--location`, `--use_legacy_sql` ni `--maximum_bytes_billed`.
- Toda llamada `bq query` sin `--dry_run` va precedida por la misma consulta con `--dry_run` y los
  mismos parámetros.
- `--label` aparece solo en `bq query` sin `--dry_run`. `bq load` no lleva `--label`.
- `bq` se invoca sin shell, con una lista de argumentos, y el SQL va en la entrada estándar.
