# Datos sintéticos

Las tres fuentes del proyecto (`COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO`) son sintéticas. No contienen compras reales, establecimientos reales ni datos personales. Las produce el generador de [`generator/`](../generator) a partir de una semilla y de los parámetros de [`generator/config.toml`](../generator/config.toml), y cualquier persona puede regenerarlas con `make data`.

Para que el análisis se parezca a un mercado real, algunos nombres sí son reales: las 32 entidades federativas con su nombre oficial del INEGI, sus municipios, las instituciones públicas de salud y las moléculas con su grupo terapéutico del Cuadro Básico. Todo lo demás es inventado. Eso incluye las unidades médicas y sus claves, las claves de los insumos, los fabricantes, las marcas, los proveedores, las fechas, las piezas y los importes.

## Cómo se generan

La semilla es un número de 128 bits guardado como texto en la configuración. De ella salen seis flujos aleatorios independientes, uno por componente (unidades médicas, insumos, empresas, compras, huérfanos y nombres con Faker), de modo que cambiar el número de compras no altera los catálogos. NumPy 2.5.3 y Faker 40.39.0 están fijados en versión exacta, porque las dos bibliotecas solo garantizan la misma secuencia con la misma versión.

Cada generación escribe un manifiesto con la huella SHA-256, el tamaño y el número de filas de cada archivo, además de los conteos de huérfanos y las versiones usadas. La copia de referencia está versionada en [`generator/manifest.json`](../generator/manifest.json). Con la misma configuración y las mismas versiones, en la misma máquina, dos generaciones producen exactamente los mismos bytes. Entre sistemas operativos distintos la coincidencia se busca, pero NumPy no la garantiza. Si `make data` informa `DIFIERE` en otra plataforma, el mensaje muestra las versiones de cada lado.

Los importes se calculan en centavos enteros. El precio unitario de cada línea se redondea a centavos una sola vez, y `IMPORTE` es exactamente `PIEZAS` por ese precio. Por eso `IMPORTE / PIEZAS` devuelve el precio de la línea sin error de redondeo.

## Campos

Una pieza es un envase, igual que en el Cuadro Básico. Los tipos son los que tendrá cada columna en BigQuery.

### `CLUE_CAT`

Cada fila es una unidad médica y `CLUE` no se repite.

| Campo | Tipo | Regla de generación |
|---|---|---|
| `CLUE` | `STRING` | Once caracteres con el formato de una CLUES: dos letras de la entidad, tres de la institución y seis dígitos al azar. |
| `ENTIDAD` | `STRING` | Uno de los 32 nombres oficiales del INEGI. Hay más unidades donde vive más gente. |
| `INSTITUCION` | `STRING` | IMSS, ISSSTE, SEDENA, SEMAR, PEMEX, IMSS-Bienestar o Servicios Estatales de Salud. |
| `DELEGACION` | `STRING` | Prefijo administrativo de la institución seguido de la entidad, por ejemplo "OOAD Jalisco". |
| `GRUPO_INSTITUCIONAL` | `STRING` | "Seguridad social", "Fuerzas Armadas y PEMEX" o "Población sin seguridad social". |
| `NIVEL_ATENCION` | `STRING` | Primer, segundo o tercer nivel, con 70 %, 25 % y 5 % de las unidades. |
| `MUNICIPIO` | `STRING` | Municipio real de la entidad (alcaldía en la Ciudad de México), elegido según su población. |

Cada institución solo tiene unidades donde opera en la realidad. SEDENA, SEMAR y PEMEX aparecen en las entidades donde los datos abiertos CLUES de la DGIS registran unidades en operación (29, 18 y 16 entidades). IMSS-Bienestar aparece en las 24 entidades adheridas y los Servicios Estatales de Salud en las 8 que no se adhirieron: Aguascalientes, Chihuahua, Coahuila de Zaragoza, Durango, Guanajuato, Jalisco, Nuevo León y Querétaro.

### `CUADRO_BASICO`

Cada fila es una presentación de una molécula y `CLAVE` no se repite. Hay 161 claves de 139 moléculas.

