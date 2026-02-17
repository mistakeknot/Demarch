# Flux-drive Correctness Review: Clavain Token-Efficiency Plan

**Reviewer:** fd-correctness (Julik)
**Date:** 2026-02-16
**Plan:** `docs/plans/2026-02-16-clavain-token-efficiency.md`
**Bead:** iv-1zh2

---

### Findings Index

1. **[CRITICAL] F1: JSON truncation mid-escape sequence** — session-start additionalContext assembly
2. **[HIGH] F2: verdict_parse_all file existence check race** — lib-verdict.sh
3. **[MEDIUM] F3: complexity-based phase skipping not implemented** — F5 describes non-existent function
4. **[MEDIUM] F4: checkpoint lock timeout silently fails** — checkpoint_write gives up without error
5. **[LOW] F5: verdict JSON parsing has no schema validation** — malformed agent output could break sprint
6. **[INFORMATIONAL] F6: existing sprint_advance stale-phase guard is correct** — user's F3 concern is already addressed

---

**VERDICT:** NEEDS_ATTENTION — Two high-severity data corruption risks (F1, F2), two medium-severity silent failure modes (F3, F4), one robustness gap (F5). All have narrow, testable fixes.

---

## F1: JSON Truncation Mid-Escape Sequence [CRITICAL]

**File:** `hub/clavain/hooks/session-start.sh:269`

### Problem

The SessionStart hook assembles `additionalContext` from multiple bash variables containing JSON-escaped text with `\\n` literal sequences (not real newlines). The final JSON is:

```bash
"additionalContext": "You have Clavain.\n\n**Below is...**\n\n${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}${handoff_context}${inflight_context}"
```

Each variable is separately escaped via `escape_for_json()`. The result is concatenated **then Claude Code truncates the full JSON blob** if it exceeds the session-start context budget.

### Interleaving Failure

1. `using_clavain_escaped` ends with `"...workflows.\\nFor more: /clavain:reference"`
2. Companion context starts with `"\\n\\nActive companion alerts:..."`
3. **Concatenation produces:** `...workflows.\\nFor more: /clavain:reference\\n\\nActive companion alerts:...`
4. **Claude Code truncates** at byte 32000 (hypothetical), landing between `\\` and `n` of the second `\\n`.
5. **Result:** `...workflows.\\nFor more: /clavain:reference\\` → incomplete escape sequence
6. **JSON parser sees:** trailing backslash before closing quote → **syntax error**
7. **Consequence:** SessionStart hook output rejected, additionalContext dropped entirely, or worse—Claude Code enters degraded mode with no Clavain awareness.

### Why It's Hard to Spot

- Truncation is non-deterministic (depends on upstream context size, which changes with `using-clavain` edits, companion discovery results, handoff length).
- The break only happens when total length crosses a threshold AND lands mid-escape.
- Error manifests as "hook ignored" with no clear diagnostic (JSON parse errors from hooks are logged but not surfaced to user).

### Fix

**Option A (robust):** Truncate **before** final concatenation, at a token-safe boundary (end of a complete variable).

```bash
# After assembling all parts, measure total length and drop lowest-priority sections first
_full_context="${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}${handoff_context}${inflight_context}"
_length=${#_full_context}
_max_length=30000  # Conservative: Claude Code's real limit is higher but varies

if [[ $_length -gt $_max_length ]]; then
    # Priority: using-clavain > companion_context > sprint_context > discovery > handoff > inflight
    # Drop inflight first, then handoff, etc., until under budget
    [[ $_length -gt $_max_length ]] && inflight_context="" && _full_context="${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}${handoff_context}"
    _length=${#_full_context}
    [[ $_length -gt $_max_length ]] && handoff_context="" && _full_context="${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}"
    # ... continue for each section in priority order
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "You have Clavain.\n\n**Below is...**\n\n${_full_context}"
  }
}
EOF
```

**Option B (simpler, less safe):** Cap each variable individually before concatenation (loses granularity but prevents mid-escape truncation).

```bash
using_clavain_escaped="${using_clavain_escaped:0:10000}"
companion_context="${companion_context:0:2000}"
# etc.
```

