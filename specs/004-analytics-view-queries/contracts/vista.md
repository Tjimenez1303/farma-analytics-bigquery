# Contract: sección 3 de `sql/farma_analytics.sql`

## Estructura

```text
-- Section 3: view.
-- <comentario en inglés: qué es la vista, su grano y para qué existe>
CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa (
    <22 columnas: NOMBRE OPTIONS (description = '...')>
)
OPTIONS (
    description = '...'
)
AS
SELECT
    <22 elementos en el mismo orden que la lista>
FROM farma_analytics.COMPRAS AS compras
INNER JOIN farma_analytics.CUADRO_BASICO AS cuadro_basico
    ON compras.CLAVE = cuadro_basico.CLAVE
INNER JOIN farma_analytics.CLUE_CAT AS clue_cat
    ON compras.CLUE = clue_cat.CLUE;
```

Las columnas, los tipos y las descripciones están en [../data-model.md](../data-model.md). Las columnas
que pasan sin cambio de nombre van sin alias. `FABRICANTE_COMPRA`, `FABRICANTE_CATALOGO`, `ANIO`,
`MES` y `ENTIDAD_ISO` llevan alias con `AS` (research R2).

## Reglas que comprueban las pruebas locales (`tests/warehouse/test_view_sql.py`)

1. Existe exactamente una sentencia `CREATE OR REPLACE VIEW`, después de la última `CREATE TABLE` y
   antes de la primera consulta. No lleva `IF NOT EXISTS`.
2. La referencia es `farma_analytics.v_compras_farma_completa`: el dataset va calificado y no hay ID
   de proyecto en ninguna referencia de la sentencia.
3. La lista de columnas tiene 22 nombres, en el orden del modelo de datos, únicos sin distinguir
   mayúsculas, todos en UPPER_SNAKE_CASE y cada uno con una descripción que no está vacía.
4. La vista tiene descripción y no tiene `expiration_timestamp`.
5. El `SELECT` tiene 22 elementos y el nombre de salida de cada uno (alias o, si no hay, el nombre de
   la columna de origen) coincide, en la misma posición, con el nombre de la lista.
6. `FROM` empieza en `farma_analytics.COMPRAS AS compras`, seguido de dos `INNER JOIN` en este orden:
   `CUADRO_BASICO AS cuadro_basico ON compras.CLAVE = cuadro_basico.CLAVE` (161 filas) y
   `CLUE_CAT AS clue_cat ON compras.CLUE = clue_cat.CLUE` (2 000 filas), según el orden que recomienda
   la guía de rendimiento (research R1b). El orden de las columnas de la vista no cambia. No hay
   otro tipo de join, `USING` ni joins con coma.
7. Cada referencia de columna va calificada con `compras`, `clue_cat` o `cuadro_basico`.
8. La definición no contiene `SELECT *`, `DISTINCT`, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`,
   `WHERE`, `QUALIFY`, funciones de agregado o de ventana, `ROUND`, `SAFE_DIVIDE`, `CAST`, `TRIM`
   ni `REGEXP`.
9. `ENTIDAD_ISO` es un `CASE clue_cat.ENTIDAD` con exactamente 32 ramas `WHEN`, sin `ELSE`. Sus
   nombres son los de `generator/reference/entidades.csv` y sus códigos son los de la lista oficial
   ISO 3166-2:MX fijada en la prueba.
10. Los tipos que derivan `ViewSpec` y `DERIVED_TYPES` (research R4) coinciden con la columna Tipo del
    modelo de datos.
11. SQLFluff no informa violaciones en el archivo (también lo comprueba pre-commit).

## Comportamiento en BigQuery (validación del quickstart)

- `bq query --dry_run` de la sentencia termina bien y estima 0 bytes, porque la DDL no lee datos.
- Reejecutar la sentencia reemplaza la vista con la misma definición y las mismas descripciones.
- `bq show --format=json farma_analytics.v_compras_farma_completa` devuelve `type = VIEW`,
  `view.useLegacySql = false`, la descripción y los 22 campos de `schema.fields` con su descripción.
