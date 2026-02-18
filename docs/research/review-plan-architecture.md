# Architecture Review: intermem Phase 1 Validation Overlay

**Review Date:** 2026-02-17
**Plan:** `/root/projects/Interverse/docs/plans/2026-02-18-intermem-phase1-validation-overlay.md`
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-18-intermem-phase1-validation-overlay.md`
**Existing Code:** `/root/projects/Interverse/plugins/intermem/intermem/`

---

## Summary

The plan adds a validation overlay (SQLite metadata DB + citation extraction + confidence scoring) to the existing intermem synthesis pipeline. Architecture assessment: **GOOD with 3 MUST-FIX issues and 2 recommendations**.

### Critical Issues (MUST FIX)

1. **Bidirectional coupling between metadata.py and stability.py** — `import_from_stability()` creates a dependency cycle
2. **Missing responsibility assignment** — Who owns entry_hash computation? (duplicated in 3 places)
3. **Validation filtering logic lives in orchestrator** — Breaks separation of concerns

### Recommendations

1. **Simplify validation skip path** — `validate=False` should be one-line early return, not scattered conditionals
2. **Extract validator.py for standalone validate skill** — Clearer ownership than dumping in synthesize.py

---

## 1. Boundaries & Coupling

### Current Architecture (Phase 0.5)

The existing pipeline has clean linear flow with clear module boundaries:

```
scanner → stability → dedup → promoter → pruner
           ↑                      ↓
      synthesize (orchestrator) ←─┘
           ↓
        journal (shared state, no business logic)
```

**Responsibilities:**
- `scanner.py` — Parse markdown → MemoryEntry objects
- `stability.py` — Hash entries, track snapshots, score stability
- `dedup.py` — Match entries against target docs
- `promoter.py` — Write to AGENTS.md/CLAUDE.md
- `pruner.py` — Delete from auto-memory
- `journal.py` — WAL-style promotion lifecycle tracking
- `synthesize.py` — Orchestrate, no business logic beyond sequencing
- `_util.py` — Shared normalization function

**Dependency Direction:** All modules import from scanner (MemoryEntry dataclass), none import from each other horizontally. Orchestrator imports everything. Journal is imported by promoter/pruner. **Clean.**

---

### Proposed Architecture (Phase 1)

```
scanner → stability → [citations → metadata] → dedup → promoter → pruner
           ↑              ↓                               ↓
      synthesize (orchestrator + validation filter) ←────┘
           ↓
        journal, metadata (parallel state stores)
```

**New modules:**
- `metadata.py` — SQLite store for entry provenance, citations, checks, confidence
- `citations.py` — Extract/resolve/validate citations, compute confidence

**New coupling introduced:**
- `metadata.py` imports `StabilityStore` (for `import_from_stability()`)
- `synthesize.py` imports `metadata.py` and `citations.py`
- `citations.py` imports `MemoryEntry` from scanner (data-only, acceptable)

---

### Issue 1: Bidirectional Coupling (metadata ↔ stability)

**Problem:** `metadata.py` gains `import_from_stability(stability_store)` method, creating a circular dependency:

```
stability.py defines StabilityStore
metadata.py imports StabilityStore for import_from_stability()
synthesize.py imports both
```

If `stability.py` later needs to query metadata (e.g., "skip entries with low confidence during snapshot recording"), we get a cycle.

**Impact:** Architecture fragility. The migration helper locks the two modules together permanently.

**Root Cause:** Migration is a one-time operation but the dependency is permanent.

**Fix Options:**

**Option A (Recommended):** One-shot migration script, not a method
- Move `import_from_stability()` to `intermem/__main__.py` or `scripts/migrate_to_phase1.py`
- CLI: `uv run python -m intermem --migrate-from-stability`
- Deletes itself after one use (or moves to `scripts/` and is never installed as library code)
- `metadata.py` never imports `StabilityStore`

**Option B:** Adapter pattern
- Create `intermem/migration.py` that imports both stability and metadata
- `MetadataStore` stays pure (no stability imports)
- Migration logic lives in the seam module

**Option C:** Data-only import
- `import_from_stability()` takes `list[dict]` (raw snapshot data), not `StabilityStore` object
- Caller (synthesize.py) does `stability_store.snapshots` and passes the list
- Weakens coupling but still creates a conceptual dependency (metadata "knows about" stability's schema)

**Recommendation:** **Option A**. Migration is a deployment concern, not a runtime concern. Keep library modules decoupled.

---

### Issue 2: entry_hash Computation — Who Owns It?

**Current state:**
- `stability.py` has `_hash_entry(entry: MemoryEntry) -> str` (SHA-256[:16])
- `dedup.py` hashes first line of entry content (SHA-256[:16])
- `promoter.py` has `_hash_content(content: str) -> str` (SHA-256[:16])
- `journal.py` stores `entry_hash` (passed in from promoter)

**Planned addition:**
- `metadata.py` will need `entry_hash` for primary key (plan says "entry_hash PK")

**Problem:** Four modules need the same hash, but the function is private (`_hash_entry`) and duplicated. If hashing logic changes (e.g., switch to SHA-256[:12] to reduce metadata.db size), 3+ files need updates.

**Impact:** Maintenance burden.易错性 (easy to get inconsistent hashes).

**Fix:**

Move to `_util.py`:
```python
def hash_entry(entry: MemoryEntry) -> str:
    """Canonical content hash for an entry (SHA-256 truncated to 16 hex chars)."""
    return hashlib.sha256(entry.content.strip().encode("utf-8")).hexdigest()[:16]

