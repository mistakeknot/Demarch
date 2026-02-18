# Brainstorm: intermem Phase 1 — Validation Overlay

**Bead:** iv-n4p7
**Phase:** brainstorm (as of 2026-02-18T00:25:22Z)
**Date:** 2026-02-18
**Status:** brainstorm
**Context:** Phase 0.5 (memory synthesis) is complete and dogfooded. 50 tests pass. Plugin installed and validated against Interverse (42 entries, 10 pointers filtered, 32 candidates identified).

---

## 1. Problem Statement

Auto-memory entries frequently reference code artifacts: file paths, function names, modules, patterns. Today, intermem treats all entries as equally trustworthy — a fact about `plugins/interkasten/server/src/store/db.ts` gets the same confidence whether that file still exists or was deleted three weeks ago.

**The core problem:** Promoted memories can go stale, injecting outdated information into agent context. There's no mechanism to detect or flag this.

**Decision gate (from roadmap):** Does validation reduce stale injections >30%?

---

## 2. Current State

### What exists (Phase 0.5)
- **scanner.py** — Parses auto-memory markdown into `MemoryEntry` dataclasses with `content`, `section`, `source_file`, `start_line`, `end_line`, `is_pointer`
- **stability.py** — JSONL snapshot store, content hashing (SHA-256[:16]), 3-snapshot stability threshold
- **dedup.py** — 3-layer matching (exact hash, fuzzy line >=75%, keyword overlap >=60%)
- **journal.py** — Append-only JSONL WAL: pending → committed → pruned
- **promoter.py** — Writes entries to target docs with `<!-- intermem -->` markers
- **pruner.py** — Removes promoted entries from source memory files
- **synthesize.py** — Pipeline orchestrator: scan → stability → dedup → approve → promote → prune

### What's missing
- No metadata database — provenance is spread across JSONL files with no queryable index
- No citation extraction — entries mentioning file paths are opaque strings
- No validation — promoted facts never checked against current codebase
- No staleness detection — once promoted, entries live forever unless manually removed
- No confidence scoring — all stable entries treated equally

---

## 3. Key Questions

### Q1: What types of citations exist in memory entries?

From analyzing the Interverse auto-memory (42 entries):

| Citation type | Example | Prevalence | Validation method |
|---|---|---|---|
| File paths (backtick) | `` `docs/guides/foo.md` `` | ~30% | `os.path.exists()` |
| File paths (prose) | "in scanner.py" | ~15% | Pattern match + exists |
| Module references | "interkasten", "intermute" | ~20% | Directory check |
| CLI commands | `` `--write-output <path>` `` | ~15% | Not validatable |
| Env variables | `DISPLAY=:99` | ~5% | Not validatable |
| Behavioral rules | "Never use X" | ~15% | Not validatable |

**Key insight:** ~50% of entries contain validatable citations (file paths + module refs). The other 50% are behavioral rules or CLI conventions that can't be programmatically validated.

### Q2: What SQLite patterns should we follow?

From research across the ecosystem:

| Convention | Source | Recommendation |
|---|---|---|
| Storage location | interspect, beads | `.intermem/metadata.db` (per-project, gitignored) |
| Journal mode | interkasten | `PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;` |
| Schema approach | interkasten | Raw SQL constant in Python module, `CREATE TABLE IF NOT EXISTS` |
| Timestamp format | All three | ISO 8601 TEXT: `DEFAULT (datetime('now'))` |
| Content hashing | stability.py | SHA-256[:16] (reuse existing `_hash_entry()`) |
| Migration strategy | intermute | Helper functions: `table_exists()`, `column_exists()` |
| Python driver | Phase 0.5 stdlib-only | `sqlite3` (stdlib) — no ORM needed |
| Busy timeout | intercore design | `PRAGMA busy_timeout = 5000;` for concurrent sessions |

### Q3: How should staleness be scored?

Borrow interwatch's signal-based scoring adapted for citations:

| Signal | Weight | Source | Phase |
|---|---|---|---|
| Cited file path deleted | -0.4 | `os.path.exists()` | 1 |
| Cited module directory gone | -0.4 | Directory check | 1 |
| Entry stable across 5+ snapshots | +0.2 | stability.jsonl | 1 |
| All citations valid | +0.3 | citation_checks table | 1 |
| Entry not validated in 14+ days | -0.1 | Timestamp comparison | 1 |
| Cited file path renamed | -0.2 | `git log --follow` | 2 (deferred) |

Starting confidence: 0.5 (neutral). Threshold: < 0.3 = "stale" (excluded from promotion, flagged in reports).

### Q4: How does this integrate with the existing pipeline?

Two integration points:

1. **After stability scoring, before dedup:** Extract citations from stable entries, validate against codebase, compute confidence. Entries with confidence < threshold get flagged, not promoted.

2. **As a standalone validation command:** `/intermem:validate` runs citation checks against already-promoted entries, flagging stale ones in target docs.

### Q5: Should we migrate stability.jsonl into SQLite?

**No, not in Phase 1.** The JSONL files remain the source of truth for Phase 0.5 operations. metadata.db is additive — it tracks provenance and citation data alongside the existing state. Migration to unified SQLite can happen in Phase 2+ if warranted.

---

## 4. Proposed Architecture

### 4.1 New module: `intermem/metadata.py`

```
MetadataStore (class)
  __init__(db_path: Path)           # Opens/creates .intermem/metadata.db
  ensure_schema()                   # CREATE TABLE IF NOT EXISTS
  record_entry(entry: MemoryEntry)  # Upsert into memory_entries
  record_citation(entry_hash, citation_type, citation_value)
  record_check(entry_hash, citation_value, result, detail)
  update_confidence(entry_hash, confidence)
  get_stale_entries() -> list       # confidence < 0.3
  get_entry_metadata(entry_hash)    # Full provenance for one entry
  import_from_stability(store)      # One-time: read stability.jsonl snapshots,
                                     # populate first_seen/last_seen/snapshot_count.
                                     # Low complexity: iterate snapshots, upsert entries.
```

