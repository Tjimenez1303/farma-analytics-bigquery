-- Are the keys, FECHA, PIEZAS and IMPORTE free of NULL? Kept even with REQUIRED columns, so a
-- schema change that relaxes a mode does not go unnoticed.
WITH nulos_por_columna AS (
    SELECT
        (
            SELECT COUNTIF(compras.CLUE IS NULL)
            FROM farma_analytics.COMPRAS AS compras
        ) AS COMPRAS_CLUE,
        (
            SELECT COUNTIF(compras.CLAVE IS NULL)
            FROM farma_analytics.COMPRAS AS compras
        ) AS COMPRAS_CLAVE,
        (
            SELECT COUNTIF(compras.COD_PROVEEDOR IS NULL)
            FROM farma_analytics.COMPRAS AS compras
        ) AS COMPRAS_COD_PROVEEDOR,
        (
            SELECT COUNTIF(compras.PIEZAS IS NULL)
            FROM farma_analytics.COMPRAS AS compras
        ) AS COMPRAS_PIEZAS,
        (
            SELECT COUNTIF(compras.IMPORTE IS NULL)
            FROM farma_analytics.COMPRAS AS compras
        ) AS COMPRAS_IMPORTE,
        (
            SELECT COUNTIF(compras.FECHA IS NULL)
            FROM farma_analytics.COMPRAS AS compras
        ) AS COMPRAS_FECHA,
        (
            SELECT COUNTIF(clue_cat.CLUE IS NULL)
            FROM farma_analytics.CLUE_CAT AS clue_cat
        ) AS CLUE_CAT_CLUE,
        (
            SELECT COUNTIF(cuadro_basico.CLAVE IS NULL)
            FROM farma_analytics.CUADRO_BASICO AS cuadro_basico
        ) AS CUADRO_BASICO_CLAVE
),

-- One row per column, without joins.
nulos_en_filas AS (
    SELECT
        nulos.OBJETO,
        nulos.NULOS
    FROM nulos_por_columna AS nulos_por_columna
    UNPIVOT (
        NULOS FOR OBJETO IN (
            COMPRAS_CLUE AS 'COMPRAS.CLUE',
            COMPRAS_CLAVE AS 'COMPRAS.CLAVE',
            COMPRAS_COD_PROVEEDOR AS 'COMPRAS.COD_PROVEEDOR',
            COMPRAS_PIEZAS AS 'COMPRAS.PIEZAS',
            COMPRAS_IMPORTE AS 'COMPRAS.IMPORTE',
            COMPRAS_FECHA AS 'COMPRAS.FECHA',
            CLUE_CAT_CLUE AS 'CLUE_CAT.CLUE',
            CUADRO_BASICO_CLAVE AS 'CUADRO_BASICO.CLAVE'
        )
    ) AS nulos
)

SELECT
    'nulos' AS CHEQUEO,
    nulos_en_filas.OBJETO,
    'nulos' AS DETALLE,
    '0' AS ESPERADO,
    CAST(nulos_en_filas.NULOS AS STRING) AS OBTENIDO
FROM nulos_en_filas AS nulos_en_filas
WHERE nulos_en_filas.NULOS > 0
