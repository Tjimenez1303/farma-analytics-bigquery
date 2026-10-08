# Implementation Plan: Dashboard comercial en Data Studio (Fase 3)

**Branch**: `005-dashboard-data-studio` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-dashboard-data-studio/spec.md`

## Summary

La feature completa la Fase 3: un informe de Data Studio de una sola página sobre
`farma_analytics.v_compras_farma_completa`, su especificación versionada y las consultas que
demuestran que sus cifras coinciden con el SQL. El enfoque:

- **Fuente**: una fuente reutilizable conectada a la vista sin consulta personalizada, con
  *Owner's credentials*, frescura de 12 horas y los 22 campos configurados en la fuente (nombre de
  negocio, tipo y agregación). Precio Promedio es un campo calculado,
  `SUM(IMPORTE) / NULLIF(SUM(PIEZAS), 0)` (R1, R2).
- **Página**: lienzo de 1600 × 900 con rejilla de 10 px y la disposición de la maqueta aprobada el
  2026-10-08 ([data-model.md](data-model.md#rejilla-y-disposición)):
  - cabecera con título, subtítulo de transparencia, cinco listas desplegables en cascada, el rango
    de fechas fijo en 2025 y el botón "Restablecer filtros" (R3, R4);
  - tres tarjetas comparadas con el periodo anterior de la misma duración (con el rango por
    defecto, 2024-01-02 a 2024-12-31) y el recuadro "Hallazgos clave" (R5, R17);
  - barras de las 32 entidades a toda la altura, Geo chart de México, barras de las 7 instituciones
    con su porcentaje y tabla del top 10 molécula-fabricante (R6 a R9);
  - tema propio con un color de datos (`#0072B2`), un acento (`#B34700`), Roboto en tres tamaños y
    contrastes medidos (R10).
- **Especificación escrita**: `docs/dashboard.md`, con pruebas locales que comprueban los campos,
  los contrastes y los tamaños de letra (R15).
- **Verificación contra el SQL**: cinco consultas en `sql/dashboard/` con los filtros como
  parámetros de arreglo, y `make bq-dashboard`, que las ejecuta con dry run y labels, imprime las
  cifras del tablero y comprueba las cifras cruzadas D1 a D4 (R12).
- **Construcción**: Claude en el Chrome del dueño, paso a paso y con capturas, pidiendo
  confirmación antes de credenciales, avisos y permisos. La comprobación sin sesión se hace en el
  navegador integrado de la app y en una ventana de incógnito del dueño (R14).
- **Documentación**: sección del dashboard en el README y Fase 3 en la matriz de trazabilidad (R18).

Las decisiones y sus fuentes están en [research.md](research.md). La documentación de Data Studio no
tiene una guía de diseño visual, así que las reglas de diseño se apoyan en la teoría de
visualización y en WCAG, verificadas en R13.

## Technical Context

**Language/Version**: GoogleSQL (BigQuery) para las consultas de verificación. Python 3.12.14
(`.python-version`) con uv para `warehouse`. GNU Make 3.81. Data Studio (versión web vigente al
2026-10-08) para el informe.

**Primary Dependencies**:

- Data Studio con el conector de BigQuery (sin coste de licencia);
- `bq` (Google Cloud SDK, validado por `make doctor`);
- SQLFluff 4.3.0 (grupo `dev`);
- biblioteca estándar de Python (`argparse`, `datetime`, `decimal`, `json`, `re`).

No hay dependencias nuevas de Python.

**Storage**: BigQuery, dataset `farma_analytics` en `US`. No se crean tablas, vistas ni datasets.
Data Studio guarda el informe y la fuente en la cuenta de Google del dueño.

**Testing**:

- pytest en `tests/warehouse/` con el `bq` falso (sin red ni credenciales) para las consultas y el
  subcomando;
- pytest en `tests/docs/` para `docs/dashboard.md`;
- SQLFluff y `scripts/lint_prosa.sh` en pre-commit;
- validación en BigQuery y Data Studio con [quickstart.md](quickstart.md).

**Target Platform**: Data Studio en el navegador, para lectores sin cuenta de Google con el enlace.
macOS del dueño para `make bq-dashboard`. Linux (`ubuntu-latest`) para las pruebas en CI.

**Project Type**: informe de BI más la herramienta de línea de comandos `warehouse` del repositorio.

**Performance Goals**:

- la página principal carga con datos en menos de 10 segundos sin sesión (SC-001);
- `make bq-dashboard` termina en menos de 2 minutos.

