# Quality Review: C1 Agency Specs Plan (2026-02-22)

**Reviewed:** `os/clavain/docs/plans/2026-02-22-c1-agency-specs.md`
**Date:** 2026-02-22
**Scope:** Naming conventions, bash idioms, file organization, error handling, test strategy

---

## Summary

The plan is solid in its architecture and dependency ordering. The main risks are a naming inconsistency between `agency_*` functions and the `sprint_*` convention used by callers, two bash anti-patterns in the proposed budget functions, an under-specified test coverage gap for the `_evaluate_spec_gates` dispatch logic, and a missing structural test extension for the new Python file. None are blockers, but three of them will either confuse future maintainers or cause silent failures under bash strict mode.

---

## 1. Naming Conventions

### Finding 1.1: `agency_*` prefix creates a split namespace — recommend `sprint_spec_*` or `spec_*`

**Severity: Medium**

The existing library functions that callers interact with all use prefixes that match their file's domain:

| File | Public prefix | Private prefix |
|------|--------------|----------------|
| `lib-sprint.sh` | `sprint_` | `_sprint_` |
| `lib-intercore.sh` | `intercore_` | (none — it is wrappers all the way) |
| `lib-verdict.sh` | `verdict_` | (none) |
| `lib-signals.sh` | `detect_` | (none) |

The proposed `lib-agency.sh` introduces an `agency_` prefix for functions like `agency_load_spec`, `agency_get_stage`, `agency_get_budget`. These functions will be called from `lib-sprint.sh` — from inside a `sprint_*` context — and from gate/budget helpers that callers think of as part of the sprint library.

The `agency_` prefix is accurate to the file name but it creates a question at every call site: "is this from lib-agency.sh or from somewhere in the companion ecosystem?" It also violates the pattern where public functions in supporting libs are either named after the lib (`verdict_*`, `intercore_*`) or after the domain concept they serve.

**Recommendation:** Use `spec_` as the public prefix (e.g. `spec_load`, `spec_get_stage`, `spec_get_budget`, `spec_get_gate`, `spec_available`) and `_spec_` for private helpers. This is shorter, unambiguous, and fits the pattern of `lib-*.sh` files providing `<concept>_` prefixed functions. Alternatively `sprint_spec_*` is more verbose but makes the coupling to the sprint domain explicit.

The `_AGENCY_SPEC_JSON` cache variable and `_AGENCY_SPEC_LOADED` guard should follow the same rename to `_SPEC_JSON` / `_SPEC_LOADED` (or `_SPRINT_SPEC_JSON` to match the existing `_SPRINT_LOADED` guard pattern in `lib-sprint.sh`).

### Finding 1.2: `_phase_to_stage` is underscore-private but has no owning lib prefix

**Severity: Low**

The plan places `_phase_to_stage` in `lib-sprint.sh`. All other private helpers in that file use the `_sprint_` prefix: `_sprint_resolve_run_id`, `_sprint_phase_cost_estimate`, `_sprint_default_budget`. `_phase_to_stage` does not follow this convention. Rename to `_sprint_phase_to_stage`.

### Finding 1.3: `sprint_stage_budget` vs `sprint_budget_remaining` — asymmetric naming

**Severity: Low**

The existing budget function is `sprint_budget_remaining()`. The plan proposes:
- `sprint_stage_budget()` — allocation for a stage
- `sprint_stage_budget_remaining()` — remaining budget for a stage
- `sprint_check_stage_budget()` — check and warn

The first one breaks the `sprint_<verb>_<noun>` pattern. The existing naming suggests `<verb>_<noun>`: `budget_remaining` (verb: budget, noun modifier: remaining). The proposed `stage_budget` reverses this to `<noun>_<verb>`.

More consistent names:
- `sprint_stage_budget()` → `sprint_budget_stage()` (allocation for stage)
- `sprint_stage_budget_remaining()` → `sprint_budget_stage_remaining()` (remaining for stage)
- `sprint_check_stage_budget()` → `sprint_budget_stage_check()` (check/warn for stage)

