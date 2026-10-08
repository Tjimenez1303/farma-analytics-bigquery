# Contrato: `scripts/lint_prosa.sh`

## Uso

```text
scripts/lint_prosa.sh                 # alcance por defecto
scripts/lint_prosa.sh RUTA [RUTA...]  # archivos o directorios concretos
scripts/lint_prosa.sh -               # texto por entrada estándar (mensaje de commit, PR)
make lint-prosa                       # equivale a la primera forma
```

- Alcance por defecto: `README.md`, `docs/**/*.md` y los comentarios de `sql/**/*.sql`.
- Variable opcional `LINT_PROSA_MULETILLAS`: ruta alternativa de la lista (por defecto
  `scripts/muletillas.txt`). Aparece comentada en `.env.example`.
- Fuera del alcance por defecto: `tests/fixtures/` (las pruebas lo pasan como ruta explícita).
- Siempre excluidos, aunque se pasen como ruta: `specs/`, `.specify/`, archivos de configuración (`*.yaml`,
  `*.yml`, `*.toml`, `*.json`, `*.env`, `.bigqueryrc`, `.sqlfluff`), `scripts/muletillas.txt` y
  `scripts/prosa_excepciones.txt`.
- Tipos de archivo: `.md` y `.txt` se revisan como prosa, `.sql` solo en sus comentarios (`--` y
  `/* */`). Otros tipos se ignoran con un aviso por la salida de errores.

## Salida y códigos

- Una línea por marca: `RUTA:LÍNEA: CATEGORÍA: FRAGMENTO`. Con entrada estándar, la ruta es
  `<stdin>`.
- Resumen final por la salida de errores: `N marcas en M de K archivos revisados`.
- Código 0 sin marcas, 1 con marcas, 2 por error de uso (ruta inexistente, ripgrep ausente).

## Preproceso (antes de buscar)

1. Los restos de herramientas se buscan sobre el texto original.
2. Se sustituyen por líneas vacías los bloques de código cercados, las líneas con el marcador
   `lint-prosa: ignorar` y los términos de la sección `[terminos]` de
   `scripts/prosa_excepciones.txt`.
3. Se eliminan el código en línea (entre comillas invertidas) y las URL.
4. En los `.sql`, se conserva solo el texto de los comentarios.
5. El número de línea de cada marca es el del archivo original.

## Categorías

| Categoría | Qué marca | Qué no marca |
|---|---|---|
| `raya` | `—` y `–` | |
| `guion-como-raya` | ` - ` entre palabras dentro de una línea | marcadores de lista al inicio de línea, flags, kebab-case, rangos (2024-2025), compuestos, fechas ISO, negativos |
| `punto-y-coma` | `;` en prosa | `;` dentro de código o en `.sql` fuera de comentarios |
| `emoji` | `\p{Extended_Pictographic}` | |
| `flecha-o-caja` | `→`, `←`, `⇒`, `✅`, `★`, `•` y caracteres de dibujo de cajas (U+2500 a U+257F) | |
| `comillas-curvas` | `“ ” ‘ ’` | comillas rectas y latinas |
| `title-case` | encabezado Markdown con alguna palabra no inicial en mayúscula inicial que no sea sigla, no tenga mayúsculas internas y no esté en `[nombres_propios]` | primera palabra, siglas (IMSS), nombres con mayúsculas internas (BigQuery) |
| `negrita-con-dos-puntos` | elementos de lista que empiezan con `**texto:**` o `**texto**:` | negritas sueltas |
| `resto-de-herramienta` | `oaicite`, `contentReference`, `utm_source=chatgpt.com`, `turn0search`, marcadores como `[insertar ...]` | |
| `muletilla` | cada entrada de `scripts/muletillas.txt` | términos de `[terminos]` |

## Formatos de lista

`scripts/muletillas.txt`:

```text
# Fórmulas de relleno
cabe destacar
es importante señalar
re:\bpotenci(ar|a|an|amos|ó)\b
```

`scripts/prosa_excepciones.txt`:

```text
[terminos]
clave primaria
estimador robusto
medicamento innovador

[nombres_propios]
BigQuery
Data
Studio
```

Añadir una entrada a cualquiera de los dos archivos cambia el comportamiento sin tocar el script
(spec, historia 4, escenario 6). Varias coincidencias de la misma categoría en una línea cuentan
como una sola marca.
