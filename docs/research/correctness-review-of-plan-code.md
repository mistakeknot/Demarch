# Correctness Review: Intermem Memory Synthesis Implementation Plan

**Reviewed file:** `/root/projects/Interverse/intermem/docs/plans/2026-02-17-intermem-memory-synthesis.md`
**Review date:** 2026-02-17
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Severity scale:** P0 = data corruption / silent loss; P1 = logic defect producing wrong results; P2 = edge-case failure; P3 = code smell with future risk

---

## Invariants This System Must Preserve

Before touching any finding, state the invariants. Every correctness decision flows from these.

1. **Promotion-prune atomicity** — An entry must never be simultaneously absent from auto-memory AND absent from the target doc. Either it is in exactly one place, or it is in both (transient). If the process dies between promote and prune, recovery must detect and complete the prune.

2. **Content identity** — The pruner removes exactly the content that was promoted, nothing more. Partial or over-removal is data loss.

3. **Stability threshold correctness** — "Stable" means the entry's hash appeared in at least 3 distinct snapshots. The scoring function must count distinct snapshot appearances by hash, not by entry identity.

4. **No silent dedup drop** — The PRD explicitly states fuzzy matches (>80%) must go to interactive review, never be silently dropped. The dedup function must not lose novel or fuzzy entries during candidate construction.

5. **Journal append-only monotonicity** — Reading a journal back after N writes and M reloads must produce the same logical state as after N writes on a fresh instance. The JSONL load must handle the state-machine's update-in-place semantics correctly.

6. **Scanner preserves entry boundaries** — Multi-line entries (code blocks, continuation lines) must be treated as a single atomic unit throughout the pipeline, from scan through prune.

---

## Findings

### P0-A: Journal Load Loses Intermediate State Transitions (journal.py)

**Location:** `lib/journal.py`, `_load()` method, lines ~992-1001

**The defect:**

```python
def _load(self) -> None:
    if not self.path.exists():
        return
    for line in self.path.read_text().splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        entry = JournalEntry(**data)
        self._entries[entry.entry_hash] = entry  # Last write wins
```

The JSONL file is an append-only log. For a given `entry_hash`, there will be multiple lines: one for `pending`, one for `committed`, one for `pruned`. The `_load()` method iterates them in order and overwrites `self._entries[entry.entry_hash]` with each new line. The last line for a hash wins.

For entries that completed the full lifecycle (pending → committed → pruned), the last line is `pruned` — correct.

But here is the crash-recovery scenario this journal is specifically designed to handle:

**Crash scenario:**

1. Write `pending` line to JSONL → flush succeeds
2. Write entry to target doc (AGENTS.md) → succeeds
3. Write `committed` line to JSONL → flush succeeds
4. Process crashes before prune

On restart, `_load()` reads the file. For this entry, the last line in the file is `committed`. `_entries[hash]` is set to the `committed` record. `get_incomplete()` correctly returns it as incomplete (`status != "pruned"`). So far so good.

**The real crash scenario (pending, no commit):**

1. Write `pending` line to JSONL → succeeds
2. Write entry to target doc → **process crashes mid-write**

On restart, target doc may have partial content. `_load()` reads the journal. Entry is `pending`. `get_incomplete()` returns it. The recovery code (which is not implemented in this plan) would need to re-do the promotion. If it does, it appends another `pending` line, then a `committed` line. The last write wins logic now handles this correctly.

**The actual P0 failure — double-pending duplication:**

There is no guard in `record_pending()` against recording a `pending` entry for a hash that is already `pending` or `committed` in the in-memory dict. If `run_synthesis()` is called twice in rapid succession (e.g., user runs the skill twice before the first run completes, or in a test loop), and the same entry hash appears in both runs, the second call will call `record_pending(h, ...)` which appends another `pending` line without checking the current state.

Now the JSONL contains:
```
{"entry_hash": "abc", "status": "pending", ...}   ← run 1
{"entry_hash": "abc", "status": "committed", ...}  ← run 1 commits
{"entry_hash": "abc", "status": "pending", ...}    ← run 2 re-journals (WRONG)
```

After `_load()` on a fresh `PromotionJournal`, the last line wins: entry appears `pending`. `get_incomplete()` returns it. But the entry is already in the target doc (from run 1). Attempting to promote it again **inserts a duplicate line into AGENTS.md**.

