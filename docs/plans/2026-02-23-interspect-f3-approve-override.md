# Plan: Interspect F3 — Approve Override + Canary + Git Commit

**Bead:** iv-gkj9
**Date:** 2026-02-23
**Brainstorm:** docs/brainstorms/2026-02-23-interspect-approve-flow-brainstorm.md

## Summary

Implement the `/interspect:approve` command and `_interspect_approve_override()` library function to promote `propose` → `exclude` entries in `routing-overrides.json` with canary monitoring, modification records, and atomic git commits.

## Tasks

### Task 1: Add `approved` field to JSON Schema

**File:** `os/clavain/config/routing-overrides.schema.json`

Add optional `approved` field (ISO 8601 date-time) to the `override` definition. This field is set when a propose entry is promoted to exclude.

**Changes:**
- Add `"approved"` property to `definitions.override.properties`
- Type: string, format: date-time, description: "ISO 8601 timestamp when proposal was approved. Only present on promoted entries."

### Task 2: Implement `_interspect_approve_override()` and `_interspect_approve_override_locked()`

**File:** `os/clavain/hooks/lib-interspect.sh`

Insert after `_interspect_apply_propose_locked()` (around line 1155).

**`_interspect_approve_override(agent)`:**
- Validate agent name format
- Pre-check: read routing-overrides.json, verify a `propose` entry exists for agent
- Build commit message (temp file, no injection)
- Call `_interspect_flock_git _interspect_approve_override_locked`
- Report success with canary info

**`_interspect_approve_override_locked(root, filepath, fullpath, agent, commit_msg_file, db)`:**
1. Read routing-overrides.json
2. Find propose entry for agent (fail if not found; exit 2 if already excluded)
3. Compute confidence from evidence DB (reuse pattern from `_interspect_apply_override_locked`)
4. Build canary snapshot (reuse pattern from `_interspect_apply_override_locked`)
5. In-place promote via jq: `action→"exclude"`, add `confidence`, `canary`, `approved` timestamp
6. Atomic write (tmp + rename + jq validation)
7. Git add + commit with `-F` (using `git -C "$root"` pattern from propose_locked, not `cd`)
8. Insert modification record into SQLite (tier: persistent, mod_type: routing, status: applied)
9. Insert canary record (baseline computation, window, expiry)
10. Output commit SHA

**Key patterns to follow** (from existing code):
- `_interspect_sql_escape` for all DB interpolation
- `_interspect_load_confidence` before confidence computation
- `_interspect_compute_canary_baseline` for canary baseline
- Exit code 2 for dedup/idempotent skip (not error)
- `git -C "$root"` instead of `cd "$root"` (F2 pattern, avoids set -e + cd failure)

### Task 3: Create `/interspect:approve` command

**File:** `os/clavain/commands/interspect-approve.md`

Command structure (mirrors interspect-revert.md pattern):

```
---
name: interspect-approve
description: Promote pending proposals to active routing overrides
argument-hint: "[agent-name]"
---
```

**No argument flow:**
1. Source lib-interspect.sh, ensure DB
2. Read routing-overrides.json
3. Filter for `action == "propose"` entries
4. If none: "No pending proposals. Run /interspect:propose to detect eligible patterns."
5. If any: Show table (agent, reason, created, evidence count) + multi-select AskUserQuestion
6. For each selected: call `_interspect_approve_override`
7. Report results

**With argument flow:**
1. Validate agent name
2. Check for propose entry
3. If not found: helpful message
4. If found: show details + confirm via AskUserQuestion (single-select: "Approve", "Show evidence", "Cancel")
5. If "Show evidence": query evidence DB, show recent corrections, re-ask
6. On approve: call `_interspect_approve_override`
7. Report result

### Task 4: Update `/interspect:propose` On Accept

**File:** `os/clavain/commands/interspect-propose.md`

In the "On Accept" section (line 114), change:
- From: `_interspect_apply_routing_override "$agent" "$reason" "$evidence_ids" "interspect"`
- To: `_interspect_approve_override "$agent"`

This ensures proposals go through the approve flow (promote existing entry) rather than creating a fresh exclude entry.

### Task 5: Update command count in CLAUDE.md

**File:** `os/clavain/CLAUDE.md`

Update command count from 54 to 55 (adding interspect-approve).

## Testing

After implementation:
1. Syntax check: `bash -n hooks/lib-interspect.sh`
2. Verify command file structure matches other interspect commands
3. Verify schema validates with jq: `jq '.' config/routing-overrides.schema.json`

## Order of Execution

Task 1 → Task 2 → Task 3 → Task 4 → Task 5

Tasks 1 and 2 can partially overlap (schema change is small). Task 3 depends on Task 2 (needs the function). Task 4 depends on Task 2. Task 5 is independent but should be last.
