import os

from fragment_api import FragmentAPI


api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))

# A 24-word TON mnemonic or Base64 32-byte private key needs no wallet selector.
purchase = api.buy_stars(
    username=os.getenv("TELEGRAM_USERNAME", "@telegram_user"),
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
    idempotency_key=os.environ["SHOP_ORDER_ID"],
)

print("Record purchase_id with your shop order:", purchase.purchase_id, flush=True)
result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
