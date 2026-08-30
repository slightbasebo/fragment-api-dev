import os

from fragment_api import FragmentAPI


api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))

# Keep a small GRAM balance in the wallet for TON network fees.
purchase = api.buy_premium(
    username=os.getenv("TELEGRAM_USERNAME", "@telegram_user"),
    months=3,
    payment_method="usdt",
    seed=os.environ["TON_WALLET_SEED"],
)

result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
