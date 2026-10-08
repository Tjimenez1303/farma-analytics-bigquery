# Feature Specification: Generador de datos sintéticos (COMPRAS, CLUE_CAT y CUADRO_BASICO)

**Feature Branch**: `002-synthetic-data-generator`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Generador de datos sintéticos: un generador en Python, gestionado con uv y con versiones exactas de NumPy y Faker (es_MX), que produce las tres fuentes COMPRAS, CLUE_CAT y CUADRO_BASICO con exactamente los campos que piden los requisitos, en CSV UTF-8 sin BOM (o Parquet con esquema explícito). Debe ser determinista: la semilla y todos los parámetros viven en un archivo de configuración versionado, y con la misma semilla y las mismas versiones produce archivos idénticos, verificados con un manifiesto SHA-256. Las claves de los catálogos son únicas, y los huérfanos en COMPRAS solo existen con una tasa explícita (orphan_rate). Para que los datos sean realistas, IMPORTE se calcula como PIEZAS por un precio unitario derivado del precio base por CLAVE, un factor por fabricante y ruido. Las distribuciones tienen cola larga y concentración tipo Pareto, con estacionalidad mensual, instituciones reales, los 32 nombres oficiales de entidades del INEGI, formatos verosímiles de CLUES y claves del Compendio Nacional de Insumos, coherencia entre MARCA y FABRICANTE, y al menos dos años completos de datos con un volumen muy por debajo del nivel gratuito de BigQuery. Los patrones inyectados a propósito quedan documentados y el README declara que los datos son sintéticos. Incluye pruebas con pytest de determinismo, integridad referencial y rangos, y un objetivo de make para regenerar los datos. El éxito se mide con dos generaciones consecutivas que dan el mismo manifiesto SHA-256 y con las pruebas en verde."

## Clarifications

### Session 2026-10-08

- Q: ¿En qué formato se escriben las fuentes? → A: CSV UTF-8 sin BOM con encabezado, fechas
  `YYYY-MM-DD`, punto decimal y sin separador de miles. Parquet queda fuera de alcance.
- Q: ¿Se versionan los archivos de datos generados? → A: No. Se versionan la configuración y el
  manifiesto, el directorio de datos queda en `.gitignore` y los datos se regeneran con `make`.
- Q: ¿Qué valor por defecto tiene `orphan_rate`? → A: 0.5 % de las filas de `COMPRAS`, repartido
  entre huérfanos de `CLUE` y de `CLAVE`, para que la reconciliación del `INNER JOIN` tenga algo que
  medir. Las claves foráneas no se declaran.
- Q: ¿Hasta dónde llega la garantía de archivos idénticos, dado que NumPy solo garantiza el mismo
  flujo con la misma build en la misma máquina? → A: Igualdad byte a byte obligatoria en el mismo
  entorno. Entre plataformas distintas se busca sin garantizarla: los importes se calculan con
  aritmética entera en centavos y el comando de verificación informa qué archivo difiere.
- Q: ¿Los fabricantes, las marcas y los proveedores son empresas ficticias o reales? → A:
  Ficticios, con nombres verosímiles generados con Faker `es_MX`. Instituciones, geografía y
  moléculas sí son reales.
- Q: ¿Las pruebas del generador corren también en GitHub Actions? → A: Sí, pytest corre en cada PR
  hacia `main` con el mismo criterio que pre-commit (avisa sin bloquear el merge). El CI comprueba
  determinismo dentro del mismo runner, integridad y rangos, y no compara con el manifiesto
  versionado.
- Q: ¿Qué patrones comerciales se inyectan y qué hallazgos se toman como objetivo? → A: Base
  (concentración Pareto, estacionalidad y huérfanos al 0.5 %) más tres patrones: mezcla distinta de
  fabricante de referencia y genéricos por institución (P3), crecimiento diferencial por grupo
  terapéutico de 2024 a 2025 (P4) y ganancia de cuota de un fabricante genérico en algunas
  moléculas en 2025 (P5). Hallazgos objetivo: precio por institución (H1) y crecimiento de un
  grupo terapéutico (H2), con la cuota de un competidor (H3) de reserva. P3 respeta la fórmula de
  precio del principio V: no hay factor por institución.
- Q: ¿Cómo se agrupan las instituciones en `GRUPO_INSTITUCIONAL`? → A: Tres grupos: "Seguridad
  social" (IMSS, ISSSTE), "Fuerzas Armadas y PEMEX" (SEDENA, SEMAR, PEMEX) y "Población sin
  seguridad social" (IMSS-Bienestar y servicios estatales de salud).

## User Scenarios & Testing *(mandatory)*

