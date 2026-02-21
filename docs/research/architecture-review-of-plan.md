# Architecture Review: Plugin Synergy Interop Implementation Plan
**Plan file:** `docs/plans/2026-02-20-plugin-synergy-interop.md`
**Review date:** 2026-02-20
**Reviewer:** Flux-drive Architecture & Design Reviewer

---

## Executive Summary

The plan is coherent at the protocol level and its interband-as-coordination-layer choice is sound. Most tasks are well-scoped. However there are five structural issues that will be expensive to fix after implementation starts: a signal-schema mismatch between Task 2 and every consumer; a hidden mutation race in the interband.sh upgrade sequence; Task 6's batch shape creating unnecessary rollback granularity; an unresolvable dedup strategy in Task 9; and Task 10 introducing a direct inter-plugin call path that bypasses the interband contract. Task 7 is the only item where the "static vs generated" question is genuine but low-priority.

---

## 1. Boundaries and Coupling

### 1.1 interband.sh is a shared mutable file touched by four separate tasks — must-fix sequencing risk

Tasks 1, 2, and 10 each modify `infra/interband/lib/interband.sh` in separate commits across separate git repositories. The plan commits each interband change immediately after the plugin change that requires it (Tasks 1 and 2 each end with two commits, Task 10 adds a third interband commit). Because interband is its own git repo with its own version line, this means:

- Three separate commits land in `infra/interband` across the lifetime of the plan.
- Each task's implementer reads a stale version of interband.sh if Tasks 1 and 2 are done in different sessions without a pull.
- The case blocks in `interband_validate_payload()`, `interband_default_retention_secs()`, and `interband_default_max_files()` are modified three times at the same logical location in the file.

The plan does not specify that the interband repo must be pulled before starting each subsequent task that modifies it, nor does it prescribe a single consolidated interband commit. This is a merge-conflict waiting to happen, but the deeper issue is testability: the contract between publisher and consumer is split across three commits, making it impossible to verify the full schema in one test run.

**Minimum fix:** Consolidate all three interband.sh additions into a single Task 1 step. Register all three `namespace:channel` pairs (`intercheck:pressure`, `intercheck:checkpoint`, `interstat:budget`) and their retention/max-files defaults in one commit. Tasks 2 and 10 then only touch plugin files. This eliminates the interband coordination risk entirely.

### 1.2 Task 10 creates a direct inter-plugin call path — boundary violation

Task 10 adds interband signal emission inside the `orange` case of `context-monitor.sh`. The code checks `[[ -n "${_ic_interband_lib:-}" ]]` — this variable is set only if the Task 1 interband sourcing block already ran in the same process. That sourcing block lives in the interband write path added by Task 1, meaning Task 10 implicitly depends on Task 1's code to have already executed in the same bash process.

More seriously, Task 10 also emits `intercheck:checkpoint_needed` and includes this message in the hook output:

```
Consider running /intermem:synthesize to preserve learnings.
```

This is a direct plugin-to-plugin coupling by name: intercheck's hook output now contains a command string specific to intermem's public interface. If intermem renames its skill, intercheck breaks silently (the message becomes stale but the code never fails). The interband protocol was designed explicitly to avoid this — publishers write signals, consumers act on them. The correct pattern is for intermem to consume `intercheck:checkpoint_needed` on session-start or via its own hook, not for intercheck to hardcode intermem's skill name in its output.

**Minimum fix:** Remove the hardcoded `/intermem:synthesize` string from the intercheck output message. Replace it with a generic message such as "Consider synthesizing session memory before continuing." The checkpoint signal over interband is already sufficient for any consumer to act.

### 1.3 Task 8 replaces interflux session-start contents entirely — regression risk

The plan says "Replace the contents of `plugins/interflux/hooks/session-start.sh`". The current file contains two substantive lines: `source "$HOOK_DIR/interbase-stub.sh"` and `ib_session_status`. The plan's replacement preserves both lines and adds budget-reading logic, which is correct. However "replace the contents" as an instruction to an implementer is dangerous — it will cause the existing interbase adoption to appear absent in a code review, making it harder to verify the Task 4/8 dependency.

**Minimum fix:** Rephrase Task 8 Step 1 as "Append the following block after line 9" rather than "Replace the contents." Diff-based verification becomes trivial.

---

## 2. Signal Schema Analysis

### 2.1 Task 2 channel name vs. type name diverges from Task 1 — not a bug, but creates confusion

In Task 2, `interband_validate_payload()` registers the type as `interstat:budget_alert`, but the retention and max-files cases use `interstat:budget`. The path generation calls `interband_path "interstat" "budget" "$session_id"`, producing `~/.interband/interstat/budget/<session_id>.json`. Task 3 (interline) and Task 8 (interflux) both read from this path — consistent.

