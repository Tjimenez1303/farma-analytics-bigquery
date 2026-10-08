# Quickstart de validación: Generador de datos sintéticos

**Feature**: `002-synthetic-data-generator` | **Fecha**: 2026-10-08

Esta guía demuestra que la feature cumple sus criterios de éxito. No es el README: el README
explica cómo regenerar los datos y esta guía valida cada criterio.

Quién ejecuta cada paso:

- **Dueño**: actualizar dependencias (`uv lock`, `make setup-dev`), porque instalan paquetes.
- **Claude o el dueño**: generar, verificar, probar y revisar la prosa. Son comandos locales que
  no tocan GCP ni instalan nada.

Detalles de cada comando: [contracts/cli-and-make.md](contracts/cli-and-make.md). Formato de los
archivos: [contracts/csv-format.md](contracts/csv-format.md) y
[contracts/manifest.md](contracts/manifest.md).

## Prerrequisitos

- Entorno de la feature 001 (`make setup-dev` ya ejecutado alguna vez).
- Tras añadir NumPy y Faker a `pyproject.toml`, el dueño ejecuta `uv lock` y `make setup-dev`
  para actualizar `uv.lock` y `.venv`.

## V1. Dos generaciones consecutivas dan el mismo manifiesto (SC-001)

1. `make data`
2. Copiar `data/manifest.json` a un archivo temporal.
3. `make data` otra vez.
4. Comparar los dos manifiestos con `cmp`.

**Resultado esperado**: las dos ejecuciones terminan con código 0, `cmp` no muestra diferencias y
`make data` informa `OK` para los tres archivos contra `generator/manifest.json`.

## V2. Un clon limpio reproduce el manifiesto versionado (SC-001, SC-009)

1. Clonar el repositorio en una carpeta nueva y ejecutar `make setup-dev`.
2. Siguiendo solo el README, ejecutar `make data`, cronometrando desde el clon.

**Resultado esperado**: `OK` en los tres archivos y menos de 10 minutos con el entorno preparado.
Si el clon está en otra plataforma y algún archivo sale `DIFIERE`, el mensaje muestra las versiones
de cada lado. Es una limitación documentada (aclaración sobre NumPy) y no un fallo de la feature.

## V3. Pruebas automatizadas (SC-002, SC-004, SC-005, SC-006, SC-007, SC-007a, SC-008)

`time make test`

**Resultado esperado**: todas las pruebas de `tests/generator/` y de la feature 001 pasan en menos
de dos minutos. Las pruebas cubren:

- determinismo (misma configuración, mismas huellas; otra semilla, otras huellas);
- contrato (encabezados, formato CSV, formatos de `CLUE` y `CLAVE`);
- integridad (unicidad de claves, huérfanos exactos y disjuntos, ausencia de vacíos);
- rangos (dominios de `PIEZAS`, `IMPORTE` y `FECHA`, los 32 nombres del INEGI, niveles de
  atención y bandas de precio al centavo);
- realismo (concentración, estacionalidad, coherencia de marcas y prefijos de CLUES, adhesión a
  IMSS-Bienestar);
- patrones P3, P4 y P5 con los umbrales de SC-007a;
- configuración inválida (código 2, nada escrito) y verificación con un archivo alterado (código 1).

## V4. Tamaño y tiempo de generación (SC-003)

1. `time make data`
2. `du -ch data/*.csv`

**Resultado esperado**: menos de dos minutos y menos de 100 MB en total.

## V5. Configuración inválida no destruye datos (historia 1, escenario 5)

1. Con una generación válida en `data/`, guardar `data/manifest.json` aparte.
2. Ejecutar `uv run python -m generator generate --config` con una copia de la configuración donde
   `orphan_rate = -0.1`.

**Resultado esperado**: código 2 y un mensaje que nombra `huerfanos.orphan_rate` y el rango
`[0, 0.05]`. `data/manifest.json` no cambia.

## V6. CI ejecuta las pruebas (FR-030a)

Abrir el PR de la feature y revisar los checks.

**Resultado esperado**: el job `tests` aparece junto a `pre-commit`, ejecuta pytest sin GCP y pasa.

## V7. Documentación honesta (SC-010, historia 4)

1. `make lint-prosa`
2. Leer la sección de datos del README y `docs/datos_sinteticos.md`.

**Resultado esperado**: el lint no reporta violaciones. El README declara que los datos son
sintéticos y explica `make data`. La documentación de los datos describe cada campo, cada patrón
inyectado (concentración, estacionalidad, huérfanos, P3, P4 y P5) con su parámetro y su valor, y
dice que fabricantes, marcas y proveedores son ficticios.

## Resultados de la validación (2026-10-08, macOS, Python 3.12.14, NumPy 2.5.3, Faker 40.39.0)

| Paso | Resultado |
|---|---|
| V1 | Dos `make data` seguidos dan manifiestos idénticos (`cmp` sin diferencias) y `OK` en los tres archivos. |
| V2 | Pendiente del dueño: clon limpio y cronómetro. |
| V3 | `make test`: 109 pruebas en verde en 41 s (55 del generador, unos 11 s). |
| V4 | `make data` en 1.4 s y 31 MB en total. |
| V5 | Código 2, mensaje `huerfanos.orphan_rate: valor -0.1 fuera de rango [0, 0.05]` y `data/manifest.json` sin cambios. |
| V6 | Pendiente del dueño: revisar los checks `pre-commit` y `tests` en el PR. |
| V7 | `make lint-prosa` sin marcas en README, `docs/datos_sinteticos.md` y `docs/trazabilidad.md`. |
