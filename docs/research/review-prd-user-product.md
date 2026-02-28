# User/Product Review: Disagreement Pipeline PRD

**Document reviewed:** `/home/mk/projects/Demarch/docs/prds/2026-02-28-disagreement-pipeline.md`
**Bead:** iv-5muhg
**Reviewer role:** UX, product, and flow analyst
**Date:** 2026-02-28

---

## Primary User and Job

The primary user is the human-above-the-loop engineer (currently: the platform author in a self-building mode). Their job at T+1 is: read a flagged disagreement finding in `/resolve`, decide whether to accept or discard it, and move on. They are not consciously "training Interspect" — they are resolving a finding. The pipeline must turn that incidental act into durable learning signal without adding cognitive overhead or changing the resolution flow at all.

Secondary consumer: Interspect itself, which reads the evidence records at T+2 to inform routing override proposals. Interspect has no UI — it is a silent background system.

---

## Overall Verdict

The scope is right for one iteration. The four features map tightly to the one broken link (T+1 -> T+2) without scope creep into the auto-proposal flow or the conflict detection logic. The non-goals list is disciplined. The acceptance criteria are mostly testable. There are three issues worth addressing before implementation: one schema gap that matters for measurement validity, one missing edge case in the emit logic, and one acceptance criterion that is not actually testable as written.

---

## Scope Evaluation

### Is the scope right for one iteration?

Yes. The PRD correctly identifies exactly one missing connection: the event bus between resolution and interspect, and builds exactly what is needed to wire it. Each feature (F1-F4) is independently mergeable and has a clear single responsibility.

The non-goals list is the strongest part of the PRD. Explicitly deferring configurable impact thresholds, batched insertion, and automatic routing override proposals prevents the "while we're here" expansion that would make this a multi-week item. Hardcoding the impact gate heuristic is the right call at current signal volume.

One minor scope note: F1 (`ic events emit`) is a general capability — it unlocks external producers beyond the disagreement pipeline. That is healthy reuse, not scope creep. But it does mean F1 carries slightly more surface area than the other features and deserves its own rollout verification before F3 depends on it.

---

## Acceptance Criteria Assessment

### F1: `ic events emit` — Largely testable

The five criteria are concrete and checkable:
- Event appears in `ic events tail` output — verifiable via CLI
- Payload validated as JSON before insertion — can test with malformed input and check exit code
- Source and type required, run optional — test missing flags
- Exit code 0 on success, prints event ID — verifiable

One gap: the criterion says "creates a durable event with Gridfire envelope" but the existing event schema contract (`contracts/events/event.json`) marks envelope as optional and has no `payload` field. The PRD introduces `--payload='<json>'` as a new field but the schema contract does not include it. If the event contract is `additionalProperties: false`, a payload field will either be silently dropped or cause a schema violation. This must be resolved before F1 ships: either add `payload` to the contract, or confirm the field is stored in a different column.

The current schema has: `id`, `run_id`, `source`, `type`, `from_state`, `to_state`, `reason`, `envelope`, `timestamp`. None of these carry arbitrary JSON payload. The `DisagreementPayload` struct described in F2 must land somewhere — and the contract needs to reflect it.

### F2: `DisagreementPayload` struct — Testable but has a measurement validity gap

The struct fields (`finding_id`, `agents`, `resolution`, `chosen_severity`, `impact`, `session_id`, `project`) are the right fields for routing signal generation. However, there is a known measurement validity finding (documented in `core/intercore/docs/research/fd-measurement-validity-review-interspect.md`, finding F-1) that directly applies here:

The `resolution` field (`"accepted"` | `"discarded"` | `"modified"`) does not distinguish between:
- "Finding was wrong" (true agent error — should penalize the low-severity agent)
- "Finding was right but cost/priority don't justify fixing it" (triage decision — neutral signal)
- "Finding was right, already addressed" (stale context — neutral signal)

If Interspect uses the `discarded` resolution value as a false-positive signal without this taxonomy, it will systematically misroute agents. This is not a nice-to-have: the F-1 finding explicitly recommends "This taxonomy should be part of the event schema, not derived after the fact."

Adding a `dismissal_reason` field to `DisagreementPayload` is the correct fix. The resolve skill already has the information available (the human must choose what to do with the finding), so collecting it requires adding one prompt or flag to the existing resolve flow — not a new user-facing step.

Proposed addition:
```
dismissal_reason: string   # "agent_wrong" | "deprioritized" | "already_fixed" | ""
                           # empty string when resolution = "accepted"
```

