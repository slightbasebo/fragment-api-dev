# Persistent starters

Small, mock-first delivery workers for Telegram Stars and Premium: **0% API service fee, no API key**. Product prices and blockchain fees still apply in live mode.

- `aiogram/`: Python 3.10+, SQLite 3.35+, native async SDK, optional owner-only aiogram 3 console.
- `node/`: Node.js **22.18+**, built-in `fetch` and `node:sqlite`; no npm runtime dependencies. Node 22 may print an experimental SQLite warning.
- `../mock_server.py`: Python standard library HTTP server, loopback-only, synthetic responses. No production backend, wallet, seed, or Telegram access.

## Local mock walkthrough

Run commands from the repository root, where `examples/` exists.

1. Start the mock in one terminal:

   ```bash
   python3 examples/mock_server.py --port 8081
   ```

2. Install the Python starter in a virtual environment:

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r examples/starters/aiogram/requirements.txt
   ```

3. Add a synthetic order and start a worker. No bot token is needed:

   ```bash
   export STARTER_MODE=mock
   export FRAGMENT_BASE_URL=http://127.0.0.1:8081
   export STARTER_DB=examples/starters/python-demo.sqlite
   export STARTER_SHOP_ID=python-demo
   .venv/bin/python examples/starters/aiogram/orders.py demo order-001 completed
   .venv/bin/python examples/starters/aiogram/orders.py worker
   ```

4. In another terminal with the same environment, read the result:

   ```bash
   .venv/bin/python examples/starters/aiogram/orders.py status order-001
   ```

5. Stop and restart the worker against the same database. Repeat the same demo command and ID: it does not create another delivery. New scenario, new test order ID.

Node equivalent, using the same mock service and a separate database:

```bash
export STARTER_MODE=mock
export FRAGMENT_BASE_URL=http://127.0.0.1:8081
export STARTER_DB=examples/starters/node-demo.sqlite
export STARTER_SHOP_ID=node-demo
node examples/starters/node/starter.mjs demo order-001 completed
node examples/starters/node/starter.mjs worker
# Another terminal, same environment:
node examples/starters/node/starter.mjs status order-001
```

There is no Node web server or public purchase endpoint. The CLI's `demo` command is disabled in live mode.

## Deterministic scenarios

Use the scenario name in `demo ORDER_ID SCENARIO`; the mock selects behavior from `username` for direct SDK calls.

| Scenario / username | Behavior |
| --- | --- |
| `completed` / `@completed` | POST accepts; first status read completes |
| `failed` / `@failed` | POST accepts; first status read fails |
| `429` / `@429` | First POST returns 429 and a two-second retry delay; same key then succeeds |
| `timeout` / `@timeout` | First POST accepts, then delays its response for two seconds; replay returns the same ID |
| `reconciliation_required` / `@reconciliation_required` | Stops automatic processing for manual reconciliation; never creates a replacement purchase |

Set `REQUEST_TIMEOUT=0.25` for the timeout scenario. Defaults use a five-second request timeout. Retries keep the same key, recipient, product, amount, payment method, and runtime wallet configuration.

Mock service implements health, price catalog/quotes, availability, wallet resolver, purchases, and versioned checkout routes. Checkout submission accepts only synthetic BOC `c3ludGhldGlj`. Never pass the mock transaction to a real wallet. `mock-only-not-a-wallet` is a sentinel, not a mnemonic or private key; the mock rejects other seed values and does not log bodies.

The mock stores server state in memory. Keep it running while testing worker restarts. Restarting the mock resets its idempotency history; it is not a durable payment backend or proof of production delivery.

## aiogram owner console

Set `BOT_TOKEN` from your runtime secret environment and `BOT_OWNER_ID` to your numeric Telegram user ID, then run:

```bash
.venv/bin/python examples/starters/aiogram/bot.py
```

`/demo ORDER_ID SCENARIO` exists only in mock mode. `/status ORDER_ID` reads a stored result. Both require the configured owner in their private chat. Group messages, anonymous messages, and other users are ignored. Live mode has no Telegram purchase, seed-entry, or payment-confirmation command. Never send wallet seeds to the bot. The bot runs the worker internally; do not start a second worker for the same database.

## Verified-paid-order integration

The queue is a **trusted backend boundary**, not a payment verifier. Your backend must verify the provider's signature, final paid status, amount, currency, and immutable merchant order selection before calling either function below. Never call them from an unauthenticated route or accept a customer's `paid=true` claim. There is no live `confirm-paid` CLI command.

Python (add `examples/starters/aiogram` to your backend's import path):

```python
from orders import Config, OrderStore

store = OrderStore(Config.from_env())
try:
    # Values come from your verified payment record, not a chat message.
    store.confirm_paid(
        merchant_order_id,
        {"product": "stars", "username": "@recipient", "amount": 50, "payment_method": "gram"},
        payment_reference=verified_provider_payment_id,
    )
finally:
    store.close()
```

Node:

```javascript
import { configFromEnv, OrderStore } from './examples/starters/node/starter.mjs';

