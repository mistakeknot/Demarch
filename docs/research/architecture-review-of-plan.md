# Architecture Review: Clavain Boundary Restructure Plan

**Plan:** `/root/projects/Interverse/docs/plans/2026-02-14-clavain-boundary-restructure.md`
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-14-clavain-boundary-restructure.md`
**Reviewer:** Flux-drive Architecture & Design Reviewer
**Date:** 2026-02-14

## Executive Summary

This plan extracts 5 domain-specific skills from Clavain into 4 new companion plugins (interslack, interform, intercraft, interdev) plus moves 1 skill to an existing plugin (tldr-swinton). The extraction reduces Clavain from 37 commands/27 skills/5 agents to 32 commands/22 skills/4 agents.

**Overall Assessment: STRUCTURALLY SOUND with 3 MUST-FIX issues and 2 recommendations.**

The boundary design is coherent and the extraction modules are clean. However, the plan has critical gaps in cross-reference handling, metadata sync, and the plugin.json update strategy.

---

## 1. Boundaries & Coupling

### ✅ Strengths

**Module boundaries are clean and domain-aligned:**
- **interslack** (slack-messaging) — Communication domain, single skill, zero dependencies on Clavain internals
- **interform** (distinctive-design) — Design/UX domain, single skill, purely advisory content
- **interdev** (mcp-cli) — Developer tooling domain, single skill, tool-discovery focused
- **intercraft** (agent-native-architecture cluster) — Coherent domain with strong internal cohesion (skill + 14 references + agent + command all reinforce the same principles)

**Coupling is broken, not created:**
- Moving skills OUT of Clavain reduces hub bloat without introducing new inter-plugin dependencies
- No skills in the extraction reference `${CLAUDE_PLUGIN_ROOT}` or call Clavain commands
- The new plugins are genuinely standalone — they can be installed independently

**Extraction does NOT create scope creep:**
- Each moved skill belongs to exactly one new plugin
- No partial extractions or split responsibilities
- The agent-native cluster moves as a unit (14 references + 1 agent + 1 command + 1 skill)

### ❌ MUST-FIX: Cross-Reference Gaps

**Issue 1: help.md alias cleanup is incomplete**

The plan says "Update `help.md` if it lists aliases, remove them" but help.md line 23 DOES list all 4 aliases:
```markdown
> **Aliases:** `/deep-review` = flux-drive, `/full-pipeline` = sprint, `/lfg` = sprint, `/cross-review` = interpeer
```

This line must be deleted. The plan treats this as optional ("if it lists"), but it's mandatory.

**Issue 2: Missing validation of moved command references**

The plan moves `/clavain:agent-native-audit` to `/intercraft:agent-native-audit` but doesn't verify:
- Does any other Clavain command reference it? (No grep check in the plan)
- Does it appear in help.md's command table? (Yes, line 54: `| /clavain:agent-native-audit |`)
- Are there any skills that invoke it? (Not checked)

**Issue 3: agent-rig.json postInstall message not updated**

Task 7 says "Fix postInstall message (remove `/lfg` reference, use `/sprint`)" but the current agent-rig.json postInstall message is not shown in the plan. The plan should explicitly state what the OLD message says and what the NEW message should say, or risk missing other alias references embedded in prose.

**Fix:**
Add to Task 7:
```markdown
4. **Cross-reference audit** (run BEFORE updating metadata):
   ```bash
   # Find all references to deleted commands
   grep -r "lfg\|full-pipeline\|cross-review\|deep-review" hub/clavain/{commands,skills,agents,README.md,CLAUDE.md,agent-rig.json}

   # Find all references to agent-native-audit (moving to intercraft)
   grep -r "agent-native-audit" hub/clavain/{commands,skills,agents,README.md,CLAUDE.md,help.md}
   ```
   Fix ALL matches before proceeding.
