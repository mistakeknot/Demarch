---
artifact_type: melange-synthesis
method: flux-melange
target: docs/brainstorms/2026-07-18-goal-native-cycle-brainstorm.md
target_description: "Brainstorm doc — goal-native Clavain/intercore cycle redesign: formation ritual + first-class Goal entity"
goal: "Find the best architecture for a goal-native Clavain/intercore cycle built around a collaborative goal-formation ritual and a first-class intercore Goal entity that contains runs; PRIORITY 1 — surface and score terminal-gate shapes beyond the three candidates in the doc, honoring that sessions close often while goals span many runs and the successor-proposal doctrine needs enforcement somewhere."
weights: balanced
rounds_run: 6
halt_reason: DRY
total_fusions: 1
emergent_findings: 3
runtime: claude
date: 2026-07-18
---

# Eye of Distance — Goal-Native Cycle Redesign

Six rounds (0–5), ten lenses (eight base, one fusion, one adjudicator), 32 findings logged, 28 upheld, 2 refuted, 2 left raw. The loop halted **DRY**: round 4 yielded 2 findings at a novel-cluster rate of 0.40, below the widening threshold, with no open disagreements remaining after the round-3/round-4 adjudications closed.

Scores below are **re-scored from the merged ledger**, not the per-round triage estimates. Two corrections matter: I lifted **f-012** from novelty 2→3 (it does not restate f-011; it reclassifies an *elicitation-quality* gap as a *terminal-gate integrity* gap — a genuine cross-frame move that changes what the finding is about), and I confirmed **f-016** as the argmax at heat 27. Everything is ranked by **HEAT = novelty × risk.product**.

The spice of this run is not the concurrency bugs — those are real but commodity-grade once named. The spice is that **five independent lenses, from distributed-transactions to Islamic endowment law to luni-solar calendars, all converged on the same structural void: the redesign has no standing party, and no independent clock, that owns a Goal between the sessions that touch it.** The doc treats that as a sequencing choice among three terminal-gate candidates. Every non-orchestration lens treats it as a missing role. That reframe is the headline.

---

## If you read one thing

**f-016 — The successor-proposal doctrine has no standing auditor. (heat 27, argmax; waqf lens)**

Every terminal-gate candidate in the doc — and every additional shape PRIORITY 1 asked to be surfaced (lease/heartbeat, escrowed close, successor-proposal-as-obligation-object) — locates the successor-proposal obligation *inside the same execution path as the closing session*. `next-goal`'s only trigger is the goal-cadence Stop-hook tier firing within the closing session's own turn (`auto-stop-actions.sh:135-146`; `SIGNALS == *goal-completed*`). No batch, cron, or kernel-level sweep exists anywhere in the repo — confirmed absent from `core/intercore/internal/sentinel` and the entire `hooks/` directory — that audits Goals after the fact for "closed without a logged successor-proposal." If the tending session dies between goal-fulfilled and next-goal-fired, the obligation evaporates with nothing positioned to notice.

The waqf lens names precisely what is missing: the *nazir*, the supervisory office bound to catch neglect **between** account-renderings. The doc's own Open Questions flag enforcement as unresolved but frame it as *"which of the three candidates sequences it best."* That framing is the defect. The successor-proposal is not a sequencing problem downstream of a terminal gate; it is a **role that does not exist in the design**. No terminal-gate shape can enforce a mandatory obligation from inside the transient party that owes it — the enforcer must outlive the administrator. This is the anti-abandonment lever the whole redesign is meant to be, and it is currently wired to the one actor guaranteed to be gone when it matters.

---

## 1. Novelty × Risk Frontier

The strict Pareto front on (novelty, risk.product) collapses to the two apex findings **f-012** and **f-016** (both nov 3 / risk 9), which dominate every other point on both axes. That degenerate front hides the trade-off shape the brief asks for, so I present the apex pair **plus the two archetype leaders** the frontier is meant to expose — a max-novelty/mid-risk lead and a mid-novelty/max-risk lead. All four lead; none is dominated once you fix an axis.

### Apex — both axes maxed

**f-016 · nov 3 / risk 9 · heat 27 · `fd-waqf-perpetual-trust`**
See "If you read one thing." Risk decomposition: **blast 3** (the successor-proposal *is* the anti-abandonment doctrine — the stated point of the whole cycle redesign), **likelihood 3** (the doc itself asserts sessions close far more often than goals; the death-mid-window case is not a corner case, it is the modal case over a goal spanning many runs). Severity P0 *(reference only)*.

