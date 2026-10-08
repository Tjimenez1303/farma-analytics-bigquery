---

description: "Task list for feature 002-synthetic-data-generator"
---

# Tasks: Generador de datos sintéticos (COMPRAS, CLUE_CAT y CUADRO_BASICO)

**Input**: Design documents from `specs/002-synthetic-data-generator/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluidos. La spec los exige (FR-030 y FR-030a) y el principio IV fija pytest para el
generador. Se escriben antes de la implementación de cada historia y deben fallar primero.

**Organization**: tareas agrupadas por historia de usuario para implementarlas y probarlas por
separado.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia a la que pertenece (US1 a US4).
- **[Dueño]** al inicio de la descripción: la ejecuta el dueño del repositorio porque instala
  paquetes. Claude escribe archivos y ejecuta verificaciones locales (`make test`, `make lint`,
  `make lint-prosa`, pytest). Las tareas que escriben en `data/` llevan "Claude, con permiso del
  dueño".

## Reglas transversales (aplican a todas las tareas)

- Python 3.12 con anotaciones de tipo en todas las funciones públicas, `from __future__ import
  annotations`, `dataclasses` inmutables (`frozen=True`) para la configuración y los registros, y
  `pathlib.Path` para rutas. Docstrings y comentarios en inglés, breves, que dicen qué es cada cosa.
- Los mensajes que ve el usuario (salida de la línea de comandos, errores de validación, ayuda de
  `make`) van en español. Los nombres de campo, archivo y parámetro se escriben tal cual.
- Determinismo: nada depende de `datetime.now`, `time`, `random` de la biblioteca estándar,
  `hash()`, el orden de un `set`, el locale, la zona horaria ni el directorio de trabajo. Todo el
  azar sale de los flujos de `generator/rng.py`. Cada llamada a NumPy tiene un tamaño fijo que no
  depende del entorno (research R2).
- Ningún parámetro numérico de la generación vive fuera de `generator/config.toml` (FR-005). Los
  catálogos de `generator/reference/` solo contienen datos de referencia.
- Dinero siempre en centavos enteros (`int` o `numpy.int64`) hasta el momento de escribir
  (research R4).
- Ningún archivo versionado menciona el documento de requisitos de origen ni contiene IDs de
  proyecto, correos o credenciales.
- Fuentes de los catálogos de referencia: solo las oficiales citadas en research.md (INEGI, DGIS,
  DOF, Compendio). Claude puede consultarlas con WebFetch y transcribe los datos sin inventarlos.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, configuración de pytest y esqueleto del paquete.

- [X] T001 [P] Añadir `data/` a `.gitignore` en un bloque `# Generated data` debajo de `# Local environments and dependencies`, sin tocar las líneas actuales
- [X] T002 Editar `pyproject.toml`: añadir en `[project]` la lista `dependencies = ["faker==40.39.0", "numpy==2.5.3"]` (versiones exactas, research R1); añadir `"ruff==0.16.8"` al grupo `dev` de `[dependency-groups]` (research R18); añadir una tabla `[tool.pytest]` con configuración nativa de pytest 9: `testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = ["--import-mode=importlib", "-ra"]` y `strict = true` (research R19); y añadir `[tool.ruff]` con `line-length = 100` y `[tool.ruff.lint]` con `extend-select = ["B", "I", "UP"]`, sin `target-version` (Ruff lo deduce de `requires-python`). Sin tocar `[tool.uv]`
- [X] T003 [Dueño] Ejecutar `uv lock` en la raíz para regenerar `uv.lock` con NumPy y Faker (depende de T002)
- [X] T004 [Dueño] Ejecutar `make setup-dev` para sincronizar `.venv` con el nuevo `uv.lock` (depende de T003)
- [X] T005 Ejecutar `make test` (configuración en `pyproject.toml`, pruebas en `tests/`) y confirmar que las pruebas de la feature 001 siguen pasando con `--import-mode=importlib` y `strict = true`. Si alguna falla por la configuración nueva, corregir la configuración, no las pruebas (depende de T004)
- [X] T006 [P] Crear `generator/__init__.py` con un docstring de una línea y sin `__version__` (el proyecto no se empaqueta), y la carpeta `generator/reference/`
- [X] T007 Añadir a `.pre-commit-config.yaml` un bloque `repo: local` con dos hooks que usan el Ruff de `.venv` (misma fuente de versión que SQLFluff): `ruff-check` (`entry: .venv/bin/ruff check`, `language: unsupported`, `types: [python]`) y `ruff-format` (`entry: .venv/bin/ruff format --check`, `language: unsupported`, `types: [python]`), en ese orden y sin `--fix`, con un comentario breve en inglés (research R18; depende de T004)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: catálogos de referencia, configuración, flujos aleatorios, escritura, manifiesto,
línea de comandos, objetivos de `make` y utilidades de pruebas que usan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza hasta terminar esta fase.

### Catálogos de referencia

