# Correctness Review: intermem Phase 2A Implementation Plan

**Date:** 2026-02-18
**Reviewer:** Julik
**Document:** `docs/plans/2026-02-18-intermem-phase2a-decay-demotion.md`
**Status:** 7 findings (2 P0, 2 P1, 2 P2, 1 P3)

---

## Summary

The plan has two critical correctness issues (P0) that will cause data integrity failures, two high-severity issues (P1) affecting recovery and consistency, and several moderate issues (P2-P3) affecting reliability and maintainability.

The primary risks:
1. **Journal/DB divergence on crash** - journal records demotions incrementally, DB transaction rolls back all updates
2. **Citation reconstruction from DB is broken** - revalidation helper can't build Citation objects from DB rows
3. **Re-promotion bypasses update_confidence()** - direct SQL UPDATE creates status field that disagrees with derived status
4. **stale_streak divergence** - normal validation path can reset status to 'active' while stale_streak stays > 0

---

## P0: Critical Data Integrity Issues

### P0-1: Journal/DB Divergence on Crash Between Sweep and Demotion

**Location:** Task 2 `sweep_all_entries()`, Task 3 `demote_entries()`, lines 113-160, 220-232

**Issue:** If the process crashes after sweep completes but before `demote_entries()` finishes:

```
Time T0: sweep_all_entries() completes, commits transaction
         Entry 247 has stale_streak = 2, status = 'stale'
Time T1: CLI handler starts calling demote_entries([entry_247, ...])
Time T2: demote_entries() removes entry 247 from AGENTS.md (filesystem write)
Time T3: journal.record_demoted(entry_247) writes to journal (JSONL append)
Time T4: Process crashes before metadata_store.mark_demoted(entry_247) runs
Time T5: DB still has entry 247 with status = 'stale', stale_streak = 2
         Journal has status = "demoted" for entry 247
         AGENTS.md no longer contains entry 247
```

**Consequence:** Entry 247 is gone from AGENTS.md but DB doesn't know it's demoted. The sweep will keep decaying it every run. If the entry reappears in auto-memory, the normal validation path checks `if status == "demoted"` to re-promote, but status is 'stale', so the entry gets treated as a duplicate and rejected by dedup.

**The plan's recovery description (line 236)** says "next sweep detects this" but provides no code for detection. The journal tracks promotions and now demotions, but the sweep doesn't check the journal for inconsistencies.

**Fix required:**

Add recovery check at the start of `sweep_all_entries()`:

```python
def sweep_all_entries(metadata_store, project_root, journal):
    # Crash recovery: reconcile journal with DB
    for journal_entry in journal.get_incomplete():
        if journal_entry.status == "demoted":
            row = metadata_store.get_entry(journal_entry.entry_hash)
            if row and row["status"] != "demoted":
                # Divergence: file was removed but DB not updated
                metadata_store.mark_demoted(journal_entry.entry_hash)

    # Begin main sweep transaction
    metadata_store.begin_transaction()
    try:
        ...
```

But the journal is `PromotionJournal` and tracks "pending", "committed", "pruned" status (journal.py lines 18, 86-114). Task 3 adds "demoted" as a new status value. The `get_incomplete()` method returns entries where `status != "pruned"`, so "demoted" entries will appear as incomplete forever.

**Better fix:** Journal entries for demotions should transition to a terminal state. Change `record_demoted()` to mark entries as "demoted-committed" or use the existing "pruned" status (since removal from target doc is analogous to pruning from source).

**Severity:** P0 because partial demotion leaves DB in inconsistent state and breaks re-promotion logic.

---

### P0-2: Citation Reconstruction from DB is Broken

**Location:** Task 2 `_revalidate_citations()`, line 162

**Issue:** The helper needs to construct `Citation` objects from DB rows to pass to `validate_citation()`. But `Citation.__init__` requires `raw_match` (citations.py line 23), and the DB stores only `citation_type` and `citation_value` (metadata.py lines 103-120).

**Failure narrative:**

```python
def _revalidate_citations(entry_hash, metadata_store, project_root):
    rows = metadata_store.conn.execute(
        "SELECT citation_type, citation_value FROM citations WHERE entry_hash = ?",
        (entry_hash,)
    ).fetchall()

    checks = []
    for row in rows:
        citation = Citation(
            type=row["citation_type"],
            value=row["citation_value"],
            raw_match=???  # NOT IN DATABASE → TypeError
        )
        result = validate_citation(citation, project_root)
        checks.append(result)
    return checks
```

