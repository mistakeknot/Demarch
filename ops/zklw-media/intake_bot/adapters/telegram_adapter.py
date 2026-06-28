"""Telegram adapter — a `/request` command + plain messages to the bot.

Lazy-imports python-telegram-bot (v21+, asyncio-native).
"""

from __future__ import annotations

import logging

from ..config import Config
from ..models import Channel, Request
from ..pipeline import handle

log = logging.getLogger("intake_bot.telegram")


async def run(cfg: Config) -> None:
    from telegram import Update  # lazy
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    app = ApplicationBuilder().token(cfg.telegram_bot_token).build()

    async def _process(update: "Update", text: str) -> None:
        chat = update.effective_chat
        user = update.effective_user

        async def reply(msg: str) -> None:
            await app.bot.send_message(chat_id=chat.id, text=msg)

        req = Request(
            channel=Channel.TELEGRAM,
            user=str(user.id) if user else str(chat.id),
            text=text,
            reply=reply,
        )
        await handle(req, cfg)

    async def request_cmd(update: "Update", ctx: "ContextTypes.DEFAULT_TYPE") -> None:
        text = " ".join(ctx.args) if ctx.args else ""
        if not text:
            await update.message.reply_text(
                "Usage: /request <title> — e.g. /request Dune Part Two 2024"
            )
            return
        await _process(update, text)

    async def free_text(update: "Update", ctx: "ContextTypes.DEFAULT_TYPE") -> None:
        if update.message and update.message.text:
            await _process(update, update.message.text)

    app.add_handler(CommandHandler("request", request_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text))

    log.info("starting telegram adapter")
    # run_polling manages its own loop; use the lower-level async API so we can
    # coexist with the other adapters under one asyncio.gather.
    async with app:
        await app.start()
        await app.updater.start_polling()
        # Park here until cancelled by the entrypoint's task group.
        import asyncio

        await asyncio.Event().wait()
