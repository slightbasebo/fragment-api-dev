"""Purchase step for a paid shop order; does not collect customer payment."""

import os

from fragment_api import FragmentAPI, Purchase


def fulfill_order(
    order_id: str,
    username: str,
    amount: int,
    *,
    product: str = "stars",
    payment_method: str = "gram",
) -> Purchase:
    api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))
    wallet = {}
    if os.environ.get("TON_WALLET_ADDRESS"):
        wallet["wallet_address"] = os.environ["TON_WALLET_ADDRESS"]
    if os.environ.get("TON_ACCOUNT_INDEX"):
        wallet["account_index"] = int(os.environ["TON_ACCOUNT_INDEX"])
    purchase = api.create_purchase(
        product=product,
        username=username,
        amount=amount,
        payment_method=payment_method,
        seed=os.environ["TON_WALLET_SEED"],
        idempotency_key=order_id,
        **wallet,
    )
    print("Save purchase_id with your order before polling:", purchase.purchase_id, flush=True)
    return purchase


if __name__ == "__main__":
    api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))
    product = os.getenv("PRODUCT", "stars")
    amount = int(os.getenv("AMOUNT", "50" if product == "stars" else "3"))
    username = os.environ["TELEGRAM_USERNAME"]
    method = os.getenv("PAYMENT_METHOD", "gram")
    order_id = os.environ["SHOP_ORDER_ID"]
    check = api.check_availability(product=product, username=username, amount=amount, payment_method=method)
    if not check.available:
        raise SystemExit(f"{check.message} {check.action or ''}")
    # In a shop, check availability before charging; fulfill only after confirmed customer payment.
    purchase = fulfill_order(order_id, username, amount, product=product, payment_method=method)
    result = api.wait(purchase.purchase_id)
    print(result.status, result.transaction_hash or result.error)