**Recommendation:** Option A. The priority-based shedding ensures critical content (using-clavain, companion alerts) always loads, while low-value content (inflight agent warnings from previous sessions) drops first.

---

## F2: verdict_parse_all File Existence Check Race [HIGH]

**File:** `hub/clavain/hooks/lib-verdict.sh:63-74`

### Problem

```bash
verdict_parse_all() {
    [[ -d "$VERDICT_DIR" ]] || return 0
    local found=0
    for f in "$VERDICT_DIR"/*.json; do
        [[ -f "$f" ]] || continue  # ← Race: glob expands first, then we check -f
        found=1
        local agent
        agent="$(basename "$f" .json)"
        jq -r --arg a "$agent" '"\(.status)\t\($a)\t\(.summary)"' "$f" 2>/dev/null || true
    done
    [[ $found -eq 0 ]] && return 0
}
```

**Race interleaving:**

1. Glob expands: `for f in .clavain/verdicts/*.json` → list includes `fd-correctness.json`
2. **Concurrent session/cleanup:** `verdict_clean` runs, deletes all `*.json` files
3. Loop iteration: `[[ -f "$f" ]]` → false, so `continue` (correct—no jq call on missing file)
4. **BUT:** If no files remain, `found=0` stays 0, function returns 0 with empty output
5. **Caller (sprint command) interprets:** "No verdicts found" vs "verdicts existed but were cleaned mid-read"

**Is this a bug?** Depends on caller assumptions:

- If sprint expects "verdict count > 0" when it knows agents completed → **silent data loss**.
- If sprint treats "no verdicts" as "agents didn't write verdicts, retry" → **infinite loop**.

**Current code has partial guard:** `|| true` on the jq call prevents errexit if file disappears between `-f` check and jq read. But the **found flag logic is wrong**: if all files disappear mid-loop, the function returns 0 (success) with no indication that a race occurred.

### Fix

Add an existence check AFTER the loop to detect mid-read deletion:

```bash
verdict_parse_all() {
    [[ -d "$VERDICT_DIR" ]] || return 0
    local found=0
    local json_files=("$VERDICT_DIR"/*.json)

    # Check if glob matched anything (bash sets first element to literal string if no match)
    [[ -f "${json_files[0]}" ]] || return 0

    for f in "${json_files[@]}"; do
        [[ -f "$f" ]] || continue
        found=1
        local agent
        agent="$(basename "$f" .json)"
        jq -r --arg a "$agent" '"\(.status)\t\($a)\t\(.summary)"' "$f" 2>/dev/null || true
    done

    # Sanity check: if we had files at glob time but found=0, warn
    if [[ $found -eq 0 && -f "${json_files[0]}" ]]; then
        echo "WARNING: verdict files existed but disappeared during read (race)" >&2
    fi
    return 0
}
```

**Better fix (atomic snapshot):** Copy JSON files to a temp dir under lock, then parse the snapshot:

```bash
verdict_parse_all() {
    [[ -d "$VERDICT_DIR" ]] || return 0
    local snapshot="/tmp/verdict-snapshot-$$"
    mkdir -p "$snapshot"
    trap "rm -rf '$snapshot'" EXIT

    # Atomic copy (quick, no lock needed—verdict files are write-once after agent completes)
    cp "$VERDICT_DIR"/*.json "$snapshot/" 2>/dev/null || return 0

    for f in "$snapshot"/*.json; do
        [[ -f "$f" ]] || continue
        local agent
        agent="$(basename "$f" .json)"
        jq -r --arg a "$agent" '"\(.status)\t\($a)\t\(.summary)"' "$f" 2>/dev/null || true
    done
}
```

**Recommendation:** Snapshot approach. Parsing 10 verdict files takes <5ms; the copy overhead is negligible, and it eliminates the race entirely.

---

## F3: Complexity-Based Phase Skipping Not Implemented [MEDIUM]

**Plan section:** F5 (Task 5.2)

### Problem

The plan says:

> Add to sprint skill:
> ```
> Score-based routing:
> - 1-2: Skip to Step 3 (write-plan), skip flux-drive review, use Sonnet-only agents
> - 3: Standard workflow, all steps
> - 4-5: Full workflow with Opus orchestration
> ```

But there's **no function** `sprint_should_skip(phase)` or `sprint_next_required_phase(complexity, current_phase)` in the existing codebase (confirmed by grep). The plan references these in the user's F3/F4 concerns, but they don't exist yet.

### Correctness Issue

The **plan describes behavior** (skip brainstorm for simple tasks) but **doesn't specify the mechanism**. Two plausible implementations:

**Option 1:** Modify `_sprint_transition_table` to return different next-phases based on `sprint_classify_complexity` result.

**Option 2:** Add a `sprint_next_required_phase(sprint_id, current_phase)` wrapper that:
1. Calls `_sprint_transition_table(current_phase)` to get the default next phase
2. Calls `sprint_classify_complexity` to get the score
3. If score ≤ 2 and `next_phase` is in the skip-list (`["brainstorm-reviewed", "strategy"]`), walks the transition table forward until hitting a non-skipped phase

**User's F3 concern is valid IF Option 2 is chosen:**

> If complexity changes between calls, the same current_phase could produce different next_phases. Is this a TOCTOU issue?

**Answer:** Yes, if complexity is re-computed on every call. **Fix:** Cache complexity in bead state at sprint creation (`bd set-state $sprint_id complexity=$score`), read it from there (not re-compute) during phase transitions.

**Existing safeguard (from F6 concern):** Line 517 in `sprint_advance` already checks for stale-phase race:

```bash
actual_phase=$(bd state "$sprint_id" phase 2>/dev/null) || actual_phase=""
if [[ -n "$actual_phase" && "$actual_phase" != "$current_phase" ]]; then
    echo "stale_phase|$current_phase|Phase already advanced to $actual_phase"
    return 1
fi
```

