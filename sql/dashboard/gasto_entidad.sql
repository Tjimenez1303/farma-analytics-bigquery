-- Dashboard bar chart and map of spending (IMPORTE) by ENTIDAD.
WITH filtrada AS (
    SELECT
        vista.ENTIDAD,
        vista.ENTIDAD_ISO,
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

por_entidad AS (
    SELECT
        filtrada.ENTIDAD,
        filtrada.ENTIDAD_ISO,
        SUM(filtrada.IMPORTE) AS IMPORTE
    FROM filtrada AS filtrada
    GROUP BY filtrada.ENTIDAD, filtrada.ENTIDAD_ISO
)

SELECT
    por_entidad.ENTIDAD,
    por_entidad.ENTIDAD_ISO,
    por_entidad.IMPORTE
FROM por_entidad AS por_entidad
ORDER BY por_entidad.IMPORTE DESC, por_entidad.ENTIDAD ASC
