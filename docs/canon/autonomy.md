# Autonomy Vocabularies

Canonical definitions for every scale in Sylveste that gets called "the autonomy ladder." There are five live ones and one retired. They measure different things, advance on different evidence, and are advanced by different parties. This page is the single definition of each; other docs link here rather than restating.

## Why this page exists

"Autonomy" is used in at least three incompatible senses across Sylveste docs. The flux-drive review of the Autarch autonomy gap ([`fd-vision-coherence.md` § "The term 'autonomy' is used inconsistently"](../research/flux-drive/autarch-autonomy-gap/fd-vision-coherence.md)) named the failure precisely: a reader can conclude that shipping autonomous subsystems advances the delegation ladder, and that does not follow. You can have fully unsupervised subsystems that still require L2 human oversight at the portfolio level.

The bare token `L3` is overloaded **five ways**: "human sets policy" (delegation), "Auto-remediate" (retired capability), "calibration loops fire unaided" (Track A), "existential failures prevented" (Track B), and "multi-external + ODD published" (Track C). `L2` is overloaded similarly. An unqualified `L<n>` in Sylveste prose is ambiguous by default — always name the scale.

## Disambiguation table

| Scale | Range | Unit of measure | Who advances it | Live status lives in |
|---|---|---|---|---|
| **Human delegation ladder** | L0–L5 | How much authority the human delegates | Human, on demonstrated safety | [Below](#1-human-delegation-ladder-l0l5) |
| **Capability mesh maturity** | M0–M4 | How mature one subsystem is | Evidence thresholds, per subsystem | [sylveste-vision.md § Current Mesh State](../sylveste-vision.md#current-mesh-state) |
| **Lifecycle phase chain** | 9 or 7 phases | Where a single run is in its lifecycle | Gates + `ic run advance` | [`core/intercore/pkg/phase/phase.go`](../../core/intercore/pkg/phase/phase.go) |
| **Discovery confidence tier** | High/Medium/Low/Discard | How confident scoring is in one discovery | Adaptive thresholds from human promote/dismiss | [Below](#4-discovery-confidence-tiers) |
| **Roadmap track levels** | A/B/C : L1–L4 | How far one roadmap track has come | Observed exit criteria, never declared | [Below](#5-roadmap-track-levels-abc--l1l4) |
| **~~v4.0 capability ladder~~** | ~~L0–L4~~ | *Retired 2026-04-11* | — | [Below](#6-retired-the-v40-capability-ladder-l0l4) |

None of these are interchangeable. Advancing one does not advance another.

---

## 1. Human delegation ladder (L0–L5)

**Measures:** how much authority the human delegates to agents. **Advanced by:** the human, and only on demonstrated safety at the previous level. This is the ladder meant by an unqualified "trust ladder."

| Level | Delegation |
|---|---|
| **L0** | Human approves every action |
| **L1** | Human approves at phase gates |
| **L2** | Human reviews evidence post-hoc |
| **L3** | Human sets policy, agent executes |
| **L4** | Agent proposes policy changes |
| **L5** | Agent proposes mechanism changes |

**Current position: L1–L2.** This is the one place that number is recorded; every other doc links here.

Each level requires demonstrated safety at the previous one. No shortcuts. The kernel boundary (agents cannot modify Intercore) is a trust threshold, not an architectural invariant — it softens as trust is earned, but through gated processes, not direct modification.

The human's role is fixed at every level: set objectives, make tradeoffs, approve deployments. What changes is how often they must exercise it. The goal is human-*above*-the-loop — governing outcomes via receipts, not step-by-step supervision.

### What the current level implies

| Surface | L1–L2 behavior (today) | L3 | L4–L5 |
|---|---|---|---|
| Code push to remote | Per-change human confirmation before each push | Human sets shipping policy (which repos, which thresholds); agent pushes when conditions are met | Human approves the policy itself; agent pushes autonomously within bounds |
| Phase advancement | Human approves at gates, or reviews post-hoc | Policy-driven | Agent may propose changes to the policy |

The push invariant ("the system never pushes without human confirmation") is an **L1–L2 safety control**, not a permanent property. It softens through gated processes as the ladder advances.

Promotion requires pre-specified evidence thresholds. Demotion is triggered by sustained regression indicators exceeding threshold for a defined observation window. Evidence epochs reset trust when environmental conditions shift (major model changes, architecture migrations, subsystem replacements). The principle — evidence earns authority — is permanent. The mechanism is revisable by human authority regardless of accumulated evidence.

## 2. Capability mesh maturity (M0–M4)

**Measures:** how mature a *single subsystem* is. **Advanced by:** evidence thresholds evaluated per subsystem. Replaced the retired linear v4.0 capability ladder with a multi-dimensional view — different subsystems mature at different rates.

| Level | Name | Criteria |
|---|---|---|
| **M0** | Planned | Design exists (brainstorm, PRD), no implementation |
| **M1** | Built | Code shipped and tests pass, not operationally tested |
| **M2** | Operational | Running under real conditions, evidence signals yielding data for 30+ days |
| **M3** | Calibrated | Evidence thresholds defined and tested, promotion/demotion criteria met |
| **M4** | Adaptive | Self-improving based on evidence, minimal human intervention needed |

System-level trust = `min(maturity across M1+ mesh cells)`. Subsystems at M0 are excluded — they are planned capabilities, not operational components. System trust is a step function: it advances when the weakest *operational* subsystem catches up. Evidence compounds per subsystem; system-level trust is gated on the weakest link.

Criticality tiers (inspired by aviation Design Assurance Levels) mean higher-consequence subsystems need more rigorous evidence at each level. Governance failure is critical; Coordination failure is medium.

**Per-subsystem current M-levels live in exactly one place:** [`sylveste-vision.md` § Current Mesh State](../sylveste-vision.md#current-mesh-state). Do not copy that table.

> **M0–M4 is not a renamed L0–L4.** The retired ladder put the *entire system* at one level. The mesh lets each subsystem sit at a different level simultaneously. The difference is structural — multi-dimensional versus linear — not cosmetic.

## 3. Lifecycle phase chains

**Measures:** where a single run sits in its lifecycle. **Advanced by:** gate evaluation plus `ic run advance`. Not a trust or maturity scale at all — a run at phase `executing` says nothing about delegation level or subsystem maturity.

**Source of truth:** [`core/intercore/pkg/phase/phase.go`](../../core/intercore/pkg/phase/phase.go). The chain is data, not doctrine — it is configurable per run via an explicit `phases` array stamped at creation.

**Default chain (9 phases)** — used when a run has no explicit phases column:

```
brainstorm → brainstorm-reviewed → strategized → planned → executing → review → polish → reflect → done
```

**Goal-native chain (7 phases)** — opt-in at run creation; `goal-formed` absorbs brainstorm/brainstorm-reviewed/strategized for goal-scale work:

```
goal-formed → planned → executing → review → polish → reflect → done
```

`DefaultChain` is never edited to add goal-native phases — in-flight runs with a NULL phases column must keep resolving to the legacy chain.

**Deprecated aliases.** Older artifacts and `lib-sprint.sh` phases_json use two names that are no longer canonical. Both still appear as stored DB values:

| Legacy value | Canonical | Note |
|---|---|---|
| `plan-reviewed` | `planned` | DB value; `ic migrate phases` converts |
| `shipping` | `polish` | DB value; `ic migrate phases` converts |

This is the source of the "8-step vs 9-step chain" discrepancy in brainstorms predating the rename.

**Macro-stages.** Above the phase chain, Clavain groups phases into five macro-stages as a mental model: **Discover → Design → Build → Ship → Reflect**. Macro-stages are not phases and are not tracked by the kernel; the kernel enforces handoff via `artifact_exists` gates at macro-stage boundaries.

## 4. Discovery confidence tiers

**Measures:** how confident scoring is in a *single discovery*. **Advanced by:** adaptive thresholds derived from human promote/dismiss behavior. The kernel enforces tier boundaries; the OS decides policy at each tier.

| Tier | Score | OS policy |
|---|---|---|
| **High** | ≥ 0.8 | Auto-create bead (P3 default), write briefing doc, notify in session inbox |
| **Medium** | 0.5 – 0.8 | Write briefing draft, surface in inbox for human promote/dismiss/adjust |
| **Low** | 0.3 – 0.5 | Log only, searchable via kernel discovery API |
| **Discard** | < 0.3 | Record with `discarded` status as negative signal |

**Adaptive thresholds.** Boundaries shift on the promotion-to-discovery ratio. Consistent promotion of Medium items (>30%, the point where manual triage cost exceeds auto-triage risk) lowers the High threshold by 0.02 per feedback cycle — a small step to prevent oscillation. Consistent dismissal of High items (<10%) raises it. Defaults are tunable per project; convergence toward human judgment is tracked by Interspect.

Discovery is a capability track **orthogonal to the delegation ladder** — it operates at any delegation level. It is the pipeline that finds work before work can be recorded.

## 5. Roadmap track levels (A/B/C : L1–L4)

**Measures:** how far one of the three roadmap tracks has come. **Advanced by:** meeting an observed exit criterion — never by declaration. **Source of truth:** [`docs/roadmap-v1.md`](../roadmap-v1.md).

Three tracks progress independently; a version bump requires **all three** to reach the gate.

| Track | Question it answers |
|---|---|
| **A — Autonomy** | Does the system's past behavior shape its future behavior without human intervention? |
| **B — Safety** | Are failures prevented and recovered from structurally, not probabilistically? |
| **C — Adoption** | Does it work on codebases the developers do not control? |

| Level | A: Autonomy | B: Safety | C: Adoption |
|---|---|---|---|
| **L1** | Manual calibration (tools exist, human invokes) | Gates exist and block | Self-building only |
| **L2** | Semi-automatic (fires at lifecycle points) | Gates learn from pass/fail history | One external project, 50+ sprints |
| **L3** | Fully autonomous loops | Five existential failure modes prevented | 3+ external projects, ODD published |
| **L4** | Self-healing / auto-remediation | Adversarial testing validates detection rates | Onboarding <60 min to first change |

**Version gates are conjunctions:** `v0.7 = A:L3 + B:L2 + C:L1` · `v0.8 = A:L3 + B:L3 + C:L2` · `v0.9 = A:L4 + B:L4 + C:L3` · `v1.0 = A:L4 + B:L4 + C:L4`.

### Track levels are earned, not set

This is the property that most distinguishes them from the delegation ladder. Each level has a mechanical exit criterion measured by observation:

- **A:L3** — 10 consecutive sprints with zero manual calibration intervention across routing, gate-threshold, and phase-cost loops.
- **B:L3** — 100 consecutive sprints with zero existential failure events.
- **B:L4** — semantic cascade detection rate >70% under adversarial probing.
- **C:L2** — 50+ completed sprints on one external project, metrics compared to the self-building baseline.

There is no command that sets a track level. A:L3's streak is machine-tracked and reportable:

```console
$ clavain-cli calibration-streak status
A:L3 receipt proof 0/10 (routing=0 gate=0 phase=0; best=0)
```

The counter increments on a clean SessionEnd and **resets to zero on any manual calibration intervention**. Implementation work for A:L3 is complete (epic `sylveste-myyw`, 18/19 children closed); what remains is the observation window, which accumulates naturally rather than being worked on.

> **Do not confuse `A:L3` with delegation `L3`.** Delegation L3 is a human decision to hand over policy authority. A:L3 is an observed fact about calibration loops. Neither implies the other.

## 6. Retired: the v4.0 capability ladder (L0–L4)

**Retired 2026-04-11**, replaced by the capability mesh (§2). Documented here because it is still cited in dated brainstorms, plans, and PRDs, which are historical receipts and are not being rewritten.

| Level | Name | What it meant |
|---|---|---|
| L0 | Record | Kernel records runs, phases, dispatches, artifacts. Human drives everything. |
| L1 | Enforce | Gates evaluate real conditions; a run cannot advance without meeting preconditions. |
| L2 | React | Events trigger automatic reactions; phase transitions spawn agents. |
| L3 | Auto-remediate | System retries failed gates, substitutes agents, adjusts parameters unaided. |
| L4 | Auto-ship | System merges and deploys when confidence thresholds are met. |

> **Collision warning.** This ladder shares the `L` prefix with both the delegation ladder (§1) and the roadmap track levels (§5), and means something different from either. A pre-April-2026 doc saying "stalls at L2 (React)" or "L3 (Auto-remediate)" is referring to *this* retired scale — not delegation L2 ("human reviews evidence post-hoc"), not A:L2 ("calibration fires at lifecycle points"). When citing old material, name the scale.

Where these level *names* survive as goals, they now attach to mesh cells — e.g. "L4 auto-ship" is tracked as depending on Governance M3 and Routing M3.

## 7. Orthogonality

The scales advance independently. Concretely:

| | Delegation L0–L5 | Maturity M0–M4 | Phase chain | Confidence tier | Track A/B/C |
|---|---|---|---|---|---|
| **Delegation L0–L5** | — | Orthogonal | Orthogonal | Orthogonal | Evidence for, not equal to |
| **Maturity M0–M4** | Orthogonal | — | Orthogonal | Gates policy at each tier | Overlapping evidence, distinct scales |
| **Phase chain** | Orthogonal | Orthogonal | — | Orthogonal | Orthogonal |
| **Track A/B/C** | Evidence for, not equal to | Overlapping evidence | Orthogonal | Orthogonal | — |

The one non-orthogonal relationship worth stating plainly: **track levels are evidence that may justify a delegation decision, but they never make one.** A:L3 being reached does not move delegation from L1–L2 to L3; it gives the human grounds to consider it.

Worked examples of what orthogonal means here:

- A system whose subsystems are all M2 may still operate at delegation L1 if the human has not yet chosen to delegate further. Capability does not confer authority.
- Advancing a subsystem M1→M2 does **not** advance the delegation ladder. It produces evidence that *may* support a later human decision to advance it.
- A run reaching phase `done` says nothing about either scale.
- Some capability *is* prerequisite to some delegation: L3 auto-ship requires Governance and Routing at M3. Prerequisite is not equivalence.

## 8. Terms that are not scales

Three phrases read like levels but are not. Each gets a distinct name so they can be told apart:

| Term | What it actually is | Do not say |
|---|---|---|
| **Unsupervised operation** | A structural property of a subsystem: it runs without human intervention in normal operation. Binary, per subsystem. Formerly written "ring autonomy." | "this ring is autonomous, so we're at L3" |
| **Sprint operating mode** | A Clavain operating mode — how much of a single sprint runs without human gates. A runtime setting, not an earned level. | "autonomous sprint mode means L4" |
| **Subsystem maturity** | The M0–M4 mesh position of one subsystem. Use this phrase where old docs said "autonomy ladder level" in the capability sense. | "the autonomy ladder" (ambiguous) |

The failure mode this table prevents: concluding that unsupervised subsystems (a structural property) advance the delegation ladder (an earned authority). They do not. You can build fully unsupervised rings and still owe the human L2 oversight at the portfolio level.

## Cross-references

- [`PHILOSOPHY.md` § Earned Authority](../../PHILOSOPHY.md) — why trust is progressive and evidence-based
- [`docs/sylveste-vision.md` § The Capability Mesh](../sylveste-vision.md) — live per-subsystem maturity and the dependency DAG
- [`os/Clavain/docs/clavain-vision.md`](../../os/Clavain/docs/clavain-vision.md) — how the OS applies these at runtime (event reactor, discovery policy)
- [`core/intercore/pkg/phase/phase.go`](../../core/intercore/pkg/phase/phase.go) — phase chains as code
- [`docs/roadmap-v1.md`](../roadmap-v1.md) — the A/B/C track ladders and version gates
- [`docs/solutions/patterns/cross-document-philosophy-alignment-20260227.md`](../solutions/patterns/cross-document-philosophy-alignment-20260227.md) — the alignment method, including why historical artifacts are never rewritten

**Enforcement is out of scope for this page.** The graduated autonomy tier system that will *read* these definitions and change gate behavior is tracked separately (`Sylveste-lcxa`), as is autonomy safety policy for auto-remediate and auto-ship (`iv-i76wv`).
