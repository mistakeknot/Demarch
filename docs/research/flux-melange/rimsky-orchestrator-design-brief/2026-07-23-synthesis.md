---
artifact_type: melange-synthesis
method: flux-melange
target: docs/brainstorms/2026-07-23-rimsky-orchestrator-design-brief.md
target_description: >-
  Rimsky — N-parallel flat-fan-out sprint orchestrator design brief (epic sylveste-3kol),
  consuming the shipped worktree-first contract; 6 open architecture questions on subsumption
  (lbkd, Mycroft), isolation crossover, controller gating, pre-spawn check cost, and the
  anti-abandonment scope-cut.
goal: >-
  Find the best architecture and scope-cut for Rimsky. Priority 1: resolve the two subsumption
  calls (Q1 lbkd, Q2 Mycroft) that change scope and sequencing. Then stress-test Q3 isolation
  crossover, Q4 controller-as-dead-code, Q5 pre-spawn check cost, Q6 anti-abandonment cut.
  Honor the three near-decided constraints (flat depth-1 fan-out, pre-dispatch cost gate,
  telemetry-as-instrument) as inputs to build on, not to re-litigate.
weights: balanced
rounds_run: 4
halt_reason: DRY
total_fusions: 0
emergent_findings: 1
runtime: claude
date: 2026-07-23
---

# Rimsky orchestrator design brief — melange synthesis

The loop ran four rounds (0–3) against seven lenses and halted DRY: round 3 produced
zero new clusters and zero novel yield. What it surfaced is not a set of design answers
but a set of **broken premises the brief is standing on** — most of the brief's "open
questions" are asked against a substrate that does not exist as described, or already
exists shipped one door over. The single highest-conviction result is that the entire
telemetry-and-cost-gate spine (constraint 3, Q4, the v1 cut) reads from a `dispatch_log`
that is **not built**: every lens that touched it landed on the same finding independently.
That is the commodity you can trust. The spice is elsewhere — in the crossover the brief
asks the orchestrator to compute but a shipped rule already answers, in a fan-out
eligibility precondition invisible to every subsumption reading, and in a safe-abort gap
that one lens invented, another confirmed, and a third partially refuted in the same run.

Findings are ranked by **heat = novelty × risk.product** throughout, re-scored by hand over
the merged ledger (per-round scores were fast triage estimates). Refuted findings — the
change-ringing lens's original `pause --drain` characterization (f-002/r1) and its
dispatch-claim-race framing (f-003/r1) — do not appear in any view below.

---

## 1. Novelty × Risk Frontier

The Pareto front on (novelty, risk.product) among upheld/raw survivors has two visible
corners plus a mid-knee. Both leads below are on the front; neither dominates the other.

### Lead A — max-novelty / mid-risk: the cost gate has no reservoir to read

**f-014** · novelty 3 · risk.product 4 (blast 2 × likelihood 2) · heat 12 · lens
`fd-canallock-flowregulation` · status raw

> The pre-dispatch cost gate (§3.2c) never names a **live signal** — rate-limit headroom,
> current session spend — that it reads before pricing the token multiplier. It can only
> ever price *the multiplier's existence*, never *the current budget's ability to afford it*.

This is the highest-novelty finding on the front and the canal-lock lens at its sharpest:
the gate is specified as a formula (task-count × multiplier) with no reservoir-level input,
so it answers "is this fan-out N× more expensive than serial?" but never "can we afford N×
right now?" `MAX_CONCURRENT` is confirmed static/advisory (§3.1), not a dynamically-read
reservoir. A cost gate that cannot see the reservoir will greenlight a wide fan-out that
exhausts the rate budget mid-run — the exact failure the gate exists to prevent.
**Risk decomposition:** blast 2 (bounded to the cost-decision path, not correctness),
likelihood 2 (only bites when the budget is already near a limit) — severity P1 for reference.
The novelty is what earns its place: no other lens saw that the gate prices a *ratio* when
the constraint it must honor is an *absolute level*.

