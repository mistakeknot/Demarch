# Brainstorm: Interspect F3 — Apply Override + Canary + Git Commit

**Bead:** iv-gkj9
**Date:** 2026-02-23
**Parent:** iv-nkak (Routing overrides Type 2 — CLOSED), iv-sksfx (Interspect Phase 2 epic)
**Depends on:** iv-8fgu (F2: pattern detection + propose flow — DONE), iv-r6mf (F1: schema — DONE)

## Context

The propose flow (F2) writes `action: "propose"` entries to `routing-overrides.json`. These are informational — flux-drive sees them in triage notes but does NOT exclude the agent. The user accepts proposals via `/interspect:propose` (multi-select AskUserQuestion), but the actual promotion from `propose` → `exclude` has no implementation yet.

The propose command's "On Accept" section calls `_interspect_apply_routing_override()`, which writes a **new** `exclude` entry. But this doesn't handle the case where a `propose` entry already exists — it would create a duplicate (the `unique_by(.agent)` dedup in `_interspect_apply_override_locked` prevents this, but the behavior is: last-write-wins, which silently replaces the propose with an exclude). This works but is accidental rather than intentional.

## What Already Works

| Component | Status | Notes |
|-----------|--------|-------|
| `_interspect_apply_routing_override()` | Working | Writes `exclude` + canary + modification record + git commit |
| `_interspect_apply_propose()` | Working | Writes `propose` entry (no canary, no modification record) |
| `_interspect_revert_routing_override()` | Working | Removes entry + closes canary + git commit |
| Canary monitoring (DB) | Working | `canary` table with baseline metrics, window tracking |
| `/interspect:propose` command | Working | Detects eligible patterns, presents multi-select, calls apply |
| `/interspect:revert` command | Working | Removes override or overlay, optional blacklist |

## What's Missing

### 1. Explicit Approve Function (`_interspect_approve_override`)

Currently, if the user accepts a proposal in `/interspect:propose`, it calls `_interspect_apply_routing_override()` which writes a fresh `exclude`. This **accidentally works** because `unique_by(.agent)` deduplicates. But the flow should be:

1. Read existing `propose` entry (preserve `evidence_ids`, `created` timestamp, `created_by`)
2. Promote `action` from `"propose"` to `"exclude"`
3. Add `confidence` (computed from evidence DB)
4. Add `canary` snapshot
5. Record modification in SQLite
6. Start canary monitoring in SQLite
7. Git commit with descriptive message

### 2. `/interspect:approve` Command

The propose command outputs `To apply: /interspect:approve ${agent}` but no such command exists. This is F3's primary deliverable.

Workflow:
- User runs `/interspect:approve fd-game-design` (or without argument to see pending proposals)
- Command reads `routing-overrides.json`, finds entries with `action: "propose"`
- If no argument: shows all pending proposals and lets user multi-select
- If argument: validates the named agent has a `propose` entry
- For each selected proposal: calls `_interspect_approve_override()`
- Reports result with canary monitoring info

### 3. Batch Approve Support

The propose flow presents a multi-select. The approve command should mirror this — allow approving multiple proposals at once.

## Design

### Approve Function: Promote vs Replace

**Option A: In-place promotion** — Read entry, change `action`, add fields, write back.

Pros: Preserves original `created`, `created_by`, `evidence_ids`. Clean audit trail (same entry, evolved action).
Cons: More complex jq manipulation inside flock. Need to handle partial field updates.

**Option B: Replace** — Delete `propose` entry, insert fresh `exclude` entry via existing `_interspect_apply_override_locked()`.

Pros: Reuses existing code. `_interspect_apply_override_locked` already handles all the exclude logic.
Cons: Loses original `created` timestamp and `created_by`. The modification record shows "applied" not "promoted".

**Decision: Option A (in-place promotion).** The `created` timestamp matters for audit trail — it tells you when the evidence first triggered the proposal, not when the user clicked approve. We can add an `approved` timestamp for when the promotion happened.

### Approve Locked Function

```
_interspect_approve_override_locked():
1. Read routing-overrides.json
2. Find propose entry for agent (fail if not found)
3. Compute confidence from evidence DB
4. Build canary snapshot
5. Promote: action→exclude, add confidence, canary, approved timestamp
6. Write routing-overrides.json (atomic)
7. Git commit
8. Insert modification record (DB)
9. Insert canary record (DB)
10. Output commit SHA
```

### Command: `/interspect:approve`

```
Arguments: [agent-name] (optional)

No argument:
  1. Read routing-overrides.json
  2. Filter for action=="propose"
  3. If none: "No pending proposals. Run /interspect:propose to detect eligible patterns."
  4. If any: Show table + multi-select AskUserQuestion
  5. For each selected: call _interspect_approve_override

With argument:
  1. Validate agent name format
  2. Check routing-overrides.json for propose entry
  3. If not found: "No proposal found for {agent}. Run /interspect:propose first."
  4. If found: confirm + call _interspect_approve_override
```

### Schema Fields Added to Promote Entry

When promoting propose → exclude, these fields are added/changed:

```json
{
  "agent": "fd-game-design",       // preserved
  "action": "exclude",             // changed from "propose"
  "reason": "...",                 // preserved
  "evidence_ids": [...],           // preserved
  "created": "2026-02-20T...",     // preserved (when propose was created)
  "created_by": "interspect",     // preserved
  "approved": "2026-02-23T...",    // NEW: when user approved
  "confidence": 0.92,             // NEW: evidence strength at approval time
  "canary": {                     // NEW: canary monitoring snapshot
    "status": "active",
    "window_uses": 20,
    "expires_at": "2026-03-09T..."
  }
}
```

The `approved` field is not in the current schema. We need to add it to `routing-overrides.schema.json`. It's optional (only present on promoted entries, not on manual excludes).

## Implementation Scope

### Must-Have (this bead)

- [ ] `_interspect_approve_override()` — outer function with validation + flock
- [ ] `_interspect_approve_override_locked()` — inner function: promote + canary + modification + git commit
- [ ] `/interspect:approve` command (commands/interspect-approve.md)
- [ ] Add `approved` field to schema (optional, format: date-time)
- [ ] Update `/interspect:propose` "On Accept" to call `_interspect_approve_override` instead of `_interspect_apply_routing_override`

### Nice-to-Have (defer)

- [ ] Approve-all shortcut (`/interspect:approve --all`)
- [ ] Approval expiry (auto-revert if canary fails)
- [ ] Notification when canary window completes

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Propose entry modified between read and approve | Low | Low | Flock atomicity prevents TOCTOU |
| No propose entries exist when approve is called | Medium | None | Graceful message + redirect to propose |
| Schema change breaks existing routing-overrides.json | Low | Low | `approved` is optional, additionalProperties: true |
| Approve called on already-excluded agent | Low | None | Dedup check inside flock; idempotent |

## Dependencies

```
iv-8fgu (F2: propose flow) — DONE → provides propose entries to approve
iv-r6mf (F1: schema) — DONE → schema to extend with approved field
iv-gkj9 (F3: this bead) → provides approve command
  ← iv-2o6c (F4: status display + revert) — needs approve to exist
```