> Nota de alcance: en esta feature los "usuarios" son quienes trabajan con el repositorio (autor,
> revisor técnico o cualquier persona que quiera reproducir la solución) y, de forma indirecta, el
> equipo comercial que consumirá el dashboard. Los nombres de tablas y campos, el lenguaje del
> generador (Python con NumPy y Faker `es_MX` en versión exacta), el gestor uv, pytest, el
> `Makefile` y el manifiesto SHA-256 no son decisiones de diseño de esta spec: los imponen el
> documento de requisitos del proyecto y la constitución (principios I, IV, V y VIII y la tabla de
> stack), así que forman parte del QUÉ.

### User Story 1 - Regenerar los datos de forma reproducible con un comando (Priority: P1)

Una persona clona el repositorio, prepara el entorno de desarrollo y ejecuta un único comando de
`make` para generar las tres fuentes. El comando lee la semilla y los parámetros del archivo de
configuración versionado, escribe los tres archivos y un manifiesto con la huella SHA-256, el
tamaño y el número de filas de cada uno. Si repite el comando, obtiene exactamente los mismos
bytes. Si compara su manifiesto con el versionado en el repositorio, coinciden.

**Why this priority**: es la medida de éxito declarada de la feature y lo que exige el principio V.
La carga en BigQuery, los chequeos de calidad (que comparan conteos contra el manifiesto), el SQL,
el dashboard y los hallazgos dependen de que cualquiera pueda reconstruir los mismos datos.

**Independent Test**: en un clon limpio con el entorno preparado, ejecutar dos veces seguidas el
objetivo de regeneración y comprobar que los dos manifiestos son idénticos byte a byte y que
coinciden con el manifiesto versionado.

**Acceptance Scenarios**:

1. **Given** un clon limpio con el entorno de desarrollo preparado, **When** la persona ejecuta el
   objetivo de regeneración, **Then** se crean los archivos de `COMPRAS`, `CLUE_CAT` y
   `CUADRO_BASICO` y el manifiesto, y el comando termina con código 0 e informa filas y huellas.
2. **Given** una primera generación terminada, **When** se ejecuta otra vez sin cambiar la
   configuración ni las versiones, **Then** los cuatro archivos son idénticos byte a byte a los
   anteriores.
3. **Given** el manifiesto versionado en el repositorio, **When** se regenera en un clon limpio,
   **Then** el manifiesto producido coincide con el versionado y el comando lo confirma. Si no
   coincide, el comando lo indica archivo por archivo y termina con código distinto de 0.
4. **Given** la configuración con otra semilla, **When** se regenera, **Then** las huellas de los
   archivos cambian, mientras que el esquema, los rangos y las reglas de integridad se siguen
   cumpliendo.
5. **Given** un archivo de configuración con un valor inválido (por ejemplo `orphan_rate` negativo
   o un rango de fechas de menos de dos años completos), **When** se ejecuta la regeneración,
   **Then** el comando falla antes de escribir nada, nombra el parámetro y el rango válido, y los
   archivos de una generación anterior quedan intactos.

---

### User Story 2 - Fuentes que cumplen el contrato y se pueden unir sin sorpresas (Priority: P1)

Quien prepara la carga en BigQuery recibe tres archivos con exactamente los campos de los
requisitos, en ese orden y con esos nombres, en un formato que BigQuery carga con esquema
explícito y tipos estrictos (`FECHA` como fecha, `PIEZAS` entero, `IMPORTE` decimal exacto, claves
como texto con ceros a la izquierda). Las claves de los catálogos son únicas y los huérfanos de
`COMPRAS` existen solo en la proporción que declara la configuración, así que la reconciliación
del `INNER JOIN` de la vista se puede predecir de antemano.

**Why this priority**: la feature de carga y la vista `v_compras_farma_completa` dependen de este
contrato. Una clave duplicada en un catálogo multiplicaría filas e inflaría `SUM(IMPORTE)`, y un
huérfano no declarado desaparecería sin aviso en el `INNER JOIN` (principios I, III y IV).

**Independent Test**: ejecutar las pruebas automatizadas de integridad y de contrato sobre los
archivos generados: encabezados exactos, unicidad de claves, ausencia de nulos en columnas
obligatorias y tasa de huérfanos medida igual a la configurada dentro de la tolerancia declarada.

**Acceptance Scenarios**:

1. **Given** los archivos generados, **When** se leen sus encabezados, **Then** `COMPRAS` tiene
   `CLUE, CLAVE, COD_PROVEEDOR, MARCA, FABRICANTE, PIEZAS, IMPORTE, FECHA`; `CLUE_CAT` tiene
   `CLUE, ENTIDAD, INSTITUCION, DELEGACION, GRUPO_INSTITUCIONAL, NIVEL_ATENCION, MUNICIPIO`; y
   `CUADRO_BASICO` tiene `CLAVE, DESCRIPCION, MOLECULA, GRUPO_TERAPEUTICO, PRESENTACION,
   FABRICANTE`, sin columnas extra y con las mismas mayúsculas.
