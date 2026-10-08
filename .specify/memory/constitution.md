# Constitución de Farma Analytics BigQuery

> Prueba técnica de Analista de Datos & BI: compras públicas de medicamentos en México, modeladas
> en Google BigQuery y visualizadas en Data Studio (antes Looker Studio).
> Las palabras MUST, MUST NOT, SHOULD y MAY se usan según RFC 2119 y se dejan en inglés para que las
> puertas de Spec Kit no sean ambiguas. Cada regla se puede verificar.

## Principios Fundamentales (Core Principles)

### I. Fidelidad al Contrato de la Prueba Técnica (NO NEGOCIABLE)

El documento `docs/technical-test-confidencial.pdf` es el contrato. Cada artefacto existe para
cumplir un requisito o un criterio de evaluación de ese documento.

- Los nombres impuestos MUST usarse exactamente, con las mismas mayúsculas, porque BigQuery
  distingue mayúsculas en los nombres de tabla:
  - dataset `farma_analytics`;
  - tablas `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO`;
  - vista `v_compras_farma_completa`.
- Ninguna herramienta MAY añadir prefijos o sufijos ni cambiar las mayúsculas. Por ejemplo,
  `schemaSuffix`, `tablePrefix` y `namePrefix` de Dataform quedan prohibidos en el entorno
  entregable.
- Cada tabla MUST contener exactamente los campos que lista la prueba, con esos mismos nombres.
- La vista MUST unir `COMPRAS` con `CLUE_CAT` (vía `CLUE`) y con `CUADRO_BASICO` (vía `CLAVE`)
  mediante `INNER JOIN`.
- Las consultas analíticas MUST responder las tres preguntas comerciales:
  - las 5 moléculas con más `IMPORTE`;
  - la institución y la entidad con mayor volumen de compra;
  - el precio promedio por pieza (`SUM(IMPORTE) / SUM(PIEZAS)`) por molécula y fabricante.
- El dashboard MUST implementar todos los controles, KPIs y visualizaciones de la Fase 3.
- Los cuatro entregables MUST existir:
  1. el archivo `.sql` con la DDL, la vista y las consultas;
  2. un enlace al dashboard con permiso de lectura;
  3. un documento con 2 hallazgos comerciales clave;
  4. un video de pantalla que explique todos los pasos.
- Las ambigüedades de la prueba MUST resolverse con una definición explícita y documentada. Por
  ejemplo: si "volumen de compra" significa `IMPORTE` o `PIEZAS`; qué `FABRICANTE` se usa; si
  "institución y estado" se evalúa en combinación o por separado. Cuando sea barato, SHOULD
  presentarse ambas interpretaciones.
- MUST existir una matriz de trazabilidad (`docs/trazabilidad.md`) que relacione cada requisito o
  criterio con su artefacto y su verificación. Su cobertura MUST ser del 100 % antes de entregar.

**Justificación**: la evaluación es una rúbrica cerrada: SQL & BigQuery 40 %, Modelado 20 %,
Dashboard 30 %, Visión comercial 10 %. Cualquier desviación del contrato resta puntos, aunque la
solución alternativa sea técnicamente mejor.

### II. GoogleSQL Ejemplar y Tipado Estricto (NO NEGOCIABLE)

El SQL es el criterio de mayor peso: "correcta definición de tipos de datos, uso adecuado de alias,
sintaxis limpia en INNER JOIN y agrupaciones (GROUP BY, SUM, AVG)". Cada sentencia debe poder
leerse como referencia de estilo.

**Tipos de datos**

- Tipos obligatorios:
  - `FECHA` MUST ser `DATE`.
  - `PIEZAS` MUST ser `INT64`.
  - `IMPORTE` MUST ser `NUMERIC`, que Google documenta como exacto y apto para cálculos financieros.
- Tipos prohibidos para dinero:
  - `FLOAT64` MUST NOT usarse.
  - `NUMERIC(p, s)` parametrizado MUST NOT usarse, porque redondea al escribir y las vistas no lo
    admiten.
- Las claves `CLUE`, `CLAVE` y `COD_PROVEEDOR` MUST ser `STRING`, porque son códigos alfanuméricos
  con ceros a la izquierda. Los atributos descriptivos también son `STRING`.
- El esquema MUST declararse explícitamente. La autodetección de esquema MUST NOT usarse.
- Las columnas obligatorias (claves, `FECHA`, `PIEZAS`, `IMPORTE`) MUST declararse `NOT NULL` en la
  DDL, lo que crea columnas en modo `REQUIRED`.
  - El modo `REQUIRED` solo puede fijarse al crear la tabla: una columna nueva siempre es
    `NULLABLE` o `REPEATED`, y el único cambio de modo permitido es de `REQUIRED` a `NULLABLE`.
  - `CREATE TABLE ... AS SELECT` MUST NOT usarse para las tablas impuestas, porque no propaga
    `NOT NULL`: las columnas resultantes quedan `NULLABLE`.
  - Si se combina una lista de columnas con `AS query_statement`, BigQuery ignora los nombres de la
    consulta y empareja por posición. Por eso el orden MUST revisarse columna a columna.
- Los nombres de columna MUST ser únicos sin distinguir mayúsculas: `Fabricante` y `FABRICANTE` son
  el mismo nombre para BigQuery.
- Las conversiones MUST ser explícitas con `CAST`.
  - Cuando el dato pueda ser inválido se usa `SAFE_CAST` o el prefijo `SAFE.` (por ejemplo
    `SAFE.PARSE_DATE`), contando cuántos `NULL` introdujo. Las pérdidas silenciosas están
    prohibidas.
  - `SAFE_` solo convierte en `NULL` los errores en tiempo de ejecución. Un cast entre tipos no
    convertibles sigue fallando al analizar la consulta.
- Los textos de fecha MUST convertirse con `PARSE_DATE` y un formato explícito que coincida con el
  origen (por ejemplo `PARSE_DATE('%Y%m%d', ...)`), nunca recortando cadenas con `SUBSTR`.
- Los cocientes MUST usar `SAFE_DIVIDE`. El redondeo (`ROUND(x, 2)`) MUST aplicarse solo en la capa
  de presentación, nunca dentro de la vista.

**Dialecto y DDL**

- Todo el SQL del proyecto MUST ser GoogleSQL. Legacy SQL queda prohibido.
  - Una consulta GoogleSQL no puede leer una vista definida en legacy SQL.
  - Desde el 2026-06-01, los proyectos que no usaron legacy SQL entre noviembre de 2025 y junio de
    2026 ya no pueden usarlo.
