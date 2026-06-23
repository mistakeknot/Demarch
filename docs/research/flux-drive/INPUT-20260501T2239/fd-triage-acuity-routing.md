### Findings Index
- P0 | TRIAGE-1 | "sylveste-s3z6.19.5 — Resolver Integration" | ineligible_agents enforcement layer not specified as pre-call resolver check — garbage-response failure mode could route fd-safety to haiku
- P1 | TRIAGE-2 | "sylveste-s3z6.19.5 — Resolver Integration" | Each failure mode documented but not paired with a named test case — "endpoint unreachable → fall through to B3" is assumed behavior, not verified behavior
- P1 | TRIAGE-3 | "sylveste-s3z6.19.2 — Dataset" | Class imbalance acknowledged in Risks section but training data coverage report in bead 2 does not require a per-complexity-tier breakdown
- P2 | TRIAGE-4 | "sylveste-s3z6.19.4 — Eval Harness" | Adversarial workload described as a category ("tasks designed to look easy but require deep reasoning") but not specified with concrete examples
- P2 | TRIAGE-5 | "sylveste-s3z6.19.5 — Resolver Integration" | Mode transition safety (in-flight calls during enforce→shadow/off transitions) not addressed in resolver spec
Verdict: risky

### Summary

From a hospital triage systems perspective, the most critical gap in Track B6 is the absence of a specification that the `ineligible_agents` check fires before — not after — the router is invoked. The garbage-response failure mode in bead 5 ("Router model not loaded → mode auto-degrades to shadow") handles the case where the router is unavailable, but does not handle the case where the router returns an unparseable or out-of-range tier value. If a garbage response is parsed permissively, it could produce a model selection that bypasses the safety floor for fd-safety and fd-correctness — a P0 because routing.yaml lines 33-37 encode those floors as an explicit project invariant. The secondary concern is that bead 5's three failure modes are documented requirements, not tested requirements: each needs its own named test case, not a shared "failure mode handling" test.

### Issues Found

#### TRIAGE-1. ineligible_agents enforcement layer not specified as pre-call check — garbage-response path could bypass safety floor for fd-safety/fd-correctness

**Severity**: P0
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Failure modes to handle" and `ineligible_agents:` schema)
**Finding**: Bead 5 specifies three explicit failure modes (endpoint unreachable, timeout, model not loaded) but does not specify a failure mode for "router returns a response that cannot be parsed as a valid tier" or "router returns a tier not in the expected set (haiku|sonnet|opus|local:*)". The `ineligible_agents` list (fd-safety, fd-correctness) is defined in the schema, but the spec does not state that the check fires as a hard resolver-layer gate before the HTTP call is made. If the check is implemented as post-processing of the router's response (e.g., "if response tier is haiku and agent is fd-safety, override to sonnet"), then a garbage response that fails to parse would not trigger the override — the resolver would have no tier value, and the behavior is undefined. Undefined behavior in the resolver chain for fd-safety calls is a P0 because routing.yaml:33-37 explicitly identifies "MUST NEVER run below Sonnet regardless of phase or category routing" as an invariant backed by experimental evidence (iv-jocaw experiment, iv-dthn Loop 2/4).

**Failure scenario**: `mode: enforce`. The Qwen3.5-3B-Instruct LoRA adapter serves the router. Under memory pressure (Qwen3.6-35B-A3B is co-resident at ~18GB per routing.yaml:739), the router returns a truncated JSON response (e.g., `{"tier": "hai` — valid HTTP 200 but malformed body). The resolver attempts to parse the response. The JSON parser throws. The resolver catches the exception. If the catch block falls through to B3, the safety floor is preserved. But if the catch block is not explicitly written (bead 5 only documents three failure modes, not this fourth one), the resolver may propagate the exception upward, leaving the call's model selection undefined. Depending on the Go implementation, this could result in a zero-value string being passed as the model to the subagent dispatch layer, bypassing the safety floor.

**Fix**: Add a fourth failure mode to bead 5's spec: "Router returns unparseable or out-of-range response → treat as timeout, fall through to B3." More importantly, specify that `ineligible_agents` is enforced as a PRE-CALL check at the resolver layer: "Before initiating the HTTP call to the router endpoint, check if the calling agent is in `ineligible_agents`. If yes, skip the microrouter layer entirely and proceed directly to the next resolver layer." This makes the safety floor hold regardless of any parser failure, garbage response, or latency issue. Add a dedicated test: "Mock the router to return `{"tier": "haiku"}` for a call from fd-safety. Assert that the resolver returns sonnet, not haiku, and that the router was never called."

---

