# Feature Specification: Vista modelada y consultas analíticas (secciones 3 y 4 del `.sql`)

**Feature Branch**: `004-analytics-view-queries`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Vista y consultas analíticas: añadir las secciones 3 y 4 de sql/farma_analytics.sql. La sección 3 crea con CREATE OR REPLACE VIEW la vista lógica farma_analytics.v_compras_farma_completa, que une COMPRAS con CLUE_CAT (vía CLUE) y con CUADRO_BASICO (vía CLAVE) mediante INNER JOIN, con COMPRAS primero, alias semánticos y una lista explícita de columnas sin SELECT *. Su grano es una fila por cada fila de COMPRAS que tiene correspondencia en ambos catálogos, sin agregaciones, DISTINCT ni ORDER BY. Conserva los nombres de los requisitos en UPPER_SNAKE_CASE, desambigua FABRICANTE como FABRICANTE_COMPRA y FABRICANTE_CATALOGO, y puede añadir derivaciones deterministas por fila útiles para el dashboard (año, mes y código ISO 3166-2 de la entidad), nunca un precio promedio por fila. La vista y cada una de sus columnas llevan descripción en español, y las referencias van calificadas con el dataset y sin ID de proyecto. La sección 4 contiene las consultas analíticas, que leen solo de la vista y responden tres preguntas: las 5 moléculas con más IMPORTE; la institución y la entidad que concentran el mayor volumen de compra; y el precio promedio por pieza, calculado como SUM(IMPORTE) / SUM(PIEZAS) con SAFE_DIVIDE, por molécula y fabricante. Las ambigüedades (si volumen de compra es IMPORTE o PIEZAS, qué FABRICANTE se usa, si institución y entidad se evalúan juntas o por separado, y cómo se tratan los empates) se resuelven con definiciones explícitas y documentadas, presentando ambas interpretaciones cuando sea barato. GROUP BY nombra las columnas, ROUND se aplica solo en la presentación, el top-N usa ORDER BY ... LIMIT y el top por grupo usa QUALIFY con el desempate documentado. Cada sentencia pasa por un dry run antes de ejecutarse, lleva labels, respeta el maximum_bytes_billed de .bigqueryrc y pasa SQLFluff, con un comentario en inglés que dice qué pregunta de negocio responde. Por el principio IV, los chequeos se ejecutan después de cada cambio en la vista: hay que añadir en sql/checks/ la reconciliación de la vista (su COUNT(*) es igual a las filas de COMPRAS menos los huérfanos y su IMPORTE es igual al del INNER JOIN), con su caso negativo, y extender la verificación de metadatos a la vista y a las descripciones de sus columnas. Hay objetivos de make para desplegar la vista y ejecutar las consultas, construidos sobre el programa warehouse existente, y el README y la matriz de trazabilidad cubren esta fase. Yo ejecuto todo lo que toca GCP. El éxito se mide con la vista creada con 298 500 filas, las tres preguntas respondidas con cifras que cuadran entre consultas, todos los chequeos (incluido el de la vista) en 0 filas, cada chequeo detectando su caso negativo y el .sql completo ejecutándose de principio a fin en la consola de BigQuery."

## Clarifications

### Session 2026-10-08

- Q: ¿Cómo se describen las columnas de la vista, con la lista de columnas de `CREATE VIEW` y
  `OPTIONS(description = ...)` o con `ALTER VIEW ... ALTER COLUMN ... SET OPTIONS` después de crearla?
  → A: Con la lista de columnas dentro de la misma sentencia, con los mismos nombres como alias en el
  `SELECT`. Así un `CREATE OR REPLACE` nunca deja la vista sin descripciones. El plan justifica la
  desviación de la preferencia de la constitución por los alias del `SELECT`. (La aclaración Q3
  ajustó después el punto de los alias: las columnas sin cambio de nombre van sin alias.)
- Q: La vista necesita las tablas y su chequeo necesita datos. ¿Qué paso despliega la vista en el
  recorrido desde cero y cómo se cumple que los chequeos corran después de cada carga y de cada
  cambio en la vista? → A: Carga y vista desacopladas. El recorrido es `bq-schema` (secciones 1 y
  2), `bq-load` y `bq-vista`. `bq-load` no toca la vista: ejecuta los seis chequeos de tablas y,
  si la vista existe, también el suyo; si no existe, avisa que hay que desplegarla sin fallar.
  `bq-vista` despliega solo la sección 3 y ejecuta los siete chequeos, de modo que cambiar la vista
  no exige cargar. `bq-checks` ejecuta los siete y falla si falta la vista.