def hash_content(content: str) -> str:
    """Hash raw content string."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16]
```

All modules import from `_util`. `stability.py`, `promoter.py`, `metadata.py` delete their private versions. `dedup.py` switches from ad-hoc hashing to the shared function.

**Acceptance:** Grep for `hashlib.sha256` across intermem/*.py — should only appear in `_util.py`.

---

### Issue 3: Validation Filtering Logic in Orchestrator

**Current plan (Task 3, lines 103-125):**

```python
if validate and stable_entries:
    metadata_store = MetadataStore(...)
    for entry in stable_entries:
        metadata_store.upsert_entry(...)
        citations = extract_citations(entry)
        for citation in citations:
            resolved = resolve_citation(citation, project_root)
            metadata_store.record_citation(...)
            result = validate_citation(citation, project_root)
            metadata_store.record_check(...)
        confidence = compute_confidence(0.5, checks, snapshot_count)
        metadata_store.update_confidence(entry_hash, confidence)

    stale_hashes = {e['entry_hash'] for e in metadata_store.get_stale_entries()}
    stable_entries = [e for e in stable_entries if hash(e) not in stale_hashes]
```

**Problem:** Business logic (citation extraction, validation loop, confidence computation, filtering) lives in the orchestrator. `synthesize.py` is supposed to be a thin sequencer.

**Impact:**
- Orchestrator grows to ~50 LOC of validation logic (23 lines in the plan snippet alone)
- Violates separation of concerns (orchestrator should call `validate_entries()`, not implement it)
- Harder to test validation in isolation
- Harder to reuse validation for standalone `/intermem:validate` skill (Task 4 will duplicate this loop)

**Fix:**

Extract to `citations.py` or new `validator.py`:

```python
# citations.py or validator.py
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
    """Validate citations for entries, update metadata, filter stale entries."""
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

        snapshot_count = # get from metadata or stability
        confidence = compute_confidence(0.5, checks, snapshot_count)
        metadata_store.update_confidence(entry_hash, confidence, status)

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

**Orchestrator becomes:**
```python
# synthesize.py
if validate and stable_entries:
    metadata_store = MetadataStore(intermem_dir / "metadata.db")
    val_result = validate_and_filter_entries(stable_entries, metadata_store, project_root)
    stable_entries = val_result.validated_entries
    validated_count = val_result.validated_count
    stale_filtered = val_result.stale_count
```

**Benefits:**
- Orchestrator stays thin (3 lines instead of 23)
- Validation logic testable in isolation
- Reusable for Task 4 (standalone validate skill)
- Clear responsibility: citations/validator module owns validation, orchestrator owns sequencing

**Where to put it:**
- If `citations.py` is small (<200 LOC), add `validate_and_filter_entries()` there
- If `citations.py` grows large, extract to `validator.py`

**Recommendation:** Start in `citations.py`. If file exceeds 300 LOC, split to `validator.py`.

---

## 2. Dependency Direction

### Current Dependencies (Phase 0.5)

```
scanner (MemoryEntry) ← stability, dedup, promoter, pruner, synthesize
journal ← promoter, pruner, synthesize
_util ← synthesize, pruner
```

**All dependencies point inward toward data structures (scanner) or shared utilities (journal, _util).** No horizontal dependencies between business logic modules. **Excellent.**

---

### Planned Dependencies (Phase 1)

**As written in the plan:**

```
scanner ← citations, metadata, stability, dedup, promoter, pruner, synthesize
journal ← promoter, pruner, synthesize
stability ← metadata (PROBLEM: bidirectional)
metadata ← synthesize
citations ← synthesize
_util ← synthesize, pruner
```

**After fixes (Issue 1, 2, 3):**

```
scanner ← citations, metadata, stability, dedup, promoter, pruner, synthesize
journal ← promoter, pruner, synthesize
_util (hash_entry, hash_content, normalize_content) ← all modules
metadata (pure store, no imports of other intermem modules except scanner/_util)
citations ← synthesize (calls validate_and_filter_entries)
```

**Dependency direction:** Still clean after fixes. All modules import data structures (scanner) or utilities (_util). No cycles.

---

### One Remaining Concern: project_root Parameter Propagation

**New parameter:** `project_root: Path` needed for citation resolution (Task 3).

**Current plan:**
- Add `project_root` to `run_synthesis()` signature
- Pass to `validate_and_filter_entries()` (after extracting that function)
- Add `--project-root` CLI arg in `__main__.py`

**Problem:** This is a new global context that didn't exist before. Phase 0.5 was project-root-agnostic (only needed `memory_dir`, `target_docs`, `intermem_dir`, all relative to some implicit root).

**Impact:** Parameter proliferation. Every function in the validation chain needs `project_root`.

**Mitigation:** This is acceptable. Project root is a legitimate context for path resolution. No cleaner alternative exists (can't auto-detect reliably, can't avoid needing it).

**Validation of fix:** Ensure `project_root` is:
- Required parameter (no default to `Path.cwd()` — that's brittle)
- Validated at entry point (`__main__.py` should check it's an absolute path)
- Used consistently (all `resolve_citation()` calls use the same root)

---

## 3. Responsibility Assignment

### Current Responsibilities (Phase 0.5)

| Module | Responsibility | Clear? |
|--------|---------------|--------|
| scanner | Parse markdown → MemoryEntry | ✓ |
| stability | Track content hashes, score stability | ✓ |
| dedup | Match against target docs | ✓ |
| promoter | Write to AGENTS.md/CLAUDE.md | ✓ |
| pruner | Delete from auto-memory | ✓ |
| journal | Append-only promotion lifecycle log | ✓ |
| synthesize | Orchestrate pipeline, no business logic | ✓ |
| _util | Shared normalization | ✓ |

**All clear.** Each module has a single, well-defined job.

---

### Planned Responsibilities (Phase 1)

| Module | Responsibility | Clear? |
|--------|---------------|--------|
| metadata | SQLite store for entry provenance, citations, checks | ✓ (after Issue 1 fix) |
| citations | Extract citations, resolve paths, validate, compute confidence | ✓ (but needs Issue 3 fix) |
| synthesize | Orchestrate pipeline **+ validation filtering logic** | ✗ (Issue 3) |

**After fixes:**

| Module | Responsibility | Clear? |
|--------|---------------|--------|
| metadata | Pure SQLite store (CRUD only, no domain logic) | ✓ |
| citations | Citation extraction, path resolution, validation, confidence scoring, filtering | ✓ |
| synthesize | Orchestrate pipeline (call modules in sequence) | ✓ |

---

### Missing: Who Manages snapshot_count?

**For confidence scoring:** `compute_confidence()` needs `snapshot_count` (plan line 74: "Stable 5+ snapshots → +0.2").

**Options:**

**Option A:** Pass from orchestrator
- `synthesize.py` has both `stability_store` and `metadata_store`
- After validation, synthesize passes `snapshot_count` from `StabilityScore` objects to `validate_and_filter_entries()`
- Con: Orchestrator needs to correlate entry → snapshot_count

**Option B:** Store in metadata.db
- `metadata.upsert_entry()` already increments `snapshot_count` (plan line 28)
- `compute_confidence()` reads from metadata.db
- Con: Duplicates snapshot_count (stability.jsonl has it implicitly, metadata.db has it explicitly)

**Option C:** Query stability.jsonl from citations module
- `validate_and_filter_entries()` takes `stability_store: StabilityStore`
- Queries `score_entries()` to get snapshot counts
- Con: Creates dependency citations → stability (acceptable if data-only)

**Recommendation:** **Option B** (store in metadata.db). Rationale:
- `snapshot_count` is provenance metadata (fits metadata.db scope)
- Avoids coupling citations → stability
- Duplication is minor (one integer per entry)
- Makes metadata.db self-contained (can compute confidence from metadata alone)

**Implementation detail:** `metadata.upsert_entry()` increments `snapshot_count` on every `last_seen` update. This matches the existing stability snapshot logic (one increment per `record_snapshot()` call).

---

### Issue 4: Standalone Validate Skill Responsibility (Task 4)

**Plan (lines 146-165):**

> Add `validate_promoted()` function in `synthesize.py` or a new `intermem/validator.py`

**Problem:** The plan is uncertain about ownership.

**Analysis:**

`validate_promoted()` needs to:
1. Scan target docs for `<!-- intermem -->` markers
2. Extract citations from marked entries
3. Validate citations
4. Update metadata.db
5. Report stale entries

**Comparison to synthesize pipeline:**
- Steps 2-4 are identical to `validate_and_filter_entries()` (after Issue 3 fix)
- Step 1 is new (scan target docs instead of memory_dir)
- Step 5 is new (reporting instead of filtering)

**Decision:** Extract to `validator.py` (separate from citations.py and synthesize.py). Rationale:
- Scanning target docs is not synthesis (synthesize writes to target docs, doesn't read them)
- Not a pure citation function (involves doc scanning + reporting)
- Deserves its own module for clarity

**Responsibility assignment:**
- `validator.py` owns `validate_promoted()` and `validate_and_filter_entries()`
- `citations.py` owns `extract_citations()`, `resolve_citation()`, `validate_citation()`, `compute_confidence()` (pure functions, no I/O)
- `metadata.py` owns database CRUD
- `synthesize.py` imports `validator.validate_and_filter_entries()`

**File structure after Phase 1:**
```
intermem/
  scanner.py          — Parse markdown
  stability.py        — Snapshot tracking
  dedup.py            — Duplicate detection
  promoter.py         — Write to target docs
  pruner.py           — Delete from auto-memory
  journal.py          — Promotion lifecycle log
  synthesize.py       — Orchestrate synthesis pipeline
  citations.py        — Citation extraction/validation/confidence (pure functions)
  metadata.py         — SQLite store for provenance/citations/checks
  validator.py        — validate_and_filter_entries(), validate_promoted()
  _util.py            — Shared utilities (hash_entry, hash_content, normalize_content)
  __main__.py         — CLI entry point
```

**Benefit:** Clear separation of concerns. Each module has ≤200 LOC and a single responsibility.

---

## 4. Coupling Between SQLite and JSONL State Stores

### Current State Stores (Phase 0.5)

- `stability.jsonl` — Per-snapshot entry hashes (append-only)
- `promotion-journal.jsonl` — Promotion lifecycle (append-only)

**Relationship:** Independent. Journal tracks promotion, stability tracks entry history. No crosstalk.

---

### Planned State Stores (Phase 1)

- `stability.jsonl` — Unchanged
- `promotion-journal.jsonl` — Unchanged
- `metadata.db` — New. Tracks entry provenance, citations, checks, confidence

**Overlap:**

| Data | stability.jsonl | metadata.db |
|------|----------------|-------------|
| entry_hash | ✓ (implicit in entries[].hash) | ✓ (PK) |
| section | ✓ (entries[].section) | ✓ (memory_entries.section) |
| snapshot_count | ✓ (implicit, count appearances) | ✓ (memory_entries.snapshot_count) |
| first_seen | ✗ | ✓ |
| last_seen | ✗ | ✓ |
| content_preview | ✓ (entries[].preview, 80 chars) | ✓ (memory_entries.content_preview) |

**Analysis:** Significant duplication. `metadata.db` contains all info from `stability.jsonl` plus citations/checks.

**Is this a problem?**

**No, for these reasons:**

1. **Different access patterns:**
   - `stability.jsonl` is append-only, read sequentially for scoring (need historical snapshots)
   - `metadata.db` is mutable, read by entry_hash (need latest state per entry)

2. **Different lifecycles:**
   - `stability.jsonl` is immutable history (snapshots never deleted)
   - `metadata.db` is current state (can be rebuilt from stability.jsonl if lost)

3. **Migration safety:**
   - Keeping `stability.jsonl` unchanged means Phase 1 is reversible (delete metadata.db, revert to Phase 0.5)

4. **No write-write conflicts:**
   - `stability.jsonl` written by `record_snapshot()`
   - `metadata.db` written by `validate_and_filter_entries()`
   - Both happen in sequence during synthesis, no concurrency issues

**Coupling risk:** Low. The two stores share a data model (entry_hash, section) but have no code dependencies. If `metadata.db` is deleted, it can be rebuilt from `stability.jsonl` via `import_from_stability()` (which should be a one-shot script, not a runtime method — see Issue 1).

**Recommendation:** Accept the duplication. The benefit of keeping Phase 0.5 state intact (rollback safety) outweighs the cost of duplicating a few fields.

---

### Forward Compatibility: Phase 2+ Migration to Pure SQLite?

**Potential future:** Phase 2 migrates `stability.jsonl` and `promotion-journal.jsonl` into `metadata.db`, consolidating to a single state store.

**Would the Phase 1 design block this?**

**No.** Current plan keeps metadata.db as an additive layer. Phase 2 can:
1. Add `snapshots` table to metadata.db (migrate stability.jsonl)
2. Add `promotion_journal` table to metadata.db (migrate promotion-journal.jsonl)
3. Update modules to read from SQLite instead of JSONL
4. Deprecate JSONL files

**Phase 1 does NOT lock us into JSONL forever.** The parallel-store design is a safe intermediate step.

---

## 5. Simplicity & YAGNI

### Abstraction Review

**New abstractions introduced:**

1. `MetadataStore` class (metadata.py)
2. `Citation`, `CheckResult` dataclasses (citations.py)
3. `validate_and_filter_entries()` function (validator.py, after Issue 3 fix)
4. `validate_promoted()` function (validator.py, Task 4)
5. `compute_confidence()` function (citations.py)

**Are these necessary?**

| Abstraction | Justified? | Reason |
|-------------|-----------|--------|
| MetadataStore | ✓ | Encapsulates SQLite, provides CRUD API, matches existing pattern (StabilityStore, PromotionJournal) |
| Citation, CheckResult | ✓ | Type safety for complex data (3+ fields each) |
| validate_and_filter_entries | ✓ | Reused by synthesis pipeline and standalone validate skill |
| validate_promoted | ✓ | Standalone skill requirement (Task 4) |
| compute_confidence | ✓ | Complex business logic (6+ signals, clamp to [0,1]) |

**All justified.** No speculative abstractions.

---

### Complexity Hot Spots

**1. Citation Extraction Regexes (citations.py)**

Plan (lines 61-64):
```
- Regex for backtick-quoted paths: `[^\s`]+/[^\s`]+` (must contain /)
- Regex for markdown link paths: [text](path/to/file)
- Regex for absolute paths: /root/projects/... or similar
- Filter out known non-path patterns: --flag, http://, VAR=value
```

**Analysis:** Four regex patterns + negative filter. Could get brittle (false positives/negatives).

**Recommendation:** Start with the simplest regex that works for real Interverse auto-memory. Add patterns incrementally as false negatives appear in testing. Do NOT try to handle every edge case in Phase 1.

**Simplification:** Combine backtick and markdown patterns into one:

```python
# Match: `path/to/file` or [text](path/to/file)
PATH_RE = re.compile(r'`([^\s`]+/[^\s`]+)`|\]\(([^)]+/[^)]+)\)')
```

Test against real auto-memory corpus (Interverse, ethics-gradient, other projects). If <90% recall, add absolute path pattern. Otherwise, skip it (YAGNI).

---

**2. Confidence Scoring Formula (citations.py)**

Plan (lines 74-81):
```python
base: 0.5
+0.3: cited file exists
+0.3: cited module exists
-0.4: cited file deleted
-0.4: cited module gone
+0.2: stable 5+ snapshots
-0.1: not validated in 14+ days
clamp [0.0, 1.0]
```

**Analysis:** 7 magic numbers. How were these chosen? What's the rationale for +0.3 vs +0.2?

**Issue:** No justification in the plan. These numbers should be derived from:
- Empirical testing (what thresholds separate good/stale entries in practice?)
- User acceptance (what confidence score feels "right" for promotion?)

**Recommendation for Phase 1:** Use simplified scoring:

```python
base = 0.5
delta_sum = sum(check.confidence_delta for check in checks)
if snapshot_count >= 5:
    delta_sum += 0.2
confidence = max(0.0, min(1.0, base + delta_sum))
```

Where `confidence_delta` is:
- +0.3 for valid citation
- -0.4 for broken citation
- 0.0 for unchecked

**Drop the "not validated in 14+ days" penalty for Phase 1.** It's not in the PRD success criteria and adds cron/revalidation complexity. Add in Phase 2 if stale-but-not-broken entries become a problem.

**Rationale:** Start with the minimum viable scoring. Tune after observing real data.

---

**3. Path Safety (citations.py)**

Plan (lines 66-69):
```python
resolved = project_root / citation.value
if not str(resolved.resolve()).startswith(str(project_root) + "/"):
    return None  # outside boundary
```

**Analysis:** This is the interkasten pattern (good). One subtlety: `pathlib.Path.resolve()` follows symlinks. Is that desired?

**Scenarios:**
- Symlink inside project pointing outside → `resolve()` escapes boundary → rejected ✓
- Symlink outside project pointing inside → Can't cite it (citation.value won't match) → N/A
- `../` path traversal → `resolve()` normalizes, then startswith check catches it ✓

**Recommendation:** Keep as-is. Document that symlinks are dereferenced for safety checks.

**Simplification opportunity:** Use `Path.is_relative_to()` (Python 3.9+):

```python
resolved = (project_root / citation.value).resolve()
if not resolved.is_relative_to(project_root):
    return None
```

Cleaner than string prefix check. Same safety guarantees.

---

### Unnecessary Complexity: Migration Helper in metadata.py

**Already covered in Issue 1.** To reiterate: `import_from_stability()` is over-engineering. Make it a one-shot script or delete it (users can manually populate metadata.db by running synthesis once).

---

## 6. Pattern Alignment

### Existing Patterns in intermem

1. **Append-only JSONL stores** — stability.jsonl, promotion-journal.jsonl
2. **WAL-style lifecycle tracking** — journal.py (pending → committed → pruned)
3. **Idempotent initialization** — `CREATE TABLE IF NOT EXISTS`, `Path.mkdir(parents=True, exist_ok=True)`
4. **Content hashing for identity** — SHA-256[:16] for entry_hash
5. **Dataclasses for structured data** — MemoryEntry, StabilityScore, JournalEntry, DedupResult

**Does Phase 1 follow these patterns?**

| Pattern | Phase 1 Adherence | Notes |
|---------|------------------|-------|
| Append-only JSONL | Partially | New state is SQLite, not JSONL (acceptable, PRD justifies it) |
| WAL-style lifecycle | ✓ | citation_checks table is append-only audit log |
| Idempotent init | ✓ | `ensure_schema()` is `CREATE TABLE IF NOT EXISTS` |
| Content hashing | ✓ | Reuses SHA-256[:16] (will after Issue 2 fix) |
| Dataclasses | ✓ | Citation, CheckResult |

**Alignment: Good.** The shift to SQLite is intentional (PRD lists stdlib-only, concurrent-safe as requirements). All other patterns maintained.

---

### Anti-Patterns Detected

**None in the core design.** The issues found (1-3) are fixable and don't reflect anti-patterns (god modules, leaky abstractions, etc.). The architecture is fundamentally sound.

---

## 7. Test Strategy Assessment

**Plan section (lines 201-207):**

```
- All new tests use `tmp_path` fixture (pytest) — no filesystem side effects
- Existing 50 tests must continue passing unchanged
- New test count: ~25-30 tests across test_metadata.py, test_citations.py, updated test_synthesize.py
- Run full suite after each task: `uv run pytest tests/ -v`
```

**Analysis:**

**Strengths:**
- `tmp_path` fixture prevents test pollution ✓
- Regression requirement (existing 50 tests pass) ✓
- Per-task testing (run suite after each task) ✓

**Gaps:**

1. **No integration test for the full validation pipeline** — Individual unit tests for metadata, citations, synthesize, but no end-to-end test that runs synthesis with validate=True and verifies stale entries are filtered.

2. **No test for `validate_promoted()` (Task 4 standalone skill)** — Plan says "Tests: Validate promoted entry with valid citations → reports all green" but doesn't specify where this test lives or how it integrates with existing test suite.

3. **No test for concurrent access to metadata.db** — Plan says "Test: Concurrent access with busy_timeout" (line 44) but doesn't specify how to simulate concurrency (multiple processes? threads? pytest-xdist?).

4. **No test for migration from stability.jsonl** — If `import_from_stability()` is kept as a method (not recommended — see Issue 1), needs a test. If converted to a script, needs a manual test checklist.

5. **No test for rollback** — PRD says "Rollback: Deleting `.intermem/metadata.db` restores Phase 0.5 behavior exactly" (PRD line 130). Should have a test: run synthesis with validate=True, delete metadata.db, run synthesis again with validate=False, verify identical output.

**Recommendations:**

**Add to test plan:**

**test_synthesize.py:**
```python
def test_full_synthesis_with_validation_filters_stale(tmp_path):
    """End-to-end: synthesis with validation excludes stale entries."""
    # Setup: auto-memory with entry citing deleted file
    # Run synthesis with validate=True
    # Assert: entry not promoted
    # Assert: SynthesisResult.stale_filtered == 1

def test_synthesis_validate_false_skips_filtering(tmp_path):
    """Synthesis with validate=False behaves like Phase 0.5."""
    # Same setup as above
    # Run synthesis with validate=False
    # Assert: stale entry IS promoted (no filtering)
    # Assert: SynthesisResult.stale_filtered == 0
```

**test_validator.py (new file):**
```python
def test_validate_promoted_reports_stale_citations(tmp_path):
    """Standalone validate skill detects stale entries in AGENTS.md."""
    # Setup: AGENTS.md with entry citing deleted file, marked with <!-- intermem -->
    # Run validate_promoted()
    # Assert: report includes entry_hash, citation, status=broken

def test_validate_promoted_all_valid(tmp_path):
    """Standalone validate skill reports all green when citations valid."""
    # Setup: AGENTS.md with entry citing existing file
    # Run validate_promoted()
    # Assert: report shows status=valid
```

**test_metadata.py:**
```python
def test_concurrent_writes_do_not_fail(tmp_path):
    """Two processes writing to metadata.db concurrently, both succeed."""
    # Use multiprocessing.Process or subprocess to spawn 2 writers
    # Both call metadata_store.upsert_entry() on different entries
    # Assert: both entries present in DB after both processes exit
    # Assert: no SQLITE_BUSY errors in logs
```

**Manual test checklist (in AGENTS.md or plan):**
```
Rollback test (manual):
1. Create test project with auto-memory
2. Run synthesis with --validate → metadata.db created
3. Verify promotion happens
4. Delete .intermem/metadata.db
5. Run synthesis with --no-validate
6. Verify promotion happens identically (no crash, no metadata queries)
```

---

## 8. Open Questions / Ambiguities

### Q1: What happens if project_root is None?

**Plan (line 73):**
> Return ('unchecked', 0.0, 'Cannot determine project root') if project_root is None

**But Task 3 (line 126):**
> Add `project_root` parameter to `run_synthesis()` (needed for citation resolution)

**Ambiguity:** Is `project_root` optional or required?

**Recommendation:** Make it required. If project root can't be determined, synthesis should fail early with a clear error message, not silently mark everything "unchecked."

**CLI design (Task 3, line 131):**
```python
parser.add_argument("--project-root", default=auto_detect_from_target_docs_parent)
```

**Auto-detect logic:**
```python
if target_docs:
    project_root = target_docs[0].parent
else:
    project_root = memory_dir.parent
```

**Failure mode:** If neither `target_docs` nor `memory_dir` is under a project root (e.g., running on `/tmp/test-memory`), should fail with:
```
Error: Cannot determine project root. Provide --project-root explicitly.
```

---

### Q2: How is snapshot_count obtained during validation?

**Mentioned in Issue "Missing: Who Manages snapshot_count?"**

**Plan (line 119):**
```python
confidence = compute_confidence(0.5, checks, snapshot_count)
```

**But where does `snapshot_count` come from?**

**Option 1 (Recommended in Issue section):** Stored in metadata.db, incremented by `upsert_entry()`.

**Option 2:** Query stability_store inside `validate_and_filter_entries()`.

**Option 3:** Pass from orchestrator (synthesize.py correlates StabilityScore.snapshot_count → entry_hash).

**Recommendation:** Clarify in the plan. My preference: Option 1 (store in metadata.db).

---

### Q3: What is the `status` field in `memory_entries` table?

**Plan (line 22):**
> memory_entries — entry provenance (entry_hash PK, content_preview, section, source_file, first_seen, last_seen, snapshot_count, confidence, **status**)

**No definition provided.** Is it:
- Promotion status (pending/committed/pruned)? No, that's in promotion-journal.jsonl.
- Validation status (unchecked/valid/stale)? Maybe.
- Lifecycle status (active/deleted)? Unclear.

**Recommendation:** Define in Task 1 or remove if unused in Phase 1.

**Suggested definition (if validation status):**
```sql
status TEXT CHECK(status IN ('active', 'stale', 'deleted'))
```
- `active` — confidence >= 0.3
- `stale` — confidence < 0.3
- `deleted` — entry no longer appears in auto-memory (detected during next scan)

---

### Q4: How does `get_stale_entries()` work?

**Plan (line 32):**
> `get_stale_entries() -> list[dict]` — entries with confidence < 0.3

**Returns `list[dict]`. What keys?**

**Recommendation:** Define the schema:

```python
def get_stale_entries(self) -> list[dict]:
    """Return entries with confidence < 0.3.

    Returns:
        List of dicts with keys: entry_hash, section, confidence, content_preview
    """
    cursor = self.conn.execute(
        "SELECT entry_hash, section, confidence, content_preview "
        "FROM memory_entries WHERE confidence < 0.3"
    )
    return [dict(row) for row in cursor.fetchall()]
```

**Acceptance test:**
```python
stale = metadata_store.get_stale_entries()
assert stale[0].keys() == {'entry_hash', 'section', 'confidence', 'content_preview'}
```

---

## 9. Execution Order Assessment

**Plan (lines 188-199):**

```
[Task 1: metadata.py] ──┐
                         ├──→ [Task 3: pipeline] ──→ [Task 4: validate skill]
[Task 2: citations.py] ─┘                     └──→ [Task 5: docs]
```

**Analysis:**

**Correct:** Tasks 1 and 2 are independent, can run in parallel.

**Incorrect:** Task 5 (docs) depends on Task 3, NOT on Task 4. You can document the `--validate` flag before implementing `/intermem:validate` skill.

**Revised execution order:**

```
[Task 1: metadata.py] ──┐
                         ├──→ [Task 3: pipeline] ──→ [Task 5: docs]
[Task 2: citations.py] ─┘          ↓
                                [Task 4: validate skill] ──→ [Update SKILL.md]
```

**Rationale:**
- Task 4 can be implemented after Task 5 (docs) because it's a separate skill
- Task 5 documents `--validate` mode in synthesis, which is Task 3
- Task 4 adds a new skill, which updates SKILL.md separately

**Low-risk reordering:** Task 4 and Task 5 can be done in any order. Both can start after Task 3 completes.

---

## 10. Summary of Required Changes

### MUST FIX Before Implementation

**Issue 1: Remove metadata → stability coupling**
- Move `import_from_stability()` to a one-shot migration script (scripts/migrate_to_phase1.py or __main__.py --migrate)
- `metadata.py` should NOT import `StabilityStore`

**Issue 2: Centralize entry_hash computation**
- Move `_hash_entry()` and `_hash_content()` to `_util.py` as public functions
- All modules import from _util (stability, metadata, citations, promoter, pruner, dedup)

**Issue 3: Extract validation logic from orchestrator**
- Create `validate_and_filter_entries()` in citations.py or validator.py
- synthesize.py calls it (3 lines), doesn't implement it (23 lines)

---

### SHOULD FIX (Recommended)

**Recommendation 1: Extract validator.py**
- Move `validate_and_filter_entries()` and `validate_promoted()` to validator.py
- Keep citations.py as pure functions (no I/O, no metadata.db interaction)

**Recommendation 2: Simplify confidence scoring**
- Drop "not validated in 14+ days" penalty for Phase 1 (add in Phase 2 if needed)
- Use base=0.5 + sum(deltas) + snapshot_bonus, clamped to [0,1]

**Recommendation 3: Simplify citation extraction regexes**
- Start with backtick + markdown link patterns only
- Test against real auto-memory corpus
- Add absolute path pattern only if <90% recall

**Recommendation 4: Use `Path.is_relative_to()` for safety check**
- Cleaner than string prefix matching
- Same security guarantees

---

### SHOULD CLARIFY (Ambiguities)

1. Is `project_root` required or optional? (Make it required)
2. Where does `snapshot_count` come from during validation? (Store in metadata.db)
3. What is `status` field in `memory_entries` table? (Define or remove)
4. What keys does `get_stale_entries()` return? (Define schema)

---

## 11. Final Verdict

**Architecture Quality: GOOD (7/10)**

**Strengths:**
- Clean module boundaries (after fixes)
- Minimal coupling (after Issue 1 fix)
- Clear responsibility assignment (after Issue 3 fix)
- Reversible design (Phase 0.5 state untouched)
- No anti-patterns detected
- Test strategy is solid (with recommended additions)

**Weaknesses:**
- Bidirectional coupling in original plan (fixable)
- Duplicated hash functions (fixable)
- Orchestrator doing business logic (fixable)
- Some ambiguities in schema/API design (clarify in Task 1)

**Risk Level: LOW** (after fixes applied)

**Recommendation: APPROVE with required fixes (Issues 1-3) and clarifications (Q1-Q4).**

---

## Appendix: Dependency Graph (After Fixes)

```
                    ┌─────────────┐
                    │   scanner   │ (MemoryEntry dataclass)
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
    │stability│       │ dedup   │      │citations│
    └────┬────┘       └────┬────┘      └────┬────┘
         │                 │                 │
         │                 │            ┌────▼────┐
         │                 │            │metadata │ (SQLite)
         │                 │            └────┬────┘
         │                 │                 │
         └────────┬────────┴─────────────────┘
                  │
             ┌────▼────┐
             │validator│ (validate_and_filter_entries)
             └────┬────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼────┐       ┌────▼────┐
    │promoter │       │ pruner  │
    └────┬────┘       └────┬────┘
         │                 │
         └────────┬────────┘
                  │
             ┌────▼────┐
             │ journal │ (WAL)
             └────┬────┘
                  │
             ┌────▼────┐
             │synthesize│ (orchestrator)
             └─────────┘
                  │
             ┌────▼────┐
             │__main__ │ (CLI)
             └─────────┘

         ┌─────────────┐
         │   _util     │ (hash_entry, hash_content, normalize_content)
         └──────┬──────┘
                │
         (imported by all modules)
```

**Legend:**
- Arrows point from importer to imported
- Dotted lines indicate data-only dependencies (dataclasses)
- No cycles
- All business logic modules converge on synthesize (orchestrator)
- _util is a shared foundation layer

**Complexity:** 10 modules, linear flow, O(n) dependencies. Excellent for a 800-line feature addition.
