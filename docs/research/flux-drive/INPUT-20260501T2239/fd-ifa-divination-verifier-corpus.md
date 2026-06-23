### Findings Index
- P0 | IF-1 | "Confidence-Cascade Verifier" | Single-diviner double-cast: verifier (bead .19.7) would share corpus and judge with microrouter, defeating independent confirmation
- P1 | IF-2 | "Build Labeled Dataset" | Hollow odu: ≥5K total examples does not guarantee per-(agent, phase, complexity-tier) cell coverage; empty cells will produce confident hallucinated verdicts
- P1 | IF-3 | "Resolver Integration" | No iyere-bowl startup self-test: router activates without verifying it can correctly handle canonical probe cases
- P2 | IF-4 | "Eval Harness" | Itefa initiation gate tests aggregate accuracy; rare-cell (obscure odu) competence is not a gate criterion
- P2 | IF-5 | "Resolver Integration" | Shadow log (microrouter-shadow.jsonl) does not specify verse-provenance fields: no way to trace a decision back to its training examples
- IMP | IF-I1 | "Confidence-Cascade Verifier" | If verifier is pursued (bead .19.7), require disjoint corpus from microrouter: different time-slice, different judge family, different features
- IMP | IF-I2 | "Build Labeled Dataset" | Add per-cell coverage report as a required "Done when" artifact; require empty-cell escalation logic in resolver
Verdict: risky

### Summary
The Yoruba Ifá divination framework exposes two critical design flaws. First, if bead .19.7 (confidence-cascade verifier) is implemented and trained using the same labeled corpus (bead .19.2) and the same judge (GPT-5.5/Opus from bead .19.3), it cannot function as an independent confirming cast — two models trained on the same data by the same teacher will fail in correlated ways, defeating the purpose of a verifier. Second, the ≥5K total labeled examples target in bead .19.2 does not prevent hollow odu: if even one (agent, phase, complexity-tier) cell in the joint distribution has too few examples, the router will confidently invent a verdict for those cases rather than declining to answer. The resolver has no empty-cell detection logic that would escalate such cases to safe defaults. The proposal also lacks a startup self-test (iyere-bowl equivalent) to verify the router is reading the system correctly before engaging on live traffic.

### Issues Found

IF-1. P0: Single-diviner double-cast — verifier shares corpus and judge with microrouter.

Bead .19.7 proposes a "reward-model-style scorer: small (1B–3B) model trained on `(task, draft, was_passed)` triples." The `was_passed` signal would come from the same interspect/bead-history corpus as the microrouter's training data (bead .19.2), and missing labels would again be filled by GPT-5.5/Opus (bead .19.3's judge pattern). The bead explicitly cross-references bead .19.3: "mirrors beads 1-4 of this epic, scoped down."

In Ifá practice, the confirmatory cast must be performed by a second babalawo who has not heard the first divination — independent judgment is the entire point. A verifier trained on the same corpus by the same judge will fail in correlated ways with the microrouter: if the router makes a bad decision on a class of tasks, the verifier trained to recognize pass/fail on the same class will have the same blind spots.

Concrete failure scenario: Router is in enforce mode. A class of C3 architectural tasks gets routed to local Qwen3.6-35B. The verifier, trained on the same task distribution, sees these as "typically passing" (because they often did in training). Both router and verifier agree: "local is fine, output passes." The actual quality degrades over a sprint with zero signals firing. The correlated failure is invisible until a human reviews the closed beads.

