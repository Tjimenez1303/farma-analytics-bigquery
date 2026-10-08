# Research: Generador de datos sintéticos

**Feature**: `002-synthetic-data-generator` | **Fecha**: 2026-10-08 | **Plan**: [plan.md](plan.md)

Cada decisión sigue el formato Decision / Rationale / Alternatives considered. Las versiones y
comportamientos se verificaron el 2026-10-08 contra PyPI, la documentación oficial de NumPy, Faker,
Python, uv y BigQuery (`docs.cloud.google.com`) y las fuentes oficiales mexicanas citadas al
final. Fecha de corte para la regla de los 14 días: 2026-09-24.

---

## R1. Versiones de NumPy y Faker

- **Decision**: `numpy==2.5.3` y `faker==40.39.0`, en `[project].dependencies` de
  `pyproject.toml`, con `uv.lock` actualizado. Python sigue en 3.12.14 (`.python-version`).
- **Rationale**: NumPy 2.5.3 se publicó el 2026-09-06 y es la versión estable más reciente con al
  menos 14 días. Exige Python 3.12 o superior y publica wheels cp312 para macOS arm64 y
  manylinux x86_64, que cubren la máquina del dueño y el runner de CI. Faker 40.40.0 (2026-09-29)
  y 40.41.0 (2026-10-05) son demasiado recientes, y 40.39.0 (2026-09-14) es la más reciente que
  cumple la regla. Exige Python 3.10 o superior y no tiene dependencias obligatorias fuera de
  Windows. La documentación de Faker dice que una semilla solo reproduce resultados con la misma
  versión y que "results are not guaranteed to be consistent across patch versions", así que el
  pin exacto es obligatorio, como ya exige el principio V.
- **Alternatives considered**: NumPy 2.4.6 (más antigua sin motivo); Faker con rango compatible
  (`~=40.39`), descartado porque un parche puede cambiar la salida; pandas o pyarrow (no hacen
  falta para escribir CSV y añaden dependencias grandes, principio VIII).

## R2. Generación aleatoria reproducible con NumPy

- **Decision**: una semilla raíz en la configuración alimenta un `numpy.random.SeedSequence`, y
  cada componente (unidades médicas, catálogo de insumos, empresas, compras, huérfanos y Faker)
  recibe su propio hijo de `spawn`, siempre en el mismo orden (`units`, `supplies`, `companies`,
  `purchases`, `orphans`, `faker`). La semilla de Faker sale de su propio hijo con
  `int(generate_state(1, dtype=np.uint64)[0])`, porque `generate_state` devuelve un array y
  reutilizar el `SeedSequence` de otro componente correlacionaría los dos flujos. La
  semilla raíz es un entero de 128 bits generado una sola vez. No se usa `multivariate_normal` ni
  nada que dependa de LAPACK.
- **Rationale**: la guía de NumPy recomienda semillas grandes (128 bits) y `spawn` para obtener
  flujos independientes de una sola semilla. Con flujos separados, cambiar el volumen de `COMPRAS`
  no altera los catálogos. La política de compatibilidad de NumPy solo garantiza el mismo flujo
  con la misma build, en el mismo entorno y la misma máquina, y advierte que
  `multivariate_normal` puede cambiar con la versión de LAPACK. También advierte que llamar a
  `rng.random()` cinco veces no está garantizado igual que `rng.random(5)`, así que el orden y el
  tamaño de cada llamada quedan fijos en el código.
- **Alternatives considered**: un solo `Generator` para todo (cualquier cambio de volumen
  desplaza el resto del flujo); `RandomState` (API heredada); sumar un índice a la semilla
  (`seed + i`), que la propia guía de NumPy desaconseja.

## R3. Faker `es_MX` y nombres ficticios

- **Decision**: una instancia `Faker("es_MX")` con `seed_instance` alimentado por un entero que
  se deriva del `SeedSequence` hijo `faker` (R2). Se usa solo para apellidos con los que
  se componen los nombres de fabricantes ("Laboratorios Ortega Salinas, S.A. de C.V.",
  "Farmacéutica Medina, S.A. de C.V.") y proveedores ("Distribuidora Ríos Cantú, S.A. de C.V.").
  Las marcas se forman con sílabas al azar y un sufijo, con el generador de NumPy. Una lista
  versionada de nombres de laboratorios reales que operan en México sirve de lista de exclusión, y
  una prueba comprueba que ningún nombre generado la contiene.
