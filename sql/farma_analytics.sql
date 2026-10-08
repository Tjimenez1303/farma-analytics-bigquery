-- Schema, view and analytical queries of farma_analytics, built on synthetic public purchases of
-- medicines in Mexico. The whole file runs in the BigQuery console, and running it again does not
-- touch the loaded data. make runs it in parts, with a dry run before each statement. bq-schema
-- runs sections 1 and 2, bq-vista runs section 3 and bq-consultas runs section 4.

-- Section 1: dataset.

-- Dataset with the fact table and both catalogs. Its labels attribute storage costs.
CREATE SCHEMA IF NOT EXISTS farma_analytics
OPTIONS (
    location = 'US',
    description = 'Compras públicas de medicamentos en México con datos sintéticos.',
    labels = [('project', 'farma-analytics'), ('env', 'dev'), ('owner', 'bi')]
);

-- Section 2: tables.
-- The tables are not partitioned or clustered because together they take about 32 MB. They have
-- no foreign keys because COMPRAS has orphan keys on purpose, and BigQuery would use the keys to
-- drop joins.

-- Fact table, one row per purchase line. The view joins it to both catalogs.
CREATE TABLE IF NOT EXISTS farma_analytics.COMPRAS (
    CLUE STRING NOT NULL OPTIONS (
        description = 'Clave CLUES de la unidad médica que compra.'
    ),
    CLAVE STRING NOT NULL OPTIONS (
        description = 'Clave del insumo comprado en el Compendio Nacional de Insumos.'
    ),
    COD_PROVEEDOR STRING NOT NULL OPTIONS (
        description = 'Código del proveedor que entrega el insumo.'
    ),
    MARCA STRING OPTIONS (
        description = 'Marca comercial del producto entregado.'
    ),
    FABRICANTE STRING OPTIONS (
        description = 'Fabricante del producto entregado, que puede diferir del de CUADRO_BASICO.'
    ),
    PIEZAS INT64 NOT NULL OPTIONS (
        description = 'Número de piezas (envases) entregadas. Medida aditiva.'
    ),
    IMPORTE NUMERIC NOT NULL OPTIONS (
        description = 'Importe de la línea en pesos mexicanos. Medida aditiva.'
    ),
    FECHA DATE NOT NULL OPTIONS (
        description = 'Fecha de la compra.'
    )
)
OPTIONS (
    description = 'Líneas de compra de medicamentos. Grano: una línea de compra. Sin llave única.'
);

-- Medical units catalog, one row per CLUE. It gives each purchase its entity and institution.
CREATE TABLE IF NOT EXISTS farma_analytics.CLUE_CAT (
    CLUE STRING NOT NULL OPTIONS (
        description = 'Clave CLUES de la unidad médica. Llave del catálogo.'
    ),
    ENTIDAD STRING OPTIONS (
        description = 'Entidad federativa con su nombre oficial del INEGI.'
    ),
    INSTITUCION STRING OPTIONS (
        description = 'Institución pública de salud a la que pertenece la unidad.'
    ),
    DELEGACION STRING OPTIONS (
        description = 'Delegación u órgano administrativo de la institución en la entidad.'
    ),
    GRUPO_INSTITUCIONAL STRING OPTIONS (
        description = 'Agrupación de instituciones por tipo de población atendida.'
    ),
    NIVEL_ATENCION STRING OPTIONS (
        description = 'Nivel de atención de la unidad: primero, segundo o tercero.'
    ),
    MUNICIPIO STRING OPTIONS (
        description = 'Municipio o alcaldía donde está la unidad.'
    )
)
OPTIONS (
    description = 'Catálogo de unidades médicas. Grano: una unidad médica. Llave: CLUE.'
);

