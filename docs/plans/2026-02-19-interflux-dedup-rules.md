# Add Finding Deduplication Rules to Interflux Synthesis

**Bead:** iv-ykx7
**Phase:** executing (as of 2026-02-19T01:38:51Z)
**Sprint:** iv-ey6s
**Date:** 2026-02-19
**Complexity:** 2/5 (simple)

## Problem

Interflux's synthesis phase handles deduplication but lacks explicit rules for edge cases: same file:line with same vs different issues, same issue at different locations, conflicting severity, and conflicting recommendations. The rules from wshobson/agents are well-defined and should be codified.

## Changes

### Task 1: Update synthesis spec (`plugins/interflux/docs/spec/core/synthesis.md`)

**File:** `plugins/interflux/docs/spec/core/synthesis.md`
**Section:** Step 3: Deduplication (lines ~57-89)

Replace the existing dedup logic with explicit rules:

1. **Same file:line + same issue** → Merge into single finding, credit all reporting agents, use highest severity
2. **Same file:line + different issues** → Keep as separate findings, tag as `co_located: true` with shared location reference
3. **Same issue + different locations** → Keep as separate findings, add `cross_references: [finding_ids]` to each
4. **Conflicting severity** → Use highest severity for verdict computation (already partially implemented — formalize)
5. **Conflicting recommendations** → Include both recommendations with agent attribution in `descriptions` map (already partially implemented — formalize)

Update the merged metadata JSON example to show the new fields (`co_located`, `cross_references`).

### Task 2: Update synthesize phase skill (`plugins/interflux/skills/flux-drive/phases/synthesize.md`)

**File:** `plugins/interflux/skills/flux-drive/phases/synthesize.md`
**Section:** Step 3.3 (line ~50-52, currently a stub referencing the subagent)

Add a brief note that the dedup rules are defined in the spec and executed by intersynth. No operational change needed here — this file delegates to the subagent.

### Task 3: Update intersynth synthesize-review agent (`plugins/intersynth/agents/synthesize-review.md`)

**File:** `plugins/intersynth/agents/synthesize-review.md`
**Section:** Step 6: Deduplicate (lines ~69-75)

Expand the dedup step with the 5 explicit rules, matching the spec. The agent needs actionable instructions since it does the actual work:

1. Match by `file:line` + normalized title
2. Same location + same issue → merge, credit all agents, highest severity
3. Same location + different issues → keep separate, tag `co_located`
4. Same issue + different locations → keep separate, cross-reference
5. Severity conflicts → use highest
6. Recommendation conflicts → preserve both with attribution

Also update the findings.json output schema in Step 8 to include `co_located` and `cross_references` fields.

### Task 4: Update findings.json schema in spec

**File:** `plugins/interflux/docs/spec/core/synthesis.md`
**Section:** Step 6: Structured Output (lines ~146-210)

Add `co_located` (boolean) and `cross_references` (string array of finding IDs) to the findings schema.

## Files Changed

| File | Change |
|------|--------|
| `plugins/interflux/docs/spec/core/synthesis.md` | Expand dedup rules (Step 3) + schema (Step 6) |
| `plugins/interflux/skills/flux-drive/phases/synthesize.md` | Minor note in Step 3.3 |
| `plugins/intersynth/agents/synthesize-review.md` | Expand dedup instructions (Step 6) + output schema (Step 8) |

## Test Plan

- [ ] Read all three files after edits to verify consistency
- [ ] Verify the 5 rules appear in both spec and agent instructions
- [ ] Verify findings.json schema includes new fields in both locations
- [ ] Run `python3 -c "import json; json.load(open('plugins/interflux/.claude-plugin/plugin.json'))"` — manifest still valid
- [ ] Run `python3 -c "import json; json.load(open('plugins/intersynth/.claude-plugin/plugin.json'))"` — manifest still valid
