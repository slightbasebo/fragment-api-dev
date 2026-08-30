import os

from fragment_api import FragmentAPI


api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))

# Use this form when the account index for the 12-word seed is already known.
purchase = api.buy_stars(
    username=os.getenv("TELEGRAM_USERNAME", "@telegram_user"),
    amount=50,
    payment_method="gram",
    seed=os.environ["TON_WALLET_SEED"],
    account_index=int(os.environ["TON_ACCOUNT_INDEX"]),
)

result = api.wait(purchase.purchase_id)
print(result.status, result.transaction_hash or result.error)
