# User/Product Review: B1 Static Routing Table PRD

**Source PRD:** `hub/clavain/docs/prds/2026-02-20-static-routing-table.md`
**Verdict file:** `hub/clavain/.clavain/verdicts/fd-user-product.md`
**Bead:** iv-dd9q
**Track:** B (Model Routing) — Step 1 of 3
**Reviewer:** fd-user-product
**Date:** 2026-02-20

---

## Primary User and Job

The primary user is a single product-minded engineer running Clavain as their autonomous software agency. The job is: control which AI models execute at each stage of a sprint without reviewing individual agent files. Secondary job: understand at a glance what the system is currently doing when troubleshooting cost or quality anomalies.

---

## Verdict Summary

B1 is a sound consolidation. The problem statement is accurate and the solution directly addresses it. The UX regression on `model-routing status` output is the sharpest concern — the proposed output is richer but currently underspecified, so it may deliver confusion rather than clarity if implemented without care. The "phase is caller-provided" decision is technically correct but creates a non-trivial documentation debt. The migration path is implicit rather than explicit. None of these are blockers, but two require remediation in acceptance criteria.

---

## Finding 1: Command UX — Status Output is Underspecified (HIGH)

### Current behavior

`model-routing status` runs `grep -r '^model:' agents/` and formats it as a per-category summary showing model per category and a mode label (economy/quality/mixed). Output is deterministic, scannable, and self-consistent — every agent listed, one line per category. The current output also names the agents by name, which lets the user verify a specific agent is getting the model they expect.

### Proposed behavior

The PRD acceptance criterion reads: "reads routing.yaml and displays a resolved routing table showing model per (phase, category)." No example output is provided. The brainstorm also offers no output format.

### Problem

A phase x category matrix has at minimum 6 phases x 4 categories = 24 cells. If rendered naively, this replaces a 4-line summary with a 24-cell grid. For the common case (user wants to verify economy vs quality mode), a 24-cell table is more friction, not less.

Additionally, the current output provides a "Mode: economy|quality|mixed" label that gives an immediate single-word answer to the most common question ("am I in economy mode?"). The proposed table eliminates this label but adds no equivalent fast-path answer.

After frontmatter removal, agent names disappear from the output entirely. The user loses the ability to verify that a specific agent is getting the model they expect.

### Recommendation

The acceptance criterion must specify output format explicitly. A workable design:

```
Model Routing — economy mode

Phase          research    review    workflow   synthesis
brainstorm     haiku       opus      sonnet     haiku
strategy       haiku       opus      sonnet     haiku
plan           haiku       sonnet    sonnet     haiku
execute        haiku       sonnet    sonnet     haiku
quality-gates  haiku       opus      sonnet     haiku
ship           haiku       sonnet    sonnet     haiku

Dispatch tiers: fast=gpt-5.3-codex-spark  deep=gpt-5.3-codex
Mode: economy  (run `model-routing quality` to switch)
```

Key requirements to add to F4 acceptance criteria:
- Single mode label at top ("economy" / "quality" / "custom")
- Phase rows, category columns — compact grid, not one-per-line
- Dispatch tiers shown in same view (now merged into routing.yaml)
- Actionable footer hint

---

## Finding 2: "quality" Mode Semantic is Fragile Post-Migration (MEDIUM)

### Current behavior

`model-routing quality` sets `model: inherit` in every agent frontmatter. "inherit" is a known Claude Code keyword that passes the parent session's model down.

### Proposed behavior

F4 acceptance criterion states: "model-routing quality writes `model: inherit` (or equivalent) for all categories so all agents use the parent session's model."

### Problem

The parenthetical "(or equivalent)" is doing a lot of work. In routing.yaml, "inherit" may not be a valid model value that `resolve_model` understands — the brainstorm YAML schema only shows concrete model names (sonnet, opus, haiku). If `resolve_model` does not handle the `inherit` sentinel, quality mode is silently broken: routing.yaml is updated, but the resolution library returns an empty or hardcoded value, and no agents actually get the parent session's model.

### Recommendation

F2 acceptance criteria must explicitly include: "`resolve_model` recognizes 'inherit' as a sentinel value and returns it as-is without substitution, allowing the caller to pass it through to the agent invocation layer." If callers are not equipped to pass `inherit` through to Claude Code's subagent dispatch, the quality mode behavior has no implementation path and the acceptance criteria are incomplete.

---

## Finding 3: Non-Goals Missing One Item — Task-Tool Override Disappears Silently (MEDIUM)

The current `model-routing.md` explicitly states: "Individual agents can still be overridden with `model: <tier>` in the Task tool call." After frontmatter removal, this escape hatch disappears. The per-agent `overrides: {}` section in routing.yaml replaces it, but there is no mention of this migration anywhere in the PRD.

An engineer who has relied on Task-tool overrides will find them gone without knowing why or where to look. This is a silent behavior change.

### Recommendation

Add to non-goals: "No per-invocation model override via Task tool arguments — per-agent overrides use routing.yaml's `overrides:` section instead." Add one sentence to F4 acceptance criteria: "Document the migration from Task-tool model overrides to routing.yaml overrides."

---

## Finding 4: "Phase is Caller-Provided" Creates Documentation Debt Without a Caller Migration Plan (MEDIUM)

