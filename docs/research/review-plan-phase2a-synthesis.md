# Synthesis Report: intermem Phase 2A Plan Review

**Context:** Multi-agent review of `docs/plans/2026-02-18-intermem-phase2a-decay-demotion.md`
**Date:** 2026-02-18
**Agents:** 3 launched (correctness, architecture, quality), 3 completed, 0 failed
**Verdict:** NEEDS-CHANGES

---

## Summary

Three agents reviewed the Phase 2A implementation plan from complementary perspectives. The plan has a sound overall structure but contains **6 critical issues** (P0) and **7 high-priority issues** (P1) that must be addressed before implementation. An additional 10 moderate issues should be fixed during implementation.

---

## Verdict Summary

| Agent | Status | Summary |
|-------|--------|---------|
| fd-correctness | NEEDS_ATTENTION | 2 P0, 2 P1 found — journal/DB divergence on crash, Citation.raw_match reconstruction broken |
| fd-architecture | NEEDS_ATTENTION | 3 must-fix issues — raw SQL in validator.py violates boundaries, demotion matching fragile, CLI breaks backward compat |
| fd-quality | NEEDS_ATTENTION | 5 critical issues — timezone mixing, SQL injection risk, NULL handling, orphaned entries, audit trail loss |

---

## Critical Findings (MUST FIX BEFORE IMPLEMENTATION)

### P0-1: Journal/DB Divergence on Crash (Correctness ≈ Quality M6)

**Agent attribution:** fd-correctness (P0-1), fd-quality (M6)
**Convergence:** 2/3 agents
**Severity:** P0 CRITICAL

**Issue:**
If the process crashes after `sweep_all_entries()` commits but before `demote_entries()` finishes, the journal records "demoted" status but the DB still has "stale". Entry is removed from AGENTS.md but DB doesn't know it's demoted. Next sweep cannot detect this inconsistency because `PromotionJournal.get_incomplete()` returns entries where `status != "pruned"`, and "demoted" entries will appear incomplete forever.

**Fix:**
Journal entries for demotions should transition to a terminal state. Change `record_demoted()` to mark entries as "demoted-committed" or use existing "pruned" status. Add recovery check at start of `sweep_all_entries()` to reconcile journal with DB.

**Location:** Task 2 (sweep), Task 3 (demote), lines 113-160, 220-232

---

### P0-2: Citation.raw_match Reconstruction Broken (Correctness P0-2)

**Agent attribution:** fd-correctness (unique finding)
**Severity:** P0 CRITICAL

**Issue:**
Task 2's `_revalidate_citations()` helper needs to construct `Citation` objects from DB rows, but `Citation.__init__` requires `raw_match` field (citations.py line 23). The DB stores only `citation_type` and `citation_value`. Sweep will crash with `TypeError` on first entry with citations.

**Fix:**
Use `raw_match = citation_value` as approximation:

```python
citation = Citation(
    type=row["citation_type"],
    value=row["citation_value"],
    raw_match=row["citation_value"],  # Sufficient for validation
)
```

This is correct because `validate_citation()` never uses `raw_match` (citations.py lines 135-167).

**Location:** Task 2 `_revalidate_citations()`, line 162

---

### P0-3: Timezone Mixing in Decay Calculation (Quality C1)

**Agent attribution:** fd-quality (unique finding)
**Severity:** P0 CRITICAL

**Issue:**
`apply_decay_penalty()` stores `last_seen` via SQLite's `datetime('now')` (timezone-naive format), but uses Python's `datetime.now(timezone.utc)` (timezone-aware) for `current_time`. The subtraction `(current_time - last_seen_dt).days` will raise `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Fix:**
Parse as naive, then make UTC-aware:

```python
last_seen_dt = datetime.fromisoformat(last_seen)
if last_seen_dt.tzinfo is None:
    last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
if current_time.tzinfo is None:
    current_time = current_time.replace(tzinfo=timezone.utc)
days_since = (current_time - last_seen_dt).days
```

**Location:** Task 2 `apply_decay_penalty()`, line 96

---

### P0-4: Raw SQL in validator.py Violates Boundaries (Architecture A1 ≈ Quality C5)

**Agent attribution:** fd-architecture (A1 CRITICAL), fd-quality (C5 MEDIUM — re-promotion audit trail)
**Convergence:** 2/3 agents (compatible fixes)
**Severity:** P0 CRITICAL (boundary violation)

**Issue:**
Task 6 adds raw SQL directly in validator.py:

```python
metadata_store.conn.execute(
    "UPDATE memory_entries SET status = 'active', stale_streak = 0, demoted_at = NULL WHERE entry_hash = ?",
    (entry_hash,)
)
```

This bypasses the data access layer. All existing validator.py code calls methods like `upsert_entry()`, `update_confidence()` — never direct `conn.execute()`. Violates established boundary pattern.

**Fix:**
Add method to metadata.py (Task 1):

```python
def reactivate_entry(self, entry_hash: str) -> None:
    """Reset a demoted entry to active status, clearing demotion markers."""
    self.conn.execute(
        "UPDATE memory_entries SET status = 'active', stale_streak = 0, reactivated_at = datetime('now') WHERE entry_hash = ?",
        (entry_hash,)
    )
    # Keep demoted_at for audit trail (don't set to NULL)
