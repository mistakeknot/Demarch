# Autonomous Capability-Routing via intercore (Sylveste-fc5)

**Date:** 2026-07-05
**Bead:** Sylveste-fc5 (epic) + Sylveste-fc5.1–.4 (phased children)
**Source doctrine:** gist df36a800e7b9f5ab214ae9aa5db9d9b0 / `os/Clavain/commands/model-routing.md` § "Capability-routing doctrine"

## Goal

Turn the capability-routing doctrine — **Fable plans → Sonnet executes → Opus validates → two-strikes escalation** — from documentation into kernel-enforced mechanism, so it runs autonomously for any kernel-tracked Clavain sprint rather than relying on the human (or the session model) to remember and apply it.

The doctrine's rules, restated:

1. Frontier model (fable) does planning, plan review, architecture, cross-repo synthesis, and hard-problem execution — not bulk execution.
2. Sonnet executes execution-grade plans (exact paths, complete code, machine-checkable acceptance criteria — written for a weaker executor, no "use your judgment" steps).
3. Opus validates execution **against the plan's acceptance criteria**, never its own judgment.
4. Two-strikes escalation: executor fails 2x or validator rejects 2x → escalate to frontier tier, record the failure mode. Never a third cheap retry.
5. Exceptions: hard problems that stalled on lesser models keep frontier in the execution loop; tasks under ~30 min (≈ C1–C2) skip the pipeline entirely (one model end-to-end).
6. Pilot 2–3 items through the full loop before fanning out a plan backlog.
7. Measure plan→execution pass rate (interspect), not shipped count.

## Survey: what already exists (verified 2026-07-05)

Three-layer stack: **intercore** (L1 kernel, `core/intercore/`, Go CLI `ic`) → **Clavain** (L2 OS/policy, `os/Clavain/`) → companion plugins (L3, `interverse/`).

### Reusable mechanism (~70% of what's needed)

