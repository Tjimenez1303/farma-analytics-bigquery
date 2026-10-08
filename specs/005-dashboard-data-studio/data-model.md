# Data Model: Dashboard comercial en Data Studio (Fase 3)

El tablero no crea datos ni objetos en BigQuery. Su modelo es la configuración de Data Studio sobre
la vista `farma_analytics.v_compras_farma_completa` (feature 004) más las consultas de verificación.
Todo lo de este archivo pasa a `docs/dashboard.md` en lenguaje para lectores
([contracts/especificacion-dashboard.md](contracts/especificacion-dashboard.md)).

## Fuente de datos

| Atributo | Valor | Requisito |
|---|---|---|
| Tipo | Reutilizable, creada desde la página de inicio de Data Studio | FR-001 |
| Conector | BigQuery, proyecto del dueño, dataset `farma_analytics`, tabla `v_compras_farma_completa` | FR-001 |
| Consulta personalizada | No | FR-001 |
| Nombre | `v_compras_farma_completa (BigQuery)` | Trazabilidad 1:1 |
| Credenciales | *Owner's credentials* | FR-002 |
| Frescura de datos | 12 horas | FR-003, R1 |
| "Field Editing in Reports" | Activado desde el 2026-10-08, solo para el "Percent of total" de la tabla de instituciones (R7). Los campos se definen en la fuente | FR-004, FR-018 |

## Campos de la fuente

Una fila por columna de la vista, en su orden, más el campo calculado. "Uso" dice dónde aparece en
la página principal.

| Columna | Nombre de negocio | Tipo | Agregación | Uso |
|---|---|---|---|---|
| `CLUE` | Clave CLUES | Text | None | Sin uso |
| `CLAVE` | Clave del insumo | Text | None | Sin uso |
| `COD_PROVEEDOR` | Proveedor | Text | None | Sin uso |
| `MARCA` | Marca | Text | None | Sin uso |
| `FABRICANTE_COMPRA` | Fabricante | Text | None | Tabla top 10 |
| `PIEZAS` | Piezas | Number | Sum | Tarjeta, tabla, campo calculado |
| `IMPORTE` | Importe | Currency (MXN) | Sum | Tarjeta, barras, mapa, tabla, campo calculado |
| `FECHA` | Fecha | Date | None | Control de rango de fechas (dimensión de fecha de la fuente) |
| `ENTIDAD` | Entidad | Text | None | Control, barras de entidades |
| `INSTITUCION` | Institución | Text | None | Control, barras de instituciones |
| `DELEGACION` | Delegación | Text | None | Sin uso |
| `GRUPO_INSTITUCIONAL` | Grupo institucional | Text | None | Control |
| `NIVEL_ATENCION` | Nivel de atención | Text | None | Sin uso |
| `MUNICIPIO` | Municipio | Text | None | Sin uso |
| `DESCRIPCION` | Descripción del insumo | Text | None | Sin uso |
| `MOLECULA` | Molécula | Text | None | Control, tabla top 10 |
| `GRUPO_TERAPEUTICO` | Grupo terapéutico | Text | None | Control |
| `PRESENTACION` | Presentación | Text | None | Sin uso |
| `FABRICANTE_CATALOGO` | Fabricante de catálogo | Text | None | Sin uso |
| `ANIO` | Año | Year | None | Sin uso |
| `MES` | Mes | Year Month | None | Sin uso |
| `ENTIDAD_ISO` | Entidad ISO | Country subdivision (1st level) | None | Mapa |

| Campo calculado | Fórmula | Tipo | Agregación | Uso |
|---|---|---|---|---|
| Precio Promedio | `SUM(IMPORTE) / NULLIF(SUM(PIEZAS), 0)` | Currency (MXN) | Auto (fija) | Tarjeta, tabla |
| Entidad (abreviatura) | `CASE Entidad WHEN <nombre> THEN <abreviatura del INEGI> … ELSE Entidad END`, 32 pares (R6) | Text | None | Etiquetas de las barras de entidades |

Alternativas registradas (R2, R9, R11), que solo se crean si la prueba en el producto las exige:

| Campo calculado | Fórmula | Cuándo |
|---|---|---|
| Precio Promedio (sin `NULLIF`) | `CASE WHEN SUM(PIEZAS) = 0 THEN NULL ELSE SUM(IMPORTE) / SUM(PIEZAS) END` | `NULLIF` no acepta un agregado |
| Entidad ISO para mapa | `CASE WHEN ENTIDAD_ISO = 'MX-CMX' THEN 'MX-DIF' ELSE ENTIDAD_ISO END` | El Geo chart no reconoce `MX-CMX` |
| Importe en millones | `SUM(IMPORTE) / 1000000` | Los números compactos usan "B" para mil millones |

