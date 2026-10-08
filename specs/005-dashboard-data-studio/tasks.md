---

description: "Task list for feature 005-dashboard-data-studio"
---

# Tasks: Dashboard comercial en Data Studio (Fase 3)

**Input**: Design documents from `specs/005-dashboard-data-studio/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluidos. El plan fija pruebas locales sin GCP para las consultas de verificación, el
subcomando `dashboard` y `docs/dashboard.md` ([contracts/](contracts/)). Se escriben antes de la
implementación y deben fallar primero.

**Organization**: tareas agrupadas por historia de usuario para implementarlas y probarlas por
separado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia a la que pertenece (US1 a US7).
- Quién ejecuta, al inicio de la descripción:
  - sin marca: Claude en local (archivos del repositorio y verificaciones locales: `make test`,
    `make lint`, `make lint-sql`, `make lint-prosa`, pytest, sqlfluff, ruff);
  - **[Chrome]**: Claude en el Chrome del dueño con Claude in Chrome, sobre su sesión de Google.
    Antes de cada acción Claude dice qué va a hacer, y al terminar describe lo que hizo y toma una
    captura para compararla con `docs/dashboard.md`;
  - **[Confirmación]**: además de [Chrome], Claude se detiene y pide el visto bueno del dueño antes
    de la acción (credenciales o permisos de la fuente, autorizar el conector, aceptar términos o
    avisos, compartir o cambiar permisos del informe);
  - **[Dueño]**: lo ejecuta el dueño porque toca GCP o necesita su sesión fuera de Chrome. Claude le
    da los comandos exactos, en orden, uno por bloque, con la explicación de cada flag y la salida
    esperada, o los pasos exactos de la interfaz si no hay comando;
  - **[Navegador integrado]**: Claude en el navegador de la app, que no tiene sesión de Google.
- Si una tarea [Chrome] no se puede completar (la extensión no llega a un diálogo, Google pide
  iniciar sesión o verificar la identidad, un selector no responde), Claude se detiene, describe lo
  que ve y le da al dueño los pasos exactos para hacerlo a mano. Después retoma desde el paso
  siguiente.

## Reglas transversales (aplican a todas las tareas)

- Python 3.12 con anotaciones de tipo, `from __future__ import annotations`, `dataclasses`
  inmutables (`frozen=True`) y `pathlib.Path`. Docstrings y comentarios en inglés, breves, que dicen
  qué es cada cosa, sin punto y coma para unir ideas. Sin dependencias nuevas. ruff con
  `skip-magic-trailing-comma`: una línea solo se parte si no cabe en 100 caracteres, y una
  estructura con entradas de formas distintas se reorganiza.
- Los mensajes que ve el usuario (salida de `python -m warehouse`, errores, `--help`, ayuda de
  `make`) van en español y nombran las cosas reales ("control Entidad", `v_compras_farma_completa`),
  nunca referencias internas.
- `bq` solo se invoca a través de `warehouse.bq.execute`. Ningún comando repite `--location`,
  `--use_legacy_sql` ni `--maximum_bytes_billed`. Toda consulta va precedida por su dry run con el
  mismo SQL y los mismos parámetros, y lleva las labels de `BQ_JOB_LABELS`.
- SQL con las reglas del principio II y de `.sqlfluff`: alias `vista` y nombre de CTE, `AS` en todo
  alias, sin AL09, ST06, `GROUP BY` por nombre, `SAFE_DIVIDE`, `ROUND` y `ORDER BY` solo en el
  `SELECT` final, sin `SELECT *`, sin ID de proyecto, líneas de 100 caracteres o menos y un
  comentario inicial en inglés que dice qué componente del tablero verifica.
- `docs/dashboard.md`, el README y la trazabilidad van en español y pasan `make lint-prosa`
  (principio IX). Los textos que se escriben en el informe (título, subtítulo, títulos de
  componentes, recuadro de hallazgos) también siguen el principio IX.
- Ningún archivo versionado menciona el documento de requisitos de origen ni contiene el ID del
  proyecto, correos o credenciales. El enlace de lectura del informe sí se versiona.
- Antes de afirmar que el lint pasa sobre archivos nuevos, hacer `git add` de esos archivos uno por
  uno (nunca `git add -A`), porque `pre-commit run --all-files` no revisa archivos sin versionar.
- En Data Studio, todo valor se toma de [data-model.md](data-model.md) y, cuando exista, de
  `docs/dashboard.md`. Si el producto obliga a apartarse, se para, se informa al dueño y se registra
  la alternativa en `docs/dashboard.md` antes de seguir.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: confirmar el punto de partida.

- [ ] T001 Confirmar que la rama es `005-dashboard-data-studio`, que el árbol está limpio y que `make test`, `make lint`, `make lint-sql` y `make lint-prosa` pasan antes de tocar nada.
- [ ] T002 [Dueño] Confirmar que la vista existe y pasa sus chequeos con `make doctor` (22 OK) y `make bq-checks` (siete chequeos en 0 filas). Claude da los dos comandos con su explicación y la salida esperada.
- [ ] T003 Crear el directorio `sql/dashboard/` y `tests/docs/` (con `__init__.py` solo si la configuración de pytest de `pyproject.toml` lo necesita para descubrir las pruebas).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: las consultas de verificación y `make bq-dashboard`, que producen las cifras con las que
se comprueba cada historia, y el primer borrador de `docs/dashboard.md`, que es la referencia para
construir el informe.

**⚠️ CRITICAL**: ninguna historia de Data Studio empieza sin T016 (cifras del estado inicial) y T019
(borrador de la especificación).

### Pruebas (escribir primero, deben fallar)

- [ ] T004 [P] Escribir `tests/warehouse/test_dashboard_sql.py` con las reglas de [contracts/verificacion-sql.md](contracts/verificacion-sql.md): los cinco archivos existen; cada uno empieza con un comentario en inglés; lee solo de `farma_analytics.v_compras_farma_completa AS vista` sin joins ni ID de proyecto; tiene una CTE `filtrada`; el bloque de filtros es idéntico al del contrato en los cinco archivos, con la línea de fechas al final del bloque y ausente solo en `kpis_por_anio.sql` (la prueba compara el bloque sin esa última línea); usa `SAFE_DIVIDE` para precio y participación y no contiene `AVG`; `ROUND` y `ORDER BY` solo en el `SELECT` final; `GROUP BY` sin ordinales; columnas de salida en el orden de [data-model.md](data-model.md#consultas-de-verificación); `top10_molecula_fabricante.sql` ordena por `IMPORTE DESC, MOLECULA, FABRICANTE_COMPRA` y termina en `LIMIT 10`; SQLFluff no informa violaciones con `.sqlfluff`.
- [ ] T005 [P] Escribir `tests/warehouse/test_dashboard_command.py` con el `bq` falso de `tests/warehouse/conftest.py`: parámetros `--parameter=fecha_inicio:DATE:2025-01-01` y `--parameter=entidades:ARRAY<STRING>:[...]` con listas vacías, varios valores y nombres con tilde codificados en JSON; periodo de referencia igual que *Previous period* (2025-01-01 a 2025-12-31 da 2024-01-02 a 2024-12-31, y 2024-03-01 a 2024-03-31 da 2024-01-30 a 2024-02-29); dry run antes de cada consulta con el mismo SQL y parámetros; labels en cada consulta; un dry run fallido detiene el comando; la vista ausente ("Falta farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'") y la vista vacía ("La vista no tiene filas: ejecuta 'make bq-load'") detienen el comando con código 1 antes de las consultas del tablero; D3 con un año sin filas cuenta 0 en los dos lados; D1 a D4 aceptan resultados que cuadran y rechazan cada caso que no cuadra (D2 con tolerancia 0.01 en la suma de participaciones); fechas inválidas o inicio posterior al fin terminan con código 2 sin llamar a `bq`; ningún valor de `entidad` en `generator/reference/entidades.csv`, de `institucion` y `grupo_institucional` en `generator/reference/instituciones.csv`, ni de `molecula` y `grupo_terapeutico` en `generator/reference/moleculas.csv` contiene una coma; `make help` lista `bq-dashboard`.

### Consultas de verificación

- [ ] T006 [P] Escribir `sql/dashboard/kpis.sql`: una fila con `FILAS` (`COUNT(*)`), `IMPORTE` (`SUM`, sin redondear), `PIEZAS` (`SUM`) y `PRECIO_PROMEDIO` (`ROUND(SAFE_DIVIDE(SUM(IMPORTE), SUM(PIEZAS)), 2)`) sobre la CTE `filtrada` con el bloque de filtros completo del contrato.
- [ ] T007 [P] Escribir `sql/dashboard/kpis_por_anio.sql`: una fila por `ANIO` con `ANIO`, `FILAS`, `IMPORTE`, `PIEZAS` y `PRECIO_PROMEDIO`, con el bloque de filtros sin la línea de fechas, `GROUP BY` por nombre y `ORDER BY ANIO`.
- [ ] T008 [P] Escribir `sql/dashboard/gasto_entidad.sql`: `ENTIDAD`, `ENTIDAD_ISO` e `IMPORTE` por entidad, ordenado por `IMPORTE DESC, ENTIDAD`.
- [ ] T009 [P] Escribir `sql/dashboard/participacion_institucion.sql`: `INSTITUCION`, `IMPORTE` y `PARTICIPACION_PCT` = `ROUND(100 * SAFE_DIVIDE(SUM(IMPORTE), SUM(SUM(IMPORTE)) OVER ()), 4)`, ordenado por `IMPORTE DESC, INSTITUCION`.
- [ ] T010 [P] Escribir `sql/dashboard/top10_molecula_fabricante.sql`: `MOLECULA`, `FABRICANTE_COMPRA`, `PIEZAS`, `IMPORTE` y `PRECIO_PROMEDIO` (2 decimales), ordenado por `IMPORTE DESC, MOLECULA, FABRICANTE_COMPRA` con `LIMIT 10`.
- [ ] T011 Ejecutar `uv run sqlfluff lint sql/dashboard/` y `uv run pytest tests/warehouse/test_dashboard_sql.py` hasta que pasen.

### Subcomando y objetivo

- [ ] T012 Escribir `warehouse/dashboard.py`: `Filters` (dataclass inmutable con `desde`, `hasta` y las cinco tuplas de valores), validación de fechas, `reference_period` (mismo número de días que termina el día anterior a `desde`, como *Previous period* de Data Studio), `as_bq_parameters` (fechas `DATE` y arreglos `ARRAY<STRING>` en JSON, sin la línea de fechas para `kpis_por_anio.sql`), ejecución de cada consulta con dry run y labels reutilizando el patrón de `warehouse/queries.py` (`_run`, `view_totals`), comprobación de la vista ausente o vacía con los mensajes del contrato, impresión (fechas del periodo de referencia, importe en millones con 1 decimal, piezas en millones con 2, precio con 2, cambio en % con 1 decimal, valor exacto entre paréntesis, totales por año, tablas con números a la derecha, bytes estimados) y las cifras cruzadas D1 a D4 de [contracts/verificacion-sql.md](contracts/verificacion-sql.md) como `CheckResult` con el chequeo `cifras_dashboard`.
- [ ] T013 Añadir `run_dashboard(filters)` en `warehouse/commands.py` (comprueba el entorno, la vista con filas, ejecuta, imprime y devuelve 0, 1 o 2) y el subcomando `dashboard` en `warehouse/__main__.py` con `--desde`, `--hasta`, `--entidad`, `--institucion`, `--grupo-institucional`, `--grupo-terapeutico` y `--molecula` (listas separadas por comas). Los subcomandos actuales siguen sin opciones. Ayuda: "calcula sobre la vista las cifras del dashboard con los filtros indicados" y, en cada opción, el nombre visible del control que reproduce ("Periodo", "Entidad", "Institución", "Grupo institucional", "Grupo terapéutico", "Molécula"). Actualizar el docstring del módulo con el subcomando nuevo.
- [ ] T014 Añadir al `Makefile` el objetivo `bq-dashboard` con `require-venv require-project`, la ayuda "Calcula sobre la vista las cifras que muestra el dashboard (KPIs, entidades, instituciones y top 10) con los filtros indicados" y las variables opcionales `DESDE`, `HASTA`, `ENTIDAD`, `INSTITUCION`, `GRUPO_INSTITUCIONAL`, `GRUPO_TERAPEUTICO` y `MOLECULA`, pasadas solo si tienen valor y entre comillas para admitir espacios y tildes.
- [ ] T015 `git add` de `sql/dashboard/*.sql`, `warehouse/dashboard.py`, `tests/warehouse/test_dashboard_sql.py` y `tests/warehouse/test_dashboard_command.py` (uno por uno) y ejecutar `make test`, `make lint` y `make lint-sql` hasta que pasen.
- [ ] T016 [Dueño] Ejecutar `make bq-dashboard`. El primer dry run comprueba también que `bq` acepta el arreglo vacío `[]` como "todas". Si lo rechaza, Claude aplica la alternativa de [research.md](research.md#r12-consultas-de-verificación-y-make-bq-dashboard) (`NULL` con tipo `ARRAY<STRING>` y `@x IS NULL OR ...` en el bloque de filtros, en las consultas, el contrato y las pruebas) antes de repetir el comando. Esperado: 7 consultas con dry run, periodo de referencia 2024-01-02 a 2024-12-31, D1 a D4 sin diferencias y las cifras de [data-model.md](data-model.md#cifras-esperadas-del-estado-inicial) (importe 2025 de 14 941.7 M, +9.6 %; 28.55 M de piezas, +7.3 %; precio 523.42, +2.1 %; México 1 731 M; IMSS 38.71 %; primer par insulina glargina con Laboratorios Serrato Castro, 2 092.9 M). El dueño pega la salida en el chat.
- [ ] T017 [Dueño] Ejecutar `make bq-dashboard ENTIDAD=Jalisco`. Esperado: D1 a D4 sin diferencias y una sola entidad en el gasto por entidad. El dueño pega la salida en el chat.

### Especificación de referencia

- [ ] T018 [P] Escribir `tests/docs/test_dashboard_spec.py` con las reglas de [contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md): la tabla de campos cubre exactamente las 22 columnas de la sección 3 de `sql/farma_analytics.sql` (leídas con `warehouse.ddl`); ninguna fórmula contiene `AVG`; cada fila de contraste con umbral numérico coincide con la fórmula de WCAG 2.1 a dos decimales y supera su umbral; hay 3 tamaños de letra o menos; si `GOOGLE_CLOUD_PROJECT` está definido, su valor no aparece en el documento.
- [ ] T019 Escribir el primer borrador de `docs/dashboard.md` con las secciones 1 a 9 de [contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md), tomadas de [data-model.md](data-model.md) y de [research.md](research.md): fuente, tabla de los 22 campos con nombre de negocio, tipo, agregación y uso, campo calculado `SUM(IMPORTE) / NULLIF(SUM(PIEZAS), 0)`, tema y tabla de contrastes con el formato `| Primer plano | Fondo | Uso | Contraste | Umbral |`, rejilla con las coordenadas, textos fijos literales de [data-model.md](data-model.md#textos-fijos) (título, subtítulo, etiqueta "Periodo", botón y etiqueta de comparación), controles, tarjetas, gráficos con sus títulos y la definición del top 10, y recuadro de hallazgos con el texto literal de R17 ajustado a las cifras de T016 y a la longitud máxima de data-model. `git add docs/dashboard.md` y `make lint-prosa`.

**Checkpoint**: cifras de referencia confirmadas en BigQuery y especificación lista para construir.

---

## Phase 3: User Story 1 - Ver los indicadores generales con un enlace de lectura (Priority: P1) 🎯 MVP

**Goal**: la fuente configurada, el informe con su lienzo y tema, el encabezado, el control de
fechas por defecto y las tres tarjetas, compartido en modo lectura.

**Independent Test**: abrir el enlace sin sesión y ver las tres tarjetas con datos y con los valores
de T016.

- [ ] T020 [US1] [Confirmación] Abrir Data Studio en el Chrome del dueño y crear una fuente de datos reutilizable desde la página de inicio (Crear, Fuente de datos) con el conector de BigQuery: proyecto del dueño, dataset `farma_analytics`, tabla `v_compras_farma_completa`, sin "Custom query". Pedir confirmación antes de autorizar el conector y antes de aceptar términos o avisos. Nombre de la fuente: `v_compras_farma_completa (BigQuery)`.
- [ ] T021 [US1] [Confirmación] En la fuente, comprobar que las credenciales son "Owner's credentials" (pedir confirmación si hay que cambiarlas), fijar la frescura de datos en "12 horas" y desactivar "Field Editing in Reports". Captura del panel.
- [ ] T022 [US1] [Chrome] Configurar los 22 campos de la fuente con la tabla de [data-model.md](data-model.md#campos-de-la-fuente): nombre de negocio, tipo ("Currency (MXN)" en `IMPORTE`, "Number" en `PIEZAS`, "Date" en `FECHA`, "Year Month" en `MES`, "Year" en `ANIO`, "Country subdivision (1st level)" en `ENTIDAD_ISO`, "Text" en el resto) y agregación ("Sum" en `IMPORTE` y `PIEZAS`, "None" en el resto). Registrar si MXN aparece en la lista de monedas y, si no aparece, aplicar la alternativa de R2 y avisar al dueño.
- [ ] T023 [US1] [Chrome] Crear el campo calculado "Precio Promedio" = `SUM(IMPORTE) / NULLIF(SUM(PIEZAS), 0)` con tipo "Currency (MXN)". Si Data Studio rechaza `NULLIF` sobre un agregado, usar `CASE WHEN SUM(PIEZAS) = 0 THEN NULL ELSE SUM(IMPORTE) / SUM(PIEZAS) END`. Registrar cuál quedó.
- [ ] T024 [US1] [Chrome] Crear un informe en blanco con la fuente, titularlo "Compras públicas de medicamentos en México", fijar el lienzo en 1600 × 900 px, la rejilla en 10 px con "Snap to grid", el modo "Fit to width" y el tema personalizado de [research.md](research.md#r10-tema-rejilla-y-colores): fondo `#FFFFFF`, texto `#202124`, color de datos `#0072B2`, cambio positivo `#0072B2`, cambio negativo `#B34700`, bordes de componentes `#DADCE0`, bordes de controles y líneas de los ejes `#80868B`, fuente Roboto (registrar si no está disponible y qué fuente queda).
- [ ] T025 [US1] [Chrome] Añadir el título (26 px) y el subtítulo de transparencia (12 px, `#5F6368`, dos líneas) en las coordenadas de [data-model.md](data-model.md#rejilla-y-disposición), con el texto literal de [data-model.md](data-model.md#textos-fijos), que también está en `docs/dashboard.md`.
- [ ] T026 [US1] [Chrome] Añadir el control de rango de fechas sobre `FECHA` en x 20, y 80, 230 × 50, con la etiqueta de texto "Periodo" (12 px, `#5F6368`) encima y con valor por defecto personalizado y fijo 2025-01-01 a 2025-12-31 (Custom, Advanced, inicio y fin "Fixed"), nunca "Auto".
- [ ] T027 [US1] [Chrome] Añadir las tres tarjetas en sus coordenadas (360 × 100 cada una): "Monto Total Comprado" (Importe, compacto, 1 decimal), "Total de Piezas Adjudicadas" (Piezas, compacto, 2 decimales) y "Precio Promedio General por Pieza" (Precio Promedio, compacto, 2 decimales), con su unidad visible ("pesos (MXN)", "piezas", "pesos (MXN) por pieza"), *Comparison type* Period, *Comparison date range* "Previous period", etiqueta de comparación "frente al periodo anterior", cambio en % con 1 decimal y "Missing data" en "-". Registrar si la tarjeta dibuja ▲▼, qué sufijo usan los números compactos para mil millones, que el periodo anterior de 2025 es 2024-01-02 a 2024-12-31 y si el valor admite 26 px. Si no hay flechas, aplicar la alternativa de R5 (campo calculado de texto con ▲ o ▼ sobre `FECHA`, en las coordenadas de data-model, fuera del grupo del control de fechas y con la excepción "▲▼ comparan siempre 2025 con el periodo anterior" visible). Si aparece "B", la de R11 (incluida la enmienda PATCH de la constitución, que se propone al dueño antes de aplicarla). Si el valor no admite 26 px, la de R10. Avisar al dueño antes de cada alternativa.
- [ ] T028 [US1] Comparar las tres tarjetas y su cambio con la salida de T016 a la precisión que muestra el tablero y anotar cada comparación en el registro de verificación de `docs/dashboard.md`.
- [ ] T029 [US1] [Confirmación] Compartir el informe con "Cualquier persona con el enlace puede ver" (Share, Manage access, link settings). Pedir confirmación antes de cambiar el permiso. Copiar el enlace de lectura al chat.
- [ ] T030 [US1] [Navegador integrado] Abrir el enlace de lectura en el navegador de la app, sin sesión de Google, y comprobar que carga con datos en las tres tarjetas, sin pedir acceso y en menos de 10 segundos. Captura.
- [ ] T031 [US1] [Dueño] Abrir el enlace en una ventana de incógnito de Chrome y confirmar en el chat que se ven las tres tarjetas con datos.

**Checkpoint**: MVP entregable. El enlace funciona sin sesión con las tarjetas correctas.

---

## Phase 4: User Story 2 - Filtrar todo el tablero con controles encadenados (Priority: P1)

**Goal**: las cinco listas desplegables en cascada y el botón de restablecer.

**Independent Test**: aplicar cada control y combinaciones, ver que las tarjetas cambian y que el
botón devuelve el estado inicial.

- [ ] T032 [US2] [Chrome] Añadir cinco controles "Drop-down list" en las coordenadas de [data-model.md](data-model.md#rejilla-y-disposición): Entidad (`ENTIDAD`), Institución (`INSTITUCION`), Grupo institucional (`GRUPO_INSTITUCIONAL`), Grupo terapéutico (`GRUPO_TERAPEUTICO`) y Molécula (`MOLECULA`), cada uno con "Enable search box", selección múltiple, orden alfabético ascendente, "Show top #" en 200 (para que no aparezca "All others") y la etiqueta visible con el nombre de negocio, con borde `#80868B`.
- [ ] T033 [US2] [Chrome] Añadir el botón "Restablecer filtros" (tipo *Report actions*, acción "Reset filters") en x 1410, y 80, 170 × 50, con texto `#0072B2` y borde `#0072B2`.
- [ ] T034 [US2] [Chrome] En modo vista, comprobar: (a) elegir Jalisco en Entidad cambia las tres tarjetas; (b) con "Oncología" en Grupo terapéutico, la lista Molécula solo ofrece moléculas de Oncología, y lo mismo entre Grupo institucional e Institución y entre Entidad e Institución; (c) sin escribir, Molécula ofrece las 139 moléculas sin "All others"; (d) el botón deja todos los controles en su valor por defecto, incluido el rango 2025. Registrar en `docs/dashboard.md` si el botón devuelve el rango de fechas. Si no lo hace, avisar al dueño y sustituirlo por un botón de tipo *Navigation* que abre el enlace del propio informe en la misma pestaña (R4), y repetir la comprobación (d).
- [ ] T035 [US2] Comparar las tarjetas con Jalisco elegido con la salida de T017 y anotarlo en el registro de verificación de `docs/dashboard.md`.

**Checkpoint**: filtros y cascada funcionando sobre las tarjetas.

---

## Phase 5: User Story 3 - Analizar dónde y quién compra, y quién vende (Priority: P1)

**Goal**: las barras de entidades, las de instituciones y la tabla del top 10, con cross-filtering.

**Independent Test**: comparar las tres visualizaciones con T016 y T017 y revisar el orden, las
etiquetas y el formato.

- [ ] T036 [US3] [Chrome] Añadir "Gasto por entidad, pesos (MXN)": *Bar chart* horizontal en x 20, y 270, 500 × 610, dimensión Entidad, métrica Importe, orden por Importe descendente, "Number of bars" 32, "Group others" desactivado, "Show data labels" con números compactos, eje con mínimo 0, color único `#0072B2`, sin leyenda, sin texto rotado y cross-filtering activo.
- [ ] T037 [US3] [Chrome] Añadir "Participación por institución, % del importe": *Bar chart* horizontal en x 1070, y 270, 510 × 280, dimensión Institución, métrica Importe con *Comparison calculation* "Percent of total", "Group others" desactivado, orden descendente, etiquetas de % con 1 decimal, color único `#0072B2`, eje con mínimo 0 y cross-filtering activo. Si el gráfico de barras no ofrece "Percent of total", avisar al dueño y usar la alternativa de R7: una *Table* con Institución y la métrica en "Percent of total" como columna de tipo "Bar", ordenada de mayor a menor, en las mismas coordenadas.
- [ ] T038 [US3] [Chrome] Añadir "Top 10 pares molécula-fabricante por importe (MXN)": *Table* en x 540, y 570, 1040 × 310, dimensiones Molécula y Fabricante, métricas Piezas (entero con separador de miles, sin compactar), Importe (compacto, 1 decimal) y Precio Promedio (2 decimales, sin compactar), orden por Importe descendente con orden secundario por Molécula y después Fabricante, "Top N" 10 filas, "Group others" desactivado, números alineados a la derecha, sin paginación y cross-filtering activo.
- [ ] T039 [US3] [Chrome] En modo vista, comprobar el cross-filtering: un clic en la barra del IMSS filtra las tarjetas, las entidades, la tabla y, si ya está, el mapa, y un segundo clic lo quita. Captura de cada estado.
- [ ] T040 [US3] Comparar con T016 el importe de cada entidad, el % de cada institución (que suman 100 % con tolerancia de redondeo) y las 10 filas del top 10 en el estado inicial, y con T017 el top 10 y el gasto por entidad con Jalisco. Anotar cada comparación en el registro de verificación de `docs/dashboard.md`.

**Checkpoint**: las tres visualizaciones obligatorias coinciden con el SQL.

---

## Phase 6: User Story 4 - Leer el tablero sin depender del color y entender sus conclusiones (Priority: P2)

**Goal**: recuadro de hallazgos y revisión completa de diseño y accesibilidad.

**Independent Test**: lista del principio VI, contrastes medidos y captura en escala de grises.

- [ ] T041 [US4] [Chrome] Añadir el recuadro "Hallazgos clave (2025, sin otros filtros)" en x 1160, y 150, 420 × 100, fondo `#F1F3F4`, texto `#202124` en 14 y 12 px, con el texto literal de `docs/dashboard.md` (tres conclusiones con cifras de T016 y la línea final sobre los patrones inyectados, R17), como máximo 5 líneas de 12 px con interlineado de 14 px. Comprobar en la captura que nada se corta.
- [ ] T042 [US4] [Chrome] Revisar la lista del principio VI sobre el informe: 16:9 sin scroll, pirámide, zona superior izquierda para lo más importante, rejilla y alineación, sin 3D, sombras, degradados ni fondos con imagen, barras desde cero, sin doble eje, orden por la métrica, un color base y como máximo un acento por gráfico, una familia y 3 tamaños, etiquetas directas sin leyendas salvo la escala de color del mapa (constitución v1.4.3), sin degradados decorativos, sin texto rotado. Corregir lo que falle.
- [ ] T043 [US4] [Navegador integrado] Abrir el enlace de lectura y aplicar de forma temporal un filtro de escala de grises a la página con la herramienta de JavaScript del navegador (solo inspección, sin tocar el informe). Comprobar con una captura que se leen los valores, el orden y el sentido de cada cambio.
- [ ] T044 [US4] Completar en `docs/dashboard.md` la tabla de contrastes con todos los pares de colores realmente usados en el informe y su contraste calculado con la fórmula de WCAG 2.1 (texto 4.5:1, elementos gráficos 3:1, "No aplica" en bordes decorativos).

**Checkpoint**: diseño y accesibilidad verificados.

---

## Phase 7: User Story 5 - Reconstruir y revisar el tablero desde su especificación escrita (Priority: P2)

**Goal**: `docs/dashboard.md` completo y comprobado con pruebas locales.

**Independent Test**: las pruebas de `tests/docs/` pasan y cada componente del informe aparece en la
especificación con el mismo valor.

- [ ] T045 [US5] Completar `docs/dashboard.md` con las secciones 10 a 12 del contrato: comportamientos comprobados en el producto (moneda MXN, `NULLIF`, flechas, comparación sin datos, fechas exactas del periodo anterior, Reset y fechas, sufijos compactos, Roboto, tamaño del valor de las tarjetas, `MX-CMX`), verificación contra el SQL (comandos de T016 y T017 y el registro completo de T028, T035 y T040) y compartir (modo, enlace de lectura, fecha y navegadores de T030 y T031). Comprobar que la sección de gráficos tiene la definición de "Top 10 de moléculas" (pares molécula-fabricante, con 6 moléculas distintas en el estado inicial). Revisar que cada componente del informe coincide con el documento y corregir el que no.
- [ ] T046 [US5] `git add tests/docs/test_dashboard_spec.py docs/dashboard.md` y ejecutar `make test` y `make lint-prosa` hasta que pasen.

**Checkpoint**: especificación completa y verificada.

---

## Phase 8: User Story 6 - Ver el gasto en un mapa como complemento (Priority: P3)

**Goal**: el Geo chart con las 32 entidades, incluida Ciudad de México.

**Independent Test**: las 32 entidades pintadas y Ciudad de México con color y tooltip.

- [ ] T047 [US6] [Chrome] Añadir "Gasto por entidad en el mapa, pesos (MXN)": *Geo chart* en x 540, y 270, 510 × 280, dimensión Entidad ISO (*Country subdivision (1st level)*), métrica Importe, zoom en México, escala de color mínimo `#DCEBF5` y máximo `#0072B2`, "Dataless" gris claro, leyenda de escala visible (constitución v1.4.3) y cross-filtering activo.
- [ ] T048 [US6] [Chrome] Probar `MX-CMX` en el orden de [research.md](research.md#r9-mapa-geo-chart-con-entidad_iso-y-la-prueba-de-mx-cmx): (1) con `ENTIDAD_ISO` tal cual, ver si Ciudad de México tiene color y tooltip (acercar el mapa si hace falta); (2) si no, crear en la fuente "Entidad ISO para mapa" = `CASE WHEN ENTIDAD_ISO = 'MX-CMX' THEN 'MX-DIF' ELSE ENTIDAD_ISO END` con tipo *Country subdivision (1st level)* y usarlo en el mapa; (3) si tampoco, cambiar a Google Maps con área rellena. Avisar al dueño antes de pasar de una opción a la siguiente. Comprobar que el mapa obedece a los controles y que las barras de entidades siguen legibles.
- [ ] T049 [US6] Registrar en `docs/dashboard.md` el resultado de la prueba de `MX-CMX`, la opción que quedó y su razón, y ejecutar `make lint-prosa`.

**Checkpoint**: mapa como complemento, sin sustituir las barras.

---

## Phase 9: User Story 7 - Seguir el recorrido de la Fase 3 en el README y la trazabilidad (Priority: P3)

**Goal**: README y matriz de trazabilidad con la Fase 3.

**Independent Test**: seguir el README desde el estado de la feature 004 y llegar a las cifras de
verificación y al enlace.

- [ ] T050 [P] [US7] Añadir al `README.md` la sección "Dashboard": qué fuente usa (vista, credenciales del propietario, frescura), cómo se verifica con `make bq-dashboard` y sus variables, qué ejecuta solo el dueño, que las consultas de Data Studio no pasan por `.bigqueryrc` y se pueden atribuir por sus labels (`requestor`, `looker_studio_report_id` y `looker_studio_datasource_id`), el enlace a `docs/dashboard.md` y el enlace de lectura del informe.
- [ ] T051 [P] [US7] Añadir a `docs/trazabilidad.md` la sección "Fase 3: dashboard" con una fila por requisito: conexión a la vista, filtro de fechas, filtro de entidad, filtro de institución y grupo institucional, filtro de grupo terapéutico y molécula, cada uno de los tres KPIs, gasto por entidad (barras y mapa), participación por institución, top 10 (con la definición: 10 pares molécula-fabricante, según el principio VI) y enlace de lectura, cada una con su componente y su verificación (prueba local, `make bq-dashboard` o registro de `docs/dashboard.md`).
- [ ] T052 [US7] `git add README.md docs/trazabilidad.md` y ejecutar `make lint-prosa`.

**Checkpoint**: Fase 3 documentada y trazada.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: cierre, revisión final y textos de entrega.

- [ ] T053 [Navegador integrado] Repetir V5 y V6 de [quickstart.md](quickstart.md) sobre el enlace de lectura con el informe terminado: cada control afecta a todos los componentes, el rango 2024-01-01 a 2025-12-31 da en las tarjetas el equivalente de 28 633.9 millones de pesos y 55.25 millones de piezas con la comparación en "-", el rango 2023-01-01 a 2023-12-31 deja las tarjetas en "-" sin cifras inventadas, la combinación vacía (SEMAR en una entidad donde no opera) muestra un estado vacío legible, la página carga en menos de 10 segundos y, con la ventana a 1366 px de ancho, las etiquetas de las 32 entidades se leen. Captura final.
- [ ] T054 [Dueño] Prueba de SC-005: una persona que no conozca el proyecto (el dueño si no hay nadie) abre el enlace de lectura y responde, cronometrada, cuál es la entidad y la institución con más importe y cuál es el par molécula-fabricante líder del top 10. Esperado: menos de 2 minutos. El dueño cuenta el resultado en el chat y Claude lo anota en la sección "Compartir" de `docs/dashboard.md`.
- [ ] T055 Buscar en los archivos nuevos y modificados el ID del proyecto (valor de `GOOGLE_CLOUD_PROJECT` en `.env`), correos, credenciales y cualquier referencia al documento de requisitos. No debe haber ninguna.
- [ ] T056 `git add` de cada archivo nuevo o modificado (revisando la lista, sin `git add -A`) y ejecutar `make test`, `make lint`, `make lint-sql` y `make lint-prosa` hasta que pasen.
- [ ] T057 Marcar las tareas completadas en este archivo y mostrar al dueño el mensaje del commit y la descripción del PR, ya pasados por `scripts/lint_prosa.sh`, con el título del PR en formato Conventional Commits (será el mensaje del commit de squash) y la descripción terminada en "Generated with [Claude Code](https://claude.com/claude-code)" sin emoji. Antes de abrir el PR, comprobar que la rama está al día con `main` y, si quedó atrás, actualizarla. Esperar su visto bueno antes de hacer commit, push o abrir el PR. El merge lo hace el dueño con squash.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias. T016 y T017 (dueño)
  dependen de T015, y T019 usa las cifras de T016.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de US1 (informe y fuente creados).
- **US3 (Phase 5)**: depende de US1. Se puede construir antes que US2, pero T040 compara el estado
  filtrado con Jalisco y necesita el control Entidad de US2.
- **US4 (Phase 6)**: depende de US1 a US3 y de US6, porque revisa el informe completo, mapa incluido.
- **US5 (Phase 7)**: T045 depende de US1 a US4 y de US6. Su prueba (`tests/docs/test_dashboard_spec.py`)
  se escribe en Foundational, antes del borrador de `docs/dashboard.md`.
- **US6 (Phase 8)**: depende de US1 y de T036 (las barras de entidades ya colocadas).
- **US7 (Phase 9)**: depende de T029 (enlace de lectura). Se puede hacer en paralelo con US4 a US6.
- **Polish (Phase 10)**: depende de todo lo anterior.

### User Story Dependencies

```text
Setup -> Foundational -> US1 -> US2 -> US3 -> US6 -> US4 -> US5 -> Polish
                                  \                          /
                                   -> US7 (después de T029) -
```

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- En Data Studio, cada componente se construye, se captura y se compara con `docs/dashboard.md`
  antes de pasar al siguiente.
- Las comparaciones con el SQL se anotan en el registro de verificación en cuanto se hacen.

### Parallel Opportunities

- Foundational: T004 y T005 (pruebas) en paralelo, y T006 a T010 (consultas) en paralelo.
- T018 (prueba de la especificación) en paralelo con cualquier tarea de Data Studio.
- US7 (T050 y T051) en paralelo con US4 a US6.
- Las tareas [Chrome] son secuenciales: hay un solo navegador y un solo informe abierto.

## Parallel Example: Foundational

```text
# Pruebas, juntas:
T004 tests/warehouse/test_dashboard_sql.py
T005 tests/warehouse/test_dashboard_command.py

# Consultas, juntas:
T006 sql/dashboard/kpis.sql
T007 sql/dashboard/kpis_por_anio.sql
T008 sql/dashboard/gasto_entidad.sql
T009 sql/dashboard/participacion_institucion.sql
T010 sql/dashboard/top10_molecula_fabricante.sql
```

## Implementation Strategy

### MVP First (User Story 1)

1. Setup y Foundational: consultas, `make bq-dashboard` con las cifras confirmadas por el dueño y
   borrador de `docs/dashboard.md`.
2. US1: fuente, informe, tarjetas y enlace de lectura comprobado sin sesión.
3. Parar y validar con el dueño. Desde aquí el enlace ya existe y cada historia lo mejora.

### Incremental Delivery

1. US2 añade los controles en cascada y el botón.
2. US3 añade las tres visualizaciones obligatorias y el cross-filtering.
3. US6 añade el mapa y resuelve `MX-CMX`.
4. US4 cierra diseño y accesibilidad con el recuadro de hallazgos.
5. US5 completa y prueba la especificación escrita.
6. US7 documenta la fase.
7. Polish: revisión final y textos de commit y PR aprobados.

Todo entra en un solo PR con squash merge, que hace el dueño.

## Notes

- [P] significa archivos distintos y sin dependencias pendientes.
- Claude narra cada paso en Data Studio antes de hacerlo y describe el resultado después, con una
  captura. Lo que no puede hacer en el navegador se lo explica al dueño paso a paso.
- Las tareas [Dueño] son las únicas que tocan GCP desde la terminal.
- Hay que hacer commit solo con el visto bueno del dueño (T057).