- El dialecto MUST fijarse por configuración y nunca depender del valor por defecto. La referencia
  del CLI sigue indicando legacy SQL como valor por defecto, mientras que la release note del
  2025-07-08 anuncia GoogleSQL: la documentación se contradice.
  - **En el repositorio**: un `.bigqueryrc` versionado en la raíz es la única fuente de los valores
    por defecto de `bq`.
    - Fija `--location` como flag global.
    - En `[query]` fija `--use_legacy_sql=false` y `--maximum_bytes_billed`. En `[mk]` fija
      `--use_legacy_sql=false`.
    - No incluye el ID de proyecto, que sale de la configuración de `gcloud` o del entorno.
  - El `Makefile` MUST exportar `BIGQUERYRC=$(CURDIR)/.bigqueryrc`. `bq` no lee un `.bigqueryrc`
    del directorio actual: lo busca en el flag `--bigqueryrc`, después en la variable `BIGQUERYRC`
    y por último en `$HOME/.bigqueryrc`.
  - **En el proyecto de GCP**: `default_sql_dialect_option` MUST fijarse en `'only_google_sql'`
    con `ALTER PROJECT ... SET OPTIONS`. Con ese valor BigQuery usa GoogleSQL cuando el job no
    indica dialecto y rechaza cualquier job en legacy SQL, así que la prohibición la impone la
    plataforma.
- Quedan prohibidos:
  - repetir en cada comando los flags que ya fija `.bigqueryrc` (`--use_legacy_sql`,
    `--location`, `--maximum_bytes_billed`), para que exista una sola fuente;
  - depender del `~/.bigqueryrc` personal;
  - fijar el dialecto con los prefijos `#standardSQL` o `#legacySQL`.
- La semántica de la DDL MUST elegirse a propósito:
  - `CREATE` sin modificador falla si el objeto existe;
  - `CREATE OR REPLACE` lo reemplaza;
  - `CREATE ... IF NOT EXISTS` no hace nada si ya existe;
  - `OR REPLACE` e `IF NOT EXISTS` no pueden combinarse.

**Estilo y legibilidad**

- Formato:
  - palabras clave en MAYÚSCULAS e indentación consistente;
  - cada cláusula raíz en su propia línea (`SELECT`, `FROM`, `INNER JOIN`, `WHERE`, `GROUP BY`,
    `HAVING`, `ORDER BY`);
  - `AND` y `OR` al inicio de línea;
  - líneas de 100 caracteres o menos y sin coma final.
- `AS` MUST escribirse siempre, tanto en tablas como en columnas.
- Los joins MUST escribirse como `INNER JOIN ... ON` explícito. Quedan prohibidos los joins con
  coma, el `JOIN` sin calificar y `USING`. La tabla de hechos (`COMPRAS`) va primero y los catálogos
  después.
- En consultas con más de una tabla, cada columna MUST ir calificada con un alias de tabla
  semántico (`compras`, `clue_cat`, `cuadro_basico`). Las letras sueltas (`a`, `b`, `c`) no se
  admiten.
- Las colisiones de nombres MUST resolverse con alias explícitos y descriptivos. `FABRICANTE`
  existe en `COMPRAS` y en `CUADRO_BASICO`, y una vista con columnas duplicadas no es válida.
- `GROUP BY` MUST nombrar las columnas. Quedan prohibidos los ordinales (`GROUP BY 1, 2`) y
  `GROUP BY ALL` en el entregable. Las columnas no agregadas van primero. `HAVING` solo se usa
  para filtrar agregados.
  - Es un criterio de estilo del proyecto: la documentación de BigQuery admite ordinales y no
    recomienda evitarlos.
- `SELECT DISTINCT` MUST NOT combinarse con un `GROUP BY` que ya proyecta todas sus claves de
  agrupación, porque cada grupo ya es una fila única.
- Los alias del `SELECT` MUST NOT usarse en `WHERE`, porque `WHERE` se evalúa antes y solo ve las
  columnas del `FROM`. Para reutilizar una expresión se repite o se calcula en una CTE. Los alias sí
  son visibles en `GROUP BY`, `HAVING` y `ORDER BY`.
- Los agregados que dependen del orden (`STRING_AGG`, `ARRAY_AGG`) MUST llevar `ORDER BY` dentro de
  la llamada, porque sin él el resultado no es determinista. Con `DISTINCT`, la clave de orden debe
  ser la misma expresión agregada.
- `AVG` MUST usarse solo para medias simples con significado de negocio, como el importe promedio
  por transacción. MUST NOT usarse para promediar cocientes.
- Cada CTE MUST tener una sola responsabilidad y un nombre descriptivo, y la consulta termina en un
  `SELECT` final. Las CTE sirven para dar legibilidad; Google aclara que no materializan
  resultados.
- `ORDER BY` MUST aparecer solo en la consulta más externa.
  - El top-N se resuelve con `ORDER BY ... LIMIT`.
  - El top-N por grupo usa funciones de ventana con `QUALIFY`, y el tratamiento de empates (`RANK`
    o `ROW_NUMBER`) se documenta.
- `SELECT *` MUST NOT aparecer en la vista ni en el entregable.
- Cada script MUST llevar un comentario de cabecera, y cada sentencia, la pregunta de negocio que
  responde. Los comentarios explican el porqué, no el qué.
- El entregable MUST usar solo funcionalidades GA de GoogleSQL. La sintaxis pipe (`|>`) MAY
  aparecer solo en un anexo opcional que incluya la consulta equivalente en sintaxis estándar. Las
  funcionalidades en Preview MUST NOT usarse.

**Rendimiento y costo** (según las best practices de Google)

- Prácticas de consulta:
  - leer solo las columnas necesarias y filtrar lo antes posible;
  - agregar antes del join cuando reduzca filas sin cambiar la semántica;
  - usar funciones de ventana en lugar de self-joins;
  - usar UDF en SQL en lugar de JavaScript;
  - usar `LIKE` en lugar de `REGEXP_CONTAINS` cuando baste.
- Cada sentencia MUST validarse con un dry run antes de ejecutarla. El dry run es gratuito, no usa
  slots y devuelve una cota superior de los bytes procesados.
- Los jobs MUST tener un `--maximum_bytes_billed`, fijado en `.bigqueryrc`. Si la estimación
  supera ese límite, la consulta falla sin cobrarse.
- Para explorar datos MUST usarse la vista previa de la consola o `bq head`, que son gratuitas, y
  no consultas. `LIMIT` MUST NOT tratarse como control de costo: en tablas sin clustering no reduce
  los bytes leídos.
- La limpieza y el tipado MUST hacerse una sola vez, en la carga. La vista no repite
  transformaciones costosas (`TRIM`, `REGEXP`, `CAST`) en cada consulta. Google recomienda
  materializar los datos ya transformados en lugar de transformarlos una y otra vez.
- Quedan prohibidas las tablas fragmentadas por fecha (`COMPRAS_YYYYMMDD`). Google recomienda
  particionar en lugar de fragmentar.
- Estas tablas están muy por debajo de ~10 GB por partición y de 64 MB para que el clustering
  compense. Por eso MUST NOT particionarse ni clusterizarse como adorno, y la decisión MUST quedar
  documentada.
  - Si una tabla superara los 64 MB, el clustering usaría como máximo 4 columnas ordenadas por
    prioridad de filtro. Las consultas deben filtrar por la primera columna para aprovechar la poda
    de bloques.

**Verificación**: SQLFluff (`dialect = bigquery`, con la configuración del repositorio) sin
violaciones, dry run sin errores y revisión contra esta lista.

