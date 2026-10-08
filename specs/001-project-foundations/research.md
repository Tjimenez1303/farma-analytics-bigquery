# Research: Fundaciones del proyecto

**Feature**: `001-project-foundations` | **Fecha**: 2026-10-07 | **Plan**: [plan.md](plan.md)

Cada decisión sigue el formato Decision / Rationale / Alternatives considered. Las versiones y
comportamientos se verificaron el 2026-10-07 contra los registros (PyPI, npm, GitHub) y la
documentación oficial (`docs.cloud.google.com`).

---

## R1. Ajuste de dialecto del proyecto

- **Decision**: aplicar con `bq query` (GoogleSQL, por `.bigqueryrc`):
  `ALTER PROJECT \`<PROJECT_ID>\` SET OPTIONS (\`region-<loc>.default_sql_dialect_option\` = 'only_google_sql')`,
  donde `<loc>` es la location de `.bigqueryrc` en minúsculas (`US` → `region-us`). Lo ejecuta el
  objetivo `make gcp-dialect`, que primero valida la sentencia con `--dry_run` y solo la ejecuta
  si el dry run se valida (principio II: cada sentencia se valida con un dry run antes de
  ejecutarse). Requiere `bigquery.config.update` (rol BigQuery Admin). Es una DDL sin bytes
  facturados e idempotente (repetirla deja el mismo valor). Comprobado el 2026-10-08: BigQuery
  acepta el dry run de esta DDL ("Query successfully validated", 0 bytes). Si algún día no lo
  admitiera, el objetivo se detiene y muestra el error en lugar de ejecutarla sin validar.
- **Rationale**: la documentación de configuración por defecto define tres valores y
  `only_google_sql` es el único que "rechaza jobs con dialecto legacy SQL". Las opciones de proyecto
  llevan calificador regional, así que el ajuste solo vale en la región de la location del proyecto.
  El cambio tarda unos minutos en hacerse efectivo.
- **Alternatives considered**: `default_google_sql` (permite legacy si se pide explícitamente, no
  cumple la prohibición del principio II); fijarlo a nivel de organización (no hay organización en
  un proyecto personal).

## R2. Verificar el dialecto con solo dry runs

- **Decision**: el diagnóstico envía un dry run de `SELECT 1` forzando `--use_legacy_sql=true`. Si
  el proyecto lo rechaza, el ajuste está activo (OK). Si el dry run se valida, el ajuste no está
  activo en esa región (FALLO con el comando de `make gcp-dialect`). El quickstart incluye una
  validación única (V4) que confirma que el dry run discrimina: se ejecuta antes y después de
  aplicar el ajuste. Si V4 demostrara que la plataforma no aplica el rechazo a los dry runs, el
  chequeo pasa a OMITIDO con la instrucción de consultar
  `region-<loc>.INFORMATION_SCHEMA.PROJECT_OPTIONS` una sola vez en la consola.
- **Rationale**: consultar `INFORMATION_SCHEMA.PROJECT_OPTIONS` es una consulta real que factura el
  mínimo de 10 MB, y la spec (FR-009, SC-002) exige 0 bytes. El dry run es gratuito y se valida
  contra la configuración del job, que es donde la plataforma aplica el rechazo. La documentación
  no dice de forma explícita si el rechazo aplica a dry runs, por eso la validación V4 es
  obligatoria antes de dar el chequeo por bueno.
- **Alternatives considered**: consultar `PROJECT_OPTIONS` en cada `make doctor` (factura bytes);
  confiar solo en el `.bigqueryrc` (no prueba nada del proyecto); `bq show` del proyecto (no expone
  las opciones de configuración).
- **Excepción documentada**: este probe repite `--use_legacy_sql`, que `.bigqueryrc` ya fija. Es la
  única excepción a la regla del principio II y está en *Complexity Tracking*.

## R3. Dry run de GoogleSQL y location

