# Python SDK

Use this reference when the client backend is Python.

## Install

```bash
pip install fragment-api-dev==1.4.0
```

The SDK uses `https://api-stars.duckdns.org` by default and does not require an API key.

## Check Before Customer Payment

```python
from fragment_api import FragmentAPI

api = FragmentAPI()
check = api.check_stars_availability("@telegram_user", 100, "gram")
if not check.available:
    print(check.message, check.action)
    raise SystemExit(2)
```

For Premium, use `api.check_premium_availability("@telegram_user", 3, "usdt")`.
The check never needs wallet credentials. Run it shortly before accepting payment. On `RateLimitError`, wait for `error.retry_after`; on `ServiceUnavailableError`, retry later and do not charge yet.

## Stars With GRAM

```python
import os

from fragment_api import FragmentAPI


api = FragmentAPI()

purchase = api.buy_stars(
    username="@telegram_user",
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
    idempotency_key=order.id,
)

save_purchase_id(order.id, purchase.purchase_id)
result = api.wait(purchase.purchase_id)
```

Use the application's real stable order identifier instead of generating a new key on each retry.

## Premium With USDT

```python
purchase = api.buy_premium(
    username="@telegram_user",
    months=3,
    payment_method="usdt",
    seed=os.environ["TON_WALLET_SEED"],
    idempotency_key=order.id,
)

save_purchase_id(order.id, purchase.purchase_id)
result = api.wait(purchase.purchase_id)
```

The paying wallet needs a small GRAM balance for TON network fees even when the purchase uses USDT.

## 12-Word Wallets

Pass the address when the index is unknown:

```python
purchase = api.buy_stars(
    username="@telegram_user",
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
    wallet_address=os.environ["TON_WALLET_ADDRESS"],
    idempotency_key=order.id,
)
```

Pass the index when it is already known:

```python
purchase = api.buy_stars(
    username="@telegram_user",
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
    account_index=int(os.environ["TON_ACCOUNT_INDEX"]),
    idempotency_key=order.id,
)
```

Resolve an unknown index once:

```python
wallet = api.resolve_wallet(
    seed=os.environ["TON_WALLET_SEED"],
    wallet_address=os.environ["TON_WALLET_ADDRESS"],
)
print(wallet.account_index, wallet.wallet_version)
```

Do not print the seed.

## Prices

```python
stars = api.get_stars_price(100)
premium = api.get_premium_price(3)

print(stars.prices.gram, stars.prices.usdt)
print(premium.prices.gram, premium.prices.usdt)
```

Money values are decimal strings. Do not convert them through binary `float` for accounting.

## Result And Errors

`api.wait()` returns a purchase with one of the terminal statuses:

- `completed`: success.
- `failed`: expose the public error and action.
- `reconciliation_required`: stop automatic processing and require reconciliation.

Catch `FragmentAPIError` when the application needs structured `code`, `action`, and `retry_after` fields:

```python
from fragment_api import FragmentAPIError

try:
    result = api.wait(purchase.purchase_id)
except FragmentAPIError as error:
    handle_public_error(code=error.code, action=error.action)
```

Do not return stack traces or request data to the end user.

## Maintained Examples

- [Stars with GRAM](../../../examples/stars_gram.py)
- [Stars with USDT](../../../examples/stars_usdt.py)
- [Premium with GRAM](../../../examples/premium_gram.py)
- [Premium with USDT](../../../examples/premium_usdt.py)
- [12-word wallet by address](../../../examples/wallet_12_words_address.py)
- [12-word wallet by index](../../../examples/wallet_12_words_index.py)
- [Availability before payment](../../../examples/check_availability.py)
