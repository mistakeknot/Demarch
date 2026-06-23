# Track B6 Microrouter — Epic + Children for Review

Source-of-truth: 8 beads (sylveste-s3z6.19 epic + 7 children).
Companion artifacts: `os/Clavain/config/routing.yaml` (existing 5-track routing stack), `os/Clavain/config/routing-overrides.schema.json`.

## Dep Graph Shape

```

🌲 Dependency tree for sylveste-s3z6.19:

sylveste-s3z6.19: [epic] Track B6: small-model microrouter for sub-task delegation [P1] (open) [1m[BLOCKED][m
    └── sylveste-s3z6: [interrank+interflux] Closed-loop model discovery — qualification feedback to AgMoDB, drift detection, proactive surfacing [P1] (in_progress)

```

## Bead Bodies

=== sylveste-s3z6.19 ===
○ sylveste-s3z6.19 [EPIC] · [epic] Track B6: small-model microrouter for sub-task delegation   [● P1 · OPEN]
Owner: 900667a0 · Type: epic
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Track B6: Small-model microrouter for sub-task delegation

Add a new resolver layer above B3 calibration in `os/Clavain/config/routing.yaml` that uses a small (~3B) local MLX model to make per-subagent model selection decisions during `/sprint` execute phase. Distilled from existing interspect verdict data; gated by mode=shadow|enforce identical to B2/B3/B4/B5.

## Why

Today the `phases.executing.model: sonnet` rule sends every subagent in the `execute` phase to the same tier. Across a sprint that can be hundreds of subagent calls — many of which (workflow chores, doc updates, simple greps wrapped in agent calls) don't need Sonnet. A learned router can decide haiku vs. sonnet vs. local-Qwen3.6-35B-A3B per call.

Cloud delegation via codex/ChatGPT OAuth is free at point of use, so the economic squeeze is smaller than typical FrugalGPT setups — but two non-cost wins remain:
- **Latency**: avoid cloud round-trip for trivial decisions (~100–300ms saved per call × hundreds of calls per sprint)
- **Privacy**: `routing.yaml` `privacy_routing` (lines 260–262) already mandates local for internal/sensitive tasks; a smarter router lets us push *more* traffic local without quality regression

## Why now

- 498 closed beads + interspect calibration data give us a real labeled corpus (task_text → agent → model → passed)
- B5 local_models is in shadow mode (`os/Clavain/config/routing.yaml:221`) — we have the local-routing plumbing already
- Qwen3.6-35B-A3B at C2 (`routing.yaml:244`) gives a strong baseline; a 3B router adds <2GB resident, doesn't compete with flash-MoE work on the M5 Max
- Sibling to sylveste-2ss (Flash-MoE benchmark suite) and child of sylveste-s3z6 (closed-loop model discovery) — same calibration-feedback story

## Non-goals

- NOT replacing the C1–C5 integer-threshold classifier in B2. That's the cheap fallback when microrouter is shadow/down.
- NOT training from scratch. Distillation from a larger judge (GPT-5.5 / Opus) onto Qwen3.5-3B-Instruct via LoRA.
- NOT routing fd-safety / fd-correctness — they keep their Sonnet floor (existing safety_floors at `routing.yaml:33-37`).

## Children (created as separate beads under this epic)

1. Brainstorm + design doc — pick router decision space (binary local/cloud vs. 3-way vs. full-tier), define training signal, paper read-through (RouteLLM, FrugalGPT, Hybrid LLM)
2. Build labeled dataset from interspect verdicts + bead history — `(task_text, agent, phase, model_used, passed)` tuples with augmentation strategy
3. Distillation training pipeline in `interlab` — LoRA on Qwen3.5-3B-Instruct, judge from GPT-5.5/Opus
4. Eval harness in `interfer/benchmarks/` — router accuracy + downstream pass@1 + latency overhead matrix (generalize the LCB v6 harness pattern)
5. Resolver integration in Clavain Go side — slot above B3 calibration, mode=off|shadow|enforce, schema bump to `routing-overrides.schema.json`
6. Privacy-routing extension — promote internal/sensitive tasks to use microrouter even when global mode is off
7. Confidence-cascade verifier (stretch) — separate small model that scores draft outputs for the existing B5 cascade (`routing.yaml:248-252`)

## Success criteria

- ≥ 90% agreement with calibrated baseline on holdout (else it regresses B3)
- ≥ 20% of execute-phase subagent calls routed to a cheaper tier than baseline with no pass@1 regression
- `mode: enforce` toggle ships with rollback documented (delete calibration file pattern, same as B3/B4)

