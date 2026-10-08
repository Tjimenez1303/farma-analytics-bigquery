-- Are PIEZAS positive, IMPORTE non-negative and FECHA inside the generator period?
WITH dominios AS (
    SELECT
        '> 0' AS PIEZAS_ESPERADO,
        '>= 0' AS IMPORTE_ESPERADO,
        COUNTIF(compras.PIEZAS <= 0) AS PIEZAS_FILAS,
        CONCAT('mínimo ', CAST(MIN(compras.PIEZAS) AS STRING)) AS PIEZAS_EXTREMO,
        COUNTIF(compras.IMPORTE < 0) AS IMPORTE_FILAS,
        CONCAT('mínimo ', CAST(MIN(compras.IMPORTE) AS STRING)) AS IMPORTE_EXTREMO,
        COUNTIF(compras.FECHA < @fecha_inicio OR compras.FECHA > @fecha_fin) AS FECHA_FILAS,
        CONCAT(
            'entre ', CAST(@fecha_inicio AS STRING), ' y ', CAST(@fecha_fin AS STRING)
        ) AS FECHA_ESPERADO,
        CONCAT(
            'mínima ', CAST(MIN(compras.FECHA) AS STRING),
            ', máxima ', CAST(MAX(compras.FECHA) AS STRING)
        ) AS FECHA_EXTREMO
    FROM farma_analytics.COMPRAS AS compras
),

-- One row per domain, without joins.
dominios_en_filas AS (
    SELECT
        violaciones.OBJETO,
        violaciones.FILAS,
        violaciones.ESPERADO,
        violaciones.EXTREMO
    FROM dominios AS dominios
    UNPIVOT (
        (FILAS, ESPERADO, EXTREMO) FOR OBJETO IN (
            (PIEZAS_FILAS, PIEZAS_ESPERADO, PIEZAS_EXTREMO) AS 'COMPRAS.PIEZAS',
            (IMPORTE_FILAS, IMPORTE_ESPERADO, IMPORTE_EXTREMO) AS 'COMPRAS.IMPORTE',
            (FECHA_FILAS, FECHA_ESPERADO, FECHA_EXTREMO) AS 'COMPRAS.FECHA'
        )
    ) AS violaciones
)

SELECT
    'dominios' AS CHEQUEO,
    dominios_en_filas.OBJETO,
    'filas fuera de dominio' AS DETALLE,
    dominios_en_filas.ESPERADO,
    CONCAT(
        CAST(dominios_en_filas.FILAS AS STRING), ' filas, ', dominios_en_filas.EXTREMO
    ) AS OBTENIDO
FROM dominios_en_filas AS dominios_en_filas
WHERE dominios_en_filas.FILAS > 0