- **Decision**: `bq --project_id=<P> --format=json query --dry_run 'SELECT 1'` sin flags de
  dialecto ni location (vienen de `.bigqueryrc`). Se parsea el JSON con Python y se compara
  `jobReference.location` con la location de `.bigqueryrc`. La referencia de `bq` no documenta la
  forma de la salida de un dry run, así que si no llega JSON o no trae la location, se marca AVISO
  con la location declarada en lugar de fallar. Los errores se clasifican por texto: API deshabilitada
  (`SERVICE_DISABLED` / `has not been used`), permiso (`Access Denied` / `bigquery.jobs.create`) o
  red.
- **Rationale**: el dry run es gratuito, no aparece en el historial de jobs y prueba a la vez
  credenciales, API, permisos y location. Python ya es prerrequisito, así que no se añade `jq`.
  El diagnóstico usa `.venv/bin/python` si existe y, si no, el `python3` del sistema (macOS y Linux
  lo traen); si no hay ninguno termina con código 2.
- **Alternatives considered**: `jq` (otra dependencia); `bq ls` (no prueba la creación de jobs).

## R4. Location del dataset existente

- **Decision**: `bq --project_id=<P> --format=json show farma_analytics`. Si no existe, el chequeo
  queda OMITIDO. Si existe, se compara su `location` con la de `.bigqueryrc` (FALLO si difiere).
- **Rationale**: lectura de metadatos sin costo. La location de un dataset no se puede cambiar.
- **Alternatives considered**: `INFORMATION_SCHEMA.SCHEMATA` (consulta facturable).

## R5. Autenticación: gcloud y ADC

- **Decision**: cuatro chequeos.
  1. Cuenta activa: `gcloud auth list --filter=status:ACTIVE --format='value(account)'`.
  2. ADC válido: `gcloud auth application-default print-access-token` termina con éxito.
  3. Proyecto de cuota de ADC: se lee la clave `quota_project_id` de
     `~/.config/gcloud/application_default_credentials.json` con Python (solo esa clave). AVISO si
     falta, con `gcloud auth application-default set-quota-project <P>`.
  4. Misma cuenta: se obtiene el correo de ADC con un POST a `https://oauth2.googleapis.com/tokeninfo`
     (el token va en el cuerpo, nunca en la URL). AVISO si difiere de la cuenta de `gcloud` o si no
     se puede obtener.
  Además, FALLO si `GOOGLE_APPLICATION_CREDENTIALS` apunta dentro del repositorio.
- **Rationale**: `bq` y `gcloud` usan la credencial de usuario de `gcloud`, mientras que Python y
  Dataform usan ADC. Si apuntan a cuentas o proyectos distintos, los errores aparecen más tarde y
  son difíciles de diagnosticar.
- **Alternatives considered**: comprobar solo ADC (no detecta que `bq` usa otra cuenta).

## R6. Resolución del proyecto

- **Decision**: `PROJECT_ID` sale de `GOOGLE_CLOUD_PROJECT` en `.env` si está definido, y si no, de
  `gcloud config get-value project`. El `Makefile` lo pasa a `bq` con `--project_id`. AVISO si
  ambos existen y difieren. FALLO si ninguno existe, y los chequeos de BigQuery quedan OMITIDOS.
- **Rationale**: el ID nunca va fijo en el código (principio VIII). Pasarlo explícito a `bq` evita
  el asistente interactivo que `bq` muestra la primera vez cuando no tiene proyecto por defecto.
- **Alternatives considered**: fijar `project_id` en `.bigqueryrc` (prohibido por la constitución);
  llamar a la variable `GOOGLE_CLOUD_PROJECT_ID` (descartado el 2026-10-07: `GOOGLE_CLOUD_PROJECT`
  es la variable que `google.auth.default()` y las bibliotecas cliente de Python leen para el
  proyecto por defecto, según `google.auth.environment_vars.PROJECT`).