### 4.2 New module: `intermem/citations.py`

```
extract_citations(entry: MemoryEntry) -> list[Citation]
  # Regex-based extraction of file paths, module refs, function names
  # Returns Citation(type, value, raw_match)

validate_citation(citation: Citation, project_root: Path) -> CheckResult
  # file_path → os.path.exists(resolved) + git log --follow
  # module → directory check
  # function_name → grep in cited file (if available)
  # Returns CheckResult(status, detail, confidence_delta)

validate_entries(entries, project_root, metadata_store)
  # Orchestrator: extract → validate → record → score
```

### 4.3 Schema: `.intermem/metadata.db`

```sql
-- Core entry tracking
CREATE TABLE IF NOT EXISTS memory_entries (
  entry_hash TEXT PRIMARY KEY,
  content_preview TEXT NOT NULL,
  section TEXT NOT NULL,
  source_file TEXT NOT NULL,
  first_seen TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen TEXT NOT NULL DEFAULT (datetime('now')),
  snapshot_count INTEGER NOT NULL DEFAULT 1,
  confidence REAL NOT NULL DEFAULT 0.5,
  status TEXT NOT NULL DEFAULT 'active'
);

-- Citations extracted from entries
CREATE TABLE IF NOT EXISTS citations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_hash TEXT NOT NULL REFERENCES memory_entries(entry_hash),
  citation_type TEXT NOT NULL,        -- Phase 1: 'file_path' | 'module'. Phase 2+: 'function' | 'pattern'
  citation_value TEXT NOT NULL,
  resolved_path TEXT,
  status TEXT NOT NULL DEFAULT 'unchecked',
  last_validated TEXT,
  last_valid TEXT
);

-- Audit log of all checks
CREATE TABLE IF NOT EXISTS citation_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_hash TEXT NOT NULL,
  citation_value TEXT NOT NULL,
  check_type TEXT NOT NULL,
  result TEXT NOT NULL,
  detail TEXT,
  checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 4.4 Pipeline integration

```
run_synthesis():
  scan → stability → [NEW: validate_citations] → dedup → approve → promote → prune
                          ↓
                    metadata.db updated
                    stale entries filtered
```

The validation step:
1. Extract citations from all stable entries
2. Validate each citation against the project root
3. Compute confidence score per entry
4. Filter entries with confidence < 0.3 from promotion candidates
5. Record all results in metadata.db for audit trail

### 4.5 New skill: `/intermem:validate`

Standalone validation that:
1. Scans already-promoted entries in AGENTS.md/CLAUDE.md (entries with `<!-- intermem -->` markers)
2. Extracts and validates their citations
3. Reports stale entries with remediation suggestions
4. Updates metadata.db

---

## 5. Scope Control

### In scope (Phase 1)
- metadata.db with SQLite (stdlib)
- Citation extraction via regex (file paths, modules)
- Basic validation: `os.path.exists()`, directory checks
- Confidence scoring per entry
- Stale entry filtering in synthesis pipeline
- `/intermem:validate` standalone skill
- Tests for all new modules
- Import existing stability data into metadata.db on first run

### Out of scope (later phases)
- Function/symbol-level validation (requires AST parsing or grep — Phase 2)
- Git history integration (`git log --follow` for renames — Phase 2)
- LLM-based citation extraction (better accuracy — Phase 3)
- Cross-project citation tracking (Phase 3)
- Automated remediation of stale entries (Phase 2)
- Decay/TTL system (Phase 2, separate bead iv-rkrm)
- Stability data migration from JSONL to SQLite (Phase 2+)

### Risk assessment
- **Low risk:** metadata.db is additive — doesn't break existing JSONL pipeline
- **Low risk:** Citation extraction is best-effort — unvalidatable entries get "unchecked" status, not rejected
- **Medium risk:** False positives in citation extraction could flag valid entries. Mitigate with conservative regex and "unchecked" default.
- **Rollback cost:** Delete `.intermem/metadata.db` — zero impact on Phase 0.5 pipeline

---

## 6. Decision Gate Measurement

To validate the >30% stale injection reduction:

1. **Synthetic test:** Create a test memory directory with known-stale citations (deleted files, missing modules). Run synthesis with and without validation. Measure: `entries_filtered_by_validation / total_stable_entries`. Must be 100% for the synthetic stale set.
2. **Real-world test:** Run against Interverse and at least one other project. Count entries with extractable citations and how many have stale citations. Even 1 stale entry caught in production validates the mechanism.
3. **Coverage metric:** `entries_with_citations / total_entries` — the fraction of entries Phase 1 can reason about. From Interverse data, expect ~50%.

**Gate pass criteria:** Synthetic test catches 100% of known stale entries AND at least 1 real-world stale citation found across test projects. If no real stale citations exist, the gate passes on synthetic test alone (the mechanism works; real data just happens to be fresh).

---

## 7. Effort Estimate

| Component | Complexity | Files |
|---|---|---|
| metadata.py (SQLite store) | Medium | 1 new |
| citations.py (extract + validate) | Medium | 1 new |
| synthesize.py integration | Low | 1 modified |
| __main__.py (--validate flag) | Low | 1 modified |
| SKILL.md (validate command) | Low | 1 new or modified |
| test_metadata.py | Medium | 1 new |
| test_citations.py | Medium | 1 new |
| test_synthesize.py updates | Low | 1 modified |

Total: ~2 new modules, ~3 modified files, ~2 new test files. Estimated ~400-600 lines of new code.
