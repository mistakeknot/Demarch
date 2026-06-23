### Findings Index
- P1 | SS7-1 | "sylveste-s3z6.19.5 — Resolver Integration" | Resolver chain terminal condition not proven reachable — no hardcoded last-resort default below phases[phase].model when both B3 and B1 fail
- P1 | SS7-2 | "sylveste-s3z6.19.5 — Resolver Integration" | Route flap from intermittent router endpoint not addressed — 100ms timeout window enables incoherent routing distribution within a single sprint
- P1 | SS7-3 | "sylveste-s3z6.19.5 — Resolver Integration" | Simultaneous failure mode combinations (timeout + calibration absent) not specified — only single failures tested in isolation
- P2 | SS7-4 | "sylveste-s3z6.19.5 — Resolver Integration" | Per-layer fallthrough reason not logged — final resolution log cannot distinguish B3-calibration-hit from microrouter-timeout-then-B3
- P2 | SS7-5 | "sylveste-s3z6.19.5 — Resolver Integration" | 100ms timeout_ms budget specification is ambiguous — does not state whether this is wall-clock at the resolver or HTTP client timeout at the model inference layer
Verdict: needs-changes

### Summary

From a telecommunications cascade routing perspective, the Track B6 resolver chain is well-structured in the steady-state case — 8 layers from kernel overrides to defaults.model mirrors the trunk group priority tables in SS7 routing. However, the specification has three gaps that would fail a telco-grade routing review: the terminal condition (what happens when B3 calibration is absent AND a phase key is missing from B1) is not proven reachable, the route-flap scenario (router endpoint intermittently available within 100ms windows) is not addressed and would produce incoherent sprint-level routing distributions, and simultaneous failure combinations are only tested in isolation. The latency budget (100ms) is also ambiguous about measurement scope — if this is measured at the router model layer rather than the resolver wall-clock, the actual budget available for model inference is systematically lower than 100ms.

### Issues Found

#### SS7-1. Resolver chain terminal condition not proven reachable — no hardcoded default below phases[phase].model

**Severity**: P1
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Resolver chain change")
**Finding**: The proposed resolver chain has 8 layers ending at `defaults.model` (the B1 static default). However, the chain traversal relies on looking up `phases[phase].model` as the penultimate fallback and `defaults.model` as the terminal fallback. Both of these are YAML key lookups. If routing.yaml is malformed or a new phase is added to the sprint workflow that does not have a `phases[phase].model` entry, the lookup returns nil/empty. If `defaults.model` is also missing (e.g., routing.yaml is partially written during an edit), the terminal fallback is also absent. The chain exhausts all 8 layers without producing a model selection. In SS7 routing, this is an end-of-chain condition — all trunk groups are exhausted without a completed call setup — and it causes the call to fail rather than route. In the resolver context, a nil model selection would either block the subagent call or produce an empty model string passed to the Agent tool dispatch.

**Failure scenario**: The team adds a new sprint phase (`verified`) to the routing.yaml phases section during sprint work. They add a `phases.verified.categories` section but forget to add `phases.verified.model`. A subagent executes in the `verified` phase. The resolver chain reaches `phases[phase].model` → lookup for `phases.verified.model` → nil. The chain proceeds to `defaults.categories[cat]`. The subagent is category `workflow`. `defaults.categories.workflow` is not defined (routing.yaml only defines research/review/synthesis/explore/general-purpose in defaults.categories). The chain proceeds to `defaults.model` → `sonnet` → this succeeds. BUT: if in a future edit someone removes or renames `defaults.model` while testing a config change, the terminal is no longer reachable and the resolver has no fallback.

**Fix**: Add a hardcoded terminal below `defaults.model` in the resolver implementation: `HARDCODED_LAST_RESORT = "sonnet"`. This constant is not in routing.yaml — it is a compile-time constant in the Go resolver that fires if and only if all YAML-based lookups fail. Document it in bead 5: "The resolver MUST have a compile-time constant last-resort model value ('sonnet') that fires if all YAML lookups return nil. This is the SS7 operator-intervention equivalent — the call never fails entirely." Add a unit test: `TestResolverChainExhaustionFallback` — remove all YAML config and verify the resolver returns 'sonnet'.

---

#### SS7-2. Route flap from intermittent router endpoint not addressed — 100ms timeout creates incoherent routing distributions

