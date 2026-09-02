# Fragment API Examples

Ready-to-run examples for buying Telegram Stars and Telegram Premium with GRAM or USDT on TON.

## Before you start

Install the Python SDK:

```bash
pip install fragment-api-dev==1.3.0
```

Set the wallet seed and recipient on your backend:

```bash
export TON_WALLET_SEED="your wallet seed"
export TELEGRAM_USERNAME="@telegram_user"
```

Never put a wallet seed in browser or frontend code.

## Check before accepting payment

Use [`check_availability.py`](check_availability.py) before charging your customer:

```bash
python examples/check_availability.py
```

The check requires only product, username, amount, and payment method. It does not need wallet credentials and does not create a purchase.

Correct shop flow:

1. Check availability shortly before payment.
2. If `available` is `false`, show `message` and `action` and do not charge.
3. If the check returns `429`, wait for `retry_after`; if it returns `503`, retry later.
4. Accept customer payment.
5. Create one purchase with a stable `idempotency_key`.
6. Save `purchase_id` and wait for a terminal status.

The result is a point-in-time check, not a reservation or guarantee. The purchase can still fail later, so always handle its final status.

## Choose a product and payment method

These examples use a 24-word TON mnemonic or Base64 32-byte private key. No wallet address or account index is needed.

| What you want to buy | Payment | Example |
|---|---|---|
| Telegram Stars | GRAM | [`stars_gram.py`](stars_gram.py) |
| Telegram Stars | USDT on TON | [`stars_usdt.py`](stars_usdt.py) |
| Telegram Premium | GRAM | [`premium_gram.py`](premium_gram.py) |
| Telegram Premium | USDT on TON | [`premium_usdt.py`](premium_usdt.py) |

USDT purchases require a small GRAM balance for TON network fees.

Run an example:

```bash
python examples/stars_gram.py
```

## Choose a wallet format

| Wallet data you have | Example | Explanation |
|---|---|---|
| 24-word TON mnemonic or Base64 32-byte private key | [`wallet_24_words.py`](wallet_24_words.py) | Send only `seed` |
| 12-word seed and wallet address | [`wallet_12_words_address.py`](wallet_12_words_address.py) | The API finds the account index |
| 12-word seed and known account index | [`wallet_12_words_index.py`](wallet_12_words_index.py) | The API uses that account index |
| 12-word seed and address, but index unknown | [`resolve_wallet.py`](resolve_wallet.py) | Resolve the index before purchase |

For a 12-word seed with an address:

```bash
export TON_WALLET_SEED="your 12 words"
export TON_WALLET_ADDRESS="UQ_YOUR_WALLET_ADDRESS"
python examples/wallet_12_words_address.py
```

For a 12-word seed with a known index:

```bash
export TON_WALLET_SEED="your 12 words"
export TON_ACCOUNT_INDEX=0
python examples/wallet_12_words_index.py
```

A 12-word seed without `TON_WALLET_ADDRESS` or `TON_ACCOUNT_INDEX` cannot identify the intended wallet.

Wallet selection works with every product and payment method. For example, Premium paid with USDT from a 12-word wallet can use its address:

```python
purchase = api.buy_premium(
    username="@telegram_user",
    months=6,
    payment_method="usdt",
    seed=os.environ["TON_WALLET_SEED"],
    wallet_address=os.environ["TON_WALLET_ADDRESS"],
)
```

If the index is already known, replace `wallet_address=...` with `account_index=...`.

## Direct REST API

The REST examples support both products, both payment methods, and optional wallet selectors.

| Language | Example |
|---|---|
| curl | [`curl.sh`](curl.sh) |
| Node.js 18+ | [`node.mjs`](node.mjs) |

Both full REST examples run the availability check before creating the purchase.

Select a product and payment method with environment variables:

```bash
export PRODUCT=premium
export AMOUNT=3
export PAYMENT_METHOD=usdt
bash examples/curl.sh
```

Valid values:

- `PRODUCT=stars`: `AMOUNT` is 50 to 1,000,000.
- `PRODUCT=premium`: `AMOUNT` is 3, 6, or 12 months.
- `PAYMENT_METHOD=gram` or `PAYMENT_METHOD=usdt`.

## Result handling

Every purchase example waits until the order reaches a final status:

- `completed`: the purchase finished successfully.
- `failed`: read the returned error and action.
- `reconciliation_required`: do not create an automatic replacement order.

Use a stable `idempotency_key` from your own order ID in production. Retrying the same logical order with the same key prevents duplicate purchases.
