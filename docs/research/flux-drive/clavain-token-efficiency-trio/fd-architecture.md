# Architecture Review: Clavain Token Efficiency Implementation Plan

**Reviewer:** fd-architecture
**Date:** 2026-02-16
**Plan:** `docs/plans/2026-02-16-clavain-token-efficiency.md`
**PRD:** `docs/prds/2026-02-16-clavain-token-efficiency.md`

---

### Findings Index

**Critical (Must Fix):**
1. F1 adds no actual implementation — Task 1.1 verifies existing state, Tasks 1.2-1.3 duplicate F3 work
2. F3 verdict schema lacks version field and migration path for schema evolution
3. F4 has structural conflict — verdict consumption already implemented in sprint.md
4. F5 complexity classifier changes break existing working implementation without migration
5. Cross-feature coupling violation — F2/F3/F4 all modify session-start.sh additionalContext assembly

**High (Strong Recommendation):**
6. F2 companion discovery → env var migration loses discoverability value
7. F3 sidecar file naming convention (`.verdict` vs `.json`) inconsistent across plan
8. F4 verdict parsing duplicates lib-verdict.sh functions already in use
9. F5 inverted return convention (`sprint_should_skip` 0=skip vs `sprint_should_pause` 0=pause) introduces maintenance hazard
10. F6 checkpoint validation warns but doesn't block on SHA mismatch — unsafe for code-dependent steps

**Medium (Consider):**
11. F3 verdict schema overspecifies structure for 2-agent use case (review vs workflow agents need different fields)
12. F4 max_turns audit crosses feature boundary (applies to all Task dispatches, not just verdict-related)
13. F5 phase-skipping logic duplicates existing complexity-based routing in sprint.md
14. F6 checkpoint schema lacks agent turn counts and actual token measurements (uses estimates)

**Verdict:** **NEEDS_ATTENTION** — 5 critical boundary violations, 1 no-op feature, 2 redundant implementations. Plan is rescuable with surgical cuts but requires consolidation pass before implementation.

---

## Boundary & Coupling Analysis

### Critical Violation #1: F1 Is a No-Op Feature

**Location:** F1 (Agent Model Declarations + Output Contracts), Tasks 1.1-1.3

**Finding:** Task 1.1 verifies that all 4 agents already declare `model: sonnet` in frontmatter. Tasks 1.2-1.3 add Output Contract sections to agent .md files, which is identical to F3 Task 3.3 ("Update flux-drive agent prompts"). F1 does not implement model routing enforcement, does not modify dispatch logic, and does not add validation. It is pure documentation work already covered by F3.

**Evidence from plan:**
- Task 1.1: "All 4 agents already declare model. Task: verify each uses the right tier" — verification, not implementation
- Task 1.2: "Add Output Contract sections to all agents" — exact duplicate of F3 Task 3.3
- Task 1.3: "Already done in Task 3.1 — this task just links to it" — admits redundancy

**Root cause:** F1 merged two beads (iv-1zh2.2 model routing + iv-1zh2.6 contracts) "for implementation efficiency" but lost the actual model routing implementation somewhere in the merge. The PRD lists F1 as "model tier enforcement" but the plan only documents existing state.

**Architectural impact:** A 1-2 hour feature that changes 0 lines of code and adds no new behavior violates the "implementation footprint proportional to user footprint" principle. If model declarations are already complete and contracts are handled by F3, F1 should not exist as a separate feature.

**Recommendation:** Delete F1 entirely. Merge Task 1.2 (agent .md Output Contract sections) into F3 Task 3.3 as a single atomic change. If model tier enforcement is desired, create a separate task that modifies dispatch.sh to read `model:` frontmatter and pass it to `codex exec --model` or Claude Code Task tool invocation.

---

### Critical Violation #2: Session-Start Hook Coupling Across F2/F3/F4

**Location:** F2 Task 2.2, F4 (implicit), session-start.sh line 269

