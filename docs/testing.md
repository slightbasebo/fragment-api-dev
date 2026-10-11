# Test your integration without spending funds

Exercise successful orders, failures, timeouts, rate limits, and reconciliation with a local mock API.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/testing) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## Use the local mock

The mock runs on your machine and returns synthetic purchase results. No Fragment invoice or blockchain transaction is created.

Use synthetic credentials only. Keep your real wallet environment separate from mock configuration.

- [Mock server](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/mock_server.py)
- [Starter setup and scenarios](https://github.com/slightbasebo/fragment-api-dev/tree/main/examples/starters)

## Cover the five important outcomes

completed: mark the order delivered once. failed: handle failure without reporting success. 429: wait and retry without multiplying requests.

timeout: retain the same order key and recover the existing attempt. reconciliation_required: stop automatic replacement and preserve the ID for inspection.


## Then verify live access

Use public prices and recipient availability to check the real API without spending funds. These checks do not prove an actual purchase can complete.

A real end-to-end purchase needs an explicitly approved recipient, amount, funded wallet, and final delivery verification.

- [Run a live price request](https://stars-market.duckdns.org/api)

