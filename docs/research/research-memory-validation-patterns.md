# Research: Memory Validation & Citation Provenance Patterns for intermem Phase 1

**Date:** 2026-02-17
**Scope:** SQLite conventions, file path validation, citation checking, staleness detection patterns across Interverse
**Purpose:** Inform intermem Phase 1 (validation overlay with `.intermem/metadata.db`, citation checking, staleness detection)

---

## 1. Existing Intermem State (Phase 0.5 Complete)

Phase 0.5 (Memory Synthesis) is already implemented in `plugins/intermem/intermem/`. The existing codebase uses **JSONL flat files** for state:

- `plugins/intermem/intermem/scanner.py` -- parses auto-memory markdown into `MemoryEntry` dataclasses
- `plugins/intermem/intermem/stability.py` -- per-entry content hashing via JSONL (`StabilityStore` with `.intermem/stability.jsonl`)
- `plugins/intermem/intermem/dedup.py` -- fuzzy matching against AGENTS.md/CLAUDE.md via `difflib.SequenceMatcher`
- `plugins/intermem/intermem/journal.py` -- WAL-style JSONL journal (`PromotionJournal`)
- `plugins/intermem/intermem/promoter.py` -- writes entries to target docs with `<!-- intermem -->` markers
- `plugins/intermem/intermem/pruner.py` -- removes promoted entries from auto-memory
- `plugins/intermem/intermem/synthesize.py` -- pipeline orchestrator

The brainstorm (`intermem/docs/brainstorms/2026-02-16-intermem-brainstorm.md`) describes Phase 1 as:

> **Phase 1:** Validation overlay (`.intermem/metadata.db`, citation-checking)
> - Decision gate: Does validation reduce stale injections >30%?
> - Rollback cost: Delete one SQLite file

The brainstorm explicitly calls for Python + SQLite. The existing Phase 0.5 uses Python 3.11+ with `uv run` and only stdlib dependencies.

**No existing PRD or plan exists for Phase 1 specifically.** The brainstorm covers the roadmap but Phase 1 needs its own strategy/PRD/plan cycle.

---

## 2. SQLite Usage Patterns Across Interverse

Three modules provide architectural precedents for intermem's metadata.db:

### 2.1 interkasten (TypeScript, better-sqlite3 + Drizzle ORM)

**File:** `plugins/interkasten/server/src/store/db.ts`
**File:** `plugins/interkasten/server/src/store/schema.ts`

**Key patterns:**
- **WAL mode + NORMAL sync:** `sqlite.pragma("journal_mode = WAL"); sqlite.pragma("synchronous = NORMAL"); sqlite.pragma("foreign_keys = ON");`
- **Schema-as-code:** Raw SQL in `SCHEMA_SQL` constant, not migration files. Uses `CREATE TABLE IF NOT EXISTS` for idempotent creation.
- **Column migrations via PRAGMA table_info:** Checks for column existence before `ALTER TABLE ADD COLUMN` -- no migration framework needed for small schemas.
- **Content-addressed storage:** `base_content` table with `content_hash TEXT NOT NULL UNIQUE` for deduplication.
- **Application-level WAL (sync_wal table):** Beyond SQLite's journal_mode WAL, interkasten has its own WAL table with state machine: `pending -> target_written -> committed -> rolled_back`. This is the pattern documented in `docs/guides/data-integrity-patterns.md`.
- **Append-only audit log:** `sync_log` table for all operations (push/pull/merge/conflict/error).
- **Drizzle ORM for type safety**, but raw SQL for schema creation and migrations.
- **Path as unique key:** `entity_map.local_path TEXT NOT NULL UNIQUE` -- file paths are indexed and used as natural keys.
- **Soft delete pattern:** `deleted INTEGER NOT NULL DEFAULT 0` + `deleted_at TEXT` for 30-day retention.
- **ISO datetime strings:** All timestamps stored as `TEXT NOT NULL DEFAULT (datetime('now'))`.

**Relevance to intermem Phase 1:** This is the closest architectural precedent. intermem's metadata.db should follow the same patterns: WAL mode, PRAGMA-based column migration, content hashing, append-only log. The interkasten schema approach (raw SQL constants, not migration files) is appropriate for a small, single-purpose database.

### 2.2 intermute (Go, modernc.org/sqlite -- pure Go, no CGO)

