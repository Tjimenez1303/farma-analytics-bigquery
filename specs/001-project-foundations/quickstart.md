# Quickstart de validación: Fundaciones del proyecto

**Feature**: `001-project-foundations` | **Fecha**: 2026-10-07

Esta guía demuestra que la feature funciona de extremo a extremo. No es el README: el README
explica el arranque para cualquier persona y esta guía valida cada criterio de éxito.

Quién ejecuta cada paso:

- **Dueño**: todo lo que toca GCP, autentica o instala herramientas.
- **Claude**: solo verificaciones locales que leen o revisan archivos del repositorio (lint,
  pytest), sin red de GCP ni instalaciones.

Detalles de cada comando: [contracts/make-targets.md](contracts/make-targets.md),
[contracts/doctor.md](contracts/doctor.md) y [contracts/lint-prosa.md](contracts/lint-prosa.md).

## Prerrequisitos

- Herramientas de [data-model.md](data-model.md#3-catálogo-de-prerrequisitos) instaladas, uv
  incluido. Python no hace falta instalarlo: uv descarga la versión de `.python-version`.
- Una cuenta de facturación de Google Cloud con permiso para asociar proyectos y crear
  presupuestos.

## V1. Arranque desde un clon limpio (SC-001)

**Dueño**, con un cronómetro:

1. Clonar el repositorio en una carpeta nueva.
2. Seguir el arranque rápido del README paso a paso: crear el proyecto, asociar la facturación,
   habilitar APIs, autenticarse, crear `.env`, `make setup-dev` y `make gcp-setup`.
3. Ejecutar `make doctor`.

**Resultado esperado**: todos los chequeos en `OK` (o `OMITIDO` en B03, porque el dataset aún no
existe), código de salida 0 y menos de 15 minutos sin contar la instalación de herramientas.

## V2. El diagnóstico no factura (SC-002)

**Dueño**:

1. `time make doctor`.
2. En la consola de BigQuery, abrir el historial de jobs del proyecto.

**Resultado esperado**: el diagnóstico tarda 60 segundos o menos y el historial no muestra ningún
job creado por él. Si aparecieran los dry runs, se anota y SC-002 se reformula para exigir 0 bytes
facturados en lugar de 0 jobs.

## V3. Fallos inducidos (SC-003)

**Claude**: `make test` ejecuta `tests/test_doctor.py`, que reproduce los 8 escenarios con stubs.

**Resultado esperado**: 8 de 8 escenarios marcan el chequeo correcto como `FALLO`, muestran remedio
y terminan con código 1.

**Dueño** (muestra real, opcional): renombrar temporalmente `~/.config/gcloud/application_default_credentials.json`,
ejecutar `make doctor`, comprobar que A02 está en `FALLO` con el comando de login y restaurar el
archivo.

## V4. El dry run discrimina el dialecto (R2, SC-004)

**Dueño**, una sola vez y antes de `make gcp-dialect`:

1. `make doctor`: B02 debe salir en `FALLO` (el dry run en legacy SQL se valida).
2. `make gcp-dialect` y esperar unos minutos.
3. `make doctor`: B02 debe salir en `OK` (el dry run en legacy SQL es rechazado).
4. En la consola de BigQuery, cambiar una consulta a legacy SQL en la configuración y ejecutar
   `SELECT 1`. La documentación no garantiza el rechazo en la consola, así que se anota el
   resultado (rechazada o no) y Claude lo documenta en el README.

**Resultado esperado**: B02 cambia de `FALLO` a `OK`. Si en el paso 3 sigue en `FALLO` después de
10 minutos, se activa el fallback de R2 y se documenta en el README.

## V5. Límite de bytes (SC-005)

**Dueño**, desde una terminal con `export BIGQUERYRC=$PWD/.bigqueryrc`:

1. Dry run de una consulta sobre una tabla pública grande, por ejemplo
   `bq --project_id=<P> query --dry_run 'SELECT * FROM \`bigquery-public-data.github_repos.contents\`'`.
   Debe estimar bastante más de 1 GiB.
2. La misma consulta sin `--dry_run`, para comprobar que el límite la detiene.

**Resultado esperado**: el dry run muestra una estimación mayor que 1 GiB, la ejecución falla con
un error de límite de bytes facturados antes de leer datos y el historial muestra 0 bytes
facturados.

## V6. Idempotencia de los ajustes (SC-006)

**Dueño**: ejecutar `make gcp-setup` dos veces seguidas.

**Resultado esperado**: la segunda ejecución termina sin errores, en la cuenta de facturación hay
un solo presupuesto `farma-analytics-bigquery`, la cuota `QueryUsagePerDay` muestra el valor de `QUERY_QUOTA_GIB_PER_DAY` (100 GiB por día por defecto)
y B02 sigue en `OK`.

## V7. Bloqueo de credenciales (SC-007)

**Claude** (en una rama desechable, sin push):

1. Crear `.env`, un `.df-credentials.json` y un JSON con una clave privada falsa.
2. Intentar `git add` y `git commit` de cada uno.

**Resultado esperado**: los tres commits se bloquean con el nombre del archivo y el hook que lo
detuvo. Después se borran los archivos de prueba y la rama.

## V8. Estilo SQL (SC-008)

**Claude**: `make test` ejecuta `tests/test_sqlfluff_config.py`.

**Resultado esperado**: `conforme.sql` con 0 violaciones y cada violación sembrada en
`no_conforme.sql` detectada con su regla.

## V9. Lint de prosa (SC-009)

**Claude**:

1. `make test` ejecuta `tests/test_lint_prosa.py`.
2. `make lint-prosa` sobre el repositorio.

**Resultado esperado**: una marca por cada violación sembrada, 0 marcas en `limpio.md` y 0 marcas
en el README.

## V10. Check de CI en el PR (SC-010)

**Claude**: en la rama desechable de V7, añadir también un `.sql` no conforme fuera de
`tests/fixtures/` y comprobar que `make lint` (el mismo comando que ejecuta CI) falla. Después se
borra.

**Dueño y Claude**: al abrir el PR de la implementación, comprobar que aparece el check de GitHub
Actions en verde. Para la prueba negativa, y solo con el permiso del dueño en ese momento,
Claude añade en una rama desechable un `.sql` no conforme y abre un PR en borrador.

**Resultado esperado**: `make lint` falla en local con el `.sql` no conforme, el check sale en
verde en el PR real y, si se aprueba la parte opcional, en rojo en el PR desechable. El PR
desechable se cierra sin merge y su rama se borra.

## Resultados de la validación (2026-10-08, proyecto del dueño)

| Validación | Resultado |
|---|---|
| V1 | Arranque del README ejecutado de principio a fin en la copia de trabajo, con todos los pasos correctos. No se cronometró en un clon limpio. |
| V2 | `make doctor` en 10 s. `bq ls -j` no muestra ningún job del diagnóstico. |
| V3, V8, V9 | `make test`: 54 pruebas en verde con ripgrep 15.2.0. |
| V4 | B02 en `FALLO` antes de `make gcp-dialect` y en `OK` después ("Legacy SQL queries are not supported"). En la consola, `#legacySQL` también se rechaza. El dry run del `ALTER PROJECT` se acepta. |
| V5 | Dry run de `samples.wikipedia`: 38.324.173.849 bytes. La ejecución falla con "Query exceeded limit for bytes billed: 1073741824". |
| V6 | Segunda ejecución de `make gcp-setup`: el presupuesto se actualiza (uno solo), y la cuota y el dialecto quedan igual. |
| V7 | `.env`, `.df-credentials.json` y una clave privada falsa, bloqueados por los hooks. |
| V10 | `make lint` falla en local con un `.sql` no conforme. El check del PR se comprueba al abrirlo. |
