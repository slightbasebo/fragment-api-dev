import asyncio
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import httpx

EXAMPLES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXAMPLES / "starters" / "aiogram"))
sys.path.insert(0, str(EXAMPLES))


class StarterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 5
        self.assertIsNotNone(importlib.util.find_spec("orders"), "persistent order worker is missing")
        from mock_server import MockServer
        from orders import Config, OrderStore, run_once

        self.Config, self.OrderStore, self.run_once = Config, OrderStore, run_once
        self.temp = tempfile.TemporaryDirectory()
        self.server = MockServer(("127.0.0.1", 0), timeout_delay=0.15)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.config = Config.from_env(
            {
                "FRAGMENT_BASE_URL": f"http://127.0.0.1:{self.server.server_port}",
                "STARTER_DB": str(Path(self.temp.name) / "orders.sqlite"),
                "REQUEST_TIMEOUT": "1",
            }
        )
        self.store = OrderStore(self.config)
        from fragment_api import AsyncFragmentAPI

        self.api = AsyncFragmentAPI(self.config.base_url, timeout=self.config.timeout)

    async def asyncTearDown(self):
        await self.api.aclose()
        self.store.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def paid(self, order_id="order-1", username="@completed", reference=None):
        return self.store.confirm_paid(
            order_id,
            {"product": "stars", "username": username, "amount": 50, "payment_method": "gram"},
            payment_reference=reference or "verified-" + order_id,
        )

    async def test_paid_order_survives_restart_and_no_duplicate_delivery(self):
        self.paid()
        await self.run_once(self.store, self.api, self.config, now=100)
        remote_id = self.store.get("order-1")["purchase_id"]
        self.store.close()
        self.store = self.OrderStore(self.config)
        self.paid()
        await self.run_once(self.store, self.api, self.config, now=110)
        await self.run_once(self.store, self.api, self.config, now=120)
        self.assertEqual(self.store.get("order-1")["status"], "completed")
        self.assertEqual(self.store.get("order-1")["purchase_id"], remote_id)
        self.assertEqual(len(self.server.orders), 1)
        self.assertNotIn("seed", json.dumps(self.store.get("order-1")))

    async def test_receipt_and_order_selection_cannot_be_reused(self):
        self.paid()
        with self.assertRaises(ValueError):
            self.paid(username="@failed")
        with self.assertRaises(ValueError):
            self.paid(order_id="order-2", reference="verified-order-1")
        with self.assertRaises(ValueError):
            self.store.confirm_paid(
                "unsafe",
                {
                    "product": "stars",
                    "username": "@completed",
                    "amount": 50,
                    "payment_method": "gram",
                    "seed": "forbidden",
                },
                payment_reference="new",
            )

    async def test_shop_and_order_ids_cannot_collide_at_separator(self):
        from dataclasses import replace

        first = self.OrderStore(
            replace(self.config, shop_id="shop:part", db_path=str(Path(self.temp.name) / "first.sqlite"))
        )
        second = self.OrderStore(
            replace(self.config, shop_id="shop", db_path=str(Path(self.temp.name) / "second.sqlite"))
        )
        selection = {"product": "stars", "username": "@completed", "amount": 50, "payment_method": "gram"}
        try:
            one = first.confirm_paid("order", selection, payment_reference="verified")
            two = second.confirm_paid("part:order", selection, payment_reference="verified")
            self.assertNotEqual(one["idempotency_key"], two["idempotency_key"])
        finally:
            first.close()
            second.close()

    async def test_retry_after_starts_when_response_arrives(self):
        from unittest.mock import patch

        from fragment_api import RateLimitError

        class SlowAPI:
            async def create_purchase(self, **kwargs):
                raise RateLimitError("Synthetic", status_code=429, response={"retry_after": 9})

        self.paid()
        with patch("orders.time.time", side_effect=[100, 105]):
            await self.run_once(self.store, SlowAPI(), self.config)
        self.assertEqual(self.store.get("order-1")["next_attempt"], 114)

    async def test_timeout_after_acceptance_reuses_same_key_on_restart(self):
        self.api.timeout = 0.04
        self.paid(username="@timeout")
        await self.run_once(self.store, self.api, self.config, now=100)
        self.assertIsNone(self.store.get("order-1")["purchase_id"])
        self.store.close()
        self.store = self.OrderStore(self.config)
        await self.run_once(self.store, self.api, self.config, now=110)
        await self.run_once(self.store, self.api, self.config, now=120)
        self.assertEqual(self.store.get("order-1")["status"], "completed")
        self.assertEqual(len(self.server.orders), 1)

    async def test_rate_limit_schedules_retry_and_terminal_scenarios_stop(self):
        for scenario in ("429", "failed", "reconciliation_required"):
            self.paid(scenario, "@" + scenario)
        await self.run_once(self.store, self.api, self.config, now=100)
        self.assertGreaterEqual(self.store.get("429")["next_attempt"], 102)
        for now in (110, 120, 130):
            await self.run_once(self.store, self.api, self.config, now=now)
        self.assertEqual(self.store.get("429")["status"], "completed")
        self.assertEqual(self.store.get("failed")["status"], "failed")
        self.assertEqual(self.store.get("reconciliation_required")["status"], "reconciliation_required")
        self.assertEqual(len(self.server.orders), 3)

    async def test_claims_are_bounded_and_recover_only_after_lease_expiry(self):
        for index in range(5):
            self.paid(str(index))
        claimed = self.store.claim(2, now=100, lease_seconds=10)
        self.assertEqual(len(claimed), 2)
        second = self.OrderStore(self.config)
        try:
            others = second.claim(5, now=101, lease_seconds=10)
            self.assertEqual(len(others), 3)
            self.assertEqual(second.claim(5, now=102, lease_seconds=10), [])
            self.assertEqual(len(second.claim(5, now=111, lease_seconds=10)), 5)
        finally:
            second.close()

    async def test_worker_bounds_network_and_polls_without_posting_again(self):
        from fragment_api import AsyncFragmentAPI

        active = peak = 0

        async def handler(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return httpx.Response(
                202, json={"purchase_id": json.loads(request.content)["idempotency_key"], "status": "queued"}
            )

        for index in range(8):
            self.paid(str(index))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with AsyncFragmentAPI(http_client=http) as api:
                await self.run_once(self.store, api, self.config, now=100)
        self.assertEqual(peak, self.config.concurrency)
        self.assertEqual(
            sum(self.store.get(str(i))["purchase_id"] is not None for i in range(8)), self.config.concurrency
        )

    async def test_mock_rejects_secrets_and_conflicting_idempotency(self):
        async with httpx.AsyncClient() as http:
            body = {
                "product": "stars",
                "username": "@completed",
                "amount": 50,
                "payment_method": "gram",
                "seed": "mock-only-not-a-wallet",
                "idempotency_key": "fixed",
            }
            url = self.config.base_url + "/api/v1/purchases"
            self.assertEqual((await http.post(url, json=body)).status_code, 202)
            body["amount"] = 51
            self.assertEqual((await http.post(url, json=body)).status_code, 409)
            body["seed"] = "do-not-send-secrets"
            self.assertEqual((await http.post(url, json=body)).status_code, 400)

    async def test_mock_checkout_roundtrip(self):
        checkout = await self.api.create_checkout(
            product="stars",
            username="@completed",
            amount=50,
            payment_method="gram",
            payer_address="0:" + "0" * 64,
            idempotency_key="checkout-1",
        )
        self.assertEqual(checkout.status, "awaiting_payment")
        self.assertIsNotNone(checkout.tonconnect_transaction)
        await self.api.submit_checkout(checkout.checkout_id, boc="c3ludGhldGlj")
        result = await self.api.wait_checkout(checkout.checkout_id, poll_interval=0.01)
        self.assertTrue(result.completed)

    async def test_async_price_availability_and_wallet_helpers_use_mock(self):
        catalog = await self.api.get_prices()
        self.assertEqual([item.months for item in catalog.premium], [3, 6, 12])
        self.assertEqual((await self.api.get_stars_price(100)).amount, 100)
        self.assertEqual((await self.api.get_premium_price(3)).product, "premium")
        self.assertTrue((await self.api.check_stars_availability("@completed", 50)).available)
        self.assertTrue((await self.api.check_premium_availability("@completed", 3)).available)
        wallet = await self.api.resolve_wallet(seed="mock-only-not-a-wallet", account_index=0)
        self.assertEqual(wallet.account_index, 0)

    async def test_live_config_requires_explicit_confirmation_and_db_cannot_switch_mode(self):
        for env in [
            {"STARTER_MODE": "typo"},
            {"FRAGMENT_BASE_URL": "https://example.com"},
            {"STARTER_MODE": "live"},
        ]:
            with self.assertRaises(ValueError):
                self.Config.from_env(env)
        live = self.Config.from_env(
            {
                "STARTER_MODE": "live",
                "STARTER_LIVE_CONFIRM": "I_UNDERSTAND_REAL_PURCHASES",
                "FRAGMENT_BASE_URL": "https://example.invalid",
                "TON_WALLET_SEED": "runtime-only",
                "STARTER_SHOP_ID": "shop",
                "STARTER_DB": self.config.db_path,
            }
        )
        with self.assertRaises(ValueError):
            self.OrderStore(live)

    async def test_bot_acl_only_owner_private_chat(self):
        from types import SimpleNamespace as Obj

        from bot import authorized

        for user, chat, kind, expected in [
            (1, 1, "private", True),
            (2, 2, "private", False),
            (1, -10, "group", False),
            (None, 1, "private", False),
        ]:
            message = Obj(from_user=Obj(id=user) if user else None, chat=Obj(id=chat, type=kind))
            self.assertEqual(authorized(message, 1), expected)

    async def test_bot_handlers_reject_public_and_live_demo_orders(self):
        from dataclasses import replace
        from unittest.mock import AsyncMock, patch

        from aiogram import Bot, Dispatcher
        from aiogram.types import Update
        from bot import make_router

        dispatcher = Dispatcher()
        dispatcher.include_router(make_router(self.store, self.config, 1))
        bot = Bot("123456:synthetic-test-token")

        def update(user, chat, kind, order_id):
            return Update.model_validate(
                {
                    "update_id": 1,
                    "message": {
                        "message_id": 1,
                        "date": 0,
                        "from": {"id": user, "is_bot": False, "first_name": "Synthetic"},
                        "chat": {"id": chat, "type": kind},
                        "text": f"/demo {order_id} completed",
                    },
                }
            )

        try:
            with patch.object(bot.session, "make_request", new=AsyncMock()):
                await dispatcher.feed_update(bot, update(2, 2, "private", "stranger"))
                await dispatcher.feed_update(bot, update(1, -1, "group", "group"))
                self.assertIsNone(self.store.get("stranger"))
                self.assertIsNone(self.store.get("group"))
                await dispatcher.feed_update(bot, update(1, 1, "private", "owner"))
                self.assertEqual(self.store.get("owner")["status"], "pending")
                live = Dispatcher()
                live.include_router(make_router(self.store, replace(self.config, mode="live"), 1))
                await live.feed_update(bot, update(1, 1, "private", "live"))
                self.assertIsNone(self.store.get("live"))
        finally:
            await bot.session.close()

    async def test_cancellation_leaves_claim_recoverable_without_resubmitting(self):
        from fragment_api import AsyncFragmentAPI

        entered = asyncio.Event()
        calls = 0

        async def handler(request):
            nonlocal calls
            calls += 1
            entered.set()
            await asyncio.Event().wait()

        self.paid()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with AsyncFragmentAPI(http_client=http) as api:
                task = asyncio.create_task(self.run_once(self.store, api, self.config, now=100))
                await entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
        self.assertEqual(calls, 1)
        self.assertEqual(self.store.get("order-1")["failures"], 0)
        self.assertEqual(self.store.claim(1, now=101, lease_seconds=10), [])
        self.assertEqual(len(self.store.claim(1, now=110, lease_seconds=10)), 1)

    async def test_retry_budget_requires_review_and_stale_worker_cannot_write(self):
        from fragment_api import AsyncFragmentAPI

        self.paid()
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, json={"error": "private-server-message"})
            )
        ) as http:
            async with AsyncFragmentAPI(http_client=http) as api:
                for now in (100, 200, 300, 400, 500):
                    await self.run_once(self.store, api, self.config, now=now)
        self.assertEqual(self.store.get("order-1")["status"], "review_required")
        self.assertNotIn("private-server-message", json.dumps(self.store.get("order-1")))
        self.paid("order-2")
        old = self.store.claim(1, now=600, lease_seconds=10)[0]
        new = self.store.claim(1, now=611, lease_seconds=10)[0]
        self.store.finish(new, status="completed", purchase_id="new", failures=0, next_attempt=0)
        self.store.finish(old, status="failed", purchase_id="old", failures=1, next_attempt=0)
        self.assertEqual(self.store.get("order-2")["status"], "completed")
