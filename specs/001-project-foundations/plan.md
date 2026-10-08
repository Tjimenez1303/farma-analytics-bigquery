# Implementation Plan: Fundaciones del proyecto (entorno local, proyecto de GCP y diagnóstico)

**Branch**: `001-project-foundations` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-project-foundations/spec.md`

## Summary

La feature deja el repositorio listo para que cualquier persona lo clone y compruebe con
`make doctor`, sin facturar más que dry runs, que tiene las herramientas, la autenticación, el
proyecto, el dialecto y la location correctos. El enfoque es un `Makefile` compatible con GNU Make
3.81 que exporta `BIGQUERYRC` hacia un `.bigqueryrc` versionado, uv para fijar Python 3.12 y las
dependencias de desarrollo con lockfile, scripts en bash 3.2 (diagnóstico y lint de prosa) que usan
Python solo para leer JSON, objetivos idempotentes para los ajustes de
GCP (dialecto con `ALTER PROJECT`, cuota con Cloud Quotas y presupuesto con Cloud Billing Budgets),
SQLFluff y bloqueo de secretos en pre-commit y en GitHub Actions, y pruebas con pytest que usan
stubs para reproducir los fallos del diagnóstico sin tocar GCP. El dueño ejecuta todo lo que toca
GCP o instala herramientas, y el README le da la secuencia exacta. Las decisiones están en
[research.md](research.md).

## Technical Context

**Language/Version**: bash 3.2 o superior (scripts), GNU Make 3.81 o superior, Python 3.12 fijado
en `.python-version` y gestionado por uv (herramientas de desarrollo y parseo de JSON), Node.js 22 o
superior (Dataform CLI),
GoogleSQL (DDL del ajuste de dialecto y ejemplos de estilo).

**Primary Dependencies**: Google Cloud CLI (`gcloud`, `bq`), uv 0.12 o superior (0.12.18 en CI),
ripgrep 14 o superior, SQLFluff 4.3.0, pre-commit 4.6.2 con `pre-commit-hooks` v6.0.0, pytest
9.1.1, `@dataform/cli` 3.0.70, GitHub Actions (`actions/checkout` v7.0.1 y `astral-sh/setup-uv`
v10.2.0 fijadas por SHA).

**Storage**: N/A. La feature no crea datasets ni tablas. Solo lee metadatos del dataset
`farma_analytics` si ya existe.

**Testing**: pytest (`make test`) para la configuración de SQLFluff, el lint de prosa y el
diagnóstico con stubs. Validación manual de extremo a extremo con [quickstart.md](quickstart.md).

**Target Platform**: macOS (bash 3.2, Make 3.81 de serie) y Linux. Windows solo mediante WSL. CI en
`ubuntu-latest`.

**Project Type**: repositorio de analítica con herramientas de línea de comandos (Makefile y
scripts). Sin aplicación ni servicio.

**Performance Goals**: `make doctor` en 60 segundos o menos (SC-002). Arranque desde el clon hasta
diagnóstico correcto en 15 minutos o menos con las herramientas ya instaladas (SC-001).

**Constraints**: 0 bytes facturados por el diagnóstico (solo dry runs y metadatos). Ningún ID de
proyecto, cuenta de facturación o correo en archivos versionados. Una sola fuente para cada valor:
location y límite de bytes en `.bigqueryrc`; cada versión en el archivo que lee su herramienta
(`.python-version`, `pyproject.toml` y `uv.lock`, `package.json` y `package-lock.json`, `rev` de
los hooks) y las mínimas del resto de herramientas del sistema en `scripts/tool_versions.env`. Ningún texto versionado menciona el
documento de requisitos de origen.

**Scale/Scope**: una persona por proyecto de GCP. 24 chequeos en el diagnóstico,
11 objetivos de `make`, 10 categorías en el lint de prosa.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Puerta | Evaluación inicial | Tras el diseño |
|---|---|---|
| G1 Contrato | PASS. No crea objetos impuestos. El diagnóstico usa el nombre exacto `farma_analytics`. La matriz de trazabilidad llega en su propia feature, y esta solo aporta la base de reproducibilidad (principio VIII). | PASS. Sin cambios. |
| G2 SQL | PASS. Único SQL de la feature: el `ALTER PROJECT` y los ejemplos de estilo. Dialecto fijado por `.bigqueryrc` y por el ajuste de proyecto. Sin `#standardSQL`. | PASS con una excepción justificada: el probe del diagnóstico fuerza `--use_legacy_sql=true` para comprobar el rechazo (ver *Complexity Tracking*). |
| G3 Modelado | N/A. Sin tablas ni vista. | N/A. |
| G4 Calidad | N/A para datos. Las herramientas nuevas tienen pruebas propias (R15). | PASS. `make test` cubre SQLFluff, lint de prosa y diagnóstico. |
| G5 Datos | N/A. El README declara que los datos son sintéticos (FR-035). | PASS. |
| G6 Dashboard | N/A. | N/A. |
| G7 Negocio | N/A. | N/A. |
| G8 Simplicidad y seguridad | PASS con dos justificaciones: el workflow de GitHub Actions (pedido en la aclaración de la spec) y uv (sustituye a `venv` y `pip`). ADC con login de usuario, `.env` ignorado, sin claves de cuenta de servicio, ID de proyecto fuera del código. | PASS. `package.json` y pytest no son componentes nuevos: los exige la constitución (Dataform CLI con versión exacta, pytest). uv cumple la exigencia de la tabla de stack de fijar la versión de Python. |
| G9 Escritura | PASS. El README debe pasar `scripts/lint_prosa.sh` (FR-035). | PASS. El quickstart incluye la verificación (V9). |

