# Plan: intermem Phase 2A — Decay + Demotion

**Bead:** iv-rkrm
**Phase:** executing (as of 2026-02-18T21:13:52Z)
**Date:** 2026-02-18 (revised 2026-02-18 after flux-drive review)
**PRD:** `docs/prds/2026-02-18-intermem-phase2-decay-progressive-disclosure.md`
**Working dir:** `plugins/intermem/`
**Reviews:** `docs/research/review-plan-phase2a-synthesis.md`

---

## Review Findings Incorporated

From PRD revision (A1-A3, C1-C3, U1-U3) and plan review (3 agents, 10 deduplicated findings):

**Structural constraints (from PRD):**
- **0 new modules** — extend validator.py, promoter.py, metadata.py, journal.py, __main__.py
- **No sweeper.py** — `sweep_all_entries()` lives in validator.py
- **No archiver.py** — `demote_entries()` lives in promoter.py
- **Decay separate from compute_confidence()** — keep citations.py pure
- **Hysteresis** — `stale_streak` >= 2 before demotion
- **Single transaction** — sweep reads + decays + writes in one SQLite transaction

**Critical fixes from plan review:**
- **Timezone safety** — normalize naive `last_seen` timestamps to UTC-aware before arithmetic (C1)
- **Citation reconstruction** — use `raw_match=citation_value` when rebuilding Citation from DB rows (P0-2)
- **Journal crash recovery** — add reconciliation check at sweep start for incomplete demotions (P0-1)
- **Data access boundary** — add `reactivate_entry()` to metadata.py, no raw SQL in validator.py (A1)
- **Hash-based markers** — embed entry hash in `<!-- intermem:HASH -->` for deterministic demotion (A2)
- **CLI backward compat** — keep all existing args on parent parser, subparsers add only new flags (A4)
- **Decay formula** — use `(days_since - 14) // 14` to avoid off-by-one at day 28 boundary (P1-1)
- **Re-promotion ordering** — check demoted status BEFORE update_confidence() overwrites it (P2-2)
- **Streak reset in update_confidence()** — auto-reset stale_streak on stale→active transition (P1-2)
- **SQL injection** — parameterized LIKE queries in search_entries() (C3)
- **Task 5 collapsed** — wiring merged into Task 2 per architecture review (A3)

---

## Task Breakdown

### Task 1: Schema Migration (`intermem/metadata.py`)

**Goal:** Add `stale_streak` and `demoted_at` columns. Add `demoted` to status CHECK constraint. Add query methods. Add `reactivate_entry()`.

**Implementation:**

1. Add `migrate_to_v2()` method:
   ```python
   def migrate_to_v2(self) -> None:
       """Add Phase 2A columns (idempotent). Requires SQLite 3.37.0+ (Python 3.11+)."""
       if not self._column_exists("memory_entries", "stale_streak"):
           self.conn.execute(
               "ALTER TABLE memory_entries ADD COLUMN stale_streak INTEGER NOT NULL DEFAULT 0"
           )
       if not self._column_exists("memory_entries", "demoted_at"):
           self.conn.execute(
               "ALTER TABLE memory_entries ADD COLUMN demoted_at TEXT"
           )
       # SQLite can't ALTER CHECK constraints. For existing DBs, we accept
       # 'demoted' as a valid status without CHECK enforcement.
       # New DBs will include 'demoted' in the CHECK from the updated _SCHEMA.
       self.conn.commit()
   ```

2. Update `_SCHEMA` — change `CHECK(status IN ('active', 'stale', 'orphaned'))` to include `'demoted'`

3. Call `migrate_to_v2()` at end of `ensure_schema()`

4. Add `increment_stale_streak(entry_hash)` method — `UPDATE memory_entries SET stale_streak = stale_streak + 1 WHERE entry_hash = ?`

5. Add `reset_stale_streak(entry_hash)` method — `UPDATE memory_entries SET stale_streak = 0 WHERE entry_hash = ?`

6. Add `mark_demoted(entry_hash)` method — sets `status = 'demoted'`, `demoted_at = datetime('now')`

