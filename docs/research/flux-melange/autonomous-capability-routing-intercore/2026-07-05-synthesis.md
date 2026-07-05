---
artifact_type: melange-synthesis
method: flux-melange
target: "docs/brainstorms/2026-07-05-autonomous-capability-routing-intercore.md"
target_description: "Phased plan to turn the fable→sonnet→opus capability-routing doctrine into intercore-enforced mechanism"
goal: "maximize verified novelty×risk surface until dry"
weights: balanced
rounds_run: 3
halt_reason: BUDGET
total_fusions: 3
emergent_findings: 6
date: 2026-07-05
---

# Flux-Melange Synthesis — Capability-Routing → Intercore Mechanism

The eye of distance over a 3-round spice loop (rounds 0–2) against the plan that would turn the fable→sonnet→opus capability-routing doctrine into intercore-enforced mechanism. 43 findings entered the ledger; 29 upheld, 1 refuted, 13 remain raw below the verify gate. Scores below are a re-score of the merged ledger, not the per-round triage estimates — the ordering held on re-scoring but the frontier tightened to a two-finding Pareto face.

**Heat = novelty × risk.product.** Everything below is ranked by heat, never by severity. Severity (P0–P3) appears for reference only; it tracks fix-urgency, not spice.

> **If you read one thing: f-027** — the two-strikes escalation ladder is *the sampling mechanism* that populates the per-(author_tier, executor_tier) pass-rate the whole doctrine gates autonomy on, and it drains sonnet's hardest cases into opus/fable by construction, inflating both tiers' apparent competence at once. The doctrine's own pass-rate premise is **unmeasurable** until escalated-dispatch attribution is decided, and the plan is silent on it. (heat 27; argmax over upheld, taste tiebreak neutral — see note in §Frontier.)

---

## 1. Novelty×Risk Frontier

The strict Pareto front on (novelty, risk.product) among upheld findings is a two-finding face — **f-027 and f-031, both at novelty 3 / risk 9 (heat 27)**. Neither dominates the other; they are different failure surfaces at the same extreme. The mid-novelty/max-risk lead the brief asks for sits one notch inside that face on the novelty axis but ties it on risk: **f-011 at novelty 2 / risk 9**. Both f-027 and f-011 lead; they are the two answers to "what is the most dangerous thing here" from two different distances.

### Lead A — max-novelty / max-risk (emergent): f-027
- **Claim.** The two-strikes escalation spillway is the exact mechanism that populates the per-(author_tier, executor_tier) gating metric's sample, and it does so asymmetrically *by construction*: every task hard enough to fail sonnet twice is removed from the sonnet-executor population and deposited into opus/fable's. The natural "each dispatch's own executor_tier" implementation silently drains sonnet's hardest cases and inflates both tiers' apparent competence simultaneously.
- **Lens(es).** `fd-fused-gauge-siltation` (fusion of `fd-eval-calibration-metrics` × `fd-hydraulic-diversion`). Emergent — see §2.
- **Risk decomposition.** blast_radius 3 × likelihood 3 = **product 9**. Blast is repo-wide: the number this corrupts is the north-star that gates autonomy widening (doctrine Rule 6). Likelihood is high because the naive/default implementation ("record each dispatch's own executor_tier") *is* the biased one — you have to notice the drain to avoid it, and the plan gives no reason to notice.
- **Severity (reference only): P0.**

### Lead B — mid-novelty / max-risk (verified base): f-011
- **Claim.** `_routing_model_tier` (bash) and `ParseModelTier` (Go) both fall through to tier 0 for any unrecognized string. If `fable` is added to `routing.yaml` config tiers but not to these tier-ranking functions, fable resolves to tier 0 — below every real safety floor — so any floor-configured agent silently clamps fable *down* to its floor on the first call.
- **Lens(es).** `fd-routing-kernel-mechanics` (base).
- **Risk decomposition.** blast_radius 3 × likelihood 3 = **product 9**. Blast is every floor-configured agent. Likelihood is high because adding `fable` to config without touching two separate tier-ranking functions in two languages is the *expected* first move — the config surface and the ranking surface are maintained independently (this is the same seam f-012/f-013 attack from the divergence side).
- **Severity (reference only): P0.**
- **Why it leads despite mid novelty.** This is the single verified finding that makes the headline feature ("fable does planning/architecture") silently *not happen* on day one — fable gets clamped away before it plans anything. It is lower-novelty only because "unrecognized string → tier 0 → ordinal floor comparison" is a known routing-kernel hazard category; it is max-risk because the plan's central capability depends on it and the failure is invisible in logs (reads as a normal clamp).

