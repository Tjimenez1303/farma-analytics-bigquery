# Contract: sección 4 de `sql/farma_analytics.sql`

La sección 4 tiene exactamente cuatro sentencias `SELECT` (o `WITH ... SELECT`), en este orden:
`P1`, `P2`, `P3` y `P3_CATALOGO`. Las preguntas, las definiciones y las columnas de salida están en
[../data-model.md](../data-model.md) y el diseño en [../research.md](../research.md) (R5).

## Forma de cada consulta

```text
-- Question N: <pregunta de negocio en inglés>.
-- Definition: <medida, fabricante, nivel y desempate que usa, en inglés>.
WITH <cte_con_nombre_descriptivo> AS (
    SELECT ... FROM farma_analytics.v_compras_farma_completa AS vista ... GROUP BY vista.<COL>, ...
)

SELECT <columnas finales con ROUND donde toca>
FROM <cte> AS <cte>
[QUALIFY ...]
ORDER BY ...
[LIMIT 5];
```

## Reglas que comprueban las pruebas locales (`tests/warehouse/test_queries_sql.py`)

1. Hay exactamente cuatro consultas después de la vista y nada más después de ellas.
2. Cada consulta tiene justo antes un comentario en inglés que empieza por `Question`.
3. La única relación que leen es `farma_analytics.v_compras_farma_completa`, con el alias `vista`.
   No mencionan `COMPRAS`, `CLUE_CAT` ni `CUADRO_BASICO` ni un ID de proyecto.
4. No hay `SELECT *`, `GROUP BY ALL`, `GROUP BY` con ordinales ni `SELECT DISTINCT` junto a
   `GROUP BY`.
5. `ROUND` aparece solo en el `SELECT` final y `ORDER BY` solo en la consulta más externa (no en las
   CTE).
6. Todo cociente usa `SAFE_DIVIDE`. `AVG` no recibe un cociente como argumento.
7. `P1` agrupa por `vista.MOLECULA`, usa `AVG(vista.IMPORTE)`, ordena por el importe total
   descendente y por `MOLECULA` ascendente, y termina en `LIMIT 5`.
8. `P2` usa `GROUP BY GROUPING SETS` con los tres conjuntos de R5, `UNPIVOT` sobre `IMPORTE` y
   `PIEZAS`, y `QUALIFY RANK() OVER (PARTITION BY ... ORDER BY ... DESC) = 1`.
9. `P3` agrupa por `vista.MOLECULA` y `vista.FABRICANTE_COMPRA`, y `P3_CATALOGO` por
   `vista.MOLECULA` y `vista.FABRICANTE_CATALOGO`. Las dos suman `vista.IMPORTE` y `vista.PIEZAS` en
   su CTE y calculan el precio en el `SELECT` final como `SAFE_DIVIDE` de esas dos sumas.
10. Los alias de columna de salida son los del modelo de datos, en UPPER_SNAKE_CASE.
11. Solo funcionalidades GA: no hay sintaxis pipe (`|>`) ni funciones en Preview.

## Cifras cruzadas (`make bq-consultas`, research R6)

| Regla | Comparación | Tolerancia |
|---|---|---|
| C1 | Σ `IMPORTE_TOTAL` y Σ `PIEZAS_TOTALES` de `P3` = totales de la vista | Exacta |
| C2 | Lo mismo con `P3_CATALOGO` | Exacta |
| C3 | `IMPORTE_TOTAL` y `PIEZAS_TOTALES` de cada molécula de `P1` = suma de sus filas en `P3` | Exacta |
| C4 | `PARTICIPACION_PCT` de `P1` y `P2` frente a `100 × valor / total` | 0.01 puntos (BigQuery redondea el cociente `NUMERIC` a 9 decimales) |
| C5 | En `P2`, el valor del líder de `INSTITUCION Y ENTIDAD` ≤ el líder de `INSTITUCION` y ≤ el de `ENTIDAD`, para cada medida | Exacta |

Antes de las reglas hay una condición previa: si la vista tiene 0 filas, `make bq-consultas` se
detiene antes de ejecutar las consultas con "La vista no tiene filas: ejecuta 'make bq-load'." y
sale con 1, porque sobre 0 filas C1 a C5 cuadrarían sin probar nada.

Los totales de la vista salen de `sql/ops/totales_vista.sql`:

```text
SELECT COUNT(*) AS FILAS, SUM(vista.IMPORTE) AS IMPORTE, SUM(vista.PIEZAS) AS PIEZAS
FROM farma_analytics.v_compras_farma_completa AS vista
```

Una regla que no cuadra produce una fila `CheckResult` con `CHEQUEO = 'cifras_cruzadas'`, y el
objetivo sale con código 1.

## Comportamiento en BigQuery (validación del quickstart)

- Cada consulta pasa por un dry run que estima bytes por debajo de `maximum_bytes_billed` (1 GiB).
- Las cuatro respuestas coinciden con las que muestra la consola al ejecutar el `.sql` completo.
