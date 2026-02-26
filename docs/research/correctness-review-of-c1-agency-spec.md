# Correctness Review: C1 Agency Spec Implementation

**Reviewer:** Julik (Flux-drive Correctness Agent)
**Date:** 2026-02-22
**Files reviewed:**
- `/home/mk/projects/Demarch/os/clavain/hooks/lib-spec.sh`
- `/home/mk/projects/Demarch/os/clavain/hooks/lib-sprint.sh`
- `/home/mk/projects/Demarch/os/clavain/scripts/agency-spec-helper.py`

**Reference:** Plan `os/clavain/docs/plans/2026-02-22-c1-agency-specs.md`, default spec `os/clavain/config/agency-spec.yaml`

---

## Invariants Under Review

These must hold unconditionally across all code paths:

1. `_SPEC_JSON` is set before `_SPEC_LOADED="ok"` — never guard before data
2. `ic gate check` always runs first in `enforce_gate`; spec gates cannot bypass or replace it
3. `spec_available()` returns false (exit 1) for both "failed" and "fallback" states
4. Budget shares sum to 100 after normalization (no share is silently lost)
5. When min_tokens push uncapped sum above total budget, per-stage allocations scale down proportionally
6. All gate evaluators (all four types) fail-open on internal errors — return 0, never block
7. `_SPEC_LIB_SOURCED` double-source guard is separate from and does not interfere with `_SPEC_LOADED` cache state
8. `enforce_gate` returns 0 (pass) when `_sprint_resolve_run_id` fails (fail-open for missing sprint)

---

## Finding Summary

| ID | Severity | File | Title |
|----|----------|------|-------|
| C1 | HIGH | lib-sprint.sh | `enforce_gate` fails open when run_id is missing — gate check silently skipped |
| C2 | HIGH | agency-spec-helper.py | Budget normalization mutates stages in place — largest-stage adjustment can produce wrong sum |
| C3 | MEDIUM | lib-spec.sh | Staleness check only covers the base spec, not the override spec |
| C4 | MEDIUM | lib-sprint.sh | `command` gate uses `eval` on spec-controlled string — arbitrary shell injection |
| C5 | MEDIUM | lib-sprint.sh | `sprint_record_phase_tokens` reads `actual_tokens` from interstat but attributes it to the wrong scope |
| C6 | MEDIUM | lib-sprint.sh | `_sprint_sum_all_stage_allocations` calls `sprint_budget_total` which calls `sprint_read_state` — O(n) round-trips per call to `sprint_budget_stage` |
| C7 | LOW | lib-spec.sh | `spec_load` resets state after mtime staleness check but then re-enters the "already tried and failed" guard |
| C8 | LOW | lib-sprint.sh | `artifact_reviewed` gate counts all files in `.clavain/verdicts/` — not scoped to the artifact being reviewed |
| C9 | LOW | agency-spec-helper.py | `normalize_budget` warns on min_tokens sum > 50000 but the threshold is never justified or documented |
| C10 | LOW | lib-spec.sh | `spec_invalidate_cache` leaves `_SPEC_PATH` set — next `spec_load` could stat a stale path |

---

## Detailed Findings

### C1 (HIGH): `enforce_gate` fails open when no run is found

**File:** `os/clavain/hooks/lib-sprint.sh`, lines 761–798

**Code:**
```bash
enforce_gate() {
    ...
    local run_id
    run_id=$(_sprint_resolve_run_id "$bead_id") || return 0   # <-- return 0 = pass
    if ! intercore_gate_check "$run_id"; then
        return 1
    fi
    ...
}
```

**Invariant violated:** "ic gate check always runs first in enforce_gate."

**Failure narrative:**

When `_sprint_resolve_run_id` fails (bead has no `ic_run_id` in state, or beads is unavailable), the function returns 0 — a clean pass — before ever calling `intercore_gate_check`. The ic gate is silently skipped entirely.

This is architecturally wrong: a missing run ID means the kernel has no record of this sprint's state, which is a stronger reason to block than any gate configuration. The correct behavior is:
- If no run ID can be resolved, either block (return 1) or at minimum propagate the failure to the caller so it can decide.
- The current `|| return 0` pattern is appropriate for fail-open spec gates but is catastrophically wrong for the mandatory ic gate precondition.

**Concrete scenario:** A sprint bead is created but `bd set-state ic_run_id=...` fails (network blip to beads). `enforce_gate` is subsequently called. `_sprint_resolve_run_id` returns empty and the `||` short-circuits to `return 0`. All gates — including any gate that would catch a broken build — are silently bypassed.

