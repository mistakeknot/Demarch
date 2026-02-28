# fd-correctness Review: Disagreement Pipeline Implementation Plan

**Date:** 2026-02-28
**Plan:** `docs/plans/2026-02-28-disagreement-pipeline.md`
**PRD:** `docs/prds/2026-02-28-disagreement-pipeline.md`

## Scope

Reviewed the implementation plan for data consistency, transaction safety, race conditions, SQL correctness, and concurrency patterns. Cross-referenced against the existing codebase:

- `core/intercore/internal/event/store.go` -- existing event store methods
- `core/intercore/internal/event/event.go` -- Event/InterspectEvent types, Source constants
- `core/intercore/internal/db/db.go` -- migration pattern, schema versioning
- `core/intercore/internal/db/schema.sql` -- embedded schema DDL (the one that actually runs)
- `core/intercore/internal/db/migrations/020_baseline.sql` -- reference baseline DDL
- `core/intercore/cmd/ic/events.go` -- CLI event handling, cursor load/save
- `interverse/interspect/hooks/lib-interspect.sh` -- consumer pattern, evidence insertion

## Verdict: NEEDS_ATTENTION

2 P0 findings (blocking), 4 P1 findings (important), 4 P2 findings (nice-to-have), 3 P3 observations.

---

## P0 Findings (Blocking)

### P0-1: UNION ALL field mapping loses chosen_severity, impact, and dismissal_reason

**Location:** Task 4 (UNION ALL query) + Task 8 (consumer wiring)

The UNION ALL query maps review_events into the 9-column unified `Event` struct:

```sql
SELECT id, COALESCE(run_id, ''), 'review', 'disagreement_resolved',
    finding_id, resolution, COALESCE(agents_json, '{}'), '', created_at
FROM review_events
```

The `scanEvents` function (store.go:322-342) scans these as: `ID, RunID, Source, Type, FromState, ToState, Reason, EnvelopeJSON, CreatedAt`. This means:

| review_events column | Unified Event field | Used by consumer? |
|---|---|---|
| finding_id | FromState | Yes |
| resolution | ToState | Yes |
| agents_json | Reason | Yes |
| chosen_severity | **LOST** | Yes (critical) |
| impact | **LOST** | Yes (critical) |
| dismissal_reason | **LOST** | Yes |

The consumer in Task 8 Step 3 then reconstructs a payload with `chosen_severity: ""`, `impact: ""`, `dismissal_reason: ""`. The downstream `_interspect_process_disagreement_event` uses these fields for:

1. **`chosen_severity`** -- decides which agents were overridden: `[[ "$agent_severity" == "$chosen_severity" ]] && continue`. With empty string, this comparison never matches, so ALL agents get evidence records, including agents that agreed with the resolution.

2. **`impact`** -- determines `override_reason` for accepted findings. Empty impact means the `"accepted" && "severity_overridden"` branch never fires.

3. **`dismissal_reason`** -- maps to `override_reason` via case statement. Empty value means discarded findings get empty override_reason.

**Consequence:** Every disagreement event will create evidence for all agents (not just overridden ones), with empty override_reasons. This inflates routing override counts and produces garbage evidence.

**Recommendation:** Either:
- (a) Encode `chosen_severity`, `impact`, `dismissal_reason` into the `agents_json` field as a composite JSON object before storage, so they survive the UNION ALL flattening.
- (b) Have the interspect consumer query `ListReviewEvents` directly instead of going through the unified UNION ALL stream. This matches how `interspect_events` are already handled (separate `ListInterspectEvents` query, not in UNION ALL).

Option (b) is architecturally cleaner and consistent with existing patterns.

### P0-2: schema.sql (embedded DDL) not updated -- fresh databases will lack review_events table

**Location:** Task 2

The plan modifies `core/intercore/internal/db/migrations/020_baseline.sql` and the migration block in `db.go`. However, the code at db.go:19 embeds `schema.sql`:

```go
//go:embed schema.sql
var schemaDDL string
```

And at db.go:357, this embedded DDL is applied:
```go
if _, err := tx.ExecContext(ctx, schemaDDL); err != nil {
    return fmt.Errorf("migrate: apply schema: %w", err)
}
```