- **Rationale**: la documentación de Faker describe `seed_instance` como la forma de dar a una
  instancia su propio generador sin tocar el compartido. El locale `es_MX` incluye los proveedores
  `person` y `company`. Varios laboratorios mexicanos reales llevan apellido en su nombre, así que
  sin la lista de exclusión un apellido podría reproducir una empresa real y atribuirle precios
  inventados, que es lo que la aclaración del 2026-10-08 quiere evitar (FR-028).
- **Alternatives considered**: `company()` de Faker directamente (devuelve despachos y clubes,
  como "Palacios y Madrigal S.C.", que no parecen laboratorios); `state()` de Faker para entidades
  (no garantiza los nombres oficiales del INEGI, que vienen de R6); RFC con `rfc()` como
  `COD_PROVEEDOR` (podría coincidir con el RFC de una empresa real).

## R4. Importe exacto en centavos

- **Decision**: el precio base de cada `CLAVE` se sortea en una banda de precio (según el nivel de
  precio de la molécula) y se guarda en centavos enteros. Los fabricantes son innovadores o
  genéricos y cada uno tiene un único factor de precio para todas sus moléculas (innovadores en
  `factor_referencia`, genéricos en `factor_generico`), que es la lectura literal del principio V
  ("× un factor por fabricante") y refleja el mercado real, donde el innovador cobra prima y el
  genérico descuento. Solo un innovador puede ser fabricante de referencia. El precio unitario de cada línea es
  `rint(precio_base_centavos × factor_fabricante × ruido)` en centavos enteros, con un solo
  redondeo, y `IMPORTE_centavos = PIEZAS × precio_unitario_centavos` con aritmética entera
  (`int64`). Al escribir, `IMPORTE` se formatea como `f"{c // 100}.{c % 100:02d}"`.
- **Rationale**: es la decisión de la aclaración sobre NumPy. Un solo redondeo por línea reduce los
  puntos donde una diferencia de plataforma en el último bit puede cambiar un centavo, y el
  producto entero es exacto. `IMPORTE / PIEZAS` devuelve el precio unitario sin error, lo que
  permite comprobar la banda de FR-016 al centavo. El mayor importe posible (menos de 10^12
  centavos) cabe de sobra en `int64` y en `NUMERIC` de BigQuery.
- **Alternatives considered**: `float` con `round(x, 2)` al final (dos redondeos y errores de
  representación binaria); `decimal.Decimal` por fila (más lento y no aporta exactitud sobre los
  enteros).

## R5. Formato CSV y compatibilidad con la carga en BigQuery

- **Decision**: `csv.writer` sobre archivos abiertos con `encoding="utf-8"` (sin BOM) y
  `newline=""`, `lineterminator="\n"`, `quoting=csv.QUOTE_MINIMAL`, delimitador coma y comillas
  dobles. Una fila de encabezado con los nombres exactos de la spec. Fechas `YYYY-MM-DD`, enteros
  sin separador de miles e importes con punto decimal y dos decimales. Ningún campo contiene saltos
  de línea, así que la carga no necesitará `--allow_quoted_newlines`.
- **Rationale**: la documentación de Python indica que el terminador por defecto de `csv.writer`
  es `"\r\n"` y que el archivo debe abrirse con `newline=""`, de lo contrario las plataformas con
  `\r\n` añaden un `\r` extra. `QUOTE_MINIMAL` solo entrecomilla los campos con caracteres
  especiales, de forma determinista. BigQuery espera CSV en UTF-8, pide quitar el BOM porque
  "might cause unexpected issues", exige el guion como separador en columnas `DATE` y salta el
  encabezado con `--skip_leading_rows`. El límite de 100 MB para archivos locales solo aplica a la
  consola de Google Cloud, y aun así el volumen previsto (R12) queda por debajo.
- **Alternatives considered**: `QUOTE_ALL` (archivos más grandes sin necesidad); separador `;` o
  coma decimal (BigQuery y la constitución piden punto decimal); `utf-8-sig` (añade BOM).

## R6. Entidades federativas: nombres oficiales y códigos

