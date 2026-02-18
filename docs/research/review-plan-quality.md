# Quality Review: Phase 2A Implementation Plan

**Date:** 2026-02-18
**Reviewer:** Flux-drive Quality & Style Reviewer
**Document:** `docs/plans/2026-02-18-intermem-phase2a-decay-demotion.md`
**Language:** Python 3.11+
**Dependencies:** Python stdlib only (sqlite3)

## Overall Assessment

The plan is well-structured and shows good adherence to existing codebase patterns. However, there are **5 critical issues** and **12 moderate issues** that must be addressed before implementation.

---

## Critical Issues (MUST FIX)

### C1: Timezone Mixing in Decay Calculation (Severity: HIGH)

**Location:** Task 2, `apply_decay_penalty()`, line 96

**Problem:**
The plan stores `last_seen` via `datetime('now')` (SQLite function, timezone-naive format `YYYY-MM-DD HH:MM:SS`), but uses `datetime.now(timezone.utc)` (timezone-aware) for `current_time`. The subtraction `(current_time - last_seen_dt).days` will raise `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Evidence from existing code:**
- `metadata.py:151`: `now = datetime.now(timezone.utc).isoformat()` (tz-aware)
- `metadata.py:21,95`: `DEFAULT (datetime('now'))` (SQLite, tz-naive)

The codebase has **mixed datetime strategies**:
- SQLite default columns use `datetime('now')` (naive)
- Explicit Python updates use `datetime.now(timezone.utc).isoformat()` (aware)

**Fix:**
```python
def apply_decay_penalty(confidence: float, last_seen: str, current_time: datetime) -> float:
    """Apply time-based decay to confidence."""
    # Parse as naive, then make UTC-aware for consistent arithmetic
    last_seen_dt = datetime.fromisoformat(last_seen)
    if last_seen_dt.tzinfo is None:
        last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)

    # Ensure current_time is also UTC-aware
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    days_since = (current_time - last_seen_dt).days
    if days_since <= 14:
        return confidence
    periods = days_since // 14
    penalty = 0.1 * periods
    return max(0.0, min(1.0, confidence - penalty))
```

**Alternative:** Migrate all `last_seen` values to UTC-aware format as part of `migrate_to_v2()`. Add a one-time data fix:
```python
# In migrate_to_v2(), after adding columns:
self.conn.execute("""
    UPDATE memory_entries
    SET last_seen = last_seen || '+00:00'
    WHERE last_seen NOT LIKE '%+%' AND last_seen NOT LIKE '%Z'
""")
```

**Test coverage needed:**
- `test_decay_with_naive_last_seen` — entry with old naive timestamp
- `test_decay_with_aware_last_seen` — entry with ISO 8601 tz-aware timestamp

---

### C2: SQLite Version Constraint for NOT NULL DEFAULT (Severity: MEDIUM-HIGH)

**Location:** Task 1, `migrate_to_v2()`, line 38

**Problem:**
The migration uses `ALTER TABLE ADD COLUMN stale_streak INTEGER NOT NULL DEFAULT 0`. SQLite only supports `NOT NULL` with `DEFAULT` in `ALTER TABLE` starting in **SQLite 3.37.0 (2021-11-27)**. Older versions require the column to be nullable.

Python 3.11 bundles SQLite 3.37.0+, so this is **safe for the stated requirement** (`requires-python = ">=3.11"`). However, the plan should document this constraint.

**Fix:**
Add a version check or document the requirement. Best practice:

```python
def migrate_to_v2(self) -> None:
    """Add Phase 2A columns (requires SQLite 3.37.0+)."""
    # Check SQLite version
    version = self.conn.execute("SELECT sqlite_version()").fetchone()[0]
    major, minor, patch = map(int, version.split('.'))
    if (major, minor, patch) < (3, 37, 0):
        raise RuntimeError(
            f"SQLite {version} does not support ALTER TABLE with NOT NULL DEFAULT. "
            f"Upgrade to SQLite 3.37.0+ or Python 3.11+."
        )

    if not self._column_exists("memory_entries", "stale_streak"):
        self.conn.execute(
            "ALTER TABLE memory_entries ADD COLUMN stale_streak INTEGER NOT NULL DEFAULT 0"
        )
    # ... rest of migration
