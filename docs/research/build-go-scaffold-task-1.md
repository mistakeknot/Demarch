# Task 1 Execution: Go Module + Subprocess Helpers + Dispatcher Shell

**Plan:** `docs/plans/2026-02-25-clavain-cli-go-migration.md`
**Bead:** iv-sevis (F1)
**Status:** COMPLETE
**Date:** 2026-02-25

---

## Summary

Created the full Go binary scaffold at `os/clavain/cmd/clavain-cli/` implementing Task 1 of the clavain-cli Go migration plan. The scaffold includes the module definition, subprocess helpers, all 12 duplicated types, a 34-command dispatcher, and stub functions across 7 command group files.

## Files Created (13 total)

| File | Purpose | Lines |
|------|---------|-------|
| `go.mod` | Module `github.com/mistakeknot/clavain-cli`, Go 1.22 | 3 |
| `exec.go` | Subprocess helpers: `findIC`, `runIC`, `runICJSON`, `runBD`, `runGit`, `bdAvailable`, `icAvailable` | ~95 |
| `types.go` | 12 types: `Run`, `BudgetResult`, `GateResult`, `GateEvidence`, `GateCondition`, `AdvanceResult`, `Artifact`, `TokenAgg`, `RunAgent`, `SprintState`, `ActiveSprint`, `Checkpoint` | ~120 |
| `main.go` | Dispatcher (34 case arms + help/default) and `printHelp()` | ~150 |
| `sprint.go` | 6 stubs: `cmdSprintCreate`, `cmdSprintFindActive`, `cmdSprintReadState`, `cmdSprintTrackAgent`, `cmdSprintCompleteAgent`, `cmdSprintInvalidateCaches` | 8 |
| `budget.go` | 7 stubs: `cmdBudgetRemaining`, `cmdBudgetTotal`, `cmdBudgetStage`, `cmdBudgetStageRemaining`, `cmdBudgetStageCheck`, `cmdStageTokensSpent`, `cmdRecordPhaseTokens` | 9 |
| `phase.go` | 10 stubs: `cmdSprintAdvance`, `cmdSprintNextStep`, `cmdSprintShouldPause`, `cmdEnforceGate`, `cmdAdvancePhase`, `cmdRecordPhase`, `cmdSetArtifact`, `cmdGetArtifact`, `cmdInferAction`, `cmdInferBead` | 12 |
| `checkpoint.go` | 6 stubs: `cmdCheckpointWrite`, `cmdCheckpointRead`, `cmdCheckpointValidate`, `cmdCheckpointClear`, `cmdCheckpointCompletedSteps`, `cmdCheckpointStepDone` | 8 |
| `claim.go` | 4 stubs: `cmdSprintClaim`, `cmdSprintRelease`, `cmdBeadClaim`, `cmdBeadRelease` | 6 |
| `complexity.go` | 2 stubs: `cmdClassifyComplexity`, `cmdComplexityLabel` | 4 |
| `children.go` | 2 stubs: `cmdCloseChildren`, `cmdCloseParentIfDone` | 4 |
| `exec_test.go` | 3 tests: `TestFindIC_NotOnPath`, `TestBDAvailable`, `TestICAvailable` | 22 |

## Verification Results

All 4 verification steps passed:

1. **Build:** `go build -o /dev/null .` -- compiled with zero errors, zero warnings
2. **Tests:** `go test -race ./...` -- PASS (1.020s), all 3 tests pass with race detector
3. **Help output:** `go run . help` -- prints full usage text with all 34 commands organized by group (Gate/Phase, Sprint State, Budget, Complexity, Children, Bead Claiming, Checkpoints, Agent Tracking)
4. **Unknown command:** `go run . nonexistent-cmd` -- prints `clavain-cli: unknown command 'nonexistent-cmd'` to stderr, exits with code 1
5. **Stub behavior:** `go run . sprint-create` -- prints `not implemented` to stderr, exits with code 1

## Architecture Notes

- **Flat package structure:** All files in `package main` — no internal packages, no cobra. Matches the plan's "plain `os.Args` dispatch" design.
- **No external dependencies:** Only stdlib (`bytes`, `encoding/json`, `fmt`, `os`, `os/exec`, `strings`, `testing`). `go.sum` not needed.
- **Layer independence:** Types in `types.go` are duplicated from `apps/autarch/pkg/intercore/types.go` to maintain L1/L2 boundary separation. The `GateResult.Passed()` method is the only behavior on the types.
- **ic binary resolution:** `findIC()` checks both `ic` and `intercore` names, caches the result in package-level `icBin` variable. `--json` flag is positional-first (before subcommand) matching the known `ic` CLI convention from MEMORY.md.
- **All 37 stub functions** return `fmt.Errorf("not implemented")` — ready for Task 2+ implementation.

## Command Count Breakdown

| Group | Commands | File |
|-------|----------|------|
| Sprint CRUD | 3 | sprint.go |
| Agent Tracking | 3 | sprint.go |
| Budget | 7 | budget.go |
| Phase/Gate | 10 | phase.go |
| Checkpoint | 6 | checkpoint.go |
| Claiming | 4 | claim.go |
| Complexity | 2 | complexity.go |
| Children | 2 | children.go |
| **Total** | **37** | |

Plus 3 help aliases (`help`, `--help`, `-h`) and the default unknown-command handler = 34 case arms in the switch statement.

## Deviations from Plan

None. All code matches the plan specifications exactly:
- Module path: `github.com/mistakeknot/clavain-cli`
- Go version: 1.22
- All 7 `exec.go` functions implemented as specified
- All 12 types with exact field names and JSON tags
- All 37 stub functions with `fmt.Errorf("not implemented")` return
- All 3 test functions from the plan
- Help text matches the plan verbatim

## Next Steps

Task 2 (Sprint CRUD Commands) can now implement `cmdSprintCreate`, `cmdSprintFindActive`, `cmdSprintReadState`, `cmdSprintTrackAgent`, `cmdSprintCompleteAgent`, and `cmdSprintInvalidateCaches` by replacing the stubs in `sprint.go` with real `ic` subprocess calls using the helpers from `exec.go`.