### III. Modelado Semántico Orientado a BI

- Modelo en estrella:
  - `COMPRAS` es la tabla de hechos; su grano es una línea de compra.
  - `CLUE_CAT` y `CUADRO_BASICO` son dimensiones con clave única (`CLUE` y `CLAVE`).
- Cada tabla MUST declarar por escrito su grano (qué representa una fila) y su llave antes de
  crearse.
  - BigQuery no impone las claves primarias: la unicidad es responsabilidad del proyecto.
  - Si una fuente puede traer duplicados, se deduplica de forma explícita sobre la llave (por
    ejemplo con `QUALIFY ROW_NUMBER() OVER (PARTITION BY llave ORDER BY ...) = 1`) y se documenta
    el criterio de desempate.
  - Esta regla es criterio de modelado dimensional: Google documenta la cláusula `QUALIFY`, pero no
    este patrón.
- `v_compras_farma_completa` MUST ser una vista lógica con una lista explícita de columnas. Su grano
  es una fila por cada fila de `COMPRAS` que tiene correspondencia en ambos catálogos. No lleva
  agregaciones, `DISTINCT` ni `ORDER BY`.
- Comportamiento de las vistas lógicas:
  - no almacenan datos: su consulta se ejecuta cada vez que se consulta la vista y se factura por
    los bytes leídos de las tablas base;
  - la caché de resultados (unas 24 horas, sin costo) solo aplica si el texto de la consulta es
    idéntico y las tablas referenciadas no cambiaron;
  - en la documentación una tabla normal MUST NOT llamarse "snapshot", porque *table snapshot* es
    otra función de BigQuery.
- Los nombres de columna de una vista son los nombres de salida de su consulta: el alias explícito
  o, si no lo hay, el nombre de la columna de origen.
  - Toda expresión calculada MUST llevar alias explícito.
  - Se prefieren los alias en el `SELECT` a `view_column_name_list`. Si se usa la lista, debe tener
    exactamente tantos nombres como columnas devuelve la consulta.
- La vista MUST conservar los nombres de columna de la prueba (UPPER_SNAKE_CASE) para que se tracen
  1:1 con el enunciado y con el dashboard. Las columnas derivadas o desambiguadas siguen la misma
  convención con un sufijo semántico, por ejemplo `FABRICANTE_COMPRA` y `FABRICANTE_CATALOGO`.
- La vista y cada una de sus columnas MUST tener descripción (`OPTIONS(description = ...)`). Las
  referencias internas MUST calificarse con el dataset y MUST NOT fijar el ID de proyecto.
- Medidas:
  - `PIEZAS` e `IMPORTE` son aditivas y se exponen sin transformar.
  - El precio promedio por pieza no es aditivo. MUST NOT guardarse por fila ni preagregarse, y MUST
    calcularse al consumir como `SUM(IMPORTE) / SUM(PIEZAS)`: con `SAFE_DIVIDE` en SQL y como campo
    calculado en Data Studio.
- Las derivaciones deterministas por fila útiles para BI MAY vivir en la vista para no repetir
  lógica en el dashboard. Ejemplos: mes, año o código ISO 3166-2 de la entidad.
- Las consultas analíticas MUST leer de `v_compras_farma_completa`. Así el SQL y el dashboard
  comparten una sola capa semántica y dan las mismas cifras.
- Claves `NOT ENFORCED`:
  - Las claves primarias MAY declararse en los catálogos una vez validada su unicidad.
  - Las claves foráneas MUST declararse solo si la integridad referencial está verificada al 100 %.
  - Si hay huérfanos deliberados, las claves foráneas MUST NOT declararse: BigQuery eliminaría el
    join y las consultas devolverían resultados incorrectos.
- Las vistas materializadas, las tablas preagregadas y BI Engine MUST NOT introducirse sin una
  necesidad medida, justificada en *Complexity Tracking*. Google reserva las vistas materializadas
  para consultas costosas y frecuentes, que tienen además costo de mantenimiento y de
  almacenamiento.

**Verificación**:

- `COUNT(*)` de la vista es igual a las filas de `COMPRAS` menos los huérfanos.
- `INFORMATION_SCHEMA` muestra las descripciones.
- La definición de la vista no tiene agregaciones ni `ORDER BY`.

### IV. Calidad de Datos Verificable

- Las reglas de calidad MUST definirse antes de dar por terminada la vista. MUST ejecutarse después
  de cada carga y de cada cambio en la vista:
  - conteo de filas por tabla frente al manifiesto del generador;
  - unicidad de `CLUE` en `CLUE_CAT` y de `CLAVE` en `CUADRO_BASICO`;
  - claves, `FECHA`, `PIEZAS` e `IMPORTE` sin nulos;
  - dominios: `PIEZAS > 0`, `IMPORTE >= 0` y `FECHA` dentro del rango declarado;
  - reconciliación del `INNER JOIN`: filas e importe antes y después, con los huérfanos
    cuantificados;
  - precio unitario implícito (`IMPORTE / PIEZAS`) plausible para cada clave.
- Cada regla MUST tener una única implementación canónica y MUST ejecutarse con un comando
  documentado. La implementación es una assertion de Dataform o una consulta en `sql/checks/` que
  debe devolver 0 filas.
- Un chequeo fallido bloquea la entrega. Queda prohibido ocultarlo con `DISTINCT`, con filtros ad
  hoc o cambiando umbrales sin justificación.
- El generador de datos MUST tener pruebas automatizadas (pytest) de determinismo, integridad
  referencial y rangos.

**Justificación**: un `INNER JOIN` descarta huérfanos sin avisar, y una clave duplicada en un
catálogo multiplica filas e infla `SUM(IMPORTE)`. Sin estos chequeos, las cifras del dashboard no
se pueden defender.

### V. Datos Sintéticos Reproducibles, Realistas y Honestos

- Reproducibilidad del generador (Python):
  - la semilla MUST fijarse en un archivo de configuración;
  - las versiones exactas de las dependencias MUST fijarse (NumPy, Faker, etc.);
  - con la misma semilla y las mismas versiones MUST producir archivos idénticos, verificados con un
    manifiesto SHA-256.
- Formato, una de dos opciones:
  - CSV en UTF-8 sin BOM, con encabezado, fechas `YYYY-MM-DD`, punto decimal y sin separador de
    miles;
  - Parquet con esquema explícito (`date32` → `DATE`).
- Integridad:
  - las claves de los catálogos MUST ser únicas;
  - las claves huérfanas en `COMPRAS` solo se permiten con una tasa explícita en la configuración
    (`orphan_rate`), documentada y medida con la reconciliación del principio IV.
- Realismo:
  - `IMPORTE` MUST calcularse como `PIEZAS` × precio unitario. El precio unitario es el precio base
    por `CLAVE` × un factor por fabricante × ruido. Nunca se genera de forma independiente.
  - Las distribuciones SHOULD tener cola larga, con concentración tipo Pareto en instituciones,
    entidades y moléculas, y SHOULD tener estacionalidad mensual.
  - Las instituciones SHOULD ser reales (IMSS, IMSS-Bienestar, ISSSTE, SEDENA, SEMAR, PEMEX...).
  - `ENTIDAD` MUST usar los 32 nombres oficiales del INEGI.
  - Los formatos de clave (CLUES y claves del Compendio Nacional de Insumos) SHOULD ser
    verosímiles.
  - `MARCA` y `FABRICANTE` MUST ser coherentes entre sí.
