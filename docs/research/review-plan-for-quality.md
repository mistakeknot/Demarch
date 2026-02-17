# Quality Review: Interspect Canary Monitoring Implementation Plan

**Reviewer:** Flux-drive Quality & Style Reviewer
**Date:** 2026-02-16
**Plan:** `/root/projects/Interverse/docs/plans/2026-02-16-interspect-canary-monitoring.md`
**Context:** Bash/SQLite plugin for Claude Code canary monitoring

---

## Executive Summary

This plan extends `lib-interspect.sh` with canary monitoring functions. The bash implementation demonstrates strong adherence to existing project patterns (SQL escaping, awk for floats, jq for JSON, error suppression via `|| true`). However, there are **3 P0 issues**, **8 P1 issues**, and **5 P2 issues** spanning error handling gaps, shell gotchas, test coverage holes, and subtle SQL injection risks.

**Key strengths:**
- Consistent use of `_interspect_sql_escape` for user-controlled values
- Proper awk usage for floating-point arithmetic
- Clean separation of concerns (baseline → sample → evaluation)
- Good test coverage breadth (15 new tests)

**Critical fixes needed:**
- SQL injection via unescaped `$before_ts` in multiple queries (P0)
- Unchecked critical errors (missing baseline INSERT guard, insufficient quoting) (P0)
- Missing validation for numeric config values (integer overflow risk) (P0)
- Variable scoping issues (`reasons` global bleed, `first` flag) (P1)
- Test gaps for edge cases (empty strings, malformed data, concurrent access) (P1)

---

## P0 Findings (Must Fix)

### P0-1: SQL Injection via Unescaped Timestamp in Baseline Computation

**Location:** Task 2, `_interspect_compute_canary_baseline`, lines 135-149

**Issue:** The `$before_ts` parameter is interpolated directly into SQL without escaping:
```bash
sqlite3 "$db" "SELECT COUNT(*) FROM sessions WHERE start_ts < '${before_ts}' ${project_filter};"
```

If `before_ts` contains a single quote (e.g., from a malformed ISO 8601 string or crafted input), this breaks the query. While timestamps are typically controlled by the code (`date -u`), the function accepts arbitrary input via `$1`.

**Impact:** SQL syntax errors or potential injection if called with untrusted input.

**Fix:** Escape `before_ts`:
```bash
local escaped_ts
escaped_ts=$(_interspect_sql_escape "$before_ts")
# Use: WHERE start_ts < '${escaped_ts}'
```

**Also affects:** Lines 145-149 (window boundaries), Task 4 evaluation function (line 406 date comparison).

---

### P0-2: Unchecked Critical Error in Baseline INSERT

**Location:** Task 2, lines 232-236 (canary INSERT)

**Issue:** The canary INSERT has error handling that falls back to `applied-unmonitored` status:
```bash
if ! sqlite3 "$db" "INSERT INTO canary ..."; then
    sqlite3 "$db" "UPDATE modifications SET status = 'applied-unmonitored' WHERE commit_sha = '${commit_sha}';" 2>/dev/null || true
    echo "WARN: Canary monitoring failed — override active but unmonitored." >&2
fi
```

However, the function does **not return 1** on failure. The caller (`_interspect_apply_override_locked`) will continue as if the canary was created, but monitoring is silently disabled. This violates the principle of least surprise and could mask persistent DB errors.

**Impact:** Silent degradation of monitoring; overrides applied without canary tracking.

**Fix:** Return 1 after the fallback update:
```bash
if ! sqlite3 "$db" "INSERT INTO canary ..."; then
    sqlite3 "$db" "UPDATE modifications SET status = 'applied-unmonitored' WHERE commit_sha = '${commit_sha}';" 2>/dev/null || true
    echo "WARN: Canary monitoring failed — override active but unmonitored." >&2
    return 1
fi
```

---

### P0-3: Missing Validation for Numeric Config Values

**Location:** Task 1, Step 3, lines 69-84

