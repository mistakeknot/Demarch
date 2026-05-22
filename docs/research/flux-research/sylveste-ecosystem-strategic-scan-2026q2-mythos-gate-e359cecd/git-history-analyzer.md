---
title: "Sylveste Git History Strategic Scan: 90 Days to Mythos Launch (2026-02-22 → 2026-05-22)"
date: 2026-05-22
session: "git-history-analyzer"
scope: "Last 90 days of commit history; identifies shipping patterns, strategic pivots, platform debt"
---

## Summary

Over the past 90 days (1,345 commits), Sylveste shows **high execution velocity on proof-of-concept work (lattice, F4-F6 ingestion, Auraken→Hermes pivot, Codex hardening) but critical architectural decisions still pending for Mythos gate**. The microrouter heuristic measurement (`7f224cca`, 2026-05-08) closed a major epic with measured evidence (6.2% traffic coverage) — a rare, vettable pivot signal. Conversely, DeepSeek V4 spike (`8b95feed` → 2026-05-17) opened a high-stakes orthogonal bet with hard wall-clock kill rules (EOD 2026-05-19) that binds the remaining time budget. Platform debt from nested-repo git corruption (`32f1de58`) required post-hoc wrapper fixes, and concurrent-agent session bundling has caused repeated reverts (`15f9d3fa`, `031c83b6`).

---

## 1. What Got Shipped vs. Abandoned

### Shipped (fully closed beads, multi-week investment)

**Lattice v0c architectural refinement** (`d5d9ce9a`, `45cdb158`, closing 2026-05-06):
- v0c.1: unqualified slash-command resolution (deterministic precedence: same-plugin → clavain → cross-plugin match)
- v0c.5: file_contract identity semantics (`./interwatch/drift.json` as first-class entity)
- v0c.6: plugin unclassified reason annotations (`non_pillar_app` for interblog)
- v0c.7: consume edge fallback logic
- Shipped consumables: 114 → 137 consume edges (+20%), down to 3 cross-plugin collisions, 1 unclassified plugin
- **Receipt**: architecture report (`cd interverse/lattice && uv run python scripts/architecture_report.py --contracts --leverage`)

**F4-F6 ingestion sprint** (F5 `a7ae35c3`, F6a `73ccc938`, closing 2026-05-06):
- F5: curator CLI + threshold-sweep harness; calibration corpus v1; 14 tie-break interviews confirmed, 2 flipped
- F6a: pre-registration + 30-diff held-out A/B harness scaffolding (signed off `73ccc938`)
- F6b: next directive (sylveste-g939), execute-deferred
- **Live signal**: session reflection at `cc23a1ec` with F1-F6 full sprint KPI closure

**Thread A + git wrapper** (`32f1de58`, closing 2026-05-06):
- Root cause: nested-repo `git status` corruption when session wrapper cwd-check missed `.git/` hierarchy
- Fixed in interlock 0.2.14 (walk-up detection); patched live in session env
- **Downstream impact**: all concurrent sessions' git indices stabilized; 2 prior bundled-work recovery commits (`15f9d3fa`, `031c83b6`) now prevented

**Skill router phase 2** (`1c0661a0`, `a9f1958e`, 2026-05-06):
- Deterministic slash-command prefix router (scan first 200 chars for `/X`)
- Upstream feature request doc (skill-router scope clarification)
- Small PR deliverable; enables follow-on phases

**Microrouter .19.8 design revision** (`110d5a60` → `7fb28359`, 2026-05-06):
- Absorbed P0-B/C/D/E + inference-path subscription leverage
- Later killed per measurement (`7f224cca`)

### Abandoned (killed with evidence)

**Microrouter .19 epic — KILLED** (`7f224cca`, 2026-05-08):
- **The pivot**: heuristic coverage measurement revealed only 6.2% of actual subagent traffic
- **Evidence receipt**: `docs/microrouter/.19.1 Phase 1 kill` commit annotation
- **Post-kill status**: artifact marked SUPERSEDED (`a64b9adc`), architecture deferred to β with `active-deferral` state fields (`21ee907f`)
- **Scope remaining**: heuristic baseline first, conditional learned router (reframed in `9e28c395`, 2026-05-05)

**Interflect hook preview** (closing `3012410e`, 2026-05-06):
- Full-loop dogfood documented (`3012410e`); v0 lane closed (`f729b09f`)
- Verdict: Interflect retrospective compounding defined (`a58f3575`), but scaffold-stage deprioritized in face of lattice + F5/F6 completion

**git-autosync** (killed structurally, `2269b804`, 2026-04-15):
- Removed autosync marker; no longer actively pulled in session startup

---

## 2. Strategic Pivots (With Receipt)

### Pivot 1: Microrouter Heuristic Kill (2026-05-08)

