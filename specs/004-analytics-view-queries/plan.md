# Implementation Plan: Vista modelada y consultas analíticas (secciones 3 y 4 del `.sql`)

**Branch**: `004-analytics-view-queries` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-analytics-view-queries/spec.md`

## Summary

La feature completa la Fase 2. Añade a `sql/farma_analytics.sql` la vista
`farma_analytics.v_compras_farma_completa` (sección 3) y las consultas que responden las tres
preguntas comerciales (sección 4), y extiende el programa `warehouse` para desplegarlas, verificarlas
y ejecutarlas. El enfoque:

- **La vista** es una sola sentencia `CREATE OR REPLACE VIEW`:
  - lleva una lista de 22 columnas con `OPTIONS(description = ...)`, que fue la aclaración Q1 (R1);
  - une las tablas con `INNER JOIN ... ON`, con `COMPRAS` primero y alias semánticos;
  - las columnas que pasan sin cambio de nombre van sin alias y las demás con `AS`, para cumplir la
    regla AL09 de SQLFluff (R2, aclaración Q3);
  - añade tres derivaciones por fila: `ANIO`, `MES` y `ENTIDAD_ISO` (R3).
- **Las consultas** son cuatro sentencias que leen solo de la vista (R5):
  - P1 usa `ORDER BY ... LIMIT 5` con desempate por nombre y `AVG` para el importe promedio por
    línea;
  - P2 usa `GROUPING SETS`, `UNPIVOT` y `QUALIFY RANK()` para dar el líder por `IMPORTE` y por
    `PIEZAS` en tres niveles;
  - P3 calcula el precio con `SAFE_DIVIDE` por molécula y `FABRICANTE_COMPRA`, y la alternativa con
    `FABRICANTE_CATALOGO`.
- **La calidad** se refuerza en tres puntos:
  - un séptimo chequeo, `07_reconciliacion_vista.sql`, compara la vista con las tablas base y busca
    nulos en las derivadas (R7);
  - ese chequeo tiene un caso negativo con filas en línea de la vista (R8);
  - la verificación de metadatos se extiende a la vista: tipo, dialecto, descripciones y tipos de
    sus 22 columnas.
- **La operación** queda así (R9):
  - carga y vista desacopladas, según la aclaración Q2;
  - `make bq-vista` despliega la vista y ejecuta los siete chequeos;
  - `make bq-load` ejecuta el chequeo de la vista solo si la vista existe;
  - `make bq-consultas` imprime las respuestas y comprueba cinco cifras cruzadas (R6, R10 y R11).
- **Pruebas y documentación**: pruebas pytest sin GCP (R12), README con el glosario y las
  definiciones de las ambigüedades, y matriz de trazabilidad de la Fase 2 (R13).

Las decisiones y sus fuentes oficiales están en [research.md](research.md).

## Technical Context

**Language/Version**: GoogleSQL (BigQuery) para la vista, las consultas, el chequeo y los totales.
Python 3.12.14 (`.python-version`) con uv para `warehouse`. GNU Make 3.81.

**Primary Dependencies**:

- `bq` (Google Cloud SDK, validado por `make doctor`);
- SQLFluff 4.3.0 (grupo `dev`), que analiza el `.sql`;
- biblioteca estándar de Python (`json`, `decimal`, `dataclasses`, `re`);
- `generator.reference` para los 32 nombres de entidad en las pruebas.

No hay dependencias nuevas.

**Storage**: BigQuery, dataset `farma_analytics` en `US`. Se añade una vista lógica que no almacena
datos. Las tablas base no cambian.

**Testing**: pytest en `tests/warehouse/` con el ejecutor falso de `bq` (sin red ni credenciales),
SQLFluff en pre-commit y validación contra BigQuery con [quickstart.md](quickstart.md), que ejecuta el
dueño.

**Target Platform**: macOS del dueño para los objetivos que tocan GCP, consola de BigQuery para el
`.sql` completo y Linux (`ubuntu-latest`) para las pruebas en CI.

**Project Type**: SQL entregable más la herramienta de línea de comandos `warehouse` del repositorio.

**Performance Goals**: el despliegue de la vista, los siete chequeos y las cuatro consultas terminan
en menos de 5 minutos (SC-006).

**Constraints**:

- ningún comando repite los flags de `.bigqueryrc`, y cada job de consulta lleva antes un dry run y
  labels estáticas;
- ninguna consulta supera 1 GiB facturado. Cada una lee como máximo las columnas que usa de
  `COMPRAS` y de los catálogos, unos pocos MB;
- en la vista no hay `SELECT *`, agregados, `DISTINCT`, `ORDER BY`, `ROUND`, precios por fila, ID de
  proyecto, expiración ni limpieza de datos;
- en las consultas, `ROUND` y `ORDER BY` solo en el `SELECT` final, `GROUP BY` con nombres y solo
  funcionalidades GA;
- comentarios SQL en inglés, descripciones y documentación para lectores en español (principio IX);
- nada versionado menciona el documento de requisitos ni el ID del proyecto.

**Scale/Scope**:

- la vista tiene 298 500 filas;
- P1 devuelve 5 filas, P2 6 o más (si hay empates), P3 497 y P3_CATALOGO 139;
- un despliegue de la vista ejecuta 1 DDL, 7 chequeos y 1 verificación de metadatos;
- `make bq-consultas` ejecuta 1 consulta de totales (que lo detiene si la vista no tiene filas) y 4
  consultas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Antes de la investigación

| Puerta | Estado | Evidencia |
|---|---|---|
| G1 Contrato | PASA | Nombre exacto `v_compras_farma_completa`; `INNER JOIN` con `CLUE_CAT` por `CLUE` y con `CUADRO_BASICO` por `CLAVE` (FR-002); las tres preguntas (FR-010 a FR-012); ambigüedades definidas con ambas interpretaciones (FR-011, FR-012, FR-015); trazabilidad de la Fase 2 (FR-026). |
| G2 SQL | PASA con justificación | Alias semánticos, `INNER JOIN ... ON`, `GROUP BY` con nombres, `SAFE_DIVIDE`, `ROUND` solo al presentar, top-N con `LIMIT`, top por grupo con `QUALIFY` (FR-002, FR-014), dry run y SQLFluff (FR-022, FR-025). La lista de columnas de la vista se aparta de una preferencia (ver Complexity Tracking). |
| G3 Modelado | PASA | Vista lógica con lista explícita de columnas, grano declarado y sin agregados (FR-001 a FR-005); precio calculado al consumir (FR-012); consultas solo sobre la vista (FR-009); descripciones en la vista y en cada columna (FR-006). |
| G4 Calidad | PASA | Reconciliación de la vista con caso negativo (FR-016, FR-017), metadatos de la vista (FR-018) y chequeos después de cada carga y de cada cambio en la vista (FR-019). |
| G5 Datos | PASA | Sin cambios en el generador. La descripción del dataset ya declara que los datos son sintéticos. |
| G6 Dashboard | N/A | Fuera de alcance. La vista deja listos `ENTIDAD_ISO`, `ANIO` y `MES`. |
| G7 Negocio | PASA | Glosario único de métricas y cifras que cuadran entre consultas (FR-023, SC-002). Los hallazgos son de otra feature. |
| G8 Simplicidad y seguridad | PASA | Sin herramientas ni dependencias nuevas, sin tablas auxiliares, sin ID de proyecto ni credenciales (FR-027). |
| G9 Escritura | PASA | README y trazabilidad en español con `make lint-prosa` (FR-026). |

### Después del diseño (Fase 1)

| Puerta | Estado | Evidencia del diseño |
|---|---|---|
| G1 Contrato | PASA | [data-model.md](data-model.md) fija las 22 columnas, las cuatro respuestas y la tabla de definiciones. [contracts/vista.md](contracts/vista.md) y [contracts/consultas.md](contracts/consultas.md) convierten el contrato en pruebas locales. |
| G2 SQL | PASA con justificación | Borrador comprobado con SQLFluff 4.3.0: la vista con lista de columnas, `GROUPING SETS`, `GROUPING()`, `UNPIVOT` y `QUALIFY` se analizan sin errores (R1, R5). `GROUPING SETS` y `GROUPING()` son GA. `CAST` explícito de `PIEZAS` a `NUMERIC` en `UNPIVOT` porque la referencia no admite coerción (R5). La violación AL09 de los alias repetidos se evita sin excepciones en `.sqlfluff` (R2, aclaración Q3). |
| G3 Modelado | PASA | Ventanas en lugar de self-joins para los totales (R5). Una lectura de la vista en P2 gracias a `GROUPING SETS`. Derivaciones sin limpieza (R3). |
| G4 Calidad | PASA | Chequeo 07 sin parámetros y con contrato común (R7). Caso negativo que simula una vista rota en lugar de reconstruirla (R8). Metadatos con `type`, `useLegacySql` y descripciones (contracts/checks.md). Momento de ejecución por objetivo definido (R9). |
| G7 Negocio | PASA | Cifras cruzadas C1 a C5 exactas con `Decimal` (R6). |
| G8 Simplicidad y seguridad | PASA | Una consulta de apoyo en `sql/ops/` y un diccionario de tres tipos (R4). Ninguna tabla, dataset ni herramienta nueva. Dataform sin tocar (R14). |
| G9 Escritura | PASA | Definiciones y glosario en el README, con cifras sacadas de `make bq-consultas` (R13). |

Resultado: sin violaciones sin justificar y sin decisiones pendientes. Se puede pasar a
`/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/004-analytics-view-queries/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1 a R15 con fuentes
├── data-model.md        # Fase 1: vista, glosario, definiciones, respuestas y estructuras
├── quickstart.md        # Fase 1: validación V0 a V8
├── contracts/
│   ├── vista.md         # Sección 3 y reglas que se prueban
│   ├── consultas.md     # Sección 4, reglas y cifras cruzadas
│   ├── checks.md        # Chequeo 07, caso negativo y metadatos de la vista
│   └── make-targets.md  # bq-vista, bq-consultas y cambios en los objetivos existentes
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
sql/
├── farma_analytics.sql                  # Añade la sección 3 (vista) y la sección 4 (P1, P2, P3, P3_CATALOGO)
├── checks/
│   ├── 07_reconciliacion_vista.sql      # Nuevo: vista frente a tablas base y derivadas sin nulos
│   └── negativos/
│       └── 07_reconciliacion_vista.json # Nuevo: filas base y filas de una vista rota
└── ops/
    └── totales_vista.sql                # Nuevo: filas, IMPORTE y PIEZAS de la vista (cifras cruzadas)