## R7. Facturación activa

- **Decision**: `gcloud billing projects describe <P> --format='value(billingEnabled)'`. `True` es
  OK, `False` es AVISO (modo sandbox, sin presupuesto ni cuota, expiración de 60 días). Si el
  comando falla por permisos o por API deshabilitada, el chequeo queda OMITIDO con el motivo.
- **Rationale**: la spec trata la facturación como informativa en el diagnóstico.
- **Alternatives considered**: no comprobarla (el sandbox pasaría desapercibido).

## R8. Cuota diaria de consultas

- **Decision**: `make gcp-quota` usa Cloud Quotas:
  `gcloud quotas preferences update farma-query-usage-per-day --service=bigquery.googleapis.com
  --quota-id=QueryUsagePerDay --preferred-value=<v> --project=<P> --allow-missing
  --allow-high-percentage-quota-decrease` (el ID de la preferencia es posicional y la bajada desde
  200 TiB es mayor que el porcentaje que gcloud acepta sin ese flag). Antes,
  `gcloud quotas info describe QueryUsagePerDay --service=bigquery.googleapis.com --project=<P>
  --format=json` lee el campo `metricUnit` de la cuota, y el objetivo se detiene mostrando el
  valor leído si no empieza por `MiBy` (MiB por día). Valor: `QUERY_QUOTA_GIB_PER_DAY` de `.env` (100 GiB en `.env.example`), convertido a MiB por el
  script. El dueño pidió tener este valor en `.env` para ajustarlo sin tocar archivos versionados.
  Requiere la API `cloudquotas.googleapis.com` y el rol Quota Administrator
  (`roles/servicemanagement.quotaAdmin`).
- **Rationale**: `QueryUsagePerDay` es la cuota de proyecto (por defecto 200 TiB por día) y es un
  tope duro: al superarla BigQuery devuelve `usageQuotaExceeded` hasta la medianoche del Pacífico.
  `update --allow-missing` crea o actualiza, así que es idempotente, mientras que `create` falla si
  la preferencia ya existe. La consola expresa el valor en TiB, pero la API usa la unidad propia de
  la cuota, por eso se lee antes de escribir. Reducir la cuota aplica en minutos. 100 GiB por día
  deja margen de sobra para el volumen previsto y queda muy por debajo del nivel gratuito mensual
  de 1 TiB.
- **Alternatives considered**: solo pasos de consola (no son comandos idempotentes);
  `gcloud beta quotas` (la versión GA ya existe); cuota por usuario `QueryUsagePerUserPerDay` (en
  un proyecto de una sola persona no aporta).

## R9. Alerta de presupuesto

- **Decision**: `make gcp-budget` busca un presupuesto con nombre `farma-analytics-bigquery` en la
  cuenta de facturación de `.env` (`gcloud billing budgets list --billing-account=<B>
  --filter=displayName=farma-analytics-bigquery`). Si no existe, lo crea con
  `gcloud billing budgets create --billing-account=<B> --display-name=farma-analytics-bigquery
  --budget-amount=<BUDGET_AMOUNT> --filter-projects=projects/<P> --calendar-period=month
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
  --billing-project=<P>`. Si existe, lo actualiza con `gcloud billing budgets update <name>
  --billing-account=<B> --budget-amount=<BUDGET_AMOUNT> --calendar-period=month
  --filter-projects=projects/<P> --clear-threshold-rules --add-threshold-rule=percent=0.5
  --add-threshold-rule=percent=0.9 --add-threshold-rule=percent=1.0 --billing-project=<P>`. Según
  la referencia de `gcloud`, `update` no acepta `--threshold-rule` (solo existe en `create`): los
  umbrales se reemplazan borrándolos y añadiéndolos de nuevo. Los avisos
  van a los administradores y usuarios de la cuenta de facturación (comportamiento por defecto), así
  que no se versiona ningún correo. `BUDGET_AMOUNT` viene de `.env` con la moneda de la cuenta (por
  ejemplo `10USD`).
