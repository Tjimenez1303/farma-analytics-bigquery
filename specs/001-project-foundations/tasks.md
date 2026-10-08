---

description: "Task list for feature 001-project-foundations"
---

# Tasks: Fundaciones del proyecto (entorno local, proyecto de GCP y diagnóstico)

**Input**: Design documents from `specs/001-project-foundations/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluidos. El plan los exige (R15) para verificar SC-003, SC-008 y SC-009 sin tocar GCP,
y la constitución fija pytest como herramienta de pruebas. Se escriben antes de la implementación
de cada historia y deben fallar primero.

**Organization**: tareas agrupadas por historia de usuario para implementarlas y probarlas por
separado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia a la que pertenece (US1 a US4).
- **[Dueño]** al inicio de la descripción: la ejecuta el dueño del repositorio porque toca GCP,
  autentica o instala herramientas. Claude escribe archivos y solo ejecuta verificaciones locales
  (lint, pytest) sin red de GCP ni instalaciones.

## Reglas transversales (aplican a todas las tareas)

- Scripts en bash compatible con 3.2: sin arrays asociativos, sin `mapfile`, sin `${var,,}`.
  `Makefile` compatible con GNU Make 3.81: sin `.ONESHELL`, sin `$(file ...)`.
- `python3` solo para leer JSON. Sin `jq`.
- Ningún archivo versionado contiene IDs de proyecto, cuentas de facturación, correos ni
  menciones al documento de requisitos de origen.
- Ningún comando repite los flags que fija `.bigqueryrc`, salvo el probe B02 del diagnóstico.
- Los comentarios de código y de archivos de configuración van en inglés y solo dicen qué es cada cosa. El README y los mensajes que ve el usuario van en español y cumplen el principio IX.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: archivos de dependencias, versiones y configuración local que todo lo demás usa.

- [X] T001 [P] Añadir a `.gitignore` las entradas de [contracts/config-files.md](contracts/config-files.md#gitignore-entradas-que-añade-esta-feature): `.env`, `.env.*`, `!.env.example`, `.venv/`, `node_modules/`, `.df-credentials.json`, `application_default_credentials.json`, `*service-account*.json`, `*-key.json`, `*.p12`, `.pytest_cache/`, `__pycache__/`, conservando las líneas actuales y sin nombrar ningún archivo de referencia local
- [X] T002 [P] Crear `.python-version` con una sola línea: la versión exacta 3.12.x más reciente que liste `uv python list 3.12` (Claude puede ejecutar ese listado porque no instala nada) y cuya fecha de publicación, comprobada en las notas de versión de python.org, tenga al menos 14 días
- [X] T003 [P] Crear `pyproject.toml` con `[project]` (`name = "farma-analytics-bigquery"`, `version = "0.1.0"`, `requires-python = ">=3.12"`), `[dependency-groups]` con `dev = ["sqlfluff==4.3.0", "pre-commit==4.6.2", "pytest==9.1.1"]` y `[tool.uv]` con `package = false` y `required-version = ">=0.12.0"`
- [X] T004 [P] Crear `package.json` con `"name": "farma-analytics-bigquery"`, `"private": true`, `"engines": {"node": ">=22"}` y `"devDependencies": {"@dataform/cli": "3.0.70"}` (sin `^` ni `~`)
- [X] T005 [P] Crear `scripts/tool_versions.env` con formato `CLAVE=valor` y las claves `MIN_GCLOUD=500.0.0`, `MIN_BQ=2.1.0`, `MIN_NODE=22.0.0`, `MIN_RIPGREP=14.0.0`, `MIN_MAKE=3.81` (Python y uv se declaran en `.python-version` y `pyproject.toml`, no aquí)
- [X] T006 [P] Crear `.env.example` con `GOOGLE_CLOUD_PROJECT=` (vacío), `BILLING_ACCOUNT_ID=000000-000000-000000`, `BUDGET_AMOUNT=10USD` y `QUERY_QUOTA_GIB_PER_DAY=100`, más las opcionales comentadas `# DOCTOR_TIMEOUT=10` y `# LINT_PROSA_MULETILLAS=scripts/muletillas.txt`; cada variable precedida de un comentario breve en inglés que diga para qué sirve y si es obligatoria (el de `GOOGLE_CLOUD_PROJECT` aclara que va el ID del proyecto, no el nombre ni el número, y que si queda vacío se usa `gcloud config get-value project`); formato "`CLAVE=valor`, sin comillas ni espacios alrededor del `=`" (data-model §2)
- [X] T007 Generar `package-lock.json` sin instalar nada con `npm install --package-lock-only --ignore-scripts` (Claude, con permiso del dueño; depende de T004)
- [X] T008 [Dueño] Generar `uv.lock` con `uv lock` en la raíz del repositorio (puede descargar el Python de `.python-version`; depende de T002 y T003)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `.bigqueryrc`, esqueleto del `Makefile` y utilidades de pruebas que usan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