This prevents the TOCTOU issue **if complexity is stable**. But if complexity changes mid-sprint (user runs `bd set-state $sprint_id complexity=5` after the sprint started with complexity=2), the skip logic could cause a backward jump (e.g., skip strategy → land at write-plan, but then on next advance, complexity=5 → require strategy → **can't go backward**).

### Fix

1. **Cache complexity at sprint creation** (in `sprint_create` or `sprint classify` command):
   ```bash
   score=$(sprint_classify_complexity "$sprint_id" "$description")
   bd set-state "$sprint_id" "complexity=$score"
   ```

2. **Read cached complexity** (never re-compute during transitions):
   ```bash
   sprint_next_required_phase() {
       local sprint_id="$1"
       local current_phase="$2"
       local complexity
       complexity=$(bd state "$sprint_id" complexity 2>/dev/null) || complexity="3"

       # Walk transition table, skipping phases based on complexity
       local next="$current_phase"
       local seen=()
       while true; do
           next=$(_sprint_transition_table "$next")
           [[ -z "$next" || "$next" == "$current_phase" ]] && return 1  # No valid next phase

           # Detect infinite loop (shouldn't happen with a valid transition table, but...)
           for phase in "${seen[@]}"; do
               [[ "$phase" == "$next" ]] && return 1
           done
           seen+=("$next")

           # Check if this phase should be skipped
           if _should_skip_phase "$next" "$complexity"; then
               continue  # Keep walking
           else
               echo "$next"
               return 0
           fi
       done
   }

   _should_skip_phase() {
       local phase="$1"
       local complexity="$2"
       case "$complexity" in
           1|2)
               [[ "$phase" =~ ^(brainstorm-reviewed|strategy)$ ]] && return 0
               ;;
       esac
       return 1
   }
   ```

3. **Loop bound:** The `seen` array prevents infinite loops, but add a hard cap:
   ```bash
   [[ ${#seen[@]} -gt 20 ]] && return 1  # Max 20 phases (transition table has ~9)
   ```

---

## F4: Checkpoint Lock Timeout Silently Fails [MEDIUM]

**File:** `hub/clavain/hooks/lib-sprint.sh:716`

### Problem

```bash
checkpoint_write() {
    # ...
    while ! mkdir "$lock_dir" 2>/dev/null; do
        retries=$((retries + 1))
        [[ $retries -gt 10 ]] && return 0  # ← Fail-safe: give up after 1s
        sleep 0.1
    done
    # ...
}
```

**If the lock is held for >1 second** (e.g., another session is doing a slow jq operation, or the lock dir is orphaned by a killed process), `checkpoint_write` **returns 0 (success) without writing anything**.

**Caller impact:**

```bash
checkpoint_write "$CLAVAIN_BEAD_ID" "executing" "step-4" "/tmp/plan.md"
# Caller assumes checkpoint was written, proceeds to next step
```

If checkpoint write fails silently, then `--resume` will skip to the wrong step (last successfully written checkpoint, not the actual current step).

**Interleaving failure:**

1. Session A: acquires lock, starts writing checkpoint for step-3
2. Session A: jq process hangs (disk I/O stall, swap thrash, etc.)
3. Session B (same sprint): tries to write checkpoint for step-4
4. Session B: lock held by A, retries 10 times (1 second), gives up
5. Session B: **returns 0, no error logged**
6. Session B: continues to step-5
7. User runs `--resume` later: checkpoint says "step-3" (from A), but B already completed step-4 and step-5
8. **Resume logic re-runs step-4**, potentially causing duplicate work or broken state

### Fix

**Option 1:** Return failure (non-zero exit code) so caller can detect and retry:

```bash
[[ $retries -gt 10 ]] && {
    echo "ERROR: checkpoint lock timeout for $CHECKPOINT_FILE" >&2
    return 1
}
```

But this breaks `set -euo pipefail` contexts unless caller uses `|| true`.

**Option 2:** Force-break stale locks (same pattern as `sprint_advance` line 488):

```bash
[[ $retries -gt 10 ]] && {
    # Force-break stale lock (>5s old)
    local lock_mtime
    lock_mtime=$(stat -c %Y "$lock_dir" 2>/dev/null) || {
        rmdir "$lock_dir" 2>/dev/null || true
        mkdir "$lock_dir" 2>/dev/null || return 1
        break
    }
    local now
    now=$(date +%s)
    if [[ $((now - lock_mtime)) -gt 5 ]]; then
        rmdir "$lock_dir" 2>/dev/null || rm -rf "$lock_dir" 2>/dev/null || true
        mkdir "$lock_dir" 2>/dev/null || return 1
        break
    fi
    echo "ERROR: checkpoint lock held by active process, cannot write" >&2
    return 1
}
```

**Recommendation:** Option 2 (force-break stale locks). It's already the pattern used in `sprint_advance`, so consistency is good. Add logging so the failure is visible:

```bash
echo "WARNING: checkpoint lock timeout, breaking stale lock (age: ${age}s)" >&2
```

---

## F5: Verdict JSON Schema Validation Missing [LOW]

**File:** `hub/clavain/hooks/lib-verdict.sh:58` (verdict_read) and `:71` (verdict_parse_all)

### Problem

If an agent writes malformed JSON to `.clavain/verdicts/fd-correctness.json`, the `jq` calls fail silently (due to `|| true`), and the verdict is **skipped without warning**.

**Example malformed output:**

```json
{
  "type": "verdict",
  "status": "CLEAN",
  "model": "sonnet",
  "summary": "All good",
  "findings_count": "three"  ← should be integer, not string
}
```

`jq -r '"\(.status)\t\($a)\t\(.summary)"'` succeeds (jq coerces the string), but `verdict_count_by_status` might break if it tries arithmetic on `findings_count`.

**More severe case:**

```
{
  "type": "verdict",
  "status": "CLEAN"
  "summary": "Missing comma causes parse error
}
```

`jq` fails, `|| true` swallows the error, verdict is silently dropped.

### Fix

Add schema validation before parsing:

```bash
verdict_read() {
    local agent="${1:?agent name required}"
    local f="${VERDICT_DIR}/${agent}.json"
    [[ -f "$f" ]] || return 1

    # Validate schema (required fields + types)
    if ! jq -e '.type and .status and .model and .summary and (.findings_count | type == "number")' "$f" >/dev/null 2>&1; then
        echo "ERROR: Invalid verdict schema in $f" >&2
        return 1
    fi

    jq -r '"\(.status)\t\(.model)\t\(.summary)"' "$f" 2>/dev/null
}
```

Or add a `verdict_validate` helper:

```bash
verdict_validate() {
    local f="$1"
    jq -e '
        .type and (.type | test("^(verdict|implementation)$")) and
        .status and (.status | test("^(CLEAN|NEEDS_ATTENTION|BLOCKED|ERROR|COMPLETE|PARTIAL|FAILED)$")) and
        .model and
        .summary and
        (.findings_count | type == "number") and
        (.tokens_spent | type == "number")
    ' "$f" >/dev/null 2>&1
}
```

Call it from `verdict_parse_all`:

```bash
for f in "$VERDICT_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    verdict_validate "$f" || {
        echo "WARNING: Skipping invalid verdict file: $f" >&2
        continue
    }
    # ... rest of parsing
done
```

**Recommendation:** Add validation. Cost is ~1ms per file (jq schema check is fast), and it prevents silent data loss when agents write bad JSON.

---

## F6: Existing sprint_advance Stale-Phase Guard is Correct [INFORMATIONAL]

**User's F3 concern:**

> The stale-phase guard (line 516-521) checks `actual_phase != current_phase` — but if complexity changes between calls, the same current_phase could produce different next_phases. Is this a TOCTOU issue?

**Answer:** No, because the guard checks **phase drift**, not complexity drift. The TOCTOU issue only exists if:

1. Two sessions call `sprint_advance("iv-123", "brainstorm")` concurrently
2. Session A acquires lock, transitions to "brainstorm-reviewed"
3. Session B acquires lock (after A releases), reads `actual_phase = "brainstorm-reviewed"`
4. Session B's `current_phase = "brainstorm"` ≠ `actual_phase`, so it aborts with `stale_phase` error

This is **correct behavior**—it prevents re-running the same transition twice.

**Complexity-based skipping doesn't break this** as long as complexity is cached (see F3 fix). If complexity is read from bead state (not re-computed), then:

- Session A and B both see `complexity=2`
- Both compute `next_phase = sprint_next_required_phase("iv-123", "brainstorm")` → "write-plan" (skipping brainstorm-reviewed and strategy)
- First to acquire lock wins, second sees stale-phase and aborts

**Edge case:** What if session A sets `complexity=5` AFTER session B has already computed `next_phase` based on `complexity=2`?

1. Session B computes `next_phase = "write-plan"` (based on complexity=2)
2. Session A changes bead state: `bd set-state iv-123 complexity=5`
3. Session B acquires lock, sets `phase=write-plan`
4. Next call to `sprint_advance` reads `complexity=5`, computes `next_phase` from "write-plan"
5. **Transition table allows:** write-plan → executing (no skip), so no issue

**Only breaks if:** User changes complexity AND manually resets phase backward (`bd set-state phase=brainstorm`). Then the transition table might produce an invalid path. **Fix:** Don't allow manual phase changes (already documented in lib-sprint.sh:466—"ALL phase transitions MUST go through this function").

---

## Additional Findings (Not in User's List)

### A1: user's F2 concern about `_extract_verdict()` is obsolete

The concern mentions:

> _extract_verdict() uses `tail -7` to find the verdict header.

But `_extract_verdict` **doesn't exist** in the codebase. The new design (F3 in the plan) uses **structured JSON verdict files** written by `lib-verdict.sh`, not a text-parsing approach. So the tail-7 concern is moot.

### A2: user's F4 concern about `sprint_should_skip` return convention is obsolete

The concern mentions:

> sprint_should_skip() return convention: Returns 0 for "yes, skip" and 1 for "no, don't skip".

But `sprint_should_skip` **doesn't exist** (only `sprint_should_pause` exists, which returns 0 for "yes, pause"). If the plan adds `sprint_should_skip`, it should follow bash convention: **0 = success = should skip**, not the opposite. Callers would use:

```bash
if sprint_should_skip "$phase"; then
    # Skip this phase
fi
```

Not `if ! sprint_should_skip ...` (double-negative is confusing).

### A3: user's F1 concern about `skill_check_budget()` return codes

The concern mentions:

> skill_check_budget() return code: Returns max_severity (0, 1, or 2). But `set -euo pipefail` is active in lib.sh — returning 1 from a function call triggers errexit.

But `skill_check_budget` **doesn't exist** in the current codebase (confirmed by codex query). If this function is added later, callers need:

```bash
budget_status=0
skill_check_budget || budget_status=$?
case $budget_status in
    0) echo "OK" ;;
    1) echo "WARNING" ;;
    2) echo "EXCEEDED" ;;
esac
```

Or the function should return 0 always and output the severity to stdout:

```bash
severity=$(skill_check_budget)  # Always returns 0, outputs "ok" | "warn" | "exceeded"
```

---

## Minimal Corrective Changes

| # | Finding | Minimal Fix | Lines Changed |
|---|---------|-------------|---------------|
| F1 | JSON truncation | Add priority-based shedding loop in session-start.sh | +15 |
| F2 | verdict_parse_all race | Use snapshot dir | +5 (replace loop) |
| F3 | Phase skipping mechanism | Add sprint_next_required_phase + cache complexity in bead | +40 |
| F4 | Checkpoint lock timeout | Copy stale-lock-breaking pattern from sprint_advance | +12 |
| F5 | Verdict schema validation | Add verdict_validate + call from parse functions | +15 |

**Total:** ~87 lines of new/changed code, all in existing files (no new files needed beyond what the plan already specifies).

---

## Test Coverage Gaps

The plan says:

> Test Strategy: Manual sprint run after F4 to validate end-to-end verdict flow

**Missing tests:**

1. **F1:** SessionStart truncation under large context (>30KB additionalContext)
2. **F2:** Concurrent `verdict_parse_all` + `verdict_clean` (race condition)
3. **F3:** Complexity change mid-sprint (cache invalidation test)
4. **F4:** Checkpoint write under lock contention (stale lock breaking)
5. **F5:** Agent writes malformed verdict JSON (schema validation)

**Recommendation:** Add integration tests for F1-F5 before merging. F2 and F4 can use `bats` with background processes (`&`) to simulate concurrency.

---

## Recommended Implementation Order

1. **F5 (schema validation)** — Low risk, high value, unblocks F2/F4 testing
2. **F2 (verdict snapshot)** — Fixes high-severity race, simple change
3. **F4 (checkpoint lock)** — Copy existing pattern, low risk
4. **F3 (phase skipping)** — Most complex, depends on complexity caching design
5. **F1 (SessionStart truncation)** — Requires measuring real-world context sizes first

---

## Summary

**High-consequence issues:**

- **F1** can cause SessionStart hook failures that leave Clavain in degraded mode (no skill discovery, no companion awareness). Probabilistic but high-impact.
- **F2** can cause silent verdict data loss if cleanup runs concurrently with parsing. Rare but breaks sprint orchestration (agents ran, verdicts lost, sprint retries indefinitely).

**Medium-consequence issues:**

- **F3** phase skipping has no implementation yet—plan describes behavior without mechanism. Cache complexity at sprint creation to avoid TOCTOU.
- **F4** checkpoint lock timeout silently fails, causing resume to skip to wrong step. Breaks multi-session workflows.

**Low-consequence issues:**

- **F5** malformed verdict JSON is swallowed silently. Add schema validation (cheap, prevents debugging hell).

**User's original concerns (F3-F5) are mostly about non-existent functions** (`_extract_verdict`, `sprint_should_skip`, `skill_check_budget`, `sprint_next_required_phase`). The plan needs to **specify these functions explicitly** with signatures, return codes, and edge-case handling.

**Existing code is solid:** `sprint_advance` stale-phase guard is correct, `checkpoint_write` lock pattern is correct (just needs stale-lock-breaking), `verdict_write` is atomic (temp+mv).

**Key architectural decision needed:** How does complexity-based phase skipping work? Option 1 (modify transition table) or Option 2 (wrapper function)? Recommend Option 2 with cached complexity to avoid TOCTOU.
