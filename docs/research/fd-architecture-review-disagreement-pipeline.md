# fd-architecture Review: Disagreement Pipeline Implementation Plan

**Date:** 2026-02-28
**Plan:** `docs/plans/2026-02-28-disagreement-pipeline.md`
**PRD:** `docs/prds/2026-02-28-disagreement-pipeline.md`
**Verdict:** NEEDS_ATTENTION (3 P1, 4 P2, 3 P3)

## Executive Summary

The Disagreement Pipeline plan wires a T/T+1/T+2 learning loop: interflux detects disagreement, clavain:resolve captures resolution and emits a kernel event, interspect consumes it as evidence for routing overrides. The overall architecture is sound -- event-driven via intercore, cursor-based consumer in interspect, fail-open shell integration. However, three P1 issues must be addressed before implementation to avoid implementation failures and data-loss bugs.

## Methodology

Reviewed all files referenced by the plan and PRD against the actual codebase:

- **Event system:** `core/intercore/internal/event/event.go`, `store.go`, `replay_capture.go`
- **Migration system:** `core/intercore/internal/db/db.go`, `schema.sql`, `migrator.go`, `migrations/020_baseline.sql`, `migrations/023_audit_trace_id.sql`
- **CLI layer:** `core/intercore/cmd/ic/events.go`, `main.go`
- **Shell integration:** `os/clavain/commands/resolve.md`
- **Consumer:** `interverse/interspect/hooks/lib-interspect.sh` (specifically `_interspect_consume_kernel_events`, `_interspect_insert_evidence`, `_interspect_classify_pattern`)

---

## Findings

### [P1] Task 7: `RESOLVED_FINDINGS` and `DISMISSAL_REASONS` arrays do not exist in resolve.md

**Location:** Plan Task 7, Step 5b shell code

Task 7's shell code references `${RESOLVED_FINDINGS[$FINDING_ID]}` and `${DISMISSAL_REASONS[$FINDING_ID]}` as bash associative arrays that are expected to be populated by Step 3 of the resolve command. These variables do not exist anywhere in the clavain codebase:

```bash
# From the plan -- these are undefined:
OUTCOME="${RESOLVED_FINDINGS[$FINDING_ID]:-}"
DISMISSAL_REASON="${DISMISSAL_REASONS[$FINDING_ID]:-agent_wrong}"
```

The current Step 5 ("Record Trust Feedback") does not use tracking arrays either. It iterates findings from `findings.json` and infers outcomes by examining what changed. Step 3 ("Implement") spawns parallel resolver agents -- it does not populate any tracking structures.

**Recommendation:** Redesign Step 5b to infer outcomes the same way Step 5 does -- by examining the working tree state after resolution -- rather than introducing new internal state to the resolve command. This avoids coupling the new feature to resolve's internal workflow.

### [P1] Task 2: Plan misses `schema.sql` update

**Location:** Plan Task 2, file list

Task 2 lists two files: `db.go` and `migrations/020_baseline.sql`. But the codebase has a critical third file: `core/intercore/internal/db/schema.sql`, which is embedded via `//go:embed schema.sql` (db.go line 18) and applied during `Migrate()` (db.go line 357).

The migration code path is:
1. `Migrate()` reads `PRAGMA user_version` inside a transaction
2. Applies conditional migration blocks (v5->v6, v7->v8, etc.) for existing databases
3. **Always applies `schemaDDL` (from `schema.sql`)** via `tx.ExecContext(ctx, schemaDDL)` at line 357
4. Sets `PRAGMA user_version = currentSchemaVersion`

For a fresh database (version 0), step 2's guards will not match, so only step 3 creates tables. If `schema.sql` lacks `review_events`, fresh databases will not have the table.

The `migrations/020_baseline.sql` is used by the separate `Migrator` system (migrator.go), which is an alternative path. The CLI currently uses `d.Migrate(ctx)` (the db.go path), making `schema.sql` the critical file for fresh installs.

**Recommendation:** Add `review_events` DDL to both `schema.sql` AND `020_baseline.sql`. Also create `024_review_events.sql` for the Migrator additive path.

### [P1] Task 8: Data loss through UNION ALL field mapping -- `chosen_severity`, `impact`, `dismissal_reason` are lost

**Location:** Plan Task 4 (UNION ALL query) and Task 8 (consumer)

