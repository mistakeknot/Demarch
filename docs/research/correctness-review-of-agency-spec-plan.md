# Correctness Review: C1 Agency Specs Plan

**Plan reviewed:** `os/clavain/docs/plans/2026-02-22-c1-agency-specs.md`
**Existing implementation:** `os/clavain/hooks/lib-sprint.sh` (enforce_gate at line 503, sprint_budget_remaining at line 380)
**Reviewer:** Julik / Correctness Review Agent
**Date:** 2026-02-22

---

## Invariants That Must Hold

Before going through the findings, the invariants this plan must preserve:

1. **Gate enforcement must never silently no-op.** A gate that "passes" because of a load failure must be distinguishable from a gate that genuinely passed. The current code is fail-open by design (intercore unavailable = gate disabled). The new code must be equally deliberate about its fail mode.

2. **Budget totals must not exceed the declared sprint budget.** If stage allocations can grow past the total (due to min_tokens floors), the budget constraint is fictional.

3. **Spec cache state must not diverge from disk mid-session.** A bash-variable cache has process lifetime. Its staleness properties must be documented and understood by callers.

4. **Deep merge must produce a valid, deterministic merged spec.** Fields present in default but absent from project override must survive. Fields present in both must resolve to a single winner. Deletion must be possible.

5. **ic gate check and spec gate check are logically independent.** If either fails, the gate fails. This conjunction must be enforced at every call site, not assumed to be transitive.

---

## Finding 1: CRITICAL — Spec Gates Short-Circuit ic Gate Check

**Severity:** Data integrity / gate bypass

### The problem

The proposed `enforce_gate` replaces the existing two-line implementation with this logic:

```bash
if [[ "$gates_json" != "{}" ]]; then
    _evaluate_spec_gates ...
    return $?    # <-- returns here
fi

# Fallback: delegate to intercore gate check
local run_id
run_id=$(_sprint_resolve_run_id "$bead_id") || return 0
intercore_gate_check "$run_id"
```

When the spec defines any gates for the current stage, the function returns from `_evaluate_spec_gates` and **never calls `intercore_gate_check`**. The plan's risk table says "both must pass" but the code only achieves that if `_evaluate_spec_gates` internally calls `intercore_gate_check` — which the plan does not specify.

The plan's stated risk mitigation: "Spec gates supplement, don't replace. If both exist, both must pass." This invariant is asserted in prose but violated in the proposed code structure.

### Concrete failure sequence

1. A sprint run has an ic-registered gate that requires artifact `plan.md` to be reviewed before advancing to `executing`.
2. The agency spec for the `build` stage defines a `command` gate that runs `rg --files | wc -l` (always exits 0).
3. `_phase_to_stage("executing")` returns `"build"`.
4. `agency_get_stage_gates("build")` returns the command gate JSON — not `{}`.
5. `_evaluate_spec_gates` runs the command gate, it passes, returns 0.
6. `enforce_gate` returns 0 without ever calling `intercore_gate_check`.
7. The sprint advances past a gate that the ic kernel considers blocked.
8. Plan artifact is marked reviewed in ic state but the review agent was never actually dispatched.

This is a 3 AM incident. The sprint advances to execution with an unreviewed plan, the quality guarantee that the gate was supposed to provide is silently voided.

### Fix

The conjunction must be structural, not documentary:

```bash
enforce_gate() {
    local bead_id="$1" target_phase="$2" artifact_path="${3:-}"

    local gate_mode
    gate_mode=$(agency_get_default "gate_mode") || gate_mode="enforce"
    [[ "$gate_mode" == "off" ]] && return 0

    # Always run ic gate check first (existing invariant)
    local run_id
    run_id=$(_sprint_resolve_run_id "$bead_id") || return 0

    if ! intercore_gate_check "$run_id"; then
        # ic gate blocked — spec gates cannot override this
        return 1
    fi

    # Additionally check spec-defined gates if any exist
    local stage
    stage=$(_phase_to_stage "$target_phase")
    local gates_json
    gates_json=$(agency_get_stage_gates "$stage") || gates_json="{}"

    if [[ "$gates_json" != "{}" ]]; then
        if [[ "$gate_mode" == "shadow" ]]; then
            _evaluate_spec_gates "$gates_json" "$bead_id" "$target_phase" "$artifact_path" "shadow" || true
            return 0
        fi
        _evaluate_spec_gates "$gates_json" "$bead_id" "$target_phase" "$artifact_path" "enforce"
        return $?
    fi

    return 0
}
```

