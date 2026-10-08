-- Do COMPRAS rows and IMPORTE equal the INNER JOIN with both catalogs plus the orphan rows, and
-- do the orphans per key match the manifest? The INNER JOIN drops orphans without warning.
WITH totales_compras AS (
    SELECT
        COUNT(*) AS FILAS,
        COALESCE(SUM(compras.IMPORTE), 0) AS IMPORTE
    FROM farma_analytics.COMPRAS AS compras
),

union_interna AS (
    SELECT
        COUNT(*) AS FILAS,
        COALESCE(SUM(compras.IMPORTE), 0) AS IMPORTE
    FROM farma_analytics.COMPRAS AS compras
    INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico
        ON compras.CLAVE = cuadro_basico.CLAVE
    INNER JOIN farma_analytics.CLUE_CAT AS clue_cat
        ON compras.CLUE = clue_cat.CLUE
),

-- Orphan flags with anti-semi-joins, so no outer join is needed.
marcas_huerfanas AS (
    SELECT
        compras.IMPORTE,
        NOT EXISTS (
            SELECT 1
            FROM farma_analytics.CLUE_CAT AS clue_cat
            WHERE clue_cat.CLUE = compras.CLUE
        ) AS SIN_CLUE,
        NOT EXISTS (
            SELECT 1
            FROM farma_analytics.CUADRO_BASICO AS cuadro_basico
            WHERE cuadro_basico.CLAVE = compras.CLAVE
        ) AS SIN_CLAVE
    FROM farma_analytics.COMPRAS AS compras
),

filas_huerfanas AS (
    SELECT
        COUNTIF(marcas_huerfanas.SIN_CLUE OR marcas_huerfanas.SIN_CLAVE) AS FILAS,
        COALESCE(
            SUM(
                IF(
                    marcas_huerfanas.SIN_CLUE OR marcas_huerfanas.SIN_CLAVE,
                    marcas_huerfanas.IMPORTE,
                    0
                )
            ),
            0
        ) AS IMPORTE,
        COUNTIF(marcas_huerfanas.SIN_CLUE) AS HUERFANOS_CLUE,
        COUNTIF(marcas_huerfanas.SIN_CLAVE) AS HUERFANOS_CLAVE
    FROM marcas_huerfanas AS marcas_huerfanas
)

SELECT
    'reconciliacion_join' AS CHEQUEO,
    'COMPRAS' AS OBJETO,
    cuadres.DETALLE,
    CAST(cuadres.ESPERADO AS STRING) AS ESPERADO,
    CAST(cuadres.OBTENIDO AS STRING) AS OBTENIDO
FROM
    UNNEST([
        STRUCT(
            'filas: COMPRAS frente a INNER JOIN más huérfanas' AS DETALLE,
            CAST((SELECT totales.FILAS FROM totales_compras AS totales) AS NUMERIC) AS ESPERADO,
            CAST(
                (SELECT interna.FILAS FROM union_interna AS interna)
                + (SELECT huerfanas.FILAS FROM filas_huerfanas AS huerfanas) AS NUMERIC
            ) AS OBTENIDO
        ),
        STRUCT(
            'IMPORTE: COMPRAS frente a INNER JOIN más huérfanas' AS DETALLE,
            (SELECT totales.IMPORTE FROM totales_compras AS totales) AS ESPERADO,
            (SELECT interna.IMPORTE FROM union_interna AS interna)
            + (SELECT huerfanas.IMPORTE FROM filas_huerfanas AS huerfanas) AS OBTENIDO
        ),
        STRUCT(
            'huérfanos de CLUE' AS DETALLE,
            CAST(@huerfanos_clue AS NUMERIC) AS ESPERADO,
            CAST(
                (SELECT huerfanas.HUERFANOS_CLUE FROM filas_huerfanas AS huerfanas) AS NUMERIC
            ) AS OBTENIDO
        ),
        STRUCT(
            'huérfanos de CLAVE' AS DETALLE,
            CAST(@huerfanos_clave AS NUMERIC) AS ESPERADO,
            CAST(
                (SELECT huerfanas.HUERFANOS_CLAVE FROM filas_huerfanas AS huerfanas) AS NUMERIC
            ) AS OBTENIDO
        )
    ]) AS cuadres
WHERE cuadres.ESPERADO != cuadres.OBTENIDO
