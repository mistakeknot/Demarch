# fd-decisions findings — microrouter deferral PRD

## Verdict

**NEEDS_ATTENTION** — The PRD operationalizes most of the critical brainstorm findings but creates two new blind spots: (1) F2's decision rule for D2 ("close the epic" vs "narrow to stable-7") depends on a headroom threshold (5%) that is not defended against the P0 feedback-loop finding, and (2) the "auto-revert to D2-then-resume" default sidesteps the question of whether D2's result should be *published* to stakeholders before the deadline, or held in reserve. Additionally, the PRD's numeric thresholds are pinned but not defensible — they read as placeholders wearing operational clothing.

---

## P0 findings

None — the PRD does not re-open the brainstorm's P0 (heuristic-controlled circularity) or contradict it. However, it leaves the P0 unresolved in the design phase (see P1 findings below).

---

## P1 findings

### Finding 1 — F2's D2 decision rule assumes headroom can be measured independently of Caveat 1 (P1)

The brainstorm's P0.1 identified that β's circularity is deferred, not broken: pass@1 outcomes accumulate *while the live heuristic makes routing decisions*, so β learns to imitate the heuristic. The PRD names four mitigations for this:

1. Off-policy randomized traffic
2. Manual-override weighting  
3. **Heuristic-stratified eval split (pre-registered as minimum required)**
4. Loss penalty for heuristic agreement

But F2 (the D2 bead specification) defines a decision rule based on headroom thresholds **without acknowledging which mitigation is in place during the 4-sprint accumulation window**:

> **Headroom < 5% on routing-eligible traffic** → close the entire `.19` epic

If the 4-sprint accumulation runs without any of the four mitigations (off-policy traffic, manual override weighting, heuristic-stratified eval, or loss penalty), then "headroom < 5%" is not a surprising failure — it's an *expected outcome* of heuristic-imitation training. The PRD pre-registers heuristic-stratified eval split as a minimum, but this is an *eval methodology* that measures post-hoc whether the router learned heuristic-easy vs heuristic-hard cases. It does not inject non-heuristic traffic during accumulation.

**Consequence:** D2 will measure the router against the oracle (or heuristic baseline) and find, roughly, that the router matches the heuristic's decisions ±noise. D2 then correctly reports "headroom <5%," and the decision rule fires. But the team has not tested whether off-policy randomization, manual overrides, or loss-penalty training would have produced better results. The decision to close the epic is made under incomplete information about whether the architecture is flawed or just under-mitigated.

**What would help:** F2's decision rule should distinguish between:
- **Headroom <5% with heuristic-stratified eval showing router ≈ heuristic on all tiers** → architecture is redundant; close epic
- **Headroom <5% with eval showing router only matches heuristic on easy tiers** → suggests under-mitigation during accumulation; recommend pivot to γ or apply off-policy mitigation retroactively to a new β run

The current rule conflates both cases.

---

### Finding 2 — Numeric thresholds (80 verdicts/cell, 20 long-tail, 30% noise, 5% headroom) are pinned but not defended (P1)

The "Operational definitions" section names four numeric thresholds:

| Threshold | Value | Source | Defensibility |
|---|---|---|---|
| Stable-7 volume | ≥80 verdicts per cell | "Stable" framing | ⚠ **Placeholder-like** — LoRA literature suggests 1K–2K per class; 80 is conservative but lower than theory |
| Long-tail volume | ≥20 verdicts per cell | "Long tail defined as agents with use_count ≥3" | ⚠ **Arbitrary** — use_count ≥3 is reasonable, but 20 verdicts for sparse agents is low for training |
| Label noise measurement | >30% → escalate; 15-30% → decide; <15% → ship | "TBD" in brainstorm | ❌ **Explicitly TBD** — 30% chosen as placeholder; no measurement protocol pinned |
| D2 headroom | <5% (lower bound 95% CI) → close epic | "Judgment call" in synthesis | ⚠ **Judgment call dressed as empirical** — no derivation; compares to β which hasn't been trained yet |

