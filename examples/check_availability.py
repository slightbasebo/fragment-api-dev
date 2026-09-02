import os

from fragment_api import FragmentAPI, RateLimitError, ServiceUnavailableError


api = FragmentAPI(base_url=os.getenv("FRAGMENT_API_URL", "https://api-stars.duckdns.org"))

try:
    check = api.check_stars_availability(
        os.getenv("TELEGRAM_USERNAME", "@telegram_user"),
        int(os.getenv("AMOUNT", "100")),
        os.getenv("PAYMENT_METHOD", "gram"),
    )
except RateLimitError as error:
    print(f"Retry after {error.retry_after} seconds")
except ServiceUnavailableError:
    print("Check again later. Do not accept payment yet.")
else:
    if check.available:
        print("Available. You can continue to payment.")
    else:
        print(check.message)
        print(check.action)