```

**Test coverage needed:**
- `test_migrate_v2_sqlite_version_check` — mock old SQLite, verify error message

---

### C3: Missing SQL Injection Protection in `search_entries()` (Severity: MEDIUM-HIGH)

**Location:** Task 1, line 64

**Problem:**
The plan specifies `search_entries(keywords: str) -> list[dict]` with a "LIKE query on content_preview + section" but doesn't show the implementation. If this uses string interpolation for `LIKE` patterns, it's vulnerable to SQL injection (e.g., `keywords="'; DROP TABLE memory_entries; --"`).

**Fix:**
Use parameterized queries with `?` placeholders:

```python
def search_entries(self, keywords: str) -> list[dict]:
    """Search entries by keyword in content_preview or section.

    Supports multiple space-separated keywords (AND logic).
    """
    if not keywords.strip():
        return []

    # Split keywords and build WHERE clause with parameterized LIKE
    tokens = keywords.strip().split()
    conditions = " AND ".join([
        "(content_preview LIKE ? OR section LIKE ?)"
        for _ in tokens
    ])
    params = []
    for token in tokens:
        pattern = f"%{token}%"
        params.extend([pattern, pattern])

    query = f"SELECT * FROM memory_entries WHERE {conditions}"
    rows = self.conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
```

**Test coverage needed:**
- `test_search_entries_sql_injection` — search with `'; DROP TABLE` and verify no error
- `test_search_empty_keywords` — empty string returns empty list

---

### C4: Missing NULL `last_seen` Handling (Severity: MEDIUM)

**Location:** Task 2, `sweep_all_entries()`, line 133

**Problem:**
The plan calls `apply_decay_penalty(base_confidence, row["last_seen"], current_time)` without checking if `last_seen` is NULL. While the schema sets `DEFAULT (datetime('now'))`, entries created before migration or via manual INSERT could have NULL.

**Fix:**
Add NULL check in `sweep_all_entries()`:

```python
# In the sweep loop:
last_seen = row["last_seen"]
if last_seen is None:
    # Entry never seen (shouldn't happen, but defensive)
    last_seen = datetime.now(timezone.utc).isoformat()
    metadata_store.conn.execute(
        "UPDATE memory_entries SET last_seen = ? WHERE entry_hash = ?",
        (last_seen, entry_hash)
    )

decayed_confidence = apply_decay_penalty(
    base_confidence, last_seen, current_time
)
```

**Test coverage needed:**
- `test_sweep_handles_null_last_seen` — manually insert entry with NULL last_seen, verify sweep doesn't crash

---

### C5: Re-promotion Logic Overwrites `demoted_at` (Severity: MEDIUM)

**Location:** Task 6, line 353

**Problem:**
The re-promotion logic sets `demoted_at = NULL` when re-activating an entry. This **loses audit history** — we can't tell when the entry was last demoted or how many times it cycled.

**Fix:**
Keep `demoted_at` as historical record, add `reactivated_at`:

```python
# In migrate_to_v2(), add:
if not self._column_exists("memory_entries", "reactivated_at"):
    self.conn.execute(
        "ALTER TABLE memory_entries ADD COLUMN reactivated_at TEXT"
    )

# In re-promotion logic (validate_and_filter_entries):
if row and row["status"] == "demoted" and confidence >= STALE_THRESHOLD:
    metadata_store.conn.execute(
        "UPDATE memory_entries SET status = 'active', stale_streak = 0, reactivated_at = datetime('now') WHERE entry_hash = ?",
        (entry_hash,)
    )
    # Keep demoted_at for audit trail
```

**Rationale:** Preserving `demoted_at` enables future analysis (e.g., "entries that were demoted more than 3 times" or "average time between demotion and re-promotion").

**Test coverage needed:**
- `test_reactivation_preserves_demoted_at` — verify demoted_at is not nulled