2. **Given** `CLUE_CAT` y `CUADRO_BASICO`, **When** se cuentan sus claves, **Then** cada `CLUE` y
   cada `CLAVE` aparece una sola vez.
3. **Given** `orphan_rate = 0`, **When** se genera, **Then** todo `CLUE` y toda `CLAVE` de
   `COMPRAS` existen en su catálogo.
4. **Given** `orphan_rate > 0`, **When** se genera, **Then** la proporción de filas de `COMPRAS`
   con alguna clave sin correspondencia coincide con la configurada dentro de la tolerancia
   declarada, y el manifiesto registra cuántas filas huérfanas hay por tipo de clave.
5. **Given** cualquier fila de `COMPRAS`, **When** se revisan sus valores, **Then** `PIEZAS` es un
   entero mayor que 0, `IMPORTE` es mayor que 0 con dos decimales como máximo y `FECHA` está dentro
   del rango declarado en la configuración.

---

### User Story 3 - Datos verosímiles que permiten hallazgos comerciales (Priority: P2)

Una analista de un laboratorio abre el dashboard construido sobre estos datos y reconoce un
mercado plausible: instituciones públicas reales, las 32 entidades con sus nombres oficiales,
claves con el formato de CLUES y del Compendio Nacional de Insumos, moléculas reales agrupadas en
grupos terapéuticos, marcas que siempre pertenecen al mismo fabricante, precios por pieza
coherentes para cada clave, concentración de compras en pocas moléculas e instituciones,
estacionalidad mensual y dos años completos que se pueden comparar entre sí.

**Why this priority**: el dashboard (30 %) y la visión comercial (10 %) necesitan datos donde haya
algo que encontrar. Sin cola larga ni dispersión de precios, el top 10, la participación por
institución y los hallazgos serían planos. Va después de P1 porque datos reproducibles y
correctos sin realismo siguen siendo cargables, y lo contrario no.

**Independent Test**: ejecutar las pruebas de rangos y realismo sobre los archivos generados y
comprobar las métricas de concentración, cobertura temporal, coherencia de marcas y precios
implícitos descritas en los criterios de éxito.

**Acceptance Scenarios**:

1. **Given** `CLUE_CAT`, **When** se listan los valores de `ENTIDAD`, **Then** aparecen las 32
   entidades federativas con su nombre oficial del catálogo de áreas geoestadísticas del INEGI y
   ningún otro valor.
2. **Given** `CLUE_CAT`, **When** se revisa cada `CLUE`, **Then** tiene el formato de una CLUES
   (prefijo de entidad, prefijo de institución y consecutivo numérico) y sus prefijos concuerdan
   con la `ENTIDAD` y la `INSTITUCION` de esa misma fila.
3. **Given** `CUADRO_BASICO`, **When** se revisa cada `CLAVE`, **Then** tiene el formato de clave
   del Compendio Nacional de Insumos para medicamentos (grupo 010) y cada `MOLECULA` pertenece a un
   solo `GRUPO_TERAPEUTICO`.
4. **Given** `COMPRAS`, **When** se agrupa por `MARCA`, **Then** cada marca aparece con un solo
   `FABRICANTE`.
5. **Given** `COMPRAS`, **When** se calcula `IMPORTE / PIEZAS` por fila, **Then** el resultado es
   el precio unitario de la fila y queda dentro de la banda plausible declarada para su `CLAVE`.
6. **Given** `COMPRAS`, **When** se agrega `IMPORTE` por mes, **Then** hay compras en todos los
   meses del rango y el perfil mensual sigue los factores de estacionalidad de la configuración.
7. **Given** una molécula con fabricante de referencia y genéricos, **When** se calcula
   `SUM(IMPORTE) / SUM(PIEZAS)` por institución, **Then** las instituciones que compran más
   producto de referencia muestran un precio promedio mayor (P3).
8. **Given** `COMPRAS` unida a `CUADRO_BASICO`, **When** se compara el `IMPORTE` de 2025 con el de
   2024 por grupo terapéutico, **Then** el grupo configurado para crecer crece claramente más que
   el resto (P4).
9. **Given** las moléculas configuradas para P5, **When** se calcula la cuota de `IMPORTE` por
   fabricante en 2024 y en 2025, **Then** el fabricante genérico configurado gana cuota y el de
   referencia la pierde.

