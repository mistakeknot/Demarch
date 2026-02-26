# Plan: Backlog Hygiene Gate for Discovery Feed

**Bead:** iv-wie5i.1
**PRD:** docs/prds/2026-02-26-backlog-hygiene-gate.md
**Date:** 2026-02-26

## Overview

Gate interject's automatic bead creation so medium-tier discoveries queue for human triage instead of silently inflating the backlog. High-tier items continue auto-creating. Add a triage skill and a one-time backlog sweep.

## Batch 1: Gate Interject Inflow (F1 + F2)

### Task 1.1: Add `pending_triage` status to interject schema

**File:** `interverse/interject/src/interject/db.py`
- Add `pending_triage` to the discovery status lifecycle (no schema migration needed — status is a text column)
- Add `get_pending_triage(limit, min_score)` method that queries `status='pending_triage'`
- Add `mark_pending_triage(discovery_id)` method

### Task 1.2: Gate `outputs.py` — medium-tier skips bead creation

**File:** `interverse/interject/src/interject/outputs.py`

Change `process()` method:
```python
def process(self, discovery: dict, tier: str, auto_create_bead: bool = True) -> dict:
    if tier == "low":
        return {"tier": "low"}
    if tier == "medium" and not auto_create_bead:
        # Write briefing for reference but don't create bead
        briefing = self._write_briefing(discovery)
        return {"tier": "medium", "briefing_path": str(briefing), "pending_triage": True}
    # ... existing high-tier and forced-promote logic unchanged
```

The caller in the scan pipeline passes `auto_create_bead=False` for automatic scans. The `_handle_promote` handler continues to call `process(discovery, "high")` with the default `auto_create_bead=True`.

### Task 1.3: Update scanner to use pending_triage

Find where `outputs.process()` is called during automatic scan (in `scanner.py` or `engine.py`). After `process()` returns with `pending_triage=True`, call `db.mark_pending_triage(discovery_id)` instead of recording as promoted.

### Task 1.4: Update `interject_inbox` to show pending items

**File:** `interverse/interject/src/interject/server.py`

Modify `_handle_inbox()` to accept `status` parameter:
```python
status = args.get("status", "new")  # default unchanged for backward compat
# Also accept "pending_triage" or "all"
```

Add a `pending_count` field to the response so users know items are waiting.

### Task 1.5: Create `/interject:triage` skill

**File:** `interverse/interject/skills/triage/SKILL.md`

Skill that:
1. Calls `interject_inbox` with `status=pending_triage`
2. Presents items in batches of 5-10 via AskUserQuestion
3. For each item: "Promote to bead", "Dismiss", "Skip for now"
4. Calls `interject_promote` or `interject_dismiss` accordingly
5. Reports summary: N promoted, M dismissed, K deferred

## Batch 2: Backlog Sweep (F3 + F4)

### Task 2.1: Write backlog sweep script

**File:** `scripts/backlog-sweep.sh`

```bash
#!/usr/bin/env bash
# One-time sweep: defer/close stale beads
# Usage: bash scripts/backlog-sweep.sh [--apply]
```

Logic:
1. `bd list --status=open --json` → parse all open beads
2. For each bead:
   - Skip if priority <= P1 (never auto-sweep high-priority)
   - Check `updated_at` — if >30 days ago AND no plan/brainstorm artifacts: candidate for defer
   - Check title for `[interject]` prefix — interject-originated beads with no phase state: candidate for close
3. Dry-run mode (default): print what would be deferred/closed
4. `--apply` mode: execute `bd defer <id>` or `bd close <id> --reason="stale-sweep"`

### Task 2.2: Add discovery score penalty for interject beads

**File:** `interverse/interphase/hooks/lib-discovery.sh`

In `score_bead()`, after existing score calculation:
```bash
# Interject-originated beads without human touch rank lower
if [[ "$title" == "[interject]"* ]] && [[ -z "$phase" ]]; then
    score=$((score - 15))
fi
```

## Estimated Size

- Batch 1: ~120 lines across 4 files + 1 new skill
- Batch 2: ~80 lines across 2 files
- Total: ~200 lines

## Test Plan

- Verify `interject_scan` with medium-tier results does NOT create beads (check bd list before/after)
- Verify `interject_promote` still creates beads correctly (high-tier path unchanged)
- Verify `/interject:triage` shows pending items and promote/dismiss works
- Run `backlog-sweep.sh` in dry-run mode and verify candidates look reasonable
- Verify discovery scoring deprioritizes `[interject]` beads without phase
