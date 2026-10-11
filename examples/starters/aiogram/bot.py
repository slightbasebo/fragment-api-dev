"""Owner-only aiogram 3 bot. Telegram never accepts wallet seeds or paid proofs."""

import asyncio
import os
from contextlib import suppress

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from fragment_api import AsyncFragmentAPI
from orders import Config, OrderStore, worker

SCENARIOS = {"completed", "failed", "429", "timeout", "reconciliation_required"}


def authorized(message, owner_id):
    return bool(
        message.from_user
        and message.from_user.id == owner_id
        and message.chat.type == "private"
        and message.chat.id == owner_id
    )


def make_router(store, config, owner_id):
    router = Router()

    @router.message(Command("start"))
    async def start(message: Message):
        if authorized(message, owner_id):
            await message.answer(
                "Owner console. /status ORDER_ID. Mock only: /demo ORDER_ID completed|failed|429|timeout|reconciliation_required. Never send seeds here."
            )

    @router.message(Command("demo"))
    async def demo(message: Message):
        if not authorized(message, owner_id):
            return
        if config.mode != "mock":
            await message.answer(
                "Demo creation is disabled in live mode. Only verified backend paid orders enter the queue."
            )
            return
        parts = (message.text or "").split()
        if len(parts) != 3 or parts[2] not in SCENARIOS:
            await message.answer("Use /demo ORDER_ID SCENARIO. Reuse the same ID when retrying.")
            return
        try:
            row = store.confirm_paid(
                parts[1],
                {"product": "stars", "username": "@" + parts[2], "amount": 50, "payment_method": "gram"},
                payment_reference="mock:" + parts[1],
            )
        except ValueError:
            await message.answer("Invalid or conflicting order. Keep the original ID and selection.")
            return
        await message.answer(f"Mock order {row['order_id']}: {row['status']}. Use /status {row['order_id']}.")

    @router.message(Command("status"))
    async def status(message: Message):
        if not authorized(message, owner_id):
            return
        parts = (message.text or "").split()
        row = store.get(parts[1]) if len(parts) == 2 else None
        await message.answer(
            f"{row['order_id']}: {row['status']}" if row else "Order not found. Use /status ORDER_ID."
        )

    return router


async def main():
    config = Config.from_env()
    owner_id = int(os.environ["BOT_OWNER_ID"])
    if owner_id <= 0:
        raise ValueError("BOT_OWNER_ID must be a positive Telegram user ID")
    store = OrderStore(config)
    try:
        async with (
            AsyncFragmentAPI(config.base_url, timeout=config.timeout) as api,
            Bot(os.environ["BOT_TOKEN"]).context() as bot,
        ):
            dispatcher = Dispatcher()
            dispatcher.include_router(make_router(store, config, owner_id))
            background = asyncio.create_task(worker(store, api, config))
            polling = asyncio.create_task(
                dispatcher.start_polling(bot, handle_as_tasks=False, close_bot_session=False)
            )
            try:
                done, _ = await asyncio.wait((background, polling), return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            finally:
                for task in (background, polling):
                    task.cancel()
                for task in (background, polling):
                    with suppress(asyncio.CancelledError):
                        await task
    finally:
        store.close()


if __name__ == "__main__":
    asyncio.run(main())
