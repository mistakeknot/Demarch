---
artifact_type: brainstorm
bead: Sylveste-3kol
stage: discover
codename: Rimsky
supersedes_codename: Conductor
melange_reviewed: 2026-07-23
melange_synthesis: docs/research/flux-melange/rimsky-orchestrator-design-brief/2026-07-23-synthesis.md
---

# Rimsky — N-parallel sprint orchestrator: design brief

> **Status:** pre-charter design brief (not a plan). Written to give `/flux-melange`
> a coherent target to steer against before the Rimsky goal is formed via
> `/clavain:goal-form`. Melange findings feed the charter; the charter feeds `/goal`.
>
> **⚠ Post-melange corrections (2026-07-23).** A flux-melange run (DRY convergence, 4
> rounds; synthesis linked in frontmatter) invalidated three premises this brief originally
> stood on. The corrections are folded in below and flagged inline `[melange-corrected]`.
> The load-bearing one: **the `dispatch_log` Rimsky was said to "extend" does not exist in
> the repo** — it is new construction, not an extension. All three corrections were
> re-verified by direct grep. See §8 for the full correction log.

## 0. One-sentence framing

**Rimsky is the consumer that the worktree-first contract
(`docs/guide-worktree-first-coordination.md`, shipped by goal 40830a1b / n2ma,
2026-07-22) exists to enable: a flat, depth-1 fan-out orchestrator that runs N
sprint/work tasks in parallel across worktree-isolated repos, coordinates the
shared-tree cases through interlock, prices the fan-out before spawning, and
measures the conflict economics of doing so.**

Epic: `sylveste-3kol` (P1, currently **empty description** — a gstack import, sibling
of `ss35` /freeze and `clha` /office-hours). The three sub-beads below already
encode most of the hard constraints; this brief assembles them into one target.

## 1. What Rimsky is (and is not)

**Is:** an orchestration layer over the EXISTING dispatch primitives — `/clavain:work`,
`/flux-review`'s fan-out, `Agent`/`Workflow` isolation, interlock reservations, and
`bd worktree create` redirect. It decides *what runs in parallel*, *in which isolation
domain*, *at what cost*, and *whether the fan-out was worth it*.

**Is not:** a new coordination substrate. interlock already coordinates shared trees;
native Claude Code worktrees already isolate; bd already redirects from worktrees. Rimsky
does not reimplement any of these — the n2ma retirement verdict established the
GIT_INDEX_FILE machinery is gone and the two-layer (isolation + coordination) model is
canonical. Rimsky is a *policy + telemetry* layer on top, not a mechanism.

## 2. The substrate Rimsky consumes (grounded, current)

| Substrate | Source | What Rimsky uses it for |
|-----------|--------|-------------------------|
| Worktree-first contract | `docs/guide-worktree-first-coordination.md` (n2ma) | Per-nested-repo isolation rule; root-ops-from-main-checkout rule; the doctor check that fails loud from a root worktree |
| `bd worktree create` redirect | `scripts/tests/bd_worktree_redirect.bats` | Every parallel task's beads writes land in the main-checkout Dolt store |
| interlock (shared-fs, 0.2.16+) | `interverse/interlock/docs/shared-fs-coordination.md` | Coordinates the deliberately-shared-tree cases (file reservations + commit lock); interlock no longer creates worktrees |
| Sprint v2 artifact bus | `docs/plans/2026-03-19-sprint-v2-artifact-bus.md` (bead `sylveste-lbkd`, **OPEN**) | How parallel sprint stages hand artifacts (brainstorm→plan→exec) to each other — **the subsumption question, see §5** |
| Fleet orchestrator prior art | `docs/plans/2026-03-12-mycroft-fleet-orchestrator-v01.md` (Autarch app) | Closest prior orchestrator — fleet monitor + T0/T1 suggest/approve dispatch. **Overlap question, see §5** |

## 3. The three encoded constraints (from sub-beads — these are near-decided, stress-test don't re-litigate)

