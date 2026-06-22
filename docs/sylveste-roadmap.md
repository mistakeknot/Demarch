# Sylveste Roadmap

**Modules:** ~70 (see Ecosystem Snapshot) | **Beads:** 3,594 total; 476 open/in-progress (12 P0, 119 P1, 229 P2, 107 P3) | **Last updated:** 2026-06-21
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json) — auto-generated superset of roadmap-placed items only (fewer than `bd stats` totals, which track all beads).

> **2026-06-21 re-baseline** (`sylveste-tizx`). Re-grounded against live beads. **What graduated since 2026-05-29:** the entire Clavain gate-correctness chain shipped — `sylveste-n35t`/`scx1`/`0ly7`/`qf1k` all CLOSED (the fail-open chain is fixed). `sylveste-ohb8` (landed_changes integrity) CLOSED. `sylveste-ioe7` (interlab→interspect mutation loop) CLOSED/LIVE 2026-06-21 — it is now a wired loop, not a future item. **New this cycle:** an agentic-orchestration/coding frontier review (`Sylveste-4b5`, 23 children) mapped the external frontier against the backlog; its headline *reinforced* the corrective-first stance rather than overturning it. **Stance unchanged:** highest-leverage work is *corrective, not additive* — fix the measurement substrate (roadmap drift + ghost infrastructure) before building more; the close-gate `sylveste-6h7x` is the spine ~10 frontier survivors gate on.
>
> **2026-05-29 re-baseline.** Re-grounded after the 2026-05-29 ecosystem analysis (`docs/research/ecosystem-analysis-2026-05-29/`, epic `sylveste-owjn`) found the prior 2026-03-27 version citing phantom `iv-*` IDs as live blockers. The `iv-` namespace was erased in two beads DB-reinit events; items were recovered under `sylveste-*` IDs (see "Corrected since last update").

---

## Now — Frontier Priorities

### P0/P1: Measurement-substrate correctness (the "ghost infrastructure" fix)
The dominant pattern across the ecosystem: infrastructure closes at *unit-test-green*, not *wired-to-production-observed*, so "done" beads aren't actually live. Compounded by beads data loss that makes "done" unreportable. Fix the substrate first. Epic: `sylveste-owjn`.
- **sylveste-tizx** (P1) Re-baseline this roadmap against live beads — *this document*; ongoing discipline, not one-shot.
- **sylveste-6h7x** (P1) Close-gate: `phase:done` requires integration-test-pass vs a live server + orphan/ghost scan. Attacks the *generator* of ghost infra.
- **sylveste-xogc** (P1) Beads durability: JSONL→DB restore + integrity check. Stops the recurring data loss that invalidated this roadmap.

### ✅ SHIPPED: Clavain gate correctness (the fail-open chain is fixed)
Clavain *was* mis-gated — review/test/ship gates failed *open*, so unreviewed code could ship. **The whole chain closed 2026-06-18→20:**
- **sylveste-n35t** (was P0) ✅ Positive completion sentinel replaces the four-layer fail-open chain (flux-engine triage / synthesize "no file = no findings" / quality-gates `cp … || true` / enforce-gate `return nil`).
- **sylveste-scx1** ✅ Safety gates inverted — degraded-modes as an active breaker.
- **sylveste-0ly7** ✅ `verdict_clean` ship gate implemented (Go evaluator) + ship stage set to `enforce`.
- **sylveste-qf1k** ✅ `tests_passed`/`vetted` decoupled from orchestrator assertion.

> The 2026-06-21 frontier review (`Sylveste-4b5`) confirms this fix: external-verifier-beats-self-critique (Kambhampati) and "silent failures are the unsolved problem" (VerifyMAS) both name a fail-open gate as the exact anti-pattern. With the chain closed, the *next* substrate priority is making the close-gate (`sylveste-6h7x`) a real enforced gate — see below.

