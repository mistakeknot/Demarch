# Quality Review: C1 Agency Spec Implementation

**Date:** 2026-02-22
**Reviewer:** Flux-drive Quality & Style Reviewer
**Scope:** 4 new files + 1 modified file in `os/clavain/`

---

## Files Reviewed

1. `os/clavain/config/agency-spec.schema.json` — JSON Schema (draft-07)
2. `os/clavain/config/agency-spec.yaml` — Default spec (5 stages, 8 companions)
3. `os/clavain/hooks/lib-spec.sh` — Bash spec loader library
4. `os/clavain/scripts/agency-spec-helper.py` — Python YAML→JSON helper
5. `os/clavain/hooks/lib-sprint.sh` — Modified: data-driven gates + per-stage budget

---

## Overall Assessment

The implementation is structurally sound and follows documented conventions closely. The fail-safe layering (spec → fallback, shadow mode before enforce, ic gate always-mandatory) is correctly implemented. Three issues warrant attention before graduate to `gate_mode: enforce`: one security issue (eval injection in gate evaluator), one correctness issue (stale failed/fallback cache on reload), and one schema ambiguity (missing `condition` field on gate_spec that is referenced in the YAML).

---

## File 1: `agency-spec.schema.json`

### Findings

**[MINOR] Root-level `additionalProperties: false` may block future top-level fields.**

Line 8 sets `additionalProperties: false` at the root. The spec comment says "Override: place `.clavain/agency-spec.yaml` in project root" and the merge semantic notes encourage extensibility. If a future key is added at the root (e.g., `metadata`, `version_history`), it will fail validation silently (the validator is non-blocking, but the schema itself becomes misleading). The `stage` definition correctly uses `additionalProperties: true` for extensibility — the same reasoning applies at the root.

This is a design judgment call, not a bug, but is worth noting given the stated extensibility goals.

**[MINOR] `condition` field present in `agent_spec` and in YAML gate definitions, but absent from `gate_spec` definition.**

`agency-spec.yaml` line 200 uses `condition: "has_security_surface"` on the optional `fd-safety` agent (correct, `agent_spec` has `additionalProperties: true` and `condition` is defined there). However, the `gate_spec` definition at line 183-184 has `condition` as a documented property with `x-note`. The `gate_spec` does define `condition` (line 181), so this is actually present. No issue.

**[MINOR] `budget_spec.share` type is `integer`, but normalization in Python produces rounded integers. No mismatch.**

Confirmed consistent.

**[ADVISORY] `artifact_spec.type` enum is a closed list.**

The enum is `["markdown", "json", "git_diff", "test_output", "verdict_json", "git_commit"]`. Any new artifact type added to a project override would fail schema validation (non-blocking, but generates a warning). Consider whether `additionalProperties: true` or an open enum would serve extensibility better. The `stage` definition is already `additionalProperties: true` for this reason.

---

## File 2: `agency-spec.yaml`

### Findings

**[PASS] Budget shares sum to 100%.**

`discover:10 + design:25 + build:40 + ship:20 + reflect:5 = 100`. Invariant holds.

**[PASS] `gate_mode: shadow` in defaults is the correct conservative posture for a first rollout.**

The comment "Start in shadow mode; graduate to enforce after validation" is accurate and appropriate.

**[ISSUE] `tests_pass` gate command uses `eval`-equivalent shell expansion at runtime.**

The `tests_pass` gate command in `ship`:
```yaml
command: "bash -c 'cd \"${PROJECT_DIR:-.}\" && if [ -f Makefile ] ...'"
```
This string is stored in YAML, passed through JSON, extracted via `jq -r`, and then executed via `eval "$cmd"` in `_sprint_evaluate_spec_gates` (lib-sprint.sh line 702). The `${PROJECT_DIR:-.}` expansion happens inside `bash -c`, so it is safe only if `PROJECT_DIR` is not attacker-controlled. In practice this is an environment variable set by the sprint runner, so the risk is low. However, the `eval` path (discussed separately under lib-sprint.sh) is the actual concern — the gate command field itself is fine; the executor is the problem.

