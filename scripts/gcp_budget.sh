#!/bin/bash
# Creates or updates the monthly budget alert for the project. Idempotent.
# Compatible with bash 3.2 (macOS default).

set -uo pipefail

BUDGET_NAME="farma-analytics-bigquery"

fail() {
  echo "$1" >&2
  exit 1
}

[ -n "${PROJECT_ID:-}" ] ||
  fail "Falta PROJECT_ID: define GOOGLE_CLOUD_PROJECT en .env o ejecuta gcloud config set project <PROJECT_ID>."
[ -n "${BILLING_ACCOUNT_ID:-}" ] || fail "Falta BILLING_ACCOUNT_ID en .env."
[ -n "${BUDGET_AMOUNT:-}" ] || fail "Falta BUDGET_AMOUNT en .env (por ejemplo 10USD)."

ERR_FILE=$(mktemp)
trap 'rm -f "$ERR_FILE"' EXIT

explain_error() {
  if grep -Eqi 'PERMISSION_DENIED|403|does not have' "$ERR_FILE"; then
    echo "Sin permiso: necesitas el rol Billing Account Administrator o Billing Account Costs Manager y la API billingbudgets.googleapis.com habilitada." >&2
  fi
  cat "$ERR_FILE" >&2
}

names=$(gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID" \
  --filter="displayName=$BUDGET_NAME" --format='value(name)' \
  --billing-project="$PROJECT_ID" 2>"$ERR_FILE") || {
  explain_error
  exit 1
}
count=$(printf '%s\n' "$names" | grep -c . || true)

if [ "$count" -eq 0 ]; then
  gcloud billing budgets create \
    --billing-account="$BILLING_ACCOUNT_ID" \
    --display-name="$BUDGET_NAME" \
    --budget-amount="$BUDGET_AMOUNT" \
    --calendar-period=month \
    --filter-projects="projects/$PROJECT_ID" \
    --threshold-rule=percent=0.5 \
    --threshold-rule=percent=0.9 \
    --threshold-rule=percent=1.0 \
    --billing-project="$PROJECT_ID" \
    --format=none 2>"$ERR_FILE" || {
    explain_error
    exit 1
  }
  echo "Presupuesto '$BUDGET_NAME' creado: $BUDGET_AMOUNT al mes, avisos al 50 %, 90 % y 100 %."
elif [ "$count" -eq 1 ]; then
  # update does not accept --threshold-rule: rules are cleared and added again.
  gcloud billing budgets update "$names" \
    --billing-account="$BILLING_ACCOUNT_ID" \
    --budget-amount="$BUDGET_AMOUNT" \
    --calendar-period=month \
    --filter-projects="projects/$PROJECT_ID" \
    --clear-threshold-rules \
    --add-threshold-rule=percent=0.5 \
    --add-threshold-rule=percent=0.9 \
    --add-threshold-rule=percent=1.0 \
    --billing-project="$PROJECT_ID" \
    --format=none 2>"$ERR_FILE" || {
    explain_error
    exit 1
  }
  echo "Presupuesto '$BUDGET_NAME' actualizado: $BUDGET_AMOUNT al mes, avisos al 50 %, 90 % y 100 %."
else
  echo "Hay $count presupuestos llamados '$BUDGET_NAME'. Deja solo uno y vuelve a ejecutar:" >&2
  printf '%s\n' "$names" >&2
  exit 1
fi