- **Decision**: `generator/reference/entidades.csv` con las 32 entidades: clave INEGI
  (`01`–`32`), nombre oficial exacto del Marco Geoestadístico, código de dos letras para la CLUES,
  población del Censo 2020 (peso de concentración), si está adherida a IMSS-Bienestar y si hay
  unidades en operación de SEDENA, SEMAR y PEMEX. Los nombres y la población se copian del
  servicio web del catálogo único de claves geoestadísticas del INEGI, y la presencia de cada
  institución de los datos abiertos CLUES 2022 de la DGIS (unidades "EN OPERACION").
- **Rationale**: el servicio `wscatgeo/v2/mgee` del INEGI devuelve los nombres oficiales, entre
  ellos "Coahuila de Zaragoza", "Ciudad de México", "México", "Michoacán de Ocampo" y "Veracruz de
  Ignacio de la Llave" (FR-020). Los códigos de dos letras siguen el catálogo de entidades de la
  CURP, que el ejemplo del instructivo de RENAPO confirma para la Ciudad de México ("DF") y que
  coincide con las CLUES públicas de la DGIS (`JCSSA001186` en Jalisco, `NTSSA000013` en Nayarit,
  `BCSSA000592` en Baja California). En la implementación se contrastan los 32 códigos con una
  muestra de los datos abiertos CLUES de la DGIS.
- **Alternatives considered**: `state()` de Faker (nombres no oficiales); abreviaturas del INEGI
  (`Ags.`, `Coah.`), que no son las que usa la CLUES.

## R7. Instituciones, prefijos CLUES y grupo institucional

- **Decision**: `generator/reference/instituciones.csv`:

  | INSTITUCION | Prefijo CLUES | GRUPO_INSTITUCIONAL | Presencia |
  |---|---|---|---|
  | IMSS | `IMS` | Seguridad social | 32 entidades |
  | ISSSTE | `IST` | Seguridad social | 32 entidades |
  | SEDENA | `SDN` | Fuerzas Armadas y PEMEX | 29 entidades con unidades en la DGIS |
  | SEMAR | `SMA` | Fuerzas Armadas y PEMEX | 18 entidades con unidades en la DGIS |
  | PEMEX | `PMX` | Fuerzas Armadas y PEMEX | 16 entidades con unidades en la DGIS |
  | IMSS-Bienestar | `IMO` | Población sin seguridad social | 24 entidades adheridas |
  | Servicios Estatales de Salud | `SSA` | Población sin seguridad social | 8 entidades no adheridas |

- **Rationale**: el anexo 2 de los lineamientos CLUES publicados en el DOF define las claves de
  institución `SSA`, `IMS`, `IST`, `SDN`, `SMA`, `IMO` (IMSS régimen Oportunidades, antecesor de
  IMSS-Bienestar) y `PMX`. Las unidades de los servicios estatales llevan el prefijo `SSA` en las
  CLUES públicas (`JCSSA001186`). La DGIS determina la institución con los caracteres 1 a 5 de la
  clave, lo que confirma el esquema entidad (2) + institución (3) + consecutivo (6). Según las
  declaraciones de enero de 2026 y una nota de agosto de 2026, las ocho entidades no adheridas son
  Aguascalientes, Chihuahua, Coahuila, Durango, Guanajuato, Jalisco, Nuevo León y Querétaro, y las
  24 restantes están adheridas. Los grupos son los de la aclaración del 2026-10-08.
- **Alternatives considered**: un prefijo inventado para IMSS-Bienestar (`IMB`), que no aparece en
  ningún catálogo consultado; asignar SEMAR y PEMEX a las 32 entidades (poco verosímil). El
  catálogo vigente de la DGIS podría usar otra clave para IMSS-Bienestar. Para datos sintéticos
  basta con que el formato sea verosímil (principio V), y la documentación de los datos lo dice.

## R8. Claves y moléculas del Compendio Nacional de Insumos

