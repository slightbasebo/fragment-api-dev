# API and SDK changelog

Public changes to Fragment API integration guides, async SDK support, starters, and client-signed checkout.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/changelog) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## SDK 1.4.0 — 12 October 2026

AsyncFragmentAPI adds async network requests and polling. The synchronous FragmentAPI interface remains available.

Client-signed checkout helpers and typed results support creating and tracking wallet-approved payments. Install the async extra when using AsyncFragmentAPI.

- [PyPI release](https://pypi.org/project/fragment-api-dev/1.4.0/)

## Developer integration update — 12 October 2026

Added an integration builder, focused guides, persistent aiogram and Node.js starters, and a local mock for testing error paths.

The public /api/v1/checkouts contract exposes wallet-approved transactions. Existing wallet-backed purchase routes remain compatible.

- [OpenAPI contract](https://github.com/slightbasebo/fragment-api-dev/blob/main/openapi.yaml)

## SDK 1.3.0

Added pre-payment recipient checks. Price helpers, wallet selection, Stars, and Premium remain available.

- [PyPI 1.3.0](https://pypi.org/project/fragment-api-dev/1.3.0/)

