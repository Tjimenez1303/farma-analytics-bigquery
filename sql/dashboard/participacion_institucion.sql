-- Dashboard bar chart of each INSTITUCION share of the filtered IMPORTE.
WITH filtrada AS (
    SELECT
        vista.INSTITUCION,
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

por_institucion AS (
    SELECT
        filtrada.INSTITUCION,
        SUM(filtrada.IMPORTE) AS IMPORTE,
        SAFE_DIVIDE(SUM(filtrada.IMPORTE), SUM(SUM(filtrada.IMPORTE)) OVER ()) AS PARTICIPACION
    FROM filtrada AS filtrada
    GROUP BY filtrada.INSTITUCION
)

SELECT
    por_institucion.INSTITUCION,
    por_institucion.IMPORTE,
    ROUND(100 * por_institucion.PARTICIPACION, 4) AS PARTICIPACION_PCT
FROM por_institucion AS por_institucion
ORDER BY por_institucion.IMPORTE DESC, por_institucion.INSTITUCION ASC
