-- Dashboard scorecards: rows, IMPORTE, PIEZAS and weighted average price of one period.
WITH filtrada AS (
    SELECT
        vista.IMPORTE,
        vista.PIEZAS
    FROM farma_analytics.v_compras_farma_completa AS vista
    WHERE
        (ARRAY_LENGTH(@entidades) = 0 OR vista.ENTIDAD IN UNNEST(@entidades))
        AND (ARRAY_LENGTH(@instituciones) = 0 OR vista.INSTITUCION IN UNNEST(@instituciones))
        AND (
            ARRAY_LENGTH(@grupos_institucionales) = 0
            OR vista.GRUPO_INSTITUCIONAL IN UNNEST(@grupos_institucionales)
        )
        AND (
            ARRAY_LENGTH(@grupos_terapeuticos) = 0
            OR vista.GRUPO_TERAPEUTICO IN UNNEST(@grupos_terapeuticos)
        )
        AND (ARRAY_LENGTH(@moleculas) = 0 OR vista.MOLECULA IN UNNEST(@moleculas))
        AND vista.FECHA BETWEEN @fecha_inicio AND @fecha_fin
)

SELECT
    COUNT(*) AS FILAS,
    SUM(filtrada.IMPORTE) AS IMPORTE,
    SUM(filtrada.PIEZAS) AS PIEZAS,
    ROUND(SAFE_DIVIDE(SUM(filtrada.IMPORTE), SUM(filtrada.PIEZAS)), 2) AS PRECIO_PROMEDIO
FROM filtrada AS filtrada