**Reading the two leads together:** f-011 breaks the mechanism at *resolution* time (fable never reaches the tier it was meant to); f-027 breaks the *measurement* of the mechanism (even where routing works, the number that would tell you it works is biased). One is a levee with a hole; the other is a gauge installed on the wrong side of the diversion. Both are load-bearing for "turn the doctrine into enforced mechanism," and neither is severity-sortable above the other — they fail different organs.

---

## 2. Top Fusions — the emergent surface

This is the section the mode exists for: findings **no single lens could produce**, each carrying an intersection_justification that shows deleting either parent collapses it to a single-parent concern. Six emergent findings survived hardened verification — f-027, f-029, f-031, f-033 (round 1), f-042, f-043 (round 2) — ranked by heat.

### The recurring meta-pattern: **the fix already exists in-repo, unwired**
Five of the six emergent fusions land on the same shape — *the mechanism the plan needs to design from scratch is already built and sitting one file away, orphaned or wired to the wrong edge.* This is the single most valuable thing the fusion layer found, because it converts a backlog of "design and build X" into "grep for X and wire it in":

| Finding | The unwired mechanism already in-repo |
|---|---|
| f-031 | **orchestrate.py's `build_prompt`/`summarize_output` read-back** (lines 290–330) already does "read a prior verdict, inject into next prompt" — wired only to the DAG dependency edge, not the retry chain. |
| f-029 | **`ListRetryChain`'s ParentDispatchID walk** + the **unused `FloorFrom`/`FloorTo`** Decision fields (decision.go:25–26) already reconstruct resolved-model-per-attempt — the author_tier fix is a join, not a new primitive. |
| f-042 | **`cmdSetArtifact`'s BLAKE3 `BlobHash`** (cxdb_client.go:355–375) is already computed and written for every artifact including Phase 3's criteria file — and never read back anywhere in clavain-cli. An existing content-addressed seal sits next to the measurement surface that needs it. |
| f-043 | **`_interspect_classify_session_source`'s `source_weight`** (0.5×/0.7×/1.0×, lib-interspect.sh:3046) already answers "is this evidence trustworthy to count at full weight" for the sibling per-agent metric — Phase 4 free-designs a parallel metric without wiring to it. |
| f-027 | **`retry.go:184`'s ParentDispatchID→Model linkage** could disambiguate a rescued success; Phase 4 never mentions consuming it. |

The plan reads as if written by authors who did not `grep` the very subsystems they are extending. The cheapest high-value move out of this whole loop is a "grep-before-you-design" pass over Phases 2–4.

### Ranked emergent findings

**f-031 — heat 27 (nov 3, risk 9, b3×l3) · P0 · `fd-fused-lesson-transport`**
Parents: `fd-escalation-retry-ladder` × `fd-swordsmith-transmission`.
Phase 2's ladder re-dispatches WORK but not KNOWLEDGE: `Retry()` copies `orig.PromptFile` verbatim (line 116), explicitly nils `VerdictFile` (line 119), and there is no interspect import in `internal/dispatch/` — so the escalated higher tier inherits *nothing* the failed attempt learned. `orchestrate.py` already implements exactly the read-back this needs, wired only to the DAG edge.
*Intersection:* the retry-ladder lens alone certifies the state machine correct (counter increments, terminates, no oscillation past attempt 3) — a clean terminating machine. The swordsmith lens alone flags "no correction is carried forward" but has no way to say *where* the carry-forward attaches — it doesn't know `retry.go`'s `VerdictFile` field exists or that orchestrate.py already solved this for a sibling edge. Only holding both reveals the fix is "route Phase 2's re-dispatch through the read-back path that already exists," not "add an escalation feature."
*Evidence:* retry.go:112–130 builds `d` with `VerdictFile: nil`; orchestrate.py:290–330 is the only extant read-back mechanism, scoped to DAG dependencies; brainstorm line 55 records the failure mode but never injects it into the escalated dispatch's input.

