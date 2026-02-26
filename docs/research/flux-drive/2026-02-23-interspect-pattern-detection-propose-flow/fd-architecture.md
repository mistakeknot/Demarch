# Architecture Review: Interspect Pattern Detection + Propose Flow

**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-interspect-pattern-detection-propose-flow.md`
**Reviewed:** 2026-02-23
**Scope:** 4 new functions in `os/clavain/hooks/lib-interspect.sh` — `_interspect_get_routing_eligible`, `_interspect_get_overlay_eligible`, `_interspect_apply_propose`, `_interspect_is_cross_cutting`

---

## Summary Verdict

The plan is architecturally sound and coherent with the existing library. The patterns it introduces — pre-flock validation, flock-guarded inner locked function, atomic write, dedup-inside-lock — exactly mirror what `_interspect_apply_routing_override` established. Two bugs and three structural concerns require fixes before implementation. The rest is optional cleanup.

---

## 1. Boundaries and Coupling

### What the plan touches

All four functions stay inside `lib-interspect.sh`. They compose five existing primitives:

- `_interspect_get_classified_patterns` — DB query + classification
- `_interspect_is_routing_eligible` — blacklist + 80%-wrong threshold check
- `_interspect_override_exists` — reads routing-overrides.json
- `_interspect_flock_git` — serialized git operations
- `_interspect_validate_agent_name`, `_interspect_validate_overrides_path`, `_interspect_validate_target` — input validation

No new inter-module dependencies are introduced. `lib-interspect.sh` does not touch any other hook library. Boundary integrity is preserved.

### Cross-cutting classification list

`_interspect_is_cross_cutting` hard-codes `fd-architecture|fd-quality|fd-safety|fd-correctness` — the same four agents named as cross-cutting in the Clavain CLAUDE.md (`7 core review agents live in interflux companion`). This is a boundary-correct list as of the plan's date. The absence of `fd-user-product`, `fd-performance`, and `fd-game-design` from the cross-cutting set is consistent with those agents being domain-specific rather than structural.

**Risk:** This list will need updating as agent definitions evolve. A comment linking to the agent registry (or to the confidence.json concept) would make future updates traceable. Currently the list is a magic constant with no pointer to its source of truth.

**Recommendation (must-fix for cross-cutting safety):** Add a comment noting which canonical source defines these agents and what triggers a list update. This does not require code change, just documentation.

---

## 2. Pattern Analysis

### `_interspect_apply_propose` correctly mirrors `_interspect_apply_routing_override`

The propose writer follows the established flock pattern precisely:

1. Pre-flock validation (agent name, evidence_ids type, path safety, target allow-list)
2. Commit message written to temp file before entering flock
3. `_interspect_flock_git` wrapper calls `_interspect_apply_propose_locked`
4. Inside lock: dedup check, JSON build via `jq -n --arg`, atomic temp+mv write, git add + commit with rollback
5. No canary or modification record — intentional lighter weight than exclude

This is the correct behavior. The plan's stated intention ("lighter than apply_routing_override — no canary, no modification record") is implemented consistently.

### Divergence from `_interspect_apply_override_locked` dedup semantics — must-fix

`_interspect_apply_override_locked` (line 748-752) treats a found existing override as an **update** (`is_new=0`, continues with `unique_by(.agent)` merge). `_interspect_apply_propose_locked` (plan Task 3, step 3) treats it as a **skip** and returns `ALREADY_EXISTS` — a string on stdout, not a non-zero exit code.

The caller reads the exit code:

```bash
flock_output=$(_interspect_flock_git _interspect_apply_propose_locked ...)
local exit_code=$?
if (( exit_code != 0 )); then
    echo "ERROR: Could not write proposal. Check git status and retry." >&2
```

When the locked function returns `0` with `ALREADY_EXISTS` on stdout, `exit_code` is `0`. The caller then executes:

```bash
local commit_sha
commit_sha=$(echo "$flock_output" | tail -1)
echo "SUCCESS: Proposed excluding ${agent}. Commit: ${commit_sha}"
```

`commit_sha` becomes the string `ALREADY_EXISTS`, and the success message prints with that as the commit hash. This is a behavioral bug — the caller will silently misreport a skip as a success with a garbage commit SHA.

**Fix:** The locked function should set `exit_code=2` (or any non-zero value) for the skip case, or the caller must detect the `ALREADY_EXISTS` sentinel. Looking at how `_interspect_apply_routing_override` outer function handles its locked variant, the cleanest fix is to have the locked function write the skip message to stderr only and return exit code `2`, then the outer function checks for code `2` and prints the "already exists" message itself without treating it as an error. Alternatively, match what the existing test expects: the test uses `run _interspect_apply_propose` and checks `echo "$output" | grep -qi "already exists"`, which requires the message to appear on stdout or stderr captured by `run`. The current implementation does write to stderr, so bats `run` would capture it in `$output`. The bug is only in the outer function's success path — the outer function needs a sentinel-aware branch.

**Smallest fix in the outer function:**

```bash
# After flock_output captured:
if echo "$flock_output" | grep -q "^ALREADY_EXISTS$"; then
    echo "INFO: Override for ${agent} already exists. Skipping." >&2
    return 0
