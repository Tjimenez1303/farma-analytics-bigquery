# Feature Specification: Carga de datos en BigQuery (esquema, carga idempotente y chequeos de calidad)

**Feature Branch**: `003-bigquery-data-load`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Carga de datos en BigQuery: crear el dataset farma_analytics en la location de .bigqueryrc, con descripción y labels, y las tablas COMPRAS, CLUE_CAT y CUADRO_BASICO con exactamente los campos de los requisitos y tipos estrictos (FECHA DATE, PIEZAS INT64, IMPORTE NUMERIC, claves y atributos STRING), NOT NULL en claves, FECHA, PIEZAS e IMPORTE, y descripción en cada tabla y columna. La DDL vive en las secciones 1 y 2 de sql/farma_analytics.sql (CREATE SCHEMA IF NOT EXISTS y CREATE TABLE IF NOT EXISTS), que es la única definición canónica del esquema; si bq load necesita un esquema JSON, se deriva de la DDL o se comprueba contra ella. La carga usa bq load desde los CSV locales generados con make data, con esquema explícito, sin autodetección y con --skip_leading_rows=1; debe ser idempotente y no puede usar CREATE OR REPLACE TABLE sobre tablas cargadas. Cada sentencia se valida con un dry run antes de ejecutarse, los jobs llevan labels y respetan el maximum_bytes_billed de .bigqueryrc sin repetir flags. Incluye los chequeos de calidad del principio IV, que se ejecutan después de cada carga y devuelven 0 filas cuando todo está bien: conteo de filas por tabla frente al manifiesto del generador, unicidad de CLUE y CLAVE, ausencia de nulos, dominios (PIEZAS > 0, IMPORTE >= 0, FECHA dentro del rango), reconciliación del INNER JOIN con los huérfanos cuantificados y precio unitario implícito plausible por clave. Las claves foráneas no se declaran porque hay huérfanos deliberados. Hay objetivos de make para crear el esquema, cargar y ejecutar los chequeos, todo SQLFluff limpio, y el README explica el recorrido. Yo ejecuto todo lo que toca GCP. El éxito se mide con las tres tablas cargadas con los conteos del manifiesto, todos los chequeos en 0 filas, make doctor con B03 en OK y una segunda carga que deja las tablas iguales."

## Clarifications

### Session 2026-10-08

- Q: Los jobs de carga de `bq load` no admiten dry run ni labels. ¿Cómo se cumple la regla de dry
  run y labels en cada job? → A: El dry run y las labels se aplican a todos los jobs de consulta
  (DDL, vaciados si los hay y chequeos). La carga se valida antes en local (verificación contra el
  manifiesto y prueba del esquema contra la DDL) y va sin labels. La excepción se documenta y la
  constitución se aclara para hablar de "jobs de consulta".
- Q: ¿En qué idioma van los comentarios del `.sql` entregable? → A: En inglés, como el resto del
  código. Se enmienda la constitución para sacar los comentarios de los `.sql` del alcance del
  principio IX, y `scripts/lint_prosa.sh` deja de revisar los `.sql`. Las descripciones del dataset,
  las tablas y las columnas siguen en español.
- Q: ¿Los chequeos se implementan como consultas en `sql/checks/` o como assertions de Dataform? →
  A: Consultas en `sql/checks/`, una por regla, ejecutadas con `bq query` (dry run, labels,
  `maximum_bytes_billed` y parámetros leídos del manifiesto). Dataform no se usa en esta feature. El
  plan justifica que se aparta del SHOULD de la tabla de stack.
- Q: Si una recarga falla a mitad de camino, ¿la tabla conserva los datos anteriores o puede quedar
  vacía hasta repetir la carga? → A: Conserva los datos anteriores. Cada tabla se reemplaza en un
  solo job de carga atómico con el esquema derivado de la DDL (descripciones y modos incluidos), sin
  vaciarla antes.
- Q: ¿Qué cuenta como precio por pieza plausible en el chequeo de `IMPORTE / PIEZAS` por clave? →
  A: Dos reglas calculadas con los parámetros de precio del generador: cada precio dentro del mínimo
  y el máximo posibles (hoy de 6.75 a 17 820 pesos) y, dentro de cada clave del catálogo, el precio
  máximo no supera 4.4 veces el mínimo, con un centavo de margen por redondeo.

