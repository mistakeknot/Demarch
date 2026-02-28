# Task 5: CLI End-to-End Integration Test — Implementation Analysis

## Summary

Added `ic situation snapshot` end-to-end test cases to `core/intercore/test-integration.sh`. Both test cases pass alongside all existing tests (130+ assertions).

## What Was Added

### Test 1: Empty Snapshot (lines 1367–1378)

Runs `ic situation snapshot` against the existing initialized DB (which has many runs/dispatches from prior tests, but this validates the command works on the full DB state). Verifies:

- Exit code is 0
- Output is valid JSON with the expected top-level keys: `timestamp`, `runs`, `dispatches`, `recent_events`, `queue`

### Test 2: Scoped Snapshot (lines 1380–1399)

Creates a new run via `ic run create --project=... --goal=...`, then runs `ic situation snapshot --run=<id>`. Verifies:

- Exit code is 0
- Output JSON contains exactly 1 run in the `runs` array
- The run's `id` matches the created run ID
- The run's `goal` matches "Snapshot test run"

## Key Design Decisions

1. **Followed existing conventions exactly:** Used the `ic()` helper function, `pass`/`fail` helpers, `--db="$TEST_DB"` flag pattern, and `python3 -c "import sys,json; ..."` for JSON validation (matching the pattern used elsewhere in the script, e.g., the replay tests).

2. **Placed tests at the end:** Appended before the final "All integration tests passed" line, following the chronological append pattern used throughout the script.

3. **Used `$TEST_DIR` as project directory:** Same convention as all other `ic run create` calls in the test script.

4. **No cleanup needed:** The script's `trap cleanup EXIT` handles temp dir removal.

## Code Reference

### Situation snapshot command implementation
- `/home/mk/projects/Demarch/core/intercore/cmd/ic/situation.go` — CLI handler, parses `--run=` and `--events=` flags
- `/home/mk/projects/Demarch/core/intercore/internal/observation/observation.go` — `Collector.Collect()` gathers Snapshot struct from phase/dispatch/event/scheduler stores

### Snapshot JSON structure (from `observation.Snapshot`)
```json
{
  "timestamp": "...",
  "runs": [{"id": "...", "phase": "...", "status": "...", "project_dir": "...", "goal": "...", "created_at": ...}],
  "dispatches": {"active": 0, "total": 0, "agents": []},
  "recent_events": [],
  "queue": {"pending": 0, "running": 0, "retrying": 0},
  "budget": null
}
```

### Test script
- `/home/mk/projects/Demarch/core/intercore/test-integration.sh` — lines 1365–1399 (new situation snapshot section)

## Verification

Full test suite run: all 130+ assertions pass including the 4 new situation snapshot assertions.