**f-027 — heat 27 (nov 3, risk 9, b3×l3) · P0 · `fd-fused-gauge-siltation`** — *the If-You-Read-One-Thing.* See §1 Lead A.
Parents: `fd-eval-calibration-metrics` × `fd-hydraulic-diversion`.
*Intersection:* fd-eval alone flags "aggregating by executor_tier needs a stratification note" (abstract, any tiered metric); fd-hydraulic alone flags "the escalation path needs from_model/to_model for observability" (a logging nicety). Neither reaches the causal claim that *this specific spillway populates this specific gate-governing number's sample asymmetrically by construction* — hard tasks flow one direction, never back. Only fusing where-escalation-routes-the-record (hydraulic) with what-the-pass-rate-assumes-about-sample-independence (eval) yields it.

**f-029 — heat 18 (nov 3, risk 6, b2×l3) · P1 · `fd-fused-gauge-siltation`**
Parents: `fd-eval-calibration-metrics` × `fd-hydraulic-diversion`.
Fable-window author_tier is sourced at *spec-load* time (declared intent), not at *dispatch* time post-fallback — so an opus-standing-in-for-fable run records `author_tier=fable` that never executed. The fix is a wiring omission, not a missing primitive: `ListRetryChain` already walks ParentDispatchID to reconstruct resolved-model-per-attempt, and `FloorFrom`/`FloorTo` already exist unused for exactly this fallback case, so Phase 4 should join `plan_execution_outcome` to the nearest preceding `routing_decisions` row's resolved tier.
*Intersection:* fd-eval alone says "author_tier must reflect actual production, not intent" (standard construct-validity); fd-hydraulic alone says "the fallback path needs a clamp/fallback event to be observable" (standard plumbing observability). The fusion is the falsifiable claim that the plumbing fix *already exists in-repo*, turning the fix from "design resolved-tier tracking" (expensive) into "reuse ListRetryChain / the existing decision fields" (cheap).

**f-033 — heat 12 (nov 3, risk 4, b2×l2) · P2 · `fd-fused-lesson-transport`**
Parents: `fd-escalation-retry-ladder` × `fd-swordsmith-transmission`.
The one-escalation cap specifies a valid terminal stop but not *what artifact accompanies surfacing to the human*. With no lesson-payload threading and an undifferentiated `failure_mode`, the default surfaces only the final dispatch's own output plus a counter — not the per-tier lesson chain (what sonnet tried and why, what opus changed and why *that* failed too), forcing the terminal inspector to re-derive the chain by hand.
*Intersection:* the retry-ladder lens is fully satisfied (chain terminates, cap enforced). The swordsmith lens has no chain-boundary concept to point at. Fusing them exposes that termination is the *one point where the state machine hands control entirely outside itself* — exactly where the transmission inheritance obligation is highest.

