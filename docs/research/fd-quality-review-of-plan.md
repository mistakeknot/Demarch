# Quality & Style Review: 2026-02-23-interspect-routing-overrides-schema.md

**Reviewed by:** fd-quality (Flux-drive Quality & Style Reviewer)
**Date:** 2026-02-23
**Plan file:** `docs/plans/2026-02-23-interspect-routing-overrides-schema.md`
**Languages in scope:** Shell (bash), JSON Schema, BATS
**Codebase read:** `os/clavain/hooks/lib-interspect.sh` (lines 1–50, 500–560, 595–784), `os/clavain/tests/shell/test_interspect_routing.bats` (setup, teardown, representative tests)

---

## Summary

The plan is structurally sound and well-motivated. Most concerns are concrete and fixable before implementation begins. One issue (`shift 9`) is a correctness trap that will silently break the canary fields when the outer function is called. Two test assertions are logically inverted or ambiguous. The JSON Schema `const: 1` vs `enum: [1]` question resolves in favor of `const`, but a tooling caveat applies. All findings are below.

---

## Finding 1 — CORRECTNESS: `shift 9` is the right construct but the test for it is incomplete

**File/Location:** Task 2, Step 5 — `_interspect_apply_override_locked` signature

**Severity:** Correctness — will silently produce wrong values if the flock call sends fewer than 12 positional args

**Finding:**

The plan's proposed signature is:

```bash
_interspect_apply_override_locked() {
    set -e
    local root="$1" filepath="$2" fullpath="$3" agent="$4"
    local reason="$5" evidence_ids="$6" created_by="$7"
    local commit_msg_file="$8" db="$9"
    shift 9
    local confidence="${1:-1.0}" canary_window_uses="${2:-20}" canary_expires_at="${3:-null}"
```

The existing function already uses `$9` as the last positional parameter before `shift 9`. This is the correct bash idiom — `${10}` and beyond require brace syntax (`${10}`), so `shift 9` is the standard pattern to avoid that. The construct itself is correct.

However, the flock call site (Task 2 Step 4) passes all 12 arguments correctly:

```bash
flock_output=$(_interspect_flock_git _interspect_apply_override_locked \
    "$root" "$filepath" "$fullpath" "$agent" "$reason" \
    "$evidence_ids" "$created_by" "$commit_msg_file" "$db" \
    "$confidence" "$canary_window_uses" "$canary_expires_at")
```

The risk here is `_interspect_flock_git`. The plan does not show whether `_interspect_flock_git` passes all trailing args through intact. If it uses `"$@"` forwarding, the positional offset works correctly. If it wraps or reconstructs args, the trailing 3 arguments are silently dropped and the defaults (`1.0`, `20`, `null`) take over — producing a confidence of 1.0 on every override, which is wrong.

**Recommendation:**

Before implementing, verify `_interspect_flock_git` passes all args with `"$@"`. Add a comment in the plan at Step 5 noting this dependency:

```bash
# NOTE: _interspect_flock_git must forward all positional args via "$@"
# to _interspect_apply_override_locked. Verify before adding params.
```

An alternative that avoids positional fragility: pass confidence and canary as named environment variables rather than additional positional args:

```bash
INTERSPECT_CONFIDENCE="$confidence" \
INTERSPECT_CANARY_USES="$canary_window_uses" \
INTERSPECT_CANARY_EXPIRES="$canary_expires_at" \
_interspect_flock_git _interspect_apply_override_locked \
    "$root" "$filepath" "$fullpath" "$agent" "$reason" \
    "$evidence_ids" "$created_by" "$commit_msg_file" "$db"
```

Then inside `_interspect_apply_override_locked`, read them from the environment with defaults:

```bash
local confidence="${INTERSPECT_CONFIDENCE:-1.0}"
local canary_window_uses="${INTERSPECT_CANARY_USES:-20}"
local canary_expires_at="${INTERSPECT_CANARY_EXPIRES:-null}"
```

This is more robust than `shift 9` because it does not depend on arg-count assumptions across the flock forwarding boundary. The existing codebase already uses env-var overrides (`_INTERSPECT_DB`, `_INTERSPECT_CANARY_WINDOW_DAYS`, etc.) for exactly this kind of cross-boundary parameter passing — this would follow the established pattern.

---

## Finding 2 — CORRECTNESS: `canary_expires_at` is computed twice independently

**File/Location:** Task 2, Steps 3 and 5 — pre-flock in `_interspect_apply_routing_override`, and existing logic in `_interspect_apply_override_locked` (lines 776–781)