**[PASS] Companion declarations are abstract and correctly scoped to C1.**

The comment "Per-agent detail deferred to C2 self-declaration" is a clean deferral. The `provides` arrays align with `requires.capabilities` across stages (spot-checked: `multi_agent_coordination` required by `build`, provided by `interlock`; `verdict_aggregation` required by `ship`, provided by `intersynth`). No gaps found.

**[MINOR] `discover` and `reflect` stages have `gates: {}` — empty objects.**

This is valid YAML and loads cleanly. `_sprint_evaluate_spec_gates` short-circuits on `length > 0` check. No bug. However, it might be cleaner to omit the `gates` key entirely when empty, to match the schema's pattern (key is optional). This is cosmetic.

---

## File 3: `os/clavain/hooks/lib-spec.sh`

### Findings

**[PASS] No `set -euo pipefail`. Sourced by hook entry points. Correct.**

The comment at line 7 explains the constraint. All functions return 0 on error per the fail-safe contract.

**[PASS] Double-source guard pattern is consistent with lib-sprint.sh and lib-intercore.sh.**

`_SPEC_LIB_SOURCED` guard at line 12-13. Consistent with `_SPRINT_LOADED` and `_GATES_LOADED` patterns.

**[ISSUE] Stale cache not cleared on `failed`/`fallback` state across process lifetime.**

At line 57:
```bash
[[ "$_SPEC_LOADED" == "failed" || "$_SPEC_LOADED" == "fallback" ]] && return 0
```
Once `_SPEC_LOADED` is set to `"failed"` (e.g., Python unavailable at session start), subsequent calls to `spec_load` will permanently skip. This is intentional per the comment: "load attempted, failed." However, if the user installs PyYAML mid-session (unlikely but possible in dev contexts), there is no recovery path short of `spec_invalidate_cache`. The mtime staleness check (lines 45-53) only runs for `ok` state, not for `failed`.

This is low risk for production (sessions are bounded and PyYAML is a fixed dependency), but the asymmetry is worth documenting in `lib-spec.sh`'s state machine comment. A one-liner addition to the existing comment block is sufficient.

**[PASS] Invariant ordering: `_SPEC_JSON` set before `_SPEC_LOADED="ok"` (lines 103-106).**

The comment at line 21-22 documents this correctly and the implementation matches.

**[PASS] Schema validation is non-blocking (warn only, continue with loaded spec).**

Lines 108-113. Correct posture for a sourced library that must not block hooks.

**[MINOR] `spec_available` calls `spec_load` on every invocation.**

```bash
spec_available() {
    spec_load  # Ensure loaded
    [[ "$_SPEC_LOADED" == "ok" ]]
}
```
`spec_load` is idempotent (mtime check + guard), so this is not expensive after the first call. No correctness issue. The pattern is clear.

**[MINOR] `spec_get_stage_gates` is redundant with `spec_get_stage` + jq.**

All `spec_get_*` helpers follow the same pattern: call `spec_load`, check state, run a `jq` query. `spec_get_stage_gates` is a thin convenience wrapper over `spec_get_stage`. Given the small total function count, this is acceptable. No action needed.

**[PASS] `spec_validate_dispatch` is correctly shadow-only (warns to stderr, never returns 1).**

Line 217: only writes to `>&2` when agent not in roster. Returns 0 always. Matches the capability_mode: shadow default.

**[MINOR] `_spec_*` private prefix stated at line 5, but `_SPEC_LIB_DIR`, `_SPEC_CLAVAIN_DIR` etc. use `_SPEC_` prefix for globals, not `_spec_` for functions.**

