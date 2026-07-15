# Deferred beads — zklw-media

Beads that couldn't be filed from this worktree (no Dolt DB reachable — runtime
state isn't in git). **File these from the main checkout** with `bd create`, then
delete the corresponding entry here.

---

## Intake: availability-nudge for purchasable content (P2) — ✅ DONE 2026-07-14

**Title:** Intake bot: nudge to Apple TV / YouTube Movies for purchasable titles

**BUILT** — implemented in the intake bot (commit on branch
`worktree-zklw-media-server`). No bead needed; recorded here for provenance.

**What shipped:**
- `tmdb.purchasable_on()` — queries TMDB `/{movie,tv}/{id}/watch/providers`,
  returns which `NUDGE_PROVIDERS` can buy/rent the title in `WATCH_REGION`.
  Casefolded+substring match (survives Apple's "Apple iTunes"→"Apple TV" rename
  and "YouTube (Movies)"). Best-effort: TMDB errors degrade to no-nudge.
- `pipeline._scarcity_nudge()` — computed between resolve and dispatch for a
  confidently-resolved title; prepends a soft nudge to the reply and STILL
  queues the download (nudge, not gate — preservation copies of rentable-only
  titles stay possible).
- Config: `NUDGE_PROVIDERS` (unset ⇒ `Apple TV,YouTube`; empty ⇒ disabled) +
  `WATCH_REGION` (default `US`). Documented in `bot.env.tpl` + README.
- 17 no-dep unit tests in `intake_bot/test_nudge.py` (all green).

**Acceptance — met:**
- ✅ Purchasable title → "watch it there" nudge before the Radarr/Sonarr grab.
- ✅ Non-provider titles pass through unchanged.

**Refs:** memory `reference_zklw_scarcity_doctrine`, `intake_bot/{tmdb,pipeline}.py`,
TMDB watch-providers API.