**Severity:** Correctness — potential clock skew, double computation, and contradicts existing locked logic

**Finding:**

The existing `_interspect_apply_override_locked` already computes `expires_at` at line 776 for the DB `canary` row:

```bash
expires_at=$(date -u -d "+${_INTERSPECT_CANARY_WINDOW_DAYS:-14} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v+"${_INTERSPECT_CANARY_WINDOW_DAYS:-14}"d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
```

The plan proposes computing it a second time in the outer function (pre-flock, Step 3), then passing it in. This means two `date` calls happen at slightly different wall-clock times, and the JSON snapshot's `expires_at` will not exactly match the DB record's `expires_at`. They'll be within milliseconds but they diverge in principle.

More importantly, the DB `canary` insert is guarded by `if (( is_new == 1 ))` inside the locked function, but the confidence computation happens unconditionally in the outer function. If the override already exists (dedup path, `is_new=0`), the outer function still computes and queries the DB for confidence/canary, and that work is thrown away when the inner function skips the insert.

**Recommendation:**

Move the confidence computation into `_interspect_apply_override_locked` alongside the existing canary computation at line 776. Both share the same DB connection, the same flock context, and the same `is_new` guard. The plan's motivation for moving confidence computation pre-flock (avoid holding the lock during DB reads) is valid, but the DB queries involved (`COUNT(*)` on the evidence table) are fast local reads — far cheaper than the git commit that already happens inside the lock. Colocating them is cleaner.

If the env-var approach from Finding 1 is adopted, computing confidence inside the locked function is trivially simple and eliminates the double-computation problem.

---

## Finding 3 — CORRECTNESS: `_interspect_load_confidence` call in outer function is a side-effect concern

**File/Location:** Task 2, Step 3 — confidence computation block

**Severity:** Minor correctness — possible double-load with altered state

**Finding:**

The plan calls `_interspect_load_confidence` in the outer `_interspect_apply_routing_override` function before the flock call. The existing `_interspect_apply_override_locked` already calls `_interspect_load_confidence` at line 758 inside the lock. If `_interspect_load_confidence` is idempotent (guarded), calling it twice is harmless. If it sets global state (sets `_INTERSPECT_CANARY_WINDOW_USES`, etc.) the double call is redundant at best, confusing at worst.

The comment at line 758 in the locked function makes the intent clear: confidence is loaded just before the canary baseline computation. The plan should not replicate this call in the outer function without checking the guard.

**Recommendation:**

Check whether `_interspect_load_confidence` is guarded (e.g., `[[ -n "${_INTERSPECT_CONFIDENCE_LOADED:-}" ]] && return 0`). If yes, the double call is safe. Either way, a brief comment in the plan noting "idempotent due to guard" would prevent future confusion.

---

## Finding 4 — TEST CORRECTNESS: Two test assertions are inverted or ambiguous

**File/Location:** Task 3 — test "read_routing_overrides validates version field"

**Severity:** Test will pass when it should fail (false green)

**Finding:**

```bash
@test "read_routing_overrides validates version field" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":2,"overrides":[]}' > "${TEST_DIR}/.claude/routing-overrides.json"

    run _interspect_read_routing_overrides
    [ "$status" -eq 1 ]
    [[ "$output" == *'"version":1'* ]]  # Returns empty structure
    [[ "${lines[0]}" == *"WARN"* ]] || [[ "$output" == *"version"* ]]
}
```

The third assertion is `[[ "${lines[0]}" == *"WARN"* ]] || [[ "$output" == *"version"* ]]`. The second branch (`"version"` in output) is trivially true because the fallback response is `{"version":1,"overrides":[]}`, which always contains the string "version". This makes the OR expression always pass regardless of whether the WARN was actually emitted. The WARN-on-stderr check is what should be verified.

The existing tests use `run` which captures stdout into `$output` and stderr into `$stderr` (in bats-core >=1.5). The plan should use `$stderr` (or check `output` after redirecting stderr).

Looking at existing test patterns in the file — tests capture stderr by including `2>/dev/null` in non-`run` calls, or they separate stdout and stderr by using `run` and checking `$output` knowing stderr is captured. The existing `read routing overrides handles malformed JSON` test calls the function with `2>/dev/null` redirect and checks the stdout fallback. The validation tests should follow the same approach.

**Fix:**