## User Scenarios & Testing *(mandatory)*

> Nota de alcance: los "usuarios" de esta feature son quienes trabajan con el repositorio (el
> dueño, que ejecuta todo lo que toca GCP, y cualquier persona que quiera reproducir la solución
> desde un clon limpio) y, de forma indirecta, el equipo comercial que consumirá la vista y el
> dashboard de las features siguientes. BigQuery, `bq`, el `.bigqueryrc` versionado, el `Makefile`,
> SQLFluff, el dry run, `maximum_bytes_billed` y el archivo `sql/farma_analytics.sql` no son
> decisiones de diseño de esta spec: los imponen el documento de requisitos y la constitución
> (principios I, II, IV y VIII, tabla de stack y sección "Entregable SQL"), así que forman parte del
> QUÉ.

### User Story 1 - Crear el dataset y las tablas desde la DDL canónica (Priority: P1)

El dueño del proyecto ejecuta un objetivo de `make` que crea el dataset `farma_analytics` y las
tablas `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` a partir de las secciones 1 y 2 de
`sql/farma_analytics.sql`. Cada sentencia pasa primero por un dry run y solo se ejecuta si el dry
run no da error. El dataset queda en la location que fija `.bigqueryrc`, con descripción y labels,
y cada tabla y cada columna tienen descripción, el tipo exigido y el modo `REQUIRED` en las
columnas obligatorias. Si repite el objetivo, no cambia nada ni se pierde ningún dato.

**Why this priority**: sin el esquema no hay dónde cargar, y el esquema es la parte del entregable
`.sql` que más pesa en los criterios de aceptación (tipos de datos).

**Independent Test**: en un proyecto sin el dataset, ejecutar el objetivo de esquema y comprobar
en `INFORMATION_SCHEMA` (o con `bq show`) la location, las labels, las descripciones, los tipos y
los modos. Ejecutarlo una segunda vez y comprobar que termina sin error y sin cambios.

**Acceptance Scenarios**:

1. **Given** un proyecto sin `farma_analytics`, **When** el dueño ejecuta el objetivo de esquema,
   **Then** existe `farma_analytics` en la location de `.bigqueryrc`, con descripción y labels, y
   existen las tres tablas vacías con exactamente los campos de los requisitos, en su orden.
2. **Given** las tablas creadas, **When** se consulta su esquema, **Then** `FECHA` es `DATE`,
   `PIEZAS` es `INT64`, `IMPORTE` es `NUMERIC` sin parámetros, el resto es `STRING`, las claves,
   `FECHA`, `PIEZAS` e `IMPORTE` son `REQUIRED` y cada tabla y columna tiene descripción.
3. **Given** las tablas ya cargadas con datos, **When** el dueño vuelve a ejecutar el objetivo de
   esquema (o el `.sql` completo en la consola), **Then** el número de filas no cambia y ninguna
   tabla se reemplaza.
4. **Given** una sentencia con un error, **When** se ejecuta el objetivo, **Then** el dry run falla,
   la sentencia no se ejecuta y el mensaje indica cuál falló.
5. **Given** `make doctor` antes de crear el dataset (B03 omitido), **When** se crea el dataset y se
   repite `make doctor`, **Then** B03 sale en OK con la location esperada.

---

### User Story 2 - Cargar los CSV de forma idempotente (Priority: P1)

Con los datos generados por `make data` y el esquema creado, el dueño ejecuta un objetivo de
`make` que carga los tres CSV locales en sus tablas con el esquema explícito que sale de la DDL,
sin autodetección y saltando la fila de encabezado. Antes de cargar se comprueba que los archivos
coinciden con el manifiesto del generador. Al terminar, cada tabla tiene exactamente las filas del
manifiesto y conserva tipos, modos y descripciones. Si repite la carga, las tablas quedan iguales:
mismas filas, mismo contenido y mismo esquema, sin duplicados.

**Why this priority**: es la Fase 1 de los requisitos y la base de la vista, las consultas y el
dashboard.