**Severity**: P1
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Schema additions": `timeout_ms: 100`)
**Finding**: The 100ms timeout is short enough that a router endpoint with high p99 latency (e.g., first request after a cold-start of the Qwen3.5-3B adapter warms up caches) could alternate between responding within 100ms and exceeding 100ms within the same sprint. This is the route-flap condition in SS7 routing: a trunk group that alternates between available and unavailable within the routing decision window creates a worse outcome than a clean fallback to a secondary trunk group, because the routing decision for the same logical call type is inconsistent. In the microrouter context: within a single sprint, some `fd-architecture` calls would get microrouted (endpoint responded in 85ms) and others would fall through to B3 (endpoint responded in 115ms on the next call). The shadow log would show a reroute rate that reflects endpoint latency variance, not router quality.

**Failure scenario**: The shadow soak sprint begins. The interfer process has been running for 48 hours but the Qwen3.5-3B LoRA adapter is loaded in MLX. On cold GPU pages (after another model temporarily displaced it from the GPU), the first inference request takes 145ms. The resolver sees timeout_ms exceeded, logs a fallthrough. The GPU pages are now warm. The next 40 requests complete in 65ms each. The resolver routes them via the microrouter. The shadow log shows 40/41 calls to the microrouter (98% "availability"). But the first call — which timed out — may have been statistically typical of the router's startup latency. The soak's reroute rate of 98% is inflated relative to what enforce mode will produce in production, where cold-start timeouts will occur after every interfer restart.

**Fix**: Add two requirements to bead 5: (a) "The router endpoint must implement a warmup signal: the resolver should not start routing calls to the endpoint until it has responded to at least one warmup probe within the last N seconds. If the endpoint is cold, fall through to B3 without incrementing the timeout counter." (b) "The shadow soak report must include a latency percentile breakdown of router endpoint response times (p50/p95/p99) separately from routing decision outcomes — this distinguishes endpoint latency variance from router quality." Add a test: `TestMicrorouterColdStartFlap` — simulate the endpoint alternating between 85ms and 115ms responses and verify the shadow log reason codes match the expected mix.

---

#### SS7-3. Simultaneous failure mode combinations not specified — only single failures tested in isolation

**Severity**: P1
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Failure modes to handle")
**Finding**: Bead 5 specifies three failure modes in isolation: (1) endpoint unreachable → fallthrough to B3, (2) timeout → fallthrough + log incident, (3) model not loaded → auto-degrade to shadow. The spec does not address combination failures: (a) timeout AND calibration file absent (B3 is also unavailable), (b) endpoint unreachable AND model not loaded (two concurrent failures), (c) garbage response AND mode=shadow (shadow log write fails). In SS7 routing, simultaneous trunk group failure and Signal Transfer Point (STP) database unavailability are the scenarios that cause network-level outages — they were never tested together because each was tested in isolation. The resolver chain for combination (a) is the most dangerous: if the microrouter times out AND routing-calibration.json is absent, the resolver chain must reach B1 phases[phase].model. If this lookup also fails (as in SS7-1), the chain has no terminal.

**Failure scenario**: `mode: enforce`. interfer is running but the Qwen3.5-3B adapter takes 115ms to respond (timeout). The resolver falls through to B3. B3 attempts to read `.clavain/interspect/routing-calibration.json`. The file was deleted 10 minutes ago during a manual rollback attempt. B3 returns nil. The resolver continues to `phases[executing].model = sonnet`. This succeeds — the fallback chain works. BUT: this path was never tested in combination. The Go implementation of the "B3 returns nil → continue to B1" path may have a bug (e.g., a nil pointer dereference on the calibration lookup return value) that only manifests when B3 and the microrouter both fail simultaneously.

**Fix**: Add two combination-failure test cases to bead 5's Done When criteria:
- `TestMicrorouterTimeoutWithStaleB3` — mock: router times out, calibration file absent. Assert: resolver reaches B1 phases[phase].model and returns a valid model.
- `TestMicrorouterEndpointUnreachableWithMissingPhase` — mock: endpoint unreachable, phases[phase].model key absent. Assert: resolver reaches defaults.model and returns a valid model.

These two tests cover the failure-combination cases most likely to produce nil-pointer bugs in the Go implementation.

---

#### SS7-4. Per-layer fallthrough reason not logged — shadow log cannot distinguish B3-calibration-hit from microrouter-timeout-then-B3

**Severity**: P2
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "shadow_log" schema)
**Finding**: The shadow log schema in bead 5 records routing decisions to `.clavain/interspect/microrouter-shadow.jsonl` but does not specify whether the log entry records only the final resolution or also which layers were traversed. In SS7 signaling, per-hop routing records (called CDRs — Call Detail Records) capture each signaling point traversed, not just the final route taken. Without per-layer logging, a call that went microrouter → timed out → B3 → returned sonnet and a call that went microrouter → returned sonnet directly appear identical in the shadow log (both show final model = sonnet). Diagnosing why the reroute rate is lower than expected requires reading the log entry count of "decided" vs "timed-out" entries — which requires the reason field from BESTEXEC-1, plus knowing which resolver layer produced the final resolution.

