---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-06-ockham-f7-health-bypass-brainstorm.md"
target_description: "Ockham F7: Health JSON + Tier 3 BYPASS trigger + double-sentinel + resume + INV-8"
tracks: 4
track_a_agents: [fd-go-crash-recovery-atomicity, fd-sqlite-concurrent-access, fd-state-machine-halt-invariants, fd-cli-safety-critical-ux, fd-go-error-handling-propagation]
track_b_agents: [fd-nuclear-scram-sequencing, fd-icu-alarm-escalation, fd-safety-board-policy-freeze, fd-psm-dual-confirmation]
track_c_agents: [fd-polynesian-heave-to-storm-protocol, fd-japanese-tosho-yaki-ire-quench-arrest, fd-benedictine-interdict-sacramental-freeze, fd-dujiangyan-cascade-gate-hydraulics]
track_d_agents: [fd-minoan-palatial-archive-sealing, fd-igbo-ofo-oath-binding-emergency-halt, fd-tlingit-potlatch-debt-quenching-emergency-reset]
date: 2026-04-06
---
# Cross-Track Synthesis: Ockham F7 Brainstorm Review

**48 findings** across 16 agents in 4 tracks. After deduplication: **12 unique findings** (4 P0, 5 P1, 2 P2, 1 P3).

## Critical Findings (P0/P1)

### P0-1: fsync missing on sentinel writes — write-before-notify is code-order only, not durable
**Convergence: 3/4 tracks** (A: fd-go-crash-recovery-atomicity, C: fd-dujiangyan-cascade-gate-hydraulics, D: fd-minoan-palatial-archive-sealing)
**Highest-confidence finding.** `factory-paused.json` is written with `f.Write()` but no `f.Sync()`. On Linux with writeback-enabled filesystems (ext4, btrfs), the write returns success when the page cache is updated — the inode may not reach disk for seconds. A crash in this window leaves no sentinel on disk while the interspect record (written after) may have persisted. The write-before-notify ordering collapses from a durability guarantee to a code-ordering convention.
**Fix:** Add `f.Sync()` before `f.Close()` in both `reconstructHalt()` and the new BYPASS trigger write path. One line per write site.

### P0-2: Resume without prior halt silently destroys earned autonomous tiers
**Convergence: 2/4 tracks** (A: fd-state-machine-halt-invariants, D: fd-tlingit-potlatch-debt-quenching-emergency-reset)
`ockham resume` resets all ratchet_state to supervised. If run when no halt is active, autonomy earned over weeks is silently destroyed with no audit trail. The Tlingit lens adds: the destruction ceremony (ratchet reset) must only execute during a valid ceremony (halt).
**Fix:** Add `if !halt.IsHalted() { return fmt.Errorf("factory is not halted") }` at top of resume. One line.

### P0-3: evaluateSignals() runs independently of governor halt guard — re-entrant BYPASS during existing halt
**Convergence: 3/4 tracks** (B: fd-nuclear-scram-sequencing, C: fd-japanese-tosho-yaki-ire-quench-arrest, D: fd-igbo-ofo-oath-binding-emergency-halt)
**Highest-confidence finding.** `check.go:evaluateSignals()` calls `eval.Evaluate()` directly, bypassing `governor.Evaluate()`'s halt check. When F7 adds BYPASS trigger logic inside the evaluator, evaluateSignals() can fire BYPASS during an existing halt — overwriting the original halt record or producing re-entrant halt events.
**Fix:** Add halt check at top of `evaluateSignals()` (brainstorm D5 already specifies this). Place it BEFORE the dry-run check.

### P0-4: Resume must never use defer os.Remove on sentinel — panic/error deletes the halt file
**Convergence: 2/4 tracks** (C: fd-dujiangyan-cascade-gate-hydraulics, D: fd-tlingit-potlatch-debt-quenching-emergency-reset)
If `ockham resume` is written with `defer os.Remove(haltPath)`, a panic or error after the deferred setup but before SQLite commit will delete the sentinel without resetting domains. Factory unblocks at pre-halt autonomy levels.
**Fix:** Never defer sentinel deletion. Delete only as an explicit ordered step after `tx.Commit()` returns nil.

### P1-1: BYPASS sentinel write failure swallowed by degraded-continue error pattern
**Convergence: 2/4 tracks** (A: fd-go-error-handling-propagation, B: fd-nuclear-scram-sequencing)
`runCheck()` logs all evaluateSignals() errors to stderr and continues (exit 0). If BYPASS fires but sentinel write fails (disk full), the emergency is swallowed. Cron sees exit 0.
**Fix:** Introduce typed `ErrBypassFailed` error. `runCheck()` propagates this error type (exit non-zero) while degrading other errors.

### P1-2: reconstructHalt() runs AFTER evaluateSignals() — halt not recovered before signal evaluation
**Convergence: 3/4 tracks** (A: fd-go-crash-recovery-atomicity, B: fd-nuclear-scram-sequencing, B: fd-psm-dual-confirmation)
**Highest-confidence finding.** In `runCheck()`, the step order is: snapshotAuthority → evaluateSignals → reconstructHalt → checkReconfirmation. After a crash during BYPASS write, the sentinel is missing. evaluateSignals() runs without halt protection. reconstructHalt() at Step 3 repairs the file — but evaluation already executed.
**Fix:** Reorder: reconstructHalt() FIRST, then snapshotAuthority, then evaluateSignals, then checkReconfirmation. One reorder in `runCheck()`.

