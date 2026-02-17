# Architecture Review — Token Budget Controls Implementation Plan

**Reviewed**: 2026-02-16 | **Agent**: fd-architecture | **Verdict**: TBD

---

## Findings Index

- P0 | P0-1 | "Task 2, Task 5" | Billing token calculation misaligned with interstat schema
- P0 | P0-2 | "Task 3, Task 5" | Session-based token queries will return empty during triage
- P0 | P0-3 | "Task 2, Task 3" | Config file path resolution depends on skill execution context
- P1 | P1-1 | "Task 3" | Budget cut algorithm has unstated ordering dependency (slicing timing)
- P1 | P1-2 | "Task 2" | Agent classification function has no error handling for unknown agent names
- P1 | P1-3 | "Task 3" | Budget override path uses PROJECT_ROOT but triage context may not know PROJECT_ROOT yet
- P2 | P2-1 | "Task 5" | Cost report schema in findings.json lacks a version field
- P2 | P2-2 | "Task 3" | Slicing multiplier cross-cutting agent exclusion list not explicitly referenced
- P2 | P2-3 | "Task 7" | Test suite checks for string presence but not semantic correctness
- P3 | P3-1 | "Architecture" | No mechanism to adjust budgets based on past accuracy
- P3 | P3-2 | "Task 1, Task 3" | Enforcement mode "soft" has unclear UX mapping
- P3 | P3-3 | "Task 1, Task 3" | Min agents guarantee may conflict with budget cap (correctly, but underdocumented)

Verdict: needs-changes

---

## Summary

This review evaluates the architectural soundness of adding budget-aware agent dispatch to flux-drive. The plan adds a new config file (`budget.yaml`), a cost estimator script querying interstat, and integrates budget cuts into the existing triage algorithm. The core integration surfaces are: (1) interflux reading interstat's SQLite database, (2) config layering via YAML, (3) skill file modifications for triage and synthesis phases, and (4) test coverage.

The architecture demonstrates strong boundary discipline overall — no new modules, clear separation between config and logic, and appropriate use of existing interstat infrastructure. However, several critical issues demand attention before implementation:

**Critical findings:**
- Billing token calculation is inconsistent with interstat's established pattern (uses `input + output` but plan queries `total_tokens` field which includes cache tokens)
- Session-based queries will fail during triage (tokens not backfilled until SessionEnd, but triage runs at session start)
- Config file path resolution has subtle coupling to skill execution context
- Budget enforcement logic creates a hidden ordering dependency (slicing multiplier must be computed before budget cut, but plan sequences them incorrectly)

**Positive architectural choices:**
- No new interstat schema changes required (queries existing `agent_runs` table)
- Config override pattern via `{PROJECT_ROOT}/.claude/flux-drive-budget.yaml` follows established conventions
- Defaults-with-fallback pattern prevents runtime failures when interstat data is sparse
- Synthesis cost report is read-only (no feedback loop to config)

The plan is implementable with targeted corrections to query logic, execution order, and token semantics.

---

## Issues Found

### Critical (P0)

**P0-1. Billing token calculation misaligned with interstat schema**

**Location:** Task 2 (estimate-costs.sh), Task 5 (synthesize.md cost report)

**Evidence:** The plan uses `COALESCE(input_tokens,0) + COALESCE(output_tokens,0)` as "billing tokens" (lines 142-143, 325), but the estimator queries `total_tokens` field (line 142) which per interstat schema (init-db.sh line 26) is `input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens`. This is effective context, NOT billing tokens.

**Impact:** Budget estimates will be wildly inflated (600x+ per project memory: `docs/solutions/patterns/token-accounting-billing-vs-context-20260216.md`). A 40K billing-token agent could show 240K estimated tokens due to cache pollution.

**Fix:** The query in estimate-costs.sh line 142 should compute billing tokens explicitly:
```sql
SELECT agent_name,
       CAST(ROUND(AVG(COALESCE(input_tokens,0) + COALESCE(output_tokens,0))) AS INTEGER) as est_billing_tokens,
       COUNT(*) as sample_size
FROM agent_runs
WHERE ...
```
NOT `AVG(total_tokens)`. The field name in the script should match semantics: `est_billing_tokens`, not `est_tokens`.