```

Quality agent notes that nulling `demoted_at` loses audit history. Keep `demoted_at`, add `reactivated_at` column for tracking re-promotion cycles.

**Location:** Task 6 re-promotion, lines 349-357

---

### P0-5: SQL Injection in search_entries() (Quality C3)

**Agent attribution:** fd-quality (unique finding)
**Severity:** P0 CRITICAL (security)

**Issue:**
Task 1 adds `search_entries(keywords: str)` with "LIKE query on content_preview + section" but doesn't show implementation. If using string interpolation for LIKE patterns, vulnerable to SQL injection (e.g., `keywords="'; DROP TABLE memory_entries; --"`).

**Fix:**
Use parameterized queries:

```python
def search_entries(self, keywords: str) -> list[dict]:
    if not keywords.strip():
        return []
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

**Location:** Task 1 `search_entries()`, line 64

---

### P0-6: NULL last_seen Handling Missing (Quality C4)

**Agent attribution:** fd-quality (unique finding)
**Severity:** P0 CRITICAL

**Issue:**
Task 2 calls `apply_decay_penalty(base_confidence, row["last_seen"], current_time)` without checking if `last_seen` is NULL. While schema sets `DEFAULT (datetime('now'))`, entries created before migration or via manual INSERT could have NULL. Will cause `TypeError` in `datetime.fromisoformat(None)`.

**Fix:**
Add NULL check in `sweep_all_entries()`:

```python
last_seen = row["last_seen"]
if last_seen is None:
    last_seen = datetime.now(timezone.utc).isoformat()
    metadata_store.conn.execute(
        "UPDATE memory_entries SET last_seen = ? WHERE entry_hash = ?",
        (last_seen, entry_hash)
    )
decayed_confidence = apply_decay_penalty(base_confidence, last_seen, current_time)
```

**Location:** Task 2 `sweep_all_entries()`, line 133

---

## High-Priority Findings (MUST FIX BEFORE MERGE)

### P1-1: Decay Formula Off-By-One at Day 28 (Correctness P1-1 ≈ Quality M5)

**Agent attribution:** fd-correctness (P1-1), fd-quality (M5)
**Convergence:** 2/3 agents (correctness has clearer analysis)
**Severity:** P1 HIGH

**Issue:**
The guard `if days_since <= 14: return confidence` means day 14 has no penalty. At day 28, `28 // 14 = 2` → penalty = 0.2, not 0.1. The PRD's English description says "per 14-day period beyond the first 14 days" (suggesting days 15-28 are first penalty period), but the mathematical formula is `periods = days_since // 14` (which treats day 28 as end of period 2).

**Timeline:**
- Day 14: no penalty (caught by guard)
- Day 15: penalty 0.1 ✓
- Day 28: penalty 0.2 ✗ (should be 0.1 per English description)
- Day 29: penalty 0.2 ✓

**Fix options:**
1. Accept day 28 getting penalty 0.2 as correct (per mathematical formula), OR
2. Adjust formula for day 28 to get penalty 0.1 (match English description):

```python
if days_since <= 14:
    return confidence
days_beyond_grace = days_since - 14
periods = (days_beyond_grace + 13) // 14  # Round to next period
penalty = 0.1 * periods
```

**Clarification needed:** Ask user which interpretation is correct. Update either formula or PRD description.

**Location:** Task 2 `apply_decay_penalty()`, lines 90-102

---

### P1-2: stale_streak Not Reset in Normal Validation (Correctness P1-2)

**Agent attribution:** fd-correctness (unique finding)
**Severity:** P1 HIGH

**Issue:**
When an entry's status transitions from 'stale' to 'active' during normal validation (not sweep), `stale_streak` is not reset. Creates inconsistent state (status='active', stale_streak=1). If entry decays again before next sweep, premature demotion.