- Los datos SHOULD cubrir al menos dos años completos, para que los KPIs puedan compararse año
  contra año.
- El volumen SHOULD bastar para un análisis significativo y quedar muy por debajo de los límites del
  nivel gratuito o del sandbox de BigQuery.
- Honestidad:
  - el README, el subtítulo del dashboard, el documento de hallazgos y el video MUST declarar que
    los datos son sintéticos;
  - los patrones inyectados a propósito MUST documentarse;
  - no se usan datos personales reales.

### VI. Dashboard Claro, Honesto e Interactivo

El dashboard vale el 30 % de la nota: "claridad visual, usabilidad, correcta aplicación de filtros y
elección adecuada de gráficos". Aplica las prácticas oficiales de Data Studio (Looker Studio se
renombró como Data Studio en abril de 2026) y la teoría de visualización de Tufte, Few,
Cleveland & McGill y Knaflic, junto con WCAG 2.1.

**Fuente de datos**

- MUST haber una sola fuente de datos reutilizable (no incrustada), conectada directamente a
  `v_compras_farma_completa`. No se usa una consulta personalizada que repita la lógica de la vista.
- La fuente MUST usar *Owner's credentials*, para que los lectores sin acceso a BigQuery vean los
  datos. La frescura de datos MUST configurarse y documentarse.
- Los campos MUST configurarse en la fuente, no en cada gráfico:
  - nombres de negocio;
  - tipos semánticos: moneda MXN, fecha y *Country subdivision (1st level)* con código ISO 3166-2
    (`MX-XXX`);
  - agregación por defecto correcta: `Sum` en las medidas y `None` en las claves y los textos.
- `Precio Promedio` MUST ser un campo calculado en la fuente, `SUM(IMPORTE) / SUM(PIEZAS)`, protegido
  contra la división entre cero. Queda prohibido usar `AVG` sobre precios por fila.

**Controles e interactividad**

- Controles obligatorios:
  - rango de fechas (`FECHA`);
  - `ENTIDAD`;
  - `INSTITUCION` / `GRUPO_INSTITUCIONAL`;
  - `GRUPO_TERAPEUTICO` / `MOLECULA`.
- Los controles van en una franja común en la cabecera. Son listas desplegables con búsqueda,
  encadenadas en cascada.
- El rango de fechas por defecto MUST cubrir un periodo con datos. *Auto* (últimos 28 días)
  dejaría vacío un tablero de datos históricos.
- Cada control MUST afectar a todos los visuales. Si hay alguna excepción, MUST indicarse en el
  tablero.
- MUST existir un botón para restablecer los filtros, y el cross-filtering MUST estar activo en los
  gráficos.
- La opción "Show top" MUST NOT ocultar valores en los controles.

**KPIs y visualizaciones**

- Tres scorecards: Monto Total Comprado, Total de Piezas Adjudicadas y Precio Promedio General por
  Pieza.
  - Llevan unidades explícitas y números compactos (K, M).
  - Se comparan con un periodo de referencia que tenga datos. El cambio se marca con ▲▼, no solo
    con color.
- Gasto por `ENTIDAD`: barras horizontales ordenadas de mayor a menor, con etiquetas de valor. Un
  mapa MAY complementarlas, pero MUST NOT ser la única representación de totales absolutos, por el
  sesgo de área.
- Participación por `INSTITUCION`: barras horizontales ordenadas, con etiquetas de %. Un pie o un
  donut solo se admite con 5 categorías o menos, mutuamente excluyentes.
- Top 10: tabla con Molécula, Fabricante, Piezas, Importe y Precio Promedio.
  - Ordenada por Importe, de mayor a menor.
  - Números alineados a la derecha, con formato consistente.
  - El título indica el grano (molécula–fabricante).

**Diseño visual**

- Disposición:
  - una página principal sin scroll, en lienzo 16:9;
  - en pirámide invertida: título y controles, después KPIs, desglose y detalle;
  - lectura en F o Z, con la rejilla fijada antes de maquetar y los componentes alineados.
- Alta proporción de tinta dedicada a los datos:
  - sin 3D, sombras, degradados ni fondos con imagen;
  - barras que empiezan en cero y sin doble eje;
  - categorías ordenadas por la métrica.
- Color:
  - un color base y, como máximo, un color de acento por gráfico;
  - paleta categórica de 8 colores o menos, apta para daltonismo (Okabe-Ito o el tema por
    defecto);
  - la misma categoría lleva el mismo color en todo el informe.
- Accesibilidad:
  - contraste WCAG 2.1 AA: al menos 4.5:1 en texto y 3:1 en elementos gráficos;
  - el color nunca es el único canal;
  - una sola familia tipográfica con 3 tamaños o menos;
  - etiquetas directas en lugar de leyendas, y sin texto rotado en los ejes.
- Transparencia:
  - un subtítulo indica la fuente (datos sintéticos), el periodo, la fecha de corte y la definición
    de precio promedio ponderado;
  - los títulos SHOULD comunicar conclusiones; si no lo hacen, un recuadro de "Hallazgos clave"
    MUST resumirlas.

**Compartir**: el dashboard se comparte con "Cualquier persona con el enlace puede ver" o con
permisos de lectura explícitos. MUST comprobarse en una ventana de incógnito sin sesión iniciada.

### VII. Visión Comercial Basada en Evidencia

- Un glosario único de métricas MUST regir el SQL, el dashboard y los documentos:
  - Monto Total = `SUM(IMPORTE)`;
  - Piezas = `SUM(PIEZAS)`;
  - Precio Promedio = `SUM(IMPORTE) / SUM(PIEZAS)`.
- Cada hallazgo comercial (se piden 2 y se pueden dar más) MUST incluir:
  - una afirmación cuantificada (monto, % o comparación);
  - la consulta SQL que lo reproduce sobre la vista;
  - el estado de filtros del dashboard en el que se ve;
  - la implicación o acción recomendada para un laboratorio farmacéutico. Por ejemplo:
    concentración de mercado, dispersión de precios, instituciones objetivo o participación de la
    competencia.
- Con los mismos filtros, las cifras MUST coincidir en el SQL, el dashboard y el documento.
- Los hallazgos MUST salir de consultar los datos, no de reformular los parámetros del generador.
  Si un hallazgo refleja un patrón inyectado a propósito, MUST indicarlo.

### VIII. Simplicidad, Reproducibilidad y Seguridad

- YAGNI: se usa el mínimo de herramientas que cumple la prueba. Cualquier componente extra MUST
  justificarse en *Complexity Tracking*: Terraform, dbt, Composer, un repositorio Dataform en GCP,
  vistas materializadas, BI Engine, particionado o clustering.
