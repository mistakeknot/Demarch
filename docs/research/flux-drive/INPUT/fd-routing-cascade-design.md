<!-- flux-drive:complete -->
# fd-routing-cascade-design — Microrouter Track B6 Resolver Design Review

**Persona**: Routing systems engineer with FrugalGPT / RouteLLM / Hybrid LLM cascade experience.
**Scope**: bead `.19.5` resolver integration, mode interactions with B2/B3/B4/B5, and the proposed insertion in `os/Clavain/config/routing.yaml`. Anti-overlap with LoRA pipeline, eval harness, rollout safety, schema architecture (covered by sibling agents).

## Findings Index

| # | Severity | Title |
|---|----------|-------|
| 1 | **P0** | Insertion above `overrides[agent]` shadows safety-floor agent overrides for fd-safety / fd-correctness |
| 2 | **P0** | `ineligible_agents` list duplicates safety_floors with no convergence check — drift hazard |
| 3 | **P1** | Mode-interaction matrix (B2 × B3 × B6) is *named* but never enumerated in spec |
| 4 | **P1** | `timeout_ms: 100` ceiling vs `p95 < 50ms` promotion gate use different measurement bases |
| 5 | **P1** | "Garbage response" failure mode is asserted but never specified — what counts as "garbage"? |
| 6 | **P2** | Decision-space label namespace not pinned to `tier_mappings` keys — silent mismatch risk |
| 7 | **P2** | Auto-degradation `enforce → shadow` on model-not-loaded is asymmetric and adversarially triggerable |
| 8 | **P2** | Confidence-cascade verifier (`.19.7`) and main router can shadow concurrently — interaction undefined |

## Verdict

**APPROVE WITH CHANGES.** The B6 cascade is conceptually correct (small-model gate → fall-through), but the resolver insertion point as written creates a P0 safety-floor bypass risk and the spec's failure-mode taxonomy is incomplete. The cascade design needs (a) a precise enumeration of mode-interaction outcomes, (b) a structural reason — not a list — that fd-safety/fd-correctness cannot be routed by B6, and (c) the `timeout_ms` ↔ promotion-gate mismatch resolved before any code lands.

## Summary

The proposal slots a learned router above B3 (calibration) and below B2 (complexity) with `mode = off|shadow|enforce` mirroring B2/B3/B4/B5. Fall-through on (a) endpoint unreachable, (b) timeout > `timeout_ms`, (c) model-not-loaded is the right shape. However, the resolver chain as drawn places the microrouter *above* `overrides[agent]`, which is where the existing safety-floor exclusions for `fd-safety` and `fd-correctness` live (`routing.yaml:540-544`). The spec's defense — an inline `ineligible_agents` list inside the `microrouter:` section — is necessary but not sufficient: it duplicates the safety-floor list maintained elsewhere in the system without any convergence check. If a future agent gets added to `subagents.overrides` but missed in `microrouter.ineligible_agents`, the safety floor is silently bypassed under `enforce`.

The deeper structural concern is that the proposed chain order treats the microrouter as a *peer* of complexity (B2) rather than a *consumer* of it. Every other learned-routing literature reference cited (RouteLLM, FrugalGPT, Hybrid LLM) treats the small-model gate as either (a) a *first-stage filter* whose output is then refined by deterministic policy, or (b) a *terminal stage* gated by all prior policy. The B6 proposal places the router in the *middle* of the chain, which is the position with the worst combinatorial-interaction surface.

## Issues Found

### P0 — Resolver insertion above `overrides[agent]` can shadow safety-floor agent overrides

The proposal's resolver chain (INPUT.md:354-366) reads:

```
kernel overrides
  > complexity override (if enabled+matching)
  > microrouter override (if enabled+matching+not-timed-out+agent-eligible)   ← NEW
  > overrides[agent]
  > calibration (if enabled+matching)
  > ...
```