#### TRIAGE-2. Each failure mode documented but not paired with a named test case — "endpoint unreachable → fall through to B3" is assumed, not verified

**Severity**: P1
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Failure modes to handle" and § "Done when")
**Finding**: Bead 5's Done When criteria include "Resolver tests cover all failure modes," which is encouraging. However, the failure mode spec lists three modes (unreachable, timeout, model not loaded) as a grouped requirement, not as three individually named test cases. In hospital triage system validation, each failure mode of the decision-support tool is a separate test scenario — "triage tool down: nurse applies ESI protocol directly" is not the same test as "triage tool returns wrong acuity: nurse overrides." Grouping them under one "failure mode handling" test allows an implementation that only tests one of the three modes to pass the Done When criteria as written.

**Failure scenario**: The Go resolver implementation is written. The test suite includes one test: `TestMicrorouterFailureModes`. The test mocks the endpoint as unreachable and verifies that B3 calibration is used. The test passes. The `timeout > timeout_ms` and `model not loaded → mode auto-degrades` failure modes are untested. In production, during the shadow soak, the model occasionally takes >100ms to respond. The timeout path fires. Because it was untested, the implementation has a subtle bug: the timeout is measured at the HTTP client level (connection timeout), not at the wall-clock level measured at the resolver entry. The router call succeeds in 95ms (within the HTTP timeout) but the total round-trip including deserialization is 115ms (over the 100ms wall-clock budget). The resolver proceeds with the router's decision rather than falling through — the shadow soak records the decision as a router decision, not a timeout fallthrough.

**Fix**: Replace the grouped "Resolver tests cover all failure modes" criterion in bead 5's Done When with three individually named tests:
- `TestMicrorouterEndpointUnreachable` — mock TCP connection refused, assert B3 fallthrough
- `TestMicrorouterTimeout` — mock HTTP call that exceeds timeout_ms wall-clock, assert fallthrough + timeout log entry
- `TestMicrorouterModelNotLoaded` — mock 503/loading response, assert mode auto-degrades to shadow and is logged

---

#### TRIAGE-3. Class imbalance acknowledged in epic Risks but bead 2's coverage report does not require per-complexity-tier breakdown

**Severity**: P1
**Section**: sylveste-s3z6.19.2 — Dataset (§ "Done when" and § "Coverage report")
**Finding**: The epic correctly identifies training data bias as a risk: "Training data is biased toward what's already been routed." Bead 2 requires a "coverage report: agents covered, phase distribution, model distribution, class imbalance numbers" as part of Done When. However, the coverage report spec does not require a per-complexity-tier breakdown — it requires model distribution (% sonnet, % haiku, etc.) but does not require showing how that distribution varies by complexity tier (C1, C2, C3). This matters because the router's job is to distinguish C1/C2 tasks (route to haiku) from C3+ tasks (route to sonnet or up). If C1/C2 tasks are 90% sonnet-labeled in the training data (because the B3 calibration found that even simple tasks needed sonnet for those agents), the router will learn to predict sonnet for C1/C2, producing systematic under-routing to haiku on the exact task complexity range the router is most valuable for.

**Failure scenario**: Bead 2 completes. The coverage report shows: model distribution = 83% sonnet, 12% haiku, 5% local. Class imbalance is documented and considered "acceptable" since it reflects the real distribution. However, when split by complexity tier: C1 tasks = 78% sonnet (many simple grep-wrapped agent calls ended up needing sonnet because of B3 calibration data), C2 tasks = 85% sonnet. The router trains on this data. During the shadow soak, ≥90% of C1/C2 calls are predicted as sonnet — this is "accurate" by the accuracy metric but provides zero rerouting for the simplest tasks. The ≥20% reroute gate is not cleared. The team investigates the router and finds the C1/C2 under-routing, but this was preventable if the coverage report had surfaced it before training.

**Fix**: Add a per-complexity-tier breakdown to the coverage report requirement in bead 2's Done When: "Per-tier model distribution table: for each complexity tier (C1–C3), show the label distribution (% haiku, % sonnet, % local). Flag if any tier shows ≥80% single-model labels — this indicates the router will learn to predict one model for that tier regardless of task features." This is a one-paragraph addition to the coverage report spec, not a new deliverable.

---

#### TRIAGE-4. Adversarial workload described as a category, not concrete examples