**Finding:** Three features modify `session-start.sh` additionalContext assembly but the plan treats them as independent:
- **F2 Task 2.2:** Removes companion discovery paragraphs from additionalContext, moves to `CLAVAIN_COMPANIONS` env var
- **F3:** Adds verdict schema and lib-verdict.sh — no explicit session-start.sh change documented, but verdict consumption requires runtime awareness
- **F4 Task 4.2:** Sprint command calls `verdict_parse_all` after quality-gates dispatch — depends on verdicts being initialized, which requires session-start or sprint-start hook

Current session-start.sh structure (from Grep output, line 269):
```bash
"additionalContext": "... ${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}${handoff_context}${inflight_context}"
```

**Coupling violation:** F2 removes `${companion_context}` but F4's verdict consumption may need to inject verdict-awareness context for sprint resume. The plan does not specify:
1. Whether `${sprint_resume_hint}` should mention available verdicts when resuming mid-sprint
2. Whether verdict directory initialization happens in session-start.sh or sprint-start
3. What happens if a user invokes flux-drive outside of sprint context (no verdict directory initialized)

**Recommendation:** Add explicit coordination task: "Session-start.sh integration checkpoint" after F2/F3/F4 complete. This task audits all additionalContext buckets, ensures verdict initialization is in the right hook, and validates that env var migration (F2) doesn't break verdict resume logic (F4). Estimate +1 hour.

---

### Critical Violation #3: F4 Verdict Consumption Already Implemented

**Location:** F4 Task 4.2, sprint.md

**Finding:** Codex query on `sprint.md` shows verdict consumption is already implemented:
- "It uses verdicts: after quality gates it calls `lib-verdict.sh` and reads/aggregates structured verdicts (`verdict_parse_all`, `verdict_count_by_status`)"
- "It also loads agent verdicts from `.clavain/verdicts/` when resuming"
- Lines referenced: 301-309, 142

**Plan's F4 Task 4.2 says:**
> "Update sprint command to use verdicts. After quality-gates dispatches review agents, instead of reading raw agent output: 1. Call verdict_parse_all to get the summary table..."

But the current implementation already does this. The plan is describing existing behavior as if it were new work.

**Root cause:** The plan was written against a stale snapshot of sprint.md or the features were implemented out of order and the plan wasn't updated.

**Recommendation:** Verify current sprint.md state. If verdict consumption is complete, delete F4 Task 4.2 entirely. Keep F4 Tasks 4.1 (lib-verdict.sh extension — but check if those functions exist) and 4.3 (max_turns audit). If verdict consumption is incomplete, rewrite Task 4.2 to describe the delta between current and desired state, not the full implementation from scratch.

---

### Critical Violation #4: F5 Changes Break Existing Implementation

**Location:** F5 Task 5.1, lib-sprint.sh `sprint_classify_complexity`, sprint.md Pre-Step

**Finding:** sprint.md already has complexity assessment and routing (Codex query result: "pre-step Complexity Assessment routes 1–2 → skip to plan, 3 → standard, 4–5 → full"). F5 Task 5.1 plans to "extend existing complexity classifier" but the changes are not extensions — they are breaking modifications:

**Plan proposes:**
- Change return value from string ("simple"/"medium"/"complex") to integer (1-5)
- Add file_count parameter (current implementation doesn't take parameters from Codex result)
- Add keyword detection for research/trivial (current implementation already has this per Codex: "trivial phrasing can force 1", "research-heavy text can force 5")

**Plan's Task 5.2 says:**
> "Before Step 1 (brainstorm), run complexity classifier. Add to sprint skill..."

But Codex query says complexity assessment already exists as a pre-step. The plan treats this as new work.

**Backward compatibility violation:** Changing return type from string to int breaks any existing caller that pattern-matches on "simple"/"medium"/"complex". The plan does not mention migration or deprecation path.

**Recommendation:** Split F5 into two tasks:
1. Audit current complexity implementation in sprint.md + lib-sprint.sh to document actual vs. planned behavior
2. If changes are needed, make them additive: add `sprint_classify_complexity_v2` that returns int, migrate sprint.md to new function, deprecate old function in a follow-up

Do not modify the existing function signature in place without verifying all callers.

---

### Critical Violation #5: F3 Verdict Schema Lacks Versioning

**Location:** F3 Task 3.1, agent-contracts.md schema definition

**Finding:** The verdict schema has 8 fixed fields but no `version` field. From lib-verdict.sh Codex summary, the current schema is a plain JSON object with keys: `type, status, model, tokens_spent, files_changed, findings_count, summary, detail_path, timestamp`.

**Plan adds** (Task 3.1): same fields, no version.

**Architectural risk:** Verdict files persist across sessions (F6 checkpoint resume loads them). If the schema evolves — e.g., adding `context_tokens` separate from `billing_tokens` (per the token accounting lesson in MEMORY.md) — there is no migration path. Old verdict files will fail to parse or produce incorrect results when read by new code.

**Evidence from MEMORY.md:**
> "Token Accounting (interstat): Billing tokens (input + output) ≠ effective context (input + cache_read + cache_creation). Difference can be 600x+ due to cache hits."

If F4 Task 4.4 ("Sprint summary with token tracking") later needs to distinguish billing vs. context tokens, the schema must change. Without a version field, detecting old-format verdicts is impossible.

**Recommendation:** Add `"version": 1` to the schema in F3 Task 3.1. Modify `verdict_write` to always set version. Modify `verdict_read` and `verdict_parse_all` to check version and either migrate or warn on version mismatch. This is a 15-minute addition that prevents multi-hour debugging when schema inevitably evolves.

---

## Pattern Analysis

### High-Impact Finding #6: F2 Companion Discovery Migration Loses Value

**Location:** F2 Task 2.2, session-start.sh companion_context

**Finding:** The plan moves companion discovery results from `additionalContext` injection to `CLAVAIN_COMPANIONS` env var. Rationale: "~500 tokens removed from additionalContext".

**Current behavior** (from session-start.sh Grep, line 53 comment):
> "Detect companion plugins — store as env var for on-demand access, inject only critical awareness context (interserve mode, active agents) into additionalContext."

This comment suggests companion_list is already stored as an env var and only critical awareness is injected. Let me verify what's actually in companion_context:

From Codex summary of session-start.sh:
> "Context buckets: companion_context, sprint_context, discovery_context, sprint_resume_hint, handoff_context, inflight_context — modularly assembled into one injected narrative block."

The plan does not show what text is in `${companion_context}`. If it's just "You have interflux, interphase, interlock installed" (3 names, ~10 tokens each = 30 tokens), the 500-token saving claim is suspect.

**Discoverability concern:** Companion plugins provide skills and agents that extend Clavain's routing table. If companion_context lists available skills (e.g., "interflux provides flux-drive skill and 7 fd-* agents"), removing this from session-start means the agent must explicitly check `CLAVAIN_COMPANIONS` env var and know what each companion provides. This shifts discovery burden from automatic (injected context) to manual (agent must query).

**Recommendation:** Before implementing F2 Task 2.2, measure actual token cost of current `${companion_context}`. If it's <100 tokens, the migration is not worth the discoverability regression. If it's truly 500 tokens, investigate why — are full skill descriptions being injected instead of just names?

Alternative: Keep companion names in additionalContext (10 tokens/plugin * 10 plugins = 100 tokens max), move only the detailed "what each companion provides" to on-demand lookup.

---

### High-Impact Finding #7: F3 Sidecar Naming Inconsistency

**Location:** F3 Task 3.1 schema, Task 3.2 lib-verdict.sh, plan text line 69

**Finding:** The plan uses two different file extensions for verdict sidecars:
- Plan line 69 (PRD F3): "write findings to `.clavain/verdicts/fd-<agent>.json`"
- Plan Task 3.1 example: `DETAIL_PATH: .clavain/verdicts/<agent-name>.md`
- lib-verdict.sh Codex summary: "persisted artifacts are `<agent>.json`"

**Inconsistency:** The verdict JSON sidecar is `.json`, but the DETAIL_PATH (full agent output) is `.md`. This is actually correct — two separate files. But the plan conflates them in the PRD quote above ("write findings to .json" when findings are in the .md, verdict metadata is in .json).

**Naming collision risk:** If an agent is named `fd-architecture`, the files are:
- `.clavain/verdicts/fd-architecture.json` (verdict metadata)
- `.clavain/verdicts/fd-architecture.md` (full findings detail)

This is fine but the plan should make the two-file pattern explicit. Currently Task 3.2 only mentions writing `.json`, not `.md`.

**Recommendation:** Add to F3 Task 3.2: "Verdict files are paired: `<agent>.json` (structured header) + `<agent>.md` (full detail). Both are written by agents, both are git-ignored, both are cleaned by `verdict_clean()`." Update lib-verdict.sh to include a `verdict_write_detail <agent> <content>` helper that writes the .md file.

---

### High-Impact Finding #8: F4 Duplicates Existing lib-verdict.sh Functions

**Location:** F4 Task 4.1, lib-verdict.sh

**Finding:** Task 4.1 says "Extract verdict parsing library" and lists functions:
- `verdict_parse_all()` — "reads all `.clavain/verdicts/*.json`, outputs a summary table"
- `verdict_count_by_status()` — "returns counts per STATUS"
- `verdict_get_attention()` — "returns only NEEDS_ATTENTION verdicts"

But lib-verdict.sh Codex summary shows these already exist:
- `verdict_parse_all` — "iterates all .json verdicts and prints one-line summaries per agent"
- `verdict_count_by_status` — "computes aggregate counts, outputs compact comma-separated summary"
- `verdict_get_attention` — "filters NEEDS_ATTENTION and FAILED verdicts"

**Duplication:** F4 Task 4.1 is not "extract" — it's "verify existing functions meet requirements". The plan treats this as new work when it's validation work.

**Recommendation:** Rewrite F4 Task 4.1 as "Validate lib-verdict.sh API" with checklist:
- [ ] `verdict_parse_all` output format matches sprint.md expectations
- [ ] `verdict_count_by_status` returns comma-separated string (not JSON)
- [ ] `verdict_get_attention` includes DETAIL_PATH in output
- [ ] All functions handle missing verdict directory gracefully (no-op, not error)

If gaps exist, document them as delta tasks. Do not rewrite functions that already exist.

---

### High-Impact Finding #9: F5 Inverted Return Convention Hazard

**Location:** F5 Task 5.2, proposed `sprint_should_skip` function

**Finding:** The plan does not show implementation of `sprint_should_skip` but the key architectural decisions list (line 5) flags: "F3's sprint_should_skip() returns 0 for skip and 1 for execute — is this inverted convention safe?"

Codex query on lib-sprint.sh shows `sprint_should_pause` exists with inverted convention:
> "Return convention is intentionally inverted: 0 + reason string = pause; 1 + no output = continue."

**Consistency analysis:** Bash convention is 0=success/true, 1=failure/false. For boolean predicates:
- `should_skip`: 0=skip (success/true), 1=continue (failure/false) — matches pause convention
- `sprint_should_pause`: 0=pause (success/true), 1=continue (failure/false) — documented as intentional

So the convention is consistent but inverted from typical Bash. The hazard is when mixing inverted predicates with normal ones:

```bash
if sprint_should_skip "$phase"; then
  # This block runs when return is 0, i.e., when skip is TRUE
  # Correct: we are skipping
fi

if some_normal_check; then
  # This block runs when return is 0, i.e., when check is TRUE
  # Same syntax, opposite semantics if some_normal_check follows standard convention
fi
```

**Recommendation:** Accept the inverted convention (it's already established in `sprint_should_pause`) but add defensive documentation:
1. Add a comment block in lib-sprint.sh above `sprint_should_pause` and `sprint_should_skip` (when created) that explains the inversion and lists all functions using this convention
2. In F5 Task 5.2, add a test case that verifies the return value matches expected behavior (e.g., `sprint_should_skip "brainstorm" && echo "SKIP" || echo "RUN"` produces expected output)
3. Name the function `sprint_check_should_skip` to make it clear it's a check/predicate, not an action

---

### High-Impact Finding #10: F6 Checkpoint Validation Is Advisory-Only

**Location:** F6 Task 6.3, checkpoint_validate function

**Finding:** Task 6.3 says:
> "Validate git SHA with checkpoint_validate (warn on mismatch, don't block)"

And from sprint.md Codex query:
> "resume logic reads checkpoint, validates SHA, gets completed steps, and skips to the first incomplete one"

But the checkpoint_validate function (Task 6.1) returns 1 on mismatch and prints a warning. The caller (Task 6.3) is instructed not to block on return code 1.

**Architectural risk:** Some sprint steps are code-dependent:
- Step 4 (Review Plan): reviews the plan file, safe to resume even if code changed
- Step 5 (Execute): writes code based on the plan, unsafe to resume if code changed since plan was written
- Step 7 (Quality Gates): runs tests on the code, unsafe if code changed since execution

If code changes between Execute and Quality Gates, resuming at Quality Gates will test the wrong code state. The warning will be printed but scroll past, and the sprint will produce incorrect results (tests run against modified code, not the code that Execute wrote).

**Recommendation:** Make validation behavior configurable per step. Add to checkpoint schema:
```json
{
  "steps": [
    {"name": "brainstorm", "sha_required": false},
    {"name": "execute", "sha_required": true},
    {"name": "quality-gates", "sha_required": true}
  ]
}
```

In F6 Task 6.3, modify resume logic:
- If resuming at a step with `sha_required: true`, block on SHA mismatch and require user override flag (`--force-resume`)
- If resuming at a step with `sha_required: false`, warn but continue

This preserves safety without making checkpointing too rigid.

---

## Simplicity & YAGNI Analysis

### Medium Finding #11: Verdict Schema Overspecifies for 2-Agent Case

**Location:** F3 Task 3.1, verdict schema

**Finding:** The schema has 8 fields but only 4 agents exist (per CLAUDE.md: "4 agents, 52 commands"). Review agents (2) and workflow agents (2) have different output characteristics:

**Review agents** (plan-reviewer, data-migration-expert):
- TYPE: verdict
- STATUS: CLEAN | NEEDS_ATTENTION
- FILES_CHANGED: always `[]` (reviewers don't change files)
- FINDINGS_COUNT: varies

**Workflow agents** (bug-reproduction-validator, pr-comment-resolver):
- TYPE: implementation
- STATUS: COMPLETE | PARTIAL | FAILED
- FILES_CHANGED: varies
- FINDINGS_COUNT: always 0 (implementations don't produce "findings")

**Overspecification:** Every verdict file has 3 fields that are always empty/zero for that agent type. `FILES_CHANGED` is dead for review agents. `FINDINGS_COUNT` is dead for workflow agents.

**YAGNI concern:** The schema anticipates future agent types (e.g., a hybrid agent that both reviews AND changes files) but no such agent exists in the plan. The plan is building generic infrastructure for a 4-agent use case.

**Recommendation:** Keep the unified schema (it's already implemented in lib-verdict.sh per Codex) but add to F3 Task 3.1 documentation: "Unused fields must be present but can be zero/empty. Review agents set `files_changed: []`. Workflow agents set `findings_count: 0`." This makes the contract explicit and prevents agents from omitting fields.

Do not split into two schemas unless agent count grows beyond 10 and field waste becomes measurable.

---

### Medium Finding #12: F4 max_turns Audit Crosses Feature Boundary

**Location:** F4 Task 4.3

**Finding:** Task 4.3 says:
> "Add max_turns to Task dispatches. Audit and add max_turns to every Task dispatch: Explore agents: 10, Review agents: 15, Implementation agents: 30, Research agents: 20."

This is a global change that affects all agent dispatches, not just verdict-consuming ones. It belongs in a separate operational excellence task, not in the "Verdict Consumption" feature.

**Scope creep:** F4's goal is "Sprint orchestrator reads structured verdicts and routes on STATUS field". Adding turn limits to dispatches improves cost control but is orthogonal to verdict consumption. An agent can exceed max_turns whether or not it writes a verdict file.

**Recommendation:** Move Task 4.3 to a new feature "F7: Agent Dispatch Turn Limits" with its own bead. This feature:
- Audits all Task tool invocations in skills/ and commands/
- Adds max_turns based on agent category
- Documents the turn limit policy in using-clavain/references/
- Estimates 1-2 hours, low risk

Keep F4 focused on verdict file I/O.

---

### Medium Finding #13: F5 Phase Skipping Duplicates Existing Logic

**Location:** F5 Task 5.2, sprint.md pre-step

**Finding:** Codex query shows sprint.md already has complexity-based phase skipping:
> "1–2 skips brainstorm+strategy and goes to plan, 3 does standard flow, 4–5 uses full/complex workflow"

F5 Task 5.2 proposes:
> "Score-based routing: 1-2: Skip to Step 3 (write-plan), skip flux-drive review, use Sonnet-only agents. 3: Standard workflow, all steps. 4-5: Full workflow with Opus orchestration."

**Duplication:** The only new behavior in F5 Task 5.2 is "use Sonnet-only agents" and "Opus orchestration" based on score. The phase skipping logic is already implemented.

**Recommendation:** Rewrite F5 Task 5.2 as "Extend complexity routing with model tier selection":
1. Keep existing phase skip logic (already works)
2. Add model tier selection: read complexity score, set `SPRINT_MODEL_TIER=haiku|sonnet|opus`
3. Modify sprint skill to pass model tier to Task dispatches (if Claude Code supports this — verify first)
4. Document model tier policy in sprint.md

Estimated delta: 1 hour (down from 3-4h in plan).

---

### Medium Finding #14: F6 Checkpoint Schema Lacks Actual Measurements

**Location:** F6 Task 6.1, checkpoint schema

**Finding:** Task 6.1 defines checkpoint schema with `tokens_spent` but F4 Task 4.4 says:
> "Token tracking is estimated (from verdict TOKENS_SPENT fields), not measured. Precise measurement is iv-8m38's job."

**Inconsistency:** The checkpoint persists estimated tokens but the schema doesn't indicate they are estimates. When iv-8m38 (precise measurement feature) ships, the checkpoint schema will need a new field `tokens_spent_actual` to store measured values alongside estimates.

**Forward compatibility:** Without a version field in checkpoints (same issue as verdicts in Finding #5), migrating from estimated to measured tokens will require manual checkpoint file surgery or a migration script.

**Recommendation:** Add to F6 Task 6.1 checkpoint schema:
```json
{
  "version": 1,
  "tokens_spent_estimated": 45200,
  "tokens_spent_actual": null,
  "measurement_source": "verdict_aggregation"
}
```

When iv-8m38 ships, it can populate `tokens_spent_actual` and set `measurement_source: "interstat"`. Old checkpoints with `tokens_spent` (no suffix) can be migrated by renaming the field.

---

## Cross-Feature Coupling

### Dependency Graph (Actual vs. Declared)

**Plan declares:**
| Feature | Depends On |
|---------|------------|
| F2 | — |
| F3 | F2 |
| F1 | F3 |
| F4 | F1 |
| F5 | F4 |
| F6 | F4 |

**Actual dependencies from findings:**
| Feature | Depends On | Why |
|---------|------------|-----|
| F2 | — | Session-start.sh change (companion → env var) |
| F3 | — | Verdict schema + lib-verdict.sh (standalone) |
| F1 | F3 | Agent .md Output Contract sections (but F1 is a no-op) |
| F4 | F3 | Reads verdict files written by agents per F3 schema |
| F5 | — | Complexity classifier change (but duplicates existing) |
| F6 | F4 | Checkpoint includes verdict file paths from F4 |

**Hidden coupling:**
- F2 + F4: Both modify session-start.sh context assembly (see Finding #2)
- F3 + F6: Both define JSON schemas without version fields (see Findings #5, #14)
- F4 + F5: Both modify sprint.md routing logic (verdict consumption + complexity routing)

**Safe parallelization:**
- F2 and F3 can run in parallel (no shared files)
- F5 and F6 can run in parallel IF F4 is complete (both read from F4 outputs)

**Unsafe parallelization:**
- F3 and F4 cannot be parallelized — F4 depends on verdict schema from F3
- F1 and F3 cannot be parallelized — both edit the same agent .md files

**Recommendation:** Revise implementation order to:
1. F3 (verdict schema + lib-verdict.sh + agent .md contracts) — 2-3h
2. F2 (session-start.sh companion migration) + F5 (complexity model tier) in parallel — 2-3h total
3. F4 (sprint verdict consumption validation) — 1h (reduced scope, mostly verification)
4. F6 (checkpointing) — 3-4h

Delete F1 entirely. Total: 8-11 hours (down from 14-19h).

---

## Decision Lens

### Boundary Integrity

**Current state:** Clavain has clear layer boundaries:
- **Session lifecycle:** hooks/session-start.sh, hooks/auto-compound.sh, hooks/session-handoff.sh
- **Sprint orchestration:** commands/sprint.md, hooks/lib-sprint.sh
- **Agent dispatch:** scripts/dispatch.sh (Codex), Task tool (Claude)
- **Artifact management:** hooks/lib-verdict.sh, hooks/lib-interspect.sh

**Plan impact:**
- F2 keeps session-start.sh in its lane (context injection only) — ✓ good
- F3 adds lib-verdict.sh as a new artifact management layer — ✓ good separation
- F4 makes sprint.md consume verdicts — ✓ correct layer (orchestrator reads artifacts)
- F5 modifies lib-sprint.sh complexity classifier — ⚠ changes existing contract
- F6 adds checkpointing to sprint.md — ⚠ sprint becomes stateful (was mostly stateless)

**Crossing concern:** F6 makes sprint.md responsible for checkpoint I/O in addition to orchestration. This is acceptable (orchestrators own their state) but adds cognitive load. Consider extracting checkpoint I/O to `hooks/lib-checkpoint.sh` so sprint.md only calls `checkpoint_write(...)` without knowing JSON schema details.

### Entropy Reduction

**Does this plan reduce or increase architectural entropy?**

**Reduces entropy:**
- F3 verdict schema standardizes agent output (eliminates ad-hoc result parsing)
- F2 moves companion discovery to env var (eliminates context injection variability)

**Increases entropy:**
- F1 adds no-op feature (pure documentation churn)
- F4 duplicates existing implementation (creates confusion about source of truth)
- F5 modifies working complexity classifier (introduces migration risk)

**Net effect:** Neutral to slightly negative due to F1/F4/F5 issues. After fixes (delete F1, validate F4, consolidate F5), net effect becomes positive.

---

## Summary

This plan tackles a real problem (token efficiency) with the right strategy (structured contracts, lazy loading, checkpointing) but suffers from:

1. **Redundant work** — F1 is a no-op, F4 reimplements existing code, F5 duplicates existing routing
2. **Missing coordination** — F2/F3/F4 all touch session-start.sh without explicit integration checkpoint
3. **Schema brittleness** — No version fields in verdicts or checkpoints, blocking future evolution
4. **Unsafe validation** — F6 warns on code changes but doesn't block code-dependent steps

**Required actions before implementation:**
1. Delete F1 (merge agent .md contract work into F3)
2. Add "Session-start.sh integration checkpoint" task after F2/F3/F4
3. Add version fields to verdict and checkpoint schemas (F3, F6)
4. Verify F4 against current sprint.md state (may be mostly complete)
5. Audit F5 against current complexity classifier (may only need model tier addition)
6. Make F6 checkpoint validation step-aware (block on code-dependent steps)

**After fixes, estimated effort:** 8-11 hours (down from 14-19h), risk reduced from Medium to Low.

**Architectural alignment:** Once fixed, this plan aligns with Clavain's modpack philosophy (interphase owns phase tracking, interflux owns agents, Clavain orchestrates) and maintains clear separation between session lifecycle, orchestration, and artifact management layers.