**File:** `services/intermute/internal/storage/sqlite/schema.sql`
**File:** `services/intermute/internal/storage/sqlite/sqlite.go`
**File:** `services/intermute/internal/storage/sqlite/resilient.go`

**Key patterns:**
- **Embedded schema via `//go:embed schema.sql`** -- schema lives in a separate `.sql` file.
- **Progressive migrations:** `migrateMessages()`, `migrateInboxIndex()`, `migrateThreadIndex()`, etc. Each checks if migration is needed via `tableExists()`, `tableHasColumn()`, `tableHasCompositePK()` helpers.
- **Transactions for multi-table writes:** `tx, err := s.db.Begin(); defer tx.Rollback(); ... tx.Commit()`
- **ResilientStore wrapper:** Every method wrapped with `CircuitBreaker + RetryOnDBLock` -- circuit breaker (threshold=5, reset=30s) prevents cascading failures.
- **Sweeper goroutine:** Background cleanup of expired reservations via `SweepExpired()` that also checks agent heartbeat freshness.
- **WAL checkpoint on close:** `PRAGMA wal_checkpoint(TRUNCATE)` before closing.
- **Cursor-based pagination:** `cursor INTEGER NOT NULL` on inbox_index, not offset/limit.
- **Composite primary keys:** `PRIMARY KEY (project, message_id)` for multi-tenant isolation.
- **JSON columns for flexible data:** `capabilities_json TEXT`, `metadata_json TEXT`, `to_json TEXT`.

**Relevance to intermem Phase 1:** The resilient store pattern (circuit breaker + retry) is overkill for a local CLI tool but the migration helper functions (`tableExists`, `tableHasColumn`) are directly reusable in Python. The sweeper pattern is relevant for staleness detection -- a periodic scan that compares timestamps and flags expired entries.

### 2.3 interspect (`.clavain/interspect/interspect.db`)

Interspect databases exist in multiple projects:
- `/root/projects/Interverse/.clavain/interspect/interspect.db`
- `/root/projects/Interverse/os/clavain/.clavain/interspect/interspect.db`
- `/root/projects/Interverse/plugins/interkasten/.clavain/interspect/interspect.db`
- `/root/projects/Interverse/plugins/intercheck/.clavain/interspect/interspect.db`
- (and 6 more)

These are per-project SQLite databases created by the interspect canary monitoring system. They follow the `.clavain/` namespace convention for Clavain-managed state.

**Relevance:** Confirms the pattern of per-project `.clavain/` or `.intermem/` SQLite databases is standard in the ecosystem.

### 2.4 beads (`.beads/bd.db`)

Referenced in `docs/research/research-intercore-state-patterns.md`:
- Primary persistence for lifecycle phases, sprint metadata, session claims
- Uses `bd set-state` / `bd state` CLI for read/write
- Per-project SQLite at `.beads/bd.db`

**Relevance:** Another per-project SQLite precedent. The CLI-first access pattern (shell commands wrapping SQLite) matches what intermem Phase 1 would use.

---

## 3. Convention Summary for intermem's metadata.db

Based on the three SQLite precedents, intermem Phase 1 should follow these conventions:

| Convention | Source | Recommendation |
|---|---|---|
| **Storage location** | interspect, beads | `.intermem/metadata.db` (per-project, gitignored) |
| **Journal mode** | interkasten | `PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA foreign_keys = ON;` |
| **Schema approach** | interkasten | Raw SQL constant in Python, `CREATE TABLE IF NOT EXISTS`, PRAGMA-based column migrations |
| **Timestamp format** | All three | ISO 8601 TEXT columns: `TEXT NOT NULL DEFAULT (datetime('now'))` |
| **Content hashing** | interkasten, intermem Phase 0.5 | SHA-256 truncated to 16 hex chars (matching existing `_hash_entry()` in stability.py) |
| **Migration strategy** | intermute | Helper functions: `table_exists()`, `column_exists()`, conditional `ALTER TABLE` |
| **Audit log** | interkasten | Append-only `citation_checks` table for all validation events |
| **Cleanup** | intermute sweeper | Periodic staleness scan comparing timestamps |
| **JSON columns** | intermute | For flexible metadata: `citations_json TEXT`, `confidence_json TEXT` |
| **Python driver** | Phase 0.5 uses stdlib only | `sqlite3` (stdlib) -- no need for SQLAlchemy or other ORM for this schema size |

