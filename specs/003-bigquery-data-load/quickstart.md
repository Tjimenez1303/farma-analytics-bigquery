# Quickstart: validar la carga en BigQuery

Guía de validación de punta a punta. Los pasos marcados **(dueño)** tocan GCP y los ejecuta el
dueño del proyecto. Los demás son locales y no necesitan credenciales. Los detalles de cada comando
están en [contracts/make-targets.md](contracts/make-targets.md) y los chequeos en
[contracts/checks.md](contracts/checks.md).

## Prerrequisitos

- Entorno de la feature 001: `make setup-dev` hecho, `gcloud` autenticado con ADC y el proyecto
  configurado (`GOOGLE_CLOUD_PROJECT` en `.env` o `gcloud config set project`).
- Datos de la feature 002: `make data` termina con los tres archivos en `OK`.

## V0. Verificaciones locales

```bash
make test
```

Ejecuta pytest, incluidas las pruebas nuevas de `tests/warehouse/` (DDL, esquema derivado, umbrales,
construcción de comandos con un ejecutor falso). Esperado: todas en `passed`.

```bash
make lint
```

Ejecuta pre-commit sobre el repositorio, incluido SQLFluff sobre `sql/`. Esperado: todos los hooks en
`Passed`. Antes hay que hacer `git add` de los archivos nuevos, porque `--all-files` no revisa los
archivos sin versionar.

```bash
make lint-prosa
```

Revisa el README y `docs/` (ya no revisa `.sql`). Esperado: sin marcas.

## V1. Diagnóstico antes de crear el dataset (dueño)

```bash
make doctor
```

Esperado: 23 OK y B03 "Location de farma_analytics" en OMITIDO ("el dataset aún no existe").

## V2. Crear el esquema (dueño)

```bash
make bq-schema
```

Esperado: cuatro sentencias con "dry run OK, ejecutada" y "Metadatos: 0 diferencias con la DDL".
Comprobación adicional:

```bash
bq show --format=prettyjson farma_analytics.COMPRAS
```

`bq show` lee los metadatos de la tabla sin crear un job (no cuesta). `--format=prettyjson` imprime
el JSON con sangría. Esperado: `schema.fields` con las 8 columnas en orden, `CLUE`, `CLAVE`,
`COD_PROVEEDOR`, `PIEZAS`, `IMPORTE` y `FECHA` con `"mode": "REQUIRED"`, `PIEZAS` como `INTEGER`,
`IMPORTE` como `NUMERIC`, `FECHA` como `DATE` y `description` en la tabla y en cada columna.

## V3. Los chequeos fallan con las tablas vacías (dueño)

```bash
make bq-checks
```

Esperado: `conteo_filas` en FALLO con tres filas (esperado 300000, 2000 y 161; obtenido 0),
`reconciliacion_join` en FALLO con dos filas (huérfanos de `CLUE` y de `CLAVE`: esperado 750,
obtenido 0), los otros cuatro chequeos en OK, metadatos sin diferencias y salida con error. Prueba
que un chequeo fallido detiene el objetivo.

## V3b. Cada chequeo detecta su error (dueño)

```bash
make bq-checks-negativos
```

Ejecuta cada chequeo de `sql/checks/` con unas pocas filas inventadas que traen un error a propósito
(por ejemplo, una `CLUE` repetida para el chequeo de unicidad), escritas dentro de la consulta en
lugar de las tablas reales. Esperado: seis líneas "detectó el error", "Casos negativos: 6 de 6
detectados.", 0 bytes estimados en cada dry run y salida sin error. No depende de que las tablas
tengan datos.

## V4. Primera carga (dueño)

Para medir SC-006, esta primera carga se ejecuta con `time` delante:

```bash
time make bq-load
```

`time` es un comando de la shell que ejecuta lo que va detrás y, al terminar, imprime cuánto tardó
(`real` es el tiempo de reloj). Esperado: los tres CSV en OK contra el manifiesto, tres cargas
terminadas, "Chequeos: 6 de 6 en 0 filas. Metadatos: 0 diferencias." (en particular, ninguna
diferencia en la descripción de las tablas después del reemplazo), los bytes estimados de cada
consulta muy por debajo de 1 GiB, la tabla de huellas con 300000, 2000 y 161 filas y `real` por
debajo de 10 minutos. Anotar las tres huellas.

## V5. Segunda carga idéntica (dueño)

```bash
make bq-load
```

Esperado: la misma salida que V4, con las mismas tres huellas (SC-004).

## V6. Re-ejecutar el esquema sobre tablas cargadas (dueño)

```bash
make bq-schema
```

Esperado: las cuatro sentencias ejecutadas sin error. Después, `make bq-checks` sigue con
`conteo_filas` en OK (SC-005): `CREATE ... IF NOT EXISTS` no tocó las tablas.

## V7. Diagnóstico final (dueño)

```bash
make doctor
```

Esperado: 24 OK, con B03 en OK y la location `US` (SC-003).

## V8. El entregable en la consola (dueño)

Abrir `sql/farma_analytics.sql`, pegar las secciones 1 y 2 en el editor de BigQuery y ejecutar.
Esperado: el validador de la consola no marca errores, las cuatro sentencias terminan y el conteo de
filas de las tablas no cambia.

## Resultado

La feature está validada cuando V0 a V8 dan lo esperado: tres tablas con los conteos del manifiesto,
seis chequeos y metadatos en 0, B03 en OK y una segunda carga con las mismas huellas.