```

### ⚠️ Recommendation: Document the intercraft coherence rationale

The agent-native-architecture extraction is the largest and most complex (14 reference docs). The plan correctly treats it as a single module, but the PRD doesn't explain WHY this cluster is coherent beyond "they're all about agent-native patterns."

The reality: this is a **knowledge cluster** where the skill, agent, and command all operate on the same body of reference documentation. The skill injects references into context. The agent reviews code against those principles. The command audits compliance. They're coupled by shared domain knowledge, not by code dependencies.

This is a GOOD extraction, but the reasoning should be documented so future extractions can apply the same "knowledge cluster" test: does the skill/agent/command trio operate on a shared reference corpus?

**Fix:** Add to PRD or ARCHITECTURE.md:
```markdown
## Extraction Pattern: Knowledge Clusters

The agent-native-architecture extraction demonstrates the "knowledge cluster" pattern:
- Skill: Injects reference docs into context for design work
- Agent: Reviews code against the same principles
- Command: Audits codebase compliance with the same principles
- References: 14 shared documents defining the domain

When a skill, agent, and command all operate on the same reference corpus, they form a coherent extraction candidate even if they don't call each other. The coupling is conceptual, not code-level.
```

---

## 2. Pattern Analysis

### ✅ Strengths

**Extraction follows "domain over artifact type" principle:**
- Not extracting "all skills" or "all single-file skills"
- Extracting by domain: communication (slack), design (form), architecture (craft), tooling (dev)
- This is the right abstraction level for plugin boundaries

**Naming convention is consistent:**
- All new plugins follow `inter` + 1-syllable pattern
- Matches existing ecosystem (interphase, interline, interflux, interpath, interwatch)
- The 1-syllable rule keeps names scannable and memorable

**No god-module creation:**
- The plan doesn't dump all extracted skills into a single "misc" plugin
- Each new plugin has a coherent, single-purpose identity

### ❌ MUST-FIX: Plugin.json metadata sync is fragile

**Issue: The plan doesn't update plugin.json arrays**

Task 7 says:
> Update `hub/clavain/.claude-plugin/plugin.json`:
>    - Update `description` with new counts (32 commands, 22 skills, 4 agents)
>    - Ensure `skills`, `commands`, `agents` arrays match filesystem

But the current plugin.json (lines 1-28) has NO `skills`, `commands`, or `agents` arrays. It uses **directory discovery** (if arrays are absent, Claude Code scans `skills/`, `commands/`, `agents/` directories).

This means the plan's instruction "update arrays" is a no-op — there are no arrays to update. The filesystem IS the source of truth.

However, the **description counts** (line 4) are hardcoded: "5 agents, 37 commands, 27 skills". These MUST be updated after the extraction, or the description will be a lie.

**Fix:** Replace Task 7 step 1 with:
```markdown
1. **`hub/clavain/.claude-plugin/plugin.json`:**
   - Update `description` line: change "5 agents, 37 commands, 27 skills" to "4 agents, 32 commands, 22 skills"
   - Update companion list: add "interslack, interform, intercraft, interdev" to the companions list
   - No array updates needed (plugin uses directory discovery)