**Implication:** The PRD claims to "pin operational definitions before accumulation begins so they cannot drift under deadline pressure," but the thresholds themselves are under-defended. They feel like Schelling points ("nice round numbers") rather than thresholds derived from first principles. A future decision-maker reading these at the 2026-06-30 deadline will see "80 verdicts per cell" and wonder: is this a firm gate or a placeholder that should be ≥100?

**What would help:** For each threshold, add one sentence explaining the derivation:
- **80 verdicts/cell**: "Conservative: LoRA training literature (cite) suggests 1K per class; 80 on stable agents assumes 10–15 classes per agent and accepts some underfit to capture sparse-agent diversity."
- **30% label noise**: "Threshold set at post-experiment 1-sprint measurement. If first sprint shows 35% noise, will re-measure at 2-sprint mark before deciding. Rule: if noise trajectory is worsening, pivot to γ; if stable or improving, continue."
- **5% headroom on D2**: "Floor threshold: if heuristic already achieves 95%+ of oracle accuracy on routing-eligible traffic, marginal gain from learned router is not worth the engineering cost. Headroom CI (not point estimate) accounts for measurement error."

---

### Finding 3 — F2 coordination point is "checkpoint not gate," but the PRD doesn't say what happens if D2 fires BEFORE `.19.9` ships (P1)

F2 specifies:

> **Coordination point with deferral:** D2 result is a CHECKPOINT (not a gate). If D2 says "kill epic" before 2026-06-30, immediately re-open `.19.10` and close epic. If D2 says "epic survives," continue deferral. If D2 hasn't run by 2026-06-30, run it BEFORE resuming `.19.1`.

This is clear on what happens *after* 2026-06-30, but ambiguous on what happens if D2 runs early and returns a kill-the-epic verdict at, say, 2026-05-20 (two weeks into the deferral):

1. **Does the result surface to stakeholders immediately?** Or is it held in reserve until the deadline?
2. **If the result is published early, what's the decision authority's response?** Re-open `.19.10` and close the epic, or push back on D2's methodology?
3. **If D2 is still running but trending toward "kill epic," should the team pause `.19.9` engineering to avoid sunk cost?**

The PRD's "immediately re-open .19.10" language suggests the first scenario (early publication), but "checkpoint not gate" suggests the second (parallel independent measurement). The ambiguity creates a coordination failure: D2 could complete early with actionable information and have nowhere to publish it.

**What would help:** Add a "Escalation path" section to F3 explaining: "If D2 result is available before 2026-06-30, publish in `docs/research/2026-MM-DD-microrouter-heuristic-baseline-d2.md` and file a bead (`sylveste-s3z6.19.11` or similar) to surface the result for decision-making. Decision authority may choose to act immediately or defer to the original 2026-06-30 gate."

---

### Finding 4 — "Single-operator project; backup defaults to primary" is a placeholder escalation path that will collapse under load (P1)

F3 specifies:

> **bd state field on `.19.10`:** `decision_authority_backup=arouth1` (single-operator project; backup defaults to primary but field is explicit; future contributors with delegation will populate this)

The framing is honest (acknowledging the SPOF), but "future contributors will populate this" is a deferred failure mode. If arouth1 is unavailable on 2026-06-30, the field is populated *too late* to be useful. The PRD punts escalation to `.19.1` design phase ("see handoff for authority transfer protocol") but the handoff does not exist yet.

**Consequence:** The deferral depends on arouth1's availability on a specific calendar date 8 weeks in the future. If arouth1 is on leave, in a high-context meeting, or working on a parallel urgent epic, the deadline passes with no one authorized to re-open the decision. The auto-revert action ("run D2 then re-enter decision") is the fallback, but it's not a substitute for human decision authority — it's a process default that may not align with project priorities.

**What would help:** Add a specific co-signer or escalation rule:
- Option A: "If arouth1 unavailable by 2026-06-15, decision authority transfers to [name]. That person will review D2 result (if available) and either confirm 2026-06-30 deadline or extend by 2 weeks."
- Option B: "Automatic escalation: if no explicit human decision by 2026-06-30, the auto-revert action fires unconditionally. Deferral is not extended."

Currently, the auto-revert is *optional* ("the next routing-related sprint runs D2 unconditionally") not *mandatory*.

---

### Finding 5 — F1's claim that updates make the PRD "load-bearing on the bead graph" is true for `.19.10` but leaves `.19.8` opaque (P1)

