# Intake bot environment template — SAFE TO COMMIT.
#
# Values are `op://` references; they are resolved into real env vars IN MEMORY
# at launch by `op run --env-file=bot.env.tpl -- python -m intake_bot`. No
# secret is ever written to disk. See agent/secrets-1password.md.
#
# Anything WITHOUT an op:// value below is a plain, non-secret setting — edit
# it directly.

# --- downstream services (tailnet-internal; not secret hosts) -------------
SEERR_URL=http://seerr:5055
SEERR_API_KEY=op://zklw-media/seerr/api_key
TMDB_API_KEY=op://zklw-media/tmdb/api_key

# --- LLM disambiguation (optional — omit to run fast-path-only) -----------
ANTHROPIC_API_KEY=op://zklw-media/anthropic/api_key
LLM_MODEL=claude-haiku-4-5-20251001

# --- channels (enable a channel by giving it a token; leave blank to skip) -
DISCORD_BOT_TOKEN=op://zklw-media/discord/bot_token
TELEGRAM_BOT_TOKEN=op://zklw-media/telegram/bot_token
EMAIL_IMAP_HOST=
EMAIL_IMAP_USER=
EMAIL_IMAP_PASSWORD=op://zklw-media/email/imap_password
EMAIL_SMTP_HOST=
EMAIL_FROM=

# --- allow-lists (comma-separated channel-native ids; blank = open) -------
# Discord: numeric user IDs. Telegram: numeric user IDs. Email: full addresses.
# When blank, the channel is open and Seerr's own per-user quotas/permissions
# are the backstop.
DISCORD_ALLOWED_USERS=
TELEGRAM_ALLOWED_USERS=
EMAIL_ALLOWED_SENDERS=

# --- scarcity nudge (zklw doctrine: only host what you can't buy/stream) ---
# Before queuing a request, check TMDB watch-providers; if the title is
# buyable/rentable on any of these providers in WATCH_REGION, the reply nudges
# the requester to watch it there (soft nudge — the download still queues).
# Matching is casefolded + substring, so "Apple TV" also catches the legacy
# "Apple iTunes" storefront and "YouTube" catches "YouTube (Movies)".
# UNSET => default "Apple TV,YouTube". Set NUDGE_PROVIDERS= (empty) to DISABLE.
NUDGE_PROVIDERS=Apple TV,YouTube
WATCH_REGION=US
