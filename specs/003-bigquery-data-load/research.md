# Research: Carga de datos en BigQuery

Decisiones de la Fase 0 del plan. Todas las afirmaciones sobre BigQuery y `bq` se verificaron el
2026-10-08 contra la documentación oficial (`docs.cloud.google.com/bigquery/docs/`); las rutas
están en la sección de fuentes.

## R1. DDL del dataset: `CREATE SCHEMA IF NOT EXISTS` con location explícita

- **Decision**: la sección 1 de `sql/farma_analytics.sql` crea el dataset con
  `CREATE SCHEMA IF NOT EXISTS farma_analytics OPTIONS (location = 'US', description = '...',
  labels = [('project', 'farma-analytics'), ('env', 'dev'), ('owner', 'bi')])`. Sin
  `default_table_expiration_days`, sin `is_case_insensitive` (queda en `FALSE`, nombres sensibles a
  mayúsculas) y sin ID de proyecto. Una prueba pytest compara la location de la DDL con la de
  `.bigqueryrc` y las labels `project` y `env` con `BQ_LABELS` del `Makefile`.
- **Rationale**: la referencia de `CREATE SCHEMA` dice que si se fija `location` y el job también la
  fija, "the two values must match; otherwise the query fails". Como `.bigqueryrc` pasa `--location`
  a todos los jobs, BigQuery rechaza cualquier diferencia y la prueba la detecta antes, sin red. Sin
  la opción, el dataset se crearía en la location del job, que en la consola no siempre es `US`; el
  `.sql` debe funcionar solo en la consola (sección "Entregable SQL"). Con `IF NOT EXISTS`, si el
  dataset ya existe la sentencia "has no effect", así que una location distinta en un dataset previo
  no da error: la detecta la verificación de metadatos (R8) y `make doctor` (B03).
- **Alternatives considered**: omitir `location` (depende de la configuración de la consola);
  generar el `.sql` con la location sustituida (el entregable dejaría de ser un archivo estático).

## R2. DDL de las tablas: tipos, modos, descripciones y lo que no se declara

- **Decision**: la sección 2 crea `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` con `CREATE TABLE IF NOT
  EXISTS farma_analytics.<TABLA> (...)`, columnas en el orden de los CSV, `NOT NULL` en `CLUE`,
  `CLAVE`, `COD_PROVEEDOR`, `FECHA`, `PIEZAS` e `IMPORTE`, `OPTIONS (description = '...')` en cada
  columna y `OPTIONS (description = '...')` en cada tabla con grano y llave. Sin `PARTITION BY`,
  `CLUSTER BY`, `PRIMARY KEY`, `FOREIGN KEY`, `AS SELECT`, labels de tabla ni expiración.
- **Rationale**: la referencia dice que `NOT NULL` crea la columna en modo `REQUIRED` y que "if any
  table exists with the same name, the CREATE statement has no effect", que es la semántica que pide
  la sección "Entregable SQL" (re-ejecutar no destruye datos). `NUMERIC` sin parámetros cumple el
  principio II. Las tablas pesan unos 32 MB en total, por debajo de los 64 MB a partir de los que el
  clustering compensa y muy lejos de los ~10 GB por partición: particionar o clusterizar sería
  adorno (principio II) y la decisión se documenta en un comentario de la DDL y en el README. Las
  claves foráneas quedan prohibidas por los huérfanos (principio III) y las primarias fuera de alcance
  (además, `WRITE_TRUNCATE` las borraría, ver R5). Las labels de tabla no llegan a facturación
  (anexo de estándares, n.º 28), así que solo el dataset las lleva.
- **Alternatives considered**: `CREATE OR REPLACE TABLE` (prohibido sobre tablas cargadas); claves
  primarias `NOT ENFORCED` en los catálogos (YAGNI en esta feature y se perderían en cada recarga).

## R3. Ejecución de la DDL desde `make`: sentencia por sentencia, dry run antes de cada una

