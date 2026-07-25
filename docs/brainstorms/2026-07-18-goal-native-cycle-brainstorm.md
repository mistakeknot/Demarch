---
artifact_type: brainstorm
bead: none
stage: discover
---

# Goal-Native Clavain/Intercore Cycle (Formation Ritual + First-Class Goal Entity)

## What We're Building

Reshape Clavain/intercore's strategy → plan → execute → review cycle around **goals as the top-level unit**, with two pillars:

**Pillar 1 — The goal-formation ritual.** Clavain/intercore becomes a process where agent and user *inter-elicit* the best possible goal by maximizing comparative advantage: the user holds intent, stakes, taste, tacit context, and go/no-go authority; the agent holds research breadth, prior art, repo state, and candidate enumeration. Mechanics: research-first (the agent never asks what it can derive), then single-question AskUserQuestion interviews (one at a time, recommended option first), producing a **goal charter**; high-stakes charters get a flux-melange review before ratification. The charter's terminal artifact is twofold: a durable intercore Goal entity (the why, scope, acceptance criteria, verdicts on adjacent work) and a **machine-evaluable completion condition** for Claude Code's built-in `/goal` command — written so the Haiku evaluator can judge it from surfaced output ("tests exit 0, bead closed with evidence", never "the feature is good"), ≤4000 chars, bounded with "or stop after N turns" where appropriate.

**Pillar 2 — Goal as a new first-class intercore entity.** An `ic goal` noun family: goals contain runs, carry the charter, accumulate close evidence. `/goal` invocation mints the entity; runs started while a goal is active auto-attach.

Rationale for the leverage bet: `/goal` is a work-until-done loop, so goal quality is the highest-leverage variable in the cycle — a mis-specified condition steers an autonomous loop until the *wrong* thing is done. The ritual front-loads collaboration exactly where errors compound, and institutionalizes what currently exists only as behavioral memory ("propose ambitious goals", "finish design calls before executing", "next-goal freshness check").

## Why This Approach

Research (2026-07-17, repo-research over Clavain + intercore source) found a wired **exit** and an empty **entry**:

- `/goal` IS a built-in Claude Code command (v2.1.139+): session-scoped completion condition, Haiku evaluator judging only surfaced conversation output, cleared on met, restored on resume. (An earlier filesystem-only search wrongly concluded it didn't exist; corrected against the documented built-in.)
- Clavain wires only the exit: goal-cadence Stop-hook regex (`hooks/lib-signals.sh:84`), goal-cadence tier in `auto-stop-actions.sh:135-146`, `commands/next-goal.md` ranking candidates from `bd ready`. Entry has zero machinery; `commands/route.md` has no goal-shaped branch; remontoire concedes "/goal starts ordinary implementation and does not alter the source cycle."
- intercore has no Goal noun: `Run.Goal` is a free-text label (`internal/phase/phase.go:186-208`). But containment plumbing exists (`ParentRunID`, portfolio runs), chains/gates are per-run configurable (`pkg/phase/phase.go:11-35`, `internal/phase/gate.go`), and beads bind runs via `bd state <bead> ic_run_id`.
- The terminal cluster is four *independent* triggers: reflect (sprint Step 9), compound (conditional Step 8), verify (ad hoc, absent from sprint.md), next-goal (Stop hook, outside phase state entirely).
- Review-gate routing is static: `quality-gates.md` is 100% flux-drive with zero melange awareness, while `classify-complexity` (C1–C5) already exists as a stakes metric.
- interphase is a second, parallel bead-scoped phase system (file sideband to statusline) competing with the kernel chain.
- Capability routing at execution scale already shipped (epic Sylveste-fc5 closed: fable tier, two-strikes escalation in `internal/dispatch/escalate.go`, opus validators).

Nobody owns formation; goals are born as free text and die formally. The ritual fills exactly that gap.

## Key Decisions

*(1–7 from the 2026-07-18 dialogue; 8–15 melange-ratified 2026-07-19 — synthesis at `docs/research/flux-melange/goal-native-cycle-redesign/2026-07-18-synthesis.md`, 6 rounds, DRY halt, 28 upheld findings, zero open disagreements at halt.)*

1. **Goal ontology: new first-class intercore entity** (`ic goal` noun family) — chosen over goal-as-parent-run and informal-label. Goals contain runs.
2. **Formation ritual as the entry point** (Pillar 1 above): comparative-advantage inter-elicitation, research-first, single-question interviews, charter document, melange review for high-stakes charters, dual terminal artifact (entity + /goal condition).
3. **Containment: Goal → runs directly** (`goal_id` on runs); **bead binding optional and stakes-scaled** — epic for C4/C5 goals, single task bead or none for C1. Rejected: goal⇔epic 1:1 (taxes lightweight bounded goals) and mandatory bead (ceremony for throwaway session goals). Beads stay linked enough that exit machinery (`bd ready`-ranked successors) keeps working.
4. **Scope: all-in, gated inside one goal** — ritual + entity, strategy diet, terminal-gate unification, stakes-routed review gates, interphase retirement, staged with internal gates. Only the capability-routing audit (vs goal-scale entry) spins off as a follow-up bead.
5. **Strategy diet via absorption**: strategy's real jobs (subsume/supersede/orthogonal verdicts on adjacent work, epic framing) migrate into the ritual's research phase; the kernel chain gains a goal-formation head instead of a `strategized` middle. This is a chain change, not a prompt edit — `strategized` is a kernel phase in DefaultChain.
6. **Ceremony is stakes-routed** via `classify-complexity` (C1–C5): C1 = one confirming question, no melange; C4/C5 = full ritual with melange pass. Same metric routes review gates (flux-drive vs melange). Anti-goal: if the ritual taxes small goals, users route around it back to free text.
7. **Migration of the informal flow**: `/goal` mints the entity; next-goal's ranked candidates become draft charters (seeded, not blank-page); goal-cadence Stop-hook tier reads the entity instead of regex-matching prose. Explicit benefit (f-032): durable entity state replaces the single-sighting Stop-hook trigger.

8. **Terminal gate = a required-properties set, not a sequencing pick (melange verdict on the delegated open question).** The run reframed "which of three sequencings" into "which office is bound to notice" — the load-bearing elements every shape needs:
   - **Standing successor-proposal auditor (f-016, run argmax):** a periodic kernel-level sweep over terminal-adjacent goals (met/abandoned/dormant) raising missing-successor as a first-class defect, independent of the closing session. Complements: `/clavain:next-goal`'s manually-invocable path also audits *other* open goals when invoked (f-030); dormancy detection is one comparison via a `last_run_advanced_at` field updated on any attached run's chain progress (f-031).
   - **Built goal-scoped lease with fencing (f-019/f-023/f-024/f-025/f-029):** neither existing primitive drops in — `sentinel` is a throttle (no holder identity, cannot distinguish quiet from dead; must NOT be the design analogy despite being the primitive already wired into the Stop-hook path) and `lock.Manager` is the right shape at the wrong scope (process-local, 5s-tuned, **no fencing token** — a stale-break permits two fully-witnessed closes of one goal). Build: monotonic fence/generation token checked on every terminal-sequence write; staleness sized to multi-LLM-call close latency, with heartbeat renewal between steps; entity-side fence = compare-and-swap `closing_run_id` via direct UPDATE row-count check (f-001).
   - **Per-step close state (f-002/f-026, cross-lens convergent):** nullable `verified_at / reflected_at / compounded_at / successor_proposed_at` timestamps, never one closed bit — crash mid-sequence is resumable; sentinel alone can't provide this (single boolean, session-scoped).
9. **Tier-independent minimum gates (f-011/f-012/f-014/f-020):** an always-on completion-condition linter (≤4000 chars, surfaced-output-only judgeability) between charter-drafted and `/goal`-mint, implemented as a new GateCondition check type in intercore's evidence model — plus a minimum witness act at every tier before successor-proposal fires. Both decoupled from C1–C5 ceremony depth, closing the C2/C3 zero-gate hole (the likely majority tier).
10. **Chain migration mechanics (f-004/f-006):** new `GoalNativeChain` constant alongside `DefaultChain`; explicit Phases arrays stamped on new runs at cutover; `DefaultChain` untouched so nil-Phases in-flight runs keep resolving. The chain change lands in clavain-cli (Go) first — sprint-advance already round-trips through it; lib-sprint.sh/sprint.md call the new verb, never reimplement.
11. **interphase retirement = paired consumer-migration (f-005):** the new Goal/kernel authority writes the same sideband JSON shape to the same path, or a companion interline bead with an explicit cutover date — never retire the writer while the statusline reader lives.
12. **Charter storage (f-013/f-021/f-018):** the doc is the review surface and must carry the **literal** condition string handed to /goal (never a paraphrase); entity fields are a one-way generated projection at ratification, no independent field-edit path. Amendments are an explicit event distinct from close evidence, with C1–C5 stakes-routing deciding whether re-ratification is required.
13. **Ritual instrumentation (f-008/f-010):** log (agent's first-listed option, user's chosen option) pairs and reuse interspect's calibrate-audit to flag anchoring drift, scoped to C3+ (the C1 recommended-default is an intentional tradeoff); seeded draft charters still run the full research-first pass — the seed bead's description is one more research input, not a shortcut.
14. **Stakes-routing hardening (f-009):** extend `tryComplexityOverride` with a blast-radius keyword bump (delete/migrate/drop-table/auth/prod/irreversible), weighted consistently with the existing ambiguity signals.
15. **Adjacent-tracker verdicts write back (f-022):** a subsume/supersede verdict mutates the adjacent tracker itself (bead status + note) in the same act that ratifies the charter — never left as a downstream-checked assertion.

## Open Questions

*(Refined 2026-07-19 post-melange. Resolved into Key Decisions above: terminal-gate required properties (→ KD 8), charter storage (→ KD 12), interphase retirement (→ KD 11), chain-change landing zone (→ KD 10).)*

- **Terminal-sequence trigger cardinality (f-003):** the one sequencing rule KD 8 leaves open — does the first session-level /goal-met attempt the intercore-level close (acquire lease → run terminal sequence), or is there a separate goal-level completion condition? Decide at plan stage.
- **Lease implementation path (f-015/f-024):** new primitive vs. re-scoped `lock.Manager` code — either way it must add the fence token and cross-session/cross-host durable state; sentinel-relabeling is explicitly ruled out.
- **Adjacent open trackers — subsume/supersede/orthogonal:** sylveste-lbkd (Sprint v2 artifact bus) and sylveste-3kol (Conductor). The melange did not produce the evidence-based verdict (correctly out of its scope); strategy Phase 0.5 enforces it as a hard gate, and per KD 15 the verdict must write back to the tracker beads in the ratification act.
- **Ritual entry surfaces:** wrapper command ending in `/goal`, a `route.md` goal-shaped branch, the sprint head, or all three — untouched by the melange, still open.
- **Never-reached regions (melange caveat — targeted re-probe or plan-review focus):** two constructed lenses yielded zero findings across six rounds: close-evidence *residence time* (does evidence consolidate before a session flush resuspends it?) and *load-path reversibility* (does the strategy-absorption cut land on a load-bearing member; interphase retirement as a mechanical withdrawal sequence). The stakes-scaled bead-binding decision (KD 3) also never got direct adversarial coverage.
- **Concurrency findings are source-read, not race-demonstrated:** f-001/f-025/f-026/f-027 read off struct definitions and call sites. Plan-stage acceptance criteria should include a live two-session same-goal race test to demonstrate the double-witness failure and its fix.
