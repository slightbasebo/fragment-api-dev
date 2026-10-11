# Connect to Fragment API

Make your first free API request, choose a wallet flow, and add Telegram Stars or Premium to your backend.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/quick-start) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Start with a price request

Fragment API lets a backend buy Telegram Stars and gift Premium through one public HTTPS interface. No API key or signup is required. API access has a 0% fee; purchase costs and TON network fees still apply.

This request reads a price. It needs no wallet and spends nothing.

```bash
curl --max-time 30 --fail-with-body 'https://api-stars.duckdns.org/api/v1/prices/quote?product=stars&amount=50'
```


## Choose your integration

Use the integration builder to select Python SDK, aiogram, Node.js, or REST. Choose Stars or Premium, GRAM or USDT, and the wallet format you use. Download the generated example and environment template.

For a Python bot, use AsyncFragmentAPI so network requests and status waits do not block other handlers. A sync FragmentAPI client is also available.

- [Open integration builder](https://stars-market.duckdns.org/api#quick-start)
- [Python and aiogram starter](https://github.com/slightbasebo/fragment-api-dev/tree/main/examples/starters/aiogram)

## Check, charge, create, track

Check availability shortly before accepting customer payment. If available is false, show the message and action and do not charge. A successful check is not a reservation.

After your shop confirms payment, create the API purchase using the stable shop order ID as idempotency_key. Save purchase_id in your order database before polling. Only completed confirms delivery.

After a timeout, resume the saved purchase. If no ID arrived, retry the identical create request with the same key. Never create an automatic replacement for reconciliation_required.

- [Purchase lifecycle and recovery](https://stars-market.duckdns.org/docs/orders-and-errors)

## Choose where signing happens

The wallet-backed purchase endpoint accepts a spend-capable seed from your trusted backend. Keep it in runtime secret storage.

The client-signed checkout endpoint returns a TonConnect transaction for your wallet to approve. It never accepts your seed. Check the amount and expiry, send the returned transaction unchanged, and submit the signed BOC.

- [Client-signed checkouts](https://stars-market.duckdns.org/docs/client-signed-checkout)