The interband library correctly uses `namespace:channel` as the key for retention/max-files and `namespace:type` as the key for payload validation. These are different concepts and the code handles them correctly. However the channel (`budget`) and type (`budget_alert`) diverge in name, while Task 1 keeps them parallel (`pressure` channel, `context_pressure` type, consistent with the interphase pattern `bead` channel, `bead_phase` type).

**Recommendation:** Rename the Task 2 channel to `budget_alert` for stylistic consistency with Task 1, or document the channel-vs-type naming convention in the interband AGENTS.md. Without documentation, the next developer adding a signal will make an arbitrary choice and the inconsistency compounds.

### 2.2 Task 2: budget_alert emission fires on every hook call above 50% — unbounded writes

The emission logic in Task 2 has no threshold-crossing gate:

```bash
if [[ "$_is_pct_int" -ge 50 ]]; then
    # emit unconditionally
fi
```

The comment says "Only emit at threshold crossings: 50%, 80%, 95%" but the code does not implement threshold crossings. It emits on every PostToolUse:Task call once percentage exceeds 50. Since each agent dispatch triggers the hook, a session that has consumed 60% of its budget will emit a new interband file on every single Task tool call for the rest of the session.

The atomic-write design means each write is individually safe, but the write frequency is unnecessary: the signal changes slowly (percentage changes by single digits per dispatch) but the file is overwritten on every dispatch above the threshold.

**Minimum fix:** Track last-emitted percentage bucket in a session-scoped file (e.g., `/tmp/interstat-budget-last-${session_id}`) and only write when the integer bucket (50, 80, 95) changes. This implements the stated intent and reduces writes by an order of magnitude.

### 2.3 Task 1 pressure level thresholds duplicate context-monitor.sh logic

The threshold computation in Task 1's interband write block recomputes `_ic_pressure_level` from `$PRESSURE` and `$EST_TOKENS` using the same awk/integer comparisons as lines 67-73 of the existing `context-monitor.sh`. The existing file already computes `LEVEL` (green/yellow/orange/red) at line 67, but the interband write is inserted before the `case "$LEVEL"` block — before `$LEVEL` is available — requiring the duplication.

This creates a divergence risk: if the thresholds are ever adjusted, there are two places to update. The existing file has the authoritative thresholds; the interband block has a copy.

**Minimum fix:** Restructure so `$LEVEL` is computed before `_ic_write_state`, then use `$LEVEL` directly in the interband write block. Alternatively, move the interband write inside the existing `case "$LEVEL"` block, where the level is already known. Either approach eliminates the threshold duplication.

---

## 3. Task 6: Batch Shape

### 3.1 Four-plugin batch is too coarse — wrong rollback granularity

Task 6 batches intermem, intertest, internext, and tool-time into one task with a shared for-loop commit. The plan's own `integration.json` contents confirm these four plugins have different companions, different standalone features, and different nudge logic. The rationale for batching appears to be "the steps are identical," but identical steps with different payloads are exactly what per-task commits are for.

The concrete failure mode: if the for-loop commit step fails for one plugin (e.g., intertest already has a session-start.sh), the loop continues silently (the `|| echo "$p: FAIL"` only echoes, does not abort). An implementer following this plan may produce a partial commit covering only 2 of 4 plugins, making task state ambiguous.

The plan also says "Check if each plugin already has a `hooks/hooks.json`. If so, merge the SessionStart entry." This conditional logic buried in a bulk step is the most likely source of execution errors: the implementer must make per-plugin decisions mid-loop.

The architectural risk is not coupling between the four plugins — they remain independent. The risk is that a single task unit with four distinct failure modes makes rollback impossible at per-plugin granularity, and makes progress-tracking via beads or IC runs inaccurate.

**Minimum fix:** Split Task 6 into four tasks (6a–6d). Each is: copy stub, create integration.json, create session-start.sh, check and create/merge hooks.json, commit. Four small tasks with clear per-plugin scope.

**Note:** `intermem` does not have a standard plugin structure at `/root/projects/Interverse/plugins/intermem/` — only docs, brainstorms, and a `.venv` directory are present. Task 6 must verify intermem plugin structure before attempting SDK adoption. This is the highest-risk of the four plugins in this batch.

---

## 4. Task 7: companion-graph.json Static vs. Generated

### 4.1 Static graph is appropriate now, but needs a consistency gate

The plan creates `companion-graph.json` as a hand-authored static file. The concern is whether it stays synchronized with the `integration.json` files added by Tasks 4–6. A generated approach would ensure consistency but requires a build step.

Static is correct for the current state: 12 edges covering a small, known graph that changes infrequently. The real risk is silent divergence: the plan's validation script (Step 2) only checks that plugin names exist as directories — it does not cross-validate edges against `integration.json` companions declarations.

**Minimum fix:** Extend the Step 2 validation script to read each plugin's `integration.json` and assert that every declared companion relationship appears in `companion-graph.json`. This is a trivial addition to the existing python3 validation block. Without it, the graph will begin diverging within the first post-plan plugin addition.