The comment says "Private prefix: `_spec_*`" but private global variables use `_SPEC_` (uppercase). The distinction is globals vs functions. This matches the prevailing pattern in `lib-intercore.sh` (e.g., `INTERCORE_BIN`, `INTERCORE_STOP_DEDUP_SENTINEL`). No inconsistency with the codebase; the comment could be more precise by distinguishing globals from functions.

---

## File 4: `os/clavain/scripts/agency-spec-helper.py`

### Findings

**[PASS] Under 100 lines, pure data transform, graceful degradation.**

File is 133 lines including docstring and `if __name__ == "__main__"`. Functional logic is 90 lines. `jsonschema` import is deferred to `cmd_validate` and degrades gracefully on `ImportError`.

**[PASS] Type hints on all public function signatures.**

`deep_merge`, `normalize_budget`, `cmd_load`, `cmd_validate`, `main` all have signatures with type annotations. Consistent with Python typing conventions.

**[ISSUE] Budget normalization rounding can produce share totals that silently deviate from 100.**

In `normalize_budget`:
```python
budget["share"] = round(budget["share"] * 100 / total_share)
```
`round()` uses banker's rounding (round-half-to-even). The correction step at lines 40-44 fixes the sum after rounding:
```python
new_total = sum(s.get("budget", {}).get("share", 0) for s in stages.values())
if new_total != 100:
    largest["budget"]["share"] += 100 - new_total
```
This is correct but only adjusts the `share` key. If a stage's `budget` dict is empty (no `share` key), `s.get("budget", {}).get("share", 0)` returns 0 and that stage is excluded from `total_share`. Then `normalize_budget` outputs shares that do not cover the full budget for stages without a `share`. This is an edge case (the default spec always has `share` on every stage), but a project override that adds a stage without `share` would silently miscalculate.

The fix is a no-op guard: if `total_share == 0` after counting only stages with `share`, skip normalization entirely. The current guard `if total_share > 0 and total_share != 100` already handles `total_share == 0` (skips), which is correct. But the adjustment to `largest` at line 43 mutates the dict in-place without guarding against `budget` being missing:
```python
largest["budget"]["share"] += 100 - new_total
```
If `largest` is somehow a stage with no `budget` key (impossible given the `max` key function but not type-constrained), this would raise `KeyError`. This is a theoretical edge case, not a practical bug.

**[PASS] `yaml.safe_load` used, not `yaml.load`.**

Line 62, 98. Correct. No arbitrary code execution risk.

**[PASS] `FileNotFoundError` for override path is silently swallowed (line 73).**

The comment "No override is fine" is correct — override absence is expected behavior. `yaml.YAMLError` for the override logs and continues with base spec (line 76). Correct degradation.

**[MINOR] `cmd_validate` reads the YAML file again from disk instead of reusing the already-parsed spec.**

```python
def cmd_validate(args):
    ...
    with open(spec_path) as f:
        spec = yaml.safe_load(f) or {}
```
This is called after `cmd_load` in a separate process invocation (`spec_load` calls the helper twice: once for `load`, once for `validate`). Re-reading from disk is expected for separate invocations. No issue.

**[MINOR] No `__all__` export list.**

Not a project convention (no other Python files use `__all__`). Not flagged.

---

## File 5: `os/clavain/hooks/lib-sprint.sh` (Modified Sections)

### Findings

**[CRITICAL] `eval "$cmd"` in `_sprint_evaluate_spec_gates` is an injection surface.**

```bash
# lib-sprint.sh line 702
eval "$cmd" >/dev/null 2>&1
actual_exit=$?
```
`$cmd` is extracted via `jq -r '.command // ""'` from the spec JSON, which originates from a YAML file on disk. In the default case this is `os/clavain/config/agency-spec.yaml` (trusted) or a project override at `.clavain/agency-spec.yaml`. A project override with a malicious `command` field would execute arbitrary shell code at gate evaluation time. The comment in the schema ("must be idempotent and read-only") is advice, not a constraint.

