# FUSED Lens Review — fd-fused-lesson-transport (round 1, probe 2)

**Target:** `docs/brainstorms/2026-07-05-autonomous-capability-routing-intercore.md`
**Lens:** fd-escalation-retry-ladder × fd-swordsmith-transmission (fused)
**North star:** maximize verified novelty×risk surface until dry
**Constraint honored:** every finding below requires BOTH parent perspectives; single-parent-catchable findings were discarded (several candidates on pure oscillation-cap correctness and pure grade-binding were dropped in this pass).

## Findings Index

- [P0] Phase 2's escalation ladder has no lesson-carrying payload spec — the only read-back path in the whole dispatch stack feeds DAG siblings, not tier-escalated retries
- [P1] `failure_mode` is scoped as a bare string with no schema, so it can satisfy the aggregation need (Phase 4) or the transmission need (correction-not-repetition) but the plan never designs it to do both
- [P2] The "one escalation per chain, then surface to human" cap (design considerations, line 82) specifies termination but not what ledger the human inherits at the cap

## Findings

### [P0] No lesson-carrying payload on tier-step — the escalation ladder re-dispatches work, not knowledge

**Severity:** P0

**Where:** `docs/brainstorms/2026-07-05-autonomous-capability-routing-intercore.md` Phase 2 (lines 53–58), cross-referenced with `core/intercore/internal/dispatch/retry.go:97-145` and `os/Clavain/scripts/orchestrate.py:290-330`.

**What:** Phase 2 says: "Extend `internal/dispatch/retry.go` with an escalation policy: attempts 1–2 same model, attempt 3 re-dispatches at the next tier up (sonnet→opus→fable), recording the failure mode." As a state-machine spec this is complete and correct — attempt/tier counters are orthogonal, the transition at attempt==3 is well-defined, and "recording the failure mode" is named as an obligation. But the plan never says the escalated tier's dispatch *receives* that failure mode as an input. Verified against actual code: `Retry()` in retry.go copies `orig.PromptFile` verbatim (line 116) and explicitly nils `VerdictFile` (line 119) rather than reading it. There is no interspect import anywhere in `internal/dispatch/`. The one place in the whole stack that *does* read a prior dispatch's verdict content back into a new dispatch's prompt — `orchestrate.py`'s `build_prompt()` (line 313) via `summarize_output()` (line 290), which injects `## Context from dependencies` from `verdict_path` (lines 296–299, 330) — is wired for DAG *sibling/dependency* propagation, not for retry chains. So the codebase already proves the pattern the plan needs ("read a verdict, inject into next prompt") exists and works, but Phase 2 doesn't route the escalation ladder through it.

**Evidence:**
- `core/intercore/internal/dispatch/retry.go:112-130` — `Retry()` builds `d := &Dispatch{PromptFile: orig.PromptFile, ..., VerdictFile: nil, ...}`: prompt copied verbatim, verdict discarded.
- `os/Clavain/scripts/orchestrate.py:290-330` (per grep-confirmed agent trace) — the only extant read-back mechanism, scoped to DAG dependencies.
- Brainstorm line 55: "attempt 3 re-dispatches at the next tier up ... recording the failure mode" — records but does not specify injection into the escalated dispatch's own input.

**Intersection justification:** The escalation-retry-ladder lens alone would certify this as done: attempt counter increments correctly, tier transitions at the right threshold, no oscillation past attempt 3 — a clean terminating state machine. The swordsmith-transmission lens alone would flag "no correction is being carried forward" but has no way to say *where in the mechanism* the carry-forward should attach — it doesn't know retry.go's `VerdictFile` field exists or that `orchestrate.py` already solved this exact problem for a sibling edge. Only holding both at once — the state machine's concrete data structures (PromptFile/VerdictFile fields, dispatch construction call sites) AND the lineage requirement (the next hand must receive what the last hand learned) — reveals that the fix is not "add an escalation feature" but "route Phase 2's re-dispatch through the read-back path `orchestrate.py` already implements for a different edge." Neither parent, reviewing independently, would produce this specific redirect.

**Suggestion:** In Phase 2, when `retry.go`'s escalation path constructs the tier-up dispatch, read the original's verdict-sidecar content (the same content `_extract_verdict` in dispatch.sh already produces) and thread it into the new dispatch's prompt the same way `orchestrate.py:build_prompt()` does for dependency context — smallest viable fix is one field addition (`PriorFailureContext string` on the escalation-dispatch constructor) plus a call to the existing summarization helper, not a new subsystem.

---

### [P1] `failure_mode` has no defined schema — the plan lets one field serve two incompatible masters

**Severity:** P1

**Where:** Brainstorm Phase 2 (line 57: "Record `escalation` evidence to interspect (agent, from_model, to_model, failure_mode, attempts)") and Phase 4 (line 68: "aggregates into a plan-pass-rate metric per (author_tier, executor_tier) pair").

**What:** The plan names `failure_mode` as a single field serving two consumers: (1) Phase 4's aggregator, which needs it to be a small closed vocabulary so pass-rates can be grouped/compared across escalations, and (2) the doctrine's own "record the failure mode" transmission obligation (model-routing.md line 94), which exists so the next tier doesn't repeat the same mistake — that need wants enough specificity to identify *which acceptance criterion failed and how* (Phase 3's per-criterion pass/fail, line 64). Verified: no `failure_mode` enum or schema exists yet anywhere in the codebase (confirmed via repo grep — it's pure doctrine-comment vocabulary today, matching the brainstorm's own gap-2 assessment on line 38). Because the plan specs it as one bare field name with no shape, whoever implements Phase 2 will pick a shape optimized for whichever consumer they're thinking about first — and the other consumer's need won't surface as a problem until Phase 4 tries to aggregate free-text reasons, or until an escalated tier tries to act on an overly-coarse enum bucket like "criteria-fail" and re-hits the same ambiguity.