On the static vs. generated question: keep it static until the graph exceeds ~30 edges or a CI gate requires it. The current state does not justify the tooling investment.

---

## 5. Task 9: Verdict-to-Bead Deduplication

### 5.1 String-match dedup is not robust — produces both false positives and false negatives

The dedup check in `verdict_auto_create_beads()`:

```bash
existing=$(bd list --json --quiet 2>/dev/null | jq -r ".[].title" 2>/dev/null | grep -Fc "${summary:0:30}" || echo "0")
[[ "$existing" -eq 0 ]] || continue
```

**False positives (suppression):** A verdict summary starting with "No issues found in authentication" will match any existing bead whose title contains the same 30-character prefix — including unrelated beads from different reviews. The first 30 characters of natural-language summaries are rarely unique identifiers. Common review phrasing ("Missing validation on", "Performance issue in") will suppress legitimate new beads.

**False negatives (duplicates):** Two verdict summaries for the same underlying finding phrased differently (e.g., "Missing input validation on user endpoint" vs. "User endpoint lacks input validation") produce zero match and both become beads. Since `verdict_auto_create_beads` iterates all verdict files on every call and verdict files are only cleaned at sprint start, repeated calls create duplicate beads for the same verdict.

The deeper problem is that summary text is not a stable identifier. Verdict files have no stable ID field; their stable identity is the agent name (the filename without `.json`).

**Minimum fix:** Use the agent name as the dedup key. Maintain a session-scoped map file (e.g., `/tmp/intersynth-bead-map-${CLAUDE_SESSION_ID}.json`) keyed on agent name, recording which bead ID was created for each verdict. Before creating a bead, check this map. After creating, record the new ID. This is session-accurate, O(1) per check, and requires no `bd list` call. At sprint start the map is implicitly reset because `CLAUDE_SESSION_ID` changes.

If cross-session dedup is needed (to prevent re-creating a bead already in the backlog from a previous session), record the agent-name-to-bead-id mapping in a persistent file and check `bd show <id>` to verify the bead still exists before skipping creation.

---

## 6. Pattern Consistency and YAGNI

### 6.1 SessionStart hooks for plugins with no active integrated features — premature

Tasks 4, 5, and 6 add SessionStart hooks that call `ib_session_status` and optionally `ib_nudge_companion`. For plugins like intertest, internext, and tool-time, the hook has no functional effect beyond emitting ecosystem status to stderr. The `integration.json` files for these three plugins list `integrated_features` that do not exist in this plan — they are aspirational.

This adds four new hooks firing on every SessionStart across the ecosystem (each sources interbase-stub.sh, does `command -v` checks, runs `ib_session_status`, optionally runs `ib_nudge_companion` with its glob + file reads) for features that have not been built.

Tasks 4 (interline) and 5 (intersynth) justify SessionStart hooks: interline's layers actively read interband signals from Tasks 1–2; intersynth's Task 9 bridges verdicts to beads. Those two plugins have concrete integrated features shipping in this same plan.

**Recommendation:** For intertest, internext, and tool-time in Task 6: create `integration.json` files only (documentation artifacts). Do not create session-start.sh or hooks.json. Add those hooks when a concrete integrated feature exists in the same plan that uses them.

### 6.2 interbase nudge plugin name is not validated against companion-graph.json

The interbase stub's `ib_nudge_companion()` checks whether the companion is installed via `compgen -G "${HOME}/.claude/plugins/cache/*/${name}/*"`. This is correct. However the companion names passed in session-start hooks are bare plugin names (`"intercheck"`, `"interflux"`, `"interwatch"`) that must match the installed plugin directory name. If any of these plugins are installed under a different directory name (e.g., via a path alias), the nudge fires incorrectly. This is a pre-existing interbase behavior, not introduced by this plan, but the plan amplifies it by adding six new nudge registrations across four tasks.

This is low-priority given the nudge is session-capped and dismissible.

### 6.3 Task 10 intermem-dir check is unreliable

The rate-limit gate in Task 10 checks `[[ -d "$(pwd)/.intermem" ]]`. The current working directory of `context-monitor.sh` is not guaranteed to be the project root across all invocations — it depends on how Claude Code sets CWD for PostToolUse hooks. If CWD is the session working directory rather than the project root, the `.intermem` check will always be false, and the interband checkpoint signal will never emit.

**Minimum fix:** Remove the `.intermem` directory existence check. The checkpoint signal should fire based on pressure threshold alone. Consumers (intermem) decide whether to act based on their own state — this is the correct interband pattern.

---

## 7. Dependency Ordering

The plan's task sequence is correct for the critical path:

```
Task 1 (intercheck publishes) → Task 3 (interline consumes intercheck)
Task 2 (interstat publishes) → Task 3 (interline consumes interstat)
Task 2 (interstat publishes) → Task 8 (interflux consumes interstat)
Task 1/2 (interband.sh updated) → Task 10 (intercheck:checkpoint_needed)
Task 5 (intersynth adopts interbase) → Task 9 (verdict-to-bead bridge)
```