F1 specifies:

> **`.19.8` body updated with closing note:** "α v0 commit shelved per `.19.10` (2026-05-06). Brainstorm contributions absorbed by downstream beads but the chosen architecture was deferred to β. See [link to .19.10 brainstorm]."

This is better than no note, but it does not fully resolve the fd-decisions P1.1 from the brainstorm review: future readers will still find `.19.8` in CLOSED state and need to reverse-engineer why a bead that "closed with α-v0 commit" is suddenly irrelevant. The F1 note uses the passive voice ("α...shelved") which obscures whether the decision was undone (reverted) or just deprioritized.

**Preferred framing:** "α v0 architecture exploration completed `.19.8`. Decision (2026-05-06): deferral to β. See `.19.10` for architecture decision and its justification. This bead's v0 commit is documented but not implemented; `.19.1` resumes with β design."

---

## P2 findings

### Finding 1 — Open Questions in the PRD include one genuinely load-bearing decision (auto-revert behavior) (P2)

The PRD ends with five open questions:

1. **Auto-revert behavior on deadline miss** — "run D2 then re-enter decision" vs "default to closing the epic"
2. **Backup decision authority** — delegation mechanism (deferred)
3. **`.19.8` body update reverse-link** — linking strategy (minor)
4. **Sprint-counting protocol when .beads/ activity is bursty** — OR-condition robustness (minor)
5. **D2 result archive location** — `docs/research/2026-MM-DD-*.md` vs TBD

**OQ #1 is load-bearing.** If the default is "run D2 then re-enter," the team has committed to running D2 as a *safety net* before any epic-close decision. But if the default is "close the epic," the deferral is actually a 2-month timer that auto-cancels the entire `.19` epic if the deadline is missed. These are fundamentally different risk postures.

The PRD frames it as "operator preference?" but this is not a preference — it's a core decision rule that affects whether D2 is a fallback (run-D2 path) or a gate (close-epic path). The choice should be made before `.19.9` starts shipping, so D2 scheduling aligns with the chosen default.

**What would help:** Remove OQ #1 from "open questions" and move to "PRD decision." Pick one: "If 2026-06-30 passes without explicit human decision, auto-revert to: run D2 unconditionally. If D2 says 'kill epic' or if 4 sprints of telemetry have not accumulated, close `.19` epic. Otherwise, resume `.19.1` design per the telemetry results." This removes the ambiguity and makes D2 a mandatory checkpoint.

---

### Finding 2 — F3's deferral_check_in mechanism is specified but has no enforcement teeth (P2)

F3 specifies:

> **PRD documents check-in protocol:** at each `deferral_check_in` date, sprint orchestrator runs `bd state sylveste-s3z6.19.10 deferral_check_in` and surfaces "deferral check-in due" notice in `/clavain:status` or session-start.

The mechanism exists, but:

1. **"Sprint orchestrator"** is vague. Who owns this check-in? If no one does, it's a volunteering task that will be skipped under load.
2. **"Surfaces in /clavain:status or session-start"** — these are informational, not gating. A notice in the status output can be ignored if the operator is busy.
3. **"Operator confirms (extends date by 2 sprints) or escalates"** — what if the operator confirms but doesn't update the `deferral_check_in` field? Then the next check-in date drifts.

**Mitigation:** The PRD should specify:
- Who is responsible: "Sprint lead runs `bd state --check deferral_check_in` at session-start for any bead with `auto_revert_action` set."
- Enforcement: "If `deferral_check_in` is overdue by >3 days, block `/clavain:sprint` from running until decision authority is contacted."
- Update protocol: "Operator response updates the field: `bd set-state sylveste-s3z6.19.10 deferral_check_in=YYYY-MM-DD` (extends by 2 sprints) or files an escape bead (sylveste-s3z6.19.10.escape) for re-decision."

Without enforcement, the check-in cadence becomes ceremonial.

---

### Finding 3 — PRD's claim that it "addresses" P0.1 is incomplete (P2)

The PRD says:

> **Caveat 1 mitigation pre-registration (for `.19.1` resumption):** ... this PRD pre-registers **heuristic-stratified eval split** as the **minimum required mitigation** before any `.19.3` LoRA training run.