Today, `routing.yaml:540-544` registers `fd-safety` and `fd-correctness` under `subagents.overrides`. That mapping currently runs *before* B3 calibration (the comment block at `routing.yaml:517-518` is explicit about this). The proposal moves the microrouter in front of `overrides[agent]`, which means in `enforce` mode the microrouter's decision is consulted *before* the safety-floor override is even read.

The `ineligible_agents` list in the proposed schema (INPUT.md:346-348) is the only thing standing between this chain and a silent fd-safety bypass. Three failure modes:

1. **Name-form mismatch.** `routing.yaml:541-544` lists agents in *qualified* form (`interflux:review:fd-safety`, `interflux:fd-safety`) — four entries for two agents. The proposed `microrouter.ineligible_agents` (INPUT.md:347) lists bare names (`fd-safety`, `fd-correctness`). `lib-routing.sh:88-113` already handles namespace stripping for the safety-floor lookup (`floor_key="${floor_key##*:}"`), but the microrouter eligibility check is unspecified — if it does exact match, the qualified form bypasses the eligibility block silently.
2. **Drift.** Adding a new safety-critical agent requires editing two lists in two locations (subagents.overrides and microrouter.ineligible_agents). There is no schema-level constraint forcing them to converge.
3. **Resolution order leak.** Even if `ineligible_agents` matches, the chain order means a router timeout *also* bypasses `overrides[agent]` if the spec's "fall through to B3" language is read literally — the spec says fall-through goes *down* the chain (to B3 calibration), skipping the override layer above it.

**Concrete remedy:** Move the microrouter resolver layer *below* `overrides[agent]`, not above it. This makes the resolution `kernel > complexity > overrides[agent] > microrouter > calibration > phases > defaults`. fd-safety/fd-correctness exit at the override step before the router is consulted at all, eliminating the bypass risk by construction. The `ineligible_agents` list then becomes a defense-in-depth check rather than the load-bearing one.

The eval-harness sibling will need to know about this reordering, because their `oracle-upper-bound` should respect the same chain.

### P0 — `ineligible_agents` duplicates `subagents.overrides` safety entries with no schema-level convergence

The existing safety floors live in two places already:
- `subagents.overrides` (`routing.yaml:540-544`) — agent-name → model
- The bash-side cache `_ROUTING_SF_AGENT_MIN` (lib-routing.sh:33), populated from `agent-roles.yaml` (a separate file in `interverse/interflux/config/flux-drive/agent-roles.yaml`)

Adding a third list (`microrouter.ineligible_agents`) compounds the divergence problem. Today `_routing_apply_safety_floor` (lib-routing.sh:88-113) reconciles two of those lists at runtime by clamping to `min_model`. The proposed B6 ineligibility is a *binary skip*, not a clamp, so it cannot piggyback on the existing reconciler.

**Concrete remedy:** Define `microrouter.ineligible_agents` as **derived** from `agent-roles.yaml` `min_model >= sonnet`, not as a separately-maintained list. Either (a) compute it at config-load time in lib-routing.sh, or (b) write an integrity test that fails CI when the lists diverge. The proposal as written invites a real-world incident the next time someone adds a safety-critical agent.

### P1 — Mode-interaction matrix is referenced but never enumerated

The risks section (INPUT.md:67-70) and the eval bead (INPUT.md:286-290) treat B6 modes (`off|shadow|enforce`) as composable with B2/B3/B4/B5 modes, but the spec never enumerates the 3⁵ = 243 combinations or even names which combinations are tested. Two specifically dangerous interactions are not addressed:

