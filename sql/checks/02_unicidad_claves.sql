-- Is each catalog key unique? A repeated key would multiply rows in the view and inflate IMPORTE.
SELECT
    'unicidad_claves' AS CHEQUEO,
    'CLUE_CAT.CLUE' AS OBJETO,
    clue_cat.CLUE AS DETALLE,
    '1' AS ESPERADO,
    CAST(COUNT(*) AS STRING) AS OBTENIDO
FROM farma_analytics.CLUE_CAT AS clue_cat
GROUP BY clue_cat.CLUE
HAVING COUNT(*) > 1

UNION ALL

SELECT
    'unicidad_claves' AS CHEQUEO,
    'CUADRO_BASICO.CLAVE' AS OBJETO,
    cuadro_basico.CLAVE AS DETALLE,
    '1' AS ESPERADO,
    CAST(COUNT(*) AS STRING) AS OBTENIDO
FROM farma_analytics.CUADRO_BASICO AS cuadro_basico
GROUP BY cuadro_basico.CLAVE
HAVING COUNT(*) > 1
