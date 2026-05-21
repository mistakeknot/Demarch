---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-18-gate-threshold-calibration-v2-brainstorm.md"
target_description: "Gate-tier calibration v2 — append-only outcome log + schema migration + rolling-window algorithm, SessionEnd trigger"
tracks: 3
track_a_agents: [fd-schema-migration-backward-compat, fd-append-log-cursor-correctness, fd-rolling-window-algorithm-soundness, fd-go-subcommand-plumbing, fd-sessionend-hook-integration]
track_b_agents: [fd-spc-control-limit-stability, fd-credit-model-psi-drift, fd-diagnostic-sensitivity-tuning, fd-ab-platform-log-integrity]
track_c_agents: [fd-horology-isochronism-drift, fd-lighthouse-logbook-cursor-integrity, fd-glassmaking-annealing-tier-promotion, fd-waqf-accounting-long-duration-reconciliation]
date: 2026-04-18
---

# Flux-review synthesis — gate-threshold calibration v2

## Critical findings (P0/P1)

### P0 — Cursor-advance must not precede tier-change write
`fd-ab-platform-log-integrity` (B) and `fd-lighthouse-logbook-cursor-integrity` (C) both flag: if SessionEnd drains the jsonl and advances `cursor_ts` *before* `gate-tier-calibration-v2.json` is durably written, a crash between the two operations permanently loses the computed update — the jsonl range has been "consumed" but no calibration change landed. Fix: write order must be `fsync(v2.json.tmp) → rename(v2.json) → update cursor`. Also keep the prior v2 file as `.v2.json.prev` for one cycle.

### P0 — Torn-write tolerance on gate-outcomes.jsonl append
`fd-append-log-cursor-correctness` (A) and `fd-lighthouse-logbook-cursor-integrity` (C) converge: the drain reader must tolerate a partial trailing line (non-terminated JSON, crash mid-append). Skip the broken line, log at debug, continue. Do NOT truncate the file. Writer must append whole-line + fsync per write OR accept line loss under crash.

### P1 — Zero-denominator and small-n edges in FPR/FNR formulas
`fd-rolling-window-algorithm-soundness` (A) and `fd-spc-control-limit-stability` (B) both name: initial window with n<10 must NOT compute a spurious FNR and promote. Concrete rule: `if weighted_n < 10 → tier stays, record NaN/null, never promote`. Also: a 100% pass rate with n=15 gives FNR=0 which is a meaningless "perfect" — freeze tier until at least one negative observation accumulates.

### P1 — Single FNR threshold across themes of different cost structures
`fd-diagnostic-sensitivity-tuning` (B) flags: safety false-negatives cost more than quality false-negatives; applying the same `0.30` promotion threshold everywhere means safety promotes too late. The brainstorm's "deferred to a follow-up bead" stance is acceptable ONLY if the v2 schema actually carries the `fnr_threshold` override field from day one (so it's populable without another migration). Confirm.

### P1 — Theme derivation is a trust boundary, not a lookup
`fd-credit-model-psi-drift` (B) and `fd-waqf-accounting-long-duration-reconciliation` (C) converge: theme names become cohort keys. If theme is inferred from `check_type` prefix today but a theme registry lands next week, old outcomes remain pooled under the inferred bucket — silent population drift. Fix: persist `theme_source: inferred|registry` per outcome so later reclassification is auditable.

## Cross-track convergence

The highest-confidence signals (≥2 tracks independently):

| Finding | Tracks | Agents |
|---|---|---|
| Cursor/write ordering P0 | B, C | fd-ab-platform-log-integrity · fd-lighthouse-logbook-cursor-integrity |
| Torn-line tolerance on append | A, C | fd-append-log-cursor-correctness · fd-lighthouse-logbook-cursor-integrity |
| n<10 / zero-denom safety | A, B | fd-rolling-window-algorithm-soundness · fd-spc-control-limit-stability |
| Theme registry governance | B, C | fd-credit-model-psi-drift · fd-waqf-accounting-long-duration-reconciliation |
| Autocorrelation of successive gate fires within a session inflates n | B | fd-spc-control-limit-stability (single-track but strong) |

## Domain-expert insights (Track A)

- **Migration idempotency (fd-schema-migration-backward-compat):** First-run migration must be idempotent against concurrent invocations (two agents with staggered SessionEnd). Use a lockfile or `rename(v2.tmp, v2)` semantics. Archive v1 only after v2 is durable.
- **Hook timeout alignment (fd-sessionend-hook-integration):** Claude Code SessionEnd hooks have a hard timeout. Calibration must short-circuit if drain would exceed budget — append unprocessed offsets to a resume cursor and finish on next SessionEnd. Do NOT block session exit.
- **/reflect interaction (fd-sessionend-hook-integration):** If `/reflect` runs the same calibration during a session and then SessionEnd re-runs it, both should converge via cursor idempotency. Distinguish `--auto` vs manual in telemetry so the streak tracker (myyw.10) can count correctly.
- **Subcommand contract (fd-go-subcommand-plumbing):** New `clavain-cli calibrate-gate-tiers` needs clean exit codes: 0 = advanced, 2 = no new outcomes, 1 = error. The hook consumes these for retry logic.

## Parallel-discipline insights (Track B)

