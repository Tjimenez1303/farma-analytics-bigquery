# Contrato: manifiesto (`data/manifest.json` y `generator/manifest.json`)

JSON en UTF-8 sin BOM, claves ordenadas alfabéticamente, sangría de 2 espacios, separadores
`", "`/`": "` por defecto de `json.dumps` con `indent`, saltos LF y un salto final. Sin fechas,
rutas absolutas ni datos del entorno fuera de las versiones. El ejemplo muestra los objetos de
`files` en una línea para que se lea mejor. El archivo real usa la sangría en todos los niveles.

```json
{
  "config_sha256": "<sha256 de los bytes de generator/config.toml>",
  "files": [
    {"bytes": 0, "name": "CLUE_CAT.csv", "rows": 0, "sha256": "<hex>"},
    {"bytes": 0, "name": "COMPRAS.csv", "rows": 0, "sha256": "<hex>"},
    {"bytes": 0, "name": "CUADRO_BASICO.csv", "rows": 0, "sha256": "<hex>"}
  ],
  "format_version": 1,
  "orphans": {"CLAVE": 0, "CLUE": 0},
  "versions": {"faker": "40.39.0", "numpy": "2.5.3", "python": "3.12.14"}
}
```

| Campo | Regla |
|---|---|
| `config_sha256` | Huella de los bytes exactos de la configuración usada. |
| `files[]` | Ordenado por `name`. `rows` cuenta filas de datos sin el encabezado. `bytes` es el tamaño en disco. |
| `format_version` | Entero. Cambia solo si cambia este contrato. |
| `orphans` | Filas de `COMPRAS` con `CLUE` sin correspondencia y con `CLAVE` sin correspondencia. Son conjuntos disjuntos. |
| `versions` | Versiones exactas en tiempo de ejecución (`platform.python_version()`, `importlib.metadata.version("numpy")` e `importlib.metadata.version("faker")`). |

Comparación en `verify`:

- Por archivo: existencia, `sha256`, `bytes` y `rows`.
- `config_sha256` y `orphans`: deben coincidir.
- `versions`: si difieren, se informa como causa probable de las diferencias, junto al resto.

Consumidores posteriores: la feature de carga usa `rows` y `orphans` para el chequeo de conteos y la
reconciliación del `INNER JOIN` (principio IV).