7. Add `reactivate_entry(entry_hash)` method (from A1 review):
   ```python
   def reactivate_entry(self, entry_hash: str) -> None:
       """Reset a demoted entry to active status, clearing demotion markers."""
       now = datetime.now(timezone.utc).isoformat()
       self.conn.execute(
           "UPDATE memory_entries SET status = 'active', stale_streak = 0, "
           "demoted_at = NULL, confidence_updated_at = ? WHERE entry_hash = ?",
           (now, entry_hash),
       )
   ```

8. Update `update_confidence()` to auto-reset stale_streak on stale→active transition (from P1-2):
   ```python
   def update_confidence(self, entry_hash: str, confidence: float) -> None:
       old_row = self.get_entry(entry_hash)
       old_status = old_row["status"] if old_row else None
       status = "active" if confidence >= STALE_THRESHOLD else "stale"
       # Preserve 'demoted' status — explicit reactivation only via reactivate_entry()
       if old_row and old_row["status"] == "demoted":
           self.conn.execute(
               "UPDATE memory_entries SET confidence = ?, confidence_updated_at = ? WHERE entry_hash = ?",
               (confidence, datetime.now(timezone.utc).isoformat(), entry_hash),
           )
           return
       now = datetime.now(timezone.utc).isoformat()
       self.conn.execute(
           "UPDATE memory_entries SET confidence = ?, confidence_updated_at = ?, status = ? WHERE entry_hash = ?",
           (confidence, now, status, entry_hash),
       )
       # Reset streak on stale→active transition
       if old_status in ("stale", "orphaned") and status == "active":
           self.reset_stale_streak(entry_hash)
   ```

9. Add query methods for F3:
   - `search_entries(keywords: str) -> list[dict]` — parameterized LIKE query (C3 fix):
     ```python
     def search_entries(self, keywords: str) -> list[dict]:
         if not keywords.strip():
             return []
         tokens = keywords.strip().split()
         conditions = " AND ".join(
             ["(content_preview LIKE ? OR section LIKE ?)" for _ in tokens]
         )
         params: list[str] = []
         for token in tokens:
             pattern = f"%{token}%"
             params.extend([pattern, pattern])
         rows = self.conn.execute(
             f"SELECT * FROM memory_entries WHERE {conditions}", params
         ).fetchall()
         return [dict(row) for row in rows]
     ```
   - `get_topics() -> list[dict]` — GROUP BY section, excludes demoted/orphaned:
     ```python
     def get_topics(self) -> list[dict]:
         rows = self.conn.execute("""
             SELECT section, COUNT(*) as entry_count, AVG(confidence) as avg_confidence
             FROM memory_entries WHERE status IN ('active', 'stale')
             GROUP BY section ORDER BY entry_count DESC
         """).fetchall()
         return [dict(row) for row in rows]
     ```
   - `get_demoted_entries() -> list[dict]` — entries with `status = 'demoted'`

**Tests** (add to `tests/test_metadata.py`):
- `test_migrate_to_v2_adds_columns` — verify stale_streak and demoted_at exist after migration
- `test_migrate_to_v2_idempotent` — run twice, no error
- `test_increment_stale_streak` — starts at 0, increments to 1, 2
- `test_reset_stale_streak` — resets to 0 after increment
- `test_mark_demoted` — sets status and demoted_at
- `test_reactivate_entry` — resets status, stale_streak, demoted_at
- `test_update_confidence_preserves_demoted` — demoted entry stays demoted after update_confidence()
- `test_update_confidence_resets_streak_on_active` — stale→active clears stale_streak
- `test_search_entries_parameterized` — matches content_preview and section
- `test_search_entries_sql_injection` — `'; DROP TABLE` as keywords doesn't crash
- `test_search_entries_empty_keywords` — returns empty list
- `test_get_topics_excludes_demoted` — demoted entries not in counts
- `test_get_demoted_entries` — only returns demoted status

**Acceptance:** All new columns present, migrations idempotent, data access boundary respected, query methods safe.

---

### Task 2: Decay Penalty + Sweep (`intermem/validator.py`)

**Goal:** Add `apply_decay_penalty()`, `sweep_all_entries()`, and demotion candidate collection.

**Implementation:**

