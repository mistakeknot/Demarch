"""The shared request → resolve → dispatch → reply pipeline.

Every adapter funnels its normalized Request through `handle()`, so the
allow-list gate, resolver, dispatch, and channel reply all live in one place
and behave identically across Discord, Telegram, and email.
"""

from __future__ import annotations

import logging

from . import tmdb
from .config import Config
from .dispatch import dispatch
from .models import Channel, Request, Resolution

log = logging.getLogger("intake_bot.pipeline")


def _human_join(items: list[str]) -> str:
    """['Apple TV'] -> 'Apple TV'; ['Apple TV','YouTube'] -> 'Apple TV or YouTube'."""
    if len(items) <= 1:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} or {items[-1]}"


def _scarcity_nudge(res: Resolution, cfg: Config) -> str:
    """If the resolved title is purchasable on a nudge provider, return a soft
    nudge line to prepend to the reply; else "". Best-effort — never raises,
    never blocks dispatch (the scarcity doctrine is a nudge, not a gate)."""
    if not cfg.nudge_enabled or res.candidate is None:
        return ""
    c = res.candidate
    try:
        hits = tmdb.purchasable_on(
            c.tmdb_id,
            c.media_type.value,
            cfg.tmdb_api_key,
            region=cfg.watch_region,
            providers=cfg.nudge_providers,
        )
    except Exception:  # noqa: BLE001 — enrichment must never break the flow
        log.debug("nudge lookup failed for tmdb_id=%s", c.tmdb_id, exc_info=True)
        return ""
    if not hits:
        return ""
    where = _human_join(sorted(hits))
    return (
        f"🛒 **{c.label()}** is available to buy or rent on {where} — "
        f"consider watching it there. (Still queuing it below.)\n\n"
    )


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
    # Scarcity nudge: only computed for a confidently-resolved title (an
    # ambiguous/failed resolution has no single candidate to check), and only
    # prepended to a successful dispatch so we never nudge on an error reply.
    nudge = _scarcity_nudge(res, cfg) if res.resolved else ""
    reply = await dispatch(res, cfg)
    text = nudge + reply.text if (nudge and reply.ok) else reply.text
    try:
        await req.reply(text)
    except Exception:  # noqa: BLE001 — a failed reply must not kill the loop
        log.exception("failed to send reply on %s", req.channel.value)
