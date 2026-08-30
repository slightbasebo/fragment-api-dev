import os

from fragment_api import FragmentAPI


api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))

purchase = api.buy_stars(
    username=os.getenv("TELEGRAM_USERNAME", "@telegram_user"),
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
)

result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
