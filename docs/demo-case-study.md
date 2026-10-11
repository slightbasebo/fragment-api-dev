# How the Fragment demo shop uses the API

A first-party example of live prices, recipient checks, wallet approval, and delivery tracking for Stars and Premium.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/demo-case-study) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## A project demonstration

Fragment Market is this project's own demo shop. It is not an independent customer testimonial. It offers Telegram Stars and Premium with live price and recipient checks.

The implementation shows how an API integration can separate selection, price display, wallet approval, and final delivery tracking.


## The checkout flow

The shop checks recipient eligibility and displays a current price. The customer connects a TON wallet, reviews a generated transaction, and approves it locally.

The page follows the checkout ID until a final result. It keeps recovery information across refreshes and does not automatically resend an uncertain payment.


## What was verified

On 12 October 2026, the public API demo returned a fresh price for a 3-month Premium subscription. That was a read-only price request, not a paid purchase or delivery test.

No uptime percentage, customer count, or delivery-time guarantee is inferred from that check. Current observations are available on the service-check page.

- [Open the demo shop](https://stars-market.duckdns.org/)
- [Service checks](https://stars-market.duckdns.org/status)

## Reuse the pattern in your project

Start with an SDK or REST example. Retain your existing payment provider and order storage. Add availability before collecting payment, then persist the API purchase ID before polling.

For a wallet-connected storefront, use client-signed checkout and keep secrets out of browser code.

- [Configure your integration](https://stars-market.duckdns.org/api#quick-start)
- [Client-signed checkout](https://stars-market.duckdns.org/docs/client-signed-checkout)