- Q: SQLFluff marca con AL09 los alias que repiten el nombre de origen (`compras.CLUE AS CLUE`).
  ¿Se quitan esos alias o se desactiva la regla? → A: Se quitan. Las columnas que pasan sin cambio
  de nombre van sin alias y llevan `AS` solo las que cambian de nombre o se calculan. Una prueba
  comprueba que cada nombre de salida coincide con la lista de columnas en la misma posición.

## User Scenarios & Testing *(mandatory)*

> Nota de alcance: los "usuarios" de esta feature son el dueño del repositorio (que ejecuta todo lo
> que toca GCP), cualquier persona que reproduzca la solución desde un clon limpio y, de forma
> indirecta, el equipo comercial de un laboratorio que leerá las respuestas y el dashboard de la
> feature siguiente. BigQuery, `bq`, el `.bigqueryrc` versionado, el `Makefile`, el programa
> `warehouse`, SQLFluff, el dry run, `maximum_bytes_billed` y el archivo `sql/farma_analytics.sql`
> los imponen el documento de requisitos y la constitución (principios I a IV y VIII, tabla de stack
> y sección "Entregable SQL"), así que forman parte del QUÉ.

### User Story 1 - Publicar la vista modelada para BI (Priority: P1)

El dueño despliega la vista `farma_analytics.v_compras_farma_completa` desde la sección 3 de
`sql/farma_analytics.sql`. La vista une cada línea de `COMPRAS` con su unidad médica de `CLUE_CAT` y
con su insumo de `CUADRO_BASICO`, descarta las líneas huérfanas y expone todas las columnas de los
requisitos con sus nombres, las dos columnas de fabricante con nombres distintos y unas pocas
derivaciones por fila que el dashboard necesita (año, mes y código ISO 3166-2 de la entidad). La
vista y cada columna tienen descripción en español. Al terminar el despliegue se ejecutan todos los
chequeos de calidad, incluido el nuevo chequeo de la vista.

**Why this priority**: la vista es el entregable que exige la Fase 2, la única fuente de las
consultas analíticas y del dashboard (principio III), y el criterio de modelado pesa un 20 %.

**Independent Test**: con las tablas cargadas, desplegar la vista y comprobar con `bq show` (sin
costo) su descripción y la de sus columnas, y con el chequeo de la vista que tiene 298 500 filas y el
mismo `IMPORTE` que el `INNER JOIN` sobre las tablas base.

**Acceptance Scenarios**:

1. **Given** las tres tablas cargadas con los datos del manifiesto, **When** el dueño despliega la
   vista, **Then** existe `farma_analytics.v_compras_farma_completa` como vista lógica, con
   descripción y con las columnas de la entidad "Vista" en ese orden, cada una con descripción.
2. **Given** la vista desplegada, **When** se ejecutan los chequeos, **Then** el chequeo de la vista
   devuelve 0 filas: su número de filas es igual a las filas de `COMPRAS` menos las filas huérfanas
   (298 500 = 300 000 − 1 500) y sus sumas de `IMPORTE` y `PIEZAS` son iguales a las del
   `INNER JOIN` sobre las tablas base.
3. **Given** la vista desplegada, **When** se despliega otra vez sin cambios, **Then** termina sin
   error, la vista conserva sus descripciones y los chequeos siguen en 0 filas.
4. **Given** la definición de la vista, **When** se revisa con las pruebas locales, **Then** no tiene
   `SELECT *`, agregaciones, `DISTINCT`, `ORDER BY`, `ROUND` ni precio por fila, usa solo
   `INNER JOIN ... ON` con `COMPRAS` primero y alias `compras`, `clue_cat` y `cuadro_basico`, y sus
   referencias van calificadas con `farma_analytics` sin ID de proyecto.
5. **Given** una vista publicada que difiere de la sección 3 (por ejemplo, sin la descripción de una
   columna), **When** se ejecutan los chequeos, **Then** la verificación de metadatos informa la
   diferencia y el objetivo falla.
6. **Given** un clon limpio con el esquema creado y sin la vista, **When** el dueño ejecuta la carga,
   **Then** la carga no crea la vista, los seis chequeos de tablas devuelven 0 filas, el mensaje
   indica que falta desplegar la vista y el objetivo termina con éxito.