```

**Also fix Task 2-6:** Each task says "update plugin.json skills array" but the new plugins also won't have arrays (they'll use directory discovery). The instructions should say "ensure plugin.json `skills` field is omitted (directory discovery)" rather than "add to skills array."

### ⚠️ Recommendation: Add version alignment to Task 7

The plan creates 4 new plugins but doesn't specify their initial version (0.1.0 is in the templates, which is good). However, Task 8 (marketplace) will fail if the version in plugin.json doesn't match the version in marketplace.json.

The plan should explicitly state: "All 4 new plugins start at version 0.1.0. When publishing, use `/interpub:release 0.1.0` for each to ensure plugin.json and marketplace.json stay in sync."

**Why this matters:** The project memory (MEMORY.md lines 5-10) documents that version drift between plugin.json and marketplace.json is a recurring failure mode. The plan should prevent this proactively.

---

## 3. Simplicity & YAGNI

### ✅ Strengths

**No premature abstractions:**
- Each new plugin has exactly 1 skill (except intercraft with 1 skill + 1 agent + 1 command)
- No "base classes" or "shared utilities" between the new plugins
- No dependency management beyond the rig installer pattern (which already exists)

**No plugin proliferation risk:**
- Going from 13 to 17 companion plugins sounds like a lot, but the PRD correctly notes that the rig installer handles this
- Each new plugin passes the "would this be useful standalone" test
- Users who don't need Slack integration won't install interslack — modularity is a feature, not a bug

**Deletion-first approach:**
- Removes 4 alias commands outright (no migration path, no deprecation shim)
- This is correct — aliases are noise, not functionality

### ❌ MUST-FIX: Validation is incomplete

Task 10 validates file counts but doesn't validate the actual functionality:

```bash
ls hub/clavain/commands/*.md | wc -l` → 32  # ✅ Good
ls hub/clavain/skills/*/SKILL.md | wc -l` → 22  # ✅ Good
```

But missing:
- **Do the new plugins load?** → `claude --plugin-dir plugins/interslack` should succeed
- **Do the moved skills work?** → Invoke each skill and verify it doesn't reference removed paths
- **Do the moved commands work?** → `/intercraft:agent-native-audit` should execute without errors
- **Does Clavain still work?** → `/clavain:sprint` should not break after removing 5 skills

**Fix:** Add to Task 10:
```markdown
### Functional Validation

For each new plugin:
```bash
# Test plugin loads without errors
claude --plugin-dir plugins/interslack --version

# Test skill invokes
# (manually invoke each moved skill and verify no path errors)
```

For Clavain:
```bash
# Test core workflow still works
claude --plugin-dir hub/clavain -p "/clavain:sprint --help"
claude --plugin-dir hub/clavain -p "/clavain:help"
```

For intercraft command:
```bash
# Test moved command loads
claude --plugin-dir plugins/intercraft -p "/intercraft:agent-native-audit --help"
```
```

---

## 4. The Intercraft Extraction (Coherence Check)

**Question:** Is skill + 14 references + agent + command a coherent module?

**Answer: YES, with high confidence.**

### Evidence of Coherence

1. **Shared reference corpus:** All 4 artifacts (skill, agent, command, references) operate on the same 14 reference documents:
   - SKILL.md invokes references to inject context
   - agent-native-reviewer.md uses the same principles to review code
   - agent-native-audit.md uses the same principles to score compliance
   - The 14 references define the shared domain vocabulary

2. **Single responsibility:** "Ensure applications follow agent-native architecture patterns." All 4 artifacts serve this goal through different mechanisms (education, review, audit).

3. **No external dependencies:** None of the 4 artifacts call Clavain commands, reference `${CLAUDE_PLUGIN_ROOT}` outside their own tree, or depend on other Clavain skills.

4. **Standalone utility:** Someone building an agent-native app would benefit from intercraft WITHOUT needing the rest of Clavain's workflow tooling.

### Anti-Pattern Check: NOT a "junk drawer"

