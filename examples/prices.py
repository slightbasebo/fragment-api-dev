from fragment_api import FragmentAPI


api = FragmentAPI()
for product, amount in [("stars", 50), ("premium", 3)]:
    quote = api.get_price(product, amount)
    print(product, amount, quote.prices.gram, "GRAM", quote.prices.usdt, "USDT", "stale:", quote.stale)
