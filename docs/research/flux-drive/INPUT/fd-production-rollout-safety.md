<!-- flux-drive:complete -->
# fd-production-rollout-safety — Microrouter Track B6 Rollout Safety Review

**Persona**: Production ML reliability engineer with shadow-mode rollout experience for ranking and routing models — has been paged when a router degraded silently.
**Scope**: shadow→enforce promotion lifecycle, rollback runbook, degradation visibility, privacy-extension safety. Anti-overlap with cascade design, LoRA pipeline, eval methodology, schema (covered by sibling agents).

## Findings Index

| # | Severity | Title |
|---|----------|-------|
| 1 | **P0** | Auto-degrade `enforce → shadow` on model-not-loaded with no operator-visible signal — stealth-shadow risk |
| 2 | **P0** | Rollback procedure as written reuses B3/B4 escape-hatch language but B6 has 3 artifacts not 1 |
| 3 | **P1** | "≥ 1 sprint shadow soak" is insufficient if soak sprint is not representative of execution mix |
| 4 | **P1** | Privacy-routing extension `.19.6` allows microrouter to override `mode=off` — bypasses kill-switch |
| 5 | **P1** | Shadow log schema is unspecified — cannot reconstruct eval-harness metrics post-hoc without it |
| 6 | **P2** | No degradation tripwire — there is no metric that auto-triggers rollback if pass@1 drops |
| 7 | **P2** | Confidence-cascade verifier (`.19.7`) shadow-mode and main-router shadow-mode interaction is undefined |
| 8 | **P2** | `mode = enforce` toggle ships with rollback documented (INPUT.md:64) — but where? Not in INPUT.md |

## Verdict

**REWORK BEFORE SHADOW.** The rollout safety story has two P0s (stealth shadow on auto-degrade, incomplete rollback) and a P1 that compounds them: the privacy extension extends router scope past the global kill switch. None of these block the design or training work, but all three must be resolved before shadow mode is enabled. The single highest-leverage change is to write a runbook in `os/Clavain/AGENTS.md` next to where B2-B5 are documented, listing the three B6 artifacts and the recovery procedure for each.

## Summary

The B6 epic uses the same `mode = off | shadow | enforce` pattern as B2/B3/B4/B5 (INPUT.md:27, 60-65, 297-301), which is correct and reduces operator surprise. However, B6 has *three* artifacts where B3 and B4 have *one*:

- B3 escape: delete `routing-calibration.json` (single file, atomic).
- B4 escape: delete `delegation-calibration.json` (single file, atomic).
- B6 escape: must address (a) adapter checkpoint `~/.cache/huggingface/.../microrouter-v0/`, (b) interfer HTTP endpoint at `localhost:8421/route`, (c) shadow log `.clavain/interspect/microrouter-shadow.jsonl`, *and* (d) the YAML `mode: off` toggle.

Reusing B3/B4 escape-hatch language without naming all four is a P0 — the operator following the B3 runbook for B6 will leave 2-3 of the artifacts in place, with unpredictable behavior. The proposal says "rollback documented" (INPUT.md:64) but no rollback documentation exists in INPUT.md or `os/Clavain/AGENTS.md`.

The shadow→enforce promotion gate (`≥ 1 sprint of shadow-mode soak`, INPUT.md:300) treats sprints as fungible. They are not. A doc-update-heavy sprint does not exercise the same routing decisions as an implementation-heavy sprint, and the production execution mix shifts substantially across sprint types.

## Issues Found

### P0 — Auto-degrade `enforce → shadow` is invisible to the operator

INPUT.md:372: `Router model not loaded → mode auto-degrades to shadow (don't fail-closed)`.

