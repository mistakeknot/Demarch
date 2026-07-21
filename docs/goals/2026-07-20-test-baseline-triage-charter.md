---
artifact_type: goal-charter
bead: Sylveste-ytm
complexity: 3
stage: goal-formed
---

# Goal Charter: Interverse Test-Baseline Triage — Root-Cause Map for the Four Rotted Suites

## Why (leverage)

Four interverse suites are red, proven pre-existing by stash/worktree
comparison during the 2026-07-20 sessions: interphase `gates.bats` 71/91
failing, Clavain shell suite 165 bats failures, interline 2 structural
failures, interflux 3 backpressure failures (Sylveste-9cs). Until baselines
are green, no exit code is trustworthy and every regression claim pays a
stash-proof tax.

mk chose **triage-first** over green-in-one-goal (interview 2026-07-20,
divergence from the recommended option — appetite control): 236+ failures
likely collapse to few root causes, but committing to full green before
the map exists risks an unbounded goal. This goal produces the map; the
execution goal spends it.

**Pre-granted authority for the successor (recorded so it is never
re-asked):** stale tests asserting deliberately retired behavior may be
rewritten to current behavior or deleted outright, rationale in the commit
message (mk-ratified).

## Scope

**In:**
1. Run all four suites fresh and capture the full failure inventory:
   - interphase: `bats tests/shell/` (focus gates.bats)
   - Clavain: `tests/run-tests.sh` (shell + structural + routing + smoke)
   - interline: structural suite
   - interflux: structural suite (backpressure cluster, Sylveste-9cs)
2. Cluster every failure by root cause (env drift, retired behavior,
   harness rot, real regression, flaky).
3. Per-cluster disposition — fix now / rewrite / delete / quarantine+bead —
   with an effort estimate and suggested execution order.
4. Triage report at
   `docs/research/2026-07-20-interverse-test-baseline-triage.md`, committed.
5. Update Sylveste-ytm with the report path and execution plan; existing
   Sylveste-9cs mapped into its cluster.

**Out:**
- Landing fixes — EXCEPT the minimal mechanical unblocking needed to make
  a suite executable at all (e.g. a missing executable bit preventing the
  runner from starting); everything else is a disposition, not a change.
- Rewriting/deleting tests (authority recorded above for the successor).
- The execution goal itself (formed after this map exists, on Sylveste-ytm).

## Acceptance criteria

1. All four suites executed with per-suite failure counts shown in
   surfaced output.
2. Triage report committed: every failing test appears in exactly one
   cluster; each cluster has root cause, disposition, effort estimate.
3. Sylveste-ytm updated with the report path and recommended execution
   order; Sylveste-9cs referenced in its cluster.
4. Work committed; goal closed with the execution goal as successor
   direction.

## Completion condition (literal — handed to /goal)

Interverse test-baseline triage complete: all four suites (interphase
bats, Clavain test runner, interline structural, interflux structural)
executed fresh with per-suite failure counts shown in surfaced output; a
triage report at docs/research/2026-07-20-interverse-test-baseline-triage.md
is committed clustering every failure by root cause with a disposition
(fix now, rewrite, delete, or quarantine with bead) and effort estimate
per cluster plus a recommended execution order; bead Sylveste-ytm is
updated with the report path shown in surfaced output; no test fixes
landed beyond mechanical suite-unblocking. Or stop after 30 turns.

## Successor obligations

The execution goal (green the suites per the map, using the pre-granted
rewrite/delete authority) forms on Sylveste-ytm once this map exists.