- [X] T008 [P] Crear `generator/reference/entidades.csv` (UTF-8, LF, encabezado `cve_ent,entidad,codigo_clues,poblacion_2020,imss_bienestar,sedena,semar,pemex`) con las 32 entidades ordenadas por `cve_ent` (`01` a `32`). `entidad` copia literalmente `nomgeo` del servicio del INEGI <https://gaia.inegi.org.mx/wscatgeo/v2/mgee/> (por ejemplo "Coahuila de Zaragoza", "Ciudad de México", "México", "Michoacán de Ocampo", "Veracruz de Ignacio de la Llave"). `poblacion_2020` es la población del Censo 2020 que devuelve el mismo servicio o, si no la incluye, la de los tabulados del Censo 2020 del INEGI. `codigo_clues` es el código de dos letras del catálogo de entidades de la CURP (`AS`, `BC`, `BS`, `CC`, `CL`, `CM`, `CS`, `CH`, `DF`, `DG`, `GT`, `GR`, `HG`, `JC`, `MC`, `MN`, `MS`, `NT`, `NL`, `OC`, `PL`, `QT`, `QR`, `SP`, `SL`, `SR`, `TC`, `TS`, `TL`, `VZ`, `YN`, `ZS`), contrastado con claves CLUES públicas de la DGIS. `imss_bienestar` es `0` solo en Aguascalientes, Chihuahua, Coahuila de Zaragoza, Durango, Guanajuato, Jalisco, Nuevo León y Querétaro, y `1` en las demás. `sedena`, `semar` y `pemex` son `1` en las entidades donde los datos abiertos CLUES 2022 de la DGIS registran unidades en operación de esa institución (29, 18 y 16 entidades) (research R6 y R7)
- [X] T009 [P] Crear `generator/reference/municipios.csv` (encabezado `cve_ent,cve_mun,municipio,poblacion_2020`, ordenado por `cve_ent` y `cve_mun`) con, por cada entidad, la capital y los municipios más poblados hasta sumar entre 5 y 10, tomados del servicio del INEGI `https://gaia.inegi.org.mx/wscatgeo/v2/mgem/<cve_ent>` con el nombre literal de `nomgeo`. En la Ciudad de México se listan sus alcaldías con el mismo criterio (research R9)
- [X] T010 [P] Crear `generator/reference/instituciones.csv` (encabezado `institucion,prefijo_clues,grupo_institucional,prefijo_delegacion,presencia`) con siete filas exactas: `IMSS,IMS,Seguridad social,OOAD,todas`; `ISSSTE,IST,Seguridad social,Oficina de Representación,todas`; `SEDENA,SDN,Fuerzas Armadas y PEMEX,Servicios de Sanidad Militar,sedena`; `SEMAR,SMA,Fuerzas Armadas y PEMEX,Sanidad Naval,semar`; `PEMEX,PMX,Fuerzas Armadas y PEMEX,Servicios de Salud PEMEX,pemex`; `IMSS-Bienestar,IMO,Población sin seguridad social,Coordinación Estatal,imss_bienestar`; `Servicios Estatales de Salud,SSA,Población sin seguridad social,Servicios de Salud,no_imss_bienestar` (research R7, FR-019 y FR-019a)
- [X] T011 [P] Crear `generator/reference/moleculas.csv` (encabezado `molecula,grupo_terapeutico,nivel_precio,presentaciones`) con unas 140 moléculas reales por su denominación genérica en español, ordenadas por `molecula`. `grupo_terapeutico` usa los nombres de los grupos de medicamentos del Compendio Nacional de Insumos para la Salud, contrastados con la edición 2025 publicada en el DOF, y cada molécula pertenece a uno solo. `nivel_precio` es `bajo`, `medio`, `alto` o `muy_alto`. `presentaciones` lista de 1 a 3 presentaciones separadas por `|`, cada una con los campos `forma;unidad;concentración;envase` (por ejemplo `Tableta;tableta;500 mg;Envase con 10 tabletas`). Debe incluir al menos 8 moléculas del grupo "Oncología", las moléculas de P3 y P5 ("Clopidogrel" con `nivel_precio` `medio`, "Atorvastatina" con `medio` e "Insulina glargina" con `alto`) y también "Losartán" y "Metformina" como moléculas normales (research R8, R10 y R11)
- [X] T012 [P] Crear `generator/reference/laboratorios_reales.txt` con un nombre o raíz por línea, en minúsculas y sin acentos, de al menos 50 laboratorios farmacéuticos reales que operan en México, multinacionales y mexicanos (por ejemplo `pfizer`, `sanofi`, `pisa`, `silanes`, `senosiain`, `liomont`, `sanfer`, `landsteiner`, `probiomed`, `psicofarma`, `chinoin`, `grossman`, `carnot`, `raam`, `birmex`), ordenados alfabéticamente (research R3)

### Configuración, flujos aleatorios y lectura de referencia

