#!/bin/bash
# Environment diagnosis for farma-analytics-bigquery.
# Read-only: runs local commands, metadata reads and BigQuery dry runs only.
# Compatible with bash 3.2 (macOS default).

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TIMEOUT="${DOCTOR_TIMEOUT:-10}"
VENV="${DOCTOR_VENV:-$REPO_ROOT/.venv}"
CATALOG="T01 T02 T03 T06 T07 T08 T09 T10 C01 C02 C03 N01 A01 A02 A03 A04 P01 P02 B01 B02 B03 B04"
N_OK=0
N_AVISO=0
N_FALLO=0
N_OMITIDO=0

# --- Startup guards -------------------------------------------------------

if [ -z "${BIGQUERYRC:-}" ] || [ ! -f "$BIGQUERYRC" ] || ! [ "$BIGQUERYRC" -ef "$REPO_ROOT/.bigqueryrc" ]; then
  echo "BIGQUERYRC debe apuntar a $REPO_ROOT/.bigqueryrc. Ejecuta el diagnóstico con 'make doctor'." >&2
  exit 2
fi

if [ -x "$VENV/bin/python" ]; then
  PY="$VENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "No hay intérprete de Python para leer JSON (.venv/bin/python ni python3)." >&2
  exit 2
fi

# shellcheck source=tool_versions.env
. "$REPO_ROOT/scripts/tool_versions.env"

# --- Helpers ---------------------------------------------------------------

# Record a check result. Usage: record ID NAME STATUS VALUE [REMEDY]
record() {
  local id=$1 name=$2 status=$3 value=$4 remedy=${5:-}
  local line pad
  # Pad by characters, not bytes, so accented names stay aligned.
  pad=$((32 - ${#name}))
  [ "$pad" -lt 1 ] && pad=1
  line=$(printf '%-8s %-4s %s%*s%s' "$status" "$id" "$name" "$pad" '' "$value")
  if [ "$status" != "OK" ] && [ -n "$remedy" ]; then
    line="$line"$'\n'"$(printf '%-8s %-4s remedio: %s' '' '' "$remedy")"
  fi
  eval "ST_$id=\$status"
  eval "OUT_$id=\$line"
  case "$status" in
    OK) N_OK=$((N_OK + 1)) ;;
    AVISO) N_AVISO=$((N_AVISO + 1)) ;;
    FALLO) N_FALLO=$((N_FALLO + 1)) ;;
    OMITIDO) N_OMITIDO=$((N_OMITIDO + 1)) ;;
  esac
}

status_of() {
  eval "printf '%s' \"\${ST_$1:-}\""
}

# Skip a check when a dependency failed or was skipped. Usage: depends_on ID NAME DEP...
depends_on() {
  local id=$1 name=$2 dep st
  shift 2
  for dep in "$@"; do
    st=$(status_of "$dep")
    if [ "$st" = "FALLO" ] || [ "$st" = "OMITIDO" ]; then
      record "$id" "$name" OMITIDO "depende de $dep ($st)" "resuelve primero $dep"
      return 1
    fi
  done
  return 0
}