**Why raw_match isn't in the DB:** It's not needed for validation. `validate_citation()` only uses `citation.type` and `citation.value` (citations.py lines 135-167). The `raw_match` field exists for audit/debugging (to show what text was originally matched in the entry content).

**Fix:**

Use `raw_match = citation_value` as an approximation:

```python
def _revalidate_citations(entry_hash, metadata_store, project_root):
    rows = metadata_store.conn.execute(
        "SELECT citation_type, citation_value FROM citations WHERE entry_hash = ?",
        (entry_hash,)
    ).fetchall()

    checks = []
    for row in rows:
        citation = Citation(
            type=row["citation_type"],
            value=row["citation_value"],
            raw_match=row["citation_value"],  # Approximation, sufficient for validation
        )
        result = validate_citation(citation, project_root)
        checks.append(result)
    return checks
```

This is correct because `raw_match` is never used by `validate_citation()` or `compute_confidence()`.

**Severity:** P0 because sweep will crash with TypeError on first entry with citations.

---

## P1: High-Severity Consistency Issues

### P1-1: Decay Formula Off-By-One at Day 28

**Location:** Task 2 `apply_decay_penalty()`, lines 90-102

**Issue:** The guard `if days_since <= 14: return confidence` means day 14 has no penalty. But at day 28, `28 // 14 = 2` → penalty = 0.2, not 0.1.

**Timeline check:**

- Day 14: 14 // 14 = 1, but guard catches it → penalty = 0
- Day 15: 15 // 14 = 1 → penalty = 0.1 ✓
- Day 28: 28 // 14 = 2 → penalty = 0.2 ✗ (should be 0.1)
- Day 29: 29 // 14 = 2 → penalty = 0.2 ✓

**The PRD says** "per 14-day period beyond the first 14 days". If the first 14 days (0-14) are the grace period, then:
- Days 15-28 should be the first penalty period → penalty 0.1
- Days 29-42 should be the second penalty period → penalty 0.2

But the formula `periods = days_since // 14` treats day 28 as the end of period 2, not period 1.

**The PRD's acceptance criteria** say "−0.1 * floor(days_since_last_seen / 14) for ages >14 days", which is the formula in the plan. So the PRD's mathematical formula doesn't match its English description.

**This is a specification ambiguity.** Either:
1. Day 28 getting penalty 0.2 is correct (per the mathematical formula), or
2. Day 28 should get penalty 0.1 (per the English description), and the formula needs adjustment:

```python
if days_since <= 14:
    return confidence
days_beyond_grace = days_since - 14
periods = (days_beyond_grace + 13) // 14  # Round to next period
penalty = 0.1 * periods
```

This gives: day 15 → penalty 0.1, day 28 → penalty 0.1, day 29 → penalty 0.2.

**Severity:** P1 because it creates a discontinuity in the decay curve at day 28, potentially causing premature demotion for entries exactly 28 days old. But it doesn't corrupt data, and the behavior is consistent (just possibly wrong vs. intent).

---

### P1-2: stale_streak Not Reset in Normal Validation Path

**Location:** Task 6 re-promotion logic, normal validation in validator.py

**Issue:** When an entry's status transitions from 'stale' to 'active' during normal validation (not during sweep), `stale_streak` is not reset. This creates inconsistent state.

**Failure narrative:**

```
Time T0: Entry has confidence 0.3 (active), stale_streak = 0
Time T1: Sweep runs, entry decays to confidence 0.25 (stale)
         sweep increments stale_streak to 1
         Entry: status = 'stale', stale_streak = 1
Time T2: User fixes a broken citation
Time T3: Normal synthesis run calls validate_and_filter_entries()
         Entry has 1 valid citation now, confidence = 0.8
         update_confidence() sets status = 'active'
         BUT stale_streak is not reset
         Entry: status = 'active', stale_streak = 1  ← inconsistent
Time T4: Next sweep runs, entry decays slightly to confidence 0.28 (stale)
         sweep increments stale_streak to 2
         Entry marked for demotion (streak >= 2)
```

The sweep WILL eventually reset stale_streak when the entry is healthy (line 148 of plan), but between T3 and T4, the entry has inconsistent state. If the entry decays again before the sweep resets the streak, it gets prematurely demoted.

**Fix:**

Make `update_confidence()` auto-reset stale_streak on stale→active transition:

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

    # Reset streak on stale→active transition
    if old_status == "stale" and status == "active":
        self.reset_stale_streak(entry_hash)
