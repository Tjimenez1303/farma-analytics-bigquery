# Contrato: `make doctor` (`scripts/doctor.sh`)

## Invocación

- `make doctor`. El script también admite ejecución directa, pero entonces exige que
  `BIGQUERYRC` apunte al `.bigqueryrc` del repositorio (si no, termina con código 2).
- Sin argumentos. Variable opcional `DOCTOR_TIMEOUT` (segundos por llamada remota, por defecto
  10).
- MUST NOT ejecutar consultas facturables ni modificar recursos locales o remotos.

## Salida

Una línea por chequeo, en el orden del catálogo, con columnas alineadas:

```text
ESTADO   ID   NOMBRE                       VALOR
         remedio: <comando o sección del README>     (solo si no es OK)
```

Al final, una línea de resumen: `Resumen: N OK, N AVISO, N FALLO, N OMITIDO`.

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | Ningún chequeo en `FALLO` (puede haber `AVISO` u `OMITIDO`). |
| 1 | Al menos un chequeo en `FALLO`. |
| 2 | El diagnóstico no pudo arrancar (sin `BIGQUERYRC`, o sin `.venv/bin/python` ni `python3` para leer JSON). |

## Catálogo de chequeos

| ID | Nombre | Depende de | OK | AVISO | FALLO | OMITIDO |
|---|---|---|---|---|---|---|
| T01 | gcloud | | versión ≥ mínima | | ausente o versión menor | |
| T02 | bq | | versión ≥ mínima | | ausente o versión menor | |
| T03 | Python del proyecto | T10 | `.venv/bin/python` coincide con `.python-version` | | falta `.venv` (remedio `make setup-dev`) o la versión no coincide | T10 falló |
| T04 | Node.js | | ≥ 22.0.0 | | ausente o menor | |
| T05 | Dataform CLI | T04 | = versión de `package.json` | otra versión | ausente | T04 falló |
| T06 | SQLFluff | T03 | = versión del grupo `dev` de `pyproject.toml` | otra versión | ausente | T03 falló |
| T07 | pre-commit | T03 | = versión del grupo `dev` de `pyproject.toml` | otra versión | ausente | T03 falló |
| T08 | ripgrep | | ≥ 14.0.0 | | ausente o menor | |
| T09 | make | | ≥ 3.81 | | ausente o menor | |
| T10 | uv | | cumple `required-version` de `pyproject.toml` | | ausente o versión menor | |
| C01 | `.bigqueryrc` del repositorio | | `BIGQUERYRC` apunta al repositorio y el archivo fija location, dialecto en `[query]` y `[mk]` y `maximum_bytes_billed`, sin proyecto | | falta algún valor o incluye proyecto | |
| C02 | `~/.bigqueryrc` personal | | no existe | existe (se ignora vía `BIGQUERYRC`) | | |
| C03 | Credenciales en el repositorio | | `GOOGLE_APPLICATION_CREDENTIALS` vacío o fuera del repositorio | | apunta dentro del repositorio | |
| N01 | Red | | Google APIs accesibles | | | sin red: A01 a A04, P02 y B01 a B03 pasan a OMITIDO (P01 es local y se evalúa igual) |
| A01 | Cuenta de gcloud | T01, N01 | hay cuenta activa | | sin cuenta activa | dependencia |
| A02 | ADC | T01, N01 | devuelve credencial | | sin ADC | dependencia |
| A03 | Proyecto de cuota de ADC | A02 | definido | falta | | dependencia |
| A04 | Misma cuenta en gcloud y ADC | A01, A02 | coinciden | difieren o no se puede saber | | dependencia |
| P01 | Proyecto de GCP | T01 | resuelto desde `.env` o `gcloud` | `.env` y `gcloud` difieren | ninguno | dependencia |
| P02 | Facturación | P01, N01 | activa | inactiva (sandbox) | | sin permiso o API |
| B01 | Dry run en la location | T02, A01, P01 | se valida en la location de `.bigqueryrc` | no se pudo leer la location del job | API deshabilitada, sin permiso, location distinta | dependencia |
| B02 | Dialecto del proyecto | B01 | el dry run en legacy SQL es rechazado | | el dry run en legacy SQL se valida (el remedio indica `make gcp-dialect` y la región `region-<loc>` que debe tener el ajuste) | dependencia, o fallback de R2 |
| B03 | Location de `farma_analytics` | B01 | igual a la de `.bigqueryrc` | | distinta | el dataset no existe, o dependencia |
| B04 | Límite de bytes | C01 | muestra `maximum_bytes_billed` en GiB | | | dependencia |

Notas:

- Cada `FALLO` y cada `AVISO` llevan remedio. Ejemplos: `brew install ripgrep`,
  `gcloud auth application-default login`, `make gcp-dialect`,
  `gcloud services enable bigquery.googleapis.com --project=<P>`.
- B01 y B02 son las únicas llamadas a `bq query`, ambas con `--dry_run`. Ningún job aparece en el
  historial del proyecto.
- Los ocho escenarios de SC-003 corresponden a: T08 (herramienta ausente), T04 (versión menor que
  la mínima), T03 (Python distinto del fijado), A02 (sin ADC), P01 (sin proyecto), B02 (dialecto
  sin fijar en la región configurada; un ajuste en otra región se ve igual), B03 (location
  distinta) y C03 (credenciales dentro del repositorio).
- `curl` (N01 y A04) se asume presente: viene de serie en macOS y Linux.
- Para leer JSON se usa `.venv/bin/python` si existe y, si no, `python3` del sistema (en macOS
  puede ser 3.9). Las versiones de `pyproject.toml` (`required-version` y grupo `dev`) se leen con
  `sed` o `grep`, sin `tomllib`, para no depender de la versión de ese `python3`.
- Un chequeo pasa a `OMITIDO` si alguna dependencia está en `FALLO` u `OMITIDO`.
- Las pruebas pueden sustituir la ruta de `.venv` con `DOCTOR_VENV` y la de `node_modules/.bin` con
  `DOCTOR_NODE_BIN`.