One implicit dependency the plan does not state: Task 4 (interline interbase adoption) creates `hooks/hooks.json`. If interline gains any non-SessionStart hook between plan authoring and Task 4 execution, the plan's create-from-scratch instruction would overwrite it. The plan should include an explicit "check if hooks/hooks.json exists" guard, as Task 5 correctly does but Task 4 does not.

---

## Summary Table

### Must-Fix Before Implementation Starts

| ID | Task | Issue |
|----|------|-------|
| M1 | 1, 2, 10 | Three separate interband.sh commits across sessions create merge-conflict risk and split testability. Consolidate all interband.sh additions into Task 1. |
| M2 | 9 | String-match dedup produces false positives (suppresses valid beads) and false negatives (creates duplicates). Replace with agent-name-keyed session map. |
| M3 | 10 | Hardcoded `/intermem:synthesize` in intercheck output breaks the interband publisher/consumer boundary. Remove it. |
| M4 | 2 | Budget alert emits on every call above threshold, not at crossing points. Add a last-emitted-bucket gate. |

### Fix Before Completion (Not Blocking to Start)

| ID | Task | Issue |
|----|------|-------|
| C1 | 6 | Four-plugin batch should be four separate tasks. Verify intermem plugin structure first. |
| C2 | 1 | Pressure threshold duplication in context-monitor.sh — use existing `$LEVEL` variable. |
| C3 | 7 | Extend validation script to cross-check edges against integration.json companions. |
| C4 | 6 | intertest, internext, tool-time: create integration.json only, no session-start hooks yet. |
| C5 | 8 | Change "Replace contents" to "Append block after line 9." |

### Low-Priority Cleanup

| ID | Task | Issue |
|----|------|-------|
| L1 | 1, 2 | Document channel vs. type naming convention in interband AGENTS.md. |
| L2 | 4 | Add "check if hooks.json exists" guard matching Task 5's guard. |
| L3 | 10 | Remove unreliable `$(pwd)/.intermem` existence check. |
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-20-dual-mode-plugin-architecture.md`
**Prior art consulted:**
- `docs/research/review-revised-dual-mode-architecture.md` (second-round architecture review of the brainstorm)
- `infra/interband/lib/interband.sh` (reference pattern)
- `plugins/interflux/.claude-plugin/plugin.json` (target plugin)
- `scripts/interbump.sh` (publish pipeline)
- `docs/guides/interband-sideband-protocol.md`

---

## Summary Verdict

The plan is architecturally sound at the macro level. The centralized-copy + stub-fallback pattern is a direct and correct extension of the existing interband pattern already working in this codebase. The five focus areas all have legitimate findings. Three of the eleven tasks contain structural problems significant enough to fix before implementation begins. The remaining issues are hardening gaps that can be addressed during or after implementation.

---

## 1. Centralized-Copy + Stub-Fallback Pattern: Is It Sound?

**Verdict: Sound with one critical guard-placement bug that must be fixed.**

The pattern itself is the right architecture for this problem. The existing `infra/interband/lib/interband.sh` proves the model works in production: load-once guard at line 9-10, centralized source, downstream consumers source a stub that tries the live path first. interbase follows this pattern faithfully.

**The specific bug in the stub template (Task 2).**

The stub as written in Task 2, Step 1 sets `_INTERBASE_LOADED=1` only in the fallback (inline stubs) path:

```bash
if [[ -f "$_interbase_live" ]]; then
    _INTERBASE_SOURCE="live"
    source "$_interbase_live"
    return 0               # <-- _INTERBASE_LOADED never set here
fi

_INTERBASE_LOADED=1        # Only reached in fallback path
ib_has_ic() { ... }
```

If the live copy is sourced successfully, `_INTERBASE_LOADED` is unset. A second plugin that sources the same stub will pass the guard check (`[[ -n "${_INTERBASE_LOADED:-}" ]]` is empty, so it does not short-circuit), attempt the live source again, and re-execute the top-level code of interbase.sh. This is benign only if interbase.sh itself sets the guard, which the plan does specify (Task 1, Step 2, line 46: `_INTERBASE_LOADED=1`), but the stub's correctness should not depend on the live file's internal convention.

The interband pattern at `infra/interband/lib/interband.sh` lines 9-10 sets `_INTERBAND_LOADED=1` unconditionally at the top before any code runs. The stub template must do the same:

```bash
[[ -n "${_INTERBASE_LOADED:-}" ]] && return 0
_INTERBASE_LOADED=1   # Set unconditionally before source attempt

_interbase_live="${INTERMOD_LIB:-${HOME}/.intermod/interbase/interbase.sh}"
if [[ -f "$_interbase_live" ]]; then
    _INTERBASE_SOURCE="live"
    source "$_interbase_live"
    return 0
fi