**Minimal fix:**
```bash
run_id=$(_sprint_resolve_run_id "$bead_id") || {
    echo "enforce_gate: no run_id for $bead_id — treating as gate pass (no ic run)" >&2
    return 0  # or return 1 if you prefer strict mode
}
```

That change is fine as-is if the intent is truly fail-open for missing sprints. But the current code provides no warning whatsoever. At a minimum, the stderr line should be there so operators can see the gate was skipped and why.

If the intent is that `enforce_gate` must check ic gates when a run exists but silently pass when no run exists, the comment at the call site should say so explicitly, because the existing code looks like a bug.

---

### C2 (HIGH): Budget normalization mutates dict in place, largest-stage fixup can produce wrong result

**File:** `os/clavain/scripts/agency-spec-helper.py`, lines 37–43

**Code:**
```python
for stage in stages.values():
    budget = stage.get("budget", {})
    if "share" in budget:
        budget["share"] = round(budget["share"] * 100 / total_share)
# Fix rounding: adjust largest stage to make sum exactly 100
new_total = sum(s.get("budget", {}).get("share", 0) for s in stages.values())
if new_total != 100:
    largest = max(stages.values(), key=lambda s: s.get("budget", {}).get("share", 0))
    largest["budget"]["share"] += 100 - new_total
```

**Invariant at risk:** "Shares always sum to 100 after normalize."

**Issue 1 — Stages without a `budget` key are skipped in the loop but counted as 0 in `total_share`:**

`total_share` is computed as:
```python
total_share = sum(s.get("budget", {}).get("share", 0) for s in stages.values())
```

This sums only stages that have a share. If one stage has no budget block at all, its contribution to `total_share` is 0, and after normalization the sum of all normalized shares will be 100 — but that stage still contributes 0 to `new_total`. This is correct. However, if a stage has a `budget` dict but no `share` key, it is also skipped in the loop (the `if "share" in budget` guard), but that stage contributes 0 to both `total_share` and `new_total`. The largest-stage fixup then adjusts based on the largest post-normalization share, which may not be the intended recipient.

**Issue 2 — `round()` in Python uses banker's rounding (round half to even):**

Python's `round()` uses IEEE 754 "round half to even" semantics. For shares like `10 * 100 / 95 = 10.526...`, `round()` gives 11. For `20 * 100 / 95 = 21.05...`, round gives 21. This is deterministic but the rounding correction step (adding `100 - new_total` to the largest stage) can produce a final sum that is off by 1 if there are many stages with fractional remainders. The fix-up assumes the residual is at most a few points, which is true in practice but is not guaranteed by the algorithm.

**Issue 3 — Mutation of `stages` dict values without copying:**

`normalize_budget` mutates the `budget` dict of each stage in-place via `budget["share"] = ...`. Since `budget` is a reference to the stage's nested dict, this modifies `spec` directly. `deep_merge` already returns a new top-level dict, but nested dicts are shared references. If `normalize_budget` is ever called more than once on the same spec object, shares are re-scaled from already-scaled values, producing geometric compression. In `cmd_load`, `normalize_budget` is called once on the already-merged spec, so this is safe today. But it is a landmine for future callers.

**Concrete failure scenario for Issue 2:**

Suppose a project override changes reflect's share from 5 to 0 (removing it entirely), leaving four stages summing to 95. After normalization: 10*100/95=10.5→11, 25*100/95=26.3→26, 40*100/95=42.1→42, 20*100/95=21.05→21. Sum = 11+26+42+21 = 100. Fixup: new_total==100, no adjustment needed. This works.

Now suppose shares are 11, 26, 26, 22, 5 (summing to 90). Normalized: 12.2→12, 28.9→29, 28.9→29, 24.4→24, 5.6→6. Sum = 100. Fixup: new_total==100. Fine. Edge case: shares are 33, 33, 34 (three stages only). total_share=100, no normalization needed, loop doesn't trigger. This also passes. The algorithm appears safe for the concrete default spec (10+25+40+20+5=100, no normalization needed at all). The risk is triggered only on override-supplied specs with non-100 sums.

**Minimal fix for Issue 3:**
```python
import copy
spec = normalize_budget(copy.deepcopy(spec))
```
or make `normalize_budget` return a new dict with copied shares.

---

### C3 (MEDIUM): Staleness check tracks only the base spec path, not the override