The `schema.sql` file uses `CREATE TABLE IF NOT EXISTS` for all tables. For fresh databases (version 0), no migration blocks fire (all guarded by `currentVersion >= N`), so only `schema.sql` creates the tables. The plan does NOT mention updating `schema.sql`.

The `020_baseline.sql` file in the migrations directory is a reference/documentation file -- it is NOT embedded or executed by the Go code.

**Consequence:** Fresh installs will not have the `review_events` table. The migration block (guarded by `currentVersion >= 20 && currentVersion < 24`) handles existing v20-v23 databases correctly, but version-0 databases skip it. After migration, `PRAGMA user_version` is set to 24, but the table doesn't exist. Any INSERT into `review_events` will fail.

**Recommendation:** Add the `review_events` DDL (with `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`) to `schema.sql`, matching the pattern used by every other table. This is mandatory.

---

## P1 Findings (Important)

### P1-1: Missing replay_input insertion contradicts PRD acceptance criteria

**Location:** Task 3 (AddReviewEvent implementation) vs PRD F1

The PRD states: "Replay input entry created for each review event (consistent with dispatch/interspect patterns)."

`AddDispatchEvent` (store.go:23-62) calls `insertReplayInput()` after insertion. `AddCoordinationEvent` (store.go:186-225) does the same. However, the plan's `AddReviewEvent` does NOT call `insertReplayInput()`.

`AddInterspectEvent` also omits `insertReplayInput`, so the plan is consistent with the interspect pattern. But the PRD explicitly requires replay inputs.

**Recommendation:** Resolve the discrepancy: either add `insertReplayInput` to `AddReviewEvent` or remove the acceptance criterion from the PRD. Given that review events are produced externally (by shell scripts via `ic events emit`), replay capture may be less critical. But the PRD should be accurate.

### P1-2: sinceInterspect cursor field: existing bug perpetuated

**Location:** Task 4 (cursor tracking)

The existing code has a known bug (documented in `architecture-review-e5-cli-events.md`): `sinceInterspect` is loaded from the cursor JSON, threaded through function signatures, but NEVER advanced in the event loop. There is no `if e.Source == "interspect" && e.ID > sinceInterspect` check in `cmdEventsTail`. The value is loaded and re-saved unchanged.

The plan adds `sinceReview` tracking but does not fix the interspect bug. This means:
1. Two cursor fields (`interspect` and potentially `review` if missed) will be round-tripped without advancement.
2. The plan does add `if e.Source == "review" && e.ID > sinceReview` (Task 4 Step 3), so review is handled correctly.
3. But not fixing interspect means a consumer that later uses interspect events will replay from zero forever.

**Recommendation:** Fix `sinceInterspect` advancement in the same change. Add the missing high-water-mark tracking for interspect events in the event loop.

### P1-3: Consumer wiring through unified event stream is lossy (architectural mismatch)

**Location:** Task 8

Task 8's wiring goes: `review_events` -> UNION ALL -> unified Event -> `_interspect_consume_kernel_events` -> reconstruct payload -> `_interspect_process_disagreement_event`. The reconstruction step loses 3 of 6 review-specific fields (see P0-1).

The existing interspect_events pattern is: separate `ListInterspectEvents` query path, NOT in the UNION ALL. The consumer queries interspect events directly.

The plan breaks from this established pattern by routing review events through the UNION ALL, then trying to reconstruct the lost fields in the consumer -- a lossy roundtrip.

**Recommendation:** Follow the interspect pattern: have the disagreement consumer call `ListReviewEvents` directly (or use `ic interspect query`-style direct access). Keep review events out of the UNION ALL, or only include them for display purposes (not for consumer processing).

### P1-4: ListEvents parameter ordering is fragile and error-prone

**Location:** Task 4 (ListEvents UNION ALL update)

The existing `ListEvents` query uses positional `?` parameters:
```
runID, sincePhaseID,                    -- phase_events WHERE
runID, runID, sinceDispatchID,          -- dispatch_events WHERE
runID, runID,                           -- coordination_events WHERE
limit                                   -- LIMIT
```