- **Decision**: `CLAVE` con el formato `010.000.NNNN.DD` (grupo 010 de medicamentos, genérico
  `000`, específico de cuatro dígitos y diferenciador de dos). `NNNN` se sortea sin repetición y
  `DD` es `00`. `generator/reference/moleculas.csv` lista 139 moléculas
  reales con denominación genérica, grupo terapéutico, nivel de precio (bajo, medio, alto, muy
  alto) y de una a tres presentaciones (161 en total), cada una con forma farmacéutica, unidad de
  contenido, concentración y envase. Cada presentación es una `CLAVE` y cada pieza es un envase,
  como en el Cuadro Básico. Los 23 grupos terapéuticos se copiaron de la edición 2014 del Cuadro
  Básico y Catálogo de Medicamentos publicada en el DOF (por ejemplo "Grupo No. 1: Analgesia" y
  "Gineco-obstetricia"), y la modificación 2026 del Compendio confirma "Oncología" y "Vacunas,
  Toxoides, Inmunoglobulinas, Antitoxinas". El grupo de vacunas no se usa porque sus claves no
  pertenecen al grupo 010.
- **Rationale**: el procedimiento del IMSS describe la clave como grupo, genérico, específico,
  diferenciador y variante, y una licitación estatal muestra el formato en uso
  (`010.000.0104.00`, paracetamol en tabletas de 500 mg). Las claves no reproducen la asignación
  oficial: tienen el formato verosímil que pide el principio V sin afirmar que una clave real
  corresponda a esa presentación.
- **Alternatives considered**: copiar claves reales del Compendio (exigiría la tabla oficial
  completa y daría a entender que la correspondencia es real); claves sin puntos (menos
  reconocibles).

## R9. Municipios y alcaldías

- **Decision**: `generator/reference/municipios.csv` con, por entidad, la capital y los municipios
  más poblados (entre 5 y 10 por entidad) según el catálogo del INEGI. En la Ciudad de México se
  usan sus alcaldías. Las unidades médicas de cada entidad se reparten entre esos municipios con
  peso proporcional a su población.
- **Rationale**: FR-021 exige municipios reales de la entidad de la fila. Un subconjunto por
  entidad basta para que el dashboard muestre nombres reconocibles sin cargar los más de 2 400
  municipios del país.
- **Alternatives considered**: el catálogo completo (archivo grande y sin ganancia analítica, ya
  que `MUNICIPIO` no es un filtro del dashboard); nombres de ciudades de Faker (no garantizan que
  pertenezcan a la entidad).

## R10. Distribuciones, concentración y estacionalidad

- **Decision**:
  - Moléculas: peso `1 / rango^alpha` (tipo Zipf) sobre un orden aleatorio de las moléculas, con
    `alpha` en la configuración. Las moléculas de `moleculas_destacadas` (las de P3 y P5) ocupan un
    rango fijo, para que los hallazgos caigan en moléculas de alto importe que se ven en el top 10
    del dashboard. El reparto entre presentaciones de una molécula usa pesos fijos.
  - Instituciones: participación explícita en la configuración (por ejemplo IMSS 0.42), de modo
    que la mayor supere el 30 % (SC-006).
  - Entidades: peso proporcional a `población^beta`. Dentro de cada entidad, las unidades de
    segundo y tercer nivel compran más que las de primero, con multiplicadores por nivel.
  - `PIEZAS`: lognormal por línea, redondeada a entero y acotada entre 1 y un máximo configurable.
  - Fechas: el número de líneas por mes sale de una multinomial con peso `estacionalidad[mes] ×
    (1 + crecimiento_total)^año`. Dentro del mes se reparten de forma uniforme entre los días
    laborables (lunes a viernes).
  - Ruido del precio: uniforme en `[1 - ruido_max, 1 + ruido_max]`.
- **Rationale**: son los mecanismos más simples que producen cola larga y concentración tipo
  Pareto (principio V, FR-017 y FR-018) con parámetros legibles. Las entregas a unidades públicas
  se hacen en días hábiles. Una banda uniforme acota el ruido, que es lo que exige FR-016.
- **Alternatives considered**: `Generator.zipf` (devuelve enteros sin límite superior, poco
  práctico para un catálogo finito); ruido normal (no acotado); días naturales (fines de semana
  con compras poco verosímiles).

## R11. Patrones comerciales P3, P4 y P5

