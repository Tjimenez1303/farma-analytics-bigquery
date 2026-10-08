# Contrato: línea de comandos del generador y objetivos de `make`

## Línea de comandos

Se invoca como módulo desde la raíz del repositorio, dentro del entorno de uv:

```text
uv run python -m generator generate [--config PATH] [--out DIR]
uv run python -m generator verify   [--manifest PATH] [--data DIR]
```

| Subcomando | Valores por defecto | Qué hace | Salida |
|---|---|---|---|
| `generate` | `--config generator/config.toml`, `--out data` | Valida la configuración, genera las tres fuentes en un directorio temporal dentro de `--out`, reemplaza cada CSV con `os.replace` y escribe `manifest.json` al final. | Una línea por archivo con nombre, filas y SHA-256 abreviado, más los conteos de huérfanos. |
| `verify` | `--manifest generator/manifest.json`, `--data data` | Recalcula SHA-256, bytes y filas de los CSV de `--data` y los compara con el manifiesto indicado. Si difieren las versiones de Python, NumPy o Faker, lo dice. | `OK` por archivo, o `DIFIERE` con el valor esperado y el obtenido. |

Códigos de salida:

| Código | Significado |
|---|---|
| 0 | Generación o verificación correcta. |
| 1 | La verificación encontró diferencias o falta algún archivo. |
| 2 | Configuración inválida o argumentos incorrectos. El mensaje nombra el parámetro, el valor recibido y el rango válido, y no se escribe nada. |

Garantías:

- Sin red, sin GCP y sin variables de entorno que alteren la salida.
- Los mensajes para el usuario van en español. Los nombres de campo y de archivo, tal cual.
- Ninguna salida incluye la fecha ni la hora de ejecución.

## Objetivos de `make`

Se añaden al `Makefile` de la feature 001 con las mismas reglas: GNU Make 3.81, `SHELL :=
/bin/bash`, `require-venv` antes de usar `uv run` y una línea `## ` de ayuda en español.

| Objetivo | Comando | Efectos | Toca GCP | Lo ejecuta |
|---|---|---|---|---|
| `data` | `uv run python -m generator generate` y después `uv run python -m generator verify` | Escribe `data/COMPRAS.csv`, `data/CLUE_CAT.csv`, `data/CUADRO_BASICO.csv` y `data/manifest.json`. Termina con código 1 si el manifiesto no coincide con el versionado. | No | Cualquiera |
| `data-verify` | `uv run python -m generator verify` | Ninguno. Comprueba los archivos de `data/` contra `generator/manifest.json`. | No | Cualquiera |
| `data-manifest` | `cp data/manifest.json generator/manifest.json` tras comprobar que existe | Actualiza la copia versionada cuando un cambio de parámetros es intencional. | No | Dueño, en el mismo PR que el cambio de configuración |
| `test` (existente) | `uv run pytest tests/` | Ahora incluye `tests/generator/`. | No | Cualquiera |

Errores:

- Si `.venv` no existe, `data`, `data-verify` y `data-manifest` piden ejecutar `make setup-dev`.
- Si `data/manifest.json` no existe, `data-manifest` termina con código 1 y pide ejecutar
  `make data` antes.