---

### User Story 4 - Datos honestos y documentados (Priority: P2)

Quien lee el README, el documento de hallazgos o ve el video sabe desde el principio que los datos
son sintéticos, conoce cómo se generaron y qué patrones se inyectaron a propósito, de modo que
puede distinguir un hallazgo que sale de consultar los datos de uno que solo repite un parámetro
del generador.

**Why this priority**: el principio V exige declarar los datos sintéticos y documentar los
patrones inyectados, y el principio VII exige que los hallazgos indiquen cuándo reflejan un patrón
inyectado. Es documentación, así que no bloquea la carga, pero sí la entrega.

**Independent Test**: revisar que el README declara los datos sintéticos y explica cómo
regenerarlos, que existe la documentación de los datos con cada patrón inyectado y su parámetro, y
que ambos pasan el lint de prosa.

**Acceptance Scenarios**:

1. **Given** el README, **When** una persona lo lee, **Then** encuentra la declaración de datos
   sintéticos y el comando para regenerarlos y verificar el manifiesto.
2. **Given** la documentación de los datos, **When** se busca un patrón inyectado (concentración,
   estacionalidad, huérfanos, P3 mezcla de fabricantes por institución, P4 crecimiento diferencial
   o P5 cambio de cuota), **Then** aparece con su descripción, el parámetro de la configuración que
   lo controla y su valor.
3. **Given** el README y la documentación de los datos, **When** se ejecuta el lint de prosa,
   **Then** no reporta violaciones.

---

### Edge Cases

- **Mismo entorno, ejecuciones distintas**: la salida no depende de la hora, la zona horaria, la
  configuración regional, el directorio de trabajo, el orden de iteración de estructuras internas
  ni de variables de entorno ajenas a la configuración. El manifiesto no contiene marcas de tiempo,
  rutas absolutas ni otros valores volátiles.
- **Otra plataforma o versión**: NumPy y Faker solo garantizan el mismo resultado con la misma
  semilla, la misma versión y, en el caso de NumPy, la misma build y máquina. Si otra plataforma
  produce huellas distintas, el comando de verificación lo detecta y lo informa por archivo, y la
  documentación explica la causa.
- **Fallo a mitad de la generación**: no quedan archivos parciales ni un manifiesto que describa
  archivos que no existen. Los archivos de la generación anterior se conservan o se reemplazan
  completos.
- **Textos con comas, comillas o acentos** (por ejemplo `DESCRIPCION` y `PRESENTACION`): se
  escriben con un entrecomillado consistente y en UTF-8, sin romper columnas.
- **Claves con ceros a la izquierda** (`CLUE`, `CLAVE`, `COD_PROVEEDOR`): se escriben como texto y
  no pierden ceros.
- **Ciudad de México**: no tiene municipios sino demarcaciones territoriales (alcaldías). En esa
  entidad `MUNICIPIO` contiene el nombre de la alcaldía.
- **Estado de México**: su nombre oficial en el catálogo del INEGI es "México". El generador usa
  el nombre oficial, y cualquier etiqueta más legible es tarea de la vista o del dashboard.
- **IMSS-Bienestar y servicios estatales**: una entidad tiene unidades de IMSS-Bienestar o de
  servicios estatales de salud, nunca de los dos, según la lista de adhesión versionada. La lista
  refleja la situación vigente y no cambia dentro del rango de fechas generado.
- **Huérfanos**: una fila huérfana tiene una `CLUE` o una `CLAVE` sin correspondencia, pero
  conserva valores válidos en el resto de los campos, de modo que solo la descarta el `INNER JOIN`
  y no un chequeo de nulos o de rangos.
- **Catálogo sin compras**: una `CLAVE` o una `CLUE` puede no aparecer en `COMPRAS`. Se permite y
  la documentación lo menciona, porque no rompe el `INNER JOIN`.
- **Moléculas con varias claves**: una misma `MOLECULA` puede tener varias `CLAVE` (distintas
  presentaciones o concentraciones), y los análisis por molécula agregan todas sus claves.
- **Fabricante de compra distinto del de catálogo**: el `FABRICANTE` de una fila de `COMPRAS`
  puede ser distinto del `FABRICANTE` de `CUADRO_BASICO` para esa `CLAVE`, porque varios
  fabricantes surten la misma clave. El de compra siempre pertenece al conjunto de fabricantes
  autorizados para esa clave.
- **Redondeo del importe**: `IMPORTE` es exactamente `PIEZAS` multiplicado por un precio unitario
  expresado en centavos, así que `IMPORTE / PIEZAS` devuelve ese precio sin error de redondeo.

## Requirements *(mandatory)*

### Functional Requirements

