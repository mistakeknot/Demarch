# Plan: intermem Phase 1 — Validation Overlay

**Bead:** iv-n4p7
**Phase:** executing (as of 2026-02-18T00:36:49Z)
**Date:** 2026-02-18
**PRD:** `docs/prds/2026-02-18-intermem-phase1-validation-overlay.md`
**Working dir:** `plugins/intermem/`
**Reviews:** `.clavain/quality-gates/plan-review-correctness.md`, `docs/research/review-plan-architecture.md`

---

## Review Findings Incorporated

Issues addressed from correctness + architecture reviews:

| ID | Finding | Resolution |
|----|---------|------------|
| C1 | JSONL-SQLite divergence | metadata.db is derived state; reconcile via upsert (idempotent) |
| C2 | 16-char hash collision | Acceptable at our scale (<1000 entries); document decision |
| C3 | Section drift | Last-write-wins: upsert unconditionally updates section |
| C4 | Path traversal | Canonicalize both sides with `Path.resolve()` + `is_relative_to()` |
| M1 | Concurrent upsert race | Atomic SQL `ON CONFLICT DO UPDATE SET snapshot_count = snapshot_count + 1` |
| M2 | Import not idempotent | Use upsert pattern; guard with migration_version in schema_version |
| R1 | `hash(e)` vs `_hash_entry(e)` | Corrected: use `hash_entry()` from `_util.py` |
| R2 | No transaction boundaries | Wrap validation loop in single transaction |
| Arch-1 | metadata→stability coupling | Move import to `__main__.py --import-stability` (one-shot migration) |
| Arch-2 | Duplicated hash computation | Centralize `hash_entry()` and `hash_content()` in `_util.py` |
| Arch-3 | Validation in orchestrator | Extract to `validator.py` with `validate_and_filter_entries()` |

---

## Pre-Task 0: Centralize Hash Functions (`intermem/_util.py`)

**Goal:** Single source of truth for content hashing across all modules.

**Implementation:**

1. Add to `_util.py`:
   ```python
   def hash_entry(entry: MemoryEntry) -> str:
       """Canonical content hash (SHA-256 truncated to 16 hex chars)."""
       return hashlib.sha256(entry.content.strip().encode("utf-8")).hexdigest()[:16]

   def hash_content(content: str) -> str:
       """Hash raw content string."""
       return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16]
   ```
2. Update imports in `stability.py`, `promoter.py`, `dedup.py` — replace private `_hash_entry()` / `_hash_content()` with shared versions
3. Delete private hash functions from those modules

**Acceptance:** `grep -r 'hashlib.sha256' intermem/` shows hits only in `_util.py`.

---

## Task Breakdown

### Task 1: Metadata Store (`intermem/metadata.py`)

**Goal:** SQLite-backed metadata database for entry provenance and citation tracking.

**Implementation:**

1. Create `intermem/metadata.py` with `MetadataStore` class
2. Schema as raw SQL constant (following interkasten pattern):
   - `schema_version` — migration tracking (includes `migration_version` for one-shot imports)
   - `memory_entries` — entry provenance (entry_hash PK, content_preview, section, source_file, first_seen, last_seen, snapshot_count, confidence, confidence_updated_at, status)
   - `citations` — extracted references (entry_hash FK, citation_type, citation_value, resolved_path, status, last_validated)
   - `citation_checks` — audit log (entry_hash, citation_value, check_type, result, detail JSON, checked_at)