This addresses the *symptom* of P0.1 (can the router beat the heuristic on hard cases?) but not the *cause* (does β training absorb non-heuristic-controlled signal during accumulation?). The eval split *measures* whether the router is a heuristic imitator, but it doesn't *prevent* that during the 4-sprint window.

The PRD correctly notes that off-policy randomization is "the strongest signal but requires changes to live agent-roles.yaml resolution; deferred for design discussion." But by deferring it, the PRD has left P0.1 unresolved at the feature level. D2 may report "headroom <5%" not because β is a bad architecture, but because the 4-sprint accumulation had no off-policy signal to learn from.

**Implication:** When D2 runs and finds low headroom, the PRD cannot distinguish between "β is fundamentally flawed" and "β is under-mitigated during accumulation." The heuristic-stratified eval split will show that the router learned to imitate the heuristic on easy cases, but that's *observable evidence* that the mitigation was needed, not evidence that it was wrong to try β.

**What would help:** F1 should add an acceptance criterion: "`.19.9` body must specify which of the four Caveat 1 mitigations will be active during the 4-sprint accumulation window, and why the others were deferred. If none are active, `.19.9` must document the rationale and the expected impact on D2's headroom measurement (e.g., 'heuristic-stratified eval will show 80%+ overlap; feature X will be added in `.19.1` design phase to break circularity')."

---

## P3 findings

### Finding 1 — F2's decision rule ties D2's "kill epic" threshold to a fixed 5% headroom, but oracle measurement method is deferred (P3)

F2 specifies:

> **Oracle upper bound:** synthesized from `verdict_outcome` aggregation OR from manual relabeling of a 200-sample stratified subset (whichever has lower noise)

The "whichever has lower noise" rule is sound, but it means D2's oracle accuracy (the denominator in the 5% headroom calculation) can vary depending on which method produces lower-noise results. If method A gives oracle_accuracy=92% and method B gives 95%, then:

- headroom = method_A - heuristic_accuracy is not comparable to headroom = method_B - heuristic_accuracy

The 5% threshold is then comparing across different measurement baselines. The PRD does not specify a tie-breaker ("if both have equal noise, use method A") or a consistency protocol ("re-run both methods on a held-out sample to ensure alignment").

**Severity: P3 because** this is a methodological detail that will only surface if D2 is actually run. It's important for audit trail, but not a blocker for PRD approval. However, if the PRD includes F2 acceptance criteria, the body should specify "Oracle measurement protocol: [specific method] is primary; if noise >20%, run [secondary method] and reconcile via [tiebreaker]."

---

## Verdict Summary

**NEEDS_ATTENTION** — The PRD operationalizes the brainstorm's findings well on paper (F1, F2, F3 all address specific P1s) but leaves three decision-quality gaps open:

1. **P1 (Critical):** F2's D2 decision rule assumes headroom can be measured independently of whether Caveat 1 mitigations are active during accumulation. PRD should clarify whether low headroom = architecture is flawed, or = architecture is under-mitigated during the 4-sprint window.

2. **P1 (Critical):** OQ #1 (auto-revert behavior) should not be open. The choice between "run D2 then re-enter decision" and "default to closing the epic" affects D2 scheduling and whether the deferral is a safety gate or a hard deadline. Move to PRD decision and make binding.

3. **P1 (Medium):** F3's check-in cadence lacks enforcement mechanism. Currently ceremonial; will be skipped under load. Add responsibility assignment and blocking condition.

4. **P2 (Medium):** Numeric thresholds (80 verdicts/cell, 30% noise, 5% headroom) are pinned but not defended against the brainstorm's finding that they may be arbitrary Schelling points. Add one-line derivation for each.

5. **P2 (Minor):** F2's D2 coordination should address early publication (if D2 finishes before 2026-06-30). Currently only specifies post-deadline behavior.

**Recommendation before implementation:** Resolve P1 findings 1 and 2. Tighten F3's enforcement to remove ceremonial drift. For P2 findings, defensibility is nice-to-have but not blocking if the decision authority is confident in the numbers. F1 is solid; F2 is solid but depends on P1 resolution.