**Contrato de las fuentes**

- **FR-001**: El generador MUST producir tres archivos, uno por fuente (`COMPRAS`, `CLUE_CAT` y
  `CUADRO_BASICO`), con exactamente los campos que listan los requisitos, en el mismo orden, con los
  mismos nombres y mayúsculas, sin columnas adicionales.
- **FR-002**: Los archivos MUST escribirse en CSV UTF-8 sin BOM, con una fila de encabezado,
  fechas `YYYY-MM-DD`, punto decimal, sin separador de miles, saltos de línea LF y un entrecomillado
  consistente. Parquet queda fuera de alcance.
- **FR-003**: Los tipos lógicos MUST ser compatibles con la DDL que exige la constitución: `FECHA`
  fecha de calendario, `PIEZAS` entero, `IMPORTE` decimal exacto con dos decimales como máximo, y
  `CLUE`, `CLAVE`, `COD_PROVEEDOR` y los atributos descriptivos como texto.
- **FR-004**: Las columnas obligatorias (claves, `FECHA`, `PIEZAS` e `IMPORTE`) MUST NOT contener
  valores vacíos. Los atributos descriptivos de los catálogos tampoco quedan vacíos.

**Determinismo y manifiesto**

- **FR-005**: La semilla y todos los parámetros de la generación (rango de fechas, volúmenes,
  `orphan_rate`, distribuciones, factores de estacionalidad, factores de precio y bandas de ruido)
  MUST vivir en un único archivo de configuración versionado. El código MUST NOT contener valores
  de parámetros fuera de ese archivo, salvo catálogos de referencia versionados (entidades,
  instituciones, moléculas).
- **FR-006**: Con la misma configuración y las mismas versiones de dependencias, en el mismo
  entorno, dos generaciones MUST producir archivos idénticos byte a byte. Entre plataformas
  distintas la igualdad SHOULD lograrse, y `IMPORTE` MUST calcularse con aritmética entera en
  centavos a partir de un precio unitario redondeado una sola vez.
- **FR-007**: Cada generación MUST escribir un manifiesto con, por archivo, su nombre relativo, su
  huella SHA-256, su tamaño en bytes y su número de filas, más el número de filas huérfanas de
  `COMPRAS` por tipo de clave. El manifiesto MUST ser determinista (orden fijo y sin marcas de
  tiempo ni rutas absolutas) y MAY incluir la huella de la configuración usada.
- **FR-008**: MUST existir un comando que compare el manifiesto recién producido con el versionado
  y termine con código distinto de 0, indicando qué archivo difiere, cuando no coincidan.
- **FR-009**: Las versiones de Python, NumPy, Faker y del resto de dependencias del generador MUST
  quedar fijadas de forma exacta y gestionarse con uv, igual que el entorno de desarrollo de la
  feature 001.
- **FR-010**: La generación MUST validar la configuración antes de escribir nada. Ante un valor
  inválido falla con un mensaje que nombra el parámetro y su rango válido, y MUST NOT dejar
  archivos parciales ni un manifiesto inconsistente.
- **FR-011**: La generación MUST funcionar sin red y sin acceso a GCP.

**Integridad**

- **FR-012**: `CLUE` MUST ser única en `CLUE_CAT` y `CLAVE` MUST ser única en `CUADRO_BASICO`.
- **FR-013**: Las filas huérfanas de `COMPRAS` (con `CLUE` o `CLAVE` sin correspondencia en su
  catálogo) MUST existir solo si `orphan_rate` es mayor que 0, y su proporción MUST coincidir con
  la configurada dentro de una tolerancia declarada. El valor por defecto de `orphan_rate` es
  0.5 % de las filas de `COMPRAS`, repartido entre huérfanos de `CLUE` y de `CLAVE` según la
  configuración. Con esa tasa las claves foráneas MUST NOT declararse (principio III), y la
  documentación de los datos lo indica.
- **FR-014**: Una clave huérfana MUST tener el mismo formato que una clave válida, para que solo la
  descarte el `INNER JOIN`.

**Realismo**

- **FR-015**: `IMPORTE` MUST calcularse como `PIEZAS` × precio unitario, donde el precio unitario
  es el precio base de la `CLAVE` × el factor del fabricante × un ruido acotado, redondeado a
  centavos. MUST NOT generarse de forma independiente.
- **FR-016**: Para cada `CLAVE` MUST existir una banda plausible de precio unitario (mínimo y
  máximo) derivada de su precio base, de los factores de fabricante y del ruido máximo, y todo
  `IMPORTE / PIEZAS` de esa clave MUST caer dentro de la banda.
