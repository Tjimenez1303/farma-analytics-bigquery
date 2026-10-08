# Implementation Plan: Generador de datos sintéticos (COMPRAS, CLUE_CAT y CUADRO_BASICO)

**Branch**: `002-synthetic-data-generator` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-synthetic-data-generator/spec.md`

## Summary

La feature añade un generador en Python que escribe las tres fuentes del proyecto en CSV, con los
campos exactos de los requisitos, y un manifiesto SHA-256 que prueba que la misma configuración
produce los mismos bytes. El enfoque:

- un paquete `generator/` que se ejecuta con `uv run python -m generator`;
- NumPy 2.5.3 con un `SeedSequence` raíz y un flujo independiente por componente (`spawn`);
- Faker 40.39.0 `es_MX` solo para apellidos de empresas ficticias;
- catálogos de referencia versionados con fuentes oficiales (INEGI, DGIS, DOF y Compendio);
- importes calculados en centavos enteros a partir de un precio unitario redondeado una sola vez;
- huérfanos exactos al 0.5 %;
- tres patrones comerciales (P3, P4 y P5) que sostienen los hallazgos;
- una configuración TOML leída con la biblioteca estándar;
- escritura atómica, verificación contra la copia versionada del manifiesto y objetivos `make
  data`, `make data-verify` y `make data-manifest`;
- pruebas pytest que también corren en GitHub Actions.

Las decisiones están en [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12.14 (`.python-version`), gestionado por uv. GNU Make 3.81.

**Primary Dependencies**: `numpy==2.5.3` y `faker==40.39.0` en `[project].dependencies`. Biblioteca
estándar para el resto: `tomllib`, `csv`, `hashlib`, `json`, `os`, `tempfile`, `argparse`,
`datetime`. Sin pandas, pyarrow ni pydantic. Herramientas de desarrollo: pytest 9.1.1, SQLFluff
4.3.0, pre-commit 4.6.2 y, nuevo, Ruff 0.16.8 (lint y formato, research R18).

**Storage**: archivos locales. `data/` (ignorado por git) con tres CSV y `manifest.json`.
Versionados: `generator/config.toml`, `generator/manifest.json` y `generator/reference/*`.

**Testing**: pytest en `tests/generator/` (`make test` y job `tests` en CI), configurado en
`[tool.pytest]` con `--import-mode=importlib` y `strict = true` (research R19). Ruff en pre-commit
y CI. Validación manual con [quickstart.md](quickstart.md).

**Target Platform**: macOS (máquina del dueño) y Linux (`ubuntu-latest` en CI). La igualdad byte a
byte se exige en el mismo entorno (aclaración sobre NumPy).

**Project Type**: herramienta de línea de comandos dentro del repositorio de analítica, sin
empaquetar (`[tool.uv] package = false`).

**Performance Goals**: generación completa en menos de 2 minutos (SC-003). Suite de pruebas en menos
de 2 minutos (SC-002).

**Constraints**: sin red ni GCP durante la generación. Salida independiente de la hora, la zona
horaria, el locale y el directorio de trabajo. Tamaño total por debajo de 100 MB. Ningún parámetro
fuera de `generator/config.toml`. Sin nombres de empresas reales en fabricantes, marcas o
proveedores. Ningún texto versionado menciona el documento de requisitos de origen.

**Scale/Scope**: unas 300 000 líneas de compra, 2 000 unidades médicas, 160 claves (139
moléculas), 12 fabricantes innovadores, 28 genéricos y 60 proveedores, entre 2024-01-01 y 2025-12-31.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Puerta | Evaluación inicial | Tras el diseño |
|---|---|---|
| G1 Contrato | PASS. Archivos con el nombre exacto de cada tabla y encabezados con los campos exactos en el orden de los requisitos (FR-001). La matriz de trazabilidad recibe las filas de "Materiales e Insumos" (FR-034). | PASS. [contracts/csv-format.md](contracts/csv-format.md) fija los encabezados y una prueba los compara literalmente. |
| G2 SQL | N/A. La feature no escribe SQL. Los tipos de [data-model.md](data-model.md) son los que exige el principio II (`DATE`, `INT64`, `NUMERIC`, claves `STRING`). | PASS. `IMPORTE` con dos decimales exactos, claves con ceros a la izquierda y fechas `YYYY-MM-DD`, compatibles con una carga con esquema explícito. |
| G3 Modelado | PASS. Grano y llave de cada tabla declarados antes de crearla. Huérfanos deliberados, así que no habrá claves foráneas (principio III). | PASS. [data-model.md](data-model.md) declara grano, llave y orden de filas de las tres fuentes. |
| G4 Calidad | PASS. pytest de determinismo, integridad referencial y rangos (principio IV). El manifiesto da los conteos para el chequeo posterior a la carga. | PASS. La suite también mide los patrones (SC-007a) y la verificación detecta archivos alterados. |
| G5 Datos | PASS. Semilla y parámetros en un archivo versionado, versiones exactas, manifiesto SHA-256, CSV UTF-8 sin BOM, `orphan_rate` explícito, `IMPORTE = PIEZAS × precio` con precio base × factor × ruido, cola larga, estacionalidad, instituciones reales, 32 nombres del INEGI, formatos verosímiles, coherencia marca-fabricante, dos años completos y datos declarados sintéticos. | PASS. P3 respeta la fórmula de precio (sin factor por institución). Los patrones inyectados se documentan en `docs/datos_sinteticos.md`. |
| G6 Dashboard | N/A. Los datos cubren los filtros obligatorios (fechas, entidad, institución, grupo institucional, grupo terapéutico y molécula). | N/A. |
| G7 Negocio | PASS. P3 y P4 sostienen los dos hallazgos principales y P5 uno de reserva. Las cifras saldrán de consultar la vista, no de los parámetros (principio VII). | PASS. |
| G8 Simplicidad y seguridad | PASS. Solo se añaden NumPy y Faker, que exige la tabla de stack. TOML con la biblioteca estándar. Sin credenciales ni ID de proyecto. Sin datos personales. | PASS con una justificación: Ruff, elegido por el dueño (ver *Complexity Tracking*). El job `tests` amplía el workflow ya justificado en la feature 001. |
| G9 Escritura | PASS. README y `docs/datos_sinteticos.md` deben pasar `scripts/lint_prosa.sh` (FR-033). | PASS. `docs/` está en el alcance por defecto del lint. La verificación está en el quickstart (V7). |

Resultado: una justificación registrada y ninguna violación sin justificar. Se puede pasar a tareas.

## Project Structure

### Documentation (this feature)

```text
specs/002-synthetic-data-generator/
├── plan.md               # Este archivo
├── research.md           # Decisiones de la fase 0
├── data-model.md         # Fuentes, entidades internas, referencia, configuración y manifiesto
├── quickstart.md         # Guía de validación de extremo a extremo
├── contracts/
│   ├── cli-and-make.md   # Subcomandos, códigos de salida y objetivos de make
│   ├── config.md         # Estructura y validación de generator/config.toml
│   ├── manifest.md       # Formato y comparación del manifiesto
│   └── csv-format.md     # Formato de los tres CSV
├── checklists/
│   └── requirements.md
└── tasks.md              # Lo genera /speckit-tasks
```

### Source Code (repository root)

```text
.
├── .github/workflows/checks.yml     # + job tests (uv sync --locked, uv run pytest)
├── .pre-commit-config.yaml          # + hooks locales ruff-check y ruff-format
├── .gitignore                       # + data/
├── Makefile                         # + data, data-verify, data-manifest
├── README.md                        # + sección de datos sintéticos y regeneración
├── pyproject.toml                   # + dependencias, ruff en dev, [tool.pytest] y [tool.ruff]
├── uv.lock                          # regenerado por el dueño con uv lock
├── generator/
│   ├── __init__.py
│   ├── __main__.py                  # argparse: generate | verify
│   ├── config.py                    # carga con tomllib y validación (código 2)
│   ├── rng.py                       # SeedSequence raíz y flujos por componente
│   ├── reference.py                 # lectura de generator/reference/
│   ├── units.py                     # CLUE_CAT
│   ├── supplies.py                  # CUADRO_BASICO, fabricantes, marcas, proveedores, precios
│   ├── purchases.py                 # COMPRAS, patrones P3-P5 y huérfanos
│   ├── pipeline.py                  # orquesta la generación completa
│   ├── writer.py                    # CSV y reemplazo atómico
│   ├── manifest.py                  # huellas, manifiesto y verificación
│   ├── config.toml                  # semilla y parámetros
│   ├── manifest.json                # copia de referencia del manifiesto
│   └── reference/
│       ├── entidades.csv
│       ├── municipios.csv
│       ├── instituciones.csv
│       ├── moleculas.csv
│       └── laboratorios_reales.txt
├── data/                            # ignorado por git
│   ├── COMPRAS.csv
│   ├── CLUE_CAT.csv
│   ├── CUADRO_BASICO.csv
│   └── manifest.json
├── docs/
│   ├── datos_sinteticos.md          # campos, reglas, patrones inyectados y fuentes
│   └── trazabilidad.md              # filas de "Materiales e Insumos"
└── tests/
    └── generator/
        ├── conftest.py              # generación completa por sesión y configuración reducida
        ├── fixtures/config_small.toml
        ├── test_config.py
        ├── test_determinism.py
        ├── test_contract.py
        ├── test_integrity.py
        ├── test_ranges.py
        ├── test_realism.py
        ├── test_patterns.py
        └── test_manifest.py
```

**Structure Decision**: el generador vive en `generator/` y los datos en `data/`, como prevé la
estructura orientativa de la constitución. Es un paquete importable desde la raíz porque el
proyecto no se empaqueta (`package = false`) y `python -m` añade el directorio actual al
`sys.path`. Los catálogos de referencia van junto al código porque son entradas versionadas del
generador, y las pruebas siguen en `tests/`. La matriz de trazabilidad se crea en esta feature
porque es la primera que cubre requisitos de datos. Las features siguientes le añaden filas.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Ruff (herramienta fuera de la tabla de stack de la constitución) | El dueño pidió los estándares de calidad de los repositorios de Python de referencia, que usan un linter y formateador. Sin él, el código que genera los datos no tendría un chequeo automático de estilo, mientras que el SQL sí lo tiene con SQLFluff. | Revisar el estilo a mano no es repetible ni deja constancia en el PR. mypy además de Ruff se descartó por añadir otra herramienta sin una necesidad medida. |