This makes ic gate check a precondition, not an alternative. Spec gates are additive only.

---

## Finding 2: CRITICAL — Silent Failure in Spec Load Causes enforce_gate to Skip Both Gate Systems

**Severity:** Gate bypass / silent data corruption

### The problem

The plan specifies: "If validation fails: warn to stderr, fall back to default spec. Never crash the sprint." The fallback behavior for `agency_get_gate` is `{}` (no spec-defined gates), and `agency_spec_available()` returns 1 for fallback mode.

The proposed `enforce_gate` calls `agency_get_stage_gates("$stage")`. If spec loading fails silently (PyYAML not installed, YAML is malformed, Python process OOMed), the function returns `{}` or an empty string. The proposed code then falls through to `intercore_gate_check`.

That much is recoverable. But there is a second failure path: the `agency_get_default "gate_mode"` call at the top of the function. If that call fails (spec not loaded, python subprocess error), the `|| gate_mode="enforce"` fallback correctly defaults to enforce mode. This particular path is safe.

The dangerous case is more subtle: what if `agency_load_spec` is called, the Python subprocess crashes mid-execution, and `_AGENCY_SPEC_LOADED` is set to a non-empty value but `_AGENCY_SPEC_JSON` is empty or partial JSON? The double-sourcing guard `[[ -n "${_AGENCY_SPEC_LOADED:-}" ]] && return 0` would prevent a retry. All subsequent queries against the corrupted cache would return empty strings or jq parse errors.

Consider `agency_get_stage_gates` when `_AGENCY_SPEC_JSON` is `""`:

```bash
gates_json=$(agency_get_stage_gates "$stage")  # returns "" on jq error
```

If `gates_json` is `""`, then `[[ "$gates_json" != "{}" ]]` is true (empty string is not `{}`). This trips the spec-gate path even though no spec is loaded. `_evaluate_spec_gates` receives `""` as `gates_json` and will either error out or pass vacuously depending on implementation.

### Concrete failure sequence

1. `agency_load_spec` is called. Python subprocess starts, reads YAML, begins JSON encoding, is killed by OOM (or YAML is 500KB and takes >10s).
2. `_AGENCY_SPEC_LOADED="partial"` is set; `_AGENCY_SPEC_JSON=""` (or truncated JSON).
3. Session continues. `enforce_gate` is called.
4. `agency_get_default "gate_mode"` returns `""` → fallback to `"enforce"` (safe so far).
5. `agency_get_stage_gates "build"` queries `_AGENCY_SPEC_JSON=""` → jq errors → returns `""`.
6. `[[ "" != "{}" ]]` is true → enters `_evaluate_spec_gates "" ...`.
7. `_evaluate_spec_gates` tries to parse `""` as JSON → empty gates, no constraints → returns 0.
8. `intercore_gate_check` is never called.
9. Gate passes with no checks applied.

### Fix

1. The cache invalidation state must distinguish "loaded successfully" from "loading attempted." Use `_AGENCY_SPEC_LOADED="ok"` vs `_AGENCY_SPEC_LOADED="failed"` vs `_AGENCY_SPEC_LOADED="fallback"`. Queries must check for `"ok"` before using the cache.

2. `enforce_gate` must treat an absent/failed spec load as "use ic gate only" not "use spec gate path with empty JSON":

