# Feature Specification: Dashboard comercial en Data Studio (Fase 3)

**Feature Branch**: `005-dashboard-data-studio`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Dashboard comercial en Data Studio (Fase 3): un dashboard sobre la vista farma_analytics.v_compras_farma_completa para analistas de laboratorios farmacéuticos, construido según el principio VI de la constitución. Usa una sola fuente de datos reutilizable, no incrustada, conectada directamente a la vista, sin consulta personalizada que repita su lógica. La fuente usa las credenciales del propietario para que los lectores sin acceso a BigQuery vean los datos, con la frescura de datos configurada y documentada. Los campos se configuran en la fuente y no en cada gráfico: nombres de negocio en español, tipos semánticos (moneda MXN en los importes, fecha en FECHA y MES, Country subdivision 1st level con ENTIDAD_ISO) y agregación por defecto Sum en las medidas y None en claves y textos. Precio Promedio es un campo calculado en la fuente, SUM(IMPORTE) / SUM(PIEZAS), protegido contra la división entre cero y nunca un AVG de precios por fila. Controles en una franja común en la cabecera, como listas desplegables con búsqueda encadenadas en cascada: rango de fechas sobre FECHA, con un valor por defecto que cubra un periodo con datos (nunca Auto, que dejaría el tablero vacío); ENTIDAD; INSTITUCION y GRUPO_INSTITUCIONAL; GRUPO_TERAPEUTICO y MOLECULA. Cada control afecta a todos los visuales, salvo excepciones indicadas en el tablero. Hay un botón para restablecer los filtros, el cross-filtering está activo y "Show top" no oculta valores en los controles. KPIs: tres scorecards, Monto Total Comprado, Total de Piezas Adjudicadas y Precio Promedio General por Pieza, con unidades explícitas, números compactos (K, M) y comparación con un periodo de referencia que tenga datos, marcando el cambio con ▲▼ y no solo con color. Visualizaciones: gasto por ENTIDAD en barras horizontales ordenadas de mayor a menor con etiquetas de valor, con un mapa opcional como complemento y nunca como única representación; participación por INSTITUCION en barras horizontales ordenadas con etiquetas de porcentaje (un pie solo con 5 categorías o menos); y una tabla Top 10 con Molécula, Fabricante (FABRICANTE_COMPRA), Piezas, Importe y Precio Promedio, ordenada por Importe, con números alineados a la derecha y un título que indique el grano molécula-fabricante. Diseño: una página principal 16:9 sin scroll, en pirámide invertida (título y controles, KPIs, desglose y detalle), con rejilla fija y componentes alineados. Sin 3D, sombras, degradados ni fondos con imagen, con barras que empiezan en cero, sin doble eje y con categorías ordenadas por la métrica. Un color base y como máximo un acento por gráfico, paleta categórica de 8 colores o menos apta para daltonismo y la misma categoría con el mismo color en todo el informe. Contraste WCAG 2.1 AA (4.5:1 en texto, 3:1 en elementos gráficos), el color nunca como único canal, una familia tipográfica con 3 tamaños o menos y etiquetas directas en lugar de leyendas. Un subtítulo indica que los datos son sintéticos, el periodo, la fecha de corte y la definición del precio promedio ponderado. Los títulos comunican conclusiones o, si no, un recuadro de "Hallazgos clave" las resume. Como Data Studio no se versiona como código, hay una especificación escrita del dashboard en docs/ (fuente, campos, controles, gráficos, tema y colores) que es la referencia para construirlo y revisarlo, en español y cumpliendo el principio IX. Las cifras del dashboard tienen que coincidir con el SQL con los mismos filtros: los KPIs con los totales de la vista, el top 10 y el gasto por entidad con consultas sobre la vista, y la comparación de periodos con una consulta por año. Esa verificación se documenta con sus consultas, que pasan por dry run, llevan labels y respetan el maximum_bytes_billed de .bigqueryrc. Hay que comprobar si Data Studio reconoce MX-CMX en el mapa y documentar la alternativa si no. Implementación: una vez aprobada la especificación, Claude construye el dashboard en mi navegador con Claude in Chrome, sobre mi sesión de Google ya iniciada, siguiendo la especificación paso a paso y verificando cada pieza con capturas. Yo inicio sesión cuando haga falta. Antes de compartir, cambiar permisos o credenciales de la fuente, o aceptar términos o avisos, Claude me pide confirmación. El dashboard se comparte con 'Cualquier persona con el enlace puede ver' o con permisos de lectura explícitos, y se comprueba en una ventana de incógnito sin sesión. El README y la matriz de trazabilidad cubren la Fase 3. El éxito se mide con: el dashboard abre con datos en una ventana de incógnito; todos los controles funcionan y afectan a todos los visuales; los tres KPIs, el top 10 y el gasto por entidad coinciden con el SQL con los mismos filtros; la lista del principio VI se cumple completa, incluido el contraste; el enlace de lectura queda listo para entregar."

## Clarifications

### Session 2026-10-08