- **FR-017**: `PIEZAS` e `IMPORTE` MUST tener distribuciones de cola larga, y las compras MUST
  concentrarse tipo Pareto en moléculas, instituciones y entidades, con parámetros en la
  configuración.
- **FR-018**: `FECHA` MUST cubrir al menos dos años calendario completos, con compras en todos los
  meses y una estacionalidad mensual controlada por doce factores de la configuración.
- **FR-018a**: La configuración MUST controlar tres patrones comerciales inyectados, además de la
  concentración, la estacionalidad y los huérfanos:
  - **P3, mezcla de fabricantes por institución**: cada institución compra una proporción distinta
    de producto del fabricante de referencia y de genéricos, de modo que el precio promedio por
    pieza de una misma molécula difiere entre instituciones. La diferencia MUST salir solo de esa
    mezcla: la fórmula de FR-015 MUST NOT incluir un factor por institución.
  - **P4, crecimiento diferencial**: el `IMPORTE` de al menos un grupo terapéutico crece de 2024 a
    2025 claramente más que el resto, con tasas por grupo en la configuración.
  - **P5, cambio de cuota**: en al menos una molécula de alto importe, un fabricante genérico gana
    cuota de 2024 a 2025 a costa del fabricante de referencia, con las moléculas y las cuotas en la
    configuración.
- **FR-018b**: Los patrones P3 y P4 MUST bastar para sostener los dos hallazgos principales (precio
  por institución y crecimiento de un grupo terapéutico), y P5 uno de reserva. Las cifras de los
  hallazgos se obtendrán consultando la vista en una feature posterior y no copiando los
  parámetros.
- **FR-019**: `INSTITUCION` MUST usar instituciones públicas reales del sector salud mexicano, con
  estos valores canónicos: `IMSS`, `ISSSTE`, `SEDENA`, `SEMAR`, `PEMEX`, `IMSS-Bienestar` y
  `Servicios Estatales de Salud`. Los servicios
  estatales solo aparecen en entidades que no se adhirieron a IMSS-Bienestar, e IMSS-Bienestar solo
  en las que sí, según una lista de referencia versionada.
- **FR-019a**: `GRUPO_INSTITUCIONAL` MUST tomar exactamente tres valores, cada institución MUST
  pertenecer a un solo grupo y la definición MUST documentarse como decisión propia del proyecto:
  - "Seguridad social": `IMSS` e `ISSSTE`;
  - "Fuerzas Armadas y PEMEX": `SEDENA`, `SEMAR` y `PEMEX`;
  - "Población sin seguridad social": `IMSS-Bienestar` y `Servicios Estatales de Salud`.
- **FR-020**: `ENTIDAD` MUST tomar exactamente los 32 nombres oficiales de entidades federativas
  del catálogo de áreas geoestadísticas del INEGI, y las 32 MUST aparecer en `CLUE_CAT`.
- **FR-021**: `MUNICIPIO` MUST ser un municipio (o alcaldía, en Ciudad de México) real de la
  `ENTIDAD` de la misma fila, y `DELEGACION` MUST ser coherente con la `ENTIDAD` y la
  `INSTITUCION`.
- **FR-022**: `NIVEL_ATENCION` MUST tomar solo los valores de primer, segundo y tercer nivel de
  atención, con una proporción verosímil (más unidades de primer nivel que de tercero).
- **FR-023**: `CLUE` MUST tener el formato de una CLUES: once caracteres con prefijo de entidad,
  prefijo de institución y consecutivo numérico, y sus prefijos MUST concordar con la `ENTIDAD` y
  la `INSTITUCION` de la fila.
- **FR-024**: `CLAVE` MUST tener el formato de clave del Compendio Nacional de Insumos para
  medicamentos (grupo 010, con bloques numéricos separados por puntos). `MOLECULA` MUST ser una
  denominación genérica real, cada molécula MUST pertenecer a un solo `GRUPO_TERAPEUTICO` y
  `DESCRIPCION` y `PRESENTACION` MUST ser coherentes con la molécula.
- **FR-025**: Cada `MARCA` MUST pertenecer a un solo `FABRICANTE` en todo el conjunto de datos. El
  `FABRICANTE` de cada fila de `COMPRAS` MUST pertenecer al conjunto de fabricantes autorizados de
  su `CLAVE`, y el `FABRICANTE` de `CUADRO_BASICO` (fabricante de referencia de la clave) MUST ser
  uno de ellos. El fabricante de referencia es siempre un fabricante innovador, y los demás
  fabricantes autorizados son genéricos, cada uno con un único factor de precio (principio V).
- **FR-026**: `COD_PROVEEDOR` MUST ser un código alfanumérico de longitud fija que identifica a un
  proveedor de forma estable en todas las filas.
