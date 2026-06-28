"""The shared request → resolve → dispatch → reply pipeline.

Every adapter funnels its normalized Request through `handle()`, so the
allow-list gate, resolver, dispatch, and channel reply all live in one place
and behave identically across Discord, Telegram, and email.
"""

from __future__ import annotations

import logging

from .config import Config
from .dispatch import dispatch
from .models import Channel, Request
from .resolver import resolve

log = logging.getLogger("intake_bot.pipeline")


def _allowed(req: Request, cfg: Config) -> bool:
    table = {
        Channel.DISCORD: cfg.discord_allowed,
        Channel.TELEGRAM: cfg.telegram_allowed,
        Channel.EMAIL: cfg.email_allowed,
    }
    allow = table.get(req.channel, frozenset())
    if not allow:
        return True  # open channel; Seerr's own permissions are the backstop
    return req.user in allow


async def handle(req: Request, cfg: Config) -> None:
    """Run one request end to end and reply on its originating channel."""
    if not _allowed(req, cfg):
        log.info("denied %s user=%s", req.channel.value, req.user)
        await req.reply("⛔ You're not on the allow-list for requests.")
        return

    log.info("request %s user=%s text=%r", req.channel.value, req.user, req.text)
    res = await resolve(req, cfg)
    reply = await dispatch(res, cfg)
    try:
        await req.reply(reply.text)
    except Exception:  # noqa: BLE001 — a failed reply must not kill the loop
        log.exception("failed to send reply on %s", req.channel.value)
