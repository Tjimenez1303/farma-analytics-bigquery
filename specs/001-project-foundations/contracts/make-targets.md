# Contrato: objetivos del `Makefile`

Reglas comunes a todos los objetivos:

- El `Makefile` exporta `BIGQUERYRC := $(CURDIR)/.bigqueryrc`, incluye `.env` si existe
  (`-include .env`) y exporta sus variables.
- `PROJECT_ID` se resuelve como `$(GOOGLE_CLOUD_PROJECT)` o, si está vacío,
  `gcloud config get-value project`.
- Ningún objetivo repite los flags que fija `.bigqueryrc` (`--use_legacy_sql`, `--location`,
  `--maximum_bytes_billed`), salvo el probe documentado del diagnóstico.
- Los jobs reales que lance `bq` llevan `--label=project:farma-analytics --label=env:dev`.
- Compatible con GNU Make 3.81 y `SHELL := /bin/bash`.

| Objetivo | Qué hace | Efectos | Toca GCP | Lo ejecuta |
|---|---|---|---|---|
| `help` (por defecto) | Lista los objetivos con una línea de descripción cada uno. | Ninguno. | No | Cualquiera |
| `setup-dev` | `uv sync --locked` (crea `.venv` con el Python de `.python-version`, descargándolo si falta), `npm ci` y, solo si existe `.pre-commit-config.yaml`, `uv run pre-commit install`. | Instala dependencias locales. | No | Dueño |
| `doctor` | Ejecuta `scripts/doctor.sh` (ver [doctor.md](doctor.md)). | Ninguno. Solo dry runs y metadatos. | Solo lectura | Dueño |
| `gcp-dialect` | Valida con `--dry_run` y después ejecuta el `ALTER PROJECT` de R1 en la región de la location de `.bigqueryrc`; si el dry run falla, se detiene sin ejecutar. | Opción de proyecto. | Sí | Dueño |
| `gcp-quota` | Ejecuta `scripts/gcp_quota.sh`: lee `metricUnit` de `QueryUsagePerDay` y aplica la preferencia `farma-query-usage-per-day` con `update --allow-missing --allow-high-percentage-quota-decrease`. | Cuota del proyecto. | Sí | Dueño |
| `gcp-budget` | Ejecuta `scripts/gcp_budget.sh`: busca el presupuesto por nombre y lo crea o lo actualiza. Requiere `BILLING_ACCOUNT_ID` y `BUDGET_AMOUNT`. | Presupuesto en la cuenta de facturación. | Sí | Dueño |
| `gcp-setup` | `gcp-dialect`, `gcp-quota` y `gcp-budget` en ese orden. | Los tres anteriores. | Sí | Dueño |
| `lint` | `uv run pre-commit run --all-files` (el mismo comando que CI). | Ninguno. | No | Cualquiera |
| `lint-sql` | `uv run sqlfluff lint .` sobre los `.sql` del repositorio (respeta `.sqlfluffignore`). | Ninguno. | No | Cualquiera |
| `lint-prosa` | `scripts/lint_prosa.sh` sobre el alcance por defecto. | Ninguno. | No | Cualquiera |
| `test` | `uv run pytest tests/`. | Ninguno. | No | Cualquiera |

Errores:

- Si falta `PROJECT_ID`, los objetivos `gcp-*` terminan con código 1 y el mensaje dice dónde
  configurarlo.
- Los objetivos pasan `PROJECT_ID` a los scripts de forma explícita
  (`PROJECT_ID=$(PROJECT_ID) scripts/gcp_quota.sh`), porque es una variable de `make` y no se
  exporta.
- Si falta `BILLING_ACCOUNT_ID` o `BUDGET_AMOUNT`, `gcp-budget` termina con código 1 sin llamar a
  GCP.
- Si un comando de GCP falla por permisos, el script muestra el permiso o el rol de
  [data-model.md](../data-model.md#5-ajustes-del-proyecto-de-gcp) y termina con código 1.
- Si `.venv` no existe, `lint`, `lint-sql` y `test` piden ejecutar `make setup-dev`.
- `PROJECT_ID` se define con asignación diferida (`=`), de modo que `gcloud` solo se invoca en los
  objetivos que lo usan. El `Makefile` exporta solo las variables de `.env`, no todas las suyas.