-- Supplies catalog, one row per CLAVE. It gives each purchase its molecule and group.
CREATE TABLE IF NOT EXISTS farma_analytics.CUADRO_BASICO (
    CLAVE STRING NOT NULL OPTIONS (
        description = 'Clave del insumo en el Compendio Nacional de Insumos. Llave del catálogo.'
    ),
    DESCRIPCION STRING OPTIONS (
        description = 'Descripción completa del insumo con el estilo del Cuadro Básico.'
    ),
    MOLECULA STRING OPTIONS (
        description = 'Denominación genérica del principio activo.'
    ),
    GRUPO_TERAPEUTICO STRING OPTIONS (
        description = 'Grupo terapéutico del Cuadro Básico al que pertenece la molécula.'
    ),
    PRESENTACION STRING OPTIONS (
        description = 'Forma farmacéutica, concentración y envase.'
    ),
    FABRICANTE STRING OPTIONS (
        description = 'Fabricante de referencia de la molécula, que puede diferir del de COMPRAS.'
    )
)
OPTIONS (
    description = 'Catálogo de insumos. Grano: una presentación de una molécula. Llave: CLAVE.'
);

-- Section 3: view.

-- Purchase lines with their medical unit and supply, plus the year, month and ISO entity code that
-- the dashboard uses. Lines whose CLUE or CLAVE is not in its catalog are left out. The queries
-- below and the dashboard read only this view, so they report the same figures.
CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa (
    CLUE OPTIONS (
        description = 'Clave CLUES de la unidad médica que compra.'
    ),
    CLAVE OPTIONS (
        description = 'Clave del insumo comprado en el Compendio Nacional de Insumos.'
    ),
    COD_PROVEEDOR OPTIONS (
        description = 'Código del proveedor que entrega el insumo.'
    ),
    MARCA OPTIONS (
        description = 'Marca comercial del producto entregado.'
    ),
    FABRICANTE_COMPRA OPTIONS (
        description = 'Fabricante del producto entregado en la línea (FABRICANTE de COMPRAS).'
    ),
    PIEZAS OPTIONS (
        description = 'Piezas (envases) entregadas. Medida aditiva.'
    ),
    IMPORTE OPTIONS (
        description = 'Importe de la línea en pesos mexicanos. Medida aditiva.'
    ),
    FECHA OPTIONS (
        description = 'Fecha de la compra.'
    ),
    ENTIDAD OPTIONS (
        description = 'Entidad federativa de la unidad médica, con su nombre oficial del INEGI.'
    ),
    INSTITUCION OPTIONS (
        description = 'Institución pública de salud de la unidad médica.'
    ),
    DELEGACION OPTIONS (
        description = 'Delegación u órgano administrativo de la institución en la entidad.'
    ),
    GRUPO_INSTITUCIONAL OPTIONS (
        description = 'Agrupación de instituciones por tipo de población atendida.'
    ),
    NIVEL_ATENCION OPTIONS (
        description = 'Nivel de atención de la unidad médica.'
    ),
    MUNICIPIO OPTIONS (
        description = 'Municipio o alcaldía de la unidad médica.'
    ),
    DESCRIPCION OPTIONS (
        description = 'Descripción completa del insumo.'
    ),
    MOLECULA OPTIONS (
        description = 'Denominación genérica del principio activo.'
    ),
    GRUPO_TERAPEUTICO OPTIONS (
        description = 'Grupo terapéutico del Cuadro Básico.'
    ),
    PRESENTACION OPTIONS (
        description = 'Forma farmacéutica, concentración y envase.'
    ),
    FABRICANTE_CATALOGO OPTIONS (
        description = 'Fabricante de referencia de la molécula (FABRICANTE de CUADRO_BASICO).'
    ),
    ANIO OPTIONS (
        description = 'Año de FECHA, para comparar año contra año.'
    ),
    MES OPTIONS (
        description = 'Primer día del mes de FECHA, para series mensuales.'
    ),
    ENTIDAD_ISO OPTIONS (
        description = 'Código ISO 3166-2 de la entidad (MX-XXX), para mapas.'
    )
)
OPTIONS (
    description = CONCAT(
        'Compras públicas de medicamentos con los datos de su unidad médica (CLUE_CAT) y de su ',
        'insumo (CUADRO_BASICO). Grano: una fila por línea de COMPRAS cuya CLUE y cuya CLAVE ',
        'existen en los catálogos, así que las líneas huérfanas quedan fuera. Es la fuente del ',
        'dashboard y de las consultas analíticas. Datos sintéticos.'
    )
)
AS
SELECT
    compras.CLUE,
    compras.CLAVE,
    compras.COD_PROVEEDOR,
    compras.MARCA,
    compras.FABRICANTE AS FABRICANTE_COMPRA,
    compras.PIEZAS,
    compras.IMPORTE,
    compras.FECHA,
    clue_cat.ENTIDAD,
    clue_cat.INSTITUCION,
    clue_cat.DELEGACION,
    clue_cat.GRUPO_INSTITUCIONAL,
    clue_cat.NIVEL_ATENCION,
    clue_cat.MUNICIPIO,
    cuadro_basico.DESCRIPCION,
    cuadro_basico.MOLECULA,
    cuadro_basico.GRUPO_TERAPEUTICO,
    cuadro_basico.PRESENTACION,
    cuadro_basico.FABRICANTE AS FABRICANTE_CATALOGO,
    EXTRACT(YEAR FROM compras.FECHA) AS ANIO,
    DATE_TRUNC(compras.FECHA, MONTH) AS MES,
    -- No ELSE, so an unknown entity stays NULL and the view check catches it.
    CASE clue_cat.ENTIDAD
        WHEN 'Aguascalientes' THEN 'MX-AGU'
        WHEN 'Baja California' THEN 'MX-BCN'
        WHEN 'Baja California Sur' THEN 'MX-BCS'
        WHEN 'Campeche' THEN 'MX-CAM'
        WHEN 'Coahuila de Zaragoza' THEN 'MX-COA'
        WHEN 'Colima' THEN 'MX-COL'
        WHEN 'Chiapas' THEN 'MX-CHP'
        WHEN 'Chihuahua' THEN 'MX-CHH'
        WHEN 'Ciudad de México' THEN 'MX-CMX'
        WHEN 'Durango' THEN 'MX-DUR'
        WHEN 'Guanajuato' THEN 'MX-GUA'
        WHEN 'Guerrero' THEN 'MX-GRO'
        WHEN 'Hidalgo' THEN 'MX-HID'
        WHEN 'Jalisco' THEN 'MX-JAL'
        WHEN 'México' THEN 'MX-MEX'
        WHEN 'Michoacán de Ocampo' THEN 'MX-MIC'
        WHEN 'Morelos' THEN 'MX-MOR'
        WHEN 'Nayarit' THEN 'MX-NAY'
        WHEN 'Nuevo León' THEN 'MX-NLE'
        WHEN 'Oaxaca' THEN 'MX-OAX'
        WHEN 'Puebla' THEN 'MX-PUE'
        WHEN 'Querétaro' THEN 'MX-QUE'
        WHEN 'Quintana Roo' THEN 'MX-ROO'
        WHEN 'San Luis Potosí' THEN 'MX-SLP'
        WHEN 'Sinaloa' THEN 'MX-SIN'
        WHEN 'Sonora' THEN 'MX-SON'
        WHEN 'Tabasco' THEN 'MX-TAB'
        WHEN 'Tamaulipas' THEN 'MX-TAM'
        WHEN 'Tlaxcala' THEN 'MX-TLA'
        WHEN 'Veracruz de Ignacio de la Llave' THEN 'MX-VER'
        WHEN 'Yucatán' THEN 'MX-YUC'
        WHEN 'Zacatecas' THEN 'MX-ZAC'
    END AS ENTIDAD_ISO
