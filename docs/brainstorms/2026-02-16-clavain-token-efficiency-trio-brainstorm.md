# Clavain Token Efficiency Trio — Brainstorm

**Beads:** iv-ked1, iv-hyza, iv-kmyj
**Date:** 2026-02-16
**Status:** Brainstorm

## Problem Statement

Three independent token efficiency improvements compound to reduce Clavain's per-session overhead by 30-50%. Each addresses a different waste vector:

1. **iv-ked1 (Skill injection budget cap):** Skills loaded via `Skill` tool have no size cap. The 23 skills total 167KB (~42K tokens). Individual skills range from 700B to 18.6KB. When multiple skills invoke in a session, uncapped injection silently bloats context. No feedback loop exists to alert skill authors that their skill exceeds a reasonable budget.
2. **iv-hyza (Summary-mode output extraction):** Subagent results (Codex dispatch, flux-drive agents, Task agents) return full verbose output into the orchestrator's context. Each result is 2-10K tokens. A 6-agent flux-drive review injects 12-60K tokens of agent prose. The Findings Index contract already provides a machine-parseable header (~30 lines), but the orchestrator still reads full prose for conflict resolution.
3. **iv-kmyj (Conditional phase skipping):** Sprint workflow runs all 8 phases (brainstorm → brainstorm-reviewed → strategized → planned → plan-reviewed → executing → shipping → done) regardless of task complexity. A complexity classifier already exists (`sprint_classify_complexity()` in lib-sprint.sh, lines 534-671) but is only used for tiered brainstorming — it doesn't gate phase skipping.

**Why together:** Each addresses a different cost surface — injection, result reading, and workflow phases. Combined, they prevent token waste at entry (skill loading), during work (agent results), and across the workflow (unnecessary phases). The compound effect is multiplicative: fewer phases × cheaper phases × tighter results = 30-50% total reduction for simple-to-moderate tasks.

## Current State

### Skill Injection (iv-ked1)

**SessionStart injection:** `session-start.sh` reads `using-clavain/SKILL.md` (1,488 bytes, ~370 tokens) into `additionalContext`. This is already compact — previous session trimmed it from ~10KB. The rest of the `additionalContext` comprises:
- Companion alerts: 200-500 chars when active (intermute agents, beads doctor)
- Interserve mode contract: ~800 chars when flag exists
- Conventions reminder: ~200 chars
- Setup hint: ~100 chars
- Upstream staleness warning: ~200 chars when stale
- Sprint context: 300-800 chars when sprint active
- Discovery brief: variable
- Sprint resume hint: ~150 chars when sprint active
- Handoff context: 0-2KB (capped at 40 lines)
- Inflight agent detection: O(N) per agent

**Total SessionStart injection:** ~2-5KB depending on active companions and sprint state. This is already reasonable.

**Skill-time injection:** When the `Skill` tool invokes a skill, the full SKILL.md is loaded. Sizes:
- writing-skills: 18,646 bytes (~4.7K tokens) — largest
- interpeer: 12,230 bytes (~3K tokens)
- engineering-docs: 11,968 bytes (~3K tokens)
- subagent-driven-development: 10,044 bytes (~2.5K tokens)
- Most skills: 3-8KB (~750-2K tokens)

**No cap exists.** A skill author can write 50KB of instructions and it all gets loaded. No warning, no truncation, no feedback.

**dispatch.sh (Codex dispatch):** Has `INJECT_DOCS_WARN_THRESHOLD=20000` (line 13) — warns when `--inject-docs` prepends >20KB. But this only covers CLAUDE.md/AGENTS.md injection, not skill content.

### Agent Result Reading (iv-hyza)