**Failure scenario:**
1. Entry decays to stale, `stale_streak = 1`
2. User fixes citation, normal synthesis runs
3. `update_confidence()` sets status='active', but doesn't reset `stale_streak`
4. Entry has status='active', `stale_streak=1` (inconsistent)
5. Next sweep decrements confidence to stale again
6. Sweep increments `stale_streak` to 2 → demoted (prematurely)

**Fix:**
Make `update_confidence()` auto-reset `stale_streak` on stale→active transition:

```python
def update_confidence(self, entry_hash: str, confidence: float) -> None:
    old_row = self.get_entry(entry_hash)
    old_status = old_row["status"] if old_row else None
    status = "active" if confidence >= STALE_THRESHOLD else "stale"
    now = datetime.now(timezone.utc).isoformat()
    self.conn.execute(
        "UPDATE memory_entries SET confidence = ?, confidence_updated_at = ?, status = ? WHERE entry_hash = ?",
        (confidence, now, status, entry_hash),
    )
    if old_status == "stale" and status == "active":
        self.reset_stale_streak(entry_hash)
```

**Location:** Task 6, normal validation in validator.py

---

### P1-3: Demotion Matching Fragile (Architecture A2 ≈ Quality M2)

**Agent attribution:** fd-architecture (A2 HIGH), fd-quality (M2 MEDIUM)
**Convergence:** 2/3 agents (architecture has better fix)
**Severity:** P1 HIGH

**Issue:**
Task 3 says "scan each target doc for lines matching content + `<!-- intermem -->` marker". But `content_preview` is truncated to 80 chars. Matching by truncated content will fail for entries >80 chars or match wrong line if two entries share same 80-char prefix. Current promoter.py doesn't embed entry hash in marker.

