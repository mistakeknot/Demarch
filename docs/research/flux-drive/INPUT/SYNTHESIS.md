# Microrouter Track B6 — Multi-Agent Review Synthesis

**Target**: epic `sylveste-s3z6.19` + 7 children (microrouter for sub-task delegation), proposing a 6th routing track inserted into `os/Clavain/config/routing.yaml`'s existing 5-track stack.

**Reviewers**: 5 Track A adjacent-domain specialists from `.claude/flux-gen-specs/microrouter-track-b6-adjacent.json`:

- `fd-routing-cascade-design` — resolver chain correctness
- `fd-lora-distillation-pipeline` — LoRA training pipeline on MLX
- `fd-eval-methodology-holdout` — eval methodology and holdout integrity
- `fd-production-rollout-safety` — rollout, rollback, degradation
- `fd-config-resolver-architecture` — schema and resolver insertion

**Methodology note**: This review was conducted in-process (multiple specialist personas adopted sequentially within one model) rather than via parallel subagent dispatch — the Task tool was not available in this environment, so the flux-drive Phase 2 dispatch fell back to in-context multi-perspective review. Findings are still grounded in concrete codebase reads (`lib-routing.sh`, `routing.yaml`, `routing-overrides.schema.json`, `interfer/server/__main__.py`); the reproducibility difference is parallelism, not depth.

## Findings Counts

| Severity | Count | Files |
|---|---|---|
| **P0** | **8** | 2 (cascade), 1 (lora), 2 (eval), 2 (rollout-safety), 3 (config-arch) — but several P0s are cross-referenced (same root cause from different angles); de-duplicated to **6 distinct P0s** |
| **P1** | 17 | distributed across all 5 files |
| **P2** | 13 | distributed across all 5 files |
| **P3** | 2 | one in lora-pipeline, one in eval |
| **Total** | **40 findings across 5 specialist files** | |

## The 6 Distinct P0s (Highest-Severity)

These are the load-bearing blockers. None of them prevent design discussion, but all must be resolved before code lands.

### P0-1: Resolver chain insertion above `overrides[agent]` shadows safety floors
**Source**: `fd-routing-cascade-design`. The proposed chain order places microrouter *above* `overrides[agent]`, which currently holds the fd-safety/fd-correctness `sonnet` overrides. The defense (`microrouter.ineligible_agents`) duplicates safety state across two lists with no convergence check, and qualifies-name vs bare-name matching is unspecified.
**Fix shape**: Move the microrouter resolver layer *below* `overrides[agent]` instead of above. Then fd-safety/fd-correctness exit at the existing override step before the router is consulted at all.

### P0-2: Endpoint `localhost:8421/route` collides with B5 interfer server (port 8421)
**Source**: `fd-config-resolver-architecture`. Confirmed by code: `interverse/interfer/server/__main__.py:22` defaults to port 8421; B5 `local_models.endpoint` (`routing.yaml:729`) is `http://localhost:8421`. The proposed B6 endpoint shares the port. If the proposal means "same server, two paths" the interfer server modification work is unscoped; if it means "different servers" the port collision is a deployment failure.
**Fix shape**: Move B6 to a different port (e.g., 8422) for v0. Re-evaluate when there's a real reason to colocate.

### P0-3: "Bump `routing-overrides.schema.json`" targets the wrong schema
**Source**: `fd-config-resolver-architecture`. That file (124 lines, read in this review) is the flux-drive interspect-overrides schema with `pattern: ^fd-[a-z][a-z0-9-]*$` and `action: exclude|propose`. It has nothing to do with routing.yaml structure. There is no JSON Schema validator for routing.yaml in the repo at all.
**Fix shape**: Drop the reference from `.19.5`. Either (a) accept that routing.yaml has no schema validator, documented explicitly, or (b) author `routing.schema.json` as a separate work item covering all six tracks.

### P0-4: "Clavain Go resolver (path TBD)" — the resolver is Bash, not Go
**Source**: `fd-config-resolver-architecture`. `os/Clavain/scripts/lib-routing.sh` is the actual resolver — 1475 lines of Bash with a YAML parser state machine and the `routing_resolve_model_complex` function called from hooks. The Go side consumes routing decisions but doesn't make them. Bead `.19.5`'s implementation plan assumes the wrong language and module.
**Fix shape**: Update `.19.5` "Files touched" to: `lib-routing.sh` (new parser block, new runtime function, wiring), `routing.yaml` (new section), Bash tests for the resolver chain.

### P0-5: Holdout target ≥ 0.85 accuracy is satisfied by majority-class collapse
**Source**: `fd-lora-distillation-pipeline`. If the training corpus is ~85% Sonnet (plausible given `phases.executing.model: sonnet` and safety overrides), a model that predicts "sonnet" always trivially clears the gate, ships to shadow with 0% reroute rate, and never advances to enforce. The risk section names this as a risk but the gate doesn't catch it.
**Fix shape**: Replace single-aggregate-accuracy gate with a vector: per-tier recall ≥ 0.60 AND aggregate accuracy ≥ 0.85. Per-tier confusion matrix promoted to a first-class output.

### P0-6: Calibration feedback loop creates temporal leakage through training labels
**Source**: `fd-eval-methodology-holdout`. `routing-calibration.json` is the *training signal* (verdict outcomes feed it) AND a *running artifact* (it updates after the holdout cut date). If judge augmentation in `.19.3` consults the live calibration file, the holdout test split contains signal that wasn't available at train start. The "by-time" holdout protects against random leakage but not this calibration-loop leakage.
**Fix shape**: Define a "calibration freeze date" matching the holdout cut. Snapshot `routing-calibration.json` at that date; pin all training/judge/eval reads to the snapshot. Add a SHA hash check across training, judge, and eval phases.

