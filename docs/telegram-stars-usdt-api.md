# Buy Telegram Stars with USDT through API

Configure USDT-on-TON purchases, understand GRAM network fees, and request exact price strings for Telegram Stars.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/telegram-stars-usdt-api) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Use USDT on the TON network

Set payment_method to usdt to pay a supported Fragment invoice using USDT on TON. USDT on another network is not interchangeable with USDT on TON.

Keep a small GRAM balance for network fees. The 0% API fee does not remove the purchase cost or blockchain fees.


## Read the price before creating the order

The price endpoint returns both gram and usdt as strings. Use Decimal for financial arithmetic in Python. A quote does not reserve the final purchase price.

```python
from decimal import Decimal
from fragment_api import FragmentAPI

quote = FragmentAPI().get_stars_price(100)
print(Decimal(quote.prices.usdt), "USDT", quote.stale)
```


## Use the same currency in the check and purchase

Run the availability check with payment_method=usdt and the exact Stars quantity. If the response is PAYMENT_METHOD_UNAVAILABLE, follow its action instead of charging for an unsupported option.

Keep the order selection unchanged across retries. Switching from usdt to gram under the same idempotency key conflicts with the original order.

- [USDT Stars example](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/stars_usdt.py)
- [Configure a USDT request](https://stars-market.duckdns.org/api#quick-start)

## Client-signed USDT payments

For client-signed checkout, use the transaction returned by the API. Its payload carries the transfer instructions; replacing it with a plain USDT transfer or comment is not equivalent.

Your wallet signs and submits the transaction. Send the signed BOC back and track the checkout until delivery is confirmed.

- [Client-signed checkout contract](https://stars-market.duckdns.org/docs/client-signed-checkout)