- **Rationale**: buscar por nombre antes de crear evita duplicados (FR-019, SC-006). La API de
  presupuestos exige proyecto de cuota, de ahí `--billing-project`. Requiere
  `billingbudgets.googleapis.com` y el rol Billing Account Administrator o Billing Account Costs
  Manager.
- **Alternatives considered**: canal de notificación con correo propio (dato personal versionado);
  Pub/Sub para cortar el gasto automáticamente (componente extra no justificado, la cuota ya es el
  tope duro).

## R10. Creación del proyecto

- **Decision**: el README documenta, en este orden y para que los ejecute el dueño:
  `gcloud projects create <P>`, `gcloud billing projects link <P> --billing-account=<B>`,
  `gcloud config set project <P>`, `gcloud services enable bigquery.googleapis.com
  billingbudgets.googleapis.com cloudquotas.googleapis.com cloudbilling.googleapis.com
  --project=<P>`, `gcloud auth login`, `gcloud auth application-default login` y
  `gcloud auth application-default set-quota-project <P>`. No hay objetivo de `make` para crear el
  proyecto porque se hace una sola vez y necesita decisiones del dueño (ID, cuenta).
- **Rationale**: aclaración de la spec (proyecto nuevo con facturación, FR-037).
- **Alternatives considered**: Terraform (componente extra, la constitución lo excluye sin
  justificación).

## R11. Versiones y dónde se fijan

- **Decision**: cada versión se declara una sola vez, en el archivo que lee su herramienta cuando
  existe (FR-003):
  - Python: `.python-version` con la versión exacta 3.12.x que ofrezca uv al implementar (la más
    reciente de la serie 3.12 con al menos 14 días publicada).
  - uv: `required-version = ">=0.12.0"` en `[tool.uv]` de `pyproject.toml` (mínima local, admite
    tu 0.12.9). CI fija la versión exacta 0.12.18 en el input `version` de `setup-uv`.
  - Herramientas de Python: grupo `dev` de `[dependency-groups]` en `pyproject.toml` con
    `sqlfluff==4.3.0`, `pre-commit==4.6.2` y `pytest==9.1.1`, más `uv.lock` versionado, que fija
    también las dependencias indirectas. `[project]` con `requires-python = ">=3.12"` y
    `[tool.uv] package = false` (proyecto no empaquetable). `make setup-dev` ejecuta
    `uv sync --locked`, que crea `.venv`.
  - Dataform CLI: `package.json` con `"@dataform/cli": "3.0.70"` y `package-lock.json` versionado,
    instalado con `npm ci`. `@dataform/core` llega con el proyecto Dataform en su propia feature.
  - Hooks: `pre-commit/pre-commit-hooks` en `rev: v6.0.0` (commit
    `3e8a8703264a2f4a69428a0aa4dcb512790b2c8c`).
  - Acciones de GitHub: `actions/checkout` v7.0.1 (`3d3c42e5aac5ba805825da76410c181273ba90b1`) y
    `astral-sh/setup-uv` v10.2.0 (`c18668ad3cf93ea998bef934396af7bb5c839dc7`), fijadas por SHA.
  - Resto de herramientas del sistema (mínimas): `scripts/tool_versions.env` con gcloud 500.0.0,
    bq 2.1.0, Node.js 22.0.0, ripgrep 14.0.0 y make 3.81.
- **Rationale**: se elige la versión más reciente con al menos 14 días publicada (sqlfluff 4.4.0,
  `@dataform/cli` 3.0.71 y uv 0.12.19 o posteriores son demasiado recientes). Node 20 dejó de
  tener soporte en abril de 2026, por eso el mínimo es Node 22. sqlfluff 4.x exige Python 3.10 o
  superior. macOS trae GNU Make 3.81 y bash 3.2, así que el `Makefile` y los scripts no usan
  funciones de versiones posteriores (`.ONESHELL`, arrays asociativos, `mapfile`).