This field is optional in the event schema (empty for accepted findings) and only populated when `resolution = "discarded"`. It costs one extra decision from the user but makes the routing signal non-gameable.

The criterion `EmitExternal()` is testable. The criterion that events appear in `ListEvents` and `ListAllEvents` is testable.

### F3: Emit logic in clavain:resolve — Two gaps

Criteria 1 and 3 are testable (can simulate severity_conflict metadata, verify emit call, verify silence when not impact-changing).

**Gap A: What counts as impact-changing is underspecified.**

The criterion says: "discarded a >=P1 finding, or accepted with severity override." This needs one more branch: what if the human modifies severity during resolution (the `"modified"` resolution value from F2's schema)? Is a P2 -> P1 severity modification impact-changing? Is a P1 -> P2 demotion? The criterion should either enumerate the three cases explicitly or define "impact-changing" as a named function/predicate that can be tested in isolation.

**Gap B: The `findings.json` path assumption.**

The resolve command's Step 5 already guards: "Only emit when findings came from flux-drive review (check: `.clavain/quality-gates/findings.json` exists)." F3 inherits this guard, which is correct. But the acceptance criterion does not mention it. An implementer reading only the PRD would not know to add this guard, and would emit disagreement events for findings from PR comments or TODO resolution flows that have no `severity_conflict` metadata (those findings will simply not have the field, but the guard prevents confusion).

Add to F3's acceptance criteria: "Emit is only attempted when `.clavain/quality-gates/findings.json` is present (gate inherited from existing Step 5 trust feedback logic)."

**Gap C: Fire-and-forget failure logging.**

The criterion says "log warning only" on emit failure. The resolve command currently uses silent failures for trust feedback ("Silent failures: If lib-trust.sh is not found or any call fails, continue normally."). The PRD upgrades this to "log warning" — which is better. But the acceptance criterion should specify where the warning goes (stderr, a log file?) so it is verifiable. Without a destination, "log warning" is not testable.

### F4: Interspect consumer logic — Partially testable

Criteria 1 and 2 are testable (consumer recognizes the source/type, calls `_interspect_insert_evidence()`).

Criterion 3 has an ambiguity: "`override_reason` derived from resolution outcome." How is `override_reason` derived? Is `"accepted"` -> `"disagreement_accepted"`, `"discarded"` -> `"disagreement_discarded"`? This needs to be spelled out. The `_interspect_insert_evidence()` function signature takes `override_reason` as a positional argument — its value directly affects how Interspect classifies patterns. Leaving derivation unspecified means the implementer will make a choice that affects routing behavior, and the acceptance criterion cannot be verified without knowing the expected value.

Criterion 4 (cursor advances after processing) is testable via `ic events cursor list` before and after.

---

## Missing Edge Cases

### Edge case 1: The finding has `severity_conflict` but no `agents` attribution

The `DisagreementPayload.agents` field is `map[string]string` (agent_name -> severity). The synthesis spec shows `"severity_conflict": {"fd-architecture": "P1", "fd-quality": "P2"}`. However, the deduplication rules (Rules 4-5) preserve "all positions" — what if a finding came from a single agent who changed their own rating across synthesis stages? Or what if the severity_conflict map has only one entry (edge case in synthesis)? The payload struct and emit logic should handle a conflict map with < 2 entries without panicking or emitting misleading data.

### Edge case 2: `ic events emit` called before `ic events cursor register` for interspect-consumer

The interspect cursor registers lazily (only if `ic` is available and cursor doesn't already exist, during `_interspect_ensure_db`). If `ic events emit` fires a `disagreement_resolved` event before the cursor has been registered, the event is durable but the cursor starts at 0 — so on next poll, interspect will replay ALL events from the beginning, potentially double-inserting evidence rows that predate the disagreement event. The cursor registration idempotency check (`grep -q 'interspect-consumer'`) protects against double-registration, but not against consuming events that already produced evidence rows. If `_interspect_insert_evidence()` is not idempotent with respect to kernel_event_id, this is a silent double-counting bug. The PRD should either confirm that `_interspect_insert_evidence()` deduplicates on `kernel_event_id`, or add this guard to F4's acceptance criteria.

### Edge case 3: Findings resolved across multiple sessions

The `disagreement_resolved` event carries `session_id`, but a finding flagged in one sprint review might not be resolved until several sessions later (the human skips it at T+1, then picks it up at T+3). The `run_id` is optional (F1 criterion: "run is optional (global events allowed)"). If run is not populated, the interspect consumer's enriched context loses the trace linkage that connects the routing signal back to the original review run. At current session volumes this is tolerable, but the PRD should confirm the decision: when resolve emits without a run_id, what is the intended behavior? Explicitly noting this in the non-goals or as a known limitation would prevent a future session from treating this as a bug.

### Edge case 4: Resolution of `modified` severity — not fully handled

The `resolution` field includes `"modified"` as a value, but F3's impact gate only defines two conditions: "discarded a >=P1 finding" and "accepted with severity override." A `modified` resolution is a third state: the human neither accepted nor discarded, but changed the severity. This is impact-changing when the modification crosses a severity tier boundary (P2 -> P1), but not when within tier (P1 -> P1 with different sub-priority). The impact gate logic needs a third branch for `modified`.

---

## Flow Analysis

### Happy path

```
interflux synthesis produces finding with severity_conflict metadata
  -> clavain:resolve shows finding to human
  -> Human accepts or discards
  -> resolve detects severity_conflict, checks impact gate
  -> Impact-changing: calls ic events emit with DisagreementPayload
  -> ic events emit validates JSON, writes event to intercore.db
  -> Returns event ID (logged or discarded by resolve)
  -> [next session or same session] interspect_ensure_db runs
  -> _interspect_consume_kernel_events() polls with interspect-consumer cursor
  -> Sees new disagreement_resolved event
  -> Calls _interspect_insert_evidence() with derived override_reason
  -> Cursor advances
  -> Interspect's existing pattern classifier eventually runs
  -> Routing override proposed (existing flow, not in scope)
```

The happy path is complete and coherent. The decoupling via event bus is correct — resolve does not need to know about interspect.

### Error path: emit fails

F3 specifies fire-and-forget: resolve does not fail. The event is never written. Interspect never sees it. There is no retry, no dead-letter queue, no alert. At current volumes this is acceptable and consistent with the existing trust feedback design ("opportunistic, never blocking"). This tradeoff should be documented as a conscious decision, not left implicit.

### Error path: interspect consumer crashes mid-batch

The cursor advances after processing each event (per F4's criterion 4). If the consumer crashes between processing and cursor save, events are replayed. This requires `_interspect_insert_evidence()` to be idempotent — see Edge case 2 above. The PRD does not verify this.

### Cancellation path: human abandons resolve mid-session

If the human exits the Claude session after accepting some findings but before the session ends cleanly, trust feedback and event emission may not have fired. The existing resolve command Step 5 runs after commit — if the commit never happens, the emit never happens. This is consistent with existing behavior and acceptable.

### Missing state: finding with `severity_conflict` where both agents agree on `P0`

If two agents both rate a finding P0 but with different recommendation text (triggering Rule 5, not Rule 4), there is no `severity_conflict` metadata. F3 correctly gates on `severity_conflict` metadata — this is not a bug, it's the correct behavior. But it's worth documenting so a future session doesn't try to "fix" it by expanding the gate.

---

## Product Validation

### Does this directly address the stated problem?

Yes. The problem is a broken learning loop. The solution wires exactly the missing link (T+1 -> T+2) via the kernel event bus. The approach is consistent with PHILOSOPHY.md's "Receipts Close Loops" principle and the OODAR model — the disagreement event is a durable receipt that enables the Orient phase of the cross-session OODAR loop.

### Is the event-driven approach the right one?

Yes, for the reasons cited in the brainstorm: durability, replayability, decoupling, and alignment with the existing cursor consumer pattern. The alternative (a direct function call from resolve to interspect's lib-interspect.sh) would introduce a tight coupling between the OS layer and a companion plugin, and would not produce a durable receipt that could be queried, replayed, or audited independently.

### Is there scope creep?

No. The four features are strictly additive. The non-goals list correctly excludes automatic routing override proposals (interspect's existing flow handles that), configurable thresholds (hardcode first), unresolved disagreements (a non-event is not an event), and batching (per-event is fine).

### Measurable success signal

The PRD has no explicit success metric. For post-release validation, one verifiable signal would be: after 10 disagreement resolutions, `ic events tail --all | jq 'select(.type == "disagreement_resolved")' | wc -l` returns 10 (or fewer, if some resolutions were not impact-changing). A second signal: `sqlite3 .clavain/interspect/interspect.db "SELECT COUNT(*) FROM evidence WHERE event = 'disagreement_resolved'"` increases after disagreement resolutions. Neither requires new instrumentation — they use existing observability.

The PRD should add one explicit success criterion at the end: "After 5 impact-changing resolutions, `ic events tail --all` shows 5 `disagreement_resolved` events and the interspect evidence table shows 5 matching rows."

---

## Summary of Findings by Priority

### Must fix before implementation

**M1 — Schema contract mismatch (F1/F2):** The event contract (`contracts/events/event.json`) has no `payload` field and uses `additionalProperties: false`. The `DisagreementPayload` struct must be reflected in the schema contract, or the payload will be silently dropped or rejected. Resolve: add `payload` as an optional object field to the contract before shipping F1.

**M2 — Missing `dismissal_reason` in DisagreementPayload (F2):** Without a reason taxonomy distinguishing "agent was wrong" from "deprioritized" or "already fixed," Interspect will misclassify discarded findings as false positives. This is the same measurement validity gap documented in `fd-measurement-validity-review-interspect.md` finding F-1. Resolve: add `dismissal_reason: string` to the payload struct.

**M3 — `override_reason` derivation unspecified (F4):** The acceptance criterion says "derived from resolution outcome" without specifying the mapping. The implementer will make an undocumented choice that directly affects routing behavior. Resolve: enumerate the mapping in F4 (e.g., `"accepted"` -> `"disagreement_accepted"`, `"discarded"` -> `"disagreement_discarded_<dismissal_reason>"`).

### Should fix before implementation

**S1 — Impact gate missing `"modified"` branch (F3):** The `resolution: "modified"` value is in the schema but not covered by the impact gate logic. Resolve: define the third branch — "modified and severity changed across P-tier boundary" is impact-changing.

**S2 — `_interspect_insert_evidence()` idempotency not confirmed (F4):** If the cursor consumer replays events, double-counting evidence rows will corrupt Interspect's pattern analysis. Resolve: confirm or add idempotency guard keyed on `kernel_event_id`.

**S3 — Warning log destination unspecified (F3):** "Log warning" is not testable without a destination. Resolve: specify stderr with a `[resolve:warn]` prefix, consistent with existing hook logging conventions.

### Nice to have

**N1 — Add explicit success metric to the PRD.** The "5 events == 5 evidence rows" check is cheap and makes the feature verifiable at the system level without test harness overhead.

**N2 — Document fire-and-forget tradeoff explicitly** in F3 as a conscious decision rather than leaving it implicit.

**N3 — Guard clause for `.clavain/quality-gates/findings.json`** should be explicit in F3's acceptance criteria, not inherited silently from the existing resolve command step 5.

---

## Files Referenced

- `/home/mk/projects/Demarch/docs/prds/2026-02-28-disagreement-pipeline.md` — the PRD under review
- `/home/mk/projects/Demarch/docs/brainstorms/2026-02-28-disagreement-pipeline-brainstorm.md` — upstream brainstorm; key decisions documented here
- `/home/mk/projects/Demarch/PHILOSOPHY.md` — defines the T/T+1/T+2 learning loop this pipeline implements
- `/home/mk/projects/Demarch/os/clavain/commands/resolve.md` — the integration point for F3; Step 5 trust feedback shows the emit pattern
- `/home/mk/projects/Demarch/interverse/interspect/hooks/lib-interspect.sh` — F4 implementation target; `_interspect_consume_kernel_events()` at line 2013 shows the cursor consumer pattern
- `/home/mk/projects/Demarch/interverse/interspect/hooks/lib-interspect.sh` — `_interspect_insert_evidence()` at line 7+ is the F4 sink
- `/home/mk/projects/Demarch/core/intercore/contracts/events/event.json` — schema contract that must be updated for F1/F2 payload field
- `/home/mk/projects/Demarch/core/intercore/cmd/ic/events.go` — confirms current `ic events` subcommands are `tail` and `cursor` only — F1 adds `emit`
- `/home/mk/projects/Demarch/core/intercore/docs/event-reactor-pattern.md` — documents cursor at-least-once delivery; underpins the idempotency requirement in S2
- `/home/mk/projects/Demarch/interverse/interflux/docs/spec/core/synthesis.md` — Rule 4/5 and `severity_conflict` schema (lines 80-88, 253)
- `/home/mk/projects/Demarch/core/intercore/docs/research/fd-measurement-validity-review-interspect.md` — F-1 finding is the prior art for M2's dismissal_reason recommendation