Similarly, synthesize.md Step 3.4b.1 (lines 322-330) uses billing formula correctly in comment but must ensure the SELECT computes it the same way.

**Architectural note:** This violates the token accounting pattern established in interstat. See `plugins/interstat/scripts/report.sh` lines 35-38, 46-49 — it explicitly distinguishes "total_tokens = input + output (billing)" from "effective context = input + cache_read + cache_creation". The plan conflates these.

---

**P0-2. Session-based token queries will return empty during triage**

**Location:** Task 3 Step 1.2c.2 (estimate-costs.sh invocation during triage)

**Evidence:** The cost estimator queries `agent_runs WHERE model = '{MODEL}'` (line 144) across all historical sessions. This is correct — it aggregates past runs. However, the synthesis cost report (Task 5 Step 3.4b.1, line 327) queries `WHERE session_id = '{current_session_id}'`, which will fail.

**Why this breaks:** Per interstat's design (from MEMORY.md and scripts/analyze.py), token columns are backfilled AFTER the session ends via JSONL parsing. During the session (when synthesis runs), `agent_runs.input_tokens` etc. are NULL. The plan's fallback (line 333) uses `result_length` as a proxy, but this is a string length, not tokens, and has no correlation to actual token counts.

**Impact:** Cost reports will show "Actual tokens pending backfill" for every run, rendering the entire actual-vs-estimated delta feature useless until post-session analysis. The plan promises real-time cost reporting but cannot deliver it with session-scoped queries.

**Fix:** Either (1) accept that cost reports only work post-session and document this clearly, OR (2) hook into Claude Code's real-time token reporting if available (check if session JSONL is written incrementally). Option 1 is simpler and safer.

**Architectural principle violated:** The plan assumes interstat provides real-time token data, but interstat's architecture is batch-oriented (SessionEnd trigger). This is a fundamental impedance mismatch.

---

**P0-3. Config file path resolution depends on skill execution context**

**Location:** Task 3 Step 1.2c.1 (budget.yaml path), Task 2 (estimate-costs.sh `BUDGET_FILE` variable)

**Evidence:** The skill references `${CLAUDE_PLUGIN_ROOT}/config/flux-drive/budget.yaml` (line 209), but the script hardcodes `PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"` (line 82). If the skill is invoked from a symlinked plugin cache dir, `SCRIPT_DIR` resolves differently than `CLAUDE_PLUGIN_ROOT`.

**Impact:** Budget file not found, estimates default to all-defaults mode, budget enforcement silently degrades. No error message because the script uses `grep ... 2>/dev/null || echo ""` (line 108).

**Fix:** The script MUST use `CLAUDE_PLUGIN_ROOT` env var if available, falling back to relative resolution:
```bash
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
```
This matches the pattern used in other interflux scripts (see `scripts/detect-domains.py` which reads from plugin root).

**Architectural principle:** Env var indirection exists specifically to solve symlink/cache resolution. Ignoring it creates hidden coupling to directory structure.

---

### Important (P1)

**P1-1. Budget cut algorithm has unstated ordering dependency**

**Location:** Task 3 Step 1.2c (budget-aware selection)

**Evidence:** Step 1.2c.2 (line 228) says "If slicing is active AND agent is NOT cross-cutting: multiply estimate by `slicing_multiplier`". Step 1.2c.3 (line 232) sorts by final_score and accumulates `agent.est_tokens`. But the slicing multiplier is applied PER-AGENT during accumulation, which means the total budget consumption depends on the ORDER in which slicing vs non-slicing agents are processed.

**Example:** If 3 slicing agents (20K each → 10K after 0.5x) and 2 non-slicing agents (40K each) are selected, and budget is 100K:
- Order 1 (slicing first): 10+10+10+40+40 = 110K → last agent deferred
- Order 2 (non-slicing first): 40+40+10+10+10 = 110K → same result (OK)

Wait, this is actually order-independent because we sort by score descending (line 233) and accumulate in that order. The issue is different: **the plan never specifies WHEN the slicing multiplier is determined**. Slicing eligibility is determined in Phase 2 (launch.md) after agents are selected, but Step 1.2c.2 requires knowing "if slicing is active" during triage (Phase 1).

