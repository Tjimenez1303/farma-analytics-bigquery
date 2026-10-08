#!/bin/bash
# Sets the project-level daily BigQuery query quota (QueryUsagePerDay). Idempotent.
# Compatible with bash 3.2 (macOS default).

set -uo pipefail

PREFERENCE_ID="farma-query-usage-per-day"

fail() {
  echo "$1" >&2
  exit 1
}

[ -n "${PROJECT_ID:-}" ] ||
  fail "Falta PROJECT_ID: define GOOGLE_CLOUD_PROJECT en .env o ejecuta gcloud config set project <PROJECT_ID>."
case "${QUERY_QUOTA_GIB_PER_DAY:-}" in
  '' | *[!0-9]* | 0*) fail "QUERY_QUOTA_GIB_PER_DAY debe ser un entero mayor que 0 en .env (valor actual: '${QUERY_QUOTA_GIB_PER_DAY:-}')." ;;
esac

ERR_FILE=$(mktemp)
trap 'rm -f "$ERR_FILE"' EXIT

explain_error() {
  if grep -q "Invalid choice: 'quotas'" "$ERR_FILE"; then
    echo "Tu gcloud no tiene el grupo 'quotas': actualízalo con gcloud components update." >&2
  elif grep -Eqi 'PERMISSION_DENIED|403|does not have' "$ERR_FILE"; then
    echo "Sin permiso: necesitas el rol Quota Administrator (roles/servicemanagement.quotaAdmin) y la API cloudquotas.googleapis.com habilitada." >&2
  fi
  cat "$ERR_FILE" >&2
}

info=$(gcloud quotas info describe QueryUsagePerDay --service=bigquery.googleapis.com \
  --project="$PROJECT_ID" --format=json 2>"$ERR_FILE") || {
  explain_error
  exit 1
}
unit=$(printf '%s\n' "$info" | sed -n 's/.*"metricUnit": *"\([^"]*\)".*/\1/p' | head -1)
case "$unit" in
  MiBy*) ;;
  *) fail "Unidad inesperada de QueryUsagePerDay: '$unit' (se esperaba MiBy...). No se aplica la cuota." ;;
esac

mib=$((QUERY_QUOTA_GIB_PER_DAY * 1024))
gcloud quotas preferences update "$PREFERENCE_ID" \
  --service=bigquery.googleapis.com \
  --quota-id=QueryUsagePerDay \
  --preferred-value="$mib" \
  --project="$PROJECT_ID" \
  --allow-missing \
  --allow-high-percentage-quota-decrease 2>"$ERR_FILE" || {
  explain_error
  exit 1
}
echo "Cuota diaria de consultas: ${QUERY_QUOTA_GIB_PER_DAY} GiB ($mib MiB) en $PROJECT_ID."