**Independent Test**: cargar dos veces seguidas y comparar después de cada carga el conteo de filas,
una huella del contenido de cada tabla y su esquema.

**Acceptance Scenarios**:

1. **Given** el esquema creado y `data/` verificado contra el manifiesto, **When** el dueño ejecuta
   el objetivo de carga, **Then** `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` tienen 300 000, 2 000 y
   161 filas, y los chequeos de calidad se ejecutan a continuación.
2. **Given** las tablas ya cargadas, **When** se repite la carga, **Then** el conteo, la huella del
   contenido y el esquema (tipos, modos y descripciones) de cada tabla son idénticos a los de la
   primera carga.
3. **Given** que falta `data/` o un archivo no coincide con el manifiesto, **When** se ejecuta la
   carga, **Then** se detiene antes de tocar BigQuery y dice que hay que ejecutar `make data`.
4. **Given** una fila que no se puede convertir al tipo de su columna, **When** se carga, **Then** la
   carga de esa tabla falla sin aceptar filas malas y la tabla conserva el contenido que tenía.
5. **Given** que el dataset no existe, **When** se ejecuta la carga, **Then** se detiene con un
   mensaje que indica crear antes el esquema.

---

### User Story 3 - Verificar la calidad después de cada carga (Priority: P2)

Después de cada carga, y también cuando el dueño lo pide con su propio objetivo de `make`, se
ejecutan los chequeos de calidad del principio IV. Cada chequeo devuelve 0 filas si todo está bien
y, si algo falla, devuelve filas que dicen qué falló y con qué valores. El objetivo termina con
error si algún chequeo devuelve filas.

**Why this priority**: sin estos chequeos, las cifras de la vista y del dashboard no se pueden
defender (un `INNER JOIN` descarta huérfanos sin avisar y una clave duplicada infla
`SUM(IMPORTE)`). Depende de que haya datos cargados.

**Independent Test**: con las tablas cargadas, ejecutar el objetivo de chequeos y ver los seis
chequeos SQL en 0 filas y la verificación de metadatos sin diferencias. Con las tablas vacías, ver
fallar el conteo y la reconciliación. Con los casos negativos, ver que cada uno de los seis chequeos
detecta su error preparado a propósito.

**Acceptance Scenarios**:

1. **Given** las tablas cargadas con los datos del manifiesto, **When** se ejecutan los chequeos,
   **Then** todos devuelven 0 filas y el objetivo termina con éxito.
2. **Given** que el número de filas de una tabla no coincide con el manifiesto, **When** se ejecutan
   los chequeos, **Then** el chequeo de conteo devuelve una fila con la tabla, el valor esperado y
   el obtenido, y el objetivo falla.
3. **Given** las tablas cargadas, **When** se ejecuta la reconciliación del `INNER JOIN`, **Then** las
   filas y el `IMPORTE` de `COMPRAS` cuadran con los del `INNER JOIN` más los de las filas huérfanas,
   y los huérfanos por `CLUE` y por `CLAVE` coinciden con el manifiesto (750 y 750).
4. **Given** cualquier chequeo, **When** se ejecuta, **Then** antes pasa por un dry run y queda bajo
   el `maximum_bytes_billed` de `.bigqueryrc`.
5. **Given** un caso negativo por chequeo (por ejemplo, una `CLUE` repetida en `CLUE_CAT` para el
   chequeo de unicidad), **When** el dueño ejecuta el objetivo de casos negativos, **Then** cada
   chequeo devuelve al menos una fila con su nombre y el objeto esperado, sin leer las tablas reales
   ni facturar bytes, y el objetivo termina con éxito; si algún chequeo devuelve 0 filas con su caso,
   el objetivo falla y dice cuál.

---

### User Story 4 - Seguir el recorrido documentado (Priority: P3)

Una persona que llega al repositorio lee en el README el recorrido de esta fase (generar los datos,
crear el esquema, cargar y verificar) con un comando por etapa, qué hace cada uno, qué ejecuta solo
el dueño porque toca GCP y qué salida esperar. La matriz de trazabilidad relaciona los requisitos de
la Fase 1 con sus artefactos y verificaciones.

**Why this priority**: lo exige la reproducibilidad del principio VIII y el video sigue este mismo
recorrido, pero no bloquea la carga.

