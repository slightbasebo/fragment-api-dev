# Add Telegram Stars API to an aiogram bot

Start an aiogram 3 integration with async API calls, persistent orders, safe retries, and local mock scenarios.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/telegram-stars-api-aiogram) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Keep bot handlers responsive

aiogram handlers run asynchronously. Use AsyncFragmentAPI for network calls and polling so waiting for a purchase does not block the event loop.

Bound purchase concurrency and store order state outside the handler. A process restart should resume tracking the same purchase rather than create another one.

```bash
pip install "fragment-api-dev[async]==1.4.0" aiogram
```


## Start with the runnable bot example

The starter separates recipient checking, customer payment confirmation, and fulfillment. Start in mock mode, then configure live credentials only on your backend.

The example restricts purchase controls to configured operators. Adapt authentication and confirmed-payment handling to your shop before opening it to customers.

- [aiogram starter and setup](https://github.com/slightbasebo/fragment-api-dev/tree/main/examples/starters/aiogram)

## Persist before waiting

Store your shop order ID and complete purchase selection before sending the create request. Save purchase_id as soon as it arrives. Use your original order ID as idempotency_key.

After restart, poll saved purchase IDs. For interrupted creation without an ID, repeat the original request with its original key. Never replace reconciliation_required automatically.


## Test the failure paths

Use local scenarios for completed, failed, rate limiting, timeout, and reconciliation_required. Confirm that an error leaves one logical order, does not charge twice, and still lets the bot respond to messages.

Mock results validate your integration code; they are not evidence that a real Fragment purchase succeeded.

- [Mock setup](https://stars-market.duckdns.org/docs/testing)
- [Node.js alternative](https://github.com/slightbasebo/fragment-api-dev/tree/main/examples/starters/node)

