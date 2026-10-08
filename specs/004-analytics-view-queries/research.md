# Research: Vista modelada y consultas analíticas

Decisiones de la Fase 0 con sus fuentes. Las rutas de la documentación de BigQuery son relativas a
`docs.cloud.google.com/bigquery/docs/` y se consultaron el 2026-10-08. Las pruebas de SQLFluff se
hicieron con la versión fijada en el repositorio (4.3.0) y la configuración `.sqlfluff`.

## R1. Sentencia de la vista: `CREATE OR REPLACE VIEW` con lista de columnas descritas

- **Decision**: la sección 3 es una sola sentencia:

  ```sql
  CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa (
      CLUE OPTIONS (description = '...'),
      ...
  )
  OPTIONS (description = '...')
  AS
  SELECT ...
  ```

  La lista de columnas tiene las 22 columnas en el orden del modelo de datos, cada una con su
  descripción. La vista lleva descripción, sin `expiration_timestamp`, sin labels y sin
  `friendly_name`.
- **Rationale**:
  - la referencia DDL (`reference/standard-sql/data-definition-language#create_view_statement`)
    solo admite descripciones de columna dentro de `CREATE VIEW` en `view_column_name_list` con
    `OPTIONS(view_column_option_list)`, y exige que "the number of columns in the column name list
    must match the number of columns in the underlying SQL query";
  - `OR REPLACE` es la semántica que la constitución pide para la vista (sección "Entregable SQL") y
    no destruye datos, porque una vista lógica no los almacena (`views-intro`);
  - el dueño eligió esta forma en la aclaración Q1 de la spec, para que un reemplazo nunca deje la
    vista sin descripciones;
  - las labels de una vista no llegan a la facturación (constitución, "Operación en BigQuery"), así
    que no aportan nada y se omiten (YAGNI).
- **Alternatives considered**: `ALTER VIEW ... ALTER COLUMN ... SET OPTIONS` después de crear la
  vista (`...data-definition-language#alter_column_set_options_statement`). Se descartó en la
  aclaración Q1: son 22 sentencias más, y un `CREATE OR REPLACE` ejecutado solo borraría las
  descripciones.
- **Verificación hecha**: SQLFluff 4.3.0 analiza la sentencia sin errores de parseo. El árbol tiene
  `create_view_statement` con un `bracketed` de `column_definition` (identificador más
  `options_segment`, sin tipo), un `options_segment` y un `select_statement`.

## R1b. Orden de los joins de la vista

- **Decision**: `COMPRAS AS compras`, después `INNER JOIN CUADRO_BASICO AS cuadro_basico` (161 filas)
  y después `INNER JOIN CLUE_CAT AS clue_cat` (2 000 filas). El chequeo 07 usa el mismo orden. El SQL
  no lleva un comentario que cite la guía (decisión del dueño, 2026-10-08).