- **SPC — autocorrelation (fd-spc-control-limit-stability):** Gate fires within a single session are not independent — one failing gate often signals correlated failures downstream. Treat outcomes from the same session as a **rational subgroup**: either downweight same-session outcomes or record session_id and compute `effective_n` = distinct sessions, not raw row count. Without this, `weighted_n` inflates and promotion happens on false signal.
- **Credit scoring — audit trail (fd-credit-model-psi-drift):** The brainstorm records verdict + check + phase but NOT the tier that was in effect when the gate fired. Without `tier_at_fire` in the jsonl row, we can't distinguish "soft gate that correctly let a marginal case through" from "hard gate that wrongly blocked." Add field.
- **Diagnostic calibration — theme cost asymmetry:** See P1 above.
- **A/B platforms — drain boundary (fd-ab-platform-log-integrity):** Outcomes generated *during* the SessionEnd hook (e.g., a final quality-gates fire triggered by the hook itself) can be ambiguously inside/outside the drain window. Define: cursor advances to `max(ts)` observed at drain start; outcomes arriving during computation are picked up next cycle.

## Structural insights (Track C)

- **Horology (fd-horology-isochronism-drift):** A mechanical clock's beat error is corrected by measuring the asymmetry of tick/tock intervals. The calibration's analog: if `tier_changed_at` happens mid-window, the rolling window spans heterogeneous tier regimes — FPR/FNR computed over that window is blended. Partition the window at tier-change boundaries; compute sub-window statistics; only promote if the *latest* sub-window meets threshold. Without this, a single promotion can "lock in" on stale data.
- **Lighthouse logbook (fd-lighthouse-logbook-cursor-integrity):** Trinity House watch changeover required the outgoing keeper to sign off before the incoming one took over. Applied: the drain operation should write an intent-marker (`drain_started: ts`) BEFORE reading outcomes, and the completion marker (`drain_committed: ts`) AFTER v2 is durable. A crash with start-but-no-commit is unambiguously "redo from start" on next SessionEnd.
- **Venetian glassmaking annealing (fd-glassmaking-annealing-tier-promotion):** Glass annealing uses a controlled cooling gradient — too fast and it cracks. Applied: soft→hard promotion should not happen from raw FNR dip alone; require N consecutive windows (e.g., 3 drains) where FNR stays above threshold. The brainstorm's single `change_count_90d ≤ 2` rule is a frequency cap but not a stability requirement. Add `consecutive_windows_above_threshold` as a promotion precondition.
- **Ottoman waqf accounting (fd-waqf-accounting-long-duration-reconciliation):** Waqf registers were reformed every few generations with full lineage traceability to the original trust deed. Applied: the v1→v2 migration should preserve a `migrated_from_v1: true` flag AND the original v1 key structure as metadata, so downstream tooling or audits can trace any v2 entry back to its v1 origin. The brainstorm says archive `.bak` but doesn't link individual entries — add `origin_key` field to migrated entries.

## Synthesis assessment

**Overall quality:** Strong. The brainstorm makes deliberate architectural choices (separate log vs. SQLite, named v2 vs. in-place, rolling-window vs. EMA) and names the separation boundary from sibling bead 8n9n explicitly. The open questions are the right ones.

**Highest-leverage improvement:** Make the jsonl row schema carry `session_id`, `tier_at_fire`, `theme_source`, and `evidence_ref` from day one — even if most are empty. Retrofitting these later means re-drain or a second migration.

**Surprising finding:** The horology and glassmaking convergence on "partition the window at tier-change boundaries and require consecutive stable sub-windows before promoting" is a structural pattern the software-engineering-only tracks didn't surface. Without it, promotion can thrash — FNR dips for one window right after a tier change (which itself changes the distribution) and locks in.

**Semantic-distance value:** Track C earned its place — the horology partitioning insight and glassmaking's "consecutive stable windows" rule are genuinely different from what A/B surfaced, and they strengthen the algorithm, not just the plumbing. Track B's SPC autocorrelation finding is also not something a pure adjacent-domain expert would frame that way.

## Action list for plan phase

**Must address (P0/P1 convergent):**
1. Write-order protocol: `fsync v2.json.tmp → rename → fsync cursor`. Keep `.v2.json.prev` for one cycle.
2. Append torn-line tolerance: drain skips broken trailing lines, logs, continues.
3. Small-n safety: `weighted_n < 10 → no promotion`; `fnr == 0 with n < 20 → freeze`.
4. Session-level rational subgrouping: record `session_id` in jsonl; optionally compute `effective_n` by distinct session.
5. Include `theme_source`, `tier_at_fire`, `fnr_threshold` (override field), `origin_key` (for migrated entries) in schema v2 from day one.

**Should address (Track C / P2 structural):**
6. Partition rolling window at `tier_changed_at` boundaries; compute sub-window statistics.
7. Require `consecutive_windows_above_threshold ≥ 3` as promotion precondition, in addition to existing rules.
8. Write `drain_started` intent marker before drain, `drain_committed` after v2 durable.

**Lower priority:**
9. Document `/reflect` vs `--auto` semantics for myyw.10 streak integration.
10. Exit-code contract for `calibrate-gate-tiers`: 0 advanced, 2 no-op, 1 error.
