-- Does each table hold the row count recorded in the generator manifest?
SELECT
    'conteo_filas' AS CHEQUEO,
    conteos.OBJETO,
    'filas' AS DETALLE,
    CAST(conteos.ESPERADO AS STRING) AS ESPERADO,
    CAST(conteos.OBTENIDO AS STRING) AS OBTENIDO
FROM
    UNNEST([
        STRUCT(
            'COMPRAS' AS OBJETO,
            @filas_compras AS ESPERADO,
            (SELECT COUNT(*) FROM farma_analytics.COMPRAS AS compras) AS OBTENIDO
        ),
        STRUCT(
            'CLUE_CAT' AS OBJETO,
            @filas_clue_cat AS ESPERADO,
            (SELECT COUNT(*) FROM farma_analytics.CLUE_CAT AS clue_cat) AS OBTENIDO
        ),
        STRUCT(
            'CUADRO_BASICO' AS OBJETO,
            @filas_cuadro_basico AS ESPERADO,
            (SELECT COUNT(*) FROM farma_analytics.CUADRO_BASICO AS cuadro_basico) AS OBTENIDO
        )
    ]) AS conteos
WHERE conteos.ESPERADO != conteos.OBTENIDO