The risk is real for any workflow that clones an untrusted repository and runs Clavain without auditing the project's `.clavain/agency-spec.yaml`.

**Recommended fix:** Replace `eval` with `bash -c`:
```bash
bash -c "$cmd" >/dev/null 2>&1
actual_exit=$?
```
This is marginally safer (avoids alias expansion and some interactive-mode side effects) but does not eliminate injection risk from the command string itself. The more substantive fix is to restrict `command` gate values to a known-safe allowlist or require the gate to be disabled in project overrides rather than replaced with arbitrary commands.

At minimum, add a comment warning that `command` gate values are executed as shell and that project overrides should be audited before running in enforce mode.

**[PASS] ic gate check is always-mandatory before spec gates.**

```bash
# lib-sprint.sh lines 774-776
if ! intercore_gate_check "$run_id"; then
    return 1  # ic gate blocked — spec gates cannot override
fi
```
The invariant "ic gates are mandatory precondition; spec gates are additive only" is correctly implemented. Spec gates cannot bypass ic.

**[PASS] Shadow mode correctly uses `|| true` to prevent gate failures from propagating.**

```bash
# line 793
_sprint_evaluate_spec_gates "$gates_json" "$bead_id" "$target_phase" "$artifact_path" "shadow" || true
return 0  # Shadow: always pass
```
The `|| true` is necessary because without `set -e`, return code propagation depends on the caller. With `|| true` the intent is unambiguous.

**[ISSUE] `_sprint_resolve_run_id` failure in `enforce_gate` returns 0 instead of 1.**

```bash
# lib-sprint.sh lines 773-775
run_id=$(_sprint_resolve_run_id "$bead_id") || return 0
if ! intercore_gate_check "$run_id"; then
    return 1
fi
```
When `_sprint_resolve_run_id` fails (no ic run for this bead), `enforce_gate` returns 0 (pass). This means a sprint without an ic run silently bypasses all gate enforcement. This is consistent with the fail-safe contract ("never block workflow"), but the semantics are surprising: a sprint that was never initialized in intercore is treated as having passed all gates.

This is a known tradeoff in the fail-safe design. The risk is that a misconfigured sprint never gets gate enforcement. It should be documented explicitly — either in a comment at this return site or in AGENTS.md.

**[PASS] `_sprint_sum_all_stage_allocations` correctly uses a fixed stage list.**

```bash
for stage in discover design build ship reflect; do
```
This hardcodes the 5 canonical stages. If a project override adds a 6th stage, `sprint_budget_stage` for that stage would fall through to `total_budget` (no-spec fallback), which is correct behavior (conservative: full budget).

**[PASS] Budget cap calculation is correct.**

```bash
# lines 466-469
if [[ $uncapped_sum -gt $total_budget && $uncapped_sum -gt 0 ]]; then
    allocated=$(( allocated * total_budget / uncapped_sum ))
fi
```
Integer division. For large budgets this is fine. For very small budgets (e.g., total=5000, stage share=10%, min_tokens=1000), integer truncation could produce 0. But `allocated` cannot be less than `min_tokens` from the prior line, so the cap rescaling can reduce below `min_tokens`. This is acceptable behavior (overallocation cap takes precedence over min_tokens floor), but is not documented.

**[MINOR] `sprint_budget_stage_check` emits to stderr with a pipe-separated format.**

```bash
echo "budget_exceeded|$stage|stage budget depleted" >&2
```
This matches the pattern used in `sprint_advance` (`echo "budget_exceeded|$current_phase|..."`) and `sprint_should_pause` (`echo "gate_blocked|$target_phase|..."`). The structured format is consistent. Callers parse stdout, not stderr, so this diagnostic-to-stderr pattern is correct.

**[MINOR] `_sprint_phase_to_stage` maps `done` to `"done"`, not a stage name.**