**Flux-drive synthesis** (synthesize.md Phase 3): Already uses index-first reading — reads Findings Index header (~30 lines) first, only falls back to prose for conflict resolution. The contract is solid. But:
- The orchestrator (Claude's context) still receives the full prose when it reads agent output files
- Each agent writes 500-5000 chars of structured index + 2000-10000 chars of prose body
- For 6 agents, that's 15-90K chars in the orchestrator's context

**Codex dispatch results:** `dispatch.sh` streams JSONL and tracks turns/commands/tokens, but the *output file* (`-o`) contains the full verbose agent response. The orchestrator reads this file to verify results — full content enters context.

**No structured extraction contract exists** for Codex results. Unlike flux-drive (which has the Findings Index), Codex output is freeform prose.

### Phase Skipping (iv-kmyj)

**Existing complexity classifier:** `sprint_classify_complexity()` (lib-sprint.sh:534-671) scores 1-5 using:
- Word count heuristics: <5 words → 3, <30 → 2, 30-100 → 3, >100 → 4
- Trivial keywords: "rename", "format", "typo", "bump" → floor at 1
- Research keywords: "explore", "investigate", "research" → ceiling at 5
- Ambiguity signals: "or", "vs", "alternative" → bump up
- Simplicity signals: "like", "similar", "just" → bump down
- File count adjustment: 0-1 files → lower, 10+ → higher
- Manual override via bead state

**Where it's used:** Only in tiered brainstorming (choosing brainstorm depth). NOT used for phase skipping.

**Phase transition:** `_sprint_transition_table()` (lib-sprint.sh:393-406) is a strict linear chain — no skip paths. `sprint_advance()` follows this table exactly. To add skipping, either the table needs conditional branches or a new function needs to bypass phases.

**Sprint workflow (sprint skill, /clavain:sprint):** The sprint.md skill orchestrates phases sequentially. Phase skipping would need to happen at this level — checking complexity before invoking each phase's command.

## Design Space

### iv-ked1: Skill Budget Cap

**Option A: Hard character cap in Skill tool handler**
Claude Code's Skill tool loads SKILL.md content. Clavain can't modify the Skill tool itself (it's a Claude Code built-in). But Clavain *can* enforce caps at skill authoring time.

**Option B: Authoring-time validation + CI gate**
Add a check to plugin validation that warns when any SKILL.md exceeds 16K chars (~4K tokens). Skills exceeding the budget must either be trimmed or split into a compact entry point + references directory.

**Option C: SessionStart injection cap (for the hook-injected context)**
Cap the total `additionalContext` at 8K chars. If content exceeds, truncate with a "Run /clavain:using-clavain for full context" message.

**Option D: Hybrid — cap at injection + lint at authoring**
Cap `additionalContext` (Option C) AND lint skill sizes (Option B). The cap prevents runtime bloat; the lint prevents authoring bloat.

**Recommendation: Option D (hybrid).** The additionalContext cap catches runtime issues; the lint catches authoring issues before they reach users.

### iv-hyza: Summary-Mode Output Extraction

**Option A: Universal verdict header contract**
Define a structured header that ALL agent results must include:

```
STATUS: pass|fail|warn
FILES_CHANGED: path1, path2, ...
FINDINGS_COUNT: N
SUMMARY: 1-2 sentence verdict
DETAIL_PATH: /tmp/agent-detail-xxx.md
```

Orchestrator reads only the header (<500 chars). Full detail stays in the file at DETAIL_PATH, outside context.

**Option B: Extend Findings Index contract to Codex results**
Codex dispatch already supports `--output-last-message`. Add a requirement that dispatch.sh post-processes the output to extract a structured header. The raw output stays in the file; only the header enters orchestrator context.

**Option C: File indirection — never read agent output into context**
Instead of reading agent files, the orchestrator gets a manifest file listing all agent outputs with their headers. Only reads the manifest (~100 lines) instead of N full files.

**Option D: Summary-mode flag on dispatch**
Add a `--summary` flag to dispatch.sh that tells the Codex agent to produce a structured summary at the end of its output. The orchestrator reads only the last N lines (the summary).

**Recommendation: Option A + B combined.** Define the universal verdict header (Option A) and implement it for both flux-drive (extending the existing Findings Index) and Codex dispatch (post-processing in dispatch.sh). Option C (file indirection) is good for flux-drive synthesis but too heavy for single-agent Codex dispatches.

### iv-kmyj: Conditional Phase Skipping

**Option A: Complexity-gated phase table**
Extend `_sprint_transition_table()` to accept complexity as a parameter:
- Complexity 1 (trivial): brainstorm → executing (skip strategy, plan, review)
- Complexity 2 (simple): brainstorm → planned → executing (skip strategy, plan review)
- Complexity 3 (moderate): full chain
- Complexity 4-5 (complex/research): full chain

**Option B: Phase whitelist per complexity tier**
Instead of modifying the transition table, define a whitelist of required phases per tier:
- Tier 1: [executing, shipping, done]
- Tier 2: [planned, executing, shipping, done]
- Tier 3-5: [brainstorm, strategized, planned, plan-reviewed, executing, shipping, done]

Sprint workflow checks: "Is current phase in the whitelist? If not, skip to the next whitelisted phase."

**Option C: Score-based gating at each phase boundary**
Before each phase, evaluate a skip score:
- "Are requirements fully specified?" (yes → skip brainstorm)
- "Is there already a plan?" (yes → skip planning)
- "Is change localized to <3 files?" (yes → skip review)

Each check is a simple heuristic, not an LLM call.

**Option D: User confirmation at skip points**
When complexity suggests a phase can be skipped, ask the user: "Complexity 2 — skip strategy phase? [Y/n]"

**Recommendation: Option B + D combined.** Phase whitelist per tier is clean and doesn't require modifying the transition table. User confirmation at skip points prevents surprises. The existing complexity classifier feeds directly into tier selection.

## Integration Points

### Cross-Feature Dependencies

1. **Skill budget cap feeds into phase skipping:** If skills are capped, the per-phase injection cost is bounded. Phase skipping then compounds the savings — fewer phases × cheaper per-phase injection.

2. **Summary-mode feeds into phase skipping:** If agent results are summarized, the review phase is cheaper. This makes it safer to NOT skip the review phase for moderate tasks — the cost is lower anyway.

3. **All three feed into interstat reporting:** iv-dyyy (interstat scaffold) tracks per-session tokens. These three improvements establish the *floor* that interstat measures against.

### Files Modified

**iv-ked1:**
- `hub/clavain/hooks/session-start.sh` — add additionalContext cap
- `hub/clavain/scripts/validate-plugin.sh` (or new lint script) — skill size validation
- `hub/clavain/AGENTS.md` — document budget convention

**iv-hyza:**
- `hub/clavain/scripts/dispatch.sh` — post-process output for verdict header
- `plugins/interflux/skills/flux-drive/phases/shared-contracts.md` — extend contract
- `hub/clavain/skills/executing-plans/SKILL.md` — reference verdict extraction
- `hub/clavain/skills/interserve/SKILL.md` — update result reading instructions

**iv-kmyj:**
- `hub/clavain/hooks/lib-sprint.sh` — add phase whitelist function, modify sprint_advance
- Sprint skill (loaded by /clavain:sprint) — add complexity check before phase commands
- `hub/clavain/skills/executing-plans/SKILL.md` — reference skip behavior

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Budget cap truncates critical skill content | Agent misses instructions, produces wrong output | Cap at 16K chars (generous) + reference pattern for overflow content |
| Summary extraction loses important detail | Orchestrator misses nuance in agent findings | Keep full detail in file; summary is supplementary, not replacement |
| Phase skipping produces low-quality output | Shipped feature has bugs or missing architecture | Only skip for complexity 1-2; require user confirmation for skips |
| Complexity classifier miscategorizes tasks | Complex task treated as trivial, skips needed phases | User override via bead state; confirmation dialog as safety net |
| Breaking change to dispatch.sh output format | Existing scripts that parse output break | Verdict header is appended, not replacing existing format |

## Open Questions

1. **What's the right budget cap?** myclaude uses 16K chars (~4K tokens). Our largest skill is 18.6KB. Should we match myclaude (forcing a trim of writing-skills) or set at 20K (grandfathering everything)?

2. **Should additionalContext have a separate cap from per-skill caps?** SessionStart injection is different from Skill-time injection — different budget makes sense.

3. **Should phase skipping be opt-in or opt-out?** Opt-in (user must enable) is safer but reduces adoption. Opt-out (enabled by default, user can force full chain) maximizes savings.

4. **Should the verdict header include a confidence score?** "CONFIDENCE: high|medium|low" would let the orchestrator decide whether to read the full detail.

5. **How to handle mid-sprint complexity changes?** A task that starts simple may become complex during execution. Should complexity re-evaluation happen between phases?

## Deliverables

### iv-ked1 (Skill Budget Cap)
1. `additionalContext` cap in session-start.sh (8K chars)
2. Skill size lint function (warn at 16K, error at 32K)
3. Integration into `/clavain:doctor` health check
4. Trim writing-skills SKILL.md if it exceeds cap (move detail to references/)

### iv-hyza (Summary-Mode Output Extraction)
1. Universal verdict header specification (STATUS, FILES_CHANGED, FINDINGS_COUNT, SUMMARY)
2. dispatch.sh `--summary` post-processing
3. Flux-drive Findings Index extension with verdict header
4. Executing-plans skill update for verdict-first reading

### iv-kmyj (Conditional Phase Skipping)
1. Phase whitelist per complexity tier (in lib-sprint.sh)
2. `sprint_skip_to_next()` function that advances past non-whitelisted phases
3. User confirmation dialog at skip points
4. Sprint skill update to check whitelist before each phase invocation