_INTERBASE_SOURCE="stub"
ib_has_ic() { ... }
```

This fix also resolves the INTERMOD_LIB dev-override edge case (Task 5, Step 5 relies on the override working correctly in isolation).

**The `ib_in_ecosystem()` function in the live copy.**

The plan defines `ib_in_ecosystem()` as:

```bash
ib_in_ecosystem()  { [[ -n "${_INTERBASE_LOADED:-}" ]] && [[ "${_INTERBASE_SOURCE:-}" == "live" ]]; }
```

After the guard fix above, `_INTERBASE_LOADED` will always be set. The distinguishing signal is `_INTERBASE_SOURCE`. This function is then correct. However, it is worth noting that `ib_in_ecosystem()` is not called anywhere in the plan — no integration feature gates on it. This is not a defect (the PRD lists it as a guard to provide), but it should not be counted as a tested path unless Task 5 adds a test case for it.

**Coupling risk assessment.** The stub-fallback pattern introduces a runtime coupling between plugins through the shared `_INTERBASE_LOADED` global in the bash environment. This is acceptable — it is the same mechanism interband uses and the ecosystem already accepts this tradeoff. The risk is bounded: the global is a flag, not state, and any plugin that sources the stub first will claim the load. Because all plugins ship the same stub template, function signatures are identical regardless of which plugin sources first.

---

## 2. Nudge Protocol Placement: SDK vs Separate Module

**Verdict: Placement is correct. Scope is proportionate. One behavior concern.**

The PRD correctly locates nudge logic in the centralized copy only, not in stubs. The revised architecture review (second round) explicitly validates this placement. The reasoning is sound: nudge logic requires durable state management and session-scoped budgeting — functionality that does not belong in a per-plugin stub and should not be duplicated across 20+ plugins.

The nudge protocol is not a separate module concern. It has no interface other than `ib_nudge_companion()`. It reads and writes files in `~/.config/interverse/`, which is a sensible location. It is small enough (roughly 60 lines in the plan) to stay in interbase.sh without turning it into a god module.

**One behavioral concern: `ib_session_status()` emits at call-site, nudge reads companion list at runtime.**

The plan's `ib_session_status()` (Task 1, Step 2) says it will count "recommended companions not installed (requires integration.json reading — deferred)". The deferred comment is the right call. But it should be made explicit in the code as a comment, not just in the plan, so the deferred scope does not silently accrete into the implementation.

**The nudge fires when `ib_nudge_companion` is called explicitly by a plugin**, not automatically at session start. This is the correct architecture (it is what the PRD F3 specifies: "triggers on first successful operation completion per session, not session-start"). The plan's Task 8 hook fires `ib_session_status` at session start, which is read-only. The nudge is invoked by feature code later. This separation is correct.

**The session_id tie.** The nudge session file is keyed to `CLAUDE_SESSION_ID`. The plan does not define where or when `CLAUDE_SESSION_ID` is set. If it is not set (a standalone user running outside Claude Code), the session file becomes `nudge-session-unknown.json`. All nudges from all standalone invocations accumulate against the same session, eventually hitting the budget of 2 and going silent permanently for that key. This is a minor but real edge case: the budget counter should reset when `CLAUDE_SESSION_ID` is absent (treat each script invocation as its own session, or disable nudging when no session ID is present). The current test in Task 3 sets `CLAUDE_SESSION_ID="test-session-$$"`, which will pass but will not catch this scenario.

---

## 3. integration.json Schema: Surface Area

**Verdict: Schema surface area is appropriate. Two field-level issues need resolution.**

The schema as specified in Task 2, Step 2:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [],
  "integrated_features": [],
  "companions": {
    "recommended": [],
    "optional": []
  }
}
```

This is clean. The previous architecture review's recommendation to rename `interbase_version` to `interbase_min_version` has been incorporated. `ecosystem_only` boolean is present, which was the schema's most important missing field. The schema cleanly separates Interverse-owned metadata from the Claude Code platform schema in `plugin.json`.

**Issue 1: `integrated_features` type mismatch between template and interflux instance.**

The template defines `integrated_features` as an empty array `[]`. The interflux instance (Task 7) populates it as an array of objects:

```json
{ "feature": "Phase tracking on review completion", "requires": "interphase" }
```

The template does not show this structure. When interbump copies the template for new plugins, contributors may populate `integrated_features` as a flat string array rather than an object array. Neither the install script nor any validation step in the plan enforces the object structure. The template should show the object structure with a commented example, or the install.sh should include a schema validation step. The Task 7 validation step does not check `integrated_features` object shape — it only checks count.

**Issue 2: `standalone_features` as free-form prose strings is correct for now, but should be noted.**

The field is display-only documentation. The plan uses it only for marketplace display and human reference. This is the right constraint. No code in the plan reads these strings to make decisions. This distinction should be documented in the AGENTS.md (Task 6) to prevent future accretion of feature-flagging logic on top of prose strings.

