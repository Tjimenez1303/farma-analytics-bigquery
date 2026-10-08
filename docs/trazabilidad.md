# Matriz de trazabilidad

Cada requisito del proyecto aparece con el artefacto que lo cumple y la forma de verificarlo. Cada feature añade sus filas al terminar, y antes de la entrega la cobertura tiene que ser completa.

## Materiales e insumos

| Requisito | Artefacto | Verificación |
|---|---|---|
| Generar `COMPRAS` con los campos `CLUE`, `CLAVE`, `COD_PROVEEDOR`, `MARCA`, `FABRICANTE`, `PIEZAS`, `IMPORTE` y `FECHA` | `data/COMPRAS.csv`, producido por `make data` | `tests/generator/test_contract.py` compara el encabezado literal y el formato de cada campo |
| Generar `CLUE_CAT` con los campos `CLUE`, `ENTIDAD`, `INSTITUCION`, `DELEGACION`, `GRUPO_INSTITUCIONAL`, `NIVEL_ATENCION` y `MUNICIPIO` | `data/CLUE_CAT.csv`, producido por `make data` | `tests/generator/test_contract.py` y `tests/generator/test_realism.py` |
| Generar `CUADRO_BASICO` con los campos `CLAVE`, `DESCRIPCION`, `MOLECULA`, `GRUPO_TERAPEUTICO`, `PRESENTACION` y `FABRICANTE` | `data/CUADRO_BASICO.csv`, producido por `make data` | `tests/generator/test_contract.py` y `tests/generator/test_realism.py` |
| Entregar los datos en CSV o Parquet | CSV en UTF-8 sin BOM, según [el contrato de formato](../specs/002-synthetic-data-generator/contracts/csv-format.md) | `tests/generator/test_contract.py` comprueba la codificación, los saltos de línea y el encabezado |
| Poder reproducir los datos | Semilla y parámetros en `generator/config.toml`, manifiesto en `generator/manifest.json` | `make data` verifica las huellas SHA-256 y `tests/generator/test_determinism.py` genera dos veces y compara |

## Fase 1: carga en BigQuery

| Requisito | Artefacto | Verificación |
|---|---|---|
| Crear el dataset `farma_analytics` | Sección 1 de [`sql/farma_analytics.sql`](../sql/farma_analytics.sql), ejecutada con `make bq-schema` | `tests/warehouse/test_ddl.py` comprueba la location contra `.bigqueryrc` y las labels contra el `Makefile`. En BigQuery, `make bq-schema` termina sin diferencias de metadatos y `make doctor` deja B03 en OK |
| Crear `COMPRAS`, `CLUE_CAT` y `CUADRO_BASICO` con sus campos | Sección 2 de `sql/farma_analytics.sql` | `tests/warehouse/test_ddl.py` compara columnas, orden, tipos y modos con el modelo de datos y con el encabezado de los CSV |
| Definir `FECHA` como `DATE` y `PIEZAS` e `IMPORTE` como numéricos | `FECHA DATE`, `PIEZAS INT64` e `IMPORTE NUMERIC` en la sección 2, con `NOT NULL` en las claves y en esas tres columnas | `tests/warehouse/test_ddl.py` y la verificación de metadatos de `make bq-checks`, que lee el esquema publicado con `bq show` |
| Cargar las tres fuentes | `make bq-load`, que reemplaza cada tabla con `bq load` y el esquema derivado de la DDL | `tests/warehouse/test_load_command.py` y `tests/warehouse/test_schema_json.py`. En BigQuery, el chequeo `conteo_filas` da 300 000, 2 000 y 161 filas, y una segunda carga muestra la misma huella de contenido |
| Describir el dataset, cada tabla y cada columna | `OPTIONS (description = ...)` en las secciones 1 y 2 | `tests/warehouse/test_ddl.py` y la verificación de metadatos |
| Comprobar la calidad de los datos cargados | Seis consultas en [`sql/checks/`](../sql/checks), ejecutadas con `make bq-checks` y al final de cada carga | `tests/warehouse/test_checks_sql.py` y `tests/warehouse/test_checks_command.py`. En BigQuery, los seis chequeos devuelven 0 filas |
| Demostrar que cada chequeo detecta su error | Casos en [`sql/checks/negativos/`](../sql/checks/negativos), ejecutados con `make bq-checks-negativos` | `tests/warehouse/test_negative_checks.py`. En BigQuery, 6 de 6 casos detectados sin facturar bytes |
