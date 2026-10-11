#!/usr/bin/env bash
set -euo pipefail

api_url="${FRAGMENT_API_URL:-https://api-stars.duckdns.org}"
product="${PRODUCT:-stars}"
amount="${AMOUNT:-50}"
payment_method="${PAYMENT_METHOD:-gram}"
username="${TELEGRAM_USERNAME:-@telegram_user}"

availability_payload="$(PRODUCT="${product}" AMOUNT="${amount}" PAYMENT_METHOD="${payment_method}" TELEGRAM_USERNAME="${username}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "product": os.environ["PRODUCT"],
    "username": os.environ["TELEGRAM_USERNAME"],
    "amount": int(os.environ["AMOUNT"]),
    "payment_method": os.environ["PAYMENT_METHOD"],
}))
PY
)"

availability="$(curl --max-time 30 --fail-with-body --silent --show-error \
  "${api_url}/api/v1/availability/check" \
  --request POST \
  --header 'Content-Type: application/json' \
  --data "${availability_payload}")"

if [[ "$(python3 -c 'import json,sys; print(str(json.load(sys.stdin)["available"]).lower())' <<<"${availability}")" != "true" ]]; then
  python3 -m json.tool <<<"${availability}"
  exit 2
fi

: "${TON_WALLET_SEED:?Set TON_WALLET_SEED}"
order_key="${IDEMPOTENCY_KEY:-${SHOP_ORDER_ID:?Set SHOP_ORDER_ID to a stable shop order ID}}"

payload="$({
  PRODUCT="${product}" \
  AMOUNT="${amount}" \
  PAYMENT_METHOD="${payment_method}" \
  TELEGRAM_USERNAME="${username}" \
  IDEMPOTENCY_KEY="${order_key}" \
  python3 - <<'PY'
import json
import os

body = {
    "product": os.environ["PRODUCT"],
    "username": os.environ["TELEGRAM_USERNAME"],
    "amount": int(os.environ["AMOUNT"]),
    "payment_method": os.environ["PAYMENT_METHOD"],
    "seed": os.environ["TON_WALLET_SEED"],
    "idempotency_key": os.environ["IDEMPOTENCY_KEY"],
}

if os.environ.get("TON_WALLET_ADDRESS"):
    body["wallet_address"] = os.environ["TON_WALLET_ADDRESS"]
if os.environ.get("TON_ACCOUNT_INDEX"):
    body["account_index"] = int(os.environ["TON_ACCOUNT_INDEX"])

print(json.dumps(body))
PY
} )"

purchase="$({
  curl --max-time 30 --fail-with-body --silent --show-error \
    "${api_url}/api/v1/purchases" \
    --request POST \
    --header 'Content-Type: application/json' \
    --data-binary @- <<<"${payload}"
} )"

purchase_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["purchase_id"])' <<<"${purchase}")"
echo "Purchase: ${purchase_id}"

deadline=$((SECONDS + 300))
while true; do
  if (( SECONDS >= deadline )); then
    echo "Status check timed out. Resume purchase ${purchase_id}; do not create a new order." >&2
    exit 3
  fi
  result="$(curl --max-time 30 --fail-with-body --silent --show-error "${api_url}/api/v1/purchases/${purchase_id}")"
  status="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"${result}")"

  if [[ "${status}" == "completed" || "${status}" == "failed" || "${status}" == "reconciliation_required" ]]; then
    python3 -m json.tool <<<"${result}"
    break
  fi

  sleep 2
done
