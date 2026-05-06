### Findings Index
- P1 | MPC-01 | "Axis 2: Token Efficiency" | /sprint and /work loops have no prediction horizon — budget gates fire reactively after exhaustion, not proactively before it
- P2 | MPC-02 | "Axis 2: Token Efficiency" | Budget constraint state is scattered across hooks and config — no single state object enables receding-horizon replanning
- P2 | MPC-03 | "Axis 2: Token Efficiency" | Heavy operations (/flux-review, /sprint C4 epics) dispatched without feedforward cost pre-check
- P2 | MPC-04 | "Axis 3: Replace LLM Orchestration" | Model tier selection (Sonnet vs Haiku vs Opus) is not budget-aware — no control-effort minimization under constraint
- P3 | MPC-05 | "Axis 1: Usability" | No graceful disturbance rejection path when user redirects mid-sprint — replan cost equals re-orient cost from scratch
Verdict: needs-changes

---

### Summary

MPC (Model Predictive Control) maps directly to Sylveste's session budget orchestration: the controller state is (tokens_used, tokens_remaining, expected_steps), the constraint set is (budget, cache TTL, MEMORY.md size), and the receding-horizon update replans every turn using revised cost estimates. Currently, Sylveste's /sprint and /work loops are purely reactive — they check budget after each step and have no mechanism to anticipate cumulative spend across a multi-phase epic. The MPC isomorphism reveals a P1 gap: /sprint on a C4 epic can exhaust budget mid-phase with no graceful degradation. The fix is a horizon-N planner that estimates tool costs feedforward and replans with control-effort minimization when constraints tighten.

---

### Issues Found

**MPC-01. P1: /sprint and /work loops have no prediction horizon — budget gates fire reactively**

- **Axis**: token-efficiency
- **Mechanism**: MPC prediction horizon N. In a standard horizon-N MPC loop: at each step k, estimate x(k+1|k), x(k+2|k), ..., x(k+N|k) using the system model. Apply the first control action u(k), then replan at k+1 with new measurements. Without horizon-N, the controller is pure bang-bang: run until limit, stop.
- **Current state**: The `/sprint` skill (in Clavain) executes phases (orientation → plan → implement → verify → close) sequentially. Budget tracking exists via the `interstat` plugin, but budget gates (`budget_gate_trip`) fire post-hoc when the session nears the configured token ceiling. There is no mechanism to estimate "how many tokens does Phase 3 (implement) require?" before dispatching it. Feedback memory (`feedback_sprint_budget_tuning.md`) confirms C4 epics exhaust budget; the fix was manual.
- **Concrete failure**: On a C4 epic (multi-file implementation + tests + verification), /sprint exhausts budget at the end of Phase 3 with Phase 4 (verify) and Phase 5 (close/beads) still pending. User sees "budget warning" with no handoff or graceful partial-commit path.
- **Proposal**: Add a horizon-N budget planner to `/sprint`:
  ```
  state = {tokens_used, tokens_remaining, current_phase, estimated_phases_remaining}

  At each phase boundary:
    predicted_spend = sum(cost_model[phase] for phase in remaining_phases)
    if tokens_remaining < predicted_spend * 1.2:
      apply control-effort minimization:
        - defer heavy subagents to next session
        - compress orientation (use cached context)
        - escalate to user: "N phases remain, estimated Xtk, remaining Ytk — continue or defer?"
  ```
  Cost model: feedforward estimates for each primitive (see MPC-03).
- **Estimated savings**: Prevents mid-epic budget exhaustion (UX) and the ~2,000+ tok cost of partial restarts. Estimated 1 session/week hits this failure; savings = ~2,000 tok/session + 1 frustration event.
- **Difficulty**: M (requires cost model + phase estimator in sprint skill + constraint state object)
- **Risk**: Cost model accuracy degrades for novel epics. Use high-confidence intervals (1.2× multiplier) to stay conservative.

---

**MPC-02. P2: Budget constraint state is scattered — no single constraint state object**

- **Axis**: token-efficiency
- **Mechanism**: MPC constraint set definition. In a proper MPC formulation, the constraint set X = {x : g(x) ≤ 0} is defined once and shared across all planning steps. In Sylveste, constraints live in:
  - `settings.json` → hook configuration (budget thresholds)
  - `MEMORY.md` → line budget (120 lines, currently 132)
  - Cache TTL (implicit — no explicit state)
  - `/loop` interval (loop-specific config)
  - `budget.yaml` (flux-drive only)
- **Current state**: Each subsystem checks its own constraint independently. There is no orchestrator-level constraint state object that lets the receding-horizon planner see "what is my total budget headroom right now across all dimensions?"
- **Proposal**: Define a lightweight `session-state.json` (written by SessionStart hook, updated by tool hooks) with fields:
  ```json
  {
    "tokens_used": N,
    "tokens_remaining": N,
    "memory_lines": N,
    "memory_budget": 120,
    "cache_age_seconds": N,
    "active_loops": [],
    "session_start": "ISO8601"
  }
  ```
  The receding-horizon planner reads this file at each phase boundary. Update: append-only via hook (no lock contention).
- **Estimated savings**: Enables MPC-01 planner. Indirectly saves ~1,000-2,000 tok/session by avoiding reactive budget trips. Direct cost: ~100 tok/session to read state file (negligible).
- **Difficulty**: S (single PR: SessionStart hook writes initial state, token-tracking hook updates it)
- **Risk**: State file diverges if hooks miss updates. Use atomic rename (write to `.tmp`, rename) to avoid partial reads.

---

**MPC-03. P2: Heavy operations dispatched without feedforward cost pre-check**

