<div align="center">

# Telegram Stars API & Telegram Premium API

### Free Fragment API for buying Telegram Stars and Premium with GRAM or USDT on TON.

[![PyPI](https://img.shields.io/pypi/v/fragment-api-dev?style=for-the-badge&logo=pypi&logoColor=white&color=0ea5e9)](https://pypi.org/project/fragment-api-dev/)
[![Python](https://img.shields.io/pypi/pyversions/fragment-api-dev?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/fragment-api-dev/)
[![API](https://img.shields.io/badge/API-ONLINE-22c55e?style=for-the-badge)](https://api-stars.duckdns.org/health)
[![License](https://img.shields.io/badge/LICENSE-MIT-0ea5e9?style=for-the-badge)](LICENSE)

**Free · No API key · Python SDK + REST API · GRAM + USDT on TON**

**[Quick start](#quick-start)** · **[Examples](examples/README.md)** · **[AI skill](#ai-assisted-integration)** · **[Prices](#prices)** · **[OpenAPI](openapi.yaml)**

</div>

---

Fragment API gives shops, Telegram bots, and backend services a simple way to buy Telegram Stars or Telegram Premium for any supported Telegram username. Use the Python SDK or call the REST API directly.

| Product | Supported values | Payment |
|---|---|---|
| Telegram Stars | 50 to 1,000,000 Stars | GRAM or USDT on TON |
| Telegram Premium | 3, 6, or 12 months | GRAM or USDT on TON |

API access is free. You pay only the Fragment purchase amount and TON network fees.

## Quick start

```bash
pip install fragment-api-dev==1.2.1
```

```python
import os
from fragment_api import FragmentAPI

api = FragmentAPI()

purchase = api.buy_stars(
    username="@telegram_user",
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
)

result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
```

This minimal example uses a 24-word TON mnemonic or a Base64 32-byte private key. Credentials are sent only by your backend; never place a seed in frontend code.

## Choose your wallet setup

| Wallet data | What to send |
|---|---|
| 24-word TON mnemonic or Base64 32-byte private key | `seed` |
| 12-word seed and wallet address | `seed` + `wallet_address` |
| 12-word seed and known account index | `seed` + `account_index` |

A 12-word seed alone is not enough. If you know the address but not its index, use the [wallet resolver example](examples/resolve_wallet.py).

## Ready-to-run examples

The [`examples/`](examples/README.md) directory contains explained examples for:

- Stars with GRAM
- Stars with USDT on TON
- Premium with GRAM
- Premium with USDT on TON
- 24-word wallets without a selector
- 12-word wallets with an address or account index
- Python SDK, Node.js, and curl

USDT purchases require a small GRAM balance for TON network fees.

## AI-assisted integration

Install the same portable skill for Codex or Claude:

```bash
# Codex
cp -R skills/fragment-api-integration "${CODEX_HOME:-$HOME/.codex}/skills/"

# Claude
cp -R skills/fragment-api-integration "$HOME/.claude/skills/"
```

Then ask your coding agent:

```text
Use $fragment-api-integration to add Telegram Stars purchases to this project.
```

The skill covers Python SDK and REST integrations, Stars and Premium, GRAM and USDT, wallet selection, idempotency, polling, and safe error handling.

## Prices

Get an informational quote without creating a purchase:

```python
quote = api.get_stars_price(100)
print(quote.prices.gram, quote.prices.usdt)
```

```bash
curl 'https://api-stars.duckdns.org/api/v1/prices/quote?product=stars&amount=100'
```

Price values are exact decimal strings. Fragment creates a fresh quote when the purchase starts.

## Important

- Use one `idempotency_key` for each logical order.
- Retry the same order with the same key.
- Wait for the final status; creating a purchase does not mean it is complete.
- Never automatically replace an order in `reconciliation_required`.

## Resources

| Resource | Link |
|---|---|
| All examples | [`examples/README.md`](examples/README.md) |
| AI integration skill | [`skills/fragment-api-integration`](skills/fragment-api-integration/SKILL.md) |
| Python SDK | [`fragment-api-dev`](https://pypi.org/project/fragment-api-dev/) |
| REST API specification | [`openapi.yaml`](openapi.yaml) |
| Production endpoint | [`https://api-stars.duckdns.org`](https://api-stars.duckdns.org/health) |

## Support

[Open an issue](https://github.com/slightbasebo/fragment-api-dev/issues) or contact [@tondotdev](https://t.me/tondotdev).

Never post wallet credentials in an issue. Report security concerns through [`SECURITY.md`](SECURITY.md).

---

<div align="center">

**LIKE IT? STAR IT!**

</div>
