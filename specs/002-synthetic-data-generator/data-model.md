# Data Model: Generador de datos sintéticos

**Feature**: `002-synthetic-data-generator` | **Fecha**: 2026-10-08 | **Plan**: [plan.md](plan.md)

Los nombres de tabla y de campo son contractuales (principio I). El tipo BigQuery es el que usará
la DDL de la feature de carga (principio II) y el formato CSV es el de
[contracts/csv-format.md](contracts/csv-format.md).

## 1. Fuentes del entregable

### 1.1 `CLUE_CAT` (dimensión de unidades médicas)

- **Grano**: una unidad médica.
- **Llave**: `CLUE`, única. Clave primaria `NOT ENFORCED` declarable en la carga una vez
  verificada la unicidad.
- **Orden de las filas**: por `CLUE`.

| Campo | Tipo BigQuery | Obligatorio | Regla |
|---|---|---|---|
| `CLUE` | `STRING` | Sí | 11 caracteres: código de entidad (2 letras) + prefijo de institución (3 letras) + consecutivo (6 dígitos). Los prefijos concuerdan con `ENTIDAD` e `INSTITUCION` (FR-023). Regex: `^[A-Z]{2}(IMS\|IST\|SDN\|SMA\|PMX\|IMO\|SSA)[0-9]{6}$`. |
| `ENTIDAD` | `STRING` | Sí | Uno de los 32 nombres oficiales del INEGI (`reference/entidades.csv`). Las 32 aparecen (FR-020). |
| `INSTITUCION` | `STRING` | Sí | Uno de los valores canónicos `IMSS`, `ISSSTE`, `SEDENA`, `SEMAR`, `PEMEX`, `IMSS-Bienestar` o `Servicios Estatales de Salud`, con la presencia por entidad de [research.md R7](research.md#r7-instituciones-prefijos-clues-y-grupo-institucional). |
| `DELEGACION` | `STRING` | Sí | Prefijo de la institución + nombre de la entidad (por ejemplo "OOAD Jalisco" en el IMSS). Coherente con `ENTIDAD` e `INSTITUCION` (FR-021). |
| `GRUPO_INSTITUCIONAL` | `STRING` | Sí | "Seguridad social", "Fuerzas Armadas y PEMEX" o "Población sin seguridad social", según la institución (FR-019a). |
| `NIVEL_ATENCION` | `STRING` | Sí | "Primer nivel", "Segundo nivel" o "Tercer nivel", con más unidades de primer nivel que de tercero (FR-022). |
| `MUNICIPIO` | `STRING` | Sí | Municipio o alcaldía real de `ENTIDAD` (`reference/municipios.csv`). |

### 1.2 `CUADRO_BASICO` (dimensión de insumos)

- **Grano**: una clave del Compendio (una presentación de una molécula).
- **Llave**: `CLAVE`, única.
- **Orden de las filas**: por `CLAVE`.

| Campo | Tipo BigQuery | Obligatorio | Regla |
|---|---|---|---|
| `CLAVE` | `STRING` | Sí | `010.000.NNNN.DD`. Regex: `^010\.000\.[0-9]{4}\.[0-9]{2}$` (FR-024). |
| `DESCRIPCION` | `STRING` | Sí | Texto del estilo del Compendio: molécula, forma, contenido por unidad y envase. Puede llevar comas y se entrecomilla al escribir. |
| `MOLECULA` | `STRING` | Sí | Denominación genérica real. Varias claves pueden compartir molécula. |
| `GRUPO_TERAPEUTICO` | `STRING` | Sí | Grupo de medicamentos del Compendio. Cada molécula pertenece a uno solo. |
| `PRESENTACION` | `STRING` | Sí | Forma farmacéutica, concentración y envase, coherente con `DESCRIPCION`. |
| `FABRICANTE` | `STRING` | Sí | Fabricante innovador de referencia de la molécula (ficticio). Pertenece al conjunto de fabricantes autorizados de la clave (FR-025). |

### 1.3 `COMPRAS` (tabla de hechos)

- **Grano**: una línea de compra (una entrega de una clave a una unidad médica por un proveedor,
  con una marca y un fabricante, en una fecha). Sin llave natural única.
- **Medidas aditivas**: `PIEZAS` e `IMPORTE`.
- **Orden de las filas**: por `FECHA`, `CLUE`, `CLAVE` y, en empate, por el orden de generación.
- **Claves foráneas**: no se declaran, porque hay huérfanos deliberados (principio III).

| Campo | Tipo BigQuery | Obligatorio | Regla |
|---|---|---|---|
| `CLUE` | `STRING` | Sí | Existe en `CLUE_CAT`, salvo huérfanos (R13). Mismo formato siempre. |
| `CLAVE` | `STRING` | Sí | Existe en `CUADRO_BASICO`, salvo huérfanos. Mismo formato siempre. |
| `COD_PROVEEDOR` | `STRING` | Sí | `PRV` + 5 dígitos (por ejemplo `PRV00042`). Identifica a un proveedor ficticio en todas sus filas. |
| `MARCA` | `STRING` | Sí | Marca ficticia. Cada marca pertenece a un solo fabricante (FR-025). |
| `FABRICANTE` | `STRING` | Sí | Fabricante ficticio autorizado para la clave. Puede diferir del de `CUADRO_BASICO`. |
| `PIEZAS` | `INT64` | Sí | Entero de 1 al máximo configurado. |
| `IMPORTE` | `NUMERIC` | Sí | `PIEZAS × precio_unitario`, en pesos con dos decimales exactos. `IMPORTE / PIEZAS` cae en la banda de su clave (FR-016). |
| `FECHA` | `DATE` | Sí | Día laborable dentro del rango de la configuración. |

## 2. Entidades internas del generador

No son fuentes del entregable y no se escriben en `data/`.

| Entidad | Atributos | Relaciones y reglas |
|---|---|---|
| Fabricante | nombre, tipo (innovador o genérico), factor único | 12 innovadores y 28 genéricos. Ficticios, con nombre compuesto por apellidos de Faker `es_MX` y forma societaria. Ninguno contiene un nombre de la lista de exclusión de laboratorios reales. El factor de precio es el mismo para todas sus moléculas (principio V). |
| Fabricantes autorizados de una molécula | molécula, un innovador de referencia y de 1 a 4 genéricos | El innovador de referencia es el `FABRICANTE` de todas las claves de la molécula en `CUADRO_BASICO`. Todas las líneas de `COMPRAS` usan un fabricante autorizado. |
| Marca | nombre, fabricante, molécula | Una por par fabricante-molécula. Nombre único en todo el conjunto. |
| Proveedor | `COD_PROVEEDOR`, nombre interno | Unos 60. Cada fabricante se distribuye por 1 a 3 proveedores. |
| Precio base | clave, centavos | Se sortea en el rango del nivel de precio de la molécula y se redondea a centavos una vez. |
| Factor de fabricante | fabricante, factor | Un solo factor por fabricante: innovadores en `factor_referencia` y genéricos en `factor_generico` de la configuración. |
| Banda de precio | clave, mínimo y máximo en centavos | `base × factor mínimo de sus fabricantes autorizados × (1 - ruido_max)` a `base × factor máximo de sus fabricantes autorizados × (1 + ruido_max)`, con un centavo de margen por redondeo. |

## 3. Catálogos de referencia (`generator/reference/`)

CSV versionados, UTF-8, con su fuente en la documentación de los datos.

| Archivo | Columnas | Fuente |
|---|---|---|
| `entidades.csv` | `cve_ent`, `entidad`, `codigo_clues`, `poblacion_2020`, `imss_bienestar`, `sedena`, `semar`, `pemex` | INEGI (nombres y población del Censo 2020), datos abiertos CLUES 2022 de la DGIS (códigos y presencia de SEDENA, SEMAR y PEMEX), fuentes de R7 (adhesión a IMSS-Bienestar) |
| `municipios.csv` | `cve_ent`, `cve_mun`, `municipio`, `poblacion_2020` | INEGI, catálogo único de claves geoestadísticas |
| `instituciones.csv` | `institucion`, `prefijo_clues`, `grupo_institucional`, `prefijo_delegacion`, `presencia` | DOF, anexo 2 de los lineamientos CLUES, y aclaración de la spec |
| `moleculas.csv` | `molecula`, `grupo_terapeutico`, `nivel_precio`, `presentaciones` (separadas por `\|`, cada una con `forma;unidad;concentración;envase`) | Denominaciones genéricas y grupos del Cuadro Básico publicado en el DOF |
| `laboratorios_reales.txt` | un nombre o raíz por línea | Lista de exclusión (R3) |

## 4. Configuración (`generator/config.toml`)

Estructura completa y rangos válidos en [contracts/config.md](contracts/config.md). Grupos de
parámetros:

- `seed`: semilla raíz (texto hexadecimal de 128 bits).
- `[periodo]`: fecha inicial y final, solo días laborables.
- `[volumen]`: líneas de compra, unidades médicas, fabricantes innovadores y genéricos,
  genéricos por molécula y proveedores.
- `[huerfanos]`: `orphan_rate` y reparto entre `CLUE` y `CLAVE`.
- `[concentracion]`: `alpha` de moléculas, moléculas destacadas con rango fijo, `beta` de entidades, participación por institución y
  reparto y multiplicador de compra por nivel de atención.
- `[estacionalidad]`: doce factores mensuales y crecimiento total de un año a otro.
- `[precios]`: rango de cada nivel de precio, factores de referencia y genéricos, ruido máximo y
  distribución de `PIEZAS`.
- `[patrones]`: P3 (molécula de ejemplo y probabilidad de referencia por institución), P4 (factor de crecimiento por
  grupo terapéutico) y P5 (moléculas, genérico elegido y cuotas inicial y final).

## 5. Manifiesto

Formato en [contracts/manifest.md](contracts/manifest.md). Reglas:

- Determinista: claves ordenadas, sin fechas, sin rutas absolutas.
- `files` ordenado por nombre, con `name`, `sha256`, `bytes` y `rows` (sin encabezado).
- `orphans` con los conteos `CLUE` y `CLAVE`.
- Copia generada en `data/manifest.json` (ignorada por git) y copia de referencia versionada en
  `generator/manifest.json`.

## 6. Ciclo de vida de los archivos

```text
config.toml ──validar──> error (código 2, nada se escribe)
     │
     └─generar en data/.tmp-*/ ──> reemplazar CSV con os.replace ──> escribir data/manifest.json
                                                                        │
                       verificar contra generator/manifest.json ─────────┤
                                                                        ├─ coincide: código 0
                                                                        └─ difiere: código 1, archivo por archivo
```

Cambiar un parámetro a propósito exige regenerar y actualizar la copia versionada del manifiesto
con `make data-manifest` en el mismo PR.