- **Axis**: token-efficiency
- **Mechanism**: Feedforward control vs. feedback control. Feedforward: when a known-expensive operation is queued, predict its cost and pre-check budget before dispatch. Feedback: react after the operation reveals its cost.
- **Current state**: `/flux-review` (16-agent fan-out, ~400k tokens) is dispatched without a budget pre-check. `/sprint` dispatches implementation subagents without estimating their cost. The pattern is purely feedback (post-hoc budget check). Feedforward estimates are not documented anywhere in the Sylveste primitives.
- **Feedforward cost estimates for the 5 most expensive primitives** (estimated from CASS analytics baseline):
  - `/flux-review` (16 agents): ~350,000-450,000 tok/invocation
  - `/sprint` Phase 3 (C4 implement): ~80,000-200,000 tok (variance high)
  - `flux-gen` (full roster gen): ~50,000-100,000 tok
  - `bd push` (full sync): ~2,000-5,000 tok
  - Hook chain per turn: ~1,000-3,000 tok (50-line SessionStart output × turns)
- **Proposal**: Add a `--dry-run` flag to `/flux-review`, `/sprint`, and other heavy operations that prints the cost estimate without dispatching. Before dispatch, check `session-state.json` (from MPC-02): if `tokens_remaining < feedforward_estimate * 1.1`, surface a warning and offer to defer.
- **Estimated savings**: Prevents the ~400k tok bust at end of session when budget is too low. Saves 1 failed /flux-review per 5 invocations → ~80,000 tok/5 sessions = ~16,000 tok/session amortized.
- **Difficulty**: S-M (flag is S; integrating session-state check is M if MPC-02 not done first)
- **Risk**: Feedforward estimates will be wrong for novel input sizes. Use range estimates with explicit uncertainty.

---

**MPC-04. P2: Model tier selection is not budget-aware — no control-effort minimization**

- **Axis**: ml-routing-replacement
- **Mechanism**: Control effort minimization. In MPC, the cost function includes a term λ·||u||² that penalizes large control inputs. When budget (remaining tokens) is the constraint, control effort = model tier choice. Using Opus when Sonnet suffices is excess control effort under budget constraint.
- **Current state**: `lib-routing.sh` in Clavain resolves model tier from `config/routing.yaml` based on agent category and phase. Budget state is not an input to `routing_resolve_agents`. A /sprint running on its last 50k tokens uses the same model tier as one with 500k remaining.
- **Proposal**: Pass `tokens_remaining` to `routing_resolve_agents`. When `tokens_remaining < threshold_tight` (e.g., 30k), apply control-effort minimization: downgrade Opus → Sonnet, Sonnet → Haiku for non-critical agents. Add `budget_mode: tight|normal|abundant` to the routing resolution chain.
- **Estimated savings**: On budget-tight sessions, saves ~30-50% of remaining token spend by tier downgrade. Estimated 1 in 5 sessions hits tight budget → ~15,000 tok/session × 20% of sessions = ~3,000 tok/session average.
- **Difficulty**: S (modify lib-routing.sh to accept budget_mode; add threshold config to routing.yaml)
- **Risk**: Quality degradation on Haiku for complex tasks. Must preserve safety floors: fd-safety and fd-correctness never below Sonnet.

---

**MPC-05. P3: No disturbance rejection path when user redirects mid-sprint**

- **Axis**: usability
- **Mechanism**: Disturbance rejection. An MPC controller includes a disturbance model D to absorb unexpected inputs. When a user redirect arrives mid-sprint ("stop, do X instead"), the controller should: (1) checkpoint current state, (2) estimate cost of abandoning vs. completing current phase, (3) replan with new objective. Currently: the sprint skill terminates without checkpointing, losing the orientation work already paid for.
- **Current state**: CLAUDE.md says "If you are redirected, stop immediately and follow the new direction." This is correct for safety, but no checkpoint is written. The next sprint re-orients from scratch (~5,000-10,000 tok orientation cost repeated).
- **Proposal**: Add a mid-sprint checkpoint hook: when a redirect is detected (user message during sprint execution), write a `sprint-checkpoint.json` with (current_phase, completed_steps, orientation_digest, open_beads). On next sprint invocation for the same bead, offer to resume from checkpoint rather than re-orient.
- **Estimated savings**: ~5,000-10,000 tok per resumed sprint. With ~2 redirects/week: ~10,000-20,000 tok/week.
- **Difficulty**: M (requires redirect detection + checkpoint write + resume logic in sprint skill)
- **Risk**: Checkpoint may be stale if significant time has passed. Add max-age TTL (e.g., 4 hours); beyond that, force full re-orient.

---

### Improvements

1. **MPC-I1**: Document the five most expensive Sylveste primitives in `docs/canon/cost-model.yaml` with p50/p90 token ranges from CASS analytics — this is the feedforward plant model the MPC planner needs.
2. **MPC-I2**: Add a budget dashboard to the statusline (Axis 1 win): show `tokens_used/remaining` live so the user can apply manual receding-horizon judgment before dispatching heavy operations.
3. **MPC-I3**: For the `/loop` skill, apply interval control-effort minimization: when budget is tight, increase loop interval (less frequent re-orientation) rather than stopping abruptly.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 1, P2: 3, P3: 1)
SUMMARY: Sylveste's sprint and work orchestration is purely reactive — budget gates trip post-hoc with no horizon-aware planner. The MPC isomorphism reveals a P1 gap: /sprint on C4 epics exhausts budget mid-phase with no graceful degradation. The receding-horizon fix requires a constraint state object (S), feedforward cost estimates for the 5 most expensive primitives (S), and a horizon-N planner in /sprint (M). These compose to a 3-PR sequence with an estimated 15,000-20,000 tok/session aggregate saving.
---

<!-- flux-drive:complete -->
