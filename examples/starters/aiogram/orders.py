"""Small paid-order queue. Only a trusted backend may call confirm_paid()."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from fragment_api import AsyncFragmentAPI, FragmentAPIError

MOCK_SEED = "mock-only-not-a-wallet"


@dataclass(frozen=True)
class Config:
    mode: str
    base_url: str
    db_path: str
    shop_id: str
    seed: str = field(repr=False)
    account_index: int | None = None
    wallet_address: str | None = None
    concurrency: int = 3
    timeout: float = 5.0

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        mode = env.get("STARTER_MODE", "mock")
        base_url = env.get("FRAGMENT_BASE_URL", "http://127.0.0.1:8081").rstrip("/")
        url = urlsplit(base_url)
        if (
            mode not in {"mock", "live"}
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path
        ):
            raise ValueError("Use mock/live mode and a bare API origin")
        if mode == "mock" and (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}):
            raise ValueError("Mock mode only permits loopback HTTP")
        if mode == "live" and (
            url.scheme != "https"
            or not url.hostname
            or not env.get("FRAGMENT_BASE_URL")
            or env.get("STARTER_LIVE_CONFIRM") != "I_UNDERSTAND_REAL_PURCHASES"
            or not env.get("TON_WALLET_SEED", "").strip()
            or not env.get("STARTER_SHOP_ID", "").strip()
        ):
            raise ValueError(
                "Live mode requires explicit HTTPS origin, confirmation, shop ID, and backend wallet seed"
            )
        concurrency = int(env.get("WORKER_CONCURRENCY", "3"))
        timeout = float(env.get("REQUEST_TIMEOUT", "5"))
        if not 1 <= concurrency <= 16 or not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("Concurrency must be 1-16; timeout must be positive and at most 60 seconds")
        index = int(env["TON_ACCOUNT_INDEX"]) if mode == "live" and env.get("TON_ACCOUNT_INDEX") else None
        if index is not None and not 0 <= index <= 100:
            raise ValueError("TON_ACCOUNT_INDEX must be 0-100")
        return cls(
            mode,
            base_url,
            env.get("STARTER_DB", f"orders-{mode}.sqlite"),
            env.get("STARTER_SHOP_ID", "demo"),
            env["TON_WALLET_SEED"] if mode == "live" else MOCK_SEED,
            index,
            env.get("TON_WALLET_ADDRESS") if mode == "live" else None,
            concurrency,
            timeout,
        )


def validate_selection(selection):
    if not isinstance(selection, dict) or set(selection) != {
        "product",
        "username",
        "amount",
        "payment_method",
    }:
        raise ValueError("Only product, username, amount, payment_method are accepted")
    product, amount, username = selection["product"], selection["amount"], selection["username"]
    if (
        product not in ("stars", "premium")
        or type(amount) is not int
        or (product == "stars" and not 50 <= amount <= 1_000_000)
        or (product == "premium" and amount not in (3, 6, 12))
        or not isinstance(username, str)
        or not re.fullmatch(r"@[A-Za-z0-9_]{1,32}", username)
        or selection["payment_method"] not in ("gram", "usdt")
    ):
        raise ValueError("Invalid order selection")
    return json.dumps(selection, sort_keys=True, separators=(",", ":"))


class OrderStore:
    def __init__(self, config: Config):
        self.config = config
        self.db = sqlite3.connect(config.db_path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS context (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY, selection TEXT NOT NULL, payment_reference TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE, purchase_id TEXT, status TEXT NOT NULL DEFAULT 'pending',
                failures INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
                lease_until REAL NOT NULL DEFAULT 0, lease_token TEXT, last_error TEXT
            );
        """)
        context = json.dumps([config.mode, config.base_url, config.shop_id])
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO context VALUES (1, ?)", (context,))
        if self.db.execute("SELECT value FROM context WHERE id=1").fetchone()[0] != context:
            self.db.close()
            raise ValueError("Database belongs to another mode, API origin, or shop; use a separate DB")

    def close(self):
        self.db.close()

    def confirm_paid(self, order_id, selection, *, payment_reference):
        """Call only after verifying provider signature, amount, currency, and final paid state."""
        for value in (order_id, payment_reference):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
                raise ValueError("Stable order ID and verified payment reference are required")
        payload = validate_selection(selection)
        identity = json.dumps([self.config.shop_id, order_id], ensure_ascii=False, separators=(",", ":"))
        key = "starter-" + hashlib.sha256(identity.encode()).hexdigest()
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO orders (order_id, selection, payment_reference, idempotency_key) VALUES (?, ?, ?, ?) ON CONFLICT(order_id) DO NOTHING",
                    (order_id, payload, payment_reference, key),
                )
                row = self.get(order_id)
                if row["selection"] != payload or row["payment_reference"] != payment_reference:
                    raise ValueError("Order ID already belongs to another selection or payment")
        except sqlite3.IntegrityError:
            raise ValueError("Payment reference already belongs to another order") from None
        return row

    def get(self, order_id):
        row = self.db.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        return dict(row) if row else None

    def claim(self, limit, *, now, lease_seconds):
        token = str(uuid.uuid4())
        with self.db:
            rows = self.db.execute(
                """
                UPDATE orders SET lease_until=?, lease_token=? WHERE order_id IN (
                    SELECT order_id FROM orders WHERE status NOT IN ('completed','failed','reconciliation_required','review_required')
                    AND next_attempt <= ? AND lease_until <= ? ORDER BY next_attempt, order_id LIMIT ?
                ) RETURNING *
            """,
                (now + lease_seconds, token, now, now, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def finish(self, row, *, status, purchase_id, failures, next_attempt, error=None):
        with self.db:
            self.db.execute(
                """UPDATE orders SET status=?, purchase_id=?, failures=?, next_attempt=?,
                last_error=?, lease_until=0, lease_token=NULL WHERE order_id=? AND lease_token=?""",
                (status, purchase_id, failures, next_attempt, error, row["order_id"], row["lease_token"]),
            )


async def run_once(store: OrderStore, api: AsyncFragmentAPI, config: Config, *, now=None):
    def current_time():
        return time.time() if now is None else now

    rows = store.claim(config.concurrency, now=current_time(), lease_seconds=config.timeout + 5)

    async def process(row):
        try:
            if row["purchase_id"]:
                result = await api.get_purchase(row["purchase_id"])
            else:
                result = await api.create_purchase(
                    **json.loads(row["selection"]),
                    seed=config.seed,
                    idempotency_key=row["idempotency_key"],
                    account_index=config.account_index,
                    wallet_address=config.wallet_address,
                )
            store.finish(
                row,
                status=result.status,
                purchase_id=result.purchase_id,
                failures=0,
                next_attempt=current_time() + 2,
            )
        except FragmentAPIError as error:
            failures = row["failures"] + 1
            retryable = error.status_code is None or error.status_code in {429, 500, 502, 503, 504}
            status = row["status"] if retryable and failures < 5 else "review_required"
            store.finish(
                row,
                status=status,
                purchase_id=row["purchase_id"],
                failures=failures,
                next_attempt=current_time() + max(error.retry_after or 0, min(2**failures, 60)),
                error=type(error).__name__,
            )  # Never persist server messages or request material.

    results = await asyncio.gather(*(process(row) for row in rows), return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            raise result


async def worker(store, api, config):
    while True:
        await run_once(store, api, config)
        await asyncio.sleep(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backend worker; demo orders are mock-only")
    parser.add_argument("command", choices=("demo", "status", "worker"))
    parser.add_argument("order_id", nargs="?")
    parser.add_argument(
        "scenario",
        nargs="?",
        default="completed",
        choices=("completed", "failed", "429", "timeout", "reconciliation_required"),
    )
    args = parser.parse_args()
    config = Config.from_env()
    store = OrderStore(config)
    try:
        if args.command == "demo":
            if config.mode != "mock":
                parser.error("Demo creation is disabled in live mode")
            row = store.confirm_paid(
                args.order_id,
                {"product": "stars", "username": "@" + args.scenario, "amount": 50, "payment_method": "gram"},
                payment_reference="mock:" + (args.order_id or ""),
            )
            print(f"{row['order_id']}: {row['status']}")
        elif args.command == "status":
            row = store.get(args.order_id)
            print(f"{row['order_id']}: {row['status']}" if row else "Order not found")
        else:

            async def main():
                async with AsyncFragmentAPI(config.base_url, timeout=config.timeout) as api:
                    await worker(store, api, config)

            asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        store.close()