### Lead A′ — co-max-novelty / mid-risk: three timbers can't be cut yet (emergent)

**f-008** · novelty 3 · risk.product 4 (blast 2 × likelihood 2) · heat 12 · lens
`fd-timberframe-joinery` · status **upheld** · new cluster

> The collision map treats `sylveste-bzy` as optional cleanup ("may require this first"),
> but 3 of 5 dual-tracked interverse plugins (interfer, intersight, interseed) still exist
> as **two competing canonical timbers at once** — monorepo-embedded AND independently
> published. Rimsky's per-nested-repo fan-out rule (its "hardest correctness constraint")
> cannot resolve *which repo to isolate* for those three until bzy closes.

The joinery lens alone caught this: a timber that belongs to two competing frame drawings
cannot be cut to a single joint face. Rimsky's fan-out eligibility rule *assumes* every
candidate has one unambiguous isolation boundary; for three live plugins it has two, so
"which repo do I worktree-isolate" has no answer. This is a **hard precondition**, not a
nice-to-have: `sylveste-bzy` is a blocking dependency for correct fan-out over those
plugins, and the brief demotes it to a parenthetical. **Risk decomposition:** blast 2
(three specific plugins, silently mis-isolated), likelihood 2 (only when a fan-out
touches one of the three) — P1 for reference. Verified live: bzy is open/P2, interhelm +
intercut resolved via the closed cpd, the other three deliberately left dual-tracked "to
avoid a large unilateral untrack mid-goal."

### Lead B — mid-novelty / max-risk: the Q3 crossover figure is fabricated

**f-005** · novelty 2 · risk.product 6 (blast 2 × likelihood 3) · heat 12 · lens
`fd-isolation-cost-control-economics` · status raw

> §5 Q3's "~200–500ms + disk per worktree" figure is attributed to
> `docs/guide-worktree-first-coordination.md`, but that document contains **no numeric cost
> claim anywhere**.

This is the max-risk-with-real-novelty lead. Q3 asks the orchestrator to compute a
worktree-vs-interlock crossover width; the *only* number feeding that crossover is invented
and mis-attributed to the shipped contract. Verified: grepping the full contract for
ms/cost/second/disk/setup returns a `worktree-setup.sh` retirement note and a TOC line —
no timing or disk figure. **Risk decomposition:** blast 2 (the whole Q3 crossover analysis
rests on it), likelihood 3 (the figure is load-bearing and used the moment anyone tries to
compute the crossover) — P0 for reference. It sits a notch below the pure-risk corner
(the dispatch-log cluster at risk 9) but carries novelty 2 where those carry 0, which is
why it leads instead of them.

**The pure-risk corner** (f-001 / f-006 / f-013, all risk.product 9, novelty 0) is the
dispatch-log fabrication. It is the single most consequential finding in the run but it is
zero-novelty commodity — every lens converged on it — so it leads the **Convergence Spine**
(§4), not the frontier. Do not mistake its absence here for low importance; it is the
opposite.

---

## 2. Top Fusions

**Fusions attempted: 0. Emergent findings: 1.**

No hybrid intersection-detector lens was spun up in this run (fusion_stats.attempted = 0).
The loop's cross-lens work was instead an **adjudication pass** in round 3 — a fusion-kind
record (`adjudication`) that operated over the contested `c-safe-abort-primitive-missing`
cluster to settle a factual dispute between findings, not to synthesize a new hazard from a
lens pair. Report the pairs that *could* have fused but did not:

- **`fd-isolation-cost-control-economics` × `fd-canallock-flowregulation` — independent here.**
  Both touched the cost gate (f-005/f-007/f-008 vs f-013/f-014) but on non-overlapping
  facets: the economics lens on the crossover math and check cost, the canal-lock lens on
  the missing reservoir signal. No intersection hazard emerged that needed both; they
  partition the cost surface rather than intersecting on it.

