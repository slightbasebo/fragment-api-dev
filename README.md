<div align="center">

# Telegram Stars API & Telegram Premium API

**Build your Telegram Stars bot or shop with Fragment API.**

[![PyPI version](https://img.shields.io/pypi/v/fragment-api-dev?color=0ea5e9&label=Python%20SDK)](https://pypi.org/project/fragment-api-dev/)
[![MIT license](https://img.shields.io/badge/license-MIT-0ea5e9)](LICENSE)

Free Telegram Stars API and Telegram Premium API for bots, Stars shops, reseller services, and backends. Python SDK or REST: check a recipient, create an order, track delivery.

**No API key. 0% API access fee. Pay with GRAM or USDT on TON.**

The 0% fee applies to API access only. Purchase costs and TON network fees still apply. USDT purchases also need a small GRAM balance for network fees.

[Start integrating](https://stars-market.duckdns.org/api#quick-start) | [Examples](examples/README.md) | [Python SDK](https://pypi.org/project/fragment-api-dev/) | [Integration help](https://t.me/tondotdev)

</div>

| Product | Supported orders |
|---|---|
| Telegram Stars | 50 to 1,000,000 Stars |
| Telegram Premium | 3, 6, or 12 months |

API endpoint: `https://api-stars.duckdns.org`

## Try the API

Fetch a real price before connecting a wallet. No signup, API key, or purchase:

```bash
curl --max-time 30 --fail-with-body 'https://api-stars.duckdns.org/api/v1/prices/quote?product=stars&amount=50'
```

The response includes exact decimal strings in `prices.gram` and `prices.usdt`. Or run the [live API demo](https://stars-market.duckdns.org/api).

## Choose your integration

- [Integration builder](https://stars-market.duckdns.org/api#quick-start): choose language, product, payment, and wallet; download matching setup files.
- [aiogram starter](examples/starters/aiogram): async bot integration with persistent order recovery.
- [Node.js starter](examples/starters/node): durable orders and safe retries.
- [Client-signed checkout](docs/client-signed-checkout.md): approve transactions in your own wallet without sending a seed.
- [Local mock](examples/mock_server.py): test success, failure, rate limiting, and uncertain results without funds.

## Quick start

Python 3.10+. Install the SDK:

```bash
pip install fragment-api-dev==1.4.0
```

This example buys **50 Stars with GRAM**. Set `TELEGRAM_USERNAME`, `TON_WALLET_SEED`, and a stable `SHOP_ORDER_ID` using the [setup guide](examples/README.md#setup). For 12-word seeds, see [wallet selection](examples/README.md#choose-your-wallet).

**Purchase requests send your wallet credential to the API and spend funds. Run only on a trusted backend. Never expose seeds or private keys in frontend code, logs, Git, or public issues.**

```python
import os
from fragment_api import FragmentAPI

api = FragmentAPI()
username = os.environ["TELEGRAM_USERNAME"]
check = api.check_stars_availability(username, 50, "gram")
if not check.available:
    raise SystemExit(f"{check.message} {check.action or ''}")

purchase = api.buy_stars(
    username=username, amount=50, payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
    idempotency_key=os.environ["SHOP_ORDER_ID"],
)
print("Record purchase_id with your shop order:", purchase.purchase_id, flush=True)
result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
```

This demo does not collect customer payment or save orders. In your shop, [check availability before charging](examples/README.md#check-before-charging), then persist `purchase_id` before polling. Availability needs no wallet credentials; it is not a reservation or delivery guarantee. On `429`, wait for `retry_after`; on `503`, retry later without charging.

Only `completed` means success. After a timeout, query the saved purchase or retry the original request with the same `idempotency_key`. **Never automatically replace an order in `reconciliation_required`.** See [result handling](examples/README.md#results-and-retries).

## Examples & integration

- [Focused documentation](docs/README.md): Python, Premium, USDT, aiogram, wallets, and errors.
- [Service checks](https://stars-market.duckdns.org/status) and [changelog](docs/changelog.md).
- [Minimal shop backend](examples/shop_minimal.py): create a purchase for a confirmed shop order, using its stable ID.
- [Test prices without wallet credentials](examples/prices.py).
- [Python SDK 1.4.0](https://pypi.org/project/fragment-api-dev/1.4.0/) and [Stars/Premium examples](examples/README.md#python-sdk).
- [REST examples: curl and Node.js](examples/README.md#rest-api) and [OpenAPI specification](openapi.yaml).
- [Wallet selection](examples/README.md#choose-your-wallet): 24-word wallets, 12-word wallets, and account resolution.
- [Prices](examples/README.md#prices): GRAM/USDT quotes without creating a purchase; final prices are not reserved.
- [AI integration skill](skills/fragment-api-integration/SKILL.md) with [Codex/Claude setup](examples/README.md#ai-assisted-integration).

## Support

Building a Telegram bot, Stars shop, or reseller backend? [Contact @tondotdev for integration help](https://t.me/tondotdev) or [open an issue](https://github.com/slightbasebo/fragment-api-dev/issues). Mention your language and intended product. Never post wallet credentials; report security concerns privately through [SECURITY.md](SECURITY.md). Code and examples: [MIT license](LICENSE).

**LIKE IT? STAR IT!** Help other Telegram bot and shop developers find the API.
