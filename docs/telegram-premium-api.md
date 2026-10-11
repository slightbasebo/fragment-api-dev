# Telegram Premium API integration

Gift 3, 6, or 12 months of Telegram Premium from your bot or shop using Python or REST and GRAM or USDT.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/telegram-premium-api) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Premium uses the same order API

The Telegram Premium API creates gifts for eligible Telegram usernames. Select 3, 6, or 12 months; REST uses product=premium and amount for the month count. The SDK helper uses months.

GRAM and USDT on TON are supported payment_method values, subject to current availability. No API key is required.


## Check eligibility before collecting payment

Call check_premium_availability for the exact username, duration, and currency. An active subscription or another recipient restriction can make a particular gift unavailable.

Use the returned code, message, and action. A 503 is an inconclusive check: keep customer payment disabled and try later.

```python
from fragment_api import FragmentAPI

api = FragmentAPI()
check = api.check_premium_availability("@telegram_user", 3, "usdt")
print(check.available, check.message, check.action)
```


## Create and track the gift

After confirmed customer payment, call buy_premium(months=3, ...) or POST /api/v1/purchases with product=premium and amount=3. Use the same stable key for all retries of that order.

HTTP 202 means accepted. Save purchase_id and wait for completed before telling the customer the gift was delivered.

- [Premium with GRAM](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/premium_gram.py)
- [Premium with USDT](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/premium_usdt.py)
- [Configure Premium integration](https://stars-market.duckdns.org/api#quick-start)

## Handle a changed result

Eligibility may change after the check. Handle the final purchase result even if the initial check was available.

For a timeout or uncertain transaction, recover the existing order. Do not generate a new key to bypass a pending outcome.

- [Errors and next actions](https://stars-market.duckdns.org/docs/orders-and-errors)