```bash
# In enforce_gate, after resolving gates_json:
if [[ -n "$gates_json" && "$gates_json" != "{}" ]] && agency_spec_available; then
    ...
fi
```

3. The cache-set and guard-set must be atomic within the bash session: set `_AGENCY_SPEC_JSON` first, then set `_AGENCY_SPEC_LOADED="ok"`. If the Python call fails, set `_AGENCY_SPEC_LOADED="failed"` and leave `_AGENCY_SPEC_JSON` empty. Never set the guard before the data.

---

## Finding 3: HIGH — Budget Arithmetic Allows Total Allocation to Exceed Sprint Budget

**Severity:** Budget enforcement defeated

### The problem

```bash
local allocated=$(( total_budget * share / 100 ))
[[ $allocated -lt $min_tokens ]] && allocated=$min_tokens
echo "$allocated"
```

Integer arithmetic is used throughout. This is fine. The rounding direction is floor (integer division truncates). The real problem is the `min_tokens` floor can push any stage's allocation above its proportional share, and the sum of all stage allocations can exceed `total_budget`.

Concrete example with the plan's own defaults:

- Total budget: 50,000 tokens (a complexity-1 sprint)
- `discover`: 10% = 5,000, `min_tokens` = 1,000 → 5,000
- `design`: 25% = 12,500, `min_tokens` = 1,000 → 12,500
- `build`: 40% = 20,000, `min_tokens` = 1,000 → 20,000
- `ship`: 20% = 10,000, `min_tokens` = 1,000 → 10,000
- `reflect`: 5% = 2,500, `min_tokens` = 1,000 → 2,500

Sum: 50,000. Fine for the defaults. Now consider a project override with generous min_tokens:

```yaml
stages:
  discover:
    budget:
      share: 5
      min_tokens: 8000   # override: "always give discover 8K minimum"
  reflect:
    budget:
      share: 2
      min_tokens: 5000   # override: "always give reflect 5K minimum"
```

On a 50K sprint:
- `discover`: 5% = 2,500 < 8,000 → allocated = 8,000
- `reflect`: 2% = 1,000 < 5,000 → allocated = 5,000
- Remaining stages take their proportional shares: 12,500 + 20,000 + 10,000 = 42,500

Total allocated: 8,000 + 5,000 + 42,500 = 55,500 > 50,000 budget.

The system will happily hand out 55,500 tokens worth of "budget remaining" on a 50K sprint. A stage that checks its `sprint_stage_budget_remaining` will never see 0 until it actually overspends — at which point the total sprint budget is already blown.

The plan does note "Budget shares don't sum to 100 → Validation check on load. Warn and normalize if off." But it says nothing about `min_tokens` floors causing overallocation. Normalization of shares alone does not fix this.

### Fix

On spec load, compute the minimum guaranteed allocation across all stages:

```python
min_guarantee = sum(stage.budget.min_tokens for stage in stages.values())
if min_guarantee > total_budget_floor:
    warn("min_tokens floors sum to {min_guarantee} which may exceed sprint budgets")
```

At runtime, `sprint_stage_budget` should cap each stage's allocation so the sum cannot exceed total:

```bash
# After computing allocated:
local uncapped_sum
uncapped_sum=$(_sum_all_stage_allocations "$sprint_id")
if [[ $uncapped_sum -gt $total_budget ]]; then
    # Scale down proportionally: allocated = allocated * total_budget / uncapped_sum
    allocated=$(( allocated * total_budget / uncapped_sum ))
fi
```

Alternatively, enforce the invariant at spec-load time: reject or warn if `sum(min_tokens) > sum(share) * typical_minimum_budget / 100`. Make the constraint visible, not implicit.

---

## Finding 4: HIGH — TOCTOU in Gate Evaluation Order Under Concurrent Sessions

**Severity:** Race condition / gate bypass under multi-session use

### The problem

