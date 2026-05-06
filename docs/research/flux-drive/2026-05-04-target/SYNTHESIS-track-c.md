---
generated_at: 2026-05-04
track: C (Distant)
agents: [fd-kalman-filter-fusion, fd-mpc-control-budget, fd-queueing-priority-scheduling, fd-ribosome-stall-rescue]
source_domains: [aerospace/sensor-fusion, process-control/MPC, queueing-theory, cellular-translation]
axes: [usability, token-efficiency, ml-routing-replacement]
---

# Track C (Distant) — Synthesis

## Cross-Agent Findings Map

| ID | Agent | Axis | Mechanism | Severity | Difficulty | Est. Savings |
|---|---|---|---|---|---|---|
| KF-01 | kalman | ml-routing | Kalman gain / innovation gating | P1 | M | 300-400 tok/turn |
| QT-01 | queueing | token-efficiency | M/M/k concurrency cap | P1 | S | ~30% retry waste |
| RB-01 | ribosome | usability | Pelota/Hbs1 stall rescue | P1 | S | 16 min/stalled review |
| MPC-01 | mpc | token-efficiency | Receding-horizon planner | P1 | M | ~2,000 tok/sprint bust |
| MPC-03 | mpc | token-efficiency | Feedforward cost pre-check | P2 | S-M | 16,000 tok/review amortized |
| MPC-04 | mpc | ml-routing | Control-effort minimization | P2 | S | ~3,000 tok/session avg |
| QT-02 | queueing | token-efficiency | Head-of-line blocking / partial synthesis | P2 | S | 8 min latency on tail |
| QT-03 | queueing | usability | Circuit breaker for MCP disconnects | P2 | M | 2 min/turn in failure mode |
| QT-04 | queueing | usability | Hook priority scheduling | P2 | S | P0 signals unblocked |
| RB-02 | ribosome | token-efficiency | mRNA half-life / memory expiry | P2 | S | 100-200 tok/session |
| RB-03 | ribosome | ml-routing | Signal peptide / SRP prefix routing | P2 | S | 180-300 tok/turn |
| RB-04 | ribosome | token-efficiency | No-go decay / agent down-weighting | P2 | M | 10-20% triage budget |
| RB-05 | ribosome | usability | Ubiquitin tagging / scheduled cleanup | P2 | XS | 5 min/session UX |
| KF-02 | kalman | ml-routing | Steady-state filter / bead dedup | P2 | S | ~4,250 tok/session |
| KF-03 | kalman | ml-routing | Observability matrix / triage shortcut | P2 | S | ~1,200 tok/review |
| KF-04 | kalman | token-efficiency | Innovation gating / voice fidelity | P2 | S | ~630 tok/session |
| MPC-02 | mpc | token-efficiency | Constraint state object | P2 | S | Enables MPC-01 |
| MPC-05 | mpc | usability | Disturbance rejection / sprint checkpoint | P3 | M | 5,000-10,000 tok/redirect |
| RB-06 | ribosome | token-efficiency | Co-translational folding / streaming synthesis | P3 | M | 2-3 min/large review |
| KF-05 | kalman | token-efficiency | Process noise / retraining cadence | P3 | M | Prevents drift |
| QT-05 | queueing | token-efficiency | Arrival-rate control / adaptive loop interval | P3 | S | 10-20% loop budget |

## Convergence Analysis

Three findings appear independently from different source domains, confirming high confidence:

**Convergent: Short-prefix routing (3 agents)**
- KF-01 (Kalman): "innovation gating — only invoke LLM when sensor disagreement exceeds threshold"
- RB-03 (Ribosome): "signal peptide / SRP — first 3 tokens decide route before full input is processed"
- Peer finding from fd-search-engine-ranking: "85% token reduction via top-k retrieval for agent triage"
→ All three independently identify the same root cause: LLM invoked for decisions observable from cheap signals. Combined confidence: very high. **Unified proposal**: SRP prefix table + Kalman fusion layer for the uncertain zone (0.70-0.85 confidence band).

