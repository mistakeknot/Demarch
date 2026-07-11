# Sylveste Roadmap

**Modules discovered:** 84 | **Ledger:** 3,662 total; 3,172 closed; 458 open; 13 in progress; 18 deferred; 1 blocked | **Last updated:** 2026-07-11

**Machine roadmap:** [`roadmap.json`](roadmap.json) | **Detailed P2-P4 inventory:** [`backlog.md`](backlog.md) | **Architecture:** [`CLAUDE.md`](../CLAUDE.md)

> **Operating decision:** remain corrective-first. The live close-gate is enforced; do not start new plugins, consolidated MCP work, A:L4/auto-ship, or additive research until the evidence-qualified A:L3 proof and the remaining P1 authorization-provenance gaps pass. Live evidence outranks graph centrality, issue priority, and unit-test completion.

---

## Current Baseline

The 2026-07-10 operating-baseline repair is complete:

- Beads/Dolt/JSONL history reconciled to 3,633 issues without discarding later state.
- Stale claims, one duplicate, four completed epics, and 12 reversed dependency edges repaired.
- Clavain source and installed surfaces canonicalized on the Mac and zklw.
- Clavain structural CI, both Codex installer doctors, Interverse quality scoring, and `ic publish doctor` are green.
- `roadmap.json` and `backlog.md` now regenerate from the canonical tracker rather than erased `iv-*` snapshots.
- The receipt and runtime-close pipeline is published and deployed as Clavain 0.6.266, Intercore 0.3.4, Interstat 0.3.1, and Interspect 0.1.22 on both hosts.
- zklw is the sole authorization signer and canonical writable ledger; the Mac holds a read-only verifier snapshot and no private key. The repaired schema-35 ledger and both real managed operations verify with zero failed signatures.
- **Recently completed:** `sylveste-6h7x`, `Sylveste-4b5.2`, `Sylveste-4b5.11`, and `Sylveste-rkm` closed after exact installed canaries, cross-host doctors, signed-history repair, and real managed close/push receipts.

One integrity closeout remains evidence-driven:

- **`sylveste-xogc`** - restoration and integrity guards are delivered; close only after the periodic integrity path is recorded and verified.

**`sylveste-tizx`** and **`Sylveste-4b5.3`** are closed after the corrected artifacts landed and the consistency audit passed.

The previous A:L3 display of 8/10 is invalid. SessionEnd advanced blind counters even when calibration failed, normal `/reflect` runs recorded manual intervention, and proof state fragmented by working directory. A:L3 restarted at zero under receipt verification.

---

## Now - Finish the Corrective Proof

### 1. Finish A:L3 with natural receipts

**`sylveste-myyw.16` (P0)** - Observe 10 consecutive natural no-touch sprints whose Intercore run, Bead closure, artifact chain, and routing/gate-threshold/phase-cost outcomes all verify.

Both deployed proof epochs are currently **0/10**. This is deliberately observational: synthetic recorder calls and direct counter manipulation do not count. Continue normal corrective sprints and let valid SessionEnd receipts accumulate; a failure, timeout, duplicate, manual intervention, or broken hash chain resets the proof.

### 2. Harden signed-history provenance

- **`sylveste-mn13` (P1)** - cryptographically anchor the three retained pre-signing rows so changing a signed record to `sig_version=0` cannot evade verification.
- **`sylveste-5xpi` (P1)** - add signer key IDs, archived public-key lookup, and enforced quarantine before enabling key rotation.

The safe single-signer baseline is live: zklw owns the only private key and writable ledger, Mac verification is read-only, and all 218 current authorization rows pass audit. These P1 items close the remaining database-tamper and future-rotation gaps rather than weakening that topology.

### 3. Guard calibration against self-confirmation

- **`sylveste-9lp.37` (P1)** - establish an external holdout for each calibration loop, including refresh policy and contamination failure mode.
- **`Sylveste-4b5.1` (P1)** - after the holdout exists, monitor agreement, diversity, and independent defect escape so consensus cannot masquerade as improvement.

### 4. Make deployment identity self-repairing

- **`sylveste-npc5` (P2)** - verify version, install path, Git commit, and binary digest atomically after Claude plugin updates; fail or perform a data-preserving repair when commit metadata is stale.
- **`sylveste-dan6` (P2)** - design authenticated remote signing or conflict-safe canonical replication before permitting Mac-originated managed operations.
- **`sylveste-otv9` (P2)** - archive or namespace both historical home ledgers without losing their real run evidence.
- **`sylveste-4jmp` (P2)** - make the Interverse quality sweep frozen and non-mutating; keep variable PQS values as telemetry rather than a deterministic gate.

`bv --robot-next` ranks the additive `sylveste-bcok` integration bridge by its
seven downstream unblocks, while robot triage also surfaces `sylveste-22oi`
and `sylveste-7505`. Those graph scores do not supersede the observed proof
and audit failures above; all three remain behind the corrective freeze.

---

## Next - After A:L3

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

- `sylveste-myyw` verifies 10 consecutive unique natural sprint receipts across all three loops.
- Managed-close policy audit verification reports zero unsigned or invalid post-cutover rows.
- The shipped runtime close-gate remains green in exact installed canaries and its recurring audit.
- Both hosts retain one canonical source/install surface and zero installer or publish-doctor errors.
- Tracker integrity and roadmap generation remain reproducible from the canonical zklw state.

Until then, the roadmap is deliberately narrow.
