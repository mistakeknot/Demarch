# intake_bot — the request routing brain

The front door for "I want this movie." Three channels in, one resolver, Seerr
out. This is the piece that makes the whole thing feel effortless: someone types
a title in Discord (or Telegram, or emails it), and it shows up in Jellyfin.

```
Discord /request ─┐
Telegram message ─┼─▶ resolver ─▶ Seerr POST /api/v1/request ─▶ Radarr ─▶ Jellyfin
email to inbox  ──┘   (TMDB fast-path,        (dedup, quota,
                       Haiku ranker on         permissions)
                       ambiguous text)
```

## What it does (and deliberately doesn't)

- **Decides WHAT to request.** Parses natural language, finds the right TMDB
  title, sends it to Seerr. That's the value it adds — Seerr/Radarr have no
  multi-channel natural-language front door.
- **Does NOT decide which release to grab.** Radarr still scores indexers and
  picks the best release. The bot is a router, not a downloader.
- **Two-tier, cost-controlled.** Clear requests ("add Dune Part Two 2024") are
  resolved by a deterministic TMDB lookup — **zero LLM cost**. Only vague text
  ("that movie with the spinning top") hits Claude Haiku, and only as a
  **ranker over a fixed candidate list** (no tool loops, can't hallucinate a
  tmdbId). With `ANTHROPIC_API_KEY` unset, it runs fast-path-only and asks the
  user to disambiguate manually.

## Layout

| File | Role |
|---|---|
| `models.py` | shared dataclasses (`Request`/`Candidate`/`Resolution`/`Reply`) |
| `config.py` | env → `Config`; fails fast on missing core secrets |
| `tmdb.py` | stdlib TMDB multi-search → candidates |
| `resolver.py` | the two-tier brain (fast-path + Haiku ranker) |
| `dispatch.py` | Seerr `POST /api/v1/request` + reply text |
| `pipeline.py` | allow-list → resolve → dispatch → reply (shared by all adapters) |
| `adapters/` | `discord_adapter`, `telegram_adapter`, `email_adapter` |
| `__main__.py` | loads config, gathers enabled adapters, supervises them |

The core (`models`/`config`/`tmdb`/`resolver`/`dispatch`/`pipeline`) is **stdlib
only**. Channel + LLM deps (`discord.py`, `python-telegram-bot`, `imap-tools`,
`anthropic`) are imported lazily inside the adapter/resolver that needs them, so
the package byte-compiles and the resolver/dispatch logic unit-tests on a bare
Python install.

## Secrets

Never in config or git. The container runs itself under `op run` (see the
`Dockerfile` ENTRYPOINT): the only thing on disk is the 1Password
service-account token, mounted read-only as a docker secret (`op_token`,
root-600 at `/etc/zklw-media/op-token` on the host). `bot.env.tpl` holds
`op://` references that resolve into the process **in memory only**. Full setup:
`../agent/secrets-1password.md`.

> A tracker RSS URL contains a passkey — but the bot never touches RSS or
> tracker creds; it only needs Seerr/TMDB/Anthropic keys + channel tokens.

## Run it

**Under Docker (the normal path), as part of the stack:**
```bash
# one-time: create the OP token secret (see secrets-1password.md step 3)
sudo install -m 600 /dev/stdin /etc/zklw-media/op-token <<< 'ops_…YOUR_TOKEN…'

# build + start just the bot (or `up -d` the whole stack)
docker compose up -d --build intake-bot
docker compose logs -f intake-bot
```

**Locally, for development:**
```bash
pip install -r intake_bot/requirements.txt
OP_SERVICE_ACCOUNT_TOKEN="$(cat /etc/zklw-media/op-token)" \
  op run --env-file=intake_bot/bot.env.tpl -- python -m intake_bot
```

Enable a channel by giving it a token in `bot.env.tpl`; leave a channel's token
blank to skip it. At least one channel must be enabled or startup fails fast.

## Allow-lists

Per channel, `*_ALLOWED_*` is a comma-separated list of channel-native IDs
(Discord/Telegram numeric user IDs; email addresses). Blank = open channel, and
Seerr's own per-user quotas/permissions are the backstop downstream.

## Scarcity nudge

Per the zklw scarcity doctrine (only host what you *can't* buy/stream), a
confidently-resolved request is checked against TMDB watch-providers before it
queues. If the title is buyable/rentable on a `NUDGE_PROVIDERS` storefront in
`WATCH_REGION`, the reply prepends a soft nudge ("available to buy or rent on
Apple TV or YouTube — consider watching it there") and **still queues the
download** — it's a nudge, not a gate, so preservation-grade copies of
rentable-only titles are still possible.

- `NUDGE_PROVIDERS` — comma-separated provider names. **Unset ⇒ `Apple TV,YouTube`.**
  Set it *empty* (`NUDGE_PROVIDERS=`) to disable the nudge entirely.
- `WATCH_REGION` — TMDB region code for provider availability (default `US`).
- Matching is casefolded + substring, so `Apple TV` also catches TMDB's legacy
  `Apple iTunes` and `YouTube` catches `YouTube (Movies)`.
- Best-effort: a TMDB provider-lookup failure degrades silently to the normal
  download flow — it never blocks a request.

## Tests

The resolver heuristics, parser, and dispatch payload shape have a no-dep smoke
test path (mock TMDB + mock Seerr `_post`). To re-run the structure check and
the scarcity-nudge tests:
```bash
python3 -m py_compile intake_bot/*.py intake_bot/adapters/*.py
python3 -m unittest intake_bot.test_nudge      # from ops/zklw-media/
```

## Status / next

- [x] Core resolver + dispatch + three adapters + entrypoint (this package).
- [x] Compose `intake-bot` service (no published ports; `op_token` secret).
- [ ] **Blocked with the rest of the stack on the 20TB mount** — the bot needs a
      live Seerr to dispatch to. Build order (DESIGN.md): base stack → ratio
      firewall → RSS → **intake bot** → autobrr.
- [ ] Map channel users → Seerr `userId` so per-user quotas attribute correctly
      (today every request is attributed to the admin key).
- [ ] `pinned_indexer` is captured from the Discord `tracker:` option but not
      yet wired to the Prowlarr hard-pin flow (DESIGN.md "Hard pin").