- **`fd-orchestration-subsumption-topology` × `fd-timberframe-joinery` — independent here.**
  Both read Q1/Q2 subsumption, but topology found the *ownership* gap (dispatch-log
  double-posting, f-010/r2 → cluster c-1) and joinery found the *fit* gap (bzy dual-tracking,
  lbkd splice defect). These are the two lenses' declared blind spots for each other — and
  the run confirmed it: neither produced a finding the other couldn't, so no fusion fired.

### The one emergent finding

**f-008 (bzy dual-tracked fan-out eligibility)** is logged as the run's single emergent
result — a new cluster (`c-bzy-dual-tracked-fanout-eligibility`) no single-facet reading of
the brief would surface. It is emergent in the sense the melange engine means: it required
holding the per-nested-repo isolation rule *and* the dual-tracking state of the interverse
plugins in the same frame, which only the joinery lens's "is each candidate a single sound
timber?" question does. It is scored in §1 as Lead A′ (novelty 3, risk 4) — the fusion view
and the frontier view intentionally both surface it, because it is both the emergent result
and a front corner.

---

## 3. Taste Calls

The ledger carries exactly one non-zero taste score across all rounds.

### -taste smell to fix

**f-007** · taste −1 · taste_kind **smell** · lens `fd-orchestration-subsumption-topology`
· status upheld

> Mycroft's `--drain` flag is **registered on the Cobra `pauseCmd` but never read** — no
> `GetBool("drain")` call, no signal-dispatch codepath anywhere in the mycroft package.
> It is a stub matching the plan doc's design intent, not working code.

Verified directly: `grep -n 'drain|Drain|GetBool'` across the whole 434-line `main.go`
returns only the registration at line 427 and help-text strings — zero conditional branches
on the flag value. `pauseCmd.RunE` (main.go:230–247) unconditionally calls `LogPause()` and
prints a message true with or without the flag. This is the classic **registered-but-unwired
flag** smell: a CLI surface that advertises a capability (graceful drain of in-flight agents)
the binary does not have. It matters here beyond cosmetics — the safe-abort thread of this
review (see §5) was partly built on treating `pause --drain` as shipped prior art Rimsky
could reuse. The smell is load-bearing: **what Rimsky can actually reuse from Mycroft is
`pause`/`resume` (stop-new-dispatch-only), not a coordinated drain.** Fix by either wiring
the flag or removing it so the next reader doesn't inherit the same false affordance.

No +taste elegance findings were logged (no finding scored taste > 0). That is itself a mild
signal: the lenses were in fault-finding mode throughout and did not pause to mark anything
in the brief worth *preserving* — a gap a human charter-author should fill, since the three
near-decided constraints (flat depth-1, cost gate, telemetry-as-instrument) are genuinely
sound and were correctly excluded from re-litigation.

---

## 4. Convergence Spine

High-convergence = high confidence, low novelty. These are commodities you can trust and
build the charter's factual base on. Two clusters dominate the spine.

### Spine 1 — The dispatch_log does not exist (4-lens convergence, the run's headline)

Cluster `c-dispatch-log-fabrication`: **f-001** (topology), **f-006** (economics),
**f-009** (anti-abandonment), **f-013** (canal-lock). Four independent lenses, each from its
own axiom set, landed on the same verified fact: the "EXISTING `/clavain:work` + `/flux-review`
dispatch log" that §3.3, §7, and bead `4b5.8` say Rimsky will "extend" **has no
implementation** — grep for `dispatch_log`, `wall_time`, `conflict_rate` across
`os/Clavain/commands/work.md` and `interverse/interflux/**/*.go` returns zero. The *only*
real `dispatch_log` schema in the repo belongs to Mycroft (Autarch), defined in the Mycroft
plan doc. Consequences, each owned by a different lens:

- **f-001 / topology:** the thing Rimsky "extends" is a fabrication; the real one is
  Mycroft's, raising the Q2 double-ownership question.