This keeps the `sprint_budget_*` family cohesive alongside `sprint_budget_remaining`.

### Finding 1.4: `agency_spec_available` — predicate naming inconsistency

**Severity: Low**

The plan lists `agency_spec_available()` as a function that "returns 0 if spec loaded, 1 if fallback." All other predicate-style functions in the lib files use no special suffix — they return 0/1 by convention. However, the naming follows the pattern from `intercore_available()` in lib-intercore.sh, so this is acceptable. No change required, but document the return-code semantics in the function comment since it is the opposite of what a boolean reader expects (`available` implies truthy=0, which is correct for bash).

---

## 2. Bash Patterns

### Finding 2.1: Python inline heredoc pattern — fine for scripts, wrong for hooks libs

**Severity: Medium**

The plan places `agency-spec-helper.py` at `os/clavain/hooks/agency-spec-helper.py` and calls it from `lib-agency.sh`. This is a new pattern for the hooks directory: no `.py` files currently exist in `hooks/`. The only precedent for calling Python from bash in this codebase is:

1. `scripts/sync-upstreams.sh` — calls Python via inline heredoc (`python3 - "$JSON" <<'PY'`)
2. `scripts/gen-catalog.py` — standalone script invoked from `catalog-reminder.sh` via the instruction to run it (not direct invocation)

The plan's approach of a standalone `.py` file called by subcommand is architecturally sound. The concern is the structural test at `tests/structural/test_scripts.py`: `_get_python_scripts()` only scans `scripts/*.py`, not `hooks/*.py`. A `.py` file in `hooks/` will:
- Not be syntax-checked by `test_python_scripts_syntax`
- Not be checked for shebang by `test_scripts_have_shebang`
- Not be included in `test_shell_scripts_syntax` (correct, it is Python)

This is a test gap, not a correctness problem, but it means the helper could silently develop syntax errors. See the test coverage section for the fix.

The dependency check for `jsonschema` is the right approach (runtime check, degrade gracefully). PyYAML is already in the test venv's `pyproject.toml` as a dependency, so it is available on this server.

### Finding 2.2: `local allocated=$(( ... ))` and `local remaining=$(( ... ))` mask arithmetic errors

**Severity: Medium**

The plan proposes two functions with this pattern:

```bash
# sprint_stage_budget()
local allocated=$(( total_budget * share / 100 ))
[[ $allocated -lt $min_tokens ]] && allocated=$min_tokens
echo "$allocated"

# sprint_stage_budget_remaining()
local remaining=$(( allocated - spent ))
[[ $remaining -lt 0 ]] && remaining=0
```

Under `set -e` (which `lib-verdict.sh` uses and some callers may inherit), `local var=$(...)` is a known bash gotcha: the `local` builtin always returns 0, so a failing command substitution inside it does not trigger `set -e`. Worse, for arithmetic expansion, if `share` or `total_budget` is empty or non-numeric, the arithmetic will expand to an error or 0 silently.

The existing `sprint_budget_remaining()` in lib-sprint.sh has the same anti-pattern at line 392 (`local remaining=$(( budget - spent ))`), so this is a pre-existing problem being propagated. The plan should not repeat it.

**Fix:** Split declaration from assignment, consistent with the style used elsewhere in lib-sprint.sh for error-sensitive assignments:

```bash
sprint_stage_budget() {
    local sprint_id="$1" stage="$2"
    local total_budget
    total_budget=$(sprint_budget_total "$sprint_id") || { echo "0"; return 0; }
    [[ "$total_budget" == "0" || -z "$total_budget" ]] && { echo "0"; return 0; }

    local stage_budget_json
    stage_budget_json=$(agency_get_budget "$stage") || { echo "$total_budget"; return 0; }
    local share min_tokens
    share=$(echo "$stage_budget_json" | jq -r '.share // 20')
    min_tokens=$(echo "$stage_budget_json" | jq -r '.min_tokens // 1000')

    # Guard non-numeric values before arithmetic
    [[ "$share" =~ ^[0-9]+$ ]] || share=20
    [[ "$min_tokens" =~ ^[0-9]+$ ]] || min_tokens=1000

    local allocated
    allocated=$(( total_budget * share / 100 ))
    [[ $allocated -lt $min_tokens ]] && allocated=$min_tokens
    echo "$allocated"
}
```

Same treatment for `sprint_stage_budget_remaining` — validate `allocated` and `spent` are numeric before the subtraction.

### Finding 2.3: `[[ "$gates_json" != "{}" ]]` is a fragile JSON presence check

**Severity: Low**

In the proposed `enforce_gate()` rewrite:

```bash
if [[ "$gates_json" != "{}" ]]; then
    _evaluate_spec_gates ...
```

This assumes the Python helper returns exactly `{}` (empty object with no whitespace) when no gates are defined for a stage. If the helper returns `{ }` or `{\n}` (pretty-printed), the check fails. Use jq to test for emptiness:

```bash
local has_gates
has_gates=$(echo "$gates_json" | jq 'length > 0' 2>/dev/null) || has_gates="false"
if [[ "$has_gates" == "true" ]]; then
    _evaluate_spec_gates ...
```

This is already the pattern elsewhere in lib-sprint.sh (e.g. `[[ "$agents_json" != "[]" ]]` for arrays — also fragile for the same reason, but arrays from jq are compact by default so it is less likely to bite).

### Finding 2.4: `sprint_budget_total` is called but not defined in the plan

**Severity: Medium**

The plan's `sprint_stage_budget()` calls `sprint_budget_total "$sprint_id"`. This function does not exist in `lib-sprint.sh`. The existing function is `sprint_budget_remaining()` which reads `token_budget` from `sprint_read_state`. There is no `sprint_budget_total` anywhere in the hooks directory.

Either:
- Define `sprint_budget_total` as part of this plan (reads `token_budget` from sprint state, returns it), or
- Inline the logic from `sprint_budget_remaining` that extracts `token_budget`

This is a missing definition that will cause a runtime error when `sprint_stage_budget` is called. It needs to be in the plan.

### Finding 2.5: `agency_get_default` is called but not listed in the function inventory

**Severity: Low**

The proposed `enforce_gate()` calls `agency_get_default "gate_mode"` but this function is not listed in the `lib-agency.sh` function inventory in the plan. The inventory lists: `agency_load_spec`, `agency_get_stage`, `agency_get_gate`, `agency_get_budget`, `agency_get_agents`, `agency_get_companion`, `agency_spec_available`. Add `agency_get_default <key>` to query top-level `defaults:` values, or rename the call to `agency_get_stage_gates` which is also referenced but also not in the inventory.

Tally: `agency_get_stage_gates` and `agency_get_default` appear in the Batch 3 code samples but are absent from the Batch 2 function inventory. Both need to be in the plan.

### Finding 2.6: Shadow mode and `_evaluate_spec_gates` have no error visibility contract

**Severity: Medium**

The plan says "evaluate gates, log results, but always return 0" for shadow mode. This is correct behavior, but the plan does not specify where the log output goes. Looking at existing patterns:

- `sprint_should_pause()` writes structured pause reasons to stdout in the format `gate_blocked|$target_phase|message`
- `enforce_gate()` currently writes nothing to stdout (delegates silently to intercore)

Shadow mode gate evaluation results should go to stderr (not stdout, which callers parse for structured signals). The plan should explicitly state: shadow mode evaluation logs to stderr, never stdout. The existing `echo "budget_exceeded|$stage|stage budget depleted" >&2` in `sprint_check_stage_budget` does redirect to stderr, which is consistent, but the gate shadow mode text is unspecified.