- **Decision**: `make bq-schema` lee `sql/farma_analytics.sql`, lo divide en sentencias con el
  analizador de SQLFluff (dialecto `bigquery`) y ejecuta solo las de tipo `CREATE SCHEMA` y `CREATE
  TABLE`, en orden. Para cada una: `bq query --dry_run`; si falla, se detiene sin ejecutarla; si pasa,
  `bq query --label=project:farma-analytics --label=env:dev`. Las secciones 3 y 4 (vista y consultas)
  las ejecutarán los objetivos de las features siguientes.
- **Rationale**: el dry run de un `CREATE TABLE` sobre un dataset que aún no existe fallaría, así que
  no se puede validar el archivo entero de una vez antes de crear el dataset. Ejecutar sentencia por
  sentencia cumple "cada sentencia se valida con un dry run antes de ejecutarse" y deja un error
  localizado. SQLFluff ya está fijado en 4.3.0, conoce comentarios, comillas y escapes del dialecto, y
  se probó el 2026-10-08 sobre una DDL de ejemplo: la analiza sin violaciones y expone nombre, tipo,
  `NOT NULL` y `description` de cada `column_definition`. Se usa su API avanzada
  (`sqlfluff.core.Linter(...).parse_string`), que da el tipo, el texto y la línea de cada segmento y
  marca como `unparsable` el SQL que no entiende.
- **SQL por la entrada estándar**: la referencia de `bq query` dice que una consulta pasada como texto
  no puede llevar comentarios y documenta la alternativa `bq query < query.sql`. Como los chequeos y
  el entregable llevan comentarios, el programa envía siempre el SQL por la entrada estándar.
