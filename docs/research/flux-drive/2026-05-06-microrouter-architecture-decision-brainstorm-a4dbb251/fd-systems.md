# fd-systems findings — microrouter architecture decision brainstorm

## P0 findings

### P0.1 — Feedback loop not actually broken; deferred until after critical path commit

**Lens: Feedback Loops & Causal Chains**

The α/β/γ decision frames the core problem as a circular calibration loop: judge training set anchors on calibration data, calibration data is built from judge outputs, outcome grading happens against judge agreement. β promises to break this via "independent ground truth" (pass@1 outcomes from real bead verdicts).

**The hidden circularity:** `.19.9` (interspect outcome-column extension) must *instrument* pass@1 data capture. But interspect writes to `routing-calibration.json` as a side effect of its normal operation (the P0-C fix from 2026-05-04: "live-file leakage flagged"). The SHA-pinned snapshot at `.19.1` time isolates v0 training from the live file, but pass@1 telemetry accumulation (4 sprints, ~8 weeks) happens in a context where:

1. `.19.1`/`.19.2`/`.19.3` remain blocked and paused
2. Live routing continues using the unfrozen heuristic + existing calibration JSON
3. `.19.9`'s pass@1 events accumulate against decisions made by the *unfrozen* live-routing heuristic

The 4-sprint telemetry window is not independent of the heuristic — it's a measurement of the heuristic's impact on real verdicts. When `.19.2` corpus is built (after 4 sprints), the labels say "these agents succeeded when routed by the live heuristic." The β model then learns to imitate the heuristic's decisions as captured in pass@1 outcomes.

**Second-order consequence:** If the live heuristic is suboptimal (unproven, per D2), pass@1 telemetry measures that suboptimality faithfully, and β learns to reproduce it. The loop is not broken — it is deferred until the team commits to .19.9 shipping, then replayed at scale across 4 sprints with real bead verdicts as the feedback signal. This is more expensive than α (which completes in days) because it pays the time cost upfront and *then* discovers if the data was good.

**Mitigation gap:** The decision acknowledges contingency trigger #1 (label noise >30%) but does not explain how "obviously-broken capture" is detected during pass@1 accumulation. The trigger fires *after* `.19.9` ships, not during the accumulation window, which means the team could discover at week 8 (when telemetry review happens) that the first 4 sprints are unusable. At that point, the cost of pivot to γ is no longer zero — the escalation decision happens in a sunk-time context.

**Severity assessment:** This is not a flaw in deferral as a strategy (the underlying reasoning is sound), but a blind spot in the decision model: β-when-ready assumes the readiness signal (4 sprints of clean pass@1) is detectable incrementally, not just at the deadline.

---

## P1 findings

### P1.1 — Cascade: 7 beads paused for 8 weeks creates downward pressure on sprint velocity and decision drift

**Lens: Pace Layers & Cascade Effects**

The decision shelves α (which was v0 at close of `.19.8`) and defers β until `.19.9` + 4 sprints. Downstream impact:

| Bead | Status | Estimated resume | Cost of delay |
|---|---|---|---|
| `.19.1` | Blocked on β telemetry | ~2026-07-01 | Design doc not started; will race against telemetry-report→plan-design→execute phase |
| `.19.2` | Blocked on `.19.1` | ~2026-07-15 | Corpus build is a bottleneck for LoRA training; delaying it compresses the training timeline |
| `.19.3` | Blocked on `.19.2` | ~2026-07-22 | LoRA training on constrained compute schedule (M5 Max ~2-6 hr per run per bead body); late start risks sprint slippage |
| `.19.4` | Blocked on `.19.2` | ~2026-07-22 | Eval harness depends on corpus shape; late start forces concurrent eval/training if anything goes wrong |
| `.19.5`/`.19.6`/`.19.7` | Paused | Unknown | No unblocking signal specified; microrouter resolver integration depends on learned router existing |

**Tempo mismatch:** `.19.9` (the critical path) is scoped as "3-5 days of engineering" (per 2026-05-04 design revision). But it sits in a queue with other P0s. If `.19.9` slips by 1 sprint (~2 weeks), the entire downstream chain shifts right by 2 weeks, compressing planning and execution for `.19.1`–`.19.4`.

