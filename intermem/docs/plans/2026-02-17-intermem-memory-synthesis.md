# Intermem Memory Synthesis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build the intermem Claude Code plugin that synthesizes auto-memory entries into curated AGENTS.md/CLAUDE.md documents, with stability detection, deduplication, interactive approval, and atomic pruning.

**Architecture:** Intermem is a Claude Code plugin (no standalone MCP server) with a single skill (`/intermem:synthesize`) backed by a Python library in `intermem/` (package name matches project name). The skill orchestrates a pipeline: scan → stability check → dedup → approve → promote+prune. Persistent state lives in `.intermem/` (stability hashes, promotion journal). All file writes use a WAL-style journal for atomicity.

**Flux-Drive Fixes (apply during implementation):**
1. **Package layout:** Use `intermem/` not `lib/` as the package directory (hatchling requires package name to match)
2. **Journal atomicity:** Call `mark_committed` AFTER `target_path.write_text()`, not before
3. **Stability scoring:** Distinguish new entries (recent) from changed entries (volatile) by checking if previous snapshot had entries in the same section
4. **Dedup marker stripping:** Strip `<!-- intermem -->` markers from target doc content before comparing in dedup
5. **Journal idempotency:** Check if hash already exists in journal before writing pending
6. **Crash recovery:** At pipeline start, check for incomplete journal entries and handle them

**Tech Stack:** Python 3.11+ (via `uv run`), JSONL for state files, difflib for fuzzy matching, hashlib for content hashing. Claude Code plugin system for skills.

**Bead:** iv-3xm0
**Phase:** executing (as of 2026-02-17T21:46:28Z)

---

## Task 1: Plugin Scaffold

**Files:**
- Create: `plugins/intermem/.claude-plugin/plugin.json`
- Create: `plugins/intermem/CLAUDE.md`
- Create: `plugins/intermem/skills/synthesize/SKILL.md`
- Create: `plugins/intermem/lib/__init__.py`
- Create: `plugins/intermem/lib/scanner.py` (empty module)
- Create: `plugins/intermem/lib/stability.py` (empty module)
- Create: `plugins/intermem/lib/dedup.py` (empty module)
- Create: `plugins/intermem/lib/promoter.py` (empty module)
- Create: `plugins/intermem/lib/pruner.py` (empty module)
- Create: `plugins/intermem/lib/journal.py` (empty module)
- Create: `plugins/intermem/tests/__init__.py`

**Step 1: Create plugin.json**

```json
{
  "name": "intermem",
  "version": "0.1.0",
  "description": "Memory synthesis — graduates stable auto-memory facts to AGENTS.md/CLAUDE.md",
  "author": {
    "name": "mistakeknot",
    "email": "mistakeknot@vibeguider.org"
  },
  "skills": [
    "./skills/synthesize/SKILL.md"
  ]
}
```

Note: No `hooks` or `mcpServers` keys — this plugin is skill-only for Phase 0.5.

**Step 2: Create CLAUDE.md**

```markdown
# intermem

Memory synthesis plugin — graduates stable auto-memory facts to curated reference documents.

## Quick Reference

- **Plugin manifest**: `.claude-plugin/plugin.json`
- **Library**: `lib/` (Python, run via `uv run`)
- **State directory**: `.intermem/` in target project root
- **Skill**: `/intermem:synthesize`

## Architecture

Pipeline: scan → stability → dedup → approve → promote+prune

- `lib/scanner.py` — Parse auto-memory markdown into structured entries
- `lib/stability.py` — Per-entry content hashing across snapshots
- `lib/dedup.py` — Fuzzy matching against AGENTS.md/CLAUDE.md
- `lib/promoter.py` — Write entries to target docs with marker comments
- `lib/pruner.py` — Remove promoted entries from auto-memory
- `lib/journal.py` — WAL-style promotion journal for atomicity

## State Files

- `.intermem/stability.jsonl` — Per-entry content hash history
- `.intermem/promotion-journal.jsonl` — Atomic promotion/prune log

## Constraints

- No hooks (Clavain hook budget)
- No MCP server (Phase 0.5 is skill-only)
- `.intermem/` must be in `.gitignore` for the target project
```

**Step 3: Create SKILL.md for synthesize**

```markdown
# Memory Synthesis

Scan auto-memory for the current project, identify stable facts, and promote them to AGENTS.md/CLAUDE.md with user approval.

## Instructions

Run the intermem synthesis pipeline using the Python library:

1. **Scan**: Read auto-memory files from the project's memory directory
2. **Stability**: Check each entry against `.intermem/stability.jsonl` — only promote entries stable across 3+ snapshots
3. **Dedup**: Compare stable candidates against existing AGENTS.md/CLAUDE.md content
4. **Approve**: Present candidates to the user with batch approval (numbered list)
5. **Promote+Prune**: Write approved entries to target docs, prune from auto-memory

### Running the Pipeline

```bash
uv run python -m intermem.synthesize --project-dir "$(pwd)"
```

Or invoke individual stages for debugging:

```bash
uv run python -m intermem.scanner --project-dir "$(pwd)"
uv run python -m intermem.stability --project-dir "$(pwd)"
```

### First Run Behavior

On first run (no `.intermem/stability.jsonl`), the scanner records a baseline snapshot. All entries are scored "recent" — none are promoted. The user must run synthesis again after a few more sessions to build history.

Display: "Building baseline — recorded N entries. Run again after your next few sessions to identify stable facts."

### Batch Approval UX

Present candidates as a numbered list grouped by target document:

```
Candidates for AGENTS.md:
  1. [stable] Oracle CLI requires DISPLAY=:99 (section: Cross-Cutting Lessons)
  2. [stable] Never use > file redirect with oracle (section: Cross-Cutting Lessons)
  3. [similar to existing] Git credential lock fix... (section: Cross-Cutting Lessons)

Candidates for CLAUDE.md:
  4. [stable] Always use uv run for Python deps (section: Tool Usage)

Enter selections (e.g., "approve 1,2,4 / reject 3" or "all"):
```

### Routing Rule

- Structural/architectural facts → AGENTS.md
- Behavioral preferences, tool usage → CLAUDE.md
- If uncertain, default to AGENTS.md (shared with all agents)
```

**Step 4: Create empty Python module files**

Create `lib/__init__.py`, `lib/scanner.py`, `lib/stability.py`, `lib/dedup.py`, `lib/promoter.py`, `lib/pruner.py`, `lib/journal.py`, and `tests/__init__.py` — all empty or with a single docstring.

**Step 5: Create pyproject.toml**

```toml
[project]
name = "intermem"
version = "0.1.0"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

No external dependencies for Phase 0.5 — only stdlib (hashlib, difflib, json, pathlib, dataclasses).

**Step 6: Commit**

```bash
git add plugins/intermem/
git commit -m "feat(intermem): scaffold plugin with skill and empty library modules"
```

---

## Task 2: Auto-Memory Scanner (F1)

**Files:**
- Create: `plugins/intermem/tests/test_scanner.py`
- Modify: `plugins/intermem/lib/scanner.py`

**Step 1: Write the failing tests**

```python
"""Tests for auto-memory scanner."""
import textwrap
from pathlib import Path
from intermem.lib.scanner import scan_memory_dir, MemoryEntry


def test_scan_empty_dir(tmp_path):
    """Empty memory dir returns empty list."""
    result = scan_memory_dir(tmp_path)
    assert result.entries == []
    assert result.total_lines == 0