```

**Severity:** P1 because inconsistent state can cause premature demotion if decay happens before the next sweep resets the streak.

---

## P2: Moderate Issues

### P2-1: Float Equality for Decay Accounting

**Location:** Task 2 `sweep_all_entries()`, line 138

**Issue:** `if decayed_confidence != base_confidence: entries_decayed += 1`

This uses float equality to count how many entries were decayed. Floating point arithmetic can produce values that differ by epsilon.

**Example:**

If confidence is 0.333... (from `compute_confidence` with multiple citation checks), then `0.333... - 0.1` may have rounding error, causing the equality check to incorrectly register or miss a decay.

**Consequence:** `entries_decayed` count could be off by a few entries. This is a cosmetic reporting issue, not a correctness issue.

**Fix:**

Use a tolerance: `if abs(decayed_confidence - base_confidence) > 1e-9: entries_decayed += 1`

**Severity:** P2 because it only affects reporting, not data integrity.

---

### P2-2: Re-promotion Logic is Dead Code

**Location:** Task 6, lines 349-357

**Issue:** The plan adds re-promotion logic to `validate_and_filter_entries()`:

```python
row = metadata_store.get_entry(entry_hash)
if row and row["status"] == "demoted" and confidence >= STALE_THRESHOLD:
    metadata_store.conn.execute(
        "UPDATE memory_entries SET status = 'active', stale_streak = 0, demoted_at = NULL WHERE entry_hash = ?",
        (entry_hash,)
    )
```

But this check runs AFTER `update_confidence()` (line 103), which unconditionally overwrites status:

```python
# metadata.py update_confidence(), line 150:
status = "active" if confidence >= STALE_THRESHOLD else "stale"
```

So if an entry has status = 'demoted' and confidence = 0.8, `update_confidence()` changes status to 'active' BEFORE the re-promotion check runs. The check `if row["status"] == "demoted"` will never match.

**The observable behavior is still correct** - demoted entries with good citations DO become active, just via `update_confidence()` overwriting status, not via the explicit re-promotion logic.

**But this is a logic bug in the plan** because the re-promotion code is dead.

**Fix option 1:** Check demoted status BEFORE update_confidence():

```python
old_row = metadata_store.get_entry(entry_hash)
was_demoted = old_row and old_row["status"] == "demoted"

confidence = compute_confidence(0.5, checks, snapshot_count)

if was_demoted and confidence >= STALE_THRESHOLD:
    # Re-promote: clear demotion state
    metadata_store.conn.execute(
        "UPDATE memory_entries SET status = 'active', confidence = ?, confidence_updated_at = ?, stale_streak = 0, demoted_at = NULL WHERE entry_hash = ?",
        (confidence, datetime.now(timezone.utc).isoformat(), entry_hash),
    )
else:
    metadata_store.update_confidence(entry_hash, confidence)
```

**Fix option 2:** Make `update_confidence()` preserve 'demoted' status:

```python
def update_confidence(self, entry_hash: str, confidence: float) -> None:
    old_row = self.get_entry(entry_hash)
    if old_row and old_row["status"] == "demoted":
        # Don't auto-promote demoted entries; let explicit re-promotion handle it
        self.conn.execute(
            "UPDATE memory_entries SET confidence = ?, confidence_updated_at = ? WHERE entry_hash = ?",
            (confidence, datetime.now(timezone.utc).isoformat(), entry_hash),
        )
        return

    status = "active" if confidence >= STALE_THRESHOLD else "stale"
    self.conn.execute(
        "UPDATE memory_entries SET confidence = ?, confidence_updated_at = ?, status = ? WHERE entry_hash = ?",
        (confidence, datetime.now(timezone.utc).isoformat(), status, entry_hash),
    )