**Evidence-driven closure**:
- Commit `610d996a` + `bff5a318` (2026-05-11): escalation regex tightened to measure coverage more accurately
- Commit `7f224cca` (2026-05-08): final measurement "heuristic only covers 6.2% of subagent traffic"
- **Why it pivoted**: original hypothesis (heuristic covers most routing) was falsified by real traffic measurement
- **Follow-on**: architecture deferred to β (commits `21ee907f` + `a64b9adc`); .19.8 design absorbed into conditional learned router instead (`9e28c395`)
- **Ground truth**: this is the cleanest evidence-based pivot in the 90-day window

### Pivot 2: Auraken → Hermes Agent Overlay (tracked, not Git-visible here)

**Referenced in memory**: `project_auraken_hermes_pivot.md` indicates shift from Go migration to Hermes Agent layering. No direct commits in this repo's scope, but **Codex hardening work** (`7a17c9bd`, 2026-05-21) and **cloud Opus tier routing** (`029a17ec`, 2026-05-17) are downstream signals of this pivot.

### Pivot 3: Launch Deferral (Mythos alignment)

**Referenced context**: launch moved 3 months to align with next Claude Opus (Mythos). Commits show steady planning work toward launch-gate blockers (OYRF public site alignment `84fa2584` → `16d24808`, 2026-05-06), but no hard "we are pushing launch to August" commit in this window.

### Pivot 4: DeepSeek V4 Spike (Orthogonal, high-stakes)

**Opened 2026-05-14** (`462699f2`), **Day-3 CPU-ref forward scheduled 2026-05-17** (`8b95feed`):
- Parallel research in `/Users/sma/projects/flash-moe/` (separate repo)
- **Kill rule (hard)**: EOD calendar day 5 (2026-05-19) → if logit cosine sim < 0.999 on top-10, STOP
- **Fallback**: Sylveste-bov (5 vs 12.9 tok/s perf regression) remains the no-go if V4 parity fails
- **Status as of 2026-05-22**: spike is live, approaching kill-rule boundary

---

## 3. Load-Bearing Systems (Multi-week investment, steady commits)

**Lattice (architecture recovery)**:
- v0c refinements span 2026-04-27 → 2026-05-06 (10 days, multiple bead closures)
- Stabilized contract semantics, leverage reporting, collision triage
- Still accumulating work: v0c.2 (MCP tool granularity), v0c.3 (service entity type), v0c.4 (periodic re-harvest hook) open

**F4-F6 ingestion pipeline**:
- Spans 2026-04-21 → 2026-05-06 (~2 weeks)
- Curator CLI, threshold sweep, calibration corpus, A/B harness scaffolding
- Multiple beads closed; sprint reflection captured (`cc23a1ec`); next phase (execute) deferred

**Skill router + lattice integration**:
- Unqualified slash resolution (v0c.1) unlocked by skill router commits (`1c0661a0`, `a9f1958e`)
- Tight dependency: slash command resolution blocked until router could introspect plugin surface

**Codex + cloud routing**:
- Cloud Opus tier defaulting (`029a17ec`, 2026-05-17)
- Codex Claude hardening (`7a17c9bd`, 2026-05-21) — ongoing tuning; not fully resolved
- Part of Auraken→Hermes pivot fallout

---

## 4. Platform Debt & Friction Signals

**Nested-repo git corruption (now fixed)**:
- Root cause: session git wrapper missed `.git/` hierarchy walk-up
- Manifested as missing-hash errors across monorepo + nested repos (`interwatch`, `interpath`, `lattice`, `interlock`, `intership`)
- **Recovery cost**: 2 bundled-work recovery commits (`15f9d3fa`, `031c83b6`); fix landed in interlock 0.2.14
- **Lesson captured**: `docs/handoffs/2026-05-06-thread-a-shipped-and-git-wrapper-fixed.md` (lines 49-66)
- **Status**: FIXED; all nested-repo branches now push cleanly

**Concurrent-agent session bundling**:
- F5/F6a/3xl3 sprint commits landed in parallel; staged deletions/modifications carried through
- Commits `15f9d3fa` and `031c83b6` restore work that was bundled unintentionally
- **Defensive pattern now documented**: `git reset HEAD` before staging, then `git add <explicit-paths>`, then `git diff --cached --name-only` to verify
- **Ongoing friction**: no structural fix; relies on manual discipline per session

**Plugin validation regex thrashing**:
- Commit `610d996a` (tighten escalation regex)
- Commit `7f5590ae` (revert the tightening)
- Both 2026-05-11 (same day); regex sensitivity oscillating around correct measurement threshold
- **Lesson**: measurement heuristic itself needs a control run before and after any tightening