- **Decision**:
  - **P3**: se mide en `patrones.p3.molecula_ejemplo` ("Clopidogrel"), que no puede ser molécula
    de P5, para que H1 no se mezcle con el cambio de cuota. La configuración fija, por institución, la probabilidad de que una línea sea del
    fabricante de referencia (por ejemplo PEMEX 0.75, SEMAR 0.70, SEDENA 0.65, ISSSTE 0.40,
    Servicios Estatales 0.35, IMSS-Bienestar 0.25, IMSS 0.20). El resto se reparte entre los
    genéricos autorizados de la clave. El precio solo depende de la clave, el fabricante y el
    ruido.
  - **P4**: en 2025, el peso de cada molécula se multiplica por el factor de crecimiento de su
    grupo terapéutico (por ejemplo Oncología 1.22 y el resto alrededor de 1.05).
  - **P5**: para las moléculas configuradas ("Atorvastatina" e "Insulina glargina", de precio
    medio y alto), la participación del genérico elegido sube de una
    cuota inicial en 2024 a una final en 2025, restando al fabricante de referencia.
- **Rationale**: son los patrones de la aclaración del 2026-10-08, que sostienen H1, H2 y H3. P3
  respeta la fórmula de precio del principio V porque la diferencia entre instituciones sale de la
  mezcla de fabricantes. Las pruebas de SC-007a miden cada patrón sobre los archivos generados.
- **Alternatives considered**: un factor de precio por institución (rompe la fórmula del principio
  V); crecimiento por molécula suelto (más parámetros sin ganar claridad).
- **Ajuste final (T043, 2026-10-08)**: con los valores de partida, la concentración del 20 % de
  moléculas con más importe dio 97 % (umbral 60-90 %) y P3 dio 1.14 (umbral 1.20). Solo se
  cambió `generator/config.toml`, sin tocar umbrales ni lógica:
  - `precios.nivel` pasa a bajo 15-100, medio 100-600, alto 600-2 500 y muy alto 2 500-9 000 pesos
    por pieza (antes 2-30, 30-400, 400-5 000 y 5 000-60 000). Con una diferencia de 500 veces
    entre niveles, cuatro biotecnológicos sumaban casi el 70 % del importe.
  - `concentracion.alpha_moleculas` pasa de 1.1 a 0.9, una cola algo menos empinada.
  - `precios.factor_referencia` pasa a 1.40-1.80 y `factor_generico` a 0.50-0.80 (antes 1.25-1.60
    y 0.60-0.95). El margen del innovador sobre el genérico era demasiado estrecho para que la
    mezcla por institución se notara en el precio promedio.
  - `patrones.p4.factor_2025` de Oncología pasa de 1.22 a 1.30, porque la cola larga de `PIEZAS`
    mete ruido en el importe y con 1.22 la diferencia quedaba cerca del umbral.
  - Resultado medido: concentración 85.5 %, institución principal 38.5 %, P3 1.28, P4 20 puntos
    y las moléculas de P3 y P5 dentro del 20 % de mayor importe.

## R12. Volúmenes y rango de fechas

- **Decision**: 2024-01-01 a 2025-12-31, unas 300 000 líneas en `COMPRAS`, unas 2 000 unidades en
  `CLUE_CAT`, unas 160 claves en `CUADRO_BASICO` (139 moléculas con una a tres presentaciones),
  12 fabricantes innovadores, 28 genéricos y unos 60 proveedores. `orphan_rate = 0.005`, repartido a partes iguales
  entre `CLUE` y `CLAVE`.
- **Rationale**: dos años completos para comparar año contra año (FR-018). Con unos 110 bytes por
  línea, `COMPRAS` ocupa unos 35 MB y los tres archivos menos de 40 MB, lejos de los 100 MB de
  SC-003, de los 10 GiB de almacenamiento gratuito y del límite de 1 GiB por consulta de
  `.bigqueryrc`. Unas 160 claves bastan para un top 10 con cola larga.
- **Alternatives considered**: un millón de líneas (unos 110 MB, sin ganancia analítica y más
  lento en las pruebas); incluir 2026 parcial (descartado en la spec).

## R13. Huérfanos

- **Decision**: se eligen al azar exactamente `round(orphan_rate × filas)` líneas de `COMPRAS`. La
  mitad recibe una `CLUE` con formato válido que no existe en `CLUE_CAT` y la otra mitad una
  `CLAVE` inexistente, sin solaparse. El resto de campos de la línea conserva valores coherentes
  con la clave original. El manifiesto registra los dos conteos.