---

## Moderate Issues (SHOULD FIX)

### M1: Inconsistent Naming — `stale_streak` vs `snapshot_count`

**Location:** Task 1, line 55

**Problem:**
The plan introduces `stale_streak` to track "consecutive sweeps where confidence was below threshold." This is analogous to `snapshot_count` (consecutive observations), but the naming diverges:
- `snapshot_count` = "how many times have we seen this entry?" (counter, always increments)
- `stale_streak` = "how many consecutive sweeps found it stale?" (streak, resets)

The term "streak" is correct, but "stale_streak" could be misread as "streak of being stale" vs "streak of consecutive sweeps that found it stale."

**Suggestion:**
Use `stale_sweep_count` or `consecutive_stale_sweeps` for clarity. The existing pattern uses `_count` suffixes (`snapshot_count`, `validated_count`, `stale_count`).

**Alternative:** Keep `stale_streak` but add a docstring to the column in the schema comment.

**Impact:** Low (semantic clarity, not correctness).

---

### M2: Demotion Without File-Specific Heuristics (Severity: MEDIUM)

**Location:** Task 3, `demote_entries()`, line 226-232

**Problem:**
The demotion logic "scans each target doc for lines matching the content + `<!-- intermem -->` marker." This is **fragile** if:
- User manually edited the line (removed/added text)
- Multiple entries have identical prefixes (e.g., "- Always use WAL mode")
- Line breaks or whitespace changed

The existing `promoter.py` doesn't show how dedup works, but the `validator.py:_extract_promoted_entries()` uses regex to find markers. The demotion logic should use the **same extraction logic** to ensure symmetry.

**Fix:**
Reuse `_extract_promoted_entries()` to find entries, then match by hash:

```python
def demote_entries(
    entry_hashes: list[str],
    metadata_store: MetadataStore,
    target_docs: list[Path],
    journal: PromotionJournal,
) -> DemotionResult:
    """Remove stale entries from target docs by hash match."""
    from intermem.validator import _extract_promoted_entries
    from intermem._util import hash_entry

    files_modified = []
    demoted_count = 0

    for doc in target_docs:
        if not doc.exists():
            continue

        # Extract all promoted entries from this doc
        promoted = _extract_promoted_entries(doc)
        promoted_hashes = {hash_entry(e): e for e in promoted}

        # Filter out entries in demotion list
        to_remove = set(entry_hashes) & set(promoted_hashes.keys())
        if not to_remove:
            continue

        # Rewrite doc without demoted lines
        lines = doc.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines = []
        for line in lines:
            # Check if this line contains a demoted entry marker
            # (need to reconstruct the entry and hash it)
            # ... this is complex, see alternative below

        # ... rest of demotion logic
```

**Alternative (simpler):** Store the **line number** in metadata.db when promoting, then use that for demotion. But this breaks if the user edits the doc.

**Best practice:** Accept that manual edits invalidate demotion. Document this as a known limitation.

**Test coverage needed:**
- `test_demote_after_manual_edit` — user edited the promoted line, verify demotion skips it gracefully
- `test_demote_duplicate_content` — two entries with identical text, verify only the correct one is removed

---

### M3: Missing Orphaned Status Handling in Sweep

**Location:** Task 2, `sweep_all_entries()`, line 119

**Problem:**
The sweep query is `SELECT * FROM memory_entries WHERE status != 'demoted'`. This **includes orphaned entries** (status = 'orphaned'). The existing schema has three statuses: `active`, `stale`, `orphaned`. The plan adds `demoted`.

What should happen to orphaned entries during sweep? Are they:
- Re-validated (current plan behavior)?
- Skipped (like demoted)?
- Promoted to demotion candidates if their citations recover?

The plan doesn't specify. Looking at `metadata.py`, the `get_unchecked_citations()` method **skips stale entries** but not orphaned. The plan should clarify the intended behavior.