1. **Flat depth-1 fan-out, no recursive sub-coordinators** (`4b5.17`). Breadth, not depth.
   The runtime silently flattens depth>1. Experimental caps (team-spawn hardcoded to 5,
   flux-review MAX_CONCURRENT from the 25-thread ceiling) are **advisory, version-volatile
   integers** — the *structural* rule (flat) is what's pinned, not the numbers. Do NOT build
   a topology-envelope probe; do NOT raise MAX_CONCURRENT (it's a deliberate rate-limit/cost gate).

2. **Pre-dispatch parallelizability + cost gate** (`4b5.7`, folded into the 3kol spec + surfaced
   in `route.md` alongside classify-complexity). Rules: (a) default parallel only across
   *independent repos/modules*; (b) intra-repo fan-out requires an automated spec-scope conflict
   check (intermap change_impact + interlock dry-run) BEFORE spawning — distinct from any
   POST-spawn check; (c) price the token multiplier into the parallelize-or-not decision;
   (d) hard rule: **do not transfer research-mode multi-agent wins to coding tasks** (the ~15x
   figure is advisory).

3. **Conflict-economics telemetry** (`4b5.8`). `[melange-corrected]` — the brief originally said
   "extend the EXISTING dispatch log." **That log does not exist.** A grep of
   `os/Clavain/commands/work.md` and `interverse/interflux/**/*.go` for `dispatch_log` /
   `conflict_rate` / `wall_time` returns zero implementations; the only real `dispatch_log` schema
   in the repo is **Mycroft's** (Autarch). So this constraint is **new construction**: *build* a
   minimal dispatch log that records wall-time, task-sum, agent-count AND conflict-rate +
   merge-resolution-time per fan-out width — operationalizing the orphaned `toctou-analysis.md:461`
   recommendation (">1% conflict rate → escalate"). **Ship the instrument, not the numbers.** The
   dynamic kill-rule controller + cost cap + intermap hotspot check are DEFERRED to P3, GATED on
   the telemetry returning a non-trivial conflict rate (interlock may already give ~zero, making a
   controller dead code). Precondition: verify multi-agent CODE dispatch is actually exercised in
   real runs. **Sequencing consequence:** because the instrument is unbuilt, telemetry-first
   sequencing fails the anti-abandonment test — see §5 Q6 for the recommended policy-first,
   instrument-second cut.

## 4. Where Rimsky plugs into the existing cycle

- **`route.md`** surfaces the parallelizability+cost gate alongside `classify-complexity` (from `4b5.7`).
- **`/sprint` / `/work`** are the dispatch verbs Rimsky orchestrates; under `/sprint`, Codex delegation
  (`clavain:interserve`) already subsumes `/work` — Rimsky sits above this, deciding fan-out shape.
- **Autosync lane discipline** (contract §8): worktree branches never autosync-push to main; Rimsky
  must respect the per-machine lane model (autosync/clavain, autosync/zklw), merge to main deliberately.
- **The nested-repo rule** (contract §5) is Rimsky's hardest correctness constraint: a naive root fan-out
  materializes almost no plugins. Rimsky must fan out *per nested repo*, and route root-spanning ops
  (publish waves) to the main checkout. The 2026-07-22 publish wave (cpd) is the cautionary tale.

## 5. Open architecture questions (THIS is what melange should chew on and score)

**Q1 — Subsumption of `sylveste-lbkd` (Sprint v2 artifact bus).** Is the artifact bus (a) a
*dependency* Rimsky requires (parallel stages need a reliable artifact handoff that works without an
active interserve run — lbkd's whole point), (b) *subsumed* into Rimsky (the bus becomes Rimsky's
inter-stage channel), or (c) *orthogonal* (bus is per-sprint-lifecycle, Rimsky is per-fan-out)? lbkd
is OPEN and unstarted — the answer determines sequencing.

**Q2 — Overlap with Mycroft fleet orchestrator (Autarch).** `[melange-corrected: answer is (a),
evidence is shipped]` Mycroft already does fleet monitor + T0/T1 suggest/approve dispatch across
sessions. The melange confirmed Mycroft is **substantially shipped, not just planned**:
`apps/Autarch/internal/mycroft/scheduler/conflict.go` already implements a pre-dispatch interlock
conflict check structurally similar to Rimsky's own Q5 mechanism, and its v0.1 scope is
observe/suggest-approve (no autonomous dispatch). **Verdict: (a) different layer** — Rimsky = within-goal
task fan-out; Mycroft = cross-session fleet coordination. Cite the *shipped code*, not the plan doc, when
the charter records this. Open sub-question the charter must still settle: does Rimsky's telemetry write
into Mycroft's existing `dispatch_log` / `tier_state` via FleetView (a Q2-consumer posture), or grow its
own log? Don't let both grow independently under the same name.

**Q3 — Isolation granularity vs. the token multiplier.** `[melange-corrected: the cited figure was
fabricated]` The cost gate (§3.2) says price the multiplier in. The brief originally claimed "the contract
notes ~200-500ms + disk per worktree" — **that figure appears nowhere in
`docs/guide-worktree-first-coordination.md`** (verified by grep); it was invented and mis-attributed.
There is therefore **no measured crossover number** to compute against today. Reframe Q3: either (a) keep
the shipped structural rule ("independent repos → worktree, shared tree → interlock" with no middle) and
NOT ask the orchestrator to compute a crossover at all, or (b) if a crossover is wanted, *measure* worktree
setup cost first (it is real — ~200-500ms is a plausible order from CC subagent behavior, but it is not a
contract claim and must be measured, not cited). Additionally, the cost gate as specified prices a *ratio*
(N× vs serial) but never reads a *reservoir* (rate-limit headroom, current session spend) — so it can say
"this fan-out is N× more expensive" but never "can we afford N× right now." A live reservoir signal is a
missing input the charter should name.

**Q4 — Does the conflict controller ever get built?** `4b5.8` gates the dynamic controller on telemetry
showing a non-trivial conflict rate, and openly suspects interlock already gives ~zero. Should Rimsky v1
ship *only* the instrument and a hard-coded escalation threshold, with the controller as explicit dead-code-
until-proven? What evidence would flip that?

**Q5 — The pre-spawn conflict check's real cost.** `4b5.7` mandates intermap change_impact + interlock
dry-run BEFORE every intra-repo fan-out. Is that check cheap enough to run unconditionally, or does it need
its own gate (only run it above N tasks)? Could the check itself become the bottleneck it's meant to prevent?

**Q6 — Anti-abandonment / stakes routing.** Rimsky is a C4/C5 capability. Is it one goal, or does it decompose
into a shippable v1 (instrument + flat fan-out + cost gate) and deferred v2 (controller, if earned)? Where are
the internal gates so it can't stall as a half-built orchestrator? `[melange-informed]` **Recommended cut:
policy-first, instrument-second.** Because the telemetry instrument is *unbuilt* (§3.3), telemetry-first
sequencing front-loads new construction and fails anti-abandonment. v1 = flat fan-out + cost gate against a
*newly-built minimal* dispatch log (acknowledged as construction, not extension); v2 = the dynamic controller,
gated on that log returning a non-trivial conflict rate. Separate **build-sequencing gates** (what unlocks the
next construction stage) from **operator-safety controls** (see Q7) — the brief originally conflated them.

**Q7 — Safe-abort for an in-flight fan-out.** `[melange-surfaced]` The brief has **zero abort/cancel/drain
vocabulary** for a live N-parallel fan-out — the only halt mechanism mentioned is the deferred-P3 kill-rule
*detection* controller, which is about *policy*, not an *operator stop button*. Does shippable-v1 require a
**stop-new-dispatch-only abort path**, independent of and prior to the deferred controller, so v1 doesn't ship
a fan-out with no safe way to halt it mid-run? Mycroft ships a reusable primitive: **`pause`/`resume`**
(stop-new-dispatch). Note the melange refuted the reuse of `pause --drain` as a *coordinated graceful drain* —
that Cobra flag is registered but never read (`apps/Autarch/cmd/mycroft/main.go:427` registration,
`:230-247` RunE ignores it), so a true drain of in-flight agents is NOT shipped prior art. What Rimsky can
reuse is stop-new-dispatch, not graceful-drain.

## 6. Collision map (beads in play)

- `sylveste-3kol` (P1, epic, empty) — the Rimsky epic itself. 4b5.17 fixes the empty description.
- `sylveste-4b5.7` / `4b5.8` / `4b5.17` (open) — the three encoded-constraint sub-beads (§3).
- `sylveste-lbkd` (open) — Sprint v2 artifact bus. **Q1.**
- `sylveste-cpd` (closed) — the publish-wave failure that motivates the nested-repo rule; Rimsky must not repeat it.
- `sylveste-bzy` (open, P2) — `[melange-corrected: HARD precondition, not optional]` 3 of 5 plugins
  (**interfer** 128 files, **intersight** 24, **interseed** 16) are STILL dual-tracked — embedded in the
  monorepo AND published independently (interhelm + intercut were resolved via cpd). Rimsky's per-nested-repo
  fan-out rule cannot decide *which repo to isolate* for these three until bzy closes: they have two competing
  canonical timbers. Either bzy is a blocking dependency for correct fan-out over those plugins, OR the Q5
  pre-spawn check must detect dual-tracking and refuse to slot a worktree for a contested repo. Verified by
  `git ls-files` counts.
- Mycroft (Autarch app, **shipped** — has `scheduler/conflict.go`, observe/suggest scope) — prior-art
  orchestrator. **Q2 answer: different layer, evidence shipped.**

## 7. What "done" might look like (candidate v1 cut, post-melange)

`[melange-corrected]` A candidate **shippable-v1** completion shape (policy-first, instrument-second):
route.md surfaces the parallelizability+cost gate; a **newly-built minimal dispatch log** (NOT an extension —
none exists) records wall-time, task-sum, agent-count, conflict-rate + merge-resolution-time per fan-out
width; a documented flat-fan-out orchestration path that fans out per nested repo, routes root-ops to main
checkout, and passes the n2ma doctor check; a **stop-new-dispatch abort path** (Q7, reusing Mycroft's
`pause`/`resume`); the Q1/Q2 subsumption calls made explicit as bead verdicts (lbkd; Mycroft = different
layer, cite shipped code); dual-tracked repos (bzy) either resolved or gated out of fan-out eligibility; the
dynamic controller explicitly **deferred to v2** with its gate condition (non-trivial measured conflict rate)
written down. The internal gate between v1 and v2 is the telemetry returning a non-trivial conflict rate —
if it returns ~zero (interlock may already give that), the controller stays permanently deferred and v1 is
the whole goal.

## 8. Melange correction log (2026-07-23)

Full synthesis: `docs/research/flux-melange/rimsky-orchestrator-design-brief/2026-07-23-synthesis.md`
(4 rounds, DRY convergence, 4 upheld / 2 refuted / 1 emergent). Corrections re-verified by direct grep:

1. **`dispatch_log` does not exist** (4-lens convergence, risk 9). The telemetry constraint is new
   construction, not "extend the existing log." Fixed in §3.3, §5 Q4/Q6, §7.
2. **Q3 cost figure fabricated** — "~200-500ms + disk per worktree" is nowhere in the shipped contract;
   it was mis-attributed. Fixed in §5 Q3.
3. **bzy is a hard precondition** — 3 of 5 plugins still dual-tracked; fan-out can't pick an isolation
   boundary for them. Promoted from parenthetical in §6.
4. **Q2 is answerable now** — Mycroft is shipped (`scheduler/conflict.go`); "different layer" verdict,
   cite the code. Fixed in §5 Q2.
5. **Safe-abort gap (new Q7)** — no abort vocabulary for a live fan-out; reusable primitive is Mycroft
   `pause`/`resume`, NOT `pause --drain` (registered-but-unwired flag). Added as §5 Q7.
6. **Cost gate reads a ratio, not a reservoir** — no live rate-limit/spend signal named. Noted in §5 Q3.

**Honest gaps in the run** (do not block goal formation): zero lens-pair fusions fired (a fused-pair hazard
may be unsought); alternative orchestrator shapes (esp. event-driven vs poll) were never produced as
first-class findings — the synthesis's scoring of them is extrapolation; Q5 pre-spawn check cost was cited
(Mycroft's 5s timeout) but never measured directly.