| Campo | Tipo | Regla de generación |
|---|---|---|
| `CLAVE` | `STRING` | Formato de clave del Compendio para medicamentos, `010.000.NNNN.00`, con un número de cuatro dígitos al azar. |
| `DESCRIPCION` | `STRING` | Texto con el estilo del Cuadro Básico, por ejemplo "Paracetamol. Tableta. Cada tableta contiene: paracetamol 500 mg. Envase con 10 tabletas." |
| `MOLECULA` | `STRING` | Denominación genérica real. Una molécula puede tener varias claves. |
| `GRUPO_TERAPEUTICO` | `STRING` | Uno de los grupos de medicamentos del Cuadro Básico. Cada molécula pertenece a uno solo. |
| `PRESENTACION` | `STRING` | Forma farmacéutica, concentración y envase. |
| `FABRICANTE` | `STRING` | Fabricante de referencia de la molécula, que siempre es un fabricante innovador ficticio. |

### `COMPRAS`

Cada fila es una línea de compra: una entrega de una clave a una unidad médica, por un proveedor, con una marca y un fabricante, en un día laborable. No hay llave única, porque dos pedidos distintos pueden coincidir en unidad, clave y fecha.

| Campo | Tipo | Regla de generación |
|---|---|---|
| `CLUE` | `STRING` | Unidad médica que compra. |
| `CLAVE` | `STRING` | Insumo comprado. |
| `COD_PROVEEDOR` | `STRING` | `PRV` seguido de cinco dígitos. Cada proveedor distribuye a uno o varios fabricantes. |
| `MARCA` | `STRING` | Marca ficticia. Cada marca pertenece a un solo fabricante. |
| `FABRICANTE` | `STRING` | Fabricante del producto entregado. Puede ser el fabricante innovador de referencia o uno de los genéricos autorizados para esa molécula. |
| `PIEZAS` | `INT64` | Entero entre 1 y 50 000, con distribución lognormal. |
| `IMPORTE` | `NUMERIC` | `PIEZAS` por el precio unitario, en pesos con dos decimales. |
| `FECHA` | `DATE` | Día laborable entre el 1 de enero de 2024 y el 31 de diciembre de 2025. |

El precio unitario de una línea es el precio base de la clave por el factor de su fabricante por un ruido de hasta 10 % arriba o abajo. Cada fabricante tiene un único factor para todas sus moléculas. Los fabricantes innovadores cobran entre 1.40 y 1.80 veces el precio base y los genéricos entre 0.50 y 0.80. El precio base depende del nivel de precio de la molécula: de 15 a 100 pesos por pieza en el nivel bajo, de 100 a 600 en el medio, de 600 a 2 500 en el alto y de 2 500 a 9 000 en el muy alto.

## Patrones inyectados a propósito

Estos patrones están en los datos porque el generador los pone. Cualquier hallazgo que los refleje tiene que decirlo. Las cifras que aparecen en el dashboard y en los hallazgos salen de consultar los datos y no coinciden exactamente con los parámetros, porque el ruido y la mezcla de compras las mueven.

| Patrón | Qué produce | Parámetro en `generator/config.toml` | Valor |
|---|---|---|---|
| Concentración por molécula | Pocas moléculas acumulan la mayor parte del importe (cola larga tipo Zipf). Insulina glargina, atorvastatina y clopidogrel tienen una posición fija entre las más compradas. | `concentracion.alpha_moleculas`, `concentracion.moleculas_destacadas` | 0.9, con las posiciones 2, 4 y 6 |
| Concentración por institución | El IMSS concentra la mayor parte de las líneas de compra. | `concentracion.participacion_institucion` | IMSS 0.42, IMSS-Bienestar 0.18, ISSSTE 0.15, Servicios Estatales de Salud 0.12, SEDENA 0.06, SEMAR 0.04, PEMEX 0.03 |
| Concentración por entidad | Las entidades más pobladas compran más. | `concentracion.beta_entidades` | 1.0 (proporcional a la población del Censo 2020) |
| Estacionalidad | Enero y febrero son los meses de más compras y noviembre y diciembre los de menos. | `estacionalidad.factores_mes` | de 1.25 en enero a 0.90 en diciembre |
| Crecimiento anual | En 2025 hay más líneas que en 2024. | `estacionalidad.crecimiento_total` | 0.06 |
| Huérfanos | El 0.5 % de las líneas de compra tiene una `CLUE` o una `CLAVE` que no existe en su catálogo, con formato válido, y el `INNER JOIN` de la vista las descarta. | `huerfanos.orphan_rate`, `huerfanos.proporcion_clue` | 0.005, mitad de cada tipo (750 y 750) |
| P3, mezcla de fabricantes por institución | PEMEX, SEMAR y SEDENA compran sobre todo al fabricante innovador y el IMSS sobre todo genéricos, así que pagan un precio promedio por pieza distinto por la misma molécula. | `patrones.p3.prob_referencia`, `patrones.p3.molecula_ejemplo` | de 0.75 en PEMEX a 0.20 en el IMSS, medido en clopidogrel |
| P4, crecimiento de un grupo terapéutico | El importe de Oncología crece de 2024 a 2025 bastante más que el del resto de grupos. | `patrones.p4.factor_2025`, `patrones.p4.factor_2025_resto` | Oncología 1.30, resto 1.05 |
| P5, cambio de cuota | En atorvastatina e insulina glargina, un genérico pasa del 15 % al 32 % de las líneas y el fabricante innovador pierde participación. | `patrones.p5.moleculas`, `patrones.p5.cuota_generico_inicial`, `patrones.p5.cuota_generico_final` | 0.15 y 0.32 |