**f-012 · nov 3 / risk 9 · heat 27 · `fd-orchestration-terminal-consistency`**
The C2/C3 melange-coverage gap is not merely an elicitation shortfall — it is a **terminal-gate integrity gap**. The unvalidated completion-condition string (f-011) is the *sole trigger* for the kernel-gated close sequence under candidate (a), and C2/C3 — the likely majority tier — gets neither a melange pass nor any other check on it. A malformed condition string reaches the terminal sequence's trigger point with zero validation of any kind. Risk decomposition: **blast 3** (drives verify-against-charter → reflect+compound → successor-proposal for the majority of goals), **likelihood 3** (line 40 assigns ceremony depth only to C1 and C4/C5; C2/C3 are structurally present in the C1–C5 metric but never assigned a check anywhere in the text). Severity P1 *(reference only)*. **The re-score lifts novelty to 3**: this is the finding that turns "the interview could be sharper" into "the close fires on an unchecked string," which is a different claim than its parent f-011.

### Max-novelty / mid-risk lead

**f-019 · nov 3 / risk 6 · heat 18 · `fd-liminal-rite-passage`**
Intercore *already contains* two tested, durable single-point-of-no-return primitives — `sentinel.Store.Check` (DB-transactional atomic claim) and `lock.Manager` (filesystem lease with `Stale()`/`Clean()` staleness+heartbeat and dead-PID reaping, exercised by `TestGhostLockCleanup`). These are mechanistically the "lease/heartbeat model" PRIORITY 1 asked to be surfaced, and the terminal-gate open question proposes new shapes from scratch while **citing neither**. `auto-stop-actions.sh:142` already calls the sentinel one hook-tier above the terminal-trigger code, for an unrelated purpose — the primitive is one hop away and unused for this problem. Risk decomposition: **blast 3** (choosing a terminal-gate mechanism ignorant of existing prior art risks re-inventing a worse one, or worse, reaching for the wrong existing one — see f-023), **likelihood 2** (the design round would plausibly have surfaced these eventually, but the doc as written does not). This is the highest-novelty finding that is *not* an apex: it is the one that hands the melange candidate list a concrete anchor instead of a blank page.

### Mid-novelty / max-risk lead

**f-020 · nov 2 / risk 9 · heat 18 · `fd-liminal-rite-passage`**
The only party that confirms a goal's terminal condition was met is the **same Haiku evaluator / session that ran the loop being judged**. For C1–C3 goals (the likely majority per the settled melange-coverage gap) there is no second-party check at all — unlike the *formation* ritual, which explicitly requires a second party (agent + user) before ratification. The design is asymmetric: it witnesses birth but not death. Line 13's evaluator "judge[s] it from surfaced output" — a self-report constraint on the loop's own output, not an external-witness constraint. Risk decomposition: **blast 3** (an unwitnessed close is the failure the whole Goal-entity is meant to prevent — a goal marked done by the only party with an incentive to mark it done), **likelihood 3** (the majority tier has, by the doc's own routing, no external witness). This is the mid-novelty/max-risk lead: the *concept* (self-judging close) is not exotic, but the risk is maximal and the asymmetry-with-formation is the sharp edge.

*Companion max-risk points on the front, same (2,9) shoulder:* **f-001** (candidate (a) names no lock/lease/single-writer, so two sessions can each independently kernel-gate the terminal sequence — the raw concurrency root) and **f-023** (the adjudicated verdict: `sentinel ≠ lock.Manager`, and a by-analogy design reaching for "the primitive already in the goal-cadence path" reaches for the sentinel, which *cannot* serve as a lease). Both are commodity-confidence (see Convergence Spine) but sit on the risk apex.

---

## 2. Top Fusions

One fusion pair was attempted — `fd-orchestration-terminal-consistency × fd-liminal-rite-passage`, fused as **`fd-fused-witnessed-transaction`** (witnessed-transaction: a status crossing that is simultaneously a fenced/idempotent/compensable transaction AND a witnessed three-phase rite). It produced **three emergent findings**, all upheld. Ranked by heat:

**f-025 · nov 3 / risk 6 · heat 18 — un-fenced double-witness**
`lock.Manager`, intercore's one candidate lease/heartbeat primitive, has **no fencing/generation token** and a **5-second default staleness window** (`DefaultStaleAge = 5 * time.Second`) against a terminal sequence that necessarily spans multiple LLM calls (verify-against-charter → reflect+compound → successor-proposal). A stale-lock break *during* that sequence lets two officiants each complete a fully witnessed, file-written close of the same Goal with no ledger of which is canonical.
*Intersection justification:* pure transaction analysis would generically say "add a fencing token" without knowing intercore's specific lease candidate already lacks one. Pure rite analysis has no way to know `StaleAge` defaults to 5 seconds against a multi-call sequence, so it could not connect "interrupted rite" to this concrete constant. Only the fused reading — transactional fence-absence PLUS rite double-witnessing of the same subject — explains why the break-and-reacquire *looks* serializable (one `Mkdir` wins at a time) yet produces two independently witnessed reincorporations. Deleting either half collapses the finding.

**f-026 · nov 3 / risk 6 · heat 18 — the sentinel is a boolean start-gate, not a step ledger**
`sentinel.Store.Check` is a single-column (`LastFired`), session-scoped, fire-once-per-interval throttle with **no step/ordinal concept**, so naively reusing it for goal-close satisfies neither the transaction parent's per-step-checkpoint requirement nor the rite parent's witnessed-completion requirement — and its one existing call site is keyed by `$SESSION_ID`, not goal ID.
*Intersection justification:* the transaction parent alone, on learning the sentinel exists, would propose reusing it and stop. The rite parent alone has no visibility into Go source to know the struct lacks a step column. Only reading both frames against the actual struct shows the missing column is *simultaneously* the transactional checkpoint gap and the ritual witnessed-completion gap — and that the session-scoped keying would additionally miscount cross-session goal mutual exclusion. This is the fusion that connects f-013's abstract "doc vs. fields" split to a specific struct definition.

**f-027 · nov 3 / risk 4 · heat 12 — the obligation-object shape inherits the fence gap one level down**
The successor-proposal-as-separate-obligation-object shape (a PRIORITY-1 candidate) relocates the fencing requirement onto a **new object's CREATE step** without inheriting any mechanism to enforce single-witness creation. Two sessions reaching terminal conditions near-simultaneously can each independently create an obligation record — reproducing the double-witness defect one level down.
*Intersection justification:* the transaction parent alone asks a generic "is create-obligation idempotent." The rite parent alone asks "is the obligation witnessed." Scoring this candidate requires both — recognizing it as a rite object (the mandatory successor-attestation) AND its creation as a transaction needing the same single-writer guarantee the terminal sequence itself needs. This is the finding that stops the obligation-object shape from being mistaken for a clean fix to f-016.

**Fusion yield: 3 emergent from 1 attempted** — a strong return. The pair was well-chosen (shared_heat 2, complementarity 2, redundancy 1 per the round-3 FUSE directive). No fusion produced a negative result; the single attempt was productive across all three of its findings.

---

## 3. Taste Calls

Taste signal in this run is thin — the corpus is dominated by structural-correctness findings, not elegance/smell calls. Two +taste elegances surfaced; no −taste smells cleared verification.

**+taste (asymmetry) · f-008 · `fd-elicitation-ritual-design`**
The "recommended option first" interview ordering runs against the ritual's own stated comparative-advantage premise (the user's judgment should steer selection), with no feedback loop to detect anchoring drift — **despite the project already owning a directly reusable pattern**: `interspect:calibrate-audit` implements "compare current ranking vs a snapshot from N days ago, flag drift" as a first-class pattern elsewhere in this same codebase. The taste call is the *asymmetry*: an anchoring counter-measure exists, is proven, and is unapplied. Preserve the instinct here — the fix is not new machinery, it is wiring an existing audit into the ritual's ordering slot. (Note the countervailing read from the lens's own failure_mode: at C1, one confirming question by design, some anchoring is an intentional tradeoff, not a defect — so scope this fix to C2+.)

**+taste (simplicity) · f-018 · `fd-waqf-perpetual-trust`**
The charter's founder-authored acceptance criteria are framed as binding every subsequent run, but the doc never states whether they are editable after ratification, nor what re-ratifies them (a second melange pass, a silent unilateral patch by whichever run notices a gap, or a wholly new Goal). The taste call is *simplicity*: the waqf frame says the founder's *shurut* are irrevocable and any mutation requires fresh ratification by the court — a clean, single rule (amendment = re-ratification at the tier the original required) closes the gap without new machinery. The smell to avoid is the implicit third option — silent unilateral patch by whichever run notices — which would let the binding condition drift with no witness, a −taste outcome the design should foreclose explicitly.