**Severity**: P2
**Section**: sylveste-s3z6.19.4 — Eval Harness (§ "Workloads")
**Finding**: Bead 4 specifies "Synthetic adversarial set: tasks designed to look easy but require deep reasoning (catch over-routing to haiku)" as one of three workloads. This is the most important workload for measuring under-triage rate, but it is the least specified. "Tasks designed to look easy but require deep reasoning" is a category description, not a dataset specification. Contrast this with the other two workloads: LCB v6 cached problems (named, with a specific file path) and replayed bead-history tasks (named, with a named holdout split). The adversarial workload has no named source, no target size, no construction method, and no acceptance criterion.

**Failure scenario**: Bead 4 implementation begins. The developer asks: what counts as an adversarial task? The description is "looks easy but requires deep reasoning." Without concrete examples, the developer constructs 10 tasks that look easy to them. These turn out to be tasks that were already in the training data (paraphrase variants), so the router correctly identifies them as needing deep reasoning. The adversarial workload produces a flattering accuracy result. The under-triage rate on genuine atypical-presentation tasks (short prompts that require multi-step architectural reasoning) is never measured.

**Fix**: Add 3-5 concrete adversarial task examples to bead 4, or specify a construction protocol: "Adversarial tasks are sampled from closed beads where (a) prompt_tokens < 300 (C1/C2 by complexity heuristic) but (b) the task ultimately required Sonnet or Opus to pass (per interspect verdict). Target: ≥50 such tasks from the holdout split." This is a one-paragraph addition to the workload spec.

---

#### TRIAGE-5. Mode transition safety (in-flight calls during enforce→off/shadow) not addressed in resolver spec

**Severity**: P2
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Schema additions" and § "Failure modes to handle")
**Finding**: Bead 5 specifies the resolver chain behavior in steady state (mode=off, mode=shadow, mode=enforce) and three failure modes, but does not specify what happens to in-flight routing decisions when the mode field changes (e.g., the user edits routing.yaml from enforce to off while a sprint is executing). In a hospital triage system, a mode change during operation is handled by completing in-flight triage decisions under the old mode and applying the new mode to subsequent patients. If the Go resolver reads the mode field from routing.yaml at request time (rather than caching it at startup), a mode change mid-sprint could cause some calls to use enforce semantics and others to use off semantics within the same sprint, creating an incoherent routing distribution that the shadow log cannot explain.

**Failure scenario**: Mode is `enforce`. A sprint is executing. The user observes an unexpected haiku routing decision and immediately edits routing.yaml to set `mode: off`. The Go resolver, which reads routing.yaml on every call (if it uses a hot-reload pattern like other Clavain configs), switches to `mode: off` mid-sprint. The shadow log shows calls before the switch attributed to enforce-mode routing and calls after attributed to off-mode routing — but since the mode is now off, the shadow log stops being written. The sprint ends with a mixed log that shows a reroute rate from the pre-switch enforce period, which the promotion gate may treat as a valid enforce-mode measurement.

**Fix**: Add a mode-transition behavior spec to bead 5: "Mode changes take effect at sprint boundaries, not at request time. The resolver reads mode once per sprint execution context and caches it for the duration. If a mid-sprint mode change is required (emergency rollback), the documented escape hatch (set mode=off in routing.yaml, identical to B3/B4 pattern) requires restarting the Clavain executor to take effect." This makes the transition semantics explicit and prevents incoherent mid-sprint routing mixes.

---

### Improvements

1. **Named test for each ineligible-agent scenario**: Beyond the pre-call check fix in TRIAGE-1, add a test for the "router returns a valid tier but agent is ineligible" path — verify the ineligible check fires even when the router call succeeds, not just when it fails.

2. **Hard-negative mining acceptance criterion**: Bead 2 mentions "hard-negative mining" as an augmentation strategy but does not specify what fraction of the training set should be hard negatives. Recommend adding a minimum target: "At least 15% of training examples should be hard negatives (tasks where the model used passed, but a cheaper model would also have passed)." Without a minimum, hard-negative mining may be implemented nominally but not at a scale that materially affects the class balance.

3. **Retrospective review log spec**: For post-incident analysis, add a requirement to bead 5 that when a task fails in enforce mode, the failure is logged with `(call_id, router_tier_predicted, router_confidence, actual_tier_used, task_result, agent_name, phase)`. This is distinct from the shadow log (which records all calls) and enables targeted retrospective review of failures.

--- VERDICT ---
STATUS: fail
FILES: 0
FINDINGS: 5 (P0: 1, P1: 2, P2: 2)
SUMMARY: One P0 gap in ineligible_agents enforcement creates a path where a garbage router response could bypass the safety floor for fd-safety/fd-correctness (routing.yaml:33-37 invariant). Two P1 gaps in failure-mode test coverage and training data tier breakdown require resolution before the shadow soak produces trustworthy evidence.
---
<!-- flux-drive:complete -->