---

## 4. File Path Validation Patterns

### 4.1 interkasten: resolve + startsWith

**File:** `plugins/interkasten/server/src/sync/engine.ts` (line 401-405)

```typescript
const resolved = resolve(projectDir, basename(entity.localPath));
if (!resolved.startsWith(projectDir + "/")) {
  appendSyncLog(this.db, {
    entityMapId: entity.id,
    operation: "error",
    // ... path traversal rejection
  });
}
```

This is the **canonical path validation pattern** in the codebase:
1. `resolve()` the path (resolves `..`, symlinks, etc.)
2. Check that the resolved path starts with the expected directory + `/`
3. Log and reject if outside boundary

### 4.2 Guard Fallthrough Pattern (docs/guides/data-integrity-patterns.md)

The guide documents the **fail-closed** pattern for path validation:

```typescript
const projectDir = this.findProjectDir(entity.localPath);
if (!projectDir) {
  // Fail closed: no context means we can't validate
  appendSyncLog(db, { ... error: "No project directory found -- aborting" });
  return;
}
```

**Key rule:** When the prerequisite for validation (project root, schema, user context) is missing, **abort the operation** rather than silently skipping validation.

### 4.3 Relevance to Citation Checking

For intermem Phase 1, citation checking validates that file paths and function names mentioned in memory entries still exist. The validation pattern should be:

1. **Extract citations:** Parse memory entry content for file paths (`/root/projects/...`, relative paths like `src/store/db.ts`), function names (backtick-quoted identifiers), and pattern references.
2. **Resolve each path** against the project root using `pathlib.Path.resolve()`.
3. **Fail-closed:** If the project root cannot be determined, mark the entry as "unverifiable" rather than "valid."
4. **Log results:** Every citation check recorded in the audit log (metadata.db `citation_checks` table).

---

## 5. Staleness Detection Patterns

### 5.1 interwatch: Signal-Based Drift Scoring

**File:** `plugins/interwatch/scripts/interwatch-scan.py`

interwatch uses a **weighted signal scoring** system for doc freshness:

- Multiple signals evaluated per document (bead_closed, version_bump, commits_since_update, file_renamed, etc.)
- Each signal has a weight and produces a count
- Score = sum(weight * count) across all signals
- Score maps to confidence tier: Green (0), Low (1-2), Medium (3-5), High (6+), Certain (deterministic change)
- Tiers map to actions: none, report-only, suggest-refresh, auto-refresh

**Key insight:** interwatch evaluates staleness via **external signals** (git history, file mtimes, beads) rather than internal content comparison. This is the right model for memory entry staleness too:

| Signal for memory entry staleness | Weight | Source |
|---|---|---|
| Cited file path no longer exists | 3 (high) | `os.path.exists()` |
| Cited file path has been renamed/moved | 2 | `git log --follow --diff-filter=R` |
| Cited function/symbol no longer exists in file | 3 (high) | grep/AST parse |
| Entry references a module that has been removed | 3 (high) | directory check |
| Entry is older than N days without re-validation | 1 (low) | timestamp comparison |
| Entry was promoted from auto-memory (known stable) | -1 (bonus) | promotion journal |
| Entry was confirmed by user correction | -2 (bonus) | explicit validation log |

### 5.2 intermute Sweeper: Time-Based Expiration

**File:** `services/intermute/internal/storage/sqlite/sweeper.go`

