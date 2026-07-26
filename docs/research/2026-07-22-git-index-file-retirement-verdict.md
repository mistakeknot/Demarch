# Retirement verdict: bespoke `GIT_INDEX_FILE` machinery — replaced, not layered

**Goal:** sylveste-n2ma (worktree-first canonicalization), condition element 1.
**Date:** 2026-07-22
**Question (from Sylveste-4b5.4):** Does Claude Code's native worktree primitive REPLACE Sylveste's hand-rolled `GIT_INDEX_FILE` machinery, or merely layer atop it?

## Verdict

**REPLACED.** The bespoke `GIT_INDEX_FILE` per-session-index machinery is fully retired from executable code. No additive worktree config may reintroduce it; the corrective half of n2ma is a confirm-and-document step, not a code-removal one.

## Evidence

### 1. No executable `GIT_INDEX_FILE` use remains
A tree-wide grep across `os/ interverse/ core/` for `GIT_INDEX_FILE` in `*.sh`, `*.go`, `*.py` returns exactly two files, and neither *uses* it:

- `interverse/interlock/tests/structural/test_structure.py` — **asserts its absence** (regression guard, see below).
- `interverse/interspect/tests/shell/test_tool_remediation.sh:24` — a **comment** describing Claude Code's *own* injected `git` shell-function wrapper (`env -u GIT_INDEX_FILE command git`), which the test *clears* (`unset -f git`) so git works in `/tmp`. This is CC-injected, not Sylveste machinery.

All other matches (11 files total) are historical handoff/solution docs.

### 2. A regression test guards the absence (sylveste-4pth)
`interlock/tests/structural/test_structure.py::TestMultiSessionCoordination` asserts, and these assertions PASS against current code:
- `test_session_start_does_not_install_git_function_wrapper` — `export GIT_INDEX_FILE=` absent, `export -f git` absent, `git()` absent. Docstring: "Regression test for sylveste-4pth: git function wrappers with a per-session index can still commit stale trees."
- `test_precommit_does_not_refresh_session_index`, `test_postcommit_does_not_refresh_session_index` — the per-session index refresh is gone.

sylveste-4pth is the stealth-revert disaster (multi-agent index pollution committing stale trees; solution doc `interlock/docs/solutions/git/stealth-revert-via-multi-agent-index-pollution-20260505.md`). The machinery that caused it is provably gone and guarded.

### 3. Git history: a two-stage retirement
```
264daf0 fix(hooks): scope GIT_INDEX_FILE to project root, don't export globally
44a51dd fix(session-start): skip git index isolation in nested repos
eca7789 fix(hooks): detect git -C/--git-dir/--work-tree to skip index isolation
f1c79a2 Replace session index isolation with worktrees        # wrapper → worktrees (tests updated)
d0e799d feat(0.2.16): shared-filesystem coordination, drop leaky per-session worktrees  # worktrees → shared-fs (tests NOT updated)
```
Stage 1 (`f1c79a2`): the `GIT_INDEX_FILE` wrapper was replaced by native `git worktree add`. Stage 2 (`d0e799d`, 0.2.16): interlock then dropped its own per-session worktree too, moving to **shared-filesystem coordination** (file reservations + a commit lock), because unconditional per-session worktrees leaked GB of orphans and were redundant with consuming projects' own worktree discipline.

## Consequence for the contract (two findings)

**Finding A — interlock is the COORDINATION layer, native worktrees are the ISOLATION layer.** interlock deliberately does NOT create worktrees now (`session-start.sh:22` "Interlock no longer creates a per-session git worktree"); it coordinates agents that *share* a working tree via reservations + commit serialization. The canonical contract must state this split cleanly: native CC worktrees isolate file edits; interlock coordinates when agents share a tree. They are complementary, not alternatives.

**Finding B — interlock's structural tests drifted red at 0.2.16 (test debt).** 7 tests in `TestMultiSessionCoordination` still assert the abandoned `f1c79a2` worktree spec (`INTERLOCK_SESSION_WORKTREE`, `session_worktree_path()`, `worktree add`, `git worktree remove`) and FAIL against the current shared-fs code, because `d0e799d` updated the code but not the tests. These are stale-since-0.2.16, not new breakage. Reconciling them to shared-fs reality is in-scope for this goal (interlock is the coordination layer the contract describes) — tracked as element-3/4 work, done carefully to preserve the sylveste-4pth guards (which stay green).

## Bottom line
Native worktrees + interlock shared-fs coordination have jointly replaced the bespoke `GIT_INDEX_FILE` machinery. No layer sits atop it because it no longer exists. Element 1 satisfied.
