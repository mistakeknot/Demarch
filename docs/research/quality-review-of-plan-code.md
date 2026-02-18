# Quality Review: intermem Memory Synthesis Implementation Plan

**File reviewed:** `intermem/docs/plans/2026-02-17-intermem-memory-synthesis.md`
**Date:** 2026-02-17
**Reviewer:** Flux-drive Quality & Style Reviewer
**Languages in scope:** Python 3.11+, TOML

---

## Executive Summary

The plan is well-structured and the TDD discipline is genuine — the RED step is explicit, the tests are not trivial stubs, and the implementation follows from them. The Python idioms are mostly correct. There are, however, several correctness bugs, false-positive test risks, and design gaps that would surface during implementation. This review categorizes each finding by severity.

---

## 1. Test Quality

### 1.1 False-Positive Risk in test_stable_after_three_snapshots (MEDIUM)

**Location:** `tests/test_stability.py::test_stable_after_three_snapshots`

```python
def test_stable_after_three_snapshots(tmp_path):
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    entries = [_entry("- Fact A")]
    for _ in range(3):
        record_snapshot(store, entries)
    scores = score_entries(store, entries)
    assert scores[0].score == "stable"
```

The test passes `entries` directly to `score_entries` using the same `store` instance that `record_snapshot` wrote to. A naive implementation that counts how many times the hash appears in `store._snapshots` (which is accumulated in-memory during the same test run) will pass. But an implementation that reloads from disk each time would also pass, and the persistence test covers that separately. The gap: this test does NOT verify that the hash counting uses the correct window. An implementation that counts all snapshots ever recorded (including ones from before the entry existed) would also pass and be subtly wrong in `test_new_entry_scores_recent`. That test does cover the gap, so overall coverage is adequate — but the ordering dependency between tests is implicit.