**File:** `os/clavain/hooks/lib-spec.sh`, lines 44–53 and 104–106

**Code:**
```bash
if [[ "$_SPEC_LOADED" == "ok" && -n "$_SPEC_PATH" && -n "$_SPEC_MTIME" ]]; then
    current_mtime=$(stat -c %Y "$_SPEC_PATH" 2>/dev/null) || current_mtime=""
    if [[ "$current_mtime" == "$_SPEC_MTIME" ]]; then
        return 0  # Still fresh
    fi
    ...
fi
...
_SPEC_PATH="$spec_path"          # base spec path only
_SPEC_MTIME=$(stat -c %Y "$spec_path" 2>/dev/null)
```

**Problem:** When a project override (`${project_dir}/.clavain/agency-spec.yaml`) is present, only the base spec's mtime is tracked. Editing the override file will not invalidate the cache. The merged, loaded spec is stale until either `spec_invalidate_cache` is called explicitly or the base spec is touched.

**Failure narrative:** Developer adds a project override to tighten a gate (e.g., sets `gate_mode: enforce`). The base spec is unchanged. The hook fires. `spec_load` checks base spec mtime — unchanged — returns cached JSON that does not include the override. The gate runs in `shadow` mode from the stale cache. The change is silently ignored until the process restarts.

**Minimal fix:** Track both paths and both mtimes:
```bash
_SPEC_OVERRIDE_PATH=""
_SPEC_OVERRIDE_MTIME=""
```
And check override mtime in the staleness test. Alternatively, combine both mtimes into a single composite key (`"$base_mtime:$override_mtime"`).

---

### C4 (MEDIUM): `command` gate uses `eval` on spec-controlled string

**File:** `os/clavain/hooks/lib-sprint.sh`, lines 700–704

**Code:**
```bash
if [[ -n "$cmd" ]]; then
    local actual_exit
    eval "$cmd" >/dev/null 2>&1
    actual_exit=$?
    [[ $actual_exit -ne $expected_exit ]] && passed=false
fi
```

**Where `cmd` comes from:**
```bash
cmd=$(echo "$gate" | jq -r '.command // ""' 2>/dev/null) || cmd=""
```

The `command` field is a string from the merged spec (base + project override). The plan spec marks command gates as "must be idempotent and read-only" in comments, but there is no enforcement of that constraint at the evaluation layer.

**Risk:** Anyone who can write to `${project_dir}/.clavain/agency-spec.yaml` (or who can modify the default spec) can inject arbitrary shell commands that run during gate evaluation. In a CI/CD or multi-agent environment, this is a supply-chain risk. The commands execute as the agent's OS user.

The actual default spec has one command gate:
```yaml
tests_pass:
  type: command
  command: "bash -c 'cd \"${PROJECT_DIR:-.}\" && if [ -f Makefile ] && grep -q test Makefile; then make test; ...'"
```

This is not a simple read-only command — it runs `make test`, which can have arbitrary side effects.

**Minimal fix:** Use an allowlist or constrain command gates to a set of safe templates. At a minimum, add a warning when a command gate runs, so operators can see what executed and when.

**Near-term defensive measure:** Replace `eval "$cmd"` with `bash -c "$cmd"` — identical behavior but makes the subshell explicit. More importantly, document that command gates run with full agent privileges and that project-override gate commands are trusted by definition.

---

### C5 (MEDIUM): `sprint_record_phase_tokens` reads total session billing — not phase-scoped

**File:** `os/clavain/hooks/lib-sprint.sh`, lines 347–355

**Code:**
```bash
local db_path="${HOME}/.claude/interstat/metrics.db"
if [[ -f "$db_path" ]]; then
    actual_tokens=$(sqlite3 "$db_path" \
        "SELECT COALESCE(SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0)), 0)
         FROM agent_runs
         WHERE session_id='${CLAUDE_SESSION_ID:-none}'" 2>/dev/null) || actual_tokens=""
fi
```

**Problem:** This query returns the total token spend for the entire session, not for the current phase. When this function is called at the end of phase N, it returns cumulative spend from phase 1 through N — it is not scoped to "tokens spent during this phase only."

If a sprint runs multiple phases in a single session:
- End of brainstorm: actual_tokens = 30,000 (all session tokens so far)
- End of strategized: actual_tokens = 55,000 (cumulative)
- End of planned: actual_tokens = 90,000 (cumulative)