```

**Severity:** P2 because the re-promotion check is dead code, but observable behavior is correct.

---

## P3: Minor Issues

### P3-1: Schema Migration Doesn't Update CHECK Constraint

**Location:** Task 1 `migrate_to_v2()`, lines 32-49

**Issue:** The plan says "SQLite can't ALTER CHECK constraints. For existing DBs, we accept 'demoted' as a valid status without CHECK enforcement."

This creates a split-brain situation:
- New DBs created after migration: CHECK includes 'demoted'
- Existing DBs created before migration: CHECK rejects 'demoted'

If someone manually sets status = 'demoted' in an existing DB via sqlite3 CLI, the CHECK constraint rejects it. But the application code will work fine because it doesn't rely on CHECK enforcement.

**Why this matters:** If a test creates a fresh DB during Phase 2A, the CHECK constraint includes 'demoted'. If production uses a Phase 1 DB, the constraint behavior differs. This can cause confusion during debugging.

**Fix:**

Either document this explicitly as a known limitation, or force a table rebuild (expensive but ensures consistency):

```python
def migrate_to_v2(self) -> None:
    # Add columns first (idempotent)
    if not self._column_exists("memory_entries", "stale_streak"):
        self.conn.execute(
            "ALTER TABLE memory_entries ADD COLUMN stale_streak INTEGER NOT NULL DEFAULT 0"
        )
    if not self._column_exists("memory_entries", "demoted_at"):
        self.conn.execute(
            "ALTER TABLE memory_entries ADD COLUMN demoted_at TEXT"
        )

    # Check if CHECK constraint update is needed
    row = self.conn.execute("SELECT migration_version FROM schema_version").fetchone()
    if row and row[0] >= 2:
        return  # Already migrated

    # Rebuild table with updated CHECK constraint (expensive but correct)
    self.conn.executescript("""
        CREATE TABLE memory_entries_new (
            entry_hash TEXT PRIMARY KEY,
            content_preview TEXT NOT NULL,
            section TEXT NOT NULL,
            source_file TEXT NOT NULL,
            first_seen TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen TEXT NOT NULL DEFAULT (datetime('now')),
            snapshot_count INTEGER NOT NULL DEFAULT 1,
            confidence REAL NOT NULL DEFAULT 0.5,
            confidence_updated_at TEXT,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'stale', 'orphaned', 'demoted')),
            stale_streak INTEGER NOT NULL DEFAULT 0,
            demoted_at TEXT
        );
        INSERT INTO memory_entries_new SELECT *, 0, NULL FROM memory_entries;
        DROP TABLE memory_entries;
        ALTER TABLE memory_entries_new RENAME TO memory_entries;
    """)

    self.conn.execute("UPDATE schema_version SET migration_version = 2")
    self.conn.commit()
```

But this is complex and risky. The simpler fix: document that CHECK constraints are advisory in existing DBs, and rely on application-level validation.

**Severity:** P3 because CHECK constraints are not critical for correctness (the application validates status values), but divergence can cause confusion.

---

## Summary Table

| ID | Severity | Location | Issue | Impact |
|----|----------|----------|-------|--------|
| P0-1 | Critical | Task 2 sweep, Task 3 demotion | Journal/DB divergence on crash between sweep and demote | Entries removed from docs but DB doesn't know → breaks re-promotion |
| P0-2 | Critical | Task 2 _revalidate_citations | Citation.raw_match not in DB, can't reconstruct | Sweep crashes with TypeError on first revalidation |
| P1-1 | High | Task 2 decay formula | Day 28 gets penalty 0.2 instead of 0.1 | Discontinuity in decay curve, premature demotion |
| P1-2 | High | Task 6 re-promotion, normal validation | stale_streak not reset in normal validation path | Inconsistent state (active status, non-zero streak) → premature demotion |
| P2-1 | Moderate | Task 2 sweep accounting | Float equality for decay count | Cosmetic: entries_decayed count may be off by 1-2 |
| P2-2 | Moderate | Task 6 re-promotion | Re-promotion logic is dead code | Logic never triggers, but observable behavior correct |
| P3-1 | Minor | Task 1 migration | CHECK constraint not updated in existing DBs | Divergence between old/new DBs, advisory only |

---

## Recommendations

1. **Fix P0-1 first:** Add journal reconciliation check at sweep start. Change demote journal entries to use terminal status (not "demoted" which gets stuck as incomplete).

2. **Fix P0-2:** Use `raw_match = citation_value` when reconstructing Citation from DB in `_revalidate_citations()`.

3. **Clarify P1-1 with user:** Ask if day 28 should get penalty 0.1 or 0.2. Update formula or PRD accordingly.

4. **Fix P1-2:** Make `update_confidence()` auto-reset stale_streak on stale→active transition.

5. **Fix P2-2:** Either check demoted status before `update_confidence()` runs, or make `update_confidence()` preserve demoted status and add explicit re-promotion call after.

6. **Accept P2-1 and P3-1:** Document as known limitations. P2-1 is cosmetic, P3-1 is advisory only.

---

## Testing Recommendations

For each fix, add tests:

- **P0-1:** `test_sweep_crash_recovery_from_journal` — simulate crash between sweep and demote, verify next sweep reconciles
- **P0-2:** `test_sweep_revalidates_citations_from_db` — entry with DB citations (no content), sweep reconstructs and validates
- **P1-1:** `test_decay_penalty_at_day_28` — explicit test for boundary case
- **P1-2:** `test_stale_to_active_resets_streak` — entry goes stale, citation fixed, verify streak reset
- **P2-2:** `test_demoted_entry_repromotion` — demoted entry reappears with good citations, verify status and streak reset