`sprint_claim` uses `intercore_lock "sprint-claim"` to serialize session registration. But `enforce_gate` and `sprint_should_pause` (line 578) call `intercore_gate_check` with no locking. In a scenario where two Claude sessions hold the same sprint (one is advancing, one is checking gates):

1. Session A: `enforce_gate` → `intercore_gate_check` → gate passes (artifact just delivered)
2. Session B: `enforce_gate` → `intercore_gate_check` → gate passes (same state snapshot)
3. Session A: `sprint_advance` → phase advances to `executing`
4. Session B: `sprint_advance` → phase is already `executing`, advance call returns `stale_phase`

This is not a new problem introduced by the plan, but the plan adds a second gate evaluation before the ic check. If spec gates involve side effects (command type runs a build, `artifact_reviewed` updates a reviewed counter), those side effects can now fire twice under concurrent sessions.

The `command` gate type runs `the command, check exit code`. If the command is write-side (deploys, creates files, sends notifications), double-firing is a real problem. The plan does not constrain gate commands to be read-only.

### Fix

Document the constraint: gate commands must be idempotent and read-only. State this explicitly in the schema and in `lib-agency.sh`. For command gates, add a `readonly: true` field that the schema enforces — or simply document the invariant and enforce it at spec review time.

The more structural fix: spec gate evaluation should happen inside the ic advance transaction if ic supports pre-advance hooks, or be wrapped in the same lock that `sprint_claim` uses. At minimum, `enforce_gate` should acquire a short lock before running multi-step gate evaluation.

---

## Finding 5: MEDIUM — Deep Merge Semantics Are Underspecified for Arrays and Deletions

**Severity:** Correctness / surprising runtime behavior

### The problem

The plan says: "Python helper merges project spec over default using recursive dict merge. Project values win." This describes dict behavior cleanly but leaves three cases unspecified:

**Case 1: Array fields.**

Default spec defines `stages.build.phases: ["plan-reviewed", "executing", "shipping"]`. Project override defines `stages.build.phases: ["executing"]` (they skip the planning phases). Does recursive dict merge replace the array or append to it? Python's standard recursive dict merge (`dict.update` / ChainMap) replaces array values wholesale. If the intent is to allow "add a phase to the default list," you need explicit append syntax (e.g., a `+phases:` key). If the intent is wholesale replace, that must be documented, because a project that specifies only `phases: ["executing"]` will lose the default phases entirely and break `_phase_to_stage` lookups.

**Case 2: Nested objects — partial overrides.**

Default spec defines `stages.ship.gates.verdict_clean: {max_needs_attention: 0}`. Project override defines `stages.ship.gates: {command: {command: "make test", exit_code: 0}}`. After recursive merge, does `verdict_clean` survive? With standard recursive merge, the project's `gates` dict is merged key-by-key into the default's `gates` dict — so yes, `verdict_clean` survives. But if the project override says `stages.ship.gates: null`, does that delete all gates? Python's recursive merge typically does not treat `null` as "delete the key."

**Case 3: Deletion.**

The plan does not specify how a project override removes a default gate. This is a common real need: "the default spec requires a `verdict_clean` gate, but this project has no review agents, so we want to skip it." There is no deletion syntax in the plan. The closest workaround is project overrides the gate with `gate_mode: off` (global, not per-gate), or sets `max_needs_attention: 999` (a hack). This is a missing feature that will cause workarounds in project specs.

### Fix

Document merge semantics explicitly in the schema and in `lib-agency.sh`'s docstring:

- Arrays: wholesale replace (no append). If you override `phases`, you replace the entire list.
- Nested objects: recursive key-merge. `null` values are ignored (not treated as delete).
- Deletion: add a sentinel: if a gate's value is `{disabled: true}`, `_evaluate_spec_gates` skips it. Or add a top-level `gates_disabled: [name1, name2]` list in the project override.

