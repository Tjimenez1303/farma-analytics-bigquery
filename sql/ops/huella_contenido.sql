-- Rows and an order-independent content fingerprint per table, to show that a second load leaves
-- the tables unchanged. Not a check: it always returns three rows. The sum, unlike BIT_XOR, does
-- not cancel out duplicate rows, and BIGNUMERIC keeps it from overflowing.
SELECT
    'COMPRAS' AS TABLA,
    COUNT(*) AS FILAS,
    SUM(CAST(FARM_FINGERPRINT(TO_JSON_STRING(compras)) AS BIGNUMERIC)) AS HUELLA
FROM farma_analytics.COMPRAS AS compras

UNION ALL

SELECT
    'CLUE_CAT' AS TABLA,
    COUNT(*) AS FILAS,
    SUM(CAST(FARM_FINGERPRINT(TO_JSON_STRING(clue_cat)) AS BIGNUMERIC)) AS HUELLA
FROM farma_analytics.CLUE_CAT AS clue_cat

UNION ALL

SELECT
    'CUADRO_BASICO' AS TABLA,
    COUNT(*) AS FILAS,
    SUM(CAST(FARM_FINGERPRINT(TO_JSON_STRING(cuadro_basico)) AS BIGNUMERIC)) AS HUELLA
FROM farma_analytics.CUADRO_BASICO AS cuadro_basico
