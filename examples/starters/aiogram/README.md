# aiogram 3 starter

Native async Fragment SDK, standard-library SQLite order store, and owner-only Telegram console. Mock mode is the default. No API key; 0% API service fee, excluding product prices and network fees.

## Run without Telegram

From the public repository root:

```bash
python3 examples/mock_server.py
# Another terminal:
python3 -m venv .venv
.venv/bin/python -m pip install -r examples/starters/aiogram/requirements.txt
export STARTER_DB=examples/starters/python-demo.sqlite
export STARTER_SHOP_ID=python-demo
.venv/bin/python examples/starters/aiogram/orders.py demo order-001 completed
.venv/bin/python examples/starters/aiogram/orders.py worker
# Another terminal with the same environment:
.venv/bin/python examples/starters/aiogram/orders.py status order-001
```

Repeat an order ID to recover it, not to create another delivery. Stop/restart the worker against the same database. The mock must remain running during restart tests.

Requirements: Python 3.10+, SQLite 3.35+, `fragment-api-dev[async]==1.4.0`, `aiogram>=3.13,<4`. The SDK's async extra adds `httpx>=0.27,<1`.

## Telegram console

Provide `BOT_TOKEN` through your runtime secret environment and `BOT_OWNER_ID` as your positive numeric Telegram user ID. Run `.venv/bin/python examples/starters/aiogram/bot.py`.

Only the owner in a private chat can use `/demo ORDER_ID SCENARIO` or `/status ORDER_ID`. `/demo` is mock-only. No command accepts a seed, a payment proof, or a live purchase request. The bot starts its own worker; do not run another worker against the same database.

## Backend integration

After your backend verifies a final paid order, call `OrderStore(Config.from_env()).confirm_paid(order_id, selection, payment_reference=verified_provider_payment_id)`. Close the store when finished. `selection` contains exactly `product`, `username`, `amount`, `payment_method`.

This function does not verify payment itself. Never expose it to unauthenticated chat or HTTP input. Live mode needs explicit configuration, a trusted payment-verification adapter, and backend-only runtime wallet secrets.

See the [shared guide](../README.md) for complete environment variables, deterministic failure scenarios, retries, lifecycle, safety gates, and tests.
