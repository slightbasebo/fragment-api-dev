# Node starter

Persistent paid-order worker using built-in `fetch` and `node:sqlite`. **Node.js 22.18+ required.** No npm dependencies, API key, web server, or public purchase endpoint. Mock mode is the default. 0% API service fee; product prices and network fees remain separate.

## Local run

From the public repository root:

```bash
python3 examples/mock_server.py
# Another terminal:
export STARTER_DB=examples/starters/node-demo.sqlite
export STARTER_SHOP_ID=node-demo
node examples/starters/node/starter.mjs demo order-001 completed
node examples/starters/node/starter.mjs worker
# Another terminal with the same environment:
node examples/starters/node/starter.mjs status order-001
```

Use `failed`, `429`, `timeout`, or `reconciliation_required` instead of `completed` with a new test order ID. Set `REQUEST_TIMEOUT=0.25` for `timeout`. Repeating the same ID preserves the original purchase. Restart the worker with the same database while keeping the mock running. Node 22 can print an experimental SQLite warning.

## Backend integration

```javascript
import { configFromEnv, OrderStore, worker } from './starter.mjs';

const config = configFromEnv();
const store = new OrderStore(config);
// After your backend verifies the provider signature, paid state, amount, and currency:
store.confirmPaid(merchantOrderId,
  { product: 'stars', username: '@recipient', amount: 50, payment_method: 'gram' },
  verifiedProviderPaymentId);
// Run one worker per database. Stop with an AbortController signal; close the store afterward.
```

`confirmPaid` is a trusted backend integration function, not a payment verifier or public endpoint. Do not expose it to customer-supplied `paid=true`, chat messages, or unsigned webhooks. The `demo` CLI is disabled in live mode. Wallet material comes only from the backend environment and is not stored with orders.

See the [shared guide](../README.md) for exact interfaces, live opt-in configuration, concurrency limits, retry/reconciliation rules, and tests.
