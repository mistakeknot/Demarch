# Architecture Review: intermem Phase 2A Plan (Decay + Demotion)

**Document:** `docs/plans/2026-02-18-intermem-phase2a-decay-demotion.md`
**Reviewer:** Architecture & Design Reviewer
**Date:** 2026-02-18

---

## Summary

The plan proposes 7 tasks to add decay, demotion, and CLI queries to intermem. Overall structure is sound, but there are **4 must-fix issues** (boundary violations, data access pattern breaks) and **2 high-priority simplifications** before implementation.

---

## Findings

### A1: Data Access Boundary Violation — Raw SQL in validator.py (Task 6)

**Severity:** CRITICAL (must-fix before implementation)

**Location:** Task 6, lines 352-356 of plan

**Issue:**
Task 6 adds raw SQL directly in `validator.py`:

```python
metadata_store.conn.execute(
    "UPDATE memory_entries SET status = 'active', stale_streak = 0, demoted_at = NULL WHERE entry_hash = ?",
    (entry_hash,)
)
```

This bypasses the data access layer and violates the established pattern where all SQL lives in `metadata.py`. All existing code in `validator.py` calls methods like `metadata_store.upsert_entry()`, `metadata_store.record_citation()`, `metadata_store.update_confidence()` — never direct `conn.execute()`.

**Impact:**
- Breaks boundary integrity between validation logic (validator.py) and data access (metadata.py)
- Creates hidden maintenance burden — future schema changes to these columns would require hunting through validator.py for raw SQL
- Sets precedent for other raw SQL to creep into validator.py

**Fix:**
Add method to `metadata.py` (Task 1):

```python
def reactivate_entry(self, entry_hash: str) -> None:
    """Reset a demoted entry to active status, clearing demotion markers."""
    self.conn.execute(
        "UPDATE memory_entries SET status = 'active', stale_streak = 0, demoted_at = NULL WHERE entry_hash = ?",
        (entry_hash,)
    )
```

Then in Task 6, validator.py calls:

```python
metadata_store.reactivate_entry(entry_hash)
```

**Test impact:** Add `test_reactivate_entry()` to `tests/test_metadata.py`.

---

### A2: Demotion Matching Logic Incomplete (Task 3)

**Severity:** HIGH (critical path issue, may not work as designed)

**Location:** Task 3, lines 226-232 of plan

**Issue:**
Task 3 says:

> a. Look up entry in metadata_store to get content_preview
> b. Scan each target doc for lines matching the content + `<!-- intermem -->` marker

But `content_preview` is truncated to 80 chars (see `validator.py:69`, `metadata.py` line 84 `content[:80]`). The actual promoted line in the target doc could be longer. Matching by truncated content will fail for entries >80 chars, or worse, match the wrong line if two entries share the same 80-char prefix.

The existing `_extract_promoted_entries()` in `validator.py` (lines 127-154) scans for `<!-- intermem -->` markers and reconstructs entries, but it doesn't preserve the entry hash. The `promoter.py` also doesn't embed the entry hash in the marker.

**Current state of promoted lines (from promoter.py:12, 61):**
```python
MARKER = "<!-- intermem -->"
insert_lines = [f"{entry.content} {MARKER}" for entry in section_entries]
```

No hash, no unique identifier.

**Impact:**
- Demotion will fail silently for entries longer than 80 chars
- Risk of removing wrong line if multiple entries have similar prefixes
- Crash recovery for demotion (Task 3, line 236) cannot work reliably without a unique identifier

**Fix options:**

**Option A (minimal, preserves existing marker format):**
Store full content in metadata.db, not just `content_preview`:

1. Add `content_full TEXT` column in Task 1 migration
2. Update `upsert_entry()` to take `content_full` and populate it
3. Demotion matches on `content_full + MARKER` instead of `content_preview`

**Option B (robust, future-proof):**
Embed entry hash in the marker:

1. Change `MARKER` to `f"<!-- intermem:{entry_hash[:8]} -->"`
2. Demotion scans for `<!-- intermem:<hash_prefix> -->` and removes that line
3. Re-promotion detects existing marker with same hash