**Issue:** Configuration values loaded from `confidence.json` are used directly in arithmetic without bounds checking:
```bash
_INTERSPECT_CANARY_WINDOW_USES=$(jq -r '.canary_window_uses // 20' "$conf")
# ...later:
local window_size="${_INTERSPECT_CANARY_WINDOW_USES:-20}"
# Used in: LIMIT ${window_size}
```

If the JSON contains a huge number (e.g., `999999999`), the `LIMIT` clause could cause massive queries. If it contains a non-numeric string (e.g., `"all"`), bash arithmetic will treat it as 0 or fail unpredictably.

**Impact:** Integer overflow in queries, potential DoS, silent failures in arithmetic contexts.

**Fix:** Add bounds checking and type validation:
```bash
_INTERSPECT_CANARY_WINDOW_USES=$(jq -r '.canary_window_uses // 20 | tonumber' "$conf")
if [[ ! "$_INTERSPECT_CANARY_WINDOW_USES" =~ ^[0-9]+$ ]] || (( _INTERSPECT_CANARY_WINDOW_USES < 1 || _INTERSPECT_CANARY_WINDOW_USES > 1000 )); then
    echo "WARN: Invalid canary_window_uses in config, defaulting to 20" >&2
    _INTERSPECT_CANARY_WINDOW_USES=20
fi
```

**Also affects:** `_INTERSPECT_CANARY_MIN_BASELINE`, `_INTERSPECT_CANARY_ALERT_PCT`, `_INTERSPECT_CANARY_WINDOW_DAYS`.

---

## P1 Findings (Should Fix)

### P1-1: Variable Scope Leakage in `check_degradation` Helper

**Location:** Task 4, lines 436-467

**Issue:** The `check_degradation` helper function is defined **inside** `_interspect_evaluate_canary` and modifies the outer scope's `reasons` variable:
```bash
reasons="${reasons}${metric_name}: ${baseline} → ${current} ..."
```

This is intentional but fragile: if `check_degradation` is later extracted to a standalone function, it will break. Additionally, `reasons` is not declared `local` in the parent scope, so it could leak to the global scope if the function is called from a context where `reasons` is already set.

**Impact:** Future refactoring hazard; potential global variable pollution.

**Fix:** Declare `reasons` as `local` at the top of `_interspect_evaluate_canary`, and pass it by reference if extracting the helper:
```bash
local reasons=""
```

---

### P1-2: Insufficient Quoting in `date` Command

**Location:** Task 2, lines 215-219

**Issue:** The relative date calculation uses:
```bash
expires_at=$(date -u -d "+${_INTERSPECT_CANARY_WINDOW_DAYS:-14} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v+${_INTERSPECT_CANARY_WINDOW_DAYS:-14}d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
```

The `-d "+${...} days"` argument is **not quoted**. If `_INTERSPECT_CANARY_WINDOW_DAYS` contains whitespace or special characters (from malformed config), the command will fail or behave unexpectedly.

**Impact:** Command injection risk (low, since config is trusted), but violates quoting discipline.

**Fix:** Quote the argument:
```bash
expires_at=$(date -u -d "+${_INTERSPECT_CANARY_WINDOW_DAYS:-14} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v+"${_INTERSPECT_CANARY_WINDOW_DAYS:-14}d" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
```

---

### P1-3: awk Division-by-Zero Risk

**Location:** Task 2, line 162; Task 3, lines 295, 301; Task 4, lines 441, 456

**Issue:** Multiple awk floating-point divisions assume non-zero denominators:
```bash
override_rate=$(awk "BEGIN {printf \"%.4f\", ${total_overrides} / ${total_sessions_in_window}}")
```

If `total_sessions_in_window` is 0, this will cause awk to print `inf` or `-inf`, which then propagates to JSON and SQLite. While there are guards before some divisions (`if (( total_sessions_in_window == 0 ))`), the pattern is inconsistent across functions.

