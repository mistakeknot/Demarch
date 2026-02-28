# Architecture Review: Disagreement → Resolution → Routing Signal Pipeline PRD

**Reviewed:** 2026-02-28
**PRD:** `/home/mk/projects/Demarch/docs/prds/2026-02-28-disagreement-pipeline.md`
**Bead:** iv-5muhg
**Reviewer role:** Flux-drive Architecture & Design Reviewer

---

## Summary

The PRD wires a T+1 → T+2 signal path that the philosophy calls out by name. The overall direction is sound, and the dependency list is accurate — every named component was verified to exist. Three structural problems need resolution before implementation begins. One is a schema boundary violation (the table the PRD assumes exists in the event UNION does not). One is a hidden contract gap that will silently corrupt cursor state. One is a missing field in the intermediate findings.json schema that makes the detection point in clavain:resolve permanently inert.

---

## 1. Boundaries & Coupling

### 1.1 Layer Topology — Passes

The flow direction is correct: L2 shell (clavain:resolve) calls L1 kernel CLI (`ic events emit`) which writes to the L1 event store, and L2 plugin consumer (interspect) reads it back via cursor. No upward dependencies from L1 into L2 are introduced.

The existing key dependency chains from `AGENTS.md` are untouched:

```
Clavain (L2) → interflux → intersearch   [untouched]
Clavain (L2) → intertrust               [untouched]
```

The new edge is `Clavain (L2) → intercore (L1)` via shell-out to `ic`, which already exists implicitly everywhere clavain calls `ic`. Not a new coupling category.

### 1.2 MUST-FIX: `EmitExternal()` Targets a Table That Is Not in the Event UNION

F2 specifies a new `event.Store.EmitExternal()` method. The PRD states: "Existing `ListEvents` and `ListAllEvents` queries return the new events without changes (they're just rows in the same table)."

This claim requires verification against the actual store code, and verification shows a problem.

`ListAllEvents` in `/home/mk/projects/Demarch/core/intercore/internal/event/store.go` (lines 113-143) unions exactly four tables:

```go
// UNION in ListAllEvents:
//   phase_events        (sincePhaseID cursor slot)
//   dispatch_events     (sinceDispatchID cursor slot)
//   discovery_events    (sinceDiscoveryID cursor slot)
//   coordination_events (no cursor — hardcoded id > 0)
```

`interspect_events` is an entirely separate table with its own `AddInterspectEvent` / `ListInterspectEvents` methods and `MaxInterspectEventID`. It is not part of the UNION. If `EmitExternal()` writes to `interspect_events`, the F1 acceptance criterion "Event appears in `ic events tail` output" silently fails because `cmdEventsTail` calls `ListAllEvents`.

If `EmitExternal()` introduces a fifth table (e.g., `review_events`), that table must be added to both `ListEvents` and `ListAllEvents`, a new cursor field must be added to the cursor state JSON, and the schema version must increment from 23 to 24. The current cursor payload is:

```json
{"phase":0,"dispatch":0,"interspect":0,"discovery":0}
```

The `interspect` field in that JSON is not the `interspect_events` table cursor — it is the cursor slot used by the consumer for a different purpose. Adding a `review` field without migrating existing registered cursors will cause those cursors to read zero for the new field on first access, processing all historical review events again.

The PRD must pick one of two concrete options:

**Option A — Use dispatch_events (zero schema change):** `EmitExternal()` inserts into `dispatch_events` with `dispatch_id="review:external"`, `run_id` from `--run`, `event_type` from `--type`, and payload serialized into `reason` (truncated to 500 chars) or a new `payload_json` column via a one-column ALTER TABLE migration. The event appears in `ListAllEvents` immediately. The `sinceDispatch` cursor slot tracks it. Tradeoff: `reason` is semantically strained; a `payload_json` column alteration is the cleaner path at minimal migration cost.

**Option B — New review_events table (schema v24):** New table `review_events (id, source TEXT, event_type TEXT, run_id TEXT, payload_json TEXT, envelope_json TEXT, created_at INTEGER)`. Added to both `ListAllEvents` and `ListEvents` UNIONs as a fifth source. A `sinceReview` cursor field added with zero-default for existing cursors. Schema bumps to v24. This is the cleanest long-term design.

The "just rows in the same table" claim in F2 must be replaced with a concrete decision on which table and a verification that it appears in `ListAllEvents`.

### 1.3 MUST-FIX: `severity_conflict` Is Not Confirmed in findings.json — Detection Point Is Unverified

F3: "When resolving a finding that has `severity_conflict` metadata..."

The resolve command sources its data from `.clavain/quality-gates/findings.json`. The interflux synthesis spec (deduplication Rule 4, documented in `docs/research/explore-flux-drive-codebase.md`) says conflicting severity is "recorded in `severity_conflict`." However, the `findings.json` schema documented in `/home/mk/projects/Demarch/interverse/interflux/skills/flux-drive/phases/synthesize.md` (Step 3.4a) specifies these finding fields:

```json
{
  "id": "P0-1",
  "severity": "P0",
  "agent": "fd-architecture",
  "section": "Section Name",
  "title": "Short description",
  "convergence": 3
}
```

