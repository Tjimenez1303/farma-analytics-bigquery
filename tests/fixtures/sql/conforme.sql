-- Style reference used by the SQLFluff configuration tests.
-- Total spend by state for valid purchase lines.
SELECT
    clue_cat.ENTIDAD,
    SUM(compras.IMPORTE) AS MONTO_TOTAL
FROM farma_analytics.COMPRAS AS compras
INNER JOIN farma_analytics.CLUE_CAT AS clue_cat
    ON compras.CLUE = clue_cat.CLUE
WHERE
    compras.PIEZAS > 0
    AND compras.IMPORTE >= 0
GROUP BY clue_cat.ENTIDAD
ORDER BY MONTO_TOTAL DESC