## Risks

- Router becomes a new failure mode that's hard to debug — mitigated by shadow-mode soak (≥ 1 sprint) before enforce, identical to how B2/B3/B4 were promoted
- Training data is biased toward what's already been routed — mitigated by including augmented "would-have-routed-differently" counterfactuals from interspect's shadow logs
- Distillation collapses to "always pick Sonnet" if loss is naive — mitigated by per-tier calibration and cost-weighted loss (RouteLLM pattern)

## References

- `os/Clavain/config/routing.yaml` — existing 5-track routing, the seam where this slots in
- `os/Clavain/config/routing-overrides.schema.json` — schema needs a `microrouter:` section
- `interverse/interspect/` — verdict collection and calibration commands
- `interverse/interlab/` — autoresearch loop, where the distillation training will live
- `interverse/interfer/benchmarks/lcb_v6_matrix/` — harness template for the eval matrix
- Papers: RouteLLM (2024), FrugalGPT (Chen et al. 2023), Hybrid LLM (Ding et al. 2024)


LABELS: clavain, interfer, interlab, interspect, routing

PARENT
  ↑ ◐ sylveste-s3z6: (EPIC) [interrank+interflux] Closed-loop model discovery — qualification feedback to AgMoDB, drift detection, proactive surfacing ● P1

CHILDREN
  ↳ ○ sylveste-s3z6.19.1: [microrouter] Design doc + paper deep-read (decision space, training signal) ● P1
  ↳ ○ sylveste-s3z6.19.2: [microrouter] Build labeled dataset from interspect verdicts + bead history ● P1
  ↳ ○ sylveste-s3z6.19.3: [microrouter] Distillation training pipeline (LoRA on Qwen3.5-3B-Instruct) ● P1
  ↳ ○ sylveste-s3z6.19.4: [microrouter] Eval harness — accuracy + downstream pass@1 + latency matrix ● P1
  ↳ ○ sylveste-s3z6.19.5: [microrouter] Resolver integration in Clavain — wire into routing.yaml ● P1
  ↳ ○ sylveste-s3z6.19.6: [microrouter] Privacy-routing extension — sensitive tasks always engage router ● P2
  ↳ ○ sylveste-s3z6.19.7: [microrouter] Confidence-cascade verifier (stretch) ● P3
  ◐ 0/7 complete (0%)