Decision 5 in the brainstorm (phase passed explicitly by callers) is technically correct for testability and determinism. However, the PRD does not enumerate which callers need updating, and there is no F5 for "update existing phase-aware callers to pass `--phase`."

The skills and hooks that invoke agents today (`lib-sprint.sh`, `interspect-evidence.sh`, `session-start.sh`) do not currently pass phase to any routing layer. After B1, they will need to. Without at least one live caller migrated, B1 delivers a library that is tested in isolation but never called at runtime. The routing table governs `model-routing status` output but has no effect on actual model selection during sprint execution.

### Recommendation

Add acceptance criterion: "At least one existing caller (e.g., the quality-gates phase hook or the flux-drive skill invocation) must be updated to call `resolve_model --phase <phase> --category <category>` and use the returned model in its agent dispatch, demonstrating the library is reachable from real code paths."

---

## Finding 5: Stale Skill Documentation Not Listed in Dependencies (LOW-MEDIUM)

`skills/interserve/SKILL.md` (lines 44, 58-59) and `skills/interserve/references/cli-reference.md` (line 22) both reference `tiers.yaml` directly by path:
- "dispatch.sh supports `--tier fast|deep` to resolve model names from `config/dispatch/tiers.yaml`"
- "Change model names in one place (`tiers.yaml`) when new models ship"
- `| --tier <fast\|deep> | Resolve model from config/dispatch/tiers.yaml |`

Both will be stale after F3 deletes `tiers.yaml`. Neither is listed in the PRD's Dependencies section. An engineer following the interserve skill after B1 ships will read stale instructions.

### Recommendation

Add both files to Dependencies. Add to F3 acceptance criteria: "Update all skill documentation that references `tiers.yaml` to reference `routing.yaml`."

---

## Finding 6: Transitional Routing State Undocumented (LOW)

Between B1 ship and caller migration (Finding 4), routing.yaml is authoritative for introspection (`model-routing status`) but has no effect on runtime dispatch. Runtime dispatch continues using agent frontmatter values because no callers yet call `resolve_model`. The user may run `model-routing economy` and believe routing changed when it has not for any actual sprint execution.

The companion plugin situation compounds this: F4 removes `model:` frontmatter from interflux, intercraft, and intersynth agents, but those plugins require separate publish steps. Until republished, cached versions still carry the old frontmatter values. For the period between frontmatter removal commit and republish, the deployed system may have no model set for those agents at all (neither frontmatter nor resolve_model callers).

### Recommendation

Add an "Interim state" note to the PRD: "Between B1 ship and caller migration, routing.yaml governs `model-routing status` output but runtime dispatch continues to use agent frontmatter until callers adopt `resolve_model`. Companion plugin frontmatter removal requires a coordinated publish of all affected plugins before the routing table takes effect at runtime."

---

## Non-Goals Assessment

The non-goals list is well-scoped and correctly defers B2/B3 features. One addition needed: explicitly defer "phase-to-dispatch-tier mapping" (brainstorm Open Question 4 — should routing.yaml also map phases to dispatch tiers, e.g., brainstorm always uses `--tier deep`). This question is left unanswered in the brainstorm and absent from the non-goals. If an implementer interprets it as in-scope for B1, it adds significant surface area without a clear design decision.

Recommend adding: "Phase-to-dispatch-tier mapping (e.g., brainstorm always uses `--tier deep`) is not part of B1."

---

## Product Validation

**Problem definition:** Accurate. Three independent routing systems confirmed in the codebase: agent frontmatter (4 Clavain agents + 17 interflux agents + others), `config/dispatch/tiers.yaml`, and interspect overrides. The inability to answer "what model will this agent use in this phase?" without reading multiple files is a real friction point.

**Solution fit:** Direct. A single routing.yaml with nested inheritance is the correct architecture. The brainstorm's rationale for nested YAML over flat/matrix alternatives is sound and appropriately self-documenting.

**Opportunity cost:** Low concern. B1 is the prerequisite for B2 and B3 per the stated roadmap. The infrastructure investment is justified by its position in the dependency chain.

**Evidence quality:** Assumption-based for urgency (no data on frequency of routing confusion). Acceptable for a single-user developer tool where the developer's stated friction is sufficient evidence.

**Success signal:** Partially defined. Regression signal is good ("dispatch.sh --tier fast produces identical output before and after migration"). There is no positive success signal for the new capability. Informal criterion to add: "The user can answer 'what model runs in quality-gates review?' from `model-routing status` output in under 10 seconds."

---

## Summary Table

| Finding | Severity | Required Action |
|---------|----------|-----------------|
| F1: Status output format underspecified | HIGH | Add example output + mode label to F4 acceptance criteria |
| F2: "inherit" sentinel not validated in F2 | MEDIUM | Add inherit sentinel handling to F2 acceptance criteria |
| F3: Task-tool override migration undocumented | MEDIUM | Add to non-goals or F4 acceptance criteria |
| F4: No callers updated in B1 | MEDIUM | Add at least one live caller as acceptance criterion |
| F5: interserve skill docs stale after F3 | LOW-MEDIUM | Add to Dependencies and F3 acceptance criteria |
| F6: Transitional routing state undocumented | LOW | Add interim state note clarifying when routing.yaml takes effect |
