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
    (`/looker/docs/studio/set-report-date-ranges`). La aclaración de la spec fija 2025 como rango por
    defecto, y la constitución prohíbe "Auto" (la v1.4.1 corrigió la razón);
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
  - la moneda se declara una vez en el subtítulo ("Importes en pesos mexicanos (MXN)"), el valor
    lleva "$" y los nombres dicen la unidad de las piezas, sin repetir la moneda en cada título
    (decisión del dueño del 2026-10-08, ver R11). La escala la pone el sufijo compacto (R11), así
    que la unidad no dice "millones";
  - *Comparison type*: Period; *Comparison date range*: Previous year; cambio en porcentaje con
    la etiqueta "frente al mismo periodo del año anterior";
  - colores de cambio: positivo `#0072B2` y negativo `#B34700` (R10), ambos con contraste de texto
    sobre blanco.
- **Rationale**:
  - opciones de la tarjeta: compact numbers, decimales, tipo de comparación, "Show absolute change",
    colores de cambio positivo y negativo, "Missing data" (`scorecard-reference`);
  - presets de comparación Previous period, Previous year, Fixed y Advanced
    (`/looker/docs/studio/set-report-date-ranges`). Previous period es el mismo número de días
    inmediatamente antes del rango: en el ejemplo oficial, del 25 al 31 de diciembre de 2018 se
    compara con el 18 al 24 de diciembre;
  - Previous year compara las mismas fechas un año antes: 2025 con 2024 completo, y un trimestre
    con el mismo trimestre del año anterior, con la misma estacionalidad. Es la comparación habitual
    en análisis comercial;
  - la segunda ronda de análisis eligió Previous period, pero con 2025 (365 días) y 2024 bisiesto
    el periodo anterior iba del 2 de enero al 31 de diciembre de 2024 y dejaba fuera el 1 de enero,
    con 64.2 M de importe. Al verlo en la tarjeta, el dueño volvió a Previous year (2026-10-08);
  - la contrapartida: con un rango de más de un año, como 2024-01-01 a 2025-12-31, el año anterior
    (2023-01-01 a 2024-12-31) solo tiene datos de 2024 y la tarjeta muestra +109.1 %, que no es
    comparable. Data Studio no permite limitar la duración del rango, así que el subtítulo lo avisa;
  - `make bq-dashboard` calcula el mismo periodo de referencia para que las cifras coincidan.
- **Riesgo**: la documentación describe el cambio solo con color y no menciona flechas
  (`scorecard-reference`). Se verifica al construir. Los colores de cambio están separados para la
  visión con daltonismo (`#0072B2` frente a `#B34700`, ΔE 22.5 en protanopia según
  `validate_palette.js`, R10), pero tienen una claridad parecida (5.19:1 y 5.50:1 sobre blanco), así
  que en escala de grises no se distinguen. Si la tarjeta no dibuja ▲▼, la alternativa (decisión del
  dueño en el análisis del 2026-10-08) es:
  - un campo calculado de texto por tarjeta en la fuente que compara los dos periodos del rango por
    defecto sobre `FECHA` (no sobre `ANIO`, que tiene tipo Year), por ejemplo para el importe
    `CASE WHEN SUM(IF(FECHA >= DATE(2025, 1, 1), IMPORTE, 0)) >= SUM(IF(FECHA >= DATE(2024, 1, 1) AND FECHA <= DATE(2024, 12, 31), IMPORTE, 0)) THEN "▲" ELSE "▼" END`,
    mostrado en una tarjeta pequeña de 60 × 30 px dentro de la esquina inferior derecha de su
    tarjeta (x de la tarjeta + 290, y 220);
  - como ese campo compara periodos fijos, el control de fechas se agrupa (Arrange, Group) con los
    7 componentes de datos y las tres flechas quedan fuera del grupo, de modo que las listas
    desplegables las siguen filtrando y el rango de fechas no. Un texto de 12 px bajo las tarjetas
    dice "▲▼ comparan siempre 2025 con 2024" como excepción visible (FR-010). Esto
    sustituye, solo en este caso, la regla de R3 de no agrupar controles;
  - fuera del rango por defecto la flecha puede no coincidir con el % de la tarjeta, y la excepción
    visible lo advierte;
  - si Data Studio no admite agregados dentro del `CASE`, se para y se consulta al dueño antes de
    otra alternativa.
