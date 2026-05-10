---
artifact_type: reflection
bead: sylveste-s3z6.19.10
stage: reflect
date: 2026-05-06
complexity: 3
sprint_outcome: shipped
---

> **⚠️ SUPERSEDED 2026-05-08** — This reflection captures lessons from a sprint whose decision (defer to β as v0 architecture) was invalidated the next day by `.19.1` Phase 1 measurement (commit `7f224cca`). The microrouter epic was killed entirely. See `docs/brainstorms/2026-05-06-microrouter-heuristic-baseline.md`.
>
> **What's still useful here**: the meta-lessons about review-round structure are real and transferable — three rounds catching three distinct kinds of error (claim vs design vs implementation), the case for putting `fd-safety` on the roster from round 1 when destructive automation is in scope, the F4-as-sibling-not-child generalization reflex, and the question of whether governance sprints over-instrument flux-drive at three rounds. None of those depend on the architecture decision being correct.
>
> **What's stale**: the sprint outcome assertion (`shipped` for a decision that was reversed within 48 hours), the references to `.19.10` and `sylveste-1mp6/5p7s/ngft/58tb`, and any framing that treats the deferral as the durable artifact of the work.

# Sprint Reflection — sylveste-s3z6.19.10 microrouter deferred-β

## Outcome

Decision recorded: defer microrouter v0 architecture to β (observed pass@1 anchor) until `.19.9` (interspect outcome-column extension) ships and 4 weeks of pass@1 telemetry accumulate. α (the prior `.19.8` v0 commit) shelved. γ (judge-ensemble across disjoint families) documented and rejected, preserved as contingency. Four child beads created: `sylveste-1mp6` (F1 bead-body cascade), `sylveste-5p7s` (F2 D2 heuristic-baseline measurement), `sylveste-ngft` (F3 deferral keep-alive state fields), `sylveste-58tb` (F4 `/clavain:status` surfacing — sibling under `.19`). State fields installed on `.19.10` for active deferral. Three flux-drive review rounds (brainstorm + PRD + plan), each producing P0 findings that drove substantive revisions.

## What was learned

### 1. Three review rounds was the right number, but each round surfaced a distinct P0

The brainstorm review's P0 was *empirical*: β doesn't break circularity by construction — outcomes accumulate while the live `agent-roles.yaml` heuristic decides which model handles each task, so the loop just moves from `judge → calibration` to `heuristic → outcome → router`. The PRD review's P0 was *operational*: heuristic-stratified eval split (the chosen mitigation) is a thermometer not a thermostat — measurement detects the gap but doesn't close it. The plan review's P0 was *structural*: SessionStart hooks can't block sessions per Claude Code spec, and `auto-close-epic` violated CLAUDE.md rule (b) requiring human confirmation for epic closes.

Each finding was downstream of the previous round's revision and could not have been caught earlier without that round's output to react to. Skipping any round would have shipped a real flaw — the brainstorm-stage circularity finding is what motivated the PRD's mitigation pre-registration; the PRD-stage thermometer/thermostat finding is what motivated the active-enforcement design that the plan-stage review then dismantled. Successive rounds are not redundant; they are catching different *kinds* of error (claim vs design vs implementation).

### 2. CLAUDE.md rule (b) auto-close-epic violation was not caught until the safety reviewer at the third round

The PRD's `auto_revert_action=auto-close-epic` was added during the PRD post-review patch (Path A) without checking CLAUDE.md's explicit policy: "auto-proceed for bead-close when none of these apply: ... (b) closing an epic." The brainstorm reviewer (`fd-decisions` + `fd-systems` + `fd-perception`) didn't catch it — they're not safety/policy reviewers. The PRD reviewer (`fd-decisions` + `fd-systems`) didn't catch it either. Only the plan-stage `fd-safety` agent flagged the rule violation. **Implication:** when a sprint introduces destructive automation (auto-close, auto-delete, auto-rollback), `fd-safety` should be on the agent roster from round 1, not just at plan review.

### 3. F4 was generalized to a sibling under `.19`, not a child of `.19.10`