Reglas de validación:

- ningún campo usa `AVG` ni un precio por fila (FR-005);
- el ID de campo de cada columna es el nombre de la columna en la vista, sin cambios, para que los
  controles en cascada encuentren el mismo campo (R3).

## Rejilla y disposición

Lienzo de 1600 × 900 px, rejilla de 10 px, márgenes laterales e inferior de 20 px y margen superior
de 10 px. Coordenadas en px desde la esquina
superior izquierda (x, y, ancho, alto). Es la maqueta aprobada el 2026-10-08.

| Componente | x | y | Ancho | Alto | Nivel de la pirámide |
|---|---|---|---|---|---|
| Título | 20 | 10 | 1560 | 30 | 1 |
| Subtítulo de transparencia | 20 | 40 | 1560 | 30 | 1 |
| Control de rango de fechas, con la etiqueta de texto "Periodo" (12 px) encima | 20 | 80 | 230 | 50 | 1 |
| Lista Entidad | 260 | 80 | 220 | 50 | 1 |
| Lista Institución | 490 | 80 | 220 | 50 | 1 |
| Lista Grupo institucional | 720 | 80 | 220 | 50 | 1 |
| Lista Grupo terapéutico | 950 | 80 | 220 | 50 | 1 |
| Lista Molécula | 1180 | 80 | 220 | 50 | 1 |
| Botón Restablecer filtros | 1410 | 80 | 170 | 50 | 1 |
| Tarjeta Monto Total Comprado | 20 | 140 | 360 | 90 | 2 |
| Tarjeta Total de Piezas Adjudicadas | 400 | 140 | 360 | 90 | 2 |
| Tarjeta Precio Promedio General por Pieza | 780 | 140 | 360 | 90 | 2 |
| Título del recuadro Hallazgos clave | 1160 | 140 | 420 | 20 | 2 |
| Texto del recuadro Hallazgos clave | 1160 | 160 | 420 | 70 | 2 |
| Marco de Periodo | 20 | 80 | 230 | 50 | 1 |
| Marcos de las tarjetas | 20, 400 y 780 | 140 | 360 | 90 | 2 |
| Barras Gasto por entidad | 20 | 240 | 500 | 640 | 3 |
| Mapa Gasto por entidad | 540 | 240 | 510 | 270 | 3 |
| Tabla Participación por institución | 1070 | 240 | 510 | 270 | 3 |
| Tabla Top 10 molécula-fabricante | 540 | 530 | 1040 | 350 | 4 |

Rejilla ajustada al construir (decisión del dueño del 2026-10-08): con filas de unos 29 px, la tabla del top 10 necesita unos 345 px para sus 10 filas, su encabezado y su título, y en 310 px solo se veían 9. Las tarjetas bajaron a 90 px y todo lo de debajo subió 30 px. La fila de tarjetas y hallazgos termina en y 230, a 10 px de los gráficos.

Si se aplica la alternativa de flechas de R5, se añaden tres tarjetas de 60 × 30 en x 310, 690 y
1070, y 190, y el texto de la excepción en x 20, y 222, 1120 × 16.

## Textos fijos

| Componente | Texto literal | Tamaño y color |
|---|---|---|
| Título | "Compras públicas de medicamentos en México" | 24 px, `#202124` |
| Subtítulo | "Datos sintéticos generados para este proyecto, del 1 ene 2024 al 31 dic 2025 (fecha de corte). Importes en pesos mexicanos (MXN). El tablero abre con 2025 y el rango se puede cambiar. Las tarjetas comparan con las mismas fechas del año anterior, y con rangos de más de un año el cambio no es comparable. Precio promedio ponderado: importe total entre piezas totales." | 12 px, `#5F6368`, dos líneas |
| Etiqueta del control de fechas | "Periodo" | 12 px, `#5F6368` |
| Botón | "Restablecer filtros" | 12 px, `#0072B2` |
| Etiqueta de comparación de las tarjetas | "frente al mismo periodo del año anterior" | La de la tarjeta |

El subtítulo cumple FR-009 y FR-026. Si cambia el rango por defecto, cambia también el subtítulo.

La disposición es inicial (aclaración de la spec): un cambio se hace primero en
`docs/dashboard.md` y después en el informe.

## Controles