- **Por verificar al construir**: qué muestra la comparación cuando el periodo de referencia no tiene
  datos (se configura "Missing data" en "-" si aplica) y que el año anterior de 2025 es
  exactamente 2024-01-01 a 2024-12-31. Comprobado el 2026-10-08: la tarjeta da +9.1 %, el cambio
  frente a 2024 completo.

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
  - la maqueta suponía que "Veracruz de Ignacio de la Llave" (31 caracteres) cabía sin rotar en la
    columna de 500 px. En el producto no cabe: Data Studio reserva unas 7 letras para cada nombre,
    sin opción para ampliarlas, aunque el gráfico sea más ancho. Por eso la dimensión es el campo
    calculado "Entidad (abreviatura)", con las abreviaturas oficiales del INEGI (decisión del dueño
    del 2026-10-08). El nombre completo sigue en la lista Entidad y en el mapa.
- **Alternatives considered**:
  - mostrar solo las 10 primeras entidades, que ocultaría 22 (FR-016);
  - tabla con barras con el nombre completo: en 610 px solo caben 19 de las 32 filas y el resto
    necesita desplazamiento dentro de la tabla;
  - código ISO 3166-2 sin "MX-" ("JAL", "CMX"): se conoce menos, y "MEX" y "CMX" se confunden.

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
- **Resultado al construir** (2026-10-08): se aplica la alternativa. El gráfico de barras cortaba
  los nombres largos de las instituciones (el mismo límite de R6), y la tabla los muestra completos.
  Además, "Percent of total" estaba bloqueado en barras y en tabla mientras "Field Editing in
  Reports" estaba desactivado. La documentación incluye el cálculo de comparación entre las
  ediciones de campo de un informe ([edit-fields-in-your-reports](https://docs.cloud.google.com/data-studio/edit-fields-in-your-reports)),
  y con la opción activada el cálculo quedó disponible. El dueño aprobó activarla, y la nota sobre
  FR-004 sigue valiendo: la fuente define nombres, tipos y agregaciones.

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
  "Dataless" `#F1F3F4` y cross-filtering activo. La escala continua cumple el principio VI desde la
  v1.4.3, porque codifica el importe y no decora. La leyenda se planeó, pero en el producto solo
  aparecía con algunos filtros. El dueño decidió quitarla (2026-10-08): el valor exacto está en el
  tooltip y en las barras de entidades.
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
  Resultado (2026-10-08): la opción 1 funciona. Con solo Ciudad de México elegida, el mapa la pinta
  con el importe de la consulta.
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
    4.5:1 sobre blanco (R13). El bermellón de Okabe-Ito (`#D55E00`, 3.87:1) no llega a 4.5:1
    para texto, por eso el acento es un naranja más oscuro;
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

- **Decision** (segunda ronda de análisis, decisión del dueño del 2026-10-08): números compactos
  en las tarjetas y en las etiquetas de las barras, como pide el principio VI, con unidades que no
  repiten la escala. El sufijo compacto ("K",
  "M" o el que use Data Studio en español) pone la escala. Separador de miles "," y punto decimal
  ".", como se usa en México.
- **Dónde va la moneda** (decisión del dueño del 2026-10-08): una sola vez en el subtítulo,
  "Importes en pesos mexicanos (MXN)", y no en cada título. La ONS pide que el subtítulo diga la
  medida, la cobertura y el periodo, sin repetir lo que dice el título, y que el símbolo de la
  moneda vaya junto a la cifra ([ONS, texto de los gráficos](https://service-manual.ons.gov.uk/data-visualisation/guidance/chart-text)).
  La guía de data.europa.eu deja las unidades fuera del título ([data.europa.eu](https://data.europa.eu/apps/data-visualisation-guide/guidelines-for-visualisation-titles)).
  Como todo el tablero usa una sola moneda y no cambia con los filtros, basta con declararla una vez.
- **Riesgo**: la documentación no dice qué sufijos usan los números compactos según el idioma. En
  inglés, mil millones es "B" (14 941.7 M se vería "14.9B"), que en español se confunde con
  "billón" (10^12). Se verifica en la tarea de las tarjetas. Si aparece "B", se para y se aplica la
  alternativa:
  - campos calculados en la fuente "Importe en millones" = `SUM(IMPORTE) / 1000000` y "Piezas en
    millones" = `SUM(PIEZAS) / 1000000`, con tipo Number y sin formato compacto;
  - unidades "millones de pesos (MXN)" y "millones de piezas" en las tarjetas y en los títulos;
  - una enmienda PATCH de la constitución que admita como "número compacto" una cifra corta con la
    escala escrita en la unidad, porque sin formato compacto la regla "números compactos (K, M)"
    quedaría incumplida.
- **Cifras esperadas**: las de [data-model.md](data-model.md#cifras-esperadas-del-estado-inicial)
  están en millones, que es como las imprime `make bq-dashboard`. El tablero las muestra con su
  sufijo compacto y la comparación se hace a la precisión que muestra.

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
  - el programa calcula el periodo de referencia igual que *Previous year* de Data Studio (las
    mismas fechas un año antes, R5), ejecuta `kpis.sql`
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
    y el orden de [tasks.md](tasks.md), con una captura después de cada componente;
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

- **Decision** (decisión del dueño del 2026-10-08): el recuadro "Hallazgos clave (según los
  filtros)" usa variables de resultados de consultas (chips) para que sus cifras sigan a los
  controles:
  - "[institución] compra el [%] del importe.";
  - "Entidad líder: [entidad], con el [%] del importe.";
  - "Molécula líder: [molécula], con el [%] del importe.".
  El recuadro no lleva texto fijo. Una línea que avisara de los patrones del generador hablaría
  siempre del estado sin filtros, aunque las demás cambien (decisión del dueño del 2026-10-08).
  El aviso va en el documento de hallazgos de la feature 006 (principio VII).
- **Rationale**:
  - un texto fijo sigue describiendo el estado para el que se escribió aunque el lector filtre.
    Las guías piden decir el alcance junto al texto o, mejor, generar el comentario desde los
    datos filtrados ([Incorta](https://docs.incorta.com/6.0/concepts-insight-filter),
    [comunidad de Power BI](https://community.fabric.microsoft.com/t5/Desktop/Dynamic-text-box-based-on-filters/m-p/2475443));
  - Data Studio tiene chips desde 2025
    ([query-result-variables](https://docs.cloud.google.com/looker/docs/studio/query-result-variables)).
    La documentación no dice si los controles los filtran, y la prueba en el producto confirmó
    que sí (con Jalisco, la institución líder pasa a Servicios Estatales de Salud, 39,4 %);
  - un chip devuelve una métrica, y admite "Porcentaje respecto al total", así que las frases
    conservan el porcentaje.
- **Alternatives considered**:
  - texto fijo con "(2025, sin otros filtros)": cumplía la constitución, pero el dueño prefirió
    que el recuadro no se quedara atrás al filtrar;
  - el hallazgo de precios de la insulina glargina (Serrato Castro 1,413 y Tamayo 694 pesos por
    pieza) compara dos filas fijas y no tiene versión dinámica. Se sustituye por la molécula
    líder, y la diferencia de precios queda en la tabla del top 10 y para el documento de la
    feature 006.
- **Longitud**: título de 14 px en un cuadro de 420 × 20 y tres líneas de 12 px con
  interlineado de 16 px en otro de 420 × 70. Con los nombres más largos posibles la línea más
  larga mide 386 px de los 404 px útiles.

## R18. README y matriz de trazabilidad

- **Decision**: una sección "Dashboard" en el README (fuente, verificación con `make bq-dashboard`,
  qué ejecuta el dueño, enlace de lectura) y una sección "Fase 3: dashboard" en
  `docs/trazabilidad.md` con una fila por control, KPI y visualización de los requisitos.
- **Rationale**: principio I (cobertura del 100 %) y principio VIII (reproducibilidad).