=== sylveste-s3z6.19.1 ===
○ sylveste-s3z6.19.1 · [microrouter] Design doc + paper deep-read (decision space, training signal)   [● P1 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Microrouter design doc + paper deep-read

Pick the router's decision space, define the training signal, and read source papers before any code.

## Decisions to make (interview-driven)

1. **Decision space**: 2-way (local/cloud) vs. 3-way (haiku/sonnet/opus) vs. full-tier (haiku/sonnet/opus/local-C2/local-C3) vs. binary "delegate-to-codex y/n"
2. **Input features**: prompt text only? Or also (agent_name, phase, file_count, prior_calibration_score)?
3. **Training signal**: pass/fail from interspect verdicts? Or cost-weighted regret (FrugalGPT-style)? Or pairwise preference (RouteLLM)?
4. **Inference mode**: every subagent call invokes router? Or only `phases.executing` subagents? Or only when prompt tokens > N?

## Papers to read first (per user preference: read papers before designing)

- RouteLLM (Ong et al. 2024) — preference-data routing, the most directly applicable
- FrugalGPT (Chen, Zaharia, Zou 2023) — cascade with cost-aware acceptance
- Hybrid LLM (Ding et al. 2024) — small-model gate to large
- AutoMix (Madaan et al. 2024) — self-verification + cascade

## Output

`docs/brainstorms/2026-MM-DD-microrouter-track-b6-design.md` with: decision-space choice, feature set, loss, inference policy, eval plan, integration sketch (where in `os/Clavain/config/routing.yaml` resolution chain).

## Done when

- Design doc committed under `docs/brainstorms/`
- Followup beads created for any decisions that spawn standalone work
- User has agreed to the decision-space and loss choice (this is a design interview, not autonomous)

## Refs

- Parent: sylveste-s3z6.19
- Existing routing chain: `os/Clavain/config/routing.yaml:11`


LABELS: clavain, design, interfer, interlab, interspect, routing

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

BLOCKS
  ← ○ sylveste-s3z6.19.2: [microrouter] Build labeled dataset from interspect verdicts + bead history ● P1
  ← ○ sylveste-s3z6.19.3: [microrouter] Distillation training pipeline (LoRA on Qwen3.5-3B-Instruct) ● P1
  ← ○ sylveste-s3z6.19.5: [microrouter] Resolver integration in Clavain — wire into routing.yaml ● P1


=== sylveste-s3z6.19.2 ===
○ sylveste-s3z6.19.2 · [microrouter] Build labeled dataset from interspect verdicts + bead history   [● P1 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Build labeled training dataset from interspect verdicts + bead history

Construct `(task_text, agent, phase, complexity_tier, model_used, passed, latency_ms, cost_proxy)` tuples for router training.

## Sources

- `.clavain/interspect/routing-calibration.json` — per-agent hit rates with model
- `.clavain/interspect/delegation-calibration.json` — CC↔Codex delegation outcomes
- Bead history (Dolt): closed beads with verdicts, ~498 baseline per `os/Clavain/CLAUDE.md`
- Interspect evidence files — full verdict traces with prompt context
- Sprint logs in `.clavain/` and session JSONLs in `~/.claude/projects/`

## Augmentation strategy

- Counterfactual labels from interspect shadow-mode logs (B3 shadow / B5 shadow recorded "would have routed to X")
- Hard-negative mining: tasks where Sonnet passed but Haiku would have too (waste) and where Haiku failed but Sonnet succeeded (miss)
- Synthetic perturbations: paraphrase prompts to expand the surface of "same task, different wording"

## Output

- `interverse/interlab/datasets/microrouter-v0/` — JSONL train/val/test splits
- Coverage report: agents covered, phase distribution, model distribution, class imbalance numbers
- Privacy scrub: any sensitive content (per `privacy_routing` classification) excluded or redacted

## Done when

- ≥ 5K labeled examples across train/val/test
- Class balance documented; if severe (e.g., 95% sonnet), augmentation plan in place
- Holdout split is by-time (last 2 weeks) not random — to catch temporal leakage from calibration feedback

## Refs

- Parent: sylveste-s3z6.19
- Depends on: design bead (decision space dictates label format)


LABELS: clavain, dataset, interfer, interlab, interspect, routing

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

DEPENDS ON
  → ○ sylveste-s3z6.19.1: [microrouter] Design doc + paper deep-read (decision space, training signal) ● P1

BLOCKS
  ← ○ sylveste-s3z6.19.3: [microrouter] Distillation training pipeline (LoRA on Qwen3.5-3B-Instruct) ● P1


=== sylveste-s3z6.19.3 ===
○ sylveste-s3z6.19.3 · [microrouter] Distillation training pipeline (LoRA on Qwen3.5-3B-Instruct)   [● P1 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Distillation training pipeline in interlab — LoRA on Qwen3.5-3B-Instruct

Train the microrouter as a LoRA adapter on Qwen3.5-3B-Instruct using the labeled dataset. Judge labels from GPT-5.5 xhigh fast (codex CLI, OAuth) for any examples missing ground truth.

## Approach

- Base: `mlx-community/Qwen3.5-3B-Instruct-4bit` (~2GB resident)
- Method: LoRA fine-tune via mlx-lm (rank 8 or 16, alpha 32)
- Loss: depends on design bead — likely cross-entropy over tier classes for v0, cost-weighted regret for v1
- Judge augmentation: where dataset lacks ground truth, prompt GPT-5.5 with `(task, model_options) → "which tier?"` to fill gaps
- Eval split is by-time (held out last 2 weeks)

## Why Qwen3.5-3B not Phi-4-mini or ModernBERT-encoder

Qwen3.5 is what's already on disk and what the rest of the routing stack uses (consistency with `routing.yaml:230` tier mappings). 3B fits resident with no memory pressure on the M5 Max. Encoder-only would be smaller/faster but loses the ability to reason about novel agent names not in training.

Open question for design bead: encoder-only Phase 2 if 3B latency is too high.

## Output

- `interverse/interlab/campaigns/microrouter-v0/` — training run logs
- `~/.cache/huggingface/hub/models--sylveste--qwen3.5-3b-microrouter-v0/` — adapter weights
- Training report: train/val curves, holdout accuracy, per-tier confusion matrix

## Done when

- Adapter checkpoint saved
- Holdout accuracy reported (target ≥ 0.85 vs. calibrated baseline; final bar set in design bead)
- Inference-time latency benchmarked locally — must be < 100ms p95 on M5 Max for the eval bead to even bother

## Refs

- Parent: sylveste-s3z6.19
- Depends on: dataset bead, design bead
- Existing interlab pattern: `interverse/interlab/` autoresearch loops


LABELS: clavain, interfer, interlab, interspect, mlx, routing, training

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

DEPENDS ON
  → ○ sylveste-s3z6.19.1: [microrouter] Design doc + paper deep-read (decision space, training signal) ● P1
  → ○ sylveste-s3z6.19.2: [microrouter] Build labeled dataset from interspect verdicts + bead history ● P1

BLOCKS
  ← ○ sylveste-s3z6.19.4: [microrouter] Eval harness — accuracy + downstream pass@1 + latency matrix ● P1


=== sylveste-s3z6.19.4 ===
○ sylveste-s3z6.19.4 · [microrouter] Eval harness — accuracy + downstream pass@1 + latency matrix   [● P1 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Microrouter eval harness — router accuracy + downstream pass@1 + latency matrix

Generalize the LCB v6 matrix harness pattern (`interverse/interfer/benchmarks/`) to evaluate the microrouter end-to-end, not just as a classifier.

## What the matrix measures

Per (router_variant × policy × workload):

1. **Router accuracy**: agreement with calibrated baseline on holdout
2. **Downstream pass@1**: when router picks model X, does the actual task pass? (this is the only metric that matters)
3. **Latency**: p50/p95/p99 of router inference + downstream model inference combined
4. **Cost proxy**: weighted token spend assuming per-tier pricing
5. **Routing distribution**: % to each tier; flag if collapse to one tier

## Workloads

- LCB v6 cached problems (`interverse/interfer/benchmarks/datasets_cache/livecodebench_v6.jsonl`) — code reasoning slice
- Replayed bead-history tasks from holdout split — realistic distribution
- Synthetic adversarial set: tasks designed to look easy but require deep reasoning (catch over-routing to haiku)

## Comparators (matrix axes)

- `none` — no microrouter, B1+B2+B3 baseline (control)
- `microrouter-shadow` — router runs but doesn't apply
- `microrouter-enforce` — full pipeline
- `oracle-upper-bound` — perfect routing (post-hoc, with ground truth) — establishes ceiling

## Output

- `interverse/interfer/benchmarks/microrouter_v0_matrix/` — JSONL + summary, durable record (mirrors LCB v6 layout)
- `docs/benchmarks/2026-MM-DD-microrouter-v0-matrix.md` — narrative findings

## Gates for promotion (off→shadow→enforce)

- Off → shadow: router latency < 50ms p95, accuracy ≥ baseline
- Shadow → enforce: ≥ 1 sprint of shadow-mode soak, no pass@1 regression vs. B3 baseline, ≥ 20% reroute rate
- These mirror the B2/B3/B4/B5 promotion pattern

## Done when

- Matrix run complete, durable record committed
- Findings doc references which gate the router clears
- Followup beads created for any failures that need investigation

## Refs

- Parent: sylveste-s3z6.19
- Depends on: training bead
- Harness template: `interverse/interfer/benchmarks/holistic_benchmark.py` and `scripts/run_lcb_matrix.sh`


LABELS: benchmarks, clavain, eval, interfer, interlab, interspect, routing

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

DEPENDS ON
  → ○ sylveste-s3z6.19.3: [microrouter] Distillation training pipeline (LoRA on Qwen3.5-3B-Instruct) ● P1

BLOCKS
  ← ○ sylveste-s3z6.19.7: [microrouter] Confidence-cascade verifier (stretch) ● P3


=== sylveste-s3z6.19.5 ===
○ sylveste-s3z6.19.5 · [microrouter] Resolver integration in Clavain — wire into routing.yaml   [● P1 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Resolver integration in Clavain Go side — wire microrouter into routing.yaml

Add the `microrouter:` section to `os/Clavain/config/routing.yaml`, bump `routing-overrides.schema.json`, and slot the new resolver layer above B3 calibration in the resolution chain (per `routing.yaml:11`).

## Schema additions

```yaml
microrouter:
  mode: off  # off | shadow | enforce
  endpoint: "http://localhost:8421/route"  # interfer-served
  model: "local:qwen3.5-3b-microrouter-v0"
  timeout_ms: 100  # hard ceiling — router timeout falls through to B3
  ineligible_agents:
    - fd-safety
    - fd-correctness  # safety floors stay sonnet
  shadow_log: ".clavain/interspect/microrouter-shadow.jsonl"
```

## Resolver chain change

Update the resolver to insert microrouter between complexity (B2) and overrides[agent] in the priority chain. New order:

```
kernel overrides
  > complexity override (if enabled+matching)
  > microrouter override (if enabled+matching+not-timed-out+agent-eligible)   ← NEW
  > overrides[agent]
  > calibration (if enabled+matching)
  > phases[phase].categories[cat]
  > phases[phase].model
  > defaults.categories[cat]
  > defaults.model
```

## Failure modes to handle

- Router endpoint unreachable → fall through to B3 (don't block resolution)
- Router times out > timeout_ms → fall through, log incident
- Router model not loaded → mode auto-degrades to shadow (don't fail-closed)

## Files touched

- `os/Clavain/config/routing.yaml` — new section
- `os/Clavain/config/routing-overrides.schema.json` — schema bump
- Clavain Go resolver (path TBD — find it during implementation; likely `core/intercore` or `os/Clavain/internal`)
- Tests for resolver chain (router on/off, agent ineligible, timeout, garbage response)

## Done when

- Schema validates new section
- Resolver tests cover all failure modes
- `mode: shadow` works end-to-end (router called, decision logged, base routing applied)
- Documented in `os/Clavain/AGENTS.md` alongside B2/B3/B4/B5

## Refs

- Parent: sylveste-s3z6.19
- Depends on: training bead (need a checkpoint to actually call) — but schema/resolver work can proceed in parallel as soon as design bead lands
- Existing pattern: every other track (B2 line 102, B3 line 167, B4 line 183, B5 line 220) shows the mode=off|shadow|enforce template to copy


LABELS: clavain, go, interfer, interlab, interspect, routing

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

DEPENDS ON
  → ○ sylveste-s3z6.19.1: [microrouter] Design doc + paper deep-read (decision space, training signal) ● P1

BLOCKS
  ← ○ sylveste-s3z6.19.6: [microrouter] Privacy-routing extension — sensitive tasks always engage router ● P2


=== sylveste-s3z6.19.6 ===
○ sylveste-s3z6.19.6 · [microrouter] Privacy-routing extension — sensitive tasks always engage router   [● P2 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Privacy-routing extension — promote sensitive tasks through microrouter

Extend `routing.yaml:260-262` privacy_routing so internal/sensitive tasks engage the microrouter even when global `mode=off`. Sensitive tasks must always stay local; the microrouter helps pick *which* local model.

## Why this is separate from the main resolver bead

Privacy is a kill-switch. Today, sensitive tasks → local-only blanket. With microrouter, we can route within the local fleet (Qwen3.5-9B for cheap C1, Qwen3.6-35B-A3B for C2/C3) without ever touching cloud. That's a quality win the global mode toggle shouldn't gate.

## Scope

- Add `microrouter.privacy_override: always` flag — when task carries `privacy=internal|sensitive`, microrouter runs regardless of global mode
- Sensitive-task router output is constrained to `local:*` tiers only (cloud filtered out at resolver level)
- Audit trail: every sensitive-task routing decision is logged to a separate JSONL (`microrouter-privacy.jsonl`) with no prompt content (just decision metadata) — keep `privacy_routing.sensitive: local-only-no-log` semantics intact

## Decisions to make

- Where does the `privacy=` signal come from? User CLI flag? Repo-level config? Per-bead label? (likely the last — `bd label privacy=sensitive`)
- Should the microrouter itself see prompt content for sensitive tasks, or only metadata (agent, phase, length)? — probably metadata-only

## Done when

- Schema supports privacy override
- Resolver routes sensitive tasks through microrouter even with `mode=off`
- Privacy audit log exists and excludes prompt content
- Test: a `privacy=sensitive` task with `mode=off` globally still gets a router decision and never escalates to cloud

## Refs

- Parent: sylveste-s3z6.19
- Depends on: resolver bead (need the basic integration first)
- Existing: `os/Clavain/config/routing.yaml:260-262`


LABELS: clavain, interfer, interlab, interspect, privacy, routing

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

DEPENDS ON
  → ○ sylveste-s3z6.19.5: [microrouter] Resolver integration in Clavain — wire into routing.yaml ● P1


=== sylveste-s3z6.19.7 ===
○ sylveste-s3z6.19.7 · [microrouter] Confidence-cascade verifier (stretch)   [● P3 · OPEN]
Owner: 900667a0 · Type: task
Created: 2026-05-02 · Updated: 2026-05-02

DESCRIPTION
# Confidence-cascade verifier (stretch) — small model that scores draft outputs

Separate small model that scores draft outputs from B5 local models, replacing the current first-3-token-probability cascade in `routing.yaml:248-252` with a learned verifier. Stretch goal — only pursue if main microrouter ships and the cascade's false-accept rate is the dominant remaining issue.

## Why this is a stretch / separate bead

The main microrouter (beads 1-5) routes *before* generation. This verifier runs *after* generation on the draft and decides accept / regenerate / escalate. It's a different artifact, different training signal (output quality, not task-difficulty), different failure modes.

The current cascade is heuristic (first-3-token avg probability < 0.6 = escalate). It's almost certainly leaving wins on the table — early-token probability correlates poorly with overall output quality. But the heuristic is also free, and replacing free with a model call needs a real win.

## Conditions to pursue

- Main microrouter has shipped to enforce mode
- Eval matrix shows ≥ 10% of B5 escalations were unnecessary (high-confidence local outputs being kicked to cloud) — wasted cloud spend
- OR ≥ 10% of B5 acceptances were wrong (low-quality local outputs being accepted because early tokens looked fine) — quality leak

## Approach (if pursued)

- Reward-model-style scorer: small (1B–3B) model trained on `(task, draft, was_passed)` triples
- Calibrate threshold: accept@p, escalate@q
- Replace `confidence_cascade.accept_threshold` and `escalate_threshold` with verifier output

## Done when

- Decision made: pursue or close as wontfix with rationale
- If pursued: full design + train + eval cycle (mirrors beads 1-4 of this epic, scoped down)

## Refs

- Parent: sylveste-s3z6.19
- Depends on: eval bead (need the data to decide if pursuing makes sense)
- Existing cascade: `os/Clavain/config/routing.yaml:248-252`


LABELS: clavain, interfer, interlab, interspect, routing, stretch

PARENT
  ↑ ○ sylveste-s3z6.19: (EPIC) [epic] Track B6: small-model microrouter for sub-task delegation ● P1

DEPENDS ON
  → ○ sylveste-s3z6.19.4: [microrouter] Eval harness — accuracy + downstream pass@1 + latency matrix ● P1



## Existing routing.yaml (the architecture this proposal extends)

```yaml
# Model routing policy for Clavain (Track B1+B2+B3+B4: Static + Complexity + Calibration + Delegation Routing)
#
# Five namespaces:
#   subagents:   Claude Code agents (haiku/sonnet/opus/inherit)
#   dispatch:    Codex CLI agents (concrete model IDs)
#   complexity:  Task complexity → model override layer (B2)
#   calibration: Evidence-based agent model calibration (B3)
#   delegation:  CC↔Codex routing policy (B4)
#
# Subagent resolution order (highest priority first):
#   kernel overrides > complexity override (if enabled+matching) > overrides[agent] > calibration (if enabled+matching) > phases[phase].categories[cat] > phases[phase].model > defaults.categories[cat] > defaults.model
#
# Dispatch resolution:
#   complexity tier promotion/demotion (if enabled) > tiers[name].model, with fallback chain
#
# When this file is absent, all consumers fall back to their existing defaults.

subagents:
  defaults:
    model: sonnet
    categories:
      research: haiku
      review: sonnet
      workflow: sonnet
      synthesis: haiku
      explore: haiku
      general-purpose: sonnet

  # Agent-level overrides (highest priority in resolution chain).
  # Safety floors: interstat data shows fd-safety on Haiku 47%, fd-correctness 26%.
  # These must NEVER run below Sonnet regardless of phase or category routing.
  # Evidence: iv-jocaw routing experiment, iv-dthn Loop 2/4 thresholds.
  overrides:
    interflux:review:fd-safety: sonnet
    interflux:review:fd-correctness: sonnet
    interflux:fd-safety: sonnet
    interflux:fd-correctness: sonnet

  phases:
    brainstorm:
      model: opus
      categories:
        # Research agents stay cheap even during brainstorm
        research: haiku
        # Review agents (flux-drive Step 1b) do structured analysis, not creative thinking
        review: sonnet
        synthesis: haiku
    brainstorm-reviewed:
      model: sonnet
    strategized:
      model: sonnet
    strategy-reviewed:
      model: sonnet
    planned:
      model: sonnet
    executing:
      model: sonnet
      categories:
        # B1+safety floors is Pareto-optimal (iv-jc4j) — no opus uplift needed
        review: sonnet
    shipping:
      model: sonnet
    reflect:
      model: sonnet
    done:
      model: sonnet

dispatch:
  tiers:
    fast:
      model: gpt-5.3-codex-spark
      description: Scoped read-only tasks, exploration, verification, quick reviews
    fast-clavain:
      model: gpt-5.3-codex-spark-xhigh
      description: Clavain interserve-mode default for read-only/administrative tasks
    deep:
      model: gpt-5.3-codex
      description: Generative tasks, implementation, complex reasoning, debates
    deep-clavain:
      model: gpt-5.3-codex-xhigh
      description: Clavain interserve-mode high-complexity/research/flux-drive dispatch

  # Fallback if a tier is unavailable (API returns model_not_found)
  fallback:
    fast: deep
    fast-clavain: deep-clavain
    deep-clavain: deep

# Complexity-aware routing (Track B2)
#
# When enabled, task complexity signals (token count, file scope, reasoning depth)
# classify each task into a tier (C1-C5). Tiers can override the base model selection
# from subagents: and promote/demote dispatch tiers.
#
# mode:
#   off     — Zero-cost bypass. Complexity section is not parsed. (default)
#   shadow  — Classify and log what *would* change, but apply base routing.
#   enforce — Classify and apply complexity overrides.
#
# Zero-cost guarantee: when mode=off, routing_resolve_model behaves identically
# to B1 with no extra function calls, no config parsing, no overhead.
complexity:
  mode: enforce  # Promoted from shadow 2026-03-18 (Sylveste-k2xf.5). Safety floors active.

  # Classification thresholds — a task's complexity tier is the highest tier
  # whose ANY threshold is met. Evaluated top-down (C5 first).
  # Signals: prompt_tokens (int), file_count (int), reasoning_depth (1-5 scale)
  tiers:
    C5:
      description: Architectural — multi-system design, novel algorithms, cross-cutting concerns
      prompt_tokens: 4000
      file_count: 15
      reasoning_depth: 5
    C4:
      description: Complex — multi-file implementation, significant refactoring
      prompt_tokens: 2000
      file_count: 8
      reasoning_depth: 4
    C3:
      description: Moderate — single-component feature, standard patterns
      prompt_tokens: 800
      file_count: 4
      reasoning_depth: 3
    C2:
      description: Simple — focused change, well-understood scope
      prompt_tokens: 300
      file_count: 2
      reasoning_depth: 2
    C1:
      description: Trivial — typo fix, config tweak, single-line change
      prompt_tokens: 0
      file_count: 0
      reasoning_depth: 1

  # Per-tier model overrides. These layer on TOP of base B1 resolution.
  # Only specified fields override; unspecified fields inherit from B1.
  # "inherit" means "use B1 result" (explicit passthrough).
  overrides:
    C5:
      subagent_model: opus
      dispatch_tier: deep
    C4:
      subagent_model: opus
      dispatch_tier: deep
    C3:
      subagent_model: inherit
      dispatch_tier: inherit
    C2:
      subagent_model: haiku
      dispatch_tier: fast
    C1:
      subagent_model: haiku
      dispatch_tier: fast

# Evidence-based calibration (Track B3)
#
# Interspect collects verdict outcomes from flux-drive agent reviews. The
# /interspect:calibrate command computes per-agent hit rates and writes
# .clavain/interspect/routing-calibration.json.
#
# mode:
#   shadow  — Log what would change, but apply base routing. (default)
#   enforce — Apply calibrated model recommendations.
#
# Env override: INTERSPECT_ROUTING_MODE=enforce
# Escape hatch: delete .clavain/interspect/routing-calibration.json
calibration:
  mode: enforce  # Promoted from shadow 2026-04-01. 21+ sprint sessions + 498 closed beads provide calibration baseline.

# CC↔Codex delegation routing (Track B4)
#
# Controls when tasks should be delegated from Claude Code to Codex CLI
# via the codex-delegate subagent. The routing policy is injected into
# Claude's context at session start; the subagent handles dispatch.
#
# mode:
#   off     — No delegation policy injected. codex-delegate agent still available manually.
#   shadow  — Policy injected, outcomes logged, but Claude decides freely. (default)
#   enforce — Policy injected with strong "MUST delegate" language for matching categories.
#
# Calibration: .clavain/interspect/delegation-calibration.json (written by interspect)
# Escape hatch: set mode=off or delete calibration file
delegation:
  mode: enforce

  # Task categories and their default routing preference.
  # codex-first: delegate to codex-delegate by default
  # claude-only: keep in Claude Code (never auto-delegate)
  # adaptive: route based on calibration data (codex-first when pass_rate > min_category_pass_rate)
  categories:
    exploration: codex-first
    implementation: codex-first
    review: codex-first
    test-generation: codex-first
    doc-update: codex-first
    architecture: claude-only
    brainstorm: claude-only
    interactive: claude-only

  # Complexity ceiling — tasks above this tier stay in Claude regardless of category
  max_delegatable_complexity: C3

  # Minimum pass rate (from calibration data) to auto-delegate a category
  # Categories below this get advisory-only routing even in enforce mode
  min_category_pass_rate: 0.70

# Local model routing via interfer (Track B5)
#
# Routes eligible tasks to local MLX models served by the interfer plugin.
# Complexity tiers map to local model tiers; confidence cascade escalates
# to cloud when local model confidence is too low.
#
# mode:
#   off     — No local routing. All tasks use cloud models. (default)
#   shadow  — Log what would route locally, but use cloud models.
#   enforce — Route eligible tasks to local models via interfer.
#
# Env override: INTERFERE_ROUTING_MODE=enforce
# Escape hatch: set mode=off or stop the interfer server
local_models:
  mode: shadow  # Promoted from off 2026-03-26 (Sylveste-09n). Shadow logs what would route locally.
  endpoint: "http://localhost:8421"

  # Map local model identifiers to Clavain model tiers (1=haiku, 2=sonnet, 3=opus)
  # Updated 2026-04-29 (Sylveste-2ss): C2 promoted to Qwen3.6-35B-A3B after LCB v6
  # matrix showed +22.3 pass@1 over 3.5 at 5× decode speed (40.0% vs 17.7%, n=175).
  # Thinking mode hurts at <600s budgets (-18.3 points, 104 runtime errors); keep off.
  # See docs/benchmarks/2026-04-27-lcb-v6-matrix.md for the full A/B.
  tier_mappings:
    "local:qwen3.5-9b-4bit": 1          # ~5GB, fast draft (mlx-community/Qwen3.5-9B-OptiQ-4bit)
    "local:qwen3.6-35b-a3b-4bit": 2     # ~18GB, MoE 3B active (mlx-community/Qwen3.6-35B-A3B-4bit), enable_thinking=False
    "local:nemotron-30b-a3b-8bit": 2     # ~32GB, MoE 3B active (mlx-community/Nemotron-Cascade-2-30B-A3B-8bit)
    "local:qwen3.5-122b-a10b-4bit": 3   # ~65GB, MoE 10B active — benchmarked 2.99 tok/s, uses entire memory budget
    "local:gpt-oss-120b-mxfp4": 3        # ~60GB, largest that fits (mlx-community/gpt-oss-120b-MXFP4-Q8)
    # flash-moe:qwen3.5-397b demoted 2026-04-29 (Sylveste-2ss): LCB v6 matrix found
    # 4 tok/s actual vs 12.9 spec'd, 24.8% pass@1 on n=141 with worker crash at #151.
    # C3 traffic now escalates to cloud; flash-moe is research-only pending Sylveste-6f0.

  # Complexity tier -> preferred local model
  # Updated 2026-04-29 (Sylveste-2ss): 3.5 → 3.6 across C1/C2; C3 escalates to cloud
  # because flash-moe's wins are a strict subset of cloud's at this budget.
  complexity_routing:
    C1: "local:qwen3.6-35b-a3b-4bit"         # MoE 3B active, 15s median gen — Qwen3.6 plain 4bit, no thinking
    C2: "local:qwen3.6-35b-a3b-4bit"         # same model, zero marginal cost vs C1
    C3: "cloud"                              # GPT-5.5 xhigh fast (codex CLI) — 84.0% pass@1 on LCB v6, dominates flash-moe

  # Confidence cascade: if first-3-token avg probability < threshold, escalate
  confidence_cascade:
    enabled: true
    accept_threshold: 0.8      # accept local output above this
    escalate_threshold: 0.6    # try larger local model between 0.6-0.8
    cloud_threshold: 0.6       # escalate to cloud below this

  # Agents that MUST NOT use local models (safety floors)
  ineligible_agents:
    - fd-safety
    - fd-correctness

  # Privacy routing: tasks classified as internal/sensitive always route locally
  privacy_routing:
    internal: "local-only"
    sensitive: "local-only-no-log"
```