- **Kernel routing module** — `core/intercore/internal/routing/{config,resolve,decision}.go`, CLI `ic route model|batch|dispatch|table|record|list`. `ResolveModel()` implements hierarchical resolution (overrides > phase.category > phase.model > defaults > "sonnet") plus safety-floor clamping. Every decision persists to a `routing_decisions` table (agent, selected_model, rule_matched, floor_applied, candidates, excluded, complexity). Clavain's bash router (`os/Clavain/scripts/lib-routing.sh:903-910`) already delegates to it as a fast path.
- **Agency specs** — `core/intercore/internal/agency/agency.go` defines per-macro-stage YAML specs with a `Models map[string]ModelConfig` (per-phase `default` + `categories` overrides), plus agents, gates, budgets, tool allow/deny. Example: `internal/agency/testdata/specs/build.yaml` (planned/executing → sonnet, review → opus). Loaded per-run via `ic agency load <stage> --run=<id>`.
- **The critical hook, verified:** `routing_resolve_model` in `lib-routing.sh` reads kernel-stored per-run models via `intercore_state_get "agency.models.${phase}"` as **step 0 — the highest-priority routing input**, above agent overrides, interspect calibration, and all static config. A loaded agency spec therefore flows directly into live per-phase model selection today.
- **Convenient accident:** the bash router deliberately skips the Go fast-path when `CLAVAIN_RUN_ID` is set (Go router doesn't support kernel overrides yet) — which is exactly the agency-spec case. So doctrine-as-spec needs **zero Go changes** to ship.
- **Validation gate** — `/clavain:quality-gates` → flux-drive: fail-closed pass/fail, mandatory fd-safety on ship-class diffs, blocks phase advancement via `clavain-cli enforce-gate`.
- **Evidence/calibration loop** — interspect B3 (per-agent routing calibration) and B4 (CC↔Codex delegation) are in `enforce` and already override live routing. Evidence DB at `.clavain/interspect/interspect.db`; calibration outputs consumed fresh on every resolution call.
- **Dispatch retry + verdict signals** — `core/intercore/internal/dispatch/retry.go` (exponential backoff, MaxRetries=3); `os/Clavain/scripts/dispatch.sh` `_extract_verdict` emits pass/warn/error/retry verdict sidecars from Codex output.

### The five gaps

1. **No fable/frontier tier anywhere in code or config.** Router vocabulary is haiku/sonnet/opus + Codex model IDs. "fable"/"frontier" appear only in doctrine comments.
2. **No two-strikes escalation.** `retry.go` copies the dispatch config verbatim **including `Model:`** — same-model retry only. codex-delegate escalates failures to the human/parent, not to a higher tier. Nothing counts "failed 2x → re-dispatch a tier up."
3. **No autonomous agency driver.** `ic agency` only load/validate/show; Clavain slash-commands orchestrate. (Partially acceptable: sprint auto-advances at Tier 1/2, so a loaded spec + existing sprint flow gets most of the way.)
4. **Validators don't check plan acceptance criteria.** quality-gates/flux-drive validators score their own review findings; nothing threads the plan's verify blocks / Must-Haves to the validator as a rubric (doctrine Rule 3).
5. **Wrong metric.** interspect tracks codex-delegate task pass rates (`delegation_outcome`), not plan→execution pass rate through the split pipeline (doctrine Rule 7).

## Phased plan (beads filed)

### Phase 1 — fable tier + capability-routing agency spec (Sylveste-fc5.1)

- Add `fable` to the routing vocabulary: `os/Clavain/config/routing.yaml` tiers, `_routing_model_tier` in `lib-routing.sh`, `ParseModelTier` in `internal/routing` (Go change optional for this phase; bash path suffices).
- **Graceful degradation:** fable availability is windowed (subscription). Router must clamp/fallback fable→opus when unavailable, never hard-fail.
- Author `capability-routing` agency spec: planning/architecture categories → fable, executing default → sonnet, review/validate categories → opus.
- Wire `/sprint` to `ic agency load` the spec when the session model is fable.
- Acceptance: with a kernel run active and spec loaded, `routing_resolve_model --phase=executing` → sonnet; `--phase=planned --category=planning` → fable (or opus fallback); `routing_decisions` records `rule_matched=agency`.

### Phase 2 — two-strikes escalation ladder (Sylveste-fc5.2, depends on 1)

- Extend `internal/dispatch/retry.go` with an escalation policy: attempts 1–2 same model, attempt 3 re-dispatches at the next tier up (sonnet→opus→fable), recording the failure mode.
- Consume the verdict sidecars dispatch.sh already emits.
- Record `escalation` evidence to interspect (agent, from_model, to_model, failure_mode, attempts).
- Honor the <30-min exception: C1–C2 complexity (B2) skips the pipeline — single model end-to-end.

### Phase 3 — thread plan acceptance criteria to validators (Sylveste-fc5.3)

- `/clavain:write-plan` emits a structured, machine-checkable acceptance-criteria block (commands to run, files that must exist, tests that must pass).
- Criteria stored as a run artifact (`set-artifact acceptance-criteria`).
- quality-gates gains a **plan-conformance verdict** distinct from review findings: the validator dispatch receives the criteria as its rubric, returns pass/fail per criterion; gate FAIL blocks advancement when any criterion fails.

### Phase 4 — measure plan→execution pass rate (Sylveste-fc5.4, depends on 3)

- New evidence type `plan_execution_outcome` written at validation time: plan author model, executor model, validator model, criteria pass/fail counts, escalation count.
- `/interspect:calibrate` aggregates into a plan-pass-rate metric per (author_tier, executor_tier) pair.
- Reported via `/interspect:delegation-status` or a new routing-effectiveness view.
- This is the north-star metric that gates widening autonomy (pilot 2–3 items first, per doctrine Rule 6).

### Deferred / adjacent

- **Go router parity** (B3/B4/agency overrides in `internal/routing`) — natural Phase 5; removes the bash-only constraint and makes the kernel the sole resolver.
- **`ic agency run` driver** — a kernel loop that dispatches a stage's agents by spec, evaluates gates, advances phases without slash-command orchestration. Bigger design question: how much orchestration should move from L2 (Clavain markdown commands) into L1 (Go kernel)?

## Design considerations / open questions

- **Fable-window detection:** how does the router know fable is currently available? Options: env var set by session-start hook; probe; static config the user flips. Simplest: treat session model == fable as the signal (the spec only loads then), with opus fallback baked into resolution for subagent dispatches that can't reach fable.
- **Executor "no judgment calls" enforcement:** the doctrine requires execution-grade plans. Phase 3's criteria block helps, but nothing lints a plan for "use your judgment" steps. Possible cheap check in write-plan or plan-review.
- **Escalation loop guard:** two-strikes must not oscillate (escalate → frontier fails → re-plan → re-execute → fail again). Cap at one escalation per dispatch chain; after that, surface to the human.
- **Cost telemetry:** `routing_decisions` + interstat session-cost should let us verify the doctrine's economic premise (fable tokens only where lesser models fail). Worth a dashboard query once Phase 4 lands.
