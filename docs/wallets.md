# Choose the right wallet for API payments

Understand 24-word and 12-word wallet inputs, wallet_address, account_index, and client-signed checkout.

SDK 1.4.0 · Last verified: 12 October 2026

[API documentation](https://stars-market.duckdns.org/docs/wallets) | [Integration builder](https://stars-market.duckdns.org/api#quick-start)

## 24-word wallet

A 24-word TON mnemonic or canonical Base64 32-byte key can be supplied as seed by your trusted backend. Use the configured wallet containing funds for the selected payment.

The integration builder uses environment-variable names, never a browser field for your actual seed.


## 12-word wallet: address or index

A 12-word BIP39 seed requires wallet_address or account_index. An index alone selects a V5R1 account. Supported account_index values are 0 through 100.

When you know the address but not its index, use the wallet resolver. Save the returned index for future requests. If both address and index are provided, the API verifies they match.

- [Resolve a wallet](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/resolve_wallet.py)
- [12 words with address](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/wallet_12_words_address.py)
- [12 words with index](https://github.com/slightbasebo/fragment-api-dev/blob/main/examples/wallet_12_words_index.py)

## Sign without sending a seed to the API

Client-signed checkout uses payer_address to create the transaction. Your wallet or backend signer approves it locally; no seed is accepted by the checkout endpoint.

The submitted transaction must match the selected payer and the returned transaction. Use the signed BOC and track the checkout ID.

- [Client-signed checkout](https://stars-market.duckdns.org/docs/client-signed-checkout)