There is no `severity_conflict` key in that schema. The synthesis subagent (`intersynth:synthesize-review`) writes `findings.json`. If `severity_conflict` is not written into that file, clavain:resolve has no detection point, and F3 silently never fires.

This is a contract gap between interflux's synthesis subagent and clavain:resolve. The PRD lists both as dependencies but does not identify the intermediate contract.

Before implementation: verify whether `intersynth:synthesize-review` writes `severity_conflict` to `findings.json`. If it does not, either (a) extend the findings.json schema to include it and update intersynth to emit it, or (b) change F3's detection mechanism to another source. This gap must be closed or F3 produces nothing and the entire pipeline is inert.

### 1.4 WATCH: Invisible Failure Mode in Fire-and-Forget Emit

F3: "The emit is fire-and-forget — resolve does not fail if the event emission fails (log warning only)."

This is architecturally correct. The concern is operational: if `ic` is not on PATH, the DB path is wrong, or schema has drifted, the event is silently dropped with no observable signal. Over time this creates a systematic gap in interspect's evidence without any way to diagnose it.

The existing trust feedback block in `resolve.md` (lines 84-91) handles unavailability gracefully using an explicit availability check:

```bash
TRUST_PLUGIN=$(find ~/.claude/plugins/cache -path "*/intertrust/*/hooks/lib-trust.sh" 2>/dev/null | head -1)
if [[ -n "$TRUST_PLUGIN" ]]; then ...
```

The emit logic should follow the same pattern. A one-line check after emit (`ic events tail --all --limit=1 2>/dev/null` or checking exit code) would make the success case observable without adding a blocking failure path. Not a blocker, but worth an implementation note.

---

## 2. Pattern Analysis

### 2.1 `EmitExternal()` Naming and Source Allowlisting

The method name `EmitExternal()` is ambiguous — all existing Store methods are called externally. The intent is "emitted by an untrusted CLI caller rather than an internal subsystem."

More importantly, the method accepts an arbitrary `source` string from the command line. All existing store methods use typed constants (`SourcePhase`, `SourceDispatch`, etc.). F1 specifies `--source=review` as a string flag but does not enumerate valid values or specify rejection of invalid ones. If `ic events emit --source=phase --type=advance` can write a synthetic phase event, that is an event integrity problem.

A source allowlist for CLI-originated events must be part of the implementation. Valid CLI-emit sources should be an enumerated set distinct from internal source constants. "review" is a new category. "phase", "dispatch", "coordination", "discovery", and "interspect" must be refused with exit code 3.

### 2.2 Payload Column Semantics

F2 introduces `DisagreementPayload` with rich structured data (agents map, chosen_severity, impact, session_id, project). The PRD does not specify which column stores this.

The existing `dispatch_events` schema has:
- `reason TEXT` — intended for a short human-readable string
- `envelope_json TEXT` — the Gridfire provenance envelope (CallerIdentity, TraceID, CapabilityScope, artifact refs)

Neither is the right home for a structured application payload. Storing `DisagreementPayload` in `reason` is semantically wrong. Storing it in `envelope_json` alongside provenance mixes application data with infrastructure provenance and breaks `ParseEnvelopeJSON` assumptions.

If Option B (new table) is chosen, a `payload_json TEXT` column is the correct home. If Option A (dispatch_events) is chosen, a one-column migration adding `payload_json` to `dispatch_events` is the cleaner path than overloading `reason`.

### 2.3 F4 Consumer Handling — May Require No New Code

The existing `_interspect_consume_kernel_events()` in `lib-interspect.sh` (verified at lines 2013-2056) reads all events from `ic events tail --all --consumer=interspect-consumer` and calls `_interspect_insert_evidence` for every event:

```bash
event_source=$(echo "$line" | jq -r '.source // empty')
event_type=$(echo "$line" | jq -r '.type // empty')
_interspect_insert_evidence \
    "$session_id" "kernel-${event_source}" "${event_type}" \
    "" "$enriched_context" "interspect-consumer"
```

If the new event has `source="review"` and appears in `ListAllEvents` (i.e., the table routing fix in 1.2 is applied), this consumer will already pick it up as `source="kernel-review"` and `event="disagreement_resolved"`. The cursor will advance. The evidence row will be created.

F4 says "converts event payload to evidence row via `_interspect_insert_evidence()` ... `override_reason` derived from resolution outcome." The current generic path passes `override_reason=""` always. If non-empty `override_reason` is required for the routing proposal flow to work correctly, the consumer needs a conditional branch to extract it from the payload:

```bash
if [[ "$event_source" == "review" && "$event_type" == "disagreement_resolved" ]]; then
    override_reason=$(echo "$line" | jq -r '.payload_json | fromjson | .impact // ""' 2>/dev/null)
    _interspect_insert_evidence "$session_id" "kernel-review" "disagreement_resolved" \
        "$override_reason" "$enriched_context" "interspect-consumer"
fi
```

The PRD must clarify whether the generic path (empty override_reason) is sufficient or whether distinct handling is needed. If generic suffices, F4 may require zero new shell code once the table routing fix is applied. If distinct handling is needed, spec the extraction expression.

