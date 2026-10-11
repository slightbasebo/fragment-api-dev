# Telegram Stars API for Python

Use the Fragment Python SDK to check a recipient, buy Telegram Stars, and recover orders without duplicate payments.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/telegram-stars-api-python) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## What the Python SDK provides

fragment-api-dev is the Python client for Fragment API. It supports Stars, Premium, live GRAM/USDT prices, recipient checks, wallet selection, and purchase status polling.

Stars quantities are whole numbers from 50 to 1,000,000. The recipient is a Telegram username beginning with @.

```bash
pip install "fragment-api-dev[async]==1.4.0"
```


## Get a price asynchronously

This example is safe to run before configuring a wallet. Monetary values remain decimal strings. stale=true means the most recent available quote was returned.

```python
import asyncio
from fragment_api import AsyncFragmentAPI

async def main():
    async with AsyncFragmentAPI() as api:
        quote = await api.get_stars_price(100)
        print(quote.prices.gram, quote.prices.usdt, quote.stale)

asyncio.run(main())
```


## Add the purchase step to your shop

Run check_stars_availability(username, amount, payment_method) before charging your customer. After confirmed payment, call buy_stars with the same product selection and a key derived from your order ID.

Persist the purchase ID before calling wait. Treat failed and reconciliation_required as results that need handling; neither is a successful delivery.

- [Minimal purchase step](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/shop_minimal.py)
- [Generate your exact Python request](https://stars-market.duckdns.org/api#quick-start)

## Retry without buying twice

A network timeout does not prove that the server rejected a purchase. Query get_purchase with the stored ID, or repeat creation using the original key and identical fields.

Keep retries bounded, respect retry_after when supplied, and stop automatic replacement on reconciliation_required. Test these branches with the local mock before spending funds.

- [Run failure scenarios](https://stars-market.duckdns.org/docs/testing)