- **Rationale**: la guía de rendimiento (`best-practices-performance-compute`, "Optimize your join
  patterns") recomienda "place the table with the largest number of rows first, followed by the
  table with the fewest rows, and then place the remaining tables by decreasing size". La misma guía
  aclara que el optimizador decide el lado de cada join, así que a este tamaño no cambian los bytes,
  el costo ni el resultado. La constitución solo exige `COMPRAS` primero y los catálogos después.
- **Alternatives considered**: el orden en que los requisitos nombran los catálogos (`CLUE_CAT` y
  después `CUADRO_BASICO`), que se lee igual que el enunciado pero no sigue la guía.

## R2. Alias del `SELECT` dentro de la vista y la regla AL09 de SQLFluff

- **Hallazgo**: la FR-006 de la spec dice que el `SELECT` repite como alias los nombres de la lista
  (`compras.CLUE AS CLUE`). SQLFluff marca cada uno de esos alias con
  `AL09 aliasing.self_alias.column` ("Column aliases should not alias to itself"), que forma parte
  del grupo `core` activo en `.sqlfluff`. Con 17 columnas que pasan sin cambio de nombre, serían 17
  violaciones.
- **Decision**: las columnas que pasan sin cambio de nombre van sin alias
  (`compras.CLUE`), porque el nombre de salida de una columna sin alias es el de la columna de origen
  (constitución, principio III, y `...data-definition-language#view_column_name_list`). Llevan alias
  con `AS` las cinco columnas cuyo nombre cambia o que se calculan (`FABRICANTE_COMPRA`,
  `FABRICANTE_CATALOGO`, `ANIO`, `MES`, `ENTIDAD_ISO`). Una prueba local comprueba que el nombre de
  salida de cada elemento del `SELECT` coincide, en la misma posición, con el nombre de la lista.
- **Rationale**: SQLFluff queda limpio sin excepciones y la regla "AS siempre" se cumple, porque
  aplica a todo alias que exista. Es el mismo estilo de `sql/checks/05_reconciliacion_join.sql`, donde
  `compras.IMPORTE` va sin alias.
- **Alternatives considered**: mantener los alias repetidos y desactivar AL09 en `.sqlfluff` o con
  `-- noqa: AL09` en la vista. Esa opción cumple la FR-006 al pie de la letra, pero mete una
  excepción de estilo en el entregable que más pesa.
- **Estado**: aprobada por el dueño el 2026-10-08. La FR-006 de la spec se ajustó en consecuencia.

## R3. Columnas y derivaciones de la vista

- **Decision**:
  - orden: las ocho columnas de `COMPRAS` (con `FABRICANTE` como `FABRICANTE_COMPRA`), las seis de
    `CLUE_CAT` sin su `CLUE`, las cinco de `CUADRO_BASICO` sin su `CLAVE` (con `FABRICANTE` como
    `FABRICANTE_CATALOGO`) y las tres derivadas, 22 en total ([data-model.md](data-model.md));
  - `ANIO = EXTRACT(YEAR FROM compras.FECHA)`, que devuelve `INT64`;
  - `MES = DATE_TRUNC(compras.FECHA, MONTH)`, que devuelve `DATE` (primer día del mes);
  - `ENTIDAD_ISO = CASE clue_cat.ENTIDAD WHEN 'Aguascalientes' THEN 'MX-AGU' ... END`, con las 32
    ramas y sin `ELSE`, de modo que un nombre desconocido da `NULL` y el chequeo de la vista lo
    detecta (R7).
- **Rationale**:
  - la constitución (principio III) permite en la vista "mes, año o código ISO 3166-2 de la
    entidad" y Data Studio usa ISO 3166-2 para *Country subdivision (1st level)* (principio VI);
  - la lista oficial ISO 3166-2:MX tiene 32 códigos y Ciudad de México es `MX-CMX`;
  - `EXTRACT` y `DATE_TRUNC` son funciones de fecha GA (`reference/standard-sql/date_functions`) y
    no son limpieza (`TRIM`, `REGEXP`, `CAST`), que la constitución prohíbe repetir en la vista;
  - un `CASE` evita una tabla auxiliar que los requisitos no piden. La guía de rendimiento pide
    "avoid repeatedly transforming data" y materializar las transformaciones costosas, con
    expresiones regulares y recortes de texto como ejemplo (`best-practices-performance-compute`).
    Un `CASE` de 32 comparaciones de igualdad no es de ese tipo y su costo es despreciable frente al
    de leer `COMPRAS`, así que no justifica una tabla materializada;
  - los nombres evitan la `Ñ` para no depender de los nombres de columna flexibles.
- **Alternatives considered**:
  - una tabla `ENTIDAD_ISO` unida a la vista: añade un objeto, una carga y un join que no pide el
    requisito;
  - `MES` como entero de 1 a 12: mezcla años en una serie temporal;
  - `FORMAT_DATE('%Y-%m', ...)` como texto: Data Studio no lo reconoce como fecha.

## R4. Modelo de la vista en el programa `warehouse`

- **Decision**: `warehouse/ddl.py` reconoce `create_view_statement` y produce un `ViewSpec` (nombre,
  descripción, consulta y columnas con nombre, tipo y descripción). Los tipos salen así:
  - una columna que es una referencia `alias.COLUMNA` toma el tipo de esa columna en el `TableSpec`
    de su tabla, resolviendo el alias con el `FROM` y los `INNER JOIN` de la vista;
  - una columna calculada toma el tipo de un diccionario `DERIVED_TYPES` en `warehouse/ddl.py`
    (`ANIO: INT64`, `MES: DATE`, `ENTIDAD_ISO: STRING`). Una prueba falla si una columna calculada
    no tiene tipo en el diccionario o si el diccionario tiene una columna que la vista no calcula.
- **Rationale**: los tipos hacen falta para dos cosas: la verificación de metadatos (FR-018) y las
  filas en línea del caso negativo de la vista (R8), que se convierten con `CAST` igual que las de
  las tablas. Derivarlos del SQL evita una segunda lista de columnas, y el diccionario cubre solo las
  tres expresiones que no se pueden leer de la DDL.
- **Alternatives considered**:
  - leer el esquema del dry run (`statistics.query.schema`): exige GCP en las pruebas y en los casos
    negativos;
  - inferir el tipo de cada expresión desde el árbol de SQLFluff: mucho código para tres columnas;
  - escribir `CAST` en las derivaciones de la vista: ruido en el entregable y contrario al espíritu
    de "conversiones solo cuando hacen falta".

## R5. Consultas de la sección 4

Cuatro sentencias `SELECT`, en este orden, cada una con un comentario en inglés que dice la pregunta
de negocio y la definición que usa. Todas leen solo `farma_analytics.v_compras_farma_completa AS
vista`. El contrato completo está en [contracts/consultas.md](contracts/consultas.md).

- **P1, las 5 moléculas con más `IMPORTE`**: una CTE agrega por `MOLECULA` (`SUM(IMPORTE)`,
  `SUM(PIEZAS)`, `AVG(IMPORTE)` y la participación con `SUM(SUM(vista.IMPORTE)) OVER ()`), y el
  `SELECT` final redondea, ordena por el importe sin redondear de mayor a menor con desempate por
  `MOLECULA` y termina en `LIMIT 5`.
  - `AVG(IMPORTE)` es el importe promedio por línea de compra: una media simple con significado de
    negocio, que la constitución permite y la FR-013 pide.
  - La función de ventana sobre el agregado da el total sin un segundo recorrido de la vista
    (constitución, "usar funciones de ventana en lugar de self-joins"). Según el orden de
    evaluación documentado en `reference/standard-sql/query-syntax#qualify_clause`, la ventana se
    calcula antes de `LIMIT`, así que el total incluye todas las moléculas.
- **P2, la institución y la entidad con mayor volumen**: una CTE agrega con
  `GROUP BY GROUPING SETS ((vista.INSTITUCION, vista.ENTIDAD), (vista.INSTITUCION), (vista.ENTIDAD))`
  y marca el nivel con `GROUPING()`. Otra CTE pasa `IMPORTE` y `PIEZAS` a filas con `UNPIVOT`
  (`PIEZAS` con `CAST` explícito a `NUMERIC`, porque la referencia de `UNPIVOT` exige tipos
  equivalentes en las columnas que se rotan y aclara que "data types can't be coerced to a common
  supertype"). El
  `SELECT` final calcula la participación con `SUM(...) OVER (PARTITION BY nivel, medida)` y se
  queda con el líder con `QUALIFY RANK() OVER (PARTITION BY nivel, medida ORDER BY valor DESC) = 1`.
  - `GROUPING SETS` y `GROUPING()` son GA: ni `reference/standard-sql/query-syntax` ni la función
    `GROUPING` de `reference/standard-sql/aggregate_functions` llevan marca de Preview (en esa
    página solo la lleva `AGG`). Con él la vista se lee una vez, mientras que tres CTE unidas con
    `UNION ALL` la leerían tres veces, porque las CTE no se materializan (constitución, principio
    II).
  - `RANK` muestra a todos los empatados en el primer lugar (aclaración de la spec, FR-011).
  - El `SELECT` final de P2 usa `QUALIFY` sin `WHERE`, `GROUP BY` ni `HAVING`. La referencia actual
    (`query-syntax#qualify_clause`) solo exige una función de ventana en `QUALIFY` o en el `SELECT`,
    pero sus dos ejemplos llevan `WHERE`, y cuando `QUALIFY` salió BigQuery exigía alguna de esas
    cláusulas. No hay fuente que confirme si la restricción sigue, así que antes de escribir P2 el
    dueño hace un dry run gratis de una consulta mínima (quickstart V0b). Si falla, el `SELECT` final
    añade `WHERE volumen_por_medida.VALOR > 0`, un filtro con sentido de negocio (un grupo sin volumen
    no puede ser líder) que no cambia el resultado ni la participación, y se sigue usando `QUALIFY`.
  - Resultado de V0b (2026-10-08): el dry run validó la consulta sin `WHERE` (0 bytes), así que P2
    usa `QUALIFY` sin el filtro alternativo.
  - La ventana de participación se evalúa antes de `QUALIFY`, así que el denominador es el total
    del nivel y de la medida, igual al total de la vista.
- **P3, el precio promedio por pieza por molécula y fabricante**: `GROUP BY vista.MOLECULA,
  vista.FABRICANTE_COMPRA`, con `SUM(IMPORTE)`, `SUM(PIEZAS)` y
  `SAFE_DIVIDE(SUM(vista.IMPORTE), SUM(vista.PIEZAS))`, redondeado solo en el `SELECT` final.
  Ordena por `MOLECULA`, precio de mayor a menor y fabricante. Con los datos actuales devuelve 497
  filas.
- **P3 alternativa, por fabricante de catálogo**: la misma consulta con `FABRICANTE_CATALOGO`.
  Devuelve 139 filas, una por molécula, porque cada molécula tiene un solo fabricante de referencia.
  Así la alternativa también es el precio promedio de cada molécula en todo el mercado.
- **Rationale común**:
  - `GROUP BY` con nombres de columna;
  - `ROUND` solo en el `SELECT` final y `ORDER BY` solo en la consulta más externa;
  - una responsabilidad por CTE;
  - todo es GA;
  - todo se comprobó con SQLFluff 4.3.0 sobre un borrador (`GROUPING SETS`, `GROUPING()`,
    `UNPIVOT`, `QUALIFY` y la vista se analizan sin errores).
- **Alternatives considered**:
  - una sola consulta para las tres preguntas: mezcla granos distintos y no se lee;
  - `ROW_NUMBER` en P2: oculta empates sin avisar;
  - P3 alternativa como columna extra de P3: los dos fabricantes tienen granos distintos.

## R6. Cifras cruzadas en `make bq-consultas`

- **Decision**: antes de las cuatro consultas, el programa ejecuta `sql/ops/totales_vista.sql`
  (filas, `SUM(IMPORTE)` y `SUM(PIEZAS)` de la vista, con dry run y labels). Si la vista tiene 0
  filas, se detiene con "La vista no tiene filas: ejecuta 'make bq-load'.", porque sobre 0 filas
  todas las reglas cuadrarían y no probarían nada. Después de las consultas compara en Python con
  `Decimal`. La salida JSON de `bq` se lee con `json.loads(..., parse_float=Decimal)` y cada valor
  se convierte con `Decimal(str(valor))`, para que la comparación sea exacta tanto si `bq` imprime un
  `NUMERIC` como texto como si lo imprime como número:
  - C1: la suma de `IMPORTE_TOTAL` y `PIEZAS_TOTALES` de P3 es igual al total de la vista;
  - C2: lo mismo para P3 alternativa;
  - C3: el `IMPORTE_TOTAL` y las `PIEZAS_TOTALES` de cada molécula de P1 son iguales a la suma de sus
    filas en P3;
  - C4: la participación de P1 y P2 difiere como máximo 0.01 puntos de `100 × valor / total`,
    calculado con el total de la vista. La tolerancia existe porque BigQuery redondea el cociente
    `NUMERIC` a 9 decimales antes de multiplicar por 100 y redondear a 2, y un valor justo en el
    límite de redondeo podría diferir en la última cifra;
  - C5: en P2, el valor del líder de la combinación no supera al del líder de la institución ni al de
    la entidad, para cada medida.
- **Rationale**: SC-002 pide cifras que cuadran entre consultas, y la constitución (principio VII)
  exige que el SQL, el dashboard y los documentos den las mismas cifras. `IMPORTE` tiene dos
  decimales en origen, así que las sumas también, y `ROUND(..., 2)` no las altera: C1, C2, C3 y C5
  son exactas. La consulta de totales vive en `sql/ops/` porque no es una pregunta ni un chequeo, igual que
  la huella de la feature 003.
- **Alternatives considered**: una consulta SQL que compare las cuatro respuestas: repetiría la
  lógica de la sección 4, que dejaría de ser la única implementación de cada pregunta.

## R7. Chequeo de la vista: `sql/checks/07_reconciliacion_vista.sql`

- **Decision**: misma forma que `05_reconciliacion_join.sql`. Varias CTE calculan:
  - las filas y las sumas de la vista;
  - las nulas de `ANIO`, `MES` y `ENTIDAD_ISO` con `COUNTIF`;
  - las filas de `COMPRAS`;
  - las filas huérfanas con `NOT EXISTS`;
  - las sumas del `INNER JOIN` sobre las tablas base.

  Un `UNNEST` de `STRUCT` produce una fila por comparación, y el `WHERE` deja solo las que no
  cuadran. `CHEQUEO = 'reconciliacion_vista'` y `OBJETO = 'v_compras_farma_completa'`. No tiene
  parámetros: compara la vista con las tablas base, y el chequeo 05 ya compara los huérfanos con el
  manifiesto.
- **Rationale**: es la verificación del principio III ("COUNT(*) de la vista es igual a las filas de
  COMPRAS menos los huérfanos") y de la FR-016. Las sumas de `PIEZAS` y los nulos de las derivadas
  cuestan poco y detectan una vista mal escrita (por ejemplo, un join que duplica filas o una entidad
  sin código). El chequeo lee `COMPRAS` varias veces (la vista, el `INNER JOIN` y los `NOT EXISTS`),
  algo que la guía de rendimiento desaconseja ("avoid repeated joins and subqueries"). Se acepta
  porque son unos pocos MB por lectura, muy por debajo de `maximum_bytes_billed`, y separar las
  lecturas deja cada comparación legible. Los bytes estimados del dry run de T024 son la evidencia.
- **Alternatives considered**: comparar con `@filas_compras − @huerfanos_clue − @huerfanos_clave`:
  supone que los dos tipos de huérfanos nunca coinciden en una fila. Hoy es así, pero lo garantiza
  el generador, no BigQuery.

## R8. Caso negativo del chequeo de la vista

- **Decision**: `sql/checks/negativos/07_reconciliacion_vista.json` trae filas para `COMPRAS`,
  `CLUE_CAT`, `CUADRO_BASICO` y para la propia vista. Las filas de la vista simulan una vista
  rota: una línea duplicada y una fila con `ENTIDAD_ISO` nulo. `checks.inline_tables` sustituye cada
  `farma_analytics.<OBJETO> AS <alias>` por sus filas, usando las columnas y los tipos del
  `TableSpec` o del `ViewSpec` (R4), y conserva la comprobación de que no queda ninguna referencia
  real.
- **Rationale**: si el caso negativo construyera la vista a partir de las filas base, la vista
  siempre cuadraría con el `INNER JOIN` y el chequeo nunca podría fallar. Sigue siendo el mismo
  archivo de `sql/checks/`, sin copias, y no lee tablas, no crea objetos y no factura bytes (R15 de
  la feature 003).
- **Alternatives considered**: crear una vista rota temporal en un dataset auxiliar: crea objetos,
  cuesta y deja restos si falla.

## R9. Despliegue de la vista y momento de los chequeos (aclaración Q2 de la spec)

- **Decision**:
  - `make bq-schema` sigue ejecutando solo las secciones 1 y 2 y verifica los metadatos del dataset
    y las tablas.
  - `make bq-load` no toca la vista. Después de cargar ejecuta los seis chequeos de tablas. Si la
    vista existe (lo dice `bq show`), también ejecuta el chequeo 07 y verifica sus metadatos. Si no
    existe, imprime "La vista no está desplegada: ejecuta 'make bq-vista'." y no falla por eso.
  - `make bq-vista` (nuevo, `python -m warehouse vista`) hace el dry run y ejecuta la sección 3, y
    después corre la verificación de metadatos completa y los siete chequeos.
  - `make bq-checks` ejecuta los siete chequeos y la verificación completa, y falla si falta la vista.
  - `make bq-consultas` (nuevo, `python -m warehouse consultas`) falla antes de ejecutar nada si falta
    la vista.
- **Rationale**: la carga y la vista quedan desacopladas, como pidió el dueño, y el principio IV se
  cumple: los chequeos corren después de cada cambio en la vista y después de cada carga, con el de
  la vista incluido cuando la vista existe. Un chequeo "aplica a la vista" si su SQL referencia
  `farma_analytics.v_compras_farma_completa` fuera de comentarios y cadenas.
- **Alternatives considered**: las opciones A, B y C de la aclaración, descartadas por el dueño.

## R10. Lectura de la sección 4 desde el programa

- **Decision**: `warehouse/ddl.py` clasifica como `query` las sentencias `select_statement`,
  `with_compound_statement` y `set_expression` (un `UNION ALL`, como el chequeo 02). `make bq-consultas` exige exactamente cuatro, en el orden de R5, y les
  asigna los identificadores fijos `P1`, `P2`, `P3` y `P3_CATALOGO`. `make bq-schema` y
  `make bq-vista` ignoran las consultas.
- **Rationale**: el `.sql` es la única fuente de las consultas (FR-021). Usar el orden en lugar de
  marcas especiales en los comentarios deja el entregable limpio, y la prueba local del número de
  consultas evita que una sentencia nueva se cuele sin contrato.
- **Alternatives considered**: un archivo por consulta en `sql/consultas/`: duplicaría el
  entregable, que tiene que ejecutarse solo en la consola.

## R11. Salida de `make bq-consultas` y límite de filas

- **Decision**: cada consulta corre con `--format=json` y `--max_rows=10000`. Si una consulta
  devuelve 10 000 filas, el objetivo falla porque el resultado podría estar truncado. P1 y P2 se
  imprimen completas. P3 y P3 alternativa imprimen su número de filas y las 20 primeras en el orden
  de la consulta, con una nota que dice que la consola muestra todas. Al final imprime el resultado
  de C1 a C5.
- **Rationale**: `bq query` muestra 100 filas por defecto (`--max_rows`), y P3 devuelve 497. La FR-023
  pide decir cuántas filas hubo y no truncar en silencio.
- **Alternatives considered**: imprimir las 497 filas, que entierra las otras respuestas, o escribir
  un archivo de resultados, que no pide nadie.

## R12. Pruebas locales sin GCP

- **Decision**: pytest en `tests/warehouse/` con el ejecutor falso de `bq` de la feature 003:
  - `test_view_sql.py`: reglas de [contracts/vista.md](contracts/vista.md) sobre la sección 3. Entre
    ellas, que las 32 entidades de `generator/reference/entidades.csv` tengan exactamente la rama
    ISO de una lista oficial fijada en la prueba;
  - `test_queries_sql.py`: reglas de [contracts/consultas.md](contracts/consultas.md) sobre la
    sección 4;
  - `test_view_parser.py`: `ViewSpec`, tipos derivados y `DERIVED_TYPES`;
  - `test_view_command.py` y `test_queries_command.py`: orden dry run y ejecución, fallos y códigos de
    salida;
  - `test_cross_figures.py`: C1 a C5 con resultados de ejemplo que cuadran y que no cuadran;
  - ampliaciones de `test_metadata.py`, `test_load_command.py`, `test_checks_command.py`,
    `test_checks_sql.py` y `test_negative_checks.py` para la vista y el séptimo chequeo.
- **Rationale**: las reglas de estilo y de contrato se comprueban sin credenciales en CI, como en la
  feature 003, y BigQuery solo hace falta para la validación del [quickstart](quickstart.md).

## R13. Documentación para lectores

- **Decision**:
  - El README añade una sección de la Fase 2 con los tres pasos (`make bq-vista`, `make bq-checks`
    y `make bq-consultas`) y una tabla de definiciones de las cuatro ambigüedades. También añade el
    glosario de métricas del principio VII (Monto Total, Piezas y Precio Promedio).
  - `docs/trazabilidad.md` añade la sección "Fase 2: consultas SQL y modelado".
  - Las cifras que aparezcan salen de `make bq-consultas`, no de los parámetros del generador.
- **Rationale**: lo piden la FR-015, la FR-026 y los principios I, VII y IX. El glosario va en el
  README porque es corto y lo leerán el dashboard y los hallazgos de las features siguientes.
- **Alternatives considered**: un `docs/glosario.md` aparte: un archivo más para tres líneas.

## R14. Dataform

- **Decision**: sin cambios. `@dataform/cli` sigue en `package.json` con el riesgo R18 aceptado
  (R13 de la feature 003). El `declaration` de la vista que menciona la tabla de stack no se crea,
  porque no hay proyecto Dataform.
- **Rationale**: la decisión de la feature 003 sigue vigente y retirarlo es otro PR (chore).

## R15. Claves primarias `NOT ENFORCED` en los catálogos

- **Decision**: no se declaran en esta feature.
- **Rationale**: la guía de rendimiento recomienda "specify key constraints in the table schema when
  table data satisfies the data integrity requirements", porque el optimizador las usa, y la
  constitución las permite (MAY) en `CLUE_CAT` y `CUADRO_BASICO` una vez validada la unicidad, que ya
  comprueba el chequeo 02. No hay una mejora medida que las justifique con 161 y 2 000 filas, y
  añadirlas exige `ALTER TABLE ... ADD PRIMARY KEY (...) NOT ENFORCED` sobre tablas ya cargadas,
  porque `CREATE TABLE IF NOT EXISTS` no modifica una tabla existente. Las claves foráneas siguen
  prohibidas por los huérfanos (constitución, principio III).
- **Alternatives considered**: declararlas ahora. Queda como opción si una feature mide un beneficio.

## Fuentes

- BigQuery, `reference/standard-sql/data-definition-language`: `create_view_statement`,
  `view_column_name_list`, `view_column_option_list` y `alter_column_set_options_statement`.
- BigQuery, `reference/standard-sql/query-syntax`: `qualify_clause` (orden de evaluación),
  `group_by_grouping_sets`, función `GROUPING` y `unpivot_operator`.
- BigQuery, `reference/rest/v2/tables`: `type` (`VIEW`), `view.query` y `view.useLegacySql`.
- BigQuery, `reference/standard-sql/date_functions`: `EXTRACT` y `DATE_TRUNC`.
- BigQuery, `views-intro`: comportamiento y limitaciones de las vistas lógicas (referencias
  calificadas con el dataset, sin parámetros, esquema guardado al crear la vista).
- BigQuery, `best-practices-performance-compute`: orden de los joins, CTE evaluadas varias veces,
  transformaciones repetidas, joins y subconsultas repetidos, y claves primarias.
- BigQuery, `information-schema-intro`: mínimo de 10 MB facturados.
- ISO 3166-2:MX, 32 códigos de subdivisión (`MX-AGU` a `MX-ZAC`, `MX-CMX` para Ciudad de México),
  consultado en `en.wikipedia.org/wiki/ISO_3166-2:MX`.
- SQLFluff 4.3.0, regla `AL09` (`aliasing.self_alias.column`), comprobada con `sqlfluff rules` y
  con un borrador de la vista y de P2.
