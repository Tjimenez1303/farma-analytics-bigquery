-- Dashboard scorecards by year (ANIO), with every filter except the date range.
WITH filtrada AS (
    SELECT
        vista.ANIO,
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
),

por_anio AS (
    SELECT
        filtrada.ANIO,
        COUNT(*) AS FILAS,
        SUM(filtrada.IMPORTE) AS IMPORTE,
        SUM(filtrada.PIEZAS) AS PIEZAS
    FROM filtrada AS filtrada
    GROUP BY filtrada.ANIO
)

SELECT
    por_anio.ANIO,
    por_anio.FILAS,
    por_anio.IMPORTE,
    por_anio.PIEZAS,
    ROUND(SAFE_DIVIDE(por_anio.IMPORTE, por_anio.PIEZAS), 2) AS PRECIO_PROMEDIO
FROM por_anio AS por_anio
ORDER BY por_anio.ANIO ASC