warehouse/
├── __main__.py                  # Subcomandos nuevos: vista y consultas
├── commands.py                  # run_view, run_queries; run_load y run_checks con la vista
├── ddl.py                       # ViewSpec, DERIVED_TYPES, sentencias create_view y query
├── metadata.py                  # Comparación de la vista; verify con vista opcional
├── checks.py                    # Chequeos de vista, inline de la vista en casos negativos
└── queries.py                   # Nuevo: ejecución de la sección 4, impresión y cifras cruzadas

tests/warehouse/
├── test_view_sql.py             # Nuevo: reglas de contracts/vista.md
├── test_queries_sql.py          # Nuevo: reglas de contracts/consultas.md
├── test_view_parser.py          # Nuevo: ViewSpec y tipos derivados
├── test_view_command.py         # Nuevo: make bq-vista con el bq falso
├── test_queries_command.py      # Nuevo: make bq-consultas con el bq falso
├── test_cross_figures.py        # Nuevo: C1 a C5
├── test_metadata.py             # Ampliado: vista
├── test_load_command.py         # Ampliado: con y sin vista
├── test_checks_command.py       # Ampliado: siete chequeos y vista ausente
├── test_checks_sql.py           # Ampliado: chequeo 07
└── test_negative_checks.py      # Ampliado: inline de la vista