Adding review_events with `WHERE (run_id = ? OR ? = '') AND id > ?` adds 3 more positional parameters: `runID, runID, sinceReviewID`. The ORDER BY and LIMIT are after the last UNION ALL, so `limit` stays last. But interleaving 3 new `?` parameters into the existing 7 requires precise counting.

The plan does not show the complete updated parameter list, leaving room for off-by-one errors that would cause type mismatches (comparing int64 cursor to TEXT run_id) that SQLite would silently coerce.

**Recommendation:** The plan should include the complete updated parameter list explicitly. Consider extracting queries into a query builder or using comments to label each parameter.

---

## P2 Findings (Nice-to-have)

### P2-1: No UNIQUE constraint on review_events(finding_id, session_id)

**Location:** Task 2 (table DDL) + Task 7 (emit logic)

If two concurrent resolve sessions process the same finding, both emit events for the same `finding_id`. The table has no deduplication constraint, so duplicate evidence records are created. This inflates override counts.

**Recommendation:** Consider a UNIQUE constraint on `(finding_id, session_id)` or document the duplicate-tolerance as intentional.

### P2-2: agents_json empty string causes downstream jq failure

**Location:** Task 3 (AddReviewEvent NULL handling)

`agents_json` has a `NOT NULL` constraint and no `NULLIF` wrapping, so empty strings are stored as-is. Downstream `jq 'to_entries[]'` on an empty string will fail. The emit path marshals a Go map which produces `{}` (never empty string), so in practice this path is safe, but it is fragile if anyone calls `AddReviewEvent` directly with empty string.

**Recommendation:** Default `agents_json` to `'{}'` if empty, or add a CHECK constraint.

### P2-3: ic events emit interspect path: missing agent_name validation

**Location:** Task 5 (cmdEventsEmit interspect routing)

The interspect route calls `AddInterspectEvent` with `payload.AgentName`, but does not validate it is non-empty. `interspect_events.agent_name` has a `NOT NULL` constraint, so an empty-payload `--context='{}'` will cause a SQL error.

**Recommendation:** Add `if payload.AgentName == ""` validation before calling `AddInterspectEvent`.

### P2-4: Migration guard `currentVersion >= 20` excludes databases at v1-v19

**Location:** Task 2 (migration block)

Databases at versions 1-19 will not get the migration block. They rely on `schema.sql` to create the table (see P0-2). If `schema.sql` is properly updated, this is fine. But if `schema.sql` is not updated (current plan omission), databases at versions 1-19 that migrate directly to v24 will skip the review_events creation entirely.

**Recommendation:** This is resolved by fixing P0-2. The guard `currentVersion >= 20` is appropriate since the baseline was established at v20.

---

## P3 Observations

### P3-1: event_type hardcoded in UNION ALL

The UNION ALL uses `'disagreement_resolved' AS event_type` for all review events. If future review event types are added, this will misrepresent them. Consider adding an `event_type` column to `review_events` for forward compatibility.

### P3-2: RESOLVED_FINDINGS and DISMISSAL_REASONS arrays referenced but not defined

Task 7's shell script references `${RESOLVED_FINDINGS[$FINDING_ID]}` and `${DISMISSAL_REASONS[$FINDING_ID]}` as bash associative arrays "set by Step 3." The plan does not show how these are populated. The implementer will need to trace through the existing resolve.md to find or create these arrays.

### P3-3: Architectural inconsistency: review_events in UNION ALL vs interspect_events not in UNION ALL

Review events and interspect events are closely related (both are profiler/evidence events). Interspect events are queried via a separate `ListInterspectEvents` path and are NOT in the unified UNION ALL stream. The plan adds review events to the UNION ALL, creating an inconsistency. This is related to P0-1 and P1-3.

---

## Summary of Required Actions

| Priority | Count | Key Action |
|---|---|---|
| P0 | 2 | Fix UNION ALL field loss (use direct query or composite JSON); add review_events to schema.sql |
| P1 | 4 | Resolve PRD/plan discrepancy on replay inputs; fix sinceInterspect bug; use direct query path; document parameter ordering |
| P2 | 4 | Consider dedup constraint; validate empty agents_json; validate interspect agent_name; migration guard is fine if schema.sql fixed |
| P3 | 3 | Forward-compatibility notes; plan completeness gaps |