const store = new OrderStore(configFromEnv());
try {
  store.confirmPaid(merchantOrderId,
    { product: 'stars', username: '@recipient', amount: 50, payment_method: 'gram' },
    verifiedProviderPaymentId);
} finally {
  store.close();
}
```

Exact interfaces:

- Python: `Config.from_env(env=None)`, `OrderStore(config)`, `confirm_paid(order_id, selection, *, payment_reference)`, `get(order_id)`, `close()`, `await run_once(store, api, config)`, `await worker(store, api, config)`.
- Node: `configFromEnv(env=process.env)`, `new OrderStore(config)`, `confirmPaid(orderId, selection, paymentReference)`, `get(orderId)`, `close()`, `await runOnce(store, config, {signal}={})`, `await worker(store, config, signal)`.
- `selection` has exactly `product`, `username`, `amount`, `payment_method`. Extra fields, including seeds, are rejected. Premium uses `product: "premium"` and `amount: 3`, `6`, or `12`.
- Order IDs and provider references allow 1-128 ASCII letters, digits, `_`, `.`, `:`, `-`. Use globally unique merchant IDs and provider-scoped payment references.

## Persistence and recovery

SQLite records the immutable selection, unique merchant ID, unique verified payment reference, stable hashed idempotency key, returned purchase ID, retry count, next attempt, and a short worker lease. It never records seed material or server error bodies. Keep the database and WAL files on durable local storage, protect access, and back them up. Do not delete them as a retry strategy.

Each iteration claims at most `WORKER_CONCURRENCY` rows and performs one HTTP operation per claimed row. The default is three; the allowed range is 1-16. Atomic SQLite claims and lease tokens prevent concurrent workers from overwriting newer results. Run one delivery worker per database for a strict global concurrency bound; independent processes each have their own bound. This is a small single-host starter, not a distributed queue.

Crash before persisting the response: after the lease expires, replay the exact request and key. Once a purchase ID is stored: only GET that ID. Requests have a hard timeout shorter than their lease. Cancelled requests leave a recoverable lease; cancellation does not label an uncertain payment failed or automatically replay it.

429, transport errors, and selected transient 5xx responses use persisted exponential delays, honoring `retry_after`. Five consecutive failures move the order to `review_required`; successes reset the failure count. `completed`, `failed`, `reconciliation_required`, and `review_required` stop automatic work. Review uncertain orders with the provider/API before resuming the **same** record; there is intentionally no automatic refund, replacement purchase, or retry-with-new-ID command. This relies on server-side idempotency; the starter does not claim distributed exactly-once delivery.

Databases are bound to mode, API origin, and shop ID. Python and Node databases are separate; do not interchange them. Keep the shop ID and runtime payer wallet configuration stable across restarts. A changed payer or a restored/out-of-date database requires manual reconciliation, not a new key.

## Live configuration

Live mode can spend real funds. Do not enable it until the trusted payment-verification adapter, recipient checks, operational reconciliation, and secret handling are ready. No live transactions are needed for the tests in this slice.

| Variable | Default / rule |
| --- | --- |
| `STARTER_MODE` | `mock`; only `mock` or `live` accepted |
| `FRAGMENT_BASE_URL` | `http://127.0.0.1:8081`; live requires an explicit HTTPS origin with no credentials, path, query, or fragment |
| `STARTER_LIVE_CONFIRM` | Live requires exact `I_UNDERSTAND_REAL_PURCHASES` |
| `STARTER_SHOP_ID` | `demo`; live requires an explicit stable shop ID |
| `STARTER_DB` | Python `orders-mock.sqlite`; Node `orders-node-mock.sqlite`; live gets a separate default |
| `WORKER_CONCURRENCY` | `3`, integer 1-16 |
| `REQUEST_TIMEOUT` | `5` seconds, positive and at most 60 |
| `TON_WALLET_SEED` | Required only in live mode, backend runtime secret only; ignored in mock mode |
| `TON_ACCOUNT_INDEX` | Optional integer 0-100; use with a 12-word wallet |
| `TON_WALLET_ADDRESS` | Optional 12-word wallet selector instead of/in addition to index |
| `BOT_TOKEN` | Required only to run the Telegram console; runtime secret |
| `BOT_OWNER_ID` | Required positive Telegram user ID for the console |

No dotenv loader is included. Set environment variables through your shell or secret manager; `environment.example` documents safe defaults. The starter does not collect credentials or seeds from customers. For customer-owned payment wallets use the SDK's `create_checkout`, `get_checkout`, `submit_checkout(..., boc=...)`, and `wait_checkout` with a TonConnect UI; that UI is intentionally outside this starter.

## Tests

From the repository root after installing the Python starter:

```bash
.venv/bin/python -m unittest discover -s examples/tests -q
node --test examples/tests/node.test.mjs
```

Tests use synthetic loopback traffic only. Python test dependencies are the SDK async extra plus `aiogram>=3.13,<4`. No pytest or npm test dependency is needed. Node's mock integration test requires `python3` on PATH (or `PYTHON` set to a Python executable).

See the [API documentation](https://stars-market.duckdns.org/docs) and [integration examples](https://github.com/slightbasebo/fragment-api-dev/tree/main/examples).