```bash
@test "read_routing_overrides validates version field" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":2,"overrides":[]}' > "${TEST_DIR}/.claude/routing-overrides.json"

    run _interspect_read_routing_overrides
    [ "$status" -eq 1 ]
    # stdout is the safe fallback
    [[ "$output" == *'"version":1'* ]]
    [[ "$output" == *'"overrides":[]'* ]]
    # WARN goes to stderr — check $stderr if bats-core >=1.5, or use 2>&1 redirect
    [[ "$stderr" == *"WARN"* ]] || [[ "$output" != *'"version":2'* ]]
}
```

Or simpler — mirror the existing `handles malformed JSON` test pattern: call without `run`, redirect stderr to `/dev/null`, and only assert the stdout fallback is correct. Then add a separate test that runs with stderr captured to verify the WARN text.

---

## Finding 5 — TEST CONSISTENCY: New test setup differs from existing sqlite3 insert pattern

**File/Location:** Task 2 — tests "apply_routing_override writes confidence field" and "writes canary snapshot"

**Severity:** Maintainability — inconsistency with codebase test patterns

**Finding:**

The plan inserts evidence rows with a minimal schema:

```bash
sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
```

The existing test for routing eligibility inserts the full schema including required columns:

```bash
sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-game-design', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
```

If the `evidence` table has `NOT NULL` constraints on `session_id`, `seq`, `ts`, `context`, or `project`, the plan's minimal inserts will fail with a constraint error before the function under test is even called, producing a confusing BATS failure.

**Recommendation:**

Match the full insert pattern from the existing eligibility tests. Also note the existing test uses 5 events across 3 projects to meet the `min_diversity` gate. The plan's test inserts 4 `agent_wrong` + 1 `agent_correct` = 5 events, but all from the same source with no `project` diversity. Whether this passes the eligibility gate depends on the confidence config loaded in `setup()` — the existing `confidence.json` requires `"min_diversity":2`. Inserting into only one implicit project may cause the eligibility check to fail before the override is written.

Use the complete insert pattern and vary the `project` field across at least 2 values, consistent with the existing test for `is_routing_eligible returns eligible at 80% threshold`.

---

## Finding 6 — JSON SCHEMA: `const: 1` vs `enum: [1]` — correct choice with a caveat

**File/Location:** Task 1, Step 1 — schema property `version`

**Severity:** Informational — correct as written, but worth documenting

**Finding:**

```json
"version": {
  "type": "integer",
  "const": 1,
  "description": "Schema version. Readers must reject version > 1."
}
```

`const` was introduced in JSON Schema draft-06 and is valid in draft-07. It is semantically equivalent to `enum: [1]` for a single value. `const: 1` is the preferred draft-07 idiom for expressing "this field must be exactly this value" and is more semantically precise than a single-element `enum`. The choice is correct.

The caveat: `jq` does not validate JSON Schema. The schema file is documentation and tooling aid only — it has no runtime enforcement unless a schema validator (e.g., `ajv-cli`) is wired into CI. The plan does not add any CI schema validation step. This is fine for now since the reader adds runtime validation inline, but the schema's value as a contract is diminished without at least a syntax check in CI.

**Minor: `$id` is a relative URI without a scheme**

```json
"$id": "routing-overrides.schema.json"
```