**No issues with `companions` structure.** The `recommended` vs `optional` split is the right granularity. The values are plugin names (strings), which is machine-actionable. The interflux instance correctly separates `interwatch` and `intersynth` (recommended) from `interphase` and `interstat` (optional).

---

## 4. install.sh → ~/.intermod/ Deployment Model

**Verdict: Appropriate for current scope. One operational gap in the interbump integration.**

The `~/.intermod/interbase/` target directory is correct. It follows the namespace pattern established by `~/.interband/` and isolates the SDK from unrelated home directory clutter. The `VERSION` file (single-line, read with `cat`) is simpler and more portable than any alternative.

**The install.sh itself is clean.** `set -euo pipefail`, `chmod 644`, explicit VERSION write. The test steps in Task 4 (stat permissions, cat VERSION) are adequate verification.

**Gap: interbump integration is structurally problematic (Task 10).**

The plan adds `install_interbase()` to `scripts/interbump.sh` and calls it at the end of the main execution flow. This creates a cross-module side effect in a publish-pipeline script. The existing `interbump.sh` is run from each plugin's root directory (`PLUGIN_ROOT` is resolved via `git rev-parse --show-toplevel`). The proposed addition adds this logic:

```bash
interbase_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/sdk/interbase"
```

This relative path navigation from `scripts/` to `sdk/interbase/` assumes interbump.sh is always invoked from the Interverse monorepo context. However, `interbump.sh` is currently invoked from plugin directories via each plugin's `scripts/bump-version.sh` thin wrapper. The resolution `$(dirname "${BASH_SOURCE[0]}")/../sdk/interbase` from a plugin's working directory will resolve to `plugins/interflux/../../sdk/interbase` if the plugin's bump-version.sh calls interbump.sh directly — which is the actual invocation pattern.

More precisely: `${BASH_SOURCE[0]}` inside a sourced function refers to the file where the function is defined, not the caller. Since interbump.sh is a standalone script (not sourced), `BASH_SOURCE[0]` will be the path to interbump.sh itself (e.g., `/root/projects/Interverse/scripts/interbump.sh`). The path `$(dirname "${BASH_SOURCE[0]}")/..` becomes `/root/projects/Interverse/scripts/..` which resolves to `/root/projects/Interverse`. The final `sdk/interbase` path resolves correctly.

However, the conditional `if [[ -f "$interbase_dir/install.sh" ]]; then` means that if this function runs from a plugin that has its own `.git` but is not under the Interverse monorepo (a plugin checked out standalone), it will silently skip the install with no indication. This is acceptable fail-open behavior, but it should be explicitly documented in the function comment.

**A deeper concern: should interbump install interbase at all?**

interbump is a publish pipeline — it bumps versions and pushes to the marketplace. Installing infrastructure to the developer's machine is a different concern. The side effect is appropriate for ensuring the developer's machine stays current, but it should be an opt-in behavior or run as a separate step rather than being embedded in the publish pipeline. The existing `post-bump.sh` hook mechanism (`POST_BUMP` in interbump.sh lines 110-118) is the right place for plugin-specific post-bump work. Installing interbase is a monorepo-level concern, not a plugin concern. Consider calling it from a monorepo-level `Makefile` or `scripts/install-infra.sh` instead, and removing it from interbump.

---

## 5. Task Ordering and Dependency Correctness

**Verdict: Ordering is mostly correct. Two dependency issues and one missing prerequisite.**

### Correct dependencies

- Tasks 1 (interbase.sh) and 2 (stub + schema templates) are independent and can proceed in parallel, but serializing them is fine.
- Task 3 (nudge protocol) correctly depends on Task 1 (core guards must exist before nudge is added).
- Task 4 (install.sh) correctly follows Task 1.
- Task 5 (unit tests) correctly follows Tasks 1, 2, 3 (tests cover all three).
- Task 6 (AGENTS.md) correctly follows everything.
- Task 7 (interflux integration.json) correctly follows Task 2 (template defines the schema).
- Task 8 (interflux hooks) correctly depends on Tasks 1-3 (the stub sourced in hooks must exist).
- Task 9 (test and validate) correctly follows Tasks 7 and 8.
- Task 10 (interbump update) is correctly positioned last in the infra track.
- Task 11 (docs update) correctly follows all implementation.

### Dependency issue 1: Task 3 test references `ib_in_ecosystem` as `_INTERBASE_SOURCE=="live"`, but this requires the guard fix.

The nudge test (Task 3, Step 1) sets up `CLAUDE_SESSION_ID` and sources interbase.sh directly (not via the stub). The test environment has no `~/.intermod/` because `export HOME="$TEST_HOME"`. This means the nudge fires from the direct source path, not the live path. The `ib_in_ecosystem()` check inside nudge (if nudge uses it) will return false because `_INTERBASE_SOURCE` is not set to "live" when sourced directly. The nudge test does not test the full path. This is acceptable for unit testing but should be noted in the test description.