Fix: If bead .19.7 is pursued, require in its "Done when" criteria: (a) verifier training corpus is time-disjoint from bead .19.2 (e.g., most recent 3 weeks only, vs. bead .19.2's general historical corpus), (b) augmentation judge is a different provider than GPT-5.5 (e.g., use Gemini or a local Qwen3.6-35B consensus), (c) verifier features must NOT include the routing decision itself (avoids circularity with microrouter).

IF-2. P1: Hollow odu — ≥5K total examples without per-cell coverage requirement.

Bead .19.2 "Done when": "≥ 5K labeled examples across train/val/test." The feature set (bead .19.1) is `(task_text, agent_name, phase, complexity_tier, ...)`. If the joint distribution of (agent_name × phase × complexity_tier) has, say, 847 distinct cells (rough estimate: ~100 active agents × 8 phases × ~5 tiers, though many are sparse), 5K examples averages fewer than 6 per cell. Cells corresponding to rare agents at high complexity (e.g., `fd-adversarial-testing-lens-safety` at C5 in `shipping` phase) may have 0 or 1 examples.

The resolver has no empty-cell detection. There is no logic equivalent to "this odu has no verse — refer the case." The router will extrapolate from neighboring cells and confidently produce a verdict that may be completely unreliable.

Concrete failure scenario: Router sees an `fd-correctness` agent call at complexity tier C4 in the `shipping` phase (rare combination). This cell has 2 training examples. Router produces a "haiku is fine" verdict with high model confidence. Task fails, correctness is missed. No safety floor fires because the safety_floor logic in routing.yaml (lines 33-37) specifies Sonnet as minimum — and haiku is below that floor. Wait: the `ineligible_agents` list in bead .19.5 includes `fd-correctness` — so this specific scenario is caught. But any agent NOT in the ineligible list with a sparse cell is at risk.

Fix: In bead .19.2 "Done when" criteria, add: "Coverage report shows no (agent, complexity_tier) cell with fewer than N examples (propose N=20 in design bead .19.1); resolver must implement empty-cell escalation to safe default (B3 calibration result) when router confidence is below a minimum threshold on sparse cells."

IF-3. P1: No iyere-bowl startup self-test.

The resolver integration (bead .19.5) specifies failure modes: endpoint unreachable → fall through, timeout → fall through, model not loaded → degrade to shadow. None of these is a startup self-test. The router could load its weights correctly, pass all health checks, and silently produce garbage verdicts on all inputs due to a corrupted adapter checkpoint or a mismatch between the training feature schema and the inference feature schema (e.g., the `prior_calibration_score` feature that bead .19.1 mentions as an input but is not always available).

In Ifá, before any divination session, the babalawo performs a sanity cast on a known question to verify the system is reading correctly that day. The microrouter has no equivalent.

Concrete failure scenario: A LoRA adapter checkpoint saved from bead .19.3 is loaded but was saved at a mid-epoch checkpoint (not the final checkpoint) due to a storage error. The router loads without error (endpoint responds, model_loaded=true). Every inference returns a subtly wrong distribution — systematically routing C3 tasks to C1-tier models. The silent degradation continues for the entire shadow-soak sprint before being noticed via the ≥20% reroute rate metric (which fires correctly, just on wrong routes).

Fix: In bead .19.5, add a `startup_probe` block to the microrouter config schema:
```yaml
startup_probe:
  enabled: true
  probes:
    - task: "write a unit test for a sorting function"
      expected_tier: "haiku"  # simple, C1
    - task: "redesign the authentication system for multi-tenant isolation"
      expected_tier: "opus"   # architectural, C4/C5
  on_probe_failure: "degrade_to_shadow"
```
Run probes on first request after load. If any probe fails, degrade to shadow and log the failure.

IF-4. P2: Itefa initiation gate tests aggregate accuracy; obscure odu are not a gate.

Bead .19.4 shadow-to-enforce gate: "no pass@1 regression vs. B3 baseline, ≥20% reroute rate." A router that achieves these metrics by correctly routing the 70% of common cases (Sonnet at C3, Haiku at C1 for simple grep agents) while completely mishandling the 30% of rare cases (unfamiliar agents, novel phases, boundary-tier tasks) will pass this gate. The rare cells are the obscure odu — the cases where a babalawo's depth of corpus is most tested.

IF-5. P2: Shadow log lacks verse-provenance fields.

Bead .19.5 specifies `shadow_log: ".clavain/interspect/microrouter-shadow.jsonl"` but does not specify the schema of log entries. In particular, there is no requirement that each log entry include:
- Which training examples most influenced the routing decision (nearest-neighbor IDs or representative features)
- Which router model version produced the decision (adapter checkpoint hash)
- The raw logit distribution over tiers (not just the argmax)

Without these, a logged routing decision cannot be traced back to its "verse" — the training example that taught it. When a misroute is found in the shadow log, the only recourse is re-running inference with debugging enabled.

### Improvements

IF-I1. Verifier independence — if bead .19.7 is pursued, the corpus, judge, and features must be disjoint from bead .19.2/19.3. Specify these constraints in bead .19.7's "Approach" section before any implementation begins.

IF-I2. Per-cell coverage gate — add a required coverage report artifact to bead .19.2's "Done when" list, specifying minimum examples per (agent, complexity_tier) cell and a resolver fallback for empty cells.

IF-I3. Shadow-log verse provenance — add schema specification to bead .19.5 requiring: `adapter_checkpoint_hash`, `top_k_training_example_ids`, `raw_logit_distribution` in every shadow log entry.

<!-- flux-drive:complete -->