- **Alternatives considered**: `requirements-dev.txt` con `venv` y `pip` (no fija la versión de
  Python ni las dependencias indirectas); instalaciones globales con pipx o `npm -g` (versiones
  distintas en cada máquina); fijar acciones por etiqueta mayor (una etiqueta puede moverse).

## R12. SQLFluff: reglas del principio II

- **Decision**: `.sqlfluff` con `dialect = bigquery`, `templater = raw`, `max_line_length = 100` y:
  - CP01 palabras clave `upper`, CP03 funciones `upper`, CP04 literales `upper`, CP05 tipos `upper`;
  - CP02 con `extended_capitalisation_policy = upper` limitado a alias de columna
    (`unquoted_identifiers_policy = column_aliases`), porque una sola política no admite columnas
    en UPPER_SNAKE_CASE y alias de tabla en snake_case a la vez;
  - AL01 y AL02 `aliasing = explicit`, AL03 expresiones con alias, AL06 `min_alias_length = 3`
    (prohíbe `a`, `b`, `c`);
  - AM04 (sin `SELECT *` de columnas indeterminadas), AM05 `fully_qualify_join_types = inner`,
    AM06 `group_by_and_order_by_style = explicit`;
  - CV03 `select_clause_trailing_comma = forbid`, ST07 (sin `USING`), RF02 (columnas calificadas
    con varias tablas);
  - operadores `AND`/`OR` al inicio de línea con `line_position = leading` para
    `binary_operator`.
  El contrato de las reglas es el par de ejemplos de `tests/fixtures/sql/` y su prueba: si una
  opción cambió de nombre en sqlfluff 4.3.0, la prueba falla y se ajusta la configuración.
- **Rationale**: SC-008 exige que cada violación sembrada se detecte. Lo que SQLFluff no puede
  verificar (por ejemplo, el orden hechos antes que catálogos, joins con coma o el comentario de
  cabecera) queda para la revisión manual contra el principio II.
- **Alternatives considered**: desactivar CP02 por completo (pierde la verificación de alias de
  columna).

## R13. pre-commit y CI

- **Decision**:
  - Hook `sqlfluff-lint` local con `entry: .venv/bin/sqlfluff lint` y `language: unsupported`, de
    modo que la versión sale solo de `pyproject.toml` y `uv.lock`. Desde pre-commit 4.4.0, `system` es un
    alias obsoleto de `unsupported` que se eliminará en una versión futura. La configuración declara
    `minimum_pre_commit_version: "4.4.0"`.
  - Hook `detect-private-key` de `pre-commit-hooks` (detecta claves de cuenta de servicio por
    contenido).
  - Hook local `forbid-credential-files` con `language: fail` sobre nombres: `.env` y `.env.*`
    salvo `.env.example`, `.df-credentials.json`, `application_default_credentials.json`,
    `*service-account*.json`, `*-key.json`, `*.p12`.
  - Exclusión de `tests/fixtures/` para que los ejemplos con violaciones no rompan el repositorio.
  - Workflow `.github/workflows/checks.yml` en `pull_request` hacia `main`: checkout,
    `setup-uv` con `version: "0.12.18"`, `uv sync --locked` (descarga el Python de
    `.python-version`) y `uv run pre-commit run --all-files --show-diff-on-failure`, el mismo
    comando que `make lint`. Sin secretos ni credenciales de
    GCP, permisos `contents: read`.
- **Rationale**: aclaración de la spec (SQLFluff y bloqueo de secretos en hooks y CI, lint de
  prosa a mano). Un hook local con el binario de `.venv` mantiene una sola fuente de versión.
- **Alternatives considered**: hook oficial de sqlfluff con su propia `rev` (dos lugares con la
  versión); gitleaks (otra herramienta, `detect-private-key` y la lista de nombres cubren los tres
  tipos de la spec).