FROM
    farma_analytics.COMPRAS AS compras
INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico
    ON compras.CLAVE = cuadro_basico.CLAVE
INNER JOIN farma_analytics.CLUE_CAT AS clue_cat
    ON compras.CLUE = clue_cat.CLUE;

-- Section 4: analytical queries.

-- Question 1: Which 5 molecules have the highest purchase amount (IMPORTE)?
-- Definition: amount is SUM(IMPORTE). A tie at the cut goes to the first MOLECULA in A to Z order.
WITH importe_por_molecula AS (
    SELECT
        vista.MOLECULA,
        SUM(vista.IMPORTE) AS IMPORTE_TOTAL,
        SUM(vista.PIEZAS) AS PIEZAS_TOTALES,
        AVG(vista.IMPORTE) AS IMPORTE_PROMEDIO_LINEA,
        SAFE_DIVIDE(SUM(vista.IMPORTE), SUM(SUM(vista.IMPORTE)) OVER ()) AS PARTICIPACION
    FROM farma_analytics.v_compras_farma_completa AS vista
    GROUP BY vista.MOLECULA
)

SELECT
    importe_por_molecula.MOLECULA,
    importe_por_molecula.PIEZAS_TOTALES,
    ROUND(importe_por_molecula.IMPORTE_TOTAL, 2) AS IMPORTE_TOTAL,
    ROUND(
        SAFE_DIVIDE(importe_por_molecula.IMPORTE_TOTAL, importe_por_molecula.PIEZAS_TOTALES), 2
    ) AS PRECIO_PROMEDIO,
    ROUND(importe_por_molecula.IMPORTE_PROMEDIO_LINEA, 2) AS IMPORTE_PROMEDIO_LINEA,
    ROUND(100 * importe_por_molecula.PARTICIPACION, 2) AS PARTICIPACION_PCT