- [X] T013 Crear `generator/config.toml` con la estructura y los valores de partida de [contracts/config.md](contracts/config.md). La semilla se genera una sola vez con `python3 -c "import secrets; print(hex(secrets.randbits(128)))"` y se guarda como texto (`seed = "0x..."`). Comentarios en inglés, uno por tabla
- [X] T014 Crear `generator/config.py` con `load_config(path: Path) -> Config`: lee con `tomllib`, convierte a `dataclasses` inmutables y aplica todas las reglas de la tabla "Reglas de validación" de [contracts/config.md](contracts/config.md), incluidas la de claves desconocidas, `genericos_por_molecula` frente a `fabricantes_genericos`, `moleculas_destacadas` y `patrones.p3.molecula_ejemplo`. Cada fallo lanza `ConfigError` con el mensaje `"<ruta.del.parametro>: valor <v> fuera de rango <rango>"` (o la variante que corresponda), que la línea de comandos convierte en código 2. Las reglas que dependen de los catálogos (instituciones, niveles de precio, grupos terapéuticos y moléculas) se validan contra los datos de `generator/reference.py`
- [X] T015 [P] Crear `generator/rng.py` con `make_streams(seed: str) -> Streams`: convierte la semilla hexadecimal en entero, crea `numpy.random.SeedSequence(entero)` y obtiene con `spawn` un `numpy.random.Generator` por componente en este orden fijo: `units`, `supplies`, `companies`, `purchases`, `orphans` y `faker`. Expone además `faker_seed(streams) -> int`, que devuelve `int(ss.generate_state(1, dtype=np.uint64)[0])` del `SeedSequence` hijo `faker` (no de `companies`), para `Faker.seed_instance` (research R2 y R3)
- [X] T016 [P] Crear `generator/reference.py` con funciones que leen cada archivo de `generator/reference/` con `csv.DictReader` (UTF-8) y devuelven tuplas de `dataclasses` inmutables ordenadas por su clave, y que fallan con un mensaje claro si falta una columna. `moleculas.csv` separa `presentaciones` por `|`

### Escritura, manifiesto y línea de comandos

- [X] T017 [P] Crear `generator/writer.py` según [contracts/csv-format.md](contracts/csv-format.md): `format_importe(centavos: int) -> str` (`f"{c // 100}.{c % 100:02d}"`), `write_csv(path, header, rows)` con `open(path, "w", encoding="utf-8", newline="")` y `csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)`, y un gestor de contexto `staging(out_dir)` que primero crea `out_dir` con `out_dir.mkdir(parents=True, exist_ok=True)` (en un clon limpio `data/` no existe), después un directorio temporal con `tempfile.mkdtemp(prefix=".tmp-", dir=out_dir)`, al confirmar mueve cada CSV con `os.replace` y escribe `manifest.json` al final, y si hay una excepción borra el temporal sin tocar `out_dir` (research R15)
- [X] T018 [P] Crear `generator/manifest.py` según [contracts/manifest.md](contracts/manifest.md): `file_entry(path) -> dict` con `hashlib.file_digest(f, "sha256")`, `bytes` del tamaño en disco y `rows` sin el encabezado; `build_manifest(config_bytes, files, orphans) -> dict` con `format_version = 1` y `versions` (`platform.python_version()`, `importlib.metadata.version("numpy")` e `importlib.metadata.version("faker")`); `dumps(manifest) -> str` con `json.dumps(..., sort_keys=True, indent=2, ensure_ascii=False) + "\n"`; y `compare(expected, actual) -> list[str]` que devuelve una línea en español por cada diferencia (archivo ausente, `sha256`, `bytes`, `rows`, `config_sha256`, `orphans`) y, si hay diferencias y las `versions` no coinciden, una línea final con las versiones de cada lado
- [X] T019 Crear `generator/__main__.py` con `argparse` y los subcomandos `generate` (`--config`, por defecto `generator/config.toml`; `--out`, por defecto `data`) y `verify` (`--manifest`, por defecto `generator/manifest.json`; `--data`, por defecto `data`) de [contracts/cli-and-make.md](contracts/cli-and-make.md). Códigos de salida: 0 correcto, 1 diferencias o archivo ausente en `verify`, 2 `ConfigError` o argumentos inválidos. `generate` imprime una línea por archivo con nombre, filas y los 12 primeros caracteres del SHA-256, más los conteos de huérfanos. Sin fechas ni horas en la salida (depende de T014, T017 y T018)
- [X] T020 Añadir al `Makefile` los objetivos `data` (`uv run python -m generator generate` seguido de `uv run python -m generator verify`), `data-verify` (`uv run python -m generator verify`) y `data-manifest` (falla con código 1 y el mensaje "Falta data/manifest.json: ejecuta 'make data' antes." si no existe; si existe, `cp data/manifest.json generator/manifest.json`), los tres con `require-venv` como prerrequisito, comentario `## ` en español y añadidos a `.PHONY` (contrato [cli-and-make.md](contracts/cli-and-make.md))

### Utilidades de pruebas