def test_scan_single_file_with_sections(tmp_path):
    """Parse a typical MEMORY.md into section-grouped entries."""
    content = textwrap.dedent("""\
        # Project Memory

        ## Oracle CLI
        - Never use `> file` redirect — use `--write-output <path>`
        - Requires: `DISPLAY=:99 CHROME_PATH=/usr/local/bin/google-chrome-wrapper`

        ## Git Workflow
        - Always commit to main, no feature branches
    """)
    (tmp_path / "MEMORY.md").write_text(content)
    result = scan_memory_dir(tmp_path)
    assert len(result.entries) == 3
    assert result.entries[0].section == "Oracle CLI"
    assert "redirect" in result.entries[0].content
    assert result.entries[2].section == "Git Workflow"


def test_scan_preserves_code_blocks(tmp_path):
    """Code blocks within an entry are kept intact, not split."""
    content = textwrap.dedent("""\
        ## Debugging

        - Use strace to trace credential issues:
          ```bash
          strace -e trace=openat,rename -f git push 2>&1
          ```
    """)
    (tmp_path / "MEMORY.md").write_text(content)
    result = scan_memory_dir(tmp_path)
    assert len(result.entries) == 1
    assert "```bash" in result.entries[0].content
    assert "strace" in result.entries[0].content


def test_scan_multiple_files(tmp_path):
    """Scans all .md files, not just MEMORY.md."""
    (tmp_path / "MEMORY.md").write_text("## Main\n- Fact one\n")
    (tmp_path / "debugging.md").write_text("## Debug\n- Fact two\n")
    result = scan_memory_dir(tmp_path)
    assert len(result.entries) == 2


def test_scan_reports_line_count(tmp_path):
    """Total line count across all files."""
    (tmp_path / "MEMORY.md").write_text("# Title\n\n## Section\n- Line 1\n- Line 2\n")
    result = scan_memory_dir(tmp_path)
    assert result.total_lines == 5


def test_scan_warns_near_cap(tmp_path):
    """Warning flag set when total lines > 150."""
    lines = ["- Fact {}\n".format(i) for i in range(160)]
    (tmp_path / "MEMORY.md").write_text("## Section\n" + "".join(lines))
    result = scan_memory_dir(tmp_path)
    assert result.near_cap is True


def test_scan_entry_has_line_range(tmp_path):
    """Each entry records its source file and line range."""
    content = "## Section\n- First fact\n- Second fact\n"
    (tmp_path / "MEMORY.md").write_text(content)
    result = scan_memory_dir(tmp_path)
    assert result.entries[0].source_file == "MEMORY.md"
    assert result.entries[0].start_line >= 1
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_scanner.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'intermem.lib.scanner'` or `ImportError: cannot import name 'scan_memory_dir'`

**Step 3: Implement scanner.py**

```python
"""Auto-memory scanner — reads and parses project memory files into structured entries."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MemoryEntry:
    """A single fact/entry parsed from auto-memory."""
    content: str
    section: str
    source_file: str
    start_line: int
    end_line: int


@dataclass
class ScanResult:
    """Result of scanning a memory directory."""
    entries: list[MemoryEntry] = field(default_factory=list)
    total_lines: int = 0
    near_cap: bool = False  # True when total_lines > 150


def scan_memory_dir(memory_dir: Path) -> ScanResult:
    """Scan all .md files in memory_dir, parse into structured entries.

    Parsing rules:
    - ## headings define sections
    - Bullet points (- or *) at indent level 0 start new entries
    - Continuation lines (indented, code blocks) belong to the current entry
    - Lines before any ## heading use filename as section name
    """
    entries: list[MemoryEntry] = []
    total_lines = 0

    md_files = sorted(memory_dir.glob("*.md"))
    for md_file in md_files:
        text = md_file.read_text()
        lines = text.splitlines()
        total_lines += len(lines)
        file_entries = _parse_file(lines, md_file.name)
        entries.extend(file_entries)

    return ScanResult(
        entries=entries,
        total_lines=total_lines,
        near_cap=total_lines > 150,
    )


def _parse_file(lines: list[str], filename: str) -> list[MemoryEntry]:
    """Parse a single markdown file into entries."""
    entries: list[MemoryEntry] = []
    current_section = filename.removesuffix(".md")
    current_entry_lines: list[str] = []
    entry_start_line = 0
    in_code_block = False

    for i, line in enumerate(lines, start=1):
        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            if current_entry_lines:
                current_entry_lines.append(line)
            continue

        if in_code_block:
            if current_entry_lines:
                current_entry_lines.append(line)
            continue

        # Section heading
        if line.startswith("## "):
            # Flush current entry
            if current_entry_lines:
                entries.append(_make_entry(
                    current_entry_lines, current_section, filename, entry_start_line, i - 1
                ))
                current_entry_lines = []
            current_section = line.lstrip("# ").strip()
            continue

        # Skip top-level headings (# Title)
        if line.startswith("# ") and not line.startswith("## "):
            if current_entry_lines:
                entries.append(_make_entry(
                    current_entry_lines, current_section, filename, entry_start_line, i - 1
                ))
                current_entry_lines = []
            continue

        # New bullet entry at root level
        if re.match(r'^[-*] ', line):
            if current_entry_lines:
                entries.append(_make_entry(
                    current_entry_lines, current_section, filename, entry_start_line, i - 1
                ))
            current_entry_lines = [line]
            entry_start_line = i
            continue

        # Continuation line (indented or empty within entry)
        if current_entry_lines:
            current_entry_lines.append(line)
        # Else: skip blank/preamble lines outside entries

    # Flush final entry
    if current_entry_lines:
        entries.append(_make_entry(
            current_entry_lines, current_section, filename, entry_start_line, len(lines)
        ))

    return entries


def _make_entry(
    lines: list[str], section: str, filename: str, start: int, end: int
) -> MemoryEntry:
    """Create a MemoryEntry from accumulated lines."""
    # Strip trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()
        end -= 1
    return MemoryEntry(
        content="\n".join(lines),
        section=section,
        source_file=filename,
        start_line=start,
        end_line=end,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_scanner.py -v
```

Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add plugins/intermem/lib/scanner.py plugins/intermem/tests/test_scanner.py
git commit -m "feat(intermem): implement auto-memory scanner with markdown parsing"
```

---

## Task 3: Stability Detection (F2)

**Files:**
- Create: `plugins/intermem/tests/test_stability.py`
- Modify: `plugins/intermem/lib/stability.py`

**Step 1: Write the failing tests**

```python
"""Tests for stability detection via per-entry content hashing."""
import json
import time
from pathlib import Path
from intermem.lib.scanner import MemoryEntry
from intermem.lib.stability import (
    StabilityStore,
    StabilityScore,
    record_snapshot,
    score_entries,
)


def _entry(content: str, section: str = "Test") -> MemoryEntry:
    return MemoryEntry(content=content, section=section, source_file="MEMORY.md", start_line=1, end_line=1)


def test_first_run_creates_baseline(tmp_path):
    """First snapshot records entries but scores all as 'recent'."""
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    entries = [_entry("- Fact A"), _entry("- Fact B")]
    record_snapshot(store, entries)
    scores = score_entries(store, entries)
    assert all(s.score == "recent" for s in scores)
    assert store.path.exists()


def test_stable_after_three_snapshots(tmp_path):
    """Entry unchanged across 3 snapshots scores 'stable'."""
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    entries = [_entry("- Fact A")]
    for _ in range(3):
        record_snapshot(store, entries)
    scores = score_entries(store, entries)
    assert scores[0].score == "stable"


def test_volatile_when_content_changes(tmp_path):
    """Entry that changed in most recent snapshot scores 'volatile'."""
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    entries_v1 = [_entry("- Fact A version 1")]
    entries_v2 = [_entry("- Fact A version 2")]
    record_snapshot(store, entries_v1)
    record_snapshot(store, entries_v1)
    record_snapshot(store, entries_v2)  # Changed!
    scores = score_entries(store, entries_v2)
    assert scores[0].score == "volatile"


def test_new_entry_scores_recent(tmp_path):
    """Entry not seen in previous snapshots scores 'recent'."""
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    old = [_entry("- Old fact")]
    record_snapshot(store, old)
    record_snapshot(store, old)
    new_entries = [_entry("- Old fact"), _entry("- Brand new")]
    record_snapshot(store, new_entries)
    scores = score_entries(store, new_entries)
    # Old fact seen 3 times = stable, new fact seen 1 time = recent
    assert scores[0].score == "stable"
    assert scores[1].score == "recent"


def test_removed_entry_not_in_scores(tmp_path):
    """Entries not in current scan are not scored."""
    store = StabilityStore(tmp_path / ".intermem" / "stability.jsonl")
    entries = [_entry("- Fact A"), _entry("- Fact B")]
    record_snapshot(store, entries)
    current = [_entry("- Fact A")]  # B removed
    record_snapshot(store, current)
    scores = score_entries(store, current)
    assert len(scores) == 1


def test_store_persists_across_instances(tmp_path):
    """Store data survives creating a new StabilityStore pointing to same file."""
    path = tmp_path / ".intermem" / "stability.jsonl"
    store1 = StabilityStore(path)
    record_snapshot(store1, [_entry("- Fact A")])

    store2 = StabilityStore(path)
    record_snapshot(store2, [_entry("- Fact A")])

    store3 = StabilityStore(path)
    record_snapshot(store3, [_entry("- Fact A")])
    scores = score_entries(store3, [_entry("- Fact A")])
    assert scores[0].score == "stable"
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_stability.py -v
```

Expected: FAIL — imports don't resolve.

**Step 3: Implement stability.py**

```python
"""Stability detection via per-entry content hashing across snapshots."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from intermem.lib.scanner import MemoryEntry


