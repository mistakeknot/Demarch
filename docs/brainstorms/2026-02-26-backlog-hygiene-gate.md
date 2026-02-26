# Backlog Hygiene Gate for Discovery Feed

**Bead:** iv-wie5i.1
**Date:** 2026-02-26
**Status:** Brainstorm

## Problem

430 open beads, growing faster than the team closes them. The primary uncontrolled inflow is **interject auto-scan** — when `interject_scan` runs, items scoring tier >= medium get a bead created immediately via `outputs.py:_create_bead()` with no human review. Other bead creation paths (strategy decomposition, sprint creation, quality-gates findings) are already human-gated.

The symptoms:
- Discovery scan returns 384 "ready" items — too many to meaningfully prioritize
- Low-quality beads dilute attention from high-impact work
- Stale beads accumulate indefinitely (no TTL or auto-archive)
- Session-start discovery is noisy with items that will never be worked on

## Current Inflow Paths

| Path | Volume | Human Gate | Fix Needed |
|------|--------|-----------|------------|
| Interject auto-scan (tier >= medium) | High | None | **Yes — primary gap** |
| `/clavain:route` orphan linking | Low | AskUserQuestion | No |
| `/clavain:strategy` decomposition | Low | Human-driven | No |
| Sprint bead creation | Low | Human-driven | No |
| Quality-gates findings | Low-medium | AskUserQuestion | No |
| Intersynth auto-bead | Off by default | Env opt-in | No |

## Current Expiry Mechanisms

- `bd stale` — read-only query, no auto-action
- Discovery scoring: -10 penalty for items >2 days old, -30 for closed-parent children
- Interject decay: 0.95 rate on discovery scores (affects interject DB, not beads)
- Claim TTL: 2h auto-release in discovery scan

**Missing:** No TTL on beads. No auto-archive. No auto-close for stale items.

## Design Options

### Option A: Gate Interject at Creation (Recommended)

**Change:** In `outputs.py`, replace `_create_bead()` with a "queue to pending" step:
1. Write to interject DB as `status=pending_triage` instead of creating bead
2. Require explicit `interject_promote` (or new batch triage command) to create bead
3. Add `/interject:triage` command for batch review of pending items

**Pros:** Stops the firehose at the source. Zero change to beads system. Interject already has the `inbox` and `promote` tools.
**Cons:** Requires human triage time. Items might languish in pending queue.

### Option B: TTL + Auto-Archive on Beads

**Change:** Add lifecycle rules to beads system:
1. Open beads with no activity for N days → auto-deferred
2. Deferred beads with no activity for M more days → auto-closed with reason "stale"
3. Discovery scan filters out deferred beads entirely

**Pros:** Self-cleaning backlog. Works regardless of inflow source.
**Cons:** Risk of auto-closing something valuable. Needs careful TTL tuning.

### Option C: Hybrid (A + B)

**Change:** Gate interject inflow AND add TTL rules.

**Pros:** Belt and suspenders — controls inflow AND cleans existing backlog.
**Cons:** More implementation surface. Diminishing returns if Option A works well.

## Recommendation

**Option C (Hybrid)** — but phase it:
1. **Phase 1:** Gate interject (Option A) — stops the bleeding
2. **Phase 2:** TTL auto-archive (Option B) — cleans accumulated debt

Phase 1 is a single-file change in `outputs.py` plus a new triage command. Phase 2 needs bd CLI changes or a cron-like sweep script.

## Key Design Decisions

1. **Triage threshold:** Should `tier=high` items still auto-create beads, or should ALL items go through triage? Recommendation: high-tier still auto-creates (they're rare and high-signal), medium-tier gets queued.
2. **TTL values:** Reasonable starting point: 14 days to defer, 30 days to close. Adjustable.
3. **Triage batch size:** `/interject:triage` should present 5-10 items at a time with quick accept/dismiss actions.
4. **Existing backlog:** Run a one-time sweep to defer/close the oldest stale beads before the gate goes live.

## Scope for This Sprint

Focus on **Phase 1 only** (gate interject inflow):
- F1: Add `pending_triage` status to interject discoveries
- F2: Change `_create_bead()` to queue medium-tier items instead of creating beads
- F3: Add `/interject:triage` batch review command
- F4: One-time backlog sweep script for existing stale beads