- [X] T021 [P] Crear `tests/generator/fixtures/config_small.toml`: copia de la estructura de `generator/config.toml` con otra semilla fija y `lineas_compra = 20000`, `unidades_medicas = 400`, `fabricantes = 15` y `proveedores = 20`, con el mismo periodo, `orphan_rate` y patrones
- [X] T022 Crear `tests/generator/conftest.py` con: `run_generator(args, cwd)` que ejecuta `sys.executable -m generator ...` con `subprocess.run` y devuelve código, stdout y stderr; un fixture de sesión `full_dataset` que genera una vez la configuración por defecto en `tmp_path_factory.mktemp("full")` y devuelve la ruta; un fixture `small_config` con la ruta de `tests/generator/fixtures/config_small.toml`; y `read_csv(path) -> tuple[list[str], list[dict[str, str]]]` que devuelve encabezado y filas leídos con `csv` en UTF-8 (depende de T019 y T021)

**Checkpoint**: base lista. Las historias pueden empezar.

---

## Phase 3: User Story 1 - Regenerar los datos de forma reproducible con un comando (Priority: P1) 🎯 MVP

**Goal**: `make data` produce los tres CSV y el manifiesto, dos ejecuciones dan los mismos bytes y
la verificación compara contra la copia versionada.

**Independent Test**: `make data` dos veces seguidas con manifiestos idénticos y `OK` contra
`generator/manifest.json` (quickstart V1). Configuración inválida, código 2 y nada escrito
(quickstart V5).

### Tests for User Story 1 ⚠️

- [X] T023 [P] [US1] Escribir `tests/generator/test_determinism.py`: dos ejecuciones de `generate` con `small_config` en directorios distintos producen los tres CSV y `manifest.json` idénticos byte a byte; con otra semilla (copia temporal de la configuración) las huellas de los tres CSV cambian; la salida no depende de la variable de entorno `TZ` ni de `LC_ALL` (ejecutar con valores distintos y comparar huellas); `generator.pipeline.generate` termina bien en el mismo proceso con `socket.socket` sustituido por una función que lanza una excepción mediante `monkeypatch` (FR-011)
- [X] T024 [P] [US1] Escribir `tests/generator/test_manifest.py`: el manifiesto tiene exactamente las claves de [contracts/manifest.md](contracts/manifest.md), `files` ordenado por `name` con los tres CSV, `rows` igual a las filas de datos de cada CSV, `config_sha256` igual al SHA-256 de la configuración usada, sin fechas (ningún valor coincide con una fecha ISO) y terminado en `"\n"`; `verify` contra el propio manifiesto devuelve 0; al alterar un byte de `COMPRAS.csv`, `verify` devuelve 1 y su salida nombra `COMPRAS.csv`; si falta un CSV, devuelve 1
- [X] T025 [P] [US1] Escribir `tests/generator/test_config.py`: la configuración por defecto carga sin errores; con `huerfanos.orphan_rate = -0.1` la generación devuelve 2, el mensaje contiene `huerfanos.orphan_rate` y `[0, 0.05]`, y un `data/manifest.json` previo no cambia; un periodo de menos de dos años completos, factores mensuales que no son doce, participaciones que no suman 1, una institución desconocida en `patrones.p3`, una `patrones.p3.molecula_ejemplo` que está en `patrones.p5.moleculas`, una molécula de P3 o P5 que no está en `moleculas_destacadas`, `genericos_por_molecula` mayor que `fabricantes_genericos` y una clave TOML desconocida devuelven 2 con la ruta del parámetro en el mensaje; `generate --out` con un directorio que no existe termina con 0 y lo crea; si se fuerza una excepción dentro de `staging` (por ejemplo con `monkeypatch` sobre `write_csv`), los archivos previos del directorio de salida no cambian y no queda ningún `.tmp-*`

### Implementation for User Story 1