1. **B6 = enforce, B5 = shadow.** B5 is currently in `shadow` (`routing.yaml:728`) — it logs what it *would* route locally but applies cloud routing. If B6 = enforce is reached first in the chain and selects a `local:*` model, does the system honor that decision (silently promoting B5 from shadow to enforce for this call) or does it suppress local routing because B5's mode is shadow? The spec doesn't answer.
2. **B6 = enforce, B3 = enforce, calibration disagrees with B6.** Both layers want to override the model. The chain order says B6 wins (it's higher in the resolution chain), which means *the calibration data that took 21+ sprints to collect* is silently discarded for any task B6 fires on. The promotion gate (≥ 90% agreement with calibrated baseline, INPUT.md:62) does not catch this — *agreement* and *override frequency* are different metrics.

**Concrete remedy:** Add a section "Mode interaction matrix" to bead `.19.5` that enumerates at minimum these 9 combinations: `B6 ∈ {off, shadow, enforce} × B5 ∈ {off, shadow, enforce}` with explicit decision rules. The eval methodology sibling will use this matrix as its workload axis.

### P1 — `timeout_ms: 100` ceiling vs `p95 < 50ms` promotion gate are at different measurement points

Bead `.19.5` (INPUT.md:345) sets `timeout_ms: 100` as the resolver ceiling. Bead `.19.4` (INPUT.md:299) sets `Off → shadow: router latency < 50ms p95` as the promotion gate. These two numbers are not consistent under realistic conditions:

- The **eval-harness 50ms p95** is measured in isolation (single inflight inference, no concurrent local-model memory pressure).
- The **production 100ms ceiling** is enforced by the resolver under *whatever* concurrent load exists — and `local_models` (B5) is in shadow, meaning the M5 Max may be running Qwen3.6-35B-A3B inference for B5 shadow logging at the same moment B6 is asked to route.

If p95 in eval is 50ms but p95 under concurrent B5 load is 70ms with p99 at 110ms, B6 will pass the promotion gate but tail-block resolution for ~1 in 100 calls under realistic conditions. With ~hundreds of subagent calls per sprint (the proposal's own latency motivation, INPUT.md:34), this is a couple of router-induced stalls per sprint — the very thing B6 is meant to *eliminate*.

**Concrete remedy:** Either (a) tighten the promotion gate to `p99 < timeout_ms / 2` (i.e., `p99 < 50ms` if `timeout_ms = 100`), or (b) require the latency benchmark in bead `.19.3` (INPUT.md:237) to run *under concurrent B5 load*, not in isolation. The LoRA-pipeline sibling will have the most direct take on whether this is feasible.

### P1 — "Garbage response" failure mode is named in spec but never defined

`spec.severity_examples` for this agent (in `microrouter-track-b6-adjacent.json`) and the success_hints both reference "garbage JSON response" as a failure mode the spec must address. INPUT.md does not define what counts as garbage:

- HTTP 200 with malformed JSON?
- HTTP 200 with valid JSON whose `tier` field names a model not in `tier_mappings`?
- HTTP 200 with valid JSON naming a tier the agent is ineligible for (e.g., router proposes `haiku` for fd-safety)?
- HTTP 200 with valid JSON naming a *different* tier than the eligible set, e.g., `local:qwen3.5-9b-4bit` when only `cloud` is allowed?

Each of these has different correct fall-through behavior. The third (router proposes a model the agent is ineligible for) is the most important — under the resolver-chain reordering above, this is what defends fd-safety. Without a defined response-validation step, an adversarially-trained router (or even a confused legitimate one) can name a tier outside its allowed set and the resolver has no defined recovery path.

**Concrete remedy:** Spec a `_microrouter_validate_response` subroutine in the integration bead that (a) parses JSON, (b) confirms the named tier is a key in `tier_mappings`, (c) confirms the named tier is in the agent's allowed set per `agent-roles.yaml`, and (d) on any failure, falls through to the *next layer* of the chain (calibration), not the *whole chain*. List the test cases by name in the bead's "Done when" criteria.

### P2 — Decision-space output labels are not pinned to `tier_mappings` keys

INPUT.md:344 says `model: "local:qwen3.5-3b-microrouter-v0"` for the microrouter itself, but never specifies what *string namespace* the router's output uses. Existing chain consumers expect strings drawn from:
- `subagents.defaults` keys (`haiku`, `sonnet`, `opus`)
- `local_models.tier_mappings` keys (`local:qwen3.6-35b-a3b-4bit`, etc.)
- `dispatch.tiers` keys (`fast`, `deep`, `fast-clavain`, `deep-clavain`)

If the router was trained with one label set (say, `haiku|sonnet|opus`) and the resolver expects another (say, `C1|C2|C3` complexity tiers), the resolver hits a silent label-mismatch every call — falls through to B3 100% of the time and the router is dead in enforce mode without an obvious failure signal.

**Concrete remedy:** Pin the router's output label set to a named enum in the design bead (`.19.1`). The eval-methodology sibling will track this; flag it explicitly to them. Add a runtime assertion in `_microrouter_validate_response` that any label outside the enum triggers fall-through *and* a structured warning log.

### P2 — Auto-degradation `enforce → shadow` on model-not-loaded is asymmetric and adversarially triggerable

INPUT.md:372 specifies "Router model not loaded → mode auto-degrades to shadow (don't fail-closed)". This is asymmetric (enforce can drop to shadow but never the reverse) and creates two problems:

1. **Stealth shadow.** Once auto-degraded, the system runs in shadow until the operator notices. The proposal doesn't define a timeout, alarm, or auto-recovery. (The production-rollout-safety sibling will have the canonical take on this one — flagging only the architectural piece here.)
2. **Adversarial trigger.** If anything that can trigger the model-not-loaded path is reachable from outside the resolver (e.g., another process unloads the MLX adapter via interfer's MCP, the disk fills, the model file is moved), an attacker can degrade the system from `enforce` to `shadow` to revert routing decisions to B3. This is low-risk in single-user dev but worth naming.

**Concrete remedy:** Replace auto-degradation with **explicit fallback** — keep `mode = enforce` in config but treat each call as fall-through-to-B3 when the model is unloaded. The resolver does not mutate its own configured mode; the operator sees one fixed mode and an external signal (alert, metric) that the model is loaded or not. This is what production ranking systems do.

### P2 — Confidence-cascade verifier (`.19.7`) and main router shadow-mode interaction is undefined

Bead `.19.7` (INPUT.md:455-501) describes a *second* small model that scores draft outputs. The "Conditions to pursue" (INPUT.md:472-476) explicitly require the main router to ship to enforce first, which sounds safe — but the spec also allows the verifier to be in shadow mode while the main router is in enforce mode (INPUT.md:482, "mirrors beads 1-4 of this epic, scoped down").

That means at some point both systems will run concurrently, both modifying routing decisions in shadow logs, and there is no defined precedence. If both shadow logs disagree about the "right" decision for a call, post-hoc analysis cannot tell which one is the source of truth.

**Concrete remedy:** Specify in `.19.7` that the verifier's shadow log records the main router's decision as a *feature*, not as a parallel decision — i.e., the verifier is a downstream consumer of the router, not a peer. This makes their interaction unambiguous.

## Improvements

- **Make the resolver chain a YAML list, not a Go/Bash hard-coded order.** This is the single highest-leverage change — every "is the chain in the right order?" question becomes a config diff instead of an audit. The config-resolver-architecture sibling has the canonical take; flagging here only because it makes B6's insertion semantically reviewable.
- **Add a `chain` integration test** that asserts: given a fixed agent + phase + complexity + calibration entry + microrouter response, the resolved model is deterministic and matches a tabulated golden expectation. The current absence of such a test is what makes the P0s above hard to catch in code review.
- **Explicitly name the failure modes that are *not* fall-through.** Right now everything falls through to B3 silently. Two cases probably should *not* fall through: (a) router returns a model that requires explicit cloud opt-out for a `privacy=sensitive` task, and (b) router returns a label outside the enum. These should fail-loud, not fall-through.

## Anti-Overlap (handed off to siblings)

- LoRA training, loss design, latency benchmarking under load → **fd-lora-distillation-pipeline**
- Holdout integrity, oracle-upper-bound construction, per-tier metric stratification → **fd-eval-methodology-holdout**
- Shadow soak adequacy, rollback runbook, degradation alerting → **fd-production-rollout-safety**
- Schema bump correctness, endpoint port conflict, zero-cost-bypass guarantee → **fd-config-resolver-architecture**