**Independent Test**: seguir el README desde un clon limpio con un proyecto configurado y llegar a
las tablas cargadas y los chequeos en 0 filas sin pasos no escritos.

**Acceptance Scenarios**:

1. **Given** un clon limpio con el entorno de la feature 001, **When** se siguen los pasos del README,
   **Then** se llega a las tres tablas cargadas, a los chequeos en 0 filas y a `make doctor` con B03
   en OK.
2. **Given** la matriz de trazabilidad, **When** se revisan las filas de la Fase 1, **Then** cada
   requisito de la fase apunta a su artefacto y a su verificación.

---

### Edge Cases

- El dataset ya existe en otra location: la location de un dataset no se puede cambiar. `make
  doctor` marca B03 como FALLO y el objetivo de esquema no debe ocultar el problema.
- Una tabla ya existe con un esquema distinto del de la DDL (por ejemplo, creada a mano o con una
  descripción antigua): `CREATE TABLE IF NOT EXISTS` no la modifica, así que la diferencia tiene que
  detectarse y no pasar en silencio.
- La carga reemplaza la tabla: el reemplazo no puede perder las descripciones ni el modo `REQUIRED`
  de las columnas.
- Se regeneran los datos con otra configuración: los chequeos comparan contra el manifiesto vigente
  y el rango de fechas configurado, no contra cifras fijas en el SQL.