**Impact:** `inf`/`NaN` in JSON output, SQLite errors (SQLite accepts `Infinity` as a REAL but comparisons fail).

**Fix:** Ensure **all** awk divisions have explicit zero checks:
```bash
if (( total_sessions_in_window == 0 )); then
    override_rate="0.0"
else
    override_rate=$(awk "BEGIN {printf \"%.4f\", ${total_overrides} / ${total_sessions_in_window}}")
fi
```

**Also audit:** Task 4, lines 456, 464 (percentage calculations with `${baseline}` in denominator).

---

### P1-4: Missing `local` Declaration for Loop Variable

**Location:** Task 3, line 311; Task 4, lines 524-525

**Issue:** Loop variables are declared but not marked `local`:
```bash
local canary_id
while IFS= read -r canary_id; do
```

In bash, `local` only affects the current function scope. While `read -r canary_id` doesn't leak to the global scope, consistency with other `local` declarations is important for readability.

**Impact:** Minor — no functional issue, but inconsistent style.

**Fix:** This is actually already correct (the `local canary_id` before the loop is sufficient), but ensure all similar patterns use the same style.

---

### P1-5: No Guard Against Empty `session_ids_sql` Subquery

**Location:** Task 2, lines 149-154

**Issue:** The baseline computation builds a subquery:
```bash
local session_ids_sql="SELECT session_id FROM sessions WHERE start_ts < '${before_ts}' ${project_filter} ORDER BY start_ts DESC LIMIT ${window_size}"
total_overrides=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE event = 'override' AND session_id IN (${session_ids_sql});")
```

If the subquery returns no rows (e.g., no sessions match the filters), the `IN ()` clause becomes `IN (NULL)`, which is valid SQL but may produce unexpected behavior in older SQLite versions (though modern SQLite handles this correctly).

**Impact:** Edge case — unlikely to break, but worth explicit handling.

**Fix:** Check `session_count` before executing the subquery-dependent queries (already done at line 137, so this is actually fine). However, the comment at line 148 about empty `window_start` suggests awareness of this edge case — ensure the fallback is robust.

---

### P1-6: Race Condition in Canary Sample Deduplication

**Location:** Task 3, lines 316-319

**Issue:** The deduplication check uses a SELECT followed by an INSERT:
```bash
exists=$(sqlite3 "$db" "SELECT COUNT(*) FROM canary_samples WHERE canary_id = ${canary_id} AND session_id = '${escaped_sid}';")
if (( exists > 0 )); then
    continue
fi
sqlite3 "$db" "INSERT INTO canary_samples ..." 2>/dev/null || continue
```

This is a classic **TOCTOU** (time-of-check-time-of-use) race. If two session-end hooks run concurrently for the same session (unlikely but possible in multi-process scenarios), both could pass the check and attempt the INSERT.

**Impact:** Low risk (Claude Code sessions are typically single-process), but the `UNIQUE` constraint will catch duplicates (`2>/dev/null || continue` swallows the error).

**Fix:** Rely entirely on the `UNIQUE` constraint and remove the SELECT check:
```bash
# Let the UNIQUE constraint handle deduplication
sqlite3 "$db" "INSERT INTO canary_samples ..." 2>/dev/null || continue
```

**Alternative:** Use `INSERT OR IGNORE` to make the intent explicit.

---

### P1-7: Test Coverage Gap for Null Baseline Scenarios

**Location:** Task 6, test suite

**Issue:** Test `evaluate_canary handles NULL baseline` (line 815) checks that the function returns `"monitoring"` status, but it doesn't verify that the function **computes a baseline** when sufficient historical data becomes available.

There's no test for the transition from `NULL baseline → baseline computed → alert/passed` across multiple evaluations.

**Impact:** Critical workflow untested — canaries with NULL baseline remain stuck if the baseline computation logic has a bug.