- **f-006 / economics:** Q4's controller-build decision is gated on telemetry from this log,
  so **the measurement clock cannot start** under the brief's framing.
- **f-009 / anti-abandonment:** §7 treats the telemetry piece as the cheap "extend an
  existing log" element; it is **new construction**, inflating v1's true size unflagged.
- **f-013 / canal-lock:** the cost gate is specified to read wall-time/task-sum/agent-count
  from this reservoir — the reservoir may not exist.

Risk.product 9 on the topology, economics, and canal-lock instances; novelty 0 because it is
the definition of convergence. **This is the "if you read one thing" candidate** and the
single most important input to the charter: the telemetry-first sequencing the whole v1 cut
assumes is building a new instrument, not extending one.

### Spine 2 — The epic metadata the brief describes is already stale

Cluster `c-epic-metadata-stale`: **f-002** (topology), **f-010** (anti-abandonment),
**f-016** (double-entry). Three lenses confirm the brief's §0 premise (epic `sylveste-3kol`
is "P1, empty description") is contradicted by the live bead as of the brief's own date —
`updated_at 2026-07-23T14:32:31Z` shows a populated description and three wired dependency
edges (4b5.7/4b5.8/4b5.17). f-016 adds the reconciliation nuance: the Rimsky-rename rationale
lives in the *notes* field, while bead `4b5.17`'s acceptance criterion names the
*description* field — so 4b5.17 is technically still unmet even though the human-readable
rationale exists. Low novelty (0), risk 3–6, but high confidence: a charter formed on "empty
epic, nothing done" **misjudges how much groundwork already exists**.

### Spine 3 — Mycroft is shipped prior art the brief cites only as a plan (partial convergence)

Cluster `c-mycroft-litmus-evidence-gap`: **f-004** + **f-017** (topology + double-entry).
Q2's "different layer" verdict is argued against Mycroft's *plan doc* only, not the
substantially-shipped `apps/Autarch/internal/mycroft/` code — which already has a pre-dispatch
interlock conflict check (`scheduler/conflict.go`) structurally similar to Rimsky's own Q5
mechanism, and a shipped scope constraint (v0.1 = observe/suggest-approve, no autonomous
dispatch) that makes the "different layer" verdict *easy* to reach if cited. The evidence for
Q2 exists and is shipped; the brief just doesn't cite it. Trust this as the factual base for
answering Q2: **(a) different layer is correct, and the shipped code supports it — cite the
code, not the plan.**

---

## 5. Live Disagreements

One disagreement was open at halt, and it is the most instructive artifact in the run.

### The `pause --drain` characterization (f-011 vs f-002, cluster c-safe-abort-primitive-missing)

**Location:** `apps/Autarch/cmd/mycroft/main.go:230–247, 427` (drain flag characterization).

The change-ringing lens (round 1, **f-002**) invented a genuinely novel scope gap by
isomorphism: ringing a bell up commits momentum a single actor can't instantly dump, and the
conductor's "stand the band" is the one coordinated safe-abort — Rimsky's N-parallel spawn is
the same commitment shape, yet the brief has **zero abort/cancel/drain vocabulary** for an
in-flight fan-out (the only hit is the deferred-P3 kill-rule *detection* mechanism). f-002
claimed Mycroft already ships the safe-abort as `pause --drain`.

Round 2's topology lens **confirmed the core** (f-004: brief has no abort vocabulary; Mycroft
*does* ship `pause`/`resume`) but round 2's own f-007 and round 3's adjudication (**f-011**)
**refuted the specific claim** that `pause --drain` is a working coordinated graceful-stop —
the `--drain` flag is registered but never read (see §3 taste call). The disagreement is
between "Mycroft ships a graceful drain Rimsky can reuse" (f-002, now refuted) and "Mycroft
ships only stop-new-dispatch, the drain is a stub" (f-011, verified).