The intent is sound (don't block production for a missing model), but as specified the system silently degrades:

- The configured `mode: enforce` in routing.yaml stays "enforce."
- The runtime resolver acts as if `mode: shadow`.
- No log entry, no metric increment, no operator-visible signal that the system is *not* doing what its config says.

This is the stealth-shadow failure pattern. A real-world incident profile:

1. Operator deploys microrouter v0.5 with `mode: enforce`.
2. Adapter file path changes silently (a `huggingface_hub` cache cleanup, a disk near-full event, a permissions issue after a system update).
3. Resolver auto-degrades. Routing decisions silently fall through to B3 calibration for an entire sprint.
4. Operator sees the sprint complete normally (B3 is good enough) and assumes B6 is working.
5. The first deliberate audit catches the discrepancy weeks later, by which point the calibration data collected during that sprint *includes shadow-mode B6 data attributed as enforce-mode* — corrupting future analysis.

This pattern interacts with a P1 from cascade-design: the `ineligible_agents` defense relies on the resolver actually *running* the microrouter check. If the router is in stealth shadow, the eligibility check never runs at all — but the system still claims to be in enforce.

**Concrete remedy:**
1. **Do not silently mutate runtime mode.** Keep configured `mode: enforce` and treat each call as fall-through-to-B3 when the model is unloaded. The `mode` is configuration, not runtime state.
2. **Emit a structured log entry** at INFO level on every fall-through with `reason=model_unloaded`, plus a Prometheus metric `microrouter_calls_fallthrough_total{reason="model_unloaded"}` increment.
3. **Add an alarm** (or a `clavain doctor` check) that fires when `microrouter_calls_fallthrough_total{reason="model_unloaded"}` is non-zero for more than 60 seconds while the configured mode is enforce.
4. Document this in the runbook as part of the rollback fix from P0 #2 below.

This interacts directly with the cascade-design sibling's P2 on "auto-degradation is asymmetric and adversarially triggerable" — they're flagging the same symptom from a different angle.

### P0 — Rollback runbook reuses B3/B4 language; B6 has 3 artifacts, not 1

INPUT.md:64: `mode: enforce toggle ships with rollback documented (delete calibration file pattern, same as B3/B4)`.

This is wrong by construction. The B3/B4 rollback is "delete one JSON file." The B6 rollback must address:

| Artifact | Where | What "rollback" means |
|---|---|---|
| Configured mode | `routing.yaml` `microrouter.mode` | Set to `off` |
| Adapter checkpoint | `~/.cache/huggingface/hub/models--sylveste--qwen3.5-3b-microrouter-v0/` | Delete OR keep (depends on intent) |
| Interfer endpoint | `localhost:8421/route` (or wherever the schema lands per config-resolver-architecture sibling's port-conflict finding) | Stop OR leave running but disable B6 |
| Shadow log | `.clavain/interspect/microrouter-shadow.jsonl` | Archive OR keep for analysis |

The runbook needs to address each of these explicitly, including:

- **Quick rollback** (the operator wants the system to act like B6 doesn't exist): just `mode: off`. Leave artifacts in place.
- **Full rollback** (the operator wants B6 gone for forensic analysis or because of corruption): set `mode: off`, archive shadow log, keep adapter checkpoint, keep endpoint running for diagnostics.
- **Failed promotion rollback** (eval matrix showed regression after enforce promotion): set `mode: shadow`, *not* `off` — keep the diagnostic data flowing for root cause.

INPUT.md does not have any of this. The phrase "delete calibration file pattern, same as B3/B4" is actively misleading — an operator following that instruction for B6 will at most disable the YAML toggle, leaving the endpoint and shadow log running.

**Concrete remedy:**
1. Write a B6 section in `os/Clavain/AGENTS.md` next to where B2-B5 are documented, with the three rollback paths above (quick / full / failed-promotion).
2. Add to bead `.19.5` "Done when": "Rollback runbook in os/Clavain/AGENTS.md is committed alongside the resolver integration."
3. Coordinate with config-resolver-architecture sibling — they will identify the exact endpoint port and path, which determines what "stop the endpoint" means operationally.

### P1 — "≥ 1 sprint shadow soak" is insufficient if soak sprint is not representative

INPUT.md:300: `Shadow → enforce: ≥ 1 sprint of shadow-mode soak, no pass@1 regression vs. B3 baseline, ≥ 20% reroute rate`.

A sprint is the unit of work, but production routing pressure varies enormously across sprint types:

- **Doc-update sprint**: 80%+ subagent calls are research/synthesis (Haiku-eligible per `routing.yaml:529-533`). Reroute rate trivially high; pass@1 trivially safe.
- **Implementation sprint**: 60%+ subagent calls are review/implementation (Sonnet target). Reroute decisions are higher-stakes; pass@1 sensitive to wrong-tier choices.
- **Refactor sprint**: heavy Opus / large-context calls. The router's training data may have few examples; the reroute decisions are extrapolations.
- **Brainstorm-heavy sprint**: `phases.brainstorm.model: opus` (`routing.yaml:548`). The router may not have brainstorm phase coverage at all.

If the soak sprint is doc-update-heavy and the first enforce-mode sprint is implementation-heavy, the gate passes on the easy distribution and fails silently on the hard one — a 15% pass@1 regression on complex tasks the soak never covered would be an incident before it's measurable.

**Concrete remedy:** Add to the promotion-gate criteria:
1. Soak sprint must have *at least 30% implementation-phase calls* and *at least 20% review-phase calls*. (Numbers chosen to roughly match the production distribution; they should be tuned by inspecting actual sprint distributions.)
2. Soak must include calls from at least 5 distinct agents.
3. Soak must include at least one call to fd-safety and fd-correctness (to confirm the eligibility check is firing in production, not just in eval).
4. If the first soak sprint doesn't meet these, run a second (or third) until it does.

This is the production-side complement of the eval-methodology sibling's P1 on per-workload gate stratification.

### P1 — Privacy-routing extension `.19.6` allows microrouter to bypass `mode=off` global kill-switch

INPUT.md:407-446 (bead `.19.6`) extends privacy_routing so internal/sensitive tasks engage the microrouter *even when global `mode=off`*. The motivation is valid (route within local fleet for sensitivity) but the safety property is concerning:

- `mode = off` is the *global kill switch*. Today, that's an operator's "disable B6 entirely" lever.
- Under `.19.6`, `mode = off` no longer disables B6 for sensitive tasks. The operator must *also* edit privacy_routing config or remove the flag to fully disable B6.
- This is two-step disable, which is what every "we lost 4 hours debugging an outage because the kill switch didn't kill it" runbook starts with.

The current `routing.yaml:767-769` privacy routing is a routing target (`local-only`, `local-only-no-log`), not a router activator. The extension changes the semantics — privacy now activates B6 logic, not just constrains B6 output. This is a meaningful expansion of B6's authority.

**Concrete remedy:**
1. Rename the proposed `microrouter.privacy_override: always` flag to `microrouter.engage_for_privacy: true|false` and default it to `false`.
2. Document explicitly that "`mode = off` AND `engage_for_privacy = true`" is a valid state, but a unusual one — the operator who sets `mode = off` typically wants the kill switch to fully kill.
3. Add a `clavain doctor` check that warns when both flags are non-default, specifically calling out the kill-switch implications.
4. Make the privacy-extension shadow-mode soak independent: the privacy route requires its own shadow soak before enforce, even if main microrouter is already enforce. Privacy traffic distribution is different from general traffic.

### P1 — Shadow log schema is unspecified — cannot replay eval-harness metrics from production

INPUT.md:349 specifies `shadow_log: ".clavain/interspect/microrouter-shadow.jsonl"` but does not specify the schema. The shadow soak metric (≥ 20% reroute rate, no pass@1 regression) requires fields like:

- `task_id`, `agent`, `phase`, `complexity_tier`
- `router_decision` (what B6 said)
- `actual_model_used` (what the chain settled on after fall-through if applicable)
- `passed` (downstream outcome)
- `latency_router_ms`, `latency_total_ms`
- `reason` (why the chain settled where it did — useful for the auto-degrade P0 above)

Without these specified, two things go wrong:

1. **Soak validation requires re-running the eval harness.** That's expensive and uses post-hoc data. The whole point of shadow soak is to compute the metrics from production data directly.
2. **Schema drift across versions.** v0 shadow logs and v1 shadow logs may have different fields, breaking longitudinal analysis.

**Concrete remedy:**
1. Specify the JSONL schema in `.19.5` "Done when" with the fields above (or the team's chosen variant).
2. Add a `version` field; bump on schema changes.
3. Add to `.19.4` (eval harness) a `replay-from-shadow-log` mode that reads production shadow logs and computes the matrix metrics. This is what makes shadow soak *self-validating*.

### P2 — No degradation tripwire — there is no metric that auto-triggers rollback

The proposal's promotion gates (≥ 20% reroute rate, no pass@1 regression) are run *before* enforce. There is no comparable *demotion* gate that runs *during* enforce — i.e., a metric that, if violated, automatically reverts the router to shadow.

In a production routing system this is the difference between "we noticed the regression" and "the regression noticed itself." Examples:

- pass@1 over a rolling 100-call window drops by ≥ 5% relative to the prior 1000-call window → auto-revert to shadow.
- p95 router latency exceeds `timeout_ms` in ≥ 10% of calls in a 1-hour window → auto-revert to shadow.
- Microrouter chooses `local:*` for an `fd-safety` or `fd-correctness` call (eligibility check failure) → immediate revert to off + alarm.

**Concrete remedy:** Add to `.19.5` "Done when": "At least one runtime tripwire (the safety-floor violation case at minimum) auto-reverts the configured mode and emits an alert." Coordinate with cascade-design sibling — the safety-floor tripwire is partly their territory.

### P2 — Confidence-cascade verifier (`.19.7`) shadow concurrency with main router

(Cross-referenced with cascade-design sibling's same finding, framed from the safety angle.)

If both `.19.7` (verifier) and main router are simultaneously in shadow during the verifier's own soak period, the system is logging two parallel routing decision streams and there is no specified precedence for post-hoc analysis. Operationally this is a debt the team will pay later.

**Concrete remedy:** Specify in `.19.7` that the verifier *cannot enter shadow* until the main router is at `enforce` for ≥ 2 weeks. Then there is one source of truth at any time.

### P2 — `mode: enforce toggle ships with rollback documented` (INPUT.md:64) — but where?

The literal text "rollback documented" is present in the success criteria but no rollback documentation is delivered in INPUT.md, in the `.19.5` integration bead's "Done when," or in `os/Clavain/AGENTS.md`. This is a process bug — the success criterion is unfalsifiable as written.

**Concrete remedy:** Replace "rollback documented" in INPUT.md:64 with "rollback runbook merged in `os/Clavain/AGENTS.md` covering all three B6 artifacts." Same fix this finding interacts with P0 #2 above.

## Improvements

- **Add a `microrouter` section to `clavain doctor`** that checks: configured mode, endpoint health, adapter file presence, shadow log freshness. Each one a structured pass/fail — `clavain doctor` already does this for B3/B4/B5 (the pattern is at `os/Clavain/AGENTS.md` "Topic Guides"); B6 should plug in.
- **Decide explicitly: is there a v0 → v1 promotion plan?** If v0 ships and v1 retrains with more data, what's the procedure? Is it (a) shadow-mode soak v1 alongside v0 in enforce, (b) replace v0 in place after retraining, (c) require a full re-soak of v1? The answer matters for the lifecycle, but no bead in this epic addresses it.
- **Consider a "maintenance window" for promotion**, not a sprint boundary. Sprints have variable duration and unpredictable shape. A maintenance window is bounded ("between two specific timestamps the router runs in shadow with X% of traffic, then we evaluate"). Only worth doing if the sprint-as-soak-unit ends up biting; for v0 it's probably overkill.

## Anti-Overlap (handed off to siblings)

- Resolver chain semantics, fall-through correctness, mode interactions → **fd-routing-cascade-design**
- Loss design, latency benchmarking, judge bias → **fd-lora-distillation-pipeline**
- Holdout integrity, gate metric construction, oracle definition → **fd-eval-methodology-holdout**
- Schema validation, port conflict, zero-cost-bypass test → **fd-config-resolver-architecture**