**f-042 — heat 12 (nov 3, risk 4, b2×l2) · P1 · `fd-fused-custody-attribution`**
Parents: `fd-eval-calibration-metrics` × `fd-assay-hallmark`.
`cmdSetArtifact` already computes `blake3.Sum256` and stores it as `ArtifactRecord.BlobHash` whenever any artifact (including Phase 3's criteria file) is registered — but that hash is **never read back anywhere in clavain-cli** (write-only telemetry, fail-open at every step), and Phase 3/4 reinvent a second, hash-less sealing story for the same artifact instead of binding the existing custody witness into `plan_execution_outcome`.
*Intersection:* the custody parent (f-034) is satisfied on paper — set-artifact exists, a hash is computed, "looks sealed." The measurement parent says "bind a version/hash into each outcome row" abstractly, as a gap to design from zero. Neither catches that a *working* hash mechanism already exists in this exact codepath and is orphaned. Only both together reveal the reconciliation bug: an already-computed BlobHash witness sits next to the exact outcome surface that needs it.

**f-043 — heat 12 (nov 3, risk 4, b2×l2) · P2 · `fd-fused-custody-attribution`**
Parents: `fd-eval-calibration-metrics` × `fd-assay-hallmark`.
The existing B3 calibration path already answers "is this evidence trustworthy at full weight" via `_interspect_classify_session_source` (bootstrap 0.5× / self-building 0.7× / normal 1.0×) through `source_weight` in `weighted_hit_rate` — expressly so calibrating-era evidence isn't pooled with steady-state. Phase 4's `plan_execution_outcome` has no analogous source class, so once the Rule-6 2–3-item pilot "passes" and autonomy widens, pilot-era rows and post-widening rows pool at identical weight in the same cell with no custody marker.
*Intersection:* the measurement parent owns "is the pilot big enough" (sample size — excluded). The custody parent would ask "was the pilot witnessed as a rehearsal" abstractly. Neither surfaces that the project *already shipped the exact fix* — weighted-by-provenance aggregation — for the sibling per-agent metric, and Phase 4 free-designs a parallel metric without wiring to it.

*Note on the two demoted fusion candidates:* f-028 (pilot >=3 precedent collides with Rule-6 pilot N) and f-032 (dual-purpose failure_mode field) were probed as fusions but **self-demoted to convergence** because a single parent already reported both the location and the root cause (f-008 and f-023 respectively). f-030 (retention/TTL) self-demoted because it bends only storage cost, not metric meaning — fd-hydraulic (f-019) owns it alone. The fusion layer policing its own intersection-only constraint is a feature, not a loss: three of nine fusion candidates were correctly rejected.

---

## 3. Taste Calls

Five findings carry `taste != 0` (all +1). The swordsmith seed produced a cluster of three (f-020, f-021, f-022), and the round-1/2 lenses added two (f-037, f-041).

- **f-020** (`c-retry-model-copy`, raw) — *metaphor-leak.* "Phase 2 has no forge to build the tier-change onto — a naive wrapper still produces same-model retries indistinguishable from escalation." The forge framing carries the load: the plan must *replace* the model-copy behavior, not layer on it.
- **f-021** (`c-inspection-independence`, upheld) — *asymmetry.* Plan-conformance and flux-drive review must not share a gate/scoring function, or a strong review score offsets a failed criterion and the fixed-gauge inspection collapses into "the master's opinion informed by a checklist." The asymmetry (one failed criterion must defeat any review score) is the taste.
- **f-022** (`c-judgment-lint`, raw) — *metaphor-leak.* Doctrine forbids "use your judgment" steps but the lint is filed as an open question with no owner, so execution-grade plans can ship judgment steps to a sonnet executor with no calibrated judgment to fall back on.
- **f-037** (`c-fable-self-attestation`, upheld) — *form-over-function.* "treat session model == fable as the signal" is the maker self-attesting his own material grade: the whole tier-separation guarantee (Rule 3) rests on an unverified in-session variable a running model could misreport. Tagged as an open design question, not a shipped gap.
- **f-041** (`c-frontmatter-selection-surface`, upheld) — *form-over-function.* Agent frontmatter `model:` fields (751 files, zero `fable` present) are a fourth, wholly separate selection surface the routing kernel has no lever over — so "fable does planning/architecture" does not reach review-agent subagents pinned to `model: sonnet`. **Caveat: f-041's headline counts were found wrong on verify (see §Caveats); the mechanism — frontmatter as an unrouted fourth surface — holds.**

---

## 4. Convergence Spine — high confidence, low novelty

High-convergence clusters are the commodity you can *trust*: multiple lenses / rounds landed on the same node independently, so confidence is high and novelty is correspondingly low. This is the floor of the plan's problem set, not its headline.

- **`c-escalation-oscillation-cap` (4 findings, cross-tier): f-005, f-016, f-024, f-025.** The sonnet→opus→fable ladder has no code-enforced per-chain cap or terminal relief valve once fable fails, *and* (f-024) there is no substrate to cap it on — `generateID()` mints a fresh random root on every `store.Create()`, so a re-triggered task severs the escalation lineage by construction and `ListRetryChain` can't distinguish new-task from exhausted-then-re-tried. f-025 gives the minimal viable fix: a persisted `EscalationChainID` keyed on `<bead-id>:<phase>`, checked-and-incremented before every dispatch creation (retry OR fresh Create), because dispatch-chain identity provably does not survive the re-trigger. Cross-tier because it fired from reliability (retry-ladder), hydraulic, and routing-kernel lenses.
- **`c-retry-model-copy` (3 findings): f-001, f-020, f-026.** `Retry()` copies `Model: orig.Model` verbatim; `RetryPolicy` has five fields, none tier-related. "attempt 3 re-dispatches at the next tier up" needs a new code path / signature change, not an incremental extension. Three lenses, one mechanical fact.
- **`c-judgment-lint` (2): f-007, f-022.** The "no judgment-call steps" and "criterion must be machine-checkable" guarantees are both filed as cheap open questions, not Phase 3 deliverables — so the validator's plan-conformance verdict silently degrades back into judgment-based review wearing a checklist.
- **`c-go-resolver-divergence` (2): f-012, f-013.** The bash fast-path and Go router will silently diverge on fable resolution the moment either is touched without the other; nothing specifies how `CLAVAIN_RUN_ID` propagates to nested subagent/background/codex-delegate dispatches, so the Go path (no agency-override support) can resolve a different model and `routing_decisions` records a plausible value with no divergence signal.
- **`c-fable-clamp-universality` (2): f-017, f-038.** The fable→opus clamp is committed only for top-level session detection; f-038 hardens f-017 from "unconfirmed" to "structural" — at least three independent paths reach a dispatch Model field with zero floor clamp by construction (`ResolveDispatchTier` bare map lookup, `ic dispatch spawn --model` raw CLI flag, `CLAVAIN_MODEL` env injection). Low-risk *today* only because `dispatch.tiers` holds Codex IDs — latent the moment a Claude tier alias is added.

---

## 5. Live Disagreements

One disagreement arose and was **resolved by adjudication**.

**f-040 vs f-011 — tier-0 floor semantics (RESOLVED: f-040 refuted).**
f-040 (`fd-routing-kernel-mechanics`, round 2) claimed a *directional split*: that Go-side `applyFloor` treats `TierUnknown` as "skip the floor comparison" (fails **OPEN** / unclamped), while the bash side, by numeric comparison (`model_tier=0 < any real floor`), clamps fable **DOWN** to the floor — a fail-open/fail-closed asymmetry that would make a manual test of the fallback path pass by coincidence while the general "fable + floor set" case is wrong. This directly disagreed with f-011's verified "clamped to floor" verdict.

**Resolution:** the verifier executed *both* resolvers' floor logic and found they **clamp identically** for an unrecognized *model* — f-040's "fails open" read of Go `applyFloor` was wrong. The fail-open path only fires when the **floor** itself is an unrecognized string, not when the *model being clamped* is. f-011 stands; f-040 is refuted.

**What the resolution teaches.** The fused/deepen probes *can be wrong* — f-040 was a plausible, well-evidenced, high-scored probe (it carried risk 9 at triage) that asserted a code behavior the verify layer disproved by execution. The value is not that the probe failed but that **the verify layer caught it before it reached synthesis**. A deepen probe reading code semantics off a grep is a hypothesis; only executing both resolvers settled it. This is the loop's one refutation and it landed on exactly the kind of finding — a confident directional-asymmetry claim about a safety clamp — where being wrong would have been most expensive.

---

## Appendix — Spice Trail

### Round 0 — seed (2 tiers, 5 lenses)
Seeded five base lenses across two adjacency tiers: `fd-escalation-retry-ladder`, `fd-eval-calibration-metrics`, `fd-routing-kernel-mechanics` (adjacent), `fd-hydraulic-diversion`, `fd-swordsmith-transmission` (distant). **Yield 15, novel_cluster_rate 0.83.** Established the problem floor: retry-model-copy, escalation-oscillation-cap, go-resolver-divergence, and the f-011 fable→tier-0 clamp (the verified max-risk base finding). High novel-cluster rate because five disjoint domains hitting a greenfield plan each opened new clusters.

### Round 1 — DEEPEN + 2× FUSE + STEER-WIDE (rate 0.83 ≥ 0.6)
Directives (from `round-1-directives.json`):
- **DEEPEN** `c-escalation-oscillation-cap` via `fd-routing-kernel-mechanics` (weight 0.3) — chosen because f-005+f-016 sat at risk 6, cross-tier convergent, but unverified; the directive wanted to confirm against retry.go/dispatch.sh mechanics and sharpen the guard design. *Yielded f-024/f-025 — the "no substrate to cap" sharpening and the EscalationChainID fix.*
- **FUSE** `fd-eval-calibration-metrics` × `fd-hydraulic-diversion` (weight 0.3) — shared_heat 2 (both fired on §Phase 4), complementarity 1 (accumulation/cadence in eval's blind spot), redundancy 0. *Produced the gauge-siltation lens → f-027 (the loop's top finding) and f-029.*
- **FUSE** `fd-escalation-retry-ladder` × `fd-swordsmith-transmission` (weight 0.2) — shared_heat 2 (§Phase 2), complementarity 1, redundancy 1 (c-retry-model-copy) → score 2. *Produced the lesson-transport lens → f-031 (tied-top) and f-033.*
- **STEER-WIDE** (weight 0.2) — justified because novel_cluster_rate 0.83 ≥ 0.6, "widening still pays." Added `fd-assay-hallmark` → f-034/f-035/f-036/f-037, the custody/provenance axis.

**Yield 8, novel_cluster_rate 0.57.** Rate dropped below the 0.6 widening threshold — the plan's novel-cluster space was starting to fill. But the two fusions delivered the four highest-heat emergent findings of the run, validating the FUSE-over-widen weighting.

### Round 2 — DEEPEN + FUSE; STEER-WIDE skipped (rate 0.57 < 0.6)
Directives (from `round-2-directives.json`):
- **DEEPEN** `c-fable-clamp-universality` via `fd-routing-kernel-mechanics` (weight 0.4) — f-017 was risk 6, single-lens, unverified; directive wanted the actual call sites enumerated. *Yielded f-038 (three unclamped paths, structural) and f-039 (escalation-clamp-bypass), and — critically — f-040, the one refuted probe.*
- **FUSE** `fd-eval-calibration-metrics` × `fd-assay-hallmark` (weight 0.6) — shared_heat 2 (§Phase 3 + §Phase 4), custody/provenance in eval's blind spot, redundancy 0: "the metrology-of-the-validator intersection." *Produced the custody-attribution lens → f-042 (orphaned BlobHash) and f-043 (orphaned source_weight).*
- **STEER-WIDE skipped** — novel_cluster_rate 0.57 < 0.6, widening no longer pays. Correct call: round 2's two directives concentrated budget on deepening and one high-value fusion rather than seeding cold lenses into a filling space.

**Yield 4, novel_cluster_rate 0.67.** Note the rate *recovered* to 0.67 — the custody fusion opened two fresh emergent clusters (`c-orphaned-custody-hash`, `c-pilot-provenance-weighting`). The space was **not** dry.

### Halt — BUDGET (not dry)
The loop halted on **BUDGET**, not exhaustion. Budget total 15, spent 14, remaining 1 — below the `round_cost_floor` of 3, so a fourth round could not be funded. **Yield was still 4 and novel_cluster_rate was 0.67** when the loop stopped. The gain history (15 → 8 → 4) is decaying but never hit zero; the round-2 rate recovery is direct evidence the target was **not dry**. A funded 4th round — most plausibly a DEEPEN on the round-2 custody findings plus a FUSE pairing `fd-assay-hallmark` × `fd-routing-kernel-mechanics` (the forged-punch-as-attribution-axis intersection the custody lens gestures at but its parents couldn't reach) — would very likely have found more. This is a budget stop mid-vein, not a mined-out one.

### Gain history
| Round | Yield | Novel-cluster rate | Directives |
|---|---|---|---|
| 0 | 15 | 0.83 | seed: 5 base lenses, 2 tiers |
| 1 | 8 | 0.57 | DEEPEN oscillation-cap · FUSE gauge-siltation · FUSE lesson-transport · STEER-WIDE assay-hallmark |
| 2 | 4 | 0.67 | DEEPEN clamp-universality · FUSE custody-attribution · (STEER-WIDE skipped) |

---

## Caveats

- **BUDGET halt with non-dry yield.** The loop stopped on budget floor (1 slot < floor 3), not exhaustion. Round-2 yield was still 4 with novel_cluster_rate recovering to 0.67. A 4th round would very likely have surfaced more novelty×risk — treat this synthesis as a mid-vein cut, not the full seam.
- **13 findings remain raw, below the verify gate.** They are unverified and excluded from all five ranked views (they appear only in cluster membership counts). Notable raw findings by heat: f-020 (metaphor-leak taste, retry-model-copy), f-022 (judgment-lint taste), f-004/f-016/f-017 (later hardened by verified successors f-024/f-038, but the round-0 originals themselves stayed raw), f-026, f-028, f-030, f-032. Do not action a raw finding without verifying it first.
- **f-041's headline counts were found wrong on verify.** The specific file counts / distribution in the claim did not hold up, but the underlying mechanism — agent frontmatter `model:` fields are a fourth selection surface the routing kernel has no lever over — is sound. Trust the mechanism, re-count before quoting numbers.
- **One refuted probe (f-040).** A confident, well-scored round-2 directional-asymmetry claim about the safety clamp was disproved by executing both resolvers. Included here only as the resolved-disagreement party; it is not an actionable finding.