- **FR-027**: El volumen total MUST quedar muy por debajo del nivel gratuito de BigQuery (10 GiB de
  almacenamiento y 1 TiB de consultas al mes) y bastar para un análisis con cola larga: del orden
  de cientos de miles de filas en `COMPRAS`, con los volúmenes exactos en la configuración.
- **FR-028**: Ningún campo MUST contener datos personales reales. `FABRICANTE`, `MARCA` y
  `COD_PROVEEDOR` MUST corresponder a empresas ficticias con nombres verosímiles generados con
  Faker `es_MX`, de modo que ningún precio ni cuota de mercado se atribuya a una empresa real.

**Operación, pruebas y documentación**

- **FR-029**: El `Makefile` MUST ofrecer un objetivo documentado que regenere los datos y el
  manifiesto, y otro (o el mismo) que verifique el manifiesto contra el versionado.
- **FR-030**: MUST existir pruebas automatizadas con pytest de determinismo (dos generaciones con
  la misma configuración dan las mismas huellas, y otra semilla da huellas distintas), de
  integridad referencial (unicidad de claves y tasa de huérfanos) y de rangos (dominios de
  `PIEZAS`, `IMPORTE`, `FECHA`, entidades, niveles de atención y bandas de precio). Las pruebas
  MUST correr sin red ni GCP, en menos de dos minutos, y pueden usar una configuración reducida.
- **FR-030a**: El workflow de GitHub Actions MUST ejecutar la suite de pytest en cada PR hacia
  `main`, con el mismo criterio que pre-commit (el check avisa pero no bloquea el merge). En el CI,
  el determinismo se comprueba con dos generaciones en el mismo runner y MUST NOT compararse con
  el manifiesto versionado.
- **FR-031**: La configuración y el manifiesto MUST versionarse. Los archivos de datos generados
  MUST NOT versionarse: su directorio queda excluido en `.gitignore` y se regeneran con `make`.
- **FR-032**: El README MUST declarar que los datos son sintéticos y explicar cómo regenerarlos y
  verificarlos.
- **FR-033**: MUST existir una documentación de los datos sintéticos para lectores que describa
  cada campo y su regla de generación y cada patrón inyectado a propósito con el parámetro que lo
  controla y su valor. Esa documentación y el README MUST pasar `scripts/lint_prosa.sh`.
- **FR-034**: La matriz de trazabilidad (`docs/trazabilidad.md`) SHOULD incorporar los requisitos
  de "Materiales e Insumos" que cubre esta feature, con su artefacto y su verificación.

### Key Entities *(include if feature involves data)*

- **COMPRAS**: tabla de hechos. Grano: una línea de compra, es decir, una entrega de una `CLAVE`
  a una unidad médica (`CLUE`) por un proveedor (`COD_PROVEEDOR`) con una marca y un fabricante en
  una fecha. No tiene llave natural única: dos líneas pueden coincidir en clave, unidad y fecha
  porque corresponden a pedidos distintos. Medidas aditivas: `PIEZAS` e `IMPORTE`.
- **CLUE_CAT**: dimensión de unidades médicas. Grano: una unidad médica. Llave: `CLUE`. Atributos:
  entidad, institución, delegación, grupo institucional, nivel de atención y municipio.
- **CUADRO_BASICO**: dimensión de insumos. Grano: una clave del Compendio. Llave: `CLAVE`.
  Atributos: descripción, molécula, grupo terapéutico, presentación y fabricante de referencia.
- **Configuración del generador**: archivo versionado con la semilla y todos los parámetros. Es la
  única fuente de los valores que controlan los datos y de los patrones inyectados.
- **Manifiesto**: archivo determinista con la huella SHA-256, el tamaño y las filas de cada archivo
  y los conteos de huérfanos. Es la referencia para verificar la reproducibilidad y para el chequeo
  de conteos tras la carga (principio IV).
- **Catálogos de referencia**: listas versionadas que alimentan el realismo (las 32 entidades del
  INEGI, sus municipios o alcaldías, las instituciones con sus prefijos y su grupo institucional,
  la lista de entidades adheridas a IMSS-Bienestar y las moléculas con su grupo terapéutico y
  presentaciones). No son fuentes del entregable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dos generaciones consecutivas con la misma configuración, en el mismo entorno,
  producen manifiestos idénticos byte a byte, y el manifiesto de un clon limpio coincide con el
  versionado.
- **SC-002**: El 100 % de las pruebas automatizadas del generador pasa, y la suite completa termina
  en menos de dos minutos en un portátil.
- **SC-003**: La regeneración completa de las tres fuentes termina en menos de dos minutos en un
  portátil y ocupa menos de 100 MB en disco, menos del 1 % del almacenamiento gratuito mensual de
  BigQuery.