JSON Schema draft-07 specifies that `$id` should be an absolute URI or a relative URI that resolves against a base. A bare filename is technically valid as a relative URI but validators may warn. If there is no JSON Schema validator in CI (there isn't currently), this is harmless. If one is added later, using an absolute path or `$id: "https://demarch.example/schemas/routing-overrides.schema.json"` avoids the warning.

---

## Finding 7 — SCHEMA STYLE: `additionalProperties: true` on override definition is inconsistent

**File/Location:** Task 1, Step 1 — `definitions.override`

**Severity:** Style inconsistency — minor

**Finding:**

The `scope` and `canary_snapshot` definitions use `additionalProperties: false`:

```json
"scope": {
  "type": "object",
  "additionalProperties": false,
  ...
}
"canary_snapshot": {
  "type": "object",
  "additionalProperties": false,
  ...
}
```

But the override definition uses `additionalProperties: true`:

```json
"override": {
  "type": "object",
  "required": ["agent", "action"],
  "additionalProperties": true,
  ...
}
```

The plan's SKILL.md update (Task 4) confirms that unknown fields must be preserved (`"future_field": "ok"` in the `ignores unknown fields` test). The `additionalProperties: true` on the override is intentional and correct for forward compatibility. However, the comment above the definition does not explain this intentional asymmetry with `scope` and `canary_snapshot`.

**Recommendation:**

Add a schema comment (in `description`) at the `override` level noting why `additionalProperties: true` — e.g., `"Forward-compatible: readers must preserve unknown fields for future schema versions."` This makes the asymmetry explicit rather than appearing accidental.

---

## Finding 8 — AWK vs BC: `awk` is the correct choice for this codebase

**File/Location:** Task 2, Step 3 — confidence computation

**Severity:** Informational — correct as written

**Finding:**

```bash
confidence=$(awk "BEGIN {printf \"%.2f\", ${wrong}/${total}}")
```

`awk` is idiomatic for float arithmetic in bash-based codebases. `bc` requires `echo "scale=2; $wrong/$total" | bc` which is wordier and has edge cases with leading zeros (e.g., `bc` produces `.80` not `0.80` for values less than 1, which would cause `--argjson confidence "$confidence"` in jq to fail with a parse error since JSON requires a leading zero).

`awk BEGIN {...}` with `printf "%.2f"` produces `0.80` correctly. This matches the test expectation `[ "$confidence" = "0.8" ]` — except `printf "%.2f"` produces `0.80` (two decimal places), not `0.8` (one decimal place). The test assertion will fail.

**Fix — either the computation or the test must be consistent:**

Option A — match awk output exactly in the test:
```bash
[ "$confidence" = "0.80" ]
```

Option B — use `printf "%.10g"` in awk (strips trailing zeros):
```bash
confidence=$(awk "BEGIN {printf \"%.10g\", ${wrong}/${total}}")
# 4/5 = 0.8, 3/5 = 0.6, etc.
```

Option B produces clean values that jq's `--argjson` also accepts. The test then uses `[ "$confidence" = "0.8" ]` as written. Option B is preferred because it produces the same precision as jq's native number output, keeping the JSON consistent.

**Security note:** The awk invocation uses double-quoted shell expansion (`"BEGIN {printf \"%.2f\", ${wrong}/${total}}"`). Both `$wrong` and `$total` come from `sqlite3 COUNT(*)` queries which return integers only. This is safe — an attacker cannot inject a non-integer through `COUNT(*)`. A brief comment noting this is worthwhile given the codebase's strong injection-awareness.

---

## Finding 9 — NAMING: New fields are consistent with codebase conventions

**File/Location:** All tasks — fields `confidence`, `canary`, `scope`

**Severity:** Informational — no issues

**Finding:**

- `confidence`: The DB `modifications` table already has a `confidence` column (line 755 of lib-interspect.sh). The plan's JSON field matches this name exactly. Consistent.
- `canary`: The DB already has a `canary` table. Using `canary` as the JSON key for the snapshot object is appropriate. The plan uses `canary_snapshot` as the schema definition name (internal reference only) but `canary` as the JSON field name — this is correct; definition names need not match field names.
- `scope`: Not currently used in the codebase. The name is clear, short, and consistent with common routing/middleware vocabulary. The sub-fields `domains` and `file_patterns` follow `snake_case` consistently with all existing fields (`evidence_ids`, `created_by`, `window_uses`, `override_reason`).
- `window_uses`: The existing `confidence.json` config uses `canary_window_uses`. The plan uses `window_uses` (without `canary_` prefix) inside the `canary` object where the context is already established. Consistent and unambiguous.
- `evidence_ids`: Already used in the existing writer's jq template (line 707). The plan adds it to the schema formally. Consistent.

All new names pass the project's `snake_case` convention and are unambiguous in context.

---

## Finding 10 — ERROR HANDLING: Validation function is graceful but has a subtle return-code ambiguity

**File/Location:** Task 3, Step 3 — updated `_interspect_read_routing_overrides`

**Severity:** Minor — could cause caller confusion

**Finding:**

The proposed reader returns exit code 1 for version mismatch and returns the safe fallback JSON on stdout:

```bash
echo '{"version":1,"overrides":[]}'
return 1
```

The existing tests check the function's return code: `[ "$status" -eq 1 ]`. However, a caller who uses `result=$(_interspect_read_routing_overrides)` without checking `$?` will silently get the fallback JSON and proceed as if everything succeeded. This is the existing behavior for malformed JSON (line 528–532), so the plan is consistent with the established pattern.

The issue is that the existing `_interspect_read_routing_overrides_locked` at line 553 calls `_interspect_read_routing_overrides` and does not check its return code. After the plan's changes, a version-2 file will emit a WARN to stderr and return the fallback — but the locked wrapper returns that fallback with exit code 0 (the subshell succeeds). Any caller relying on `_interspect_read_routing_overrides_locked` for the lock-protected path gets misleading exit-code semantics.

**Recommendation:**

Propagate the exit code from the inner call in the locked wrapper. This is a one-line fix:

```bash
# In _interspect_read_routing_overrides_locked, line 553:
_interspect_read_routing_overrides
# Change to:
_interspect_read_routing_overrides; return $?
```

Or simply rely on the last command's exit code if `set -e` is not active in the subshell. Either way, the plan should note this wrapper needs updating alongside the inner function.

---

## Finding 11 — SHELL IDIOM: `echo "$content" | jq ...` vs `jq ... <<< "$content"`

**File/Location:** Task 3, Step 3 — validation calls inside `_interspect_read_routing_overrides`

**Severity:** Style note — not a bug

**Finding:**

The plan uses `echo "$content" | jq ...` consistently throughout the proposed validation code. The existing function body (line 534) also uses `jq '.' "$fullpath"` (reading from file directly). The proposed code reads the file into `$content` first and then pipes to jq multiple times, creating multiple jq processes for a single file.

This is consistent with patterns elsewhere in the file. The alternative `jq -r '.version // empty' <<< "$content"` (here-string) avoids the pipeline and is slightly more efficient, but given jq startup cost is negligible for a config file of this size, this is a non-issue. The `echo "$content" | jq` pattern is already established — do not change it here.

---

## Finding 12 — TASK 5 (SMOKE TEST): Final commit message uses `git add -A`

**File/Location:** Task 5, Step 6

**Severity:** Inconsistency with global CLAUDE.md guidance

**Finding:**

```bash
git add -A && git commit -m "test(interspect): add integration smoke test for routing-overrides schema"
```

The global `CLAUDE.md` ("Settings Hygiene") section warns against `git add -A` because it may accidentally stage sensitive files. All other commit steps in the plan use specific file paths. Task 5 Step 6 is described as "if any cleanup needed" and references no specific files, making `git add -A` particularly ambiguous.

**Recommendation:**

Replace with `git add .claude/routing-overrides.json` if a test file was left behind, or remove the step entirely since Task 5 is a smoke test that should not produce committed artifacts. The test file created in Step 1 is meant to be cleaned up (Step 4), leaving nothing to commit.

---

## Summary Table

| # | Area | Severity | Action Required |
|---|------|----------|-----------------|
| 1 | `shift 9` arg forwarding through flock | Correctness | Verify `_interspect_flock_git` passes `"$@"` intact; consider env-var approach |
| 2 | `canary_expires_at` computed twice | Correctness | Move confidence+canary computation into the locked function |
| 3 | `_interspect_load_confidence` double-call | Minor correctness | Verify guard; add comment |
| 4 | WARN assertion uses trivially-true OR branch | Test correctness | Fix assertion to use `$stderr` or redirect pattern |
| 5 | Minimal evidence inserts missing required columns | Test correctness | Match full insert schema from existing tests; vary `project` field |
| 6 | `const: 1` vs `enum: [1]` | Correct; informational | No change needed; note no CI validator is wired |
| 7 | `additionalProperties: true` asymmetry undocumented | Style | Add description explaining forward-compat intent |
| 8 | `awk "%.2f"` vs test expecting `"0.8"` | Correctness | Use `%.10g` in awk, or fix test to expect `"0.80"` |
| 9 | Naming (`confidence`, `canary`, `scope`) | Consistent | No action needed |
| 10 | `_interspect_read_routing_overrides_locked` exit code | Minor | Propagate exit code in locked wrapper |
| 11 | `echo "$content" \| jq` style | Consistent | No action needed |
| 12 | `git add -A` in smoke test | Inconsistency | Use specific path or remove the commit step |

---

## Priority Order for Fixes Before Implementation

1. **Finding 8** (awk precision vs test expectation) — will cause immediate BATS failure on first run; fix before writing a single line of code.
2. **Finding 5** (incomplete evidence inserts) — will cause sqlite3 constraint errors masking the real test failure.
3. **Finding 4** (inverted WARN assertion) — test passes when it should fail; makes CI unreliable.
4. **Finding 1** (shift 9 / flock forwarding) — verify the flock wrapper before implementing; if not `"$@"`, redesign with env-vars.
5. **Finding 2** (double computation) — architectural cleanup; lower urgency but cleaner to fix now than after implementation.
6. All remaining findings are documentation and minor-style level.