The `Event` struct has a fixed set of fields: `ID`, `RunID`, `Source`, `Type`, `FromState`, `ToState`, `Reason`, `Envelope`, `Timestamp`. Task 4's UNION ALL maps review_events as:

| review_events column | Event struct field |
|---|---|
| `finding_id` | `FromState` |
| `resolution` | `ToState` |
| `agents_json` | `Reason` |
| `chosen_severity` | **NOT MAPPED** |
| `impact` | **NOT MAPPED** |
| `dismissal_reason` | **NOT MAPPED** |

Task 8's consumer code then tries to reconstruct these fields:

```bash
review_payload=$(echo "$line" | jq -c '{
    finding_id: .from_state,
    resolution: .to_state,
    agents_json: .reason,
    chosen_severity: "",      # <-- always empty!
    impact: "",               # <-- always empty!
    dismissal_reason: ""      # <-- always empty!
}')
```

But `_interspect_process_disagreement_event` depends on non-empty `chosen_severity` and `impact`:
- Line 793: `[[ -z "$finding_id" || -z "$resolution" ]] && return 0` -- passes
- Line 821: `[[ "$agent_severity" == "$chosen_severity" ]]` -- compares against empty string, so NO agent gets skipped, creating spurious evidence for ALL agents including those whose severity was correct
- Lines 797-808: `override_reason` logic checks `$impact == "severity_overridden"` -- this will never be true since impact is always empty

This means the consumer will either: (a) create evidence records for ALL agents (including those whose severity was correct), or (b) create evidence records with empty `override_reason`, corrupting the evidence base.

**Recommendation:** Do not route review events through the UNION ALL. Instead, have the interspect consumer call `ListReviewEvents` directly (via a new `ic events tail --source=review` flag or a dedicated `ic review-events list` subcommand). This preserves all fields without lossy mapping through the generic `Event` struct.

Alternative: Pack `chosen_severity`, `impact`, and `dismissal_reason` into the `reason` JSON blob alongside `agents_json` in the UNION ALL query. The consumer would then extract all fields from a single JSON object in the `reason` field.

---

### [P2] UNION ALL sustainability and growing function signatures

**Location:** `core/intercore/internal/event/store.go` lines 68, 108

After this change, `ListEvents` will need 5 cursor parameters and `ListAllEvents` will need 4. The function signatures are already long:

```go
// Current:
func (s *Store) ListEvents(ctx, runID, sincePhaseID, sinceDispatchID, sinceDiscoveryID, limit)

// After plan:
func (s *Store) ListEvents(ctx, runID, sincePhaseID, sinceDispatchID, sinceDiscoveryID, sinceReviewID, limit)
```

Additionally, the cursor JSON tracks `sinceInterspect` but it is NOT used in the UNION ALL queries (interspect_events have their own `ListInterspectEvents` path). This means the cursor has a phantom field that is never consumed by `ListEvents`/`ListAllEvents`.

Note also that `coordination_events` uses `id > 0` (hardcoded) in both queries rather than a parameterized cursor, so cursor tracking is already inconsistent across event types.

**Recommendation:** Consider refactoring to a cursor struct parameter in a follow-up. For now, the plan's approach is consistent with existing conventions.

### [P2] `ic events emit` source validation vs. routing mismatch

**Location:** Plan Task 5, lines 502-510 vs. 538-584

The emit command validates that `--source` is one of 6 known constants (phase, dispatch, interspect, discovery, coordination, review), but the routing switch only handles 2 (review, interspect). This means `--source=phase` passes validation at line 504 but fails at the routing switch at line 582 with "source not yet supported for emit."

This creates a confusing UX: a user sees their source is "known" but then gets rejected.

**Recommendation:** Only validate sources that are actually emittable. Replace the broad validation switch with one that matches the routing switch exactly. Add a clear error message listing supported emit sources.

### [P2] Shell-to-Go boundary uses inline JSON in CLI arguments

**Location:** Plan Task 7 shell code

The resolve command constructs JSON via `jq -n` and passes it as `--context="$CONTEXT"`. While this works for typical payloads, it has two risks:

