---

description: "Task list for feature 003-bigquery-data-load"
---

# Tasks: Carga de datos en BigQuery (esquema, carga idempotente y chequeos de calidad)

**Input**: Design documents from `specs/003-bigquery-data-load/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluidos. La spec exige pruebas automatizadas (FR-002, FR-009) y el plan fija pytest sin
GCP en `tests/warehouse/` (research R14). En cada historia se escriben antes de la implementación y
deben fallar primero.

**Organization**: tareas agrupadas por historia de usuario para implementarlas y probarlas por
separado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia a la que pertenece (US1 a US4).
- **[Dueño]** al inicio de la descripción: la ejecuta el dueño porque toca GCP. Claude escribe
  archivos y ejecuta solo verificaciones locales (`make test`, `make lint`, `make lint-prosa`,
  `make lint-sql`, pytest, sqlfluff).

## Reglas transversales (aplican a todas las tareas)

- Python 3.12 con anotaciones de tipo en todas las funciones públicas, `from __future__ import
  annotations`, `dataclasses` inmutables (`frozen=True`) y `pathlib.Path`. Docstrings y comentarios
  en inglés, breves, que dicen qué es cada cosa. Sin dependencias nuevas: biblioteca estándar más
  SQLFluff 4.3.0 (ya en el grupo `dev`).
- Los mensajes que ve el usuario (salida de `python -m warehouse`, errores, ayuda de `make`) van en
  español. Nombres de tabla, columna, archivo y parámetro se escriben tal cual.
- `bq` se invoca con `subprocess.run` y una lista de argumentos, nunca con `shell=True`, a través de
  una sola función de `warehouse/bq.py` que las pruebas sustituyen por un ejecutor falso.
- Ningún comando repite `--location`, `--use_legacy_sql` ni `--maximum_bytes_billed` (los fija
  `.bigqueryrc`). Toda consulta que se ejecuta va precedida por su dry run con los mismos
  parámetros. `--label` solo en `bq query` sin `--dry_run`. `bq load` sin `--label` ni `--dry_run`
  (research R6).
- SQL: GoogleSQL con las reglas del principio II y de `.sqlfluff` (palabras clave en mayúsculas, `AS`
  siempre, alias de tabla semánticos `compras`, `clue_cat`, `cuadro_basico`, `INNER JOIN ... ON` con
  `COMPRAS` primero, `GROUP BY` por nombre, `CAST` explícito, `SAFE_DIVIDE` en cocientes, sin
  `SELECT *`, sin ID de proyecto, referencias `farma_analytics.<TABLA>`, `AS` también en las tablas
  de las subconsultas, alias del `SELECT` nunca en `WHERE`). El único join permitido es `INNER
  JOIN ... ON` (constitución, principio II): ni `LEFT JOIN`, ni `CROSS JOIN`, ni comas entre
  elementos del `FROM`, tampoco con `UNNEST`. Los huérfanos se cuentan con `NOT EXISTS` y los
  conteos por columna se pasan a filas con `UNPIVOT`. Comentarios en inglés, breves
  (constitución v1.3.0). Cada archivo lleva un comentario de cabecera y cada sentencia un comentario
  que dice qué es y para qué existe: la pregunta de negocio o la regla que responde (principio II,
  "los comentarios explican el porqué"). Por ejemplo, `-- Fact table at purchase-line grain, joined
  to both catalogs by the view.`
- Descripciones de dataset, tablas y columnas en español, sin comillas simples ni `;`.
- Ningún archivo versionado menciona el documento de requisitos de origen ni contiene IDs de
  proyecto, correos o credenciales.
- Antes de afirmar que el lint pasa sobre archivos nuevos, hacer `git add` de esos archivos, porque
  `pre-commit run --all-files` no revisa archivos sin versionar.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: sacar los `.sql` del lint de prosa (FR-032) y preparar el esqueleto del paquete y de
las pruebas.

- [X] T001 [P] Editar `scripts/lint_prosa.sh` para que deje de revisar `.sql` (FR-032, constitución v1.3.0): en `add_file` el patrón pasa a `*.md | *.txt` y el aviso a "(solo .md y .txt)"; en `add_dir` el `find` deja de buscar `-name '*.sql'`; se elimina la línea `[ -d sql ] && add_dir sql`; se elimina la función `sql_comments` y la rama `*.sql)` del `case` que la usa. El resto del comportamiento no cambia
- [X] T002 [P] Editar `tests/test_lint_prosa.py`: sustituir `test_sql_only_checks_comments` por una prueba que pasa un archivo `.sql` temporal con una raya en un comentario y comprueba que no hay marcas, que el código de salida es 0 y que stderr contiene "se ignora" y "(solo .md y .txt)"; y borrar `tests/fixtures/prosa/comentarios.sql`
- [X] T003 [P] Editar la viñeta de `make lint-prosa` en la sección "Calidad" de `README.md` para que diga que revisa el README y la carpeta `docs/` (sin mencionar los `.sql`), en español y cumpliendo el principio IX
- [X] T004 [P] Crear `warehouse/__init__.py` con un docstring de una línea y las carpetas `sql/checks/`, `sql/ops/` y `tests/warehouse/` (sin `__init__.py` en `tests/warehouse/`, igual que `tests/generator/`)
- [X] T005 [P] Crear `tests/warehouse/conftest.py` con: la fixture `fake_bq`, un ejecutor falso que registra cada lista de argumentos recibida y devuelve `(returncode, stdout, stderr)` según reglas configurables por la prueba (por ejemplo, "si el argumento contiene `--dry_run` y el texto incluye `CREATE TABLE`, devuelve 1"), con una respuesta por defecto de éxito y salida vacía; y la fixture `warehouse_env`, que fija `BIGQUERYRC` al `.bigqueryrc` del repositorio, `PROJECT_ID=proyecto-prueba` y `BQ_JOB_LABELS="--label=project:farma-analytics --label=env:dev"` con `monkeypatch`, y antepone `tests/fixtures/stubs/bin` al `PATH` para que `check_environment()` encuentre el `bq` falso que ya usan las pruebas de `doctor.sh` (en CI no hay `bq` instalado); `fake_bq` sustituye `warehouse.bq.execute`, de modo que el stub nunca llega a ejecutarse
- [X] T006 Ejecutar `make test` y `make lint-prosa` y confirmar que pasan con T001 y T002 (depende de T001 y T002)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ejecución de `bq`, análisis de la DDL, contrato de resultados y verificación de
metadatos, que usan las tres historias técnicas.

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

### Pruebas (escribir primero, deben fallar)

- [X] T007 [P] Crear `tests/warehouse/test_bq.py`: (a) `check_environment()` sale con código 2 y un mensaje en español si `BIGQUERYRC` no existe o no es el mismo archivo que `<repo>/.bigqueryrc`, si falta `PROJECT_ID` o si `bq` no está en el `PATH`; (b) `dry_run_query(sql, params)` produce `["bq", "--project_id=proyecto-prueba", "query", "--dry_run", *params]` con `sql` en la entrada estándar (la referencia de `bq` pide quitar los comentarios si la consulta va como argumento, y la otra vía documentada es `bq query < query.sql`); (c) `run_query(sql, params, as_json=True, max_rows=1000)` produce `["bq", "--project_id=proyecto-prueba", "--format=json", "query", "--label=project:farma-analytics", "--label=env:dev", "--max_rows=1000", *params]` con `sql` en la entrada estándar con las labels leídas de `BQ_JOB_LABELS` (sin `max_rows` no se añade el flag); `estimated_bytes(stdout)` extrae el número de "running this query will process N bytes" de la salida de un dry run y devuelve `None` si no aparece; (d) `load_csv(table, csv_path, schema_path)` produce exactamente `["bq", "--project_id=proyecto-prueba", "load", "--replace", "--source_format=CSV", "--skip_leading_rows=1", "--autodetect=false", "--max_bad_records=0", "--encoding=UTF-8", "farma_analytics.<TABLA>", "<csv>", "<schema>"]`; (e) `show(ref)` produce `["bq", "--project_id=proyecto-prueba", "--format=json", "show", ref]`; (f) ningún comando contiene `--location`, `--use_legacy_sql` ni `--maximum_bytes_billed`; `--label` nunca aparece junto a `--dry_run` ni en `load`
- [X] T008 [P] Crear `tests/fixtures/sql/ddl_minima.sql` (ya excluido por `.sqlfluffignore`) con un `CREATE SCHEMA IF NOT EXISTS` con `location`, `description` y `labels`, dos `CREATE TABLE IF NOT EXISTS` con columnas `NOT NULL` y sin él, todas con `OPTIONS (description = ...)`, comentarios `--` y `/* */`, una descripción con coma y acentos, y una sentencia `SELECT` final que debe clasificarse como "otra"
- [X] T009 [P] Crear `tests/warehouse/test_ddl_parser.py` sobre `tests/fixtures/sql/ddl_minima.sql`: `parse_file(path)` devuelve las sentencias en orden con su tipo (`create_schema`, `create_table`, `other`) y su texto exacto sin el `;` final; `dataset_spec()` devuelve nombre, `location`, descripción y labels como dict; `table_specs()` devuelve nombre, descripción y columnas en orden con `name`, `type`, `mode` (`REQUIRED` si hay `NOT NULL`, si no `NULLABLE`) y `description` sin comillas; un archivo con SQL inválido lanza un error con el número de línea (depende de T008)
- [X] T010 [P] Crear `tests/warehouse/test_metadata.py`: `compare(dataset_spec, table_specs, show)` con `show` falso que devuelve el JSON de `bq show`: sin diferencias devuelve `[]`; `"type": "INTEGER"` equivale a `INT64`; un campo sin `mode` equivale a `NULLABLE`; informa con `CheckResult(CHEQUEO="esquema_ddl", ...)` una columna de más, una de menos, un orden distinto, un tipo, un modo o una descripción distinta, una descripción de tabla distinta, labels distintas y una `location` distinta (sin distinguir mayúsculas); si `bq show` sale con error y "not found" (sin distinguir mayúsculas) aparece en stdout o en stderr, para el dataset o una tabla, devuelve una diferencia cuyo `DETALLE` dice "Falta <objeto>: ejecuta 'make bq-schema'"; cualquier otro error de `bq show` devuelve una diferencia con el mensaje de `bq`

### Implementación

- [X] T011 Crear `warehouse/results.py` con `CheckResult` (`frozen` dataclass con `chequeo`, `objeto`, `detalle`, `esperado`, `obtenido`, todos `str`), `from_row(dict)` para filas JSON de `bq` con las claves `CHEQUEO`, `OBJETO`, `DETALLE`, `ESPERADO`, `OBTENIDO`, y `format_table(results)` que imprime una tabla de texto alineada (contrato de [contracts/checks.md](contracts/checks.md))
- [X] T012 Crear `warehouse/bq.py` con `check_environment()`, `dry_run_query`, `run_query`, `estimated_bytes`, `load_csv`, `show` y `execute(argv)` (la única llamada a `subprocess.run`, con `capture_output=True`, `text=True`, `check=False` y un `timeout` de 600 s), según [contracts/make-targets.md](contracts/make-targets.md) y la prueba T007. `PROJECT_ID` y `BQ_JOB_LABELS` se leen del entorno (depende de T007)
- [X] T013 Crear `warehouse/ddl.py` con `parse_file`, `dataset_spec` y `table_specs` usando la API avanzada `sqlfluff.core.Linter(dialect="bigquery").parse_string(sql)` y recorriendo los segmentos (`create_schema_statement`, `create_table_statement`, `column_definition`, `options_segment`; las hojas se identifican con `is_type`), con `DatasetSpec`, `TableSpec` y `ColumnSpec` como en [data-model.md](data-model.md). Las cadenas de `description` se devuelven sin comillas y con los escapes de GoogleSQL resueltos (depende de T009)
- [X] T014 Crear `warehouse/metadata.py` con `compare(...)` y `verify(dataset_spec, table_specs) -> list[CheckResult]`, que llama a `bq.show` para el dataset y cada tabla, busca "not found" en stdout y stderr juntos como hace `scripts/doctor.sh`, y aplica la comparación de [contracts/checks.md](contracts/checks.md#verificación-de-metadatos-fr-026-sin-consulta) (depende de T010, T011, T012 y T013)
- [X] T015 Ejecutar `make test` y `uv run ruff check warehouse tests/warehouse` y confirmar que T007, T009 y T010 pasan (depende de T012 a T014)

**Checkpoint**: base lista; las historias pueden empezar.

---

## Phase 3: User Story 1 - Crear el dataset y las tablas desde la DDL canónica (Priority: P1) 🎯 MVP

**Goal**: `make bq-schema` crea `farma_analytics` y las tres tablas desde las secciones 1 y 2 de
`sql/farma_analytics.sql`, con dry run antes de cada sentencia y verificación de metadatos al final.

**Independent Test**: en un proyecto sin el dataset, `make bq-schema` termina con "Metadatos: 0
diferencias con la DDL"; `bq show` muestra tipos, modos y descripciones; una segunda ejecución no
cambia nada; `make doctor` pasa B03 a OK (quickstart V1, V2 y V7).

### Pruebas (escribir primero, deben fallar)

- [X] T016 [P] [US1] Crear `tests/warehouse/test_ddl.py` con las reglas 1 a 8 de [contracts/ddl.md](contracts/ddl.md) sobre `sql/farma_analytics.sql`: exactamente un `CREATE SCHEMA` y luego tres `CREATE TABLE` (`COMPRAS`, `CLUE_CAT`, `CUADRO_BASICO`) antes de cualquier otra sentencia; en las sentencias `CREATE SCHEMA` y `CREATE TABLE` (según `warehouse.ddl.parse_file`, porque las secciones 3 y 4 tendrán `AS SELECT` en la vista y `PARTITION BY` en funciones de ventana), ausencia sin distinguir mayúsculas de `AS SELECT`, `PARTITION BY`, `CLUSTER BY`, `PRIMARY KEY`, `FOREIGN KEY`, `expiration_timestamp` y `default_table_expiration_days`; en todo el archivo y fuera de comentarios, ausencia de `OR REPLACE TABLE` y de cualquier referencia con tres partes `x.farma_analytics.y`; `location` igual al valor de `--location=` en `.bigqueryrc` sin distinguir mayúsculas; labels `project` y `env` iguales a las de la línea `BQ_LABELS :=` del `Makefile`, label `owner` presente, claves y valores en minúsculas; columnas, orden, tipos y modos exactamente iguales a las tablas de [data-model.md](data-model.md) y al orden de `generator.pipeline.HEADERS`; `NOT NULL` exactamente en `CLUE`, `CLAVE`, `COD_PROVEEDOR`, `FECHA`, `PIEZAS` e `IMPORTE` de cada tabla donde aparecen; `IMPORTE` es `NUMERIC` sin parámetros; dataset, tablas y columnas con `description` no vacía y sin `'` ni `;`
- [X] T017 [P] [US1] Crear `tests/warehouse/test_schema_command.py` con `fake_bq` y `warehouse_env`: `run_schema()` llama, para cada una de las 4 sentencias en orden, primero a `dry_run_query` y después a `run_query` con el mismo texto; si el dry run de la sentencia 3 falla, no ejecuta la 3 ni las siguientes, imprime "[3/4]" con el error de `bq` y devuelve 1; si una ejecución falla, devuelve 1; ignora las sentencias de tipo `other`; al final llama a `metadata.verify` y devuelve 1 si hay diferencias y 0 si no, imprimiendo "Metadatos: 0 diferencias con la DDL"