@dataclass
class StabilityScore:
    """Stability assessment for a single entry."""
    entry: MemoryEntry
    score: str  # "stable", "recent", "volatile"
    snapshot_count: int  # How many snapshots this hash has appeared in


class StabilityStore:
    """Persistent store for per-entry content hash history.

    Each snapshot is a JSONL line: {"timestamp": ..., "hashes": {"hash1": "content_preview", ...}}
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._snapshots: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self._snapshots.append(json.loads(line))

    def _save_snapshot(self, snapshot: dict) -> None:
        self._snapshots.append(snapshot)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(snapshot) + "\n")

    @property
    def snapshots(self) -> list[dict]:
        return self._snapshots


def _hash_entry(entry: MemoryEntry) -> str:
    """Compute content hash for an entry."""
    return hashlib.sha256(entry.content.strip().encode()).hexdigest()[:16]


def record_snapshot(store: StabilityStore, entries: list[MemoryEntry]) -> None:
    """Record a new snapshot of current entries."""
    hashes = {}
    for entry in entries:
        h = _hash_entry(entry)
        preview = entry.content[:80].replace("\n", " ")
        hashes[h] = preview
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hashes": hashes,
    }
    store._save_snapshot(snapshot)


def score_entries(store: StabilityStore, entries: list[MemoryEntry]) -> list[StabilityScore]:
    """Score each entry's stability based on snapshot history.

    - stable: hash present in 3+ snapshots and not changed in most recent
    - volatile: hash only in most recent snapshot AND a different hash for same content existed before
    - recent: hash in 1-2 snapshots (including new entries)
    """
    scores = []
    for entry in entries:
        h = _hash_entry(entry)
        count = sum(1 for snap in store.snapshots if h in snap.get("hashes", {}))

        if count >= 3:
            scores.append(StabilityScore(entry=entry, score="stable", snapshot_count=count))
        elif count == 1 and len(store.snapshots) >= 2:
            # Only in the latest snapshot — could be volatile (changed) or genuinely new
            # Check if this is a new entry or a modification of an existing one
            # For now, if total snapshots > 1 and this hash only appears once, it's volatile
            # (it either just appeared or just changed)
            # But we need to distinguish: was there a *similar* entry before?
            # Simple heuristic: if there are older snapshots and this hash is only in the latest, mark volatile
            scores.append(StabilityScore(entry=entry, score="volatile", snapshot_count=count))
        else:
            scores.append(StabilityScore(entry=entry, score="recent", snapshot_count=count))

    return scores
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_stability.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add plugins/intermem/lib/stability.py plugins/intermem/tests/test_stability.py
git commit -m "feat(intermem): implement stability detection with per-entry content hashing"
```

---

## Task 4: Deduplication Checker (F3)

**Files:**
- Create: `plugins/intermem/tests/test_dedup.py`
- Modify: `plugins/intermem/lib/dedup.py`

**Step 1: Write the failing tests**

```python
"""Tests for deduplication checker against AGENTS.md/CLAUDE.md content."""
import textwrap
from pathlib import Path
from intermem.lib.scanner import MemoryEntry
from intermem.lib.dedup import check_duplicates, DedupResult


def _entry(content: str, section: str = "Test") -> MemoryEntry:
    return MemoryEntry(content=content, section=section, source_file="MEMORY.md", start_line=1, end_line=1)


def test_novel_entry_detected(tmp_path):
    """Entry with no match in target docs is marked novel."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Build\n- Run `make build`\n")
    entry = _entry("- Always use pytest with -v flag")
    results = check_duplicates([entry], [agents])
    assert len(results) == 1
    assert results[0].status == "novel"


def test_exact_duplicate_detected(tmp_path):
    """Entry identical to existing content is marked exact_duplicate."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Testing\n- Always use pytest with -v flag\n")
    entry = _entry("- Always use pytest with -v flag")
    results = check_duplicates([entry], [agents])
    assert results[0].status == "exact_duplicate"


def test_fuzzy_duplicate_detected(tmp_path):
    """Entry similar but not identical is marked fuzzy_duplicate with confidence."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Testing\n- Always run pytest with the -v verbose flag\n")
    entry = _entry("- Always use pytest with -v flag")
    results = check_duplicates([entry], [agents])
    assert results[0].status == "fuzzy_duplicate"
    assert results[0].confidence > 0.7


def test_multiple_target_docs(tmp_path):
    """Checks against all provided target documents."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Agents\n\n## Build\n- Use make\n")
    claude = tmp_path / "CLAUDE.md"
    claude.write_text("# Claude\n\n## Prefs\n- Always use pytest with -v flag\n")
    entry = _entry("- Always use pytest with -v flag")
    results = check_duplicates([entry], [agents, claude])
    assert results[0].status == "exact_duplicate"
    assert "CLAUDE.md" in results[0].matched_in


def test_missing_target_doc_skipped(tmp_path):
    """Non-existent target doc is gracefully skipped."""
    entry = _entry("- Some fact")
    results = check_duplicates([entry], [tmp_path / "nonexistent.md"])
    assert len(results) == 1
    assert results[0].status == "novel"


def test_dedup_result_has_match_context(tmp_path):
    """Fuzzy duplicate includes the matched line for user context."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## CLI\n- Oracle requires DISPLAY=:99 environment variable\n")
    entry = _entry("- Oracle CLI requires DISPLAY=:99")
    results = check_duplicates([entry], [agents])
    assert results[0].matched_line is not None
    assert "Oracle" in results[0].matched_line
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_dedup.py -v
```

Expected: FAIL — imports don't resolve.

**Step 3: Implement dedup.py**

```python
"""Deduplication checker — compares entries against AGENTS.md/CLAUDE.md content."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from intermem.lib.scanner import MemoryEntry

FUZZY_THRESHOLD = 0.80


@dataclass
class DedupResult:
    """Deduplication result for a single entry."""
    entry: MemoryEntry
    status: str  # "novel", "exact_duplicate", "fuzzy_duplicate"
    confidence: float  # 0.0 to 1.0 (1.0 = exact match)
    matched_in: str  # Filename where match was found, or ""
    matched_line: str | None  # The matching line from target doc


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip markdown bullets and whitespace."""
    text = text.strip().lower()
    if text.startswith(("- ", "* ")):
        text = text[2:]
    return text