### P1: Frontier delta — the close-gate is the spine
- **sylveste-4b5** (P1, epic, 23 children) Agentic-frontier roadmap delta. 91-agent review of the mid-2026 orchestration/coding frontier → mapped vs backlog → adversarially verified (44 credible → 24 survived). **Top items, all corrective:** consensus-trap monitor on the now-live `ioe7` loop (`4b5.1`, blocks on holdout register `9lp.37`); make runtime-health/state-delta the *substance* of the `6h7x` close-gate (`4b5.2`); SWE-bench roadmap-drift fix (`4b5.3`); native-worktree retirement audit folded into `n2ma` (`4b5.4`). Full delta: `docs/research/2026-06-21-agentic-frontier-roadmap-delta.md`.

### P1: Wire ONE loop end-to-end (make "wired" the unit of progress)
- **sylveste-xka6** (P1) Promote B2 complexity routing dispatch-side **shadow → enforce** + quality-evidence. Callers ARE wired (`sylveste-2aqs`/`magy` closed) but in caller-local shadow; the punt was enforce. Cleanest verified narrow loop to close — and the frontier names it the hard dependency for two additive levers (cache-aware cost `4b5.18`, pass@k escalation `4b5.15`).
- **sylveste-i8gp** (P1) Evidence-pipeline flywheel second source — **UNBLOCKED** (deps `sylveste-5qv9` + `sylveste-xcn4` closed).
- ~~**sylveste-ohb8** `landed_changes` referential-integrity audit~~ → ✅ **CLOSED 2026-06-21** (nullable FKs / missing `REFERENCES` addressed).

### P1 (corrected — was citing phantom IDs)
- **SWE-bench / benchmark harness** — ⚠️ the prior `Sylveste-ynh`/`9lx`/`6i0`/`sdk0` citations were **PHANTOM** (no live beads; `ynh7` is a closed token-optimization audit, not SWE-bench). The **real** live harness work is the interfer Flash-MoE benchmark suite: **`sylveste-2ss`** (epic, in-progress) → `b7j` (SWE-bench Lite + LiveCodeBench-v6 wiring, closed), **`r8g`** (SWE-bench Lite runner, open), capstone **`m71`** (Pareto speed-vs-quality, open). Frontier caveat (`4b5.3`/`4b5.19`): SWE-bench Verified is reportedly contaminated — the LiveCodeBench-v6 (time-segmented) choice already partly mitigates; do not swap to SWE-bench Pro until the harness feeds a live routing decision.

### Corrected since last update (was wrong / now resolved)
- **iv-ho3** "Factory Substrate, in progress 120 days" → **DONE.** Recovered as `sylveste-5qv9`, CLOSED 2026-04-10 (CXDB built, integration test passing).
- **iv-3ov** (evidence pipeline wiring) → **DONE.** Recovered as `sylveste-xcn4`, CLOSED 2026-04-28.
- **Measurement-hardening chain** `iv-ho3→iv-296→iv-g36hy→iv-3ov` → **2/4 links shipped** under new IDs; not a pristine queued chain.
- **iv-jgdct** "B2 fully built, zero callers" → **STALE.** Callers shipped in shadow (`sylveste-2aqs`/`magy`). Real work is shadow→enforce (`sylveste-xka6`).
- **iv-v5ayb** "go.mod replace breaks interlock/intermap" → **MOSTLY DONE.** interbase/go published (`v0.1.1`, no replace); only `lattice→attp` local replace residual (`sylveste-s01c`).
- **"7 dead plugins"** (intercept, intermix, interpub, intersense, intersynth, intertrack, intersite) → **REFUTED.** Zero are dead; intersense already self-archived; interpub powers the marketplace; intersite drives the GSV pipeline. **Do not archive.**
- **sylveste-g3a / interpath-witness** (cited in prior planning) → **PHANTOM** (no live bead).

---

## Next — Strategic Themes (P2)

Medium-term direction. Full item inventory: [backlog.md](backlog.md). New items below carry live bead IDs from the 2026-05-29 analysis.

1. **Skaffen Sovereign Agent** — Go-native second runtime (OODARC loop, masaq TUI, intercore bridge). **Strategic caveat (sylveste-104h):** Skaffen's evidence path lacks `run_id` attribution and risks reproducing the unwired-evidence ghost in Go. Gate Skaffen's evidence layer on consuming Clavain's *proven* schema after one loop is live — don't mint a parallel silo. Relates to `sylveste-benl`.

