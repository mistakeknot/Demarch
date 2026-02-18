# PRD: intermem Phase 1 — Validation Overlay

**Bead:** iv-n4p7
**Date:** 2026-02-18
**Status:** PRD
**Brainstorm:** `docs/brainstorms/2026-02-18-intermem-phase1-validation-overlay.md`
**Research:** `docs/research/research-memory-validation-patterns.md`

---

## Problem

Intermem graduates stable auto-memory entries to curated reference documents (AGENTS.md/CLAUDE.md). Once promoted, entries are assumed accurate indefinitely. In practice, ~50% of entries reference code artifacts (file paths, modules) that can go stale — files get deleted, modules get renamed, directories get reorganized. Stale promoted entries inject outdated information into agent context, causing incorrect behavior.

**Impact:** Every stale entry pollutes every future session's context window with wrong information. The damage compounds over time as the codebase evolves.

---

## Solution

Add a validation overlay to the synthesis pipeline:

1. **Citation extraction** — Parse memory entries for references to code artifacts (file paths, module directories)
2. **Citation validation** — Check whether cited artifacts still exist in the codebase
3. **Confidence scoring** — Score each entry based on citation validity and stability history
4. **Stale filtering** — Exclude low-confidence entries from promotion; flag already-promoted stale entries

All state stored in `.intermem/metadata.db` (SQLite, stdlib, per-project, gitignored).

---

## Features

### F1: Metadata Database (`.intermem/metadata.db`)

SQLite database alongside existing JSONL state files. Tracks:
- Entry provenance: first seen, last seen, snapshot count, source file
- Citations per entry: type, value, validation status
- Audit trail: every citation check logged

**Schema conventions:** WAL mode, NORMAL sync, `CREATE TABLE IF NOT EXISTS`, ISO 8601 timestamps, SHA-256[:16] content hashing (matching existing `stability.py`). Follow interkasten patterns.

**Migration helpers:** `table_exists()`, `column_exists()` for forward-compatible schema evolution. Schema version tracked in `schema_version` table.

### F2: Citation Extraction (`intermem/citations.py`)

Regex-based extraction of two citation types:
- **File paths:** Backtick-quoted paths with `/` separators (`` `path/to/file.ext` ``), absolute paths, paths after "File:", "See:", "in" keywords
- **Module references:** Known module names (from directory listing), directory path references

Each citation gets a type, raw value, and resolved path.

**Path safety:** Resolve all paths against project root using `pathlib.Path.resolve()`. Reject paths that escape the project boundary (interkasten's `resolve + startsWith` pattern).

**Not in Phase 1:** Function/symbol names (requires AST/grep — Phase 2), git rename detection (Phase 2), LLM-based extraction (Phase 3).

### F3: Citation Validation

For each extracted citation:
- **file_path:** `os.path.exists(resolved_path)` → valid/broken
- **module:** Directory exists check → valid/broken

All checks logged in `citation_checks` audit table. Each check records: entry hash, citation value, check type, result, detail JSON, timestamp.

**Fail-closed:** If project root cannot be determined, entries are marked "unchecked" (not "valid"). Never silently skip validation.

### F4: Confidence Scoring

Per-entry confidence score (0.0–1.0) computed from signals:

| Signal | Delta | Phase |
|---|---|---|
| Cited file path exists | +0.3 | 1 |
| Cited module directory exists | +0.3 | 1 |
| Cited file deleted | -0.4 | 1 |
| Cited module gone | -0.4 | 1 |
| Stable 5+ snapshots | +0.2 | 1 |
| Not validated in 14+ days | -0.1 | 1 |

Base: 0.5. Threshold: confidence < 0.3 = "stale" (excluded from promotion).

Entries with no extractable citations keep base confidence (0.5) — they are neither penalized nor boosted.

### F5: Pipeline Integration

`run_synthesis()` gains a `validate` parameter (default: True when metadata.db exists):

```
scan → stability → [validate_citations] → dedup → approve → promote → prune
```

The validation step:
1. Record all stable entries in metadata.db (upsert first_seen/last_seen)
2. Extract citations from entries not yet checked (or checked >24h ago)
3. Validate citations against project root
4. Compute confidence scores
5. Filter entries with confidence < 0.3 from promotion candidates
6. Return `SynthesisResult` with new fields: `validated_count`, `stale_filtered`

### F6: Standalone Validate Skill

New or updated `/intermem:validate` that:
1. Scans already-promoted entries in target docs (entries with `<!-- intermem -->` markers)
2. Extracts and validates their citations
3. Reports stale entries with file/module that's missing
4. Updates metadata.db

CLI: `uv run python -m intermem --validate --project-root /path/to/project`

---

## Non-Goals

- Migrating stability.jsonl or promotion-journal.jsonl into SQLite
- Function/symbol-level validation (requires grep/AST — Phase 2)
- Git rename detection (Phase 2)
- Automated remediation of stale entries (Phase 2)
- Decay/TTL system (Phase 2, bead iv-rkrm)
- Cross-project citation tracking (Phase 3)
- LLM-based citation extraction (Phase 3)

---

## Success Criteria

1. **Synthetic test:** 100% detection of known-stale citations in test fixtures
2. **Real-world test:** At least 1 stale citation found across Interverse + other projects, OR if all are fresh, the mechanism demonstrably works on synthetic data
3. **Coverage:** ~50% of entries have extractable citations (measurable)
4. **No regression:** All existing 50 Phase 0.5 tests continue to pass
5. **Rollback:** Deleting `.intermem/metadata.db` restores Phase 0.5 behavior exactly

---

## Technical Constraints

- **Python stdlib only** — no new dependencies (sqlite3 is stdlib)
- **No hooks** — Clavain hook budget constraint continues
- **Additive state** — metadata.db alongside existing JSONL, not replacing
- **Path-safe** — all path resolution bounded to project root
- **Concurrent-safe** — `PRAGMA busy_timeout = 5000` for multiple sessions

---

## Effort Estimate

| Component | New/Modified | Lines (est.) |
|---|---|---|
| `intermem/metadata.py` | New | ~150 |
| `intermem/citations.py` | New | ~200 |
| `intermem/synthesize.py` | Modified | ~40 |
| `intermem/__main__.py` | Modified | ~20 |
| `tests/test_metadata.py` | New | ~150 |
| `tests/test_citations.py` | New | ~200 |
| `tests/test_synthesize.py` | Modified | ~30 |
| SKILL.md / CLAUDE.md | Modified | ~20 |

Total: ~800 lines new code, ~90 lines modified.