1. Add `DEMOTION_STREAK_THRESHOLD = 2` constant

2. Add `apply_decay_penalty()` with timezone safety (C1 fix) and corrected formula (P1-1 fix):
   ```python
   def apply_decay_penalty(confidence: float, last_seen: str, current_time: datetime) -> float:
       """Apply time-based decay to confidence. Separate from compute_confidence (stays pure).

       Grace period: first 14 days, no decay.
       After 14 days: -0.1 per additional 14-day period.
         - Days 15-28: -0.1
         - Days 29-42: -0.2
         - Days 43-56: -0.3
       Clamp to [0.0, 1.0].
       """
       last_seen_dt = datetime.fromisoformat(last_seen)
       # Normalize timezone — metadata.db may have naive timestamps from datetime('now')
       if last_seen_dt.tzinfo is None:
           last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
       if current_time.tzinfo is None:
           current_time = current_time.replace(tzinfo=timezone.utc)

       days_since = (current_time - last_seen_dt).days
       if days_since <= 14:
           return confidence
       # Subtract grace period, then count 14-day penalty periods
       days_beyond_grace = days_since - 14
       periods = (days_beyond_grace + 13) // 14  # ceiling division
       penalty = 0.1 * periods
       return max(0.0, min(1.0, confidence - penalty))
   ```

3. Add `_revalidate_citations()` helper with raw_match fix (P0-2):
   ```python
   def _revalidate_citations(
       entry_hash: str, metadata_store: MetadataStore, project_root: Path
   ) -> list[CheckResult]:
       """Re-validate citations for an entry using DB-stored citation data."""
       rows = metadata_store.conn.execute(
           "SELECT citation_type, citation_value FROM citations WHERE entry_hash = ?",
           (entry_hash,),
       ).fetchall()
       checks: list[CheckResult] = []
       for row in rows:
           citation = Citation(
               type=row["citation_type"],
               value=row["citation_value"],
               raw_match=row["citation_value"],  # Approximation; raw_match not in DB
           )
           result = validate_citation(citation, project_root)
           checks.append(result)
       return checks
   ```

4. Add `sweep_all_entries()` with journal recovery (P0-1 fix), orphan skipping (M3), NULL safety (C4), and demotion candidates (A3 collapse):
   ```python
   @dataclass
   class SweepResult:
       entries_swept: int
       entries_decayed: int
       entries_marked_for_demotion: int
       demotion_candidates: list[str]  # entry_hashes with stale_streak >= threshold

   def sweep_all_entries(
       metadata_store: MetadataStore,
       project_root: Path,
       journal: PromotionJournal | None = None,
   ) -> SweepResult:
       """Re-validate all entries: recheck citations, apply decay, update stale_streak.

       Includes journal crash recovery and demotion candidate collection.
       """
       # Crash recovery: reconcile journal with DB (P0-1 fix)
       if journal is not None:
           for jentry in journal.get_unresolved_demotions():
               row = metadata_store.get_entry(jentry.entry_hash)
               if row and row["status"] != "demoted":
                   metadata_store.mark_demoted(jentry.entry_hash)

       metadata_store.begin_transaction()
       try:
           # Only sweep active and stale entries (skip demoted, orphaned)
           entries = metadata_store.conn.execute(
               "SELECT * FROM memory_entries WHERE status IN ('active', 'stale')"
           ).fetchall()

           current_time = datetime.now(timezone.utc)
           entries_decayed = 0
           entries_marked = 0

           for row in entries:
               entry_hash = row["entry_hash"]
               checks = _revalidate_citations(entry_hash, metadata_store, project_root)
               snapshot_count = row["snapshot_count"]
               base_confidence = compute_confidence(0.5, checks, snapshot_count)

               # NULL last_seen safety (C4)
               last_seen = row["last_seen"]
               if last_seen is None:
                   last_seen = current_time.isoformat()

               decayed_confidence = apply_decay_penalty(
                   base_confidence, last_seen, current_time
               )
               metadata_store.update_confidence(entry_hash, decayed_confidence)

               if abs(decayed_confidence - base_confidence) > 1e-9:
                   entries_decayed += 1

               # Hysteresis: track stale streak
               if decayed_confidence < STALE_THRESHOLD:
                   metadata_store.increment_stale_streak(entry_hash)
                   row_updated = metadata_store.get_entry(entry_hash)
                   if row_updated and row_updated["stale_streak"] >= DEMOTION_STREAK_THRESHOLD:
                       entries_marked += 1
               else:
                   metadata_store.reset_stale_streak(entry_hash)

           metadata_store.commit_transaction()
       except Exception:
           metadata_store.rollback_transaction()
           raise

       # Collect demotion candidates (post-transaction, from committed state)
       demotion_rows = metadata_store.conn.execute(
           "SELECT entry_hash FROM memory_entries WHERE stale_streak >= ? AND status != 'demoted'",
           (DEMOTION_STREAK_THRESHOLD,),
       ).fetchall()
       demotion_candidates = [r["entry_hash"] for r in demotion_rows]

       return SweepResult(
           entries_swept=len(entries),
           entries_decayed=entries_decayed,
           entries_marked_for_demotion=entries_marked,
           demotion_candidates=demotion_candidates,
       )
   ```