7. **Given** la vista desplegada, **When** el dueño vuelve a cargar los datos, **Then** la carga no
   reemplaza la vista y ejecuta los siete chequeos, incluido el de la vista.
8. **Given** la vista desplegada y una modificación de la sección 3, **When** el dueño despliega la
   vista, **Then** no hace falta cargar: se reemplaza solo la vista y corren los siete chequeos.
9. **Given** que la vista no existe, **When** el dueño ejecuta el objetivo de chequeos, **Then** el
   objetivo falla e indica que hay que desplegarla.

---

### User Story 2 - Responder las tres preguntas comerciales (Priority: P1)

El dueño ejecuta las consultas de la sección 4, que leen solo de la vista, y obtiene las respuestas a
las tres preguntas de la Fase 2: las 5 moléculas con más `IMPORTE`, la institución y la entidad que
concentran el mayor volumen de compra y el precio promedio por pieza por molécula y fabricante. Cada
ambigüedad tiene una definición escrita y, donde es barato, la consulta muestra las dos
interpretaciones. Las cifras de las tres consultas cuadran entre sí y con el total de la vista.

**Why this priority**: es la otra mitad de la Fase 2 y el criterio SQL & BigQuery (agrupaciones,
`SUM`, `AVG`, alias) pesa un 40 %.

**Independent Test**: con la vista desplegada, ejecutar el objetivo de consultas y comprobar que
imprime las tres respuestas, que cada consulta pasó por dry run y quedó bajo el límite de bytes, y que
la verificación de cifras cruzadas no encuentra diferencias.

**Acceptance Scenarios**:

1. **Given** la vista desplegada, **When** se ejecuta la consulta de la pregunta 1, **Then** devuelve
   exactamente 5 moléculas ordenadas por `IMPORTE` total de mayor a menor (empates resueltos por
   nombre de molécula), con su importe, sus piezas y su participación en el importe total de la vista.
2. **Given** la vista desplegada, **When** se ejecuta la consulta de la pregunta 2, **Then** muestra
   el líder por `IMPORTE` (definición principal) y por `PIEZAS` (interpretación alternativa) para la
   combinación institución-entidad, para la institución sola y para la entidad sola, con su valor y su
   participación, y si hay empate en el primer lugar muestra todos los empatados.
3. **Given** la vista desplegada, **When** se ejecuta la consulta de la pregunta 3, **Then** devuelve
   una fila por molécula y `FABRICANTE_COMPRA` con importe, piezas y precio promedio
   `SUM(IMPORTE) / SUM(PIEZAS)` calculado con división segura y redondeado solo al presentar, y la
   interpretación alternativa con `FABRICANTE_CATALOGO` también está disponible.
4. **Given** las respuestas de las tres consultas, **When** se cruzan sus cifras, **Then** la suma de
   `IMPORTE` y `PIEZAS` de la pregunta 3 es igual al total de la vista, el `IMPORTE` de cada molécula
   de la pregunta 1 es igual a la suma de sus filas en la pregunta 3, y las participaciones de las
   preguntas 1 y 2 usan ese mismo total.
5. **Given** que la vista no existe, **When** se ejecuta el objetivo de consultas, **Then** se detiene
   antes de ejecutar nada con un mensaje que indica cómo desplegarla.
6. **Given** una consulta que superaría el `maximum_bytes_billed` de `.bigqueryrc` o con un error,
   **When** se ejecuta el objetivo, **Then** el dry run o el job fallan sin facturar y el mensaje dice
   qué consulta falló.

---

### User Story 3 - Ejecutar el `.sql` entregable de principio a fin en la consola (Priority: P2)

Una persona abre `sql/farma_analytics.sql` en la consola de BigQuery, con el proyecto que ya tiene
las tablas cargadas, y lo ejecuta completo sin otras herramientas. Las secciones 1 y 2 no tocan los
datos, la sección 3 reemplaza la vista y la sección 4 muestra las respuestas a las tres preguntas.

