### Findings Index
- P0 | YI-1 | "Privacy-Routing Extension" | Privacy inner-quench shares endpoint liveness check with outer circuit — privacy=sensitive tasks can fall through to cloud when router endpoint is down
- P1 | YI-2 | "Eval Harness" | Shadow-to-enforce promotion is metric-threshold automated with no operator review gate — a router passing aggregate metrics but failing on high-stakes agents auto-promotes
- P1 | YI-3 | "Resolver Integration" | Garbage-response failure mode is unnamed and unspecified — resolver does not enumerate behavior when microrouter returns malformed/out-of-vocabulary output
- P2 | YI-4 | "Resolver Integration" | Rollback procedure is incomplete: deleting calibration file does not stop interfer endpoint from serving stale weights
- P2 | YI-5 | "Resolver Integration" | Clay-coating asymmetry gap: ineligible_agents list in bead .19.5 is hardcoded; no dynamic mechanism to honor per-agent safety floors defined elsewhere in routing.yaml
- IMP | YI-I1 | "Eval Harness" | Add required operator review checklist to shadow → enforce promotion; specify smith's-eye criteria (what to look for in the shadow log, not just metric thresholds)
- IMP | YI-I2 | "Resolver Integration" | Define full-stack rollback procedure: calibration file deletion + interfer server stop + resolver mode reset, as a single documented runbook step
Verdict: risky

### Summary
The yaki-ire lens reveals that the Track B6 proposal has a critical inner-quench failure: the privacy-routing extension (bead .19.6) fires the microrouter even when global mode=off, but shares the same endpoint liveness check with the outer circuit. If the interfer-served router at localhost:8421 is down, a privacy=sensitive task will fall through to whatever default the resolver produces — which may not respect the local-only constraint. This is the highest-severity finding in this agent's domain. Additionally, the shadow-to-enforce promotion gate is fully automated by metric thresholds (≥20% reroute rate, no pass@1 regression) with no operator review step — a router that satisfies aggregate metrics while routing badly on a small set of high-stakes agents (e.g., architectural C5 tasks) will auto-promote without a human reading the temper line. The rollback procedure ("delete calibration file pattern") is incomplete: the interfer endpoint continues serving the adapter weights and the resolver will continue consulting it.

### Issues Found

YI-1. P0: Privacy inner-quench shares endpoint liveness check with outer circuit.

Bead .19.6 specifies: "Add `microrouter.privacy_override: always` flag — when task carries `privacy=internal|sensitive`, microrouter runs regardless of global mode." Bead .19.5 specifies the resolver failure modes: "Router endpoint unreachable → fall through to B3 (don't block resolution)." 

The privacy override fires the router even when global mode=off. But the failure mode for an unreachable endpoint is defined as "fall through to B3" — B3 calibration does NOT enforce local-only. The privacy_routing block in routing.yaml (lines 767-769) mandates `internal: "local-only"` and `sensitive: "local-only-no-log"`, but this is enforced by the privacy_routing section, not by the microrouter fallback. If the endpoint is down and the microrouter falls through to B3, the B3 calibration data may recommend cloud for the same task that should stay local.

Concrete failure scenario: User runs a sprint with `bd label privacy=sensitive` on a bead involving internal architecture docs. The interfer server on localhost:8421 is down (crashed, or not yet started). The resolver sees `privacy=sensitive`, attempts the microrouter per the privacy_override flag, gets a connection refused, and falls through to B3 calibration. B3 recommends "cloud: deep-clavain" (the model that was historically most successful for this agent type). The sensitive task is sent to GPT-5.5 xhigh fast via codex CLI. The privacy routing constraint is silently violated. The audit log shows "B3: cloud" with no indication that the privacy override was attempted and failed.

Fix: In bead .19.5 resolver failure mode specification, add: "Router endpoint unreachable AND task.privacy=sensitive → fail-closed (do NOT route to cloud). Either route to a local fallback model directly or return an error that blocks the task until the endpoint is restored. The privacy=sensitive circuit must have a distinct 'fail-local' behavior that does not delegate to B3." Add a `privacy_fallback_model` field to the microrouter schema:
```yaml
microrouter:
  privacy_fallback_model: "local:qwen3.6-35b-a3b-4bit"  # used when endpoint down AND privacy=sensitive
```

YI-2. P1: Shadow-to-enforce promotion is automated by metric thresholds without operator review.

Bead .19.4 shadow-to-enforce gate: "≥ 1 sprint of shadow-mode soak, no pass@1 regression vs. B3 baseline, ≥ 20% reroute rate." These are all measurable metrics that could auto-fire a promotion script. There is no requirement for an operator to read the shadow log before promotion. The first time this gate is reached, a router that satisfies aggregate metrics while routing badly on C4/C5 architectural tasks (e.g., always choosing sonnet when opus is needed) will auto-promote.

In yaki-ire, the tosho must personally read the steel's color (hamon line) before stamping mei — elapsed time in the quench is insufficient evidence. The gate in bead .19.4 is entirely stopwatch-based.

