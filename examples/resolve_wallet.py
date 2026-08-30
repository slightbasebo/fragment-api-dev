import os

from fragment_api import FragmentAPI


api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))

# Find the account index that produces the supplied address from a 12-word seed.
wallet = api.resolve_wallet(
    seed=os.environ["TON_WALLET_SEED"],
    wallet_address=os.environ["TON_WALLET_ADDRESS"],
)

print("Wallet:", wallet.wallet_address)
print("Account index:", wallet.account_index)
print("Wallet version:", wallet.wallet_version)