3. PRAGMA setup: `journal_mode = WAL`, `synchronous = NORMAL`, `foreign_keys = ON`, `busy_timeout = 5000`
4. `status` field in `memory_entries`: `CHECK(status IN ('active', 'stale', 'orphaned'))`. Default: `'active'`. Updated by `update_confidence()` based on threshold.
5. Methods:
   - `ensure_schema()` — idempotent CREATE TABLE IF NOT EXISTS
   - `upsert_entry(entry_hash, content_preview, section, source_file)` — **atomic SQL upsert:**
     ```sql
     INSERT INTO memory_entries (entry_hash, content_preview, section, source_file, snapshot_count, last_seen)
     VALUES (?, ?, ?, ?, 1, datetime('now'))
     ON CONFLICT(entry_hash) DO UPDATE SET
       snapshot_count = snapshot_count + 1,
       last_seen = datetime('now'),
       section = excluded.section,
       source_file = excluded.source_file;
     ```
     Section uses last-write-wins (C3 resolution).
   - `record_citation(entry_hash, citation_type, citation_value, resolved_path)`
   - `record_check(entry_hash, citation_value, check_type, result, detail)` — append to audit log
   - `update_confidence(entry_hash, confidence)` — sets confidence, confidence_updated_at, and derives status ('active' if >= 0.3, 'stale' otherwise)
   - `get_stale_entries() -> list[dict]` — entries with `status = 'stale'` (confidence < 0.3). Returns dicts with keys: entry_hash, section, confidence, content_preview.
   - `get_unchecked_citations(max_age_hours=24) -> list[dict]` — JOIN with memory_entries where `status = 'active'` (skip stale/orphaned entries)
   - `begin_transaction()` / `commit_transaction()` / `rollback_transaction()` — explicit transaction control for batch operations
6. Migration helpers: `_table_exists()`, `_column_exists()` for future schema evolution
7. **No `import_from_stability()` method** — migration handled externally (see Task 3, `__main__.py`)

**Tests** (`tests/test_metadata.py`):
- Create/open database, ensure_schema is idempotent
- Upsert entry: insert then update increments snapshot_count atomically
- Upsert entry: section updates with last-write-wins
- Record and query citations
- Record check in audit log
- Update confidence → status transitions (active ↔ stale)
- get_stale_entries returns correct dict keys
- get_unchecked_citations filters by entry status
- Concurrent upsert from threads: N threads × M upserts = N*M snapshot_count
- Transaction commit/rollback behavior

**Acceptance:** MetadataStore creates `.intermem/metadata.db`, handles all CRUD with atomic upserts, survives repeated ensure_schema calls.

---

### Task 2: Citation Extraction (`intermem/citations.py`)

**Goal:** Pure functions for extracting, resolving, and validating citations. No I/O beyond `os.path.exists()`.

**Implementation:**

1. Create `intermem/citations.py`
2. Dataclasses:
   - `Citation(type: str, value: str, raw_match: str)` — type is 'file_path' or 'module'
   - `CheckResult(status: str, confidence_delta: float, detail: str)` — status is 'valid', 'broken', 'unchecked'