### Dependency issue 2: Task 8 step 5 destructively modifies the developer's `~/.intermod/`.

Task 8, Step 5 runs:

```bash
mv ~/.intermod ~/.intermod.bak 2>/dev/null || true
bash plugins/interflux/hooks/session-start.sh 2>&1
mv ~/.intermod.bak ~/.intermod 2>/dev/null || true
```

This is a destructive mutation of the live `~/.intermod/` directory with no atomicity guarantee. If the test step fails mid-execution, `~/.intermod.bak` may be left in place and `~/.intermod/` absent, breaking the live ecosystem. The safe alternative is to use `INTERMOD_LIB=/dev/null` or `INTERMOD_LIB=/nonexistent/path` to simulate absence without touching the real directory:

```bash
INTERMOD_LIB=/dev/null bash plugins/interflux/hooks/session-start.sh 2>&1
```

This is already the documented dev-testing override mechanism (`INTERMOD_LIB` env var overrides the path). The plan should use it rather than renaming the live directory.

### Missing prerequisite: Task 8 assumes interflux has no existing hooks.

The plan creates `plugins/interflux/hooks/hooks.json` and `plugins/interflux/hooks/session-start.sh` as new files. The current interflux structure shows no `hooks/` directory (confirmed: Glob found no files under `plugins/interflux/hooks/`). This is fine. However, the plan does not check whether any existing interflux hook scripts contain inline guards that need to be replaced with `ib_*` calls (PRD F4: "Existing inline guards in interflux hooks replaced with `ib_*` calls"). The interflux CLAUDE.md states "Phase tracking is the caller's responsibility — interflux commands do not source lib-gates.sh," which suggests no existing guards exist. But the plan should include an explicit verification step rather than assuming.

### Task ordering gap: Task 9 Step 4 references "existing interflux tests."

The plan says "if tests exist, run them." The interflux test suite exists at `plugins/interflux/tests/test-budget.sh` (confirmed by Glob). This test should be listed explicitly in Task 9 rather than guarded with a conditional. The plan currently treats it as optional discovery rather than a required regression gate.

---

## 6. Additional Structural Findings

### `ib_session_status()` output goes to stderr, but the plan's session-start hook calls it unconditionally.

Task 8, Step 2 creates `session-start.sh` that calls `ib_session_status` for all users — both stub and live mode. In stub mode, `ib_session_status` is a no-op (returns 0, no output). In live mode it emits `[interverse] beads=... | ic=...` to stderr. This is the correct design per the PRD.

However, the hook is a SessionStart hook that runs on every session. A user who installs interflux but does not have the ecosystem will see nothing (correct). A user who has the ecosystem will see the status line on every session start. The plan should verify this is the intended user experience — the prior architecture review (Q5) flagged that the status line should be limited to what interbase.sh can determine from its own guards, not per-plugin mode display. The plan complies with this constraint (the status shows beads and ic state, not "interflux=standalone vs integrated"). This is acceptable.

### The `_ib_nudge_is_dismissed()` function uses `jq` without a guard.

The nudge protocol implementation (Task 3, Step 3) uses `jq` in `_ib_nudge_is_dismissed()` and `_ib_nudge_record()`. Each function has a `command -v jq &>/dev/null || return 1` guard. However, if jq is absent, `_ib_nudge_is_dismissed()` returns 1 (not dismissed), and nudge fires. On every call. Because the dismissal check fails open as "not dismissed," the nudge will repeatedly fire regardless of prior state when jq is missing.

The safer behavior when jq is absent is to return 0 from `_ib_nudge_is_dismissed()` (treat as dismissed — silently skip all nudging) rather than returning 1 (not dismissed — always fire). This matches the fail-open safety contract stated in the interbase.sh header: "Fail-open: all functions return safe defaults if dependencies missing."

### The `ib_has_companion()` implementation is fragile.

```bash
ib_has_companion() {
    local name="${1:-}"
    [[ -n "$name" ]] || return 1
    compgen -G "${HOME}/.claude/plugins/cache/*/${name}/*" &>/dev/null
}
```

This checks the Claude Code plugin cache directory structure, which is an internal implementation detail of Claude Code's plugin system. The path `~/.claude/plugins/cache/*/pluginname/` is correct for the current marketplace layout (confirmed in interverse troubleshooting docs: `CACHE_DIR="$HOME/.claude/plugins/cache/interagency-marketplace/$PLUGIN_NAME"`). However, the glob here uses `*/pluginname/*` (two wildcards — one for marketplace, one for version), while the actual structure is `marketplace-name/plugin-name/version/`. The extra wildcard level for version means the glob matches correctly only when a version directory exists inside the plugin name directory. This is the expected installed state. The risk is that a partially installed plugin (plugin name dir exists, no version dir) returns false (not installed), which is the correct behavior. No change needed, but this should be documented in AGENTS.md.

---

## 7. Scope Assessment