| Control | Campo | Tipo | Valor por defecto | Búsqueda | Selección múltiple | Límite de valores |
|---|---|---|---|---|---|---|
| Periodo | `FECHA` | Date range control | Fijo, 2025-01-01 a 2025-12-31 | No aplica | No aplica | No aplica |
| Entidad | `ENTIDAD` | Drop-down list | Todas | Sí | Sí | 200 (hay 32) |
| Institución | `INSTITUCION` | Drop-down list | Todas | Sí | Sí | 200 (hay 7) |
| Grupo institucional | `GRUPO_INSTITUCIONAL` | Drop-down list | Todos | Sí | Sí | 200 (hay 3) |
| Grupo terapéutico | `GRUPO_TERAPEUTICO` | Drop-down list | Todos | Sí | Sí | 200 (hay 22) |
| Molécula | `MOLECULA` | Drop-down list | Todas | Sí | Sí | 200 (hay 139) |

Relaciones: todos los controles usan la misma fuente, así que se filtran entre sí (cascada) y
afectan a los 7 componentes de datos (3 tarjetas y 4 gráficos). No hay excepciones de alcance. Si la construcción descubre
una, se indica junto al visual afectado (FR-010).

## Tarjetas

| Tarjeta | Métrica | Unidad visible | Formato del valor | Comparación |
|---|---|---|---|---|
| Monto Total Comprado | Importe (`SUM(IMPORTE)`) | "$" en el valor, moneda en el subtítulo | Compacto, 1 decimal | Previous year, cambio en %, 1 decimal |
| Total de Piezas Adjudicadas | Piezas (`SUM(PIEZAS)`) | "Piezas" en el nombre | Compacto, 2 decimales | Previous year, cambio en %, 1 decimal |
| Precio Promedio General por Pieza | Precio Promedio | "$" en el valor y "por Pieza" en el nombre | Compacto, 2 decimales (por debajo de mil se ve igual, por encima pasa a "K") | Previous year, cambio en %, 1 decimal |

Estado sin datos en el periodo de referencia: "Missing data" en "-" (R5).

## Gráficos

| Componente | Tipo | Dimensión | Métrica | Orden | Límite | Etiquetas | Color |
|---|---|---|---|---|---|---|---|
| Gasto por entidad | Bar chart horizontal | Entidad (abreviatura) | Importe | Importe descendente | 32 barras, sin "Others" | Valor compacto | `#0072B2` |
| Mapa de gasto por entidad | Geo chart, zoom México, sin leyenda (R9) | Entidad ISO | Importe | No aplica | 32 áreas | Tooltip | Escala `#DCEBF5` a `#0072B2`, "Dataless" `#F1F3F4` |
| Participación por institución | Table with bars (alternativa de R7) | Institución | Importe, Percent of total ("% del importe") | Descendente | 7 filas, sin "Others" | % con 1 decimal junto a la barra | `#0072B2` |
| Top 10 molécula-fabricante | Table | Molécula, Fabricante | Piezas (entero con separador de miles, sin compactar), Importe (compacto, 1 decimal), Precio Promedio (2 decimales, sin compactar) | Importe descendente, después Molécula y Fabricante | Top N 10, sin "Others" | Números a la derecha | Texto `#202124` |

Títulos de componentes (descriptivos, aclaración de la spec):

- "Gasto por entidad";
- "Gasto por entidad en el mapa";
- "Participación por institución, % del importe";
- "Top 10 pares molécula-fabricante por importe". Una molécula puede salir con varios fabricantes
  (en 2025, 10 filas con 6 moléculas distintas), que es la definición de "Top 10 de moléculas" del
  principio VI.

Alternativas registradas, que solo se aplican si la prueba en el producto las exige:

| Riesgo | Alternativa |
|---|---|
| La tarjeta no dibuja ▲▼ | Campo calculado de texto con ▲ o ▼ por tarjeta sobre `FECHA`, fuera del grupo del control de fechas y con la excepción "▲▼ comparan siempre 2025 con 2024" visible (R5) |
| Los números compactos usan "B" | Campos "Importe en millones" y "Piezas en millones" sin compactar, unidades en millones y enmienda PATCH de la constitución (R11) |
| El gráfico de barras no admite "Percent of total" | Tabla de Institución con la columna en "Percent of total" de tipo "Bar" (R7) |
| El botón no devuelve el rango de fechas | Botón *Navigation* que recarga el propio informe (R4) |
| El valor de la tarjeta no admite 26 px | Ajustar los demás tamaños para mantener 3 (R10) |

## Recuadro de hallazgos clave

| Atributo | Valor |
|---|---|
| Título | "Hallazgos clave (según los filtros)" |
| Contenido | Tres conclusiones con chips (institución, entidad y molécula líderes con su % del importe) que cambian con los controles. Sin texto fijo (R17) |
| Longitud | 3 líneas de 12 px con interlineado de 16 px, una por conclusión, en un cuadro de 420 × 70 bajo un cuadro de título de 14 px de 420 × 20 |
| Origen de cada cifra | Chips sobre la fuente, comprobados contra `make bq-dashboard` con los filtros por defecto y con Jalisco |
| Advertencia | No va en el recuadro, porque sus líneas cambian con los filtros. Va en el documento de hallazgos (feature 006, principio VII) |