**Actual problem:** Budget cut runs in Step 1.2c (Phase 1 triage) but slicing activation happens in Phase 2 (launch). The plan says "If slicing is active" (line 228) but provides no mechanism to detect this in Phase 1. This is a temporal coupling violation.

**Fix:** Either (1) slicing detection must move earlier (into Step 1.1 document profiling where "slicing eligible (>=1000 lines)" is already computed, line 58), OR (2) budget estimates must be computed twice (once without slicing in Phase 1, once with slicing in Phase 2 if activated). Option 1 is simpler — the document profile already knows if slicing is eligible; just pass `--slicing` to estimate-costs.sh based on that flag.

**Revised Step 1.2c.2:** "If document profile shows slicing eligible (>=1000 lines for diffs, >=200 lines for docs), pass `--slicing` to estimate-costs.sh. For non-cross-cutting agents, the script applies `slicing_multiplier`."

---

**P1-2. Agent classification function has no error handling for unknown agent names**

**Location:** Task 2 (estimate-costs.sh `classify_agent` function, lines 126-135)

**Evidence:** The function uses a case statement with a default fallback (`*) echo "generated"`). If a new agent is added to interflux (e.g., `fd-perception`, `fd-decisions`) but the classification function isn't updated, it will be misclassified as "generated" and get the 40K default instead of the correct cognitive (35K) default.

**Impact:** Budget estimates drift as agent roster evolves. This is a maintenance burden and a hidden coupling between the script and the agent roster.

**Fix:** The classification should use agent metadata (the `category` field from agent roster) rather than hardcoding name patterns. However, the script has no access to agent metadata files. Better approach: add a comment warning that new agents require updating this function, OR make the default category configurable in budget.yaml (e.g., `unknown_agent_default: 40000`).

**Architectural smell:** The script duplicates knowledge that exists elsewhere (agent categories). This violates DRY at the architecture level. But adding a dependency on agent metadata would increase coupling. The lesser evil is explicit duplication with a maintenance comment.

---

**P1-3. Budget override path uses PROJECT_ROOT but triage context may not know PROJECT_ROOT yet**

**Location:** Task 3 Step 1.2c.1 (budget config loading, line 216)

**Evidence:** The plan says "If a project-level override exists at `{PROJECT_ROOT}/.claude/flux-drive-budget.yaml`, use that instead." But `PROJECT_ROOT` is defined in SKILL-compact.md line 12 as "nearest .git ancestor or INPUT_DIR". For multi-repo invocations or when flux-drive is invoked on a file outside a git repo, `PROJECT_ROOT` may be undefined or point to the wrong location.

**Impact:** Budget overrides silently ignored. User sets project-specific budgets but they're never applied.

**Fix:** The skill MUST verify `PROJECT_ROOT` is set before checking for overrides. If unset, skip override check and log "No PROJECT_ROOT detected, using default budget config." This matches the pattern in domain detection (SKILL-compact.md line 28: cache check uses PROJECT_ROOT).

**Architectural principle:** Config layering (defaults → project overrides → user overrides) requires stable path anchors. PROJECT_ROOT is the anchor but it's computed, not guaranteed.

---

### Minor (P2)

**P2-1. Cost report schema in findings.json lacks a version field**

**Location:** Task 5 Step 3.4b.3 (findings.json schema extension, lines 344-372)

**Evidence:** The plan adds a `cost_report` field to findings.json but doesn't version the schema. If cost reporting evolves (e.g., adds cache token deltas, effective context deltas), downstream consumers have no way to detect schema changes.

**Impact:** Future schema changes break parsing in tools that consume findings.json (e.g., interbudget, future dashboards).

**Fix:** Add `"cost_report_version": 1` to the cost_report object. Bump on schema changes.

---

**P2-2. Slicing multiplier is stored in budget.yaml but has domain-specific implications**

**Location:** Task 1 (budget.yaml, line 50) and Task 3 Step 1.2c.2 (slicing application, line 228)

**Evidence:** The slicing multiplier is 0.5 globally, but the plan says "multiply estimate by this factor when document slicing is active" without considering that slicing effectiveness varies by agent type. Cross-cutting agents (architecture, quality) get full content even when slicing is active (per slicing.md lines 11-18), so their multiplier should be 1.0, not 0.5.