- Q: ¿Dónde va el mapa de gasto por entidad: en la página principal, en una segunda página o solo
  como prueba de `MX-CMX`? → A: En la página principal, junto a las barras de entidades y sin
  sustituirlas. La rejilla de la especificación del dashboard reparte el lienzo 16:9 para que las 32
  barras, el mapa, el gráfico de instituciones, la tabla y las tarjetas se lean sin scroll.
- Q: Los títulos de Data Studio son texto fijo. ¿Títulos con la conclusión, títulos descriptivos con
  un recuadro de "Hallazgos clave" o ambos? → A: Títulos descriptivos (qué mide el gráfico y en qué
  unidad) y un recuadro de "Hallazgos clave" que dice a qué estado de filtros corresponde cada
  conclusión, para que nada quede falso al filtrar.
- Q: ¿Con qué rango abre el tablero y con qué periodo se comparan las tarjetas? → A: Abre con 2025
  completo y compara con el mismo periodo del año anterior (2024). Es la única opción en la que el
  periodo de referencia tiene datos. Para ver 2024-2025 el analista amplía el rango, y entonces la
  comparación queda sin datos y se ve como indica la especificación del dashboard.
- Q: ¿La disposición de la página con el mapa es definitiva? → A: Es la disposición inicial. Se
  puede cambiar después de verla construida, actualizando primero la especificación del dashboard.

## User Scenarios & Testing *(mandatory)*

> Nota de alcance: los "usuarios" de esta feature son el analista comercial de un laboratorio
> farmacéutico que abre el enlace de lectura sin cuenta de GCP, el dueño del repositorio (que es el
> propietario del informe y de la fuente, y ejecuta todo lo que toca GCP) y quien revisa la entrega
> comparando el tablero con su especificación escrita y con el SQL. Data Studio, BigQuery, la vista
> `v_compras_farma_completa`, el `.bigqueryrc` versionado, el `Makefile` y el programa `warehouse`
> los imponen el documento de requisitos y la constitución (principios I, III, VI, VII y VIII), así
> que forman parte del QUÉ. Los nombres de opciones de Data Studio (*Owner's credentials*, *Country
> subdivision (1st level)*, *Show top*) se citan porque la constitución los fija como reglas
> verificables.

### User Story 1 - Ver los indicadores generales del mercado con un enlace de lectura (Priority: P1)

Un analista abre el enlace del dashboard en un navegador sin sesión de Google. Ve una sola página
16:9 sin scroll. Arriba están el título, el subtítulo de transparencia (datos sintéticos, periodo,
fecha de corte y definición del precio promedio ponderado) y la franja de controles. Debajo, tres
tarjetas: Monto Total Comprado, Total de Piezas Adjudicadas y Precio Promedio General por Pieza. Cada
tarjeta tiene unidad explícita y número compacto (K, M) y se compara con un periodo de referencia que
tiene datos, con el cambio marcado con ▲ o ▼ además del color.

**Why this priority**: sin una fuente que funcione con las credenciales del propietario y un enlace
de lectura no hay entregable (requisitos, criterio de entrega 2). Las tarjetas son el primer nivel
de la pirámide invertida y el primer requisito visual de la Fase 3.

**Independent Test**: con solo la fuente, el encabezado y las tres tarjetas construidos, abrir el
enlace en una ventana de incógnito sin sesión y comprobar que las tarjetas muestran datos y que sus
valores coinciden con la consulta de totales sobre la vista para el mismo rango de fechas.

**Acceptance Scenarios**:

1. **Given** el informe compartido en modo lectura, **When** alguien lo abre en una ventana de
   incógnito sin sesión de Google, **Then** la página carga con datos en las tres tarjetas, sin
   pedir acceso a BigQuery ni mostrar errores de permisos.
2. **Given** el rango de fechas por defecto, **When** se compara cada tarjeta con la consulta de
   totales sobre la vista filtrada por ese rango, **Then** Monto Total Comprado es igual a
   `SUM(IMPORTE)`, Total de Piezas Adjudicadas es igual a `SUM(PIEZAS)` y Precio Promedio General
   por Pieza es igual a `SUM(IMPORTE) / SUM(PIEZAS)`, con la precisión que muestra la tarjeta.
3. **Given** el rango de fechas por defecto, **When** se lee la comparación de cada tarjeta,
   **Then** el periodo de referencia tiene datos, el cambio coincide con la consulta por año y su
   dirección se distingue por el símbolo ▲ o ▼ aunque se vea en escala de grises.
4. **Given** la página principal, **When** se mide el lienzo, **Then** es 16:9, todo el contenido
   cabe sin scroll y el subtítulo dice que los datos son sintéticos, el periodo cubierto, la fecha
   de corte y que el precio promedio es `SUM(IMPORTE) / SUM(PIEZAS)`.

---

### User Story 2 - Filtrar todo el tablero con controles encadenados (Priority: P1)

El analista acota el análisis con la franja de controles de la cabecera: rango de fechas sobre
`FECHA`, entidad, institución y grupo institucional, grupo terapéutico y molécula. Cada lista
desplegable permite buscar y solo ofrece valores compatibles con lo ya elegido en los otros
controles (por ejemplo, al elegir el grupo terapéutico Oncología, la lista de moléculas solo muestra
moléculas de Oncología). Cada control afecta a todos los visuales. Un botón deja todos los filtros
en su estado inicial, y al hacer clic en una barra o en una fila los demás gráficos se filtran por
ese valor.