Also, `_evaluate_spec_gates` is introduced as a private helper with no defined signature or return contract. Since it is called inside the rewritten `enforce_gate`, it needs at minimum: argument list, return code semantics in enforce mode vs shadow mode, and what it writes to stderr vs stdout. The plan should specify this before implementation.

---

## 3. File Organization

### Finding 3.1: `lib-agency.sh` placement in `hooks/` is correct

**Severity: Note (no issue)**

All library files (`lib-sprint.sh`, `lib-intercore.sh`, `lib-gates.sh`, `lib-verdict.sh`, `lib-signals.sh`, `lib-discovery.sh`) live in `hooks/`. Placing `lib-agency.sh` there is consistent.

### Finding 3.2: `agency-spec-helper.py` in `hooks/` is a new category

**Severity: Low**

No `.py` files currently exist in `hooks/`. The directory contains only `.sh` files plus `hooks.json`. The structural tests scan `hooks/*.sh` for syntax and shebang but only scan `scripts/*.py` for Python. The plan implicitly creates a new category that falls through the test coverage grid.

There are two options:

**Option A (recommended):** Move the helper to `scripts/agency-spec-helper.py` and reference it as `${CLAVAIN_DIR}/scripts/agency-spec-helper.py`. This is where `gen-catalog.py` and the `clavain_sync` package live. The structural test `_get_python_scripts()` already covers `scripts/*.py`. The only change needed is to extend the glob to catch the helper specifically (it currently only returns `scripts/*.py` at the top level, not `scripts/**/*.py`, but the helper would be at top level).

**Option B:** Keep it in `hooks/agency-spec-helper.py` and extend `test_scripts.py` to also scan `hooks/*.py`.

Option A requires less test infrastructure change and follows the precedent of `gen-catalog.py`.

### Finding 3.3: `config/` directory placement for schema and spec is correct

**Severity: Note (no issue)**

`os/clavain/config/routing.yaml` already exists, establishing that `config/` holds YAML configuration files. Placing `agency-spec.yaml` and `agency-spec.schema.json` there is consistent with this pattern.

---

## 4. Error Handling

### Finding 4.1: "Never crash the sprint" is correctly specified for loader failure, but the fallback path for `_evaluate_spec_gates` failure is not

**Severity: Medium**

The plan specifies that validation failures in `agency_load_spec` fall back to default spec (warn + continue). This is correct. However, `_evaluate_spec_gates` is called from `enforce_gate()` and the error path is not fully specified.

If `_evaluate_spec_gates` itself fails (e.g., a `command` gate type runs a command that is not found, or a `verdict_clean` gate finds a malformed verdict file), does `enforce_gate` return 0 (fail-open) or 1 (fail-closed)?

The existing behavior of `enforce_gate` is fail-open: `run_id=$(_sprint_resolve_run_id "$bead_id") || return 0`. This is the "never crash the sprint" convention. The new `_evaluate_spec_gates` should preserve this: on any internal error, log to stderr and return 0. The plan should make this explicit.

Additionally, the shadow mode check (`gate_mode=$(agency_get_default "gate_mode") || gate_mode="enforce"`) correctly falls back to enforce mode if the spec is unavailable — this is the safe default. This is correct.

### Finding 4.2: Validation warning must be distinguishable from other stderr output

**Severity: Low**

The plan says "warn to stderr" for validation failures. The existing codebase uses a mix of plain `echo "..." >&2` and structured formats. For observability, spec validation warnings should use a consistent prefix so they can be grepped in hook output logs. Suggest: `echo "agency-spec: validation warning: ..." >&2` with the `agency-spec:` prefix matching the file name. This follows the pattern used in `lib-intercore.sh`: `printf 'ic: DB health check failed...\n' >&2`.

### Finding 4.3: Budget shares validation — normalize vs reject

**Severity: Low**