- [X] T026 [P] [US1] Crear `generator/units.py` con `build_units(config, reference, rng) -> tuple[Unit, ...]`: reparte `volumen.unidades_medicas` entre entidades e instituciones respetando la columna `presencia` de `instituciones.csv` y las banderas de `entidades.csv`, asigna `NIVEL_ATENCION` según `concentracion.reparto_nivel`, `MUNICIPIO` con peso proporcional a `poblacion_2020` de `municipios.csv`, `DELEGACION` como `"<prefijo_delegacion> <entidad>"`, `GRUPO_INSTITUCIONAL` desde `instituciones.csv` y `CLUE` como `codigo_clues + prefijo_clues + consecutivo de 6 dígitos` sin repetir. Devuelve las unidades ordenadas por `CLUE`
- [X] T027 [P] [US1] Crear `generator/supplies.py` con `build_supplies(config, reference, rng, faker) -> Supplies`: una `CLAVE` por presentación con formato `010.000.NNNN.00` y `NNNN` sorteado sin repetición entre `0100` y `6999`; `DESCRIPCION` del estilo del Compendio (`"<Molécula>. <Forma>. Cada <unidad> contiene: <molécula> <concentración>. <Envase>."`); `PRESENTACION` con forma, concentración y envase; fabricantes ficticios con apellidos de `faker.last_name()` y forma `"Laboratorios <Apellido> <Apellido>, S.A. de C.V."` o `"Farmacéutica <Apellido>, S.A. de C.V."`, descartando cualquier nombre que contenga una entrada de `laboratorios_reales.txt` (comparación en minúsculas y sin acentos); `volumen.fabricantes_innovadores` fabricantes innovadores y `volumen.fabricantes_genericos` genéricos, cada uno con **un único factor** de precio para todas sus moléculas (innovadores dentro de `factor_referencia`, genéricos dentro de `factor_generico`, principio V); por molécula, un innovador de referencia que es el `FABRICANTE` de todas sus claves y de `volumen.genericos_por_molecula` genéricos autorizados; una marca única por par fabricante-molécula hecha con sílabas al azar; proveedores con `COD_PROVEEDOR` `PRV` + 5 dígitos y de 1 a 3 por fabricante; precio base en centavos enteros por clave dentro del rango de su `nivel_precio`; y la banda de precio de cada clave (`base × factor mínimo de sus autorizados × (1 - ruido_max)` a `base × factor máximo de sus autorizados × (1 + ruido_max)`). Devuelve las claves ordenadas por `CLAVE`
- [X] T028 [US1] Crear `generator/purchases.py` con `build_purchases(config, units, supplies, rng) -> Purchases`: reparte `volumen.lineas_compra` por mes con una multinomial de pesos `factores_mes[m] × (1 + crecimiento_total)^año`, fechas uniformes entre los días laborables del mes, unidad por participación de institución, `población^beta` de la entidad y `peso_compra_nivel`, clave por peso Zipf `1 / rango^alpha_moleculas` sobre las moléculas, donde las de `concentracion.moleculas_destacadas` ocupan su rango fijo y el resto se ordena al azar con el flujo `purchases`, fabricante autorizado, marca y proveedor coherentes, `PIEZAS` lognormal entera entre 1 y `piezas_max`, precio unitario `rint(base × factor × ruido)` en centavos con ruido uniforme en `[1 - ruido_max, 1 + ruido_max]` e `IMPORTE` en centavos como `PIEZAS × precio_unitario`. Devuelve las filas ordenadas por `FECHA`, `CLUE`, `CLAVE` y orden de generación (depende de T026 y T027)
- [X] T029 [US1] Crear `generator/pipeline.py` con `generate(config_path: Path, out_dir: Path) -> dict`: carga y valida la configuración antes de crear nada, crea los flujos y la instancia `Faker("es_MX")` con `seed_instance(faker_seed(...))`, construye unidades, insumos y compras, escribe los tres CSV con los encabezados exactos de [contracts/csv-format.md](contracts/csv-format.md) dentro de `staging(out_dir)` y escribe el manifiesto. Conectar `generate` de `generator/__main__.py` a esta función (depende de T028)
- [X] T030 [US1] Ejecutar `make test` hasta que `tests/generator/test_determinism.py`, `tests/generator/test_manifest.py` y `tests/generator/test_config.py` (T023, T024 y T025) pasen
- [X] T031 [US1] Ejecutar `make data` y después `make data-manifest` para crear la primera versión de `generator/manifest.json`, y repetir `make data` para comprobar `OK` en los tres archivos (Claude, con permiso del dueño; depende de T030)

**Checkpoint**: la regeneración reproducible funciona. Es el MVP.

---

## Phase 4: User Story 2 - Fuentes que cumplen el contrato y se pueden unir sin sorpresas (Priority: P1)

**Goal**: encabezados y formatos exactos, claves únicas, ningún vacío, dominios correctos y
huérfanos exactos al 0.5 %.

**Independent Test**: `test_contract.py`, `test_integrity.py` y `test_ranges.py` pasan sobre la
generación completa.

### Tests for User Story 2 ⚠️

- [X] T032 [P] [US2] Escribir `tests/generator/test_contract.py` sobre `full_dataset`: encabezados literales `CLUE,CLAVE,COD_PROVEEDOR,MARCA,FABRICANTE,PIEZAS,IMPORTE,FECHA`, `CLUE,ENTIDAD,INSTITUCION,DELEGACION,GRUPO_INSTITUCIONAL,NIVEL_ATENCION,MUNICIPIO` y `CLAVE,DESCRIPCION,MOLECULA,GRUPO_TERAPEUTICO,PRESENTACION,FABRICANTE`; los archivos empiezan sin BOM (`b"\xef\xbb\xbf"`), no contienen `b"\r"` y terminan en `b"\n"`; `CLUE` cumple `^[A-Z]{2}(IMS|IST|SDN|SMA|PMX|IMO|SSA)[0-9]{6}$`; `CLAVE` cumple `^010\.000\.[0-9]{4}\.[0-9]{2}$`; `COD_PROVEEDOR` cumple `^PRV[0-9]{5}$`; `IMPORTE` cumple `^[0-9]+\.[0-9]{2}$`; `FECHA` cumple `^[0-9]{4}-[0-9]{2}-[0-9]{2}$`; `PIEZAS` cumple `^[0-9]+$`; ningún campo contiene salto de línea; las filas están en el orden de [data-model.md](data-model.md)
- [X] T033 [P] [US2] Escribir `tests/generator/test_integrity.py` sobre `full_dataset`: `CLUE` única en `CLUE_CAT` y `CLAVE` única en `CUADRO_BASICO`; ningún campo vacío en los tres archivos; el número de filas de `COMPRAS` con `CLUE` sin correspondencia más el de `CLAVE` sin correspondencia es exactamente `round(orphan_rate × lineas_compra)`, los dos conjuntos son disjuntos, su reparto sigue `proporcion_clue` y los conteos coinciden con `orphans` del manifiesto; con una configuración temporal con `orphan_rate = 0` no hay huérfanos
- [X] T034 [P] [US2] Escribir `tests/generator/test_ranges.py` sobre `full_dataset`: `PIEZAS` entera entre 1 y `piezas_max`; `IMPORTE` mayor que 0; `FECHA` entre `periodo.inicio` y `periodo.fin` y siempre de lunes a viernes; `IMPORTE` en centavos divisible por `PIEZAS`