fi
```

Insert this check before extracting `commit_sha`.

### `_interspect_get_routing_eligible` double-counts DB queries — performance concern

The function pipelines through `_interspect_get_classified_patterns` (one SQLite pass) then for each qualifying agent makes two additional SQLite calls inside the loop (total and wrong counts) to compute `pct`. This redundancy is architecturally wasteful: the classified patterns query already groups by `source|event|override_reason` and produces `ec` (event_count). The wrong count for a specific agent is a subset query that repeats work already done by the grouping.

The plan uses this data to output `agent_wrong_pct` as the fifth column. However, `_interspect_get_classified_patterns` emits one row per `(source, event, override_reason)` tuple — meaning an agent with both `agent_wrong` and `deprioritized` override_reasons produces two rows. The loop processes each row independently, so the `agent_wrong` row produces `ec` = wrong-count events, and a second `total` query to the DB captures all override events for that agent.

This approach is correct but executes N+2 queries per agent in the routing-eligible set. At typical scale (single-digit eligible agents) this is not a problem. It becomes relevant only if the evidence table grows large. This is acceptable for a library function called by interactive skills, not by a tight hook loop.

**Verdict:** No change required for correctness or current scale. Worth a comment noting the query pattern for future optimization.

### `_interspect_get_overlay_eligible` uses associative arrays — Bash 3 incompatibility risk

The function uses `local -A agent_total agent_wrong agent_sessions agent_projects`. Associative arrays (`-A`) require Bash 4.0+. The existing `lib-interspect.sh` does not use associative arrays anywhere else in the file. macOS ships Bash 3.2 by default.

**Check against codebase convention:** The test harness uses `bats` and the setup explicitly references a Linux environment (`/home/mk/...`). The AGENTS.md mentions the server is Linux. The `#!/usr/bin/env bash` shebang does not pin a version. If this codebase is Linux-only, Bash 4+ is safe. If any contributor or CI runner uses macOS default bash, this will silently fail.

**Verdict:** Document the Bash 4+ requirement at the function declaration level. The existing codebase does not have a blanket policy documented in CLAUDE.md or AGENTS.md, so this should be made explicit rather than assumed.

### `_interspect_get_overlay_eligible` accumulation logic has a silent truncation bug — must-fix

The associative array accumulation in `_interspect_get_overlay_eligible`:

```bash
agent_total[$src]=$(( ${agent_total[$src]:-0} + ec ))
agent_sessions[$src]=$sc
agent_projects[$src]=$pc
if [[ "$reason" == "agent_wrong" ]]; then
    agent_wrong[$src]=$ec
fi
```

`_interspect_get_classified_patterns` emits one row per `(source, event, override_reason)` tuple. For an agent with `reason=agent_wrong` and `reason=deprioritized`, the loop processes both rows. `agent_total` correctly accumulates both `ec` values. But `agent_sessions[$src]` is overwritten on every row — the second iteration replaces the first. If the two rows have different `sc` (session_count), the final value is whichever row was processed last. This is non-deterministic because the SQL query orders by `ec DESC`, and the row order between rows for the same agent depends on which has higher event count.

More critically: `agent_wrong[$src]=$ec` assigns the event count from the `agent_wrong` row. This is correct only if the agent has exactly one `agent_wrong` row. If there are multiple `override_reason` values for `agent_wrong` groupings (which cannot happen under the current SQL GROUP BY, since `override_reason` is a grouping column), it would be overwritten. Under current SQL semantics this is safe — but the session count non-determinism is a real issue.

**Fix:** Use the `sc` and `pc` from the first row seen for that agent (guard with `[[ -z "${agent_sessions[$src]:-}" ]]`), or — better — derive them from a dedicated SQL query. The cleanest architectural fix is to compute the overlay-eligible set entirely in SQL (a single query with a HAVING clause), matching how `_interspect_is_routing_eligible` queries the DB directly rather than layering over the classified patterns function.

---

## 3. Simplicity and YAGNI

### `_interspect_apply_propose` calls `_interspect_load_confidence` — but never uses its variables

The `_interspect_get_overlay_eligible` function calls `_interspect_load_confidence` at the top. This is correct because the overlay eligibility check uses `_INTERSPECT_MIN_AGENT_WRONG_PCT`... but the function computes `pct` independently with integer arithmetic and the band threshold `40-79` is hard-coded, not drawn from the confidence config. This means `_interspect_load_confidence` is called but its output (`_INTERSPECT_MIN_AGENT_WRONG_PCT`) is never consulted for the overlay band decision.

The routing threshold (80%) is already encoded in `_INTERSPECT_MIN_AGENT_WRONG_PCT`. The overlay lower bound (40%) has no corresponding config variable. This is a YAGNI miss in the other direction: the config system exists for tuning thresholds, but the overlay band's boundaries are not tunable.

