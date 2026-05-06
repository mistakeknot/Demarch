### Findings Index
- P1 | QT-01 | "Axis 2: Token Efficiency" | /flux-review fans out 16 agents without concurrency cap — M/M/∞ queue with unbounded server contention at Anthropic API tier
- P2 | QT-02 | "Axis 2: Token Efficiency" | Synthesis blocks on slowest agent (max-latency policy) — head-of-line blocking; Little's Law predicts cascading slowdown above 70% utilization
- P2 | QT-03 | "Axis 1: Usability" | MCP server disconnects cause hook chains to queue indefinitely — no backpressure or circuit-breaker mechanism
- P2 | QT-04 | "Axis 1: Usability" | Hook chain per turn is an unbounded serial queue — hooks execute sequentially with no priority inversion protection for urgent signals
- P3 | QT-05 | "Axis 2: Token Efficiency" | Activity loops (/loop, /sprint ticks) have no arrival-rate control — when tick interval is short, tokens-in-flight (Little's Law L=λW) spike
Verdict: needs-changes

---

### Summary

Sylveste's parallel dispatch architecture (16-agent /flux-review, serial MCP tool calls, hook chains per turn) exhibits classic queueing pathologies. The M/M/k model applies directly: service rate μ (Anthropic API throughput per agent), arrival rate λ (agent requests/second during fan-out), k (API concurrency slots). At 16 agents dispatched simultaneously with a shared API quota, utilization ρ = λ/kμ easily exceeds the safe 70% threshold where wait-time blows up non-linearly. Head-of-line blocking at synthesis (waiting for the slowest agent) turns the 50th-percentile latency into the 99th-percentile experience. MCP disconnect events inject unbounded service times into serial hook queues, stalling the entire chain. These are well-characterized queueing problems with known solutions: concurrency caps (M/M/k admission control), synthesis timeouts with partial results, and circuit breakers for disconnected MCP servers.

---

### Issues Found

**QT-01. P1: /flux-review fans out 16 agents without concurrency cap — M/M/∞ contention**

- **Axis**: token-efficiency
- **Mechanism**: M/M/k queue with k server slots. If k = Anthropic API concurrent-session limit (typically 5-10 for standard accounts), dispatching 16 agents simultaneously creates an admission queue. By Erlang C formula, P(queue) → 1 as ρ → 1. All 16 contend for the same API, causing rate-limit 429 errors → exponential backoff retries → double-pay on retried tokens.
- **Current state**: `phases/launch.md` dispatches Stage 1 agents "in parallel" via Task tool with `run_in_background: true`. No concurrency limiter governs the fan-out. The `flux-watch.sh` monitor observes completions but does not throttle dispatch. With 16 agents × ~20,000 tok average = 320,000 tok in-flight simultaneously. Anthropic rate limits (tokens/minute) apply across all concurrent requests from the same API key.
- **Concrete failure**: /flux-review with 16 agents on a large diff: 6 agents complete, 10 hit rate-limit retry. Retry agents double-pay input tokens (cached input is re-sent). Some agents hit 3-retry limit and fail → partial synthesis. Wall-clock time: 2× expected. Net token cost: ~30% higher than serial dispatch would have been.
- **Little's Law estimate**: L = λW. If λ = 16 agents dispatched simultaneously, W = 3 min average service time → L = 48 agent-minutes of tokens in-flight. Reducing to k=6 concurrent: L = 6×3 = 18 agent-minutes in-flight, same total work, 2.7× lower peak contention.
- **Proposal**: Add a concurrency gate to `phases/launch.md` Stage 1 dispatch:
  ```bash
  MAX_CONCURRENT=6  # Safe below Anthropic rate-limit inflection point
  DISPATCHED=0
  for agent in ${STAGE1_AGENTS[@]}; do
    while [ $(count_running_agents) -ge $MAX_CONCURRENT ]; do sleep 5; done
    dispatch_agent "$agent" &
    ((DISPATCHED++))
  done
  ```
  Stage 2 expansion (phases/expansion.md) already does incremental dispatch — apply same pattern to Stage 1.
- **Estimated savings**: Eliminates rate-limit retries (~30% token waste on retried runs). At 400k tok/review × 30% retry overhead × assumed 20% of reviews hit limit → ~24,000 tok/review amortized. Latency improvement: wall-clock time reduces from max-retry-latency to steady-throughput latency.
- **Difficulty**: S (add semaphore gate to dispatch loop in phases/launch.md)
- **Risk**: Cap too low → review takes longer. Tune MAX_CONCURRENT against actual API quota tier.

---

**QT-02. P2: Synthesis blocks on slowest agent — head-of-line blocking by max-latency policy**

- **Axis**: token-efficiency
- **Mechanism**: Head-of-line blocking in M/M/k queue. When synthesis waits for all k servers to complete before proceeding, the synthesis latency = max(agent_1, agent_2, ..., agent_k) rather than the 90th percentile. One Oracle agent timing out at 600s blocks the entire synthesis.
- **Current state**: `phases/synthesize.md` and the monitoring contract (`flux-watch.sh`) wait for all N expected `.md` files before proceeding to synthesis. The timeout is 300s (Task) or 600s (Codex). A partial-results path exists only for the failure-stub case (after retry), not as a proactive synthesis strategy.
- **Little's Law**: If 1 of 16 agents is a 5-minute outlier (Oracle), the mean synthesis wait = 5 min even if 15 agents completed in 90s. P90 latency of the whole review = max(agent_latencies) → dominated by the tail.
- **Proposal**: Add a timeout-and-proceed policy to `flux-watch.sh`: after 80th-percentile expected completion time (e.g., 120s for Task agents), synthesize with available results. Mark missing agents as "timed out — findings omitted" in the SYNTHESIS.md. Formally: treat each agent slot as an M/M/k server; accept synthesis when min(N_completed, 0.8×N_total) agents have returned.
- **Estimated savings**: For reviews where Oracle or a slow agent is in the roster, synthesis latency drops from 600s (full timeout) to ~120s (80th-percentile completion). UX: user gets results in 2 min instead of 10 min in the tail case. Token savings: avoids the re-try cost for the orchestrator waiting in a hot-spin.
- **Difficulty**: S (modify flux-watch.sh to accept --partial-ok threshold flag; modify synthesize.md protocol)
- **Risk**: Partial synthesis may miss a critical finding from the late agent. Mitigate: always include the timed-out agent's stub in SYNTHESIS.md with a "findings omitted — re-run agent" note.

---

**QT-03. P2: MCP server disconnects cause hook chains to stall — no circuit breaker**

- **Axis**: usability
- **Mechanism**: Backpressure in a serial queue with failed servers. In a standard M/G/1 queue, a server with infinite service time (hung MCP connection) causes queue utilization → 1 and wait time → ∞. Without a circuit breaker, the queue stalls.
- **Current state**: Claude Code detects MCP server disconnects (4 disconnected per session per target doc context). When a hook fires that calls a disconnected MCP server, the hook tool call hangs until the client-side timeout. Per-turn latency includes one timeout duration per disconnected server that a hook touches. `settings.json` / `settings.local.json` drift (Axis 1 usability issue) causes hooks to reference MCP servers no longer active in the session.
- **Proposal**: Add a circuit-breaker table to the hook runner:
  1. Track per-MCP-server success/failure counts (sliding window of 5 calls).
  2. If failure_rate > 60% in the window: mark server as OPEN (circuit open).
  3. While circuit is OPEN: skip hooks that require this server, log "circuit open: mcp-server-X skipped".
  4. After 60s: enter HALF-OPEN state, allow 1 probe call. If success: CLOSE; if fail: back to OPEN.
  This is the standard Hystrix/Resilience4j pattern applied to MCP server invocation.
- **Estimated savings**: Per-turn latency: removes 1 MCP timeout per disconnected server per turn. If timeout is 30s and 4 servers disconnect: up to 2 min saved per turn in failure mode. UX: per-turn latency becomes bounded and predictable.
- **Difficulty**: M (requires hook runner modification in core harness — not just config)
- **Risk**: False-positive circuit opens: transient failures trip the breaker prematurely. Tune window size and threshold carefully.

---

**QT-04. P2: Hook chain per turn is an unbounded serial queue — no priority scheduling**

- **Axis**: usability
- **Mechanism**: Priority inversion in a FIFO queue. When hooks execute sequentially in registration order, a low-priority informational hook (e.g., statusline update) can block a high-priority signal hook (e.g., budget alarm, permission error). This is textbook priority inversion: a P3 task holds the mutex while a P0 task waits.
- **Current state**: SessionStart hooks fire in the order listed in `settings.json`. Per the target doc, SessionStart emits ~50 lines of system reminders each turn. These are FIFO-queued: all hooks execute before any turn content is processed. A slow hook (e.g., CASS auto-index triggered by staleness check) blocks all subsequent hooks.
- **Proposal**: Add `priority: [0-3]` field to hook definitions in `settings.json`. Hook runner executes P0 hooks first (budget alarm, permission check), then P1 (session state), then P2 (informational), then P3 (statusline, cosmetic). If a P3 hook is slow (> 2s), skip it and emit a "slow hook skipped" notice rather than blocking P0/P1 hooks.
- **Estimated savings**: When CASS auto-index blocks (slow disk), P0 budget alarm still fires. UX: urgent signals are never delayed by cosmetic hooks. Token savings: indirect (prevents retry costs from missed budget alarms).
- **Difficulty**: S (add priority field to settings.json schema; modify hook runner to sort by priority before execution)
- **Risk**: Defining priorities for 20+ hooks requires owner judgment. Default new hooks to P2 if unclassified.

---

**QT-05. P3: /loop and /sprint tick intervals have no arrival-rate control under token pressure**

- **Axis**: token-efficiency
- **Mechanism**: Little's Law L = λW applied to loop ticks. At high tick frequency (λ high), tokens-in-flight L spikes even if per-tick work W is small. Under budget pressure, the correct response is to reduce λ (increase interval) rather than allow L to grow.
- **Current state**: The `/loop` skill runs at a user-specified interval (or self-paced). No mechanism adjusts the interval based on current budget consumption rate. Feedback memory (`feedback_sprint_budget_tuning.md`) notes that sprint budgets exhaust on C4 epics — this is partially a loop-rate problem.
- **Proposal**: Add a budget-adaptive interval to `/loop`: if `tokens_remaining / estimated_tokens_per_tick < loop_ticks_remaining`, automatically double the interval and notify the user ("slowing loop to preserve budget"). This is direct application of arrival-rate control (throttle λ to keep L = λW below budget ceiling).
- **Estimated savings**: Prevents loop from consuming budget too rapidly on long-running tasks. Estimated 10-20% reduction in loop-induced budget exhaustion events.
- **Difficulty**: S (add adaptive interval logic to loop skill, reading session-state.json from MPC-02)
- **Risk**: Slowing loop may frustrate user if they expect a specific cadence. Make adaptive interval opt-in (`--adaptive-budget`).

---

### Improvements

1. **QT-I1**: Add a `--concurrency N` flag to `/flux-review` and expose it in `config/flux-drive/budget.yaml` so the cap can be tuned per API tier without code changes.
2. **QT-I2**: Expose a per-turn `queue_depth` metric in the statusline (how many hooks are pending, how many MCP servers are in OPEN circuit state) — turns an invisible backpressure problem into a visible one.
3. **QT-I3**: For synthesis, implement `interflux:fetch-findings` (already listed as an available skill) to stream available findings into synthesis as agents complete — this is the co-translational-folding equivalent (see fd-ribosome-stall-rescue peer finding) and converts max-latency synthesis into streaming synthesis.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 1, P2: 3, P3: 1)
SUMMARY: /flux-review dispatches 16 agents without a concurrency cap, creating M/M/∞ contention at the Anthropic API tier that causes rate-limit retries and 30% token waste on affected runs. Synthesis head-of-line blocking turns one slow agent into a full-review latency penalty. The fixes are a semaphore gate (S difficulty) and a partial-results synthesis threshold (S difficulty) — both are single-PR changes. MCP circuit breakers (M) and hook priority scheduling (S) address the serial-queue stall patterns that degrade per-turn usability.
---

<!-- flux-drive:complete -->