A bad extraction would be "move all rarely-used skills to misc-plugin." Intercraft is NOT this. The cluster has:
- Conceptual unity (agent-native architecture)
- Internal cross-references (agent and command both reference the skill's reference docs)
- A clear user journey (learn → review → audit)

### Risk: Command path references

The plan flags this (Task 4, line 129):
> **Special check:** Verify the agent-native-audit command doesn't reference `${CLAUDE_PLUGIN_ROOT}` paths that would break after extraction.

This is the ONLY coherence risk. If agent-native-audit.md hardcodes paths to the reference docs, those paths will break post-extraction.

**Verification:**
Reading agent-native-audit.md (lines 1-278), I see:
- Line 30: "invoke the agent-native-architecture skill" — uses skill invocation, not filesystem paths ✅
- Lines 43-217: Sub-agent prompts reference principles by name, not by file path ✅
- No `${CLAUDE_PLUGIN_ROOT}` or hardcoded `/hub/clavain/skills/` paths ✅

**Conclusion:** The intercraft extraction is architecturally sound. The 4 components form a knowledge cluster and can move as a unit without breaking internal references.

---

## 5. Finding-Duplicate-Functions → tldr-swinton (Fit Analysis)

**Question:** Does finding-duplicate-functions belong in tldr-swinton?

**Answer: YES, with minor reservation.**

### Evidence of Fit

1. **Domain alignment:** tldr-swinton is "token-efficient code context" (CLAUDE.md line 1). Finding-duplicate-functions is "codebase analysis for semantic duplication" (SKILL.md line 1). Both are codebase analysis tools.

2. **Tool similarity:** tldr-swinton provides:
   - `/tldrs-extract <file>` — Extract file structure (functions, classes, imports)
   - Semantic search, structural search, diff context

   finding-duplicate-functions provides:
   - `extract-functions.sh` — Extract function catalog from source
   - Semantic clustering of duplicates via LLM

   The overlap: both extract function metadata from codebases for analysis.

3. **No Clavain-specific dependencies:** The 5 scripts in finding-duplicate-functions/ are self-contained bash/markdown. No references to Clavain paths, no invocations of other Clavain skills.

### Reservation: Skill vs Tool Distinction

tldr-swinton is primarily an **MCP server** (provides tools) with 3 **orchestration skills** on top (CLAUDE.md lines 29-33):
- tldrs-session-start — Runs diff-context automatically
- tldrs-map-codebase — Understand architecture
- tldrs-interbench-sync — Sync interbench coverage

finding-duplicate-functions is an **orchestration skill** (dispatches subagents to categorize/detect duplicates).

The fit question: Does tldr-swinton own "codebase analysis orchestration" or just "code context primitives"?

Current state: tldr-swinton HAS orchestration skills (map-codebase dispatches agents). So adding finding-duplicate-functions as a 4th orchestration skill is consistent with the existing pattern.

### Alternative: interdev

The plan puts mcp-cli in interdev ("developer tooling"). finding-duplicate-functions is also a developer tool (codebase hygiene). It could go there.

But interdev is scoped as "tool discovery" (mcp-cli is about discovering and using MCP tools), whereas finding-duplicate-functions is about codebase analysis. Weak fit.

### Recommendation: Proceed with tldr-swinton

The domain fit (codebase analysis) outweighs the tool-vs-skill distinction. tldr-swinton already has orchestration skills, so this isn't breaking a boundary.

**One fix needed:** Task 6 says "Verify scripts don't reference Clavain-specific paths or variables." This check is necessary but the plan doesn't say HOW to verify. Add:
```bash
# Task 6 validation
grep -r "CLAVAIN\|clavain" hub/clavain/skills/finding-duplicate-functions/scripts/
grep -r "\${CLAUDE_PLUGIN_ROOT}" hub/clavain/skills/finding-duplicate-functions/scripts/
```
Both should return zero matches.

---

## 6. Parallelization Diagram (Dependency Correctness)

The plan's diagram (lines 236-244):
```
[1] ─────────────────────────────────────────┐
[2] interslack  ─────────────────────────────┤
[3] interform   ─────────────────────────────┤──→ [7] Update metadata ──→ [10] Validate
[4] intercraft  ─────────────────────────────┤──→ [8] Marketplace    ──┘
[5] interdev    ─────────────────────────────┤──→ [9] Git init       ──┘
[6] tldr-swinton ────────────────────────────┘
```

### ✅ Dependency Correctness: Mostly Correct

**Tasks 1-6 are truly parallel:**
- Deleting alias commands (Task 1) doesn't touch any files that Tasks 2-6 modify ✅
- Tasks 2-6 each move different skills from Clavain to different destinations ✅
- No file is modified by more than one task ✅

**Task 7 (Update metadata) correctly depends on Tasks 1-6:**
- Can't update README counts until extractions are done ✅
- Can't update plugin.json description until file counts are known ✅

**Task 8 (Marketplace) correctly depends on Tasks 2-5:**
- Needs plugin.json files from new plugins ✅
- But doesn't actually depend on Task 1 (alias deletion) or Task 6 (tldr-swinton move)
- The diagram shows Task 8 depending on all of Tasks 1-6, but it only needs Tasks 2-5

**Task 9 (Git init) correctly depends on Tasks 2-5:**
- Can't `git init` until plugin directories exist ✅
- But doesn't depend on Tasks 1, 6, 7, or 8

**Task 10 (Validate) correctly depends on all tasks:**
- Final validation must run after everything else ✅

### ❌ Minor Issue: Task 8 and 9 aren't actually parallel

The diagram shows:
```
[7] Update metadata ──→ [10] Validate
[8] Marketplace    ──┘
[9] Git init       ──┘
```

This implies Tasks 8 and 9 can run in parallel and both feed into Task 10. But Task 8 (add to marketplace.json) and Task 9 (git init the new plugins) are independent — neither depends on the other.

However, Task 10 (validation) includes checking `python3 -c "import json; json.load(open('plugins/<name>/.claude-plugin/plugin.json'))"` which means the plugin directories must exist (from Tasks 2-5) but doesn't require Task 9 (git init) to have completed.

**Fix:** The diagram should show:
```
[7] Update metadata ──→ [10] Validate
[8] Marketplace    ──┘      ↑
[9] Git init       ─────────┘
```
Tasks 7 and 8 can run in parallel (they modify different repos). Task 9 is independent and can run anytime after Tasks 2-5. Task 10 depends on all of them.

But this is a minor diagram nit — the parallelization strategy itself is sound.

---

## 7. Plugin.json Array Updates (Plan Correctness)

**Critical Finding:** The plan's instructions for updating plugin.json arrays are based on a false assumption.

### Current State

Clavain's plugin.json (lines 1-28) has:
- ✅ `name`, `version`, `description`, `author`, `license`, `keywords`, `mcpServers`
- ❌ NO `commands` array
- ❌ NO `skills` array
- ❌ NO `agents` array

This means Clavain uses **directory discovery** (Claude Code scans `commands/`, `skills/`, `agents/` dirs).

### Plan's Instructions (Task 7, line 181)

> Ensure `skills`, `commands`, `agents` arrays match filesystem

This is **impossible** because the arrays don't exist. The instruction should be:

> Verify filesystem matches expected counts (plugin uses directory discovery, not arrays)

### Fix for All Tasks

Replace every instance of "update plugin.json skills/commands/agents array" with:

**For new plugins (Tasks 2-5):**
```markdown
**plugin.json:**
- Uses directory discovery (no `commands`, `skills`, `agents` arrays)
- Directories: `./skills/`, `./commands/`, `./agents/` as applicable
```

**For Clavain (Task 7):**
```markdown
**plugin.json:**
- Update `description` counts: "4 agents, 32 commands, 22 skills"
- Update companions list: add interslack, interform, intercraft, interdev
- No array updates (uses directory discovery)
```

**For tldr-swinton (Task 6):**
```markdown
**plugin.json:**
- Verify it uses directory discovery or has a `skills` array
- If array exists: add `./skills/finding-duplicate-functions`
- If directory discovery: move files and plugin auto-discovers
```

---

## 8. Risk Assessment

### High-Risk Areas

1. **Cross-reference breakage** (P0)
   - Risk: help.md, sprint.md, setup.md, or other commands reference deleted aliases or moved commands
   - Mitigation: Add grep audit to Task 7 (see Section 1)

2. **Version sync failure** (P0)
   - Risk: New plugins published with plugin.json version ≠ marketplace.json version
   - Mitigation: Use `/interpub:release <version>` for all 4 new plugins (see Section 2)

3. **Path breakage in moved artifacts** (P1)
   - Risk: agent-native-audit or finding-duplicate-functions reference old plugin root paths
   - Mitigation: Already flagged in plan (Task 4 line 129, Task 6 line 174) but needs explicit grep check

### Medium-Risk Areas

4. **Functional regression** (P2)
   - Risk: Clavain's core workflows break after removing 5 skills
   - Mitigation: Add functional validation to Task 10 (see Section 3)

5. **Incomplete cleanup** (P2)
   - Risk: Stale references in README, CLAUDE.md, agent-rig.json postInstall message
   - Mitigation: Cross-reference audit (see Section 1)

### Low-Risk Areas

6. **Git repo creation** (P3)
   - Risk: GitHub repos don't exist yet, marketplace URLs are placeholders
   - Mitigation: Plan explicitly notes this (Task 8 line 207)

7. **Rig installer compatibility** (P3)
   - Risk: New plugins don't auto-install as companions
   - Mitigation: agent-rig.json update in Task 7 handles this

---

## 9. Must-Fix Summary

**Before executing the plan, make these changes:**

### Fix 1: Add Cross-Reference Audit to Task 7
```markdown
**Task 7 Step 0 (run BEFORE updating metadata):**

Cross-reference audit:
```bash
# Find all references to deleted commands
grep -rn "lfg\|full-pipeline\|cross-review\|deep-review" \
  hub/clavain/{commands,skills,agents,README.md,CLAUDE.md,agent-rig.json,help.md}

# Find all references to moved command
grep -rn "agent-native-audit" hub/clavain/{commands,skills,agents,README.md,CLAUDE.md,help.md}

# Find all references to moved skills
grep -rn "slack-messaging\|distinctive-design\|agent-native-architecture\|finding-duplicate-functions\|mcp-cli" \
  hub/clavain/{commands,README.md,CLAUDE.md,agent-rig.json}
```

Fix ALL matches:
- Delete alias references from help.md line 23
- Update agent-native-audit references to /intercraft:agent-native-audit
- Update postInstall message (remove /lfg, use /sprint)
```

### Fix 2: Correct Plugin.json Update Instructions

Replace Task 7 Step 1:
```markdown
**OLD (incorrect):**
Ensure `skills`, `commands`, `agents` arrays match filesystem

**NEW (correct):**
Update `description` counts: change "5 agents, 37 commands, 27 skills" to "4 agents, 32 commands, 22 skills"
Update companions list in description: add "interslack, interform, intercraft, interdev"
No array updates needed — Clavain uses directory discovery
```

### Fix 3: Add Functional Validation to Task 10

Add after file count checks:
```bash
### Functional Validation

# Test new plugins load
for plugin in interslack interform intercraft interdev; do
  claude --plugin-dir "plugins/$plugin" --version || echo "FAIL: $plugin"
done

# Test Clavain still works
claude --plugin-dir hub/clavain -p "/clavain:help" | grep -q "Daily Drivers" || echo "FAIL: Clavain help"

# Test moved command
claude --plugin-dir plugins/intercraft -p "/intercraft:agent-native-audit --help" | grep -q "Agent-Native" || echo "FAIL: intercraft command"

# Test tldr-swinton skill addition
claude --plugin-dir plugins/tldr-swinton -p "list skills" | grep -q "finding-duplicate-functions" || echo "FAIL: tldr-swinton skill"
```

---

## 10. Recommendations (Optional Improvements)

### Recommendation 1: Document the Knowledge Cluster Pattern

Add to PRD or Clavain's ARCHITECTURE.md:
```markdown
## Extraction Pattern: Knowledge Clusters

When a skill, agent, and command all operate on the same reference corpus (like the 14 agent-native-architecture docs), they form a coherent extraction candidate. The coupling is conceptual (shared domain knowledge), not code-level (function calls).

Example: intercraft extraction moves skill + agent + command + 14 references as a unit because they all serve the same goal (agent-native architecture compliance) through different mechanisms (education, review, audit).
```

### Recommendation 2: Add Version Sync Reminder to Task 8

Replace Task 8 instruction:
```markdown
**OLD:**
Add 4 entries to marketplace.json with version 0.1.0

**NEW:**
Add 4 entries to marketplace.json with version 0.1.0
CRITICAL: After publishing, verify plugin.json version matches marketplace.json version for all 4 plugins
Use `/interpub:release 0.1.0` to ensure atomic updates
```

### Recommendation 3: Improve Parallelization Diagram

Replace diagram with:
```
Tasks 1-6 (parallel) ──┐
                       ├──→ Task 7 (metadata) ──┐
                       ├──→ Task 8 (marketplace) ├──→ Task 10 (validate)
                       └──→ Task 9 (git init) ───┘
```

Notes:
- Tasks 7, 8, 9 can run in parallel (modify different files)
- Task 10 depends on all of 7, 8, 9
- Task 8 only needs Tasks 2-5 (not 1 or 6)
- Task 9 only needs Tasks 2-5 (not 1, 6, 7, or 8)

---

## 11. Final Verdict

### Architecture Correctness: ✅ SOUND
- Module boundaries are clean and domain-aligned
- Extraction breaks coupling without creating new dependencies
- The intercraft cluster is coherent (knowledge cluster pattern)
- finding-duplicate-functions fits tldr-swinton's domain

### Plan Completeness: ⚠️ NEEDS FIXES
- Missing cross-reference audit (MUST-FIX)
- Plugin.json array updates are based on false assumption (MUST-FIX)
- Functional validation is incomplete (MUST-FIX)

### Execution Risk: MEDIUM → LOW (after fixes)
- High risk: cross-reference breakage, version drift
- Medium risk: functional regression, incomplete cleanup
- All risks have clear mitigation paths

### Recommendation: PROCEED AFTER APPLYING 3 MUST-FIX CHANGES

The architectural design is sound. The plan is executable. The fixes are small and localized. Once the 3 must-fix changes are applied, this restructure will successfully clarify Clavain's boundary and reduce hub bloat without breaking existing functionality.

---

## Appendix: Extraction Scorecard

| Module | Boundary | Coupling | Coherence | Fit | Risk |
|--------|----------|----------|-----------|-----|------|
| interslack (slack-messaging) | ✅ Clean | ✅ Zero deps | ✅ Single skill | ✅ Communication domain | Low |
| interform (distinctive-design) | ✅ Clean | ✅ Zero deps | ✅ Single skill | ✅ Design domain | Low |
| intercraft (agent-native cluster) | ✅ Clean | ✅ Zero deps | ✅ Knowledge cluster | ✅ Architecture domain | Medium* |
| interdev (mcp-cli) | ✅ Clean | ✅ Zero deps | ✅ Single skill | ✅ Tooling domain | Low |
| tldr-swinton (finding-duplicate-functions) | ✅ Clean | ✅ Zero deps | ✅ Analysis skill | ✅ Code analysis domain | Low |

*intercraft risk is medium due to command path reference risk, but verification shows it's safe.

---

## File References

- Plan: `/root/projects/Interverse/docs/plans/2026-02-14-clavain-boundary-restructure.md`
- PRD: `/root/projects/Interverse/docs/prds/2026-02-14-clavain-boundary-restructure.md`
- Clavain plugin.json: `/root/projects/Interverse/hub/clavain/.claude-plugin/plugin.json`
- help.md: `/root/projects/Interverse/hub/clavain/commands/help.md`
- sprint.md: `/root/projects/Interverse/hub/clavain/commands/sprint.md`
- agent-native-audit.md: `/root/projects/Interverse/hub/clavain/commands/agent-native-audit.md`
- finding-duplicate-functions: `/root/projects/Interverse/hub/clavain/skills/finding-duplicate-functions/`
- tldr-swinton CLAUDE.md: `/root/projects/Interverse/plugins/tldr-swinton/CLAUDE.md`