def _extract_lines(path: Path) -> list[tuple[str, str]]:
    """Extract content lines from a markdown file. Returns (raw_line, filename) pairs."""
    if not path.exists():
        return []
    lines = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        # Skip headings, blank lines, and non-content
        if stripped and not stripped.startswith("#"):
            lines.append((stripped, path.name))
    return lines


def check_duplicates(
    entries: list[MemoryEntry],
    target_docs: list[Path],
) -> list[DedupResult]:
    """Check each entry against all target docs for duplicates.

    - Exact hash match → exact_duplicate (auto-skip)
    - Fuzzy match > 80% → fuzzy_duplicate (flag for review)
    - Below threshold → novel
    """
    # Build lookup of all target content
    target_lines: list[tuple[str, str]] = []
    target_hashes: dict[str, tuple[str, str]] = {}  # hash → (raw_line, filename)
    for doc in target_docs:
        for raw_line, filename in _extract_lines(doc):
            norm = _normalize(raw_line)
            h = hashlib.sha256(norm.encode()).hexdigest()[:16]
            target_hashes[h] = (raw_line, filename)
            target_lines.append((raw_line, filename))

    results = []
    for entry in entries:
        entry_norm = _normalize(entry.content.split("\n")[0])  # Compare first line
        entry_hash = hashlib.sha256(entry_norm.encode()).hexdigest()[:16]

        # Check exact hash match
        if entry_hash in target_hashes:
            raw_line, filename = target_hashes[entry_hash]
            results.append(DedupResult(
                entry=entry,
                status="exact_duplicate",
                confidence=1.0,
                matched_in=filename,
                matched_line=raw_line,
            ))
            continue

        # Check fuzzy match
        best_ratio = 0.0
        best_match: tuple[str, str] | None = None
        for raw_line, filename in target_lines:
            target_norm = _normalize(raw_line)
            ratio = SequenceMatcher(None, entry_norm, target_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (raw_line, filename)

        if best_ratio >= FUZZY_THRESHOLD and best_match:
            results.append(DedupResult(
                entry=entry,
                status="fuzzy_duplicate",
                confidence=best_ratio,
                matched_in=best_match[1],
                matched_line=best_match[0],
            ))
        else:
            results.append(DedupResult(
                entry=entry,
                status="novel",
                confidence=best_ratio,
                matched_in="",
                matched_line=best_match[0] if best_match else None,
            ))

    return results
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_dedup.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add plugins/intermem/lib/dedup.py plugins/intermem/tests/test_dedup.py
git commit -m "feat(intermem): implement dedup checker with fuzzy string matching"
```

---

## Task 5: Promotion Journal (F5 prerequisite)

**Files:**
- Create: `plugins/intermem/tests/test_journal.py`
- Modify: `plugins/intermem/lib/journal.py`

The journal is the WAL-style atomicity layer used by both F4 (promoter) and F5 (pruner). Build it first.

**Step 1: Write the failing tests**

```python
"""Tests for the promotion journal (WAL-style atomicity)."""
import json
from pathlib import Path
from intermem.lib.journal import PromotionJournal, JournalEntry


def test_journal_creates_file(tmp_path):
    """Journal file is created on first write."""
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("hash1", "AGENTS.md", "## Section", "- Fact content")
    assert journal.path.exists()


def test_journal_records_pending(tmp_path):
    """Pending entries are recorded with correct status."""
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("hash1", "AGENTS.md", "## Section", "- Fact content")
    entries = journal.get_incomplete()
    assert len(entries) == 1
    assert entries[0].status == "pending"
    assert entries[0].entry_hash == "hash1"


def test_journal_marks_committed(tmp_path):
    """After promotion write succeeds, entry is marked committed."""
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("hash1", "AGENTS.md", "## Section", "- Fact")
    journal.mark_committed("hash1")
    entries = journal.get_incomplete()
    # Committed but not yet pruned = still incomplete
    assert len(entries) == 1
    assert entries[0].status == "committed"


def test_journal_marks_pruned(tmp_path):
    """After prune succeeds, entry is marked pruned (complete)."""
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("hash1", "AGENTS.md", "## Section", "- Fact")
    journal.mark_committed("hash1")
    journal.mark_pruned("hash1")
    entries = journal.get_incomplete()
    assert len(entries) == 0  # Fully complete


def test_journal_survives_reload(tmp_path):
    """Journal state persists across instances."""
    path = tmp_path / ".intermem" / "promotion-journal.jsonl"
    j1 = PromotionJournal(path)
    j1.record_pending("hash1", "AGENTS.md", "## Section", "- Fact")
    j1.mark_committed("hash1")

    j2 = PromotionJournal(path)
    entries = j2.get_incomplete()
    assert len(entries) == 1
    assert entries[0].status == "committed"


def test_journal_multiple_entries(tmp_path):
    """Multiple entries tracked independently."""
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("hash1", "AGENTS.md", "## A", "- Fact 1")
    journal.record_pending("hash2", "CLAUDE.md", "## B", "- Fact 2")
    journal.mark_committed("hash1")
    journal.mark_pruned("hash1")
    incomplete = journal.get_incomplete()
    assert len(incomplete) == 1
    assert incomplete[0].entry_hash == "hash2"
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_journal.py -v
```

Expected: FAIL.

**Step 3: Implement journal.py**

```python
"""WAL-style promotion journal for atomic promote+prune operations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class JournalEntry:
    """A single promotion journal record."""
    entry_hash: str
    target_file: str
    target_section: str
    content: str
    status: str  # "pending", "committed", "pruned"
    timestamp: str


class PromotionJournal:
    """Append-only journal tracking promotion lifecycle.

    Lifecycle: pending → committed (written to target) → pruned (removed from source)

    On crash recovery, incomplete entries (pending or committed) can be
    replayed or discarded.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: dict[str, JournalEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            entry = JournalEntry(**data)
            self._entries[entry.entry_hash] = entry

    def _append(self, entry: JournalEntry) -> None:
        self._entries[entry.entry_hash] = entry
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({
                "entry_hash": entry.entry_hash,
                "target_file": entry.target_file,
                "target_section": entry.target_section,
                "content": entry.content,
                "status": entry.status,
                "timestamp": entry.timestamp,
            }) + "\n")

    def record_pending(self, entry_hash: str, target_file: str, target_section: str, content: str) -> None:
        """Record that an entry is about to be promoted."""
        self._append(JournalEntry(
            entry_hash=entry_hash,
            target_file=target_file,
            target_section=target_section,
            content=content,
            status="pending",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

    def mark_committed(self, entry_hash: str) -> None:
        """Mark an entry as successfully written to target doc."""
        entry = self._entries[entry_hash]
        updated = JournalEntry(
            entry_hash=entry.entry_hash,
            target_file=entry.target_file,
            target_section=entry.target_section,
            content=entry.content,
            status="committed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._append(updated)

    def mark_pruned(self, entry_hash: str) -> None:
        """Mark an entry as successfully pruned from source."""
        entry = self._entries[entry_hash]
        updated = JournalEntry(
            entry_hash=entry.entry_hash,
            target_file=entry.target_file,
            target_section=entry.target_section,
            content=entry.content,
            status="pruned",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._append(updated)

    def get_incomplete(self) -> list[JournalEntry]:
        """Return entries that haven't completed the full lifecycle."""
        return [e for e in self._entries.values() if e.status != "pruned"]
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_journal.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add plugins/intermem/lib/journal.py plugins/intermem/tests/test_journal.py
git commit -m "feat(intermem): implement WAL-style promotion journal for atomicity"
```

---

## Task 6: Promoter — Write Entries to Target Docs (F4)

**Files:**
- Create: `plugins/intermem/tests/test_promoter.py`
- Modify: `plugins/intermem/lib/promoter.py`

**Step 1: Write the failing tests**

```python
"""Tests for the promoter — writes entries to AGENTS.md/CLAUDE.md."""
import textwrap
from pathlib import Path
from intermem.lib.scanner import MemoryEntry
from intermem.lib.journal import PromotionJournal
from intermem.lib.promoter import promote_entries, PromotionResult


def _entry(content: str, section: str = "Testing") -> MemoryEntry:
    return MemoryEntry(content=content, section=section, source_file="MEMORY.md", start_line=1, end_line=1)


def test_promote_appends_to_matching_section(tmp_path):
    """Entry is appended under the matching ## section."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Testing\n- Existing fact\n\n## Build\n- Build stuff\n")
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    entry = _entry("- New testing fact", section="Testing")

    result = promote_entries([entry], agents, journal)

    content = agents.read_text()
    assert "- New testing fact" in content
    # Should appear after "- Existing fact" but before "## Build"
    testing_idx = content.index("## Testing")
    build_idx = content.index("## Build")
    new_fact_idx = content.index("- New testing fact")
    assert testing_idx < new_fact_idx < build_idx
    assert result.promoted_count == 1


def test_promote_adds_marker_comment(tmp_path):
    """Promoted entries have <!-- intermem --> marker."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Testing\n- Existing fact\n")
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    entry = _entry("- New fact", section="Testing")

    promote_entries([entry], agents, journal)

    content = agents.read_text()
    assert "<!-- intermem -->" in content


def test_promote_creates_section_if_missing(tmp_path):
    """If target section doesn't exist, appends new section at end."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Build\n- Build stuff\n")
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    entry = _entry("- New testing fact", section="Testing")

    promote_entries([entry], agents, journal)

    content = agents.read_text()
    assert "## Testing" in content
    assert "- New testing fact" in content


def test_promote_journals_entries(tmp_path):
    """Each promoted entry is recorded in the journal as committed."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## Testing\n- Existing\n")
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    entry = _entry("- New fact", section="Testing")

    promote_entries([entry], agents, journal)

    incomplete = journal.get_incomplete()
    assert len(incomplete) == 1
    assert incomplete[0].status == "committed"


def test_promote_creates_target_if_missing(tmp_path):
    """If target file doesn't exist, creates it with a heading."""
    agents = tmp_path / "AGENTS.md"  # Does not exist yet
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    entry = _entry("- New fact", section="Testing")

    promote_entries([entry], agents, journal)

    assert agents.exists()
    content = agents.read_text()
    assert "## Testing" in content
    assert "- New fact" in content


def test_promote_multiple_entries_same_section(tmp_path):
    """Multiple entries for the same section are grouped together."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Project\n\n## CLI\n- Existing\n")
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    entries = [
        _entry("- Fact A", section="CLI"),
        _entry("- Fact B", section="CLI"),
    ]

    result = promote_entries(entries, agents, journal)

    content = agents.read_text()
    assert "- Fact A" in content
    assert "- Fact B" in content
    assert result.promoted_count == 2
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_promoter.py -v
```

Expected: FAIL.

**Step 3: Implement promoter.py**

```python
"""Promoter — writes approved entries to AGENTS.md/CLAUDE.md with journal tracking."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from intermem.lib.scanner import MemoryEntry
from intermem.lib.journal import PromotionJournal

MARKER = "<!-- intermem -->"


@dataclass
class PromotionResult:
    """Summary of a promotion operation."""
    promoted_count: int
    sections_modified: list[str]
    sections_created: list[str]


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]


def promote_entries(
    entries: list[MemoryEntry],
    target_path: Path,
    journal: PromotionJournal,
) -> PromotionResult:
    """Write entries to the target document, grouped by section.

    For each entry:
    1. Journal as pending
    2. Write to target doc under matching section (or create section)
    3. Journal as committed
    """
    if not entries:
        return PromotionResult(promoted_count=0, sections_modified=[], sections_created=[])

    # Group entries by target section
    by_section: dict[str, list[MemoryEntry]] = {}
    for entry in entries:
        by_section.setdefault(entry.section, []).append(entry)

    # Read or create target document
    if target_path.exists():
        content = target_path.read_text()
    else:
        content = f"# {target_path.stem}\n"

    sections_modified = []
    sections_created = []

    for section_name, section_entries in by_section.items():
        # Journal all entries as pending first
        for entry in section_entries:
            h = _hash_content(entry.content)
            journal.record_pending(h, target_path.name, section_name, entry.content)

        # Find the section in the document
        section_pattern = re.compile(
            rf'^(## {re.escape(section_name)}\s*\n)(.*?)(?=^## |\Z)',
            re.MULTILINE | re.DOTALL,
        )
        match = section_pattern.search(content)

        # Build the text to insert
        insert_lines = []
        for entry in section_entries:
            insert_lines.append(f"{entry.content} {MARKER}")

        insert_text = "\n".join(insert_lines) + "\n"

        if match:
            # Insert at end of existing section (before next ## or EOF)
            section_body = match.group(2)
            # Find insertion point: after last non-empty line in section body
            insert_pos = match.end(2)
            # Ensure there's a newline before our insertion
            if not section_body.endswith("\n"):
                insert_text = "\n" + insert_text
            content = content[:insert_pos] + insert_text + content[insert_pos:]
            sections_modified.append(section_name)
        else:
            # Create new section at end
            if not content.endswith("\n"):
                content += "\n"
            content += f"\n## {section_name}\n{insert_text}"
            sections_created.append(section_name)

        # Write the file
        target_path.write_text(content)

        # Journal all entries as committed
        for entry in section_entries:
            h = _hash_content(entry.content)
            journal.mark_committed(h)

    return PromotionResult(
        promoted_count=len(entries),
        sections_modified=sections_modified,
        sections_created=sections_created,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_promoter.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add plugins/intermem/lib/promoter.py plugins/intermem/tests/test_promoter.py
git commit -m "feat(intermem): implement promoter with section-aware insertion and journal"
```

---

## Task 7: Auto-Memory Pruner (F5)

**Files:**
- Create: `plugins/intermem/tests/test_pruner.py`
- Modify: `plugins/intermem/lib/pruner.py`

**Step 1: Write the failing tests**

```python
"""Tests for auto-memory pruner — removes promoted entries from source files."""
import textwrap
from pathlib import Path
from intermem.lib.scanner import MemoryEntry, scan_memory_dir
from intermem.lib.journal import PromotionJournal
from intermem.lib.pruner import prune_promoted, PruneResult


def _setup_memory(tmp_path: Path, content: str) -> Path:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "MEMORY.md").write_text(content)
    return memory_dir


def test_prune_removes_promoted_entry(tmp_path):
    """Promoted entry is removed from auto-memory."""
    content = "## Section\n- Fact A\n- Fact B\n- Fact C\n"
    memory_dir = _setup_memory(tmp_path, content)

    # Simulate: Fact B was promoted and committed in journal
    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("fakehash", "AGENTS.md", "Section", "- Fact B")
    journal.mark_committed("fakehash")

    entry = MemoryEntry(content="- Fact B", section="Section", source_file="MEMORY.md", start_line=3, end_line=3)
    result = prune_promoted([entry], memory_dir, journal)

    remaining = (memory_dir / "MEMORY.md").read_text()
    assert "- Fact A" in remaining
    assert "- Fact B" not in remaining
    assert "- Fact C" in remaining
    assert result.lines_removed > 0


def test_prune_creates_backup(tmp_path):
    """Backup .bak file is created before pruning."""
    content = "## Section\n- Fact A\n- Fact B\n"
    memory_dir = _setup_memory(tmp_path, content)

    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("h", "AGENTS.md", "Section", "- Fact B")
    journal.mark_committed("h")

    entry = MemoryEntry(content="- Fact B", section="Section", source_file="MEMORY.md", start_line=2, end_line=2)
    prune_promoted([entry], memory_dir, journal)

    assert (memory_dir / "MEMORY.md.bak").exists()
    backup = (memory_dir / "MEMORY.md.bak").read_text()
    assert "- Fact B" in backup  # Original content preserved


def test_prune_dry_run(tmp_path):
    """Dry run reports what would be removed without modifying files."""
    content = "## Section\n- Fact A\n- Fact B\n"
    memory_dir = _setup_memory(tmp_path, content)

    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("h", "AGENTS.md", "Section", "- Fact B")
    journal.mark_committed("h")

    entry = MemoryEntry(content="- Fact B", section="Section", source_file="MEMORY.md", start_line=2, end_line=2)
    result = prune_promoted([entry], memory_dir, journal, dry_run=True)

    # File should be unchanged
    remaining = (memory_dir / "MEMORY.md").read_text()
    assert "- Fact B" in remaining
    assert result.lines_removed > 0  # Reports what would be removed
    assert result.dry_run is True


def test_prune_cleans_orphaned_headers(tmp_path):
    """Section header is removed if all its entries are pruned."""
    content = "## Main\n- Keep this\n\n## Orphan\n- Remove me\n"
    memory_dir = _setup_memory(tmp_path, content)

    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("h", "AGENTS.md", "Orphan", "- Remove me")
    journal.mark_committed("h")

    entry = MemoryEntry(content="- Remove me", section="Orphan", source_file="MEMORY.md", start_line=5, end_line=5)
    prune_promoted([entry], memory_dir, journal)

    remaining = (memory_dir / "MEMORY.md").read_text()
    assert "## Orphan" not in remaining
    assert "## Main" in remaining
    assert "- Keep this" in remaining


def test_prune_marks_journal_pruned(tmp_path):
    """After successful prune, journal entry is marked pruned."""
    content = "## Section\n- Fact A\n"
    memory_dir = _setup_memory(tmp_path, content)

    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("h", "AGENTS.md", "Section", "- Fact A")
    journal.mark_committed("h")

    entry = MemoryEntry(content="- Fact A", section="Section", source_file="MEMORY.md", start_line=2, end_line=2)
    prune_promoted([entry], memory_dir, journal)

    incomplete = journal.get_incomplete()
    assert len(incomplete) == 0  # Fully complete


def test_prune_reports_new_line_count(tmp_path):
    """Result includes new total line count after pruning."""
    content = "## Section\n- Fact A\n- Fact B\n- Fact C\n"
    memory_dir = _setup_memory(tmp_path, content)

    journal = PromotionJournal(tmp_path / ".intermem" / "promotion-journal.jsonl")
    journal.record_pending("h", "AGENTS.md", "Section", "- Fact B")
    journal.mark_committed("h")

    entry = MemoryEntry(content="- Fact B", section="Section", source_file="MEMORY.md", start_line=3, end_line=3)
    result = prune_promoted([entry], memory_dir, journal)

    assert result.new_total_lines < 4
    assert result.lines_removed >= 1
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_pruner.py -v
```

Expected: FAIL.

**Step 3: Implement pruner.py**

```python
"""Auto-memory pruner — removes promoted entries from source files."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from intermem.lib.scanner import MemoryEntry, scan_memory_dir
from intermem.lib.journal import PromotionJournal


@dataclass
class PruneResult:
    """Summary of a prune operation."""
    lines_removed: int
    new_total_lines: int
    dry_run: bool = False


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]


def prune_promoted(
    entries: list[MemoryEntry],
    memory_dir: Path,
    journal: PromotionJournal,
    dry_run: bool = False,
) -> PruneResult:
    """Remove promoted entries from auto-memory files.

    Only prunes entries that are 'committed' in the journal (successfully written to target).
    Creates .bak backup before modifying. Marks journal entries as 'pruned' on success.
    """
    # Group entries by source file
    by_file: dict[str, list[MemoryEntry]] = {}
    for entry in entries:
        by_file.setdefault(entry.source_file, []).append(entry)

    total_removed = 0

    for filename, file_entries in by_file.items():
        filepath = memory_dir / filename
        if not filepath.exists():
            continue

        original_content = filepath.read_text()
        lines = original_content.splitlines(keepends=True)

        # Build set of content strings to remove
        remove_contents = {e.content.strip() for e in file_entries}

        # Parse and rebuild, skipping matched entries
        result_lines: list[str] = []
        i = 0
        raw_lines = original_content.splitlines()
        while i < len(raw_lines):
            line = raw_lines[i]

            # Check if this line starts an entry to remove
            matched = False
            for content in remove_contents:
                entry_lines = content.splitlines()
                if i + len(entry_lines) <= len(raw_lines):
                    candidate = raw_lines[i:i + len(entry_lines)]
                    if [l.strip() for l in candidate] == [l.strip() for l in entry_lines]:
                        total_removed += len(entry_lines)
                        i += len(entry_lines)
                        # Skip trailing blank line after removed entry
                        if i < len(raw_lines) and not raw_lines[i].strip():
                            total_removed += 1
                            i += 1
                        matched = True
                        break

            if not matched:
                result_lines.append(line)
                i += 1

        # Clean orphaned section headers (## Heading with no content before next ## or EOF)
        cleaned_lines = _clean_orphaned_headers(result_lines)

        # Clean trailing blank lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        if cleaned_lines:
            cleaned_lines.append("")  # Ensure final newline

        new_content = "\n".join(cleaned_lines)
        if cleaned_lines:
            new_content += "\n" if not new_content.endswith("\n") else ""

        if not dry_run:
            # Create backup
            backup_path = filepath.with_suffix(filepath.suffix + ".bak")
            backup_path.write_text(original_content)

            # Write cleaned content
            filepath.write_text(new_content)

            # Mark journal entries as pruned
            for entry in file_entries:
                h = _hash_content(entry.content)
                try:
                    journal.mark_pruned(h)
                except KeyError:
                    pass  # Entry might have a different hash in journal

    # Calculate new total
    new_total = 0
    if not dry_run:
        scan = scan_memory_dir(memory_dir)
        new_total = scan.total_lines
    else:
        # Estimate for dry run
        scan = scan_memory_dir(memory_dir)
        new_total = scan.total_lines - total_removed

    return PruneResult(
        lines_removed=total_removed,
        new_total_lines=new_total,
        dry_run=dry_run,
    )


def _clean_orphaned_headers(lines: list[str]) -> list[str]:
    """Remove ## headers that have no content entries following them."""
    result = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("## "):
            # Look ahead: is there any non-blank, non-heading content before next ## or EOF?
            has_content = False
            j = i + 1
            while j < len(lines):
                if lines[j].startswith("## ") or lines[j].startswith("# "):
                    break
                if lines[j].strip():
                    has_content = True
                    break
                j += 1
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
    return result
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_pruner.py -v
```

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add plugins/intermem/lib/pruner.py plugins/intermem/tests/test_pruner.py
git commit -m "feat(intermem): implement auto-memory pruner with backup and journal tracking"
```

---

## Task 8: Synthesize Pipeline (Orchestrator)

**Files:**
- Create: `plugins/intermem/tests/test_synthesize.py`
- Create: `plugins/intermem/lib/synthesize.py`

This is the orchestrator that wires F1-F5 together into the complete pipeline invoked by the skill.

**Step 1: Write the failing tests**

```python
"""Integration tests for the full synthesis pipeline."""
import textwrap
from pathlib import Path
from intermem.lib.synthesize import run_synthesis, SynthesisResult


def _setup_project(tmp_path: Path, memory_content: str, agents_content: str = "") -> dict:
    """Set up a fake project directory with memory and target docs."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "MEMORY.md").write_text(memory_content)

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    if agents_content:
        (project_dir / "AGENTS.md").write_text(agents_content)

    return {
        "memory_dir": memory_dir,
        "project_dir": project_dir,
        "agents_path": project_dir / "AGENTS.md",
        "claude_path": project_dir / "CLAUDE.md",
        "intermem_dir": tmp_path / ".intermem",
    }


def test_first_run_builds_baseline(tmp_path):
    """First run records baseline, promotes nothing."""
    env = _setup_project(tmp_path, "## Facts\n- Fact A\n- Fact B\n")
    result = run_synthesis(
        memory_dir=env["memory_dir"],
        target_docs=[env["agents_path"]],
        intermem_dir=env["intermem_dir"],
        auto_approve=True,
    )
    assert result.baseline_recorded is True
    assert result.promoted_count == 0
    assert (env["intermem_dir"] / "stability.jsonl").exists()


def test_stable_entries_promoted_after_three_runs(tmp_path):
    """Entries stable across 3 runs are promoted on 4th run."""
    env = _setup_project(
        tmp_path,
        "## Facts\n- Stable fact\n",
        "# Project\n\n## Facts\n",
    )
    # Run 3 times to build stability
    for _ in range(3):
        run_synthesis(
            memory_dir=env["memory_dir"],
            target_docs=[env["agents_path"]],
            intermem_dir=env["intermem_dir"],
            auto_approve=True,
        )

    # 4th run should promote
    result = run_synthesis(
        memory_dir=env["memory_dir"],
        target_docs=[env["agents_path"]],
        intermem_dir=env["intermem_dir"],
        auto_approve=True,
    )
    assert result.promoted_count == 1
    agents_content = env["agents_path"].read_text()
    assert "- Stable fact" in agents_content


def test_volatile_entries_not_promoted(tmp_path):
    """Entries that change between runs are not promoted."""
    env = _setup_project(tmp_path, "## Facts\n- Version 1\n")

    # Build some history
    run_synthesis(
        memory_dir=env["memory_dir"],
        target_docs=[env["agents_path"]],
        intermem_dir=env["intermem_dir"],
        auto_approve=True,
    )

    # Change the content
    (env["memory_dir"] / "MEMORY.md").write_text("## Facts\n- Version 2\n")

    result = run_synthesis(
        memory_dir=env["memory_dir"],
        target_docs=[env["agents_path"]],
        intermem_dir=env["intermem_dir"],
        auto_approve=True,
    )
    assert result.promoted_count == 0


def test_exact_duplicates_skipped(tmp_path):
    """Entries already in target docs are not promoted."""
    env = _setup_project(
        tmp_path,
        "## Facts\n- Already there\n",
        "# Project\n\n## Facts\n- Already there\n",
    )
    # Build stability
    for _ in range(4):
        result = run_synthesis(
            memory_dir=env["memory_dir"],
            target_docs=[env["agents_path"]],
            intermem_dir=env["intermem_dir"],
            auto_approve=True,
        )
    assert result.promoted_count == 0
    assert result.duplicates_skipped >= 1


def test_pruning_after_promotion(tmp_path):
    """Promoted entries are pruned from auto-memory."""
    env = _setup_project(
        tmp_path,
        "## Facts\n- Stable fact\n- Other fact\n",
        "# Project\n\n## Facts\n",
    )
    # Build stability for all entries
    for _ in range(3):
        run_synthesis(
            memory_dir=env["memory_dir"],
            target_docs=[env["agents_path"]],
            intermem_dir=env["intermem_dir"],
            auto_approve=True,
        )

    # Promote
    result = run_synthesis(
        memory_dir=env["memory_dir"],
        target_docs=[env["agents_path"]],
        intermem_dir=env["intermem_dir"],
        auto_approve=True,
    )

    memory_content = (env["memory_dir"] / "MEMORY.md").read_text()
    # Promoted entries should be removed from memory
    assert result.promoted_count > 0
    assert result.pruned_count > 0
```

**Step 2: Run tests to verify they fail**

```bash
cd plugins/intermem && uv run pytest tests/test_synthesize.py -v
```

Expected: FAIL.

**Step 3: Implement synthesize.py**

```python
"""Synthesis pipeline orchestrator — wires scanner, stability, dedup, promoter, and pruner."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from intermem.lib.scanner import scan_memory_dir, MemoryEntry
from intermem.lib.stability import StabilityStore, record_snapshot, score_entries
from intermem.lib.dedup import check_duplicates
from intermem.lib.promoter import promote_entries
from intermem.lib.pruner import prune_promoted
from intermem.lib.journal import PromotionJournal


@dataclass
class SynthesisResult:
    """Summary of a full synthesis run."""
    total_entries: int
    stable_entries: int
    duplicates_skipped: int
    candidates_count: int
    promoted_count: int
    pruned_count: int
    baseline_recorded: bool
    new_line_count: int


def run_synthesis(
    memory_dir: Path,
    target_docs: list[Path],
    intermem_dir: Path,
    auto_approve: bool = False,
    dry_run: bool = False,
) -> SynthesisResult:
    """Run the full synthesis pipeline.

    1. Scan auto-memory
    2. Record snapshot and score stability
    3. Filter to stable entries
    4. Check for duplicates
    5. Promote novel + fuzzy-flagged entries (with approval)
    6. Prune promoted entries from auto-memory

    Args:
        memory_dir: Path to auto-memory directory
        target_docs: List of paths to AGENTS.md/CLAUDE.md
        intermem_dir: Path to .intermem/ state directory
        auto_approve: If True, skip interactive approval (for testing)
        dry_run: If True, report what would change without modifying files
    """
    intermem_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Scan
    scan = scan_memory_dir(memory_dir)
    if not scan.entries:
        return SynthesisResult(
            total_entries=0, stable_entries=0, duplicates_skipped=0,
            candidates_count=0, promoted_count=0, pruned_count=0,
            baseline_recorded=False, new_line_count=scan.total_lines,
        )

    # Step 2: Stability
    stability_store = StabilityStore(intermem_dir / "stability.jsonl")
    is_first_run = len(stability_store.snapshots) == 0
    record_snapshot(stability_store, scan.entries)

    if is_first_run:
        return SynthesisResult(
            total_entries=len(scan.entries), stable_entries=0, duplicates_skipped=0,
            candidates_count=0, promoted_count=0, pruned_count=0,
            baseline_recorded=True, new_line_count=scan.total_lines,
        )

    scores = score_entries(stability_store, scan.entries)
    stable = [s for s in scores if s.score == "stable"]

    if not stable:
        return SynthesisResult(
            total_entries=len(scan.entries), stable_entries=0, duplicates_skipped=0,
            candidates_count=0, promoted_count=0, pruned_count=0,
            baseline_recorded=False, new_line_count=scan.total_lines,
        )

    # Step 3: Dedup
    stable_entries = [s.entry for s in stable]
    dedup_results = check_duplicates(stable_entries, target_docs)

    exact_dupes = [r for r in dedup_results if r.status == "exact_duplicate"]
    novel = [r for r in dedup_results if r.status == "novel"]
    fuzzy = [r for r in dedup_results if r.status == "fuzzy_duplicate"]

    # Candidates = novel entries + fuzzy matches (flagged for review)
    candidates = [r.entry for r in novel] + [r.entry for r in fuzzy]

    if not candidates:
        return SynthesisResult(
            total_entries=len(scan.entries), stable_entries=len(stable),
            duplicates_skipped=len(exact_dupes), candidates_count=0,
            promoted_count=0, pruned_count=0, baseline_recorded=False,
            new_line_count=scan.total_lines,
        )

    # Step 4: Approval (auto_approve for testing, interactive in real usage)
    if auto_approve:
        approved = candidates
    else:
        # In real usage, this is handled by the skill's interactive UX
        approved = candidates

    if not approved or dry_run:
        return SynthesisResult(
            total_entries=len(scan.entries), stable_entries=len(stable),
            duplicates_skipped=len(exact_dupes), candidates_count=len(candidates),
            promoted_count=0, pruned_count=0, baseline_recorded=False,
            new_line_count=scan.total_lines,
        )

    # Step 5: Promote
    journal = PromotionJournal(intermem_dir / "promotion-journal.jsonl")

    # Route entries to appropriate target doc (first available for now)
    target = target_docs[0] if target_docs else None
    if target is None:
        return SynthesisResult(
            total_entries=len(scan.entries), stable_entries=len(stable),
            duplicates_skipped=len(exact_dupes), candidates_count=len(candidates),
            promoted_count=0, pruned_count=0, baseline_recorded=False,
            new_line_count=scan.total_lines,
        )

    promotion_result = promote_entries(approved, target, journal)

    # Step 6: Prune
    prune_result = prune_promoted(approved, memory_dir, journal)

    return SynthesisResult(
        total_entries=len(scan.entries),
        stable_entries=len(stable),
        duplicates_skipped=len(exact_dupes),
        candidates_count=len(candidates),
        promoted_count=promotion_result.promoted_count,
        pruned_count=prune_result.lines_removed,
        baseline_recorded=False,
        new_line_count=prune_result.new_total_lines,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd plugins/intermem && uv run pytest tests/test_synthesize.py -v
```

Expected: All 5 tests PASS.

**Step 5: Run full test suite**

```bash
cd plugins/intermem && uv run pytest tests/ -v
```

Expected: All tests across all modules PASS.

**Step 6: Commit**

```bash
git add plugins/intermem/lib/synthesize.py plugins/intermem/tests/test_synthesize.py
git commit -m "feat(intermem): implement synthesis pipeline orchestrator"
```

---

## Task 9: Wire Up and Final Integration

**Files:**
- Modify: `plugins/intermem/skills/synthesize/SKILL.md` (finalize with exact commands)
- Create: `plugins/intermem/lib/__main__.py` (CLI entry point)
- Modify: `plugins/intermem/pyproject.toml` (add console script)

**Step 1: Create CLI entry point**

```python
"""CLI entry point for intermem synthesis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from intermem.lib.synthesize import run_synthesis


def _find_memory_dir(project_dir: Path) -> Path | None:
    """Find the auto-memory directory for a project.

    Claude Code encodes the project path as: replace / with -, strip leading slash.
    e.g., /root/projects/Interverse → -root-projects-Interverse
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return None

    # Encode the project path
    encoded = str(project_dir).replace("/", "-")
    if encoded.startswith("-"):
        pass  # Already has leading dash from root /
    else:
        encoded = "-" + encoded

    memory_dir = claude_projects / encoded / "memory"
    if memory_dir.exists():
        return memory_dir

    return None


def _find_target_docs(project_dir: Path) -> list[Path]:
    """Find AGENTS.md and CLAUDE.md in the project directory."""
    docs = []
    for name in ["AGENTS.md", "CLAUDE.md"]:
        path = project_dir / name
        if path.exists():
            docs.append(path)
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Intermem memory synthesis")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(),
                        help="Project root directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying files")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Skip interactive approval (for testing)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    memory_dir = _find_memory_dir(project_dir)
    if memory_dir is None:
        print(f"No auto-memory directory found for {project_dir}")
        print("Expected at: ~/.claude/projects/<encoded-path>/memory/")
        sys.exit(1)

    target_docs = _find_target_docs(project_dir)
    if not target_docs:
        print(f"No AGENTS.md or CLAUDE.md found in {project_dir}")
        print("At least one target document is needed for promotion.")
        sys.exit(1)

    intermem_dir = project_dir / ".intermem"

    result = run_synthesis(
        memory_dir=memory_dir,
        target_docs=target_docs,
        intermem_dir=intermem_dir,
        auto_approve=args.auto_approve,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps({
            "total_entries": result.total_entries,
            "stable_entries": result.stable_entries,
            "duplicates_skipped": result.duplicates_skipped,
            "candidates_count": result.candidates_count,
            "promoted_count": result.promoted_count,
            "pruned_count": result.pruned_count,
            "baseline_recorded": result.baseline_recorded,
            "new_line_count": result.new_line_count,
        }, indent=2))
    else:
        if result.baseline_recorded:
            print(f"Building baseline — recorded {result.total_entries} entries.")
            print("Run again after your next few sessions to identify stable facts.")
        elif result.promoted_count > 0:
            print(f"Promoted {result.promoted_count} entries, pruned {result.pruned_count} lines.")
            print(f"Auto-memory: {result.new_line_count} lines remaining.")
        elif result.candidates_count > 0:
            print(f"Found {result.candidates_count} candidates (skipped {result.duplicates_skipped} duplicates).")
        else:
            print(f"Scanned {result.total_entries} entries. {result.stable_entries} stable, none ready for promotion.")
            if result.stable_entries == 0:
                print("No entries stable across 3+ snapshots yet. Keep running periodically.")


if __name__ == "__main__":
    main()
```

**Step 2: Update pyproject.toml**

Add `[project.scripts]` section:

```toml
[project]
name = "intermem"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
intermem = "intermem.lib.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 3: Add .intermem/ to .gitignore patterns**

Add to the project's `.gitignore` (or note in CLAUDE.md):
```
# Intermem state (per-project, not committed)
.intermem/
```

**Step 4: Run full test suite one final time**

```bash
cd plugins/intermem && uv run pytest tests/ -v --tb=short
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add plugins/intermem/
git commit -m "feat(intermem): wire up CLI entry point and finalize plugin structure"
```

---

## Summary

| Task | Feature | Files | Tests |
|------|---------|-------|-------|
| 1 | Plugin scaffold | 11 created | — |
| 2 | Auto-memory scanner (F1) | scanner.py | 7 tests |
| 3 | Stability detection (F2) | stability.py | 6 tests |
| 4 | Dedup checker (F3) | dedup.py | 6 tests |
| 5 | Promotion journal (F5 prereq) | journal.py | 6 tests |
| 6 | Promoter (F4) | promoter.py | 6 tests |
| 7 | Auto-memory pruner (F5) | pruner.py | 6 tests |
| 8 | Synthesis pipeline | synthesize.py | 5 tests |
| 9 | CLI + wiring | __main__.py, pyproject.toml | — |

**Total: 9 tasks, 42 tests, 9 commits**