- Todo es código versionado:
  - el generador, los esquemas, los scripts de carga, el SQL y los chequeos;
  - una especificación escrita del dashboard (campos, controles, gráficos y tema), porque Data
    Studio no se versiona como código.
- Reproducibilidad: desde un clon limpio, `README.md` y un `Makefile` MUST permitir regenerar los
  datos, cargarlos, validarlos y desplegar el SQL, con un comando por etapa. El video sigue ese
  mismo recorrido.
- Seguridad:
  - autenticación con ADC (`gcloud auth application-default login`);
  - claves de cuenta de servicio, archivos `.env` y credenciales MUST NOT versionarse; solo se
    versiona `.env.example`;
  - el ID de proyecto se toma de la configuración y nunca va fijo en el código;
  - el PDF confidencial de la prueba MUST NOT versionarse, publicarse ni reproducirse literalmente.

### IX. Escritura Humana en la Documentación

La documentación que leen personas MUST sonar escrita por una persona: concreta, con criterio y sin
las marcas que delatan texto generado por IA.

**Alcance**

- La regla aplica a:
  - `README.md` y los ADR (`docs/decisiones/`);
  - el documento de hallazgos, el diccionario de datos y la especificación del dashboard;
  - el guion del video;
  - los comentarios dentro de los `.sql` entregables;
  - las descripciones de PR y el cuerpo de los mensajes de commit.
- La regla NO aplica a los artefactos de Spec Kit (esta constitución, specs, planes, tareas y
  checklists) ni a los archivos de configuración. Esos documentos mantienen su formato estructurado
  de plantilla.

**Puntuación y símbolos prohibidos en prosa**

- La raya (`—`) y la semirraya (`–`) MUST NOT usarse para incisos ni para rematar una idea. El
  guion suelto (` - `) tampoco puede usarse como si fuera una raya.
- El punto y coma (`;`) MUST NOT usarse para unir ideas.
- Las ideas MUST unirse con:
  - conectores;
  - oraciones subordinadas ("que", "donde", "cuando");
  - comas o paréntesis cuando el inciso es real.
- Partir cada idea en una frase corta separada por un punto MUST NOT ser el sustituto. Ese estilo
  también es un perfil típico de los modelos.
- Quedan prohibidos en la prosa y en los títulos:
  - emojis;
  - flechas (`→`) y símbolos decorativos (`✅`, `★`, `•`);
  - caracteres de dibujo de cajas.
- Los dos puntos MUST NOT usarse para anunciar una "revelación" ("La conclusión es clara: ...").
  Sí se usan para enumerar, definir o citar.
- Las comillas MUST ser rectas (`"..."`) o latinas (`«...»`), sin mezclarlas, y nunca las comillas
  curvas inglesas.
- Las negritas solo se usan para una advertencia real.

**Vocabulario y muletillas prohibidos**

- Fórmulas de relleno: "cabe destacar", "cabe señalar", "es importante señalar", "es fundamental
  tener en cuenta", "vale la pena mencionar", "sin lugar a dudas".
- Aperturas genéricas: "en el mundo actual", "en el panorama actual", "en la era digital", "en un
  entorno cada vez más...", "en el dinámico mundo de".
- Verbos de moda y calcos del inglés: "adentrarse", "sumergirse", "profundizar en", "explorar"
  (como en "en este documento exploraremos"), "potenciar", "desbloquear el potencial", "navegar
  por", "subrayar", "resaltar", "aprovechar" (calco de *leverage*), "fomentar".
- Cuantificadores vagos: "un amplio abanico", "una amplia gama", "un sinfín de".
- Adjetivos inflados: "robusto", "holístico", "integral", "transformador", "innovador", "de
  vanguardia", "meticuloso", "intrincado", "invaluable", "sin precedentes", "en constante
  evolución", "multifacético".
- Sustantivos de moda: "sinergia", "tapiz", "panorama" o "paisaje" (calco de *landscape*),
  "testimonio de".
- Calcos y rodeos:
  - "juega un papel clave" o "desempeña un papel crucial";
  - "a nivel de" con el sentido de "en cuanto a" (el DPD lo rechaza);
  - "sirve como", "se erige como" o "constituye" en lugar de "es";
  - "utilizar", "llevar a cabo" o "realizar un análisis" en lugar de "usar", "hacer" o "analizar".
- Cierres mecánicos: "en resumen", "en conclusión", "en definitiva", "en este sentido".
- Excepciones propias del dominio, permitidas porque son términos técnicos: "clave primaria",
  "estimador robusto", "medicamento innovador" (frente a genérico) e "integral" en sentido
  matemático.

**Estructuras retóricas prohibidas**