Wait, the plan DOES handle this: "If slicing is active AND agent is NOT cross-cutting: multiply estimate" (line 228). So cross-cutting agents are excluded from the multiplier. This is correct.

But there's still an issue: the plan says "multiply estimate by `slicing_multiplier`" (line 228) but doesn't specify where the cross-cutting exclusion list is defined. The skill needs to know which agents are cross-cutting.

**Fix:** Add a comment in budget.yaml listing the cross-cutting agents (fd-architecture, fd-quality) OR reference slicing.md as the source of truth. Better: the skill should read slicing.md's cross-cutting table (lines 11-18) rather than hardcoding the list.

**Architectural smell:** Knowledge about which agents are cross-cutting is duplicated between slicing.md and the budget cut logic. This is acceptable if the skill explicitly references slicing.md, but the plan doesn't specify this.

---

**P2-3. Test suite checks for string presence but not semantic correctness**

**Location:** Task 7 (test-budget.sh tests 8-11, lines 526-551)

**Evidence:** Tests 8-11 use `grep -q` to check for strings like "Step 1.2c", "Est. Tokens", "cost report", "Measurement Definitions". These are structural tests (file contains string X) but don't verify the logic is correct (e.g., that budget cut actually prevents over-budget dispatch).

**Impact:** Tests pass even if budget cut logic is broken, as long as the text is present.

**Fix:** Add at least one integration test that:
1. Sets a low budget (e.g., 50K)
2. Triggers a review that would normally select 5 agents (200K total estimated)
3. Verifies that only 2 agents (top scorers) are dispatched and the rest are marked "Deferred (budget)"

This requires either mocking the cost estimator or creating a fixture interstat DB with known agent costs.

**Scope note:** This might be out of scope for Task 7 (which focuses on structural validation) but should be added to a separate Task 8 (integration tests).

---

### Observations (P3)

**P3-1. No mechanism to adjust budgets based on past accuracy**

The plan collects estimated vs actual deltas (synthesis cost report, Task 5) but has no feedback loop to refine future estimates. Over time, if estimates are consistently off (e.g., all agents run 20% over estimate), budgets should auto-adjust.

This is likely out of scope for v1, but worth noting as a future enhancement. A simple heuristic: if p95 delta across last 20 runs is >+15%, multiply all estimates by 1.15 on next run.

---

**P3-2. Enforcement mode "soft" has unclear UX**

Task 1 budget.yaml line 56 defines `enforcement: soft` as "warn + offer override". But the plan doesn't specify what "warn" looks like. Is it a message in the triage table? A separate AskUserQuestion? How does "offer override" work — is it the "Launch all (override budget)" option in Step 1.3 (line 272)?

The plan should clarify that "soft enforcement" maps to adding the override option in the triage confirmation (which it does in Task 3 Step 2, line 272), and that "hard enforcement" would remove that option and auto-defer agents. This is implicit but should be explicit.

---

**P3-3. Min agents guarantee may conflict with budget cap**

Task 1 budget.yaml line 53 sets `min_agents: 2`, and Task 3 Step 1.2c.3 line 238 says "always select the top-scoring agents if `cumulative < BUDGET_TOTAL` OR `agents_selected < min_agents`."