Enforce this in the schema and test the edge cases in the test suite (Task 1.2 in the plan's testing strategy section).

---

## Finding 6: MEDIUM — Bash Variable Cache Has No Invalidation Trigger Except Explicit Call

**Severity:** Staleness / incorrect spec application mid-session

### The problem

The plan specifies: "First call to `agency_load_spec` parses YAML→JSON and stores in `_AGENCY_SPEC_JSON`. Subsequent calls use cached JSON. `agency_invalidate_cache` forces reload."

The cache lives in a bash variable. In a normal Claude Code session, the session is a single process and the cache is valid for its lifetime. The staleness risk arises in two scenarios:

**Scenario A: `/sprint` edits the project spec during planning.** The sprint workflow generates a project `agency-spec.yaml` as a planning artifact (this is an implied use case: the spec is what gets authored during `design` stage). If `agency_load_spec` is called early (e.g., during `brainstorm` to determine gate mode), the cache is populated with the pre-authoring spec. When the spec is written during `design`, the cache is stale. `enforce_gate` will evaluate gates based on the old spec for the rest of the session.

**Scenario B: Interflux or another companion modifies the project spec.** A flux-drive review agent might update the project override spec as part of its output. Same staleness applies.

The plan lists `agency_invalidate_cache` as a function. It does not specify when the sprint lifecycle calls it. If `sprint_set_artifact` writes a spec file, should it also invalidate the spec cache? The plan does not say.

This is not a race condition — it is a deterministic staleness bug. The fix is straightforward but requires explicit wiring.

### Fix

1. Hook `agency_invalidate_cache` into `sprint_set_artifact` when the artifact path matches `*agency-spec.yaml`.
2. Add a file-modification-time check to `agency_load_spec`: if `_AGENCY_SPEC_MTIME` is set and the file's mtime differs, invalidate and reload. `stat -c %Y` is available on Linux.
3. Document which sprint lifecycle events should trigger invalidation.

---

## Finding 7: MEDIUM — `sprint_stage_tokens_spent` Is Referenced But Not Defined

**Severity:** Runtime error / undefined function

### The problem

The plan's `sprint_stage_budget_remaining` calls `sprint_stage_tokens_spent "$sprint_id" "$stage"`:

```bash
spent=$(sprint_stage_tokens_spent "$sprint_id" "$stage")
```

This function does not exist in the current `lib-sprint.sh`. The existing code tracks tokens via `sprint_record_phase_tokens` which writes per-phase token data to ic state under `"phase_tokens"` key. There is no existing wrapper that sums tokens for a macro-stage (which maps multiple phases to one stage).

A grepped search of the hooks directory finds no definition of `sprint_stage_tokens_spent`. The plan lists it as part of the `sprint_stage_budget_remaining` implementation but does not specify it as a function to implement. It is a phantom function reference — the same class of bug documented in the project's own MEMORY.md under "Phantom Wrapper Functions in lib-intercore.sh."

If this function is missing at runtime and bash `set -e` is active, the call will terminate the script. If bash is lenient, the function returns empty string, `(( allocated - "" ))` causes an arithmetic error, and `remaining` is set to 0 — meaning every stage reports zero budget remaining from the first call.

### Fix

Explicitly define `sprint_stage_tokens_spent` in the plan as a Task 3.2 sub-item:

```bash
sprint_stage_tokens_spent() {
    local sprint_id="$1" stage="$2"
    local run_id
    run_id=$(_sprint_resolve_run_id "$sprint_id") || { echo "0"; return 0; }
    local phase_tokens_json
    phase_tokens_json=$(intercore_state_get "phase_tokens" "$run_id" 2>/dev/null) || phase_tokens_json="{}"
    # Sum tokens for all phases that belong to this stage
    local total=0
    while read -r phase; do
        local phase_stage
        phase_stage=$(_phase_to_stage "$phase")
        if [[ "$phase_stage" == "$stage" ]]; then
            local phase_total
            phase_total=$(echo "$phase_tokens_json" | jq -r \
                --arg p "$phase" '(.[($p)].input_tokens // 0) + (.[($p)].output_tokens // 0)' 2>/dev/null) || phase_total=0
            total=$(( total + phase_total ))
        fi
    done <<< "$(echo "$phase_tokens_json" | jq -r 'keys[]' 2>/dev/null)"
    echo "$total"
}
```

Add this to the file summary and task list.

---

## Finding 8: LOW — `_phase_to_stage` Maps `brainstorm` and `research` to `discover`, but `research` Is Not in the Sprint Phase Chain

**Severity:** Silent no-op / incorrect stage mapping

### The problem

```bash
_phase_to_stage() {
    case "$1" in
        research|brainstorm) echo "discover" ;;
        ...
```

The sprint's canonical phase chain (set at `sprint_create`, line 131) is:

```
brainstorm, brainstorm-reviewed, strategized, planned, plan-reviewed, executing, shipping, reflect, done
```

`research` is not a phase in this chain. It appears in the `_phase_to_stage` mapping but will never be passed by any real sprint phase transition. This is harmless but signals the mapping was written with a different phase model in mind (perhaps an earlier iteration). When the spec is queried for gates during the `research` phase, the call will never happen from real sprints — but a test that passes `research` directly will exercise a code path that real runs never hit.

More practically: `plan-reviewed` is in the sprint chain but `_phase_to_stage` maps it to `design`, alongside `planned`, `strategized`, and `brainstorm-reviewed`. That mapping is correct. The false positive is `research`.

### Fix

Remove `research` from the `_phase_to_stage` case or leave it and add a comment: "research is not a current phase; retained for forward compatibility." The `*` wildcard already handles unknown phases with `echo "unknown"`, so this is not broken — just misleading.

---

## Summary Table

| # | Finding | Severity | Invariant Broken |
|---|---------|----------|-----------------|
| 1 | Spec gates short-circuit ic gate check — only one system runs, not both | Critical | Gate conjunction |
| 2 | Silent spec load failure can cause enforce_gate to skip all gate checks | Critical | Gate never silently no-ops |
| 3 | min_tokens floors can push sum of stage allocations above total budget | High | Budget totals |
| 4 | Gate command side effects can fire twice under concurrent sessions | High | Idempotency |
| 5 | Array/deletion merge semantics unspecified — surprising runtime behavior | Medium | Deterministic merge |
| 6 | Spec cache has no automatic invalidation when spec file changes mid-session | Medium | Cache consistency |
| 7 | sprint_stage_tokens_spent is referenced but not defined anywhere | Medium | No phantom wrappers |
| 8 | _phase_to_stage includes `research` which is not in the sprint phase chain | Low | Phase mapping accuracy |

---

## Recommended Pre-Implementation Changes to the Plan

1. **Rewrite the `enforce_gate` pseudocode** to make ic gate check a mandatory first step, not an alternative fallback. The spec gate path is additive.

2. **Define cache state machine** in lib-agency.sh: `_AGENCY_SPEC_LOADED` must be one of `""` (never loaded), `"ok"` (loaded successfully), `"failed"` (load attempted, failed), `"fallback"` (no spec file found). Queries must check for `"ok"` before trusting `_AGENCY_SPEC_JSON`.

3. **Add `sprint_stage_tokens_spent` to the file summary** as a required new function in Task 3.2.

4. **Add a constraint check at spec-load time**: validate that `sum(min_tokens)` does not exceed the minimum expected budget for the lowest complexity tier (50,000 tokens for complexity-1). Warn if violated.

5. **Specify deep-merge semantics explicitly** in Task 2.2: arrays replace, dicts merge, `null` is ignored, deletion requires `{disabled: true}` sentinel. Add these as test cases in the test strategy.

6. **Specify cache invalidation triggers** in Task 2.1: which sprint lifecycle events call `agency_invalidate_cache`. Recommend hooking `sprint_set_artifact` when the artifact path is `*agency-spec.yaml`.
