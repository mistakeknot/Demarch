# Intermap Live Changes Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Harden `live_changes` correctness and observability while delivering `>=30%` repeated-call median latency improvement without breaking API behavior.

**Architecture:** Keep the public tool contract unchanged and incrementally improve internals in `python/intermap/live_changes.py`. Add deterministic regression fixtures for symbol mapping, implement structured extraction-failure logging, and introduce a guarded optimization path with a legacy fallback mode for rollback safety.

**Tech Stack:** Python 3, pytest, git diff subprocess integration, Intermap extractors, standard logging.

**Prior Learnings:**
- `interverse/intermap/docs/research/quality-review-of-sprint.md` — symbol overlap correctness and silent exception swallowing are known quality gaps; encode as mandatory regression + logging tests before optimization.
- `interverse/intermap/docs/research/performance-review-of-sprint.md` — repeated sequential git subprocess calls are a primary latency driver; prioritize low-risk subprocess/parse reduction and lightweight caching.
- `interverse/intermap/docs/research/review-intermap-correctness.md` — preserve timeout discipline and deterministic behavior; avoid introducing blocking/unstable runtime paths.

---

### Task 1: Correctness Regression Fixtures for Symbol Mapping

**Files:**
- Modify: `interverse/intermap/python/tests/test_live_changes.py`
- Modify: `interverse/intermap/python/intermap/live_changes.py`

**Step 1: Write failing regression tests**

Add tests for required fixtures:
- `test_symbol_annotation_body_edit_marks_enclosing_function`
- `test_symbol_annotation_method_body_edit_marks_class_method`
- `test_symbol_annotation_pure_deletion_does_not_false_mark_symbols`
- `test_symbol_annotation_non_python_file_has_no_symbol_annotations`

Each test should initialize a temporary git repo fixture, create baseline commit(s), apply targeted edits, call `get_live_changes(...)`, and assert expected `symbols_affected` behavior.

**Step 2: Run tests to verify they fail against current logic**

Run:
```bash
cd /home/mk/projects/Demarch/interverse/intermap
PYTHONPATH=python python3 -m pytest python/tests/test_live_changes.py -k "body_edit or method_body or pure_deletion or non_python" -v
```
Expected: At least one new regression test fails due to current def-line-only symbol matching behavior.

**Step 3: Implement minimal correctness fix in `live_changes.py`**

Implement symbol-overlap logic based on changed line ranges and symbol spans (function/class/method coverage), while keeping existing output keys unchanged.

**Step 4: Re-run correctness tests**

Run the command from Step 2.
Expected: All new regression tests pass.

**Step 5: Commit**

```bash
git -C /home/mk/projects/Demarch/interverse/intermap add python/intermap/live_changes.py python/tests/test_live_changes.py
git -C /home/mk/projects/Demarch/interverse/intermap commit -m "test+fix: harden live_changes symbol overlap regression coverage"
```

### Task 2: Structured Observability for Extraction Failures

**Files:**
- Modify: `interverse/intermap/python/intermap/live_changes.py`
- Modify: `interverse/intermap/python/tests/test_live_changes.py`

**Step 1: Write failing observability test**

Add a test using `caplog` and extractor monkeypatching to force extraction failure and assert a structured debug log entry is emitted with:
- logger `intermap.live_changes`
- event/message `live_changes.extractor_error`
- fields: `file`, `project_path`, `baseline`, `error_type`, `error_message`

**Step 2: Run targeted observability test and verify failure**

Run:
```bash
cd /home/mk/projects/Demarch/interverse/intermap
PYTHONPATH=python python3 -m pytest python/tests/test_live_changes.py -k "extractor_error or caplog" -v
```
Expected: Fails before implementation.

**Step 3: Implement structured logging contract**

Update exception handling in `get_live_changes` to emit the required structured debug event without failing the whole tool call.

**Step 4: Re-run observability and regression tests**

Run:
```bash
cd /home/mk/projects/Demarch/interverse/intermap
PYTHONPATH=python python3 -m pytest python/tests/test_live_changes.py -v
```
Expected: Pass.

**Step 5: Commit**

```bash
git -C /home/mk/projects/Demarch/interverse/intermap add python/intermap/live_changes.py python/tests/test_live_changes.py
git -C /home/mk/projects/Demarch/interverse/intermap commit -m "feat: add structured extractor error observability for live_changes"
```

### Task 3: Performance Optimization + Guarded Rollback Mode

**Files:**
- Modify: `interverse/intermap/python/intermap/live_changes.py`
- Create: `interverse/intermap/python/tests/test_live_changes_perf.py`
- Modify: `interverse/intermap/python/tests/test_live_changes.py`

**Step 1: Write perf benchmark harness (initially failing threshold)**

Create `test_live_changes_perf.py` to:
- Build synthetic repo fixture with >=10 changed Python files and 5 unchanged files
- Execute 35 repeated identical `get_live_changes` calls (`baseline="HEAD~1"`)
- Drop first 5 warmups
- Compare medians for baseline vs optimized path
- Capture environment metadata and baseline provenance (commit SHA + mode)

**Step 2: Run perf benchmark to capture baseline**

Run:
```bash
cd /home/mk/projects/Demarch/interverse/intermap
PYTHONPATH=python python3 -m pytest python/tests/test_live_changes_perf.py -q
```
Expected: Baseline metrics recorded; threshold not met before optimization.

**Step 3: Implement low-risk optimizations + fallback mode**

Add incremental performance improvements (e.g., reduced subprocess overhead / parse reuse / short-lived diff cache) and guarded mode switch:
- `INTERMAP_LIVE_CHANGES_MODE=optimized|legacy` (default `optimized`)
- `legacy` path preserves pre-optimization behavior for rollback

**Step 4: Re-run benchmark and verify threshold**

Run command from Step 2.
Expected: `>=30%` median latency improvement on repeated identical calls, with correctness suite still green.

**Step 5: Commit**

```bash
git -C /home/mk/projects/Demarch/interverse/intermap add python/intermap/live_changes.py python/tests/test_live_changes.py python/tests/test_live_changes_perf.py
git -C /home/mk/projects/Demarch/interverse/intermap commit -m "perf: optimize live_changes repeated calls with guarded legacy fallback"
```

### Task 4: Final Verification + Documentation Evidence

**Files:**
- Modify: `interverse/intermap/docs/research/performance-review-of-sprint.md`
- Modify: `interverse/intermap/docs/research/quality-review-of-sprint.md`

**Step 1: Run full targeted test suite for touched areas**

Run:
```bash
cd /home/mk/projects/Demarch/interverse/intermap
PYTHONPATH=python python3 -m pytest python/tests/test_live_changes.py python/tests/test_live_changes_perf.py -v
```
Expected: Pass.

**Step 2: Record benchmark evidence + rollback note**

Append benchmark summary (baseline median, optimized median, improvement %, commit SHA, mode) and rollback instructions using `INTERMAP_LIVE_CHANGES_MODE=legacy` to research docs.

**Step 3: Run go/python sanity check**

Run:
```bash
cd /home/mk/projects/Demarch/interverse/intermap
go build ./...
```
Expected: Build succeeds.

**Step 4: Commit docs and verification updates**

```bash
git -C /home/mk/projects/Demarch/interverse/intermap add docs/research/performance-review-of-sprint.md docs/research/quality-review-of-sprint.md
git -C /home/mk/projects/Demarch/interverse/intermap commit -m "docs: capture live_changes hardening benchmark and rollback guidance"
```