The plan-revision (Path C) replaced the dropped session-start hook with a follow-up bead for `/clavain:status` enhancement. Initially F4 was framed as scoped to `.19.10`, but the enhancement is generic — any future deferral that uses the same state-field convention (`deferral_check_in`, `deferral_deadline`, etc.) gets the surfacing for free. Filing F4 as a child of `.19.10` would have artificially narrowed the implementation. Filed instead as a sibling under `.19` epic. Reflex to widen scope when the work is generic — caught here, useful pattern for future sprints.

### 4. The deferred-β decision is now embedded across the bead graph, not just in the brainstorm

Five beads now carry the deferral context: `.19.10` (PRD + brainstorm + plan + 3 syntheses), `.19.1` (v0=β not α; mitigation pre-registration), `.19.2` (label source = pass@1 from `.19.9`), `.19.8` (closing note: α shelved), `.19.9` (elevated to critical-path P0; operational requirements). A future operator reading any of these beads can reconstruct the deferral state without chasing brainstorms. The cost of doing this was non-trivial (5 bead updates with idempotent guards) but is the durable artifact of the decision. Memory-only or PRD-only would have been brittle.

### 5. Three rounds of "balanced" quality flux-drive may be overkill for governance sprints

This sprint cost ~7 agent dispatches across three rounds. Each round used 2-3 agents. Total token usage was substantial (~250k+ across reviews). For a governance/decision sprint that ships only doc + bead-state changes, this may be over-instrumented. Possible adjustments: use `--quality=fast` for governance sprints; restrict roster to fd-decisions + fd-safety + fd-systems for decision documents; auto-skip review rounds when the diff is purely doc and prior round's findings are confirmed addressed. Worth filing as a follow-up to the flux-drive routing.

## What to do differently next time

- **Always add fd-safety to brainstorm review when the sprint involves destructive automation** (auto-close, auto-delete, auto-rollback, force-pushes). Triage logic should detect the keyword set in the brainstorm body and pin fd-safety to Stage 1.
- **Check CLAUDE.md before pre-registering destructive defaults in PRDs.** A 30-second `grep` would have caught the rule (b) conflict at PRD draft time. Worth a writing-plans / strategy-skill checklist item.
- **For decision-bead sprints, verify the named decision authority and deadline are real** — single-operator placeholder is honest but means deadline-passed surfacing is the only real backstop. Future sprints with non-trivial deadlines should add a sanity check that the surfacing path actually fires.
- **F4-style generalization questions belong in the strategy/plan phase, not at bead-creation time.** When the implementation is reusable, parent it under the broader epic, not the immediate decision.

## Patterns worth distilling

(Candidates for `docs/solutions/patterns/`:)

1. **Decision-deferral with state-field surfacing** — bd state fields + `/clavain:status` reads them, instead of session-start hooks (which can't block) or auto-destruction (which violates CLAUDE.md rule b). Generic for any future deferral on the bead graph.
2. **CLAUDE-md-policy check at strategy-phase** — a 30-second grep for "auto-proceed", "auto-close", "auto-delete" in any draft PRD that proposes destructive automation, cross-referenced against CLAUDE.md's bead-close rules.
3. **Three-round-review compounding for decision sprints** — record the pattern so future sprints don't try to skip rounds when each is producing distinct P0 categories (empirical / operational / structural).

These will be filed as separate `/clavain:compound` work in a follow-up; not in scope for this reflection.

## Sprint health

- Brainstorm + 3 review rounds + revisions + execute + verify all completed in a single session.
- No code changes; doc-only diff (brainstorm + PRD + plan + 3 syntheses + state-field events in `.beads/issues.jsonl`).
- Path C decision was load-bearing — without dropping the hook, this sprint would have shipped a CLAUDE.md violation and an inert enforcement layer.
- The four child beads are appropriately scoped: F1 is mechanical (this sprint), F2 is sibling work (D2 measurement, separate timeline), F3 is the state-field installation (this sprint), F4 is the surfacing layer (separate sprint).