- [X] T009 Crear `.bigqueryrc` en la raíz con el contenido exacto de [contracts/config-files.md](contracts/config-files.md#bigqueryrc): `--location=US` como flag global, `[query]` con `--use_legacy_sql=false` y `--maximum_bytes_billed=1073741824`, y `[mk]` con `--use_legacy_sql=false`; sin `--project_id`, sin `--dataset_id` y sin comentarios (la referencia de `bq` no documenta que los admita)
- [X] T010 Crear `Makefile` con: `SHELL := /bin/bash`, `export BIGQUERYRC := $(CURDIR)/.bigqueryrc`, `-include .env` seguido de `export GOOGLE_CLOUD_PROJECT BILLING_ACCOUNT_ID BUDGET_AMOUNT QUERY_QUOTA_GIB_PER_DAY DOCTOR_TIMEOUT LINT_PROSA_MULETILLAS` (solo esas, no un `export` sin argumentos), `PROJECT_ID = $(or $(GOOGLE_CLOUD_PROJECT),$(shell gcloud config get-value project 2>/dev/null))` con asignación diferida para que `gcloud` solo se invoque en los objetivos que lo usan, `BQ = bq --project_id=$(PROJECT_ID)`, `BQ_LABELS := --label=project:farma-analytics --label=env:dev`, un objetivo `help` por defecto que lista cada objetivo con su comentario `## descripción` (con `grep` y `awk` compatibles con Make 3.81) y una regla de guarda que pide `make setup-dev` cuando falta `.venv`
- [X] T011 Añadir al `Makefile` el objetivo `setup-dev` (`uv sync --locked`, `npm ci` y, solo si existe `.pre-commit-config.yaml`, `uv run pre-commit install`, para que los commits no fallen mientras la configuración de hooks no exista) y el objetivo `test` (`uv run pytest tests/`), ambos con su comentario `##`
- [X] T012 [Dueño] Ejecutar `make setup-dev` para crear `.venv` con el Python fijado y `node_modules` (depende de T007, T008 y T011)
- [X] T013 Crear `tests/conftest.py` con fixtures de pytest: `repo_root` (ruta absoluta del repositorio), `run_script(args, env, input)` que ejecuta un script con `subprocess.run` y devuelve código, stdout y stderr, y `stub_path(tmp_path, overrides)` que copia `tests/fixtures/stubs/` a un directorio temporal, aplica las variables de comportamiento recibidas y devuelve un `PATH` donde los stubs van primero

**Checkpoint**: base lista. Las historias pueden empezar.

---

## Phase 3: User Story 1 - Diagnóstico del entorno desde un clon limpio (Priority: P1) 🎯 MVP

**Goal**: `make doctor` informa chequeo por chequeo el estado de herramientas, autenticación, proyecto, dialecto, location y límite de bytes, con remedio en cada fallo y sin facturar.

**Independent Test**: con stubs, los 8 escenarios de SC-003 marcan el chequeo correcto como `FALLO` con remedio y código 1, el caso sano termina con código 0, y ninguna llamada a `bq query` va sin `--dry_run`. En real, V1 y V2 del quickstart.

### Tests for User Story 1 ⚠️

> Escribirlos primero y comprobar que fallan antes de implementar.

- [X] T014 [P] [US1] Crear los stubs ejecutables de bash en `tests/fixtures/stubs/` para `gcloud`, `bq`, `uv`, `node`, `rg`, `make`, `sqlfluff`, `pre-commit` y `dataform`, más un directorio `tests/fixtures/stubs/venv/bin/` con `python`, `sqlfluff` y `pre-commit` falsos para usar con `DOCTOR_VENV`: cada stub responde según variables de entorno (`STUB_GCLOUD_VERSION`, `STUB_UV_VERSION`, `STUB_NODE_VERSION`, `STUB_ADC=ok|missing`, `STUB_ACCOUNT`, `STUB_PROJECT`, `STUB_BILLING=True|False|error`, `STUB_DRYRUN=ok|disabled|denied`, `STUB_DRYRUN_LOCATION`, `STUB_LEGACY=rejected|accepted`, `STUB_DATASET_LOCATION` vacío si no existe, `STUB_PYTHON_VERSION`, etc.), registra cada invocación con sus argumentos en `$STUB_LOG`, y el `python` falso solo simula `--version` y delega el resto en el `python3` real
- [X] T015 [P] [US1] Crear `tests/test_doctor.py` con: caso sano (código 0, todos `OK` salvo B03 `OMITIDO` sin dataset); los 8 escenarios de SC-003 según [contracts/doctor.md](contracts/doctor.md#catálogo-de-chequeos) (T08 ripgrep ausente, T04 Node 20, T03 Python 3.11 frente a `.python-version`, A02 sin ADC, P01 sin proyecto, B02 legacy aceptado con remedio que nombra `region-us`, B03 location distinta, C03 credenciales dentro del repositorio), cada uno con estado `FALLO`, línea `remedio:` y código 1; código 2 sin `BIGQUERYRC`; dependencias (P01 falla y B01 a B03 salen `OMITIDO`; T10 falla y T03, T06 y T07 salen `OMITIDO`); sin red (N01) con A01 a A04, P02 y B01 a B03 en `OMITIDO` y P01 evaluado; y una prueba que lee `$STUB_LOG` y falla si alguna llamada a `bq query` no lleva `--dry_run`

### Implementation for User Story 1

- [X] T016 [US1] Crear `scripts/doctor.sh` (bash 3.2, `set -u`) con la infraestructura: guarda de `BIGQUERYRC` (debe existir y apuntar a `.bigqueryrc` del repositorio, si no código 2); intérprete solo para JSON `${DOCTOR_VENV:-.venv}/bin/python` o, si no existe, `python3` (en macOS puede ser 3.9, sin `tomllib`), y código 2 si no hay ninguno; carga de `scripts/tool_versions.env`; función `version_ge` que compara versiones con puntos sin `sort -V`; función `record ID NOMBRE ESTADO VALOR REMEDIO` que imprime con columnas alineadas y la línea `remedio:` cuando el estado no es `OK`; función `depends_on` que marca `OMITIDO` con motivo si alguna dependencia está en `FALLO` u `OMITIDO` (la omisión se propaga en cadena); evaluación en orden de dependencias (T10 antes que T03) e impresión en el orden del catálogo; `DOCTOR_TIMEOUT` (por defecto 10 s) en cada llamada remota; resumen `Resumen: N OK, N AVISO, N FALLO, N OMITIDO` y códigos 0, 1 y 2 de [contracts/doctor.md](contracts/doctor.md#códigos-de-salida)
- [X] T017 [US1] Implementar en `scripts/doctor.sh` los chequeos T01 a T10: mínimas de `tool_versions.env` para gcloud, bq, Node, ripgrep y make; T10 compara `uv --version` con `required-version` de `pyproject.toml` (leído con `sed`, sin `tomllib`); T03 compara `${DOCTOR_VENV:-.venv}/bin/python --version` con `.python-version` (`FALLO` con remedio `make setup-dev` si falta `.venv`); SQLFluff y pre-commit comparados con el grupo `dev` de `pyproject.toml` (leído con `sed` o `grep`) y Dataform con `package.json` (leído como JSON con Python), buscando primero en `.venv/bin/` y `node_modules/.bin/` y después en el `PATH`; "Una versión exacta distinta es AVISO (la herramienta funciona, pero no es la fijada), salvo que falte, que es FALLO" (data-model §3); remedio con el comando de instalación de macOS y Linux o `make setup-dev`
- [X] T018 [US1] Implementar en `scripts/doctor.sh` los chequeos C01 (lee `$BIGQUERYRC` y exige `--location=`, `--use_legacy_sql=false` en `[query]` y en `[mk]`, `--maximum_bytes_billed=` entero mayor que 10485760 y ausencia de `--project_id`), C02 (`AVISO` si existe `~/.bigqueryrc`), C03 (`FALLO` si `GOOGLE_APPLICATION_CREDENTIALS` resuelve a una ruta dentro del repositorio) y B04 (muestra `maximum_bytes_billed` en GiB)
- [X] T019 [US1] Implementar en `scripts/doctor.sh` N01 (acceso a `https://bigquery.googleapis.com` con `curl` y el timeout; si falla, A, P y B pasan a `OMITIDO`) y A01 a A04 según R5: cuenta activa con `gcloud auth list --filter=status:ACTIVE --format='value(account)'`, ADC con `gcloud auth application-default print-access-token`, `quota_project_id` leído solo como clave del JSON de ADC, y correo de ADC con un POST a `https://oauth2.googleapis.com/tokeninfo` con el token en el cuerpo (nunca en la URL), `AVISO` si no coincide o no se puede obtener; nunca imprimir el token
- [X] T020 [US1] Implementar en `scripts/doctor.sh` P01 (proyecto desde `GOOGLE_CLOUD_PROJECT` o `gcloud config get-value project`, `AVISO` si ambos existen y difieren, `FALLO` si ninguno) y P02 (`gcloud billing projects describe <P> --format='value(billingEnabled)'`: `True` OK, `False` AVISO con la advertencia de sandbox, error `OMITIDO` con el motivo)
- [X] T021 [US1] Implementar en `scripts/doctor.sh` B01 (`bq --project_id=<P> --format=json query --dry_run 'SELECT 1'`, parseo de `jobReference.location`, comparación con la location de `.bigqueryrc`, `AVISO` si no hay JSON o location, `FALLO` clasificado como API deshabilitada, permiso denegado o location distinta con su remedio), B02 (mismo dry run forzando `--use_legacy_sql=true`, con un comentario que explica que es la excepción documentada de R2: rechazado es `OK`, validado es `FALLO` con remedio `make gcp-dialect` que nombra la región `region-<loc>` calculada desde `.bigqueryrc`) y B03 (`bq --project_id=<P> --format=json show farma_analytics`: inexistente `OMITIDO`, location distinta `FALLO`)
- [X] T022 [US1] Añadir al `Makefile` el objetivo `doctor` (`## Diagnostica herramientas, autenticación, dialecto y location sin facturar`) que ejecuta `scripts/doctor.sh` y marcar el script como ejecutable (`chmod +x`)
- [X] T023 [US1] Ejecutar `make test` (Claude, sin red de GCP) y ajustar `scripts/doctor.sh` hasta que `tests/test_doctor.py` pase completo (depende de T012)
- [X] T024 [US1] Crear `README.md` en español siguiendo el orden de [contracts/config-files.md](contracts/config-files.md#readmemd): descripción del proyecto con la declaración de que los datos son sintéticos y la herramienta de dashboards llamada Data Studio; prerrequisitos con enlace a `scripts/tool_versions.env`, `.python-version` y `pyproject.toml`, comandos de instalación para macOS (Homebrew) y Linux, uv incluido, y la nota de que Python lo descarga uv; arranque rápido numerado con los comandos de R10 (crear el proyecto, asociar la facturación, `gcloud config set project`, habilitar `bigquery.googleapis.com billingbudgets.googleapis.com cloudquotas.googleapis.com cloudbilling.googleapis.com`, `gcloud auth login`, `gcloud auth application-default login`, `gcloud auth application-default set-quota-project`), copiar `.env.example` a `.env`, `make setup-dev`, `make gcp-setup` y `make doctor` con un ejemplo de salida correcta; cada comando en su propio bloque `bash`; sustituye al README actual conservando su descripción

**Checkpoint**: US1 funcional y probada con stubs. Validación real en V1 y V2 tras US2.

---

## Phase 4: User Story 2 - Proyecto de GCP restringido a GoogleSQL y con costo acotado (Priority: P1)

**Goal**: objetivos idempotentes que fijan `only_google_sql`, la cuota diaria y el presupuesto, y documentación de los controles de costo.

**Independent Test**: con stubs, `gcp_budget.sh` crea si no existe y actualiza si existe, y ambos scripts terminan con código 1 sin llamar a GCP cuando falta un dato o la unidad no es la esperada. En real, V4, V5 y V6 del quickstart.

### Tests for User Story 2 ⚠️

- [X] T025 [P] [US2] Crear `tests/test_gcp_scripts.py` con stubs de `gcloud` (reutilizando `tests/fixtures/stubs/`): presupuesto ausente llama a `budgets create` con `--display-name=farma-analytics-bigquery`, `--calendar-period=month`, `--filter-projects=projects/<P>`, los tres `--threshold-rule=percent=0.5|0.9|1.0` y `--billing-project=<P>`; presupuesto existente llama a `budgets update <name>` con `--clear-threshold-rules` y los tres `--add-threshold-rule=percent=0.5|0.9|1.0`, sin ningún `--threshold-rule`, y nunca a `create`; más de un presupuesto con ese nombre termina con código 1 y lista los nombres; sin `BILLING_ACCOUNT_ID` o `BUDGET_AMOUNT` termina con código 1 sin invocar `gcloud`; cuota con `QUERY_QUOTA_GIB_PER_DAY=100` y `metricUnit` que empieza por `MiBy` llama a `quotas preferences update farma-query-usage-per-day` con `--quota-id=QueryUsagePerDay --preferred-value=102400 --allow-missing --allow-high-percentage-quota-decrease`; sin `QUERY_QUOTA_GIB_PER_DAY` o con un valor no entero termina con código 1 sin invocar `gcloud`; con otra unidad termina con código 1, muestra la unidad leída y no llama a `update`

### Implementation for User Story 2

- [X] T026 [US2] Añadir al `Makefile` el objetivo `gcp-dialect` que calcula la región como `region-` más la location de `.bigqueryrc` en minúsculas (leída con `sed` del archivo, nunca duplicada en el `Makefile`) y, siguiendo el principio II, primero valida la sentencia con `$(BQ) query --dry_run "ALTER PROJECT \`$(PROJECT_ID)\` SET OPTIONS (\`region-<loc>.default_sql_dialect_option\` = 'only_google_sql')"` y solo si el dry run se valida la ejecuta con `$(BQ) query $(BQ_LABELS)` y la misma sentencia (si el dry run falla, se detiene con código 1 y muestra el error), con guarda que termina con código 1 si falta `PROJECT_ID` y un mensaje que recuerda el rol BigQuery Admin (`bigquery.config.update`) si falla por permisos
- [X] T027 [P] [US2] Crear `scripts/gcp_quota.sh` (bash 3.2) con la constante `PREFERENCE_ID=farma-query-usage-per-day` definida solo en este script: exige `PROJECT_ID` y `QUERY_QUOTA_GIB_PER_DAY` (entero mayor que 0) antes de cualquier llamada, lee `metricUnit` con `gcloud quotas info describe QueryUsagePerDay --service=bigquery.googleapis.com --project=<P> --format=json` y Python, se detiene con código 1 si no empieza por `MiBy`, y aplica `gcloud quotas preferences update "$PREFERENCE_ID" --service=bigquery.googleapis.com --quota-id=QueryUsagePerDay --preferred-value=$((QUERY_QUOTA_GIB_PER_DAY * 1024)) --project=<P> --allow-missing --allow-high-percentage-quota-decrease`; ante error de permisos nombra el rol Quota Administrator (`roles/servicemanagement.quotaAdmin`) y la API `cloudquotas.googleapis.com`; si `gcloud` no reconoce el grupo `quotas`, el remedio es `gcloud components update`
- [X] T028 [P] [US2] Crear `scripts/gcp_budget.sh` (bash 3.2) con la constante `BUDGET_NAME=farma-analytics-bigquery` definida solo en este script: exige `PROJECT_ID`, `BILLING_ACCOUNT_ID` y `BUDGET_AMOUNT` antes de cualquier llamada; busca con `gcloud billing budgets list --billing-account=<B> --filter="displayName=$BUDGET_NAME" --format='value(name)' --billing-project=<P>`; si no hay resultado ejecuta `gcloud billing budgets create` con los flags de R9; si hay uno ejecuta `gcloud billing budgets update <name> --billing-account=<B> --budget-amount=<BUDGET_AMOUNT> --calendar-period=month --filter-projects=projects/<P> --clear-threshold-rules --add-threshold-rule=percent=0.5 --add-threshold-rule=percent=0.9 --add-threshold-rule=percent=1.0 --billing-project=<P>` (la referencia de `gcloud` no admite `--threshold-rule` en `update`); si hay más de uno termina con código 1 y lista los nombres; ante error de permisos nombra los roles Billing Account Administrator o Billing Account Costs Manager y la API `billingbudgets.googleapis.com`
- [X] T029 [US2] Añadir al `Makefile` los objetivos `gcp-quota`, `gcp-budget` y `gcp-setup` (este último ejecuta `gcp-dialect`, `gcp-quota` y `gcp-budget` en ese orden), pasando el proyecto de forma explícita (`PROJECT_ID=$(PROJECT_ID) scripts/gcp_quota.sh` y `PROJECT_ID=$(PROJECT_ID) scripts/gcp_budget.sh`, porque `PROJECT_ID` es una variable de `make` y no se exporta), con comentarios `##` y `chmod +x` de los dos scripts
- [X] T030 [US2] Ejecutar `make test` (Claude) hasta que `tests/test_gcp_scripts.py` pase
- [X] T031 [US2] Añadir a `README.md` la sección de controles de costo: límite de 1 GiB por consulta en `.bigqueryrc`, cuota diaria configurable en `.env` (`QUERY_QUOTA_GIB_PER_DAY`, 100 GiB por defecto) como tope duro (error `usageQuotaExceeded` hasta la medianoche del Pacífico), alerta de presupuesto que avisa pero no detiene el gasto, permisos que necesita cada objetivo, cómo comprobar a mano el presupuesto (Facturación, Presupuestos y alertas) y la cuota (IAM y administración, Cuotas, "Query usage per day"), qué pasa si el proyecto queda sin facturación (modo sandbox: sin presupuesto ni cuota y expiración de 60 días en tablas y vistas), la advertencia de que `bq` fuera del `Makefile` usa `~/.bigqueryrc` salvo que se exporte `BIGQUERYRC`, y la nota de que el ajuste de dialecto tiene ámbito regional y aplica al CLI y a la API (el resultado en la consola se añade tras V4)

**Checkpoint**: US1 y US2 completas. El dueño puede ejecutar el arranque real.

---

## Phase 5: User Story 3 - Estilo SQL y protección del repositorio en cada commit y en cada PR (Priority: P2)

**Goal**: SQLFluff con las reglas del principio II y bloqueo de credenciales en pre-commit y en GitHub Actions.

**Independent Test**: `tests/test_sqlfluff_config.py` pasa (conforme sin violaciones, cada violación sembrada detectada), los intentos de commitear `.env`, credenciales de Dataform o una clave privada se bloquean, y `make lint` (el mismo comando que CI) falla con un `.sql` no conforme (V7 y V10).

### Tests for User Story 3 ⚠️

- [X] T032 [P] [US3] Crear `tests/fixtures/sql/conforme.sql` con una consulta que cumpla todo el principio II (palabras clave en mayúsculas, `AS` explícito, `INNER JOIN ... ON` con alias semánticos de 3 o más letras como `compras` y `clue_cat`, columnas calificadas, `GROUP BY` por nombre, `AND` al inicio de línea, líneas de 100 caracteres o menos, sin coma final, comentario de cabecera) y `tests/fixtures/sql/no_conforme.sql` con una violación de cada tipo: palabra clave en minúsculas, alias de tabla sin `AS`, `JOIN` sin `INNER`, `USING`, `GROUP BY 1`, coma final en el `SELECT`, línea de más de 100 caracteres, alias de una letra y `AND` al final de línea
- [X] T033 [P] [US3] Crear `tests/test_sqlfluff_config.py` que copia cada ejemplo y el `.sqlfluff` del repositorio a `tmp_path` (porque `.sqlfluffignore` excluye `tests/fixtures/`), ejecuta `uv run sqlfluff lint --format json` sobre la copia, exige 0 violaciones en `conforme.sql` y exige en `no_conforme.sql` al menos una violación de cada código esperado (CP01, AL01, AM05, ST07, AM06, CV03, LT05, AL06, LT03)

### Implementation for User Story 3

- [X] T034 [US3] Crear `.sqlfluff` con `[sqlfluff]` `dialect = bigquery`, `templater = raw`, `max_line_length = 100`; `[sqlfluff:rules:capitalisation.keywords]` `capitalisation_policy = upper`; `[sqlfluff:rules:capitalisation.identifiers]` `extended_capitalisation_policy = upper` y `unquoted_identifiers_policy = column_aliases`; `capitalisation.functions` y `capitalisation.types` con `extended_capitalisation_policy = upper`; `capitalisation.literals` con `capitalisation_policy = upper`; `aliasing.table` y `aliasing.column` con `aliasing = explicit`; `aliasing.length` con `min_alias_length = 3`; `ambiguous.join` con `fully_qualify_join_types = inner`; `ambiguous.column_references` con `group_by_and_order_by_style = explicit`; `convention.select_trailing_comma` con `select_clause_trailing_comma = forbid`; y `[sqlfluff:layout:type:binary_operator]` `line_position = leading`; más `.sqlfluffignore` con `tests/fixtures/`
- [X] T035 [US3] Ejecutar `make test` (Claude) y ajustar `.sqlfluff` hasta que `tests/test_sqlfluff_config.py` pase; si una opción cambió de nombre en sqlfluff 4.3.0, corregirla según `docs.sqlfluff.com` y anotarlo en [research.md](research.md) R12
- [X] T036 [US3] Crear `.pre-commit-config.yaml` con `minimum_pre_commit_version: "4.4.0"` (primera versión con `language: unsupported`), `exclude: ^tests/fixtures/` y tres hooks en este orden: `sqlfluff-lint` local (`language: unsupported`, `entry: .venv/bin/sqlfluff lint`, `files: \.sql$`), `detect-private-key` de `https://github.com/pre-commit/pre-commit-hooks` en `rev: v6.0.0`, y `forbid-credential-files` local (`language: fail`, `entry` con un mensaje en español, `files` con la regex de R13 que cubre `.env`, `.env.*` salvo `.env.example`, `.df-credentials.json`, `application_default_credentials.json`, `*service-account*.json`, `*-key.json` y `*.p12`); sin el lint de prosa
- [X] T037 [P] [US3] Crear `.github/workflows/checks.yml`: `on: pull_request` con `branches: [main]`, `permissions: contents: read`, un job en `ubuntu-latest` con `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`, `astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0` con `version: "0.12.18"`, `uv sync --locked` y `uv run pre-commit run --all-files --show-diff-on-failure`; sin `secrets` ni autenticación con GCP
- [X] T038 [US3] Añadir al `Makefile` los objetivos `lint` (`uv run pre-commit run --all-files`, el mismo comando que CI) y `lint-sql` (`uv run sqlfluff lint .`, que respeta `.sqlfluffignore`), con comentarios `##` y la guarda de `.venv`
- [X] T039 [US3] Ejecutar `uv run pre-commit install` y `make lint` (Claude) y corregir lo que falle en archivos del repositorio
- [X] T040 [US3] Validar V7 y la parte local de V10 (Claude, en una rama local desechable y sin push): crear `.env`, `.df-credentials.json` y un JSON con una clave privada falsa e intentar commitear cada uno (los tres deben bloquearse con el nombre del archivo y el hook); añadir un `.sql` no conforme fuera de `tests/fixtures/` y comprobar que `make lint` falla; borrar después los archivos y la rama
- [X] T041 [US3] Añadir a `README.md` la sección de calidad: `make lint`, `make lint-sql`, `make test`, qué corre en cada commit y qué corre en GitHub Actions en cada PR (el mismo comando que `make lint`; el check avisa pero no bloquea el merge)

**Checkpoint**: US3 completa e independiente de US1 y US2.

---

## Phase 6: User Story 4 - Revisión de la prosa para lectores bajo demanda (Priority: P2)

**Goal**: `scripts/lint_prosa.sh` marca las 10 categorías del principio IX con archivo, línea y fragmento, y se ejecuta a mano.

**Independent Test**: `tests/test_lint_prosa.py` pasa: una marca por violación sembrada, 0 marcas en el documento limpio, usos permitidos sin marcas, excepciones respetadas, entrada estándar y exclusiones.

### Tests for User Story 4 ⚠️

- [X] T042 [P] [US4] Crear en `tests/fixtures/prosa/`: `violaciones.md` con una línea por categoría de [contracts/lint-prosa.md](contracts/lint-prosa.md#categorías) (raya, semirraya, guion como raya, punto y coma, emoji, flecha, carácter de caja, comillas curvas, encabezado en Title Case, lista con `**Cabecera:**`, `oaicite`, `utm_source=chatgpt.com` dentro de una URL y dos muletillas, una literal y una cubierta por `re:`); `limpio.md` sin ninguna violación; `usos_permitidos.md` con marcadores de lista, flags de CLI, kebab-case, el rango 2024-2025, una palabra compuesta, una fecha ISO, un número negativo, "clave primaria", "estimador robusto", un título "Arranque con BigQuery y Data Studio", rayas dentro de bloques de código y código en línea, y una línea con `<!-- lint-prosa: ignorar -->`; y `comentarios.sql` con una raya en un comentario y `;` como terminador
- [X] T043 [P] [US4] Crear `tests/test_lint_prosa.py` que ejecuta `scripts/lint_prosa.sh` sobre cada fixture y comprueba: en `violaciones.md` una marca por línea sembrada con la categoría correcta y código 1; en `limpio.md` y `usos_permitidos.md` 0 marcas y código 0; en `comentarios.sql` solo la marca de la raya; con `-` y texto por entrada estándar, la ruta `<stdin>`; que una entrada nueva añadida a una copia temporal de `scripts/muletillas.txt` se detecta sin tocar el script (mediante `LINT_PROSA_MULETILLAS` apuntando a la copia); que `specs/` y `.specify/` quedan excluidos aunque se pasen como ruta; y código 2 con una ruta inexistente

### Implementation for User Story 4

- [X] T044 [P] [US4] Crear `scripts/muletillas.txt` con comentarios `#` por grupo y todas las entradas del principio IX de la constitución: fórmulas de relleno, aperturas genéricas, verbos de moda (con `re:` para conjugaciones de "adentrarse", "sumergirse", "profundizar en", "potenciar", "navegar por", "subrayar", "resaltar", "aprovechar", "fomentar" y "exploraremos"), cuantificadores vagos, adjetivos inflados, sustantivos de moda, calcos y rodeos ("juega un papel clave", "desempeña un papel crucial", "a nivel de", "sirve como", "se erige como", "constituye", "utilizar", "llevar a cabo", "realizar un análisis"), cierres mecánicos, "no solo", "sino también", inflado de importancia ("marca un hito", "sienta las bases"), atribuciones vagas ("los expertos coinciden", "diversos estudios"), fórmulas de chat ("excelente pregunta", "aquí tienes", "espero que te sea útil", "si quieres, puedo"), descargos ("según mi última actualización") y tono publicitario ("al siguiente nivel", "información valiosa para la toma de decisiones")
- [X] T045 [P] [US4] Crear `scripts/prosa_excepciones.txt` con la sección `[terminos]` ("clave primaria", "estimador robusto", "medicamento innovador") y la sección `[nombres_propios]` (BigQuery, GoogleSQL, Google, Cloud, Data, Studio, Looker, Dataform, SQLFluff, Python, Node, Homebrew, Linux, macOS, GitHub, Actions, México, IMSS, ISSSTE, SEDENA, SEMAR, PEMEX, INEGI)
- [X] T046 [US4] Crear `scripts/lint_prosa.sh` (bash 3.2, ripgrep sin PCRE2) según [contracts/lint-prosa.md](contracts/lint-prosa.md): argumentos (sin argumentos, rutas o `-`), alcance por defecto y exclusiones, búsqueda de restos de herramientas sobre el texto original, preproceso a un directorio temporal que conserva rutas y números de línea (bloques de código, marcador `lint-prosa: ignorar` y `[terminos]` a líneas vacías, código en línea y URL eliminados, en `.sql` solo comentarios), las 10 categorías con sus patrones (`\p{Extended_Pictographic}` para emojis, U+2500 a U+257F para cajas), lectura de `${LINT_PROSA_MULETILLAS:-scripts/muletillas.txt}` con frases literales con límites de palabra sin distinguir mayúsculas y líneas `re:` como regex, regla de Title Case con siglas, mayúsculas internas y `[nombres_propios]`, salida `RUTA:LÍNEA: CATEGORÍA: FRAGMENTO`, resumen por la salida de errores y códigos 0, 1 y 2; limpieza del directorio temporal con `trap`
- [X] T047 [US4] Añadir al `Makefile` el objetivo `lint-prosa` (`## Revisa la prosa para lectores según el principio IX`) y `chmod +x scripts/lint_prosa.sh`
- [X] T048 [US4] Ejecutar `make test` (Claude) hasta que `tests/test_lint_prosa.py` pase
- [X] T049 [US4] Añadir a `README.md`, en la sección de calidad, `make lint-prosa`, cuándo ejecutarlo (antes de abrir cada PR, también sobre el mensaje de commit y la descripción del PR con `scripts/lint_prosa.sh -`) y cómo usar las excepciones

**Checkpoint**: las cuatro historias funcionan por separado.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: verificaciones finales, validación real con el dueño y entrega.

- [X] T050 Ejecutar `make lint-prosa` (Claude) y corregir `README.md` hasta 0 marcas (FR-035, SC-009)
- [X] T051 Ejecutar `make test` y `make lint` completos (Claude) y dejar ambos sin fallos
- [X] T052 Buscar en todos los archivos nuevos o modificados cualquier ID real, correo, token o mención al documento de requisitos de origen o a su proceso de revisión (con `rg -i` y los términos que conoce el dueño, sin escribirlos en ningún archivo versionado) y corregir lo que aparezca
- [X] T053 [Dueño] Validar V1 y V2 de [quickstart.md](quickstart.md): arranque desde un clon limpio en 15 minutos o menos y `make doctor` en 60 segundos o menos sin jobs en el historial (si aparecen dry runs, avisar a Claude para reformular SC-002)
- [X] T054 [Dueño] Validar V4 de [quickstart.md](quickstart.md) antes y después de `make gcp-dialect` y anotar el resultado en la consola; Claude documenta ese resultado en `README.md` y, si B02 no discrimina tras 10 minutos, activa el fallback de R2 en `scripts/doctor.sh`, `tests/test_doctor.py` y `README.md`
- [X] T055 [Dueño] Validar V5 y V6 de [quickstart.md](quickstart.md): consulta que supera el límite falla sin coste y `make gcp-setup` dos veces deja un solo presupuesto, la misma cuota y el mismo dialecto
- [X] T056 Commit en `001-project-foundations`, pasar el cuerpo del mensaje de commit y la descripción del PR por `scripts/lint_prosa.sh -` hasta 0 marcas, actualizar la rama con `main` si quedó atrás, push y PR hacia `main` con título Conventional Commits; comprobar que aparece el check de GitHub Actions en verde (V10); el merge lo hace el dueño
- [ ] T057 [Dueño] Decidir si se ejecuta la parte opcional de V10 (PR desechable en borrador con un `.sql` no conforme); Claude solo la ejecuta con ese permiso explícito y cierra el PR sin merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias. T007 depende de T004 y T008 (dueño) de T002 y T003.
- **Foundational (Phase 2)**: depende de Setup. T012 (dueño) depende de T007, T008 y T011, y bloquea todas las tareas de "Ejecutar `make test`".
- **US1 a US4 (Phases 3 a 6)**: dependen de Foundational. Entre sí son independientes, salvo que comparten `Makefile` y `README.md`, que se editan en secuencia.
- **Polish (Phase 7)**: depende de las cuatro historias. T053 a T055 dependen además de que el dueño haya creado el proyecto con el README.

### User Story Dependencies

- **US1 (P1)**: tras Foundational. La validación real (V1, V2) necesita los objetivos `gcp-*` de US2, pero las pruebas con stubs no.
- **US2 (P1)**: tras Foundational. No depende de US1 para sus pruebas.
- **US3 (P2)**: tras Foundational. Necesita `.venv` (T012).
- **US4 (P2)**: tras Foundational. No necesita `.venv` para el script, solo para pytest.

### Within Each User Story

- Pruebas primero, comprobando que fallan.
- Scripts antes que objetivos del `Makefile`.
- Objetivos antes que la sección correspondiente del README.

### Parallel Opportunities

- Setup: T001 a T006 en paralelo.
- US1: T014 y T015 en paralelo.
- US2: T025, T027 y T028 en paralelo.
- US3: T032, T033 y T037 en paralelo.
- US4: T042, T043, T044 y T045 en paralelo.
- Con Foundational terminado, US2, US3 y US4 pueden avanzar en paralelo con US1, coordinando las ediciones de `Makefile` y `README.md`.

---

## Parallel Example: User Story 4

```bash
Task: "Crear fixtures de prosa en tests/fixtures/prosa/"
Task: "Crear tests/test_lint_prosa.py"
Task: "Crear scripts/muletillas.txt"
Task: "Crear scripts/prosa_excepciones.txt"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 y Phase 2 (el dueño ejecuta T008 y T012).
2. Phase 3: `make doctor` con sus pruebas de stubs en verde.
3. Parar y validar: el dueño puede ejecutar `make doctor` contra su proyecto aunque B02 salga en `FALLO` hasta tener US2.

### Incremental Delivery

1. Setup y Foundational: base lista.
2. US1: diagnóstico (MVP).
3. US2: ajustes de GCP. El dueño ejecuta el arranque real y V1, V2, V4 a V6.
4. US3: estilo SQL, hooks y CI.
5. US4: lint de prosa y README sin marcas.
6. Polish y un único PR para la feature.

---

## Notes

- Las tareas con **[Dueño]** no las ejecuta Claude. Claude entrega el comando exacto y espera la salida.
- Los commits se agrupan por historia en la rama `001-project-foundations` y se integran en un solo PR con squash.
- Evitar editar `Makefile` o `README.md` desde dos tareas a la vez.
