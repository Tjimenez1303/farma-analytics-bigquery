---

description: "Task list for feature 004-analytics-view-queries"
---

# Tasks: Vista modelada y consultas analíticas (secciones 3 y 4 del `.sql`)

**Input**: Design documents from `specs/004-analytics-view-queries/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluidos. La spec exige pruebas automatizadas locales (FR-008, FR-014) y el plan fija
pytest sin GCP en `tests/warehouse/` (research R12). En cada historia se escriben antes de la
implementación y deben fallar primero.

**Organization**: tareas agrupadas por historia de usuario para implementarlas y probarlas por
separado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia a la que pertenece (US1 a US5).
- **[Dueño]** al inicio de la descripción: la ejecuta el dueño porque toca GCP. Claude escribe
  archivos, ejecuta solo verificaciones locales (`make test`, `make lint`, `make lint-sql`,
  `make lint-prosa`, pytest, sqlfluff, ruff) y le da al dueño los comandos exactos, en orden, uno por
  bloque, con la explicación de cada flag y la salida esperada.

## Reglas transversales (aplican a todas las tareas)

- Python 3.12 con anotaciones de tipo, `from __future__ import annotations`, `dataclasses`
  inmutables (`frozen=True`) y `pathlib.Path`. Docstrings y comentarios en inglés, breves, que dicen
  qué es cada cosa. Sin dependencias nuevas.
- Los mensajes que ve el usuario (salida de `python -m warehouse`, errores, ayuda de `make`) van en
  español. Nombres de tabla, columna, archivo y parámetro se escriben tal cual.
- `bq` solo se invoca a través de `warehouse.bq.execute`. Ningún comando repite `--location`,
  `--use_legacy_sql` ni `--maximum_bytes_billed`. Toda consulta que se ejecuta va precedida por su
  dry run con el mismo SQL y los mismos parámetros, y lleva las labels de `BQ_JOB_LABELS`. El SQL
  viaja por la entrada estándar.
- SQL: GoogleSQL con las reglas del principio II y de `.sqlfluff`:
  - palabras clave en mayúsculas, `AS` en todo alias, sin alias que repita el nombre de origen
    (AL09), referencias simples antes que expresiones en cada `SELECT` (ST06);
  - alias de tabla semánticos (`compras`, `clue_cat`, `cuadro_basico`, `vista` y el nombre de la
    CTE), `INNER JOIN ... ON` con `COMPRAS` primero como único join;
  - `GROUP BY` por nombre, `SAFE_DIVIDE` en cocientes, `ROUND` y `ORDER BY` solo en el `SELECT`
    final, `CAST` explícito, sin `SELECT *` y sin ID de proyecto;
  - comentarios en inglés y breves que dicen qué es cada objeto y para qué existe, o qué pregunta de
    negocio responde, sin repetir reglas de la constitución.
- Descripciones de la vista y de sus columnas en español, sin comillas simples ni `;`, con los
  textos de [data-model.md](data-model.md).
- Ningún archivo versionado menciona el documento de requisitos de origen ni contiene IDs de
  proyecto, correos o credenciales.
- Antes de afirmar que el lint pasa sobre archivos nuevos, hacer `git add` de esos archivos, porque
  `pre-commit run --all-files` no revisa archivos sin versionar.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: confirmar el punto de partida y preparar el fixture del analizador.

- [X] T001 Ejecutar `make test`, `make lint` y `make lint-prosa` en la rama `004-analytics-view-queries` y confirmar que todo pasa antes de cambiar código
- [X] T002 [P] Ampliar `tests/fixtures/sql/ddl_minima.sql` (excluido por `.sqlfluffignore`) con una sentencia `CREATE OR REPLACE VIEW ejemplo.v_ejemplo` entre las tablas y el `SELECT` final: lista de columnas `ID OPTIONS (description = 'Llave de UNO.')`, `CANTIDAD OPTIONS (description = 'Cantidad de DOS.')` y `ANIO OPTIONS (description = 'Año de DIA.')`, `OPTIONS (description = 'Vista de prueba.')` y `AS SELECT uno.ID, dos.CANTIDAD, EXTRACT(YEAR FROM dos.DIA) AS ANIO FROM ejemplo.UNO AS uno INNER JOIN ejemplo.DOS AS dos ON uno.ID = dos.ID`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: que `warehouse` entienda la vista y las consultas (análisis, metadatos y casos
negativos), que usan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

### Pruebas (escribir primero, deben fallar)

- [X] T003 [P] Actualizar `tests/warehouse/test_ddl_parser.py`: la lista de `(kind, target)` del fixture pasa a ser `create_schema`, `create_table` ×2, `("create_view", "ejemplo.v_ejemplo")` y `("query", "")`; `parsed.tables` sigue con dos tablas (la vista no es una tabla); `parsed.view` no es `None` (depende de T002)
- [X] T004 [P] Crear `tests/warehouse/test_view_parser.py` sobre el fixture: `ViewSpec` con `dataset = "ejemplo"`, `name = "v_ejemplo"`, `ref = "ejemplo.v_ejemplo"`, `description = "Vista de prueba."` y columnas en orden con nombre y descripción de la lista; tipos `ID: STRING` y `CANTIDAD: INT64` resueltos por alias desde los `TableSpec`, `ANIO: INT64` desde `DERIVED_TYPES`; `mode = "NULLABLE"` en todas; `DdlError` si la lista y el `SELECT` tienen distinto número de columnas, si el nombre de salida de un elemento del `SELECT` (alias o, sin alias, nombre de la columna) no coincide con el de la lista en la misma posición, o si una columna calculada no está en `DERIVED_TYPES`; `Ddl.view is None` en un SQL sin vista (depende de T002)
- [X] T005 [P] Ampliar `tests/warehouse/test_metadata.py` con la vista según [contracts/checks.md](contracts/checks.md#verificación-de-metadatos-de-la-vista-fr-018): `compare(dataset, tables, show, view=spec)` sin diferencias devuelve `[]`; informa con `CHEQUEO="esquema_ddl"` un `type` distinto de `VIEW` ("tipo de objeto"), `view.useLegacySql` distinto de `false` ("dialecto de la vista"), la descripción de la vista, una columna de más, de menos, en otra posición, otro tipo (`INTEGER` equivale a `INT64`) u otra descripción; no compara el modo; si `bq show` de la vista da "not found", devuelve una diferencia con `DETALLE` "Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'"; con `view=None` no llama a `bq show` para la vista; `object_exists(ref, show)` devuelve `True`, `False` con "not found" y lanza un error con el mensaje de `bq` en cualquier otro fallo
- [X] T006 [P] Ampliar `tests/warehouse/test_negative_checks.py`: `inline_tables(sql, case, relations)` sustituye también `farma_analytics.v_compras_farma_completa AS vista` por un `SELECT` sobre `UNNEST(ARRAY<STRUCT<...>>[...])` con las 22 columnas y sus tipos del `ViewSpec`, con valores convertidos con `CAST`; lanza `ValueError` si el caso no trae filas para una relación que el SQL referencia; `references_view(sql)` es `True` solo si la vista aparece fuera de comentarios y cadenas
- [X] T007 Ampliar `tests/warehouse/conftest.py`: el `bq show` falso responde para `farma_analytics.v_compras_farma_completa` con `{"type": "VIEW", "view": {"query": "...", "useLegacySql": false}, "description": ..., "schema": {"fields": [...]}}` construido desde el `ViewSpec` del `.sql` (con `_API_TYPES` para `INT64`), y una opción de la fixture (por ejemplo `fake_bq.missing_view = True`) hace que responda "Not found: Table" con código 1

### Implementación

- [X] T008 Ampliar `warehouse/ddl.py` según [research.md](research.md) R4 y R10 y [data-model.md](data-model.md#viewspec-análisis-de-la-sección-3): `Statement.kind` admite `create_view` (cuerpo `create_view_statement`, `target` igual a la referencia) y `query` (`select_statement` o `with_compound_statement`); `ViewSpec` (`dataset`, `name`, `description`, `query`, `columns`, propiedad `ref`); `DERIVED_TYPES = {"ANIO": "INT64", "MES": "DATE", "ENTIDAD_ISO": "STRING"}`; `Ddl.view: ViewSpec | None`. Los nombres y las descripciones salen de los `column_definition` del `bracketed` de la vista. El tipo de un elemento `column_reference` sale del `TableSpec` de la tabla cuyo alias aparece en el `FROM` o en un `INNER JOIN`. El de un elemento calculado sale de `DERIVED_TYPES`. Lanza `DdlError` en los casos de T004 (depende de T003 y T004)
- [X] T009 Ampliar `warehouse/metadata.py`: `compare(..., view: ViewSpec | None = None)` y `verify(dataset, tables, view=None)` con la comparación de T005; `object_exists(ref, show=None) -> bool`; el mensaje de vista ausente es "Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'" y `missing_objects` lo sigue detectando (depende de T005, T007 y T008)
- [X] T010 Ampliar `warehouse/checks.py`: `inline_tables(sql, case, relations)` con `relations` igual a las tablas más la vista (mismo `_inline_select`, que solo usa `name` y `type`); `references_view(sql)`; `run_sql_checks(expectations, include_view=True)`, que con `include_view=False` no ejecuta los chequeos que referencian la vista, imprime "La vista no está desplegada: ejecuta 'make bq-vista'." y los descuenta del total; `run_negative_checks(expectations, relations)` (depende de T006 y T008)
- [X] T011 Ejecutar `make test` y `uv run ruff check warehouse tests/warehouse` y confirmar que T003 a T006 pasan y que las pruebas existentes siguen en verde (depende de T008 a T010)

**Checkpoint**: `warehouse` entiende la vista y las consultas; las historias pueden empezar.

---

## Phase 3: User Story 1 - Publicar la vista modelada para BI (Priority: P1) 🎯 MVP

**Goal**: `make bq-vista` despliega la vista desde la sección 3 y ejecuta los siete chequeos; la carga
no toca la vista y verifica su chequeo solo si existe.

**Independent Test**: con las tablas cargadas, `make bq-vista` termina con "Chequeos: 7 de 7 en 0
filas. Metadatos: 0 diferencias." y `bq show` muestra `type = VIEW`, la descripción y las 22 columnas
descritas (quickstart V1 a V4).

### Pruebas (escribir primero, deben fallar)

- [X] T012 [P] [US1] Crear `tests/warehouse/test_view_sql.py` con las reglas 1 a 11 de [contracts/vista.md](contracts/vista.md) sobre `sql/farma_analytics.sql`, usando `warehouse.ddl.parse_file` y el árbol de SQLFluff. La lista oficial ISO 3166-2:MX se fija en la prueba como diccionario de 32 pares con los valores de la tabla "Mapeo ENTIDAD → ENTIDAD_ISO" de [data-model.md](data-model.md), y se compara con los nombres de `generator/reference/entidades.csv` (columna `entidad`) y con las ramas `WHEN` del `CASE`. Las 22 columnas esperadas, en orden y con su tipo, son las de la tabla de la vista de data-model
- [X] T013 [P] [US1] Crear `tests/warehouse/test_view_command.py` con `fake_bq` y `warehouse_env`: `run_view()` hace el dry run y después la ejecución de la sentencia `create_view` con el mismo texto, y no ejecuta las sentencias `create_schema`, `create_table` ni `query`; imprime "[1/1] CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa: dry run OK (<N> bytes estimados), ejecutada"; si falta el dataset o una tabla, sale con 1 y "ejecuta 'make bq-schema'" sin llamar al dry run; si el dry run falla, sale con 1 sin ejecutar; al terminar ejecuta los siete chequeos y la verificación de metadatos con la vista, y sale con 0 solo si todo da 0
- [X] T014 [P] [US1] Ampliar `tests/warehouse/test_checks_sql.py`: la lista de archivos esperados añade `07_reconciliacion_vista.sql` (y la prueba se renombra a `test_exactly_the_seven_checks`); el chequeo 07 no usa parámetros, referencia la vista y las tres tablas base, y su `SELECT` final cumple el contrato común
- [X] T015 [P] [US1] Ampliar `tests/warehouse/test_load_command.py`: con `fake_bq.missing_view = True`, `run_load()` ejecuta seis chequeos, imprime "La vista no está desplegada: ejecuta 'make bq-vista'.", termina con 0 y ningún comando enviado contiene `CREATE OR REPLACE VIEW`; con la vista presente ejecuta los siete chequeos y verifica los metadatos de la vista
- [X] T016 [P] [US1] Ampliar `tests/warehouse/test_checks_command.py`: el mensaje de éxito pasa a "Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias."; con la vista ausente, `run_checks()` sale con 1 e imprime "Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'"

### Implementación

- [X] T017 [US1] Añadir la sección 3 a `sql/farma_analytics.sql` según [contracts/vista.md](contracts/vista.md) y [data-model.md](data-model.md):
  - un comentario `-- Section 3: view.` y un comentario en inglés que dice qué es la vista y para qué existe (por ejemplo, `-- Single semantic layer for the analytical queries and the dashboard: one row per purchase line with both catalogs.`);
  - `CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa (` con las 22 columnas en este orden, cada una con `OPTIONS (description = '<texto de la columna Descripción de data-model>')`: `CLUE`, `CLAVE`, `COD_PROVEEDOR`, `MARCA`, `FABRICANTE_COMPRA`, `PIEZAS`, `IMPORTE`, `FECHA`, `ENTIDAD`, `INSTITUCION`, `DELEGACION`, `GRUPO_INSTITUCIONAL`, `NIVEL_ATENCION`, `MUNICIPIO`, `DESCRIPCION`, `MOLECULA`, `GRUPO_TERAPEUTICO`, `PRESENTACION`, `FABRICANTE_CATALOGO`, `ANIO`, `MES`, `ENTIDAD_ISO`;
  - `OPTIONS (description = '<descripción de la vista de data-model>')`;
  - `AS SELECT` con `compras.CLUE`, `compras.CLAVE`, `compras.COD_PROVEEDOR`, `compras.MARCA`, `compras.FABRICANTE AS FABRICANTE_COMPRA`, `compras.PIEZAS`, `compras.IMPORTE`, `compras.FECHA`, `clue_cat.ENTIDAD`, `clue_cat.INSTITUCION`, `clue_cat.DELEGACION`, `clue_cat.GRUPO_INSTITUCIONAL`, `clue_cat.NIVEL_ATENCION`, `clue_cat.MUNICIPIO`, `cuadro_basico.DESCRIPCION`, `cuadro_basico.MOLECULA`, `cuadro_basico.GRUPO_TERAPEUTICO`, `cuadro_basico.PRESENTACION`, `cuadro_basico.FABRICANTE AS FABRICANTE_CATALOGO`, `EXTRACT(YEAR FROM compras.FECHA) AS ANIO`, `DATE_TRUNC(compras.FECHA, MONTH) AS MES` y `CASE clue_cat.ENTIDAD WHEN '<nombre>' THEN '<código>' ... END AS ENTIDAD_ISO` con las 32 ramas de la tabla de mapeo de data-model y sin `ELSE`;
  - `FROM farma_analytics.COMPRAS AS compras INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico ON compras.CLAVE = cuadro_basico.CLAVE INNER JOIN farma_analytics.CLUE_CAT AS clue_cat ON compras.CLUE = clue_cat.CLUE` (orden de research R1b, sin comentario que lo cite);
  - las columnas que pasan sin cambio de nombre no llevan alias (AL09) y no hay `WHERE`, agregados, `DISTINCT`, `ORDER BY`, `ROUND` ni `CAST` (depende de T012)
- [X] T018 [P] [US1] Crear `sql/checks/07_reconciliacion_vista.sql` según [contracts/checks.md](contracts/checks.md#chequeo-07-sqlchecks07_reconciliacion_vistasql) con la forma de `sql/checks/05_reconciliacion_join.sql`:
  - cabecera en inglés con la regla que comprueba;
  - CTE `totales_vista` (`COUNT(*)`, `COALESCE(SUM(vista.IMPORTE), 0)`, `COALESCE(SUM(vista.PIEZAS), 0)` y `COUNTIF(... IS NULL)` de `ENTIDAD_ISO`, `ANIO` y `MES`, desde `farma_analytics.v_compras_farma_completa AS vista`);
  - CTE `totales_compras` con las filas de `COMPRAS`;
  - CTE `filas_huerfanas` con `COUNTIF` de las filas sin `CLUE` o sin `CLAVE` en su catálogo, calculado con `NOT EXISTS`;
  - CTE `union_interna` con filas, `IMPORTE` y `PIEZAS` del `INNER JOIN` de las tablas base, en el mismo orden que la vista: `COMPRAS`, `CUADRO_BASICO` y `CLUE_CAT`;
  - `SELECT` final con `'reconciliacion_vista' AS CHEQUEO`, `'v_compras_farma_completa' AS OBJETO` y las seis filas de `DETALLE` de la tabla del contrato, desde `UNNEST([STRUCT(...), ...]) AS cuadres` con `ESPERADO` y `OBTENIDO` como `NUMERIC` y convertidos a `STRING` con `CAST`, filtradas con `WHERE cuadres.ESPERADO != cuadres.OBTENIDO` (depende de T014)
- [X] T019 [P] [US1] Cambiar el orden de los joins de la CTE `union_interna` de `sql/checks/05_reconciliacion_join.sql` para que sea el mismo que el de la vista (research R1b): `INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico ON compras.CLAVE = cuadro_basico.CLAVE` antes de `INNER JOIN farma_analytics.CLUE_CAT AS clue_cat ON compras.CLUE = clue_cat.CLUE`. No cambia nada más: ni las CTE, ni el resultado, ni su caso negativo, que sigue detectándose igual
- [X] T020 [P] [US1] Crear `sql/checks/negativos/07_reconciliacion_vista.json` según [contracts/checks.md](contracts/checks.md#caso-negativo-sqlchecksnegativos07_reconciliacion_vistajson): `tablas.COMPRAS`, `tablas.CLUE_CAT` y `tablas.CUADRO_BASICO` con las mismas filas que `sql/checks/negativos/05_reconciliacion_join.json` (dos líneas que casan y una huérfana de `CLUE`); `tablas.v_compras_farma_completa` con tres filas de 22 columnas en texto: las dos líneas que casan con sus valores de catálogo, `ANIO`, `MES` (`YYYY-MM-01`) y `ENTIDAD_ISO` correctos (`MX-JAL` y `MX-CMX`), y la primera línea repetida con `ENTIDAD_ISO` en `null`; `esperado = {"CHEQUEO": "reconciliacion_vista", "OBJETO": "v_compras_farma_completa"}` (depende de T018)
- [X] T021 [US1] Ampliar `warehouse/commands.py` según [contracts/make-targets.md](contracts/make-targets.md) y la tabla "Ejecución por objetivo" de [contracts/checks.md](contracts/checks.md#ejecución-por-objetivo):
  - `run_view()` hace la verificación de dataset y tablas, el dry run y la ejecución de la sentencia `create_view`, y después todos los chequeos con la vista;
  - `_run_all_checks(ddl, expectations, view_mode)` con `view_mode` igual a `"required"` (para `checks` y `vista`) o `"if_exists"` (para `load`, que decide con `metadata.object_exists`);
  - `run_schema()` sigue ignorando la vista y las consultas;
  - `run_negative_checks_command()` pasa las tablas y la vista a `checks.run_negative_checks` (depende de T009, T010, T013, T015, T016 y T017)
- [X] T022 [US1] Añadir el subcomando `vista` ("despliega la vista desde la sección 3 y ejecuta los chequeos") a `warehouse/__main__.py`, y el objetivo `bq-vista: require-venv require-project ## Despliega la vista desde sql/farma_analytics.sql y ejecuta los chequeos` con `@$(WAREHOUSE) vista` y su entrada en `.PHONY` al `Makefile` (depende de T021)
- [X] T023 [US1] Hacer `git add` de los archivos nuevos y ejecutar `make test`, `make lint` y `make lint-sql`; las tres deben terminar sin errores (depende de T017 a T022)
- [X] T024 [US1] [Dueño] Ejecutar V0b y V1 a V4 de [quickstart.md](quickstart.md) (dry run de `QUALIFY` sin `WHERE`, `make bq-load` sin vista, que es la única recarga de esta validación, `make bq-vista` dos veces, `bq show` de la vista, el paso opcional V2b con `INFORMATION_SCHEMA` y `make bq-checks`) y compartir la salida. Si algo no coincide con lo esperado, se corrige antes de seguir (depende de T023)

**Checkpoint**: la vista existe con 298 500 filas y los siete chequeos están en 0.

---

## Phase 4: User Story 2 - Responder las tres preguntas comerciales (Priority: P1)

**Goal**: la sección 4 responde P1, P2 y P3 (más P3_CATALOGO) leyendo solo de la vista, y
`make bq-consultas` imprime las respuestas y comprueba las cifras cruzadas.

**Independent Test**: `make bq-consultas` imprime las cuatro respuestas con su número de filas y
bytes estimados y termina con "Cifras cruzadas: 5 de 5 cuadran." (quickstart V6).

### Pruebas (escribir primero, deben fallar)

- [X] T025 [P] [US2] Crear `tests/warehouse/test_queries_sql.py` con las reglas 1 a 11 de [contracts/consultas.md](contracts/consultas.md) sobre las sentencias `query` de `warehouse.ddl.parse_file()`, recorriendo el árbol de SQLFluff para las reglas de `ROUND`, `ORDER BY`, `GROUP BY`, `GROUPING SETS`, `UNPIVOT`, `QUALIFY`, `LIMIT`, `AVG` y `SAFE_DIVIDE`. Comprueba también que los alias de salida y su orden son los de la tabla "Respuestas de la sección 4" de [data-model.md](data-model.md)
- [X] T026 [P] [US2] Crear `tests/warehouse/test_cross_figures.py` para `warehouse.queries.cross_figures(results, totals) -> list[CheckResult]` con resultados de ejemplo, unos con valores como texto y otros como número JSON, porque el plan no supone cómo los imprime `bq --format=json` (research R6):
  - un juego que cuadra devuelve `[]`;
  - cada una de C1 a C5 rota por separado devuelve al menos una fila con `CHEQUEO="cifras_cruzadas"` y `OBJETO` igual a la regla;
  - C4 acepta una diferencia de hasta 0.01 puntos entre `PARTICIPACION_PCT` y `100 × valor / total` calculado con `Decimal`, y falla con 0.02
- [X] T027 [P] [US2] Crear `tests/warehouse/test_queries_command.py` con `fake_bq` y `warehouse_env`:
  - `run_queries()` sale con 1 sin consultar si no hay exactamente cuatro sentencias `query`, o si la vista no existe ("Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'");
  - ejecuta `sql/ops/totales_vista.sql` (dry run y labels) antes que las consultas y, si `FILAS` es 0, sale con 1 con "La vista no tiene filas: ejecuta 'make bq-load'." sin ejecutar ninguna consulta;
  - si el dry run de una consulta falla, sale con 1, dice cuál (`P1`, `P2`, `P3` o `P3_CATALOGO`) y no la ejecuta;
  - para cada consulta, dry run y después `run_query(..., as_json=True, max_rows=10000)` con el mismo texto;
  - si una consulta devuelve 10 000 filas, sale con 1 y dice que el resultado podría estar truncado;
  - imprime `P1` y `P2` completas y de `P3` y `P3_CATALOGO` el número de filas y las 20 primeras;
  - sale con 0 e imprime "Cifras cruzadas: 5 de 5 cuadran." solo si `cross_figures` no devuelve filas

### Implementación

- [X] T028 [US2] Añadir a `sql/farma_analytics.sql` el comentario `-- Section 4: analytical queries.` y la consulta P1 según [research.md](research.md) R5:
  - comentarios `-- Question 1: ...` y `-- Definition: amount is SUM(IMPORTE); ties at the cut are broken by MOLECULA ascending.`;
  - CTE `importe_por_molecula` desde `farma_analytics.v_compras_farma_completa AS vista` con `vista.MOLECULA`, `SUM(vista.IMPORTE) AS IMPORTE_TOTAL`, `SUM(vista.PIEZAS) AS PIEZAS_TOTALES`, `AVG(vista.IMPORTE) AS IMPORTE_PROMEDIO_LINEA` y `SAFE_DIVIDE(SUM(vista.IMPORTE), SUM(SUM(vista.IMPORTE)) OVER ()) AS PARTICIPACION`, con `GROUP BY vista.MOLECULA`;
  - `SELECT` final con `MOLECULA`, `PIEZAS_TOTALES`, `ROUND(... IMPORTE_TOTAL, 2) AS IMPORTE_TOTAL`, `ROUND(SAFE_DIVIDE(IMPORTE_TOTAL, PIEZAS_TOTALES), 2) AS PRECIO_PROMEDIO`, `ROUND(IMPORTE_PROMEDIO_LINEA, 2) AS IMPORTE_PROMEDIO_LINEA` y `ROUND(100 * PARTICIPACION, 2) AS PARTICIPACION_PCT`, todas calificadas con el alias de la CTE;
  - `ORDER BY importe_por_molecula.IMPORTE_TOTAL DESC, importe_por_molecula.MOLECULA ASC LIMIT 5` (depende de T025)
- [X] T029 [US2] Añadir a `sql/farma_analytics.sql` la consulta P2 según R5:
  - comentarios `-- Question 2: ...` y `-- Definition: volume is SUM(IMPORTE), with SUM(PIEZAS) as the alternative; institution and entity are ranked together and separately; RANK keeps ties.`;
  - CTE `volumen_por_nivel` con `vista.INSTITUCION`, `vista.ENTIDAD`, `CASE WHEN GROUPING(vista.ENTIDAD) = 1 THEN 'INSTITUCION' WHEN GROUPING(vista.INSTITUCION) = 1 THEN 'ENTIDAD' ELSE 'INSTITUCION Y ENTIDAD' END AS NIVEL`, `SUM(vista.IMPORTE) AS IMPORTE` y `CAST(SUM(vista.PIEZAS) AS NUMERIC) AS PIEZAS`, con `GROUP BY GROUPING SETS ((vista.INSTITUCION, vista.ENTIDAD), (vista.INSTITUCION), (vista.ENTIDAD))`;
  - CTE `volumen_por_medida` desde `volumen_por_nivel UNPIVOT (VALOR FOR MEDIDA IN (IMPORTE, PIEZAS)) AS volumen`;
  - `SELECT` final con `MEDIDA`, `NIVEL`, `INSTITUCION`, `ENTIDAD`, `ROUND(VALOR, 2) AS VALOR` y `ROUND(100 * SAFE_DIVIDE(VALOR, SUM(VALOR) OVER (PARTITION BY MEDIDA, NIVEL)), 2) AS PARTICIPACION_PCT`;
  - `QUALIFY RANK() OVER (PARTITION BY ... MEDIDA, ... NIVEL ORDER BY ... VALOR DESC) = 1` y `ORDER BY` por `MEDIDA`, `NIVEL`, `INSTITUCION` y `ENTIDAD` ascendentes;
  - si V0b falló en T024, añadir `WHERE volumen_por_medida.VALOR > 0` antes de `QUALIFY` (research R5) (depende de T028 y T024)
- [X] T030 [US2] Añadir a `sql/farma_analytics.sql` las consultas P3 y P3_CATALOGO según R5, cada una con sus comentarios `-- Question 3: ...` y `-- Definition: ...`:
  - P3 usa la CTE `precio_por_fabricante_compra` con `vista.MOLECULA`, `vista.FABRICANTE_COMPRA`, `SUM(vista.IMPORTE) AS IMPORTE_TOTAL` y `SUM(vista.PIEZAS) AS PIEZAS_TOTALES`, agrupada por las dos columnas. El `SELECT` final tiene `MOLECULA`, `FABRICANTE_COMPRA`, `PIEZAS_TOTALES`, `ROUND(IMPORTE_TOTAL, 2) AS IMPORTE_TOTAL` y `ROUND(SAFE_DIVIDE(IMPORTE_TOTAL, PIEZAS_TOTALES), 2) AS PRECIO_PROMEDIO`, con `ORDER BY` por `MOLECULA` ascendente, precio sin redondear descendente y `FABRICANTE_COMPRA` ascendente;
  - P3_CATALOGO es igual con `FABRICANTE_CATALOGO` y la CTE `precio_por_fabricante_catalogo`. Su comentario dice que da una fila por molécula porque cada molécula tiene un solo fabricante de referencia (depende de T029)
- [X] T031 [P] [US2] Crear `sql/ops/totales_vista.sql` con una cabecera en inglés (totals of the view for the cross-figure checks of `make bq-consultas`) y `SELECT COUNT(*) AS FILAS, SUM(vista.IMPORTE) AS IMPORTE, SUM(vista.PIEZAS) AS PIEZAS FROM farma_analytics.v_compras_farma_completa AS vista`
- [X] T032 [US2] Crear `warehouse/queries.py` según [research.md](research.md) R6, R10 y R11 y [data-model.md](data-model.md#queryresult-una-respuesta-de-la-sección-4):
  - `QUERY_IDS = ("P1", "P2", "P3", "P3_CATALOGO")`, títulos en español, `MAX_ROWS = 10000` y `PREVIEW_ROWS = 20`;
  - `QueryResult`;
  - `view_totals() -> dict | str`, que ejecuta `sql/ops/totales_vista.sql` y devuelve un error si la vista tiene 0 filas;
  - `run_section(statements) -> list[QueryResult] | str`, que hace dry run y ejecución con `checks.run_checked_query` o una función equivalente con `max_rows`, y lee el JSON con `json.loads(..., parse_float=Decimal)`;
  - los valores numéricos se convierten con `Decimal(str(valor))` antes de comparar (research R6);
  - `format_result(result)`;
  - `cross_figures(results, totals) -> list[CheckResult]`, con C1 a C5 de [contracts/consultas.md](contracts/consultas.md#cifras-cruzadas-make-bq-consultas-research-r6) (depende de T026 y T027)
- [X] T033 [US2] Añadir `run_queries()` a `warehouse/commands.py`, el subcomando `consultas` ("ejecuta las consultas analíticas de la sección 4 y comprueba las cifras cruzadas") a `warehouse/__main__.py` y el objetivo `bq-consultas: require-venv require-project ## Ejecuta las consultas analíticas sobre la vista y comprueba las cifras cruzadas` con `@$(WAREHOUSE) consultas` y su entrada en `.PHONY` al `Makefile` (depende de T030 a T032)
- [X] T034 [US2] Hacer `git add` y ejecutar `make test`, `make lint` y `make lint-sql`; las tres deben terminar sin errores (depende de T033)
- [X] T035 [US2] [Dueño] Ejecutar V6 de [quickstart.md](quickstart.md) (`time make bq-consultas`) y compartir la salida: las cuatro respuestas, los bytes estimados de cada consulta, el tiempo total y "Cifras cruzadas: 5 de 5 cuadran." (depende de T034 y T024)

**Checkpoint**: las tres preguntas tienen respuesta y las cifras cuadran.

---

## Phase 5: User Story 3 - Ejecutar el `.sql` entregable de principio a fin en la consola (Priority: P2)

**Goal**: `sql/farma_analytics.sql` se ejecuta completo en la consola sin errores y sin tocar los
datos.

**Independent Test**: el dueño pega el archivo completo en la consola, lo ejecuta dos veces y las
respuestas coinciden con `make bq-consultas` (quickstart V8).

- [X] T036 [P] [US3] Añadir a `tests/warehouse/test_ddl.py` la prueba `test_deliverable_section_order`: las sentencias de `sql/farma_analytics.sql` son, en este orden, un `create_schema`, tres `create_table`, un `create_view` y cuatro `query`, sin ninguna otra; y el archivo no contiene `#standardSQL`, `#legacySQL` ni sintaxis pipe (`|>`) fuera de comentarios y cadenas
- [X] T037 [US3] Actualizar el comentario de cabecera de `sql/farma_analytics.sql` para que diga que el archivo corre de principio a fin en la consola, que `make bq-schema` ejecuta las secciones 1 y 2, `make bq-vista` la 3 y `make bq-consultas` la 4, siempre con dry run antes de cada sentencia, y que re-ejecutarlo no cambia los datos (depende de T030 y T036)
- [X] T038 [US3] [Dueño] Ejecutar V8 de [quickstart.md](quickstart.md): pegar `sql/farma_analytics.sql` completo en la consola de BigQuery, ejecutarlo dos veces, comparar P1 y P2 con la salida de T035 y después ejecutar `make bq-checks` (siete chequeos en 0 y las tablas con 300 000, 2 000 y 161 filas) (depende de T037 y T035)

---

## Phase 6: User Story 4 - Demostrar que el chequeo de la vista detecta errores (Priority: P2)

**Goal**: el caso negativo del chequeo 07 se detecta junto con los otros seis, sin leer datos ni
facturar bytes.

**Independent Test**: `make bq-checks-negativos` imprime "Casos negativos: 7 de 7 detectados." con 0
bytes estimados en cada caso (quickstart V5).

- [X] T039 [P] [US4] Ampliar `tests/warehouse/test_negative_checks.py`:
  - el caso 07 trae filas para las cuatro relaciones y su vista tiene una fila más que las líneas que casan y un `ENTIDAD_ISO` nulo;
  - con `fake_bq` respondiendo una fila con el objeto esperado para cada caso, `run_negative_checks` imprime "Casos negativos: 7 de 7 detectados." y sale con 0;
  - el SQL que se envía para el caso 07 no contiene ninguna referencia `farma_analytics.` fuera de comentarios y cadenas (depende de T020 y T021)
- [X] T040 [US4] Ejecutar `make test` y confirmar que T039 pasa (depende de T039)
- [X] T041 [US4] [Dueño] Ejecutar V5 de [quickstart.md](quickstart.md) (`make bq-checks-negativos`) y compartir la salida (depende de T040 y T024)

---

## Phase 7: User Story 5 - Seguir el recorrido documentado de la Fase 2 (Priority: P3)

**Goal**: el README explica la Fase 2 y la matriz de trazabilidad la cubre.

**Independent Test**: siguiendo el README desde el estado de la feature 003 se llega a la vista, a
los siete chequeos y a las tres respuestas sin pasos que no estén escritos.

- [X] T042 [P] [US5] Añadir a `README.md` una sección de la Fase 2 en español que cumpla el principio IX:
  - el recorrido `make bq-vista`, `make bq-checks` y `make bq-consultas`, qué hace cada uno, que los ejecuta el dueño porque tocan GCP y qué salida esperar;
  - que `make bq-load` no toca la vista y avisa si falta;
  - el glosario de métricas y la tabla de definiciones de las ambigüedades de [data-model.md](data-model.md), con la razón de cada una;
  - la limitación de que el precio por molécula mezcla presentaciones con envases de distinto tamaño.

  Las cifras que se citen salen de la salida de T035, con unidad, periodo y origen (depende de T035)
- [X] T043 [P] [US5] Añadir a `docs/trazabilidad.md` la sección "Fase 2: consultas SQL y modelado" con filas para: la vista con `INNER JOIN` y su nombre, cada una de las tres preguntas, las definiciones de las ambigüedades, el chequeo de la vista y su caso negativo, y las descripciones de la vista. Cada fila lleva su artefacto y su verificación (prueba local y paso del quickstart)
- [X] T044 [US5] Ejecutar `make lint-prosa` y corregir lo que marque (depende de T042 y T043)

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T045 [P] Buscar en todos los archivos modificados o nuevos (`git diff --name-only main` y los no versionados) menciones del documento de requisitos de origen, del ID del proyecto de GCP, de correos y de credenciales, y quitarlas si aparecen
- [X] T046 Hacer `git add` de todo y ejecutar `make test`, `make lint`, `make lint-sql` y `make lint-prosa`; las cuatro deben terminar sin errores (depende de T044 y T045)
- [X] T047 [Dueño] Ejecutar V7 de [quickstart.md](quickstart.md) (`time make bq-vista`, sin recargar las tablas) para medir SC-006 junto con el tiempo de T035 (depende de T046)
- [X] T048 Marcar las tareas hechas en este archivo y revisar SC-001 a SC-007 con la salida de T024, T035, T038, T041 y T047. Después, redactar el mensaje de commit (Conventional Commits, cuerpo en español) y la descripción del PR, pasarlos por `scripts/lint_prosa.sh -` y enseñárselos al dueño. Solo con su visto bueno, hacer commit y push de la rama, sin abrir todavía el PR (depende de T047)
- [X] T049 [Dueño] Comprobar en un clon limpio de la rama publicada el SC-008 de esta feature, que cubre también el SC-008 de la feature 003 y la V2 de la 002. Los pasos: `git clone --branch 004-analytics-view-queries <url>` en un directorio temporal y seguir solo el README (`make setup-dev`, `make data`, `make bq-schema`, `make bq-vista`, `make bq-checks`, `make bq-checks-negativos`, `make bq-consultas` y `make doctor`). `make bq-load` no se repite, para no reescribir las tablas. Si algo falla, se corrige con un commit nuevo en la rama (depende de T048)
- [X] T050 Abrir el PR hacia `main` con la descripción aprobada en T048, vincularlo y revisar su CI. El merge con squash lo hace el dueño (depende de T049)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP: sin vista no hay consultas.
- **US2 (Phase 4)**: depende de US1, porque las consultas leen la vista y `run_queries` exige que
  exista. Sus pruebas (T025 a T027) se pueden escribir en paralelo con US1.
- **US3 (Phase 5)**: depende de US1 y US2, porque valida el archivo completo.
- **US4 (Phase 6)**: depende de T020 y T021 de US1. Se puede hacer en paralelo con US2.
- **US5 (Phase 7)**: depende de US2 (cifras de T035) y documenta el comportamiento final.
- **Polish (Phase 8)**: depende de todo lo anterior. El PR (T050) se abre al final.

### User Story Dependencies

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> US5 -> Polish
                           \
                            -> US4 (en paralelo con US2)
```

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- El SQL va antes que la orquestación, y la orquestación antes que `__main__` y el `Makefile`.
- Cada historia termina con `git add` y la batería local.

### Parallel Opportunities

- Foundational: T003, T004, T005 y T006 (pruebas) en paralelo.
- US1: T012 a T016 en paralelo. T018 y T019 en paralelo con T017, y T020 después de T018.
- US2: T025, T026 y T027 en paralelo. T031 en paralelo con T028 a T030.
- US4 en paralelo con US2. T042 y T043 en paralelo.

## Parallel Example: User Story 1

```text
# Pruebas de la historia, juntas:
T012 tests/warehouse/test_view_sql.py
T013 tests/warehouse/test_view_command.py
T014 tests/warehouse/test_checks_sql.py
T015 tests/warehouse/test_load_command.py
T016 tests/warehouse/test_checks_command.py

# SQL de la historia, juntos:
T017 sql/farma_analytics.sql (sección 3)
T018 sql/checks/07_reconciliacion_vista.sql
T019 sql/checks/05_reconciliacion_join.sql (orden de los joins)
```

## Implementation Strategy

### MVP First (User Story 1)

1. Setup y Foundational.
2. US1: vista, chequeo 07, `make bq-vista` y pruebas.
3. Parar y validar: el dueño ejecuta V1 a V4 (T024). Con eso la vista queda en BigQuery, lista
   también para conectar Data Studio.

### Incremental Delivery

1. US2 añade las tres respuestas y las cifras cruzadas.
2. US4 demuestra que el chequeo de la vista detecta errores.
3. US3 valida el `.sql` completo en la consola.
4. US5 documenta la fase.
5. Polish: lint completo, V7, clon limpio y textos de commit y PR aprobados.

Todo entra en un solo PR con squash merge, que hace el dueño.

## Notes

- [P] significa archivos distintos y sin dependencias pendientes.
- Las tareas [Dueño] son las únicas que tocan GCP. Claude prepara los comandos y la salida esperada.
- Hay que hacer commit solo con el visto bueno del dueño (T048).
