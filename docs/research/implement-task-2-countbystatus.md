# Task 2: Add SchedulerStore.CountByStatus Method

## Summary

Added `CountByStatus(ctx context.Context) (map[string]int, error)` to the scheduler store at `core/intercore/internal/scheduler/store.go`. This method queries the `scheduler_jobs` table with `SELECT status, COUNT(*) FROM scheduler_jobs GROUP BY status` and returns a map of status string to count.

## Files Modified

### `core/intercore/internal/scheduler/store.go`

Added the `CountByStatus` method before the existing `Prune` method. The method:
- Uses `db.QueryContext` with a `GROUP BY status` query
- Returns `map[string]int` (empty but non-nil map for empty tables)
- Follows the existing error wrapping convention (`fmt.Errorf("store.count-by-status: %w", err)`)
- Properly closes rows with `defer rows.Close()`
- Checks `rows.Err()` after iteration (matching the pattern in `List` and `RecoverPending`)

### `core/intercore/internal/scheduler/store_test.go`

Added `TestCountByStatus` test function following existing patterns:
- Uses the existing `openTestDB(t)` helper (in-memory SQLite with schema creation)
- Tests empty database case: verifies no error, non-nil map, zero length
- Tests populated case: inserts 6 jobs (2 pending, 1 running, 3 completed)
- Verifies each status count matches expected values
- Verifies absent statuses return zero value (not present in map)

## Design Decisions

1. **Error prefix**: Used `store.count-by-status` to match the `store.<method>` convention used by other methods (`store.create`, `store.list`, `store.recover`, `store.prune`).

2. **Empty map vs nil**: Returns an initialized empty map for empty tables (via `make(map[string]int)`), not nil. This prevents nil-pointer issues in callers.

3. **No status validation**: The method returns whatever statuses exist in the database without filtering to known `JobStatus` constants. This is intentional — it reflects the actual database state, which could include unexpected values from schema evolution or manual edits.

4. **rows.Err() check**: Added the `rows.Err()` check after the scan loop, matching the pattern in `List` and `RecoverPending`. The task description omitted this, but it's required for correctness per Go database/sql best practices.

## Test Results

```
=== RUN   TestCountByStatus
--- PASS: TestCountByStatus (0.00s)
PASS
```

Full scheduler test suite: all 10 tests pass (3.3s total).
