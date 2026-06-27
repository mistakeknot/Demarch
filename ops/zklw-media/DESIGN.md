# zklw media server — full design (intake routing + ratio engine)

This extends the base Jellyfin/*arr stack (see `README.md`) with the two
systems you actually asked for:

1. **Multi-channel request intake** — Discord + Telegram + email → an agent
   that parses, disambiguates, and dispatches to the *arr stack.
2. **A ratio engine** — use zklw's bandwidth to build ratio across your
   trackers (HDBits, Karagarga, TorrentLeech, AudioNews) and climb toward
   elite trackers, *within the rules*.

> ⚠️ Everything here is rules-compliant by design. The "tripwires" sections
> are the firewall the automation must respect — breaking them gets accounts
> **banned**, sometimes taking your whole invite-tree (and inviter) down with
> you. Read those before enabling anything.

---

## Part 1 — Request intake & routing

### The flow

```
Discord /request     Telegram msg      email to movies@…
   (discord.py)   (python-telegram-bot)  (imap-tools + smtplib)
        │                  │                    │
        └────────┬─────────┴──────────┬─────────┘
                 │  normalized {channel, user, text, reply}
                 ▼
        ┌──────────────────────────────────────────┐
        │  RESOLVER  (one always-on asyncio service)│
        │  1. fast-path: explicit "Title (Year)"    │
        │       → TMDB/Seerr search, 1 strong hit?  │
        │       → dispatch, no LLM cost             │
        │  2. ambiguous ("the new dune") → Claude    │
        │       Haiku 4.5, structured-output JSON,  │
        │       ranks TMDB candidates → {tmdbId,…}  │
        └───────────────┬──────────────────────────┘
                        ▼
              Seerr  POST /api/v1/request   ← dedup + per-user quota + perms
                        ▼
                 Radarr / Sonarr → Prowlarr → indexers → qBittorrent
                        ▼
                 reply to the originating channel: "Added Dune (2024) ✅"
```

### Key research-driven decisions

- **Dispatch through Seerr, not directly to Radarr.** Seerr (the 2026 merge of
  Overseerr + Jellyseerr — build against `seerr-team/seerr`) already does
  request dedup, per-user quotas, and permissions. We attribute each request to
  the linked Seerr user (admin key + `userId`) so quotas apply. Replaces the
  plain Jellyseerr in the base compose.
- **Two-tier LLM, cost-controlled.** Clear requests ("add Dune Part Two 2024")
  never touch the LLM — a deterministic TMDB lookup handles them. Only vague
  requests ("that movie with the spinning top") hit Claude Haiku 4.5 with a
  JSON-schema structured output that ranks pre-fetched TMDB candidates. The LLM
  is a *ranker*, not a searcher (cheaper, no tool-loops).
- **Build thin, don't reinvent.** No existing bot does Discord+Telegram+email
  +LLM, so the intake service is custom — but it's ~one asyncio process with
  three adapter tasks, all funnelling into one resolver. Everything downstream
  is Seerr's job.

### Per-title tracker routing — the honest answer

You asked to "route requests to different trackers." The research verdict:
**Radarr/Sonarr are built to score across *all* indexers and grab the best
release — per-request "send THIS title to THAT tracker" is the exception path,
not a first-class feature.** What's actually achievable:

- **Bias, don't force:** indexer **priority** (tiebreaker), **release profiles**
  (prefer freeleech/internal flags), and **indexer tags** (restrict which
  indexers a tagged title queries). This covers "anime → anime tracker,
  4K → HD tracker" as *standing rules*, which is what you usually want.
- **Hard pin (exception):** for "get this specific release from this specific
  tracker," the agent uses Prowlarr's interactive search with `indexerIds=<id>`
  and pushes the chosen release — a manual flow, bypassing the scored pipeline.

So the agent's routing value is mostly **content-type routing as config** plus a
**manual pin escape-hatch**, not magical per-request tracker selection. The base
config lives in `routing.example.yml` (title/category pattern → indexer pref).

---

## Part 2 — The ratio engine

### Goal restated

Use zklw's always-on bandwidth to (a) keep healthy ratios on all trackers
automatically, and (b) build the kind of account — age, ratio buffer, zero
Hit-and-Run record, rare-content seeding — that gets you *invited* to elite
trackers. The legitimate strategy and the "good citizen" strategy are the same.

### The three levers (in priority order)

1. **Cross-seed (biggest free win).** `cross-seed` finds content you already
   have that *also* exists on your other trackers, and seeds one physical copy
   to all of them — multiplying upload for ~zero extra disk/bandwidth. One
   download → ratio gain on N trackers.
2. **Race new uploads.** Early seeders capture most of a new torrent's upload.
   RSS polling (every few min) is the easy baseline; **autobrr** (IRC announce,
   ~1s) is the performance tier for when you want to actually win races.
3. **Long-tail / rare-content seeding + bonus points.** A 24/7 box is the only
   thing that can seed rare/dead torrents and earn bonus-point economies —
   exactly what trackers reward and what builds reputation (esp. Karagarga,
   where *contributing rare content* is the whole culture).

### The stack additions

| Service | Job | Critical setting |
|---|---|---|
| **cross-seed** | seed one file to N trackers | `linkType: hardlink`, `linkCategory` set, same `/data` mount |
| **autobrr** *(opt-in)* | race new uploads via IRC announce | per-tracker IRC creds (from 1Password) |
| **qbit_manage** | HnR-safe lifecycle: only it deletes | `share_limits` group per tracker w/ `min_seeding_time` |
| RSS *(baseline)* | simple new-upload pull | per-tracker personal RSS URL (carries passkey — secret) |

### The hardlink invariant (do not violate)

Download dir + cross-seed link dirs + media library **must be on one
filesystem / one `/data` mount**. Off-mount = hardlinks silently fail →
cross-seed copies data (2× disk) and *arr imports break. This is the #1
misconfiguration. Our compose already mounts a single `${MEDIA_ROOT}:/data`
everywhere — keep it that way.

### The ratio-vs-cleanup firewall (the dangerous part)

- qBittorrent native share limits → **pause-only, NEVER delete**.
- **Only `qbit_manage` removes torrents**, and only after that tracker's
  `min_seeding_time` is satisfied. Per-tracker seed-time floors:
  - TorrentLeech: 4–10 days by userclass (strict HnR — start at 10d).
  - HDBits: account-ratio model, no per-torrent HnR *reported* (unconfirmed —
    seed long anyway).
  - Karagarga: **no HnR, no min seed time** — but seeding rare stuff is the
    whole point, so seed anyway for reputation.
  - AudioNews: hard 0.8 ratio floor, seed fresh in-demand tools.
- Radarr/Sonarr cleanup must respect the same floors (don't let an upgrade
  delete a still-obligated torrent — hardlinks protect the *bytes*, but the
  torrent entry must keep seeding).

---

## Part 3 — Per-tracker cheat-sheet (verify in-site; some rules are login-gated)

| | HDBits | Karagarga | TorrentLeech | AudioNews |
|---|---|---|---|---|
| Tier | Elite (destination) | Prestige specialist (arthouse) | Entry/mid (best ratio-builder w/ seedbox) | Niche (audio *production* tools) |
| Ratio | ~1:1 expected | Lenient tiers (max ~0.25) | Global 0.4; per-torrent 1:1 / class seedtime | Hard 0.8 |
| HnR | None reported ⚠️ | **None** | **Strict** (4–10d by class) | Ratio-based |
| Seedbox | Allowed; never run same torrent on 2 accts/1 box | Fine (norm for rare seeding) | **Allowed & must be declared in profile** | Allowed; use static IP |
| Freeleech | Tiered + Neutral Leech; finish before expiry | Rare ("Featured" torrents) | Auto-FL on packs + anything >14GB (still must seed to 1:1) | None standing |
| Bonus pts | Seed bonus (rates not public) | None — paid in ratio/upload credit | **TL Points** (seed-time × size × rarity) | Per-release seed bonus |
| Culture note | HD-quality elitism | Upload rare/world cinema, fund subtitle "pots", NO modern blockbusters | Seedbox-friendly racer's tracker | Seed fresh VSTs/DAWs, not giant libs |

### The climb (mid → elite)
1. Build a clean record on **TorrentLeech** (your seedbox makes this easy):
   ratio buffer ~1.5–2:1, account age >1yr, **zero HnR**, high seed count.
2. Reach Power-User/Elite → unlocks the **invite forum** where other trackers
   recruit. This is the main interview-free path up.
3. Apply with **unedited profile screenshots** (3+ trackers, >1yr age).
4. Interview trackers (RED/OPS): connect via IRC **from home, not the seedbox**;
   genuinely learn formats via interviewfor.red — never use leaked answers.

### NEVER (the ban firewall)
- Never fake ratio / run spoofers / report untransferred upload (auto-detected).
- Never run **multiple tracker accounts from one seedbox IP** → use a dedicated
  IP. Never run the same torrent on two accounts from one box (HDBits cheating).
- Never let automation grab freeleech then bail on seeding (the classic HnR).
- Never let cross-seed produce **phantom announces**: disable qBittorrent
  tracker auto-merge so upload on tracker A isn't announced to trackers B/C.
- Never buy/sell/trade invites/accounts. Invite-trees mean your inviter is
  liable for you; cheating can treeban innocents.
- Never hammer trackers with bulk cross-seed searches (respect 30s delay,
  ~400/day defaults). Never use VPN where banned (AudioNews blocks at signup).
- Declare your seedbox on TorrentLeech (mandatory).

---

## Secrets — 1Password at runtime

All tracker passkeys, RSS URLs, IRC creds, and API keys live in **1Password**,
pulled at service start via the `op` CLI with a service-account token. Nothing
sensitive sits in plaintext config or git. See `agent/secrets-1password.md`.

---

## Build order (so nothing is enabled before its safety net)

1. Base stack up, libraries scanned (base `README.md`).
2. cross-seed + **qbit_manage first** (the HnR firewall) — never the reverse.
3. RSS feeds as the simple new-upload baseline.
4. Intake bot (Discord first, then Telegram, then email).
5. autobrr last (opt-in racing tier), once seed-time floors are proven safe.

Tracked as deferred next-actions in `README.md` (file as beads from main
checkout).