Resultado: sin violaciones sin justificar. Se puede pasar a tareas.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-foundations/
├── plan.md              # Este archivo
├── research.md          # Decisiones de la fase 0
├── data-model.md        # Entidades de configuración y del informe
├── quickstart.md        # Guía de validación de extremo a extremo
├── contracts/
│   ├── make-targets.md  # Objetivos de make: entradas, efectos y quién los ejecuta
│   ├── doctor.md        # Catálogo de chequeos, estados, salida y códigos
│   ├── lint-prosa.md    # Uso, categorías, formatos de lista y excepciones
│   └── config-files.md  # Contenido obligatorio de los archivos versionados
├── checklists/
│   └── requirements.md
└── tasks.md             # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
.
├── .bigqueryrc                      # location, dialecto y maximum_bytes_billed (sin proyecto)
├── .env.example                     # variables locales con valores de ejemplo
├── .gitignore                       # .env, credenciales, .venv, node_modules
├── .sqlfluff                        # reglas del principio II
├── .sqlfluffignore                  # tests/fixtures/
├── .pre-commit-config.yaml          # sqlfluff-lint, detect-private-key, forbid-credential-files
├── .github/
│   └── workflows/
│       └── checks.yml               # pre-commit en cada PR hacia main, sin GCP
├── Makefile                         # exporta BIGQUERYRC, objetivos de la feature
├── README.md                        # arranque rápido
├── package.json                     # @dataform/cli exacto
├── package-lock.json
├── .python-version                  # versión de Python fijada (3.12.x)
├── pyproject.toml                   # proyecto no empaquetable, grupo dev exacto, required-version de uv
├── uv.lock                          # lockfile completo de Python
├── scripts/
│   ├── doctor.sh                    # diagnóstico
│   ├── gcp_quota.sh                 # cuota diaria idempotente
│   ├── gcp_budget.sh                # presupuesto idempotente
│   ├── lint_prosa.sh                # lint de prosa
│   ├── muletillas.txt               # lista versionada del principio IX
│   ├── prosa_excepciones.txt        # términos de dominio y nombres propios permitidos
│   └── tool_versions.env            # versiones mínimas de herramientas del sistema
└── tests/
    ├── conftest.py                  # utilidades de stubs y rutas
    ├── fixtures/
    │   ├── sql/                     # conforme.sql y no_conforme.sql
    │   ├── prosa/                   # limpio.md, violaciones.md, usos_permitidos.md, comentarios.sql
    │   └── stubs/                   # gcloud, bq, rg, node... falsos para el diagnóstico
    ├── test_sqlfluff_config.py
    ├── test_lint_prosa.py
    └── test_doctor.py
```

**Structure Decision**: un solo repositorio sin código de aplicación. La lógica vive en
`scripts/` y se invoca desde el `Makefile`. Las pruebas viven en `tests/`, que la constitución ya
prevé, y sus ejemplos en `tests/fixtures/`, excluidos de SQLFluff, de pre-commit y del alcance por
defecto del lint de prosa. `docs/`, `sql/`, `generator/`, `data/` y `dataform/` llegan en features
posteriores.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Workflow de GitHub Actions (componente fuera del stack de la constitución) | La aclaración de la spec pide que SQLFluff y el bloqueo de secretos corran en cada PR, porque los hooks locales se pueden saltar con `--no-verify` y la constitución exige que los chequeos pasen antes de integrar. | Ejecutar `pre-commit run --all-files` a mano antes de cada PR depende de la memoria del autor y no deja constancia en el PR. |
| uv (binario fuera del stack de la constitución) | La tabla de stack exige Python "con versión fijada" y versiones exactas. uv fija la versión de Python en `.python-version`, la descarga si falta y genera un lockfile con las dependencias indirectas, igual en local y en CI. | `venv` y `pip` con `requirements-dev.txt` no fijan la versión de Python (local tenía 3.14 y CI 3.12) ni las dependencias indirectas. |
| El probe del diagnóstico repite `--use_legacy_sql` (que `.bigqueryrc` ya fija) | Es la única forma de comprobar con un dry run gratuito que el proyecto rechaza legacy SQL (R2). | Consultar `INFORMATION_SCHEMA.PROJECT_OPTIONS` factura un mínimo de 10 MB en cada ejecución e incumple SC-002. |