Concrete failure scenario: Shadow-mode soak completes. Automated check runs: sprint completed ✓, pass@1 no regression ✓, reroute rate 23% ✓. Router auto-promotes to enforce. In the first enforce sprint, 15 C5 architectural tasks that should have routed to Opus route to Sonnet (router learned from a training set where C5 tasks were rare). Three beads fail quality gates. Rollback takes 2 hours: delete calibration file, verify B3 re-activates, re-run failed beads.

Fix: In bead .19.4, add to the shadow-to-enforce gate: "AND operator has reviewed shadow log and confirmed: (a) no systematic bias toward any single tier (routing distribution histogram shows no tier receiving >80% of decisions), (b) per-agent sample of decisions reviewed for at least fd-safety, fd-correctness, fd-architecture at C4/C5, (c) promotion sign-off commit message documents review." This is the smith's-eye gate.

YI-3. P1: Garbage-response failure mode is unnamed and unspecified.

Bead .19.5 enumerates three failure modes: endpoint unreachable, router timeout, router model not loaded. It does NOT enumerate: router returns a response that is not a valid tier name (e.g., "I recommend using a model that balances cost and quality" or an empty string or a tier name that doesn't exist in routing.yaml). The resolver tests (bead .19.5 "Done when") include "garbage response" as a test case title but do not specify the expected behavior.

Concrete failure scenario: During a sprint, the router returns "local:qwen3.5-9b-4bit" for a C3 task (a valid local model name but one that bead .19.5's schema maps to tier 1, below the appropriate level). The resolver does not recognize it as a garbage response — it's a valid tier name — and applies it. The task fails. Alternatively: the router returns an empty string. The resolver crashes in the Go resolver code (TBD path) because the response parser didn't handle empty string. Resolution depends on how the Go resolver handles nil/empty tier strings.

Fix: Add a fourth named failure mode in bead .19.5: "Router returns unrecognized tier name OR confidence below `min_confidence_threshold` → fall through to B3, log as `decision_type: garbage_response`." Add to the test list: "Test: router returns empty string → falls through, logged." "Test: router returns valid-looking but non-existent tier → falls through, logged." 

YI-4. P2: Rollback procedure is incomplete — interfer endpoint continues serving stale weights.

Bead .19.5 "Failure modes to handle" and the epic's "Risks" section both reference "delete calibration file pattern, same as B3/B4" as the escape hatch. For B3 (evidence-based calibration), deleting `.clavain/interspect/routing-calibration.json` disables calibration. For the microrouter, the "calibration file" would presumably be the adapter checkpoint path. But the interfer server at `http://localhost:8421/route` is a separate process (the B5 local_models endpoint, routing.yaml line 729) that loads the adapter weights independently. Deleting the checkpoint file does not stop the interfer server from serving the already-loaded weights in memory. The resolver continues consulting the endpoint (it's reachable, so no fallthrough), and the router continues making decisions from stale weights.

YI-5. P2: Clay-coating asymmetry gap — ineligible_agents is a static list that may miss dynamic safety floors.

Bead .19.5 schema hardcodes `ineligible_agents: [fd-safety, fd-correctness]`. The routing.yaml safety floors (lines 33-37) define four overrides: `interflux:review:fd-safety: sonnet`, `interflux:review:fd-correctness: sonnet`, `interflux:fd-safety: sonnet`, `interflux:fd-correctness: sonnet`. The ineligible list uses short names but the overrides block uses full subagent_type names. If an agent is referenced by its full name in a routing call but the ineligible check uses short name comparison, the check may silently miss the ineligible classification. Additionally, any new safety-critical agents added to the overrides block in the future must be manually added to the microrouter ineligible list.

### Peer Findings Noted

From fd-gongfu-cha-cascade-discernment (blocking): Circular calibration — GPT-5.5/Opus is both augmentation judge and calibrated baseline anchor. This is complementary to YI-2: the auto-promotion gate is not only stopwatch-based, it's evaluating against a circular calibrated baseline. Both findings reinforce that the shadow-to-enforce transition needs an operator gate with explicit baseline provenance review.

From fd-glacial-sediment-cascade-sorting (blocking): Audit-trail unconformity — no-op short-circuit erases microrouter activity. This directly affects YI-2: without a complete shadow log, an operator review gate cannot be informed. The shadow log must log all decisions (including pass-through) before any operator review step is meaningful.

### Improvements

YI-I1. Operator review checklist for shadow → enforce — add a required sign-off step with a specific checklist: routing distribution histogram, per-agent sample at C4/C5, confirmation of no systematic tier collapse. Document as a required commit message in the promotion procedure.

YI-I2. Full-stack rollback runbook — replace "delete calibration file pattern" with a documented 3-step sequence: (1) delete/rename the adapter checkpoint, (2) send SIGTERM to the interfer server (or call a /reload endpoint that drops the adapter), (3) verify resolver falls through to B3 by confirming next shadow log entry shows `decision_type: skipped`. Add this to bead .19.5 "Done when."

YI-I3. Privacy fallback model — add `privacy_fallback_model` to microrouter schema spec in bead .19.5, with explicit fail-closed behavior when endpoint is unreachable for privacy=sensitive tasks.

<!-- flux-drive:complete -->