**How it resolves and why it still matters.** The adjudication is factual, not a taste call,
and it lands cleanly: f-002's parent insight (the safe-abort scope gap is real; the brief
never asks whether v1 needs a way to halt a live fan-out) **survives**; only its evidentiary
sub-claim about drain dies. The *severable* conclusion the charter should adopt (**f-012**,
adjudication's remediation):

> Add an explicit Q6 sub-question: does shippable-v1 require a **stop-new-dispatch-only abort
> path** (reusable from Mycroft's `pause`/`resume`), independent of and prior to the deferred
> P3 kill-rule controller — so the v1/v2 scope cut doesn't silently ship a fan-out with no
> safe way to halt it mid-run.

This is the disagreement doing its job: an unresolved contradiction that, once adjudicated,
converts a refuted flourish into a concrete, cheap, shippable v1 requirement. The safe-abort
gap is real; the reusable mechanism is `pause`/`resume`, not `pause --drain`; and Q6 as
written asks only *build-sequencing* gates, never an *operational-safety* gate — a scope gap
(f-005/r2) confirmed by three findings in the cluster.

---

## Genuinely different orchestrator shapes (goal-directed, not in the brief)

The goal asked to surface orchestrator shapes absent from the brief and score them against
three survival tests: the **nested-repo hazard** (contract §5, per-nested-repo isolation),
the **token multiplier** (cost gate), and the **anti-abandonment doctrine** (v1 must stand
with v2 permanently absent). The lenses did not fan these out as first-class findings — a gap
in the run (see caveats) — but the ledger's shape lets me score the four named candidates:

- **Telemetry-first vs policy-first sequencing.** The run's headline (Spine 1) settles this
  in reverse: telemetry-first is what the brief *assumes*, but the telemetry instrument is
  unbuilt, so telemetry-first sequencing **fails the anti-abandonment test** — it front-loads
  new construction the brief mislabels as free, delaying every downstream gate. A **policy-first,
  instrument-second** cut (ship flat fan-out + cost gate against a *newly-built* minimal log,
  acknowledged as construction) survives all three tests and is the recommended shape.

- **Orchestrator-as-library vs orchestrator-as-command.** The brief implicitly assumes
  command (§4: route.md, /sprint, /work). Library survives the nested-repo hazard *better*
  (isolation logic callable per-repo without a session-level command boundary) and is neutral
  on cost. Not adjudicated by the lenses; flag for the charter.

- **Escrowed/staged fan-out vs immediate spawn.** Directly relevant to the safe-abort gap
  (§5): a staged fan-out (reserve → dry-fit all → commit-spawn as one gated step) makes the
  stop-new-dispatch abort trivial and survives the nested-repo hazard by dry-fitting per repo
  before any spawn. Survives the token-multiplier test only if the pre-spawn check is cheap
  (Q5, unresolved — f-007/r0 notes Mycroft's 5s-timeout prior art is uncited).

- **Event-driven vs poll.** Not reachable from the ledger; the lenses never generated a
  finding bearing on it. Genuinely unexplored — see caveats.

---

## Appendix — Spice Trail

| Round | Event | Yield | Novel-cluster rate | Directive(s) & why |
|------:|-------|------:|-------------------:|--------------------|
| 0 | assay | 1 | 1.00 | Cold assay, 2 agents dispatched. |
| 1 | probe → assay | 2 | 1.00 | **STEER-WIDE** on `fd-changeringing-conductor` — "novel_cluster_rate 1.00 ≥ 0.6, widening still pays." Widened into the change-ringing lens, which invented the safe-abort scope gap (f-002/r1). |
| 2 | probe → assay | 7 | 0.29 | **DEEPEN** on `fd-orchestration-subsumption-topology` ("risk 6, unconfirmed — confirm or refute") + **STEER-WIDE** on `fd-timberframe-joinery`. The deepen confirmed the safe-abort gap (f-004) and surfaced the drain stub (f-007); the widen produced the run's one emergent finding (f-008, bzy) plus the lbkd splice defect (f-009). Peak yield. |
| 3 | probe → assay | 2 | 0.00 | **PROBE-DISAGREEMENT** (no lens — adjudication) on the open `pause --drain` contradiction. Adjudicated f-011/f-012: confirmed the safe-abort gap, refuted the drain characterization, emitted the Q6 remediation. Zero new clusters → DRY. |

**Where steering paid.** The round-1 STEER-WIDE into change-ringing was the highest-leverage
move: it manufactured the safe-abort thread that dominated rounds 2–3, even though its
originating evidentiary claim was later refuted — the *frame* survived the *fact* dying.
The round-2 STEER-WIDE into joinery produced the only emergent finding. The round-2 DEEPEN
correctly confirmed-and-corrected in one pass (confirmed the gap, caught the drain stub).

**Halt reason: DRY.** Round 3's novel_cluster_rate hit 0.00 and yield dropped to 2 (both
adjudication housekeeping, no new hazards). The gain curve — 1.00 → 1.00 → 0.29 → 0.00 —
is a clean convergence, not a budget clamp. The loop found its floor: the brief's premises
are broken in a small, enumerable set of ways, and by round 3 every lens was re-deriving the
same set.

---

## If you read one thing

**The `dispatch_log` Rimsky is designed to "extend" does not exist** (Spine 1 —
f-001/f-006/f-009/f-013, risk.product 9, four-lens convergence). The telemetry instrument,
the cost gate's reservoir, and Q4's controller-build measurement clock all read from a schema
that is nowhere in the repo except as Mycroft's own. `argmax(heat)` points at the fabricated
Q3 cost figure and the missing reservoir signal (f-005/f-014, heat 12) — genuinely spicy —
but the |taste| tiebreaker and the sheer downstream blast radius put the dispatch-log
convergence first: **rewrite constraint 3, Q4, and the §7 v1 cut to say "build a minimal
dispatch log," not "extend the existing one," and re-size v1 accordingly before the charter
is formed.**

---

## Caveats

- **Refuted, not surfaced.** f-002/r1 (`pause --drain` as shipped graceful-stop) and f-003/r1
  (dispatch-claim-race by isomorphism) are refuted and appear in no view except as the
  resolved side of the §5 disagreement. Their *parent frames* (safe-abort gap; claim-write
  hazard) partly survive; their specific evidentiary claims do not.
- **Zero fusions attempted.** No hybrid intersection-detector lens was spun up
  (`fusion_stats.attempted = 0`); the round-3 "fusion" record is an adjudication, not a
  lens-pair synthesis. High-tension pairs (economics × canal-lock; topology × joinery) were
  present but never fused — a genuinely different-hazard finding from a fused pair may exist
  and was not sought.
- **Orchestrator-shape space under-explored.** The goal asked to surface and score
  alternative orchestrator shapes (event-driven vs poll, staged vs immediate, library vs
  command). The lenses never generated first-class findings on these; the scoring in the
  "different shapes" section above is *my* extrapolation from the ledger, not a lens result.
  Event-driven vs poll is genuinely unreached.
- **Q5 cost never measured.** The pre-spawn check cost (Q5) has only prior-art *citation*
  (f-007/r0: Mycroft's 5s-timeout-per-source) — no lens measured intermap change_impact +
  interlock dry-run latency directly. Whether the dry-fit stays cheap is asserted, not
  verified.
- **Single-region verification.** Load-bearing greps (dispatch_log absence, drain read-site
  absence, Mycroft pause wiring, lbkd `=` splice defect, toctou mis-citation) were
  re-verified in this synthesis and all held. The bzy dual-tracking state (f-008) was
  verified against `.beads/issues.jsonl` by the joinery lens but not re-run here beyond the
  bead's own text.
- **Not a budget clamp.** The DRY halt reflects true convergence (novel_cluster_rate → 0),
  not exhausted slots — no top-up would have paid.