### P1-3: INV-8 uses enumerated blocklist — new write paths default to permitted
**Convergence: 3/4 tracks** (B: fd-safety-board-policy-freeze, C: fd-benedictine-interdict-sacramental-freeze, D: fd-igbo-ofo-oath-binding-emergency-halt)
**Highest-confidence finding.** Halt guards are placed individually per-command. `checkReconfirmation()` calls `SetSignalState()` with no halt check. New commands in F8+ will forget the guard. The Benedictine/Igbo lenses both insist: an allowlist (only listed operations permitted) is structurally safer than a blocklist (only listed operations blocked).
**Fix:** In `runCheck()`, add top-level halt check that skips everything except reconstructHalt() and snapshotAuthority(). Future operations default to blocked.

### P1-4: Health JSON must read persisted state, not recompute — blocked by halt guard during halt
**Convergence: 2/4 tracks** (B: fd-icu-alarm-escalation, D: fd-minoan-palatial-archive-sealing)
`ockham health` must work when halted (R1). If health constructs signals via evaluateSignals() (which will be halt-guarded), it produces incomplete data exactly when health data is most critical.
**Fix:** Health reads from signals.db signal_state table directly. Add `at_advisory_floor` field per the ICU alarm agent.

### P1-5: Root-cause deduplication counts themes, not causal independence
**Convergence: 3/4 tracks** (B: fd-psm-dual-confirmation, C: fd-polynesian-heave-to-storm-protocol, D: fd-igbo-ofo-oath-binding-emergency-halt)
**Highest-confidence finding.** A single infrastructure failure (e.g., interspect DB slow) can fire both `auth` and `perf` INFORM signals simultaneously, triggering BYPASS for one root cause. The single-lane-per-bead invariant (check.go line 202-208) provides accidental mitigation — but it is not designed or documented.
**Fix for F7:** Document the single-lane-per-bead invariant as a design constraint. Add `BypassThreshold` to Config with validation (`>= 2`). Track causal independence for F8.

## Cross-Track Convergence

| Finding | Track A | Track B | Track C | Track D | Score |
|---------|---------|---------|---------|---------|-------|
| fsync on sentinel writes | x | | x | x | **3/4** |
| evaluateSignals() halt guard | | x | x | x | **3/4** |
| INV-8 allowlist vs blocklist | | x | x | x | **3/4** |
| Root-cause deduplication | | x | x | x | **3/4** |
| reconstructHalt() step ordering | x | x | x | | **3/4** |
| Resume without halt guard | x | | | x | 2/4 |
| Never defer sentinel deletion | | | x | x | 2/4 |
| BYPASS error propagation | x | x | | | 2/4 |
| Health reads persisted state | | x | | x | 2/4 |

**5 findings** achieved 3/4 convergence — independently discovered from completely different reasoning traditions. These are the highest-confidence signals.

## P2 Findings (deduped)

### P2-1: Health JSON needs structured halt_reason and at_advisory_floor
**Tracks:** B (fd-icu-alarm-escalation), C (fd-japanese-tosho-yaki-ire-quench-arrest)
`halt_reason` should be `{code, fired_themes[], fired_at}` not a string. Signals should include `at_advisory_floor: bool` and `consecutive_clears`.

### P2-2: Health reads need a read transaction for snapshot consistency
**Track:** A (fd-sqlite-concurrent-access)
Multiple signal_state/ratchet_state reads without a transaction can produce contradictory data. Wrap in `BeginTx(ctx, &sql.TxOptions{ReadOnly: true})`.

## P3 Finding

### P3-1: Resume should display halt context and domain preview before accepting --confirm
**Convergence: 3/4 tracks** (A: fd-cli-safety-critical-ux, B: fd-nuclear-scram-sequencing, D: fd-minoan-palatial-archive-sealing)
Show halt reason, timestamp, fired themes, and domain reset count before `--confirm` is accepted.

## Synthesis Assessment

**Overall quality of the brainstorm:** Strong. The write-before-notify ordering, double-sentinel pattern, and policy immutability requirements are well-specified. The 4 P0s are implementation-level gaps in a design-level document — they describe how the implementation must enforce the design's intent.

**Highest-leverage improvement:** Reorder `runCheck()` to put `reconstructHalt()` first (P1-2), then add allowlist halt guard (P1-3). These two changes, totaling ~10 lines, close the three biggest convergent findings simultaneously: reconstructHalt ordering, evaluateSignals halt guard, and INV-8 allowlist.

**Surprising finding:** The fsync gap (P0-1). Three independent tracks — a Go crash-recovery specialist, a 2,300-year-old Chinese irrigation engineer, and a Bronze Age Mycenaean scribe — all converged on the same issue: `f.Write()` without `f.Sync()` makes write-before-notify a code-ordering convention, not a durability guarantee. The Minoan scribe's "runner before seal" framing was the most vivid: a messenger who departs before the clay seal hardens carries news of a halt while the archive remains writable.

**Semantic distance value:** The outer tracks (C/D) contributed qualitatively different insights. The distant track's Benedictine interdict agent surfaced the allowlist-vs-blocklist framing that is architecturally significant for F7 and beyond. The esoteric track's Igbo ofo-binding agent independently arrived at the same allowlist recommendation through a completely different cultural logic (divine categorical prohibition vs. canonical enumerated exemptions). The Tlingit potlatch agent's "never defer sentinel deletion" finding is a concrete Go implementation trap that the adjacent agents mentioned but didn't elevate to P0. The convergence between the Polynesian storm protocol and the Go crash-recovery agent on step-ordering proves the issue is structural, not domain-specific.
