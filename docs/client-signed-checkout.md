# Client-signed Fragment checkout API

Create Stars or Premium invoices and approve payments in your own wallet without sending a seed to the API.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/client-signed-checkout) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Create a transaction for your payer

POST /api/v1/checkouts with product, username, amount, payment_method, payer_address, and idempotency_key. No seed or API key is required.

The response includes checkout_id, status, and tonconnect_transaction when a payable transaction is available. Reuse the same key for the same logical checkout.

```http
POST /api/v1/checkouts
Content-Type: application/json

{
  "product": "stars",
  "username": "@telegram_user",
  "amount": 50,
  "payment_method": "gram",
  "payer_address": "<YOUR_TON_WALLET_ADDRESS>",
  "idempotency_key": "shop:order-1001"
}
```


## Review and sign locally

Only offer payment while status is awaiting_payment and the returned validUntil has not elapsed. Review the recipient, amount, destination, and payload in your signing application.

Send the returned transaction unchanged to your connected wallet. GRAM amounts in TonConnect messages are integer nanotons; they are not display prices. For USDT, preserve the returned jetton payload.


## Submit the result and track delivery

POST /api/v1/checkouts/{checkout_id}/submitted with the signed boc returned by the wallet. A wallet callback does not prove delivery.

GET /api/v1/checkouts/{checkout_id} to follow the result. Only completed means delivered. Keep the checkout ID and do not sign or pay again after an ambiguous response.

```http
POST /api/v1/checkouts/<CHECKOUT_ID>/submitted
Content-Type: application/json

{"boc": "<SIGNED_BOC_FROM_WALLET>"}
```


## Expired or uncertain checkouts

An expired invoice must not be paid. First check whether a previous payment exists before creating a genuinely new checkout.

reconciliation_required means the result needs inspection. Do not create an automatic replacement. Rate limits and temporary errors do not change this rule.

- [Full public contract](https://github.com/slightbasebo/fragment-api-dev/blob/main/openapi.yaml)
- [Recovery guide](https://stars-market.duckdns.org/docs/orders-and-errors)