**Why this priority**: es la definición de terminado del entregable `.sql` (constitución, "Entregable
SQL"), pero depende de las historias 1 y 2.

**Independent Test**: pegar el archivo completo en la consola, ejecutarlo y comprobar que cada
sentencia termina sin error, que las cifras coinciden con las del objetivo de consultas y que el
número de filas de las tres tablas no cambia.

**Acceptance Scenarios**:

1. **Given** las tablas cargadas, **When** se ejecuta el archivo completo en la consola, **Then**
   todas las sentencias terminan sin error y las tres respuestas coinciden con las del objetivo de
   consultas.
2. **Given** las tablas cargadas, **When** se ejecuta el archivo completo dos veces, **Then** las tres
   tablas conservan sus filas (300 000, 2 000 y 161) y la vista sigue pasando su chequeo.

---

### User Story 4 - Demostrar que el chequeo de la vista detecta errores (Priority: P2)

El chequeo nuevo de la vista tiene su caso negativo versionado, como los seis chequeos existentes.
El objetivo de casos negativos lo ejecuta con filas preparadas en lugar de las tablas y la vista
reales, sin leer datos ni facturar bytes, y confirma que lo detecta.

**Why this priority**: el principio IV exige chequeos que fallen cuando deben. Un chequeo que nunca
falla no prueba nada.

**Independent Test**: ejecutar el objetivo de casos negativos y ver 7 de 7 casos detectados con 0
bytes facturados.

**Acceptance Scenarios**:

1. **Given** el caso negativo de la vista (por ejemplo, una fila de la vista duplicada o con un
   `IMPORTE` distinto del de su línea de `COMPRAS`), **When** se ejecutan los casos negativos,
   **Then** el chequeo de la vista devuelve al menos una fila que la identifica y el objetivo termina
   con éxito.
2. **Given** un chequeo que devuelve 0 filas con su caso negativo, **When** se ejecutan los casos
   negativos, **Then** el objetivo falla y dice cuál.

---

### User Story 5 - Seguir el recorrido documentado de la Fase 2 (Priority: P3)

Una persona lee en el README cómo desplegar la vista y ejecutar las consultas, qué definición usa
cada pregunta ambigua y qué cifras esperar. La matriz de trazabilidad relaciona los requisitos de la
Fase 2 con sus artefactos y verificaciones.

**Why this priority**: lo exigen la reproducibilidad (principio VIII) y la matriz de trazabilidad
(principio I), pero no bloquea la vista ni las consultas.

**Independent Test**: seguir el README desde el estado que deja la feature 003 y llegar a la vista
desplegada, a los chequeos en 0 filas y a las tres respuestas sin pasos no escritos.

**Acceptance Scenarios**:

1. **Given** las tablas cargadas, **When** se siguen los pasos de la Fase 2 del README, **Then** se
   llega a la vista con 298 500 filas, a los siete chequeos en 0 filas y a las tres respuestas.
2. **Given** la matriz de trazabilidad, **When** se revisan las filas de la Fase 2, **Then** la vista,
   cada una de las tres preguntas y cada definición de ambigüedad apuntan a su artefacto y a su
   verificación.

---

### Edge Cases

- Primera carga en un clon limpio: la vista todavía no existe, así que su chequeo no aplica. La
  carga lo dice en su salida y no falla, y el objetivo de chequeos sí falla mientras la vista falte.
- Recarga con datos nuevos (por ejemplo, otra `orphan_rate`): la definición de la vista no cambia,
  pero sí sus filas, y por eso la carga ejecuta el chequeo de la vista cuando la vista existe.
- `CREATE OR REPLACE VIEW` reemplaza la vista completa: las descripciones de las columnas se tienen que
  fijar en la misma sentencia o se pierden con cada despliegue.
- Una `ENTIDAD` que no está entre los 32 nombres oficiales (por ejemplo, con otra grafía) no tendría
  código ISO: el chequeo de la vista tiene que detectarlo en lugar de dejar un nulo silencioso.
- Ciudad de México usa el código vigente `MX-CMX` (antes `MX-DIF`). Que Data Studio lo reconozca en
  un mapa se comprueba en la feature del dashboard.
- Empate en el quinto lugar de la pregunta 1: el desempate por nombre de molécula hace que el
  resultado sea determinista, y el comentario de la consulta lo dice.
- Empate en el primer lugar de la pregunta 2: se muestran todos los empatados en lugar de elegir uno
  al azar.
- Una molécula con varias presentaciones (139 moléculas y 161 claves) mezcla envases de distinto
  tamaño en el precio por pieza. Es lo que pide el requisito y se documenta como limitación.
- Un grupo con `SUM(PIEZAS) = 0` no puede darse con los datos actuales (`PIEZAS > 0`), pero la
  división segura devuelve `NULL` en lugar de fallar.
- La vista existe pero las tablas están vacías: el chequeo de la vista cuadra (0 frente a 0), así
  que quien lo detecta es el chequeo de conteo (01). Las cifras cruzadas también cuadrarían sobre 0
  filas, por eso el objetivo de consultas se detiene antes de ejecutarlas si la vista no tiene filas
  y dice que hay que cargar los datos.
- Una columna de una tabla base cambia o desaparece: BigQuery guarda el esquema de las tablas al
  crear la vista y no lo actualiza solo, así que el esquema publicado de la vista queda desactualizado
  (las consultas siguen dando resultados correctos) hasta que se recrea. La verificación de metadatos
  lo informa y `make bq-vista` lo corrige.
- La pregunta 3 devuelve cientos de filas: el objetivo de consultas no puede truncarlas en silencio y
  tiene que decir cuántas filas hubo si no las imprime todas.
- La caché de resultados devuelve una consulta repetida sin costo: las cifras no cambian porque las
  tablas no cambiaron.
- Una referencia sin dataset o con ID de proyecto en la sección 3 o 4 haría que el `.sql` dependiera
  del proyecto: las pruebas locales lo impiden.

## Requirements *(mandatory)*

### Functional Requirements

**Vista (sección 3 de `sql/farma_analytics.sql`)**

- **FR-001**: La sección 3 MUST crear `farma_analytics.v_compras_farma_completa` con
  `CREATE OR REPLACE VIEW` como vista lógica, con descripción en español que declare su grano y que
  descarta las líneas huérfanas.
- **FR-002**: La vista MUST unir `COMPRAS` con `CLUE_CAT` por `CLUE` y con `CUADRO_BASICO` por
  `CLAVE` mediante `INNER JOIN ... ON`, con `COMPRAS` primero, alias `compras`, `clue_cat` y
  `cuadro_basico`, cada columna calificada con su alias, `AS` en todos los alias y una lista explícita
  de columnas sin `SELECT *`.
- **FR-003**: El grano de la vista MUST ser una fila por cada fila de `COMPRAS` con correspondencia en
  ambos catálogos. La definición MUST NOT tener agregaciones, `DISTINCT`, `ORDER BY`, `LIMIT`,
  filtros adicionales ni `ROUND`.
- **FR-004**: La vista MUST exponer todas las columnas de los requisitos con sus nombres en
  UPPER_SNAKE_CASE, las claves `CLUE` y `CLAVE` una sola vez (desde `COMPRAS`) y `FABRICANTE` dos
  veces con nombres distintos: `FABRICANTE_COMPRA` (de `COMPRAS`, fabricante del producto entregado)
  y `FABRICANTE_CATALOGO` (de `CUADRO_BASICO`, fabricante de referencia). Los nombres MUST ser únicos
  sin distinguir mayúsculas.
- **FR-005**: La vista MUST añadir tres derivaciones deterministas por fila, con alias explícito y
  descripción: `ANIO` (año de `FECHA`, entero), `MES` (primer día del mes de `FECHA`, fecha) y
  `ENTIDAD_ISO` (código ISO 3166-2 de la entidad, `MX-XXX`, para los 32 nombres oficiales). MUST NOT
  añadir precios por fila, cocientes, agregados ni transformaciones de limpieza (`TRIM`, `REGEXP`,
  `CAST` de tipos ya cargados).
- **FR-006**: La vista y cada una de sus columnas MUST tener descripción en español, fijada en la
  propia sentencia de la sección 3 para que sobreviva a cada `CREATE OR REPLACE`. Las descripciones
  de columna MUST ir en la lista de columnas de la vista (`view_column_name_list` con
  `OPTIONS(description = ...)`), con exactamente tantos nombres como columnas devuelve la consulta y
  en el mismo orden. El nombre de salida de cada elemento del `SELECT` MUST coincidir, en la misma
  posición, con el de la lista: las columnas que pasan sin cambio de nombre van sin alias (un alias
  igual al nombre de origen viola la regla AL09 de SQLFluff) y las que cambian de nombre o se
  calculan llevan alias con `AS`. MUST NOT usarse sentencias `ALTER VIEW ... ALTER COLUMN` para las
  descripciones. La desviación de la preferencia de la constitución por los alias del `SELECT` se
  justifica en el plan.
- **FR-007**: Las referencias de la vista MUST calificarse con `farma_analytics` y MUST NOT incluir el
  ID de proyecto. La vista MUST NOT llevar expiración.
- **FR-008**: Una prueba automatizada local (sin GCP) MUST comprobar FR-002 a FR-007 sobre el texto de
  la sección 3: tipo de join, orden de las tablas, alias, ausencia de `SELECT *`, agregaciones,
  `DISTINCT`, `ORDER BY` y `ROUND`, columnas esperadas en orden, nombres únicos, descripciones
  presentes y referencias sin proyecto.

**Consultas analíticas (sección 4)**

- **FR-009**: La sección 4 MUST contener las consultas que responden las tres preguntas de la Fase 2.
  Cada consulta MUST leer solo de `farma_analytics.v_compras_farma_completa` y MUST llevar un
  comentario breve en inglés con la pregunta de negocio que responde y la definición que usa.
- **FR-010**: Pregunta 1, las 5 moléculas con más `IMPORTE`: MUST agrupar por `MOLECULA`, ordenar por
  `SUM(IMPORTE)` de mayor a menor con desempate por `MOLECULA` ascendente y quedarse con 5 filas con
  `ORDER BY ... LIMIT`. MUST mostrar el importe total, las piezas totales y la participación en el
  importe total de la vista.
- **FR-011**: Pregunta 2, la institución y la entidad con mayor volumen de compra: la definición
  principal de volumen MUST ser `SUM(IMPORTE)` (monto comprado, la misma medida de la pregunta 1 y
  del gasto del dashboard) y la alternativa `SUM(PIEZAS)`. La consulta MUST mostrar el líder de cada
  medida en tres niveles: la combinación `INSTITUCION`-`ENTIDAD`, `INSTITUCION` sola y `ENTIDAD`
  sola, con su valor y su participación en el total. El líder por nivel y medida MUST obtenerse con
  una función de ventana y `QUALIFY`, con `RANK` para que un empate muestre a todos los empatados.
- **FR-012**: Pregunta 3, el precio promedio por pieza por molécula y fabricante: MUST calcularse
  como `SAFE_DIVIDE(SUM(IMPORTE), SUM(PIEZAS))` agrupando por `MOLECULA` y `FABRICANTE_COMPRA`
  (definición principal, porque es quien vendió a ese precio) y mostrar importe, piezas y precio.
  MUST existir también la interpretación con `FABRICANTE_CATALOGO`. MUST NOT promediar precios por
  fila ni usar `AVG` sobre un cociente.
- **FR-013**: Al menos una consulta SHOULD usar `AVG` para una media simple con significado de
  negocio (por ejemplo, el importe promedio por línea de compra), porque los requisitos piden
  agrupaciones con `SUM` y `AVG`, y nunca para promediar cocientes.
- **FR-014**: Estilo de la sección 4: `GROUP BY` MUST nombrar las columnas (sin ordinales ni
  `GROUP BY ALL`), `ROUND` MUST aplicarse solo en el `SELECT` final, `ORDER BY` MUST aparecer solo en
  la consulta más externa, cada CTE MUST tener una sola responsabilidad y un nombre descriptivo, solo
  funcionalidades GA de GoogleSQL, líneas de 100 caracteres o menos y SQLFluff sin violaciones. Una
  prueba automatizada local MUST comprobar que cada consulta lee solo de la vista, tiene comentario,
  usa división segura para el precio y no usa ordinales en `GROUP BY`.
- **FR-015**: Las cuatro ambigüedades (qué es volumen de compra, qué `FABRICANTE` se usa, si
  institución y entidad se evalúan juntas o por separado, y cómo se tratan los empates) MUST quedar
  definidas por escrito en español en la documentación para lectores y en inglés en los comentarios
  del `.sql`, con la razón de cada definición.

**Calidad (principio IV)**

- **FR-016**: MUST añadirse en `sql/checks/` un chequeo canónico de la vista, con el mismo contrato de
  salida que los seis existentes (0 filas si todo está bien; si falla, chequeo, objeto, detalle,
  esperado y obtenido), que compruebe:
  - filas de la vista = filas de `COMPRAS` − filas con al menos una clave huérfana;
  - `SUM(IMPORTE)` y `SUM(PIEZAS)` de la vista = las del `INNER JOIN` sobre las tablas base;
  - `ENTIDAD_ISO`, `ANIO` y `MES` sin nulos en ninguna fila.
- **FR-017**: El chequeo de la vista MUST tener un caso negativo versionado en
  `sql/checks/negativos/`, ejecutado por el objetivo de casos negativos con el mismo archivo de
  `sql/checks/`, sin leer tablas ni vistas reales, sin crear objetos y sin facturar bytes.
- **FR-018**: La verificación de metadatos MUST extenderse a la vista: que exista, que sea una vista,
  su descripción, los nombres y el orden de sus columnas, sus tipos frente al modelo de datos y la
  descripción de cada columna frente a la sección 3, con la misma comparación sin costo de
  `bq show` que ya usan las tablas.
- **FR-019**: Los chequeos MUST ejecutarse después de cada carga y de cada cambio en la vista, con
  la carga y la vista desacopladas. El recorrido desde un clon limpio es esquema, carga y vista:
  - el objetivo de esquema MUST seguir ejecutando solo las secciones 1 y 2;
  - el objetivo de carga MUST NOT crear, reemplazar ni modificar la vista. Al terminar MUST ejecutar
    los seis chequeos de tablas y la verificación de metadatos de las tablas y, si la vista ya
    existe, también el chequeo de la vista y sus metadatos. Si la vista no existe, MUST informarlo
    con un mensaje que indica desplegarla y MUST NOT fallar por ese motivo;
  - el objetivo de la vista MUST ejecutar solo la sección 3 y después los siete chequeos y la
    verificación de metadatos completa. Cambiar la vista MUST NOT requerir una carga;
  - el objetivo de chequeos MUST ejecutar los siete chequeos y MUST fallar si la vista no existe.
- **FR-020**: Un chequeo fallido MUST hacer fallar el objetivo y MUST NOT ocultarse con `DISTINCT`,
  filtros ad hoc ni umbrales cambiados sin justificación.

**Operación, estilo y documentación**

- **FR-021**: MUST existir un objetivo de `make` para desplegar la vista (`bq-vista`) y otro para
  ejecutar las consultas (`bq-consultas`), construidos sobre el programa `warehouse`, que lee las sentencias de
  `sql/farma_analytics.sql` (sin copias del SQL). Los ejecuta el dueño, requieren el proyecto
  configurado y fallan con un mensaje claro si falta.
- **FR-022**: Cada job de consulta (la vista, las consultas, el chequeo y la verificación de cifras)
  MUST pasar por un dry run antes de ejecutarse y no ejecutarse si falla, MUST llevar las labels
  estáticas de los jobs (`project`, `env`) y MUST respetar el `maximum_bytes_billed` de
  `.bigqueryrc` sin repetir los flags que ese archivo ya fija.
- **FR-023**: El objetivo de consultas MUST imprimir las respuestas en un formato legible, decir
  cuántas filas devolvió cada consulta y los bytes estimados, y verificar de forma automática las
  cifras cruzadas de la historia 2 (escenario 4). Si alguna no cuadra, MUST terminar con error e
  informar la diferencia. Si la vista no tiene filas, MUST detenerse antes de ejecutar las consultas
  con un mensaje que indica cargar los datos.
- **FR-024**: `sql/farma_analytics.sql` MUST ejecutarse de principio a fin en la consola de BigQuery
  sin otras herramientas, y re-ejecutarlo MUST NOT cambiar el contenido de las tablas.
- **FR-025**: Todo `.sql` nuevo o modificado MUST pasar SQLFluff con la configuración del repositorio,
  y el repositorio MUST seguir pasando `make lint`, `make test` y `make lint-prosa`.
- **FR-026**: El README MUST explicar el recorrido de la Fase 2 (desplegar la vista, ejecutar los
  chequeos y las consultas, qué ejecuta solo el dueño y qué salida esperar) y las definiciones de las
  ambigüedades. La matriz de trazabilidad MUST añadir las filas de la Fase 2. Ambos en español y
  cumpliendo el principio IX.
- **FR-027**: Los archivos versionados MUST NOT contener el ID del proyecto, credenciales ni
  referencias al documento de requisitos.

### Key Entities *(include if feature involves data)*

- **Vista `v_compras_farma_completa`**: capa semántica única para el SQL y el dashboard. Grano: una
  línea de compra con correspondencia en ambos catálogos. Columnas, en este orden:
  - de `COMPRAS`: `CLUE`, `CLAVE`, `COD_PROVEEDOR`, `MARCA`, `FABRICANTE_COMPRA`, `PIEZAS`,
    `IMPORTE`, `FECHA`;
  - de `CLUE_CAT`: `ENTIDAD`, `INSTITUCION`, `DELEGACION`, `GRUPO_INSTITUCIONAL`, `NIVEL_ATENCION`,
    `MUNICIPIO`;
  - de `CUADRO_BASICO`: `DESCRIPCION`, `MOLECULA`, `GRUPO_TERAPEUTICO`, `PRESENTACION`,
    `FABRICANTE_CATALOGO`;
  - derivadas: `ANIO`, `MES`, `ENTIDAD_ISO`.
- **Pregunta comercial**: una de las tres preguntas de la Fase 2, con su consulta, su definición de
  las ambigüedades y su resultado.
- **Glosario de métricas** (principio VII): Monto Total = `SUM(IMPORTE)`, Piezas = `SUM(PIEZAS)`,
  Precio Promedio = `SUM(IMPORTE) / SUM(PIEZAS)`.
- **Chequeo de la vista**: séptima regla de `sql/checks/`, con su caso negativo.
- **Cifras cruzadas**: igualdades entre las respuestas de las tres consultas y el total de la vista
  que prueban que todas usan la misma capa semántica.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La vista existe con exactamente 298 500 filas (300 000 líneas de compra menos 750
  huérfanas de `CLUE` y 750 de `CLAVE`) y su `IMPORTE` total es idéntico, sin redondeo, al del
  `INNER JOIN` sobre las tablas base.
- **SC-002**: Las tres preguntas tienen respuesta y la verificación de cifras cruzadas encuentra 0
  diferencias entre ellas y con el total de la vista.
- **SC-003**: Los siete chequeos SQL devuelven 0 filas y la verificación de metadatos no informa
  diferencias en el dataset, las tres tablas, la vista y las 22 descripciones de columna de la vista.
- **SC-004**: El objetivo de casos negativos detecta 7 de 7 casos sin facturar bytes.
- **SC-005**: El `.sql` completo se ejecuta sin errores en la consola de BigQuery, sus respuestas
  coinciden con las del objetivo de consultas y, después de dos ejecuciones, las tablas conservan
  300 000, 2 000 y 161 filas.
- **SC-006**: Ninguna consulta, chequeo ni despliegue supera el límite de bytes de `.bigqueryrc`, y el
  despliegue de la vista más los chequeos y las consultas terminan en menos de 5 minutos.
- **SC-007**: `make lint`, `make test` y `make lint-prosa` terminan sin errores y SQLFluff no informa
  violaciones.
- **SC-008**: La matriz de trazabilidad cubre el 100 % de los requisitos de la Fase 2 y una persona
  llega a SC-001, SC-002 y SC-003 siguiendo el README sin pasos que no estén escritos.

## Assumptions

- Las tablas están cargadas y verificadas por la feature 003 (300 000, 2 000 y 161 filas, seis
  chequeos en 0 filas). Los huérfanos de `CLUE` y de `CLAVE` son filas distintas, porque el generador
  deja cada línea huérfana sin una sola de sus claves.
- El dry run, las labels y el límite de bytes aplican a los jobs que lanza `make`. En la consola, el
  validador de consultas estima los bytes y el límite lo pone la cuota diaria del proyecto.
- `MES` como fecha del primer día del mes sirve para series mensuales sin mezclar años, y `ANIO`
  como entero sirve para comparar año contra año. Los nombres evitan la `Ñ` para no depender de los
  nombres de columna flexibles.
- Los códigos ISO 3166-2 salen de la lista oficial de las 32 entidades (`MX-AGU` a `MX-ZAC`, con
  `MX-CMX` para Ciudad de México) y se resuelven con una expresión por fila en la vista, sin una
  tabla auxiliar, porque los requisitos no la piden y la constitución permite esta derivación.
- El precio promedio por molécula mezcla presentaciones de distinto tamaño de envase. El desglose
  por `CLAVE` o `PRESENTACION` no lo piden los requisitos y queda para el dashboard o los hallazgos.
- Quedan fuera de alcance: el dashboard, el documento de hallazgos, las claves primarias, las vistas
  materializadas y Dataform. `@dataform/cli` sigue sin cambios, con el riesgo R18 ya aceptado.
- El dueño ejecuta todos los comandos que tocan GCP. Las pruebas y el lint locales no necesitan
  credenciales.
