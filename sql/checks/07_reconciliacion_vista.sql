-- Does the view keep every COMPRAS row that has a match in both catalogs, with the same IMPORTE
-- and PIEZAS as the INNER JOIN of the tables, and no NULL in its derived columns?
WITH totales_vista AS (
    SELECT
        COUNT(*) AS FILAS,
        COALESCE(SUM(vista.IMPORTE), 0) AS IMPORTE,
        COALESCE(SUM(vista.PIEZAS), 0) AS PIEZAS,
        COUNTIF(vista.ENTIDAD_ISO IS NULL) AS ENTIDAD_ISO_NULOS,
        COUNTIF(vista.ANIO IS NULL) AS ANIO_NULOS,
        COUNTIF(vista.MES IS NULL) AS MES_NULOS
    FROM farma_analytics.v_compras_farma_completa AS vista
),

totales_compras AS (
    SELECT COUNT(*) AS FILAS
    FROM farma_analytics.COMPRAS AS compras
),

-- Orphan rows, counted with NOT EXISTS so no outer join is needed.
filas_huerfanas AS (
    SELECT
        COUNTIF(
            NOT EXISTS (
                SELECT 1
                FROM farma_analytics.CLUE_CAT AS clue_cat
                WHERE clue_cat.CLUE = compras.CLUE
            )
            OR NOT EXISTS (
                SELECT 1
                FROM farma_analytics.CUADRO_BASICO AS cuadro_basico
                WHERE cuadro_basico.CLAVE = compras.CLAVE
            )
        ) AS FILAS
    FROM farma_analytics.COMPRAS AS compras
),

union_interna AS (
    SELECT
        COALESCE(SUM(compras.IMPORTE), 0) AS IMPORTE,
        COALESCE(SUM(compras.PIEZAS), 0) AS PIEZAS
    FROM farma_analytics.COMPRAS AS compras
    INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico
        ON compras.CLAVE = cuadro_basico.CLAVE
    INNER JOIN farma_analytics.CLUE_CAT AS clue_cat
        ON compras.CLUE = clue_cat.CLUE
)

SELECT
    'reconciliacion_vista' AS CHEQUEO,
    'v_compras_farma_completa' AS OBJETO,
    cuadres.DETALLE,
    CAST(cuadres.ESPERADO AS STRING) AS ESPERADO,
    CAST(cuadres.OBTENIDO AS STRING) AS OBTENIDO
FROM
    UNNEST([
        STRUCT(
            'filas: vista frente a COMPRAS menos huérfanas' AS DETALLE,
            CAST(
                (SELECT totales.FILAS FROM totales_compras AS totales)
                - (SELECT huerfanas.FILAS FROM filas_huerfanas AS huerfanas) AS NUMERIC
            ) AS ESPERADO,
            CAST((SELECT totales.FILAS FROM totales_vista AS totales) AS NUMERIC) AS OBTENIDO
        ),
        STRUCT(
            'IMPORTE: vista frente a INNER JOIN' AS DETALLE,
            (SELECT interna.IMPORTE FROM union_interna AS interna) AS ESPERADO,
            (SELECT totales.IMPORTE FROM totales_vista AS totales) AS OBTENIDO
        ),
        STRUCT(
            'PIEZAS: vista frente a INNER JOIN' AS DETALLE,
            CAST((SELECT interna.PIEZAS FROM union_interna AS interna) AS NUMERIC) AS ESPERADO,
            CAST((SELECT totales.PIEZAS FROM totales_vista AS totales) AS NUMERIC) AS OBTENIDO
        ),
        STRUCT(
            'ENTIDAD_ISO nulos' AS DETALLE,
            CAST(0 AS NUMERIC) AS ESPERADO,
            CAST(
                (SELECT totales.ENTIDAD_ISO_NULOS FROM totales_vista AS totales) AS NUMERIC
            ) AS OBTENIDO
        ),
        STRUCT(
            'ANIO nulos' AS DETALLE,
            CAST(0 AS NUMERIC) AS ESPERADO,
            CAST((SELECT totales.ANIO_NULOS FROM totales_vista AS totales) AS NUMERIC) AS OBTENIDO
        ),
        STRUCT(
            'MES nulos' AS DETALLE,
            CAST(0 AS NUMERIC) AS ESPERADO,
            CAST((SELECT totales.MES_NULOS FROM totales_vista AS totales) AS NUMERIC) AS OBTENIDO
        )
    ]) AS cuadres
WHERE cuadres.ESPERADO != cuadres.OBTENIDO