FROM importe_por_molecula AS importe_por_molecula
ORDER BY importe_por_molecula.IMPORTE_TOTAL DESC, importe_por_molecula.MOLECULA ASC
LIMIT 5;

-- Question 2: Which institution and which entity concentrate the largest purchase volume?
-- Definition: volume is SUM(IMPORTE), with SUM(PIEZAS) as the alternative. Institution and entity
-- are ranked together and separately, and RANK keeps every leader when there is a tie.
WITH volumen_por_nivel AS (
    SELECT
        vista.INSTITUCION,
        vista.ENTIDAD,
        SUM(vista.IMPORTE) AS IMPORTE,
        SUM(CAST(vista.PIEZAS AS NUMERIC)) AS PIEZAS,
        CASE
            WHEN GROUPING(vista.ENTIDAD) = 1 THEN 'INSTITUCION'
            WHEN GROUPING(vista.INSTITUCION) = 1 THEN 'ENTIDAD'
            ELSE 'INSTITUCION Y ENTIDAD'
        END AS NIVEL
    FROM farma_analytics.v_compras_farma_completa AS vista
    GROUP BY GROUPING SETS (
        (vista.INSTITUCION, vista.ENTIDAD),
        (vista.INSTITUCION),
        (vista.ENTIDAD)
    )
),

-- IMPORTE and PIEZAS become rows, so one window ranks both.
volumen_por_medida AS (
    SELECT
        volumen.INSTITUCION,
        volumen.ENTIDAD,
        volumen.NIVEL,
        volumen.MEDIDA,
        volumen.VALOR
    FROM volumen_por_nivel
    UNPIVOT (VALOR FOR MEDIDA IN (IMPORTE, PIEZAS)) AS volumen
)

SELECT
    volumen_por_medida.MEDIDA,
    volumen_por_medida.NIVEL,
    volumen_por_medida.INSTITUCION,
    volumen_por_medida.ENTIDAD,
    ROUND(volumen_por_medida.VALOR, 2) AS VALOR,
    ROUND(
        100 * SAFE_DIVIDE(
            volumen_por_medida.VALOR,
            SUM(volumen_por_medida.VALOR) OVER (
                PARTITION BY volumen_por_medida.MEDIDA, volumen_por_medida.NIVEL
            )
        ),
        2
    ) AS PARTICIPACION_PCT