**Fix:**
If orphaned means "entry was promoted but source file disappeared," then sweep should **skip orphaned** (they can't decay further). If orphaned means "entry lost its source context," then sweep should **include them** for potential recovery.

**Recommendation:**
Add `AND status IN ('active', 'stale')` to the sweep query:

```python
entries = metadata_store.conn.execute(
    "SELECT * FROM memory_entries WHERE status IN ('active', 'stale')"
).fetchall()
```

**Test coverage needed:**
- `test_sweep_skips_orphaned_entries` — orphaned entry not processed by sweep

---

### M4: Empty `metadata.db` Edge Case

**Location:** Task 2, `sweep_all_entries()`, line 118

**Problem:**
If the database has no entries (new project, or all entries demoted), the sweep returns `SweepResult(entries_swept=0, ...)`. This is correct, but the plan doesn't show how the CLI handles this.

**Fix:**
Add to CLI sweep handler:

```python
if sweep_result.entries_swept == 0:
    print("No entries to sweep.")
    sys.exit(0)
```

**Test coverage:** Covered by `test_sweep_command` if it checks empty DB case.

---

### M5: Decay Formula Off-by-One (Severity: LOW)

**Location:** Task 2, `apply_decay_penalty()`, line 100

**Problem:**
The formula is `periods = days_since // 14`. At exactly 14 days, `periods = 1`, penalty = 0.1. But the docstring says "-0.1 per 14-day period **beyond the first 14 days**" (emphasis mine). This suggests the first 14 days are a grace period, and penalties start at day 15.

Current logic:
- Days 0-14: no penalty (correct)
- Days 15-28: `periods = 1`, penalty = 0.1 ❌ (should be 0.1)
- Days 29-42: `periods = 2`, penalty = 0.2 ❌ (should be 0.1)

The issue is the `if days_since <= 14: return confidence` check. If `days_since = 14`, we return early. If `days_since = 15`, `periods = 15 // 14 = 1`, penalty = 0.1. This is **correct** if we interpret "beyond the first 14 days" as "starting at day 15."

But if we want the first penalty at day 28 (after two full periods), then:
```python
if days_since < 28:
    return confidence
periods = (days_since - 14) // 14
```

**Clarification needed:** The plan should specify:
- Day 15-28: -0.1? (current interpretation)
- Day 29-42: -0.1? (alternative interpretation)

**Recommendation:** Keep current logic but clarify docstring:
```python
"""Apply time-based decay to confidence.

Grace period: first 14 days, no decay.
After 14 days: -0.1 per additional 14-day period.
  - Days 15-28: -0.1
  - Days 29-42: -0.2
  - Days 43-56: -0.3
  - etc.
"""
```

**Test coverage:** The plan includes tests for 28 days (-0.2) and 42 days (-0.3), which are correct for the current logic.

---

### M6: Demotion Without Atomic Rollback

**Location:** Task 3, `demote_entries()`, line 222

**Problem:**
The demotion logic modifies multiple files (target docs) and updates the database, but doesn't use a transaction. If the process crashes mid-demotion:
- Some entries are removed from docs
- Some are not yet marked as demoted in metadata
- The journal shows 'demoted' but the DB shows 'active'

The plan mentions "crash recovery" (line 236) but doesn't show the recovery implementation. The existing `promoter.py` uses the journal but doesn't show how to detect incomplete promotions on restart.

**Fix:**
1. Wrap demotion in a try-except, mark journal entries as 'demoted_pending' before file modifications, then 'demoted_complete' after DB update.
2. On next sweep, detect journal entries with 'demoted_pending' but DB still shows 'active', and either:
   - Retry demotion (idempotent)
   - Skip (assume manual rollback)

**Alternative:** Accept that demotion is eventually consistent. The next sweep will detect the mismatch and fix it.

**Test coverage needed:**
- `test_demote_partial_crash` — simulate crash after file write but before DB update, verify next sweep detects it

---

### M7: CLI Query Exit Codes Unclear

**Location:** Task 4, line 294

**Problem:**
The plan says "Exit code 0 on results, 1 on no results, 2 on error" but doesn't specify:
- What counts as "no results"? Zero entries found, or query succeeded but empty?
- What errors trigger exit code 2? DB doesn't exist, DB corrupted, invalid SQL?

**Fix:**
Specify in the plan:
```python
# Exit codes:
# 0 = query succeeded (even if 0 results)
# 1 = user error (e.g., invalid flags)
# 2 = system error (e.g., DB corrupt, permission denied)
```

Then implement:
```python
try:
    results = metadata_store.search_entries(args.search)
    print_results(results)
    sys.exit(0)  # Success even if 0 results
except FileNotFoundError:
    print(f"Error: {intermem_dir / 'metadata.db'} not found", file=sys.stderr)
    sys.exit(2)
except sqlite3.DatabaseError as e:
    print(f"Error: Database corrupt: {e}", file=sys.stderr)
    sys.exit(2)
```

**Test coverage needed:**
- `test_query_missing_db` — verify exit code 2
- `test_query_corrupt_db` — verify exit code 2

---

### M8: `_revalidate_citations()` Duplicates Logic

**Location:** Task 2, line 162

**Problem:**
The helper `_revalidate_citations(entry_hash, metadata_store, project_root)` duplicates the citation validation logic from `validate_and_filter_entries()`. This violates DRY and creates maintenance burden (e.g., if citation extraction changes, must update both).

**Fix:**
Extract a pure function for citation validation that both `validate_and_filter_entries()` and `sweep_all_entries()` can call:

```python
def _validate_entry_citations(
    entry: MemoryEntry,
    metadata_store: MetadataStore,
    project_root: Path,
) -> list[CheckResult]:
    """Extract and validate citations for an entry (pure, no DB writes)."""
    citations = extract_citations(entry)
    checks: list[CheckResult] = []
    for citation in citations:
        result = validate_citation(citation, project_root)
        checks.append(result)
    return checks
```

Then both functions call this, followed by their specific DB operations.

**Impact:** Moderate (code quality, maintainability).

---

### M9: `get_promoted_entries()` Definition Missing

**Location:** Task 1, line 61

**Problem:**
The plan says "Add `get_promoted_entries()` method — returns entries with `status = 'active'` and `confidence_updated_at IS NOT NULL`."

But the docstring says "entries that have been through validation." This is ambiguous — does it mean:
- Entries with confidence calculated at least once? (the NOT NULL check)
- Entries currently promoted to target docs? (requires cross-referencing journal or scanning docs)

The name `get_promoted_entries()` suggests the latter, but the implementation suggests the former.

**Fix:**
Rename to `get_validated_entries()` if it just means "entries with confidence scores":

```python
def get_validated_entries(self) -> list[dict]:
    """Return entries that have been validated at least once."""
    rows = self.conn.execute(
        "SELECT * FROM memory_entries WHERE confidence_updated_at IS NOT NULL"
    ).fetchall()
    return [dict(row) for row in rows]
```

Or, if you need truly promoted entries, add a `promoted_at` column and update it in `promoter.py`.

---

### M10: Hysteresis Threshold Hard-Coded

**Location:** Task 2, line 19

**Problem:**
The plan says "Hysteresis — `stale_streak >= 2` before demotion" but this is hard-coded. Future tuning (e.g., "wait 3 sweeps instead of 2") requires code changes.

**Fix:**
Add a constant:

```python
# At top of validator.py
DEMOTION_STREAK_THRESHOLD = 2

# In sweep logic:
if row_updated and row_updated["stale_streak"] >= DEMOTION_STREAK_THRESHOLD:
    entries_marked += 1
```

**Impact:** Low (future maintainability).

---

### M11: Missing `get_topics()` Column Details

**Location:** Task 1, line 65

**Problem:**
The plan says "`get_topics()` — GROUP BY section with COUNT and AVG(confidence)" but doesn't specify:
- Should it only include active entries, or all statuses?
- Should it filter by confidence threshold?
- What fields are returned? (`section`, `count`, `avg_confidence`?)

**Fix:**
Specify in the plan:

```python
def get_topics(self) -> list[dict]:
    """Return topic summary: section name, entry count, average confidence.

    Includes active and stale entries, excludes demoted/orphaned.
    """
    rows = self.conn.execute("""
        SELECT
            section,
            COUNT(*) as entry_count,
            AVG(confidence) as avg_confidence
        FROM memory_entries
        WHERE status IN ('active', 'stale')
        GROUP BY section
        ORDER BY entry_count DESC
    """).fetchall()
    return [dict(row) for row in rows]
```

**Test coverage needed:**
- `test_get_topics_excludes_demoted` — demoted entries not in counts

---

### M12: CLI Backward Compatibility Unclear

**Location:** Task 4, line 279

**Problem:**
The plan says "When no subcommand is given (`args.command is None`), fall through to existing synthesis behavior." But argparse subparsers with `dest="command"` don't set `None` by default — they raise an error if no subcommand is given.

**Fix:**
Make the default subcommand explicit:

```python
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command", required=False)

# Later:
if args.command is None:
    args.command = "synthesize"
```

Or better, use `set_defaults`:

```python
parser.set_defaults(command="synthesize")
```

**Test coverage needed:**
- `test_no_subcommand_defaults_to_synthesize` — verify `intermem` (no args) runs synthesis

---

## Test Coverage Gaps

The plan lists ~29 tests, but misses these edge cases:

### Missing Tests

1. **`test_migrate_v2_on_empty_db`** — migration on a fresh DB (no existing entries)
2. **`test_migrate_v2_with_existing_demoted_status`** — DB already has a demoted entry (manual insert before migration)
3. **`test_apply_decay_negative_days`** — `last_seen` in the future (clock skew)
4. **`test_sweep_concurrent_sweep_attempts`** — two sweeps running simultaneously (transaction isolation)
5. **`test_demote_already_demoted_entry`** — idempotency check
6. **`test_demote_entry_not_in_target_doc`** — entry hash exists in DB but not in any target doc (manual removal)
7. **`test_query_search_with_special_chars`** — search for `%`, `_`, `'`, `"` (SQL LIKE escaping)
8. **`test_query_topics_empty_db`** — no entries, verify empty list not error
9. **`test_reactivation_while_still_stale`** — entry reappears but confidence still < 0.3 (should stay demoted)
10. **`test_sweep_updates_confidence_even_if_no_decay`** — verify base confidence recalculated from citations even if no time decay

### Existing Test Conventions (from analysis)

The existing tests follow these patterns:
- **Fixtures:** `tmp_path` (pytest builtin), `store(tmp_path)` (MetadataStore fixture)
- **Assertion style:** Direct `assert`, no fluent chains
- **Mock strategy:** Monkeypatching (`store.upsert_entry = failing_upsert`) not `unittest.mock`
- **Naming:** `test_<function>_<scenario>` (e.g., `test_upsert_increments_snapshot_count`)
- **Class grouping:** Tests grouped by class (`TestValidateAndFilter`, `TestEnsureSchema`)

The plan should follow these conventions.

---

## Python Idiom Observations

### Excellent Patterns (keep these)

1. **Explicit transactions:** `begin_transaction()` / `commit_transaction()` / `rollback_transaction()` wrapper methods instead of raw `conn.execute("BEGIN")`. Clean and testable.

2. **Type hints:** All function signatures in the plan have proper type hints. Good.

3. **Dataclasses for results:** `SweepResult`, `DemotionResult` use `@dataclass`. Pythonic.

4. **Context-free datetime imports:** The plan imports `datetime, timezone` explicitly, not `from datetime import *`. Good namespace hygiene.

### Potential Improvements

1. **Missing `__future__` import:** The plan's new code doesn't show `from __future__ import annotations` at the top of new functions. All existing modules have this. Add it for consistency.

2. **String formatting:** The plan uses f-strings, which matches existing code. Good.

3. **Pathlib:** The plan uses `Path` consistently. Good.

4. **No type: ignore comments:** The existing code has zero type ignore comments. Keep this standard — fix types, don't suppress.

---

## Error Handling Gaps

### Missing Exception Handling

1. **`apply_decay_penalty()`** — no handling for `ValueError` if `last_seen` is malformed (e.g., manual edit to DB)

2. **`sweep_all_entries()`** — catches `BaseException` (too broad). Should catch `Exception` and let `KeyboardInterrupt` / `SystemExit` propagate.

3. **CLI query handler** — no exception handling for database errors. The plan shows the handler but not error paths.

### Recommended Exception Strategy

```python
# In apply_decay_penalty:
try:
    last_seen_dt = datetime.fromisoformat(last_seen)
except ValueError:
    # Corrupt timestamp, assume stale
    return 0.0

# In sweep_all_entries:
try:
    # ... sweep logic
except Exception:  # Not BaseException
    metadata_store.rollback_transaction()
    raise
```

---

## File Impact Summary Verification

The plan claims ~565 lines across 11 files, ~29 new tests. Let me verify this is realistic:

| File | Claimed Lines | Plausibility |
|------|---------------|--------------|
| `metadata.py` | +60 | Reasonable (migration + 7 methods @ ~8 lines each) |
| `validator.py` | +90 | Reasonable (2 functions + helper @ ~30 lines each) |
| `promoter.py` | +50 | Reasonable (1 function @ ~50 lines) |
| `journal.py` | +10 | Reasonable (1 method @ ~10 lines) |
| `__main__.py` | +80 | Reasonable (subparsers + 2 handlers @ ~40 lines each) |
| Test files | +260 | Reasonable (~29 tests @ ~9 lines each) |
| Docs | +15 | Reasonable |

**Total:** ~565 lines. **Assessment:** Plausible.

---

## Summary of Required Changes

### Before Implementation Starts

1. **Fix timezone mixing in `apply_decay_penalty()`** (C1)
2. **Add SQLite version check in `migrate_to_v2()`** (C2)
3. **Use parameterized queries in `search_entries()`** (C3)
4. **Add NULL `last_seen` handling in `sweep_all_entries()`** (C4)
5. **Preserve `demoted_at` during re-promotion** (C5)

### During Implementation

6. **Clarify `stale_streak` naming or add docstring** (M1)
7. **Document demotion limitations for manually edited files** (M2)
8. **Exclude orphaned entries from sweep** (M3)
9. **Add empty DB case to CLI handlers** (M4)
10. **Clarify decay formula in docstring** (M5)
11. **Add demotion crash recovery in sweep** (M6)
12. **Specify CLI query exit codes** (M7)
13. **Extract `_validate_entry_citations()` to avoid duplication** (M8)
14. **Rename `get_promoted_entries()` to `get_validated_entries()`** (M9)
15. **Add `DEMOTION_STREAK_THRESHOLD` constant** (M10)
16. **Specify `get_topics()` SQL and filters** (M11)
17. **Fix argparse backward compatibility** (M12)

### Before Merge

18. **Add 10 missing edge-case tests** (see Test Coverage Gaps)
19. **Verify all 119 existing tests still pass**
20. **Run `mypy` if configured (no type: ignore)**

---

## Positive Observations

1. **Transaction discipline:** The plan correctly wraps all multi-step operations (sweep, validation) in transactions. Crash safety is a first-class concern.

2. **Idempotent migrations:** The migration check (`_column_exists`) before `ALTER TABLE` is correct.

3. **Hysteresis:** The 2-sweep threshold before demotion is a good safeguard against premature removal.

4. **Separation of concerns:** Decay is separate from `compute_confidence()`, keeping `citations.py` pure. This is excellent design.

5. **Backward compatibility:** The CLI preserves existing behavior when no subcommand is given (with the fix from M12).

6. **Test-first mindset:** The plan includes tests for each task. Good.

---

## Final Verdict

**Overall Quality:** B+ (Good, with critical fixes required)

**Readiness for Implementation:** No — must fix C1-C5 before starting Task 2.

**Estimated Fix Time:** 2-4 hours to address all critical and moderate issues in the plan.

**Recommendation:** Revise the plan to incorporate fixes from C1-C5 and clarifications from M1-M12, then proceed to implementation.
