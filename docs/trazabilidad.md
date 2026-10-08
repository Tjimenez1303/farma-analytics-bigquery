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

## Fase 2: consultas SQL y modelado

| Requisito | Artefacto | Verificación |
|---|---|---|
| Crear la vista `v_compras_farma_completa` | Sección 3 de [`sql/farma_analytics.sql`](../sql/farma_analytics.sql), desplegada con `make bq-vista` | `tests/warehouse/test_view_sql.py` comprueba el nombre, las 22 columnas, sus tipos y que la vista no agrega ni ordena. En BigQuery, `make bq-vista` termina con 7 de 7 chequeos en 0 y sin diferencias de metadatos |
| Unir `COMPRAS` con `CLUE_CAT` por `CLUE` y con `CUADRO_BASICO` por `CLAVE` con `INNER JOIN` | Los dos `INNER JOIN` de la sección 3 | `tests/warehouse/test_view_sql.py` comprueba los joins y sus condiciones. El chequeo `reconciliacion_vista` confirma 298 500 filas y el mismo `IMPORTE` que el `INNER JOIN` de las tablas |
| Describir la vista y cada columna | `OPTIONS (description = ...)` de la vista y de su lista de columnas | `tests/warehouse/test_view_sql.py` y la verificación de metadatos con `bq show`. `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` devuelve las 22 descripciones |
| Las 5 moléculas con más `IMPORTE` | Primera consulta de la sección 4 | `tests/warehouse/test_queries_sql.py`. En BigQuery, `make bq-consultas` comprueba que su importe coincide con la consulta de precios |
| La institución y la entidad con mayor volumen de compra | Segunda consulta de la sección 4 | `tests/warehouse/test_queries_sql.py`. En BigQuery, `make bq-consultas` comprueba sus participaciones y que el líder de la combinación no supera a los otros dos |
| El precio promedio por pieza por molécula y fabricante | Tercera y cuarta consultas de la sección 4 | `tests/warehouse/test_queries_sql.py`. En BigQuery, `make bq-consultas` comprueba que sus importes y piezas suman el total de la vista |
| Resolver las ambigüedades de las preguntas | Comentarios de cada consulta y la sección "View and analytical queries" del [README](../README.md) | Revisión de las definiciones y `make lint-prosa` |
| Comprobar la vista después de cada cambio | [`sql/checks/07_reconciliacion_vista.sql`](../sql/checks/07_reconciliacion_vista.sql) y su caso negativo | `tests/warehouse/test_checks_sql.py` y `tests/warehouse/test_negative_checks.py`. En BigQuery, `make bq-checks-negativos` detecta 7 de 7 casos sin facturar bytes |


## Fase 3: dashboard

| Requisito | Artefacto | Verificación |
|---|---|---|
| Conectar el dashboard a la vista | Fuente reutilizable de Data Studio sobre `v_compras_farma_completa`, con credenciales del propietario, descrita en [`docs/dashboard.md`](dashboard.md) | `tests/docs/test_dashboard_spec.py` compara la tabla de campos con las 22 columnas de la vista. El enlace de lectura abre con datos sin sesión de Google (sección "Compartir") |
| Filtro de fechas | Control Periodo sobre `FECHA`, con 2025 como rango fijo por defecto | `make bq-dashboard DESDE=... HASTA=...` reproduce cualquier rango. Registro de `docs/dashboard.md`: el botón Restablecer filtros devuelve 2025 |
| Filtro de entidad | Lista Entidad con búsqueda y selección múltiple | `make bq-dashboard ENTIDAD=Jalisco` coincide con el tablero en tarjetas, entidades, instituciones y top 10 (registro de `docs/dashboard.md`) |
| Filtro de institución y grupo institucional | Listas Institución y Grupo institucional, en cascada | `make bq-dashboard INSTITUCION=... GRUPO_INSTITUCIONAL=...`. Registro de `docs/dashboard.md`: con "Fuerzas Armadas y PEMEX", Institución ofrece PEMEX, SEDENA y SEMAR |
| Filtro de grupo terapéutico y molécula | Listas Grupo terapéutico y Molécula, en cascada | `make bq-dashboard GRUPO_TERAPEUTICO=... MOLECULA=...`. Registro de `docs/dashboard.md`: con Oncología, Molécula solo ofrece moléculas oncológicas |
| KPI Monto Total Comprado | Tarjeta con `SUM(Importe)` y comparación con el año anterior | `make bq-dashboard`: 14 941.7 M y +9.1 % en 2025, igual que el tablero |
| KPI Total de Piezas Adjudicadas | Tarjeta con `SUM(Piezas)` y comparación con el año anterior | `make bq-dashboard`: 28.55 M y +6.9 % en 2025, igual que el tablero |
| KPI Precio Promedio General por Pieza | Tarjeta con el campo calculado `SUM(Importe) / NULLIF(SUM(Piezas), 0)` | `tests/docs/test_dashboard_spec.py` comprueba que ninguna fórmula usa `AVG`. `make bq-dashboard`: 523.42 y +2.1 % en 2025, igual que el tablero |
| Gasto por entidad | Barras horizontales de las 32 entidades, con su abreviatura del INEGI, y mapa de México como complemento | `make bq-dashboard`: las 32 entidades coinciden en orden e importe. `tests/docs/test_dashboard_spec.py` comprueba la tabla de abreviaturas contra el catálogo |
| Participación por institución | Tabla con barras y "Porcentaje respecto al total" | `make bq-dashboard`: los 7 porcentajes coinciden y suman 100 %, también con Jalisco elegido |
| Top 10 de moléculas, entendido como los 10 pares molécula-fabricante con más importe (principio VI) | Tabla con Molécula, Fabricante, Piezas, Importe y Precio Promedio | `make bq-dashboard`: las 10 filas coinciden en orden, piezas, importe y precio, sin filtros y con Jalisco |
| Diseño claro y accesible | Tema, colores, rejilla y textos de `docs/dashboard.md` | `tests/docs/test_dashboard_spec.py` recalcula los contrastes con la fórmula de WCAG 2.1 y cuenta los tamaños de letra. Revisión del principio VI y prueba en escala de grises (registro de `docs/dashboard.md`) |
| Compartir el dashboard con un enlace de lectura | "Cualquier persona con el enlace puede ver", con el enlace en el README y en `docs/dashboard.md` | Comprobación sin sesión en el navegador integrado y en una ventana privada (sección "Compartir") |