1. **Shell quoting fragility:** If any field contains characters that interact with shell quoting (unlikely with current controlled agent names, but possible with finding IDs from external tools), the JSON could be corrupted.
2. **Discoverability:** The `--context` flag accepts an opaque JSON blob whose schema is defined nowhere in the CLI help. Future callers must reverse-engineer the expected structure from the switch case.

**Recommendation:** Consider supporting `--context-file=/path/to/file` or `--context=-` (read from stdin) as a robustness improvement. Not blocking.

### [P2] Task 8 UNION ALL field mapping creates semantic mismatch

**Location:** Plan Task 4 and Task 8

Even if the data-loss issue (P1 above) is resolved by packing extra fields into the `reason` JSON, the fundamental semantic mismatch remains: `finding_id` mapped to `from_state`, `resolution` to `to_state`. Code reading the UNION ALL output must know the mapping for each source type.

The `Event` struct's comment says `FromState` is "from_phase or from_status" -- adding "or finding_id" further dilutes the semantic meaning. This is an existing pattern (discovery_events maps `discovery_id` to `run_id`), but adding review events increases the maintenance burden.

---

### [P3] PRD/plan inconsistency on replay input

**Location:** PRD F1 acceptance criteria vs. Plan Task 3

The PRD states: "Replay input entry created for each review event (consistent with dispatch/interspect patterns)." The plan's `AddReviewEvent` does not call `insertReplayInput`. Looking at existing code:

- `AddDispatchEvent` -- calls `insertReplayInput` (yes)
- `AddCoordinationEvent` -- calls `insertReplayInput` (yes)
- `AddInterspectEvent` -- does NOT call `insertReplayInput` (no)

The PRD's parenthetical "consistent with dispatch/interspect patterns" is self-contradictory since those patterns differ. Since review events carry a `run_id`, replay capture would be meaningful for deterministic replay.

**Recommendation:** Add `insertReplayInput` to `AddReviewEvent` for consistency with dispatch/coordination. Update PRD to reference "dispatch/coordination patterns" instead of "dispatch/interspect patterns."

### [P3] Two migration systems -- plan only addresses the active one

The codebase has two migration paths:
1. `db.go` `Migrate()` with inline SQL + `schemaDDL` (currently used by CLI)
2. `migrator.go` `Migrator` with `migrations/*.sql` files (newer, not yet the primary path)

The plan modifies both `db.go` and `020_baseline.sql`, covering both systems for the migration block and baseline respectively. However, it does not create `024_review_events.sql` in the `migrations/` directory. Without this file, a database at version 23 migrated via the `Migrator` path will not get the review_events table.

This is a minor gap since the CLI currently uses `d.Migrate(ctx)`, but should be addressed for forward compatibility.

### [P3] `AddReviewEvent` has 10 positional string parameters

The function signature follows the existing pattern (`AddInterspectEvent` has 7 string params) but pushes readability limits. A struct parameter would be cleaner but is not the established convention.

### [P3] Module coupling is appropriately loose

The three-module coupling (clavain:resolve -> intercore -> interspect) is well-designed:
- **clavain:resolve** is fire-and-forget to the event bus (`|| true`)
- **intercore** is a dumb pipe (write event, read events via cursor)
- **interspect** is an independent consumer (polls events, creates evidence)

Each module can fail independently. The `command -v ic &>/dev/null || return 0` guard in interspect and the `|| true` in resolve ensure graceful degradation. No coupling concerns.

---

## Summary of Required Changes

| Priority | Finding | Required Action |
|---|---|---|
| P1 | `RESOLVED_FINDINGS`/`DISMISSAL_REASONS` undefined | Redesign Task 7 to infer outcomes from working tree state |
| P1 | Missing `schema.sql` update | Add review_events DDL to `schema.sql` in Task 2 file list |
| P1 | Data loss through UNION ALL | Use `ListReviewEvents` directly or pack all fields into reason JSON |
| P2 | Growing function signatures | Note for future refactoring to cursor struct |
| P2 | Emit validation/routing mismatch | Unify validation and routing switches in Task 5 |
| P2 | Inline JSON in CLI arguments | Consider stdin/file input support |
| P2 | Semantic field mapping | Consider separate query path for review events |
| P3 | Replay input inconsistency | Add `insertReplayInput` to `AddReviewEvent` |
| P3 | Missing `024_review_events.sql` | Create migration file for Migrator path |
| P3 | Positional params / coupling | Observation only |