**Fix:** Add a test:
```bash
@test "evaluate_canary computes baseline after sufficient sessions accumulate" {
    DB=$(_interspect_db_path)
    # Start with no baseline
    sqlite3 "$DB" "INSERT INTO canary (..., baseline_override_rate) VALUES (..., NULL);"

    # Add 15 sessions (min_baseline)
    for i in $(seq 1 15); do
        sqlite3 "$DB" "INSERT INTO sessions ..."
        sqlite3 "$DB" "INSERT INTO evidence ..."
    done

    # Re-evaluate — should now have baseline
    result=$(_interspect_evaluate_canary 1)
    # Assert baseline is no longer NULL in the canary row
    baseline=$(sqlite3 "$DB" "SELECT baseline_override_rate FROM canary WHERE id = 1;")
    [ "$baseline" != "" ]
}
```

---

### P1-8: No Test for Concurrent Session-End Hooks

**Location:** Task 6, test suite

**Issue:** The sample collection and canary evaluation functions are called from hooks that could theoretically run concurrently. There's no test simulating concurrent INSERT attempts.

**Impact:** Medium risk — the `UNIQUE` constraint and `|| continue` guards should handle this, but it's untested.

**Fix:** Add a stress test (requires bats concurrency):
```bash
@test "record_canary_sample handles concurrent calls gracefully" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary ..."
    sqlite3 "$DB" "INSERT INTO evidence ..."

    # Simulate 10 concurrent session-end calls for the same session
    for i in {1..10}; do
        (_interspect_record_canary_sample "test_session" &)
    done
    wait

    # Should have exactly 1 sample
    count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary_samples;")
    [ "$count" -eq 1 ]
}
```

---

## P2 Findings (Nice to Have)

### P2-1: Naming Inconsistency: `uses_so_far` vs `sample_count`

**Location:** Throughout the plan

**Issue:** The canary table has a `uses_so_far` column (incremented per sample), but the evaluation logic also computes `sample_count` from the `canary_samples` table. These should always be equal, but there's no validation to ensure this invariant.

**Impact:** Confusion if the two diverge due to a bug (e.g., failed INSERT but successful UPDATE).

**Fix:** Add a sanity check in `_interspect_evaluate_canary`:
```bash
local uses_from_table uses_from_samples
uses_from_table=$(sqlite3 "$db" "SELECT uses_so_far FROM canary WHERE id = ${canary_id};")
uses_from_samples=$(sqlite3 "$db" "SELECT COUNT(*) FROM canary_samples WHERE canary_id = ${canary_id};")
if (( uses_from_table != uses_from_samples )); then
    echo "WARN: Canary ${canary_id} uses_so_far mismatch (table: ${uses_from_table}, samples: ${uses_from_samples})" >&2
fi
```

---

### P2-2: Session-Start Hook Output Format Unclear

**Location:** Task 5, Step 1, lines 585-599

**Issue:** The session-start hook outputs JSON:
```bash
echo "{\"additionalContext\":\"WARNING: ${ALERT_MSG}\"}"
```

The comment says "This piggybacks on the existing hook output mechanism," but there's no reference to the hooks.json binding format. If the hook is configured with `"outputMode": "text"` instead of `"json"`, this will fail.

**Impact:** Hook output may not be injected into session context if the binding is misconfigured.

**Fix:** Add a note in the plan to verify hooks.json:
```json
{
  "SessionStart": [
    {
      "hook": "./interspect-session.sh",
      "outputMode": "json"
    }
  ]
}
```

---

### P2-3: Test Naming Inconsistency: Underscores vs Spaces

**Location:** Task 6

**Issue:** Test names use underscores in function names but spaces in descriptions:
```bash
@test "compute_canary_baseline returns null with no sessions" {
```

This is fine, but the project's existing tests (if any) should be checked for consistency.

**Impact:** Cosmetic — no functional issue.

**Fix:** Audit existing bats tests in `hub/clavain/tests/shell/` and match the prevailing style.

---

### P2-4: Missing Edge Case Tests for Malformed Data