**Constraints**:

- cada consulta de `make bq-dashboard` lleva dry run, labels y el `maximum_bytes_billed` de
  `.bigqueryrc` (1 GiB), sin repetir sus flags;
- las consultas que lanza Data Studio no pasan por `.bigqueryrc` y las limita la cuota diaria de
  100 GiB del proyecto (R16);
- una sola página 16:9 sin scroll, con como máximo 50 gráficos por página (límite de Data Studio,
  aquí se usan 7 componentes de datos);
- comentarios SQL en inglés y documentación para lectores en español con el principio IX;
- nada versionado menciona el documento de requisitos ni el ID del proyecto.

**Scale/Scope**:

- la fuente lee 298 500 filas de la vista y Data Studio lanza una consulta por componente de datos
  (unas 15 por carga de página, contando los controles);
- `make bq-dashboard` ejecuta 7 consultas;
- `docs/dashboard.md` describe 22 campos, 1 campo calculado, 6 controles, 1 botón, 3 tarjetas,
  4 gráficos y 1 recuadro de texto.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitución v1.4.3. En esta rama, la v1.4.1 corrigió la razón de no usar "Auto", la v1.4.2
sustituyó la lectura en F o Z por la regla de Few y añadió el matiz de contraste de Okabe-Ito, y la
v1.4.3 aclaró que una escala de color que codifica una medida no es un degradado decorativo y que se
admite una leyenda cuando no caben etiquetas directas.

### Antes de la investigación

| Puerta | Estado | Evidencia |
|---|---|---|
| G1 Contrato | PASA | Fuente conectada a `v_compras_farma_completa` (FR-001). Los cuatro filtros de la Fase 3 (FR-006), los tres KPIs con sus nombres (FR-013), las tres visualizaciones (FR-016, FR-018, FR-019) y el enlace de lectura (FR-028). Trazabilidad de la Fase 3 (FR-036). |
| G2 SQL | PASA | Consultas de verificación con el estilo del principio II, SQLFluff, dry run, labels y límite de bytes (FR-031, FR-032). |
| G3 Modelado | PASA | Una sola capa semántica: el tablero y las consultas leen de la vista. Precio Promedio calculado al consumir, sin `AVG` (FR-005). La vista no cambia. |
| G4 Calidad | PASA | No hay datos nuevos. La coincidencia tablero-SQL se comprueba con D1 a D4 y con el registro de verificación (FR-033). |
| G5 Datos | PASA | El subtítulo declara que los datos son sintéticos (FR-026) y el recuadro marca los patrones inyectados (FR-027). |
| G6 Dashboard | PASA | Todos los controles, KPIs y visuales. Diseño, accesibilidad y compartición del principio VI (FR-006 a FR-029). |
| G7 Negocio | PASA | Las cifras del recuadro de hallazgos salen de `make bq-dashboard` y coinciden con el tablero. |
| G8 Simplicidad y seguridad | PASA | Sin herramientas, dependencias ni objetos nuevos en BigQuery. Sin ID de proyecto ni credenciales en el repositorio (FR-037). Confirmación del dueño antes de credenciales y permisos (FR-002, FR-028). |
| G9 Escritura | PASA | `docs/dashboard.md`, README y trazabilidad con `make lint-prosa` (FR-030, FR-036). |

### Después del diseño (Fase 1)

