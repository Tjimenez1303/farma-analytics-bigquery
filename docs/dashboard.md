# Especificación del dashboard

El dashboard resume las compras públicas de medicamentos de `farma_analytics.v_compras_farma_completa` para el equipo comercial de un laboratorio: cuánto se compra, dónde, qué institución compra y qué fabricantes venden cada molécula. Lo construimos en Data Studio (el nombre de Looker Studio desde abril de 2026), que no guarda los informes como código. Este documento es la definición versionada del informe, con la que se construye, se revisa y, si hiciera falta, se reconstruye. Los datos son sintéticos y cubren del 1 de enero de 2024 al 31 de diciembre de 2025.

## Fuente de datos

El informe usa una sola fuente reutilizable, creada desde la página de inicio de Data Studio con el conector de BigQuery y conectada a la vista `v_compras_farma_completa` como tabla, sin consulta personalizada. Se llama `v_compras_farma_completa (BigQuery)` para que se reconozca la vista de origen. Elegimos una fuente reutilizable porque una incrustada se copia con el informe y sus campos se configurarían dos veces.

La fuente usa las credenciales del propietario (*Owner's credentials*), de modo que un lector sin acceso a BigQuery ve los datos sin poder consultar el dataset. La frescura de datos es de 12 horas, el valor más largo que admite BigQuery, porque los datos no cambian y no tiene sentido repetir consultas antes. La opción "Field Editing in Reports" (en el producto, "Edición de campos de informes") está activada desde el 2026-10-08 por una sola razón: el cálculo "Porcentaje del total" de la tabla de instituciones es una edición del campo dentro del gráfico, y con la opción desactivada Data Studio lo bloquea. Los nombres, tipos y agregaciones siguen definidos solo en la fuente, y ningún otro componente cambia un campo. Solo los editores del informe pueden hacer estas ediciones. El acceso de las visualizaciones comunitarias también, porque el informe no usa ninguna y así ningún componente de terceros lee los datos.

Las consultas que lanza Data Studio no pasan por `.bigqueryrc`. Las limita la cuota diaria del proyecto, y cada una lleva las labels `requestor`, `looker_studio_report_id` y `looker_studio_datasource_id`, que sirven para atribuir su costo.

## Campos

Cada columna de la vista tiene en la fuente un nombre de negocio, un tipo y una agregación por defecto. Los gráficos no cambian nada de esto.

| Columna | Nombre de negocio | Tipo | Agregación | Uso |
|---|---|---|---|---|
| `CLUE` | Clave CLUES | Text | None | Sin uso |
| `CLAVE` | Clave del insumo | Text | None | Sin uso |
| `COD_PROVEEDOR` | Proveedor | Text | None | Sin uso |
| `MARCA` | Marca | Text | None | Sin uso |
| `FABRICANTE_COMPRA` | Fabricante | Text | None | Tabla del top 10 |
| `PIEZAS` | Piezas | Number | Sum | Tarjeta, tabla y campo calculado |
| `IMPORTE` | Importe | Currency (MXN) | Sum | Tarjeta, barras, mapa, tabla y campo calculado |
| `FECHA` | Fecha | Date | None | Control Periodo |
| `ENTIDAD` | Entidad | Text | None | Control y barras de entidades |
| `INSTITUCION` | Institución | Text | None | Control y barras de instituciones |
| `DELEGACION` | Delegación | Text | None | Sin uso |
| `GRUPO_INSTITUCIONAL` | Grupo institucional | Text | None | Control |
| `NIVEL_ATENCION` | Nivel de atención | Text | None | Sin uso |
| `MUNICIPIO` | Municipio | Text | None | Sin uso |
| `DESCRIPCION` | Descripción del insumo | Text | None | Sin uso |
| `MOLECULA` | Molécula | Text | None | Control y tabla del top 10 |
| `GRUPO_TERAPEUTICO` | Grupo terapéutico | Text | None | Control |
| `PRESENTACION` | Presentación | Text | None | Sin uso |
| `FABRICANTE_CATALOGO` | Fabricante de catálogo | Text | None | Sin uso |
| `ANIO` | Año | Number | None | Sin uso |
| `MES` | Mes | Year Month | None | Sin uso |
| `ENTIDAD_ISO` | Entidad ISO | Country subdivision (1st level) | None | Mapa |

El precio promedio por pieza no está en la vista porque no se puede sumar, así que se calcula al consumir con un campo de la fuente.

| Campo calculado | Fórmula | Tipo | Agregación | Uso |
|---|---|---|---|---|
| Precio Promedio | `SUM(Importe) / NULLIF(SUM(Piezas), 0)` | Currency (MXN) | Auto | Tarjeta y tabla del top 10 |
| Entidad (abreviatura) | `CASE Entidad WHEN "Aguascalientes" THEN "Ags." … ELSE Entidad END`, con los 32 pares de la tabla de abreviaturas | Text | None | Etiquetas de las barras de entidades |

El editor de fórmulas nombra los campos por su nombre de negocio, así que `Importe` y `Piezas` son las columnas `IMPORTE` y `PIEZAS` de la vista. El ID del campo calculado es `PRECIO_PROMEDIO`. `NULLIF` devuelve vacío cuando no hay piezas, en lugar de un error. Como la fórmula ya agrega, Data Studio fija la agregación en "Auto" y ningún gráfico puede promediar precios por fila.

El ID de "Entidad (abreviatura)" es `ENTIDAD_ABREVIATURA`. Existe porque Data Studio reserva en las barras horizontales un espacio fijo de unas 7 letras para cada nombre, que no crece con el ancho del gráfico: "Veracruz de Ignacio de la Llave" salía como "Veracr…" y "Ciudad de México" se partía en tres líneas montadas sobre la barra siguiente. Las abreviaturas son las oficiales del INEGI, del campo `nom_abrev` de su Catálogo Único de Claves Geoestadísticas (servicio `gaia.inegi.org.mx/wscatgeo/v2/mgee/`, consultado el 2026-10-08). El nombre completo sigue en la lista Entidad, en la vista y en el mapa.

| Clave INEGI | Entidad | Abreviatura |
|---|---|---|
| 01 | Aguascalientes | Ags. |
| 02 | Baja California | BC |
| 03 | Baja California Sur | BCS |
| 04 | Campeche | Camp. |
| 05 | Coahuila de Zaragoza | Coah. |
| 06 | Colima | Col. |
| 07 | Chiapas | Chis. |
| 08 | Chihuahua | Chih. |
| 09 | Ciudad de México | CDMX |
| 10 | Durango | Dgo. |
| 11 | Guanajuato | Gto. |
| 12 | Guerrero | Gro. |
| 13 | Hidalgo | Hgo. |
| 14 | Jalisco | Jal. |
| 15 | México | Mex. |
| 16 | Michoacán de Ocampo | Mich. |
| 17 | Morelos | Mor. |
| 18 | Nayarit | Nay. |
| 19 | Nuevo León | NL |
| 20 | Oaxaca | Oax. |
| 21 | Puebla | Pue. |
| 22 | Querétaro | Qro. |
| 23 | Quintana Roo | Q. Roo |
| 24 | San Luis Potosí | SLP |
| 25 | Sinaloa | Sin. |
| 26 | Sonora | Son. |
| 27 | Tabasco | Tab. |
| 28 | Tamaulipas | Tamps. |
| 29 | Tlaxcala | Tlax. |
| 30 | Veracruz de Ignacio de la Llave | Ver. |
| 31 | Yucatán | Yuc. |
| 32 | Zacatecas | Zac. |

Data Studio no deja convertir `ANIO`, un entero en BigQuery, al tipo de fecha Año: haría falta un campo calculado con `PARSE_DATE`. Como el tablero no usa `ANIO`, lo dejamos como número sin agregación, que es lo que evita que se sume por error. La fuente tiene además el campo automático Record Count, que Data Studio añade a toda fuente y que el tablero no usa.

## Tema y colores

El fondo es blanco y los datos llevan un solo color, el azul `#0072B2` de la paleta Okabe-Ito, que distingue bien quien tiene daltonismo. El único acento es el naranja oscuro `#B34700`, reservado para un cambio negativo en las tarjetas. Usamos ese naranja y no el bermellón de Okabe-Ito (`#D55E00`) porque el bermellón se queda en 3.87:1 sobre blanco y no alcanza el 4.5:1 de un texto. Ningún gráfico colorea por categoría, así que la misma categoría tiene siempre el mismo color.

| Elemento | Color |
|---|---|
| Fondo del informe y de los componentes | `#FFFFFF` |
| Texto principal | `#202124` |
| Texto secundario (subtítulo, etiquetas de los controles) | `#5F6368` |
| Datos (barras, escala del mapa, cambio positivo, botón) | `#0072B2` |
| Cambio negativo de las tarjetas | `#B34700` |
| Bordes de los controles y líneas de los ejes | `#80868B` |
| Bordes de los componentes | `#DADCE0` |
| Fondo del recuadro de hallazgos y color "Dataless" del mapa | `#F1F3F4` |
| Mínimo de la escala del mapa | `#DCEBF5` |

Los contrastes están medidos con la fórmula de WCAG 2.1. El texto necesita 4.5:1 y los elementos gráficos 3:1. Los bordes de los componentes son decorativos y no transmiten datos. El mínimo de la escala del mapa tampoco tiene umbral, porque el mismo importe aparece como texto en las barras de entidades (WCAG 2.1, criterio 1.4.11).

| Primer plano | Fondo | Uso | Contraste | Umbral |
|---|---|---|---|---|
| `#202124` | `#FFFFFF` | Texto principal | 16.10:1 | 4.5:1 |
| `#5F6368` | `#FFFFFF` | Texto secundario | 6.05:1 | 4.5:1 |
| `#202124` | `#F1F3F4` | Texto del recuadro de hallazgos | 14.46:1 | 4.5:1 |
| `#0072B2` | `#FFFFFF` | Barras, cambio positivo y texto del botón | 5.19:1 | 4.5:1 |
| `#B34700` | `#FFFFFF` | Cambio negativo | 5.50:1 | 4.5:1 |
| `#80868B` | `#FFFFFF` | Bordes de los controles y líneas de los ejes | 3.68:1 | 3:1 |
| `#636466` | `#FFFFFF` | Etiqueta de comparación de las tarjetas (color fijo de Data Studio) | 5.92:1 | 4.5:1 |
| `#202124` | `#ECF3FE` | Encabezado de las tablas | 14.43:1 | 4.5:1 |
| `#202124` | `#F8F9FB` | Filas alternas de las tablas | 15.28:1 | 4.5:1 |
| `#0072B2` | `#F8F9FB` | Barras de la tabla de instituciones en filas alternas | 4.92:1 | 3:1 |
| `#DADCE0` | `#FFFFFF` | Bordes de los componentes y marcos de las tarjetas | 1.37:1 | No aplica |
| `#DCEBF5` | `#FFFFFF` | Mínimo de la escala del mapa | 1.22:1 | No aplica |

Todo el informe usa Roboto en tres tamaños. El tema de Data Studio traía Arial por defecto, y lo cambiamos en los estilos principales y en los destacados. Los cuadros de texto llevan relleno izquierdo y superior de 0 px para alinearse con la rejilla.

| Tamaño de letra | Uso |
|---|---|
| 24 px | Título y valores de las tarjetas |
| 14 px | Títulos de los componentes y del recuadro de hallazgos |
| 12 px | Subtítulo, etiquetas, controles, ejes, tablas y texto del recuadro |

## Rejilla, disposición y textos fijos

La página mide 1600 × 900 px (16:9) y se ve en modo "Ajustar al ancho", sin scroll. La navegación entre páginas está oculta porque el informe tiene una sola página. La rejilla es de 10 px con "Snap to grid", con márgenes laterales e inferior de 20 px y superior de 10 px. La disposición sigue el orden de lectura: arriba a la izquierda el título y el periodo, que es lo primero que hay que saber (Few, "Common Pitfalls in Dashboard Design"). Después vienen los controles, las tarjetas, el desglose por entidad e institución y, al final, el detalle del top 10.

| Componente | x | y | Ancho | Alto |
|---|---|---|---|---|
| Título | 20 | 10 | 1560 | 30 |
| Subtítulo | 20 | 40 | 1560 | 30 |
| Marco de Periodo (rectángulo blanco, borde `#80868B`) | 20 | 80 | 230 | 50 |
| Marcos de las tarjetas (rectángulos blancos, borde `#DADCE0`) | 20, 400 y 780 | 140 | 360 | 90 |
| Etiqueta "Periodo" | 20 | 80 | 230 | 20 |
| Control Periodo | 20 | 100 | 230 | 30 |
| Lista Entidad | 260 | 80 | 220 | 50 |
| Lista Institución | 490 | 80 | 220 | 50 |
| Lista Grupo institucional | 720 | 80 | 220 | 50 |
| Lista Grupo terapéutico | 950 | 80 | 220 | 50 |
| Lista Molécula | 1180 | 80 | 220 | 50 |
| Botón Restablecer filtros | 1410 | 80 | 170 | 50 |
| Tarjeta Monto Total Comprado | 20 | 140 | 360 | 90 |
| Tarjeta Total de Piezas Adjudicadas | 400 | 140 | 360 | 90 |
| Tarjeta Precio Promedio General por Pieza | 780 | 140 | 360 | 90 |
| Título del recuadro Hallazgos clave | 1160 | 140 | 420 | 20 |
| Texto del recuadro Hallazgos clave | 1160 | 160 | 420 | 70 |
| Barras de gasto por entidad | 20 | 240 | 500 | 640 |
| Mapa de gasto por entidad | 540 | 240 | 510 | 270 |
| Tabla de participación por institución | 1070 | 240 | 510 | 270 |
| Tabla del top 10 | 540 | 530 | 1040 | 350 |

| Componente | Texto |
|---|---|
| Título | Compras públicas de medicamentos en México |
| Subtítulo | Datos sintéticos generados para este proyecto, del 1 ene 2024 al 31 dic 2025 (fecha de corte). Importes en pesos mexicanos (MXN). El tablero abre con 2025 y el rango se puede cambiar. Las tarjetas comparan con las mismas fechas del año anterior, y con rangos de más de un año el cambio no es comparable. Precio promedio ponderado: importe total entre piezas totales. |
| Etiqueta del control de fechas | Periodo |
| Botón | Restablecer filtros |
| Etiqueta de comparación de las tarjetas | frente al mismo periodo del año anterior |

La tabla del top 10 necesita unos 345 px: filas de unos 29 px, el encabezado y el título. Por eso las tarjetas miden 90 px y no 100, y los gráficos empiezan en y 240. Los espacios entre la franja de controles y las tarjetas, y entre las tarjetas y los gráficos, son de 10 px.

Dos rectángulos de fondo dan a los controles y a las tarjetas el mismo aspecto. El control Periodo no tiene borde propio y queda dentro de un rectángulo blanco de 230 × 50 con borde `#80868B`, del mismo tamaño y color que las cinco listas. Cada tarjeta queda dentro de un rectángulo blanco de 360 × 90 con borde `#DADCE0`, que agrupa título, valor y cambio. Los rectángulos están al fondo, detrás de su componente.

## Controles

Los seis controles ocupan una franja en la cabecera y usan la misma fuente que los gráficos. Por eso se filtran entre sí sin ningún ajuste: al elegir Oncología en Grupo terapéutico, la lista Molécula solo ofrece moléculas de Oncología. Ningún control está agrupado con ningún gráfico, así que cada uno afecta a los siete componentes con datos.

| Control | Campo | Tipo | Valor por defecto | Búsqueda | Selección múltiple | Valores mostrados |
|---|---|---|---|---|---|---|
| Periodo | `FECHA` | Date range control | Fijo, del 2025-01-01 al 2025-12-31 | No aplica | No aplica | No aplica |
| Entidad | `ENTIDAD` | Drop-down list | Todas | Sí | Sí | Hasta 200 (hay 32) |
| Institución | `INSTITUCION` | Drop-down list | Todas | Sí | Sí | Hasta 200 (hay 7) |
| Grupo institucional | `GRUPO_INSTITUCIONAL` | Drop-down list | Todos | Sí | Sí | Hasta 200 (hay 3) |
| Grupo terapéutico | `GRUPO_TERAPEUTICO` | Drop-down list | Todos | Sí | Sí | Hasta 200 (hay 22) |
| Molécula | `MOLECULA` | Drop-down list | Todas | Sí | Sí | Hasta 200 (hay 139) |

El periodo por defecto es un rango fijo y no "Auto". Con BigQuery, "Auto" muestra todo el dataset (2024-2025), que no es el periodo que elegimos para abrir el tablero. Las listas ordenan sus valores de la A a la Z, y el límite de 200 evita que "Show top #" esconda valores bajo "All others". No muestran la métrica junto a cada valor ("Mostrar valores" desactivado), porque la lista sirve para elegir y la cifra ya está en las tarjetas. El texto del botón y de la lista es de 12 px y el borde es `#80868B`.

El botón Restablecer filtros usa la acción "Reset filters" y devuelve todos los controles y los filtros por clic (cross-filtering) a su valor por defecto.

## Tarjetas

| Tarjeta | Métrica | Unidad | Formato del valor | Comparación |
|---|---|---|---|---|
| Monto Total Comprado | Importe | "$" en el valor | Compacto, 1 decimal | Año anterior, cambio en % con 1 decimal |
| Total de Piezas Adjudicadas | Piezas | "Piezas" en el nombre | Compacto, 2 decimales | Año anterior, cambio en % con 1 decimal |
| Precio Promedio General por Pieza | Precio Promedio | "$" en el valor y "por Pieza" en el nombre | Compacto, 2 decimales | Año anterior, cambio en % con 1 decimal |

La moneda se declara una sola vez en el subtítulo, "Importes en pesos mexicanos (MXN)", y no se repite en los títulos. Así lo recomienda la guía de gráficos de la ONS: el subtítulo dice la medida, la cobertura y el periodo, y el símbolo de la moneda va junto a la cifra. Como todo el tablero usa una sola moneda, basta con decirlo una vez.

La comparación es *Previous year*: las mismas fechas un año antes. Con el rango por defecto, 2025 se compara con 2024 completo, y un trimestre se compara con el mismo trimestre del año anterior, con la misma estacionalidad. Cuando el año anterior no tiene datos, como con 2024, la tarjeta muestra "-" ("Missing data"). Con un rango de más de un año la comparación pierde sentido: 2024-2025 se compara con 2023-2024, que solo tiene datos de 2024, y la tarjeta muestra +109.1 %. El subtítulo lo avisa. Antes usábamos *Previous period*, que cuenta los mismos días justo antes del rango, pero con 2025 (365 días) y 2024 bisiesto dejaba fuera el 1 de enero de 2024 (decisión del dueño del 2026-10-08). El sentido del cambio se marca con una flecha hacia arriba o hacia abajo, además del color.

## Gráficos

### Gasto por entidad

Barras horizontales de Importe por Entidad (abreviatura), de mayor a menor, con las 32 entidades y sin agrupar ninguna en "Others". Cada barra lleva su importe como etiqueta en formato compacto con un decimal, en 12 px, `#202124` y a la derecha de la barra, el eje empieza en 0, no hay leyenda y el texto no se rota. La etiqueta tiene fondo blanco: a la barra más larga no le cabe la etiqueta fuera, Data Studio la pone dentro y, sin ese fondo, `#202124` sobre `#0072B2` quedaría en 3.10:1, por debajo de 4.5:1. El color es `#0072B2` y el cross-filtering está activo. Las barras ocupan toda la altura de la columna izquierda porque son la representación principal del gasto por entidad.

### Gasto por entidad en el mapa

Geo chart de México con Entidad ISO como subdivisión de primer nivel y el Importe en una escala de un solo tono, de `#DCEBF5` a `#0072B2`, con el color "Dataless" en `#F1F3F4`, zoom en México, título en 14 px y cross-filtering activo. El importe aparece en el tooltip con el código de la entidad. No lleva leyenda: con "Mostrar leyenda" activado, Data Studio la dibujaba con algunos filtros (por ejemplo, solo Ciudad de México) y no sin filtros, ni al recargar ni al desactivarla y activarla. Para que el mapa se vea igual en cualquier estado, la leyenda está desactivada. Los valores exactos están en las barras y en el tooltip. Complementa las barras y nunca las sustituye: en un mapa coloreado se juzga el tono, que se lee con menos precisión que la longitud de una barra (Cleveland y McGill, 1984).

### Participación por institución, % del importe

Tabla con barras (*Table with bars*) con Institución e Importe con el cálculo "Porcentaje respecto al total", que la columna llama "% del importe". Va de mayor a menor, con las 7 instituciones y sin "Others", y cada fila lleva su porcentaje con un decimal junto a la barra. El encabezado y las filas usan 12 px y no hay números de fila. "Ignorar filtros de lienzo" está desactivado, así que el 100 % es el total filtrado, como en la consulta. No usamos un gráfico circular porque hay más de 5 instituciones.

Es la alternativa de R7. El gráfico de barras cortaba "IMSS-Bienestar" y "Servicios Estatales de Salud" por el mismo límite de ancho de los nombres que las entidades, y la tabla los muestra completos en el mismo espacio.

### Top 10 pares molécula-fabricante por importe

Tabla con Molécula, Fabricante, Piezas, Importe y Precio Promedio, ordenada por Importe de mayor a menor y después por Molécula y Fabricante, con 10 filas y sin paginación. Piezas va como entero con separador de miles, Importe en formato compacto con un decimal y Precio Promedio con dos decimales. Los números van alineados a la derecha. Las columnas Molécula y Fabricante tienen el ancho justo para el nombre más largo ("Laboratorios Marroquín Carrillo, S.A. de C.V."), sin números de fila, con encabezado y filas en 12 px. Las 10 filas coinciden con la consulta en orden, piezas, importe y precio (2026-10-08).

El "Top 10 de moléculas" se entiende como los 10 pares molécula-fabricante con más importe, porque la tabla muestra el fabricante de cada fila. Por eso una molécula puede salir más de una vez: con el rango por defecto, las 10 filas tienen 6 moléculas distintas, porque insulina glargina, trastuzumab, tocilizumab y bevacizumab aparecen con dos fabricantes cada una.

## Recuadro de hallazgos

El recuadro "Hallazgos clave (según los filtros)" resume las conclusiones del tablero y cambia con los controles. Sus cifras son variables de resultados de consultas (*query result variables*, los chips que se insertan con `@` en un cuadro de texto): cada una es una consulta pequeña sobre la misma fuente, y los controles del informe la filtran igual que a los gráficos. Lo comprobamos el 2026-10-08: con Jalisco elegido, la primera línea pasa de "IMSS, 38,7 %" a "Servicios Estatales de Salud, 39,4 %", el mismo valor que la consulta. Así ninguna conclusión queda falsa al filtrar. Por la misma razón el recuadro no lleva texto fijo: el aviso de que los líderes sin filtros (IMSS, México e insulina glargina) son patrones inyectados por el generador va en el documento de hallazgos de la feature 006, como pide el principio VII. El subtítulo ya dice que los datos son sintéticos.

| Línea | Chips | Consulta de cada chip | Valor sin filtros (2025) |
|---|---|---|---|
| "[institución] compra el [%] del importe." | `institucion_lider` y `institucion_lider_pct` | Institución por Importe descendente, fila 1. El porcentaje es Importe con "Porcentaje respecto al total" y formato Percent(1) | IMSS, 38,7 % (la consulta da 38.7062) |
| "Entidad líder: [entidad], con el [%] del importe." | `entidad_lider` y `entidad_lider_pct` | Entidad por Importe descendente, fila 1, con el mismo porcentaje | México, 11,6 % (la consulta da 1 731.1 M de 14 941.7 M) |
| "Molécula líder: [molécula], con el [%] del importe." | `molecula_lider` y `molecula_lider_pct` | Molécula por Importe descendente, fila 1, con el mismo porcentaje | Insulina glargina, 17,4 % |

Los chips tienen fondo transparente y texto `#202124`, para que se lean como parte de la frase. Data Studio deja un pequeño margen alrededor de cada chip, por eso se ve un espacio antes de la coma. El porcentaje de la molécula líder no está en `make bq-dashboard`, que agrupa por par molécula-fabricante. Con todo el rango de la vista el chip da 18,5 %, que coincide con el 18.53 % de la consulta de la feature 004.

El recuadro son dos cuadros de texto con fondo `#F1F3F4` y texto `#202124`: el título en 14 px (420 × 20, sin relleno superior) y las tres líneas en 12 px con interlineado de 16 px y relleno superior de 4 px (420 × 70). Son dos cuadros porque Data Studio no cambia el tamaño de una parte del texto de un cuadro, y no ofrece interlineado de 14 px (salta de 10 a 16). Cada línea cabe en una: con Roboto de 12 px y los nombres más largos posibles ("Servicios Estatales de Salud", "Veracruz de Ignacio de la Llave", "Piperacilina y tazobactam"), la más larga mide 386 px de los 404 px útiles.

## Comportamientos comprobados en el producto

La documentación de Data Studio no aclara algunos puntos. Se comprueban al construir el informe y aquí queda lo que se vio.

| Punto | Resultado |
|---|---|
| La moneda MXN en el tipo Currency | Existe como `MXN - Peso mexicano ($)` (2026-10-08) |
| `NULLIF` sobre un agregado en el campo calculado | Se acepta y el campo se guarda sin errores (2026-10-08) |
| Flechas en la comparación de las tarjetas | Data Studio pone un icono de flecha hacia arriba o hacia abajo junto al porcentaje, así que el sentido no depende solo del color (2026-10-08) |
| Lo que muestra la tarjeta sin datos en el año anterior | Con el Periodo en 2024, cuyo año anterior (2023) no tiene datos, las tres tarjetas muestran "-" en el cambio y ninguna cifra inventada. Los valores (13,7 mil M, 26,71 M y $512,71) coinciden con la fila de 2024 de la consulta por año (2026-10-08) |
| Fechas exactas del año anterior de 2025 | Con *Previous year* las tarjetas dan +9.1 %, +6.9 % y +2.1 %, que es el cambio frente a 2024 completo. Con *Previous period* daban +9.6 %, +7.3 % y +2.1 %, el cambio frente al 2 de enero al 31 de diciembre de 2024 (2026-10-08) |
| Si Restablecer filtros devuelve el rango de fechas por defecto | Sí. Con Jalisco, Oncología y el rango del 1 de enero al 30 de junio de 2025, el botón deja todas las listas en "todos" y el periodo en 2025 (2026-10-08) |
| Orden de los valores con tilde inicial | Data Studio ordena por código de carácter, así que las moléculas que empiezan con "Á" (Ácido fólico, Ácido valproico y otras) salen después de la Z. El cuadro de búsqueda las encuentra igual (2026-10-08) |
| Cascada entre controles | Con Jalisco, Institución ofrece 6 instituciones, sin IMSS-Bienestar, como el SQL. Con Oncología, Molécula solo ofrece moléculas oncológicas. Con "Fuerzas Armadas y PEMEX", Institución ofrece PEMEX, SEDENA y SEMAR (2026-10-08) |
| Sufijo de los números compactos para mil millones | Con el informe en español sale "mil M", por ejemplo "$14,9 mil M". El valor usa coma decimal y el porcentaje de cambio usa punto ("9.6%"), y Data Studio no permite cambiarlo (2026-10-08) |
| Roboto en la lista de fuentes del tema | Está disponible. El tema traía Arial y se cambió (2026-10-08) |
| Tamaño del valor de las tarjetas | La lista salta de 24 a 28 px, sin 26. Usamos 24 px también en el título de la página para seguir con tres tamaños. La línea de comparación queda en 12 px (2026-10-08) |
| Ancho de los nombres en las barras horizontales | Fijo, de unas 7 letras, aunque el gráfico sea el doble de ancho. Sin opción para cambiarlo, y rotar el texto está prohibido. Por eso las barras usan la abreviatura del INEGI (2026-10-08) |
| Etiqueta de la barra más larga | No cabe fuera y Data Studio la pone dentro de la barra. Con fondo blanco en la etiqueta se lee con 16.10:1 (2026-10-08) |
| "Porcentaje del total" con "Field Editing in Reports" desactivado | El control del cálculo de comparación aparece desactivado, en barras y en tabla. Al activar la opción en la fuente queda disponible (2026-10-08) |
| Chips de texto (*query result variables*) y controles del informe | Los controles los filtran como a un gráfico, aunque la documentación no lo dice. Admiten "Porcentaje respecto al total" con "Field Editing in Reports" activado (2026-10-08) |
| Color de la etiqueta de comparación de las tarjetas | Data Studio lo fija en `#636466` y la tarjeta no ofrece opción para cambiarlo. Da 5.92:1 sobre blanco (2026-10-08) |
| Colores por defecto de las tablas | Encabezado en negro sobre `#ECF3FE` y filas alternas en `#F8F9FB`. El texto del encabezado se cambió a `#202124` (2026-10-08) |
| Lectura en escala de grises | Con un filtro de escala de grises temporal en el navegador se leen los valores, el orden de las barras y el sentido de cada cambio, que lleva icono de flecha (2026-10-08) |
| Rango 2024-2025 completo | Las tarjetas muestran $28,6 mil M y 55,25 M, el total de la vista, con +109.1 % frente a 2023-2024, el caso que avisa el subtítulo. Los hallazgos dan IMSS 38,5 %, México 11,2 % e insulina glargina 18,5 %, como las consultas de la feature 004 (2026-10-08) |
| Rango sin datos (2023) | Las tarjetas muestran "-", las tablas "No hay datos", el mapa queda gris y los chips de los hallazgos dicen "No hay datos". Ninguna cifra inventada (2026-10-08) |
| Combinación de filtros sin filas | La cascada la impide: con SEMAR elegida, la lista Entidad solo ofrece las entidades donde compra, y al revés. Por eso el estado vacío solo se alcanza con el Periodo (2026-10-08) |
| Ventana de 1366 px de ancho | Las etiquetas de las 32 entidades, las tarjetas y las tablas se leen (2026-10-08) |
| Modo de visualización sin scroll | Data Studio solo ofrece "Ajustar al ancho" y "Tamaño real" a quien abre el informe. "Ajustar a la pantalla" solo existe en el modo presentación. Con "Ajustar al ancho", la página de 1600 × 900 cabe sin scroll en ventanas de proporción 16:9 o más estrechas. En ventanas más anchas queda un pequeño scroll vertical, y el modo presentación con "Ajustar a la pantalla" la muestra entera (2026-10-08) |
| `MX-CMX` (Ciudad de México) en el mapa | El Geo chart lo reconoce tal cual, sin alternativa. Con solo Ciudad de México en la lista Entidad, el mapa pinta su área con $954.360.378,29, el importe de la consulta (2026-10-08) |
| Leyenda de escala del Geo chart con zoom en México | Con "Mostrar leyenda" activado solo aparece con algunos filtros. Se desactivó (2026-10-08) |

## Verificación contra el SQL

Las cifras del tablero tienen que coincidir con las consultas de [`sql/dashboard/`](../sql/dashboard), que leen la vista con los mismos filtros. `make bq-dashboard` las ejecuta con dry run, labels y el límite de bytes de `.bigqueryrc`, y comprueba que cuadran entre sí. Sus variables reproducen los controles: `DESDE` y `HASTA` para Periodo, y `ENTIDAD`, `INSTITUCION`, `GRUPO_INSTITUCIONAL`, `GRUPO_TERAPEUTICO` y `MOLECULA` para las listas, con varios valores separados por comas. Por ejemplo, `make bq-dashboard ENTIDAD=Jalisco` da lo que muestra el tablero con Jalisco elegido.

La última ejecución, del 2026-10-08, ya compara con el año anterior y terminó con las cuatro cifras cruzadas en orden en los dos estados.

| Estado | Componente | Valor del tablero | Valor del SQL | Resultado |
|---|---|---|---|---|
| Inicial | Monto Total Comprado | $14,9 mil M, flecha arriba, 9.1 % | 14 941.7 M, +9.1 % | Coincide |
| Inicial | Total de Piezas Adjudicadas | 28,55 M, flecha arriba, 6.9 % | 28.55 M, +6.9 % | Coincide |
| Inicial | Precio Promedio General por Pieza | $523,42, flecha arriba, 2.1 % | 523.42, +2.1 % | Coincide |
| Jalisco | Monto Total Comprado | $1.105,6 M, flecha arriba, 1.4 % | 1 105.6 M, +1.4 % | Coincide |
| Jalisco | Total de Piezas Adjudicadas | 2,12 M, flecha arriba, 7.9 % | 2.12 M, +7.9 % | Coincide |
| Jalisco | Precio Promedio General por Pieza | $521,76, flecha abajo en `#B34700`, -6.0 % | 521.76, -6.0 % | Coincide |
| Inicial | Gasto por entidad | 32 barras, de Mex. ($1.731,1 M) a BCS ($122,2 M) | Las 32 entidades de la consulta, en el mismo orden y con el mismo importe en millones | Coincide |
| Inicial | Participación por institución | 38,7 %, 16,6 %, 16,3 %, 12,1 %, 6,8 %, 5,2 % y 4,2 % (suman 100 %) | 38.7062, 16.5982, 16.3253, 12.0979, 6.8351, 5.212 y 4.2254 | Coincide |
| Inicial | Top 10 | 10 filas, de insulina glargina con Serrato Castro ($2.092,9 M) a etanercept con Marroquín Carrillo ($279,5 M) | Las mismas 10 filas con las mismas piezas, importe y precio | Coincide |
| Jalisco | Gasto por entidad | Una barra, Jal. con $1.105,6 M | Jalisco, 1 105.6 M | Coincide |
| Jalisco | Participación por institución | 39,4 %, 26,3 %, 14,0 %, 6,9 %, 6,7 % y 6,7 % | 39.4285, 26.3344, 14.0283, 6.8795, 6.6718 y 6.6573 | Coincide |
| Jalisco | Top 10 | 10 filas, de insulina glargina con Serrato Castro ($152,5 M) a tocilizumab con Farmacéutica Valdez ($16,2 M) | Las mismas 10 filas con las mismas piezas, importe y precio | Coincide |

El filtro por clic (*cross-filtering*) funciona: un clic en IMSS deja las tarjetas en $5.783,4 M, el importe del IMSS en la consulta, y cambia las barras de entidades y el top 10. Un segundo clic lo quita (2026-10-08).

## Compartir

El informe se comparte con "Cualquier persona con el enlace puede ver", con permiso de lector. Enlace de lectura: <https://datastudio.google.com/reporting/47a2dbb4-120b-4324-8af0-6216a40771c6>.

| Comprobación sin sesión | Fecha | Resultado |
|---|---|---|
| Navegador integrado de la app, sin sesión de Google | 2026-10-08 | Abre sin pedir acceso y a los 5 segundos ya muestra las tres tarjetas con datos |
| Ventana privada del navegador del dueño | 2026-10-08 | Muestra las tres tarjetas con datos y las mismas cifras |

Prueba de lectura del tablero, cronometrada el 2026-10-08 con el enlace de lectura y el periodo por defecto (2025). No había otra persona disponible, así que la hizo el dueño del informe, que conoce el proyecto. El resultado es una referencia y no sustituye la prueba con alguien ajeno.

| Pregunta | Respuesta | Cifra en el tablero |
|---|---|---|
| Entidad con más importe | México | $1.731,1 M, el 11,6 % del importe |
| Institución con más importe | IMSS | 38,7 % del importe |
| Par molécula-fabricante líder del top 10 | Insulina glargina y Laboratorios Serrato Castro, S.A. de C.V. | $2.092,9 M |

Las tres respuestas son correctas y llevaron unos 40 segundos, por debajo de los 2 minutos del criterio.
