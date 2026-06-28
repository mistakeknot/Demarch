"""Entrypoint: `python -m intake_bot`.

Loads config from the environment (already resolved by `op run`), then launches
one asyncio task per enabled channel adapter and supervises them together. If
any adapter crashes, it's logged and the others keep running.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from . import config as config_mod
from .adapters import discord_adapter, email_adapter, telegram_adapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("intake_bot")


async def _supervise(name: str, coro) -> None:
    """Run an adapter; log and swallow its failure so siblings survive."""
    try:
        await coro
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        log.exception("adapter %s crashed", name)


async def main() -> None:
    cfg = config_mod.load()

    tasks: list[asyncio.Task] = []
    if cfg.discord_enabled:
        tasks.append(
            asyncio.create_task(_supervise("discord", discord_adapter.run(cfg)))
        )
    if cfg.telegram_enabled:
        tasks.append(
            asyncio.create_task(_supervise("telegram", telegram_adapter.run(cfg)))
        )
    if cfg.email_enabled:
        tasks.append(asyncio.create_task(_supervise("email", email_adapter.run(cfg))))

    log.info(
        "intake bot up: %d channel(s) — LLM ranker %s",
        len(tasks),
        "on" if cfg.llm_enabled else "off (fast-path only)",
    )

    # Clean shutdown on SIGTERM (docker stop) / SIGINT.
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass  # e.g. on platforms without signal handlers

    await stop.wait()
    log.info("shutting down")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except config_mod.ConfigError as e:
        log.error("config error: %s", e)
        raise SystemExit(2)
