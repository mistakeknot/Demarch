# Secrets via 1Password at runtime

Goal: tracker passkeys, RSS URLs, IRC creds, and API keys never sit in
plaintext config or git. Services pull them from 1Password at start using the
`op` CLI with a **service-account token**. You authenticate once; the agent
(and these notes) never see the secret values.

## One-time setup on zklw

1. Install the 1Password CLI (`op`):
   ```bash
   # https://developer.1password.com/docs/cli/get-started/
   ARCH=$(dpkg --print-architecture)
   curl -sSfo op.zip "https://cache.agilebits.com/dist/1P/op2/pkg/v2/op_linux_${ARCH}_latest.zip"
   sudo unzip -o op.zip op -d /usr/local/bin/ && rm op.zip
   op --version
   ```

2. Create a **1Password Service Account** (in your 1Password account:
   Developer → Service Accounts) scoped to ONLY a "zklw-media" vault. Copy the
   token once.

3. Put the token where systemd/Docker can read it, root-only:
   ```bash
   sudo install -m 600 /dev/stdin /etc/zklw-media/op-token <<< 'ops_…YOUR_TOKEN…'
   ```

## Vault layout (you create these items in the "zklw-media" vault)

One item per service/tracker, with fields referenced by `op://` URIs:

```
op://zklw-media/radarr/api_key
op://zklw-media/sonarr/api_key
op://zklw-media/seerr/api_key
op://zklw-media/jellyfin/api_key
op://zklw-media/qbittorrent/password
op://zklw-media/anthropic/api_key          # for the LLM disambiguation layer
op://zklw-media/discord/bot_token
op://zklw-media/telegram/bot_token
op://zklw-media/email/imap_password
# trackers — passkeys / RSS / IRC
op://zklw-media/hdbits/passkey
op://zklw-media/hdbits/rss_url             # personal RSS (contains passkey!)
op://zklw-media/hdbits/irc_key             # for autobrr (opt-in)
op://zklw-media/torrentleech/rss_url
op://zklw-media/karagarga/passkey
op://zklw-media/audionews/passkey
```

## How services consume them

**Pattern A — `op run` injects env at launch (best for the bot):**
Write a template env file with `op://` references (safe to commit — no secrets):
```
# bot.env.tpl  — committed; values are RESOLVED at runtime, not stored
ANTHROPIC_API_KEY=op://zklw-media/anthropic/api_key
DISCORD_BOT_TOKEN=op://zklw-media/discord/bot_token
TELEGRAM_BOT_TOKEN=op://zklw-media/telegram/bot_token
RADARR_API_KEY=op://zklw-media/radarr/api_key
SEERR_API_KEY=op://zklw-media/seerr/api_key
```
Launch with the service-account token in the environment:
```bash
OP_SERVICE_ACCOUNT_TOKEN="$(cat /etc/zklw-media/op-token)" \
  op run --env-file=bot.env.tpl -- python -m intake_bot
```
`op run` resolves every `op://` ref into a real env var **only inside the child
process** — they're never written to disk.

**Pattern B — one-shot materialization for tools that need a real file**
(e.g. cross-seed/autobrr configs that want literal values). Render at boot into
a tmpfs (RAM, never hits disk), used, then gone:
```bash
OP_SERVICE_ACCOUNT_TOKEN="$(cat /etc/zklw-media/op-token)" \
  op inject -i autobrr.toml.tpl -o /run/zklw-media/autobrr.toml   # /run = tmpfs
```

**Pattern C — the mediactl agent** reads keys the same way: instead of a static
`~/.config/zklw-media/agent.env`, launch it under `op run` so the agent's API
keys are resolved fresh each invocation and never stored.

## Why this shape

- The **service-account token** is the only persistent secret on disk, root-600,
  and it's revocable/rotatable in one click without touching any service.
- Everything else is referenced by `op://` path in committable templates, so the
  repo documents *what* secrets exist without ever containing them.
- `op run`/`op inject` keep resolved values in process memory or tmpfs, not in
  the filesystem or git.

> Reminder: a tracker's **RSS URL contains your passkey** — treat it as a
> secret. Leaking it (or a `.torrent` file) leaks your passkey, which can get
> your account banned for "sharing."
