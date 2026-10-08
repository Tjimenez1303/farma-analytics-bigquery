-- Is the implied price per piece (IMPORTE / PIEZAS) of each catalog CLAVE inside the bounds the
-- generator can produce, and is its spread between the cheapest and the dearest line plausible?
WITH precios_por_clave AS (
    SELECT
        compras.CLAVE,
        MIN(SAFE_DIVIDE(compras.IMPORTE, compras.PIEZAS)) AS PRECIO_MINIMO,
        MAX(SAFE_DIVIDE(compras.IMPORTE, compras.PIEZAS)) AS PRECIO_MAXIMO
    FROM farma_analytics.COMPRAS AS compras
    INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico
        ON compras.CLAVE = cuadro_basico.CLAVE
    GROUP BY compras.CLAVE
)

SELECT
    'precio_unitario' AS CHEQUEO,
    'CUADRO_BASICO.CLAVE' AS OBJETO,
    precios.CLAVE AS DETALLE,
    CONCAT(
        'entre ', CAST(@precio_minimo AS STRING), ' y ', CAST(@precio_maximo AS STRING),
        ', máximo hasta ', CAST(@dispersion_maxima AS STRING), ' veces el mínimo'
    ) AS ESPERADO,
    CONCAT(
        'mínimo ', CAST(precios.PRECIO_MINIMO AS STRING),
        ', máximo ', CAST(precios.PRECIO_MAXIMO AS STRING)
    ) AS OBTENIDO
FROM precios_por_clave AS precios
-- One cent rounding margin: prices are rounded to cents before IMPORTE is computed.
WHERE
    precios.PRECIO_MINIMO < @precio_minimo - NUMERIC '0.01'
    OR precios.PRECIO_MAXIMO > @precio_maximo + NUMERIC '0.01'
    OR precios.PRECIO_MAXIMO
    > @dispersion_maxima * (precios.PRECIO_MINIMO + NUMERIC '0.01') + NUMERIC '0.01'
