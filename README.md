<div align="center">

# Telegram Stars API & Telegram Premium API

**Your shop. One API. Stars & Premium.**

[![PyPI version](https://img.shields.io/pypi/v/fragment-api-dev?color=0ea5e9&label=Python%20SDK)](https://pypi.org/project/fragment-api-dev/)
[![MIT license](https://img.shields.io/badge/license-MIT-0ea5e9)](LICENSE)

Fragment API connects your shop, Telegram bot, or backend to Stars and Premium purchases through a Python SDK or REST API.

**No API key. 0% API access fee. Pay with GRAM or USDT on TON.**

The 0% fee applies to API access only. Purchase costs and TON network fees still apply. USDT purchases also need a small GRAM balance for network fees.

[Documentation](https://stars-market.duckdns.org/api) | [Shop](https://stars-market.duckdns.org/) | [Health](https://api-stars.duckdns.org/health) | [Examples](examples/README.md)

</div>

| Product | Supported orders |
|---|---|
| Telegram Stars | 50 to 1,000,000 Stars |
| Telegram Premium | 3, 6, or 12 months |

API endpoint: `https://api-stars.duckdns.org`

## Quick start

Python 3.10+. Install the SDK:

```bash
pip install fragment-api-dev==1.3.0
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

- [Python SDK 1.3.0](https://pypi.org/project/fragment-api-dev/1.3.0/) and [Stars/Premium examples](examples/README.md#python-sdk).
- [REST examples: curl and Node.js](examples/README.md#rest-api) and [OpenAPI specification](openapi.yaml).
- [Wallet selection](examples/README.md#choose-your-wallet): 24-word wallets, 12-word wallets, and account resolution.
- [Prices](examples/README.md#prices): GRAM/USDT quotes without creating a purchase; final prices are not reserved.
- [AI integration skill](skills/fragment-api-integration/SKILL.md) with [Codex/Claude setup](examples/README.md#ai-assisted-integration).

## Support

[Open an issue](https://github.com/slightbasebo/fragment-api-dev/issues) or contact [@tondotdev](https://t.me/tondotdev). Report security concerns privately through [SECURITY.md](SECURITY.md); never post wallet credentials. Code and examples: [MIT license](LICENSE).

**LIKE IT? STAR IT!** Help other Telegram bot and shop developers find the API.