```bash
done) echo "done" ;;
```
`"done"` is not a stage in `agency-spec.yaml` (stages are discover/design/build/ship/reflect). `spec_get_stage_gates "done"` will return `{}` (no gates), which is correct behavior — there is no gate to enforce after the sprint is complete. No bug, but the mapping communicates clearly.

**[PASS] `verdict_clean` gate evaluation correctly iterates verdict files with a `[[ -f "$verdict_file" ]] || continue` guard.**

Lines 730-737. The glob `*.json` check with a file existence guard prevents false positives when the directory is empty (bash expands the glob to the literal pattern string). This is correct defensive shell.

**[PASS] `artifact_reviewed` gate uses `ls | wc -l` for verdict counting.**

```bash
verdict_count=$(ls .clavain/verdicts/*.json 2>/dev/null | wc -l) || verdict_count=0
```
`ls` + `wc -l` is used (rather than `find`) but this is within a controlled path with no user-controllable filenames. Acceptable in context.

---

## Cross-Cutting Findings

### Naming Consistency

All new public functions follow the `spec_*` prefix (lib-spec.sh) and private `_spec_*` / `_SPEC_*` conventions. New sprint functions (`sprint_budget_stage`, `sprint_budget_stage_remaining`, `sprint_budget_total`, `sprint_stage_tokens_spent`, `sprint_budget_stage_check`) follow the established `sprint_*` prefix. `_sprint_phase_to_stage` and `_sprint_evaluate_spec_gates` follow the `_sprint_*` private prefix. Naming is consistent throughout.

### Error Propagation

All functions return 0 on error in fail-safe contexts. `enforce_gate` returns 1 only on ic gate block or spec gate block in enforce mode. Shadow mode always returns 0. This layering is correct.

### Test Coverage Gap

There are no tests visible for `lib-spec.sh` or the new budget functions in `lib-sprint.sh`. Given that `_sprint_sum_all_stage_allocations` calls `spec_get_budget` in a loop and `sprint_budget_stage` does integer arithmetic with potential truncation, these are candidates for shell unit tests (bats or equivalent) before `gate_mode: enforce` is activated.

---

## Priority Summary

| Priority | File | Finding |
|----------|------|---------|
| HIGH | lib-sprint.sh:702 | `eval "$cmd"` executes arbitrary shell from spec command gates — injection surface for untrusted project overrides |
| MEDIUM | lib-sprint.sh:773 | `_sprint_resolve_run_id` failure silently passes gate — undocumented fail-open semantic |
| LOW | lib-spec.sh:57 | `failed`/`fallback` states are permanently sticky for session — no recovery path documented |
| LOW | agency-spec-helper.py:43 | `largest["budget"]["share"]` mutation assumes `budget` key exists — guarded by `max` logic but not type-constrained |
| ADVISORY | agency-spec.schema.json:8 | Root `additionalProperties: false` may block future top-level keys |
| ADVISORY | agency-spec.schema.json:117 | `artifact_spec.type` closed enum blocks project extension |

---

## Recommended Actions

1. **`eval "$cmd"` (HIGH):** Add a comment at lib-sprint.sh line 700-702 documenting the execution surface. In a follow-up sprint, restrict `command` gate values to an allowlist or add a YAML-level schema constraint (e.g., prefix must be `bash -c '...'` with no substitution from env).

2. **Silent fail-open on no run_id (MEDIUM):** Add a comment at lib-sprint.sh line 773: `# No ic run → gate enforcement unavailable, fail-open per fail-safe contract.` This makes the semantic explicit without changing behavior.

3. **Sticky failure state (LOW):** Add to the state machine comment block in lib-spec.sh: `# Note: 'failed' and 'fallback' states are not retried within a session. Call spec_invalidate_cache() to force retry.`

4. **Budget normalization edge case (LOW):** The Python helper is correct for all realistic inputs. No code change needed; the existing warning (`spec: budget shares sum to N%, normalizing to 100%`) already signals the normalization.
