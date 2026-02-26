# PRD: Backlog Hygiene Gate for Discovery Feed

**Bead:** iv-wie5i.1
**Date:** 2026-02-26
**Priority:** P0

## Problem Statement

Interject auto-scan creates beads for all discoveries with tier >= medium, with no human review. This is the only fully automatic bead inflow path, and it has inflated the open backlog to 430 items (384 ready). The backlog is too large to meaningfully prioritize, diluting focus on high-impact work.

## Features

### F1: Pending Triage Status in Interject

Add `pending_triage` to the interject discovery status lifecycle. Medium-tier items go to `pending_triage` instead of directly creating beads. High-tier items continue to auto-create beads (they're rare and high-signal).

**Changes:**
- `src/interject/outputs.py` — `_create_bead()` gated on tier
- `src/interject/schema.py` — add `pending_triage` status if needed
- Interject DB migration if status column needs new value

**Acceptance:** `interject_scan` with medium-tier results does NOT create beads; items appear in `interject_inbox` with `pending_triage` status.

### F2: Triage Batch Review Command

New `/interject:triage` skill that presents pending items in batches of 5-10, with quick accept (promote to bead) or dismiss actions.

**Changes:**
- `interverse/interject/skills/triage/SKILL.md` — new skill
- Uses existing `interject_promote` and `interject_dismiss` MCP tools
- Filters `interject_inbox` to `status=pending_triage` only

**Acceptance:** Running `/interject:triage` shows pending items and lets user batch-promote or dismiss them.

### F3: One-Time Backlog Sweep

Script to defer or close stale beads in the existing backlog. Criteria:
- Open beads with no activity for >30 days → `bd defer <id>`
- Deferred beads with priority >= P3 and no activity for >14 days → `bd close <id> --reason="stale-sweep"`
- Report: count of deferred, closed, and kept beads

**Changes:**
- `scripts/backlog-sweep.sh` — one-time script
- Dry-run mode by default, `--apply` to execute

**Acceptance:** Running the sweep reduces open backlog by removing genuinely stale items.

### F4: Discovery Score Penalty for Pending Items

Ensure `discovery_scan_beads` deprioritizes beads that were created from interject (have `[interject]` prefix in title) and have no human interaction (no state changes, no plan/brainstorm artifacts linked).

**Changes:**
- `interverse/interphase/hooks/lib-discovery.sh` — add scoring adjustment
- Items with `[interject]` title prefix and no phase state → -15 score penalty

**Acceptance:** Interject-originated beads without human touch rank lower in discovery results.

## Out of Scope

- TTL auto-archive rules (Phase 2 — requires bd CLI changes)
- Changes to `bd` CLI itself
- Cron/daemon for periodic triage
- Notification system for pending triage items

## Success Metrics

- Open bead count decreases from ~430 to <200 after sweep
- New interject scans don't inflate backlog (medium-tier items queue, not create)
- `/interject:triage` provides clear accept/dismiss workflow
