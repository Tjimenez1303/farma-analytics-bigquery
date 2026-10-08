# Quickstart: validar la vista y las consultas analíticas

Guía de validación de punta a punta. Los pasos marcados **(dueño)** tocan GCP y los ejecuta el
dueño. Los demás son locales y no necesitan credenciales. Los comandos están detallados en
[contracts/make-targets.md](contracts/make-targets.md), la vista en
[contracts/vista.md](contracts/vista.md), las consultas en
[contracts/consultas.md](contracts/consultas.md) y el chequeo nuevo en
[contracts/checks.md](contracts/checks.md).

## Prerrequisitos

- Estado que deja la feature 003: `farma_analytics` con `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO`
  cargadas (300 000, 2 000 y 161 filas) y `make doctor` con 24 OK.
- La vista todavía no existe. Si existe de una prueba anterior, se puede borrar desde la consola
  antes de V2 para validar el recorrido desde cero. Esa decisión la toma el dueño.

## V0. Verificaciones locales

```bash
make test
```

Esperado: todas las pruebas en `passed`, incluidas `test_view_sql.py`, `test_queries_sql.py`, las
pruebas de comandos con el `bq` falso y las de cifras cruzadas.

```bash
make lint
```

Esperado: todos los hooks en `Passed`, con SQLFluff limpio sobre `sql/farma_analytics.sql` y
`sql/checks/07_reconciliacion_vista.sql`. Antes hay que hacer `git add` de los archivos nuevos.

```bash
make lint-prosa
```

Esperado: sin marcas en el README ni en `docs/trazabilidad.md`.

## V0b. `QUALIFY` sin `WHERE` (dueño, antes de escribir P2)

```bash
BIGQUERYRC="$PWD/.bigqueryrc" bq query --dry_run 'SELECT numero FROM UNNEST([1, 2, 3]) AS numero QUALIFY RANK() OVER (ORDER BY numero DESC) = 1'
```

Dry run gratis que no lee datos (research R5). `BIGQUERYRC` apunta al `.bigqueryrc` del
repositorio, igual que hace el `Makefile`, para que `bq` use GoogleSQL y la location del proyecto. Esperado: el mensaje de que la consulta procesará
0 bytes. Si responde que `QUALIFY` necesita `WHERE`, `GROUP BY` o `HAVING`, P2 usa el filtro
alternativo de R5.

## V1. Recarga sin vista: aviso sin fallo (dueño)

```bash
make bq-load
```

Esperado: tres tablas cargadas, seis chequeos en OK, el aviso "La vista no está desplegada: ejecuta
'make bq-vista'." y salida sin error. La vista sigue sin existir: la carga no la crea.

Es la única recarga de esta validación. La constitución pide no reescribir las tablas sin
necesidad, y este es el único caso que solo se puede comprobar en BigQuery real: la respuesta "not
found" de `bq show` para la vista. El caso de la carga con la vista ya desplegada lo cubren las
pruebas locales (`tests/warehouse/test_load_command.py`), y su verificación de la vista es la misma
que ejecutan `make bq-vista` y `make bq-checks`.

## V2. Desplegar la vista (dueño)

```bash
make bq-vista
```

Esperado: "CREATE OR REPLACE VIEW farma_analytics.v_compras_farma_completa: dry run OK (0 bytes
estimados), ejecutada", siete chequeos en OK (incluido `reconciliacion_vista`) y "Metadatos: 0
diferencias".

```bash
bq show --format=prettyjson farma_analytics.v_compras_farma_completa
```

`bq show` lee los metadatos sin crear un job. Esperado: `"type": "VIEW"`, `"useLegacySql": false`, la
descripción de la vista y 22 campos en `schema.fields`, en el orden del modelo de datos, cada uno con
`description`. `PIEZAS` y `ANIO` como `INTEGER`, `IMPORTE` como `NUMERIC`, `FECHA` y `MES` como
`DATE`.

## V2b. Descripciones en `INFORMATION_SCHEMA` (dueño, opcional)

La constitución verifica las descripciones con `INFORMATION_SCHEMA` (principio III). `bq show` ya
las comprobó sin costo. Este paso lo confirma con la vista de metadatos, que factura un mínimo de
10 MB:

```sql
SELECT
    column_paths.COLUMN_NAME,
    column_paths.DESCRIPTION
FROM farma_analytics.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS AS column_paths
WHERE column_paths.TABLE_NAME = 'v_compras_farma_completa'
```

Se ejecuta primero con `bq query --dry_run` y después con las labels del `Makefile`. Esperado: 22
filas, cada una con su descripción.

## V3. Redesplegar sin cambios (dueño)

```bash
make bq-vista
```

Esperado: la misma salida que en V2. Las descripciones siguen ahí y las tablas no cambian.

## V4. Chequeos con la vista desplegada (dueño)

```bash
make bq-checks
```

Esperado: "Chequeos: 7 de 7 en 0 filas. Metadatos: 0 diferencias." (SC-003).

## V5. Cada chequeo detecta su error (dueño)

```bash
make bq-checks-negativos
```

Esperado: "Casos negativos: 7 de 7 detectados." con 0 bytes estimados en cada caso (SC-004).

## V6. Las tres preguntas (dueño)

```bash
make bq-consultas
```

Esperado:

- P1 con 5 moléculas ordenadas por importe;
- P2 con un líder (o varios si hay empate) por nivel y medida;
- P3 con 497 filas y P3_CATALOGO con 139, de las que se muestran 20;
- "Cifras cruzadas: 5 de 5 cuadran." (SC-002);
- cada consulta con dry run y bytes estimados por debajo de 1 GiB (SC-006).

Se anotan las respuestas de P1 y P2 para compararlas en V8.

## V7. Tiempo del despliegue de la vista (dueño)

```bash
time make bq-vista
```

Esperado: la misma salida que en V2 y un tiempo que, sumado al de `time make bq-consultas` de V6,
queda por debajo de 5 minutos (SC-006). No recarga las tablas.

## V8. El entregable completo en la consola (dueño)

Abrir `sql/farma_analytics.sql`, pegar el archivo completo en el editor de BigQuery y ejecutarlo dos
veces. Esperado:

- todas las sentencias terminan sin error;
- las respuestas de P1 y P2 coinciden con las de V6;
- después de las dos ejecuciones, las tablas siguen con 300 000, 2 000 y 161 filas, y `make
  bq-checks` sigue en 7 de 7 (SC-005).

## Resultado

La feature está validada cuando V0 a V8 dan lo esperado:

- vista con 298 500 filas y el mismo `IMPORTE` que el `INNER JOIN`;
- siete chequeos y metadatos en 0;
- siete casos negativos detectados;
- tres preguntas respondidas con las cifras cruzadas cuadradas;
- `.sql` ejecutado de principio a fin en la consola.
