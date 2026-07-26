# fd-canallock-flowregulation — round 0

## Findings Index
- [P1] phantom-reservoir-dispatch-log — cost gate prices a token multiplier against a dispatch log whose wall-time/task-sum/agent-count fields are not found in repo (§3.3, §7)
- [P1] no-summit-level-read-before-gate-opens — the pre-dispatch cost gate (§3.2c) has no named reservoir signal (rate-limit headroom, budget remaining) to read before pricing the multiplier in
- [P2] chamber-sizing-left-as-runtime-choice — Q3 crossover is posed as an open question when the contract text itself (§5) already answers it structurally for nested repos
- [P2] gate-ordering-priming-cost-unstated — Q5's pre-spawn intermap+interlock dry-run has no stated priming cost vs. the passage (fan-out width) it protects, so there's no width threshold below which the gate self-defeats
- [P3] dry-lockage-clearing-condition-vague — Q4's "what evidence would flip it" is asked but not given a measurable trigger value [t]

## Findings

### phantom-reservoir-dispatch-log
- **Severity:** P1
- **Where:** §3.3 (constraint 3, conflict-economics telemetry) and §7 ("what done might look like")
- **What:** The brief states the dispatch log "already records wall-time, task-sum, agent-count" and that Rimsky's telemetry work is purely additive (append conflict-rate + merge-resolution-time to an existing table). I searched `os/Clavain/cmd/clavain-cli/` and `interverse/interlock/` for this existing dispatch log schema and found no file defining wall-time/task-sum/agent-count fields together. If this log does not exist as described, the entire §3.3 framing ("extend the EXISTING log") is a chamber built on a reservoir level nobody has actually gauged — Rimsky would need to build the base log AND the extension, which changes the v1 scope-cut math in Q6.
- **Evidence:** `grep -rn "wall.time\|wall_time" os/Clavain/cmd/clavain-cli/` returned nothing; broader search for `conflict_rate`/`conflict.rate` in `os/Clavain/` and `interverse/interlock/` (excluding docs/research) returned nothing. The claim traces to bead `Sylveste-4b5.8`'s description, which uses the identical phrase "Extend the EXISTING /clavain:work + /flux-review dispatch log" — so the unverified claim is inherited from the bead, not invented by the brief, but neither source shows the receipt.
- **Suggestion:** Before Q6 fixes the v1 boundary, spend one grep/read pass locating the actual dispatch-log implementation (or confirm it doesn't exist under that description). If it doesn't exist, "ship the instrument" in v1 must include building the base log, not just appending two columns — a real scope delta that changes the shippable-v1 sizing.

### no-summit-level-read-before-gate-opens
- **Severity:** P1
- **Where:** §3.2(c) "price the token multiplier into the parallelize-or-not decision"; Q5
- **What:** The pre-dispatch cost gate is specified as pricing the multiplier into a decision, but nowhere does the brief name what the gate reads to know the *current* reservoir level — an actual token-rate-limit budget remaining, a per-session spend ceiling, or a hardcoded width cap. Without a named signal, "price the multiplier in" can only ever mean "know the multiplier exists," not "know whether the summit can afford it right now." A lock-keeper who prices water cost but never checks the reservoir gauge still drains the pound dry on a big flight.
- **Evidence:** Contract doc (`docs/guide-worktree-first-coordination.md`) has no token-budget or rate-limit section — it only covers worktree mechanics (isolation rules, nested-repo routing, autosync lanes). The brief's own retired-figure caveat (§3.1: "MAX_CONCURRENT... is a deliberate rate-limit/cost gate" left untouched) confirms a cap exists but is static, not a live-read reservoir level.
- **Suggestion:** Add one explicit sub-question to Q3/Q5: does the cost gate read a live signal (e.g., remaining rate-limit budget from the API, or session token spend so far) or only a static advisory constant? If only static, say so plainly in §3.2(c) rather than implying dynamic pricing — this changes whether Q4's "dynamic controller" is really about conflict *or* about budget-awareness the brief hasn't separated.

### chamber-sizing-left-as-runtime-choice
- **Severity:** P2
- **Where:** Q3 (§5) vs. contract §5 "Sharp edge — nested repos"
- **What:** Q3 asks whether there's "a crossover the orchestrator should compute" between per-repo-worktree isolation and interlock-shared-tree, implying an open, possibly dynamic decision. But the contract's §5 nested-repo rule already answers this at build time for the dominant case in this codebase: "worktree isolation is per nested repo, not root" — a structural, not computed, rule. The brief frames Q3 as more open than the contract's own hardest correctness constraint (§4: "Rimsky must fan out per nested repo") actually leaves it.
- **Evidence:** `docs/guide-worktree-first-coordination.md` §5, lines 73-96: "Contract rule: worktree isolation is per nested repo, not root." The brief's own §4 restates this as Rimsky's "hardest correctness constraint," yet §5's Q3 still asks whether the crossover needs computing — for the primary case (nested repos) the contract already forecloses computation.
- **Suggestion:** Split Q3 into two sub-cases explicitly: (a) nested-repo fan-out — already answered structurally by the contract, no computation needed; (b) same-repo, different-file-set fan-out where worktree-vs-interlock genuinely trades off cost vs. isolation and a width crossover might matter. Only (b) is a live open question; conflating them makes Q3 look more unresolved than it is.

### gate-ordering-priming-cost-unstated
- **Severity:** P2
- **Where:** Q5 (§5); constraint 2(b) (§3.2)
- **What:** The mandated pre-spawn check (intermap change_impact + interlock dry-run) runs before every intra-repo fan-out with no stated cost figure and no stated fan-out-width threshold below which the check's own cost could exceed the savings it's meant to protect (avoiding a conflict on a 2-task fan-out is cheap to lose to; the dry-run still pays its full cost). Q5 asks the right question ("could the check itself become the bottleneck?") but the brief supplies no candidate answer or even an order-of-magnitude estimate to reason from.
- **Evidence:** Neither `docs/guide-worktree-first-coordination.md` nor the brief itself states a cost for `intermap change_impact` or `interlock dry-run` individually — contrast with the worktree cost figure the brief does supply elsewhere in the doc corpus (~200-500ms+disk, found in `docs/research/flux-drive/2026-05-04-target/fd-queueing-priority-scheduling.md` and similar, not in the contract doc directly — see companion double-entry finding on citation grounding).
- **Suggestion:** Before Rimsky implementation, get one cheap number: time `intermap change_impact` and `interlock dry-run` on a representative repo, and state it next to the worktree setup cost. If the pre-spawn check is sub-50ms, Q5 mostly resolves itself (run unconditionally). If it's comparable to worktree setup cost, Q5 needs its own gate (e.g., skip below N=2 tasks).

### dry-lockage-clearing-condition-vague
- **Severity:** P3 [t]
- **Where:** Q4 (§5); constraint 3 (§3.3)
- **What:** Q4 asks "what evidence would flip that?" for the deferred controller but the brief (and the source bead `4b5.8`) only gestures at "a non-trivial conflict rate" without a number. The stress-test question is well-posed but its own answer is left as open as the question — a keeper who says "build the second gate when the water gets scarce" without naming a gauge reading is still guessing at flood time.
- **Evidence:** `4b5.8` description: "GATED on the telemetry returning a non-trivial conflict rate (interlock may already give ~zero...)" — "non-trivial" is never quantified anywhere in the brief or the bead.
- **Suggestion:** Borrow the number that already exists one hop away: `docs/research/research-toctou-in-multi-agent-coding.md:461` (see double-entry lens finding on the misattributed filename) states ">1% conflict rate → escalate." Pin the controller's clearing condition to that number explicitly in Q4's answer, don't leave "non-trivial" undefined.

## Verdict
The brief's cost-gate and telemetry machinery reads as already-flowing water (an "existing" dispatch log, a priced multiplier) that a repo search cannot substantiate — the reservoir accounting the doctrine demands of every gate has not itself been applied to the brief's own citations. The nested-repo chamber-sizing question (Q3) is posed more open than the contract's own text leaves it for the dominant case, and the pre-spawn gate's priming cost (Q5) is asked about but never estimated, leaving no way to set the threshold the question itself calls for.