| Puerta | Estado | Evidencia del diseño |
|---|---|---|
| G1 Contrato | PASA | [data-model.md](data-model.md) fija cada control, tarjeta y gráfico con su campo de la vista. R18 define una fila de trazabilidad por requisito de la Fase 3. |
| G2 SQL | PASA | Borrador con parámetros `ARRAY<STRING>` y `UNNEST` sin violaciones de SQLFluff 4.3.0. Parámetros de arreglo porque BigQuery no admite parámetros NULL (R12). Bloque de filtros idéntico vigilado por una prueba ([contracts/verificacion-sql.md](contracts/verificacion-sql.md)). |
| G3 Modelado | PASA | Campos configurados en la fuente con su ID igual al nombre de la columna (R2, R3). El porcentaje de instituciones es una configuración del gráfico, no un campo, porque un porcentaje del total no se puede calcular por fila (R7). Las alternativas de R2, R9 y R11 son campos calculados en la fuente, nunca cambios en la vista. |
| G4 Calidad | PASA | D1 a D4 con resultados exactos en `Decimal` y tolerancia solo en porcentajes. Estados inicial, filtrado, ampliado y vacío definidos ([data-model.md](data-model.md#estados-del-tablero)). |
| G6 Dashboard | PASA con riesgos registrados | Cada regla del principio VI tiene componente y verificación. Riesgos sin documentar en Data Studio, con alternativa escrita que cumple la constitución: flechas de la tarjeta (R5), "Percent of total" en barras (R7), moneda MXN y `NULLIF` (R2), sufijos compactos (R11), Reset y el rango de fechas (R4), `MX-CMX` (R9), Roboto y el tamaño del valor de la tarjeta (R10). El mapa lleva leyenda de escala, que la constitución v1.4.3 admite cuando no caben etiquetas directas (R9). El top 10 tiene grano molécula-fabricante, con la definición escrita (R8). |
| G7 Negocio | PASA | Cifras esperadas del estado inicial calculadas en local y reproducibles con `make bq-dashboard` ([data-model.md](data-model.md#cifras-esperadas-del-estado-inicial)). |
| G8 Simplicidad y seguridad | PASA | Sin vistas materializadas, BI Engine ni extracts (R16). Sin función de tabla ni objetos nuevos (R12). Las credenciales del propietario evitan cuentas de servicio (R1). |
| G9 Escritura | PASA | Secciones de `docs/dashboard.md` fijadas en [contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md), con pruebas locales de campos, contrastes y tamaños de letra. |

Resultado: sin violaciones sin justificar y sin decisiones pendientes. Se puede pasar a
`/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/005-dashboard-data-studio/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones R1 a R18 con fuentes
├── data-model.md        # Fase 1: fuente, campos, rejilla, controles, componentes, consultas y cifras
├── quickstart.md        # Fase 1: validación V0 a V8
├── contracts/
│   ├── especificacion-dashboard.md  # Secciones de docs/dashboard.md y reglas que se prueban
│   └── verificacion-sql.md          # sql/dashboard/, make bq-dashboard y D1 a D4
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
sql/
└── dashboard/                              # Nuevo: consultas de verificación del tablero
    ├── kpis.sql
    ├── kpis_por_anio.sql
    ├── gasto_entidad.sql
    ├── participacion_institucion.sql
    └── top10_molecula_fabricante.sql

warehouse/
├── __main__.py          # Subcomando nuevo: dashboard, con sus opciones de filtro
├── commands.py          # run_dashboard
└── dashboard.py         # Nuevo: filtros, periodo de referencia, ejecución, impresión y D1 a D4

tests/
├── warehouse/
│   ├── test_dashboard_sql.py       # Nuevo: reglas de las consultas de sql/dashboard/
│   └── test_dashboard_command.py   # Nuevo: subcomando con el bq falso, parámetros y D1 a D4
└── docs/
    └── test_dashboard_spec.py      # Nuevo: campos, contrastes y tamaños de docs/dashboard.md

docs/
├── dashboard.md         # Nuevo: especificación del informe y registro de verificación
└── trazabilidad.md      # Filas de la Fase 3

Makefile                 # bq-dashboard
README.md                # Sección del dashboard y enlace de lectura
```

**Structure Decision**: se mantiene la estructura de las features 003 y 004. Las consultas del
tablero van en `sql/dashboard/` y no en la sección 4 de `sql/farma_analytics.sql`, porque son
verificaciones con parámetros y no respuestas del entregable. Su lógica va en
`warehouse/dashboard.py`, separada de `queries.py`, porque tiene filtros, periodo de referencia y
otras cifras cruzadas. Las pruebas de la especificación van en `tests/docs/`, porque comprueban un
documento y no el paquete `warehouse`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| El porcentaje de participación por institución se configura en el gráfico ("Percent of total") y no en la fuente, aunque FR-004 pide configurar los campos en la fuente | Un porcentaje del total depende de los filtros activos y no se puede calcular por fila en un campo de la fuente (R7) | Un campo calculado con el total fijo daría porcentajes incorrectos en cuanto se filtra. Calcularlo en la vista exige agregar, prohibido por el principio III |
| El bloque de filtros se repite en las cinco consultas de `sql/dashboard/` | Cada archivo se puede leer y ejecutar solo, y una prueba exige que el bloque sea idéntico (R12) | Una función de tabla o una vista con parámetros crea objetos nuevos en el dataset (principio VIII). Montar el SQL en Python impide revisarlo con SQLFluff |