2. **Adaptive Routing (shadow → enforce)** — Not "build" but "wire": promote B2 to enforce (`sylveste-xka6`), then interspect calibration. The learning loop that makes the system cheaper over time.

3. **Autonomous Improvement Loop** — ✅ **WIRED 2026-06-21** (`sylveste-ioe7` CLOSED): interlab `is_new_best` mutations now drain into interspect as pattern-kind evidence and are read by the classifier. The loop is live. **Open follow-on:** nothing yet monitors its verifier-vs-generator agreement trend, so the consensus-trap breaker (`sylveste-4b5.1`, P1) is the corrective next step — gated on a frozen external holdout (`sylveste-9lp.37`) so the trend is interpretable.

4. **Clavain control-loop quality** — Brainstorm-summary feedforward into plan review (`sylveste-td2o`); local plan-phase verification in `/work` + `/execute-plan` (`sylveste-ungg`). Cheaper, non-redundant review.

5. **interverse hygiene + DX** — Safe quick wins: root `go.work`, 3 missing READMEs, intersearch `DEPENDENCIES.md`, `HOOKS-REGISTRY.md` (`sylveste-qhn1`); close `lattice→attp` (`sylveste-s01c`). Skill-description boilerplate trim via interskill:audit (`sylveste-z0pc`, ~3-4kt/session).

---

## Later — Horizon (P3)

Longer-term directions, not yet scoped into specific items. Full inventory: [backlog.md](backlog.md).

