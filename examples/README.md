# Fragment API Examples

Integrate Telegram Stars and Telegram Premium purchases with Python, curl, or Node.js. No API key. API base URL: `https://api-stars.duckdns.org`.

[Quick start](../README.md#quick-start) | [Documentation](https://stars-market.duckdns.org/api) | [OpenAPI](../openapi.yaml) | [AI skill](#ai-assisted-integration)

## Complete starters

- [aiogram 3](starters/aiogram): async calls, persistent orders, mock-first setup.
- [Node.js](starters/node): persistent orders and restart recovery.
- [Mock API](mock_server.py): local synthetic success, failure, timeout, rate-limit, and reconciliation scenarios.

Use these starters when your integration needs durable recovery. The focused scripts below demonstrate individual calls.

## Setup

From the repository root, try prices first with Python 3.10+, without any wallet credentials:

```bash
python -m pip install fragment-api-dev==1.4.0
python examples/prices.py
```

Run file-based examples from the repository root. Python examples need Python 3.10+:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install fragment-api-dev==1.4.0
export TELEGRAM_USERNAME="@your_recipient"
export SHOP_ORDER_ID="your-shop:order-1001"
export PRODUCT=stars AMOUNT=50 PAYMENT_METHOD=gram
```

Replace the recipient and order ID with values from your shop. Keep the same ID and purchase fields for retries; use a different ID only for a different logical order. Keys must contain 1-128 printable ASCII characters. Namespace IDs by shop to avoid collisions.

**Purchase and wallet-resolution requests send your wallet credential to the API. Run them only on a trusted backend. Load `TON_WALLET_SEED` from backend environment variables or secret storage. Never put seeds or private keys in frontend code, logs, shell history, Git, issues, or AI chats. Purchase examples spend real funds.**

For a manual Bash session, enter the seed without echoing it or recording it in shell history:

```bash
read -rsp 'Wallet seed: ' TON_WALLET_SEED
export TON_WALLET_SEED
printf '\n'
```

Supported settings:

| Setting | Values |
|---|---|
| `PRODUCT=stars` | `AMOUNT=50` to `1000000` |
| `PRODUCT=premium` | `AMOUNT=3`, `6`, or `12` months |
| `PAYMENT_METHOD` | `gram` or `usdt` on TON |

0% API access fee does not mean free purchases: purchase costs and TON network fees still apply. USDT purchases also need a small GRAM balance for network fees.

## Check before charging

1. Check availability shortly before accepting customer payment, using the intended product, recipient, amount, and payment method.
2. Continue only when `available` is `true`. Otherwise, show `message` and `action` without charging.
3. On `429`, wait for `retry_after`; on `503` or a connection error, retry later without charging.
4. Confirm customer payment in your own shop, then create the purchase using that shop order's stable key.
5. Persist `purchase_id` with the shop order before polling. Only `completed` means success.

The check needs no seed, wallet address, or API key. It does not create a purchase or reserve a price. Availability can change afterward; handle final purchase failures too.

Run this standalone check with the setup variables above:

```python
import os
from fragment_api import FragmentAPI, FragmentAPIError, RateLimitError

api = FragmentAPI()
try:
    check = api.check_availability(
        product=os.environ["PRODUCT"],
        username=os.environ["TELEGRAM_USERNAME"],
        amount=int(os.environ["AMOUNT"]),
        payment_method=os.environ["PAYMENT_METHOD"],
    )
except RateLimitError as error:
    raise SystemExit(f"Do not charge. Retry after {error.retry_after} seconds.")
except FragmentAPIError as error:
    raise SystemExit(f"Do not charge. {error.code or ''} {error.action or str(error)}")

if not check.available:
    raise SystemExit(f"Do not charge. {check.message} {check.action or ''}")
print("Available. Continue to your shop's payment step.")
```

The smaller [`check_availability.py`](check_availability.py) script checks **Stars only**, defaults to 100 Stars, and does not read `PRODUCT`. Set `AMOUNT` explicitly. It prints failures but is not an exit-code gate for a purchase command.

## Python SDK

After the pre-payment check and confirmed customer payment, use this purchase snippet. It reads the setup variables, supports both products, passes an explicit order key, and accepts optional wallet selectors:

```python
import os
from fragment_api import FragmentAPI

api = FragmentAPI()
wallet = {}
if os.environ.get("TON_WALLET_ADDRESS"):
    wallet["wallet_address"] = os.environ["TON_WALLET_ADDRESS"]
if os.environ.get("TON_ACCOUNT_INDEX"):
    wallet["account_index"] = int(os.environ["TON_ACCOUNT_INDEX"])

purchase = api.create_purchase(
    product=os.environ["PRODUCT"],
    username=os.environ["TELEGRAM_USERNAME"],
    amount=int(os.environ["AMOUNT"]),
    payment_method=os.environ["PAYMENT_METHOD"],
    seed=os.environ["TON_WALLET_SEED"],
    idempotency_key=os.environ["SHOP_ORDER_ID"],
    **wallet,
)
print("Record purchase_id with your shop order:", purchase.purchase_id, flush=True)
result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
```

Printing an ID is not durable storage. In your application, save it in the order record before `api.wait()`. See [results and retries](#results-and-retries) for timeout recovery.

Choose the example matching your integration:

| Goal | Example |
|---|---|
| Test the API without a wallet | [`prices.py`](prices.py) |
| Purchase step for a paid shop order | [`shop_minimal.py`](shop_minimal.py) |
| Check a recipient before charging | [`check_availability.py`](check_availability.py) |

`shop_minimal.py` accepts both products, both payment methods, and optional wallet selectors. Run it with the setup variables above. Its `fulfill_order()` function creates a purchase and returns its ID; save that ID in your shop database before polling. Customer payment collection stays in your shop. Availability must be checked before charging; only call fulfillment after confirmed payment.

```bash
export PRODUCT=stars AMOUNT=100 PAYMENT_METHOD=usdt
python examples/shop_minimal.py
```

For Premium, set `PRODUCT=premium` and `AMOUNT=3`, `6`, or `12`. Keep `SHOP_ORDER_ID` unchanged when retrying the same order. If a saved purchase needs reconciliation, inspect that purchase instead of creating a replacement.

Focused scripts show SDK method signatures:

| Purchase | GRAM | USDT on TON |
|---|---|---|
| 50 Stars: `buy_stars(amount=50, ...)` | [`stars_gram.py`](stars_gram.py) | [`stars_usdt.py`](stars_usdt.py) |
| 3 months: `buy_premium(months=3, ...)` | [`premium_gram.py`](premium_gram.py) | [`premium_usdt.py`](premium_usdt.py) |

These small Python scripts require `SHOP_ORDER_ID` and pass it as the idempotency key. Their quantities and payment methods are fixed in code. They skip the pre-payment availability step; use the flow above when integrating a shop. Reuse the same key for retries and save the returned purchase ID.

## Choose your wallet

| Wallet data | Purchase fields | Reference |
|---|---|---|
| 24-word TON mnemonic or Base64 32-byte private key | `seed` only | [`wallet_24_words.py`](wallet_24_words.py) |
| 12-word seed and wallet address | `seed` + `wallet_address` | [`wallet_12_words_address.py`](wallet_12_words_address.py) |
| 12-word seed and known account index | `seed` + `account_index` | [`wallet_12_words_index.py`](wallet_12_words_index.py) |

A 12-word seed alone cannot identify the intended wallet. For the purchase snippet above, set one selector:

```bash
export TON_WALLET_ADDRESS="UQ_YOUR_WALLET_ADDRESS"
```

Or, if the account index is known:

```bash
export TON_ACCOUNT_INDEX=0
```

Replace placeholders with your actual wallet selection. Index range: `0..100`; index alone selects V5R1. If both selectors are set, the API verifies they match. Remove stale selector variables when switching wallets.

To resolve an unknown index from a 12-word seed and address, set `TON_WALLET_SEED` and `TON_WALLET_ADDRESS`, then run:

```bash
python examples/resolve_wallet.py
```

[`resolve_wallet.py`](resolve_wallet.py) returns the address, index, and wallet version without buying anything. Wallet selection applies to both products and payment methods.

## REST API

No authentication header is required. Use the [OpenAPI specification](../openapi.yaml) for request and response schemas.

| Client | Requirements | Example |
|---|---|---|
| curl | Bash, Python 3, curl with `--fail-with-body` | [`curl.sh`](curl.sh) |
| Node.js | Node.js 18+ | [`node.mjs`](node.mjs) |

Both scripts check availability, create a purchase, then poll its status. Neither collects customer payment nor durably saves the ID. In a shop, run the check before charging and persist the ID before polling.

After setup, select the order and explicitly reuse its key:

```bash
export PRODUCT=premium AMOUNT=3 PAYMENT_METHOD=usdt
export IDEMPOTENCY_KEY="${SHOP_ORDER_ID:?Set SHOP_ORDER_ID from your shop order}"
bash examples/curl.sh
```

Alternatively, run `node examples/node.mjs` instead of the last command. Both scripts accept `IDEMPOTENCY_KEY` or `SHOP_ORDER_ID` and require a stable key. They stop polling after 5 minutes; a timeout does not mean failure. Resume the saved purchase ID or retry creation with its original key. Do not run both examples as separate purchases for one customer order.

`FRAGMENT_API_URL` overrides the base URL in the file-based examples. Do not point credential-bearing requests at an untrusted host.

## Prices

Quotes need no wallet credentials and create no purchase:

```python
from fragment_api import FragmentAPI

api = FragmentAPI()
stars = api.get_stars_price(100)
premium = api.get_premium_price(3)
print(stars.prices.gram, stars.prices.usdt, stars.stale)
print(premium.prices.gram, premium.prices.usdt, premium.stale)
```

```bash
curl --fail-with-body 'https://api-stars.duckdns.org/api/v1/prices/quote?product=stars&amount=100'
```

Prices are exact decimal strings; use decimal arithmetic, not binary `float`, for accounting. `stale=true` marks a cached fallback quote. Quotes are informational: Fragment creates a fresh quote when the purchase starts.

## Results and retries

| Result | What to do |
|---|---|
| `completed` | Mark the shop order delivered. |
| `failed` | Inspect `result.error` (`code`, `message`) and handle the customer's order. |
| `reconciliation_required` | Stop automatic processing and request reconciliation. Never create an automatic replacement order. |

`api.wait()` stops at all three statuses; it does not raise an exception merely because a purchase failed. Its default timeout is 300 seconds. A timeout or connection error does not prove that the purchase failed.

- Persist `purchase_id`; resume with `api.get_purchase(purchase_id)` or `api.wait(purchase_id)`.
- If creation returned no ID, retry the original request with the same `idempotency_key` and unchanged fields. Never generate a new key to bypass uncertainty.
- On `409`, inspect the existing order and key conflict; do not switch keys to force a purchase.
- HTTP errors expose `code`, `action`, and `retry_after` when provided. Keep request bodies and wallet credentials out of error reports.

## AI-assisted integration

The [portable integration skill](../skills/fragment-api-integration/SKILL.md) covers Python, REST, availability, wallets, prices, idempotency, and polling. From the repository root, choose your agent:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/fragment-api-integration "${CODEX_HOME:-$HOME/.codex}/skills/"
```

For Claude:

```bash
mkdir -p "$HOME/.claude/skills"
cp -R skills/fragment-api-integration "$HOME/.claude/skills/"
```

Ask: `Use $fragment-api-integration to add Telegram Stars purchases to this backend.`

Never share wallet credentials with an AI agent. Let your backend load them at runtime. Support: [@tondotdev](https://t.me/tondotdev); security reports: [SECURITY.md](../SECURITY.md).