**Import:** `from intermem.citations import compute_confidence, validate_citation, CheckResult, Citation`
**Import:** `from intermem.metadata import STALE_THRESHOLD`
**Import:** `from datetime import datetime, timezone`

**Tests** (add to `tests/test_validator.py`):
- `test_apply_decay_penalty_within_14_days` — no penalty
- `test_apply_decay_penalty_at_15_days` — -0.1 penalty
- `test_apply_decay_penalty_at_28_days` — -0.1 penalty (off-by-one fix verified)
- `test_apply_decay_penalty_at_29_days` — -0.2 penalty
- `test_apply_decay_penalty_at_42_days` — -0.3 penalty
- `test_apply_decay_penalty_clamps_to_zero` — very old entry doesn't go negative
- `test_apply_decay_naive_timestamp` — naive last_seen handled without TypeError
- `test_apply_decay_aware_timestamp` — UTC-aware last_seen works
- `test_sweep_all_entries_no_decay` — fresh entries unchanged
- `test_sweep_all_entries_with_decay` — old entries get penalized
- `test_sweep_stale_streak_increment` — streak goes up when stale
- `test_sweep_stale_streak_reset` — streak resets when healthy
- `test_sweep_single_transaction` — verify atomicity (mock crash mid-sweep)
- `test_sweep_skips_orphaned_entries` — orphaned entries not processed
- `test_sweep_null_last_seen` — entry with NULL last_seen doesn't crash
- `test_sweep_returns_demotion_candidates` — entries with streak >= 2 listed
- `test_sweep_crash_recovery_from_journal` — incomplete demotion in journal reconciled

**Acceptance:** Decay formula correct, timezone-safe, sweep runs in single transaction, stale_streak tracks correctly, demotion candidates collected.

---

### Task 3: Demotion (`intermem/promoter.py` + `intermem/journal.py`)

**Goal:** Remove stale entries from target docs using hash-based markers. Journal-first for crash safety.

**Implementation (journal.py):**

1. Add `record_demoted()` method to `PromotionJournal`:
   ```python
   def record_demoted(self, entry_hash: str, target_file: str, target_section: str, content: str) -> None:
       """Record that an entry has been demoted (removed from target doc)."""
       self._append(JournalEntry(
           entry_hash=entry_hash,
           target_file=target_file,
           target_section=target_section,
           content=content,
           status="demoted",
           timestamp=datetime.now(timezone.utc).isoformat(),
       ))
   ```

2. Add `get_unresolved_demotions()` method — returns journal entries with status "demoted" that don't have a corresponding "demoted-committed" entry. Used by sweep crash recovery.