**Fix:** `record_pending()` must check if the entry is already committed or pruned in `self._entries` and refuse:

```python
def record_pending(self, entry_hash: str, ...) -> None:
    existing = self._entries.get(entry_hash)
    if existing and existing.status in ("committed", "pruned"):
        return  # Already processed; do not re-journal
    self._append(JournalEntry(..., status="pending", ...))
```

---

### P0-B: Promotion and Prune Use Different Hash Functions (promoter.py vs pruner.py)

**Location:** `lib/promoter.py` `_hash_content()`, `lib/pruner.py` `_hash_content()`, `lib/stability.py` `_hash_entry()`

**The defect:**

Three separate `_hash_content()` / `_hash_entry()` functions exist across three modules, and they are NOT identical:

`stability.py`:
```python
def _hash_entry(entry: MemoryEntry) -> str:
    return hashlib.sha256(entry.content.strip().encode()).hexdigest()[:16]
```

`promoter.py`:
```python
def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]
```

`pruner.py`:
```python
def _hash_content(content: str) -> str:
    return hashlib.sha256(content.strip().encode()).hexdigest()[:16]
```

The promoter calls `_hash_content(entry.content)` and journals with that hash. The pruner calls `_hash_content(entry.content)` with the same entry object and tries to call `journal.mark_pruned(h)`. This looks consistent.

But consider: the promoter journals the entry at promotion time. The pruner receives the same `MemoryEntry` objects from the synthesizer. Are they the same objects with identical `.content`? They should be — but only if the pruner is called in the same Python process with the same entry list.

**The real failure mode:** The pruner has a `try/except KeyError: pass` guard:

```python
try:
    journal.mark_pruned(h)
except KeyError:
    pass  # Entry might have a different hash in journal
```

The comment acknowledges that the hash might differ. This silent swallow means: if the hash computed by the pruner does not match the hash stored in the journal by the promoter, `mark_pruned` is never called, **the journal entry stays "committed" forever**, and on the next run `get_incomplete()` returns it as incomplete. The recovery path (not implemented) would then attempt to re-promote the already-promoted entry, inserting a duplicate into AGENTS.md.

**Why would hashes differ?** The promoter stores `entry.content` stripped. The entry object passed to the pruner is the same Python object — content is identical. In the current single-process flow this is fine. But if the journal is reloaded and content is reconstructed from the journal's `content` field (in future recovery code), the `content` field is the raw `entry.content`, not the stripped version used to compute the hash. This is a latent time bomb.

**Fix:** Extract `_hash_content` into a single function in a shared `lib/common.py` or `lib/hashing.py`, and have all three modules import it. Verify the function takes the exact same input representation. Never silently swallow `KeyError` in journal operations — raise with context or log and abort.

---

### P0-C: Pruner Removes by Content Match Across the Entire File, Not by Position

**Location:** `lib/pruner.py`, `prune_promoted()`, lines ~1519-1537

**The defect:**

```python
remove_contents = {e.content.strip() for e in file_entries}

while i < len(raw_lines):
    line = raw_lines[i]
    matched = False
    for content in remove_contents:
        entry_lines = content.splitlines()
        if i + len(entry_lines) <= len(raw_lines):
            candidate = raw_lines[i:i + len(entry_lines)]
            if [l.strip() for l in candidate] == [l.strip() for l in entry_lines]:
                # Remove this block
```

The pruner matches by content, scanning the whole file. If the **same text appears twice** in auto-memory (two identical entries in different sections, which can happen if a user accidentally duplicates a lesson), the pruner removes **both occurrences** even though only one was promoted. This violates the invariant that the pruner removes exactly what was promoted.

Additionally, the `MemoryEntry` dataclass stores `source_file`, `start_line`, and `end_line`. The pruner ignores these entirely and does a content-based scan. This means: if the entry content is a substring of another entry's content (e.g., a short fact whose text appears verbatim as a prefix of a longer multi-line entry), the match condition `[l.strip() for l in candidate] == [l.strip() for l in entry_lines]` would NOT match (length differs) — but it would match the short entry's lines within a longer multi-line block if those lines happen to appear at position `i`.

**The stricter failure:** Stripping whitespace for comparison (`l.strip()`) means that an entry like `- Fact A` and `    - Fact A` (with leading indent) are treated as identical content. A deeply nested list item could accidentally match a top-level entry.