**Beads Dolt drift** (mentioned in handoff):
- `f2144001` + `4fe952c0` (2026-04-15): guard Beads JSONL Dolt drift
- Parallel sessions mutating `.beads/issues.jsonl` unsafely; non-idempotent exports
- **Defensive practice**: `bd export > .beads/issues.jsonl` before every commit to keep backups in sync

---

## 5. Handoffs as Ground Truth

**Latest handoff** (`2026-05-06-thread-a-shipped-and-git-wrapper-fixed.md`):
- Thread A complete: 10 beads closed (lattice v0c.{1,5,6,7}, git wrapper, others)
- P0 queue shows ~15 open epics; Track B6 routing, Auraken→Hermes, Mythos readiness are warm
- Lattice v0c.4 (periodic re-harvest) next smallest
- Open blocker: `sylveste-dsbl` (F3 meta-tracker) stays open; not directly actionable until F4 resumes

**Day-3 DeepSeek spike handoff** (`2026-05-17-deepseek-v4-spike-day3-kickoff.md`):
- Baseline logit capture scripting (Day-3)
- Wall-clock kill rule EOD 2026-05-19 non-negotiable
- On failure: RunPod H200 rental fallback (~$5-10 cost, requires user go-ahead)
- Dead ends: MLX checkpoint not loadable by transformers v5.8.1; Day-1 & Day-2 architecture hypotheses all falsified

**Pre-handoff sprint closure** (`2026-05-06-3xl3.1-flux-explore-teams-planned-execute-deferred.md`):
- Flux-explore --teams brainstorm + PRD + plan landed (execute deferred)
- Shows strategic planning for next cohort (teams-scale dispatch), but not yet shipped

---

## Recent Strategic Signal (Last 30 Days: 2026-04-22 → 2026-05-22)

### What the code is actually betting on

1. **Lattice architectural stability is critical path to Mythos gate**: v0c.1-7 shipped on schedule; leverage reporting unblocked skill router. This is load-bearing for plugin discovery at launch.

2. **F4-F6 ingestion + A/B infrastructure is approaching readiness**: F5 fully closed, F6a signed off, F6b deferred for execute phase. Sprint reflection (`cc23a1ec`) shows this work is measurable and closing on schedule.

3. **Microrouter is NOT shipping with Mythos in original form**: measurement-driven kill (`7f224cca`, 6.2% coverage) flipped the entire strategy to "heuristic baseline first, conditional learned router β". This is evidence-based but represents a 6-week sunk investment being redirected.

4. **Codex hardening and cloud Opus tier routing are active unresolved threads**: commits `7a17c9bd` (2026-05-21) and `029a17ec` (2026-05-17) show ongoing tuning. Neither is shipped; both are part of Auraken→Hermes pivot fallout.

5. **DeepSeek V4 parity is a high-variance orthogonal bet expiring in days**: if Day-5 parity check (EOD 2026-05-19) hits logit cosine sim < 0.999, spike kills. **This binding decision point is happening within the reporting window.** Sylveste-bov (lower-perf fallback) is the safety ratchet.

### What the backlog says vs. what commits show

- **Backlog claim**: 15 P0 epics in `bd list --status open --priority 0`
- **Commit reality**: only lattice v0c, F4-F6, skill router, microrouter (now β-deferred), and flash-moe spike are actively shipping. Others are tracked but not actively moving.
- **Mythos readiness**: launch blockers (OYRF public site DNS/pages activation) are tracked as beads (`6c7f288b`, `1f89ae85`) but not closed; no critical-path urgency signal in May commits.

### Platform debt that could delay Mythos

1. **Nested-repo git corruption is FIXED but fragile**: all downstream repos (flash-moe, interstream, mistakeknot/lattice, etc.) must use `env -u GIT_INDEX_FILE git -C ...` to avoid triggering the old bug. This is now a durable session-env pattern, but any new nested repo needs explicit documentation.

2. **Concurrent-agent bundling lacks structural mitigation**: defensive git discipline per session is working, but grows as team size increases. Consider pre-commit hook or post-rebase verification for multi-agent scenarios.

3. **Beads Dolt drift is managed but non-idempotent**: `bd export` before commit is now documented practice, but the system doesn't prevent accidental non-compliance. No automation in place.

4. **DeepSeek V4 spike introduces calendar-clock risk**: 2026-05-19 is a hard wall; if the CPU-ref forward script hits timeout, RunPod rental ($5-10) needs user approval mid-sprint.

---

## Methodology Note

Analysis based on:
- `git log --since=2026-02-22 --oneline` (1,345 commits)
- Strategic commits grouped by theme (microrouter, lattice, F4-F6, skill-router, Codex, OYRF)
- Handoff documents (`docs/handoffs/2026-05-*.md`) as ground truth for session directives and dead ends
- Memory file (`project_*_*.md`) for context on pivot decisions

