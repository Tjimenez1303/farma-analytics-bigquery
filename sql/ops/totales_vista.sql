-- Rows, IMPORTE and PIEZAS of the view. make bq-consultas checks the four answers against them.
SELECT
    COUNT(*) AS FILAS,
    SUM(vista.IMPORTE) AS IMPORTE,
    SUM(vista.PIEZAS) AS PIEZAS
FROM farma_analytics.v_compras_farma_completa AS vista