- **Kernel library bindings** — Native client bindings for intercore (blocked by intent router)
- **Continuous dispatch** — Daemon mode for always-on agent orchestration
- **Workspace isolation** — Git worktree per task for parallel safe execution
- **Runtime budget enforcement** — Real-time token budget checks mid-execution
- **Intercom Go rewrite** — Port Rust daemon to Go + Skaffen integration (Sylveste-mvy)
- **Mycroft fleet orchestrator** — Multi-agent fleet coordination (brainstorm complete)
- **Evaluation infrastructure** — intermix harness (planned), model-capability sensitivity benchmarks, verifier context patterns
- **Exploration-exploitation strategy** — Skaffen Orient phase (Sylveste-e0t)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads (context) |
|--------|----------|---------|--------|---------|----------------------|
| agent-rig | core/agent-rig | 0.1.0 | early | no | n/a |
| autarch | apps/autarch | 0.1.0 | active | yes | n/a |
| clavain | os/clavain | 0.6.253 | active | yes | n/a |
| interblog | apps/interblog | 0.1.3 | early | no | n/a |
| interband | core/interband | — | planned | no | n/a |
| interbench | core/interbench | — | planned | no | n/a |
| intercache | interverse/intercache | 0.2.0 | early | no | n/a |
| interchart | interverse/interchart | 0.1.8 | early | no | n/a |
| intercheck | interverse/intercheck | 0.2.2 | active | yes | 4 |
| intercom | apps/intercom | 1.1.0 | active | shipped | n/a |
| intercore | core/intercore | — | active | yes | n/a |
| intercraft | interverse/intercraft | 0.1.2 | active | yes | 4 |
| interdeep | interverse/interdeep | 0.1.6 | early | no | n/a |
| interdev | interverse/interdev | 0.2.0 | active | yes | 4 |
| interdoc | interverse/interdoc | 5.2.1 | active | yes | 4 |
| interfer | interverse/interfer | 0.1.0 | early | no | n/a |
| interfluence | interverse/interfluence | 0.2.10 | active | yes | 4 |
| interflux | interverse/interflux | 0.2.70 | active | yes | n/a |
| interform | interverse/interform | 0.1.0 | active | yes | 4 |
| interhelm | interverse/interhelm | 0.2.0 | active | yes | n/a |
| interject | interverse/interject | 0.1.14 | active | yes | 4 |
| interkasten | interverse/interkasten | 0.4.25 | active | no | n/a |
| interknow | interverse/interknow | 0.1.5 | early | no | n/a |
| interlab | interverse/interlab | 0.4.8 | active | yes | n/a |
| interlearn | interverse/interlearn | 0.1.0 | active | yes | 8 |
| interleave | interverse/interleave | 0.1.2 | early | no | n/a |
| interlens | interverse/interlens | 2.2.4 | active | yes | 4 |
| interline | interverse/interline | 0.2.13 | active | yes | 4 |
| interlock | interverse/interlock | 0.2.10 | active | yes | n/a |
| interlore | interverse/interlore | 0.1.0 | early | no | n/a |
| intermap | interverse/intermap | 0.1.6 | active | yes | 7 |
| intermem | interverse/intermem | 0.2.4 | active | yes | n/a |
| intermix | interverse/intermix | 0.1.11 | active | no | n/a |
| intermonk | interverse/intermonk | 0.1.1 | early | no | n/a |
| intermute | core/intermute | — | active | yes | n/a |
| intermux | interverse/intermux | 0.1.5 | active | yes | 4 |
| intername | interverse/intername | 0.1.2 | early | no | n/a |
| internext | interverse/internext | 0.1.5 | active | yes | 4 |
| interpath | interverse/interpath | 0.3.2 | active | yes | 4 |
| interpeer | interverse/interpeer | 0.1.0 | early | no | n/a |
| interphase | interverse/interphase | 0.3.17 | active | yes | 4 |
| interplug | interverse/interplug | 0.1.5 | early | no | n/a |
| interpub | interverse/interpub | 0.1.8 | active | yes | 4 |
| interpulse | interverse/interpulse | 0.1.5 | early | no | n/a |
| interrank | interverse/interrank | 0.3.0 | active | no | n/a |
| interscribe | interverse/interscribe | 0.1.1 | early | no | n/a |
| intersearch | interverse/intersearch | 0.2.1 | active | yes | 4 |
| ~~intersense~~ | ~~interverse/intersense~~ | — | archived | — | — |
| intership | interverse/intership | 0.3.1 | early | no | n/a |
| intersight | interverse/intersight | 0.1.5 | early | no | n/a |
| interskill | interverse/interskill | 0.1.3 | early | no | n/a |
| interslack | interverse/interslack | 0.1.0 | active | yes | 4 |
| interspect | interverse/interspect | 0.1.21 | active | [vision](./interspect-vision.md) | n/a |
| interstat | interverse/interstat | 0.2.27 | active | yes | 4 |
| intersynth | interverse/intersynth | 0.1.9 | early | no | n/a |
| intertest | interverse/intertest | 0.1.2 | early | no | n/a |
| intertrace | interverse/intertrace | 0.1.2 | early | no | n/a |
| intertrack | interverse/intertrack | 0.1.4 | active | yes | n/a |
| intertree | interverse/intertree | 0.1.2 | early | no | n/a |
| intertrust | interverse/intertrust | 0.1.3 | early | no | n/a |
| interverse | root | — | active | yes | n/a |
| interwatch | interverse/interwatch | 0.3.3 | active | yes | 5 |
| marketplace | core/marketplace | — | active | yes | n/a |
| skaffen | os/skaffen | — | active | yes | n/a |
| tldr-swinton | interverse/tldr-swinton | 0.7.17 | active | yes | n/a |
| tool-time | interverse/tool-time | 0.3.10 | active | yes | n/a |
| tuivision | interverse/tuivision | 0.2.0 | active | yes | 4 |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Keeping Current

```
# Regenerate this roadmap JSON from current repo state
scripts/sync-roadmap-json.sh docs/roadmap.json

# Regenerate via interpath command flow (Claude Code)
/interpath:roadmap    (from Interverse root)

# Propagate items to subrepo roadmaps
/interpath:propagate  (from Interverse root)
```

---

**Moved to separate files:** Module highlights → [sylveste-reference.md](sylveste-reference.md). Research agenda, cross-module dependencies, modules without roadmaps → [backlog.md](backlog.md).