**Recommendation:** Add a comment in `test_stable_after_three_snapshots` noting that it tests the minimum count boundary. Also add a test for `count == 2` entries scoring "recent" (the 2-snapshot case is unspecified and the implementation defaults to "recent" for `count < 3` that isn't `count == 1 with >= 2 snapshots`).

### 1.2 The test_volatile_when_content_changes Test Has a Logic Gap (HIGH)

**Location:** `tests/test_stability.py::test_volatile_when_content_changes`

```python
def test_volatile_when_content_changes(tmp_path):
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    entries_v1 = [_entry("- Fact A version 1")]
    entries_v2 = [_entry("- Fact A version 2")]
    record_snapshot(store, entries_v1)
    record_snapshot(store, entries_v1)
    record_snapshot(store, entries_v2)  # Changed!
    scores = score_entries(store, entries_v2)
    assert scores[0].score == "volatile"
```

The `score_entries` implementation scores an entry as "volatile" when `count == 1` AND `len(store.snapshots) >= 2`. But this condition is met by ANY genuinely new entry that appears for the first time in the second or later snapshot. There is no semantic distinction between "new fact added" and "existing fact modified" — both produce `count == 1` in the latest snapshot.

Looking at `test_new_entry_scores_recent` (Task 3), the `_entry("- Brand new")` entry also has `count == 1` in a store with 3 snapshots. But the implementation marks it "volatile" under the condition `count == 1 and len(store.snapshots) >= 2`. This means `test_new_entry_scores_recent` would FAIL with the provided implementation — `scores[1].score` would be "volatile" not "recent".

This is a genuine correctness bug in the implementation that is caught by the test suite, which is the intent of TDD. However, neither the tests nor the implementation resolve the ambiguity: a brand-new entry and a modified entry are indistinguishable by hash alone. The plan should either:
- Accept that new entries and changed entries both score "volatile" until stable (and fix `test_new_entry_scores_recent` to expect "volatile"), or
- Track entries by a stable identifier (e.g., section + position) in addition to content hash.

The current design cannot pass both `test_volatile_when_content_changes` (expects "volatile") and `test_new_entry_scores_recent` (expects "recent" for a brand-new entry) simultaneously.

**Recommendation:** This is the most significant correctness gap in the plan. Resolve the ambiguity before implementation by choosing one of the following approaches:
- Score all `count == 1, snapshots >= 2` entries as "volatile" (simpler; fix the test expectation for new entries)
- Add a section+ordinal key to the stability store so new entries can be detected by absence of any prior key, not just hash mismatch

### 1.3 False-Positive in test_exact_duplicate_detected (LOW)

**Location:** `tests/test_dedup.py::test_exact_duplicate_detected`

```python
def test_exact_duplicate_detected(tmp_path):
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Testing\n- Always use pytest with -v flag\n")
    entry = _entry("- Always use pytest with -v flag")
    results = check_duplicates([entry], [agents])
    assert results[0].status == "exact_duplicate"
```

The dedup implementation normalizes text by stripping the bullet `- ` prefix before hashing. The entry content is `"- Always use pytest with -v flag"`, which normalizes to `"always use pytest with -v flag"`. The line from the file is `"- Always use pytest with -v flag"`, which also normalizes to `"always use pytest with -v flag"`. This will pass.

However, the test does not verify that the hash comparison is case-insensitive. An implementation that hashes without lowercasing would also pass this specific test. The `_normalize` function lowercases, but a test that verifies case-insensitive matching (e.g., entry in all-caps vs. lowercase in file) would confirm the normalization is working.

**Recommendation:** Add a test with `entry = _entry("- ALWAYS USE PYTEST WITH -V FLAG")` against a lowercase target to verify case normalization is actually exercised.

### 1.4 Missing Edge Cases in Scanner Tests (MEDIUM)

**Location:** `tests/test_scanner.py`

The scanner tests do not cover:
- A file that is empty (`""`): `scan_memory_dir` calls `text.splitlines()` which returns `[]`, so `_parse_file` returns `[]`. The `total_lines` would be 0. This should work but is untested.
- A file with only a top-level `# Heading` and no `##` sections or bullets: the `source_file` fallback section name (`filename.removesuffix(".md")`) is used. Untested.
- A bullet point that itself contains nested sub-bullets (indented `  - sub-item`): the continuation-line logic would accumulate sub-bullets into the parent entry, which is likely correct but untested.
- Files with CRLF line endings (`\r\n`): `splitlines()` handles these, but the content field will have `\r` stripped from line ends inside multi-line entries assembled via `"\n".join(lines)`. Untested — and the `\r` may or may not matter for hashing.
- A `.md` file that contains only headings and no bullet entries: returns empty entry list. Untested.

**Recommendation:** Add at minimum an empty-file test and a headings-only test.

### 1.5 test_prune_dry_run Does Not Assert No Backup Created (LOW)

**Location:** `tests/test_pruner.py::test_prune_dry_run`

```python
def test_prune_dry_run(tmp_path):
    ...
    result = prune_promoted([entry], memory_dir, journal, dry_run=True)
    remaining = (memory_dir / "MEMORY.md").read_text()
    assert "- Fact B" in remaining
    assert result.lines_removed > 0
    assert result.dry_run is True
```

The test correctly asserts the file is unchanged. But it does not assert that the `.bak` backup was NOT created during dry-run. The implementation wraps the backup creation in `if not dry_run:`, so it would pass, but explicitly asserting `assert not (memory_dir / "MEMORY.md.bak").exists()` would prevent a regression where someone moves backup creation outside the dry-run guard.

### 1.6 Integration Tests Lack Assertion on Memory File After Pruning (MEDIUM)

**Location:** `tests/test_synthesize.py::test_pruning_after_promotion`

```python
def test_pruning_after_promotion(tmp_path):
    ...
    memory_content = (env["memory_dir"] / "MEMORY.md").read_text()
    # Promoted entries should be removed from memory
    assert result.promoted_count > 0
    assert result.pruned_count > 0
```

The variable `memory_content` is read but never asserted on. This is a dead variable — the test passes even if the memory file is completely unchanged, as long as `result.pruned_count > 0` (which comes from the `PruneResult.lines_removed` count, a computed integer, not a file verification). The test would pass even if the pruner had a bug that reported lines_removed but did not actually write the file.

**Recommendation:** Add `assert "- Stable fact" not in memory_content` (and similarly for `- Other fact`).

---

## 2. Naming Conventions

### 2.1 `_hash_content` Duplicated Across Modules (MEDIUM)

The function `_hash_content(content: str) -> str` with identical body appears in both `promoter.py` and `pruner.py`. This is a copy-paste violation that creates a hash-mismatch risk if one copy is ever changed.

**Fix:** Extract to a shared internal utility, either in `scanner.py` (since `MemoryEntry` is the source type) or in a new `lib/_util.py`. The existing `_hash_entry` in `stability.py` performs the same computation but on a `MemoryEntry` object rather than a string. All three should use one source of truth.

```python
# In lib/_util.py or lib/scanner.py
def hash_content(content: str) -> str:
    """Compute a short content hash for an entry."""
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]
```

### 2.2 `StabilityScore.score` Field Should Use a Literal Type (LOW)

```python
@dataclass
class StabilityScore:
    entry: MemoryEntry
    score: str  # "stable", "recent", "volatile"
    snapshot_count: int
```

The `score` field is a plain `str` but is semantically an enum. A typo in a string comparison (`score == "volatilr"`) would silently fail. Use `typing.Literal`:

```python
from typing import Literal
ScoreLabel = Literal["stable", "recent", "volatile"]

@dataclass
class StabilityScore:
    entry: MemoryEntry
    score: ScoreLabel
    snapshot_count: int
```

The same applies to `DedupResult.status` (`"novel"`, `"exact_duplicate"`, `"fuzzy_duplicate"`) and `JournalEntry.status` (`"pending"`, `"committed"`, `"pruned"`).

### 2.3 `_find_memory_dir` Has Misleading Dead Code (LOW)

**Location:** `lib/__main__.py`

```python
encoded = str(project_dir).replace("/", "-")
if encoded.startswith("-"):
    pass  # Already has leading dash from root /
else:
    encoded = "-" + encoded
```

The `else` branch adds a leading `-` only when `encoded` does NOT already start with `-`. But `str(project_dir)` for an absolute path always starts with `/`, which becomes `-` after the replace. The `else` branch is dead code for all absolute paths. On a relative path, it would add a `-` prefix, but `project_dir = args.project_dir.resolve()` ensures the path is always absolute. The `else` branch will never execute.

**Fix:** Remove the conditional entirely:

```python
encoded = str(project_dir).replace("/", "-")
# Always has a leading "-" because resolve() returns an absolute path starting with "/"
```

Or use the pattern Claude Code actually uses (which strips the leading slash first):

```python
encoded = "-" + str(project_dir).lstrip("/").replace("/", "-")
```

---

## 3. Error Handling

### 3.1 `StabilityStore._load` Does Not Handle Malformed JSONL (HIGH)

```python
def _load(self) -> None:
    if self.path.exists():
        for line in self.path.read_text().splitlines():
            if line.strip():
                self._snapshots.append(json.loads(line))
```

If the `.intermem/stability.jsonl` file is partially written (e.g., the process was killed mid-write), `json.loads(line)` will raise `json.JSONDecodeError` on the corrupted line. This propagates as an unhandled exception from `StabilityStore.__init__`, crashing the entire synthesis run.

**Fix:**

```python
def _load(self) -> None:
    if not self.path.exists():
        return
    for line in self.path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            self._snapshots.append(json.loads(line))
        except json.JSONDecodeError:
            # Corrupted line — skip and continue loading remaining snapshots
            continue
```

The same issue applies to `PromotionJournal._load`.

### 3.2 `PromotionJournal.mark_committed` and `mark_pruned` Raise Unguarded `KeyError` (HIGH)

```python
def mark_committed(self, entry_hash: str) -> None:
    entry = self._entries[entry_hash]  # KeyError if not found
```

If `mark_committed` is called with a hash that was never recorded via `record_pending` (e.g., due to a bug in the promoter or a hash mismatch), a bare `KeyError` propagates with no context. In the pruner:

```python
try:
    journal.mark_pruned(h)
except KeyError:
    pass  # Entry might have a different hash in journal
```

The pruner silently swallows the `KeyError`. This is the right defensive move given the hash is recomputed differently, but it exposes the underlying problem: the `_hash_content` function in `pruner.py` and the `_hash_content` function in `promoter.py` compute hashes from `content.strip()`, while the journal stores entries keyed by hash. If anything whitespace-normalizes differently, the journal entry is irrecoverably lost. The silent `pass` hides this.

**Fix:** At minimum, raise a more informative error from `mark_committed`:

```python
def mark_committed(self, entry_hash: str) -> None:
    if entry_hash not in self._entries:
        raise KeyError(f"Journal has no pending entry for hash {entry_hash!r}")
    entry = self._entries[entry_hash]
    ...
```

And add explicit hash alignment between `promoter.py` and `pruner.py` (see naming item 2.1).

### 3.3 `scan_memory_dir` Does Not Handle Unreadable Files (MEDIUM)

```python
for md_file in md_files:
    text = md_file.read_text()
```

`read_text()` with no `encoding` argument uses the system default encoding, which may fail on files with non-UTF-8 content (a realistic scenario for memory files that record code snippets). An `UnicodeDecodeError` would crash the entire scan.

**Fix:**

```python
text = md_file.read_text(encoding="utf-8", errors="replace")
```

### 3.4 `promote_entries` Writes Target File Inside a Section Loop (MEDIUM)

**Location:** `promoter.py`

```python
for section_name, section_entries in by_section.items():
    # ... modify content string ...
    target_path.write_text(content)  # Inside the loop
    # ... journal.mark_committed ...
```

The target file is written once per section. If there are two sections to add and the process crashes between the first and second write, the journal records both as "committed" but the second was never written. The second write also re-reads the `content` variable (not the file), which means the in-memory `content` string is correct — but the loop structure obscures this. The actual WAL protection is at the journal level, not at the file-write level.

More immediately: if `target_path.write_text(content)` raises (e.g., disk full), the journal entry was already marked committed but the write failed. The journal state is now wrong.

**Fix:** Move `target_path.write_text(content)` outside the loop and call `journal.mark_committed` only after the write succeeds:

```python
for section_name, section_entries in by_section.items():
    for entry in section_entries:
        h = _hash_content(entry.content)
        journal.record_pending(h, target_path.name, section_name, entry.content)
    # ... modify content string in-memory ...

# Single write after all sections are processed
target_path.write_text(content)

# Only mark committed after successful write
for section_name, section_entries in by_section.items():
    for entry in section_entries:
        h = _hash_content(entry.content)
        journal.mark_committed(h)
```

### 3.5 Pruner's `KeyError` Swallow Masks Hash Divergence (MEDIUM)

Already noted in 3.2. The `except KeyError: pass` pattern in `pruner.py` means a corrupted or mismatched journal silently results in entries being removed from auto-memory but not marked pruned in the journal. On next run, `get_incomplete()` will still return them as "committed" (not "pruned"), and the promoter might attempt to re-promote them into the target doc.

---

## 4. Python Idioms

### 4.1 `pyproject.toml` Is Missing `[tool.hatch.build.targets.wheel]` Package Discovery (HIGH)

```toml
[project]
name = "intermem"
version = "0.1.0"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The library code lives in `plugins/intermem/lib/`, but the package is named `intermem`. Hatchling's default package discovery looks for a directory named `intermem` at the project root (i.e., `plugins/intermem/intermem/`), not `plugins/intermem/lib/`. Without explicit configuration, `uv run python -m intermem.lib.scanner` will fail with `ModuleNotFoundError`.

The test imports use `from intermem.lib.scanner import ...`, which requires a top-level `intermem/` package. The `lib/` directory is intended to be the `intermem/lib/` sub-package. The project layout as described would require either:

**Option A:** Rename `lib/` to `intermem/lib/` (i.e., add an outer `intermem/` package wrapper). Then `plugins/intermem/intermem/lib/scanner.py` would be the path.

**Option B:** Keep `lib/` at `plugins/intermem/lib/` and configure hatchling:

```toml
[tool.hatch.build.targets.wheel]
packages = ["lib"]

[tool.hatch.build.targets.wheel.sources]
"lib" = "intermem/lib"
```

**Option C (simplest):** Rename `lib/` to `intermem/` and update all imports to `from intermem.scanner import ...`. This matches the SKILL.md command `uv run python -m intermem.synthesize`.

Note that the SKILL.md shows `uv run python -m intermem.synthesize` but the module is at `lib/synthesize.py`, not `intermem/synthesize.py`. The `__main__.py` is at `lib/__main__.py`, so `python -m intermem.lib` would work but `python -m intermem.synthesize` would not. This is a structural inconsistency that needs resolution before Task 1 is complete.

The console script entry point has the same issue:

```toml
[project.scripts]
intermem = "intermem.lib.__main__:main"
```

Hatchling needs to find the `intermem` package. Without explicit source mapping, it won't.

**Recommendation:** In Task 1, choose Option C (rename `lib/` to `intermem/`) and update SKILL.md to use `uv run python -m intermem` (which invokes `__main__.py`). This is the most natural Python package layout.

### 4.2 `from __future__ import annotations` Is Inconsistent (LOW)

`from __future__ import annotations` is present in `scanner.py`, `stability.py`, `dedup.py`, `promoter.py`, `pruner.py`, `synthesize.py`, and `__main__.py`. It is absent from `journal.py`. This is an inconsistency. Since the project targets Python 3.11+, PEP 563 (postponed evaluation) is available and the import is good practice for forward references. Apply it uniformly to `journal.py`.

### 4.3 `dataclass` Fields With `str` Status Should Use `field(default=...)` or Be Explicit (LOW)

`PruneResult` has a field with a default:

```python
@dataclass
class PruneResult:
    lines_removed: int
    new_total_lines: int
    dry_run: bool = False
```

This is correct Python dataclass syntax (fields with defaults must come after fields without defaults). No issue here.

However, `StabilityScore`, `DedupResult`, `JournalEntry`, and `PromotionResult` all lack `__post_init__` validation. For a library that will be serialized to/from JSONL, consider adding `__post_init__` to `JournalEntry` to validate that `status` is one of the allowed values. This is not strictly required but would catch programming errors early.

### 4.4 `_clean_orphaned_headers` Uses `continue` After Mutation in a `while` Loop (LOW)

**Location:** `pruner.py`

```python
while i < len(lines):
    if lines[i].startswith("## "):
        ...
        if has_content:
            result.append(lines[i])
        else:
            # Skip this orphaned header and any blank lines after it
            i += 1
            while i < len(lines) and not lines[i].strip() and not lines[i].startswith("#"):
                i += 1
            continue
    else:
        result.append(lines[i])
    i += 1
```

The inner `while` loop increments `i`, then the outer `while` body reaches the `continue`, which skips the outer `i += 1`. This is correct but fragile. If someone adds an `i += 1` at the bottom of the `if has_content` branch, it would double-increment.

**Recommendation:** Refactor to make the control flow explicit with a local `skip_count` variable or use a for-loop with an index list comprehension.

### 4.5 `scan_memory_dir` Calls `sorted()` But Does Not Document Sort Order (LOW)

```python
md_files = sorted(memory_dir.glob("*.md"))
```

`glob()` returns paths in filesystem order (undefined). `sorted()` gives lexicographic order by full path. This is fine and deterministic, but the sort criterion is not documented. A comment `# Sort for deterministic ordering across runs` would clarify the intent.

### 4.6 Context Manager Missing for File Writes (LOW)

In `scanner.py`, files are read with `md_file.read_text()`, which handles open/close automatically. In `stability.py`, `journal.py`, and `pruner.py`, file opens use `with self.path.open("a") as f:` — correct. In `pruner.py`, two writes use `filepath.write_text(...)` and `backup_path.write_text(...)` — these are safe (write_text opens and closes internally). No issues with context managers as written, but worth noting that `write_text` does not perform an atomic rename, meaning a crash mid-write leaves a truncated file. The plan acknowledges this is acceptable for Phase 0.5.

---

## 5. Module Structure

### 5.1 Package Layout vs. SKILL.md Commands Are Inconsistent (HIGH)

Already covered in 4.1. The SKILL.md (Task 1) shows:

```bash
uv run python -m intermem.synthesize --project-dir "$(pwd)"
uv run python -m intermem.scanner --project-dir "$(pwd)"
uv run python -m intermem.stability --project-dir "$(pwd)"
```

But the modules are at `lib/synthesize.py`, `lib/scanner.py`, `lib/stability.py`. These commands would fail. None of these modules except `synthesize.py` have a `main()` function or `if __name__ == "__main__"` block anyway.

SKILL.md is the agent-facing interface and should be accurate. Either:
- Rename `lib/` to `intermem/` (so `python -m intermem.synthesize` works after installing with `uv tool install -e .`)
- Or update SKILL.md to use `uv run python -m intermem.lib.synthesize`

### 5.2 `_hash_content` Duplication Creates Coupling Risk (MEDIUM)

Already noted in 2.1. The promoter computes hashes to write to the journal; the pruner recomputes hashes to look up journal entries. If they diverge, prune silently fails. The shared utility approach prevents this class of bug.

### 5.3 `synthesize.py` Routing Logic Is a Stub (LOW)

```python
# Route entries to appropriate target doc (first available for now)
target = target_docs[0] if target_docs else None
```

The SKILL.md describes a routing rule (structural facts → AGENTS.md, behavioral preferences → CLAUDE.md). The implementation ignores it and uses `target_docs[0]`. This is acceptable for Phase 0.5, but there is no test for routing behavior. If routing is deferred, a `# TODO(phase 1): route by entry type` comment would prevent this from being forgotten.

### 5.4 `auto_approve` Branch in `synthesize.py` Has Dead Code (LOW)

```python
if auto_approve:
    approved = candidates
else:
    # In real usage, this is handled by the skill's interactive UX
    approved = candidates
```

Both branches assign `approved = candidates`. The `else` branch is semantically identical to the `if` branch. This is clearly a placeholder, but it means the `auto_approve=False` path is entirely untested and the behavior is unimplemented (the `else` should eventually present candidates to the user interactively via the Claude Code skill interface, not assign the same list). Mark it explicitly:

```python
if not auto_approve:
    raise NotImplementedError(
        "Interactive approval is handled by the skill; call run_synthesis with auto_approve=True"
    )
approved = candidates
```

---

## 6. pyproject.toml Configuration

### 6.1 Missing Package Source Configuration (HIGH)

Covered in 4.1. The `pyproject.toml` as written:

```toml
[project]
name = "intermem"
version = "0.1.0"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Hatchling will fail to find any Python package unless:
1. There is a directory named `intermem/` at the project root (`plugins/intermem/intermem/`), OR
2. `[tool.hatch.build.targets.wheel]` specifies the source mapping.

Recommended final form for Option C (rename `lib/` to `intermem/`):

```toml
[project]
name = "intermem"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
intermem = "intermem.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

With directory structure:
```
plugins/intermem/
  intermem/
    __init__.py
    __main__.py
    scanner.py
    stability.py
    dedup.py
    promoter.py
    pruner.py
    journal.py
    synthesize.py
  tests/
    __init__.py
    test_scanner.py
    ...
  pyproject.toml
  .claude-plugin/plugin.json
  CLAUDE.md
  skills/synthesize/SKILL.md
```

### 6.2 Missing `[project.optional-dependencies]` for Test Dependencies (LOW)

The plan uses `uv run pytest`. For `uv run pytest` to work, pytest must be available. Either:
- Add `pytest` as a dev dependency in `pyproject.toml`:
  ```toml
  [project.optional-dependencies]
  dev = ["pytest>=8.0"]
  ```
  Then use `uv run --extra dev pytest tests/`
- Or use `uv add --dev pytest` before the first test run (Task 2, Step 2).

The plan does not mention installing pytest at all. Task 2 Step 2 instructs running `uv run pytest tests/test_scanner.py -v` without any prior `uv add pytest`. This will fail with `No module named pytest` on a fresh checkout.

---

## 7. Additional Observations

### 7.1 No Test for `scan_memory_dir` Against a Non-Directory Path

If `memory_dir` does not exist, `memory_dir.glob("*.md")` raises `OSError`. The caller (`run_synthesis`) calls `scan_memory_dir(memory_dir)` without checking if `memory_dir` exists. The CLI's `_find_memory_dir` returns `None` and exits if the directory is missing, but `run_synthesis` itself does not guard against a missing `memory_dir`. Tests using `tmp_path` always have a valid directory. A defensive `if not memory_dir.is_dir(): return ScanResult()` in `scan_memory_dir` would make the library more robust.

### 7.2 WAL Journal Does Not Replay on Crash Recovery

The plan calls the journal "WAL-style" and mentions crash recovery. The `get_incomplete()` method returns uncommitted/unpruned entries, but there is no `replay_incomplete()` function and no test that simulates a crash (e.g., a committed but not-yet-pruned journal entry on startup). The next run would simply promote the entry again (creating a duplicate in the target doc) since `run_synthesis` creates a fresh `PromotionJournal` and never checks for incomplete entries before starting.

**Recommendation:** Add a crash recovery step at the start of `run_synthesis`:

```python
journal = PromotionJournal(intermem_dir / "promotion-journal.jsonl")
incomplete = journal.get_incomplete()
if incomplete:
    # Handle committed-but-not-pruned entries from previous run
    ...
```

And add a test:
```python
def test_crash_recovery_committed_not_pruned(tmp_path):
    """If previous run committed but did not prune, next run prunes without re-promoting."""
    ...
```

### 7.3 `_parse_file` Section-Heading Detection Is Fragile for `##` Inside Code Blocks

```python
if line.startswith("## "):
    ...
```

The implementation correctly tracks `in_code_block` and uses `continue` for code-block lines. However, the code block tracking is broken: when a code fence line is encountered, it toggles `in_code_block` and then `continue`s without checking whether the toggle means we're now in or out of a block. The problem:

```python
if line.strip().startswith("```"):
    in_code_block = not in_code_block
    if current_entry_lines:
        current_entry_lines.append(line)
    continue  # ALWAYS skip the fence line from section/bullet detection
```

This is actually correct — the `continue` skips the rest of the loop iteration, so fence lines never trigger the `if line.startswith("## ")` check. The `in_code_block` guard before the section-heading check handles lines INSIDE the block:

```python
if in_code_block:
    if current_entry_lines:
        current_entry_lines.append(line)
    continue
```

So a `## heading inside a code block` is correctly ignored. The implementation is correct, but the logic is non-obvious. A comment explaining the two-stage guard would help maintainers.

---

## Summary Table

| Finding | Severity | Module | Category |
|---------|----------|--------|----------|
| test_new_entry_scores_recent vs. test_volatile conflict — implementation cannot pass both | HIGH | stability.py | Correctness |
| `mark_committed`/`mark_pruned` raise bare KeyError | HIGH | journal.py | Error handling |
| Malformed JSONL crashes StabilityStore and PromotionJournal | HIGH | stability.py, journal.py | Error handling |
| `pyproject.toml` missing package source; `lib/` not discoverable as `intermem` | HIGH | pyproject.toml | Build |
| `promote_entries` journals committed before write succeeds | MEDIUM | promoter.py | Error handling |
| `_hash_content` duplicated in promoter.py and pruner.py | MEDIUM | promoter.py, pruner.py | Structure |
| SKILL.md module paths don't match `lib/` layout | HIGH | SKILL.md | Structure |
| Dead variable `memory_content` in test_pruning_after_promotion | MEDIUM | test_synthesize.py | Test quality |
| Missing edge case tests (empty file, encoding errors) | MEDIUM | test_scanner.py | Test quality |
| `score` / `status` fields should use `Literal` types | LOW | stability.py, dedup.py, journal.py | Idioms |
| `auto_approve=False` path is dead code | LOW | synthesize.py | Correctness |
| `_find_memory_dir` dead `else` branch | LOW | __main__.py | Correctness |
| `pytest` not added as dependency before first test run | LOW | pyproject.toml | Build |
| No crash-recovery test or logic for committed-but-not-pruned | LOW | synthesize.py, journal.py | Correctness |
| `from __future__ import annotations` missing in journal.py | LOW | journal.py | Idioms |