- El paralelismo negativo ("no es X, es Y") y la fórmula "no solo... sino también".
- La regla de tres por costumbre ("rápido, escalable y seguro").
- El gerundio de posterioridad o las coletillas valorativas ("se depuró la tabla, garantizando la
  calidad").
- Inflar la importancia ("marca un hito", "sienta las bases") en lugar de decir qué cambió y
  cuánto.
- Las atribuciones vagas ("los expertos coinciden", "diversos estudios"). Toda afirmación nombra su
  fuente.
- La apertura genérica y el párrafo final que resume lo ya dicho. El texto empieza por el hallazgo
  y termina cuando se acaba la información.
- Las preguntas retóricas como transición ("¿El resultado? Un aumento notable").
- La sección de "desafíos y perspectivas futuras" de plantilla. En su lugar va una lista de
  limitaciones concretas.

**Formato prohibido en documentos para lectores**

- Un encabezado por cada párrafo.
- Viñetas para algo que en realidad es un razonamiento.
- Listas con una cabecera en negrita seguida de dos puntos (`**Escalabilidad:** ...`).
- Títulos en Title Case. En español solo llevan mayúscula la primera palabra y los nombres propios.
- Emojis en los títulos y separadores `---` entre todas las secciones.
- Tablas de dos o tres filas que cabrían en una frase.
- Párrafos simétricos con frases de la misma longitud.

**Tono prohibido**

- Fórmulas de chat: "¡Excelente pregunta!", "Aquí tienes", "Espero que te sea útil", "Si quieres,
  puedo...".
- Descargos ("según mi última actualización") y la neutralidad por defecto ("podría sugerir",
  "potencialmente") cuando hay datos para tomar postura.
- El tono publicitario ("lleva el análisis al siguiente nivel").
- Restos de herramientas, como marcadores sin rellenar (`[insertar cifra]`), `oaicite`,
  `contentReference` o `utm_source=chatgpt.com`.
- Frases que valdrían para cualquier proyecto ("aporta información valiosa para la toma de
  decisiones").
- Cifras, citas o referencias que no salgan de una consulta o de una fuente que se pueda nombrar.

**Rasgos obligatorios**

- Frases de longitud variada (unas de 5 a 8 palabras, otras de 25 a 35) y párrafos de tamaño
  distinto.
- Cifras con unidad, periodo y origen. Por ejemplo: "el IMSS concentra el 58 % del importe de 2025
  (consulta H1 sobre `v_compras_farma_completa`)".
- Los nombres propios del dominio: tablas, columnas, instituciones y moléculas.
- Voz activa con sujeto. La primera persona del plural está permitida.
- Postura explícita ("no recomendamos X porque...") y limitaciones concretas.
- Un solo término por concepto, sin sinónimos para variar, y verbos simples ("es", "tiene", "usa").
- La razón de cada decisión.
- Como máximo un conector al inicio de frase por párrafo, sin repetir el mismo conector en 300
  palabras.
  - Conectores naturales: "porque", "ya que", "así que", "por eso", "de modo que", "pero",
    "aunque", "en cambio", "mientras que", "cuando", "si", "es decir", "por ejemplo".
  - Conectores que se vuelven muletilla si se repiten: "además", "sin embargo", "no obstante", "por
    otro lado", "por lo tanto", "asimismo".

**Usos permitidos**

- Listas numeradas para pasos reproducibles y viñetas para enumeraciones reales, como parámetros o
  columnas.
- Tablas con datos reales; por ejemplo, el diccionario de datos.
- `;` en SQL, en código y en CSV, y `--` como comentario SQL.
- El guion en:
  - marcadores de lista de Markdown;
  - flags de CLI, YAML y kebab-case;
  - rangos (2024-2025);
  - palabras compuestas (teórico-práctico);
  - fechas ISO y números negativos.
- Los prefijos de Conventional Commits (`feat:`, `fix:`) y los encabezados del README.

**Verificación**

- Un script versionado (`scripts/lint_prosa.sh`) MUST revisar con `ripgrep` la documentación del
  alcance. Antes de revisar, el script quita los bloques de código, el código en línea y las URL.
  En los `.sql` solo revisa los comentarios.
- El script marca:
  - rayas y semirrayas;
  - guiones usados como raya;
  - punto y coma en prosa;
  - emojis, flechas y caracteres de caja;
  - comillas curvas;
  - Title Case en los títulos;
  - listas con cabecera en negrita;
  - restos de herramientas;
  - las muletillas de `scripts/muletillas.txt`.
- Una lectura en voz alta por parte del autor completa la revisión.
- La lista de muletillas se revisa con cada generación de modelos porque caduca.
- El objetivo es escribir bien, no engañar a un detector. Ningún rasgo aislado prueba nada y no se
  introducen errores a propósito.

## Stack Tecnológico y Restricciones de Plataforma

| Ámbito | Decisión |
|---|---|
| Almacén | Google BigQuery (GoogleSQL). Una sola location (por defecto `US`), declarada en la configuración y pasada en cada job. |
| Carga | `bq load` con esquema explícito, o `LOAD DATA` desde Cloud Storage. Scripts idempotentes. |
| Transformación | `sql/farma_analytics.sql`, única fuente de verdad de la DDL, la vista y las consultas. |
| Calidad | Dataform CLI local (SHOULD) para assertions y declarations. SQLFluff (`bigquery`) con pre-commit. Dry run. |
| Generador | Python 3.12 o superior, con versión fijada. NumPy y Faker (`es_MX`) con versión exacta. pytest. |
| Orquestación | `Makefile`, sin Airflow ni Composer, que exporta `BIGQUERYRC` hacia el `.bigqueryrc` versionado (dialecto, location y límite de bytes). El proyecto de GCP usa `default_sql_dialect_option = 'only_google_sql'`. |
| BI | Data Studio conectado a `v_compras_farma_completa`. |
| Estilo de prosa | `scripts/lint_prosa.sh` con `ripgrep` y la lista versionada `scripts/muletillas.txt` (principio IX). |

**Entregable SQL**

- `sql/farma_analytics.sql` MUST ejecutarse de principio a fin en la consola de BigQuery, sin otras
  herramientas. Sus secciones van en este orden:
  1. `CREATE SCHEMA IF NOT EXISTS`, con location, descripción y labels;
  2. `CREATE TABLE IF NOT EXISTS`, con tipos, `NOT NULL` en las columnas obligatorias y
     descripciones;
  3. `CREATE OR REPLACE VIEW`;
  4. las consultas analíticas.
- Re-ejecutar el script MUST NOT destruir datos:
  - queda prohibido `CREATE OR REPLACE TABLE` sobre tablas ya cargadas;
  - no se usa `default_table_expiration`.
- El esquema de cada tabla MUST tener una única definición canónica: la DDL. Si `bq load` necesita
  un esquema JSON, MUST derivarse de la DDL o comprobarse contra ella.

**Dataform**

- Es la capa declarativa de calidad y documentación:
  - CLI local con `@dataform/core` 3.x en versión exacta;
  - `workflow_settings.yaml` en `dataform/`;
  - una `declaration` para cada una de las tres tablas y para la vista;
  - assertions en un dataset aparte (`farma_analytics_assertions`).
- MUST NOT reimplementar la lógica de la vista. Antes de `run` se ejecutan `dataform compile` y
  `dataform run --dry-run`.
- Convertir el SQLX en la fuente de verdad requiere una enmienda. En ese caso, el `.sql` se genera
  y un chequeo falla si difiere del versionado.

**Convenciones de nombres**

- Los objetos impuestos se nombran exactamente como en la prueba.
- Las columnas de origen y de la vista van en UPPER_SNAKE_CASE.
- Los alias de tabla van en snake_case semántico.
- Los objetos auxiliares van en snake_case con prefijo:
  - `v_` para vistas;
  - `stg_` para staging;
  - `farma_analytics_<propósito>` para datasets auxiliares.
- El prefijo de vistas es `v_` porque lo impone la prueba. El prefijo `vw_` es una convención de un
  lab de Google Skills, no de la documentación oficial, y no se usa. La documentación solo exige
  nombres únicos en el dataset y sensibles a mayúsculas.
- `.sqlfluff` MUST reflejar estas convenciones; por ejemplo, ajustando la regla de capitalización
  CP02.

**Operación en BigQuery**

- Labels: máximo 64 por recurso, con claves y valores en minúsculas y sin datos personales.
  - MUST NOT usarse valores volátiles o únicos, como timestamps o IDs de ejecución.
  - Las labels de tablas y vistas no llegan a los datos de facturación. Para atribuir costos, el
    dataset lleva labels (`project`, `env`, `owner`), que cuentan en la facturación de
    almacenamiento, y los jobs del `Makefile` llevan `--label`, que cuenta en la facturación de
    cómputo.
- Expiración:
  - Google recomienda configurar la expiración por defecto en datasets y tablas. En este proyecto
    MAY aplicarse solo a datasets auxiliares o temporales (por ejemplo,
    `farma_analytics_assertions`).
  - MUST NOT aplicarse a `farma_analytics`, porque el dashboard debe seguir disponible durante la
    evaluación.
  - Una tabla que expira se elimina con todos sus datos, aunque puede recuperarse dentro de la
    ventana de *time travel*. Una vista que expira se elimina y no se restaura directamente.
  - `expiration_timestamp` se evalúa al ejecutar la DDL, y `CREATE OR REPLACE` lo vuelve a
    calcular.
- Almacenamiento de largo plazo: una tabla o partición que pasa 90 días sin modificarse baja de
  precio de forma automática, y cualquier escritura reinicia el contador. Por eso las tablas
  cargadas MUST NOT reescribirse sin necesidad. A este volumen el ahorro es marginal.
- Referencias: el dominio canónico de la documentación es `docs.cloud.google.com`. La página
  `estimate-costs` ya no existe y redirige a `best-practices-costs#estimate-query-costs`.

**Fuera de alcance, con la regla que aplicaría**

- Consultas programadas: los datos son estáticos y no hace falta refrescarlos. Si se necesitaran,
  usarían una cuenta de servicio dedicada con permisos mínimos, escritura idempotente y una hora
  que no sea en punto. Las ejecuciones exactamente a la hora en punto pueden dispararse varias
  veces.
- Vistas autorizadas: el dashboard se comparte con las credenciales del propietario, así que no
  hacen falta. Si se necesitaran, la vista autorizada iría en un dataset distinto del de origen y en
  la misma región.
- Seguridad por fila (*row access policies*): no se usa.
  - Si se necesitara, la política se crearía sobre la tabla y no como filtro `SESSION_USER()`
    dentro de una vista. Una vista con ese filtro no protege la tabla de origen si el usuario tiene
    acceso al dataset.
  - El control de acceso se probaría también por la negativa, con una identidad de prueba. Con la
    política, un usuario fuera del `grantee_list` obtiene 0 filas. Sin acceso al dataset, la
    consulta devuelve un error de acceso denegado.

**Costo y disponibilidad**

- Todos los jobs usan dry run, y el límite `--maximum_bytes_billed` viene de `.bigqueryrc`.
- Si se usa el sandbox, MUST documentarse que tablas y vistas expiran a los 60 días, y MUST
  garantizarse que sigan disponibles durante la ventana de evaluación.
- SHOULD preferirse un proyecto con facturación con estos controles:
  - una alerta de presupuesto, que avisa pero no detiene el gasto;
  - una cuota diaria de consultas a nivel de proyecto, que es un tope duro.

**Estructura del repositorio (orientativa)**:

- `generator/`, `data/`, `sql/` (entregable y `checks/`), `dataform/`, `scripts/` y `tests/`;
- `docs/`: hallazgos, diccionario de datos, especificación del dashboard, trazabilidad y decisiones;
- `specs/`: artefactos de Spec Kit.

## Flujo de Trabajo y Puertas de Calidad

- Flujo de Spec Kit: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-analyze` → `/speckit-implement`.
- Las features SHOULD seguir las fases de la prueba: datos sintéticos, carga, SQL y modelado,
  dashboard y entrega.

**Constitution Check**: son las puertas de `/speckit-plan`. Se revisan antes de la investigación y
otra vez después del diseño.

- **G1 Contrato**: ¿se usan los nombres, campos y joins impuestos? ¿La matriz de trazabilidad
  cubre los requisitos afectados?
- **G2 SQL**: ¿los tipos, alias, joins, agrupaciones y estilo cumplen el principio II? ¿Pasan
  SQLFluff y el dry run?
- **G3 Modelado**: ¿se respeta el grano de la vista? ¿Las medidas no aditivas se calculan al
  consumir? ¿Hay una sola capa semántica?
- **G4 Calidad**: ¿cada dato nuevo o modificado tiene chequeos canónicos? ¿Pasa la reconciliación?
- **G5 Datos**: ¿el generador es determinista y realista? ¿Declara que los datos son sintéticos?
- **G6 Dashboard**: ¿están todos los controles, KPIs y visuales requeridos? ¿Cumple las reglas de
  diseño, accesibilidad y compartición?
- **G7 Negocio**: ¿los hallazgos están cuantificados, son reproducibles y coinciden entre
  artefactos?
- **G8 Simplicidad y seguridad**: ¿todo componente extra está justificado? ¿El repositorio está
  libre de secretos y de material confidencial?
- **G9 Escritura**: ¿la documentación para lectores pasa `scripts/lint_prosa.sh` y la lectura en voz
  alta del principio IX?

**Definición de terminado por entregable**

- `.sql`: se ejecuta sin errores en la consola, pasa SQLFluff y los chequeos, y sus comentarios
  pasan el chequeo de prosa.
- Dashboard: abre con datos en una ventana de incógnito, todos los controles funcionan y cumple la
  lista del principio VI.
- Hallazgos: 2 hallazgos con la evidencia que exige el principio VII, en un documento que cumple el
  principio IX.
- README y ADR: cumplen el principio IX.
- Video: recorre el quickstart de principio a fin, con un guion que cumple el principio IX.

**Git**

- Conventional Commits, cambios pequeños y una rama por feature. Los commits MUST NOT contener
  secretos ni el PDF confidencial.
- Todo cambio MUST entrar a `main` mediante un pull request. Los commits y push directos a `main`
  están prohibidos, incluso para cambios de documentación o de gobernanza.
- Los PR MUST integrarse con squash merge, de modo que cada PR queda como un único commit en `main`
  y el historial se mantiene lineal.
  - El título del PR MUST seguir Conventional Commits, porque se convierte en el mensaje del commit
    resultante.
  - La descripción del PR cumple el principio IX.
- Antes de integrar un PR:
  - los chequeos disponibles MUST pasar (SQLFluff, pytest, `scripts/lint_prosa.sh` y dry run);
  - la rama se actualiza con `main` si quedó atrás.
- Después del merge la rama remota se elimina.
- SHOULD configurarse el repositorio para hacer cumplir estas reglas:
  - solo squash merge;
  - borrado automático de ramas;
  - protección de `main`.

## Estándares BigQuery Verificados

Hay 38 estándares compilados del lab "Creating Permanent Tables and Access-Controlled Views in
BigQuery", que Google Skills publicó en diciembre de 2024. Todos se verificaron contra la
documentación oficial el 2026-10-07.

- Leyenda de la columna Estado:
  - **C**: confirmado;
  - **P**: confirmado con matiz;
  - **N**: no está en la documentación oficial (criterio de ingeniería o solo del lab).
- Ninguno resultó contradicho.
- Las rutas son relativas a `docs.cloud.google.com/bigquery/docs/`.

| # | Estándar | Estado | Dónde se aplica | Fuente |
|---|---|---|---|---|
| 1 | CTAS no propaga `NOT NULL` | C | II, tipos | `reference/standard-sql/data-definition-language#column_name_and_column_schema` |
| 2 | Lista de columnas con `AS query` empareja por posición | C | II, tipos | `...data-definition-language#create_table_details` |
| 3 | Sin nombres de columna duplicados, ni con distinto case | C | II, tipos | `schemas#column_names` |
| 4 | No se añade una columna `REQUIRED` a una tabla existente | C | II, tipos | `managing-table-schemas#add_an_empty_column` |
| 5 | `description` en `OPTIONS` de tablas y columnas | C | III | `schemas#column_descriptions` |
| 6 | `NUMERIC` para dinero, no `FLOAT64` | C | II, tipos | `reference/standard-sql/data-types#decimal_types` |
| 7 | `CAST` explícito, `SAFE_CAST` solo para errores en ejecución | P | II, tipos | `reference/standard-sql/conversion_functions#safe_casting` |
| 8 | `PARSE_DATE('%Y%m%d', ...)` para textos de fecha | C | II, tipos | `reference/standard-sql/date_functions#parse_date` |
| 9 | Declarar el grano y deduplicar sobre la llave | N | III | `primary-foreign-keys`, `...query-syntax#qualify_clause` |
| 10 | Semántica de `CREATE`, `OR REPLACE` e `IF NOT EXISTS` | C | II, DDL | `...data-definition-language#create_view_statement` |
| 11 | Dialecto por defecto de la consola y del CLI | P | II, DDL y stack | `introduction-sql#changing_from_the_default_dialect` |
| 12 | GoogleSQL no lee vistas en legacy SQL | C | II, DDL | `views-intro#view_limitations` |
| 13 | Los prefijos `#standardSQL` van antes de la consulta y en su propia línea | P | II, DDL (prohibidos) | `introduction-sql#changing_from_the_default_dialect` |
| 14 | Particionar en lugar de fragmentar por fecha | C | II, rendimiento | `partitioned-tables#dt_partition_shard` |
| 15 | Clustering a partir de 64 MB, con máximo 4 columnas ordenadas | P | II, rendimiento | `clustered-tables#when_to_use_clustering` |
| 16 | Expiración por defecto en datasets y tablas | C | Stack, solo auxiliares | `best-practices-storage#use-expiration-settings` |
| 17 | Almacenamiento de largo plazo tras 90 días sin escritura | P | Stack | `best-practices-costs#store-data-bigquery` |
| 18 | Evitar `SELECT *` | C | II | `best-practices-performance-compute#avoid_select` |
| 19 | Dry run antes de ejecutar | C | II, rendimiento | `best-practices-costs#perform-dry-run` |
| 20 | `maximum_bytes_billed` | C | II, rendimiento y stack | `best-practices-costs#restrict-bytes-billed` |
| 21 | `LIMIT` no reduce costo sin clustering, usar vista previa | P | II, rendimiento | `best-practices-costs#preview-data` |
| 22 | No transformar los mismos datos una y otra vez | C | II, rendimiento | `best-practices-performance-compute#avoid_repeatedly_transforming_data` |
| 23 | Vistas materializadas para consultas costosas y frecuentes | C | III (solo si se mide) | `logical-materialized-view-overview#when_to_use_materialized_views` |
| 24 | La vista lógica ejecuta su consulta en cada lectura | P | III | `views-intro`, `cached-results#cache-exceptions` |
| 25 | Consultas programadas con cuenta de servicio | P | Stack, fuera de alcance | `scheduling-queries#using_a_service_account` |
| 26 | Prefijo `vw_` para vistas | N | Stack, no se usa (`v_` impuesto) | `views#view_naming` |
| 27 | Las columnas de la vista son los alias de salida | P | III | `...data-definition-language#view_column_name_list` |
| 28 | Labels: máximo 64, sin valores volátiles, las de tabla y vista no llegan a facturación | P | Stack | `labels-intro#requirements`, `adding-labels#job-label` |
| 29 | Vistas autorizadas en un dataset separado | C | Stack, fuera de alcance | `create-authorized-views#create_a_dataset_to_store_your_authorized_view` |
| 30 | Las row access policies filtran todas las vías de lectura | P | Stack, fuera de alcance | `using-row-level-security-with-features` |
| 31 | `SESSION_USER()` en una vista no protege la tabla de origen | N | Stack, fuera de alcance | `managing-row-level-security` |
| 32 | Probar el acceso por la negativa | P | Stack, fuera de alcance | `best-practices-row-level-security#test_service_accounts_with_row_access_policies` |
| 33 | `expiration_timestamp` se evalúa al ejecutar la DDL | C | Stack | `...data-definition-language#view_option_list` |
| 34 | Al expirar, la tabla se elimina con sus datos y la vista se elimina | P | Stack | `managing-tables#updating_a_tables_expiration_time`, `managing-views#view-expiration` |
| 35 | Los alias del `SELECT` no son visibles en `WHERE` | C | II, estilo | `reference/standard-sql/query-syntax#select-list_aliases` |
| 36 | Los agregados dependientes del orden necesitan `ORDER BY` | C | II, estilo | `reference/standard-sql/aggregate-function-calls#aggregate_function_call_syntax` |
| 37 | `GROUP BY` por nombre, no por ordinal | N | II, estilo (criterio propio) | `...query-syntax#group_by_col_ordinals` |
| 38 | `DISTINCT` con `GROUP BY` es redundante si proyecta todas las claves | P | II, estilo | `...query-syntax#select_distinct` |

## Gobernanza (Governance)

- **Jerarquía**:
  - el PDF de la prueba define el QUÉ y prevalece sobre todo;
  - esta constitución define el CÓMO y prevalece sobre specs, planes y tareas;
  - si la constitución contradice la prueba, se enmienda la constitución.
- **Enmiendas**: solo se hacen con `/speckit-constitution`, e incluyen un Sync Impact Report, la
  razón del cambio y la fecha de `Last Amended` actualizada.
- **Versionado** (SemVer):
  - MAJOR: se elimina o se redefine un principio de forma incompatible;
  - MINOR: se añade un principio o una sección, o se amplía la guía de forma sustancial;
  - PATCH: aclaraciones de redacción.
- **Cumplimiento**:
  - cada `plan.md` MUST pasar el Constitution Check (G1 a G9);
  - cada violación MUST justificarse en *Complexity Tracking*, indicando la alternativa simple
    que se descartó;
  - `/speckit-analyze` y la revisión final antes de entregar comprueban todas las puertas y la
    matriz de trazabilidad.
- **Guía operativa**: `README.md` y `specs/<feature>/quickstart.md`.
- **Fuentes normativas** (verificadas el 2026-10-07):
  - BigQuery (`docs.cloud.google.com/bigquery/docs/`): query-syntax, best-practices-performance-
    compute, best-practices-costs, best-practices-storage, data-types, data-definition-language,
    primary-foreign-keys, load-statements, introduction-sql, legacy-sql-feature-availability y
    labels-intro. El anexo de estándares verificados detalla cada una.
  - Data Studio: a-typical-workflow, data-credentials, about-calculated-fields, about-controls y
    geo-dimension-reference.
  - Dataform: best-practices-repositories y assertions.
  - SQLFluff, con el dialecto bigquery.
  - Teoría de visualización: Tufte, Few, Cleveland & McGill y Knaflic.
  - Accesibilidad: WCAG 2.1.
  - Escritura humana:
    - Wikipedia, "Signs of AI writing";
    - Kobak et al. (*Science Advances*, 2025) sobre vocabulario en exceso;
    - Alonso Simón et al. (UCM, RAEL 2025) sobre rasgos de GPT en español;
    - el *Diccionario panhispánico de dudas*.

**Version**: 1.2.0 | **Ratified**: 2026-10-07 | **Last Amended**: 2026-10-07