3. `extract_citations(entry: MemoryEntry) -> list[Citation]`:
   - Regex for backtick-quoted paths: `` `[^\s`]+/[^\s`]+` `` (must contain `/`)
   - Regex for markdown link paths: `[text](path/to/file)`
   - Regex for absolute paths: `/root/projects/...` or similar
   - **Exclusion filters** (applied after extraction):
     ```python
     EXCLUDE_PATTERNS = [
         re.compile(r'^https?://'),       # URLs
         re.compile(r'^\w+://'),          # Other protocols
         re.compile(r'^[A-Z_]+='),        # Env vars
         re.compile(r'^--'),              # CLI flags
         re.compile(r'^\$'),              # Shell variables
     ]
     ```
   - Classify: if contains file extension → file_path; if matches known module dir → module
4. `resolve_citation(citation: Citation, project_root: Path) -> Path | None`:
   - **Canonicalize both sides** (C4 fix):
     ```python
     canonical_root = project_root.resolve()
     resolved = (canonical_root / citation.value).resolve()
     if not resolved.is_relative_to(canonical_root):
         return None  # Escaped project boundary
     return resolved
     ```
   - Uses `Path.is_relative_to()` (Python 3.9+) instead of string prefix comparison
5. `validate_citation(citation: Citation, project_root: Path) -> CheckResult`:
   - file_path: `resolved.exists()` → CheckResult('valid', +0.3, '') or ('broken', -0.4, 'File not found')
   - module: check directory exists → CheckResult('valid', +0.3, '') or ('broken', -0.4, 'Directory not found')
   - Return ('unchecked', 0.0, 'Cannot resolve') if resolve_citation returns None
6. `compute_confidence(base: float, checks: list[CheckResult], snapshot_count: int) -> float`:
   - Start at base (0.5)
   - Add deltas from each check (+0.3 valid, -0.4 broken, 0.0 unchecked)
   - If snapshot_count >= 5: +0.2
   - Clamp to [0.0, 1.0]
   - **Note:** Additive with hard clamp. Many valid citations → 1.0. One broken citation among valid ones still lowers score. Entries with no extractable citations keep base (0.5).

**Tests** (`tests/test_citations.py`):
- Extract backtick file paths
- Extract markdown link paths
- Extract absolute paths
- Ignore CLI flags, URLs, env vars, shell variables, protocol URLs
- Resolve relative paths against project root (canonicalized)
- Reject path traversal attempts (`../../etc/passwd`)
- Reject symlink escape attempts
- Validate existing file → 'valid'
- Validate missing file → 'broken'
- Validate existing directory → 'valid'
- resolve_citation returns None for unresolvable → 'unchecked'
- Compute confidence: all valid → high, one broken → low
- Compute confidence: many valid citations clamp to 1.0
- Entry with no citations → base confidence (0.5)
- Snapshot bonus: count >= 5 adds 0.2

**Acceptance:** Can extract citations from real Interverse auto-memory entries, validate against filesystem, compute meaningful confidence scores.

---

### Task 3: Validation Pipeline (`intermem/validator.py` + pipeline integration)

**Goal:** Wire validation into synthesis pipeline. Extract validation logic into `validator.py` (not in orchestrator).

**Implementation:**

1. Create `intermem/validator.py` with:
   ```python
   @dataclass
   class ValidationResult:
       validated_entries: list[MemoryEntry]
       stale_filtered: list[MemoryEntry]
       validated_count: int
       stale_count: int

   def validate_and_filter_entries(
       entries: list[MemoryEntry],
       metadata_store: MetadataStore,
       project_root: Path,
   ) -> ValidationResult:
       """Validate citations, update metadata, filter stale entries."""
       metadata_store.begin_transaction()
       try:
           for entry in entries:
               entry_hash = hash_entry(entry)  # from _util
               metadata_store.upsert_entry(entry_hash, ...)

               citations = extract_citations(entry)
               checks = []
               for citation in citations:
                   resolved = resolve_citation(citation, project_root)
                   metadata_store.record_citation(entry_hash, ...)
                   result = validate_citation(citation, project_root)
                   metadata_store.record_check(entry_hash, ...)
                   checks.append(result)

               snapshot_count = # from upserted metadata.db row
               confidence = compute_confidence(0.5, checks, snapshot_count)
               metadata_store.update_confidence(entry_hash, confidence)

           metadata_store.commit_transaction()
       except Exception:
           metadata_store.rollback_transaction()
           raise

       stale_hashes = {e['entry_hash'] for e in metadata_store.get_stale_entries()}
       validated = [e for e in entries if hash_entry(e) not in stale_hashes]
       stale = [e for e in entries if hash_entry(e) in stale_hashes]

       return ValidationResult(
           validated_entries=validated,
           stale_filtered=stale,
           validated_count=len(entries),
           stale_count=len(stale),
       )
   ```

2. Update `synthesize.py` — thin integration (3 lines, not 23):
   ```python
   # Add validate and project_root parameters to run_synthesis()
   if validate and stable_entries:
       metadata_store = MetadataStore(intermem_dir / "metadata.db")
       val_result = validate_and_filter_entries(stable_entries, metadata_store, project_root)
       stable_entries = val_result.validated_entries
       validated_count = val_result.validated_count
       stale_filtered = val_result.stale_count
   ```

3. `project_root` parameter: **required** (no default). If None, raise ValueError early.
4. Add to `SynthesisResult`:
   - `validated_count: int` — entries that were validated
   - `stale_filtered: int` — entries excluded due to low confidence
5. Update `__main__.py`:
   - Add `--project-root` argument (default: auto-detect from target_docs parent or memory_dir parent)
   - Add `--no-validate` flag to skip validation
   - Add `--import-stability` flag for one-shot migration from stability.jsonl to metadata.db (idempotent, guarded by migration_version)

**Tests** (update `tests/test_synthesize.py` + new `tests/test_validator.py`):
- `test_validator.py`:
  - validate_and_filter_entries with all-valid citations → all entries pass
  - validate_and_filter_entries with broken citation → stale entries filtered
  - validate_and_filter_entries wraps in transaction (simulate crash → rollback)
  - validate_and_filter_entries with no citations → entries keep base confidence, pass through
- `test_synthesize.py`:
  - Synthesis with validation: stale entries filtered
  - Synthesis with `validate=False`: behaves like Phase 0.5
  - Synthesis result includes validated_count and stale_filtered
  - Full end-to-end: auto-memory with stale citation → not promoted
  - All existing 50 tests still pass unchanged

**Acceptance:** `run_synthesis()` with validate=True filters stale entries via `validator.py`. Orchestrator stays thin. All existing 50 tests still pass.

---

### Task 4: Standalone Validate Skill

**Goal:** `/intermem:validate` command that checks already-promoted entries.

**Implementation:**

1. Add `validate_promoted()` function in `intermem/validator.py`:
   - Scan target docs for lines with `<!-- intermem -->` marker
   - Parse marked entries into pseudo-MemoryEntry objects
   - Extract citations from each marked entry
   - Validate citations against project root
   - Report stale entries
   - Update metadata.db
2. Wire into `__main__.py` as `--validate` mode
3. Update SKILL.md or create new `skills/validate/SKILL.md`
4. Output format: table showing entry, citations, status, confidence

**Tests** (in `tests/test_validator.py`):
- Validate promoted entry with valid citations → reports all green
- Validate promoted entry with stale citation → reports stale with detail
- Missing target doc → graceful skip

**Acceptance:** Can run `/intermem:validate` and see report of promoted entry health.

---

### Task 5: Documentation & Cleanup

**Goal:** Update CLAUDE.md, update SKILL.md, add validator.py to architecture docs.

**Implementation:**

1. Update `CLAUDE.md`:
   - Add metadata.db to state files section
   - Add `citations.py`, `metadata.py`, `validator.py` to architecture section
   - Document hash collision decision (16-char SHA-256, acceptable at <1000 entries)
2. Update `SKILL.md`:
   - Document `--validate` mode
   - Document `--project-root` flag
   - Document `--no-validate` flag
   - Document `--import-stability` flag
3. Clean up temp review files from docs/research/ if needed

**Acceptance:** Documentation reflects Phase 1 capabilities.

---

## File Structure After Phase 1

```
intermem/
  scanner.py          — Parse markdown → MemoryEntry
  stability.py        — Snapshot tracking + scoring
  dedup.py            — Duplicate detection
  promoter.py         — Write to target docs
  pruner.py           — Delete from auto-memory
  journal.py          — Promotion lifecycle log (WAL)
  synthesize.py       — Orchestrate pipeline (thin sequencer)
  citations.py        — Citation extraction/validation/confidence (pure functions)
  metadata.py         — SQLite store for provenance/citations/checks (CRUD only)
  validator.py        — validate_and_filter_entries(), validate_promoted()
  _util.py            — hash_entry(), hash_content(), normalize_content()
  __main__.py         — CLI entry point
```

## Execution Order

Pre-Task 0 (hash centralization) first, then Tasks 1 and 2 in parallel.

```
[Pre-Task 0: _util.py] ──→ [Task 1: metadata.py] ──┐
                            [Task 2: citations.py] ──┤
                                                      ├──→ [Task 3: validator.py + pipeline]
                                                      │         ├──→ [Task 4: validate skill]
                                                      │         └──→ [Task 5: docs]
```

## Test Strategy

- All new tests use `tmp_path` fixture (pytest) — no filesystem side effects
- Existing 50 tests must continue passing unchanged
- New test count: ~30-35 tests across test_metadata.py, test_citations.py, test_validator.py, updated test_synthesize.py
- Run full suite after each task: `uv run pytest tests/ -v`
- Concurrent access test uses `threading` (not multiprocessing) for simplicity

## Design Decisions

- **Hash length (16 chars):** Kept for backward compatibility with stability.jsonl. Collision risk negligible at <1000 entries. Document in CLAUDE.md.
- **Section drift:** Last-write-wins. upsert_entry() always updates section to latest value.
- **Dual state stores:** metadata.db is derived/additive alongside JSONL. No reconciliation needed because metadata.db is rebuilt from synthesis runs. Phase 2 may consolidate.
- **snapshot_count source:** Stored in metadata.db, incremented atomically by upsert_entry(). Used by compute_confidence() without querying stability.jsonl.
- **14-day decay penalty:** Deferred to Phase 2. Phase 1 uses static signals only.

## Rollback

Delete `.intermem/metadata.db`. The Phase 0.5 pipeline (`stability.jsonl` + `promotion-journal.jsonl`) is untouched and continues working. `--no-validate` flag also available.