- Valores con comas y comillas dentro del campo (por ejemplo, `FABRICANTE` "Genéricos Guevara, S.A.
  de C.V.") y acentos en UTF-8: se cargan sin partir columnas ni cambiar caracteres.
- Huérfanos de `CLAVE`: casi cada uno tiene una clave distinta que no está en el catálogo, así que el
  precio unitario por clave solo se evalúa en las claves del catálogo.
- Una consulta de chequeo superaría el límite de bytes: falla sin cobrarse y el objetivo informa el
  error.
- El dueño no tiene permisos suficientes en BigQuery: el dry run o el job fallan con el mensaje de
  permisos y no se ejecuta nada más.
- Se ejecutan los chequeos con las tablas vacías: fallan el conteo de filas y la reconciliación
  (los huérfanos medidos son 0 frente a los del manifiesto), que es el comportamiento esperado.
- Una carga a medias por un corte de red: la tabla conserva el contenido anterior y, al repetir la
  carga, el resultado es el mismo que el de una carga completa.

## Requirements *(mandatory)*

### Functional Requirements

**Esquema (secciones 1 y 2 de `sql/farma_analytics.sql`)**

- **FR-001**: La sección 1 MUST crear el dataset `farma_analytics` con `CREATE SCHEMA IF NOT EXISTS`,
  en la misma location que fija `.bigqueryrc`, con descripción y con las labels `project`, `env` y
  `owner` (minúsculas, sin valores volátiles ni datos personales) y sin expiración por defecto.
- **FR-002**: Una prueba automatizada local MUST fallar si la location escrita en la DDL difiere de la
  de `.bigqueryrc`, porque el `.sql` debe poder ejecutarse en la consola sin otras herramientas.
- **FR-003**: La sección 2 MUST crear `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` con
  `CREATE TABLE IF NOT EXISTS`, con exactamente los campos de los requisitos, con sus nombres y en el
  mismo orden que los CSV.
- **FR-004**: Los tipos MUST ser `FECHA DATE`, `PIEZAS INT64`, `IMPORTE NUMERIC` (sin parámetros) y
  `STRING` para las claves (`CLUE`, `CLAVE`, `COD_PROVEEDOR`) y los atributos descriptivos.
- **FR-005**: `CLUE`, `CLAVE` y `COD_PROVEEDOR` (en cada tabla donde aparecen), `FECHA`, `PIEZAS` e
  `IMPORTE` MUST declararse `NOT NULL`. El resto de columnas queda `NULLABLE`.
- **FR-006**: El dataset, cada tabla y cada columna MUST tener descripción. Cada tabla declara en su
  descripción su grano y su llave.
- **FR-007**: La DDL MUST NOT usar `CREATE OR REPLACE TABLE`, `CREATE TABLE ... AS SELECT`,
  particionado, clustering, expiración ni ID de proyecto. La decisión de no particionar ni
  clusterizar MUST quedar documentada.
- **FR-008**: MUST NOT declararse claves foráneas, porque hay huérfanos deliberados. Las claves
  primarias quedan fuera de esta feature.
- **FR-009**: El esquema de cada tabla MUST tener una sola definición canónica, la DDL. Si la carga
  necesita un esquema en otro formato, MUST derivarse de la DDL o una prueba automatizada MUST fallar
  cuando difieran en nombres, orden, tipos, modos o descripciones.
- **FR-010**: Re-ejecutar las secciones 1 y 2 (con `make` o en la consola) MUST NOT borrar ni
  reemplazar datos.

**Carga**

- **FR-011**: La carga MUST leer los CSV locales que produce `make data`, después de verificarlos
  contra `generator/manifest.json`. Si la verificación falla, MUST detenerse antes de llamar a
  BigQuery.
- **FR-012**: La carga MUST usar un esquema explícito, MUST NOT usar autodetección, MUST saltar una
  fila de encabezado y MUST NOT tolerar filas malas.
- **FR-013**: La carga MUST ser idempotente: repetirla deja cada tabla con el mismo número de filas,
  el mismo contenido y el mismo esquema (tipos, modos y descripciones), sin duplicados.
- **FR-014**: Si la carga de una tabla falla, esa tabla MUST conservar intacto el contenido que tenía
  antes (la recarga reemplaza la tabla en un solo paso atómico y no la vacía antes), y el objetivo
  MUST terminar con error indicando la tabla. El esquema que usa ese reemplazo MUST derivarse de la
  DDL, con descripciones y modos, para que la tabla no pierda ninguno (FR-009).
- **FR-015**: Cada carga MUST terminar ejecutando los chequeos de calidad. La carga solo se da por
  buena si todos devuelven 0 filas.
- **FR-016**: Cada job de consulta (DDL, chequeos y huella de contenido) MUST validarse con un dry
  run antes de ejecutarse, y no ejecutarse si el dry run falla. Los jobs de carga quedan exentos
  porque `bq load` no tiene dry run y la API no define su comportamiento en jobs que no son
  consultas. En su lugar, antes de cargar MUST pasar la verificación de los CSV contra el manifiesto
  (FR-011) y la verificación de metadatos de la tabla destino (FR-026), y el esquema de la carga se
  deriva de la DDL en el momento (FR-009). La excepción MUST quedar documentada.
- **FR-017**: Los jobs de consulta MUST llevar labels estáticas (`project`, `env`) y MUST respetar el
  `maximum_bytes_billed` de `.bigqueryrc`. Los jobs de carga van sin labels porque `bq` solo admite
  labels en jobs de consulta. Los comandos MUST NOT repetir los flags que ya fija `.bigqueryrc`
  (`--location`, `--use_legacy_sql`, `--maximum_bytes_billed`).

**Chequeos de calidad (principio IV)**

- **FR-018**: Cada chequeo del principio IV (FR-019 a FR-024) MUST tener una única implementación
  canónica, devolver 0 filas cuando todo está bien y, cuando falla, filas que identifican el
  chequeo, el objeto y los valores esperado y obtenido. La implementación canónica es una consulta
  por regla en `sql/checks/`, ejecutada con `bq query`.
- **FR-019**: Conteo: el número de filas de cada tabla MUST coincidir con `rows` del manifiesto
  vigente. Los valores esperados se leen del manifiesto al ejecutar, no se escriben fijos en el SQL.
- **FR-020**: Unicidad: `CLUE` MUST ser única en `CLUE_CAT` y `CLAVE` MUST ser única en
  `CUADRO_BASICO`.
- **FR-021**: Nulos: las claves, `FECHA`, `PIEZAS` e `IMPORTE` MUST NOT tener nulos (el chequeo se
  mantiene aunque el modo `REQUIRED` ya lo impida, para detectar un cambio de esquema).
- **FR-022**: Dominios: `PIEZAS > 0`, `IMPORTE >= 0` y `FECHA` dentro del rango del periodo de la
  configuración del generador (hoy del 2024-01-01 al 2025-12-31).
- **FR-023**: Reconciliación del `INNER JOIN` de `COMPRAS` con `CLUE_CAT` (vía `CLUE`) y con
  `CUADRO_BASICO` (vía `CLAVE`): las filas y el `IMPORTE` de `COMPRAS` MUST ser iguales a los del
  `INNER JOIN` más los de las filas huérfanas, y los huérfanos de `CLUE` y de `CLAVE` MUST coincidir
  con `orphans` del manifiesto.
- **FR-024**: Precio unitario implícito: para cada `CLAVE` del catálogo, `IMPORTE / PIEZAS` MUST
  cumplir dos reglas, con un centavo de margen por redondeo en cada precio:
  - cota absoluta: cada precio queda entre el mínimo posible (menor precio base de los niveles ×
    menor factor genérico × (1 − ruido máximo)) y el máximo posible (mayor precio base × mayor factor
    de referencia × (1 + ruido máximo)); con la configuración actual, de 6.75 a 17 820 pesos;
  - dispersión: el precio máximo de la clave no supera su precio mínimo multiplicado por (mayor
    factor de referencia × (1 + ruido máximo)) / (menor factor genérico × (1 − ruido máximo)); hoy,
    4.4 veces.
  Los umbrales MUST calcularse a partir de `generator/config.toml` al ejecutar (no fijos en el SQL)
  y su cálculo MUST quedar documentado. Las claves huérfanas quedan fuera porque no están en el
  catálogo.
- **FR-025**: Un chequeo fallido MUST hacer fallar el objetivo de `make` y MUST NOT ocultarse con
  `DISTINCT`, filtros ad hoc ni umbrales cambiados sin justificación.
- **FR-026**: Un chequeo adicional MUST comprobar que el esquema publicado de cada tabla (nombres,
  orden, tipos, modos y descripciones) coincide con la DDL, para detectar tablas que
  `CREATE TABLE IF NOT EXISTS` no corrigió o que una carga alteró. Como no es una regla del
  principio IV, se implementa como comparación de metadatos (`bq show`, sin job ni costo) con el
  mismo contrato de salida que los chequeos SQL.
- **FR-033**: Cada uno de los seis chequeos SQL MUST tener un caso negativo versionado: unas pocas
  filas con un error preparado a propósito que ese chequeo tiene que detectar. Un objetivo de `make`
  MUST ejecutar cada chequeo con sus filas en lugar de las tablas reales (sin leer tablas, sin crear
  objetos y sin facturar bytes) y fallar si alguno devuelve 0 filas o no informa el objeto esperado.
  El SQL que se ejecuta es el mismo archivo de `sql/checks/`, sin copias.

**Operación, estilo y documentación**

- **FR-027**: MUST existir objetivos de `make` para crear el esquema, cargar y ejecutar los chequeos,
  con un comando por etapa. Los que tocan GCP los ejecuta el dueño. Requieren el proyecto
  configurado y fallan con un mensaje claro si falta.
- **FR-028**: Todo `.sql` nuevo MUST pasar SQLFluff con la configuración del repositorio, y el
  repositorio MUST seguir pasando `make lint`, `make test` y `make lint-prosa`.
- **FR-029**: El README MUST explicar el recorrido de esta fase y la matriz de trazabilidad MUST
  cubrir los requisitos de la Fase 1, ambos en español y cumpliendo el principio IX.
- **FR-030**: Los comentarios de todos los `.sql` (el entregable y los chequeos) MUST ir en inglés,
  breves. Las descripciones del dataset, las tablas y las columnas van en español, porque las verán
  los lectores en BigQuery y en Data Studio.
- **FR-031**: Los archivos versionados MUST NOT contener el ID del proyecto, credenciales ni
  referencias al documento de requisitos.
- **FR-032**: `scripts/lint_prosa.sh` MUST dejar de revisar los `.sql`, y sus pruebas y la línea del
  README que describe su alcance MUST actualizarse en consecuencia.

### Key Entities *(include if feature involves data)*

- **Dataset `farma_analytics`**: contenedor de las tablas en una location fija (`US`), con
  descripción y labels de atribución de costos.
- **`COMPRAS`**: tabla de hechos. Grano: una línea de compra. Sin llave única. Columnas `CLUE`,
  `CLAVE`, `COD_PROVEEDOR`, `MARCA`, `FABRICANTE`, `PIEZAS`, `IMPORTE`, `FECHA`.
- **`CLUE_CAT`**: dimensión de unidades médicas. Grano: una unidad médica. Llave `CLUE`. Columnas
  `CLUE`, `ENTIDAD`, `INSTITUCION`, `DELEGACION`, `GRUPO_INSTITUCIONAL`, `NIVEL_ATENCION`,
  `MUNICIPIO`.
- **`CUADRO_BASICO`**: dimensión de insumos. Grano: una presentación de una molécula. Llave `CLAVE`.
  Columnas `CLAVE`, `DESCRIPCION`, `MOLECULA`, `GRUPO_TERAPEUTICO`, `PRESENTACION`, `FABRICANTE`.
- **Manifiesto del generador**: fuente de las cifras esperadas (filas por archivo y huérfanos por
  tipo) contra las que se comparan la carga y los chequeos.
- **Chequeo de calidad**: regla con nombre, una implementación canónica y un resultado de 0 filas
  cuando se cumple.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Después de la carga, `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` tienen exactamente las
  filas del manifiesto (300 000, 2 000 y 161).
- **SC-002**: Los seis chequeos SQL (conteo, unicidad, nulos, dominios, reconciliación y precio
  unitario) devuelven 0 filas y la verificación de metadatos contra la DDL no informa diferencias
  después de cada carga, y los seis detectan su caso negativo (6 de 6) sin facturar bytes.
- **SC-003**: `make doctor` pasa de 23 OK con B03 omitido a 24 OK, con B03 en OK y la location
  esperada.
- **SC-004**: Una segunda carga deja las tres tablas con el mismo conteo, la misma huella de
  contenido y el mismo esquema que la primera, y los chequeos siguen en 0 filas.
- **SC-005**: Ejecutar otra vez la creación del esquema sobre tablas cargadas deja el conteo de filas
  igual en las tres tablas.
- **SC-006**: El recorrido completo (esquema, carga y chequeos) termina en menos de 10 minutos con una
  conexión doméstica, y ninguna consulta de chequeo supera el límite de bytes de `.bigqueryrc`.
- **SC-007**: `make lint`, `make test` y `make lint-prosa` terminan sin errores, y SQLFluff no
  informa violaciones en los `.sql`.
- **SC-008**: Una persona que sigue el README desde un clon limpio llega a SC-001, SC-002 y SC-003 sin
  pasos que no estén escritos.

## Assumptions

- El entorno de la feature 001 ya está listo: proyecto de GCP con facturación,
  `only_google_sql` en `region-us`, cuota diaria y alerta de presupuesto. La location es `US`.
- Los CSV vienen de `make data` (feature 002): UTF-8 sin BOM, con encabezado, fechas `YYYY-MM-DD`,
  punto decimal y campos entre comillas cuando contienen comas. Pesan unos 32 MB en total, de modo
  que se cargan desde la máquina local sin pasar por Cloud Storage.
- `rows` del manifiesto excluye la fila de encabezado.
- Las labels del dataset usan valores estáticos: `project` y `env` iguales a las labels de jobs del
  `Makefile` (`farma-analytics` y `dev`) y `owner` con un identificador de equipo, nunca el nombre de
  una persona.
- Los jobs de carga por lotes no procesan bytes de consulta, así que `maximum_bytes_billed` solo
  aplica a los jobs de consulta (DDL, chequeos, casos negativos y huella).
- La reconciliación de esta feature se hace con el `INNER JOIN` sobre las tablas base. Cuando exista
  `v_compras_farma_completa`, la feature de la vista añade su propia reconciliación.
- El rango de fechas válido es el periodo de `generator/config.toml`.
- Quedan fuera de alcance: la vista, las consultas analíticas, el dashboard, las claves primarias,
  la carga desde Cloud Storage y Dataform. `@dataform/cli` sigue sin cambios en `package.json`, con
  el riesgo R18 ya aceptado (research R13).
- El dueño ejecuta todos los comandos que tocan GCP. Las pruebas y el lint locales no necesitan
  credenciales.
