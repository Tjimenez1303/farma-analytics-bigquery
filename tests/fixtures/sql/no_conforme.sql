-- Breaks one style rule per case on purpose (used by tests).
select c.ENTIDAD, SUM(compras.IMPORTE) as MONTO_TOTAL,
FROM farma_analytics.COMPRAS compras
JOIN farma_analytics.CLUE_CAT c USING (CLUE)
WHERE compras.PIEZAS > 0 AND
    compras.IMPORTE >= 0 AND compras.FECHA >= '2024-01-01' AND compras.FECHA < '2025-01-01' AND compras.CLAVE IS NOT NULL
GROUP BY 1