But what if the top 2 agents each cost 80K and budget is 100K? They fit. What if they each cost 60K and budget is 100K? They still fit (120K > 100K but we're under min_agents threshold). So the min_agents rule OVERRIDES the budget.

This is correct behavior (the plan says "regardless of budget", line 53), but it means budgets are not hard caps — they're soft targets. The plan should document this more clearly, especially in the Measurement Definitions section (Task 6).

---

## Improvements

**IMP-1. Consolidate token semantics into a shared constant or enum**

The distinction between billing tokens (input+output) and effective context (input+cache_read+cache_creation) appears in 3 places: estimate-costs.sh, synthesize.md cost report, and AGENTS.md Measurement Definitions. Consider adding a shared SQL snippet file (e.g., `config/interstat/queries.sql`) with named queries:
```sql
-- billing_tokens.sql
COALESCE(input_tokens,0) + COALESCE(output_tokens,0)

-- effective_context.sql
COALESCE(input_tokens,0) + COALESCE(cache_read_tokens,0) + COALESCE(cache_creation_tokens,0)
```
Scripts can source these via `$(cat queries/billing_tokens.sql)` to ensure consistency.

**Rationale:** Reduces duplication and makes the token accounting pattern auditable in one place.

---

**IMP-2. Add a --dry-run flag to estimate-costs.sh for testing**

The script outputs JSON but has no way to test it without a real interstat DB. Add:
```bash
--dry-run    # Use fixture data instead of querying DB
```
This would output sample estimates (e.g., fd-architecture: 42K, fd-quality: 38K) for test validation.

**Rationale:** Makes test-budget.sh more robust (Test 6, line 505) by not depending on ~/.claude/interstat/metrics.db existence.

---

**IMP-3. Surface budget config in triage table as a header**

The triage table (Task 3 Step 1.3, lines 263-272) shows per-agent estimates and a budget summary line. Consider adding a header ABOVE the table:
```
Budget: plan (150K) | Slicing: active (0.5x for domain agents)
```
This gives users context before they read the agent list.

**Rationale:** Improves clarity — users see the budget constraint before evaluating agent selection.

---

**IMP-4. Log when default estimates are used vs interstat data**

The cost estimator uses interstat data when available (>=3 runs, line 147) and falls back to defaults otherwise. The triage table shows "Source" column (line 265) but there's no aggregate summary like "5/8 agents using historical data, 3/8 using defaults."

Adding this to the budget summary line would help users calibrate confidence:
```
Budget: 120K / 150K (80%) | Deferred: 2 agents (60K est.) | Estimates: 5 historical / 3 default
```

**Rationale:** Transparency about estimate quality helps users decide whether to trust budget cuts.

---

**IMP-5. Validate budget.yaml on plugin load**

Task 7 test-budget.sh validates the config file (Tests 1-5, lines 463-495) but this only runs during testing. If a user edits budget.yaml and introduces invalid YAML or missing keys, they won't know until flux-drive fails mid-run.

Consider adding a SessionStart hook that runs `python3 -c "import yaml; yaml.safe_load(open('budget.yaml'))"` and logs a warning if invalid. This is cheap (1ms) and catches 90% of config errors.

**Rationale:** Fail-fast on config errors rather than surfacing them during triage.

---

**IMP-6. Add a budget.yaml example for project overrides**

The plan mentions `{PROJECT_ROOT}/.claude/flux-drive-budget.yaml` (line 216) but doesn't provide an example. Add a comment in the main budget.yaml:
```yaml
# Override per-project via {PROJECT_ROOT}/.claude/flux-drive-budget.yaml
# Example project override (only include keys you want to override):
#   budgets:
#     plan: 200000    # Increase budget for this project
#   min_agents: 3     # Require at least 3 agents
```

**Rationale:** Reduces user confusion about override syntax and scope.

---

**IMP-7. Consider adding a budget.yaml schema file**

For projects using YAML schema validation (e.g., with VS Code YAML extension), a JSON Schema file would enable autocomplete and validation. This is low-priority but high-value for users who edit config frequently.

**Rationale:** Improves config editing UX, especially for less common fields like `slicing_multiplier`.

---

## Verdict

**needs-changes**

The plan is architecturally sound in its module boundaries and integration approach, but has 3 critical correctness issues (P0-1, P0-2, P0-3) that would cause runtime failures or incorrect behavior. These MUST be fixed before implementation:

1. Fix billing token calculation to match interstat semantics (query `input+output`, not `total_tokens`)
2. Document that synthesis cost reports only work post-session (accept batch-mode limitation), OR redesign to use real-time token sources
3. Use `CLAUDE_PLUGIN_ROOT` env var for config resolution to handle symlinked plugin cache dirs

The P1 issues (ordering dependency, agent classification brittleness, PROJECT_ROOT assumptions) are important but addressable via documentation and explicit sequencing in the skill file.

Once these are corrected, the plan delivers the stated goal (budget-aware agent dispatch) without introducing architectural entropy. The config layering is clean, the interstat integration is read-only (no schema changes), and the skill modifications are localized to the triage and synthesis phases as intended.

---

<!-- flux-drive:complete -->