**Fix:**
Embed hash in marker (architecture agent's Option B):

1. Change `MARKER` to `f"<!-- intermem:{entry_hash[:8]} -->"`
2. Demotion scans for `<!-- intermem:<hash_prefix> -->` and removes that line
3. Re-promotion detects existing marker with same hash
4. 8-char hash prefix is collision-safe for <1000 entries (per CLAUDE.md)

**Implementation impact:**
- Task 3: Update promoter.py to embed hash
- Task 3: Demotion uses regex `<!-- intermem:([a-f0-9]{8}) -->` to extract hash
- Task 6: Re-promotion checks if existing marker has same hash before re-adding
- Backward-compatible: old markers still detected via `_INTERMEM_MARKER_RE`

**Location:** Task 3 `demote_entries()`, lines 226-232

---

### P1-4: CLI Backward Compatibility Broken (Architecture A4 ≈ Quality M12)

**Agent attribution:** fd-architecture (A4 HIGH), fd-quality (M12 MODERATE)
**Convergence:** 2/3 agents (architecture has cleaner solution)
**Severity:** P1 HIGH (user-facing breakage)

**Issue:**
Plan moves existing args to `synthesize` subparser. This breaks `python -m intermem --project-dir . --validate` (no subcommand) because argparse will reject `--project-dir` (not on parent parser).

**Current usage:**
```bash
python -m intermem --project-dir . --dry-run --validate
```

**After proposed change:**
```bash
python -m intermem synthesize --project-dir . --dry-run --validate  # new
python -m intermem --project-dir . --dry-run --validate              # BREAKS
```

**Fix:**
Keep common args on parent parser:

```python
parser = argparse.ArgumentParser(description="Intermem memory synthesis")
# ALL existing args here (project-dir, dry-run, auto-approve, validate, etc.)
parser.add_argument(...)

subparsers = parser.add_subparsers(dest="command", required=False)

# sweep and query subparsers only add their specific flags
sweep_parser = subparsers.add_parser("sweep", ...)
query_parser = subparsers.add_parser("query", ...)

args = parser.parse_args()

if args.command == "sweep":
    # handle sweep
elif args.command == "query":
    # handle query
else:
    # Fall through to synthesis (all flags work without subcommand)
```

**Location:** Task 4 CLI handlers, lines 258-279

---

### P1-5: Re-promotion Logic is Dead Code (Correctness P2-2)

**Agent attribution:** fd-correctness (P2-2 MODERATE, but logic bug)
**Severity:** P1 HIGH (logic bug, not just cosmetic)

**Issue:**
Task 6 adds re-promotion check:

```python
if row and row["status"] == "demoted" and confidence >= STALE_THRESHOLD:
    metadata_store.conn.execute("UPDATE ... SET status = 'active' ...")
```

But this runs AFTER `update_confidence()` (line 103), which unconditionally overwrites status:

```python
status = "active" if confidence >= STALE_THRESHOLD else "stale"
```

So if entry has status='demoted' and confidence=0.8, `update_confidence()` changes status to 'active' BEFORE re-promotion check. Check never matches.

**Fix Option 1:**
Check demoted status BEFORE update_confidence():

```python
old_row = metadata_store.get_entry(entry_hash)
was_demoted = old_row and old_row["status"] == "demoted"
confidence = compute_confidence(0.5, checks, snapshot_count)
if was_demoted and confidence >= STALE_THRESHOLD:
    metadata_store.reactivate_entry(entry_hash)  # Uses P0-4 fix
else:
    metadata_store.update_confidence(entry_hash, confidence)
```

**Fix Option 2:**
Make `update_confidence()` preserve 'demoted' status, let explicit re-promotion handle it.

**Location:** Task 6 `validate_and_filter_entries()`, lines 349-357

---

### P1-6: Orphaned Entries Not Handled in Sweep (Quality M3)

**Agent attribution:** fd-quality (unique finding)
**Severity:** P1 HIGH (specification gap)

**Issue:**
Sweep query is `SELECT * FROM memory_entries WHERE status != 'demoted'`. This includes orphaned entries (status='orphaned'). Plan doesn't specify what happens to orphaned entries during sweep. Should they be re-validated, skipped, or promoted to demotion candidates?

**Fix:**
Clarify in plan. Recommendation: exclude orphaned from sweep (they can't decay further if source file disappeared):

```python
entries = metadata_store.conn.execute(
    "SELECT * FROM memory_entries WHERE status IN ('active', 'stale')"
).fetchall()
```

**Location:** Task 2 `sweep_all_entries()`, line 119

---

### P1-7: SQLite Version Constraint Not Enforced (Quality C2)

**Agent attribution:** fd-quality (unique finding)
**Severity:** P1 HIGH (migration failure on older SQLite)

**Issue:**
Migration uses `ALTER TABLE ADD COLUMN ... NOT NULL DEFAULT`. SQLite only supports `NOT NULL` with `DEFAULT` in `ALTER TABLE` starting in SQLite 3.37.0 (2021-11-27). Python 3.11 bundles 3.37.0+, but plan should document/enforce this.

**Fix:**
Add version check:

```python
def migrate_to_v2(self) -> None:
    """Add Phase 2A columns (requires SQLite 3.37.0+)."""
    version = self.conn.execute("SELECT sqlite_version()").fetchone()[0]
    major, minor, patch = map(int, version.split('.'))
    if (major, minor, patch) < (3, 37, 0):
        raise RuntimeError(
            f"SQLite {version} does not support ALTER TABLE with NOT NULL DEFAULT. "
            f"Upgrade to SQLite 3.37.0+ or Python 3.11+."
        )
    # ... rest of migration
```

**Location:** Task 1 `migrate_to_v2()`, line 38

---

## Moderate Findings (SHOULD FIX)

### M1: Float Equality for Decay Accounting (Correctness P2-1)

**Severity:** P2 MODERATE

**Issue:**
`if decayed_confidence != base_confidence: entries_decayed += 1` uses float equality. Floating point rounding can make count off by 1-2.

**Fix:**
Use tolerance: `if abs(decayed_confidence - base_confidence) > 1e-9: entries_decayed += 1`

**Impact:** Cosmetic (affects reporting, not data integrity)

**Location:** Task 2 `sweep_all_entries()`, line 138

---

### M2: Task 5 Redundant (Architecture A3)

**Severity:** MEDIUM (task structure)

**Issue:**
Task 5 is titled "Wire Sweep into Demotion Pipeline" but only adds 3 lines of SQL and a field to `SweepResult`. Real work is in Tasks 2 and 3. This is artificial separation.

**Fix:**
Collapse Task 5 into Task 2:
- Add `demotion_candidates` field to `SweepResult` and populate it in `sweep_all_entries()`
- Move `test_full_lifecycle_decay_to_demotion` to Task 2

**Impact:** Simplifies task structure, reduces merge conflicts

**Location:** Task 5 (lines 305-335)

---

### M3: Schema CHECK Constraint Split-Brain (Correctness P3-1, Architecture A8)

**Severity:** P3 MINOR

**Issue:**
Plan says "SQLite can't ALTER CHECK constraints. For existing DBs, we accept 'demoted' without CHECK enforcement." Creates split-brain:
- New DBs: CHECK includes 'demoted'
- Existing DBs: CHECK rejects 'demoted'

**Fix:**
Accept and document. Add comment to `migrate_to_v2()`:

```python
"""Note: CHECK constraint on status only enforced for new DBs (created after Phase 2A).
Existing DBs accept 'demoted' status but don't have CHECK enforcement. This is acceptable
because all status updates go through MetadataStore methods, not raw SQL."""
```

**Impact:** Documentation clarity only

**Location:** Task 1 migration, lines 32-49

---

### M4: Unused get_promoted_entries() Method (Architecture A7, Quality M9)

**Severity:** LOW

**Issue:**
Task 1 adds `get_promoted_entries()` but it's never called anywhere in Tasks 2-7. YAGNI violation.

**Fix:**
Remove from plan. Add when concrete use case appears.

**Location:** Task 1, line 61

---

### M5: Demotion Matching Edge Cases (Quality M2)

**Severity:** MEDIUM (P1-3 fix handles this)

**Issue:**
Quality agent notes demotion fragile if user manually edited line or multiple entries have identical prefixes. Architecture agent's hash-in-marker fix (P1-3) resolves this.

**Action:** Covered by P1-3 fix.

---

### M6: CLI Query Exit Codes Unclear (Quality M7)

**Severity:** LOW

**Issue:**
Plan says "Exit code 0 on results, 1 on no results, 2 on error" but doesn't specify what counts as "no results" vs "error".

**Fix:**
Specify in plan:
- 0 = query succeeded (even if 0 results)
- 1 = user error (invalid flags)
- 2 = system error (DB corrupt, permission denied)

**Location:** Task 4 CLI query handler, line 294

---

### M7: Hysteresis Threshold Hard-Coded (Quality M10)

**Severity:** LOW

**Issue:**
`stale_streak >= 2` is hard-coded. Future tuning requires code changes.

**Fix:**
Add constant:

```python
DEMOTION_STREAK_THRESHOLD = 2

if row_updated["stale_streak"] >= DEMOTION_STREAK_THRESHOLD:
    entries_marked += 1
```

**Location:** Task 2 sweep logic, line 19

---

### M8: get_topics() Implementation Underspecified (Quality M11)

**Severity:** LOW

**Issue:**
Task 1 says "`get_topics()` — GROUP BY section with COUNT and AVG(confidence)" but doesn't specify which statuses to include.

**Fix:**
Specify in plan: include active/stale, exclude demoted/orphaned.

```python
def get_topics(self) -> list[dict]:
    rows = self.conn.execute("""
        SELECT section, COUNT(*) as entry_count, AVG(confidence) as avg_confidence
        FROM memory_entries
        WHERE status IN ('active', 'stale')
        GROUP BY section ORDER BY entry_count DESC
    """).fetchall()
    return [dict(row) for row in rows]
```

**Location:** Task 1, line 65

---

### M9: Empty DB Edge Case (Quality M4)

**Severity:** LOW

**Issue:**
If DB has no entries, sweep returns `SweepResult(entries_swept=0, ...)`. Plan doesn't show how CLI handles this.

**Fix:**
Add to CLI sweep handler:

```python
if sweep_result.entries_swept == 0:
    print("No entries to sweep.")
    sys.exit(0)
```

**Location:** Task 2 sweep CLI handler

---

### M10: _revalidate_citations() Duplicates Logic (Quality M8)

**Severity:** LOW

**Issue:**
Helper duplicates citation validation logic from `validate_and_filter_entries()`. DRY violation.

**Fix:**
Extract pure function `_validate_entry_citations()` that both call.

**Location:** Task 2 `_revalidate_citations()`, line 162

---

## Conflicts

None. All three agents converged on the critical issues, with complementary perspectives providing additional context for fixes.

---

## Test Coverage Recommendations

Add these tests (quality agent identified 10 missing edge cases):

1. `test_migrate_v2_on_empty_db` — migration on fresh DB
2. `test_apply_decay_negative_days` — last_seen in future (clock skew)
3. `test_sweep_concurrent_sweep_attempts` — transaction isolation
4. `test_demote_already_demoted_entry` — idempotency
5. `test_demote_entry_not_in_target_doc` — entry hash in DB but removed from doc
6. `test_query_search_with_special_chars` — SQL LIKE escaping (`%`, `_`, `'`, `"`)
7. `test_query_topics_empty_db` — no entries, verify empty list not error
8. `test_reactivation_while_still_stale` — entry reappears but confidence < 0.3
9. `test_sweep_handles_null_last_seen` — NULL last_seen doesn't crash
10. `test_decay_with_naive_last_seen` — timezone compatibility

---

## Files

**Agent reports:**
- `/root/projects/Interverse/docs/research/review-plan-correctness.md`
- `/root/projects/Interverse/docs/research/review-plan-phase2a-architecture.md`
- `/root/projects/Interverse/docs/research/review-plan-quality.md`

**Plan under review:**
- `/root/projects/Interverse/docs/plans/2026-02-18-intermem-phase2a-decay-demotion.md`