La diferencia de precio entre instituciones de P3 sale solo de qué fabricantes compra cada una. No existe un factor de precio por institución.

## Definiciones y limitaciones

El `FABRICANTE` de `CUADRO_BASICO` es el fabricante de referencia de la molécula, mientras que el de `COMPRAS` es el fabricante del producto entregado en esa línea. Las dos columnas tienen el mismo nombre en los requisitos y significan cosas distintas, por eso la vista las tendrá que distinguir.

Los fabricantes, las marcas y los proveedores son empresas ficticias. Los nombres de los fabricantes se arman con apellidos que genera Faker con el locale `es_MX`, y una lista de laboratorios reales que operan en México ([`generator/reference/laboratorios_reales.txt`](../generator/reference/laboratorios_reales.txt)) descarta cualquier nombre que coincida con uno de ellos. Las marcas se forman con sílabas al azar. Si algún nombre se parece al de una empresa real, es una coincidencia.

Las claves CLUES y las del Compendio tienen un formato verosímil, pero no corresponden a establecimientos ni a insumos reales. Los prefijos de institución de la CLUES son los que usa la DGIS, incluido `IMO` para IMSS-Bienestar, que es la clave del antiguo régimen IMSS-Oportunidades y la que aparece en los datos abiertos de 2022.

Como hay huérfanos a propósito, las tablas no declaran claves foráneas. BigQuery no las comprueba y las usaría para eliminar joins, lo que daría resultados incorrectos con estas filas.

Puede haber claves del catálogo o unidades médicas sin ninguna compra. No afecta a la vista, porque el `INNER JOIN` parte de `COMPRAS`.

Solo se generan medicamentos del grupo 010 del Compendio. Las vacunas y el material de curación quedan fuera porque sus claves pertenecen a otros grupos.

## Fuentes de los catálogos de referencia

Los catálogos de [`generator/reference/`](../generator/reference) son entradas versionadas del generador y no se cargan en BigQuery.

| Archivo | Contenido | Fuente |
|---|---|---|
| `entidades.csv` | Nombre oficial, población 2020, código de dos letras de la CLUES y presencia de cada institución | [INEGI, catálogo de áreas geoestadísticas estatales](https://gaia.inegi.org.mx/wscatgeo/v2/mgee/) y [DGIS, datos abiertos CLUES 2022](http://www.dgis.salud.gob.mx/descargas/datosabiertos/recursosSalud/CLUES_2022.csv) |
| `municipios.csv` | Capital y municipios más poblados de cada entidad, con su población 2020. Quedan fuera los municipios creados después del Censo 2020, que no tienen población | [INEGI, catálogo de áreas geoestadísticas municipales](https://gaia.inegi.org.mx/wscatgeo/v2/mgem/) |
| `instituciones.csv` | Prefijo CLUES, grupo institucional y prefijo de delegación | [DOF, lineamientos CLUES](https://dof.gob.mx/nota_detalle_popup.php?codigo=5283475) y datos abiertos de la DGIS |
| `moleculas.csv` | Denominación genérica, grupo terapéutico, nivel de precio y presentaciones | [DOF, Cuadro Básico y Catálogo de Medicamentos, edición 2014](https://farmacopea.org.mx/Repositorio/LegislacionFiles/CBCMed2014_02mar15.pdf) |
| `laboratorios_reales.txt` | Laboratorios reales que ningún nombre ficticio puede reproducir | Lista propia |

La adhesión de cada entidad a IMSS-Bienestar sigue la lista que dio el gobierno federal en enero de 2026 y que repitió una nota de MVS Noticias en agosto de 2026.