**Recommendation:** Option B. The hash makes demotion deterministic and enables future features like tracking individual entry lifecycle. The 8-char hash prefix is collision-safe for <1000 entries per project (already documented as acceptable in CLAUDE.md).

**Implementation impact:**
- Task 3: Update `promoter.py` to embed hash in marker
- Task 3: Demotion uses regex `<!-- intermem:([a-f0-9]{8}) -->` to extract hash
- Task 6: Re-promotion checks if existing marker has same hash before re-adding
- All 119 existing tests pass (marker change is backward-compatible — old markers still detected via `_INTERMEM_MARKER_RE`)

**Test impact:** Add tests for long entries (>80 chars), duplicate prefixes, hash-based matching.

---

### A3: Task 5 Redundant — Collapse into Task 2 or Task 3

**Severity:** MEDIUM (unnecessary task boundary, no technical blocker)

**Location:** Task 5 (lines 305-335 of plan), execution order diagram (lines 394-403)

**Issue:**
Task 5 is titled "Wire Sweep into Demotion Pipeline" but its only work is:

1. Query for `stale_streak >= 2` entries (3 lines of SQL)
2. Add `demotion_candidates` field to `SweepResult` dataclass
3. Update CLI handler to call `demote_entries()` with those candidates

This is just wiring code. The real implementation work happens in Task 2 (`sweep_all_entries()`) and Task 3 (`demote_entries()`). Task 5 doesn't add any new logic — it just connects what was already built.

**Why this task exists:**
The plan treats "demotion detection" (Task 2) and "CLI integration" (Task 4) as independent of "wiring them together" (Task 5). This is artificial separation — the wiring is trivial and belongs with either the sweep implementation (Task 2) or the CLI handler (Task 4).

**Impact:**
- Extra merge step increases chance of rebase conflicts
- Cognitive overhead: "Wait, Task 2 built the sweep, but it doesn't return demotion candidates?"
- Misleading execution order diagram suggests Tasks 4 and 6 can't start until Task 5 completes, but Task 6 has no dependency on Task 5

**Fix:**
Collapse Task 5 into Task 2:

**Task 2 (revised):**
1. Add `apply_decay_penalty()` (as written)
2. Add `sweep_all_entries()` (as written)
3. Add `demotion_candidates` field to `SweepResult` and populate it:
   ```python
   demotion_candidates = [
       row["entry_hash"] for row in entries
       if metadata_store.get_entry(row["entry_hash"])["stale_streak"] >= 2
   ]
   return SweepResult(..., demotion_candidates=demotion_candidates)
   ```
4. Test: `test_sweep_returns_demotion_candidates`
5. Test: `test_full_lifecycle_decay_to_demotion` (move from Task 5)

