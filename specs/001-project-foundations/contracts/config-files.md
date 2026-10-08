# Contrato: archivos de configuración versionados

Cada archivo lista el contenido obligatorio y lo que tiene prohibido. Las decisiones están en
[research.md](../research.md).

## `.bigqueryrc`

Ver [data-model.md](../data-model.md#1-configuración-versionada-de-bq-bigqueryrc). Contenido
exacto esperado:

```text
--location=US

[query]
--use_legacy_sql=false
--maximum_bytes_billed=1073741824

[mk]
--use_legacy_sql=false
```

## `.env.example`

- Las variables de [data-model.md](../data-model.md#2-configuración-local-env-a-partir-de-envexample):
  cuatro activas y dos opcionales comentadas, cada una precedida por un comentario breve en inglés que
  dice para qué sirve y si es obligatoria.
- Valores vacíos o ficticios. Sin IDs reales, correos ni secretos.

## `.gitignore` (entradas que añade esta feature)

`.env`, `.env.*` con excepción `!.env.example`, `.venv/`, `node_modules/`, `.df-credentials.json`,
`application_default_credentials.json`, `*service-account*.json`, `*-key.json`, `*.p12`,
`.pytest_cache/`, `__pycache__/`. No nombra ningún archivo de referencia local.

## `.sqlfluff` y `.sqlfluffignore`

- `.sqlfluff`: reglas de R12.
- `.sqlfluffignore`: `tests/fixtures/`.

## `.pre-commit-config.yaml`

- `minimum_pre_commit_version: "4.4.0"` y `exclude: ^tests/fixtures/`.
- Hooks, en este orden: `sqlfluff-lint` (local, `language: unsupported`,
  `.venv/bin/sqlfluff lint`, archivos `\.sql$`),
  `detect-private-key` (`pre-commit-hooks` v6.0.0) y `forbid-credential-files` (local,
  `language: fail`, patrones de R13).
- MUST NOT incluir el lint de prosa.

## `.github/workflows/checks.yml`

- Disparador: `pull_request` con `branches: [main]`.
- `permissions: contents: read`. Sin `secrets` ni autenticación con GCP.
- Pasos: checkout, `astral-sh/setup-uv` con `version: "0.12.18"`, `uv sync --locked` y
  `uv run pre-commit run --all-files --show-diff-on-failure`.
- Acciones fijadas por SHA completo, con la etiqueta en un comentario.
- El check no se configura como requisito de merge en esta feature.

## `.python-version`, `pyproject.toml`, `uv.lock` y `package.json`

- `.python-version`: una sola línea con la versión exacta 3.12.x.
- `pyproject.toml`: `[project]` con `name = "farma-analytics-bigquery"`, `version = "0.1.0"` y
  `requires-python = ">=3.12"`; `[dependency-groups]` con `dev = ["sqlfluff==4.3.0",
  "pre-commit==4.6.2", "pytest==9.1.1"]`; `[tool.uv]` con `package = false` y
  `required-version = ">=0.12.0"`.
- `uv.lock`: generado por `uv lock` y versionado.
- `package.json`: `"private": true`, `devDependencies` con `"@dataform/cli": "3.0.70"` (sin `^`
  ni `~`), `engines.node` `>=22`. `package-lock.json` versionado.

## `scripts/tool_versions.env`

Claves de [data-model.md](../data-model.md#3-catálogo-de-prerrequisitos), formato `CLAVE=valor`.

## `README.md`

Secciones mínimas, en este orden:

1. Qué es el proyecto, con la declaración de que los datos son sintéticos.
2. Prerrequisitos, con enlace a `scripts/tool_versions.env`, `.python-version` y `pyproject.toml`,
   y comandos de instalación para macOS (Homebrew) y Linux, uv incluido. Python no se instala a
   mano: lo descarga uv.
3. Arranque rápido numerado: crear el proyecto y asociar la facturación, habilitar APIs,
   autenticarse (gcloud y ADC), copiar `.env.example` a `.env`, `make setup-dev`, `make gcp-setup`
   y `make doctor` con un ejemplo de salida correcta.
4. Controles de costo: qué hace cada uno, que la alerta avisa pero no detiene el gasto, que la
   cuota es un tope duro, cómo comprobar ambos a mano y qué pasa si el proyecto queda sin
   facturación (modo sandbox: sin presupuesto ni cuota y expiración de 60 días en tablas y vistas).
5. Calidad: `make lint`, `make lint-sql`, `make lint-prosa`, `make test` y qué corre en CI.
6. Advertencia sobre `~/.bigqueryrc` cuando se usa `bq` fuera del `Makefile`, y nota sobre el
   ajuste de dialecto: tiene ámbito regional, aplica al CLI y a la API, y el resultado comprobado en
   la consola (validación V4).

Escrito en español. La herramienta de dashboards se llama Data Studio.

MUST pasar `scripts/lint_prosa.sh` sin marcas y MUST NOT mencionar el documento de requisitos de
origen.
