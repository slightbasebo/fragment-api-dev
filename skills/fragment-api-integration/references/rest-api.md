# REST API

Use this reference for non-Python backends or when the project already has a preferred HTTP client.

## Base URL

```text
https://api-stars.duckdns.org
```

No API key or authentication header is required.

## Public Endpoints

```text
POST /api/v1/purchases
GET  /api/v1/purchases/{purchase_id}
POST /api/v1/wallets/resolve
GET  /api/v1/prices
GET  /api/v1/prices/quote?product=stars&amount=100
GET  /health
```

## Create A Purchase

```json
{
  "product": "stars",
  "username": "@telegram_user",
  "amount": 50,
  "payment_method": "gram",
  "seed": "READ_FROM_BACKEND_SECRET_STORAGE",
  "idempotency_key": "shop-order-1001"
}
```

For Premium, set `product` to `premium` and use `amount` for the duration: `3`, `6`, or `12`.

For USDT on TON, set `payment_method` to `usdt`. The wallet still needs a small GRAM balance for network fees.

Never send the seed from browser code. Construct this request only in the trusted backend.

## Wallet Selectors

A 24-word TON mnemonic or Base64 32-byte private key needs no additional field.

A 12-word seed requires one of:

```json
{"wallet_address": "UQ_YOUR_WALLET_ADDRESS"}
```

```json
{"account_index": 0}
```

Both may be sent together to verify the exact wallet selection.

If only the address is known, resolve it once:

```http
POST /api/v1/wallets/resolve
Content-Type: application/json

{
  "seed": "READ_FROM_BACKEND_SECRET_STORAGE",
  "wallet_address": "UQ_YOUR_WALLET_ADDRESS"
}
```

Store the returned `account_index` for later orders from that wallet.

## Poll The Result

Persist `purchase_id` from the create response, then call:

```text
GET /api/v1/purchases/{purchase_id}
```

Stop at:

- `completed`
- `failed`
- `reconciliation_required`

Only `completed` is success. Do not automatically create a new order for `reconciliation_required` or after a timeout. Query the saved purchase or retry the same create request with the same `idempotency_key`.

## Errors

Preserve public `code`, `error`, and `action` fields for client-facing diagnostics. Do not expose the request body, seed, stack trace, or transport internals.

Handle at least:

- `400`: correct the request.
- `409`: inspect the existing logical order or idempotency conflict.
- `429`: back off before retrying.
- `503`: temporary service unavailability; do not create an unrelated replacement order.

## Maintained References

- [curl example](../../../examples/curl.sh)
- [Node.js example](../../../examples/node.mjs)
- [OpenAPI 3.1](../../../openapi.yaml)
