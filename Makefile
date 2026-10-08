# Compatible with GNU Make 3.81 (macOS default).
SHELL := /bin/bash
.DEFAULT_GOAL := help

# bq defaults for this repository.
export BIGQUERYRC := $(CURDIR)/.bigqueryrc

-include .env
export GOOGLE_CLOUD_PROJECT BILLING_ACCOUNT_ID BUDGET_AMOUNT QUERY_QUOTA_GIB_PER_DAY DOCTOR_TIMEOUT LINT_PROSA_MULETILLAS

# Deferred so gcloud only runs in targets that need the project.
PROJECT_ID = $(or $(GOOGLE_CLOUD_PROJECT),$(shell gcloud config get-value project 2>/dev/null))
BQ = bq --project_id=$(PROJECT_ID)
BQ_LABELS := --label=project:farma-analytics --label=env:dev

# Location comes only from .bigqueryrc.
LOCATION = $(shell sed -n 's/^--location=//p' .bigqueryrc)
REGION = region-$(shell printf '%s' '$(LOCATION)' | tr '[:upper:]' '[:lower:]')
DIALECT_SQL = ALTER PROJECT \`$(PROJECT_ID)\` SET OPTIONS (\`$(REGION).default_sql_dialect_option\` = 'only_google_sql')

.PHONY: help setup-dev test require-venv require-project doctor gcp-dialect gcp-quota gcp-budget gcp-setup lint lint-sql lint-prosa data data-verify data-manifest bq-schema bq-vista bq-load bq-checks bq-checks-negativos bq-consultas

help: ## Lista los objetivos disponibles
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-20s %s\n", $$1, $$2}'

require-venv:
	@test -d .venv || { echo "Falta .venv: ejecuta 'make setup-dev'."; exit 1; }

setup-dev: ## Instala Python, las dependencias de desarrollo y los hooks de pre-commit
	uv sync --locked
	@if [ -f .pre-commit-config.yaml ]; then uv run pre-commit install; else echo "Sin .pre-commit-config.yaml: hooks no instalados."; fi

test: require-venv ## Ejecuta las pruebas automatizadas
	uv run pytest tests/

doctor: ## Diagnostica herramientas, autenticación, dialecto y location sin facturar
	@scripts/doctor.sh

require-project:
	@test -n "$(PROJECT_ID)" || { echo "Falta el proyecto: define GOOGLE_CLOUD_PROJECT en .env o ejecuta gcloud config set project <PROJECT_ID>."; exit 1; }

gcp-dialect: require-project ## Restringe el proyecto a GoogleSQL (dry run y después ALTER PROJECT)
	@echo "Dry run: $(DIALECT_SQL)"
	@$(BQ) query --dry_run "$(DIALECT_SQL)" || { echo "El dry run falló y no se ejecuta la sentencia. Si es un error de permisos, necesitas el rol BigQuery Admin (bigquery.config.update)."; exit 1; }
	@$(BQ) query $(BQ_LABELS) "$(DIALECT_SQL)" || { echo "Falló el ALTER PROJECT. Si es un error de permisos, necesitas el rol BigQuery Admin (bigquery.config.update)."; exit 1; }
	@echo "Dialecto only_google_sql fijado en $(REGION). Puede tardar unos minutos en aplicarse."

gcp-quota: require-project ## Fija la cuota diaria de consultas (QUERY_QUOTA_GIB_PER_DAY)
	@PROJECT_ID=$(PROJECT_ID) scripts/gcp_quota.sh

gcp-budget: require-project ## Crea o actualiza la alerta de presupuesto mensual
	@PROJECT_ID=$(PROJECT_ID) scripts/gcp_budget.sh

gcp-setup: gcp-dialect gcp-quota gcp-budget ## Aplica dialecto, cuota y presupuesto

# BigQuery schema, view, load, checks and queries. Job labels come from BQ_LABELS.
WAREHOUSE = PROJECT_ID=$(PROJECT_ID) BQ_JOB_LABELS="$(BQ_LABELS)" uv run python -m warehouse

bq-schema: require-venv require-project ## Crea el dataset y las tablas desde sql/farma_analytics.sql (dry run antes de cada sentencia)
	@$(WAREHOUSE) schema

bq-vista: require-venv require-project ## Crea o reemplaza la vista v_compras_farma_completa y ejecuta los chequeos
	@$(WAREHOUSE) vista

bq-load: require-venv require-project ## Verifica data/, carga los CSV en BigQuery y ejecuta los chequeos
	@$(WAREHOUSE) load

bq-checks: require-venv require-project ## Ejecuta los chequeos de calidad sobre las tablas cargadas
	@$(WAREHOUSE) checks

bq-checks-negativos: require-venv require-project ## Comprueba que cada chequeo detecta su caso negativo (0 bytes facturados)
	@$(WAREHOUSE) checks-negativos

bq-consultas: require-venv require-project ## Responde las tres preguntas comerciales sobre la vista y cruza sus cifras
	@$(WAREHOUSE) consultas

lint: require-venv ## Ejecuta los chequeos de pre-commit sobre todo el repositorio (igual que CI)
	uv run pre-commit run --all-files

lint-sql: require-venv ## Revisa el estilo de los archivos .sql con SQLFluff
	uv run sqlfluff lint .

lint-prosa: ## Revisa la prosa para lectores según el principio IX de la constitución
	@scripts/lint_prosa.sh

data: require-venv ## Genera los datos sintéticos y los verifica contra el manifiesto versionado
	uv run python -m generator generate
	uv run python -m generator verify

data-verify: require-venv ## Verifica data/ contra generator/manifest.json
	uv run python -m generator verify

data-manifest: require-venv ## Actualiza generator/manifest.json tras un cambio intencional de parámetros
	@test -f data/manifest.json || { echo "Falta data/manifest.json: ejecuta 'make data' antes."; exit 1; }
	cp data/manifest.json generator/manifest.json