The risks table says "Warn and normalize if off" for budget shares that don't sum to 100. The normalization approach (proportional rescaling) is more complex to implement correctly than it appears. If `share` values are integers (as the schema specifies), proportional rescaling may not produce integers that sum to 100 (integer rounding). The simpler safe fallback is: if shares don't sum to 100, warn and use uniform 20% for all stages (5 stages * 20% = 100%). Normalization can be a follow-on improvement. The plan should specify which approach will be implemented.

---

## 5. Test Strategy

### Finding 5.1: The 6 test types are necessary but missing coverage for the gate evaluation dispatch

**Severity: Medium**

The plan's 6 tests cover:
1. Schema validation (Python helper pass/fail) — good
2. Loader test (agency_get_stage returns JSON) — good
3. Override merge test — good
4. Gate test (spec `command` gate → enforce_gate checks it) — **partial**
5. Budget split test — good
6. Companion lookup test — good

Test 4 covers the happy path for one gate type (`command`). But `_evaluate_spec_gates` must dispatch across four gate types: `artifact_reviewed`, `command`, `phase_completed`, `verdict_clean`. Each type has different file access or command execution behavior. The plan should add:

- One test per gate type in enforce mode (passes/fails correctly)
- One shadow mode test confirming it always returns 0 regardless of gate result
- One test for the `gate_mode == "off"` early-exit path

The existing test for `enforce_gate` at line 678 of `test_lib_sprint.bats` is a pure delegation test (confirms it calls `intercore_gate_check`). After the plan's modification, this test will need to be updated to mock `agency_get_default` and `agency_get_stage_gates` — the plan does not mention updating the existing test.

### Finding 5.2: No test for the Python helper's `query` subcommand

**Severity: Low**

The plan specifies three subcommands for the helper: `load`, `validate`, `query`. Test 1 covers `validate`, Test 2 implicitly covers `load`. The `query` subcommand (accepts JSON on stdin, extracts dotted path) has no dedicated test. Add a test that pipes known JSON to `query` and verifies the extracted value. This subcommand is the most likely to have off-by-one errors in path parsing.

### Finding 5.3: No test for `agency_invalidate_cache`

**Severity: Low**

The plan mentions `agency_invalidate_cache` as a function to force spec reload. The caching mechanism (`_AGENCY_SPEC_JSON` bash variable) is session-scoped. There should be a test confirming:
- First call loads from disk (slow path)
- Second call uses cache (no subprocess)
- After `agency_invalidate_cache`, third call reloads from disk

This is testable by mocking the Python helper with a counter.

### Finding 5.4: Structural test extension needed for hooks/*.py

**Severity: Medium**

As noted in Finding 3.2, placing `agency-spec-helper.py` in `hooks/` creates a coverage gap in `test_scripts.py`. If the helper stays in `hooks/`, extend `_get_python_scripts()` to also scan `hooks/*.py`:

```python
def _get_python_scripts():
    root = Path(__file__).resolve().parent.parent.parent
    scripts = []
    for subdir in ("scripts", "hooks"):
        d = root / subdir
        if d.is_dir():
            scripts.extend(sorted(d.glob("*.py")))
    return scripts
```

If moved to `scripts/`, no change needed.

### Finding 5.5: Test for `sprint_stage_tokens_spent` — function not defined in plan

**Severity: Medium**

The plan's `sprint_stage_budget_remaining()` calls `sprint_stage_tokens_spent "$sprint_id" "$stage"`. This function does not exist in `lib-sprint.sh` and is not defined in the plan. Budget Test 5 ("verify sprint_stage_budget splits correctly") will fail at the remaining calculation unless `sprint_stage_tokens_spent` is also implemented. The plan needs to either:
- Define `sprint_stage_tokens_spent` (reads per-stage token data from intercore state, likely from the `phase_tokens` blob written by `sprint_record_phase_tokens`)
- Or simplify `sprint_stage_budget_remaining` to use the total spend and a proportional attribution, which is less accurate but simpler

