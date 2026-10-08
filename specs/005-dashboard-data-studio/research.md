# Research: Dashboard comercial en Data Studio (Fase 3)

Decisiones de la Fase 0 con sus fuentes. Salvo que se diga otra cosa, las rutas de Data Studio son
relativas a `docs.cloud.google.com/data-studio/` (algunas páginas viven todavía en
`docs.cloud.google.com/looker/docs/studio/`, se indica la ruta completa) y se consultaron el
2026-10-08. Data Studio es el nombre de Looker Studio desde abril de 2026 y las páginas muestran el
aviso del cambio de nombre.

Hallazgo general: la documentación oficial de Data Studio **no tiene una guía de diseño visual** de
dashboards (ni de selección de gráficos ni de accesibilidad más allá del texto alternativo de las
imágenes). Las reglas de diseño del principio VI salen de la teoría de visualización y de WCAG
(R13). La documentación de Google aporta la mecánica de cada componente y consejos sueltos de color,
rejilla, rendimiento y credenciales, que se aplican abajo.

Las cifras de diseño (rangos de valores, longitudes de nombres, totales de 2024 y 2025) se
calcularon en local con los CSV de `data/`, verificados con `make data-verify` contra el manifiesto.
Son los mismos datos que carga BigQuery, y el total de 2024-2025 coincide con el de la vista
(28 633.9 M de pesos y 55.25 M de piezas). Las cifras oficiales del tablero saldrán de
`make bq-dashboard` (R12).

## R1. Fuente de datos: reutilizable, credenciales del propietario y frescura

- **Decision**:
  - una fuente reutilizable creada desde la página de inicio de Data Studio con el conector de
    BigQuery, apuntando a la tabla `farma_analytics.v_compras_farma_completa` (sin "Custom query");
  - credenciales: *Owner's credentials*;
  - frescura de datos: 12 horas;
  - nombre de la fuente: "v_compras_farma_completa (BigQuery)", para que se trace 1:1 con la vista.
- **Rationale**:
  - una fuente incrustada vive dentro del informe y se copia con él; una reutilizable se comparte y
    se gestiona aparte (`/looker/docs/studio/embedded-data-sources`), que es lo que pide el principio
    VI;
  - con *Owner's credentials* un lector sin acceso al dataset ve los datos sin ganar acceso directo
    al dataset, y es el valor por defecto cuando el conector lo admite
    (`/looker/docs/studio/data-credentials-article`). La caché es compartida entre lectores
    (`improve-performance`);
  - para BigQuery la frescura va de 1 a 50 minutos o de 1 a 12 horas, con 12 horas por defecto
    (`/looker/docs/studio/manage-data-freshness`). Los datos son estáticos, así que el valor más
    largo repite menos consultas;
  - Google recomienda no compartir la fuente para que alguien vea el informe: el acceso lo deciden
    las credenciales (`think`, `share-reusable-data-sources`).
- **Alternatives considered**:
  - *Viewer's credentials*: cada lector necesitaría acceso al dataset y el enlace público no
    mostraría datos;
  - *Service account credentials*: exige crear y administrar una cuenta de servicio con permisos,
    sin beneficio para un informe de lectura (YAGNI, principio VIII);
  - "Custom query": prohibido por el principio VI porque repetiría la lógica de la vista;
  - extract de datos (`extract-data-for-faster-performance`): una copia estática más rápida, pero
    rompe la regla de conectarse directamente a la vista y añade otra capa que verificar.
- **Confirmación**: fijar las credenciales es una acción que Claude no hace sin pedir confirmación
  (FR-002). Como *Owner's* es el valor por defecto, lo normal es que solo haya que confirmar que
  queda así.

## R2. Campos de la fuente: nombres, tipos, agregación y Precio Promedio