No −taste smell survived verification as a standalone finding; the closest, f-013/f-021 (charter doc vs. kernel fields as two un-reconciled attestation artifacts), is scored as a correctness gap, not an elegance smell, and lives in the convergence spine.

---

## 4. Convergence Spine

High-convergence findings are **high-confidence, low-novelty commodity** — the things you can trust without re-verifying, precisely because more than one lens (or an adjudication pass) landed on them independently. Four cross-lens convergent clusters:

- **Terminal-close checkpointing** (`c-terminal-close-checkpointing`: f-002 + f-026). The Goal's close evidence is coarse ("accumulates close evidence") with no per-step completion record — a crash mid-sequence is unrecoverable and indistinguishable from not-started. The orchestration lens flagged it abstractly (f-002); the fusion lens (f-026) grounded it in the sentinel's single-column struct. Backed by a *live precedent*: `sprint.md:463` documents Step 7 and Step 9 both passing `shipping` as `currentPhase` under one shared key, causing silent double-recording (Sylveste-84sv, partial fix only). **Trust this: the checkpoint gap is real and already has a production analogue.**

- **Charter-evaluator validation gap** (`c-charter-evaluator-validation-gap`: f-007 refuted → f-011 CONFIRMED). The ritual states the Haiku-evaluator / surfaced-output-only / ≤4000-char constraint precisely (line 13) but describes **no step, at any stakes tier including C4/C5 melange, that validates a drafted completion condition against that constraint before ratification**. A charter can pass full C5 melange while its condition string is still malformed for Haiku, because melange reviews charter *substance* (scope, acceptance criteria, adjacent-work verdicts), not the condition string's fit to the built-in's judging contract. Note: f-007 was **refuted** and re-issued as the CONFIRMED f-011 after a DEEPEN pass — the confirmation is the trustworthy artifact.

- **Charter doc / field sync gap** (`c-charter-doc-field-sync-gap`: f-013 + f-021). The doc's own open question (line 48) admits melange may review *the doc* while the kernel gates on *the fields* — two objects with no reconciliation step, so even a full melange pass may not validate the literal condition string handed to `/goal`. Two lenses, same conclusion; f-021 left raw but its convergent parent f-013 is upheld.

- **Lock-manager no-fence / double-witness** (`c-lock-manager-no-fence-double-witness`: f-025 + f-029). The fusion (f-025) and the round-4 adjudication (f-029) independently land that even `lock.Manager` — the *correctly* identified lease-shaped primitive — has no fencing/generation token and only a 5s staleness window, so pointing at it as prior art is *necessary corrective guidance but not sufficient design guidance*. f-029 left raw; its convergent parent f-025 is upheld and emergent.

Adjacent commodity-grade (single-lens but adjudicator-confirmed, high-confidence/low-novelty): **f-023 / f-028** (`sentinel ≠ lock.Manager`; the by-analogy risk is that a naive lease design reaches for the Stop-hook-wired sentinel, which cannot serve as a lease) and **f-001** (candidate (a) names no single-writer mechanism). These are the load-bearing facts the melange candidate list must not get wrong.

---

## 5. Live Disagreements

**None open at halt.** Two contradictions were raised and both closed by adjudication before DRY:

- **f-015 vs f-019** (round 2): the waqf lens (f-015) claimed the sentinel is intercore's only liveness-adjacent primitive and is a throttle, not a lease; the rite lens (f-019) claimed intercore has *two* durable lease/heartbeat primitives (sentinel + `lock.Manager`). **Adjudicated by f-023 (round 3):** f-015's claim (2) holds — the sentinel is a pure interval-throttle with no owner/PID/release semantics. f-019's claim (1) contained a *bundling error* — only `lock.Manager` qualifies as a genuine lease; the sentinel does not, and lumping them together overstates the sentinel's fitness. The narrowing insight the contradiction exposed (f-024): even `lock.Manager` alone is not a drop-in fit — it is process-local (`/tmp/intercore/locks`, 5s staleness, local `pidAlive`), tuned for short command-level mutual exclusion, not a goal spanning runs/sessions across machines and days.

- **Re-adjudicated at round 4** (f-028): confirms f-023's verdict holds and explicitly rules that f-019's *narrow* point — a real, tested lease primitive already exists unreferenced in the doc — **survives and should carry into the melange candidate list**, while its *broad* bundling is discarded. This is a clean resolution: the useful half of the disputed finding is promoted, the erroneous half is retired.