**Fix:** Use the `start_line` and `end_line` from the `MemoryEntry` to anchor the removal to a specific position, with content verification as a sanity check. If position and content both match, prune. If content matches but position does not, log a warning and skip (do not prune). This is a safer strategy than content-scan-the-whole-file.

---

### P0-D: Promoter Writes Target File Inside a Section Loop — Interleaved Failure Window

**Location:** `lib/promoter.py`, `promote_entries()`, lines ~1253-1296

**The defect:**

```python
for section_name, section_entries in by_section.items():
    # Journal all entries as pending first
    for entry in section_entries:
        h = _hash_content(entry.content)
        journal.record_pending(h, target_path.name, section_name, entry.content)

    # ... build insert_text ...

    # Write the file
    target_path.write_text(content)

    # Journal all entries as committed
    for entry in section_entries:
        h = _hash_content(entry.content)
        journal.mark_committed(h)
```

The loop iterates over sections. For each section:
1. Journal entries as `pending`
2. Write the full file (with accumulated content)
3. Journal entries as `committed`

When there are multiple sections (e.g., entries for "CLI" and "Git Workflow"), the sequence is:

```
Section "CLI":
  - journal CLI entries as pending
  - write file (CLI entries appended)
  - journal CLI entries as committed

Section "Git Workflow":
  - journal Git entries as pending
  - write file (Git entries appended to already-modified file)
  - journal Git entries as committed
```