### Implementation for User Story 2

- [X] T035 [US2] Añadir a `generator/purchases.py` la inyección de huérfanos de research R13 con el flujo `orphans`: elegir sin reemplazo exactamente `round(orphan_rate × lineas_compra)` filas, asignar `round(total × proporcion_clue)` a huérfanos de `CLUE` y el resto a huérfanos de `CLAVE`, sustituir la clave por otra con formato válido que no exista en su catálogo (consecutivo o `NNNN` no usados), conservar el resto de campos y devolver los dos conteos para el manifiesto
- [X] T036 [US2] Revisar `generator/units.py`, `generator/supplies.py` y `generator/purchases.py` hasta que T032, T033 y T034 pasen con `make test`, sin cambiar los umbrales de las pruebas
- [X] T037 [US2] Regenerar con `make data` y actualizar `generator/manifest.json` con `make data-manifest` (Claude, con permiso del dueño; depende de T036)

**Checkpoint**: las tres fuentes cumplen el contrato y la reconciliación del join es predecible.

---

## Phase 5: User Story 3 - Datos verosímiles que permiten hallazgos comerciales (Priority: P2)

**Goal**: geografía e instituciones reales, coherencia de marcas y precios, concentración,
estacionalidad y los patrones P3, P4 y P5 medibles.

**Independent Test**: `test_realism.py` y `test_patterns.py` pasan sobre la generación completa con
los umbrales de SC-005 a SC-008 y SC-007a.

### Tests for User Story 3 ⚠️

- [X] T038 [P] [US3] Escribir `tests/generator/test_realism.py` sobre `full_dataset`: los valores de `ENTIDAD` son exactamente los 32 de `entidades.csv` y aparecen los 32; los dos primeros caracteres de cada `CLUE` corresponden a su `ENTIDAD` y los tres siguientes a su `INSTITUCION`; SEDENA solo en entidades `sedena = 1`, SEMAR solo en `semar = 1`, PEMEX solo en `pemex = 1`, IMSS-Bienestar solo en `imss_bienestar = 1` y Servicios Estatales de Salud solo en `imss_bienestar = 0`; `GRUPO_INSTITUCIONAL` toma exactamente los tres valores de FR-019a y cada institución está en un solo grupo; `NIVEL_ATENCION` solo toma "Primer nivel", "Segundo nivel" y "Tercer nivel", con más unidades de primero que de tercero; cada `MUNICIPIO` pertenece a su entidad en `municipios.csv`; cada `DELEGACION` es `"<prefijo_delegacion> <ENTIDAD>"` según la institución de la fila (FR-021); cada `DESCRIPCION` empieza por su `MOLECULA` y contiene la concentración de su `PRESENTACION` (FR-024); cada `MOLECULA` tiene un solo `GRUPO_TERAPEUTICO`; cada `MARCA` tiene un solo `FABRICANTE`; el `FABRICANTE` de cada línea de `COMPRAS` está autorizado para su clave y el de `CUADRO_BASICO` aparece entre los fabricantes de compra de esa clave; el `FABRICANTE` de `CUADRO_BASICO` es siempre un innovador; ningún `FABRICANTE` contiene una entrada de `laboratorios_reales.txt`; cada `COD_PROVEEDOR` solo aparece con fabricantes que distribuye (FR-026); `IMPORTE / PIEZAS` cae dentro de la banda de su clave (base × factor mínimo de sus fabricantes autorizados × (1 - ruido_max) a base × factor máximo × (1 + ruido_max), con un centavo de margen), calculada con los precios base y factores que expone `generator.supplies`; el 20 % de moléculas con más importe concentra entre el 60 % y el 90 % del total; la institución con más importe supera el 30 %; todos los meses del periodo tienen compras y en cada año el mes con más importe supera al de menos en al menos 1.2 veces
- [X] T039 [P] [US3] Escribir `tests/generator/test_patterns.py` sobre `full_dataset` con los umbrales de SC-007a: en la molécula de `patrones.p3.molecula_ejemplo` (leída de la configuración, nunca escrita en el código de la prueba), `SUM(IMPORTE) / SUM(PIEZAS)` de la institución con mayor proporción de fabricante de referencia supera en al menos un 20 % al de la institución con menor proporción (P3); el crecimiento del importe de "Oncología" de 2024 a 2025 supera en al menos 10 puntos porcentuales al del resto de grupos juntos (P4); en cada molécula de `patrones.p5.moleculas`, el fabricante genérico elegido gana al menos 10 puntos de cuota de importe de 2024 a 2025 y el de referencia pierde cuota (P5); la molécula de P3 y las de P5 están dentro del 20 % de moléculas con más importe (FR-018a)

