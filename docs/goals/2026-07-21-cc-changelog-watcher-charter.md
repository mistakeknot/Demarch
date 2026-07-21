---
artifact_type: goal-charter
bead: Sylveste-b15
complexity: 3
stage: goal-formed
---

# Goal Charter: Claude Code Changelog Watcher — Standing Cadence + First Mapping Digest + AgMoDB Refresh

## Why (leverage)

New Claude Code capabilities (hooks, tools, SDK/plugin surfaces) are build
fuel for the Sylveste ecosystem, but nothing tracks them today — the
2026-07-20 session established that discovery is ad hoc. A standing
watcher turns CC releases into a durable work queue. mk deferred this
behind the test-baseline goal ("we should do ytm first"); that goal closed
2026-07-21 with all suites green, so exit codes downstream of this work
are now trustworthy.

**Interview decisions (2026-07-21):**
1. Architecture = **zklw user timer + in-session mapping** (recommended
   option): weekly systemd --user timer on zklw per the estate-drift
   precedent — dumb diff, at most ONE open delta bead updated in place,
   zero unattended LLM cost; the capability→plugin mapping happens
   in-session with full ecosystem context.
2. Watch scope v1 = **CC changelog only** (anthropics/claude-code
   CHANGELOG.md; other feeds widen later on evidence).
3. Success bar = **watcher + first digest + AgMoDB capability-notes
   update** (mk custom answer): beyond the live watcher and first mapped
   digest, refresh the curated Claude Code entry in AgMoDB
   (`~/projects/agmodb` on zklw, deployed at agmodb.com,
   `src/lib/agent-seeds.ts` — features map, supportedModels, description)
   from the digest findings.

## Scope

**In:**
1. Watcher script + **systemd user timer** on zklw (mk has no sudo —
   `systemctl --user`), estate-drift pattern: fetch CHANGELOG.md, diff
   against last-seen version state, file/update at most one open delta
   bead; state file survives reboots; failures silent-but-logged.
2. One live cycle run: baseline recorded, delta-or-no-delta outcome
   shown.
3. First capability mapping digest, produced in-session, bounded to the
   current CC minor series: new capabilities → Sylveste plugins that
   could exploit them → candidate beads filed; digest committed under
   `docs/research/` in the Sylveste root repo.
4. AgMoDB refresh from the digest: update the `claude-code` entry in
   `src/lib/agent-seeds.ts` (features/supportedModels/description as
   warranted — supportedModels is visibly stale), `npx tsc --noEmit`
   green, committed and pushed per AgMoDB workflow (auto-deploys).
5. Close Sylveste-b15.

**Out:**
- Agent SDK / API release-note feeds (v2, evidence-gated).
- Building any of the mapped candidate features (they become beads).
- AgMoDB entries other than claude-code; AgMoDB schema changes.

## Acceptance criteria

1. Timer enabled and listed on zklw (`systemctl --user list-timers`
   output surfaced); script + unit files committed to an appropriate repo.
2. Live cycle surfaced: baseline version state + delta bead (or no-delta
   proof).
3. Digest doc committed in Sylveste with candidate bead IDs surfaced.
4. agent-seeds.ts claude-code entry updated; tsc clean; pushed.
5. Sylveste-b15 closed.

## Completion condition (literal — handed to /goal)

Claude Code changelog watcher shipped: watcher script and systemd user timer installed and enabled on zklw with systemctl --user list-timers output surfaced, following the estate-drift pattern (at most one open delta bead, updated in place, state file recording last-seen version); one live cycle run surfaced showing the recorded baseline and its delta-or-no-delta outcome; the first capability mapping digest committed under docs/research/ in the Sylveste root repo with the commit and candidate bead IDs surfaced; AgMoDB src/lib/agent-seeds.ts claude-code entry updated per the digest with npx tsc --noEmit passing and the commit pushed, output surfaced; bead Sylveste-b15 closed with output surfaced. Or stop after 40 turns.

## Successor obligations

Propose a successor at close per Goal Cadence. Leading candidates at
formation: the small-fix bundle (Sylveste-a3a date-d fallbacks +
Sylveste-1zu ic publish --cwd hard-error + Sylveste-zlc legacy /tmp
sideband removal), or widening the watcher to SDK/API feeds if the first
digest proves high-yield.
