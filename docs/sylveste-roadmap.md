# Sylveste Roadmap

**Modules discovered:** 84 | **Ledger:** 3,632 total; 3,143 closed; 457 open; 13 in progress; 18 deferred; 1 blocked | **Last updated:** 2026-07-10

**Machine roadmap:** [`roadmap.json`](roadmap.json) | **Detailed P2-P4 inventory:** [`backlog.md`](backlog.md) | **Architecture:** [`CLAUDE.md`](../CLAUDE.md)

> **Operating decision:** remain corrective-first. Do not start new plugins, consolidated MCP work, A:L4/auto-ship, or additive research until the enforced close-gate and the evidence-qualified A:L3 proof pass. Live runtime evidence outranks graph centrality, issue priority, and unit-test completion.

---

## Current Baseline

The 2026-07-10 operating-baseline repair is complete:

- Beads/Dolt/JSONL history reconciled to 3,632 issues without discarding later state.
- Stale claims, one duplicate, four completed epics, and 12 reversed dependency edges repaired.
- Clavain source and installed surfaces canonicalized on the Mac and zklw.
- Clavain structural CI, both Codex installer doctors, Interverse quality scoring, and `ic publish doctor` are green.
- `roadmap.json` and `backlog.md` now regenerate from the canonical tracker rather than erased `iv-*` snapshots.

Two administrative closeouts remain evidence-driven:

- **`sylveste-xogc`** - restoration and integrity guards are delivered; close only after the periodic integrity path is recorded and verified.
- **`sylveste-tizx`** and **`Sylveste-4b5.3`** - this refresh supplies the corrected live roadmap and benchmark IDs; close after the generated artifacts land and the consistency audit passes.

The previous A:L3 display of 8/10 is invalid. SessionEnd advanced blind counters even when calibration failed, normal `/reflect` runs recorded manual intervention, and proof state fragmented by working directory. A:L3 restarts at zero under receipt verification.

---

## Now - Prove the Corrective Substrate

### 1. Enforce live-state closure

**`sylveste-6h7x` (P1)** - Require an installed artifact to boot, report healthy subsystems, handle a live event, produce the expected state delta, and leave no ghost/orphan surface before `phase:done` can close.

This is the highest-leverage live graph node: **8 direct and 10 transitive unblocks**. The corrected dependencies place the gated follow-ons behind it rather than making the close-gate wait on its own consumers.

### 2. Restart and finish A:L3 with real receipts

**`sylveste-myyw` (P0)** - Replace counters with unique sprint/session receipts for routing, gate-threshold, and phase-cost calibration. Failures, timeouts, manual edits, duplicate sessions, or broken hash continuity reset the proof. Close only after 10 consecutive natural no-touch sprints.

Required sequence:

1. Attribute successful phase transitions to the active Intercore run.
2. Give each calibration loop strict `updated`, `valid_noop`, `failed`, or `timeout` outcomes.
3. Verify receipts from history rather than trusting cached counters.
4. Add an open proof child so raw epic close fails until verification passes.
5. Deploy one canary sprint, then observe 10 natural sprints. Synthetic recorder calls do not count.

### 3. Make runtime evidence substantive

- **`Sylveste-4b5.2` (P1)** - after `sylveste-6h7x`, require boot, subsystem health, named startup/DI/connection failure checks, and a post-event state delta.
- **`Sylveste-4b5.11` (P2)** - after `sylveste-6h7x`, refuse false green when parallel agents validate against shared ports, databases, migrations, or environment state.

### 4. Guard calibration against self-confirmation

- **`sylveste-9lp.37` (P1)** - establish an external holdout for each calibration loop, including refresh policy and contamination failure mode.
- **`Sylveste-4b5.1` (P1)** - after the holdout exists, monitor agreement, diversity, and independent defect escape so consensus cannot masquerade as improvement.

---

## Next - After Close-Gate and A:L3

1. **`sylveste-xka6` (P1)** - promote B2 routing from shadow to enforce with observed quality and cost evidence. This unlocks `Sylveste-4b5.15` and `Sylveste-4b5.18`.
2. **`sylveste-i8gp` (P1)** - activate the second cross-subsystem evidence source and prove attribution through the live flywheel.
3. **`sylveste-oyrf` (P0)** - resume longitudinal cost-calibration evidence. Keep **`sylveste-3rod`** as the launch outcome gate, not a general build epic.
4. **`Sylveste-2ss` -> `Sylveste-r8g` -> `sylveste-m71`** - resume the benchmark campaign only when its result feeds a live routing decision.
5. **`sylveste-n2ma` (P1)** - make worktree-first coordination canonical after its prerequisites land.

These outrank standalone feature work because each closes or measures an existing loop rather than creating a new surface.

---

## Later - Explicitly Frozen

- **`sylveste-7505`** - consolidated Interverse MCP server. Re-evaluate process savings and tool parity after the corrective gates pass; do not start implementation during the freeze.
- **`sylveste-7aj8` / `sylveste-lgci`** - autonomous skill calibration and formal A:L4 evaluation remain post-v0.7 work. `sylveste-ysny` must first show that the scoring signal is dense enough to trust.
- **`Sylveste-4b5.14`, `Sylveste-4b5.15`, `Sylveste-4b5.16`, `Sylveste-4b5.18`, `Sylveste-4b5.20`** - additive or measurement-gated experiments remain behind their corrected prerequisites.
- **`sylveste-3kol`** - broad parallel orchestration follows the live close-gate and canonical worktree contract.
- New plugins and open-ended research remain out of scope until the Now exit conditions are observed, not merely implemented.

---

## Prioritization Rules

1. **Observed closure before expansion.** Installed, live, and state-changing evidence is required for completion.
2. **Finish active corrective work first.** A nearly-complete gate outranks a new high-centrality feature.
3. **Unblocking beats inventory priority.** Dependency direction and transitive unlocks matter more than a raw P0/P1 label.
4. **Bad evidence blocks autonomy.** Sparse, saturated, self-referential, or unattributed signals remain read-only.
5. **Frozen means frozen.** Graph tools may rank additive work highly; the operating freeze is the higher-order constraint.

---

## Artifact Contract

- `docs/roadmap.json` is the machine-readable rollup of all non-closed tracker items. Its `now`, `next`, and `later` phases map from P0/P1, P2, and P3/P4.
- `docs/backlog.md` is generated from the same tracker state and contains every live P2-P4 item grouped by module. Do not hand-edit it.
- This document is the curated strategic view. Keep **Now to six or fewer outcomes** and move full inventory detail to the generated backlog.
- Regenerate machine artifacts with `scripts/sync-roadmap-json.sh docs/roadmap.json docs/backlog.md`, then run `scripts/audit-roadmap-beads.sh` before publishing.

---

## Exit Conditions

The corrective freeze ends only when:

- `sylveste-6h7x` blocks closure on missing live-runtime evidence and is observed firing.
- `sylveste-myyw` verifies 10 consecutive unique natural sprint receipts across all three loops.
- Both hosts retain one canonical source/install surface and zero installer or publish-doctor errors.
- Tracker integrity and roadmap generation remain reproducible from the canonical zklw state.

Until then, the roadmap is deliberately narrow.