---

## 3. Simplicity & YAGNI

### 3.1 `ic events emit` Is Correctly Scoped

The CLI subcommand is the right mechanism. It decouples shell plugins from Go internals, makes the event bus accessible to any future script, and follows the existing CLI-first design decision documented in intercore's `CLAUDE.md` ("CLI only (no Go library API in v1) — bash hooks shell out to `ic`"). The flag set is minimal and sufficient. No objection.

### 3.2 NULL Handling for `--run` Must Match Existing Convention

F1: "run is optional (global events allowed)." The existing store uses `NULLIF(?, '')` to convert empty string to NULL for `run_id`. The new command must follow the same convention — not store `""` in `run_id`. The `ListEvents` query filters `WHERE run_id = ?`; an empty string stored as `""` would not be returned correctly. Worth a unit test for the NULL/empty-string boundary.

### 3.3 Hardcoded Impact Gate — Correct YAGNI

The non-goal on configurable thresholds is correctly justified. There is no second concrete consumer that would need a different threshold. The heuristic (discard ≥P1, or accept with severity override) is the correct starting point.

### 3.4 `DisagreementPayload` Field Names Must Be Exported

F2 defines the struct with lowercase field names (Go notation would make them unexported). Since the payload must round-trip through JSON for `ic events emit --payload='<json>'`, all fields must be exported with `json:` struct tags. The PRD uses lowercase as informal notation; the implementation must not transcribe it literally.

---

## 4. Risk Register

| # | Risk | Severity | Action |
|---|------|----------|--------|
| R1 | `EmitExternal()` targets wrong or absent table; `ic events tail` does not show the event; F1 AC silently fails | High | Must-fix: specify target table; verify it is in `ListAllEvents` UNION |
| R2 | `severity_conflict` not in findings.json schema; F3 detection never fires; entire pipeline produces nothing | High | Must-fix: verify intersynth emits this field or extend the schema |
| R3 | CLI source allowlist absent; `--source=phase` could inject synthetic phase events | Medium | Should-fix: enumerate valid CLI sources in `EmitExternal`; exit code 3 on invalid |
| R4 | Cursor field migration not specified; existing interspect-consumer cursor re-reads all historical review events on first session after deploy | Medium | Should-fix: specify zero-default migration for new cursor field |
| R5 | F4 generic consumer path may be sufficient; F4 may overestimate required code | Low | Clarify: state whether empty `override_reason` is acceptable |
| R6 | `DisagreementPayload` lowercase fields break JSON marshal | Low | Fix at implementation: uppercase exported fields with json tags |

---

## 5. Recommended Changes to the PRD

### Must-fix (block implementation)

**F2 — Specify the target table:**

Replace "event.Store.EmitExternal() — a new method for CLI-originated events" with a concrete target:

- Option A: Insert into `dispatch_events` (no new table; add `payload_json TEXT` column via ALTER TABLE in schema v24 migration; update dispatch_events INSERT and UNION columns).
- Option B: New `review_events` table in schema v24; added to `ListAllEvents` and `ListEvents` UNIONs; `sinceReview` cursor field with zero-default.

Update F1 AC "Event appears in `ic events tail`" to explicitly state which table/source field will be returned.

**F3 — Verify the findings.json contract:**

Add to the Dependencies section: `intersynth:synthesize-review must write severity_conflict map to findings.json per-finding`. Either confirm it already does, or add a sub-feature: "extend findings.json schema with severity_conflict field (map[string]string) and update intersynth to emit it."

### Should-fix (before shipping)

**F1 — Source allowlist:** Valid `--source` values for CLI emit are enumerated (initially just "review"). Reject "phase", "dispatch", "coordination", "discovery", "interspect". Exit code 3 on invalid source.

**F2/F4 — Cursor migration path:** "Existing interspect-consumer cursors will have no `sinceReview` key; consumer defaults to 0 (re-reads from origin). This is acceptable for the first deploy — review events are sparse and reprocessing them is idempotent (duplicate evidence rows are harmless). Document this in the implementation notes."

**F4 — Specify override_reason handling:** State whether the generic consumer path (empty override_reason) is sufficient for routing proposals, or whether the consumer must extract `impact` from `DisagreementPayload` into `override_reason`.

---

## 6. What Is Correct and Should Not Change

Using the existing cursor mechanism is the right integration seam. Do not introduce a poll loop, a separate watch process, or a direct DB write from the shell skill.

Fire-and-forget semantics for the emit call in clavain:resolve are correct. The pipeline is a learning loop, not a control path. Missing one event does not break the system; the overall evidence base degrades gracefully.

Routing through the event bus rather than a direct function call from clavain to interspect is the right decoupling. clavain:resolve does not need to know interspect exists. The event is the contract.

The `run` flag being optional correctly enables global disagreement events not tied to a specific run — severity conflicts span agents that may have run under different dispatches.

The impact gate heuristic is appropriate signal filtering. Without a gate, every resolved finding (including P3 nits with no conflict) would emit events, flooding interspect's evidence table with low-value rows.