**Why this priority**: los cuatro filtros son el primer requisito de la Fase 3 y la "correcta
aplicación de filtros" es uno de los cuatro aspectos del criterio de dashboard (30 %).

**Independent Test**: con la franja de controles y al menos una tarjeta y un gráfico, aplicar cada
control por separado y en combinación, comprobar que cambian todos los visuales y que el botón de
restablecer devuelve el estado inicial.

**Acceptance Scenarios**:

1. **Given** el tablero en su estado inicial, **When** el analista elige una entidad, **Then** las
   tarjetas, los gráficos y la tabla muestran solo compras de esa entidad.
2. **Given** un grupo terapéutico elegido, **When** el analista abre la lista de moléculas, **Then**
   solo aparecen las moléculas de ese grupo, y lo mismo ocurre entre grupo institucional e
   institución y entre entidad e institución.
3. **Given** cualquier lista desplegable, **When** el analista escribe parte de un nombre, **Then**
   la lista se reduce a los valores que lo contienen, y sin escribir nada la lista ofrece todos los
   valores posibles (las 32 entidades, las 7 instituciones, las 139 moléculas) sin que una opción de
   "mostrar los primeros N" oculte ninguno.
4. **Given** varios filtros aplicados, **When** el analista pulsa el botón de restablecer, **Then**
   todos los controles vuelven a su valor por defecto, incluido el rango de fechas por defecto.
5. **Given** el tablero en su estado inicial, **When** el analista hace clic en una barra del
   gráfico de instituciones, **Then** los demás gráficos, las tarjetas y la tabla se filtran por esa
   institución, y un segundo clic quita el filtro.
6. **Given** el rango de fechas por defecto, **When** se abre el tablero, **Then** el rango es fijo y
   cubre un periodo con datos dentro de 2024-01-01 a 2025-12-31 (nunca "Auto").
7. **Given** un control que por diseño no afecte a algún visual, **When** se revisa el tablero,
   **Then** esa excepción está indicada en el propio tablero junto al visual afectado.

---

### User Story 3 - Analizar dónde y quién compra, y quién vende (Priority: P1)

Debajo de las tarjetas, el analista ve el gasto por entidad en barras horizontales ordenadas de
mayor a menor con la etiqueta del importe en cada barra, la participación por institución en barras
horizontales ordenadas con la etiqueta del porcentaje y la tabla "Top 10 molécula-fabricante" con
Molécula, Fabricante, Piezas, Importe y Precio Promedio, ordenada por Importe. Así puede responder en
qué estados conviene concentrar la fuerza de ventas, qué institución pesa más en la demanda y qué
fabricantes lideran cada molécula y a qué precio.

**Why this priority**: son las tres visualizaciones obligatorias de la Fase 3 y la "elección
adecuada de gráficos" es otro aspecto del criterio de dashboard.

**Independent Test**: con los tres visuales construidos, comparar sus cifras con consultas sobre la
vista con los mismos filtros (estado inicial y al menos una combinación de filtros) y revisar el
orden, las etiquetas y el formato.

**Acceptance Scenarios**:

1. **Given** el estado inicial, **When** se lee el gráfico de entidades, **Then** muestra las
   entidades con compras ordenadas por importe de mayor a menor, con el eje empezando en cero, la
   etiqueta del importe en cada barra en formato compacto y los mismos importes que la consulta de
   gasto por entidad sobre la vista.
2. **Given** el estado inicial, **When** se lee el gráfico de instituciones, **Then** muestra las 7
   instituciones ordenadas por participación, con la etiqueta del porcentaje del importe total en
   cada barra, y los porcentajes suman 100 % (con tolerancia de redondeo).
3. **Given** el estado inicial, **When** se lee la tabla, **Then** tiene exactamente 10 filas de
   pares molécula-`FABRICANTE_COMPRA` ordenadas por Importe de mayor a menor, el título indica ese
   grano, los números están alineados a la derecha con formato consistente y las 10 filas coinciden
   con la consulta del top 10 sobre la vista.
4. **Given** una entidad elegida en el control, **When** se comparan el top 10 y el gasto por
   entidad con las consultas sobre la vista con el mismo filtro, **Then** coinciden.
5. **Given** cualquier precio promedio del tablero, **When** se revisa su definición, **Then** sale
   del campo calculado de la fuente `SUM(IMPORTE) / SUM(PIEZAS)` y no de un promedio de precios por
   fila.

---

### User Story 4 - Leer el tablero sin depender del color y entender sus conclusiones (Priority: P2)

Un analista con daltonismo, o que imprime el tablero en escala de grises, lee las mismas cifras y
las mismas conclusiones que cualquier otro. El texto cumple contraste 4.5:1 y los elementos gráficos
3:1, las barras llevan etiquetas directas en lugar de leyendas, la misma categoría tiene el mismo
color en todo el informe y ningún dato depende solo del color. Los títulos de los gráficos comunican
la conclusión o un recuadro de "Hallazgos clave" las resume.

