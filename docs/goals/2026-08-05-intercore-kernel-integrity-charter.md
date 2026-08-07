# Charter: Intercore Kernel Integrity — Witnesses, Locks, and Honest Replay

**Date:** 2026-08-05 · **Complexity:** C3 · **Source:** flux-melange review `docs/research/flux-melange/clavain-core-verse-improvements/` (192 findings; this charter bundles the top intercore cluster)

## Why (leverage)

The melange's highest-heat findings compound in one place: intercore's witness machinery. Four verified defects make the kernel's durable record untrustworthy while its docs claim the opposite — and every downstream remediation (recovery, gates, audit) is being designed on top of that record. All fixes are in one Go module, each already root-caused to file:line with a sketched fix. Best blast-radius/cost ratio in the 10-item program; items 1–3 of the program's sequenced recommendation.

## Scope

**In (sequenced):**

1. **Lock staleness fuse** (f-038, f-063..f-066): wire the existing `pidAlive` into the `tryBreakStale` break path in `core/intercore/internal/lock/lock.go`; replace the `TestStaleBreaking` pin that locks in timestamp-only breaking; reconcile the bash fallback's never-break semantics note; correct the overclaiming docs (`AGENTS.md:80`, `docs/product/intercore-vision.md:377`).
2. **Nil event recorders** (f-039, f-040, f-067..f-070, V4): wire real recorders into the 15 `dispatch.New(..., nil)` sites and 4 `budget.New(..., nil)` sites in `cmd/ic` so `dispatch_transition` / `budget.warning` / `budget.exceeded` actually land; fix the false "same transaction" doc comment at `cmd/ic/dispatch.go:237`.
3. **Event cursor integrity** (f-135, V1): add the missing coordination case to the high-water-mark loop in `cmd/ic/events.go:143-154` (kill the hardcoded 0 at :126/:128); wire the persisted interspect cursor that is currently saved-but-never-advanced.
4. **CancelByRun witness** (f-185, V5): make run-level cancellation (`internal/dispatch/dispatch.go:473-488`) emit a `dispatch_transition` event per cancelled dispatch instead of a raw UPDATE that bypasses `UpdateStatus`.
5. **Honest replay** (f-184, f-045, f-134, f-144, f-145): `ic run replay` reports `events_expected` vs `events_found` and signals sparsity in its exit code / `--json` output; `internal/replay/reconstruct.go:36-38` stops silently dropping coordination/review/discovery event sources; the hardcoded exit-1 reexecute stub (`cmd/ic/run_replay.go:115,135-137`) fails with an explicit "not implemented" message rather than a bare 1.

**Out (successor obligations, deliberately excluded):**

- Audit-chain wiring (f-188): requires chain-topology redesign (run-scoped chains, tx-allocated sequence, checksum policy v2) — separate goal.
- `ic sweep` / scheduler / stall-detector wiring (f-158): landing-process gap — separate goal.
- `ClearLocks` staleness guard + `--dry-run` (f-060); gate-mode 3-file fix (Clavain layer); exemplar root; fleet triage — separate goals.

## Acceptance criteria

- All five scope items implemented in `core/intercore` with unit tests pinning the NEW behavior (the lock fix must remove the old pin).
- `go test ./...` and `go test -race ./internal/lock/ ./internal/dispatch/ ./internal/event/ ./internal/replay/` pass.
- Docs touched by item 1 no longer claim behavior the code doesn't have.
- No new finding in the melange ledger is reintroduced (witness events stay inside the admitting transaction where the schema allows; where post-commit is unavoidable, the comment says so honestly).

## Completion condition (literal, handed to /goal)

```
In /Users/sma/projects/Sylveste/core/intercore, all of: (1) `go test ./...` exits 0 and `internal/lock` tests assert PID-liveness-checked stale breaking (no timestamp-only break test remains); (2) `grep -rn "dispatch.New(" cmd/ic` shows zero nil-recorder call sites and `grep -rn "budget.New(" cmd/ic` shows zero nil fourth arguments; (3) `cmd/ic/events.go` contains a coordination case in the high-water-mark loop and no hardcoded `0` in the sinceCoordinationID position; (4) `CancelByRun` in internal/dispatch/dispatch.go emits a dispatch_transition event, proven by a passing unit test; (5) `ic run replay` output (text and --json) includes events_expected and events_found and signals sparsity, and internal/replay/reconstruct.go no longer filters out SourceCoordination/SourceReview/SourceDiscovery; (6) the reexecute stub exits with an explicit not-implemented message; (7) `bash test-integration.sh` passes. Or stop after 60 turns.
```

## Successor obligations

On completion, file (or hand to next-goal): audit-chain wiring (f-188), `ic sweep` witness-spine landing (f-158), `ClearLocks` hardening (f-060), Clavain-side gate-mode 3-file fix (f-101/f-102/f-108), `SYLVESTE_EXEMPLAR_ROOT` (f-084/f-085). Commit + push in the Sylveste repo; close the minted bead.

## Interview note

Formed under auto permission mode — the C3 interview was skipped per mode rules; scope selected as the ritual's recommended option (kernel integrity bundle). The user holds go/no-go at the /goal invocation.