**Task 4 (CLI, no change except depends on Task 2's new field):**
CLI handler uses `sweep_result.demotion_candidates` immediately.

**Task 6 becomes Task 5** (re-number).

**Revised execution order:**
```
[Task 1: metadata.py] ──────┐
                              ├──→ [Task 3: promoter.py + journal.py]
[Task 2: validator.py] ──────┘          │
   (now includes wiring)                 ├──→ [Task 4: CLI]
                                         │         │
                                         └──→ [Task 5: Re-promotion] ──┘
                                                    │
                                              [Task 6: Docs]
```

**Parallelism:** Tasks 4 and 5 can overlap after Task 3, as claimed in the plan, but now it's actually true (previously Task 5 was falsely shown as parallel to Task 6).

---

### A4: CLI Backward Compatibility Risk — Subparser Restructuring (Task 4)

**Severity:** HIGH (user-facing breakage if implemented as written)

**Location:** Task 4, lines 258-279 of plan

**Issue:**
The plan says:

> 2. **Backward compatibility:** When no subcommand is given (`args.command is None`), fall through to existing synthesis behavior. This preserves `/intermem:synthesize` and existing CLI usage.

But the proposed implementation moves existing args to a `synthesize` subparser:

```python
synth_parser = subparsers.add_parser("synthesize", help="Run synthesis pipeline")
# ... existing args ...
```

This breaks `python -m intermem --project-dir . --validate` (no subcommand). argparse will reject `--project-dir` because it's not on the parent parser.

**Current CLI usage (from `__main__.py`):**
```bash
python -m intermem --project-dir . --dry-run --validate
```

**After proposed change:**
```bash
python -m intermem synthesize --project-dir . --dry-run --validate  # new
python -m intermem --project-dir . --dry-run --validate              # BREAKS
```

**Impact:**
- Existing `/intermem:synthesize` skill calls break (they don't pass `synthesize` subcommand)
- User scripts break
- Documentation everywhere becomes stale

**Fix:**
Keep common args on the parent parser:

```python
parser = argparse.ArgumentParser(description="Intermem memory synthesis")
parser.add_argument("--project-dir", type=Path, default=Path.cwd())
parser.add_argument("--project-root", type=Path, default=None)
parser.add_argument("--json", action="store_true")

subparsers = parser.add_subparsers(dest="command")

synth_parser = subparsers.add_parser("synthesize", help="Run synthesis pipeline")
synth_parser.add_argument("--dry-run", action="store_true")
synth_parser.add_argument("--auto-approve", action="store_true")
synth_parser.add_argument("--validate", action="store_true")
synth_parser.add_argument("--no-validate", action="store_true")
synth_parser.add_argument("--validate-only", action="store_true")

sweep_parser = subparsers.add_parser("sweep", help="Re-validate + decay pass")
# no sweep-specific args beyond the parent parser

query_parser = subparsers.add_parser("query", help="Query metadata database")
query_parser.add_argument("--search", type=str)
query_parser.add_argument("--topics", action="store_true")
query_parser.add_argument("--demoted", action="store_true")

args = parser.parse_args()

if args.command is None:
    # Fall through to existing synthesis behavior
    # Synth-specific args need defaults when running without subcommand:
    args.dry_run = getattr(args, "dry_run", False)
    args.auto_approve = getattr(args, "auto_approve", False)
    args.validate = getattr(args, "validate", False)
    args.no_validate = getattr(args, "no_validate", False)
    args.validate_only = getattr(args, "validate_only", False)
    # ... existing synthesis handler
```

**Alternative (cleaner):**
Put synthesis args on parent parser, make subparsers fully optional:

```python
parser = argparse.ArgumentParser(description="Intermem memory synthesis")
# ALL existing args here (project-dir, dry-run, auto-approve, validate, etc.)
parser.add_argument(...)  # all current flags

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

This keeps all existing flag combinations working without subcommands.

**Test impact:** Add `test_no_subcommand_backward_compat` as planned, but also test all existing flag combinations without subcommands.

---

### A5: validator.py Responsibility Sprawl (Observation, Not a Blocker)

**Severity:** LOW (worth noting for Phase 2B refactor)

**Location:** Task 2 (lines 82-180 of plan)

**Issue:**
After this plan, `validator.py` will have:

**Current (Phase 1):**
- `validate_and_filter_entries()` — validate citations during synthesis pipeline
- `validate_promoted()` — validate already-promoted entries in target docs
- `_extract_promoted_entries()` — scan target docs for `<!-- intermem -->` markers

**Added in Phase 2A (this plan):**
- `apply_decay_penalty()` — time-based confidence decay
- `sweep_all_entries()` — re-validate all entries in metadata.db
- `_revalidate_citations()` — helper for sweep
- Re-promotion logic in `validate_and_filter_entries()`

That's two distinct responsibilities:

1. **Entry validation during synthesis pipeline** (validate_and_filter_entries, validate_promoted)
2. **Full-DB sweep with decay** (sweep_all_entries, apply_decay_penalty)

The plan justifies this:

> - **No sweeper.py** — `sweep_all_entries()` lives in validator.py
> - **Decay separate from compute_confidence()** — keep citations.py pure

This is a deliberate choice per PRD review findings (C1, C3). The rationale: validator.py already imports `compute_confidence` and calls `metadata_store`, so adding sweep logic there avoids a new module.

**Analysis:**
This is acceptable for Phase 2A, but the module is growing in two directions:

- **Inbound validation** (pipeline: entries → validation → metadata)
- **Outbound maintenance** (sweep: metadata → revalidation → decay)

If Phase 2B adds more sweep-related features (e.g., proactive re-validation schedules, decay curve adjustments), consider extracting a `maintenance.py` module with:

- `sweep_all_entries()`
- `apply_decay_penalty()`
- Future: `schedule_revalidation()`, `adjust_decay_curve()`

validator.py would keep just the inbound validation logic.

**Recommendation:** Accept this for Phase 2A. Add a TODO comment in validator.py:

```python
# TODO Phase 2B: If sweep logic grows further, extract to maintenance.py
def sweep_all_entries(metadata_store: MetadataStore, project_root: Path) -> SweepResult:
```

**No action required now.**

---

### A6: Task Execution Order — Tasks 4 and 6 Not Actually Independent

**Severity:** LOW (plan documentation issue, not code issue)

**Location:** Execution order diagram (lines 392-403 of plan)

**Issue:**
The plan claims:

> **Parallelism:** Tasks 1 and 2 can be implemented simultaneously. Tasks 4 and 6 can overlap after Task 3.

But Task 6 modifies `validate_and_filter_entries()`, which is called during normal synthesis (not just sweep). Task 4 adds the CLI handlers for sweep, which don't depend on Task 6's re-promotion logic.

However, the full lifecycle test in Task 5 (`test_full_lifecycle_decay_to_demotion`) might **logically** want re-promotion to be testable, but the plan says Task 5 only tests "entry ages → confidence drops → stale_streak reaches 2 → demotion triggered." Re-promotion is a separate round-trip, tested in Task 6.

**Correct dependency:**
- Task 4 (CLI) depends on Tasks 1, 2, 3 (schema, sweep, demote)
- Task 6 (re-promotion) depends on Task 2 (validator.py changes) but **not** on Task 4 or Task 5

So Tasks 4 and 6 are truly independent. The plan's diagram is correct.

**Clarification:**
The plan should note that `test_full_lifecycle_decay_to_demotion` in Task 5 does **not** test re-promotion. Re-promotion is tested in Task 6's `test_demoted_entry_repromotion`. This keeps the tests aligned with the task boundaries.

**No fix needed.** Document this in the plan revision if Task 5 is collapsed per A3.

---

### A7: Missing Method in metadata.py — `get_promoted_entries()` (Task 1)

**Severity:** LOW (unused method, plan bloat)

**Location:** Task 1, lines 61-62 of plan

**Issue:**
Task 1 adds:

> 7. Add `get_promoted_entries()` method — returns entries with `status = 'active'` and `confidence_updated_at IS NOT NULL` (entries that have been through validation)

This method is never called anywhere in Tasks 2-7. The sweep logic in Task 2 uses:

```python
entries = metadata_store.conn.execute(
    "SELECT * FROM memory_entries WHERE status != 'demoted'"
).fetchall()
```

Not `get_promoted_entries()`.

**Why it exists:**
Likely anticipatory — "we might need this later for querying promoted entries." But intermem follows YAGNI (per PRD review finding U1: "Challenge every abstraction").

**Impact:**
Adds unused code and tests, increasing maintenance surface for no current benefit.

**Fix:**
Remove `get_promoted_entries()` from Task 1. If it's needed later, add it in the task that needs it.

**Alternatively:**
If the intent was to use it in the CLI query handler (Task 4), the plan should say so explicitly. But the plan's CLI query methods are `search_entries()`, `get_topics()`, `get_demoted_entries()` — no "show promoted" query.

**Recommendation:** Delete this method from the plan. Add it back if a concrete use case appears in Phase 2B.

---

### A8: Schema Migration Risk — `demoted` Status in CHECK Constraint

**Severity:** LOW (plan acknowledges this, but solution is incomplete)

**Location:** Task 1, lines 26-48 of plan

**Issue:**
Task 1 says:

> SQLite can't ALTER CHECK constraints. Recreate isn't needed —
> the CHECK was in CREATE TABLE IF NOT EXISTS, which only runs on first creation.
> For existing DBs, we accept 'demoted' as a valid status without CHECK enforcement.
> New DBs will include 'demoted' in the CHECK from the updated _SCHEMA.

This is a split-brain state: old DBs have no CHECK enforcement for `'demoted'`, new DBs do. If someone manually sets `status = 'invalid_value'` on an old DB, SQLite won't reject it. On a new DB, it will.

**Impact:**
Low, because all status updates go through `metadata_store.mark_demoted()` and `metadata_store.update_confidence()`, which set valid values. But if someone manually edits `metadata.db` (debugging, forensics), behavior differs between old and new DBs.

**Better solution:**
Document the split-brain state clearly:

```python
def migrate_to_v2(self) -> None:
    """Add Phase 2A columns (idempotent).

    Note: The CHECK constraint on status is only enforced for new DBs
    (those created after Phase 2A). Existing DBs accept 'demoted' status
    but don't have CHECK enforcement. This is acceptable because all
    status updates go through MetadataStore methods, not raw SQL.
    """
    if not self._column_exists("memory_entries", "stale_streak"):
        self.conn.execute(
            "ALTER TABLE memory_entries ADD COLUMN stale_streak INTEGER NOT NULL DEFAULT 0"
        )
    if not self._column_exists("memory_entries", "demoted_at"):
        self.conn.execute(
            "ALTER TABLE memory_entries ADD COLUMN demoted_at TEXT"
        )
    self.conn.commit()
```

**Recommendation:**
Accept the split-brain state (it's documented in the plan). Add documentation to CLAUDE.md: "If `stale_streak` exists, schema supports 'demoted' status." No code change needed.

---

## Must-Fix Before Implementation

1. **A1 (CRITICAL):** Add `metadata_store.reactivate_entry()` method, remove raw SQL from validator.py (Task 6)
2. **A2 (HIGH):** Fix demotion matching logic — embed entry hash in marker or store full content (Task 3)
3. **A4 (HIGH):** Fix CLI backward compatibility — keep common args on parent parser (Task 4)

---

## Recommended Simplifications

4. **A3 (MEDIUM):** Collapse Task 5 into Task 2 — eliminates artificial task boundary
5. **A7 (LOW):** Remove unused `get_promoted_entries()` method from Task 1

---

## Observations for Future Phases

6. **A5 (LOW):** validator.py growing in two directions — consider `maintenance.py` in Phase 2B
7. **A6 (LOW):** Plan correctly notes Tasks 4 and 6 are independent — no fix needed
8. **A8 (LOW):** Schema CHECK constraint split-brain is acceptable, document in migration notes

---

## Architectural Strengths

The plan gets several things right:

1. **No new modules:** Extends existing files per PRD constraints (C1, C3). This is correct for the current scope.
2. **Single transaction for sweep:** Task 2's sweep runs in one transaction (lines 115-153). This is mandatory for consistency.
3. **Hysteresis via stale_streak:** Avoids flapping (lines 19, 142-148). Good design.
4. **Journal integration:** Task 3 correctly adds `record_demoted()` to journal.py, maintaining WAL pattern.
5. **Crash recovery awareness:** Task 3 mentions crash recovery (line 236), though A2 shows the implementation needs the hash-based marker to be reliable.
6. **Test coverage:** ~29 new tests across 5 test files. Comprehensive.

---

## Coupling & Dependency Analysis

### Inbound dependencies (what each task needs):
- Task 1: None (schema migration is foundational)
- Task 2: Task 1 (needs `stale_streak` columns, `increment_stale_streak()`, `reset_stale_streak()`)
- Task 3: Task 1 (needs `mark_demoted()`), partial dependency on Task 2 (shares transaction pattern)
- Task 4: Tasks 1, 2, 3 (CLI calls all new methods)
- Task 5: Tasks 2, 3 (wires sweep to demotion) — **A3 suggests collapsing this**
- Task 6: Task 2 (modifies `validate_and_filter_entries()`)
- Task 7: All tasks (docs)

### Module coupling (after Phase 2A):
- **validator.py → metadata.py:** Heavy (7 method calls after A1 fix: `upsert_entry`, `record_citation`, `record_check`, `update_confidence`, `get_entry`, `reactivate_entry`, `increment_stale_streak`, `reset_stale_streak`)
- **validator.py → citations.py:** Heavy (4 function calls: `extract_citations`, `resolve_citation`, `validate_citation`, `compute_confidence`)
- **promoter.py → metadata.py:** Light (1 method call: `mark_demoted`)
- **promoter.py → journal.py:** Medium (3 method calls: `record_pending`, `mark_committed`, `record_demoted`)
- **__main__.py → validator.py, promoter.py, metadata.py:** Light (calls top-level functions only)

No circular dependencies. All dependencies flow downward in the layer stack:

```
CLI (__main__.py)
    ↓
Pipeline (synthesize.py, validator.py, promoter.py)
    ↓
Core logic (citations.py, dedup.py, stability.py)
    ↓
Storage (metadata.py, journal.py)
```

This is correct architecture.

---

## Boundary Analysis: Demotion vs Promotion

**Question:** Should demotion logic live in `promoter.py` or a separate module?

**Plan's choice:** `promoter.py` gains `demote_entries()` (Task 3).

**Rationale:** "promoter.py owns target doc mutations — both adding and removing content."

**Analysis:**

**For keeping demotion in promoter.py:**
- Symmetry: `promote_entries()` adds lines, `demote_entries()` removes lines
- Both need journal integration
- Both mutate target docs (AGENTS.md/CLAUDE.md)

**Against:**
- Naming confusion: "promoter" implies adding, not removing
- Different triggers: promotion is pipeline-driven (synthesis), demotion is maintenance-driven (sweep)
- Different failure modes: promotion can fail if section doesn't exist, demotion can fail if line not found

**Verdict:** The plan's choice is acceptable. The boundary is "target doc mutation" not "promotion vs demotion." If Phase 2B adds more demotion features (e.g., bulk archive to a separate doc), consider extracting to `target_doc_manager.py` with both `promote_entries()` and `demote_entries()`.

**For Phase 2A:** Keep as planned (demotion in promoter.py).

---

## Data Flow Analysis: Sweep → Demote → Re-promote

**Full lifecycle:**

1. **Entry promoted** (Phase 1):
   - `scanner` → `stability` → `validator` → `dedup` → `promoter` → target doc
   - metadata.db: `status='active'`, `confidence=0.8`, `stale_streak=0`

2. **Time passes, entry not seen in auto-memory** (Phase 2A):
   - User stops working on that area, auto-memory doesn't regenerate the fact
   - 14 days pass, no `last_seen` update

3. **Sweep triggered** (`intermem sweep`):
   - `sweep_all_entries()` re-validates citations
   - `apply_decay_penalty()` reduces confidence: 0.8 → 0.6 (first 14-day period)
   - `stale_streak` still 0 (confidence >= 0.3)

4. **Another 14 days pass, another sweep**:
   - Confidence: 0.6 → 0.4 (second 14-day period)
   - Still above threshold, `stale_streak` still 0

5. **Another 14 days, third sweep**:
   - Confidence: 0.4 → 0.3 (third 14-day period, at threshold boundary)
   - `stale_streak` = 0 (confidence exactly 0.3, not below)

6. **Another 14 days, fourth sweep**:
   - Confidence: 0.3 → 0.2 (fourth 14-day period, now below threshold)
   - `stale_streak` incremented to 1

7. **Another 14 days, fifth sweep**:
   - Confidence: 0.2 → 0.1 (fifth 14-day period)
   - `stale_streak` incremented to 2
   - **Demotion triggered** (stale_streak >= 2)
   - `demote_entries()` removes line from target doc
   - metadata.db: `status='demoted'`, `demoted_at=<timestamp>`

8. **Entry reappears in auto-memory** (user returns to that area):
   - Normal synthesis pipeline runs
   - `validate_and_filter_entries()` sees entry hash in metadata.db with `status='demoted'`
   - Citations re-validated, confidence computed (e.g., 0.8)
   - Task 6 logic: if confidence >= 0.3 and status == 'demoted', call `metadata_store.reactivate_entry()` (A1 fix)
   - Entry now `status='active'`, `stale_streak=0`, `demoted_at=NULL`
   - Dedup sees entry not in target doc (was removed during demotion)
   - Entry promoted again

**Timeline:** ~70 days (5 sweeps × 14 days) from last_seen to demotion. This is intentionally long (hysteresis prevents premature demotion).

**Gaps in the plan:**

**Gap 1:** Task 6 (lines 346-357) says re-promotion happens in `validate_and_filter_entries()`. But that function runs during synthesis on entries from auto-memory. A demoted entry in metadata.db but **not** in auto-memory won't be touched. Re-promotion only works if the fact reappears in auto-memory.

**Is this correct?** Yes. Re-promotion should only happen when the fact is actively re-learned (appears in auto-memory again). If a demoted entry never reappears, it stays demoted. This is correct behavior.

**Gap 2:** The dedup check (line 359) assumes the promoted line was removed from the target doc during demotion. But if demotion failed (e.g., line not found, wrong content match — see A2), the line might still be in the target doc. Dedup would see it as a duplicate and skip re-promotion.

**Fix:** A2 fix (hash-based marker) makes demotion deterministic, eliminating this failure mode.

**Verdict:** Data flow is sound after A1 and A2 fixes.

---

## Exit Criteria Recommendation

Before merging Phase 2A:

1. All 4 must-fix issues (A1, A2, A4, and either accept or address A3) resolved
2. All 119 existing tests pass
3. All ~29 new tests pass
4. Manual test: Backward compat — run existing `/intermem:synthesize` skill without code changes
5. Manual test: Full round-trip — entry promoted → ages 70+ days → sweep → demoted → reappears → re-promoted
6. Schema migration verified on a real metadata.db from Phase 1 (copy from a live project, run migration, verify columns added)
7. CLI backward compat verified: `python -m intermem --project-dir . --validate` works without `synthesize` subcommand

---

## Summary Recommendations

**Architecture verdict:** The plan is structurally sound, but has 3 critical boundary violations (A1, A2, A4) that must be fixed before implementation. The task breakdown is mostly correct, with one unnecessary task (A3) that should be collapsed.

**Action items:**
1. Revise Task 1 to add `reactivate_entry()` method
2. Revise Task 3 to embed entry hash in `<!-- intermem -->` marker (or store full content)
3. Revise Task 4 to keep common CLI args on parent parser for backward compatibility
4. Collapse Task 5 into Task 2 (optional but recommended)
5. Remove unused `get_promoted_entries()` method from Task 1 (optional)

**Estimated revision effort:** 2-3 hours to update plan + add tests for the new constraints.

**Green light after revisions:** Yes, with the must-fix issues addressed.

---

## File Locations for Reference

**Plan under review:**
- `/root/projects/Interverse/docs/plans/2026-02-18-intermem-phase2a-decay-demotion.md`

**Existing source files analyzed:**
- `/root/projects/Interverse/plugins/intermem/intermem/validator.py`
- `/root/projects/Interverse/plugins/intermem/intermem/metadata.py`
- `/root/projects/Interverse/plugins/intermem/intermem/promoter.py`
- `/root/projects/Interverse/plugins/intermem/intermem/__main__.py`
- `/root/projects/Interverse/plugins/intermem/intermem/synthesize.py`
- `/root/projects/Interverse/plugins/intermem/intermem/journal.py`

**Project documentation:**
- `/root/projects/Interverse/plugins/intermem/CLAUDE.md`