**Decision drift risk:** The 2-month deferral creates a window where:
- The original motivation for the epic (latency/privacy wins) is not discussed
- Contributors who wrote `.19.1`–`.19.7` designs 4+ months ago may have context drift
- Other routing-adjacent work (D2 heuristic measurement, D1 dormant-five pruning) ships in parallel, potentially invalidating assumptions in the paused beads

**Mitigation:** The decision notes `.19.9` becomes "critical-path P0" and D2 runs in parallel as a "separate bead," but the strategy phase has not pinned:
- Who unblocks `.19.9` if it stalls?
- Does `.19.1` planning start *before* or *after* `.19.9` ships (affects parallelism)?
- If D2 kills the epic mid-deferral (contingency trigger #3), which of `.19.1`–`.19.4` is already committed?

**Severity assessment:** The deferral itself is sound, but the coordination cost across 2 months of pause is underestimated. This is a P1 because it compounds with P1.2 below.

---

### P1.2 — Schelling trap: "4 sprints of pass@1 telemetry" is a target that can be gamed without explicit definition of quality

**Lens: Schelling Traps & Emergent Behavior**

The decision specifies two readiness criteria for β: (a) `.19.9` ships, (b) "4 sprints of pass@1 telemetry accumulate." Contingency trigger #2 checks "pass@1 volume per (agent, complexity_tier) cell is below minimum for stable training." But the decision defers pinning "minimum per cell" and "4 sprints" to the strategy phase.

**The trap:** As the deferral deadline (circa 2026-07-01) approaches, there is implicit pressure to declare β "ready" and resume the downstream beads. Without pre-registered thresholds, the measurement of "4 sprints' worth" becomes subjective:

- Did "4 sprints" mean 4 calendar weeks, 4 true work weeks, or 4 sprints in which `.19.9` *finishes collecting new events*? (Different curves if interspect data lags.)
- Does "volume per (agent, complexity_tier) cell" mean every cell ≥ N examples, or N examples in aggregate across all cells?
- If 3 cells hit the threshold at week 12 and 1 cell is still sparse, does that trigger the γ-fallback or is it "close enough"?

**Incentive structure:** The decision authority (arouth1) bears the cost of either (i) waiting longer for telemetry or (ii) defaulting to γ (which adds ensemble orchestration work to `.19.2`). But the person implementing `.19.1`–`.19.4` bears the cost of deferral (idle time, context drift). There is an asymmetric incentive to declare "ready" once the deadline is in sight, even if thresholds are ambiguous.

**Collision with empirical discovery:** D2 (heuristic baseline measurement) is supposed to run in parallel and determine if "headroom >5%". If D2 finishes early and says "heuristic within 5%, kill the epic," then all of `.19.1`–`.19.4` are sunk work. The decision does not specify *when* D2's result is reviewed relative to the β-readiness call. If D2's result becomes available mid-deferral (say, week 4), the team must decide: do we pivot before `.19.9` ships, or do we complete the telemetry anyway as a "did we make the right call?" backstop?

**Severity assessment:** This is a P1 because the decision passes the hard part (the architectural call) but leaves the soft part (the operational definition of "ready") to future sessions, where time pressure and context drift conspire to produce a binary choice between deferral and acceleration.

---

### P1.3 — Dormant-Five prune (D1) is filed separately but shares decision authority and timeline with .19 epic

**Lens: Causal Chains & Emergent Complexity**

D1 (moving fd-game-design, fd-people, fd-decisions, fd-resilience, fd-perception out of always-triaged) is called a "separate parallel-runnable bead" but it lives in the same flux-drive review corpus that feeds `.19`. The decision summary says "D1 is tracked separately as a follow-up bead under the interflux epic, not under `.19`."

**Hidden coupling:** Removing 5 reviewers from the always-triaged set has a second-order effect on review coverage:
- These reviewers are dormant *because they rarely surface findings* in this corpus
- But their dormancy is measured against a review workload that is heavy on `.19` (microrouter epic spans 7+ beads)
- If D1 prunes them before `.19` resumes, and `.19.1`–`.19.4` land later, the dormant-five absence is not experienced as "we don't miss them" — it's experienced as "we didn't run them during the high-review-volume phase"

**Empirical hazard:** The 2026-05-05 analysis of the dormant five says "zero observed signal" across the reviewed corpus. But that corpus was biased toward architecture/correctness/safety findings (`.19.8` dominated the review load in recent weeks). A dormant reviewer might have signal *on* `.19`'s decision (e.g., fd-resilience on the contingency-trigger design, fd-people on the contributor-coordination aspects), but that signal was not observed because the corpus was upstream of `.19.8`'s publication and reflection artifacts.

**Severity assessment:** This is a P1 because the prune decision and the deferral decision are causally linked (both in the same flux-review session) but are treated as independent. If D1 ships and then `.19.1` surfaces a finding that fd-resilience or fd-people could have contributed to, the team will have lost the option value of those reviewers during the critical design phase.

---

## P2 findings

### P2.1 — γ (ensemble-of-judges) contingency lacks re-entry cost estimation if triggered mid-deferral

**Lens: Unintended Consequences & Option Value**

The decision preserves γ as a contingency with trigger conditions (label noise >30%, volume per cell <N, or strategic pivot). The re-entry cost summary says "zero today" (no `.19.2`/`.19.3` has run) and "Operating cost (~$30-150 + Qwen local compute)." But that estimate is anchored at the *decision point*, not at the *trigger point*.

If label noise is detected at week 6 (mid-deferral), the cost is no longer zero:

1. **Sunk time:** `.19.9` engineering has shipped; 4 sprints are partially accumulated (not 4 full clean sprints with quality). The decision to pivot costs the team "we were 2 weeks from having β data; now we're starting γ from scratch."
2. **Ensemble orchestration cost:** The decision says "adds ensemble-orchestration to `.19.2`" but does not itemize. Rough estimate: 1–2 days of `.19.2` work to integrate 4-way inference, family rotation, disagreement handling into the corpus-build pipeline. If `.19.2` was scheduled 2026-07-22, pivoting to γ at week 6 pushes that out.
3. **Model family availability:** Qwen3.6-35B is listed as a local-compute option. If it's not installed or the M5 Max has insufficient VRAM during the week-6 pivot, the re-entry cost becomes "add GPU cluster booking + delays to next sprint."

**Severity assessment:** This is a P2 because the contingency is sound in principle, but the decision does not account for the temporal coupling between contingency triggers and the deferral timeline. The "operating cost is bounded" claim is true in abstract, but not true in the context of a 2-month pause with a mid-point decision re-entry.

---

### P2.2 — D2 (heuristic baseline measurement) shares D4's assumption but is not blocked by it

**Lens: Causal Dependencies & Feedback**

D2 (Approach E: replay shadow over verdict corpus, compare heuristic vs oracle, quantify headroom) is presented as a "sanity check" independent of the β-deferral. The decision says "D2 should be a separate bead under `.19` (file as a follow-up). The deferral decision is independent: even if D2 says 'epic survives,' β-after-telemetry remains the v0 architecture."

**The hidden dependency:** D2 is supposed to answer "does the heuristic need a learned router at all?" But β's readiness (contingency triggers, telemetry sufficiency) is *also* based on the unspoken assumption that a learned router is worth building. If D2 finishes early (week 3) and says "headroom <5%, kill the epic," the decision to defer to β becomes *retroactively wrong*. The team has committed to 8 weeks of `.19.9` engineering + 4 sprints of telemetry accumulation for an architecture that D2 proved unnecessary.

The decision acknowledges this ("heuristic-baseline measurement is mentioned as a 'separate parallel-runnable bead'") but does not specify:
- Does D2 block `.19.9` shipping, or is `.19.9` scheduled independently?
- If D2 finishes with a "kill the epic" verdict before `.19.9` is done, is the result published immediately or held until `.19.9` is also closed?
- Does the strategy phase treat D2 as a decision gate (before any other `.19` work resumes) or a sanity check (in parallel)?

**Severity assessment:** This is a P2 because it's not a flaw in the deferral (the decision is correct to defer), but a missing coordination point. If the wrong person owns D2 or if D2 runs in isolation from `.19.9` scheduling, the two beads can diverge in their readiness signals and create a coordination failure.

---

## P3 findings

### P3.1 — Pace-layer rationality: "4 sprints" as a gating window buys time for telemetry signal to mature, but adds operational burden

**Lens: Pace Layers & System Inertia**

The 4-sprint telemetry window (~8 weeks) is slower than α's "days to training" timeline but faster than the 2026-05-05 analysis's framing of "months" of telemetry. The decision frames this as a necessary wait for "pass@1 accumulation" to produce stable training labels.

From a systems dynamics view, this is a reasonable pace-layer choice:
- **Fast layer (hours–days):** α training can run; results are available in days
- **Slow layer (weeks–months):** β telemetry maturity; results are available in 8 weeks
- **Integration layer (days after slow layer):** β training uses the matured labels; results available 2 weeks after telemetry closes

The 4-sprint waiting period is the cost of moving from a fast layer (judge agreement) to a slow layer (real outcomes). This is defensible if the accuracy improvement from β to α justifies 8 weeks of waiting.

**But:** The decision does not quantify the accuracy delta or compare to γ (which has mixed cost: some compute upfront, no wait). The comparison should be:

| Architecture | Time to first model | Confidence in labels | Maintenance cost |
|---|---|---|---|
| α | Days | Medium (judge agreement) | One judge family; scope for drift |
| β | 8 weeks + days | High (real outcomes) | Telemetry pipeline; live-file freeze mgmt |
| γ | Days–week | Medium-high (ensemble disagreement) | 4-way orchestration; per-tier consensus measurement |

The decision rationale says "β makes the headroom question answerable directly" but does not acknowledge that γ also answers it (via ensemble disagreement ≥80% threshold on hard tiers), at a faster pace and with lower operational overhead.

**Severity assessment:** This is a P3 (consider also) because the pace-layer choice is *good* but under-explained. Adding a comparison of α/β/γ against "time to first training" and "operational complexity" would strengthen the decision rationale.

---

## P3.2 — Review-after anchor is a single point of failure

**Lens: Crumple Zones & Fail-Safe Design**

The decision sets "review_after: .19.9 ships + 4 sprints of pass@1 telemetry" as the gate for re-entering the β-vs-γ decision. This is a single point of failure in the sense that:

- If `.19.9` slips and doesn't ship until week 4, the 4-sprint window doesn't close until week 12
- If telemetry accumulation is slow (e.g., fewer sprints than expected that quarter), the deadline moves right
- If the team wants to re-evaluate earlier (e.g., after 2 weeks of telemetry to spot-check quality), there's no intermediate gate

A more resilient design would include:
- Intermediate checkpoints (e.g., "after 1 sprint of pass@1, run a label-quality spot-check")
- A time-boxed review trigger (e.g., "if `.19.9` hasn't shipped by 2026-06-15, re-evaluate the decision")
- An operator-initiated escalation path (e.g., "if label noise is obvious after 2 sprints, pivot immediately without waiting for 4")

**Severity assessment:** This is a P3 because it's not a design flaw (the single gate is operationally simpler), but a resilience gap. The decision would be stronger with an intermediate checkup scheduled at the 1-sprint mark.

---

## Verdict

**NEEDS_ATTENTION** — The deferral is strategically sound, but operationally incomplete. P0.1 identifies a lurking feedback loop that β-deferred doesn't fully break. P1.1–P1.3 expose coordination gaps (cascade timing, contingency game-ability, dormant-five coupling) that will surface as the 2-month deferral unfolds. The strategy phase should address:
1. Define "4 sprints of pass@1" operationally (cells, volume, quality thresholds) before `.19.9` ships
2. Specify D2 coordination: when is its result published, and does it gate `.19.9` or run in parallel?
3. Add intermediate checkpoints to the `.19.9` + 4-sprint review gate (1-sprint label-quality spot-check; escalation path if noise is early)
4. Clarify the timeline coupling between D1 (dormant-five pruning) and D2/`.19` resumption: does D1 ship before or after D4 decision point?