### Implementation for User Story 3

- [X] T040 [US3] Añadir a `generator/purchases.py` el patrón P3: la probabilidad de que una línea sea del fabricante de referencia es `patrones.p3.prob_referencia[institucion]` y el resto se reparte por igual entre los genéricos autorizados. El precio sigue dependiendo solo de clave, fabricante y ruido (FR-018a, research R11)
- [X] T041 [US3] Añadir a `generator/purchases.py` el patrón P4: en 2025 el peso de cada molécula se multiplica por `patrones.p4.factor_2025[grupo]` o por `factor_2025_resto` si su grupo no aparece
- [X] T042 [US3] Añadir a `generator/purchases.py` el patrón P5: para cada molécula de `patrones.p5.moleculas`, elegir con el flujo `purchases` un genérico autorizado y fijar su cuota de líneas en `cuota_generico_inicial` en 2024 y `cuota_generico_final` en 2025, restando la diferencia al fabricante de referencia. P5 tiene prioridad sobre P3 solo en las moléculas de P5. La molécula de ejemplo de P3 nunca está en P5 (lo valida la configuración), así que H1 se mide sin interferencia
- [X] T043 [US3] Ejecutar `make test` y ajustar solo los valores de `generator/config.toml` (nunca los umbrales de las pruebas ni la lógica para forzar un resultado) hasta que T038 y T039 pasen. Anotar en `specs/002-synthetic-data-generator/research.md`, al final de R11, los valores finales y la razón de cada ajuste
- [X] T044 [US3] Regenerar con `make data` y actualizar `generator/manifest.json` con `make data-manifest` (Claude, con permiso del dueño; depende de T043)

**Checkpoint**: los datos sostienen los hallazgos H1, H2 y H3.

---

## Phase 6: User Story 4 - Datos honestos y documentados (Priority: P2)

**Goal**: README y documentación de los datos que declaran que son sintéticos, explican cómo
regenerarlos y describen cada patrón inyectado.

**Independent Test**: `make lint-prosa` sin violaciones y revisión de quickstart V7.

### Implementation for User Story 4

- [X] T045 [P] [US4] Crear `docs/datos_sinteticos.md` en español con el principio IX: qué son los datos y que son sintéticos; cómo se generan (semilla, configuración, flujos independientes y manifiesto); una tabla por fuente con cada campo, su tipo previsto en BigQuery y su regla de generación (tomada de [data-model.md](../../specs/002-synthetic-data-generator/data-model.md)); los patrones inyectados (concentración, estacionalidad, huérfanos, P3, P4 y P5) con el parámetro de `generator/config.toml` que los controla y su valor final; la definición del `FABRICANTE` de catálogo como fabricante de referencia y del de compra como fabricante del producto entregado; que fabricantes, marcas y proveedores son ficticios y que cualquier coincidencia es accidental; que las claves CLUES y del Compendio tienen formato verosímil y no corresponden a establecimientos o insumos reales, incluido el uso de `IMO` para IMSS-Bienestar; que con huérfanos no se declaran claves foráneas; que puede haber claves y unidades del catálogo sin compras y que eso no afecta al `INNER JOIN`; que los fabricantes son innovadores o genéricos, cada uno con un único factor de precio; las limitaciones (igualdad byte a byte garantizada solo en el mismo entorno); y las fuentes de cada catálogo de referencia con su URL
- [X] T046 [P] [US4] Crear `docs/trazabilidad.md` con una tabla `Requisito | Artefacto | Verificación` y las filas de la sección de materiales e insumos de los requisitos del proyecto: estructura de `COMPRAS`, de `CLUE_CAT` y de `CUADRO_BASICO` (cada una con `data/<TABLA>.csv` y `test_contract.py`) y formato CSV o Parquet (CSV, `contracts/csv-format.md` y `test_contract.py`), sin nombrar el documento de requisitos de origen. Las features siguientes añadirán sus filas
- [X] T047 [US4] Añadir al `README.md` una sección "Datos sintéticos" que diga que los datos son sintéticos, que fabricantes, marcas y proveedores son ficticios, cómo regenerarlos con `make data`, qué significa un `DIFIERE` y cuándo usar `make data-manifest`, con un enlace a `docs/datos_sinteticos.md`. Mantener la declaración ya existente sin duplicarla
- [X] T048 [US4] Ejecutar `make lint-prosa` y corregir el texto de README, `docs/datos_sinteticos.md` y `docs/trazabilidad.md` hasta que no haya violaciones, sin añadir excepciones nuevas salvo términos de dominio justificados en `scripts/prosa_excepciones.txt`

