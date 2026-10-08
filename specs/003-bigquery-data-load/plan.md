# Implementation Plan: Carga de datos en BigQuery (esquema, carga idempotente y chequeos de calidad)

**Branch**: `003-bigquery-data-load` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-bigquery-data-load/spec.md`

## Summary

La feature crea en BigQuery el dataset `farma_analytics` y las tablas `COMPRAS`, `CLUE_CAT` y
`CUADRO_BASICO` desde las secciones 1 y 2 de `sql/farma_analytics.sql`, carga los CSV de `make data`
y comprueba la calidad después de cada carga. El enfoque:

- DDL estática y ejecutable en la consola: `CREATE SCHEMA IF NOT EXISTS` con `location = 'US'`,
  descripción y labels, y `CREATE TABLE IF NOT EXISTS` con tipos estrictos, `NOT NULL` en las
  columnas obligatorias y descripción en cada tabla y columna (research R1 y R2);
- un paquete `warehouse/` en Python que analiza la DDL con SQLFluff, ejecuta cada sentencia después
  de su dry run y deriva de ella el esquema JSON de la carga (R3, R4 y R11);
- recarga atómica con `bq load --replace` por tabla, esquema explícito, sin autodetección, una fila
  de encabezado y cero filas malas (R5);
- dry run, labels y `maximum_bytes_billed` en todos los jobs de consulta y validación local antes de
  la carga, según la constitución v1.3.0 (R6);
- seis chequeos del principio IV en `sql/checks/`, con un contrato de salida común y las cifras
  esperadas como parámetros leídos del manifiesto y de la configuración del generador (R7 y R9);
- una verificación de metadatos con `bq show` que compara el esquema publicado con la DDL (R8) y una
  huella de contenido para demostrar que la segunda carga deja las tablas iguales (R10);
- un caso negativo por chequeo en `sql/checks/negativos/`, que se ejecuta con los datos en línea en
  lugar de las tablas para demostrar que cada chequeo detecta su error, sin facturar bytes (R15);
- objetivos `make bq-schema`, `make bq-load`, `make bq-checks` y `make bq-checks-negativos`, pruebas
  pytest sin GCP, README y
  matriz de trazabilidad.

Las decisiones y sus fuentes oficiales están en [research.md](research.md).

## Technical Context

**Language/Version**: GoogleSQL (BigQuery) para la DDL, los chequeos y la huella. Python 3.12.14
(`.python-version`) con uv para el programa `warehouse`. GNU Make 3.81.

**Primary Dependencies**: `bq` (Google Cloud SDK 588, ya validado por `make doctor`). Biblioteca
estándar de Python (`argparse`, `subprocess`, `json`, `tomllib`, `tempfile`, `decimal`, `dataclasses`).
SQLFluff 4.3.0, ya fijado en el grupo `dev`, como analizador de la DDL. Reutiliza
`generator.config.load_config`, `generator.reference.load_reference`, `generator.manifest.load`,
`generator.manifest.verify` y `generator.pipeline.HEADERS`. Sin
dependencias nuevas.

**Storage**: BigQuery, dataset `farma_analytics` en `US`, tres tablas nativas sin particionar ni
clusterizar (unos 32 MB). Entrada local: `data/*.csv` (ignorado por git) y `generator/manifest.json`.

**Testing**: pytest en `tests/warehouse/` (`make test` y job `tests` de CI), sin red ni credenciales,
con un ejecutor falso de `bq` (research R14). SQLFluff en pre-commit para `sql/`. Validación contra
BigQuery con [quickstart.md](quickstart.md), que ejecuta el dueño.

**Target Platform**: macOS del dueño para los objetivos que tocan GCP. Linux (`ubuntu-latest`) para
las pruebas en CI.

**Project Type**: SQL entregable más una herramienta de línea de comandos dentro del repositorio
(`[tool.uv] package = false`).

**Performance Goals**: esquema, carga y chequeos completos en menos de 10 minutos (SC-006). La
carga de unos 32 MB desde la máquina local domina el tiempo.

**Constraints**:

- ningún comando repite los flags de `.bigqueryrc`; `BIGQUERYRC` apunta al archivo del repositorio;
- dry run antes de cada job de consulta y labels estáticas en cada uno; los jobs de carga van sin
  dry run ni labels (constitución v1.3.0);
- ninguna consulta supera 1 GiB facturado (`maximum_bytes_billed`); los chequeos leen como máximo las
  columnas de `COMPRAS`;
- nada de `CREATE OR REPLACE TABLE`, CTAS, particionado, clustering, claves foráneas, expiración ni ID
  de proyecto en el SQL;
- comentarios de código en inglés; descripciones y documentación para lectores en español
  (principio IX);
- ningún texto versionado menciona el documento de requisitos de origen.

**Scale/Scope**: 300 000 filas en `COMPRAS`, 2 000 en `CLUE_CAT` y 161 en `CUADRO_BASICO`. Cuatro
sentencias DDL, tres cargas, seis consultas de chequeo, una de huella y una verificación de
metadatos por ejecución, más seis consultas de casos negativos (0 bytes) cuando se piden.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Antes de la investigación

| Puerta | Estado | Evidencia |
|---|---|---|
| G1 Contrato | PASA | Nombres exactos `farma_analytics`, `COMPRAS`, `CLUE_CAT`, `CUADRO_BASICO`; campos exactos de los requisitos (FR-003); `FECHA DATE`, `PIEZAS` e `IMPORTE` numéricos (Fase 1). La matriz de trazabilidad se amplía con la Fase 1 (FR-029). |
| G2 SQL | PASA | Tipos del principio II (FR-004), `NOT NULL` (FR-005), esquema explícito sin autodetección (FR-012), semántica `IF NOT EXISTS` elegida a propósito (FR-010), dry run en consultas (FR-016), SQLFluff (FR-028), sin particionado ni clustering como adorno (FR-007). |
| G3 Modelado | PASA | Grano y llave por tabla declarados antes de crearla (FR-006, data-model); sin claves foráneas por los huérfanos (FR-008). La vista queda para la feature siguiente. |
| G4 Calidad | PASA | Las seis reglas del principio IV con implementación canónica en `sql/checks/`, ejecutadas después de cada carga (FR-015, FR-018 a FR-025). |
| G5 Datos | PASA | Los CSV salen de `make data` y se verifican contra el manifiesto antes de cargar (FR-011). La descripción del dataset declara que los datos son sintéticos. |
| G6 Dashboard | N/A | Fuera de alcance. |
| G7 Negocio | N/A | Fuera de alcance. |
| G8 Simplicidad y seguridad | PASA con justificación | Sin herramientas nuevas: `bq`, Python, uv y SQLFluff ya están en el stack. Se aparta del SHOULD de Dataform para la calidad (ver Complexity Tracking). Sin ID de proyecto ni credenciales versionadas (FR-031). |
| G9 Escritura | PASA | README y trazabilidad en español con `make lint-prosa`; comentarios SQL en inglés según la v1.3.0 (FR-030, FR-032). |

### Después del diseño (Fase 1)

| Puerta | Estado | Evidencia del diseño |
|---|---|---|
| G1 Contrato | PASA | [data-model.md](data-model.md) fija columnas, orden y tipos; [contracts/ddl.md](contracts/ddl.md) los convierte en pruebas (reglas 5 a 7) y añade el orden de `generator.pipeline.HEADERS`. |
| G2 SQL | PASA | Location validada por BigQuery y por prueba (R1); `IF NOT EXISTS` sin `OR REPLACE` (R2); dry run por sentencia (R3); esquema de carga derivado de la DDL, sin segunda definición versionada (R4); `SAFE_DIVIDE`, `CAST` explícito, alias semánticos, `INNER JOIN ... ON` con `COMPRAS` primero y sin `SELECT *` en los chequeos ([contracts/checks.md](contracts/checks.md)); `LIMIT` no se usa como control de costo. |
| G3 Modelado | PASA | Descripciones con grano y llave en cada tabla; unicidad comprobada por chequeo porque BigQuery no impone claves; reconciliación del `INNER JOIN` lista para que la vista la reutilice. |
| G4 Calidad | PASA | Seis chequeos con contrato común y un caso negativo cada uno que prueba que detectan su error (R15), parámetros desde el manifiesto y la configuración (sin cifras fijas), umbrales de precio derivados y documentados (R9), fallo con código 1 (FR-025). La verificación de metadatos cubre FR-026 sin duplicar una regla del principio IV (R8). |
| G5 Datos | PASA | `make bq-load` verifica `data/` contra el manifiesto antes de llamar a `bq`; el manifiesto versionado es la fuente de las cifras esperadas. |
| G8 Simplicidad y seguridad | PASA con justificación | Un paquete Python pequeño sin dependencias nuevas (R11); Dataform sin usar y sin tocar (R13); `bq` sin shell; sin archivos temporales versionados. |
| G9 Escritura | PASA | `scripts/lint_prosa.sh` deja de mirar `.sql` y sus pruebas y el README se actualizan (FR-032). |

Resultado: sin violaciones sin justificar. Se puede pasar a `/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/003-bigquery-data-load/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1 a R15 con fuentes
├── data-model.md        # Fase 1: dataset, tablas, parámetros y contrato de resultados
├── quickstart.md        # Fase 1: validación V0 a V8
├── contracts/
│   ├── ddl.md           # Secciones 1 y 2 del .sql y reglas que se prueban
│   ├── checks.md        # Contrato de los chequeos, metadatos y huella
│   └── make-targets.md  # Objetivos de make, comandos bq y códigos de salida
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
sql/
├── farma_analytics.sql          # Entregable: secciones 1 y 2 (esta feature)
├── checks/
│   ├── 01_conteo_filas.sql
│   ├── 02_unicidad_claves.sql
│   ├── 03_nulos.sql
│   ├── 04_dominios.sql
│   ├── 05_reconciliacion_join.sql
│   ├── 06_precio_unitario.sql
│   └── negativos/               # Un caso negativo por chequeo (JSON con filas y objeto esperado)
│       ├── 01_conteo_filas.json
│       ├── ...
│       └── 06_precio_unitario.json
└── ops/
    └── huella_contenido.sql     # Huella por tabla (no es un chequeo)

warehouse/
├── __init__.py
├── __main__.py                  # argparse: schema, load, checks, checks-negativos
├── commands.py                  # Orquestación de schema, load, checks y checks-negativos
├── results.py                   # CheckResult y salida común de chequeos y metadatos
├── ddl.py                       # Análisis de la DDL con SQLFluff -> DatasetSpec, TableSpec
├── bq.py                        # Construcción y ejecución de comandos bq (sin shell)
├── expectations.py              # Parámetros desde manifest.json y config.toml, umbrales R9
├── metadata.py                  # Verificación de metadatos con bq show
└── checks.py                    # Chequeos, casos negativos con datos en línea y huella

tests/warehouse/
├── conftest.py                  # Ejecutor falso de bq y rutas del repositorio
├── test_ddl_parser.py           # Análisis de la DDL sobre tests/fixtures/sql/ddl_minima.sql
├── test_ddl.py                  # Reglas de contracts/ddl.md
├── test_schema_json.py          # Esquema de carga derivado de la DDL
├── test_expectations.py         # Parámetros y umbrales
├── test_bq.py                   # Flags, dry run antes de ejecutar, labels solo en consultas
├── test_metadata.py             # Comparación de metadatos con la DDL
├── test_schema_command.py       # Orden dry run -> ejecución en make bq-schema
├── test_load_command.py         # Verificación de CSV, metadatos, carga, chequeos y huella
├── test_checks_command.py       # Ejecución de chequeos y códigos de salida
├── test_checks_sql.py           # Parámetros de sql/checks/ conocidos por el programa
└── test_negative_checks.py      # Sustitución por datos en línea y casos negativos

tests/fixtures/sql/ddl_minima.sql  # DDL de prueba para el analizador (ignorada por SQLFluff)

Makefile                         # bq-schema, bq-load, bq-checks, bq-checks-negativos; BQ_JOB_LABELS
scripts/lint_prosa.sh            # Deja de revisar .sql
tests/test_lint_prosa.py         # Prueba de .sql actualizada
tests/fixtures/prosa/            # Se retira el fixture de comentarios .sql (comentarios.sql)
README.md                        # Recorrido de la carga; alcance de make lint-prosa
docs/trazabilidad.md             # Filas de la Fase 1
```

**Structure Decision**: se mantiene la estructura orientativa de la constitución (`sql/` con el
entregable y `checks/`, `scripts/`, `tests/`). Se añaden `warehouse/`, paralelo a `generator/` y con
el mismo modo de ejecución (`uv run python -m ...`), y `sql/ops/` para la consulta de huella, que no
es un chequeo y no debe correr como tal. No se crea `dataform/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No se usa Dataform para la calidad, que la tabla de stack marca como SHOULD | El dueño eligió consultas en `sql/checks/` (aclaración Q2): dry run, labels, límite de bytes y parámetros funcionan con `bq query` sin otra herramienta, y se evita depender de `@dataform/cli` con la vulnerabilidad crítica de R18 | Assertions de Dataform: añaden un dataset (`farma_analytics_assertions`), un `workflow_settings.yaml` y el riesgo de R18 para hacer lo mismo; tener ambas rompería la única implementación canónica |
| Paquete Python `warehouse/` en lugar de solo `make` y `bq` | Hay que analizar la DDL, derivar JSON, leer TOML y comparar metadatos | Bash con `sed` y `jq`: frágil con comentarios y cadenas del SQL, y `jq` no está en el stack |