### Implementación

- [X] T018 [US1] Escribir `sql/farma_analytics.sql` (secciones 1 y 2) según [contracts/ddl.md](contracts/ddl.md) y [data-model.md](data-model.md): cabecera en inglés (propósito, que se ejecuta en la consola o con `make bq-schema`, datos sintéticos, lista de las cuatro secciones); "Section 1: dataset" con `CREATE SCHEMA IF NOT EXISTS farma_analytics OPTIONS (location = 'US', description = '<descripción del dataset de data-model>', labels = [('project', 'farma-analytics'), ('env', 'dev'), ('owner', 'bi')])`; "Section 2: tables" con un comentario de una línea (sin particionado ni clustering porque las tablas suman unos 32 MB; sin claves foráneas por los huérfanos deliberados) y `CREATE TABLE IF NOT EXISTS farma_analytics.COMPRAS`, `farma_analytics.CLUE_CAT` y `farma_analytics.CUADRO_BASICO`, en ese orden, con estas columnas literales: `COMPRAS` = `CLUE STRING NOT NULL`, `CLAVE STRING NOT NULL`, `COD_PROVEEDOR STRING NOT NULL`, `MARCA STRING`, `FABRICANTE STRING`, `PIEZAS INT64 NOT NULL`, `IMPORTE NUMERIC NOT NULL`, `FECHA DATE NOT NULL`; `CLUE_CAT` = `CLUE STRING NOT NULL`, `ENTIDAD STRING`, `INSTITUCION STRING`, `DELEGACION STRING`, `GRUPO_INSTITUCIONAL STRING`, `NIVEL_ATENCION STRING`, `MUNICIPIO STRING`; `CUADRO_BASICO` = `CLAVE STRING NOT NULL`, `DESCRIPCION STRING`, `MOLECULA STRING`, `GRUPO_TERAPEUTICO STRING`, `PRESENTACION STRING`, `FABRICANTE STRING`; cada columna con `OPTIONS (description = '...')` y cada tabla con `OPTIONS (description = '...')` con los textos de data-model (grano y llave). Antes de cada sentencia, un comentario breve en inglés dice qué es el objeto y para qué existe (por ejemplo, `-- Fact table at purchase-line grain, joined to both catalogs by the view.` o `-- Medical units catalog, one row per CLUE.`), sin repetir reglas de la constitución (depende de T016)
- [X] T019 [US1] Crear `warehouse/commands.py` con `run_schema() -> int` según [contracts/make-targets.md](contracts/make-targets.md#make-bq-schema--python--m-warehouse-schema): llama a `bq.check_environment()`, analiza `sql/farma_analytics.sql`, recorre las sentencias `create_schema` y `create_table` con dry run y ejecución, imprime "[i/n] <TIPO> <objeto>: dry run OK (<N> bytes estimados), ejecutada" con `bq.estimated_bytes` y termina con la verificación de metadatos (depende de T014, T017 y T018)
- [X] T020 [US1] Crear `warehouse/__main__.py` con `argparse` (`prog="python -m warehouse"`, descripción y ayuda en español) y el subcomando `schema` que llama a `commands.run_schema()`; `main()` devuelve el código de salida y el módulo termina con `raise SystemExit(main())` (depende de T019)
- [X] T021 [US1] Editar `Makefile`: añadir `bq-schema` a `.PHONY` y el objetivo `bq-schema: require-venv require-project ## Crea el dataset y las tablas desde sql/farma_analytics.sql (dry run antes de cada sentencia)` con la receta `@PROJECT_ID=$(PROJECT_ID) BQ_JOB_LABELS="$(BQ_LABELS)" uv run python -m warehouse schema`, junto a los objetivos `gcp-*` y sin tocar los existentes
- [X] T022 [US1] Ejecutar `git add` de los archivos nuevos y después `make test`, `make lint` y `make lint-sql`; corregir hasta que pasen (SQLFluff sin violaciones en `sql/farma_analytics.sql`) (depende de T018 a T021)
- [X] T023 [US1] [Dueño] Ejecutar los pasos V1 y V2 de [quickstart.md](quickstart.md) (`make doctor`, `make bq-schema`, `bq show --format=prettyjson farma_analytics.COMPRAS`) y compartir la salida (depende de T022)

**Checkpoint**: el dataset y las tablas existen con el esquema de la DDL.

---

## Phase 4: User Story 2 - Cargar los CSV de forma idempotente (Priority: P1)

**Goal**: `make bq-load` verifica `data/`, comprueba los metadatos, reemplaza cada tabla en un solo
job de carga con el esquema derivado de la DDL, vuelve a comprobar los metadatos e imprime la huella
de contenido.

**Independent Test**: dos ejecuciones seguidas de `make bq-load` imprimen 300000, 2000 y 161 filas y
las mismas huellas (quickstart V4 y V5).

### Pruebas (escribir primero, deben fallar)

- [X] T024 [P] [US2] Crear `tests/warehouse/test_schema_json.py`: `load_schema(table_spec)` devuelve para cada columna de `sql/farma_analytics.sql` un dict con exactamente las claves `name`, `type`, `mode` y `description`, en el orden de la DDL, con `type` igual al tipo de la DDL (`STRING`, `INT64`, `NUMERIC`, `DATE`) y `mode` `REQUIRED` o `NULLABLE`; `write_load_schemas(table_specs, directory)` escribe `<TABLA>.json` en UTF-8 con `ensure_ascii=False` y su contenido vuelve a cargarse igual
- [X] T025 [P] [US2] Crear `tests/warehouse/test_load_command.py` con `fake_bq`, `warehouse_env` y un directorio temporal con tres CSV de prueba y su manifiesto, pasados como `run_load(data_dir=..., manifest_path=...)`: si los CSV no coinciden con el manifiesto o falta alguno, `run_load` devuelve 1, imprime "ejecuta 'make data'" y no llama a `bq`; si la verificación de metadatos previa informa "Falta ...", `run_load` devuelve 1 y no llama a `bq load`; con metadatos correctos llama a `bq load` una vez por tabla en el orden de la DDL con `<data_dir>/<TABLA>.csv` y `<tmp>/<TABLA>.json`; si la carga de `CLUE_CAT` falla, devuelve 1, imprime la tabla y el error de `bq` y no carga `CUADRO_BASICO`; con las cargas terminadas ejecuta `sql/ops/huella_contenido.sql` con dry run y después con labels y `--format=json`, e imprime la tabla `TABLA FILAS HUELLA` (T042 añade los chequeos antes de la huella); el directorio temporal de esquemas ya no existe al terminar

### Implementación

- [X] T026 [US2] Añadir a `warehouse/ddl.py` las funciones `load_schema(table_spec)` y `write_load_schemas(table_specs, directory)` (research R4, [contracts/ddl.md](contracts/ddl.md#derivación-del-esquema-de-carga)) (depende de T024)
- [X] T027 [P] [US2] Escribir `sql/ops/huella_contenido.sql`: cabecera en inglés (huella por tabla para comparar dos cargas, no es un chequeo) y un `SELECT` por tabla unido con `UNION ALL`, con `'COMPRAS' AS TABLA`, `COUNT(*) AS FILAS` y `SUM(CAST(FARM_FINGERPRINT(TO_JSON_STRING(compras)) AS BIGNUMERIC)) AS HUELLA` desde `farma_analytics.COMPRAS AS compras`, y lo mismo con `clue_cat` y `cuadro_basico` (research R10)
- [X] T028 [US2] Añadir a `warehouse/commands.py` la función `run_load(repo_root: Path = REPO_ROOT, data_dir: Path | None = None, manifest_path: Path | None = None) -> int` (por defecto `<repo>/data` y `<repo>/generator/manifest.json`) según [contracts/make-targets.md](contracts/make-targets.md#make-bq-load--python--m-warehouse-load): entorno; verificación de los CSV con `generator.manifest.verify(manifest_path, data_dir)` antes de cualquier llamada a `bq`, que si falla imprime las diferencias y "Los CSV no coinciden con el manifiesto: ejecuta 'make data'." y devuelve 1 (FR-011, aunque se ejecute sin `make`); análisis de la DDL; metadatos previos; esquemas en un `tempfile.TemporaryDirectory`; `bq load` por tabla; y huella. No repite aquí la verificación de metadatos posterior a la carga, porque `run_checks` (T042) empieza por ella. Crear en este paso `warehouse/checks.py` con `run_fingerprint()` (dry run con bytes estimados, ejecución con labels y `--format=json`, impresión de `TABLA FILAS HUELLA`) y llamarla desde `run_load`. Deja un punto marcado para llamar a los chequeos, que se conecta en T042 (depende de T025, T026 y T027)
- [X] T029 [US2] Añadir el subcomando `load` a `warehouse/__main__.py` y el objetivo `bq-load: require-venv require-project ## Verifica data/, carga los CSV en BigQuery y ejecuta los chequeos` a `Makefile` (con `bq-load` en `.PHONY` y la misma receta que `bq-schema` con `load`). No depende de `data-verify` porque `run_load` ya verifica los CSV contra el manifiesto (T028) y así no se calculan dos veces las huellas (depende de T028)
- [X] T030 [US2] Ejecutar `git add` y después `make test`, `make lint` y `make lint-sql` hasta que pasen (depende de T026 a T029)

**Checkpoint**: la carga es repetible y comprobable con la huella; faltan los chequeos.

---

## Phase 5: User Story 3 - Verificar la calidad después de cada carga (Priority: P2)

**Goal**: seis chequeos del principio IV en `sql/checks/`, con parámetros desde el manifiesto y la
configuración, que corren con `make bq-checks` y al final de cada `make bq-load`.

**Independent Test**: con tablas vacías, `make bq-checks` falla en `conteo_filas` (tres filas) y en
`reconciliacion_join` (huérfanos de `CLUE` y de `CLAVE` en 0 frente a 750) y deja los demás en OK
(V3); con las tablas cargadas, los seis chequeos y los metadatos quedan en 0 (V4).

### Pruebas (escribir primero, deben fallar)

- [X] T031 [P] [US3] Crear `tests/warehouse/test_expectations.py`: `load_expectations(config_path=CONFIG_PATH, manifest_path=MANIFEST_PATH)` (por defecto `generator/config.toml` y `generator/manifest.json`) los lee (con `generator.config.load_config(path, generator.reference.load_reference())`) y devuelve exactamente: `filas_compras` 300000, `filas_clue_cat` 2000, `filas_cuadro_basico` 161, `huerfanos_clue` 750, `huerfanos_clave` 750 (`INT64`); `fecha_inicio` 2024-01-01 y `fecha_fin` 2025-12-31 (`DATE`); `precio_minimo` `Decimal("6.75")`, `precio_maximo` `Decimal("17820")` y `dispersion_maxima` `Decimal("4.4")` (`NUMERIC`), calculados con `Decimal` según research R9 y con la dispersión redondeada hacia arriba a 6 decimales; `as_bq_parameters(names)` devuelve, solo para los nombres pedidos, cadenas `--parameter=filas_compras:INT64:300000`, `--parameter=fecha_inicio:DATE:2024-01-01`, `--parameter=precio_minimo:NUMERIC:6.75`; con una configuración de prueba distinta (copia temporal con `ruido_max = 0.20`) los umbrales cambian según la fórmula
- [X] T032 [P] [US3] Crear `tests/warehouse/test_checks_sql.py`: existen exactamente `sql/checks/01_conteo_filas.sql`, `02_unicidad_claves.sql`, `03_nulos.sql`, `04_dominios.sql`, `05_reconciliacion_join.sql` y `06_precio_unitario.sql`; cada uno empieza con un comentario `--`; `referenced_parameters(sql)` (regex `@([a-z_]+)` fuera de comentarios y cadenas) devuelve solo nombres que `load_expectations()` provee, y cada archivo usa los parámetros de la tabla de [contracts/checks.md](contracts/checks.md); ningún archivo contiene `SELECT *` ni una referencia de tres partes; cada `SELECT` final proyecta las columnas `CHEQUEO`, `OBJETO`, `DETALLE`, `ESPERADO` y `OBTENIDO`
- [X] T033 [P] [US3] Crear `tests/warehouse/test_checks_command.py` con `fake_bq` y `warehouse_env`: `run_checks()` verifica primero los metadatos; para cada archivo de `sql/checks/` en orden de nombre llama a `dry_run_query` y después a `run_query(as_json=True, max_rows=1000)` con el mismo texto y solo sus parámetros; una respuesta de 1000 filas se informa como "1000 o más"; una respuesta `[]` cuenta como OK; una respuesta con filas imprime `FALLO` con la tabla de `format_table` y hace que la función devuelva 1 aunque siga con los demás chequeos; un dry run fallido devuelve 1 sin ejecutar ese chequeo; con todo en orden imprime "Chequeos: 6 de 6 en 0 filas. Metadatos: 0 diferencias." y devuelve 0

### Implementación

- [X] T034 [US3] Crear `warehouse/expectations.py` con `load_expectations(config_path: Path = CONFIG_PATH, manifest_path: Path = MANIFEST_PATH)` y `as_bq_parameters(names)` según la tabla `Expectations` de [data-model.md](data-model.md#expectations-cifras-esperadas) y research R9, reutilizando `generator.config.load_config`, `generator.reference.load_reference` y `generator.manifest.load` (depende de T031)
- [X] T035 [P] [US3] Escribir `sql/checks/01_conteo_filas.sql`: cabecera en inglés con la regla; `SELECT` sobre `UNNEST([STRUCT(...), ...]) AS conteos` con una estructura por tabla (`'COMPRAS'` con `@filas_compras` y `(SELECT COUNT(*) FROM farma_analytics.COMPRAS AS compras)`, ídem `CLUE_CAT AS clue_cat` con `@filas_clue_cat` y `CUADRO_BASICO AS cuadro_basico` con `@filas_cuadro_basico`), que proyecta `'conteo_filas' AS CHEQUEO`, `OBJETO`, `'filas' AS DETALLE`, `CAST(... AS STRING) AS ESPERADO` y `OBTENIDO`, filtrando `WHERE` esperado `!=` obtenido
- [X] T036 [P] [US3] Escribir `sql/checks/02_unicidad_claves.sql`: dos `SELECT` unidos con `UNION ALL`, uno sobre `farma_analytics.CLUE_CAT AS clue_cat` con `GROUP BY clue_cat.CLUE HAVING COUNT(*) > 1` y otro sobre `farma_analytics.CUADRO_BASICO AS cuadro_basico` con `GROUP BY cuadro_basico.CLAVE HAVING COUNT(*) > 1`; proyectan `'unicidad_claves' AS CHEQUEO`, `'CLUE_CAT.CLUE'` o `'CUADRO_BASICO.CLAVE' AS OBJETO`, la llave repetida en `DETALLE`, `'1' AS ESPERADO` y `CAST(COUNT(*) AS STRING) AS OBTENIDO`
- [X] T037 [P] [US3] Escribir `sql/checks/03_nulos.sql`: una CTE `nulos_por_columna` de una sola fila cuyas columnas son conteos `COUNTIF(<col> IS NULL)`, tomados con subconsultas escalares de una tabla cada una (`(SELECT COUNTIF(compras.CLUE IS NULL) FROM farma_analytics.COMPRAS AS compras) AS COMPRAS_CLUE`, y así `COMPRAS_CLAVE`, `COMPRAS_COD_PROVEEDOR`, `COMPRAS_PIEZAS`, `COMPRAS_IMPORTE`, `COMPRAS_FECHA`, `CLUE_CAT_CLUE` y `CUADRO_BASICO_CLAVE`), sin joins; una CTE que la pasa a filas con `UNPIVOT (NULOS FOR OBJETO IN (...))`; y un `SELECT` final que devuelve las filas con `NULOS > 0`, con `'nulos' AS CHEQUEO`, `OBJETO` en forma `TABLA.COLUMNA` gracias al alias de cadena de cada columna dentro del `IN` (por ejemplo `COMPRAS_CLUE AS 'COMPRAS.CLUE'`), `'nulos' AS DETALLE`, `'0' AS ESPERADO` y `CAST(NULOS AS STRING) AS OBTENIDO`
- [X] T038 [P] [US3] Escribir `sql/checks/04_dominios.sql`: una CTE sobre `farma_analytics.COMPRAS AS compras` con `COUNTIF(compras.PIEZAS <= 0)`, `COUNTIF(compras.IMPORTE < 0)`, `COUNTIF(compras.FECHA < @fecha_inicio OR compras.FECHA > @fecha_fin)`, `MIN` y `MAX` de cada columna; una segunda CTE pasa a filas los tres conteos de violaciones con `UNPIVOT`, como en T037 (sin `UNNEST` ni joins), y el `SELECT` final filtra sobre la columna que produce `UNPIVOT` (nunca sobre alias del `SELECT`); devuelve una fila por dominio violado con `'dominios' AS CHEQUEO`, `'COMPRAS.PIEZAS'`, `'COMPRAS.IMPORTE'` o `'COMPRAS.FECHA' AS OBJETO`, `DETALLE` con la regla (`PIEZAS > 0`, `IMPORTE >= 0`, `FECHA entre @fecha_inicio y @fecha_fin`), `ESPERADO` con la cota y `OBTENIDO` con el número de filas fuera de dominio y el mínimo o máximo encontrado
- [X] T039 [P] [US3] Escribir `sql/checks/05_reconciliacion_join.sql` (research R7, [contracts/checks.md](contracts/checks.md)): CTE `totales_compras` (`COUNT(*)`, `SUM(compras.IMPORTE)`), CTE `union_interna` con `COMPRAS` `INNER JOIN farma_analytics.CLUE_CAT AS clue_cat ON compras.CLUE = clue_cat.CLUE` `INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico ON compras.CLAVE = cuadro_basico.CLAVE` (filas e importe), CTE `marcas_huerfanas` sobre `farma_analytics.COMPRAS AS compras`, sin joins, con `compras.IMPORTE`, `NOT EXISTS (SELECT 1 FROM farma_analytics.CLUE_CAT AS clue_cat WHERE clue_cat.CLUE = compras.CLUE) AS SIN_CLUE` y `NOT EXISTS (SELECT 1 FROM farma_analytics.CUADRO_BASICO AS cuadro_basico WHERE cuadro_basico.CLAVE = compras.CLAVE) AS SIN_CLAVE`; CTE `filas_huerfanas` con `COUNTIF(SIN_CLUE OR SIN_CLAVE)`, `SUM(IF(SIN_CLUE OR SIN_CLAVE, IMPORTE, 0))`, `COUNTIF(SIN_CLUE)` y `COUNTIF(SIN_CLAVE)`; los cuadres se pasan a filas con `UNPIVOT` o con `UNION ALL` de `SELECT` sobre las CTE de una fila, sin joins; un `SELECT` final que devuelve una fila por cuadre incumplido: filas totales = internas + huérfanas, importe total = interno + huérfano (igualdad exacta en `NUMERIC`), huérfanos de `CLUE` = `@huerfanos_clue` y de `CLAVE` = `@huerfanos_clave`
- [X] T040 [P] [US3] Escribir `sql/checks/06_precio_unitario.sql` (research R9): CTE `precios_por_clave` con `compras.CLAVE`, `MIN(SAFE_DIVIDE(compras.IMPORTE, compras.PIEZAS)) AS PRECIO_MINIMO` y `MAX(...) AS PRECIO_MAXIMO` desde `COMPRAS` `INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico ON compras.CLAVE = cuadro_basico.CLAVE`, `GROUP BY compras.CLAVE`; `SELECT` final con una fila por clave que incumple `PRECIO_MINIMO >= @precio_minimo - 0.01`, `PRECIO_MAXIMO <= @precio_maximo + 0.01` o `PRECIO_MAXIMO <= @dispersion_maxima * (PRECIO_MINIMO + 0.01) + 0.01` (literales `NUMERIC '0.01'` con un comentario "one cent rounding margin"), con `'precio_unitario' AS CHEQUEO`, `'CUADRO_BASICO.CLAVE'` como `OBJETO` y la clave y la regla en `DETALLE`
- [X] T041 [US3] Añadir a `warehouse/checks.py` (creado en T028) `referenced_parameters(sql)` y `run_sql_checks(expectations) -> tuple[int, list[CheckResult]]`: archivos de `sql/checks/` en orden de nombre; dry run con bytes estimados impresos; ejecución con `as_json=True`, `max_rows=1000` y solo sus parámetros. Si un chequeo devuelve 1000 filas, el resumen dice "1000 o más" porque la salida de `bq` se recorta en `--max_rows` (depende de T032 a T040)
- [X] T042 [US3] Añadir a `warehouse/commands.py` la función `run_checks() -> int` (metadatos más chequeos SQL, resumen "Chequeos: N de 6 en 0 filas. Metadatos: M diferencias.") y conectar `run_checks` dentro de `run_load` justo después de las cargas y antes de la huella, como pide FR-015 (`run_checks` empieza por la verificación de metadatos, que hace de verificación posterior a la carga). Si `run_checks` devuelve 1, `run_load` devuelve 1 sin calcular la huella. Actualizar `tests/warehouse/test_load_command.py` para comprobar ese orden y que no hay huella cuando un chequeo falla (depende de T033 y T041)
- [X] T043 [US3] Añadir el subcomando `checks` a `warehouse/__main__.py` y el objetivo `bq-checks: require-venv require-project ## Ejecuta los chequeos de calidad sobre las tablas cargadas` a `Makefile` (en `.PHONY`, misma receta con `checks`) (depende de T042)
- [X] T044 [US3] Ejecutar `git add` y después `make test`, `make lint` y `make lint-sql` hasta que pasen; si SQLFluff marca sangría en los `UNNEST`, corregir con `uv run sqlfluff fix` sobre el archivo y revisar el diff (depende de T034 a T043)

#### Casos negativos (FR-033, research R15)

- [X] T045 [P] [US3] Crear seis archivos en `sql/checks/negativos/`, uno por chequeo y con el mismo nombre base (`01_conteo_filas.json` ... `06_precio_unitario.json`), en UTF-8 y con este formato: `{"esperado": {"CHEQUEO": "<nombre>", "OBJETO": "<objeto>"}, "tablas": {"COMPRAS": [...], "CLUE_CAT": [...], "CUADRO_BASICO": [...]}}`, donde cada fila es un objeto con todas las columnas de la tabla y valores como cadenas JSON (`null` para nulo). Cada caso trae unas pocas filas válidas y un solo error a propósito: `01_conteo_filas` 2 filas en `COMPRAS` (esperado `OBJETO` `COMPRAS`); `02_unicidad_claves` una `CLUE` repetida en `CLUE_CAT` (`CLUE_CAT.CLUE`); `03_nulos` una fila de `COMPRAS` con `CLUE` nula (`COMPRAS.CLUE`); `04_dominios` una fila con `PIEZAS` 0 (`COMPRAS.PIEZAS`); `05_reconciliacion_join` una fila de `COMPRAS` con una `CLUE` que no está en `CLUE_CAT` (`COMPRAS`); `06_precio_unitario` una `CLAVE` del catálogo con dos filas a 10.00 y a 100.00 pesos por pieza, que supera la dispersión de 4.4 (`CUADRO_BASICO.CLAVE`). Los datos son inventados y con el formato de los CSV del generador
- [X] T046 [P] [US3] Crear `tests/warehouse/test_negative_checks.py`: (a) hay un caso por cada archivo de `sql/checks/` y viceversa, y cada caso tiene todas las columnas de las tres tablas según la DDL; (b) `inline_tables(sql, case, table_specs)` sustituye cada `farma_analytics.<TABLA> AS <alias>` por `(SELECT <columnas en orden> FROM UNNEST(ARRAY<STRUCT<CLUE STRING, ...>>[...])) AS <alias>`, con los tipos de la DDL y `CAST` explícito de cada valor (`CAST('2024-01-02' AS DATE)`, `CAST('5341.60' AS NUMERIC)`, `NULL` tipado), y el resultado ya no contiene `farma_analytics.`; una tabla vacía en el caso produce un `ARRAY` vacío tipado; (c) con `fake_bq`, `run_negative_checks()` hace dry run y ejecución con labels, `as_json=True` y solo los parámetros de cada chequeo, devuelve 0 si cada chequeo devuelve al menos una fila con el `CHEQUEO` y el `OBJETO` esperados, y 1 si alguno devuelve `[]` o no incluye ese objeto, nombrándolo en la salida
- [X] T047 [US3] Añadir a `warehouse/checks.py` `load_negative_case(path)`, `inline_tables(sql, case, table_specs)` y `run_negative_checks(expectations, table_specs) -> int`: lee cada archivo de `sql/checks/` y su caso de `sql/checks/negativos/`, sustituye las tablas por los datos en línea (solo en memoria; los `.sql` versionados no cambian), imprime los bytes estimados del dry run (deben ser 0) y el resultado por chequeo ("detectó el error" o "NO detectó el error") y termina con "Casos negativos: N de 6 detectados." (depende de T045, T046 y T041)
- [X] T048 [US3] Añadir a `warehouse/commands.py` la función `run_negative_checks_command() -> int` (entorno, DDL y expectativas; no verifica metadatos porque no lee tablas), el subcomando `checks-negativos` a `warehouse/__main__.py` y el objetivo `bq-checks-negativos: require-venv require-project ## Comprueba que cada chequeo detecta su caso negativo (0 bytes facturados)` a `Makefile`, en `.PHONY` y con la misma receta que los otros objetivos `bq-*` (depende de T047)
- [X] T049 [US3] Ejecutar `git add` y después `make test`, `make lint` y `make lint-sql` hasta que pasen (depende de T045 a T048)

**Checkpoint**: carga y calidad completas; falta la documentación.

---

## Phase 6: User Story 4 - Seguir el recorrido documentado (Priority: P3)

**Goal**: el README explica la fase de carga y la matriz de trazabilidad cubre la Fase 1.

**Independent Test**: seguir el README desde un clon limpio lleva a las tablas cargadas y los
chequeos en 0 sin pasos no escritos; `make lint-prosa` no marca nada.

- [X] T050 [P] [US4] Añadir a `README.md` una sección "Carga en BigQuery" después de "Datos sintéticos", en español y cumpliendo el principio IX: el recorrido con un comando por etapa (`make data`, `make bq-schema`, `make bq-load`, `make bq-checks`) en lista numerada; qué ejecuta solo quien tiene acceso al proyecto de GCP; qué hace cada objetivo y la salida esperada; que `sql/farma_analytics.sql` es la única definición del esquema y que el esquema de la carga se deriva de ella; que cada consulta pasa por un dry run y lleva labels y que los jobs de carga no admiten ni lo uno ni lo otro; que la recarga reemplaza cada tabla en un job atómico; por qué no hay particionado, clustering ni claves foráneas; qué hace cada chequeo y de dónde salen sus cifras; qué hace `make bq-checks-negativos` (cada chequeo frente a un error preparado a propósito, sin leer tablas ni facturar bytes) y cuándo conviene ejecutarlo (después de cambiar un chequeo); cómo corregir una descripción cambiada después de crear la tabla; y que `make bq-load` solo se repite cuando cambian los datos, porque cada recarga reescribe las tablas y reinicia los 90 días que BigQuery espera para pasarlas a almacenamiento de largo plazo (la segunda carga de validación es la excepción). Si "Arranque rápido" enumera los pasos del proyecto, añadir los objetivos nuevos
- [X] T051 [P] [US4] Añadir a `docs/trazabilidad.md` una sección "Fase 1: carga en BigQuery" con filas para: crear el dataset `farma_analytics`; cargar `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` con sus campos; `FECHA` como `DATE` y `PIEZAS` e `IMPORTE` numéricos; tipos estrictos y `NOT NULL`; descripciones; chequeos de calidad y sus casos negativos; recarga idempotente. Cada fila con el artefacto (`sql/farma_analytics.sql`, `sql/checks/...`, `sql/checks/negativos/...`, `make bq-load`) y la verificación (`tests/warehouse/test_ddl.py`, quickstart V2 a V5, `make bq-checks`, `make bq-checks-negativos`)
- [X] T052 [US4] Ejecutar `make lint-prosa` y corregir el README y la trazabilidad hasta que no haya marcas (depende de T050 y T051)

**Checkpoint**: todas las historias completas en el repositorio.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T053 Quitar el comentario HTML "Sync Impact Report" del principio de `.specify/memory/constitution.md` (es material temporal de revisión y no se versiona), dejando la versión 1.3.0 y la fecha 2026-10-08 en el pie
- [X] T054 [P] Buscar en todos los archivos modificados o nuevos (`git diff --name-only main` y los no versionados) menciones del documento de requisitos de origen, del ID del proyecto de GCP, de correos y de credenciales, y quitarlas si aparecen
- [X] T055 Ejecutar `git add` de todo y después `make test`, `make lint`, `make lint-sql` y `make lint-prosa`; las cuatro deben terminar sin errores (depende de T053 y T054)
- [X] T056 [Dueño] Ejecutar en orden los pasos V3, V3b, V4, V5, V6, V7 y V8 de [quickstart.md](quickstart.md) (`make bq-checks` con tablas vacías, `make bq-checks-negativos`, dos veces `make bq-load`, `make bq-schema` y `make bq-checks` sobre tablas cargadas, `make doctor` y las secciones 1 y 2 en la consola) y compartir la salida. La primera carga de V4 se ejecuta como `time make bq-load` para medir SC-006 junto con los bytes estimados que imprime cada dry run. En V4 se revisa en concreto que la verificación de metadatos posterior a la carga no informa la descripción de tabla: si `--replace` la borrara, se aplica la contingencia de research R5 (reaplicar la descripción con `ALTER TABLE ... SET OPTIONS` en una consulta con dry run y labels después de cada carga) y se añaden sus pruebas antes de seguir. Si algo no coincide con lo esperado, se corrige antes del commit (depende de T055 y T023)
- [X] T057 Marcar las tareas hechas en este archivo, revisar que SC-001 a SC-007 de la spec se cumplen con la salida de T056 y redactar el mensaje de commit (Conventional Commits, cuerpo en español) y la descripción del PR; pasarlos por `scripts/lint_prosa.sh -` y enseñárselos al dueño. Solo con su visto bueno, hacer commit y push de la rama, sin abrir todavía el PR (depende de T056)
- [ ] T058 [Dueño] Comprobar SC-008 en un clon limpio de la rama ya publicada: `git clone --branch 003-bigquery-data-load <url del repositorio>` en un directorio temporal, seguir solo el README (`make setup-dev`, `make data`, `make bq-schema`, `make bq-checks`, `make bq-checks-negativos` y `make doctor`) y confirmar que `make data` reproduce el manifiesto, que `make bq-schema` termina sin cambios, que los chequeos siguen en 0 sobre las tablas ya cargadas, que los seis casos negativos se detectan y que `make doctor` da 24 OK. `make bq-load` no se repite aquí para no reescribir las tablas sin necesidad. Cubre también la validación V2 pendiente de la feature 002. Si falla, se corrige con un commit nuevo en la rama (depende de T057)
- [ ] T059 Abrir el PR hacia `main` con la descripción aprobada en T057, vincularlo y revisar su CI; el merge con squash lo hace el dueño (depende de T058)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de US1 (necesita la DDL y el dataset creado).
- **US3 (Phase 5)**: depende de US1 para los metadatos y la DDL, y de US2 para conectar los
  chequeos dentro de la carga (T042) y para su prueba completa con datos (V4). Los casos negativos
  (T045 a T049) solo dependen de los chequeos SQL y no necesitan datos cargados.
- **US4 (Phase 6)**: depende de US1 a US3 porque documenta su comportamiento final.
- **Polish (Phase 7)**: depende de todo lo anterior. T056 necesita que el dueño ya haya hecho T023;
  T058 necesita la rama publicada en T057 y las tablas cargadas de T056; el PR (T059) se abre al
  final.

### User Story Dependencies

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> US4 -> Polish
                              \______________/
                     (US3 se puede escribir en paralelo con US2;
                      solo T042 espera a T028)
```

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- Datos y SQL antes que la orquestación, la orquestación antes que `__main__` y el `Makefile`.
- Cada historia termina con `git add` y la batería local (`make test`, `make lint`, `make lint-sql`).

### Parallel Opportunities

- Setup: T001, T002, T003, T004 y T005 tocan archivos distintos.
- Foundational: T007, T008, T009 y T010 (pruebas) en paralelo; luego T011, T012 y T013 en paralelo y
  T014 al final.
- US1: T016 y T017 en paralelo.
- US2: T024, T025 y T027 en paralelo.
- US3: T031, T032 y T033 en paralelo; los seis SQL (T035 a T040) en paralelo entre sí y con T034;
  T045 y T046 en paralelo.
- US4: T050 y T051 en paralelo.

## Parallel Example: User Story 3

```text
# Pruebas de la historia, juntas:
T031 tests/warehouse/test_expectations.py
T032 tests/warehouse/test_checks_sql.py
T033 tests/warehouse/test_checks_command.py

# Los seis chequeos, juntos:
T035 sql/checks/01_conteo_filas.sql
T036 sql/checks/02_unicidad_claves.sql
T037 sql/checks/03_nulos.sql
T038 sql/checks/04_dominios.sql
T039 sql/checks/05_reconciliacion_join.sql
T040 sql/checks/06_precio_unitario.sql
```

## Implementation Strategy

### MVP First (User Story 1)

1. Setup y Foundational.
2. US1: DDL, `make bq-schema` y pruebas.
3. Parar y validar: el dueño ejecuta V1 y V2 (T023). Con eso el entregable `.sql` ya tiene sus dos
   primeras secciones probadas en BigQuery.

### Incremental Delivery

1. US2 añade la carga con huella (las tablas tienen datos).
2. US3 añade los chequeos y los conecta a la carga.
3. US4 documenta el recorrido.
4. Polish: lint completo, validación V3 a V8 y del clon limpio por el dueño, textos de commit y PR
   aprobados.

Todo entra en un solo PR con squash merge, que hace el dueño.

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Las tareas [Dueño] tocan GCP: Claude entrega el comando exacto con la explicación de cada flag y
  la salida esperada, y espera la salida del dueño.
- Si una tarea descubre un conflicto con la documentación oficial o con la constitución, se detiene
  y se presenta con opciones antes de seguir.