This is the same class of problem as Finding 2.4 (calling undefined functions).

---

## 6. Additional Observations

### 6.1: `lib-agency.sh` should not use `set -euo pipefail`

The plan does not mention this, but `lib-intercore.sh` has an explicit comment: "Do NOT use set -e here — it would exit the parent shell on any failure." All library files (`lib-sprint.sh`, `lib-intercore.sh`, `lib-signals.sh`) are sourced by hook entry points and must not set strict mode. Only hook entry point scripts (`session-start.sh`, `auto-stop-actions.sh`, etc.) use `set -euo pipefail`. The plan should note that `lib-agency.sh` must not use strict mode.

`lib-verdict.sh` is the exception — it has `set -euo pipefail` and appears to be source-able. Inspect whether this causes issues before following that precedent.

### 6.2: Session-scoped caching has a correctness assumption worth documenting

The plan caches the parsed spec in `_AGENCY_SPEC_JSON` (a bash variable). Bash variable caches are process-scoped. Since each hook invocation is a new subshell, the cache provides no benefit across hook invocations — it only benefits multiple calls within a single sourced execution (e.g., `enforce_gate` calling `agency_get_stage_gates` and `agency_get_budget` in the same script run). This is fine but worth documenting so future maintainers don't expect cross-invocation caching.

If cross-invocation caching is desired, use `intercore_state_set` with a short TTL (as `session-start.sh` does for discovery briefs). The plan doesn't need this for correctness, but should document the scope.

### 6.3: Python helper subcommand interface — prefer stdin for JSON passthrough

The plan specifies:
```
agency-spec-helper.py query <spec_json> <jq_path>  → value on stdout
```

Passing large JSON as a command-line argument is fragile (ARG_MAX limits, shell quoting). The plan's description says "Accept JSON on stdin" for `query`, but the usage signature shows it as a positional argument. These two descriptions conflict. Standardize on stdin for JSON input:

```
echo "$spec_json" | agency-spec-helper.py query <jq_path>
```

This is consistent with how `intercore_state_set` works (stdin for JSON) and avoids argument length limits when the spec is large.

---

## Summary of Issues by Priority

| # | Finding | Severity | Blocking? |
|---|---------|----------|-----------|
| 2.4 | `sprint_budget_total` not defined | Medium | Yes — runtime error |
| 5.5 | `sprint_stage_tokens_spent` not defined | Medium | Yes — runtime error |
| 1.1 | `agency_*` prefix inconsistency | Medium | No — but creates confusion |
| 2.2 | `local` + arithmetic anti-pattern | Medium | No — silent failure risk |
| 2.5 | `agency_get_default` / `agency_get_stage_gates` not in inventory | Low | Yes — incomplete spec |
| 4.1 | `_evaluate_spec_gates` error contract unspecified | Medium | No — but sets precedent |
| 5.1 | Missing gate-type-specific tests | Medium | No — coverage gap |
| 5.4 | `hooks/*.py` not covered by structural test | Medium | No — coverage gap |
| 2.3 | Fragile `!= "{}"` JSON check | Low | No |
| 1.2 | `_phase_to_stage` missing `_sprint_` prefix | Low | No |
| 1.3 | `sprint_stage_budget` breaks naming convention | Low | No |
| 2.6 | Shadow mode log destination unspecified | Low | No |
| 3.2 | `.py` file in `hooks/` is a new category | Low | No |
| 5.2 | `query` subcommand untested | Low | No |
| 6.1 | `set -euo pipefail` prohibition not mentioned | Low | No |
| 6.3 | JSON on CLI vs stdin conflict in helper spec | Low | No |

**Two runtime-error blockers** (Finding 2.4 and 5.5) need to be resolved before implementation starts. The remaining issues should be addressed in the plan revision or flagged as implementation-time decisions.