## Estados del tablero

| Estado | Definición | Qué se verifica |
|---|---|---|
| Inicial | Rango 2025-01-01 a 2025-12-31, sin otros filtros | KPIs, comparación, entidades, instituciones, top 10 y hallazgos |
| Filtrado | Rango por defecto y una entidad elegida (por ejemplo, Jalisco) | KPIs, top 10 y gasto por entidad (FR-033) |
| Ampliado | Rango 2024-01-01 a 2025-12-31 | Totales de toda la vista y comparación de +109.1 %, que no es comparable porque 2023-2024 solo tiene datos de 2024. El subtítulo lo avisa |
| Vacío | Una combinación sin filas (por ejemplo, SEMAR en una entidad donde no opera) | Estado vacío legible |

## Consultas de verificación

Viven en `sql/dashboard/`, leen solo de la vista y comparten el mismo bloque de filtros
([contracts/verificacion-sql.md](contracts/verificacion-sql.md)).

| Consulta | Parámetros | Columnas de salida | Filas |
|---|---|---|---|
| `kpis.sql` | Filtros | `FILAS`, `IMPORTE`, `PIEZAS`, `PRECIO_PROMEDIO` | 1 |
| `kpis_por_anio.sql` | Filtros salvo las fechas | `ANIO`, `FILAS`, `IMPORTE`, `PIEZAS`, `PRECIO_PROMEDIO` | 1 por año (2 con los datos actuales) |
| `gasto_entidad.sql` | Filtros | `ENTIDAD`, `ENTIDAD_ISO`, `IMPORTE` | Hasta 32 |
| `participacion_institucion.sql` | Filtros | `INSTITUCION`, `IMPORTE`, `PARTICIPACION_PCT` | Hasta 7 |
| `top10_molecula_fabricante.sql` | Filtros | `MOLECULA`, `FABRICANTE_COMPRA`, `PIEZAS`, `IMPORTE`, `PRECIO_PROMEDIO` | Hasta 10 |

Parámetros comunes:

| Parámetro | Tipo | Valor por defecto | Significado del valor vacío |
|---|---|---|---|
| `@fecha_inicio` | DATE | 2025-01-01 | No admite vacío |
| `@fecha_fin` | DATE | 2025-12-31 | No admite vacío |
| `@entidades` | ARRAY<STRING> | `[]` | Todas |
| `@instituciones` | ARRAY<STRING> | `[]` | Todas |
| `@grupos_institucionales` | ARRAY<STRING> | `[]` | Todos |
| `@grupos_terapeuticos` | ARRAY<STRING> | `[]` | Todos |
| `@moleculas` | ARRAY<STRING> | `[]` | Todas |

`kpis_por_anio.sql` no usa `@fecha_inicio` ni `@fecha_fin`: es la consulta por año que compara 2025
con 2024 sin depender del rango.

## Cifras esperadas del estado inicial

Calculadas en local con los CSV de `data/` (R12). `make bq-dashboard` las tiene que reproducir sobre
la vista, y son las que se comparan con el tablero.

Las tarjetas comparan 2025 con las mismas fechas del año anterior, 2024 completo (R5).

| Cifra | 2025 | 2024 (año anterior) | Cambio |
|---|---|---|---|
| Importe | 14 941.7 M | 13 692.2 M | +9.1 % |
| Piezas | 28.55 M | 26.71 M | +6.9 % |
| Precio promedio | 523.42 | 512.71 | +2.1 % |
| Filas | 153 682 | 144 818 | No aplica |

| Cifra de 2025 | Valor |
|---|---|
| Entidad líder | México, 1 731 M (11.59 %) |
| Entidad con menos importe | Baja California Sur, 122 M (0.82 %) |
| Institución líder | IMSS, 38.71 % |
| Primer par del top 10 | Insulina glargina, Laboratorios Serrato Castro, 2 092.9 M, 1 413.31 por pieza |
| Décimo par del top 10 | Etanercept, Laboratorios Marroquín Carrillo, 279.5 M |

## Registro de verificación

Una fila por cifra comparada, en `docs/dashboard.md` (FR-033).

| Campo | Contenido |
|---|---|
| Estado | Inicial, Filtrado o Ampliado, con los filtros exactos |
| Componente | Tarjeta, barra, fila de la tabla |
| Valor del tablero | Lo que muestra Data Studio, con su redondeo |
| Valor del SQL | Salida de `make bq-dashboard` |
| Resultado | Coincide o la diferencia y su causa |