## R14. Lint de prosa

- **Decision**: `scripts/lint_prosa.sh` en bash compatible con 3.2, con ripgrep (motor por defecto,
  sin PCRE2).
  - Preproceso: copia cada archivo a un directorio temporal conservando la ruta, sustituye por
    líneas en blanco los bloques de código y las líneas de comentario de excepción, y borra el
    código en línea y las URL. En los `.sql` conserva solo los comentarios. El número de línea no
    cambia.
  - Los restos de herramientas se buscan en el texto original, antes de quitar URL.
  - Categorías: raya y semirraya, guion como raya (`\S - \S` fuera de marcadores de lista),
    punto y coma en prosa, emojis (`\p{Extended_Pictographic}`), flechas y caracteres de caja,
    comillas curvas, Title Case en encabezados, listas con cabecera en negrita, restos de
    herramientas y muletillas.
  - `scripts/muletillas.txt`: una entrada por línea, `#` para comentarios, frase literal sin
    distinguir mayúsculas y con límites de palabra. Las líneas con prefijo `re:` son expresiones
    regulares para cubrir conjugaciones.
  - Excepciones: `scripts/prosa_excepciones.txt` con términos de dominio permitidos y nombres
    propios para la regla de Title Case, y el marcador de línea `lint-prosa: ignorar` dentro de un
    comentario HTML (`<!-- lint-prosa: ignorar -->`) o SQL (`-- lint-prosa: ignorar`).
  - Alcance por defecto: `README.md`, `docs/**/*.md` y los comentarios de `sql/**/*.sql`. Excluye
    `specs/`, `.specify/`, archivos de configuración, `scripts/muletillas.txt` y
    `scripts/prosa_excepciones.txt`. Acepta rutas o `-` para leer la entrada estándar.
  - Salida: `ruta:línea: categoría: fragmento`, código 1 si hay marcas y 2 si hay un error de uso.
- **Rationale**: el motor de ripgrep entiende propiedades Unicode y límites de palabra Unicode, que
  bastan para estas reglas. ripgrep no permite renombrar la entrada estándar, por eso el preproceso
  usa una copia temporal con la misma ruta.
- **Alternatives considered**: Vale o proselint (herramienta extra y sin reglas en español);
  PCRE2 (no siempre viene compilado en ripgrep).

## R15. Pruebas automatizadas de esta feature

- **Decision**: pytest en `tests/`:
  - `test_sqlfluff_config.py`: el ejemplo conforme da 0 violaciones y cada violación sembrada
    aparece con su regla.
  - `test_lint_prosa.py`: una violación por categoría, documento limpio sin marcas, usos permitidos
    del guion, excepciones, entrada estándar y exclusión de Spec Kit.
  - `test_doctor.py`: el diagnóstico corre con un `PATH` de stubs falsos de `gcloud`, `bq`, etc.,
    y reproduce los 8 escenarios de fallo de SC-003 sin tocar GCP.
  Se ejecutan con `make test`, sin red ni credenciales.
- **Rationale**: el principio IV ya fija pytest como herramienta de pruebas. Los stubs permiten
  verificar SC-003 en local y de forma repetible.
- **Alternatives considered**: bats (otra herramienta); pruebas manuales (no repetibles).

## R16. Valores de costo iniciales

- **Decision**: `maximum_bytes_billed = 1073741824` (1 GiB por consulta) en `.bigqueryrc`, cuota de
  100 GiB por día (en `.env`) y presupuesto mensual definido por el dueño en `.env` con avisos al 50 %, 90 % y
  100 %. Se revisan cuando exista el volumen real de la feature de generación.
- **Rationale**: BigQuery factura un mínimo de 10 MB por tabla referenciada, así que 1 GiB no
  bloquea consultas normales sobre tablas de pocos cientos de MB y corta escaneos accidentales.