**Convergent: Streaming / partial-result synthesis (2 agents)**
- QT-02 (Queueing): "head-of-line blocking — synthesis waits for max-latency agent"
- RB-06 (Ribosome): "co-translational folding — downstream work begins before upstream completes"
→ Both independently identify the same mechanism: serial synthesis wait is the wrong queue discipline. **Unified proposal**: `interflux:fetch-findings` streaming mode in synthesize.md with 80th-percentile timeout.

**Convergent: Memory / state expiry (2 agents)**
- RB-02 (Ribosome): "mRNA decay half-life — memory entries accumulate without expiration"
- MPC-02 (MPC): "constraint state scattered across hooks — no single state object"
→ Both point to the same gap: session state management is fragmented. **Unified proposal**: `session-state.json` (MPC-02) + `expires_after` frontmatter (RB-02) as complementary layers of the same state management problem.

## Priority Sequence (Effort-Adjusted)

### Tier 1 — S difficulty, highest ROI (do first)

1. **QT-01**: Concurrency cap in phases/launch.md — semaphore gate `MAX_CONCURRENT=6`. Eliminates rate-limit retry waste (~30% token overhead on affected reviews). One-line change in dispatch loop.
2. **QT-02**: Partial-results synthesis threshold in flux-watch.sh — `--partial-ok 0.80`. Converts max-latency synthesis to 80th-percentile latency.
3. **RB-01**: Stall-rescue detection in flux-watch.sh — 60s no-output timeout → error stub + peer finding. Recovers 16 min per stalled review.
4. **RB-03 / KF-01 combined**: SRP prefix table for /command-prefixed inputs, Kalman fusion for the 0.70-0.85 confidence band. Saves 180-400 tok/turn.
5. **KF-02**: Embedding-based bead dedup pre-filter in bd create. ~4,250 tok/session.
6. **MPC-02**: `session-state.json` written by SessionStart hook. Prerequisite for MPC-01 and MPC-04.

### Tier 2 — M difficulty, compound ROI (do second)

7. **MPC-01**: Horizon-N budget planner in /sprint. Requires MPC-02. Prevents C4 epic budget exhaustion.
8. **QT-03**: Circuit breaker for MCP server disconnects. Removes 2 min/turn stall in failure mode.
9. **RB-04**: No-go decay agent down-weighting. Requires CASS analytics pipeline.

### Tier 3 — XS/S difficulty, UX wins (do alongside)

10. **RB-05**: Ubiquitin-tag frontmatter (`scheduled_for_cleanup`). XS — purely additive frontmatter field.
11. **QT-04**: Hook priority scheduling (`priority: [0-3]` in settings.json). S — schema + runner sort.
12. **RB-02**: `expires_after` frontmatter on memory files + SessionStart staleness check. S.

## Total Estimated Savings (Track C)

Assuming Tier 1 fully shipped:
- Routing decisions (KF-01, RB-03): −300-400 tok/turn × 80% of turns = −240-320 tok/turn net
- Bead dedup (KF-02): −4,250 tok/session
- Concurrency fix (QT-01): −30% retry overhead on reviews (est. ~20k tok/affected review × frequency)
- Stall rescue (RB-01): −16 min wall-clock per stalled review (UX, not token)
- Synthesis latency (QT-02): −6-8 min latency in tail case (UX)

**Estimated Tier 1 token savings**: 5,000-8,000 tok/session (conservative; assuming 20 turns/session and 20% of turns hit routing)
**UX wins**: Stall recovery, bounded synthesis latency, no mid-epic budget exhaustion

## Peer Findings Integration

From fd-search-engine-ranking (Track B): "85% token reduction via top-k embedding retrieval for agent triage" — this is the Kalman observability lens applied to the 679-agent index. KF-03 and this finding compose: the triage shortcut handles well-typed inputs, top-k embedding handles the moderate-confidence case, full Sonnet triage handles novel inputs.

From fd-build-system-caching (Track B): "timestamped OUTPUT_DIR defeats prompt cache" — relevant to MPC-03 (feedforward cost model). Fixing cache hermeticity reduces the feedforward estimate for iterative /flux-review runs from 400k to ~200k tok/review.

<!-- flux-drive:complete -->