**Evidence:**
- Brainstorm line 57 lists `failure_mode` as one undifferentiated tuple element alongside `agent, from_model, to_model, attempts`.
- Brainstorm line 68 (Phase 4) needs it aggregable per (author_tier, executor_tier).
- Brainstorm line 64 (Phase 3) already produces a richer artifact — per-criterion pass/fail — that could feed `failure_mode` but isn't connected to it in the plan text.
- model-routing.md:94 — "record the failure mode" is the transmission-facing doctrine language this field is meant to satisfy.

**Intersection justification:** The pure state-machine (escalation-ladder) review would check only that `failure_mode` is *present* and machine-readable enough to log — satisfied, nothing to flag. The pure craft-transmission review would want the failure captured "in the master's own vocabulary" for correction, but wouldn't independently connect that need to Phase 4's aggregation requirement three phases later, since aggregation-fitness is out of that lens's scope. It takes holding both — the counter/aggregation need from the state-machine side and the actionable-correction need from the transmission side — to see that one undifferentiated field is being asked to do two jobs whose optimal shapes conflict (a closed enum aggregates cleanly but starves correction; free text corrects well but resists aggregation), and that the plan never resolves which shape wins or how both needs get served.

**Suggestion:** Phase 2 should split `failure_mode` into a small closed enum (for Phase 4's grouping) plus a structured reference to the specific failed criterion/detail from Phase 3's per-criterion artifact (for transmission) — e.g., `failure_mode: enum` + `failed_criteria: [ids]` — rather than one string. This is a one-field-becomes-two-fields change to the Phase 2 schema sketch, not a redesign.

---

### [P2] The escalation-chain termination cap specifies a stop condition but not what the human inherits

**Severity:** P2

**Where:** Brainstorm "Design considerations" (line 82): "Escalation loop guard: two-strikes must not oscillate ... Cap at one escalation per dispatch chain; after that, surface to the human."

**What:** As a pure oscillation guard this is correct and sufficient: it bounds the chain (no infinite escalate→fail→re-plan loops), and "surface to the human" is a valid terminal state for a state machine. But the plan doesn't say what artifact accompanies that surfacing. Given finding P0 above (no lesson-payload threading) and P1 (undifferentiated failure_mode), the most likely default implementation surfaces only the final dispatch's own failed output plus a counter ("escalated once, still failing") — not the per-tier lesson chain (what sonnet tried and why it failed, what opus changed and why *that* failed too). The doctrine's own framing of the human/frontier as the terminal inspector (this is functionally the "master" the craft-lineage frame describes) means the human is being asked to make a judgment call — continue, re-plan, abandon — without the evidence trail that would let them do it without re-deriving the whole chain by hand.

**Evidence:**
- Brainstorm line 82 specifies only the cap and the "surface to the human" action, no artifact.
- No `set-artifact` or evidence-bundle call is specified for the termination event, versus Phase 3's explicit `set-artifact acceptance-criteria` (line 63) for a different (non-terminal) event — the plan already has a precedent for run-artifact persistence but doesn't apply it here.
- Phase 4's `plan_execution_outcome` evidence type (line 68) records counts, not the lesson chain itself.

**Intersection justification:** The escalation-ladder lens is fully satisfied here — the chain terminates, the cap is enforced, no oscillation. The craft-transmission lens alone would say "the master needs the full inspection history" but wouldn't necessarily connect that to a *termination event specifically*, since transmission concerns apply at every hand-off, not just the last one. Fusing them exposes the specific gap: termination is the one point where the state machine hands control entirely outside itself (to a human), which is exactly the point where the transmission lens says the inheritance obligation is highest — and the plan's silence on the terminal artifact is invisible to either lens reviewing alone, since the state-machine lens sees a correct guard and the transmission lens (without the state-machine's chain-boundary concept) has no specific line to point at.

**Suggestion:** When the one-escalation cap is hit, persist a chain-lesson artifact (reusing the `set-artifact` pattern already established for acceptance-criteria in Phase 3) containing each tier's attempt, its failure_mode/failed_criteria (per P1's fix), and the verdict at each step — surfaced to the human alongside the final failed output, not instead of it.

---

## Verdict

**3 findings, all requiring both parent lenses.** The dominant pattern across all three: the brainstorm's escalation mechanics (attempt/tier counters, termination cap, "record the failure mode" as a checklist item) are internally consistent and would pass a pure state-machine review outright. The gap only appears when asking, at each tier-step or terminal hand-off, "does the receiving party (next tier, or human) get the lesson as structured input, or just the work plus a number" — and the codebase already contains the missing mechanism (`orchestrate.py`'s dependency-context injection) wired to the wrong edge, which is the strongest evidence that this is a real, fixable gap rather than a speculative one. Two candidate findings were discarded during drafting for being catchable by a single parent alone (a pure oscillation-cap edge case, and a pure grade-to-task binding question) per the fusion constraint.