- **Rationale**: con un número exacto la tolerancia de SC-004 se cumple por construcción y la
  reconciliación de la feature de carga puede predecir el resultado. Un huérfano con formato válido
  solo lo descarta el `INNER JOIN` (FR-014).
- **Alternatives considered**: un sorteo de Bernoulli por fila (la tasa medida varía); claves con
  formato inválido (las rechazaría un chequeo de formato antes del join).

## R14. Configuración

- **Decision**: `generator/config.toml`, leído con `tomllib` de la biblioteca estándar y validado
  con código propio antes de escribir nada. La semilla se guarda como texto
  (`seed = "0x..."`). Los niveles de precio de las moléculas están en el catálogo de referencia y
  los rangos de cada nivel en la configuración.
- **Rationale**: `tomllib` existe desde Python 3.11 y no añade dependencias. La especificación TOML
  1.0 solo garantiza enteros de 64 bits sin pérdida y obliga a dar error si no se pueden
  representar, así que una semilla de 128 bits como entero no es portable. Separar el nivel de
  precio (dato de referencia) de su rango (parámetro) cumple FR-005.
- **Alternatives considered**: YAML (necesita PyYAML); JSON (sin comentarios); pydantic para
  validar (dependencia grande para unas decenas de reglas).

## R15. Manifiesto, verificación y escritura atómica

- **Decision**: `data/manifest.json` en JSON con claves ordenadas, sangría de 2 espacios, LF y
  salto final. Contiene la versión del formato, la huella SHA-256 de la configuración, las
  versiones de Python, NumPy y Faker, y por archivo su nombre, SHA-256, bytes y filas sin
  encabezado, además de los conteos de huérfanos. Las versiones se leen con
  `importlib.metadata.version`, la forma estándar de la biblioteca de Python (`faker.VERSION`
  existe pero no forma parte de la API exportada). La copia de referencia vive versionada en
  `generator/manifest.json`. El generador escribe primero en un directorio temporal dentro de
  `data/` (que crea si no existe, porque git la ignora y falta en un clon limpio), reemplaza cada
  archivo con `os.replace` y escribe el manifiesto al final. La
  verificación recalcula las huellas de los archivos en disco y las compara con el manifiesto
  versionado, archivo por archivo.
- **Rationale**: las versiones dentro del manifiesto explican de inmediato una diferencia entre
  entornos. `hashlib.file_digest` (Python 3.11+) calcula la huella por bloques. `os.replace` es
  atómico en POSIX dentro del mismo sistema de archivos, así que nunca queda un CSV a medias. Si el
  proceso se corta entre dos reemplazos, el manifiesto anterior ya no coincide y la verificación lo
  detecta.
- **Alternatives considered**: formato `sha256sum` (no guarda filas ni huérfanos, que necesita el
  chequeo de conteos del principio IV); manifiesto con fecha de generación (rompería el
  determinismo).

## R16. Pruebas y CI

- **Decision**: `tests/generator/` con pytest. Un fixture de sesión genera una vez la
  configuración por defecto completa en un directorio temporal, y otro fixture usa una
  configuración reducida (unas 20 000 líneas) para las pruebas que generan varias veces. El
  workflow `checks.yml` añade un job `tests` con `uv sync --locked` y `uv run pytest`, sin GCP ni
  secretos y sin comparar con el manifiesto versionado.
- **Rationale**: FR-030 y FR-030a. La suite completa debe tardar menos de dos minutos (SC-002), y
  las pruebas de patrones necesitan el volumen completo para que las métricas sean estables. El job
  separado deja ver en el PR si falló el estilo o las pruebas.
- **Alternatives considered**: meter pytest como hook de pre-commit (ralentiza cada commit);
  generar el volumen completo en cada prueba (supera el tiempo objetivo).

## R17. Fijar el corte de 14 días con `exclude-newer` de uv

- **Decision**: no se usa en esta feature. Las versiones se fijan de forma exacta a mano, como en
  la feature 001.
- **Rationale**: uv acepta `exclude-newer` con duraciones relativas ("14 days"), lo que
  automatizaría la regla del dueño. Sin embargo, afectaría también a las dependencias de
  desarrollo ya fijadas y cambia la resolución con el paso del tiempo, así que merece una decisión
  propia.
- **Alternatives considered**: activarlo ahora (cambio de alcance no pedido).