The absence of open disagreement at halt is a genuine signal, not an artifact of under-probing: the two PROBE-DISAGREEMENT directives (rounds 3, 4) each fired and closed their target. The design space's contested region was the sentinel-vs-lock question, and it is settled.

---

## Appendix — Spice Trail

| Round | Event | Yield | Novel-cluster rate | Directive(s) & why | Steered where |
|---|---|---|---|---|---|
| 0 | assay | 10 | 1.00 | initial fan-out, 2 agents | orchestration-terminal-consistency + kernel-phase-migration + elicitation-ritual — the doc's three named axes |
| 1 | probe→assay | 8 | 0.88 | **DEEPEN** `fd-orchestration-terminal-consistency` (risk 6, unconfirmed — confirm or refute); **STEER-WIDE** `fd-waqf-perpetual-trust` (novel-cluster rate 1.00 ≥ 0.6, widening still pays) | DEEPEN converted f-007→f-011 (confirmed); STEER-WIDE opened the waqf frame that produced the argmax f-016 |
| 2 | probe→assay | 4 | 0.50 | **STEER-WIDE** `fd-liminal-rite-passage` (rate 0.88 ≥ 0.6) | rite lens surfaced f-019 (the existing-primitives finding) and f-020 (unwitnessed close) — and set up the round-3 disagreement |
| 3 | probe→assay | 5 | 0.80 | **PROBE-DISAGREEMENT** (f-015 vs f-019 contradiction — adjudicate); **FUSE** `fd-fused-witnessed-transaction` (shared_heat 2, complementarity 2, redundancy 1) | adjudication produced f-023/f-024; the fuse produced all 3 emergent findings (f-025/f-026/f-027) |
| 4 | probe→assay | 5 | 0.40 | **PROBE-DISAGREEMENT** (re-adjudicate — closes to f-028); **STEER-WIDE** `fd-calendrical-intercalation` (rate 0.80 ≥ 0.6) | re-adjudication confirmed f-023 and promoted f-019's narrow half; calendrical lens added the independent-clock / epact frame (f-030/f-031/f-032) |
| 5 | halt | — | — | **DRY** | round-4 rate 0.40 < 0.6 widening threshold, yield 2, no open disagreements → stop |

**Fusion stats:** 1 attempted, 3 emergent (100% of the single pair's findings were productive).
**Gain history:** yields 9→6→2→4→2 (note the non-monotone bump at round 3 — the FUSE + PROBE-DISAGREEMENT double-directive re-inflated yield before the round-4 decline to DRY).

### Caveats

- **Two findings left raw, not upheld.** f-021 (charter storage → two attestation artifacts) and f-029 (lock.Manager still no fence even when correctly substituted) were logged at `status: raw` — their convergent parents (f-013, f-025 respectively) *are* upheld and carry the claim, so the substance is surfaced, but the raw findings themselves were not independently re-verified before halt. They appear in the convergence spine as parent-backed, not as standalone verified findings.
- **Two findings refuted, correctly excluded.** f-007 (re-issued as the CONFIRMED f-011) and f-017 (terminal-gate has no C-tier stakes-routing — refuted; the claim over-read the doc). Neither appears in any of the five views.
- **Regions never reached.** Two base lenses — `fd-tidalsediment-accretion` (estuarine settling/consolidation dynamics) and `fd-timberjoinery-loadpaths` (fastener-free joinery / reversible load paths) — were defined but **dispatched zero findings**. The sediment lens's residence-time / consolidation frame (does close-evidence have slack to settle before the next session flush?) and the joinery lens's reversibility frame (is the interphase-retirement seam cut on the load-bearing member, with a known withdrawal sequence?) are genuine unexamined angles. If a further round is ever run, these two are the widening candidates — the interphase-retirement question (f-005) in particular is exactly a joinery load-path problem the joinery lens never got to score.
- **No failed probes.** All directives across rounds 1–4 fired successfully (spice trail `failed: 0` throughout). No budget-clamped verification — the adjudicator ran twice with full code-reading access.
- **The whole run is doc-plus-code static analysis.** No terminal-gate mechanism was prototyped or run; the concurrency findings (f-001, f-025, f-026, f-027) are read off struct definitions and call sites, not observed under a race. The failure modes are *demonstrable-from-source* but not *demonstrated-under-load* — a prototype race test (two sessions, same goal, near-simultaneous close) would move f-025 from PLAUSIBLE-from-code to CONFIRMED-under-load.