- **Evidencia del dry run en DDL**: la referencia de DDL muestra `bq query --dry_run` sobre un
  `CREATE PROCEDURE` ("You can use the BigQuery dry run feature to validate your stored procedure
  without creating it"), y `make gcp-dialect` de la feature 001 ya hace dry run de un `ALTER
  PROJECT` en el proyecto real. La quickstart V2 lo confirma para `CREATE SCHEMA` y `CREATE TABLE`.
  El dry run de cada sentencia imprime los bytes estimados, de modo que la salida muestra que
  ninguna consulta se acerca al límite de `.bigqueryrc` (SC-006).
- **Alternatives considered**: dividir por `;` con una expresión regular (frágil con `;` dentro de
  cadenas); ejecutar el archivo como script de varias sentencias (sin dry run por sentencia y con
  el problema del dataset inexistente); marcadores de sección en comentarios (otra convención que
  mantener).

## R4. Esquema de carga derivado de la DDL

- **Decision**: el mismo análisis de R3 produce, para cada tabla, la lista de columnas con nombre,
  tipo, modo y descripción. De ella se escribe en un directorio temporal un archivo JSON de esquema
  por tabla (`[{"name", "type", "mode", "description"}]`), que se pasa como tercer argumento
  posicional de `bq load`. Los archivos no se versionan. La comparación con lo que devuelve la API
  normaliza `INT64` a `INTEGER`, porque `TableFieldSchema` documenta `INTEGER (or INT64)` y la API
  devuelve el nombre heredado.
- **Rationale**: cumple la sección "Entregable SQL" ("si `bq load` necesita un esquema JSON, MUST
  derivarse de la DDL") sin una segunda definición versionada. La página de esquemas documenta el
  formato del archivo y que debe ser local.
- **Alternatives considered**: versionar `schemas/*.json` y compararlos con la DDL en una prueba
  (dos fuentes que mantener); copiar el esquema de la tabla viva con `bq show --schema` (propagaría
  una tabla desviada en lugar de detectarla).

## R5. Carga idempotente y atómica: `bq load --replace` por tabla

- **Decision**: cada tabla se carga con
  `bq load --replace --source_format=CSV --skip_leading_rows=1 --autodetect=false
  --max_bad_records=0 --encoding=UTF-8 farma_analytics.<TABLA> data/<TABLA>.csv <esquema>.json`.
  Antes de cargar se comprueba que el dataset y las tres tablas existen y coinciden con la DDL (R8).
  Si una tabla no existe, se detiene y pide `make bq-schema`, porque `--replace` la crearía sin pasar
  por la DDL.
- **Rationale**:
  - la documentación de carga CSV dice que "load jobs are atomic and consistent; if a load job
    fails, none of the data is available": una recarga fallida deja la tabla como estaba
    (aclaración de la spec, opción A);
  - `--replace` equivale a `WRITE_TRUNCATE`, que según el recurso Job "overwrites the data, removes
    the constraints and uses the schema from the load job". Por eso el esquema de la carga lleva modos
    y descripciones de la DDL (R4) y por eso no se declaran claves en esta feature;
  - `--autodetect` vale `false` por defecto, pero se escribe explícito porque el principio II prohíbe
    la autodetección y así queda visible en el comando;
  - `--max_bad_records=0` es el valor por defecto y se escribe explícito por FR-012;
  - `--allow_quoted_newlines` no hace falta: ningún campo generado contiene saltos de línea. Las comas
    dentro de `FABRICANTE` van entre comillas dobles, que es el `--quote` por defecto;
  - las fechas `YYYY-MM-DD` son el formato que exige la carga CSV para `DATE`, y los CSV no llevan BOM,
    como recomienda la misma página;
  - la misma página recomienda un `jobId` único por job de carga para poder reintentar sin duplicar
    datos. Con `--replace` un reintento reemplaza la tabla otra vez y el resultado es el mismo, así
    que no se fija `--job_id`.
- **Riesgo y contingencia**: el recurso Job dice que `WRITE_TRUNCATE` "uses the schema from the load
  job" y no menciona la descripción de la tabla, que es metadato de tabla y no parte del esquema.
  Se espera que se conserve, y la verificación de metadatos posterior a cada carga lo comprueba
  (quickstart V4). Si se perdiera, la contingencia es reaplicarla después de cada carga con
  `ALTER TABLE farma_analytics.<TABLA> SET OPTIONS (description = ...)`, un job de consulta con dry
  run y labels cuyo texto sale de la misma DDL.
- **Resultado (2026-10-08)**: en la quickstart V4 la verificación de metadatos posterior a las tres
  cargas con `--replace` no informó diferencias. La descripción de la tabla, las descripciones de
  las columnas y los modos se conservan, así que la contingencia no hace falta.
- **Alternatives considered**: `TRUNCATE TABLE` y carga en modo anexar (dejaba la tabla vacía si la
  carga fallaba, descartado en la aclaración); `WRITE_TRUNCATE_DATA`, que conserva esquema y
  restricciones, pero `bq` no tiene flag para ese modo y habría que usar la biblioteca cliente;
  tabla de staging y `MERGE` (más piezas sin beneficio a este volumen).

## R6. Dry run, labels y límite de bytes por tipo de job

- **Decision**: los jobs de consulta (DDL, chequeos y huella de contenido) llevan dry run previo,
  `--label=project:farma-analytics --label=env:dev` y el `maximum_bytes_billed` de `.bigqueryrc`.
  Los jobs de carga van sin dry run ni labels. Ningún comando repite `--location`,
  `--use_legacy_sql` ni `--maximum_bytes_billed`. El programa comprueba al arrancar que `BIGQUERYRC`
  apunta al `.bigqueryrc` del repositorio, igual que `scripts/doctor.sh`.
- **Rationale**: en la referencia de `bq`, `--dry_run` y `--label` son flags de `bq query`; la página
  de labels dice "the bq tool supports adding labels only to query jobs", y el recurso Job dice que
  el dry run en jobs que no son consultas tiene "behavior ... undefined". Es lo que fija la
  constitución v1.3.0 (principio II y "Costo y disponibilidad"). `--parameter` necesita GoogleSQL,
  que ya fija `.bigqueryrc`.
- **Alternatives considered**: biblioteca `google-cloud-bigquery` para poner labels en la carga
  (nueva dependencia sin cambio en el costo, descartada en la aclaración Q1).

## R7. Chequeos de calidad: una consulta por regla en `sql/checks/`

- **Decision**: seis archivos, uno por regla del principio IV, ejecutados en orden por nombre:
  `01_conteo_filas.sql`, `02_unicidad_claves.sql`, `03_nulos.sql`, `04_dominios.sql`,
  `05_reconciliacion_join.sql` y `06_precio_unitario.sql`. Todos devuelven el mismo contrato de
  columnas (`CHEQUEO`, `OBJETO`, `DETALLE`, `ESPERADO`, `OBTENIDO`, todas `STRING`) y 0 filas cuando
  la regla se cumple (ver [contracts/checks.md](contracts/checks.md)). Las cifras esperadas llegan
  como parámetros con nombre (`@filas_compras`, `@fecha_inicio`, `@precio_minimo`...) mediante
  `bq query --parameter=NOMBRE:TIPO:VALOR`; el programa pasa a cada archivo solo los parámetros que
  menciona. El resultado se lee con `--format=json`.
- **Rationale**: es la opción elegida en la aclaración Q2. Los parámetros evitan cifras fijas en el
  SQL (FR-019, FR-022 y FR-024) y la página de consultas parametrizadas documenta la forma
  `NAME:TYPE:VALUE`. Un contrato común de columnas permite un solo programa para todos. Cada
  consulta lee solo las columnas que necesita; el conteo usa `COUNT(*)`, que se resuelve con
  metadatos, y el resto lee como máximo las columnas de `COMPRAS` (unos 30 MB), muy por debajo del
  límite de 1 GiB.
- **Alternatives considered**: una sola consulta con `UNION ALL` de todas las reglas (una regla por
  archivo es lo que pide el principio IV); assertions de Dataform (descartadas en Q2).

## R8. Verificación del esquema publicado contra la DDL (FR-026): metadatos con `bq show`

- **Decision**: la comparación del esquema publicado con la DDL no es una consulta: el programa lee
  `bq show --format=json farma_analytics` y `bq show --format=json farma_analytics.<TABLA>` y compara
  con el análisis de la DDL la location, la descripción y las labels del dataset, y la descripción y
  los campos de cada tabla (nombre, orden, tipo normalizado, modo y descripción). Informa las
  diferencias con el mismo contrato de columnas que los chequeos SQL y falla si hay alguna. Corre al
  final de `make bq-schema`, antes y después de cada carga y dentro de `make bq-checks`.
- **Rationale**: `bq show` lee metadatos sin crear un job, así que no cuesta nada, y devuelve las
  descripciones tal cual. En `INFORMATION_SCHEMA.TABLE_OPTIONS`, en cambio, la descripción llega como
  literal entre comillas (`"test data"`), lo que obliga a reproducir su escape, y las consultas a
  `INFORMATION_SCHEMA` no usan caché y se facturan cada vez. Esta regla no es una de las seis del
  principio IV, así que no rompe la "única implementación canónica" de esas reglas.
- **Alternatives considered**: consulta en `sql/checks/` sobre `INFORMATION_SCHEMA.COLUMNS`,
  `COLUMN_FIELD_PATHS` y `TABLE_OPTIONS` con el esquema esperado como parámetro JSON (más compleja,
  con costo y con el problema del escape).

## R9. Umbrales del precio unitario (FR-024)

- **Decision**: los umbrales se calculan al ejecutar a partir de `generator/config.toml`, leído con
  `generator.config.load_config` para no duplicar el análisis ni la validación:
  - `precio_minimo = min(nivel.*[0]) × factor_generico[0] × (1 − ruido_max)` = 15 × 0.5 × 0.9 = 6.75;
  - `precio_maximo = max(nivel.*[1]) × factor_referencia[1] × (1 + ruido_max)` = 9 000 × 1.8 × 1.1
    = 17 820;
  - `dispersion_maxima = factor_referencia[1] × (1 + ruido_max) / (factor_generico[0] × (1 −
    ruido_max))` = 1.98 / 0.45 = 4.4, redondeada hacia arriba a 6 decimales.
  La consulta acepta un centavo de margen por redondeo: `PRECIO_MINIMO >= @precio_minimo - 0.01`,
  `PRECIO_MAXIMO <= @precio_maximo + 0.01` y `PRECIO_MAXIMO <= @dispersion_maxima × (PRECIO_MINIMO +
  0.01) + 0.01`. Solo se evalúan las claves presentes en `CUADRO_BASICO` (`INNER JOIN`).
- **Rationale**: el generador fija el precio base de cada clave con distribución log-uniforme dentro
  de su nivel, lo redondea a centavos, lo multiplica por el factor del fabricante (uniforme en el
  rango de su tipo) y por un ruido uniforme en `[1 − ruido_max, 1 + ruido_max]`, y redondea el
  resultado a centavos (`generator/supplies.py` y `generator/purchases.py`). Como `IMPORTE` es
  exactamente `PIEZAS` × precio redondeado, `IMPORTE / PIEZAS` devuelve ese precio sin error, y el
  único desvío posible frente a las cotas teóricas es el redondeo a centavos. Los huérfanos de
  `CLAVE` usan claves casi siempre distintas fuera del catálogo, así que no tienen dispersión que
  medir. El cociente se calcula con `SAFE_DIVIDE` (principio II).
- **Alternatives considered**: cotas por clave con los factores reales de sus fabricantes (el
  generador no los exporta); regla estadística sobre la mediana (descartada en la aclaración).

## R10. Huella de contenido para comprobar la segunda carga (SC-004)

- **Decision**: `sql/ops/huella_contenido.sql` devuelve por tabla `FILAS = COUNT(*)` y
  `HUELLA = SUM(CAST(FARM_FINGERPRINT(TO_JSON_STRING(<alias>)) AS BIGNUMERIC))`. `make bq-load` la
  ejecuta al final (con dry run y labels) e imprime la tabla. Dos cargas iguales imprimen las mismas
  cifras.
- **Rationale**: la suma no depende del orden de las filas, que BigQuery no garantiza, y a
  diferencia de `BIT_XOR` no se anula cuando hay dos filas idénticas (en `COMPRAS` puede haberlas).
  `BIGNUMERIC` evita el desbordamiento de sumar 300 000 enteros de 64 bits. No es un chequeo (no
  devuelve 0 filas), por eso vive fuera de `sql/checks/`.
- **Alternatives considered**: comparar `numRows` y `lastModifiedTime` de `bq show` (no detecta
  contenido distinto con el mismo número de filas); exportar y comparar archivos (costo y tiempo).

## R11. Orquestación: paquete `warehouse/` y objetivos de `make`

- **Decision**: un paquete `warehouse/` sin empaquetar, como `generator/`, ejecutado con
  `uv run python -m warehouse {schema,load,checks,checks-negativos}`, y cuatro objetivos nuevos:
  - `make bq-schema`: dry run y ejecución de las secciones 1 y 2 y verificación de metadatos;
  - `make bq-load`: verifica los CSV contra el manifiesto con `generator.manifest.verify` (dentro
    del programa, para que FR-011 se cumpla también sin `make`), verifica metadatos, carga las tres
    tablas, vuelve a verificar metadatos, ejecuta los chequeos e imprime la huella;
  - `make bq-checks`: verificación de metadatos y los seis chequeos SQL;
  - `make bq-checks-negativos`: cada chequeo frente a su caso negativo, con datos en línea (R15).
  Los cuatro dependen de `require-venv` y `require-project`, reciben el proyecto por la variable
  `PROJECT_ID` y las labels de jobs por `BQ_JOB_LABELS` (exportadas desde `BQ_LABELS` del `Makefile`,
  que sigue siendo la única fuente). `bq` se invoca con `subprocess.run` y una lista de argumentos,
  sin shell, con `--project_id` global igual que `$(BQ)`.
- **Rationale**: el trabajo incluye analizar la DDL, leer TOML y JSON y comparar estructuras, que en
  bash sería frágil. Python 3.12 y uv ya están en el stack (principio VIII y tabla de stack), así
  que no se añade ninguna herramienta. No hay dependencias nuevas: `tomllib`, `json`, `subprocess`,
  `tempfile`, `decimal` y `argparse` son de la biblioteca estándar, y SQLFluff ya está fijado en el
  grupo `dev`, que `uv sync` y `uv run` instalan por defecto.
- **Alternatives considered**: script bash como `doctor.sh` (análisis de SQL y JSON a mano); la
  biblioteca cliente de BigQuery (nueva dependencia, autenticación ADC distinta de la de `bq`).

## R12. Comentarios del SQL y textos de descripción

- **Decision**: comentarios en inglés y breves en todos los `.sql` (cabecera del archivo, una línea
  por sección y la pregunta de cada chequeo). Las descripciones de dataset, tablas y columnas, en
  español, con grano y llave en las de tabla, y la mención de que los datos son sintéticos en la del
  dataset (principio V). `scripts/lint_prosa.sh` deja de revisar `.sql` (FR-032).
- **Rationale**: aclaración Q3 y constitución v1.3.0 (principios II y IX).
- **Alternatives considered**: ninguna nueva; ver la aclaración.

## R13. Dataform CLI (R18 de la feature 001)

- **Decision**: esta feature no usa Dataform y no toca `package.json`, `scripts/doctor.sh` ni
  `make setup-dev`. `@dataform/cli` 3.0.70 sigue instalado con el riesgo aceptado en R18. Si al
  cerrar el proyecto ninguna feature lo usa, se retira en un PR `chore` propio que actualice también
  el diagnóstico y el README.
- **Rationale**: retirarlo ahora toca el diagnóstico (que comprueba la herramienta), el README y la
  instalación, fuera del alcance de la carga. Mantenerlo no añade riesgo nuevo: solo corre en local y
  esta feature no lo invoca.
- **Alternatives considered**: retirarlo en esta feature (mezcla un cambio de herramientas con la
  carga en un mismo PR).

## R14. Pruebas locales sin GCP

- **Decision**: pruebas pytest en `tests/warehouse/`, sin red ni credenciales, que corren en
  `make test` y en el job `tests` de CI:
  - la DDL tiene exactamente los campos, el orden, los tipos y los modos esperados, con el mismo
    orden que `generator.pipeline.HEADERS`, y descripción en dataset, tablas y columnas;
  - la DDL no contiene `OR REPLACE TABLE`, `AS SELECT`, `PARTITION BY`, `CLUSTER BY`, `FOREIGN KEY`,
    expiración ni ID de proyecto;
  - la location y las labels coinciden con `.bigqueryrc` y `BQ_LABELS`;
  - el JSON de esquema derivado coincide con la DDL;
  - los umbrales salen 6.75, 17 820 y 4.4 con la configuración actual y los parámetros salen del
    manifiesto;
  - los comandos `bq` construidos: dry run antes de cada consulta, labels solo en consultas, flags
    de carga exactos y ningún flag de `.bigqueryrc` repetido;
  - con un ejecutor falso, un dry run fallido detiene el proceso sin ejecutar la sentencia y un
    chequeo con filas hace fallar el comando;
  - cada archivo de `sql/checks/` usa solo parámetros que el programa sabe proveer;
  - cada chequeo tiene su caso negativo y la sustitución por datos en línea no deja referencias a
    `farma_analytics.` (R15).
  SQLFluff revisa los `.sql` nuevos en pre-commit, como ya hace.
- **Rationale**: todo lo que se puede comprobar sin GCP se comprueba en CI. Lo que necesita BigQuery
  se valida con el [quickstart](quickstart.md), que ejecuta el dueño.
- **Alternatives considered**: emulador de BigQuery (no hay uno oficial).

## R15. Casos negativos de los chequeos con datos en línea (FR-033)

- **Decision**: cada chequeo de `sql/checks/` tiene un caso en `sql/checks/negativos/` (JSON con unas
  pocas filas y un error preparado). `make bq-checks-negativos` sustituye en memoria cada
  `farma_analytics.<TABLA> AS <alias>` por `(SELECT <columnas> FROM UNNEST(ARRAY<STRUCT<...>>[...]))
  AS <alias>`, tipado con la DDL y con `CAST` explícito de cada valor, y exige que el chequeo
  devuelva al menos una fila con el `CHEQUEO` y el `OBJETO` esperados. Cada consulta pasa por dry run
  y lleva labels.
- **Rationale**: con los datos buenos, un chequeo correcto y uno mal escrito devuelven las dos 0 filas,
  así que la V4 no distingue entre ellos. La V3 (tablas vacías) solo hace fallar el conteo y la
  reconciliación. Ejecutar el mismo texto versionado contra un error conocido es la forma de probar
  que cada chequeo detecta lo que dice. La consulta no lee tablas, por eso el dry run estima 0 bytes
  y no se factura nada. Es la única vía para probar el chequeo de nulos, porque el modo `REQUIRED`
  impide cargar nulos en una tabla. `UNNEST` de un `ARRAY` de `STRUCT` es la forma documentada en la
  referencia de sintaxis de consulta para construir filas en línea, y un `ARRAY` tipado
  (`ARRAY<STRUCT<...>>[]`) permite casos con una tabla vacía.
- **Alternatives considered**: dataset auxiliar `farma_analytics_pruebas` con expiración y CSV con
  errores (crea objetos, factura almacenamiento y no puede probar los nulos); solo revisión de código
  (deja el riesgo de un chequeo que nunca falla).

## Fuentes

Rutas relativas a `docs.cloud.google.com/bigquery/docs/`, consultadas el 2026-10-08:

- `reference/standard-sql/data-definition-language` (`CREATE SCHEMA`, `schema_option_list`, `CREATE
  TABLE`, `NOT NULL` y `REQUIRED`, `IF NOT EXISTS`, `column_option_list`)
- `reference/bq-cli-reference` (`bq load`: `--replace`, `--schema`, `--autodetect`,
  `--skip_leading_rows`, `--max_bad_records`; `bq query`: `--dry_run`, `--label`, `--parameter`;
  flags globales)
- `adding-labels#job-label` (labels solo en jobs de consulta con `bq`)
- `reference/rest/v2/Job` (`dryRun`, `WRITE_TRUNCATE`, `WRITE_TRUNCATE_DATA`)
- `reference/rest/v2/tables` (`TableFieldSchema`, `INTEGER (or INT64)`)
- `loading-data-cloud-storage-csv` (atomicidad de la carga, formato `DATE`, BOM, `--replace`)
- `batch-loading-data` (carga desde archivos locales)
- `schemas` (formato del archivo JSON de esquema)
- `running-queries#dry-run` (dry run)
- `parameterized-queries` (parámetros con nombre en `bq query`)
- `information-schema-intro` y `information-schema-table-options` (sin caché y formato de
  `option_value`)
- `best-practices-costs#restrict-bytes-billed` (`maximum_bytes_billed`)
- `reference/standard-sql/load-statements` (`LOAD DATA`, descartado)