## R18. Ruff para el código Python

- **Decision**: `ruff==0.16.8` en el grupo `dev`, configurado en `pyproject.toml` (`line-length =
  100` y `extend-select = ["B", "I", "UP"]` sobre las reglas por defecto). Se ejecuta con dos hooks
  locales de pre-commit (`ruff check` y `ruff format --check`, sin `--fix`), que corren también en
  CI con `make lint`. El dueño eligió esta opción el 2026-10-08.
- **Rationale**: los proyectos de Python de referencia (pandas, SciPy, FastAPI y Airflow, según la
  documentación de Ruff) usan Ruff para lint y formato, y sustituye a Flake8, Black e isort con una
  sola herramienta. 0.16.9 se publicó el 2026-09-24 a las 20:37 GMT y no cumple los 14 días con
  margen; 0.16.8 (2026-09-16) sí. La documentación de Ruff propone el repositorio
  `ruff-pre-commit`, pero un hook local que usa `.venv/bin/ruff` mantiene la versión en un solo
  lugar (`uv.lock`), igual que SQLFluff en la feature 001. Sin `--fix`, el orden de los hooks no
  importa según esa misma documentación, y se dejan lint y después formato. `B` (flake8-bugbear)
  detecta errores frecuentes, `I` ordena imports y `UP` moderniza la sintaxis a Python 3.12, que
  Ruff deduce de `requires-python`. 100 caracteres es el mismo límite que el principio II fija para
  el SQL.
- **Nota de implementación (2026-10-08)**: el conjunto por defecto de Ruff 0.16 es más amplio que
  el clásico `E4`, `E7`, `E9` y `F`. La página "Default Rules" de la documentación incluye reglas
  sueltas de `B`, `UP`, `PLW`, `S`, `BLE`, `ASYNC`, `SIM` y `RUF`, entre otras. Al activar los hooks
  aparecieron tres avisos en las pruebas de la feature 001 (`PLW1510`, `subprocess.run` sin `check`
  explícito, y `F401`, un import sin uso), que se corrigieron sin cambiar su comportamiento.
- **Alternatives considered**: sin linter de Python (el SQL tendría más disciplina que el código
  que genera los datos); Ruff más mypy (otra herramienta y las anotaciones ya documentan los
  tipos); `ruff-pre-commit` con su propio `rev` (dos fuentes de versión).

## R19. Configuración de pytest y estructura del paquete

- **Decision**: `generator/` se queda en la raíz, como prevé la constitución, y pytest se configura
  en `[tool.pytest]` de `pyproject.toml` con `--import-mode=importlib`, `pythonpath = ["."]`,
  `testpaths = ["tests"]` y `strict = true`. El dueño eligió esta opción el 2026-10-08.
- **Rationale**: la guía de pytest recomienda con fuerza la estructura `src/` con el paquete
  instalado, para que la raíz del repositorio no quede importable por accidente. Este proyecto no se
  empaqueta (`package = false`), así que esa estructura añadiría un backend de empaquetado sin uso.
  El modo `importlib`, que la guía recomienda para proyectos nuevos, no modifica `sys.path` al
  importar los módulos de prueba, y `pythonpath` añade solo la raíz de forma explícita. Pytest 9
  admite la tabla nativa `[tool.pytest]` con tipos TOML, y `strict = true` activa
  `strict_config`, `strict_markers`, `strict_parametrization_ids` y `strict_xfail`, de modo que una
  errata en la configuración o un marcador sin registrar fallan en lugar de ignorarse.
- **Alternatives considered**: `src/generator/` con `package = true` (se aparta de la estructura de
  la constitución sin beneficio para un proyecto que no se distribuye); dejar el modo `prepend` por
  defecto (la guía lo mantiene solo por compatibilidad).

## Fuentes