**Location:** Task 6, test suite

**Issue:** No tests for:
- Empty strings in `override_reason` or `context` fields
- Non-numeric values in REAL columns (SQLite allows text in REAL columns)
- ISO 8601 timestamps with timezones (SQLite string comparison assumes UTC)

**Impact:** Low risk — SQLite is permissive, but garbage in could lead to garbage out.

**Fix:** Add sanitization tests:
```bash
@test "record_canary_sample handles empty override_reason gracefully" {
    # Insert evidence with override_reason = ''
    # Verify sample still recorded
}
```

---

### P2-5: Status Display Uses Inline JSON Assembly

**Location:** Task 5, Step 2, lines 614-655

**Issue:** The status command assembles complex output with inline loops and conditionals:
```
{for each canary in CANARY_SUMMARY:
  **{agent}** [{status}]
  ...
}
```

This pseudo-template syntax is unusual. If this is meant to be executed by Claude Code's command renderer, it should be clarified. If it's meant to be bash, it should use proper loops.

**Impact:** Unclear execution model — could cause rendering issues.

**Fix:** If this is a Claude Code template, add a comment:
```markdown
<!-- This template is rendered by Claude Code's command system -->
```

If it's bash, replace with:
```bash
echo "$CANARY_SUMMARY" | jq -r '.[] | "**\(.agent)** [\(.status)]"'
```

---

## Test Coverage Assessment

**Breadth:** Good — 15 new tests covering baseline computation, sample collection, evaluation, and DB schema.

**Depth:** Moderate — missing edge cases (NULL handling, concurrent access, malformed data, baseline transitions).

**Risk areas:**
- **Concurrency:** No tests for concurrent session-end hooks (P1-8)
- **Baseline transitions:** No test for NULL → computed baseline (P1-7)
- **Error paths:** No tests for DB corruption, failed INSERTs, or network issues (acceptable for unit tests, but integration tests should cover this)

**Recommendation:** Add 5-7 more tests (see P1-7, P1-8, P2-4).

---

## Shell-Specific Gotchas Summary

1. **Word splitting in date command:** `-d "+${DAYS} days"` should be quoted (P1-2)
2. **Integer overflow in LIMIT clause:** Config values need bounds checking (P0-3)
3. **Division by zero in awk:** Inconsistent guards before divisions (P1-3)
4. **TOCTOU race in deduplication:** Check-then-insert pattern (P1-6)
5. **SQL injection via timestamps:** Unescaped `$before_ts` (P0-1)
6. **Global variable leakage:** `reasons` not declared `local` (P1-1)

---

## Final Recommendations

1. **Fix all P0 issues before implementation begins** — especially SQL injection and error handling gaps.
2. **Address P1 issues during implementation** — they're not blockers but will prevent production bugs.
3. **Defer P2 issues to a follow-up PR** — cosmetic and edge-case fixes can wait.
4. **Add integration tests** — the unit tests are solid, but hook orchestration needs end-to-end validation.
5. **Document assumptions** — especially around timestamp formats, config bounds, and SQLite version requirements.

---

## Appendix: Checklist for Implementer

Before marking each task complete:

- [ ] Run `bash -n` on all modified files
- [ ] Run bats tests and verify new tests pass
- [ ] Manually test with `sqlite3 :memory:` to verify schema migrations
- [ ] Check for unescaped variables in all SQL strings (`grep -n "sqlite3.*'.*\$" lib-interspect.sh`)
- [ ] Verify all awk divisions have zero checks
- [ ] Confirm hooks.json uses `"outputMode": "json"` for session-start hook
- [ ] Test with malformed confidence.json (e.g., `{"canary_window_uses": "invalid"}`)
- [ ] Simulate expired canaries (set `window_expires_at` to past date)
- [ ] Verify `/interspect:status` output with 0, 1, and 10+ canaries
- [ ] Test baseline computation with exactly `min_baseline` sessions (boundary)