**Why this priority**: es lo que separa un tablero que cumple de uno que es claro (principio VI,
"Diseño visual"), pero se aplica sobre visuales que ya existen.

**Independent Test**: revisar el tablero con la lista del principio VI, medir el contraste de cada
par de colores de texto y de gráfico con una calculadora WCAG y ver una captura en escala de grises.

**Acceptance Scenarios**:

1. **Given** cada par de color de texto y fondo del tema, **When** se mide su contraste, **Then** es
   de al menos 4.5:1, y cada color de barra frente al fondo es de al menos 3:1.
2. **Given** una captura del tablero en escala de grises, **When** alguien lee las tarjetas y los
   gráficos, **Then** obtiene los mismos valores, el sentido del cambio de cada tarjeta y el orden de
   las categorías.
3. **Given** el tablero, **When** se cuentan familias y tamaños de letra, **Then** hay una sola
   familia y 3 tamaños o menos, sin texto rotado en los ejes.
4. **Given** el tablero, **When** se revisan los efectos visuales, **Then** no hay 3D, sombras,
   degradados, fondos con imagen ni doble eje, y cada gráfico usa un color base y como máximo un
   acento.
5. **Given** el tablero en su estado inicial, **When** se lee el recuadro de "Hallazgos
   clave", **Then** cada conclusión es una afirmación cuantificada que coincide con el SQL y dice
   a qué estado de filtros corresponde.

---

### User Story 5 - Reconstruir y revisar el tablero desde su especificación escrita (Priority: P2)

Como Data Studio no se versiona como código, una especificación escrita en `docs/` describe la
fuente, cada campo con su nombre de negocio, tipo y agregación, el campo calculado, cada control,
cada gráfico con su posición en la rejilla, el tema y los colores con sus contrastes. Quien revisa la
entrega compara el tablero con ese documento punto por punto, y quien lo quiera reconstruir puede
hacerlo siguiéndolo. Un objetivo de `make` ejecuta las consultas de verificación sobre la vista y
deja las cifras que el tablero tiene que mostrar.

**Why this priority**: lo exige el principio VIII ("todo es código versionado") y es la referencia
con la que se construye y se revisa el tablero, pero el tablero puede verse sin él.

**Independent Test**: leer la especificación sin abrir Data Studio y comprobar que cada componente
del tablero tiene su definición, y ejecutar el objetivo de verificación para obtener las cifras
esperadas del estado inicial.

**Acceptance Scenarios**:

1. **Given** la especificación del dashboard, **When** se compara con el tablero publicado,
   **Then** cada campo, control, tarjeta, gráfico, color y tamaño de letra del tablero aparece en la
   especificación con el mismo valor, y no hay componentes sin especificar.
2. **Given** la vista desplegada, **When** el dueño ejecuta el objetivo de verificación del
   dashboard, **Then** cada consulta pasa por dry run, lleva labels, respeta el `maximum_bytes_billed`
   de `.bigqueryrc` y produce los totales, la comparación por año, el gasto por entidad y el top 10
   del estado inicial.
3. **Given** la especificación y el linter de prosa, **When** se revisa el documento, **Then** está
   en español y pasa `scripts/lint_prosa.sh`.

---

### User Story 6 - Ver el gasto en un mapa como complemento (Priority: P3)

El analista ve el gasto por entidad también en un mapa de México coloreado por estado, que
complementa las barras y nunca las sustituye. Ciudad de México aparece con su código vigente
`MX-CMX`. Si Data Studio no lo reconoce, la alternativa queda documentada y aplicada.

**Why this priority**: el mapa es opcional en los requisitos ("barras o mapa") y el principio VI
prohíbe que sea la única representación, pero la feature 004 dejó pendiente comprobar `MX-CMX`.

**Independent Test**: construir el mapa con `ENTIDAD_ISO` como subdivisión de primer nivel y
comprobar que se pintan las 32 entidades, incluida Ciudad de México.

**Acceptance Scenarios**:

1. **Given** el mapa con `ENTIDAD_ISO`, **When** se ve en el estado inicial, **Then** se pintan las
   32 entidades y Ciudad de México tiene color y su importe en el tooltip.
2. **Given** que Data Studio no reconoce `MX-CMX`, **When** se revisa la especificación del
   dashboard, **Then** documenta la prueba, la alternativa elegida y su razón, y el mapa la aplica.

---

### User Story 7 - Seguir el recorrido de la Fase 3 en el README y la trazabilidad (Priority: P3)

Una persona lee en el README cómo se conecta el dashboard a la vista, cómo se verifica contra el SQL
y dónde está el enlace de lectura. La matriz de trazabilidad relaciona cada requisito de la Fase 3
con su componente del tablero y con su verificación.

**Why this priority**: lo exigen el principio VIII y la cobertura del 100 % de la matriz (principio
I) antes de entregar, pero no bloquea el tablero.

**Independent Test**: seguir el README desde el estado que deja la feature 004 y llegar al tablero y
a las cifras de verificación sin pasos no escritos.

**Acceptance Scenarios**:

1. **Given** la vista desplegada, **When** se siguen los pasos de la Fase 3 del README, **Then** se
   llega a las cifras de verificación y al enlace de lectura.
2. **Given** la matriz de trazabilidad, **When** se revisan las filas de la Fase 3, **Then** cada
   control, KPI y visualización de los requisitos apunta a su componente y a su verificación.

---

### Edge Cases

- Rango de fechas sin datos (por ejemplo, 2023): las tarjetas muestran un estado vacío o un guion y
  no un cero que parezca una cifra real. La especificación dice cómo se ve.
- Rango elegido por el analista cuyo periodo de referencia no tiene datos (por ejemplo, 2024 contra
  2023, o 2024-2025 contra 2023-2024, que solo tiene datos en 2024): la tarjeta no puede mostrar un cambio inventado. La especificación documenta qué muestra la
  comparación en ese caso.
- Combinación de filtros sin filas (por ejemplo, SEMAR en una entidad donde no opera): los visuales
  muestran un estado vacío legible, no un error.
- Precio promedio con `SUM(PIEZAS) = 0`: no ocurre con los datos actuales (`PIEZAS > 0`), pero el
  campo calculado devuelve vacío en lugar de un error o de infinito.
- Valores con texto largo (por ejemplo, "Veracruz de Ignacio de la Llave" o "Población sin seguridad
  social"): las etiquetas no se cortan de forma que se pierda el significado ni se rotan.
- 32 barras de entidades en una página sin scroll: cada barra y su etiqueta tienen que leerse en el
  lienzo 16:9. Si no caben, la especificación justifica la alternativa sin ocultar entidades sin
  avisarlo.
- Empate en el décimo lugar del top 10: el orden secundario es estable y está documentado, como en
  la pregunta 1 de la feature 004.
- Una molécula con varios fabricantes puede aparecer más de una vez en el top 10, porque el grano es
  molécula-fabricante. El título lo dice.
- Cross-filtering que deja el tablero en un estado confuso: el botón de restablecer lo devuelve al
  estado inicial.
- Lector con la caché de Data Studio desactualizada: los datos son estáticos, así que la frescura
  configurada no cambia las cifras. Se documenta el valor elegido y su razón.
- La tarjeta no admite cross-filtering como origen (solo lo recibe), así que el clic que filtra el
  tablero sale de las barras y de la tabla.
- Cuota diaria de consultas agotada o facturación desactivada: el tablero no mostraría datos a los
  lectores. La documentación indica el riesgo y que el consumo del tablero se puede atribuir por las
  labels que Data Studio añade a cada job (`requestor`, `looker_studio_report_id` y
  `looker_studio_datasource_id`).
- Ciudad de México no reconocida en el mapa como `MX-CMX`: el mapa queda con un hueco, y la
  alternativa documentada lo corrige sin cambiar la vista si es posible.
- Ventana de incógnito: las extensiones de Chrome están desactivadas por defecto en incógnito, así
  que la comprobación sin sesión tiene que hacerse por una vía que no use la sesión del dueño.

## Requirements *(mandatory)*

### Functional Requirements

**Fuente de datos**

- **FR-001**: MUST existir una sola fuente de datos reutilizable (no incrustada en el informe),
  conectada directamente a `farma_analytics.v_compras_farma_completa` como tabla, sin consulta
  personalizada. Todos los componentes del informe MUST usar esa fuente.
- **FR-002**: La fuente MUST usar las credenciales del propietario (*Owner's credentials*), para que
  los lectores sin acceso a BigQuery vean los datos. Antes de fijar o cambiar las credenciales, Claude
  MUST pedir confirmación al dueño.
- **FR-003**: La frescura de datos de la fuente MUST configurarse con un valor explícito y documentarse
  con su razón en la especificación del dashboard.
- **FR-004**: Cada campo de la vista que use el informe MUST configurarse en la fuente, no en cada
  gráfico, con:
  - un nombre de negocio en español (por ejemplo, `IMPORTE` como "Importe" y `FABRICANTE_COMPRA`
    como "Fabricante");
  - su tipo semántico: moneda MXN en `IMPORTE`, número en `PIEZAS`, fecha en `FECHA` y en `MES`,
    *Country subdivision (1st level)* en `ENTIDAD_ISO` y texto en las claves y los nombres;
  - su agregación por defecto: `Sum` en `IMPORTE` y `PIEZAS`, y `None` en las claves y los textos.
  La especificación del dashboard MUST listar la configuración de cada campo, incluidos los que se
  dejan sin usar.
- **FR-005**: "Precio Promedio" MUST ser un campo calculado de la fuente equivalente a
  `SUM(IMPORTE) / SUM(PIEZAS)`, con tipo moneda MXN, protegido contra la división entre cero (devuelve
  vacío cuando `SUM(PIEZAS)` es 0). MUST NOT existir en el informe un `AVG` de precios por fila ni un
  precio por fila.

**Controles e interactividad**

- **FR-006**: MUST existir, en una franja común en la cabecera, un control de rango de fechas sobre
  `FECHA` y listas desplegables con búsqueda para `ENTIDAD`, `INSTITUCION`, `GRUPO_INSTITUCIONAL`,
  `GRUPO_TERAPEUTICO` y `MOLECULA`.
- **FR-007**: Las listas desplegables MUST estar encadenadas en cascada: las opciones de cada lista
  MUST limitarse a los valores compatibles con lo elegido en las demás.
- **FR-008**: Ninguna lista MUST ocultar valores por un límite de "mostrar los primeros N" (*Show
  top #*, que agrupa el exceso en "All others"): sin búsqueda, cada lista MUST ofrecer todos los
  valores existentes. Por la misma razón, el gráfico de entidades y el de instituciones MUST NOT
  agrupar categorías en "Others".
- **FR-009**: El rango de fechas por defecto MUST ser el rango fijo 2025-01-01 a 2025-12-31, y las
  tarjetas MUST compararse con el mismo periodo del año anterior (2024-01-01 a 2024-12-31). MUST NOT
  usar "Auto": con BigQuery, "Auto" muestra todo el rango del dataset (2024-01-01 a 2025-12-31), que
  no es el periodo por defecto elegido y cuyo año anterior solo tiene datos en parte, de modo que la
  comparación mezclaría dos años con uno. El subtítulo MUST decir que el tablero abre con 2025
  frente a 2024 y que el rango se puede ampliar.
- **FR-010**: Cada control MUST afectar a todas las tarjetas, gráficos y tablas. Cualquier
  excepción MUST indicarse con un texto visible junto al visual afectado y en la especificación.
- **FR-011**: MUST existir un botón visible que restablezca todos los controles y filtros a su estado
  por defecto.
- **FR-012**: El cross-filtering MUST estar activo en los gráficos de barras y en la tabla, de modo
  que un clic en una categoría filtre los demás visuales.

**KPIs**

- **FR-013**: MUST existir tres tarjetas, "Monto Total Comprado", "Total de Piezas Adjudicadas" y
  "Precio Promedio General por Pieza", calculadas como `SUM(IMPORTE)`, `SUM(PIEZAS)` y el campo
  calculado Precio Promedio.
- **FR-014**: Cada tarjeta MUST mostrar su unidad explícita (pesos MXN, piezas, pesos MXN por pieza)
  y números compactos (K, M), con los decimales indicados en la especificación.
- **FR-015**: Cada tarjeta MUST compararse con un periodo de referencia con datos y mostrar el cambio
  con ▲ o ▼ además del color. El color de subida o bajada MUST NOT ser el único canal. La
  documentación oficial no dice si la tarjeta dibuja esas flechas, así que se comprueba al
  construirla y, si no las dibuja, la especificación del dashboard documenta y aplica una
  alternativa que muestre el sentido del cambio con un símbolo o una palabra.

**Visualizaciones**

- **FR-016**: Gasto por entidad: MUST ser un gráfico de barras horizontales de `SUM(IMPORTE)` por
  `ENTIDAD`, ordenado de mayor a menor, con el eje desde cero y la etiqueta del valor en cada barra.
  Ninguna entidad con compras MUST quedar oculta sin que el gráfico lo indique.
- **FR-017**: Un mapa de México con `SUM(IMPORTE)` por `ENTIDAD_ISO` MUST complementar las barras de
  FR-016 en la página principal, con un solo tono secuencial y el importe en el tooltip. MUST NOT ser
  la única representación del gasto por entidad, MUST NOT reducir las barras de FR-016 hasta que sus
  etiquetas dejen de leerse y MUST obedecer los mismos controles.
- **FR-018**: Participación por institución: MUST ser un gráfico de barras horizontales con el
  porcentaje de `SUM(IMPORTE)` por `INSTITUCION` sobre el total filtrado, ordenado de mayor a menor y
  con la etiqueta del porcentaje en cada barra. Como hay 7 instituciones, MUST NOT usarse un pie ni
  un donut.
- **FR-019**: Top 10: MUST ser una tabla con las columnas Molécula, Fabricante (`FABRICANTE_COMPRA`),
  Piezas, Importe y Precio Promedio, con exactamente 10 filas de pares molécula-fabricante ordenadas
  por Importe de mayor a menor, con un orden secundario documentado para los empates, números
  alineados a la derecha con formato consistente y un título que diga el grano molécula-fabricante.
- **FR-020**: Ningún gráfico MUST usar 3D, sombras, degradados, fondos con imagen ni doble eje, y las
  categorías MUST ordenarse por la métrica.

**Diseño visual y accesibilidad**

- **FR-021**: El informe MUST tener una página principal con lienzo 16:9 donde todo el contenido
  cabe sin scroll, en pirámide invertida (título, subtítulo y controles; tarjetas; desglose por
  entidad e institución; detalle del top 10), con una rejilla definida en la especificación antes de
  maquetar y los componentes alineados a ella.
- **FR-022**: Color: cada gráfico MUST usar un color base y como máximo un acento. La paleta
  categórica, si se usa, MUST tener 8 colores o menos, apta para daltonismo (Okabe-Ito o el tema por
  defecto), y la misma categoría MUST llevar el mismo color en todo el informe.
- **FR-023**: Contraste WCAG 2.1 AA: cada texto MUST tener al menos 4.5:1 frente a su fondo y cada
  elemento gráfico al menos 3:1. La especificación MUST listar cada par de colores con su contraste
  medido.
- **FR-024**: El color MUST NOT ser el único canal de ningún dato. Las barras MUST llevar etiquetas
  directas en lugar de leyendas y MUST NOT haber texto rotado en los ejes.
- **FR-025**: El informe MUST usar una sola familia tipográfica con 3 tamaños o menos.
- **FR-026**: Un subtítulo MUST indicar que los datos son sintéticos, el periodo que cubren
  (2024-01-01 a 2025-12-31), la fecha de corte y que el precio promedio es ponderado,
  `SUM(IMPORTE) / SUM(PIEZAS)`.
- **FR-027**: Los títulos de los gráficos MUST ser descriptivos (qué mide y en qué unidad) y un
  recuadro de "Hallazgos clave" en la página principal MUST resumir las conclusiones, cada una con el
  estado de filtros al que corresponde (por ejemplo, "con el rango por defecto y sin otros
  filtros"). Cada conclusión MUST estar cuantificada y coincidir con el SQL. Si refleja un patrón
  inyectado por el generador, MUST indicarlo.

**Compartir**

- **FR-028**: El informe MUST compartirse con "Cualquier persona con el enlace puede ver" o con
  permisos de lectura explícitos. Antes de compartir o cambiar permisos, Claude MUST pedir
  confirmación al dueño.
- **FR-029**: MUST comprobarse que el enlace abre con datos en un navegador sin sesión de Google
  (ventana de incógnito o equivalente), con una captura como evidencia.

**Especificación escrita y verificación**

- **FR-030**: MUST existir en `docs/` una especificación del dashboard en español que cumpla el
  principio IX y describa la fuente (vista, credenciales, frescura), cada campo (nombre de negocio,
  tipo, agregación), el campo calculado, cada control (campo, tipo, valor por defecto, cascada), cada
  tarjeta, cada gráfico (campos, orden, etiquetas, posición en la rejilla), el tema (fondo, colores,
  familia y tamaños de letra) y cada par de colores con su contraste. Es la referencia para
  construirlo y revisarlo.
- **FR-031**: MUST existir consultas de verificación versionadas que leen solo de la vista y producen,
  para el estado inicial, los totales de las tres tarjetas, la comparación con el periodo de
  referencia (una consulta por año), el gasto por entidad, la participación por institución y el top
  10 molécula-fabricante, y que aceptan los mismos filtros que el tablero para comprobar al menos una
  combinación filtrada. Cumplen el estilo SQL del principio II y pasan SQLFluff.
- **FR-032**: Un objetivo de `make`, construido sobre el programa `warehouse`, MUST ejecutar esas
  consultas con dry run previo, labels estáticas en cada job y el `maximum_bytes_billed` de
  `.bigqueryrc`, e imprimir las cifras que el tablero tiene que mostrar. Lo ejecuta el dueño y falla
  con un mensaje claro si la vista no existe o no tiene filas.
- **FR-033**: La comparación entre el tablero y esas cifras MUST documentarse con el estado de
  filtros, el valor del tablero, el valor del SQL y el resultado, para los tres KPIs, el top 10 y el
  gasto por entidad, en el estado inicial y en al menos una combinación de filtros.
- **FR-034**: MUST comprobarse si Data Studio reconoce `MX-CMX` como subdivisión de México y
  documentarse el resultado. Si no lo reconoce, MUST documentarse y aplicarse una alternativa que no
  rompa el resto del tablero.

**Construcción, documentación y repositorio**

- **FR-035**: Una vez aprobada la especificación del dashboard, Claude MUST construir el tablero en
  el navegador del dueño con Claude in Chrome, sobre su sesión de Google, siguiendo la especificación
  paso a paso y verificando cada componente con una captura. MUST pedir confirmación antes de
  compartir, publicar, cambiar permisos o credenciales de la fuente y aceptar términos o avisos.
- **FR-036**: El README MUST explicar la Fase 3: qué fuente usa el tablero, cómo se verifica contra
  el SQL, qué ejecuta solo el dueño y dónde está el enlace de lectura. La matriz de trazabilidad MUST
  añadir las filas de la Fase 3. Ambos en español y cumpliendo el principio IX.
- **FR-037**: Los archivos versionados MUST NOT contener el ID del proyecto de GCP, credenciales ni
  referencias al documento de requisitos. El enlace de lectura del informe MAY versionarse.
- **FR-038**: El repositorio MUST seguir pasando `make lint`, `make test`, `make lint-sql` y
  `make lint-prosa`.

### Key Entities *(include if feature involves data)*

- **Fuente de datos**: conexión reutilizable de Data Studio a `v_compras_farma_completa`, con
  credenciales del propietario, frescura de datos y la configuración de cada campo. Es la única capa
  de campos del informe.
- **Campo de la fuente**: columna de la vista con su nombre de negocio, tipo semántico y agregación
  por defecto. Ejemplos: Importe (moneda MXN, `Sum`), Entidad ISO (*Country subdivision (1st
  level)*, `None`).
- **Precio Promedio**: campo calculado `SUM(IMPORTE) / SUM(PIEZAS)` con protección ante división
  entre cero, según el glosario del principio VII.
- **Control**: filtro de la cabecera (rango de fechas o lista desplegable) con su campo, su valor
  por defecto y su relación en cascada con los demás.
- **Tarjeta (KPI)**: métrica con unidad, formato compacto y comparación con el periodo de referencia.
- **Visual**: gráfico o tabla con sus campos, orden, etiquetas, colores y posición en la rejilla.
- **Especificación del dashboard**: documento en `docs/` que define todo lo anterior y el tema.
- **Consulta de verificación**: consulta versionada sobre la vista que produce la cifra que un
  componente del tablero tiene que mostrar con un estado de filtros dado.
- **Registro de verificación**: tabla con estado de filtros, valor del tablero, valor del SQL y
  resultado de la comparación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El enlace de lectura abre con datos en un navegador sin sesión de Google, sin pedir
  acceso ni mostrar errores, y la página principal carga completa en menos de 10 segundos.
- **SC-002**: Los 6 controles (rango de fechas y 5 listas desplegables) funcionan, cada uno cambia el
  100 % de las tarjetas, gráficos y tablas (salvo excepciones indicadas en el tablero), y el botón de
  restablecer devuelve el estado inicial en un clic.
- **SC-003**: Los 3 KPIs, las 10 filas del top 10 y el importe de cada entidad coinciden con el SQL
  sobre la vista con los mismos filtros, en el estado inicial y en al menos una combinación filtrada,
  con 0 diferencias a la precisión que muestra el tablero.
- **SC-004**: La lista del principio VI se cumple al 100 %, incluido el contraste: cada texto mide al
  menos 4.5:1 y cada elemento gráfico al menos 3:1.
- **SC-005**: Un analista que no conoce el proyecto responde en menos de 2 minutos, solo con el
  tablero, cuál es la entidad y la institución con más importe y cuál es la molécula-fabricante
  líder del top 10.
- **SC-006**: El 100 % de los componentes del tablero aparece en la especificación escrita con los
  mismos valores, y la especificación pasa `scripts/lint_prosa.sh`.
- **SC-007**: Todas las consultas de verificación pasan el dry run, llevan labels y ninguna supera el
  límite de bytes de `.bigqueryrc`.
- **SC-008**: El enlace de lectura queda documentado en el README, listo para entregar, y las filas de
  la Fase 3 de la matriz de trazabilidad cubren el 100 % de los controles, KPIs y visualizaciones de
  los requisitos.

## Assumptions

- La vista `v_compras_farma_completa` está desplegada con 298 500 filas y sus 22 columnas descritas
  (feature 004). Esta feature no cambia la vista. Si la prueba de `MX-CMX` exige otro código, la
  alternativa preferida se resuelve en Data Studio (por ejemplo, un campo calculado en la fuente), y
  cambiar la vista queda como último recurso con sus chequeos.
- "Fabricante" en el tablero es `FABRICANTE_COMPRA` (quien vendió a ese precio), la misma definición
  principal de la pregunta 3 de la feature 004. `FABRICANTE_CATALOGO` queda en la fuente sin usarse en
  la página principal.
- El top 10 tiene grano molécula-fabricante, como fija la constitución, así que una molécula puede
  aparecer más de una vez. El orden secundario ante empates es por molécula y fabricante ascendentes.
- La fecha de corte es la última `FECHA` con datos (2025-12-31). Los datos son estáticos y no hay
  refrescos programados.
- La frescura de datos se fija en 12 horas, el valor más largo que admite BigQuery (de 1 a 50
  minutos o de 1 a 12 horas, con 12 horas por defecto), porque los datos no cambian y así se
  repiten menos consultas.
- Las consultas que Data Studio lanza contra BigQuery no pasan por `.bigqueryrc`. Su costo lo limita
  la cuota diaria de 100 GiB del proyecto, y cada consulta a la vista lee unos pocos MB.
- Las extensiones de Chrome no funcionan en incógnito salvo que cada usuario active "Allow in
  Incognito" (ayuda de Chrome Enterprise), así que Claude no puede operar ahí sin cambiar esa
  configuración, y cambiarla queda fuera de lo que Claude hace por su cuenta. La comprobación sin sesión la hace el dueño en una
  ventana de incógnito o Claude en un navegador sin sesión de Google (por ejemplo, el navegador
  integrado de la app). Se decide en el plan.
- El informe es propiedad de la cuenta de Google del dueño. Cambiar de propietario o publicarlo en la
  galería de Data Studio queda fuera de alcance.
- El informe tiene una sola página. El mapa va en ella con una disposición inicial que puede
  ajustarse después de verla construida (aclaraciones del 2026-10-08).
- Los hallazgos comerciales completos (documento con 2 hallazgos) y el guion del video son de la
  feature 006. Esta feature solo incluye las conclusiones que se ven en el tablero.
- Data Studio es el nombre actual de Looker Studio desde abril de 2026 (constitución, principio VI).
  La documentación oficial se cita con la URL vigente en el plan.