**Crash after "write file" for section 1, before section 2 is processed:**
- File on disk has CLI entries (good)
- CLI entries are `committed` in journal
- Git entries have NOT been journaled yet (they're still unprocessed)
- On restart, `get_incomplete()` returns only the CLI committed entries (if recovery exists)
- Git entries were never journaled and are silently dropped — they will never be promoted unless the user runs synthesis again

This is acceptable for the synthesize pipeline (re-run is safe), but the comment "uses WAL-style journal for atomicity" implies the journal provides recovery guarantees. It does not for multi-section promotions.

**More dangerous:** If two sections have entries that overlap in content (unlikely but possible), the second `target_path.write_text(content)` call uses the `content` variable that was modified by the first section's insertion. The regex pattern for section matching:

```python
section_pattern = re.compile(
    rf'^(## {re.escape(section_name)}\s*\n)(.*?)(?=^## |\Z)',
    re.MULTILINE | re.DOTALL,
)
```

This pattern is compiled fresh per section and applied to the current (already-modified) `content` string. This is correct — it operates on the accumulating content. But there is a subtle issue: the `(?=^## |\Z)` lookahead requires `^` to match start-of-line, which requires `re.MULTILINE`. This flag is set. However, the pattern uses `.*?` (non-greedy, DOTALL) to capture section body. If two consecutive `## SectionA` headings exist (perhaps from a prior promotion that created a section), the pattern would match the first one's body as everything up to the second heading's start. This is correct behavior — but only if the regex engine correctly handles the interplay of DOTALL and MULTILINE with the lookahead.

**Concrete failure:** If a section heading appears in the content of an entry (e.g., an entry contains the text `## Build` as part of a code example or description), the regex `(?=^## |\Z)` could be fooled into thinking the section ends at that in-content heading. The content variable would be sliced at the wrong point, and `insert_pos` would be incorrect, causing the new entry to be inserted in the middle of a section body rather than at its end.

**Fix:** Parse the document into a structured list of (heading, body) tuples once, modify the structure, then serialize back to text. Do not re-parse with regex after each modification.

---

### P1-A: Stability Scoring Has an Off-by-One: "Volatile" Mislabels Genuinely New Entries

**Location:** `lib/stability.py`, `score_entries()`, lines ~618-627

**The defect:**

```python
elif count == 1 and len(store.snapshots) >= 2:
    # Only in the latest snapshot — could be volatile (changed) or genuinely new
    # Simple heuristic: if total snapshots > 1 and this hash is only in the latest, mark volatile
    scores.append(StabilityScore(entry=entry, score="volatile", snapshot_count=count))
else:
    scores.append(StabilityScore(entry=entry, score="recent", snapshot_count=count))
```

Consider the scenario from `test_new_entry_scores_recent`:
- Snapshot 1: {old_fact}
- Snapshot 2: {old_fact}
- Snapshot 3: {old_fact, brand_new}

After snapshot 3 is recorded, `score_entries` is called with `[old_fact, brand_new]`.

For `brand_new`: `count = 1` (appears only in snapshot 3), `len(store.snapshots) = 3 >= 2`. The code labels it `volatile`.

The test asserts `scores[1].score == "recent"` — but the implementation returns `volatile`. The test would **FAIL**.

The code comment says "could be volatile (changed) or genuinely new" and acknowledges the ambiguity, but the chosen resolution (mark volatile) contradicts the test expectation. The PRD says entries not seen in previous snapshots should score "recent".

The test `test_new_entry_scores_recent` is correct per the PRD. The implementation is wrong.

**Why this matters for correctness:** Labeling a brand-new entry `volatile` means it will never be promoted, even after 10 more sessions. The user adds a new lesson, runs synthesis immediately, it gets branded `volatile`, and the stability system has no path to recover it to `stable` because its hash cannot accumulate 3 appearances while being constantly labeled `volatile`. It is permanently suppressed.

**Fix:** Distinguish "volatile" (a hash that replaced a different hash for what appears to be the same logical entry) from "new" (no prior hash at all for this entry). Since entries are tracked only by content hash and not by identity, the only safe heuristic is: if the hash appears for the first time, it is `recent`, regardless of how many snapshots exist. Volatile scoring requires comparing whether a similar hash existed in prior snapshots — which requires fuzzy matching at the stability layer, not just exact hash lookup.

The minimal fix: remove the `count == 1 and len >= 2 → volatile` branch. Any entry with count < 3 that is not already `volatile` is `recent`. The `volatile` label requires a separate mechanism to identify "this entry changed from a prior version."

---

### P1-B: `score_entries` is Called After `record_snapshot` — Scores Include the Current Snapshot

**Location:** `lib/synthesize.py`, `run_synthesis()`, lines ~1862-1873

**The defect:**

```python
stability_store = StabilityStore(intermem_dir / "stability.jsonl")
is_first_run = len(stability_store.snapshots) == 0
record_snapshot(stability_store, scan.entries)   # ← Snapshot N recorded HERE

if is_first_run:
    return ...

scores = score_entries(stability_store, scan.entries)  # ← Counts include snapshot N
stable = [s for s in scores if s.score == "stable"]
```

`record_snapshot` appends the current snapshot to `stability_store._snapshots`. Then `score_entries` counts how many snapshots contain each hash — and the just-recorded snapshot N is already in the list.

Effect on the 3-snapshot threshold:

- After run 1: store has snapshot 1 recorded. `count = 1`. `is_first_run` triggers early return, scoring skipped. Correct.
- After run 2: snapshot 2 is recorded (total: 2). `count = 2`. Entry scores `recent`. Correct (PRD requires 3).
- After run 3: snapshot 3 is recorded (total: 3). `count = 3`. Entry scores `stable`. The code promotes on run 3.

But the PRD says "unchanged across 3+ snapshots" and the SKILL.md says "Run again after your next few sessions." The intent is that the user must run synthesis 3 separate times before promotion occurs — not 3 times counting the very first baseline run plus 2 more.

**This may or may not be a bug depending on intent.** If the first run's baseline counts as snapshot 1, then run 3 achieving stable is correct by the test suite's expectations. The test `test_stable_after_three_snapshots` calls `record_snapshot` 3 times and expects `stable` — which is consistent with the current behavior. The SKILL.md states "the scanner records a baseline snapshot" on first run, implying it counts.

However: `is_first_run` early return prevents scoring after run 1. Scoring starts on run 2, when the count is already 2 (snapshot 1 + snapshot 2). On run 3, count reaches 3 and entry is stable. So the user experiences: "run once (baseline), run again (recent), run a third time (stable, promoted)." Three runs total. This is consistent and defensible.

**What is not defensible:** on the second run, `is_first_run` is false, but the entry has count 2. The current code:
```python
elif count == 1 and len(store.snapshots) >= 2:
    ...volatile...
else:
    ...recent...
```

An entry with count 2 falls into `else → recent`. Correct. This path works as long as the P1-A volatile mislabeling bug above is fixed.

**Actual issue here:** The `is_first_run` check happens BEFORE `record_snapshot`. So on the very first call, `len(stability_store.snapshots) == 0` is true, the snapshot is recorded, then early return fires. The snapshot IS recorded on first run. On the second run, `len(...) == 1` (not 0), so `is_first_run` is false. This is correct. But this also means the comment "First run records baseline — all entries scored 'recent'" is only enforced by early return, not by scoring logic. If someone removes the early return, first-run entries would be scored with count 1, which (after fixing P1-A) would be `recent` anyway. The early return is defensive but not strictly required — which is fine.

**No code change required here if P1-A is fixed.**

---

### P1-C: Dedup Compares Only the First Line of Multi-Line Entries

**Location:** `lib/dedup.py`, `check_duplicates()`, line ~805

**The defect:**

```python
entry_norm = _normalize(entry.content.split("\n")[0])  # Compare first line
```

The comment says "Compare first line." For entries that span multiple lines (e.g., a bullet followed by a code block or continuation lines), the dedup check only compares the first line against target doc content.

**Failure case:**

Auto-memory entry:
```
- Use strace to trace credential issues:
  ```bash
  strace -e trace=openat,rename -f git push 2>&1
  ```
```

AGENTS.md already has this exact entry. The first line is `- Use strace to trace credential issues:` (14 words). AGENTS.md also has just this first line (if it was previously promoted as a single-line entry). The dedup check compares `use strace to trace credential issues:` vs `use strace to trace credential issues:` — exact match. Entry is correctly marked `exact_duplicate`. Correct.

**But consider the inverse:** The full multi-line entry is novel (not in AGENTS.md), but a different single-line entry `- Use strace for git debugging` is already in AGENTS.md. The fuzzy match compares the first line of the candidate against all lines in AGENTS.md. The first line `use strace to trace credential issues:` might score >80% against `use strace for git debugging`. The full entry (which adds meaningful new content — the actual command) is labeled `fuzzy_duplicate` and presented with "[similar to existing]" annotation.

This is merely a UX issue (user sees it for review), not a data loss issue. Novel entries are never silently dropped (P0 invariant 4 holds). This is a P2 issue.

**However:** The dedup target content extraction (`_extract_lines`) also extracts lines from AGENTS.md one at a time. Multi-line entries in AGENTS.md are split into individual lines. Each code block line (e.g., `strace -e trace=openat ...`) is treated as a separate "fact" for comparison. An auto-memory entry whose first line is `- Run with: strace -e trace=openat` would fuzzy-match against the code-block content line — a false positive fuzzy match.

**Fix:** Either compare full entry content against full existing entries (requires parsing AGENTS.md into entry-level units, not lines), or accept the first-line-only limitation and document it. Do not compare code block interior lines from AGENTS.md against entry first lines.

---

### P1-D: Scanner Ignores Code Block Tracking When Code Block Starts with No Active Entry

**Location:** `lib/scanner.py`, `_parse_file()`, lines ~338-347

**The defect:**

```python
if line.strip().startswith("```"):
    in_code_block = not in_code_block
    if current_entry_lines:
        current_entry_lines.append(line)
    continue
```

When `in_code_block` toggles to `True` and `current_entry_lines` is empty (i.e., the code block appears at the top of a section before any bullet point), the code block opening line is NOT appended to `current_entry_lines` (because `current_entry_lines` is empty). The `continue` then skips to the next line.

Inside the code block, subsequent lines hit:
```python
if in_code_block:
    if current_entry_lines:
        current_entry_lines.append(line)
    continue
```

Since `current_entry_lines` is still empty, all code block lines are silently discarded. The closing ` ``` ` toggles `in_code_block` back to `False` and is also discarded.

**Failure case:** Auto-memory file with:
```markdown
## Setup

```bash
export DISPLAY=:99
export CHROME_PATH=/usr/local/bin/google-chrome-wrapper
```

- Use oracle with these env vars
```

The code block (3 lines) is silently dropped. Only `- Use oracle with these env vars` becomes an entry. The critical setup context is lost from the scan output. This content can never be promoted.

**Fix:** When a code block opens and `current_entry_lines` is empty, start a new implicit entry from the code block opening. Or, at minimum, synthesize a synthetic bullet entry containing the orphaned code block so it is preserved in scan output.

---

### P1-E: Scanner Off-By-One in `end_line` for Final Entry

**Location:** `lib/scanner.py`, `_parse_file()`, lines ~386-390

**The defect:**

```python
# Flush final entry
if current_entry_lines:
    entries.append(_make_entry(
        current_entry_lines, current_section, filename, entry_start_line, len(lines)
    ))
```

The final entry's `end_line` is set to `len(lines)`. For a file with N lines, `len(lines)` is N. Lines are 1-indexed (the loop uses `enumerate(lines, start=1)`). So the last line has index N, and `end_line = len(lines)` is correct for the final line.

But `_make_entry` strips trailing blank lines and adjusts `end` downward:

```python
def _make_entry(lines, section, filename, start, end):
    while lines and not lines[-1].strip():
        lines.pop()
        end -= 1
    return MemoryEntry(..., end_line=end)
```

If the file ends without a trailing blank line, `end_line = len(lines)` (correct). If it ends with blank lines, `end` is decremented for each stripped blank line. This is correct behavior for trimming.

**However:** `_make_entry` mutates the `lines` list in place (`lines.pop()`). The caller owns this list — it is the `current_entry_lines` accumulator. After `_make_entry` returns, `current_entry_lines` has been mutated. Since this happens only at flush time (after which `current_entry_lines` is not reused), this is a benign mutation. But it is poor practice and could cause issues if `_make_entry` is called in contexts where the caller reuses the list.

**The actual off-by-one:** Non-final entries use `i - 1` as `end_line`:

```python
if line.startswith("## "):
    if current_entry_lines:
        entries.append(_make_entry(
            current_entry_lines, current_section, filename, entry_start_line, i - 1
        ))
```

When a `##` heading is encountered at line `i`, the previous entry ended at line `i-1`. But the `in_code_block` tracking: the ` ``` ` line that closes a code block sets `in_code_block = False` and does a `continue`. If the next line after the closing ` ``` ` is `## NewSection`, the flush happens at `i - 1` where `i` is the `##` line. `i - 1` is the blank line between ` ``` ` and `##`. The code block closing line ` ``` ` is at `i - 2`. `_make_entry` strips trailing blank lines. So `end_line` ends up at the closing ` ``` ` line — correct.

No actual corruption here. P3 for the mutation of input argument.

---

### P2-A: Promoter Regex Does Not Account for Entries Inserted with `<!-- intermem -->` Marker

**Location:** `lib/promoter.py`, section insertion regex

**The defect:**

The promoter appends entries with `{entry.content} <!-- intermem -->`. On subsequent synthesis runs, the scanner reads the auto-memory file and finds `- Some fact <!-- intermem -->` as the content of an entry (after a successful prune, this line would be gone from auto-memory, but before pruning, it could appear in AGENTS.md entries if those are ever scanned).

The AGENTS.md file is a target, not a source, so scanning AGENTS.md is not part of the pipeline. However, the dedup checker reads AGENTS.md to extract existing facts. The extraction logic:

```python
for line in path.read_text().splitlines():
    stripped = line.strip()
    if stripped and not stripped.startswith("#"):
        lines.append((stripped, path.name))
```

This extracts `- Some fact <!-- intermem -->` as a raw line. The normalization:

```python
def _normalize(text: str) -> str:
    text = text.strip().lower()
    if text.startswith(("- ", "* ")):
        text = text[2:]
    return text
```

This produces `some fact <!-- intermem -->` as the normalized form. The hash of this string differs from the hash of `some fact` (without the marker). So on the next run, a candidate entry `- Some fact` will NOT match the already-promoted `- Some fact <!-- intermem -->` as an exact duplicate. The fuzzy match ratio between `some fact` and `some fact <!-- intermem -->` is `len("some fact") * 2 / (len("some fact") + len("some fact <!-- intermem -->"))` ≈ 0.72, which is below the 0.80 threshold. The entry would be labeled `novel` and re-promoted, creating a **duplicate entry in AGENTS.md**.

**Fix:** Strip the `<!-- intermem -->` marker from lines before normalization in `_extract_lines`:

```python
stripped = re.sub(r'\s*<!--.*?-->\s*$', '', stripped)
```

Or, strip HTML comments before any comparison operation.

---

### P2-B: Stability Store Appends Without File-Level Locking

**Location:** `lib/stability.py`, `StabilityStore._save_snapshot()`

```python
def _save_snapshot(self, snapshot: dict) -> None:
    self._snapshots.append(snapshot)
    self.path.parent.mkdir(parents=True, exist_ok=True)
    with self.path.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
```

There is no file lock. The plugin is described as single-agent, user-initiated only ("No multi-agent coordination — single-agent operation only"). In practice, two concurrent terminal sessions running `/intermem:synthesize` simultaneously (e.g., user fires it twice in different Claude Code windows in the same project) would race on the JSONL append. Python's `open("a")` append mode on Linux is atomic for writes up to PIPE_BUF (4096 bytes) on the same filesystem due to kernel-level append atomicity guarantees. A single JSON line for a typical snapshot is well under 4096 bytes. So concurrent appends would interleave lines without corrupting individual lines, but both processes would read the same initial state (both `_snapshots` lists have the same N entries from load), both would append their snapshots independently, and the JSONL would end up with N+2 snapshots instead of N+2 correct ordered snapshots. This is a P2 not P0 because the append atomicity of Linux filesystem protects individual lines, and extra snapshots do not corrupt the stability count (they inflate it, which is conservative).

---

### P2-C: Pruner Does Not Verify Target File Integrity Before Prune

**Location:** PRD F5 acceptance criteria vs. `lib/pruner.py` implementation

**The defect:**

The PRD says:
> Re-verifies target file content hash before pruning (detects concurrent edits during approval window)

The implemented `prune_promoted()` function does not verify the target file. It only prunes from the auto-memory source files. The target file verification would require comparing the current content of AGENTS.md against what was written during promotion to confirm the promotion is still intact before pruning the source.

Without this check: if a user manually edits AGENTS.md and removes the just-promoted entry during the approval/prune window, the prune would proceed and the entry would be deleted from both places — violating invariant 1 (entry must be in at least one place).

This is a P2 because the window is narrow (between promotion write and prune, typically milliseconds in the current synchronous implementation) and requires deliberate concurrent manual editing.

---

### P2-D: `_clean_orphaned_headers` Misses Top-Level `#` Headings as Section Boundaries

**Location:** `lib/pruner.py`, `_clean_orphaned_headers()`, lines ~1598-1600

```python
while j < len(lines):
    if lines[j].startswith("## ") or lines[j].startswith("# "):
        break
    if lines[j].strip():
        has_content = True
        break
    j += 1
```

The look-ahead stops at `#` (top-level) headings. But the look-ahead's `has_content` detection checks `lines[j].strip()` — any non-blank line (including `# Title` heading itself) would set `has_content = True` and prevent the orphan cleanup. Wait — no: the heading check `lines[j].startswith("## ") or lines[j].startswith("# ")` comes before the content check and issues `break` immediately. So a top-level heading terminates the look-ahead without setting `has_content`. The `## OrphanSection` would then have no content (just the top-level heading follows), and would be removed.

This seems correct. However: what about `###` (third-level) headings? The orphan checker does not treat `###` as a boundary. A `##` heading followed only by `### Subheading` content (no bullets) would be preserved as non-orphan (the `###` line is non-blank, sets `has_content = True`). This is arguably correct behavior (a section with subsections is not empty). P3 edge case.

---

### P3-A: `run_synthesis` Creates a New `PromotionJournal` Every Invocation — No Recovery Check

**Location:** `lib/synthesize.py`, `run_synthesis()`, line ~1917

```python
journal = PromotionJournal(intermem_dir / "promotion-journal.jsonl")
```

The journal is instantiated fresh on every synthesis run. The `_load()` will read any existing journal entries. `get_incomplete()` would return any previously committed-but-not-pruned entries. However, `run_synthesis()` never calls `journal.get_incomplete()` to check for leftover entries from a crashed prior run before proceeding. It just appends new entries and proceeds.

The PRD says: "On startup, checks for incomplete journal entries and offers to resume or discard." This is not implemented.

---

### P3-B: `_find_memory_dir` Path Encoding Is Fragile

**Location:** `lib/__main__.py`, `_find_memory_dir()`, lines ~1997-2013

```python
encoded = str(project_dir).replace("/", "-")
if encoded.startswith("-"):
    pass  # Already has leading dash from root /
else:
    encoded = "-" + encoded
```

Claude Code encodes project paths as `replace("/", "-")` with the leading `/` becoming a leading `-`. The code handles this by checking `startswith("-")`. But `str(project_dir)` for an absolute path always starts with `/`, which becomes `-` after replace. The `else` branch (prepend `-`) is dead code. The comment "Already has leading dash from root /" is misleading — any absolute path on Linux starts with `/` which maps to `-`.

More importantly: the encoding does NOT account for paths containing spaces (spaces remain as spaces, but Claude Code might encode them differently), paths with non-ASCII characters, or Windows-style paths. On this specific deployment (Linux), this is P3. But if the plugin is distributed more broadly, this could fail silently.

---

### P3-C: Journal `get_incomplete` Returns Entries in Dict Iteration Order — Non-Deterministic in Python < 3.7

**Location:** `lib/journal.py`, `get_incomplete()`

```python
return [e for e in self._entries.values() if e.status != "pruned"]
```

Python 3.7+ guarantees dict insertion order. The plan specifies Python 3.11+. Insertion order is the order of the LAST write for each hash (since `_load()` overwrites the dict key each time). This means entries are ordered by when their final status was recorded, which is nondeterministic relative to the original pending order. For the recovery use case, order doesn't matter (each entry is independent). For the UX display use case (showing users what happened), this could cause confusing output order. P3.

---

## Summary Table

| ID | Severity | Location | Issue |
|----|----------|----------|-------|
| P0-A | P0 | `journal.py` `_load()` | Double-pending allows re-promotion of already-promoted entries → duplicate lines in AGENTS.md |
| P0-B | P0 | `promoter.py`, `pruner.py` | Silent `KeyError` swallow means journal never reaches `pruned` → phantom re-promotion on future runs |
| P0-C | P0 | `pruner.py` content scan | Removes all occurrences of identical content, not just the promoted one → double-removal data loss |
| P0-D | P0 | `promoter.py` section loop | `target_path.write_text(content)` inside section loop; regex applied after prior modifications can match content inside entry text → garbled AGENTS.md |
| P1-A | P1 | `stability.py` `score_entries` | Brand-new entries labeled `volatile` instead of `recent` → permanently suppressed, never promotable |
| P1-B | P1 | `synthesize.py` | `score_entries` called after `record_snapshot`; threshold correct but implicit — also relates to P1-A fix |
| P1-C | P1 | `dedup.py` | First-line-only comparison causes false fuzzy-duplicate hits for multi-line entries vs in-content lines |
| P1-D | P1 | `scanner.py` | Orphaned code blocks (before any bullet) are silently discarded from scan output |
| P2-A | P2 | `promoter.py`, `dedup.py` | `<!-- intermem -->` marker in promoted entries causes dedup to miss already-promoted content → re-promotion on next run |
| P2-B | P2 | `stability.py` | No file lock on JSONL append; concurrent sessions double-count snapshots |
| P2-C | P2 | `pruner.py` | PRD requires target-file integrity check before prune; not implemented |
| P2-D | P2 | `pruner.py` | `_clean_orphaned_headers` has minor boundary behavior around `#` headings |
| P3-A | P3 | `synthesize.py` | No startup journal recovery check; PRD requirement unimplemented |
| P3-B | P3 | `__main__.py` | Path encoding fragile; dead `else` branch; undocumented assumptions |
| P3-C | P3 | `journal.py` | Non-deterministic iteration order for `get_incomplete()` output |

---

## Priority Fixes (Minimum Safe Subset Before Shipping)

These must be fixed before any production use. The P0s can cause silent data corruption.

**Fix 1 (P0-A + P0-B): Centralize hashing and make journal idempotent**

Move `_hash_content`/`_hash_entry` to a single `lib/hashing.py`. Add guard to `record_pending`:
```python
existing = self._entries.get(entry_hash)
if existing and existing.status in ("committed", "pruned"):
    return
```
Remove the `except KeyError: pass` in pruner; replace with a logged error that aborts the prune for that entry.

**Fix 2 (P0-C): Anchor prune to position, verify by content**

Use `entry.start_line` and `entry.end_line` to locate the content. Verify by comparing actual lines at those positions against expected content. Remove only if both match. If they do not match (file changed since scan), log and skip.

**Fix 3 (P0-D): Parse document once, modify structure, serialize once**

Replace the per-section regex loop in `promoter.py` with a single structured parse: split document into `[(heading, body), ...]` tuples, insert into the right tuple, join back. Write the file exactly once.

**Fix 4 (P1-A): Correct volatile scoring**

Remove the `count == 1 and len(snapshots) >= 2 → volatile` branch. Volatile requires evidence that the hash changed. The simplest correct fix: all entries with count < 3 score `recent`. Implement volatile detection separately if desired: if the entry's content is similar (fuzzy) to a hash seen in prior snapshots but with a different exact hash, score `volatile`.

**Fix 5 (P2-A): Strip intermem markers before dedup comparison**

In `_extract_lines`, strip `<!-- ... -->` HTML comments from lines before adding them to the comparison set.
