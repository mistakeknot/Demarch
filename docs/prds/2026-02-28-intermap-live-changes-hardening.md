# PRD: Intermap Live Changes Hardening

## Problem
The current `live_changes` MCP tool can miss important symbol-level change annotations, swallows extraction failures silently, and may be too slow on repeated identical invocations.

## Solution
Harden the existing implementation without breaking the API by improving symbol overlap correctness, making failures observable, and optimizing repeated-call latency.

## Features

### F1: Correctness hardening for symbol annotations
**What:** Improve overlap logic and add regression coverage so changed regions map reliably to affected symbols.

**Acceptance criteria:**
- [ ] Tests cover body-level symbol overlap behavior for changed code regions.
- [ ] Mandatory fixtures are implemented and passing:
  - `test_symbol_annotation_body_edit_marks_enclosing_function`
  - `test_symbol_annotation_method_body_edit_marks_class_method`
  - `test_symbol_annotation_pure_deletion_does_not_false_mark_symbols`
  - `test_symbol_annotation_non_python_file_has_no_symbol_annotations`
- [ ] Output schema remains backward compatible.

### F2: Observability for extraction failures
**What:** Replace silent exception swallowing with structured, non-fatal logging/observability.

**Acceptance criteria:**
- [ ] No broad silent `except Exception: pass` path remains in `live_changes` extraction flow.
- [ ] Failure paths emit structured debug logs with this contract:
  - Logger: `intermap.live_changes`
  - Event key/message: `live_changes.extractor_error`
  - Fields: `file`, `project_path`, `baseline`, `error_type`, `error_message`
  - One log entry per failed file extraction attempt
- [ ] Operator access path is documented in the PR/notes (`intermap-mcp` stderr logs and `pytest` `caplog` validation for unit tests).
- [ ] Tool still returns useful output even when individual file extraction fails.

### F3: Repeated-call performance optimization
**What:** Add low-risk optimizations to reduce repeated identical-call median latency.

**Acceptance criteria:**
- [ ] Benchmark protocol is implemented and reproducible:
  - Command: `PYTHONPATH=python python3 -m pytest python/tests/test_live_changes_perf.py -q`
  - Dataset: synthetic git repo fixture with at least 10 changed Python files and 5 unchanged files
  - Runs: 35 repeated identical invocations (`baseline="HEAD~1"`), discard first 5 warmup runs
  - Metric: median wall-clock latency of the remaining 30 runs
  - Environment notes captured (CPU model, Python version, OS)
  - Baseline provenance captured in benchmark output (commit SHA and `INTERMAP_LIVE_CHANGES_MODE`)
- [ ] Median latency improves by `>=30%` vs baseline.
- [ ] Correctness tests remain green with optimizations enabled.

## Non-goals
- Redesigning the `live_changes` public API.
- Large architectural replacement of the analysis pipeline.
- Introducing risky behavior changes across unrelated Intermap MCP tools.

## Dependencies
- Existing Intermap Python extraction and diff parsing modules.
- Current test harness in `interverse/intermap/python/tests`.
- Git diff availability in test/runtime environments.

## Guardrails / Rollback
- Keep a guarded fallback path during rollout:
  - `INTERMAP_LIVE_CHANGES_MODE=optimized|legacy` (default `optimized`)
  - `legacy` mode preserves pre-optimization behavior for emergency rollback during validation.
- If correctness regressions are detected, rollback criterion is immediate switch to `legacy` mode and follow-up bead for rework.

## Open Questions
- Which optimization gives best gain with lowest complexity (subprocess reduction, parsing reuse, caching strategy) while preserving deterministic output?
- Should the performance benchmark run in CI by default or as an opt-in perf job?
