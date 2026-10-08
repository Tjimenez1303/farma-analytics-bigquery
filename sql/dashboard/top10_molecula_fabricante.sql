-- Dashboard table of the 10 MOLECULA and FABRICANTE_COMPRA pairs with the highest IMPORTE.
WITH filtrada AS (
    SELECT
        vista.MOLECULA,
        vista.FABRICANTE_COMPRA,
        vista.PIEZAS,
        vista.IMPORTE
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
),

por_par AS (
    SELECT
        filtrada.MOLECULA,
        filtrada.FABRICANTE_COMPRA,
        SUM(filtrada.PIEZAS) AS PIEZAS,
        SUM(filtrada.IMPORTE) AS IMPORTE
    FROM filtrada AS filtrada
    GROUP BY filtrada.MOLECULA, filtrada.FABRICANTE_COMPRA
)

SELECT
    por_par.MOLECULA,
    por_par.FABRICANTE_COMPRA,
    por_par.PIEZAS,
    por_par.IMPORTE,
    ROUND(SAFE_DIVIDE(por_par.IMPORTE, por_par.PIEZAS), 2) AS PRECIO_PROMEDIO
FROM por_par AS por_par
ORDER BY por_par.IMPORTE DESC, por_par.MOLECULA ASC, por_par.FABRICANTE_COMPRA ASC
LIMIT 10
