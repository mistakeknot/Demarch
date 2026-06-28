"""zklw intake bot — the routing brain in front of Radarr/Seerr.

Three channel adapters (Discord, Telegram, email) normalize incoming requests
into a single shape, hand them to a two-tier resolver (deterministic TMDB
fast-path; Claude Haiku ranker only for ambiguous text), and dispatch the
winner through Seerr's request API (which owns dedup, quotas, and permissions).

The bot decides WHAT to ask Radarr for. Radarr still decides WHICH release to
grab. This package is deliberately thin: it adds the multi-channel + natural-
language front door that Seerr/Radarr don't have, and nothing more.

Heavy third-party deps (discord.py, python-telegram-bot, imap-tools, anthropic)
are imported lazily inside the adapter/resolver that needs them, so the core
modules import and structure-check on a bare Python install.
"""

__all__ = ["models", "resolver", "dispatch", "config"]