**Failure scenario**: During the shadow soak, the reroute rate is 12% (lower than the ≥20% gate requires). Investigation begins. The shadow log shows all entries with their final model. Without per-layer logging, the team cannot determine how many of the non-rerouted calls were: (a) router decided sonnet (router is correctly conservative), (b) router timed out → B3 decided sonnet (router was slow, not wrong), (c) router returned haiku but agent was ineligible (filtered). Each of these requires a different response. Without the per-layer information, the team spends a sprint investigating whether the router is making wrong decisions when the real issue was timeout-induced fallthroughs.

**Fix**: Extend the shadow log schema to include a `resolver_path` array field: `[{"layer": "microrouter", "result": "haiku", "reason": "decided", "latency_ms": 67}, {"layer": "b3-calibration", "result": "skipped", "reason": "microrouter-decided"}, ...]`. This is a minor schema addition that produces dramatically more diagnostic value. The per-layer entries need only be present when the path deviates from the happy path (microrouter decided → done). Log the full path only when a fallthrough occurred.

---

#### SS7-5. 100ms timeout_ms budget specification is ambiguous — measurement point not specified

**Severity**: P2
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Schema additions": `timeout_ms: 100`)
**Finding**: The `timeout_ms: 100` field in the proposed schema does not specify where this timeout is measured. It could mean: (a) wall-clock time measured at the resolver entry point (most conservative), (b) HTTP client read timeout (excludes connection establishment), or (c) model inference time only (excludes HTTP overhead). In SS7 routing, timer T7 (addressing completion timer) is specified as wall-clock time from the SETUP message being sent to the CONNECT being received — not just the processing time at the terminating exchange. The localhost:8421 endpoint involves: DNS (trivial for localhost), TCP connection establishment (~1ms on first connection if not pooled), HTTP request serialization, model inference, HTTP response deserialization. If only the model inference time is budgeted at 100ms, the actual wall-clock budget consumed by the router call can be 120-140ms (adding HTTP overhead), which is invisible to the timeout check.

**Failure scenario**: The router model achieves p95 inference latency of 88ms (meets the 100ms budget at the model layer). The resolver sees wall-clock elapsed time of 112ms when the response arrives (24ms of HTTP overhead: connection + serialization + deserialization). If `timeout_ms: 100` is enforced at the HTTP client read-timeout level rather than the resolver wall-clock level, the call is not logged as a timeout but the total resolver overhead exceeds the documented budget. Over a sprint with 200 router-eligible calls, the total latency overhead from the microrouter is 200 × 112ms = 22.4 seconds of additional latency, where the spec's intent was ≤200 × 100ms = 20 seconds.

**Fix**: Add a spec clarification to bead 5: "`timeout_ms` is wall-clock time measured at the resolver entry point (before connection establishment) to response-parsed (after deserialization). It is NOT the HTTP client read timeout." Recommend setting `timeout_ms: 80` in the implementation to leave 20ms of headroom for HTTP overhead, while keeping the spec's stated budget at 100ms. Add a test that measures the wall-clock time from resolver entry to response parsed and verifies it is within `timeout_ms`.

---

### Improvements

1. **Warmup probe pattern for endpoint health**: Add an optional `warmup_probe_interval_s` field to the schema (default: 30s). The resolver pings the endpoint before routing a call when the last successful response was >N seconds ago. This eliminates the cold-start flap condition by detecting cold endpoints before calls are routed to them.

2. **Resolver chain reachability proof in AGENTS.md**: When bead 5 is closed, add a section to `os/Clavain/AGENTS.md` showing the resolver chain as a state machine with all 8 layers and their skip conditions. Include the hardcoded last-resort constant. This produces an always-current reference for debugging and onboarding, mirroring how telco operations teams document their routing tables.

3. **Concurrency cap for router endpoint**: The bead 5 spec should specify a maximum concurrent call count to the router endpoint (e.g., `max_concurrent_requests: 5`). During parallel multi-agent dispatches (common in flux-drive reviews with 4+ agents launching simultaneously), multiple subagents could call the router concurrently. Without a concurrency cap, the router's p95 latency under concurrent load may be higher than the measured p95 under serial load, causing the router to time out more frequently during multi-agent sprints than single-agent sprints.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 3, P2: 2)
SUMMARY: Three P1 gaps in cascade chain terminal condition, route flap handling, and simultaneous failure mode combinations present operational risks during the shadow soak and enforce periods. Route flap is the most likely to manifest in production: the 100ms timeout window is tight enough that normal endpoint latency variance will produce incoherent routing distributions that invalidate the soak metrics.
---
<!-- flux-drive:complete -->
