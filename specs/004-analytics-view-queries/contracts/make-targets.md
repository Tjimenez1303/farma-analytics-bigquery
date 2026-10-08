# Contract: objetivos de `make` (cambios sobre la feature 003)

Las variables de entorno, los códigos de salida y las reglas de construcción de comandos no cambian:
ver
[../../003-bigquery-data-load/contracts/make-targets.md](../../003-bigquery-data-load/contracts/make-targets.md).
Todos los objetivos nuevos dependen de `require-venv` y `require-project` y los ejecuta el dueño.

## `make bq-vista` → `python -m warehouse vista` (nuevo)

1. Analiza `sql/farma_analytics.sql` y toma la sentencia `CREATE OR REPLACE VIEW`. Si no la hay,
   sale con 1.
2. Verificación de metadatos del dataset y de las tablas. Si falta alguno, sale con 1 con el mensaje
   "Falta <objeto>: ejecuta 'make bq-schema'".
3. `bq --project_id=P query --dry_run` con la sentencia por la entrada estándar. Si falla, sale con 1
   sin ejecutarla.
4. `bq --project_id=P query --label=project:farma-analytics --label=env:dev` con la sentencia.
5. Verificación de metadatos completa y los siete chequeos, igual que `bq-checks`.

Salida esperada (resumida):

```text
[1/1] CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa: dry run OK (0 bytes estimados), ejecutada
OK    conteo_filas: 0 filas (... bytes estimados)
...
OK    reconciliacion_vista: 0 filas (... bytes estimados)
Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias.
```

## `make bq-consultas` → `python -m warehouse consultas` (nuevo)

1. Analiza el `.sql` y exige exactamente cuatro consultas en la sección 4 (`P1`, `P2`, `P3` y
   `P3_CATALOGO`). Si no, sale con 1.
2. Comprueba con `bq show` que existe la vista. Si no, sale con 1 con el mensaje "Falta
   farma_analytics.v_compras_farma_completa: ejecuta 'make bq-vista'".
3. Ejecuta `sql/ops/totales_vista.sql` (dry run y labels). Si la vista tiene 0 filas, sale con 1
   con el mensaje "La vista no tiene filas: ejecuta 'make bq-load'." sin ejecutar las consultas.
4. Para cada consulta: dry run y después `bq --project_id=P --format=json query --label=...
   --max_rows=10000`. Si el dry run o la consulta fallan, sale con 1 indicando cuál. Si una consulta
   devuelve 10 000 filas, sale con 1 porque el resultado podría estar truncado.
5. Imprime `P1` y `P2` completas y, de `P3` y `P3_CATALOGO`, el número de filas y las 20 primeras.
6. Comprueba C1 a C5 con los totales del paso 3. Imprime
   "Cifras cruzadas: 5 de 5 cuadran." o las diferencias, y sale con 1 si alguna no cuadra.

Salida esperada (resumida, las cifras salen de BigQuery):

```text
P1 Las 5 moléculas con más importe (5 filas, ... bytes estimados)
MOLECULA  PIEZAS_TOTALES  IMPORTE_TOTAL  PRECIO_PROMEDIO  IMPORTE_PROMEDIO_LINEA  PARTICIPACION_PCT
...
P3 Precio promedio por molécula y fabricante de la compra (497 filas; se muestran 20, la consola muestra todas)
...
Cifras cruzadas: 5 de 5 cuadran.
```

## Cambios en objetivos existentes

- `make bq-schema`: sin cambios de comportamiento. Ignora la vista y las consultas al ejecutar, y su
  verificación de metadatos no incluye la vista.
- `make bq-load`: después de cargar ejecuta la verificación de metadatos y los chequeos según la
  tabla de [checks.md](checks.md). Si la vista no existe, imprime "La vista no está desplegada:
  ejecuta 'make bq-vista'." y no cuenta el chequeo 07 como fallo. No crea ni reemplaza la vista.
- `make bq-checks`: siete chequeos, y falla si falta la vista.
- `make bq-checks-negativos`: siete casos.
- `Makefile`: añade `bq-vista` y `bq-consultas` a `.PHONY` y a `make help`.

## Reglas de construcción de comandos (probadas sin GCP)

- Ningún comando repite `--location`, `--use_legacy_sql` ni `--maximum_bytes_billed`.
- Toda sentencia o consulta viaja por la entrada estándar.
- Cada job de consulta tiene antes un dry run con el mismo SQL, y labels.
- `--max_rows` solo se añade en las consultas de la sección 4 y en los chequeos.