# Return 0 when version $1 >= version $2.
version_ge() {
  local IFS=.
  local -a a b
  a=($1)
  b=($2)
  local i x y
  for i in 0 1 2 3; do
    x=${a[i]:-0}
    y=${b[i]:-0}
    x=${x%%[!0-9]*}
    y=${y%%[!0-9]*}
    x=${x:-0}
    y=${y:-0}
    if ((10#$x > 10#$y)); then return 0; fi
    if ((10#$x < 10#$y)); then return 1; fi
  done
  return 0
}

# First dotted version number in a text.
first_version() {
  grep -Eo '[0-9]+(\.[0-9]+)+' | head -1
}

# Run a command with a timeout. Usage: run_timeout SECONDS CMD...
run_timeout() {
  local secs=$1
  shift
  "$@" &
  local pid=$!
  (sleep "$secs" && kill -TERM "$pid") >/dev/null 2>&1 &
  local watcher=$!
  wait "$pid"
  local rc=$?
  kill "$watcher" >/dev/null 2>&1
  wait "$watcher" 2>/dev/null
  return $rc
}

# Value of a flag in .bigqueryrc. Usage: rc_value SECTION FLAG (empty SECTION = global).
rc_value() {
  awk -v sec="$1" -v flag="$2" '
    /^\[.*\]$/ { cur = substr($0, 2, length($0) - 2); next }
    cur == sec && index($0, flag "=") == 1 { print substr($0, length(flag) + 2); exit }
  ' "$BIGQUERYRC"
}

# Read a key from JSON on stdin.
json_get() {
  "$PY" -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
for key in sys.argv[1].split("."):
    data = data.get(key, {}) if isinstance(data, dict) else {}
print(data if isinstance(data, str) else "")
' "$1"
}

# Pinned version of a dev dependency in pyproject.toml.
dev_pin() {
  sed -n "s/^ *\"$1==\([^\"]*\)\".*/\1/p" "$REPO_ROOT/pyproject.toml" | head -1
}

# Locate a tool: preferred directory first, then PATH.
locate() {
  if [ -x "$2/$1" ]; then
    printf '%s' "$2/$1"
  else
    command -v "$1" 2>/dev/null
  fi
}

# Check a system tool against a minimum version.
check_min() {
  local id=$1 name=$2 cmd=$3 min=$4 remedy=$5 version_cmd=$6
  if ! command -v "$cmd" >/dev/null 2>&1; then
    record "$id" "$name" FALLO "no encontrado (mínimo $min)" "$remedy"
    return
  fi
  local found
  found=$(eval "$version_cmd" 2>/dev/null | first_version)
  if [ -z "$found" ]; then
    record "$id" "$name" FALLO "versión no reconocida (mínimo $min)" "$remedy"
  elif version_ge "$found" "$min"; then
    record "$id" "$name" OK "$found (mínimo $min)"
  else
    record "$id" "$name" FALLO "$found (mínimo $min)" "$remedy"
  fi
}

# Check a tool against an exact pinned version.
check_exact() {
  local id=$1 name=$2 path=$3 pinned=$4 remedy=$5
  if [ -z "$path" ]; then
    record "$id" "$name" FALLO "no encontrado (fijado $pinned)" "$remedy"
    return
  fi
  local found
  found=$("$path" --version 2>/dev/null | first_version)
  if [ "$found" = "$pinned" ]; then
    record "$id" "$name" OK "$found"
  else
    record "$id" "$name" AVISO "${found:-desconocida} (fijado $pinned)" "$remedy"
  fi
}

# --- Tools (T01 to T10) ----------------------------------------------------

check_min T01 "gcloud" gcloud "$MIN_GCLOUD" \
  "instala o actualiza Google Cloud CLI: https://cloud.google.com/sdk/docs/install (gcloud components update)" \
  "gcloud version | grep 'Google Cloud SDK'"
check_min T02 "bq" bq "$MIN_BQ" \
  "bq viene con Google Cloud CLI: gcloud components update" \
  "bq version"

uv_min=$(sed -n 's/^required-version *= *"[^0-9]*\([0-9.]*\)".*/\1/p' "$REPO_ROOT/pyproject.toml")
check_min T10 "uv" uv "$uv_min" \
  "brew install uv (macOS) o curl -LsSf https://astral.sh/uv/install.sh | sh (Linux)" \
  "uv --version"

if depends_on T03 "Python del proyecto" T10; then
  pinned_py=$(tr -d '[:space:]' < "$REPO_ROOT/.python-version")
  if [ ! -x "$VENV/bin/python" ]; then
    record T03 "Python del proyecto" FALLO "falta .venv (fijado $pinned_py)" "make setup-dev"
  else
    found_py=$("$VENV/bin/python" --version 2>&1 | first_version)
    if [ "$found_py" = "$pinned_py" ]; then
      record T03 "Python del proyecto" OK "$found_py"
    else
      record T03 "Python del proyecto" FALLO "$found_py (fijado $pinned_py)" "make setup-dev"
    fi
  fi
fi

if depends_on T06 "SQLFluff" T03; then
  check_exact T06 "SQLFluff" "$(locate sqlfluff "$VENV/bin")" "$(dev_pin sqlfluff)" "make setup-dev"
fi
if depends_on T07 "pre-commit" T03; then
  check_exact T07 "pre-commit" "$(locate pre-commit "$VENV/bin")" "$(dev_pin pre-commit)" "make setup-dev"
fi

check_min T08 "ripgrep" rg "$MIN_RIPGREP" \
  "brew install ripgrep (macOS) o sudo apt install ripgrep (Linux)" \
  "rg --version"
check_min T09 "make" make "$MIN_MAKE" \
  "xcode-select --install (macOS) o sudo apt install make (Linux)" \
  "make --version"

# --- Local configuration (C01 to C03) ----------------------------------------

LOCATION=$(rc_value "" "--location")
MAX_BYTES=$(rc_value "query" "--maximum_bytes_billed")
c01_missing=""
[ -n "$LOCATION" ] || c01_missing="$c01_missing --location"
[ "$(rc_value query --use_legacy_sql)" = "false" ] || c01_missing="$c01_missing [query]--use_legacy_sql=false"
[ "$(rc_value mk --use_legacy_sql)" = "false" ] || c01_missing="$c01_missing [mk]--use_legacy_sql=false"
case "$MAX_BYTES" in
  '' | *[!0-9]*) c01_missing="$c01_missing --maximum_bytes_billed" ;;
  *) [ "$MAX_BYTES" -gt 10485760 ] || c01_missing="$c01_missing --maximum_bytes_billed>10MB" ;;
esac
if grep -q -- '--project_id' "$BIGQUERYRC"; then
  record C01 ".bigqueryrc del repositorio" FALLO "incluye --project_id" "quita --project_id de .bigqueryrc"
elif [ -n "$c01_missing" ]; then
  record C01 ".bigqueryrc del repositorio" FALLO "falta:$c01_missing" "revisa .bigqueryrc según el README"
else
  record C01 ".bigqueryrc del repositorio" OK "location $LOCATION, GoogleSQL, límite de bytes"
fi

if [ -f "$HOME/.bigqueryrc" ]; then
  record C02 "~/.bigqueryrc personal" AVISO "existe (make lo ignora)" \
    "bq fuera de make lo usaría: exporta BIGQUERYRC=$REPO_ROOT/.bigqueryrc"
else
  record C02 "~/.bigqueryrc personal" OK "no existe"
fi

gac="${GOOGLE_APPLICATION_CREDENTIALS:-}"
if [ -z "$gac" ]; then
  record C03 "Credenciales en el repositorio" OK "GOOGLE_APPLICATION_CREDENTIALS vacío"
else
  case "$gac" in /*) ;; *) gac="$PWD/$gac" ;; esac
  gac_dir=$(dirname "$gac")
  if [ -d "$gac_dir" ]; then gac="$(cd "$gac_dir" && pwd -P)/$(basename "$gac")"; fi
  case "$gac" in
    "$REPO_ROOT"/*)
      record C03 "Credenciales en el repositorio" FALLO "apunta dentro del repositorio" \
        "mueve la clave fuera del repositorio o usa ADC: gcloud auth application-default login" ;;
    *) record C03 "Credenciales en el repositorio" OK "fuera del repositorio" ;;
  esac
fi

# --- Network and authentication (N01, A01 to A04) ----------------------------

if curl -s -o /dev/null -m "$TIMEOUT" https://bigquery.googleapis.com >/dev/null 2>&1; then
  record N01 "Red" OK "Google APIs accesibles"
else
  record N01 "Red" OMITIDO "sin acceso a Google APIs" "revisa la conexión a internet"
fi

if depends_on A01 "Cuenta de gcloud" T01 N01; then
  ACCOUNT=$(run_timeout "$TIMEOUT" gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -1)
  if [ -n "$ACCOUNT" ]; then
    record A01 "Cuenta de gcloud" OK "$ACCOUNT"
  else
    record A01 "Cuenta de gcloud" FALLO "sin cuenta activa" "gcloud auth login"
  fi
fi

TOKEN=""
if depends_on A02 "ADC" T01 N01; then
  TOKEN=$(run_timeout "$TIMEOUT" gcloud auth application-default print-access-token 2>/dev/null)
  if [ -n "$TOKEN" ]; then
    record A02 "ADC" OK "credencial válida"
  else
    record A02 "ADC" FALLO "sin credenciales ADC" "gcloud auth application-default login"
  fi
fi

if depends_on A03 "Proyecto de cuota de ADC" A02; then
  adc_file="${CLOUDSDK_CONFIG:-$HOME/.config/gcloud}/application_default_credentials.json"
  quota=""
  [ -f "$adc_file" ] && quota=$(json_get quota_project_id < "$adc_file")
  if [ -n "$quota" ]; then
    record A03 "Proyecto de cuota de ADC" OK "$quota"
  else
    record A03 "Proyecto de cuota de ADC" AVISO "sin proyecto de cuota" \
      "gcloud auth application-default set-quota-project <PROJECT_ID>"
  fi
fi

if depends_on A04 "Misma cuenta en gcloud y ADC" A01 A02; then
  ADC_EMAIL=$(printf 'access_token=%s' "$TOKEN" |
    curl -s -m "$TIMEOUT" --data @- https://oauth2.googleapis.com/tokeninfo 2>/dev/null | json_get email)
  if [ -z "$ADC_EMAIL" ]; then
    record A04 "Misma cuenta en gcloud y ADC" AVISO "no se pudo leer la cuenta de ADC" \
      "comprueba que usaste la misma cuenta en gcloud auth login y en application-default login"
  elif [ "$ADC_EMAIL" = "$ACCOUNT" ]; then
    record A04 "Misma cuenta en gcloud y ADC" OK "$ADC_EMAIL"
  else
    record A04 "Misma cuenta en gcloud y ADC" AVISO "gcloud $ACCOUNT, ADC $ADC_EMAIL" \
      "gcloud auth application-default login con la cuenta $ACCOUNT"
  fi
fi
TOKEN=""

# --- Project (P01, P02) -----------------------------------------------------

PROJECT=""
if depends_on P01 "Proyecto de GCP" T01; then
  gcloud_project=$(gcloud config get-value project 2>/dev/null | grep -v '^(unset)$' | head -1)
  env_project="${GOOGLE_CLOUD_PROJECT:-}"
  PROJECT="${env_project:-$gcloud_project}"
  if [ -z "$PROJECT" ]; then
    record P01 "Proyecto de GCP" FALLO "sin proyecto configurado" \
      "define GOOGLE_CLOUD_PROJECT en .env o ejecuta gcloud config set project <PROJECT_ID>"
  elif [ -n "$env_project" ] && [ -n "$gcloud_project" ] && [ "$env_project" != "$gcloud_project" ]; then
    record P01 "Proyecto de GCP" AVISO "$PROJECT (.env) y $gcloud_project (gcloud) difieren" \
      "se usa el de .env; alinea con gcloud config set project $PROJECT"
  else
    record P01 "Proyecto de GCP" OK "$PROJECT"
  fi
fi

if depends_on P02 "Facturación" P01 N01; then
  billing=$(run_timeout "$TIMEOUT" gcloud billing projects describe "$PROJECT" --format='value(billingEnabled)' 2>/dev/null)
  case "$billing" in
    True) record P02 "Facturación" OK "activa" ;;
    False) record P02 "Facturación" AVISO "inactiva (modo sandbox)" \
      "gcloud billing projects link $PROJECT --billing-account=<BILLING_ACCOUNT_ID>" ;;
    *) record P02 "Facturación" OMITIDO "no se pudo consultar" \
      "requiere permiso de lectura de facturación y la API cloudbilling.googleapis.com" ;;
  esac
fi

# --- BigQuery (B01 to B04) --------------------------------------------------

REGION="region-$(printf '%s' "$LOCATION" | tr '[:upper:]' '[:lower:]')"
ERR_FILE=$(mktemp)
trap 'rm -f "$ERR_FILE"' EXIT

if depends_on B01 "Dry run en la location" T02 A01 P01; then
  out=$(run_timeout "$TIMEOUT" bq --project_id="$PROJECT" --format=json query --dry_run 'SELECT 1' 2>"$ERR_FILE")
  rc=$?
  if [ $rc -ne 0 ]; then
    # bq may print errors on stdout when --format=json is set.
    printf '%s\n' "$out" >> "$ERR_FILE"
    err=$(tr '\n' ' ' < "$ERR_FILE" | head -c 300)
    if grep -Eqi 'SERVICE_DISABLED|has not been used|is disabled' "$ERR_FILE"; then
      record B01 "Dry run en la location" FALLO "API de BigQuery deshabilitada" \
        "gcloud services enable bigquery.googleapis.com --project=$PROJECT"
    elif grep -Eqi 'Access Denied|PERMISSION_DENIED|bigquery.jobs.create' "$ERR_FILE"; then
      record B01 "Dry run en la location" FALLO "sin permiso para crear jobs" \
        "pide el rol BigQuery Job User (roles/bigquery.jobUser) en $PROJECT"
    else
      record B01 "Dry run en la location" FALLO "error: ${err:-código $rc}" "revisa el mensaje de bq"
    fi
  else
    job_location=$(printf '%s' "$out" | json_get jobReference.location)
    upper_location=$(printf '%s' "$LOCATION" | tr '[:lower:]' '[:upper:]')
    upper_job=$(printf '%s' "$job_location" | tr '[:lower:]' '[:upper:]')
    if [ -z "$job_location" ]; then
      record B01 "Dry run en la location" AVISO "validado; bq no informó la location (declarada $LOCATION)" \
        "sin acción: la location sale de .bigqueryrc"
    elif [ "$upper_job" = "$upper_location" ]; then
      record B01 "Dry run en la location" OK "validado en $job_location"
    else
      record B01 "Dry run en la location" FALLO "validado en $job_location, esperado $LOCATION" \
        "revisa --location en .bigqueryrc"
    fi
  fi
fi

if depends_on B02 "Dialecto del proyecto" B01; then
  # Documented exception (research R2): this probe forces legacy SQL to check that the project rejects it.
  if run_timeout "$TIMEOUT" bq --project_id="$PROJECT" --format=json query --dry_run --use_legacy_sql=true 'SELECT 1' >"$ERR_FILE" 2>&1; then
    record B02 "Dialecto del proyecto" FALLO "el proyecto acepta legacy SQL" \
      "make gcp-dialect (fija only_google_sql en $REGION)"
  else
    record B02 "Dialecto del proyecto" OK "legacy SQL rechazado ($(grep -m1 . "$ERR_FILE" | cut -c1-60))"
  fi
fi

if depends_on B03 "Location de farma_analytics" B01; then
  out=$(run_timeout "$TIMEOUT" bq --project_id="$PROJECT" --format=json show farma_analytics 2>"$ERR_FILE")
  if [ $? -ne 0 ]; then
    printf '%s\n' "$out" >> "$ERR_FILE"
    if grep -qi 'not found' "$ERR_FILE"; then
      record B03 "Location de farma_analytics" OMITIDO "el dataset aún no existe" "sin acción"
    else
      record B03 "Location de farma_analytics" OMITIDO "no se pudo leer el dataset" "revisa el mensaje de bq show"
    fi
  else
    ds_location=$(printf '%s' "$out" | json_get location)
    if [ "$(printf '%s' "$ds_location" | tr '[:lower:]' '[:upper:]')" = "$(printf '%s' "$LOCATION" | tr '[:lower:]' '[:upper:]')" ]; then
      record B03 "Location de farma_analytics" OK "$ds_location"
    else
      record B03 "Location de farma_analytics" FALLO "$ds_location, esperado $LOCATION" \
        "la location de un dataset no se puede cambiar: recrea farma_analytics en $LOCATION"
    fi
  fi
fi

if depends_on B04 "Límite de bytes" C01; then
  record B04 "Límite de bytes" OK "$(awk -v b="$MAX_BYTES" 'BEGIN { printf "%.2f GiB por consulta", b / 1073741824 }')"
fi

# --- Report -----------------------------------------------------------------

echo "Diagnóstico de farma-analytics-bigquery"
echo
for id in $CATALOG; do
  eval "printf '%s\n' \"\${OUT_$id}\""
done
echo
echo "Resumen: $N_OK OK, $N_AVISO AVISO, $N_FALLO FALLO, $N_OMITIDO OMITIDO"

[ "$N_FALLO" -eq 0 ]