Each phase's token record gets the cumulative total, not the per-phase delta. The stored `phase_tokens` JSON becomes useless for per-phase accounting and double-counts every token for every phase after the first.

The fallback estimate path (`_sprint_phase_cost_estimate`) does not have this problem since it returns a static per-phase estimate. So the interstat path is actually worse than the fallback.

**Minimal fix:** Either:
1. Record a session-level baseline token count at the start of each phase and subtract it here to get the delta, or
2. Accept that interstat only provides session totals and abandon the interstat path in favor of always using estimates (simpler and more honest about what the data represents).

---

### C6 (MEDIUM): O(n^2) ic round-trips in `sprint_budget_stage`

**File:** `os/clavain/hooks/lib-sprint.sh`, lines 437–469

**Call chain:**

`sprint_budget_stage(sprint_id, stage)`
→ calls `sprint_budget_total(sprint_id)`
  → calls `sprint_read_state(sprint_id)` — 4+ ic/beads subprocess calls
→ calls `_sprint_sum_all_stage_allocations(sprint_id)`
  → calls `sprint_budget_total(sprint_id)` again (another full `sprint_read_state` invocation)
  → loops 5 stages × `spec_get_budget` (jq on cached JSON, fast)

So every call to `sprint_budget_stage` makes 2 full `sprint_read_state` round-trips. `sprint_read_state` itself calls:
- `_sprint_resolve_run_id` (bd state read)
- `intercore_run_status` (ic subprocess)
- `ic run artifact list` (ic subprocess)
- `ic run events` (ic subprocess)
- `intercore_run_agent_list` (ic subprocess)
- `ic run tokens` (ic subprocess)

That is approximately 6 subprocess calls per `sprint_read_state`, so `sprint_budget_stage` costs ~12 subprocess calls total. If a caller invokes `sprint_budget_stage` for each of 5 stages (e.g., to display a budget summary), the cost is ~60 subprocess calls.

**This is not a race condition** — it is a correctness risk because under load or slow ic responses, the two calls to `sprint_read_state` within a single `sprint_budget_stage` invocation can return different values (token budgets can be updated between calls), making the `uncapped_sum` check compare against a stale budget. Specifically: if the budget is increased between the first `sprint_budget_total` call and the `_sprint_sum_all_stage_allocations` call, the scaling formula will over-correct.

**Minimal fix:** Pass `total_budget` as a parameter to `_sprint_sum_all_stage_allocations` so it is computed only once per `sprint_budget_stage` call. The current code already has `total_budget` in scope inside `sprint_budget_stage` — just pass it down:
```bash
uncapped_sum=$(_sprint_sum_all_stage_allocations "$sprint_id" "$total_budget")
```

And in `_sprint_sum_all_stage_allocations`:
```bash
_sprint_sum_all_stage_allocations() {
    local sprint_id="$1"
    local total_budget="${2:-$(sprint_budget_total "$sprint_id")}"
    ...
}
```

---

### C7 (LOW): Cache reset during staleness check races with the "skip if already failed" guard

**File:** `os/clavain/hooks/lib-spec.sh`, lines 44–57

**Code:**
```bash
# Already loaded — check mtime for staleness
if [[ "$_SPEC_LOADED" == "ok" && ... ]]; then
    ...
    # Stale — force reload
    _SPEC_LOADED=""
    _SPEC_JSON=""
fi

# Skip if we already tried and failed (or fell back)
[[ "$_SPEC_LOADED" == "failed" || "$_SPEC_LOADED" == "fallback" ]] && return 0
```

**Problem:** The staleness branch resets `_SPEC_LOADED` to `""` and then falls through to the guard check. The guard skips on `failed` or `fallback` but not on `""`. So after a staleness reset, execution continues past the guard into the reload path. This is the correct behavior — a stale "ok" cache should trigger a fresh reload.

However, there is a subtle issue with the control flow: if `_SPEC_LOADED` was `"ok"` and the mtime check fails (e.g., `stat` errors on the path), `current_mtime` becomes empty, and `"" == "$_SPEC_MTIME"` is false only if `_SPEC_MTIME` is non-empty. If `_SPEC_MTIME` was also empty (stat failed at load time), then `"" == ""` is true and the cache is treated as fresh despite the file being unreadable. The mtime comparison is not guarded against both sides being empty.

**Failure scenario:** Spec file is deleted after being loaded. `stat -c %Y` returns empty. `_SPEC_MTIME` from original load was also empty (same stat failure on initial load). `"" == ""` is true. Cache is treated as fresh. `_SPEC_JSON` from the previous load is used indefinitely — the stale cache never expires.