3. Add `mark_demotion_committed(entry_hash)` — appends a journal entry with status "demoted-committed" (terminal state, so "demoted" entries don't stay incomplete forever).

**Implementation (promoter.py):**

1. **Change MARKER format** (A2 fix) — embed entry hash for deterministic matching:
   ```python
   MARKER_PREFIX = "<!-- intermem"
   MARKER_SUFFIX = " -->"

   def make_marker(entry_hash: str | None = None) -> str:
       if entry_hash:
           return f"<!-- intermem:{entry_hash[:8]} -->"
       return "<!-- intermem -->"

   # Regex matches both old (<!-- intermem -->) and new (<!-- intermem:HASH -->)
   _INTERMEM_MARKER_RE = re.compile(r"<!--\s*intermem(?::([a-f0-9]+))?\s*-->")
   ```

2. Update `promote_entries()` to use hash-based markers:
   ```python
   insert_lines = [
       f"{entry.content} {make_marker(hash_entry(entry))}"
       for entry in section_entries
   ]
   ```

3. Add `demote_entries()` function with journal-first pattern:
   ```python
   def demote_entries(
       entry_hashes: list[str],
       metadata_store: MetadataStore,
       target_docs: list[Path],
       journal: PromotionJournal,
   ) -> DemotionResult:
       """Remove stale entries from target docs by hash-based marker matching.

       Order: journal.record_demoted → remove from file → metadata.mark_demoted → journal.mark_committed
       Crash recovery: sweep checks for recorded-but-uncommitted demotions.
       """
       demoted_count = 0
       files_modified: list[str] = []

       for doc in target_docs:
           if not doc.exists():
               continue
           text = doc.read_text(encoding="utf-8")
           lines = text.splitlines(keepends=True)
           new_lines: list[str] = []
           removed_in_doc = False

           for line in lines:
               match = _INTERMEM_MARKER_RE.search(line)
               if match:
                   marker_hash = match.group(1)  # None for old-style markers
                   if marker_hash and marker_hash in [h[:8] for h in entry_hashes]:
                       # Found a hash match — record journal FIRST, then remove
                       full_hash = next(h for h in entry_hashes if h[:8] == marker_hash)
                       content = _INTERMEM_MARKER_RE.sub("", line).strip()
                       journal.record_demoted(full_hash, str(doc), "", content)
                       metadata_store.mark_demoted(full_hash)
                       journal.mark_demotion_committed(full_hash)
                       demoted_count += 1
                       removed_in_doc = True
                       continue  # Skip this line (remove from doc)
               new_lines.append(line)

           if removed_in_doc:
               doc.write_text("".join(new_lines), encoding="utf-8")
               files_modified.append(str(doc))

       return DemotionResult(demoted_count=demoted_count, files_modified=files_modified)
   ```

4. Add `DemotionResult` dataclass: `demoted_count: int, files_modified: list[str]`

5. Update `_extract_promoted_entries()` in validator.py to also handle hash-based markers (backward compat — both old and new markers detected).

**Tests** (add to `tests/test_promoter.py`):
- `test_promote_uses_hash_marker` — new promotions use `<!-- intermem:HASH -->`
- `test_demote_removes_line_by_hash` — hash-matched line removed, others preserved
- `test_demote_updates_metadata` — status becomes 'demoted'
- `test_demote_records_journal` — journal has 'demoted' then 'demoted-committed' entries
- `test_demote_crash_recovery` — partial demotion (no committed) detected by sweep
- `test_demote_old_style_marker_skipped` — old `<!-- intermem -->` markers not accidentally demoted
- `test_demote_entry_not_in_any_doc` — entry hash in DB but not in docs, graceful no-op

**Tests** (add to `tests/test_journal.py`):
- `test_record_demoted` — new status value accepted and persisted
- `test_get_unresolved_demotions` — returns demoted without committed
- `test_mark_demotion_committed` — committed entry paired with demoted

**Acceptance:** Hash-based markers for deterministic demotion, journal-first for crash safety, backward compat with old markers.

---

### Task 4: CLI — sweep and query (`intermem/__main__.py`)

**Goal:** Add `intermem sweep` and `intermem query` subcommands with full backward compatibility.

**Implementation:**

1. Restructure `main()` — keep ALL existing args on parent parser (A4 fix):
   ```python
   parser = argparse.ArgumentParser(description="Intermem memory synthesis")
   # ALL existing args stay on parent parser for backward compat
   parser.add_argument("--project-dir", type=Path, default=Path.cwd())
   parser.add_argument("--project-root", type=Path, default=None)
   parser.add_argument("--dry-run", action="store_true")
   parser.add_argument("--auto-approve", action="store_true")
   parser.add_argument("--validate", action="store_true")
   parser.add_argument("--no-validate", action="store_true")
   parser.add_argument("--validate-only", action="store_true")
   parser.add_argument("--json", action="store_true")

   subparsers = parser.add_subparsers(dest="command", required=False)

   sweep_parser = subparsers.add_parser("sweep", help="Re-validate + decay pass")
   # No sweep-specific args — uses parent parser's --project-dir, --project-root, --json

   query_parser = subparsers.add_parser("query", help="Query metadata database")
   query_parser.add_argument("--search", type=str, help="Search entries by keyword")
   query_parser.add_argument("--topics", action="store_true", help="List topics with counts")
   query_parser.add_argument("--demoted", action="store_true", help="Show demoted entries")
   ```

2. **Backward compatibility:** When `args.command is None`, fall through to existing synthesis behavior. All existing flag combinations work without subcommand.

3. `sweep` handler:
   ```python
   elif args.command == "sweep":
       metadata_store = MetadataStore(intermem_dir / "metadata.db")
       journal = PromotionJournal(intermem_dir / "promotion-journal.jsonl")
       sweep_result = sweep_all_entries(metadata_store, project_root, journal)

       if sweep_result.entries_swept == 0:
           print("No entries to sweep.")
           sys.exit(0)

       if sweep_result.demotion_candidates:
           target_docs = [project_root / "AGENTS.md", project_root / "CLAUDE.md"]
           demote_result = demote_entries(
               sweep_result.demotion_candidates, metadata_store, target_docs, journal
           )
           # print results...

       sys.exit(0)
   ```

4. `query` handler:
   ```python
   elif args.command == "query":
       metadata_store = MetadataStore(intermem_dir / "metadata.db")
       try:
           if args.search:
               results = metadata_store.search_entries(args.search)
           elif args.topics:
               results = metadata_store.get_topics()
           elif args.demoted:
               results = metadata_store.get_demoted_entries()
           else:
               print("Specify --search, --topics, or --demoted", file=sys.stderr)
               sys.exit(1)
           # Format and print...
           sys.exit(0)
       except FileNotFoundError:
           print(f"Error: metadata.db not found", file=sys.stderr)
           sys.exit(2)
       except sqlite3.DatabaseError as e:
           print(f"Error: Database error: {e}", file=sys.stderr)
           sys.exit(2)
   ```

**Tests** (new file `tests/test_cli.py`):
- `test_sweep_command` — runs sweep via subprocess, exits 0
- `test_sweep_empty_db` — no entries, prints "No entries to sweep"
- `test_query_search` — finds matching entries
- `test_query_topics` — returns topic list
- `test_query_demoted` — returns demoted entries
- `test_query_missing_db` — exits 2 with error message
- `test_no_subcommand_backward_compat` — `--project-dir . --validate` works without subcommand
- `test_all_existing_flags_without_subcommand` — `--dry-run`, `--auto-approve`, `--validate-only` all work

**Acceptance:** Both subcommands work, backward compatibility verified for all existing flag combinations, error handling with proper exit codes.

---

### Task 5: Re-promotion of Demoted Entries

**Goal:** Demoted entries re-entering auto-memory go through normal pipeline with explicit re-promotion.

**Implementation:**

1. In `validate_and_filter_entries()`, check demoted status BEFORE calling `update_confidence()` (P2-2 fix):
   ```python
   # After computing confidence, before update_confidence:
   row = metadata_store.get_entry(entry_hash)
   was_demoted = row and row["status"] == "demoted"

   confidence = compute_confidence(0.5, checks, snapshot_count)

   if was_demoted and confidence >= STALE_THRESHOLD:
       # Re-promote: explicit reactivation clears demotion state
       metadata_store.reactivate_entry(entry_hash)
       metadata_store.update_confidence(entry_hash, confidence)
   else:
       metadata_store.update_confidence(entry_hash, confidence)
   ```

2. The dedup check in the normal pipeline sees the entry as novel (removed from target doc during demotion), so it'll be promoted again normally.

3. **Note:** `update_confidence()` preserves 'demoted' status (from Task 1 update), so demoted entries with low confidence stay demoted — only entries that both reappear in auto-memory AND have good confidence get reactivated.

**Tests** (add to `tests/test_validator.py`):
- `test_demoted_entry_repromotion` — demoted entry reappears with good citations → status reset to active
- `test_demoted_entry_stays_demoted_if_stale` — demoted entry reappears but still stale → stays demoted
- `test_reactivation_while_still_stale` — entry reappears with confidence < 0.3, stays demoted
- `test_full_lifecycle_decay_to_demotion` — entry ages through sweeps, gets demoted, reappears, re-promoted

**Acceptance:** Full round-trip: promote → decay → demote → reappear → re-promote works.

---

### Task 6: Documentation + Cleanup

**Goal:** Update CLAUDE.md, AGENTS.md references, skill docs.

**Implementation:**

1. Update `plugins/intermem/CLAUDE.md`:
   - Add sweep subcommand to quick reference
   - Add query subcommand to quick reference
   - Document `stale_streak` hysteresis behavior
   - Document decay formula with day-boundary table
   - Add Phase 2A to architecture section
   - Document hash-based marker format
   - Note CHECK constraint split-brain for existing DBs

2. Update skill YAML if needed for new CLI capabilities

3. Verify all 119 existing tests + new tests pass

**Acceptance:** Documentation reflects Phase 2A capabilities. All tests green.

---

## Execution Order

Task 5 (formerly Task 6) collapsed into proper dependency chain. Former Task 5 (wire pipeline) merged into Task 2.

```
[Task 1: metadata.py] ──────┐
                              ├──→ [Task 3: promoter.py + journal.py]
[Task 2: validator.py] ──────┘          │
                                         ├──→ [Task 4: CLI]
                                         │
                                         └──→ [Task 5: Re-promotion]
                                                        │
                                                  [Task 6: Docs]
```

**Parallelism:** Tasks 1 and 2 can be implemented simultaneously. Tasks 4 and 5 can overlap after Task 3.

---

## Test Strategy

- All tests use `tmp_path` fixture — no filesystem side effects
- Existing 119 tests must pass unchanged after every task
- New test count estimate: ~35 tests across metadata, validator, promoter, journal, CLI
- Run full suite after each task: `uv run pytest tests/ -v`
- Sweep transaction tests: verify rollback on simulated error
- Timezone tests: both naive and aware timestamps
- SQL injection tests: parameterized queries verified
- Backward compat tests: all existing CLI flag combinations

---

## File Impact Summary

| File | Changes | Est. Lines |
|---|---|---|
| `intermem/metadata.py` | migrate_to_v2, stale_streak methods, reactivate_entry, updated update_confidence, query methods, updated schema | ~80 |
| `intermem/validator.py` | apply_decay_penalty, sweep_all_entries, _revalidate_citations, re-promotion logic, DEMOTION_STREAK_THRESHOLD | ~100 |
| `intermem/promoter.py` | hash-based markers, demote_entries, DemotionResult, make_marker | ~70 |
| `intermem/journal.py` | record_demoted, get_unresolved_demotions, mark_demotion_committed | ~25 |
| `intermem/__main__.py` | parent-parser backward compat, sweep handler, query handler | ~80 |
| `tests/test_metadata.py` | 13 new tests | ~100 |
| `tests/test_validator.py` | 17 new tests | ~150 |
| `tests/test_promoter.py` | 7 new tests | ~60 |
| `tests/test_journal.py` | 3 new tests | ~25 |
| `tests/test_cli.py` | 8 new tests | ~70 |
| `CLAUDE.md` | Updated docs | ~20 |

**Total:** ~780 lines across 11 files, ~48 new tests.

---

## Rollback

- Delete `stale_streak` and `demoted_at` columns: not needed — SQLite ignores unknown columns in existing queries
- Skip `apply_decay_penalty()` call: restores Phase 1 behavior
- Hash-based markers: backward compat regex matches both old and new styles
- Subcommands: no subcommand → falls through to existing synthesis
- Demotion: if disabled, entries just stay with low confidence but remain in target docs