The sweeper pattern:
1. Periodic background scan (configurable interval)
2. Query for entries past their expiration time
3. Cross-reference with agent heartbeat (don't sweep if agent is still active)
4. Delete expired entries and emit events

For intermem, staleness detection is not about deletion but about **flagging** -- marking entries as stale so the synthesis pipeline can either re-validate or propose removal.

### 5.3 Proposed Staleness Detection Architecture

Combine interwatch's signal scoring with intermute's periodic sweep:

```
citation_entries table:
  entry_hash TEXT NOT NULL      -- links to stability.jsonl entry
  citation_type TEXT NOT NULL   -- 'file_path' | 'function_name' | 'pattern' | 'module'
  citation_value TEXT NOT NULL  -- the actual path/name/pattern
  first_seen TEXT NOT NULL
  last_validated TEXT NOT NULL
  last_valid TEXT               -- last time the citation checked out
  status TEXT NOT NULL          -- 'valid' | 'stale' | 'broken' | 'unverifiable'
  confidence REAL NOT NULL      -- 0.0 to 1.0

citation_checks table (audit log):
  id INTEGER PRIMARY KEY
  entry_hash TEXT NOT NULL
  citation_value TEXT NOT NULL
  check_type TEXT NOT NULL      -- 'file_exists' | 'symbol_exists' | 'pattern_match'
  result TEXT NOT NULL           -- 'valid' | 'stale' | 'broken'
  detail TEXT                    -- JSON with error message or match context
  checked_at TEXT NOT NULL
```

---

## 6. Existing Citation/Reference Checking Patterns

### 6.1 No Formal Citation Validation Exists in the Codebase

Searching the codebase for "citation", "reference check", "provenance" patterns found **zero implemented citation validation systems**. The interwatch drift detection is the closest analog, but it checks document freshness against external signals, not internal reference validity.

The intermem brainstorm notes (gap #3):
> **No memory validation on retrieval** -- only Copilot checks if memories are still true

And from the landscape research:
> **Copilot Memory** | Citation validation | Validates memories against current code

This confirms that citation validation for memory entries is a genuinely novel capability in the Interverse ecosystem. There is no existing code to reuse -- this needs to be built from scratch.

### 6.2 interwatch Signals as Citation Check Primitives

While no citation checker exists, interwatch's signal evaluators provide reusable primitives:

- `eval_file_changed()` -- uses `git diff --name-status` to detect renames/deletes since a reference date
- `eval_version_bump()` -- compares declared version against actual version
- `eval_component_count_changed()` -- counts actual components vs documented claims
- `eval_commits_since_update()` -- uses `git rev-list --count` for recency

These can be adapted for citation checking:
- `git log --follow <path>` to detect if a cited file was renamed
- `grep -rn <function_name> <file>` to verify a cited function still exists
- `os.path.exists()` for basic path validation

### 6.3 Compound (Clavain) as Provenance Source

The Compound system in Clavain already captures provenance metadata in its YAML frontmatter:

```yaml
# docs/solutions/*.md
---
date: YYYY-MM-DD
category: <category>
signal_weight: N
files: [list, of, files]
---
```

This `files` field is effectively a citation list. Phase 1 could mine Compound solution docs for their file references and validate those as well, extending citation checking beyond auto-memory to all memory stores.

---

## 7. WAL Pattern (Application-Level)

### 7.1 interkasten's sync_wal Table

**File:** `plugins/interkasten/server/src/store/schema.ts` (lines 66-79)

```sql
CREATE TABLE IF NOT EXISTS sync_wal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_map_id INTEGER NOT NULL REFERENCES entity_map(id),
  operation TEXT NOT NULL,     -- 'push' | 'pull' | 'merge'
  state TEXT NOT NULL,         -- 'pending' | 'target_written' | 'committed' | 'rolled_back'
  old_base_id INTEGER REFERENCES base_content(id),
  new_content TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT
);
```

State machine: `pending -> target_written -> committed` (success) or `pending -> rolled_back` (failure).

### 7.2 intermem Phase 0.5's Promotion Journal

The existing `PromotionJournal` in `plugins/intermem/intermem/journal.py` already implements an application-level WAL using JSONL:

State machine: `pending -> committed -> pruned`

### 7.3 data-integrity-patterns.md Rules

From `/root/projects/Interverse/docs/guides/data-integrity-patterns.md`:

1. **WAL entry lifetime = first mutation -> last side effect**
2. Call `mark_committed` AFTER the file write succeeds, not before
3. WAL delete only AFTER all effects complete
4. **Audit technique:** grep for all write calls and verify each has a WAL entry

### 7.4 Recommendation for Phase 1

Phase 1 adds a **metadata database** but does not need its own WAL table because:
- Citation checks are **read-only observations** -- they don't mutate memory entries
- The staleness flag update is a simple single-table UPDATE, not a multi-step operation
- The existing promotion journal (JSONL) handles write atomicity for Phase 0.5's promote+prune

However, if Phase 1 adds **automated remediation** (e.g., auto-updating stale citations), then a WAL table becomes necessary. Design for it now, implement later:

```sql
-- Reserved for Phase 2+ remediation
CREATE TABLE IF NOT EXISTS remediation_wal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_hash TEXT NOT NULL,
  operation TEXT NOT NULL,       -- 'update_citation' | 'remove_entry' | 'flag_review'
  state TEXT NOT NULL DEFAULT 'pending',
  old_value TEXT,
  new_value TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT
);
```

---

## 8. Proposed metadata.db Schema

Based on all patterns found, here is the recommended schema for `.intermem/metadata.db`:

```sql
-- Schema version tracking (intermute migration pattern)
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Memory entry metadata (core of Phase 1)
CREATE TABLE IF NOT EXISTS memory_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_hash TEXT NOT NULL UNIQUE,        -- SHA-256[:16] of normalized content
  content_preview TEXT NOT NULL,           -- First 200 chars for display
  section TEXT NOT NULL,                   -- Section heading the entry belongs to
  source_file TEXT NOT NULL,               -- e.g., "MEMORY.md"
  source_store TEXT NOT NULL DEFAULT 'auto_memory',  -- 'auto_memory' | 'compound' | 'interfluence' | 'clavain_learnings'
  first_seen TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen TEXT NOT NULL DEFAULT (datetime('now')),
  snapshot_count INTEGER NOT NULL DEFAULT 1,
  stability_score TEXT NOT NULL DEFAULT 'recent',  -- 'recent' | 'stable' | 'volatile'
  promoted_to TEXT,                        -- NULL or 'AGENTS.md' | 'CLAUDE.md'
  promoted_at TEXT,
  confidence REAL NOT NULL DEFAULT 0.5,    -- Overall confidence score 0.0-1.0
  status TEXT NOT NULL DEFAULT 'active',   -- 'active' | 'stale' | 'broken' | 'archived'
  stale_reason TEXT                        -- JSON: why this entry was flagged stale
);

CREATE INDEX IF NOT EXISTS idx_entries_hash ON memory_entries(entry_hash);
CREATE INDEX IF NOT EXISTS idx_entries_status ON memory_entries(status);
CREATE INDEX IF NOT EXISTS idx_entries_source ON memory_entries(source_store);

-- Citations extracted from memory entries
CREATE TABLE IF NOT EXISTS citations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_hash TEXT NOT NULL,               -- FK to memory_entries.entry_hash
  citation_type TEXT NOT NULL,            -- 'file_path' | 'function_name' | 'module' | 'pattern' | 'url'
  citation_value TEXT NOT NULL,           -- The actual reference (path, name, pattern)
  resolved_value TEXT,                    -- Resolved absolute path (if file_path type)
  first_seen TEXT NOT NULL DEFAULT (datetime('now')),
  last_validated TEXT,                    -- Last time we checked this citation
  last_valid TEXT,                        -- Last time the citation checked out
  status TEXT NOT NULL DEFAULT 'unchecked',  -- 'valid' | 'stale' | 'broken' | 'unchecked'
  confidence REAL NOT NULL DEFAULT 0.5
);

CREATE INDEX IF NOT EXISTS idx_citations_entry ON citations(entry_hash);
CREATE INDEX IF NOT EXISTS idx_citations_status ON citations(status);
CREATE INDEX IF NOT EXISTS idx_citations_type ON citations(citation_type);

-- Append-only audit log of all citation checks
CREATE TABLE IF NOT EXISTS citation_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_hash TEXT NOT NULL,
  citation_id INTEGER REFERENCES citations(id),
  check_type TEXT NOT NULL,              -- 'file_exists' | 'symbol_grep' | 'git_log' | 'url_head'
  result TEXT NOT NULL,                  -- 'valid' | 'stale' | 'broken' | 'error'
  detail TEXT,                           -- JSON: error message, match context, git rename info
  checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_checks_entry ON citation_checks(entry_hash);
CREATE INDEX IF NOT EXISTS idx_checks_date ON citation_checks(checked_at);
```

---

## 9. Citation Extraction Strategy

Memory entries contain several types of citable references. The extraction pipeline should parse each type:

### 9.1 File Paths

**Regex patterns:**
- Absolute paths: `` `/root/projects/...` `` or bare `/root/projects/...`
- Relative paths in backticks: `` `src/store/db.ts` ``, `` `plugins/interkasten/server/...` ``
- Paths after "File:", "See:", "in" keywords
- Paths in markdown links: `[text](path/to/file.md)`

**Validation:** `os.path.exists(resolved_path)`, and if not found, `git log --all --follow -- <path>` to detect renames.

### 9.2 Function/Symbol Names

**Regex patterns:**
- Backtick-quoted identifiers: `` `functionName()` ``, `` `ClassName.method` ``
- After "function", "class", "method" keywords

**Validation:** `grep -rn <symbol> <cited_file>` if file path is also cited; otherwise `grep -rn <symbol> <project_root>` (expensive, cache results).

### 9.3 Module/Package Names

**Regex patterns:**
- Import references: "interkasten", "intermute", "Clavain"
- Directory references: `` `plugins/interkasten/` ``, `` `services/intermute/` ``

**Validation:** Directory existence check.

### 9.4 Pattern/Convention References

**Regex patterns:**
- "WAL pattern", "circuit breaker", "resolve + startsWith"
- These are conceptual references, harder to validate

**Validation:** Best-effort grep for the pattern name in codebase docs. Mark as "unverifiable" if not found (low confidence, not "broken").

---

## 10. Confidence Scoring Model

Borrow interwatch's tiered model but adapt for citation validation:

| Condition | Confidence Adjustment | Rationale |
|---|---|---|
| All citations valid | +0.3 | Strong evidence entry is current |
| Entry stable across 5+ snapshots | +0.2 | Longevity suggests accuracy |
| User explicitly confirmed | +0.3 | Highest signal |
| Promoted to AGENTS.md/CLAUDE.md | +0.1 | Was already reviewed |
| One citation stale (file moved) | -0.2 | Partially outdated |
| One citation broken (file deleted) | -0.4 | Likely outdated |
| Entry not validated in 14+ days | -0.1 | Staleness by time |
| Entry not seen in last 3 snapshots | -0.3 | Possibly removed by user |

Starting confidence: 0.5 (neutral).
Threshold for flagging: < 0.3 = "stale", < 0.1 = "broken".

---

## 11. Migration Path from Phase 0.5 to Phase 1

### 11.1 JSONL to SQLite

Phase 0.5 stores state in two JSONL files:
- `.intermem/stability.jsonl` -- per-entry hash history
- `.intermem/promotion-journal.jsonl` -- promotion lifecycle

Phase 1 should:
1. **Keep JSONL files as input sources** -- the stability store and journal are append-only and work well as JSONL.
2. **Add metadata.db alongside** -- the new database adds citation tracking and staleness detection on top.
3. **Import existing stability data** -- on first Phase 1 run, read all snapshots from `stability.jsonl` and populate `memory_entries` with `first_seen`, `last_seen`, and `snapshot_count`.
4. **Import journal data** -- read `promotion-journal.jsonl` and populate `promoted_to` and `promoted_at` fields.

This is non-destructive: the JSONL files remain the source of truth for Phase 0.5 operations, and metadata.db adds the new Phase 1 capabilities.

### 11.2 Dual-Read Pattern

During transition:
- `StabilityStore` continues reading/writing JSONL (Phase 0.5 pipeline unchanged)
- `MetadataStore` (new) reads from both JSONL (for stability data) and SQLite (for citations/staleness)
- Phase 0.5's `run_synthesis()` orchestrator gains an optional `--validate` flag that triggers citation checking after stability scoring

### 11.3 Eventual Consolidation (Phase 2+)

In a future phase, stability tracking could move into metadata.db entirely, replacing `stability.jsonl`. But this is explicitly not a Phase 1 concern -- keeping the JSONL files means Phase 1 has zero risk of breaking the existing synthesis pipeline.

---

## 12. Key Architectural Decisions for Phase 1

### 12.1 Language: Python (stdlib sqlite3)

Matches Phase 0.5. No external dependencies needed -- Python's `sqlite3` module supports WAL mode, parameterized queries, and all needed features.

### 12.2 Schema Location: In-Code Constant

Follow interkasten's pattern: raw SQL string in a Python module (e.g., `intermem/metadata_schema.py`), not separate migration files. The schema is small enough.

### 12.3 Migration Helpers

Port intermute's pattern to Python:

```python
def table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None

def column_exists(conn, table: str, column: str) -> bool:
    for row in conn.execute(f"PRAGMA table_info({table})"):
        if row[1] == column:
            return True
    return False
```

### 12.4 Citation Check Frequency

Not real-time (too expensive). Run citation checks:
- On every `/intermem:synthesize` invocation (piggyback on existing skill)
- Optionally via a new `/intermem:validate` skill for on-demand checking
- Future: SessionStart hook to surface stale entries (but respect Clavain hook budget)

### 12.5 Fail-Open for Citations

Follow the guard fallthrough pattern from `data-integrity-patterns.md`: if a citation cannot be checked (e.g., project root unknown, git not available), mark as "unchecked" rather than "valid" or "broken". Never silently skip validation.

### 12.6 Path Safety

Apply interkasten's `resolve + startsWith` pattern: when resolving citation paths, ensure they stay within the project boundary. A memory entry citing `../../.ssh/authorized_keys` should be flagged as suspicious, not validated against the filesystem.

---

## 13. Files Referenced in This Research

| File | Why It Matters |
|---|---|
| `plugins/interkasten/server/src/store/db.ts` | WAL mode setup, schema migration, content hashing |
| `plugins/interkasten/server/src/store/schema.ts` | Drizzle schema with sync_wal, content-addressed storage |
| `plugins/interkasten/server/src/sync/engine.ts` | Path validation: resolve + startsWith pattern |
| `services/intermute/internal/storage/sqlite/schema.sql` | Comprehensive SQLite schema with events, agents, reservations |
| `services/intermute/internal/storage/sqlite/sqlite.go` | Migration helpers, transaction patterns, JSON columns |
| `services/intermute/internal/storage/sqlite/resilient.go` | CircuitBreaker + RetryOnDBLock wrapper pattern |
| `services/intermute/internal/storage/sqlite/sweeper.go` | Background cleanup of expired entries |
| `plugins/interwatch/scripts/interwatch-scan.py` | Signal-based drift scoring, staleness detection |
| `plugins/interwatch/skills/doc-watch/phases/detect.md` | Signal evaluation reference (bead_closed, version_bump, etc.) |
| `docs/guides/data-integrity-patterns.md` | WAL protocol rules, guard fallthrough pattern |
| `intermem/docs/brainstorms/2026-02-16-intermem-brainstorm.md` | Phase roadmap, landscape research, design decisions |
| `intermem/docs/plans/2026-02-17-intermem-memory-synthesis.md` | Phase 0.5 implementation plan (already executed) |
| `intermem/docs/research/architecture-review-of-intermem.md` | Flux-Drive architecture review of brainstorm |
| `plugins/intermem/intermem/stability.py` | Existing content hashing and snapshot system |
| `plugins/intermem/intermem/journal.py` | Existing JSONL WAL journal |
| `docs/research/research-intercore-state-patterns.md` | Temp file patterns, beads state, interband protocol |
| `docs/prds/2026-02-17-intercore-state-database.md` | intercore Go CLI with SQLite -- parallel effort |

---

## 14. Risks and Open Questions

1. **intercore overlap:** The intercore PRD proposes a unified Go CLI + SQLite database for all Clavain state. Should intermem's metadata.db eventually be a consumer of intercore, or remain independent? Recommendation: remain independent for Phase 1 (different lifecycle, different data model), but design the schema so it could be imported into intercore later.

2. **Symbol validation cost:** Grepping for function names across a project is expensive. Consider caching results in `citation_checks` and only re-checking when `git log` shows the cited file has changed.

3. **Citation extraction accuracy:** Regex-based extraction will have false positives (backtick-quoted non-code text) and false negatives (paths without backticks). Accept this for Phase 1; Phase 2 could use LLM-based extraction for higher accuracy.

4. **Multi-project scope:** Phase 0.5 is per-project. Phase 1's `metadata.db` should also be per-project (in `.intermem/`), not global. Cross-project citation checking is a Phase 3+ concern.

5. **Concurrent access:** If multiple Claude Code sessions run `/intermem:synthesize` simultaneously, metadata.db needs `busy_timeout` set. SQLite WAL mode handles concurrent reads, but writes need serialization. Recommendation: `PRAGMA busy_timeout = 5000;` (5 seconds, matching intercore's design).