**Minimal fix:**
```bash
current_mtime=$(stat -c %Y "$_SPEC_PATH" 2>/dev/null) || current_mtime=""
if [[ -n "$current_mtime" && -n "$_SPEC_MTIME" && "$current_mtime" == "$_SPEC_MTIME" ]]; then
    return 0  # Still fresh
fi
# If either mtime is empty, fall through to reload
_SPEC_LOADED=""
_SPEC_JSON=""
```

---

### C8 (LOW): `artifact_reviewed` gate counts all verdict files, not per-artifact

**File:** `os/clavain/hooks/lib-sprint.sh`, lines 687–691

**Code:**
```bash
local verdict_count=0
if [[ -d ".clavain/verdicts" ]]; then
    verdict_count=$(ls .clavain/verdicts/*.json 2>/dev/null | wc -l) || verdict_count=0
fi
[[ $verdict_count -lt $min_agents ]] && passed=false
```

The gate checks that `min_agents` verdicts exist in `.clavain/verdicts/` but does not filter by which artifact the verdicts are for. If a different artifact was reviewed in a previous stage, those verdict files inflate the count and the gate passes even though the specific artifact (e.g., `plan`) has zero reviews.

Additionally, `ls .clavain/verdicts/*.json` is run relative to the current working directory at invocation time, not relative to `PROJECT_DIR`. If the hook is invoked from a different working directory, this path is wrong.

**Minimal fix:** Verdicts should be named or tagged per-artifact so the gate can filter. As a practical interim fix, at minimum use an absolute path constructed from a known project root variable:
```bash
local verdicts_dir="${SPRINT_LIB_PROJECT_DIR:-.}/.clavain/verdicts"
```

---

### C9 (LOW): min_tokens warning threshold of 50000 is a magic number

**File:** `os/clavain/scripts/agency-spec-helper.py`, line 46

**Code:**
```python
if total_min > 50000:
    print(f"spec: min_tokens sum ({total_min}) exceeds 50000 floor ...", file=sys.stderr)
```

The default spec's min_tokens sum is 23000. The warning threshold of 50000 is more than double the default but less than the smallest meaningful sprint budget (50k tokens for complexity tier 1). A sprint with a 50k total budget and min_tokens summing to 23000 would allocate 46% of the budget to minimums alone — which is already arguably a warning condition.

This is not a bug, but the threshold is undocumented and not configurable. If someone sets a low complexity-1 sprint budget of 50000 and min_tokens stay at 23000, the threshold warning fires but the actual problem (nearly half the budget pre-committed to minimums) goes unreported in a meaningful way.

**Recommendation:** Either tie the threshold to the actual sprint budget (computed at runtime in shell, not Python), or change the warning to report the percentage of a hypothetical budget consumed by minimums.

---

### C10 (LOW): `spec_invalidate_cache` leaves `_SPEC_PATH` set

**File:** `os/clavain/hooks/lib-spec.sh`, lines 125–130

**Code:**
```bash
spec_invalidate_cache() {
    _SPEC_LOADED=""
    _SPEC_JSON=""
    _SPEC_MTIME=""
    _SPEC_PATH=""   # This is correct -- path IS cleared.
}
```

On re-reading: `_SPEC_PATH` is actually cleared in `spec_invalidate_cache`. This is correct behavior.

**However**, there is an edge case: the staleness check at the top of `spec_load` gates on `_SPEC_LOADED == "ok"`. After `spec_invalidate_cache`, `_SPEC_LOADED` is `""`, so the staleness block is skipped. The subsequent "skip if failed/fallback" guard also passes (state is `""`). Reload proceeds. This is the correct behavior.

**Revised status:** This finding is not a real bug. The cache invalidation is clean. Closing C10 as a false alarm from initial inspection. It is left here as documentation that the control flow was verified.

---

## Invariant Verification Results

