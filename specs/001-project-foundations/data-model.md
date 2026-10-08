# Data Model: Fundaciones del proyecto

**Feature**: `001-project-foundations` | **Fecha**: 2026-10-07

La feature no tiene datos de negocio. Sus "entidades" son archivos de configuración, el informe
del diagnóstico y los ajustes del proyecto de GCP. Para cada una se indica qué contiene, quién la
escribe, dónde vive y qué reglas la validan.

## 1. Configuración versionada de `bq` (`.bigqueryrc`)

| Campo | Sección | Valor | Regla |
|---|---|---|---|
| `--location` | global | `US` | Única fuente de la location del proyecto (FR-015). |
| `--use_legacy_sql` | `[query]` | `false` | Obligatorio (FR-013). |
| `--maximum_bytes_billed` | `[query]` | `1073741824` | Entero en bytes, mayor que 10 MB (mínimo facturable por tabla). |
| `--use_legacy_sql` | `[mk]` | `false` | Obligatorio (FR-013). |

- MUST NOT contener `--project_id` ni `--dataset_id`.
- Sin comentarios: no está documentado que `bq` los admita, así que la explicación vive en el
  README.
- La valida el chequeo `C1` del diagnóstico.

## 2. Configuración local (`.env`, a partir de `.env.example`)

| Variable | Obligatoria | Ejemplo en `.env.example` | Uso |
|---|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | No (si falta, se usa `gcloud config`) | vacío | ID del proyecto para `bq` y los ajustes. |
| `BILLING_ACCOUNT_ID` | Solo para crear el proyecto y el presupuesto | `000000-000000-000000` | Cuenta de facturación. |
| `BUDGET_AMOUNT` | Solo para el presupuesto | `10USD` | Importe mensual con la moneda de la cuenta. |
| `QUERY_QUOTA_GIB_PER_DAY` | Solo para la cuota | `100` | Cuota diaria de bytes de consulta del proyecto, en GiB. Entero mayor que 0. `gcp_quota.sh` lo convierte a MiB (× 1024). |
| `DOCTOR_TIMEOUT` | No (comentada) | `10` | Segundos por llamada remota del diagnóstico. |
| `LINT_PROSA_MULETILLAS` | No (comentada) | `scripts/muletillas.txt` | Ruta alternativa de la lista de muletillas. |

- Las variables que solo usan las pruebas (`DOCTOR_VENV` y las `STUB_*`) no van en `.env.example`.

- Formato compatible con `make` y con `source` de bash: `CLAVE=valor`, sin comillas ni espacios
  alrededor del `=`.
- `.env` está en `.gitignore`. `.env.example` se versiona y MUST NOT contener valores reales.

## 3. Catálogo de prerrequisitos

**Mínimas** en `scripts/tool_versions.env` (herramientas del sistema sin archivo propio):

| Clave | Valor | Comando de detección |
|---|---|---|
| `MIN_GCLOUD` | `500.0.0` | `gcloud version` (línea `Google Cloud SDK`) |
| `MIN_BQ` | `2.1.0` | `bq version` |
| `MIN_NODE` | `22.0.0` | `node --version` |
| `MIN_RIPGREP` | `14.0.0` | `rg --version` |
| `MIN_MAKE` | `3.81` | `make --version` |

**Declaradas en el archivo que lee cada herramienta**:

| Herramienta | Archivo | Versión | Detección |
|---|---|---|---|
| uv | `pyproject.toml`, `[tool.uv] required-version` | `>=0.12.0` (mínima) | `uv --version` |
| Python del proyecto | `.python-version` | 3.12.x exacta | `.venv/bin/python --version` (FALLO si falta `.venv` o no coincide) |
| SQLFluff | `pyproject.toml` grupo `dev` y `uv.lock` | `4.3.0` | `.venv/bin/sqlfluff --version`, si no, `sqlfluff` del `PATH` |
| pre-commit | `pyproject.toml` grupo `dev` y `uv.lock` | `4.6.2` | `.venv/bin/pre-commit --version`, si no, el del `PATH` |
| pytest | `pyproject.toml` grupo `dev` y `uv.lock` | `9.1.1` | no lo comprueba el diagnóstico |
| Dataform CLI | `package.json` | `3.0.70` | `node_modules/.bin/dataform --version`, si no, el del `PATH` |