(Plus a 7th P0-tier finding from `fd-production-rollout-safety` worth highlighting:)

### P0-7 (rollout-safety angle): Auto-degrade `enforce → shadow` is invisible to the operator
**Source**: `fd-production-rollout-safety`. INPUT.md:372 says "Router model not loaded → mode auto-degrades to shadow" with no log entry, metric, or alert. The configured `mode: enforce` stays "enforce" while the runtime acts as `shadow`. Production incident profile: silent fall-through for an entire sprint that gets attributed to enforce-mode B6 in calibration data, corrupting future analysis.
**Fix shape**: Don't mutate runtime mode. Keep configured mode; treat each call as fall-through-to-B3 when the model is unloaded; emit structured log + metric on every fall-through; alarm on sustained fall-through.

## Cross-Cutting Themes

Three patterns recur across the 5 specialist findings:

### Theme 1: Lists that should be one source of truth
- Safety floors live in `subagents.overrides`, `_ROUTING_SF_AGENT_MIN` (from `agent-roles.yaml`), and the proposed `microrouter.ineligible_agents` — three lists requiring manual convergence (P0-1, plus issue #6 in cascade-design and config-resolver-architecture).
- Resolution chain order lives in routing.yaml comments AND lib-routing.sh code with no machine-readable list (config-resolver P1, cascade-design improvement).
- Recommended structural fix: a `resolution_chain:` YAML list in routing.yaml that lib-routing.sh honors, plus a config-load-time intersection check that warns when safety lists diverge.

### Theme 2: Gates with the wrong shape
- ≥ 0.85 holdout accuracy is satisfied by collapse (P0-5).
- ≥ 90% agreement with calibrated baseline AND ≥ 20% reroute rate are mutually exclusive against the same baseline (eval P1).
- ≥ 50ms p95 in eval vs 100ms timeout in production are at different measurement points (cascade P1, lora P1).
- ≥ 1 sprint shadow soak treats sprints as fungible when they are not (rollout-safety P1).
- Recommended structural fix: every gate in this epic should be rewritten to (a) name its baseline explicitly, (b) be measured under conditions matching production, and (c) where a single gate can be gamed (collapse), require a *vector* of metrics not a scalar.

### Theme 3: Failure modes named but not specified
- "Garbage response" appears in failure-mode lists with no definition (cascade P1).
- "Endpoint unreachable" includes "endpoint up but path 404" only by accident; not differentiated from "endpoint down" (config-arch P0-2 byproduct).
- "Mode auto-degrades" has no operator signal (P0-7).
- "Decision space label namespace" is unspecified — silent label mismatch is a possible silent failure (cascade P2).
- Recommended structural fix: add a `_microrouter_validate_response` subroutine in `.19.5` that explicitly enumerates fall-through reasons and emits structured logs differentiating them.

## Output Files Written

All 5 specialist findings files plus this synthesis are at `/Users/sma/projects/Sylveste/docs/research/flux-drive/INPUT/`:

| File | Findings | Highest |
|---|---|---|
| `fd-routing-cascade-design.md` | 8 | P0 ×2 |
| `fd-lora-distillation-pipeline.md` | 8 | P0 ×1 |
| `fd-eval-methodology-holdout.md` | 8 | P0 ×2 |
| `fd-production-rollout-safety.md` | 8 | P0 ×2 |
| `fd-config-resolver-architecture.md` | 8 | P0 ×3 |
| `SYNTHESIS.md` | (this file) | — |

## Recommended Next Steps

In order of leverage:

1. **Fix the three factual errors in `.19.5` first** (P0-2, P0-3, P0-4). The bead currently says "schema bump routing-overrides.schema.json" and "Go resolver path TBD" — both wrong. Until corrected, no implementation can start. Estimate: a 30-minute bead-body edit.

2. **Reorder the resolver chain** to put microrouter below `overrides[agent]` (P0-1). This is a one-line change to the proposed chain in `.19.5` plus a corresponding two-line change to `lib-routing.sh`. Eliminates the safety-floor bypass risk by construction.

3. **Specify the holdout-protection protocol in `.19.2`** (P0-6) and the per-tier recall gates in `.19.3` (P0-5). These are the two highest-impact methodology fixes; together they mean the eval matrix produces honest numbers and the trained model isn't a constant function.

4. **Write the rollback runbook** for `os/Clavain/AGENTS.md` (P0 from rollout-safety + the explicit rollback claim in INPUT.md:64). This is a several-hour writing task that closes the operational-readiness gap.

5. **Address the auto-degrade visibility issue** (P0-7) — replace silent runtime mutation with explicit fall-through plus structured logging.

After these five, the P1 layer becomes the natural next focus, dominated by gate-design fixes and shadow-soak coverage requirements.

## What This Review Did Not Cover

- The proposal's *higher-level value question* (is a microrouter worth building given Codex OAuth is free at point of use?) — flagged by lora-pipeline P1 as a loss-design issue but not as a go/no-go question. The specialist reviewers were asked to assume "build" and review the design.
- The brainstorm/design bead `.19.1` itself — the review covered downstream beads that depend on `.19.1`'s outputs; once `.19.1` runs, those decisions will refine the findings here.
- Specific test cases — concrete remedies often say "add a test for X" without spelling out the exact assertion. The implementation team is closer to the existing test patterns than this review can be from outside.
