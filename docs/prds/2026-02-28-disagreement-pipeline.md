# PRD: Disagreement → Resolution → Routing Signal Pipeline

**Bead:** iv-5muhg
**Date:** 2026-02-28

## Problem

When review agents disagree on finding severity, the disagreement is detected (interflux synthesis Rules 4-5 produce `severity_conflict` in findings.json) and the human resolution is recorded (intertrust `_trust_record_outcome()`), but nothing feeds that resolution as a routing signal to Interspect. The learning loop described in PHILOSOPHY.md ("disagreement at T, human resolution at T+1, routing signal at T+2") is broken at T+1→T+2.

## Solution

Wire the pipeline end-to-end using intercore's event bus: clavain:resolve emits a `disagreement_resolved` event when an impact-changing resolution occurs, and interspect's cursor consumer picks it up to create evidence records that inform routing overrides.

## Features

### F1: `disagreement_resolved` event type in intercore
**What:** Add a new `SourceReview` constant and `review_events` table to the intercore event schema, following the same pattern as `interspect_events`.
**Acceptance criteria:**
- [x] New `SourceReview = "review"` constant in `internal/event/event.go`
- [x] `ReviewEvent` struct with fields: ID, RunID, FindingID, Agents (JSON map of agent→severity), Resolution (accepted/discarded/deferred), DismissalReason (agent_wrong/deprioritized/already_fixed/not_applicable — required when Resolution=discarded), ChosenSeverity, Impact (decision_changed/severity_overridden), SessionID, ProjectDir, Timestamp
- [x] `AddReviewEvent` method on `event.Store` — follows same pattern as `AddInterspectEvent`
- [x] `review_events` table created via schema migration (new `PRAGMA user_version`)
- [x] Review events queried via dedicated `ListReviewEvents` (not UNION ALL — matches interspect_events pattern); cursor tracking gets `sinceReview` field
- [x] Replay input entry created for each review event (consistent with dispatch/coordination patterns)
- [x] Existing tests pass; new unit tests for `AddReviewEvent` and cursor integration

### F2: `ic events emit` CLI subcommand
**What:** Add an `emit` subcommand to `ic events` so external producers (shell scripts in clavain:resolve) can write events to the kernel event store without Go code.
**Acceptance criteria:**
- [x] `ic events emit --source=review --type=disagreement_resolved --context='{"finding_id":"...","agents":{"fd-arch":"P1","fd-quality":"P2"},...}'` writes a review event via `AddReviewEvent`
- [x] `--run`, `--session`, `--project` flags accepted (optional, default to env vars `$IC_RUN_ID`, `$CLAUDE_SESSION_ID`, `$PWD`)
- [x] `--context` accepts JSON string; validates it parses before insertion
- [x] Validates `--source` is emittable; rejects unsupported sources with exit code 3
- [x] Prints the event ID on success, exits 0
- [x] Integration test: emit roundtrip confirms event IDs are monotonically increasing + error handling

### F3: Emit logic in clavain:resolve
**What:** Extend clavain:resolve Step 5 to detect `severity_conflict` on resolved findings, apply the impact gate, and emit via `ic events emit`.
**Acceptance criteria:**
- [ ] After recording trust feedback, check each resolved finding for `severity_conflict` field in `.clavain/quality-gates/findings.json`
- [ ] Impact gate: only emit when the resolution "changed a decision" — finding was discarded despite having P0/P1 severity from at least one agent, OR was accepted when the majority severity was lower
- [ ] Call `ic events emit --source=review --type=disagreement_resolved --context=<JSON>` with the disagreement payload
- [ ] Silent fail-open: if `ic` binary not found or emit fails, log warning and continue (same pattern as existing trust feedback)
- [ ] No change to existing trust feedback behavior — emit is additive, runs after `_trust_record_outcome`

### F4: Interspect cursor consumer for `disagreement_resolved` events
**What:** Extend interspect's event consumer to handle `disagreement_resolved` events and convert them to evidence records.
**Acceptance criteria:**
- [ ] `lib-interspect.sh` has new function `_interspect_process_disagreement_event` that parses the review event payload
- [ ] For each agent whose severity was overridden by the resolution, call `_interspect_insert_evidence` with: agent name, type `"disagreement_override"`, the resolution context, and the project
- [ ] Evidence records include finding_id, agent's severity vs chosen severity, and resolution outcome
- [ ] `override_reason` mapping: `dismissal_reason=agent_wrong` → `override_reason="agent_wrong"`; `dismissal_reason=deprioritized` → `override_reason="deprioritized"` (does NOT count toward routing override threshold); `dismissal_reason=already_fixed` → `override_reason="stale_finding"` (does NOT count); `resolution=accepted` with severity override → `override_reason="severity_miscalibrated"`
- [ ] Existing `_interspect_classify_pattern` naturally picks up `disagreement_override` evidence (counts by agent, not by type)
- [ ] Consumer polls `ic events tail --consumer=interspect-disagreement --since-review=<cursor>` for review events
- [ ] When accumulated overrides cross routing-eligibility threshold (≥80%), existing `_interspect_apply_propose` handles it — no new routing logic needed

## Non-goals

- **Automatic routing override proposals** — Existing interspect proposal flow handles this. We just feed it data.
- **Configurable impact gate threshold** — Hardcode the heuristic (P0/P1 involvement + decision change). Make configurable only if tuning is needed.
- **Handling never-resolved disagreements** — If a finding with severity_conflict is never resolved, no event emits. No timeout needed.
- **Batch evidence insertion** — Per-event is fine at current volume.
- **Real-time event streaming** — Cursor polling at 500ms is sufficient.
- **Disagreement UI** — severity_conflict in findings.json and Conflicts section in summary.md are sufficient.

## Dependencies

- **iv-r6mf** (closed): Interspect routing-overrides.json schema + flux-drive reader
- **intercore Go toolchain**: `go build` with `modernc.org/sqlite`
- **interflux synthesis**: `severity_conflict` field in findings.json (Rules 4-5)
- **intertrust**: `_trust_record_outcome()` in `lib-trust.sh`
- **interspect**: `_interspect_insert_evidence()` and cursor consumer in `lib-interspect.sh`

## Open Questions

None blocking — all resolved during brainstorm and validated against codebase.