- Comparación: versión detectada mayor o igual a la mínima, o igual a la exacta. Una versión
  exacta distinta es AVISO (la herramienta funciona, pero no es la fijada), salvo que falte, que es
  FALLO.

## 4. Informe del diagnóstico

Cada chequeo produce un registro:

| Campo | Tipo | Valores |
|---|---|---|
| `id` | texto | identificador estable del catálogo (ver [contracts/doctor.md](contracts/doctor.md)) |
| `nombre` | texto | descripción corta |
| `estado` | enum | `OK`, `AVISO`, `FALLO`, `OMITIDO` |
| `valor` | texto | lo detectado (versión, cuenta, proyecto, location...) |
| `remedio` | texto | comando o sección del README; obligatorio si el estado es `AVISO`, `FALLO` u `OMITIDO` |
| `depende_de` | lista de `id` | si alguno es `FALLO` u `OMITIDO`, este pasa a `OMITIDO` con el motivo (la omisión se propaga en cadena) |

Resumen final: número de chequeos por estado. Código de salida: 0 si no hay ningún `FALLO`, 1 si
hay al menos uno, 2 si el diagnóstico no pudo arrancar (por ejemplo, sin `BIGQUERYRC`).

Transiciones: `pendiente` → `OK` / `AVISO` / `FALLO`, o `pendiente` → `OMITIDO` si una dependencia
falló o quedó omitida, o no hay red.

## 5. Ajustes del proyecto de GCP

| Ajuste | Identidad (para idempotencia) | Valor | Lo aplica | Permiso |
|---|---|---|---|---|
| Dialecto | opción `region-<loc>.default_sql_dialect_option` del proyecto | `only_google_sql` | `make gcp-dialect` | `bigquery.config.update` (BigQuery Admin) |
| Cuota diaria | preferencia `farma-query-usage-per-day` de `QueryUsagePerDay` | `QUERY_QUOTA_GIB_PER_DAY` × 1024 MiB por día (100 GiB en `.env.example`) | `make gcp-quota` | `serviceusage.quotas.update` (Quota Administrator) |
| Presupuesto | presupuesto con nombre `farma-analytics-bigquery` en la cuenta | `BUDGET_AMOUNT`, mensual, avisos 50/90/100 % | `make gcp-budget` | Billing Account Administrator o Costs Manager |

- Repetir cualquier objetivo deja el mismo estado (SC-006).
- El nombre de la preferencia es una constante de `scripts/gcp_quota.sh` y el del presupuesto, de
  `scripts/gcp_budget.sh`. No son variables de `.env`, para que la búsqueda por nombre sea siempre
  la misma.

## 6. Reglas de calidad

- **`.sqlfluff`**: reglas de R12. Las validan los ejemplos de `tests/fixtures/sql/`.
- **`.pre-commit-config.yaml`**: tres hooks (`sqlfluff-lint`, `detect-private-key`,
  `forbid-credential-files`) y exclusión de `tests/fixtures/`.
- **`scripts/muletillas.txt`**: una entrada por línea. Tipos de línea: comentario (`#`), vacía,
  frase literal (sin distinguir mayúsculas, con límites de palabra) o regex con prefijo `re:`.
  Contenido inicial: todo el vocabulario, las fórmulas y los cierres prohibidos del principio IX.
- **`scripts/prosa_excepciones.txt`**: dos secciones, `[terminos]` (frases permitidas que se
  eliminan antes de buscar muletillas: "clave primaria", "estimador robusto", "medicamento
  innovador") y `[nombres_propios]` (palabras que la regla de Title Case acepta: BigQuery, Data,
  Studio, Google, Cloud, Dataform, GoogleSQL, Python, Node, IMSS, ISSSTE, México...).
- **Marcador de línea**: `lint-prosa: ignorar` dentro de un comentario hace que el script salte esa
  línea. Se usa solo para falsos positivos puntuales y queda visible en el diff.
