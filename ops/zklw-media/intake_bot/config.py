"""Configuration, loaded from the process environment.

The bot is launched under `op run --env-file=bot.env.tpl` (see
agent/secrets-1password.md), so by the time this module reads os.environ every
`op://` reference has already been resolved into a real value IN MEMORY ONLY.
This module therefore just reads plain env vars — it never touches 1Password
itself, never writes secrets to disk, and never logs their values.

Nothing here has a secret default. A missing required secret raises at startup
(fail fast) rather than silently running half-configured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when a required setting is absent — surfaced at startup."""


def _req(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise ConfigError(
            f"missing required env var {name}. Launch under "
            f"`op run --env-file=bot.env.tpl` so 1Password resolves it."
        )
    return val


def _opt(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    # --- downstream services (tailnet-internal URLs) -------------------
    seerr_url: str
    seerr_api_key: str
    tmdb_api_key: str

    # --- LLM disambiguation (optional; bot degrades to fast-path only) --
    anthropic_api_key: str
    llm_model: str

    # --- channels (each optional; only enabled adapters need creds) -----
    discord_bot_token: str
    telegram_bot_token: str
    email_imap_host: str
    email_imap_user: str
    email_imap_password: str
    email_smtp_host: str
    email_from: str

    # --- behavior -------------------------------------------------------
    # Whitelist of who may request, per channel. Empty => open (rely on
    # Seerr's own per-user quotas/permissions downstream).
    discord_allowed: frozenset[str]
    telegram_allowed: frozenset[str]
    email_allowed: frozenset[str]

    # --- scarcity nudge -------------------------------------------------
    # Per the zklw scarcity doctrine: only host what you CAN'T buy/stream.
    # Before dispatching, check whether the title is purchasable on these
    # providers in `watch_region`; if so, nudge the requester there. Empty
    # set disables the nudge entirely.
    nudge_providers: frozenset[str]
    watch_region: str

    @property
    def nudge_enabled(self) -> bool:
        return bool(self.nudge_providers)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_bot_token)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def email_enabled(self) -> bool:
        return bool(self.email_imap_host and self.email_imap_user)


def _csv_set(name: str) -> frozenset[str]:
    raw = os.environ.get(name, "")
    return frozenset(p.strip() for p in raw.split(",") if p.strip())


def _csv_set_default(name: str, default: str) -> frozenset[str]:
    """Like _csv_set but uses `default` when the var is UNSET. An explicitly
    empty string ("") still yields the empty set, so the feature can be turned
    off without editing the default — set-but-empty means "off", not "default"."""
    raw = os.environ.get(name)
    if raw is None:
        raw = default
    return frozenset(p.strip() for p in raw.split(",") if p.strip())


def load() -> Config:
    """Build Config from the environment. Raises ConfigError on missing core."""
    cfg = Config(
        # Seerr + TMDB are the irreducible core — without them there is no
        # resolve+dispatch path, so they are required.
        seerr_url=_req("SEERR_URL"),
        seerr_api_key=_req("SEERR_API_KEY"),
        tmdb_api_key=_req("TMDB_API_KEY"),
        anthropic_api_key=_opt("ANTHROPIC_API_KEY"),
        llm_model=_opt("LLM_MODEL", "claude-haiku-4-5-20251001"),
        discord_bot_token=_opt("DISCORD_BOT_TOKEN"),
        telegram_bot_token=_opt("TELEGRAM_BOT_TOKEN"),
        email_imap_host=_opt("EMAIL_IMAP_HOST"),
        email_imap_user=_opt("EMAIL_IMAP_USER"),
        email_imap_password=_opt("EMAIL_IMAP_PASSWORD"),
        email_smtp_host=_opt("EMAIL_SMTP_HOST"),
        email_from=_opt("EMAIL_FROM"),
        discord_allowed=_csv_set("DISCORD_ALLOWED_USERS"),
        telegram_allowed=_csv_set("TELEGRAM_ALLOWED_USERS"),
        email_allowed=_csv_set("EMAIL_ALLOWED_SENDERS"),
        # Default ON with Apple TV + YouTube per the scarcity doctrine; set
        # NUDGE_PROVIDERS="" to disable, or override the list/region.
        nudge_providers=_csv_set_default("NUDGE_PROVIDERS", "Apple TV,YouTube"),
        watch_region=_opt("WATCH_REGION", "US"),
    )
    if not (cfg.discord_enabled or cfg.telegram_enabled or cfg.email_enabled):
        raise ConfigError(
            "no channel enabled — set at least one of DISCORD_BOT_TOKEN, "
            "TELEGRAM_BOT_TOKEN, or EMAIL_IMAP_HOST/EMAIL_IMAP_USER."
        )
    return cfg
