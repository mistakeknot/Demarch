# Correctness Review: iv-xlpg Pollard Hunter Resilience Plan
**Date:** 2026-02-23
**Full review:** `/home/mk/projects/Demarch/.claude/reviews/iv-xlpg-plan-correctness.md`

## Summary

The plan has two ship-blocking correctness defects and three high-severity issues.

**Ship-blocker 1 — Success() semantic break (Finding 2):**
Task 1 changes `Success()` to return `r.Status == HunterStatusOK` instead of `len(r.Errors) == 0`. Since none of the 12+ existing hunter implementations set `Status`, every hunt that produces partial errors (appending to `r.Errors`) will now report `Success() == true`. The run history database will record false-positive successes via `api/scanner.go:CompleteRun`. Do not change `Success()`. Instead add a `DeriveStatus()` method that computes the enum from existing fields.

**Ship-blocker 2 — HunterStatus name collision (Finding 1):**
`research/run.go:31` already defines `type HunterStatus struct` in this package family. Adding `type HunterStatus int` to the `hunters` package creates two types with the same name visible to importers of both packages. Rename the new enum to `HuntOutcome` or `ResultCode`.

**High — Watcher context-cancellation guard is dead code (Finding 7):**
The plan's Task 5 watcher fix checks `if err != nil` to detect context cancellation. But `Scanner.Scan` never returns a non-nil error — cancellation is signalled via `result.Errors`. The resilience fix does not work as written; check `ctx.Err()` directly instead.

**High — Backoff overflow (Finding 3):**
`1<<(attempt-1)` overflows to negative at attempt 64. Cap the shift at 30.

**High — isTransient "temporary" substring matches too broadly (Finding 5):**
The string "temporary" matches business-logic error messages unrelated to network transience. Replace with a `RetriableError` interface or remove "temporary" and "503" from the list.

See full review at `/home/mk/projects/Demarch/.claude/reviews/iv-xlpg-plan-correctness.md` for all 10 findings with code-level detail and minimal corrective changes.