- **SC-004**: El 100 % de las claves de catálogo es único, y la tasa de huérfanos medida se desvía
  de `orphan_rate` en no más de una décima de punto porcentual (o es exactamente 0 si
  `orphan_rate = 0`).
- **SC-005**: El 100 % de las filas cumple los dominios: `PIEZAS > 0`, `IMPORTE > 0`, `FECHA` en
  rango, `ENTIDAD` entre los 32 nombres oficiales y `IMPORTE / PIEZAS` dentro de la banda de su
  clave.
- **SC-006**: El 20 % de las moléculas con más importe concentra entre el 60 % y el 90 % del
  `IMPORTE` total, y la institución con más importe supera el 30 % del total.
- **SC-007**: Todos los meses del rango tienen compras, y el cociente entre el mes con más importe
  y el mes con menos en un mismo año refleja los factores de estacionalidad configurados (al menos
  1.2 veces).
- **SC-007a**: En la molécula de ejemplo de P3, el precio promedio por pieza de la institución con
  más producto de referencia supera en al menos un 20 % al de la institución con menos. El grupo
  terapéutico de P4 crece al menos 10 puntos porcentuales más que el total del resto de grupos.
  En cada molécula de P5, el fabricante genérico gana al menos 10 puntos de cuota de `IMPORTE`.
  Las moléculas de P3 y P5 están dentro del 20 % de moléculas con más `IMPORTE` (definición de
  "alto importe" de FR-018a).
- **SC-008**: Ninguna `MARCA` aparece con más de un `FABRICANTE`, y el 100 % de los `CLUE` tiene
  prefijos coherentes con su entidad e institución.
- **SC-009**: Una persona que no participó en el proyecto puede regenerar y verificar los datos
  siguiendo solo el README, en menos de 10 minutos con el entorno ya preparado.
- **SC-010**: El README y la documentación de los datos pasan el lint de prosa sin violaciones, y
  cada patrón inyectado aparece documentado con su parámetro.

## Assumptions

- El rango de fechas por defecto son los años calendario completos 2024 y 2025 (del 2024-01-01 al
  2025-12-31). Así se cumplen los dos años completos para comparar año contra año sin un año
  parcial que distorsione los KPIs.
- Volúmenes por defecto, ajustables en la configuración: unas 300 000 filas en `COMPRAS`, unas
  2 000 unidades en `CLUE_CAT` y unas 160 claves en `CUADRO_BASICO` (139 moléculas). Con unos 110 bytes por fila
  de `COMPRAS`, el conjunto ocupa del orden de 35 MB.
- Las instituciones y la geografía son reales (instituciones públicas, nombres del INEGI,
  municipios y alcaldías) y las moléculas son denominaciones genéricas reales. Los fabricantes, las
  marcas y los proveedores son ficticios (ver FR-028).
- El `FABRICANTE` de `CUADRO_BASICO` se interpreta como el fabricante de referencia de la clave
  (titular del producto de referencia), y el de `COMPRAS` como el fabricante del producto entregado
  en esa línea. Esta definición resuelve una ambigüedad de los requisitos según el principio I y
  quedará documentada.
- Solo se generan medicamentos (grupo 010 del Compendio). Material de curación, vacunas y otros
  grupos quedan fuera.
- El formato de CLUES se toma de ejemplos públicos de la DGIS (por ejemplo `JCSSA001186`): dos
  letras de entidad, tres de institución y seis dígitos. Los prefijos de entidad e institución se
  verificarán contra el catálogo CLUES de la DGIS en el plan.
- Los nombres oficiales de las 32 entidades se verificarán en el plan contra el catálogo único de
  claves de áreas geoestadísticas del INEGI.
- La lista de entidades adheridas a IMSS-Bienestar se verificará en el plan contra fuentes
  oficiales (convenios publicados en el DOF o el sitio de IMSS-Bienestar).
- La reproducibilidad se exige en el mismo entorno. La coincidencia entre plataformas distintas
  (macOS y Linux) se busca, pero NumPy no la garantiza. Para reducir el riesgo, el precio unitario
  se redondea a centavos una sola vez y `IMPORTE` se calcula con enteros. El CI no exige que el
  manifiesto coincida entre plataformas (ver FR-030a).
- La carga en BigQuery, la DDL y los chequeos SQL son features posteriores. Esta feature solo
  entrega archivos, manifiesto, pruebas, documentación y objetivos de `make`.
- La versión exacta de cada dependencia nueva se elige en el plan con la regla del proyecto: la
  más reciente que lleve al menos 14 días publicada.