FROM volumen_por_medida AS volumen_por_medida
QUALIFY
    RANK() OVER (
        PARTITION BY volumen_por_medida.MEDIDA, volumen_por_medida.NIVEL
        ORDER BY volumen_por_medida.VALOR DESC
    ) = 1
ORDER BY
    volumen_por_medida.MEDIDA ASC,
    volumen_por_medida.NIVEL ASC,
    volumen_por_medida.INSTITUCION ASC,
    volumen_por_medida.ENTIDAD ASC;

-- Question 3: What is the average price per piece by molecule and manufacturer?
-- Definition: SUM(IMPORTE) / SUM(PIEZAS) by MOLECULA and FABRICANTE_COMPRA, the manufacturer
-- that sold at that price.
WITH precio_por_fabricante_compra AS (
    SELECT
        vista.MOLECULA,
        vista.FABRICANTE_COMPRA,
        SUM(vista.IMPORTE) AS IMPORTE_TOTAL,
        SUM(vista.PIEZAS) AS PIEZAS_TOTALES
    FROM farma_analytics.v_compras_farma_completa AS vista
    GROUP BY vista.MOLECULA, vista.FABRICANTE_COMPRA
)

SELECT
    precio_por_fabricante_compra.MOLECULA,
    precio_por_fabricante_compra.FABRICANTE_COMPRA,
    precio_por_fabricante_compra.PIEZAS_TOTALES,
    ROUND(precio_por_fabricante_compra.IMPORTE_TOTAL, 2) AS IMPORTE_TOTAL,
    ROUND(
        SAFE_DIVIDE(
            precio_por_fabricante_compra.IMPORTE_TOTAL,
            precio_por_fabricante_compra.PIEZAS_TOTALES
        ),
        2
    ) AS PRECIO_PROMEDIO
FROM precio_por_fabricante_compra AS precio_por_fabricante_compra
ORDER BY
    precio_por_fabricante_compra.MOLECULA ASC,
    PRECIO_PROMEDIO DESC,
    precio_por_fabricante_compra.FABRICANTE_COMPRA ASC;

-- Question 3 by FABRICANTE_CATALOGO, the reference manufacturer. Each molecule has only one, so
-- this is the price of each molecule across the whole market.
WITH precio_por_fabricante_catalogo AS (
    SELECT
        vista.MOLECULA,
        vista.FABRICANTE_CATALOGO,
        SUM(vista.IMPORTE) AS IMPORTE_TOTAL,
        SUM(vista.PIEZAS) AS PIEZAS_TOTALES
    FROM farma_analytics.v_compras_farma_completa AS vista
    GROUP BY vista.MOLECULA, vista.FABRICANTE_CATALOGO
)

SELECT
    precio_por_fabricante_catalogo.MOLECULA,
    precio_por_fabricante_catalogo.FABRICANTE_CATALOGO,
    precio_por_fabricante_catalogo.PIEZAS_TOTALES,
    ROUND(precio_por_fabricante_catalogo.IMPORTE_TOTAL, 2) AS IMPORTE_TOTAL,
    ROUND(
        SAFE_DIVIDE(
            precio_por_fabricante_catalogo.IMPORTE_TOTAL,
            precio_por_fabricante_catalogo.PIEZAS_TOTALES
        ),
        2
    ) AS PRECIO_PROMEDIO
FROM precio_por_fabricante_catalogo AS precio_por_fabricante_catalogo
ORDER BY
    precio_por_fabricante_catalogo.MOLECULA ASC,
    precio_por_fabricante_catalogo.FABRICANTE_CATALOGO ASC;
