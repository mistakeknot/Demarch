# Deferred beads — zklw-media

Beads that couldn't be filed from this worktree (no Dolt DB reachable — runtime
state isn't in git). **File these from the main checkout** with `bd create`, then
delete the corresponding entry here.

---

## Intake: availability-nudge for purchasable content (P2)

**Title:** Intake bot: nudge to Apple TV / YouTube Movies for purchasable titles

**Description:**
Per the zklw scarcity doctrine (2026-07-09): the server is only for content the
user CANNOT legitimately buy or stream. Before a request hits the download stack,
the intake resolver (or Seerr) should check whether the title is available to
buy/stream on **Apple TV** or **YouTube Movies** and, if so, nudge the requester
("you can watch this on Apple TV / YouTube Movies") instead of — or before —
queueing a download.

**Approach:**
- Cheapest interim: static request-guidance note in Seerr's request UI text.
- Better: automated check in `intake_bot/resolver` using TMDB
  `/movie/{id}/watch/providers` (or JustWatch) filtered to the user's region +
  providers {Apple TV, YouTube}. If found → return an "available to buy" nudge in
  the bot reply and skip auto-dispatch (or require an explicit override).
- Keep it a soft nudge, not a hard block — user may still want a
  preservation-grade copy of something that's only rentable.

**Acceptance:**
- A request for a title purchasable on Apple TV or YouTube Movies produces a
  "watch it there" nudge before any Radarr/Sonarr grab.
- Titles NOT on those providers pass through to the normal download flow unchanged.

**Refs:** memory `reference_zklw_scarcity_doctrine`, `intake_bot/resolver`,
TMDB watch-providers API.