- NumPy, historial de versiones: <https://pypi.org/rss/project/numpy/releases.xml>
- NumPy 2.5.3, metadatos y wheels: <https://pypi.org/pypi/numpy/2.5.3/json>
- Faker, historial de versiones: <https://pypi.org/rss/project/faker/releases.xml>
- Faker 40.39.0, metadatos: <https://pypi.org/pypi/Faker/40.39.0/json>
- NumPy, generación aleatoria y semillas: <https://numpy.org/doc/stable/reference/random/index.html>
- NumPy, flujos paralelos y `spawn`: <https://numpy.org/doc/stable/reference/random/parallel.html>
- NumPy, política de compatibilidad: <https://numpy.org/doc/stable/reference/random/compatibility.html>
- Faker, semillas: <https://faker.readthedocs.io/en/master/index.html>
- Faker, locale `es_MX`: <https://faker.readthedocs.io/en/master/locales/es_MX.html>
- Python 3.12, módulo `csv`: <https://docs.python.org/3.12/library/csv.html>
- uv, referencia de configuración (`package`, `exclude-newer`): <https://docs.astral.sh/uv/reference/settings/>
- Ruff, historial de versiones: <https://pypi.org/rss/project/ruff/releases.xml>
- Ruff, configuración: <https://docs.astral.sh/ruff/configuration/>
- Ruff, integraciones y pre-commit: <https://docs.astral.sh/ruff/integrations/>
- Ruff, proyectos que lo usan: <https://docs.astral.sh/ruff/>
- pytest, buenas prácticas: <https://docs.pytest.org/en/stable/explanation/goodpractices.html>
- pytest, configuración en `pyproject.toml`: <https://docs.pytest.org/en/stable/reference/customize.html>
- pytest, referencia de opciones (`strict`, `pythonpath`, `--import-mode`): <https://docs.pytest.org/en/stable/reference/reference.html>
- pytest, `tmp_path_factory`: <https://docs.pytest.org/en/stable/how-to/tmp_path.html>
- Synthea: <https://github.com/synthetichealth/synthea>
- SDV: <https://github.com/sdv-dev/SDV>
- dbldatagen: <https://github.com/databrickslabs/dbldatagen>
- TOML 1.0, enteros: <https://toml.io/en/v1.0.0#integer>
- BigQuery, carga de CSV: <https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-csv>
- BigQuery, carga desde archivos locales: <https://docs.cloud.google.com/bigquery/docs/batch-loading-data>
- Google Cloud, nivel gratuito: <https://docs.cloud.google.com/free/docs/free-cloud-features>
- INEGI, servicio del catálogo único de claves geoestadísticas: <https://gaia.inegi.org.mx/wscatgeo/v2/mgee/>
- INEGI, catálogo AGEEML: <https://www.inegi.org.mx/app/ageeml/>
- DOF, lineamientos CLUES y catálogo de instituciones: <https://dof.gob.mx/nota_detalle_popup.php?codigo=5283475>
- DGIS, catálogos CLUES: <http://www.dgis.salud.gob.mx/contenidos/intercambio/clues_gobmx.html>
- DGIS, datos abiertos CLUES 2022: <http://www.dgis.salud.gob.mx/descargas/datosabiertos/recursosSalud/CLUES_2022.csv>
- DOF, Cuadro Básico y Catálogo de Medicamentos, edición 2014 (grupos terapéuticos y formato de descripción): <https://farmacopea.org.mx/Repositorio/LegislacionFiles/CBCMed2014_02mar15.pdf>
- INEGI, servicio de municipios por entidad: <https://gaia.inegi.org.mx/wscatgeo/v2/mgem/>
- RENAPO, instructivo normativo de la CURP: <https://www.gob.mx/cms/uploads/attachment/file/337251/Instructivo_Normativo_para_la_Asignacion_de_la_CURP.pdf>
- IMSS, procedimiento con la estructura de la clave: <https://www.imss.gob.mx/sites/all/statics/pdf/procedimientos/1832-003-002.pdf>
- Gobierno de Oaxaca, anexo de licitación con claves del Compendio: <https://www.oaxaca.gob.mx/administracion/wp-content/uploads/sites/66/2020/03/ANEXO-M.pdf>
- DOF, modificación al Compendio 2025: <https://sidof.segob.gob.mx/notas/docFuente/5799600>
- MVS Noticias, entidades no adheridas a IMSS-Bienestar (agosto de 2026): <https://mvsnoticias.com/nacional/2026/8/18/rebasa-imss-bienestar-a-entidades-no-adheridas-742399.html>
- El Financiero, conferencia del 20 de enero de 2026: <https://www.elfinanciero.com.mx/nacional/2026/01/20/claudia-sheinbaum-mananera-temas-hoy-20-de-enero-de-2026-en-vivo/>