| Invariant | Status | Notes |
|-----------|--------|-------|
| `_SPEC_JSON` set before `_SPEC_LOADED="ok"` | PASS | Lines 103→106. Data first, guard second. Clear. |
| `ic gate check` always runs first in `enforce_gate` | CONDITIONAL PASS | Runs first IF `_sprint_resolve_run_id` succeeds. If it fails, ic gate is silently skipped (C1). |
| `spec_available()` returns false for "failed" and "fallback" | PASS | `[[ "$_SPEC_LOADED" == "ok" ]]` — any other value returns 1. |
| Budget shares sum to 100 after normalize | CONDITIONAL PASS | Sum is correct for the default spec (shares already sum to 100). Rounding edge cases possible for override specs with unusual share distributions (C2). |
| Overallocation cap scales down correctly | CONDITIONAL PASS | Logic is correct when `total_budget` is read consistently. Double read of `sprint_read_state` can produce inconsistency (C6). |
| All gate evaluators fail-open on internal errors | PASS | Unknown gate types hit the `*` case with `continue`, not `any_failed=1`. jq errors in each case guard are caught with `|| continue` or `|| cmd=""` patterns. |
| `_SPEC_LIB_SOURCED` is separate from `_SPEC_LOADED` | PASS | Sourced once at library load; `_SPEC_LOADED` is separately initialized to `""`. They cannot interfere. |
| `enforce_gate` returns 0 when resolve fails | PASS (but undocumented) | Returns 0 via `|| return 0`. Behavior is correct for fail-open intent but produces no warning (C1). |

---

## Priority Ordering

1. **C1** — Silent ic gate bypass when sprint has no run ID. This can allow phase transitions through broken states. Highest consequence, trivial fix.

2. **C2** — Budget normalization mutation safety. The default spec is not affected today (shares sum exactly to 100), but project overrides can trigger rounding artifacts. Fix before C1 ships to users with custom specs.

3. **C5** — Phase token accounting captures cumulative session tokens instead of per-phase delta. This silently produces wrong data in `phase_tokens` state without errors. Downstream budget analysis will be wrong for multi-phase sessions.

4. **C4** — `eval` on spec-controlled command gate. Not exploitable from outside the repo today, but the pattern normalizes untrusted eval. Add the warning; the full fix can wait for C2 composer work.

5. **C3** — Override mtime not tracked. Low-frequency failure (only hurts when override is edited mid-session without restarting). Easy to fix.

6. **C6** — Double `sprint_read_state` invocation. Performance issue with a correctness edge case. Fix is trivial (pass total_budget as parameter).

7. **C7** — Empty mtime double-empty equality making stale cache appear fresh. Edge case (requires stat failure at both load and check time). Fix is one guard line.

8. **C8** — Verdict count not scoped to artifact. Functional gap that can cause false-pass on gate checks if any review verdicts exist from other stages.

---

## Unchanged Correct Behaviors (Confirmed)

These were verified as implemented correctly, consistent with the plan spec:

- Double-source guard (`_SPEC_LIB_SOURCED`) at top of `lib-spec.sh` prevents re-initialization of cache state variables on re-source.
- `spec_load` falls through to `"fallback"` cleanly when neither default nor override spec exists.
- Python helper exits non-zero and writes to stderr when YAML parse fails; `lib-spec.sh` catches the non-zero exit and sets `_SPEC_LOADED="failed"`.
- `jq empty` validation of the Python helper output catches cases where the helper writes a warning to stdout mixed with valid JSON.
- Gate mode `"off"` exits `enforce_gate` before any ic or spec gate runs.
- Shadow mode runs `_sprint_evaluate_spec_gates` with `|| true` suffix ensuring shadow always returns 0.
- Unknown gate types hit `continue` (not `any_failed=1`), preserving fail-open behavior.
- `spec_available` triggers `spec_load` first, so it is always current.
- `enforce_gate` correctly interprets `gate_mode="shadow"` to log-but-pass rather than block.

---

## Test Coverage Gaps

The testing strategy in the plan covers gate types, shadow mode, and cache state machine transitions. These cases are missing:

1. **No run ID path in `enforce_gate`**: Test that `enforce_gate` called with a bead that has no `ic_run_id` logs a warning to stderr and returns 0 (documenting the fail-open behavior explicitly).

2. **Override-only staleness**: Load spec with override. Modify override. Call `spec_load`. Verify cache is invalidated. Currently, this test would fail silently — the cache would not refresh.

3. **Phase token delta correctness**: Call `sprint_record_phase_tokens` twice in the same mock session with increasing cumulative tokens. Verify that phase 2's token count reflects only phase 2's spend, not total session spend.

4. **Command gate stdout/stderr suppression**: Verify that a command gate that produces stdout does not contaminate the function's return value.

5. **Budget consistency under concurrent `sprint_read_state` calls**: Not feasible to test in shell without mocking, but should be noted as a known risk for high-frequency budget queries.
