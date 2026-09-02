---
name: fragment-api-integration
description: Integrate Telegram Stars or Telegram Premium purchases through Fragment API using the Python SDK or direct REST, including pre-payment availability checks, GRAM/USDT payments, and wallet selection.
---

# Fragment API Integration

Integrate the API into the user's existing backend with the smallest change that fits its language and framework.

## Choose The Client

- For Python, read [Python SDK](references/python-sdk.md) and use `fragment-api-dev`.
- For other backend languages, read [REST API](references/rest-api.md).
- Keep the user's current framework, storage, queue, and HTTP client unless a change is necessary for the integration.
- The production base URL is `https://api-stars.duckdns.org` and no API key is required.

## Gather Inputs

Confirm these values from existing project configuration or ask for non-secret choices only:

- Product: Stars or Premium.
- Stars amount `50..1,000,000`, or Premium duration `3`, `6`, or `12` months.
- Payment method: `gram` or `usdt`.
- Telegram username including `@`.
- Wallet format:
  - A 24-word TON mnemonic or Base64 32-byte private key uses `seed` only.
  - A 12-word seed also requires `wallet_address` or `account_index`.

Do not ask the user to paste a seed into chat. Read it at runtime from a backend environment variable or the project's existing secret manager. Never place it in frontend code, logs, errors, tests, fixtures, commits, or example values.

USDT purchases still require a small GRAM balance for TON network fees.

## Implement The Order Flow

1. Validate product, amount, payment method, username, and wallet selector before creating an order.
2. Call the availability checker shortly before accepting customer payment. It uses only product, username, amount, and payment method; never send wallet credentials to it.
3. Continue only when `available` is `true`. On `available: false`, show `message` and `action` and do not accept payment.
4. On `429`, wait for `retry_after`. On `503`, retry later and do not accept payment yet.
5. Accept customer payment, then derive a stable `idempotency_key` from the client's logical order ID. Reuse it for every retry of that same order.
6. Create the purchase once and persist `purchase_id` before waiting or polling.
7. Wait until `completed`, `failed`, or `reconciliation_required`; treat only `completed` as success.
8. Preserve public `code`, `error`, `action`, and `retry_after` fields without returning request bodies, stack traces, or credentials.

The availability result is a point-in-time check, not a reservation or guarantee. Keep the existing final purchase-failure handling.

Never create a replacement order automatically after an ambiguous response. Query the saved `purchase_id` or retry the original request with the same `idempotency_key`. Never repeat an order in `reconciliation_required` automatically.

## Wallet Selection

For a 12-word seed with a known address but unknown index, call the wallet resolver once and store the returned `account_index`. Reuse that index for later purchases from the same wallet.

If both address and index are supplied, pass both so the API verifies the exact wallet selection.

## Prices And Testing

Use the public prices endpoints or SDK price helpers for display and estimates. Quotes are informational and do not reserve the final Fragment price.

Add unit tests around payload construction, idempotency reuse, status mapping, and public error handling. Mock paid purchase calls. Do not execute a paid test or deploy to production without explicit authorization.

For maintained runnable examples, see [`examples/`](../../examples/README.md) and [`openapi.yaml`](../../openapi.yaml).