tests/fixtures/sql/ddl_minima.sql  # Ampliado con una vista mínima para el analizador

Makefile                         # bq-vista y bq-consultas
README.md                        # Fase 2: recorrido, glosario y definiciones
docs/trazabilidad.md             # Filas de la Fase 2
```

**Structure Decision**: se mantiene la estructura de la feature 003. La lógica de las consultas va
en un módulo propio, `warehouse/queries.py`, porque imprime resultados y compara cifras, lo que no
encaja en `checks.py`. La consulta de totales va en `sql/ops/` junto a la huella, porque no es un
chequeo ni una pregunta del entregable.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| La vista usa `view_column_name_list`, aunque la constitución (principio III) prefiere los alias del `SELECT` | Es la única forma de fijar la descripción de cada columna dentro de `CREATE VIEW` (referencia DDL, `view_column_option_list`), y la FR-006 exige que las descripciones sobrevivan a cada `CREATE OR REPLACE` (aclaración Q1) | Solo alias en el `SELECT` y 22 sentencias `ALTER VIEW ... ALTER COLUMN`: un `CREATE OR REPLACE` ejecutado solo borra las descripciones, y el `.sql` crece 22 sentencias. La lista cumple la condición de la constitución: tiene tantos nombres como columnas y lo comprueba una prueba |
| No se usa Dataform (SHOULD de la tabla de stack) ni se crea su `declaration` de la vista | Sigue vigente la decisión de la feature 003 (aclaración Q2 y research R13 de esa feature): los chequeos viven en `sql/checks/` y `@dataform/cli` tiene el riesgo R18 | Ver el Complexity Tracking de `specs/003-bigquery-data-load/plan.md`. Crear solo la `declaration` de la vista no aporta nada sin un proyecto Dataform |
| Diccionario `DERIVED_TYPES` con los tipos de tres columnas calculadas | Los tipos de la vista hacen falta para los metadatos y para el caso negativo, y no se pueden leer de la DDL para las expresiones | Leer el esquema del dry run exige GCP en las pruebas, e inferir tipos desde el árbol de SQLFluff es mucho código para tres columnas. Una prueba ata el diccionario a la vista |