**Checkpoint**: la documentación cumple el principio V (honestidad) y el principio IX.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: CI, rendimiento y validación final.

- [X] T049 Añadir a `.github/workflows/checks.yml` un job `tests` en `ubuntu-latest` con los mismos pasos fijados por SHA que el job `pre-commit` (`actions/checkout` v7.0.1 y `astral-sh/setup-uv` v10.2.0 con `version: "0.12.18"`), seguido de `uv sync --locked` y `uv run pytest`, sin secretos ni acceso a GCP, con un comentario en inglés de una línea (FR-030a)
- [X] T050 Medir con `time make test` y `time make data` que la suite y la generación tardan menos de 2 minutos y con `du -ch data/*.csv` que el total queda por debajo de 100 MB (SC-002 y SC-003). Si no se cumple, optimizar el código vectorizando con NumPy, sin cambiar la salida esperada o, si cambia, actualizando el manifiesto
- [X] T051 Ejecutar `make lint` y `make test` completos sobre el repositorio (`generator/`, `tests/`, `Makefile`, `.github/workflows/checks.yml`) y corregir lo que falle
- [X] T052 Recorrer [quickstart.md](quickstart.md) de V1 a V7 y anotar el resultado de cada paso en `specs/002-synthetic-data-generator/quickstart.md` (V2 y V6 los confirma el dueño: clon limpio y checks del PR)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias. T003 y T004 los ejecuta el dueño y bloquean T005.
- **Foundational (Phase 2)**: depende de Setup. Bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de US1, porque añade huérfanos y contrato sobre el pipeline de US1.
- **US3 (Phase 5)**: depende de US1. Puede ir en paralelo con US2 si se coordinan los cambios en `generator/purchases.py`, pero el orden recomendado es US2 antes de US3.
- **US4 (Phase 6)**: T046 y T047 pueden empezar tras US1. T045 necesita los valores finales de T043.
- **Polish (Phase 7)**: depende de todas las historias.

### User Story Dependencies

- **US1 (P1)**: tras Foundational, sin dependencias de otras historias.
- **US2 (P1)**: usa el pipeline de US1 y se prueba de forma independiente con sus propias pruebas.
- **US3 (P2)**: usa el pipeline de US1 y se prueba de forma independiente con sus propias pruebas.
- **US4 (P2)**: documenta lo que producen US1 a US3.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Catálogos y entidades antes que compras. Compras antes que el pipeline.
- Cada historia termina regenerando el manifiesto versionado si cambió la salida.

### Parallel Opportunities

- Setup: T001, T002 y T006 en paralelo. T007 después de T004.
- Foundational: T008 a T012 (catálogos) en paralelo; T015, T016, T017 y T018 en paralelo cuando
  exista T013; T021 en paralelo con todo lo anterior.
- US1: T023, T024 y T025 en paralelo; T026 y T027 en paralelo.
- US2: T032, T033 y T034 en paralelo.
- US3: T038 y T039 en paralelo. T040 a T042 tocan el mismo archivo y van en secuencia.
- US4: T045 y T046 en paralelo.

---

## Parallel Example: Foundational

```bash
Task: "Crear generator/reference/entidades.csv desde el servicio del INEGI (T008)"
Task: "Crear generator/reference/municipios.csv desde el servicio del INEGI (T009)"
Task: "Crear generator/reference/instituciones.csv con las siete filas exactas (T010)"
Task: "Crear generator/reference/moleculas.csv con unas 140 moléculas (T011)"
Task: "Crear generator/reference/laboratorios_reales.txt (T012)"
```

## Parallel Example: User Story 1

```bash
Task: "Escribir tests/generator/test_determinism.py (T023)"
Task: "Escribir tests/generator/test_manifest.py (T024)"
Task: "Escribir tests/generator/test_config.py (T025)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Setup, con `uv lock` y `make setup-dev` del dueño.
2. Completar Foundational.
3. Completar US1 y validar con quickstart V1 y V5.
4. **PARAR Y VALIDAR**: los datos ya son reproducibles y cargables, aunque todavía sin huérfanos ni
   patrones.

### Incremental Delivery

1. Setup y Foundational: base lista.
2. US1: regeneración reproducible (MVP).
3. US2: contrato completo y huérfanos.
4. US3: realismo y patrones que sostienen los hallazgos.
5. US4: documentación honesta.
6. Polish: CI y validación final. Después, mensaje de commit y descripción del PR pasados por el
   lint de prosa para el visto bueno del dueño.

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- Las tareas del dueño llevan **[Dueño]** y el comando exacto se le entrega explicado.
- Si una prueba de realismo no pasa, se ajusta la configuración y se documenta el porqué. Nunca se
  rebaja un umbral para que pase (principio IV).
- Commit y PR solo con el visto bueno del dueño, por rama y con squash merge.