- **Alternatives considered**: 10 GiB por consulta (margen innecesario con este volumen); mover el límite por
  consulta a `.env` (descartado por el dueño el 2026-10-07: `bq` no lee variables de entorno en
  `.bigqueryrc` y la constitución fija ahí el valor como única fuente, así que exigiría enmendarla y
  generar el archivo en cada ejecución). La cuota diaria sí vive en `.env`.

## R17. uv como gestor de Python y dependencias

- **Decision**: uv sustituye a `venv` y `pip`. `.python-version` fija Python, `pyproject.toml`
  declara el grupo `dev`, `uv.lock` fija todo el árbol, `make setup-dev` ejecuta `uv sync --locked`
  y los objetivos usan `uv run`. El hook de SQLFluff sigue apuntando a `.venv/bin/sqlfluff`, que es
  el entorno que crea uv.
- **Rationale**: el análisis encontró que el `.venv` local se crearía con Python 3.14 mientras CI usa
  3.12, sin ningún archivo que fije la versión, y la tabla de stack de la constitución exige Python
  "con versión fijada". uv descarga la versión fijada si falta, así que el dueño no instala Python
  a mano, y el lockfile cubre también las dependencias indirectas. El dueño ya tiene uv instalado.
- **Alternatives considered**: `.python-version` con pyenv (otra herramienta y sin lockfile);
  instalar Python 3.12 con Homebrew y seguir con `venv` y `pip` (no fija las dependencias
  indirectas).

## R18. Vulnerabilidades conocidas de Dataform CLI (riesgo aceptado)

- **Decision**: se mantiene `@dataform/cli` 3.0.70 aceptando las 5 vulnerabilidades que reporta
  `npm audit` (crítica en `vm2`, altas en `braces`, `chokidar` y `parse-duration`). Se vuelve a
  evaluar al empezar la feature de Dataform.
- **Rationale**: la 3.0.71 también fija `vm2` 3.11.6, así que ninguna versión publicada corrige la
  crítica. `vm2` es el sandbox con el que Dataform compila el SQLX del propio repositorio, que es
  código de confianza, y la herramienta solo corre en local (CI no instala dependencias de Node).
  El dueño eligió esta opción el 2026-10-07.
- **Alternatives considered**: forzar `vm2` 3.12.2 con `overrides` (puede romper la compilación y
  hoy no hay proyecto Dataform con que probarlo); pasar a 3.0.71 (solo corrige `parse-duration` y
  tiene menos de 14 días).

## Fuentes

- BigQuery, configuración por defecto: `docs.cloud.google.com/bigquery/docs/default-configuration`
- BigQuery, cuotas personalizadas: `docs.cloud.google.com/bigquery/docs/custom-quotas`
- gcloud quotas preferences: `docs.cloud.google.com/sdk/gcloud/reference/quotas/preferences/create`
- gcloud quotas preferences update e info describe: `docs.cloud.google.com/sdk/gcloud/reference/quotas/preferences/update`, `.../quotas/info/describe`
- gcloud billing budgets create: `docs.cloud.google.com/sdk/gcloud/reference/billing/budgets/create`
- bq, `.bigqueryrc` y flags de `query`: `docs.cloud.google.com/bigquery/docs/reference/bq-cli-reference`
- pre-commit, lenguajes de hooks (`unsupported`, `fail`): `pre-commit.com`
- SQLFluff, reglas de capitalización y ambigüedad: `docs.sqlfluff.com/en/stable/reference/rules/`
- Registros: PyPI (sqlfluff, pre-commit, pytest), npm (`@dataform/cli`), GitHub releases
  (`pre-commit-hooks`, `actions/checkout`, `astral-sh/setup-uv`).
- uv, dependencias y versiones de Python: `docs.astral.sh/uv/concepts/projects/dependencies/`,
  `docs.astral.sh/uv/concepts/python-versions/`, `docs.astral.sh/uv/reference/settings/`