The plan's 11 tasks map cleanly to the 4 PRD features (F1 → Tasks 1, 4, 5; F2 → Task 2; F3 → Task 3; F4 → Tasks 7, 8, 9, 11; cross-cutting → Tasks 6, 10). No task touches components outside the stated goal. No task creates abstractions without an immediate consumer (interbase.sh is immediately consumed by interflux in Task 8). The interbump integration in Task 10 is the only questionable addition — it extends the publish pipeline with infrastructure-install side effects that belong in a separate script. That is the one scope concern.

The nudge protocol is proportionate: 60 lines of shell with clear state boundaries (`~/.config/interverse/`) and a defined budget. It does not require a separate module.

---

## Must-Fix Before Implementation

**M1 — Guard placement bug in stub template (Task 2).**

Set `_INTERBASE_LOADED=1` before the live source attempt, not only in the fallback path. Without this, two plugins in the same session will each re-source the live copy.

```bash
[[ -n "${_INTERBASE_LOADED:-}" ]] && return 0
_INTERBASE_LOADED=1   # Must be unconditional

_interbase_live="${INTERMOD_LIB:-${HOME}/.intermod/interbase/interbase.sh}"
if [[ -f "$_interbase_live" ]]; then
    _INTERBASE_SOURCE="live"
    source "$_interbase_live"
    return 0
fi
_INTERBASE_SOURCE="stub"
# ... fallback stubs ...
```

**M2 — Replace destructive mv test with INTERMOD_LIB override (Task 8, Step 5).**

Replace the `mv ~/.intermod ~/.intermod.bak` pattern with:

```bash
INTERMOD_LIB=/nonexistent bash plugins/interflux/hooks/session-start.sh 2>&1
```

The existing `INTERMOD_LIB` override mechanism exists precisely for this use case.

**M3 — Fix `_ib_nudge_is_dismissed` jq-absent behavior (Task 3).**

Change the fallback when jq is absent from `return 1` (not dismissed, nudge fires) to `return 0` (treated as dismissed, nudge silent). Add a symmetric guard to `_ib_nudge_session_count` to return a large number (e.g., 99) when jq is absent, ensuring the budget check also blocks nudging without jq.

---

## Should-Fix (Quality Improvements)

**S1 — Make Task 9 Step 4 explicit.**

Replace "ls tests/ 2>/dev/null && echo 'Run existing tests' || echo 'No existing test suite'" with the explicit test invocation `bash /root/projects/Interverse/plugins/interflux/tests/test-budget.sh`. The test exists and should be a required regression gate.

**S2 — Add `CLAUDE_SESSION_ID` absence handling to nudge (Task 3).**

When `CLAUDE_SESSION_ID` is empty, either disable nudging (safest) or use `$$` as a per-invocation session key rather than `unknown` (which accumulates across all standalone invocations).

**S3 — Move interbase install out of interbump (Task 10).**

Call `bash sdk/interbase/install.sh` from a dedicated `scripts/install-infra.sh` or a `Makefile` target. Remove the `install_interbase()` function from interbump.sh. The publish pipeline should publish plugins, not mutate the developer's home directory.

**S4 — Add `integrated_features` object shape to the template.**

The template in Task 2, Step 2 shows `integrated_features: []`. Add a commented example object inside the array showing the `{feature, requires}` shape, or use a `$schema` reference comment, so contributors know the required structure.

**S5 — Task 8 should include an explicit check for inline guards to replace.**

Add a step: "Grep interflux hooks for existing `command -v ic`, `command -v bd`, or `ib_has_ic` patterns before adding stub sourcing, to identify any guards that need to be replaced." (Current structure shows no existing hooks, so this is likely a no-op, but the plan should verify rather than assume.)

---

## Nice-to-Have

**N1 — Document `ib_has_companion()` cache path assumption in AGENTS.md.**

Note the specific path pattern `~/.claude/plugins/cache/marketplace/plugin-name/version/` and the Claude Code internal convention dependency.

**N2 — Add `ib_in_ecosystem()` to the guard unit tests (Task 5).**

Currently the test covers `ib_in_sprint`, `ib_phase_set`, `ib_emit_event`, and `ib_session_status`. `ib_in_ecosystem()` is not covered despite being a documented guard function.

**N3 — Note `standalone_features` as display-only in AGENTS.md (Task 6).**

Prevents future feature-flag logic from being accidentally built on free-form prose strings.

---

## Conclusion

The plan is implementable as written after the three must-fix corrections. The centralized-copy + stub-fallback pattern is architecturally justified and has a working precedent in infra/interband. The integration.json schema is appropriately scoped. The nudge protocol belongs in interbase.sh. The install.sh → ~/.intermod/ deployment model is sound. Task ordering is correct with two execution-level fixes (guard placement, destructive mv). The one structural recommendation worth taking seriously before implementation: remove the interbase install from interbump and put it in a dedicated infrastructure script.