**Verdict (must-fix):** Either remove the `_interspect_load_confidence` call from `_interspect_get_overlay_eligible` (since it reads no config variables), or use `_INTERSPECT_MIN_AGENT_WRONG_PCT` as the upper bound of the overlay band (treating the config threshold as the routing cutoff, so overlay = `[40, threshold)`). The latter is strongly preferable because it keeps the band boundary in sync with the routing threshold: if the team raises `min_agent_wrong_pct` to 85%, the overlay band should automatically extend to `[40, 85)`.

**Concrete fix for `_interspect_get_overlay_eligible`:**

```bash
# Replace hard-coded 80 with config variable (already loaded):
(( pct >= 40 && pct < _INTERSPECT_MIN_AGENT_WRONG_PCT )) || continue
```

The lower bound (40%) is not in the config. This is a separate decision the team should make — either add `min_overlay_wrong_pct` to `confidence.json` defaults, or document that 40% is a fixed floor.

### `_interspect_get_routing_eligible` calls `_interspect_is_routing_eligible` per agent — double load

`_interspect_is_routing_eligible` calls `_interspect_load_confidence` (idempotent due to guard) and runs two SQLite queries per agent: total overrides and wrong overrides. `_interspect_get_routing_eligible` already has the event counts from the classified patterns output. Calling `_interspect_is_routing_eligible` again redundantly re-queries the same data.

This is a performance concern only, not a correctness concern. `_interspect_is_routing_eligible` also checks the blacklist — that check is genuinely additive. A cleaner design would inline the blacklist check and compute pct from classified patterns data. But given the low call frequency (interactive skill use only), the duplication is tolerable.

**Verdict:** Optional cleanup. The plan could add a `# NOTE: recomputes pct; blacklist check is the additive value` comment to prevent future confusion.

### `_interspect_is_cross_cutting` is appropriately minimal

The `case` statement pattern matches the existing `_interspect_validate_hook_id` approach (same file, line 1522). This is correct. No objection.

### Test for "apply_propose skips if override already exists" uses a heredoc in a bats test

The bats test at Task 3, Step 1:

```bash
cat > "$TEST_DIR/.claude/routing-overrides.json" << 'EOF'
...
EOF
```

This is fine inside a bats test file — the restriction on heredocs in Bash tool calls (from CLAUDE.md) applies to the Bash tool in Claude Code sessions, not to code being written to disk. No issue.

---

## 4. Test Coverage Assessment

The 16 new tests cover the primary positive and negative paths adequately. Two gaps:

**Gap 1:** No test for the `_interspect_apply_propose_locked` skip path correctly propagating through the outer function (the `ALREADY_EXISTS` bug described above). The existing test `"apply_propose skips if propose already exists"` uses `run _interspect_apply_propose` and checks `$output` for "already exists" — this will pass once the outer function correctly handles the sentinel, but currently the outer function will print a success message with garbage commit SHA instead. The test may pass for the wrong reason depending on the exact output content.

**Gap 2:** No test for `_interspect_get_overlay_eligible` with an agent that has evidence across multiple `override_reason` values to exercise the accumulation path. This is the path that exposes the `agent_sessions` overwrite bug.

---

## Must-Fix Summary

| # | Location | Issue | Fix |
|---|----------|-------|-----|
| M1 | `_interspect_apply_propose` outer function | `ALREADY_EXISTS` sentinel not detected; caller prints success with garbage commit SHA | Add sentinel check before `commit_sha` extraction |
| M2 | `_interspect_get_overlay_eligible` | `agent_sessions[$src]` overwritten non-deterministically across multiple rows for same agent | Guard with `[[ -z "${agent_sessions[$src]:-}" ]]` or use single SQL query |
| M3 | `_interspect_get_overlay_eligible` | Calls `_interspect_load_confidence` but uses hard-coded `80` instead of `$_INTERSPECT_MIN_AGENT_WRONG_PCT`; band drifts out of sync if config threshold changes | Replace `pct < 80` with `pct < _INTERSPECT_MIN_AGENT_WRONG_PCT` |

---

## Optional Improvements

| # | Location | Issue |
|---|----------|-------|
| O1 | `_interspect_is_cross_cutting` | Add comment naming the source of truth for the cross-cutting agent list |
| O2 | `_interspect_get_routing_eligible` inner loop | Comment that `_interspect_is_routing_eligible` call is for blacklist check; pct recomputed for output column only |
| O3 | `lib-interspect.sh` header `# Provides:` block | Add the 4 new function names (Task 5 in the plan already calls this out) |
| O4 | `confidence.json` schema | Consider adding `min_overlay_wrong_pct` (lower bound of overlay band) so both thresholds are tunable from config |

---

## Files Touched

- `/home/mk/projects/Demarch/os/clavain/hooks/lib-interspect.sh` — all 4 functions inserted here
- `/home/mk/projects/Demarch/os/clavain/tests/shell/test_interspect_routing.bats` — 16 new tests added here