- **Decision**: la configuración de los 22 campos y del campo calculado está en
  [data-model.md](data-model.md#campos-de-la-fuente). Lo esencial:
  - nombres de negocio en español sin mayúsculas sostenidas ("Importe", "Piezas", "Entidad",
    "Fabricante" para `FABRICANTE_COMPRA`);
  - `IMPORTE`: Currency, peso mexicano (MXN), agregación `Sum`;
  - `PIEZAS`: Number, `Sum`;
  - `FECHA`: Date (`YYYYMMDD`), `MES`: Date, mes y año (`YYYYMM`), `ANIO`: Year;
  - `ENTIDAD_ISO`: Geo, *Country subdivision (1st level)*;
  - claves y textos: Text, agregación `None`;
  - campo calculado "Precio Promedio" = `SUM(IMPORTE) / NULLIF(SUM(PIEZAS), 0)`, tipo Currency MXN.
- **Rationale**:
  - tipos y agregaciones disponibles: `aggregation` y `/looker/docs/studio/data-types`. Currency
    solo añade el símbolo de la moneda y no convierte;
  - un campo calculado con agregación explícita en la fórmula queda en "Auto" y no se puede volver a
    agregar (`aggregation`, `/looker/docs/studio/about-calculated-fields`). Así ningún gráfico puede
    promediar el precio por fila;
  - `SUM(a)/SUM(b)` es un ejemplo oficial de campo calculado y `NULLIF` existe en la lista de
    funciones (`nullif`, `function-list`). La documentación no dice qué devuelve una división entre
    cero, así que la protección es explícita;
  - una métrica que se deja en `None` en la fuente se suma por defecto en los informes
    (`aggregation`), por eso las medidas llevan `Sum` explícito y los textos `None`.
- **Por verificar al construir** (queda registrado en la especificación del dashboard):
  - que MXN aparece en la lista de monedas. Si no aparece, Number con prefijo "$" y la unidad
    "pesos (MXN)" en el título de cada componente;
  - que `NULLIF` acepta un agregado. Si no, `CASE WHEN SUM(PIEZAS) = 0 THEN NULL ELSE SUM(IMPORTE) /
    SUM(PIEZAS) END` (`case-searched`).
- **Alternatives considered**: `AVG` de un precio por fila (prohibido por los principios III y VI);
  un precio por fila en la vista (prohibido por el principio III).

## R3. Controles: listas desplegables en cascada, "Show top #" y rango de fechas

- **Decision**:
  - seis controles en la franja de la cabecera: un control de rango de fechas sobre `FECHA` y cinco
    *Drop-down list* (Entidad, Institución, Grupo institucional, Grupo terapéutico, Molécula), con
    "Enable search box" activado y selección múltiple permitida;
  - en cada lista, el límite de valores ("Show top #") se fija por encima del número de valores
    posibles (200 para Molécula, que tiene 139, y lo mismo para las demás), de modo que no aparece
    "All others";
  - el orden de cada lista es alfabético ascendente por el valor, para que el analista encuentre el
    nombre sin escribir;
  - el control de fechas tiene como valor por defecto un rango personalizado fijo,
    2025-01-01 a 2025-12-31 (Custom, Advanced, inicio y fin "Fixed");
  - los controles son de nivel de página (el informe tiene una sola página) y no se agrupan con
    ningún gráfico, así que afectan a todos.
- **Rationale**:
  - la cascada es automática cuando los controles y los gráficos usan la misma fuente: un control
    limita las opciones de los demás sin ningún ajuste (`/looker/docs/studio/about-controls`,
    `/looker/docs/studio/drop-down-list-and-fixed-size-list-control`). Por eso la fuente única es
    también la condición de la cascada;
  - "Show top #" agrupa lo que excede el límite en "All others" (ayuda de Data Studio,
    `support.google.com/looker-studio/answer/11335992`), lo que ocultaría valores (FR-008);
  - con BigQuery, "Auto" muestra todo el rango del dataset y no los últimos 28 días
    (`/looker/docs/studio/set-report-date-ranges`). La aclaración de la spec fija 2025 frente a 2024
    y la constitución v1.4.1 prohíbe "Auto";
  - por defecto, un control afecta a todos los gráficos de su página, y agrupar componentes limita
    ese alcance (`apply-controls-to-specific-charts`). No se agrupa nada.
- **Alternatives considered**:
  - *Fixed-size list* o *Input box*: la lista desplegable con búsqueda es lo que pide el principio
    VI y ocupa una sola fila;
  - controles de nivel de informe: solo tienen sentido con varias páginas.

## R4. Botón para restablecer y cross-filtering

- **Decision**:
  - un componente Botón con la acción "Reset filters" (tipo *Report actions*), con el texto
    "Restablecer filtros", al final de la franja de controles;
  - cross-filtering activado en el gráfico de entidades, el de instituciones, el mapa y la tabla.
    Las tarjetas lo reciben pero no lo originan.
- **Rationale**:
  - el botón con "Reset filters" existe (`add-buttons`). El Reset de la barra de filtros reinicia los
    controles y los cross-filters, y el Reset de nivel de informe además el orden y los drill-down
    (`add-a-quick-filter`). Al refrescar el informe los controles vuelven a su valor por defecto
    (`explore-your-data`);
  - el cross-filtering se activa por gráfico en DATA, *Chart interactions*, viene activo por
    defecto en la mayoría de conectores y no existe en las tarjetas
    (`/looker/docs/studio/chart-cross-filtering`).
- **Por verificar al construir**: que el botón devuelve el control de fechas a 2025 y quita los
  cross-filters. Si no devuelve las fechas, la alternativa que cumple FR-011 es un botón de tipo
  *Navigation* que abre el enlace del propio informe en la misma pestaña: al recargar el informe,
  los controles vuelven a su valor por defecto (`explore-your-data`). Se registra cuál quedó.

## R5. Tarjetas: unidades, números compactos y comparación con ▲▼

- **Decision**:
  - tres tarjetas (*Scorecard*) con la métrica, "Compact numbers" y la precisión de la
    especificación;
  - la unidad va en el nombre visible de la tarjeta o en un texto debajo ("millones de pesos
    (MXN)", "millones de piezas", "pesos (MXN) por pieza");
  - *Comparison type*: Period; *Comparison date range*: Previous year; cambio en porcentaje;
  - colores de cambio: positivo `#0072B2` y negativo `#B34700` (R10), ambos con contraste de texto
    sobre blanco.
- **Rationale**:
  - opciones de la tarjeta: compact numbers, decimales, tipo de comparación, "Show absolute change",
    colores de cambio positivo y negativo, "Missing data" (`scorecard-reference`);
  - presets de comparación Previous period, Previous year, Fixed y Advanced
    (`/looker/docs/studio/set-report-date-ranges`). Previous year compara el primer trimestre de
    2025 con el de 2024, con la misma estacionalidad, mientras que Previous period lo compararía con
    el último trimestre de 2024.
- **Riesgo**: la documentación describe el cambio solo con color y no menciona flechas
  (`scorecard-reference`). Se verifica al construir. Los colores de cambio están separados para la
  visión con daltonismo (`#0072B2` frente a `#B34700`, ΔE 22.5 en protanopia según
  `validate_palette.js`, R10), pero tienen una claridad parecida (5.19:1 y 5.50:1 sobre blanco), así
  que en escala de grises no se distinguen. Si la tarjeta no dibuja ▲▼, la alternativa (decisión del
  dueño en el análisis del 2026-10-08) es:
  - un campo calculado de texto por tarjeta en la fuente, por ejemplo para el importe
    `CASE WHEN SUM(IF(ANIO = 2025, IMPORTE, 0)) >= SUM(IF(ANIO = 2024, IMPORTE, 0)) THEN "▲" ELSE "▼" END`,
    mostrado en una tarjeta de texto pequeña junto al cambio;
  - como ese campo compara años fijos, su componente se agrupa aparte del control de fechas (las
    listas desplegables lo siguen filtrando) y el tablero dice junto a él "▲▼ compara 2025 con 2024"
    como excepción visible (FR-010);
  - si Data Studio no admite agregados dentro del `CASE`, se para y se consulta al dueño antes de
    otra alternativa.
- **Previous year**: los ejemplos oficiales muestran las mismas fechas de calendario un año antes
  (del 26 de diciembre de 2018 al 1 de enero de 2019 se compara con el 26 de diciembre de 2017 al
  1 de enero de 2018), no 365 días (`/looker/docs/studio/set-report-date-ranges`). Es el mismo
  periodo de referencia que calcula `make bq-dashboard`.
- **Por verificar al construir**: qué muestra la comparación cuando el periodo de referencia no tiene
  datos (se configura "Missing data" en "-" si aplica) y cómo trata el 29 de febrero.

## R6. Gasto por entidad: barras horizontales

- **Decision**: *Bar chart* horizontal, dimensión Entidad, métrica Importe, orden por Importe
  descendente, "Number of bars" 32 con "Group others" desactivado, "Show data labels" con números
  compactos, eje con mínimo 0, un solo color (`#0072B2`), sin leyenda, cross-filtering activo.
- **Rationale**:
  - opciones de orientación, Top N, "Group the rest as 'Others'" (activado por defecto), etiquetas,
    mínimo del eje y color único (`bar-chart-and-column-chart-reference`). No existe una opción
    "empezar en cero" para un solo eje, así que el mínimo se fija en 0;
  - las barras ordenadas por valor y desde cero son la recomendación de la guía de visualización
    del Government Analysis Function del Reino Unido y de Few (R13);
  - el nombre más largo es "Veracruz de Ignacio de la Llave" (31 caracteres), que cabe sin rotar en
    la columna de 500 px de la rejilla con letra de 12 px (lo comprobó la maqueta).
- **Alternatives considered**: mostrar solo las 10 primeras entidades, que ocultaría 22 (FR-016).

## R7. Participación por institución: porcentaje del total

- **Decision**: *Bar chart* horizontal, dimensión Institución, métrica Importe con *Comparison
  calculation* "Percent of total", orden descendente, "Group others" desactivado, etiquetas de datos
  en porcentaje con un decimal, un solo color, cross-filtering activo.
- **Rationale**: "Percent of total" se configura en la métrica del gráfico y no es compatible con
  "Group others" (`add-comparison-metrics-and-running-totals`). Es la única forma de mostrar el % sin
  repetir lógica: un porcentaje del total no se puede calcular por fila en la fuente. Con 7
  instituciones, el pie queda prohibido por el principio VI (máximo 5).
- **Nota sobre FR-004**: el porcentaje es una configuración del gráfico y no un campo de la fuente.
  Los nombres, tipos y agregaciones siguen viniendo de la fuente, y el plan lo declara como
  apartamiento en *Complexity Tracking*.
- **Por verificar al construir**: la página de cálculos de comparación no dice qué gráficos admiten
  "Percent of total". Si el gráfico de barras no lo admite, la alternativa es una *Table* con
  Institución y la métrica Importe en "Percent of total" mostrada como columna de tipo "Bar"
  (`table-reference`), ordenada de mayor a menor, con el % visible y en las mismas coordenadas.

## R8. Top 10 molécula-fabricante: tabla

- **Decision**: *Table* con dimensiones Molécula y Fabricante y métricas Piezas, Importe y Precio
  Promedio, orden por Importe descendente con orden secundario por Molécula, "Top N" con 10 filas y
  "Group others" desactivado, números alineados a la derecha, sin paginación, cross-filtering
  activo. Título "Top 10 pares molécula-fabricante por importe".
- **Rationale**: Top N con "Top rows" desactiva la paginación, "Alignment" aplica a las columnas de
  tipo Number y hay orden secundario (`table-reference`).
- **Definición de "Top 10 de moléculas"** (decisión del dueño en el análisis del 2026-10-08): son
  los 10 pares molécula-fabricante con más importe, como fija el principio VI. Una molécula puede
  aparecer varias veces: en 2025 las 10 filas tienen 6 moléculas distintas. La definición va en el
  título, en `docs/dashboard.md` y en la trazabilidad.
- **Empates**: la consulta de verificación ordena por Importe, Molécula y Fabricante. Si Data Studio
  ordena distinto un empate exacto en el décimo lugar, la especificación lo registra. Con los datos
  actuales no hay empates (el décimo par tiene 279.5 M y el undécimo menos).

## R9. Mapa: Geo chart con `ENTIDAD_ISO` y la prueba de `MX-CMX`

- **Decision**: *Geo chart* con dimensión `ENTIDAD_ISO` (Country subdivision, 1st level), zoom en
  México, métrica Importe, escala de un solo tono (mínimo `#DCEBF5`, máximo `#0072B2`), color
  "Dataless" gris claro, leyenda de escala visible y cross-filtering activo. La leyenda y la escala
  continua cumplen el principio VI desde la v1.4.3: en un mapa no caben etiquetas directas en cada
  entidad, la escala codifica el importe y no decora, y el valor exacto está en el tooltip y en las
  barras de entidades (decisión del dueño del 2026-10-08).
- **Rationale**:
  - la subdivisión de primer nivel acepta ISO 3166-2 o el nombre, con zoom de país, y México no está
    entre los países excluidos (`/looker/docs/studio/geo-dimension-reference`,
    `geo-chart-reference`);
  - el Geo chart no dibuja mapa base, así que toda la tinta es de datos (Tufte, R13). Google Maps
    añade calles y relieve que no informan;
  - el sombreado es la tarea perceptiva menos precisa (Cleveland y McGill, R13), por eso el mapa
    complementa las barras y nunca las sustituye.
- **Prueba de `MX-CMX`** (FR-034), en este orden, parando en la primera que funcione:
  1. Geo chart con `ENTIDAD_ISO` tal cual. Éxito si Ciudad de México tiene color y tooltip;
  2. campo calculado en la fuente, "Entidad ISO para mapa" =
     `CASE WHEN ENTIDAD_ISO = 'MX-CMX' THEN 'MX-DIF' ELSE ENTIDAD_ISO END`, con tipo Country
     subdivision, porque `MX-DIF` es el código anterior a 2016 que algunos catálogos conservan;
  3. Google Maps (área rellena) con `ENTIDAD_ISO` (`google-maps-reference`).
  Cambiar la vista queda como último recurso y exigiría sus chequeos (principio IV).
- **Contraste**: el mínimo de la escala no llega a 3:1 sobre blanco. Lo admite la excepción de WCAG
  1.4.11 porque el mismo dato aparece como texto en las barras de entidades. Los bordes entre
  entidades los dibuja el gráfico.

## R10. Tema, rejilla y colores

- **Decision**:
  - lienzo personalizado de 1600 × 900 px (16:9), modo de visualización "Fit to width", rejilla de
    10 px con "Snap to grid";
  - tema personalizado: fondo `#FFFFFF`, texto `#202124`, texto secundario `#5F6368`, bordes de
    componente `#DADCE0`, color de datos `#0072B2`, acento `#B34700` (solo para el cambio negativo),
    fondo del recuadro de hallazgos `#F1F3F4`;
  - una familia tipográfica, Roboto, en tres tamaños: 26 px (título y valores de las tarjetas),
    14 px (títulos de componentes) y 12 px (todo lo demás);
  - la disposición y las coordenadas son las de la maqueta aprobada el 2026-10-08
    ([data-model.md](data-model.md#rejilla-y-disposición)).
- **Contrastes medidos** con la fórmula de WCAG 2.1:

  | Par | Uso | Contraste | Umbral |
  |---|---|---|---|
  | `#202124` sobre `#FFFFFF` | Texto principal | 16.10:1 | 4.5:1 |
  | `#5F6368` sobre `#FFFFFF` | Texto secundario | 6.05:1 | 4.5:1 |
  | `#202124` sobre `#F1F3F4` | Texto del recuadro de hallazgos | 14.46:1 | 4.5:1 |
  | `#0072B2` sobre `#FFFFFF` | Barras y cambio positivo | 5.19:1 | 3:1 y 4.5:1 |
  | `#B34700` sobre `#FFFFFF` | Cambio negativo | 5.50:1 | 4.5:1 |
  | `#DADCE0` sobre `#FFFFFF` | Bordes decorativos de componentes | 1.37:1 | No aplica: no transmiten datos |
  | `#80868B` sobre `#FFFFFF` | Línea base de los ejes y bordes de controles | 3.68:1 | 3:1 |

- **Rationale**:
  - el tema personalizado define fuente, colores de texto, fondo, bordes, paleta, color de "Others" y
    estilo de cambio positivo y negativo, y es uno por informe (`themes`);
  - Google recomienda usar el color de forma consistente y con significado (`color-your-data`,
    `how-to-color-your-reports`) y una rejilla con *smart guides* para alinear
    (`report-and-page-layout`);
  - el lienzo admite tamaños de hasta 2000 × 10 000 px y el preset "Screen (16:9)"
    (`report-and-page-layout`);
  - `#0072B2` es el azul de Okabe-Ito y el único color de esa paleta, junto con el negro, que llega a
    4.5:1 sobre blanco (R13). El naranja de Okabe-Ito (`#D55E00`, 3.87:1) no llega a 4.5:1 para
    texto, por eso el acento es un naranja más oscuro;
  - la validación de paleta del skill de visualización (`validate_palette.js`) pasa los cinco
    chequeos para `#0072B2` y `#B34700`, con separación CVD ΔE 22.5 (protanopia).
- **Por verificar al construir**:
  - que Roboto está en la lista de fuentes del tema (la documentación no publica la lista). Si no
    está, la fuente sans por defecto del tema, que se registra;
  - el tamaño del valor de las tarjetas: `scorecard-reference` solo documenta el tamaño de la
    etiqueta. Si el valor no se puede fijar en 26 px, se mide el que pone Data Studio y se ajustan
    el título y los demás textos para que el total siga en 3 tamaños.
- **Dimension value colors**: no hacen falta, porque ningún gráfico colorea por categoría. Si se
  añadiera uno, se usaría el mapa de colores por valor del informe (`the-dimension-value-color-map`)
  para que cada categoría tenga el mismo color en todo el informe.

## R11. Formato de números y unidades

- **Decision**: números compactos en las tarjetas y en las etiquetas de las barras, separador de
  miles "," y punto decimal ".", como se usa en México. Los importes se leen en millones de pesos
  ("M").
- **Riesgo**: la documentación no dice qué sufijos usan los números compactos según el idioma. En
  inglés, mil millones es "B", que en español se confunde con "billón" (10^12). Se verifica al
  construir. Si aparece "B", la alternativa es un campo calculado en la fuente, "Importe en millones"
  = `SUM(IMPORTE) / 1000000` con tipo Number, usado en las etiquetas, y la unidad "millones de
  pesos" en los títulos.

## R12. Consultas de verificación y `make bq-dashboard`

- **Decision**:
  - cinco consultas versionadas en `sql/dashboard/`, que leen solo de la vista:
    `kpis.sql` (totales de un periodo), `kpis_por_anio.sql` (totales por `ANIO`, la "consulta por
    año"), `gasto_entidad.sql`, `participacion_institucion.sql` y `top10_molecula_fabricante.sql`;
  - los filtros se pasan como parámetros con nombre: `@fecha_inicio` y `@fecha_fin` (DATE) y un
    arreglo `ARRAY<STRING>` por cada lista desplegable (`@entidades`, `@instituciones`,
    `@grupos_institucionales`, `@grupos_terapeuticos`, `@moleculas`). Un arreglo vacío significa
    "todas", con `ARRAY_LENGTH(@x) = 0 OR columna IN UNNEST(@x)`;
  - un subcomando `python -m warehouse dashboard` y un objetivo `make bq-dashboard`, con variables
    opcionales `DESDE`, `HASTA`, `ENTIDAD`, `INSTITUCION`, `GRUPO_INSTITUCIONAL`,
    `GRUPO_TERAPEUTICO` y `MOLECULA` (listas separadas por comas);
  - el programa calcula el periodo de referencia (las mismas fechas un año antes), ejecuta `kpis.sql`
    dos veces y las demás una vez, cada una con dry run previo, labels y el límite de
    `.bigqueryrc`, imprime las cifras con el formato del tablero y comprueba cuatro cifras cruzadas
    (D1 a D4, [contracts/verificacion-sql.md](contracts/verificacion-sql.md)).
- **Rationale**:
  - las listas desplegables admiten selección múltiple, y un arreglo la reproduce. El arreglo vacío
    significa "todas". El tipo `ARRAY<T>` se pasa con `--parameter='nombre:ARRAY<STRING>:["a","b"]'`
    (`docs.cloud.google.com/bigquery/docs/parameterized-queries`);
  - las dos páginas oficiales no coinciden sobre NULL: `parameterized-queries` dice "A query
    parameter value can't be NULL" y la referencia de `bq` dice que `NULL` en `--parameter`
    "specifies a null value" (`docs.cloud.google.com/bigquery/docs/reference/bq-cli-reference`).
    El diseño no depende de NULL;
  - ninguna de las dos páginas documenta el arreglo vacío `[]`. El primer dry run de T016, que no
    factura, lo comprueba. Si `bq` lo rechaza, la alternativa es pasar `NULL` con el tipo
    `ARRAY<STRING>` y escribir el filtro como `@x IS NULL OR columna IN UNNEST(@x)`;
  - el programa `warehouse` ya construye `--parameter` (`warehouse/expectations.py`) y ya ejecuta
    dry run y labels (`warehouse/bq.py`), así que no hay dependencias nuevas;
  - ningún valor de los cinco campos de filtro contiene comas (comprobado en los CSV: 139 moléculas,
    22 grupos terapéuticos, 32 entidades, 7 instituciones y 3 grupos institucionales), así que la
    coma sirve de separador. Una prueba lo vigila con los catálogos de referencia del generador;
  - el filtro común se repite en las cinco consultas para que cada archivo se pueda leer y ejecutar
    solo. Una prueba exige que el bloque de filtros sea idéntico en todas.
- **Verificación hecha**: un borrador de `top10_molecula_fabricante.sql` con `UNNEST` de un parámetro
  de arreglo pasa SQLFluff 4.3.0 con `.sqlfluff` sin violaciones.
- **Alternatives considered**:
  - cadena vacía como "todas" (`@entidad = ''`): no admite selección múltiple;
  - una función de tabla o una vista con parámetros: crea objetos nuevos en el dataset sin
    necesidad (principio VIII);
  - comprobar solo a mano en la consola: no deja un registro reproducible (FR-031 a FR-033).

## R13. Teoría de visualización y accesibilidad verificadas

| Regla del principio VI | Fuente | Estado |
|---|---|---|
| Contraste 4.5:1 en texto y 3:1 en texto grande; 3:1 en objetos gráficos; el color no es el único medio | W3C, Understanding WCAG 2.1: SC 1.4.3, 1.4.11 y 1.4.1 (`w3.org/WAI/WCAG21/Understanding/`) | Confirmada. Texto grande es 18 pt o 14 pt en negrita. 1.4.11 admite excepción si el dato está también como texto |
| Fórmula de luminancia relativa y ratio de contraste | W3C, glosario de WCAG 2.1 | Confirmada |
| Paleta Okabe-Ito apta para daltonismo | Okabe e Ito, "Color Universal Design", jfly (`jfly.uni-koeln.de/color/`) | Confirmada con matiz: naranja, azul cielo y amarillo no llegan a 3:1 sobre blanco (constitución v1.4.2) |
| Barras mejor que pie y mapas solo como complemento | Cleveland y McGill, "Graphical Perception", JASA 79(387), 1984 | Confirmada: posición y longitud se leen con menos error que ángulo y sombreado |
| Tinta dedicada a los datos y sin decoración | Tufte, *The Visual Display of Quantitative Information* (1983, 2001) | Confirmada por la página oficial del libro |
| Una sola pantalla, sin decoración ni colores de más, zona superior izquierda para lo más importante | Few, "Common Pitfalls in Dashboard Design" (2006), errores 1, 9, 11 y 12 | Confirmada (constitución v1.4.2) |
| Sin doble eje | Few, "Dual-Scaled Axes in Graphs" (2008) | Confirmada |
| Pie solo con 5 categorías o menos, barras desde cero y ordenadas por valor | UK Government Analysis Function, "Data visualisation: charts" | Confirmada |
| Gris más un acento, etiquetas directas, títulos con la conclusión | Knaflic, *Storytelling with Data* (2015) y blog de storytellingwithdata.com | Confirmada. Los títulos descriptivos más el recuadro de hallazgos son la adaptación a títulos fijos (aclaración de la spec) |
| Una familia y 3 tamaños o menos | Guía de diseño de dashboards de Oracle | Convención sin fuente académica. Se mantiene |

## R14. Construcción con Claude in Chrome y comprobación sin sesión

- **Decision**:
  - Claude construye el informe en el Chrome del dueño con Claude in Chrome, sobre su sesión de
    Google, siguiendo [contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md)
    y el orden de [quickstart.md](quickstart.md), con una captura después de cada componente;
  - Claude pide confirmación antes de: crear la fuente con sus credenciales, aceptar términos o
    avisos de Data Studio, compartir el informe y cambiar permisos;
  - la comprobación sin sesión la hace Claude en el navegador integrado de la app, que no comparte
    perfil ni sesión con Chrome, y el dueño la repite en una ventana de incógnito de Chrome.
- **Rationale**: en incógnito las extensiones solo funcionan si el usuario activa "Allow in
  Incognito" en `chrome://extensions` (ayuda de Chrome Enterprise,
  `support.google.com/chrome/a/answer/13130396`). Cambiar esa configuración queda fuera de lo que
  Claude hace por su cuenta. El enlace compartido permite ver el informe sin cuenta de Google
  (`/looker/docs/studio/ways-to-share-your-reports`).

## R15. Especificación escrita del dashboard

- **Decision**: `docs/dashboard.md`, en español y con el principio IX, con las secciones que fija
  [contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md): fuente, campos,
  tema y contrastes, rejilla, controles, tarjetas, gráficos, recuadro de hallazgos, comportamientos
  verificados en el producto, verificación contra el SQL y enlace de lectura.
- **Pruebas locales**: `tests/docs/test_dashboard_spec.py` comprueba que la tabla de campos cubre
  las 22 columnas de la vista, que cada contraste declarado coincide con la fórmula de WCAG y supera
  su umbral, y que no hay más de tres tamaños de letra.
- **Rationale**: el principio VIII exige la especificación porque Data Studio no se versiona como
  código. Las pruebas convierten SC-004 y SC-006 en algo que se comprueba sin abrir Data Studio.

## R16. Costo y disponibilidad

- **Decision**: no se añaden vistas materializadas, BI Engine ni extracts. El README documenta que
  las consultas del tablero no pasan por `.bigqueryrc`, que las limita la cuota diaria del proyecto
  y que se pueden atribuir con las labels que Data Studio pone en cada job.
- **Rationale**:
  - Google recomienda BI Engine y vistas materializadas para vistas con cálculos pesados
    (`bigquery-performance`, `improve-performance`). Esta vista es un join de 300 000 filas con
    columnas de pocos MB, y la constitución exige una necesidad medida antes de introducirlas
    (principio III, YAGNI);
  - cada job de Data Studio lleva las labels `requestor` (`looker_studio`),
    `looker_studio_report_id` y `looker_studio_datasource_id`
    (`docs.cloud.google.com/bigquery/docs/visualize-looker-studio`);
  - la caché compartida de *Owner's credentials* y la frescura de 12 horas reducen las consultas
    repetidas (R1).

## R17. Contenido del recuadro de hallazgos

- **Decision**: tres conclusiones del estado inicial (2025, sin otros filtros), tomadas de la salida
  de `make bq-dashboard`, cada una con su cifra y, si refleja un patrón del generador, con esa
  advertencia. El borrador de la maqueta: el IMSS concentra el 38.7 % del importe (patrón inyectado);
  la insulina glargina es la molécula con más importe (17.4 %) y su primer fabricante cobra unos
  1 413 pesos por pieza frente a 694 del segundo; el estado de México lidera las entidades con el
  11.6 %.
- **Rationale**: aclaración de la spec (títulos descriptivos más recuadro) y principio VII (cifras
  que coinciden con el SQL). Los dos hallazgos del documento de entrega son de la feature 006 y
  pueden reutilizar estos.

## R18. README y matriz de trazabilidad

- **Decision**: una sección "Dashboard" en el README (fuente, verificación con `make bq-dashboard`,
  qué ejecuta el dueño, enlace de lectura) y una sección "Fase 3: dashboard" en
  `docs/trazabilidad.md` con una fila por control, KPI y visualización de los requisitos.
- **Rationale**: principio I (cobertura del 100 %) y principio VIII (reproducibilidad).
