# Purchase status, idempotency, and recovery

Handle accepted orders, terminal results, timeouts, rate limits, and uncertain payments without duplicate purchases.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/orders-and-errors) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Only completed means delivered

queued, preparing, sending, submitted, and confirming are intermediate purchase states. HTTP 202 only acknowledges creation.

completed means delivery succeeded. failed means the purchase failed. reconciliation_required means the outcome is uncertain: stop automatic replacement and inspect the original order.


## Keep one key per logical order

Generate idempotency_key from your shop order ID before calling the API. Persist the selection with that key. Retry identical requests with that same key.

If the request times out before you receive an ID, you can repeat creation with the original key. If you have an ID, poll it. A fresh key can create a second purchase.


## Act on the actual error

400: fix the invalid input before another request. 409: inspect the existing key and selection; do not bypass it with a new key. 429: respect Retry-After or retry_after when supplied.

503 or a connection failure does not prove that a purchase was rejected. For purchase creation, recover the original request. For an availability check, wait before accepting customer payment.


## What information helps support?

Send the purchase or checkout ID, approximate time, product, payment method, HTTP status, and public error code through the support contact. Do not include request bodies, seeds, private keys, or signed BOCs in issues.

A live price response and a successful health check measure different capabilities from completed delivery.

- [Integration support](https://t.me/tondotdev)
- [Public service checks](https://stars-market.duckdns.org/status)

