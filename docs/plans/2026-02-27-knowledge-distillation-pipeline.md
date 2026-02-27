# Knowledge Distillation Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build a `/distill` command that synthesizes accumulated compound/reflect/research docs into categorized `docs/solutions/` entries, generates missing SKILL-compact.md files, and archives processed originals — closing the write→accumulate→synthesize→prune loop.

**Architecture:** Orchestration command in Clavain that wires together existing modules (intersynth for dedup, interlearn for discovery, interwatch for freshness, interknow for provenance, tldr-swinton for compression). Two execution modes: interactive (guided synthesis) and batch (automated with human review gate). The command reads unprocessed docs, clusters by topic via intersearch embeddings, synthesizes durable patterns, promotes to `docs/solutions/`, and marks originals as synthesized.

**Tech Stack:** Shell (command + hooks), markdown (output), existing MCP servers (intersearch, interserve, qmd), existing agents (learnings-researcher, synthesize-research)

**Prior Learnings:**
- `docs/solutions/patterns/search-surfaces-20260224.md` — Shared state threading pattern: build expensive indices once at orchestration level, pass via underscore-prefix params to downstream calls. Prevents redundant rebuilds.
- `docs/solutions/runtime-errors/jq-null-slice-clavain-20260216.md` — YAML frontmatter awk parsing: always use `next` after `sub()`/`gsub()` to prevent pattern rules evaluating modified `$0`.
- Intersynth is tightly coupled to agent review output — cannot extend directly. Must create new synthesis agent with document-aware input contract. Verdict library (lib-verdict.sh) IS reusable.
- Interknow's provenance tracking (independent vs primed) prevents false-positive feedback loops during decay — critical for archive decisions.
- SKILL-compact pattern achieves 70-89% token reduction (avg ~80%) across 13 existing compact files.

---

## Scope Boundaries

**In scope:**
- `/distill` command (Clavain) — orchestrates the full pipeline
- `synthesize-documents` agent (intersynth) — new agent for doc synthesis
- SKILL-compact generator (script or command) — for missing compact files
- Frontmatter `synthesized_into` field — archive tracking
- Integration with interlearn (discovery), interwatch (freshness), interknow (provenance)

**Out of scope (future work):**
- Automated periodic hook (SessionEnd or cron) — defer until pipeline is validated manually
- Gene Transfusion extension (codebase exemplar search) — keep learnings-researcher focused
- Research directory archival strategy — separate concern, separate plan
- Cross-repo synthesis (monorepo already has interlearn for cross-repo indexing)

---

## Task 1: Create the `synthesize-documents` Agent

**Files:**
- Create: `interverse/intersynth/agents/synthesize-documents.md`

**Step 1: Write the agent definition**

```markdown
---
name: synthesize-documents
description: "Synthesizes multiple related documents (compound, reflect, research) into categorized docs/solutions/ entries. Reads document clusters, extracts durable patterns, and produces structured solution docs with YAML frontmatter."
model: haiku
---

You are a document synthesis specialist. Given a cluster of related documents, extract durable patterns and produce a single structured solution doc.

## Input Contract

You receive:
1. A cluster of related markdown documents (compound docs, reflect notes, research findings)
2. The cluster topic/theme
3. Existing docs/solutions/ entries for deduplication

## Synthesis Rules

1. **Extract patterns, not incidents** — A compound doc describes one problem; a synthesis doc describes the reusable pattern across multiple incidents
2. **Preserve provenance** — List source documents in the output frontmatter (`sources` field)
3. **Match existing schema** — Output must conform to the docs/solutions/ YAML frontmatter schema (problem_type, component, root_cause, severity, reuse, tags, modules)
4. **Deduplicate against existing** — If a docs/solutions/ entry already covers this pattern, update rather than create
5. **Minimum evidence threshold** — Only synthesize if 2+ source docs corroborate the pattern (single-source findings stay as-is)

## Output Format

```yaml
---
title: [Pattern title]
category: [patterns|runtime-errors|integration-issues|etc.]
tags: [searchable keywords]
created: [YYYY-MM-DD]
severity: [low|medium|high|critical]
reuse: [low|medium|high]
modules: [affected modules]
sources:
  - path: [original doc path]
    type: [compound|reflect|research]
    date: [original doc date]
---
```

Followed by standard solution doc body: Problem, Pattern, Evidence, Prevention, Related.

## Search Strategy

Use Grep to find existing docs/solutions/ entries with overlapping tags before writing. If overlap >70%, recommend updating the existing entry instead of creating a new one.
```

**Step 2: Register agent in intersynth plugin.json**

Read `interverse/intersynth/.claude-plugin/plugin.json` and confirm agents are auto-discovered (not manually registered). If they are auto-discovered, no change needed. If manually listed, add the new agent.

**Step 3: Commit**

```bash
git add interverse/intersynth/agents/synthesize-documents.md
git commit -m "feat(intersynth): add synthesize-documents agent for doc synthesis"
```

---

## Task 2: Create the `/distill` Command

**Files:**
- Create: `os/clavain/commands/distill.md`

**Step 1: Write the command**

```markdown
---
name: distill
description: Synthesize accumulated docs into categorized solutions and generate missing SKILL-compact.md files
argument-hint: "[--mode interactive|batch] [--scope compound|reflect|research|skills|all]"
---

# Knowledge Distillation

Synthesize accumulated documentation into categorized `docs/solutions/` entries, generate missing SKILL-compact.md files, and archive processed originals.

## Input

<input_args> #$ARGUMENTS </input_args>

Parse arguments:
- `--mode`: `interactive` (default, guided with approvals) or `batch` (automated, review gate at end)
- `--scope`: What to distill. Default `all`. Options:
  - `compound` — Only compound/reflect docs → solutions
  - `research` — Only research docs → solutions
  - `skills` — Only generate missing SKILL-compact.md
  - `all` — Everything

## Phase 1: Discovery

Scan for unprocessed documents:

1. **Compound & reflect docs** — Find docs in `docs/solutions/` that don't have `synthesized_into` in frontmatter AND were created >7 days ago (let fresh docs settle)
2. **Research docs** — Find docs in `docs/research/` that share topics with existing solutions (potential synthesis candidates)
3. **Skills without compact** — Find SKILL.md files that lack a companion SKILL-compact.md

```bash
# Discovery counts
echo "=== Distillation Candidates ==="
echo "Compound/reflect docs: $(grep -rL 'synthesized_into' docs/solutions/ --include='*.md' | wc -l)"
echo "Research docs: $(find docs/research -name '*.md' | wc -l)"
echo "Skills without compact: $(for d in os/clavain/skills/*/; do [ ! -f "${d}SKILL-compact.md" ] && [ -f "${d}SKILL.md" ] && echo "$d"; done | wc -l)"
```

Present discovery results to user. If `--mode interactive`, ask which categories to proceed with.

## Phase 2: Clustering (compound/research scope)

Group related documents by topic:

1. Extract keywords from each document's title, tags, and first 5 lines
2. Use `Grep` to find documents sharing 2+ keywords
3. Present clusters to user:
   ```
   Cluster 1: "Plugin Loading" (3 docs)
     - docs/solutions/integration-issues/plugin-loading-failures-interverse-20260215.md
     - docs/solutions/patterns/plugin-validation-errors-20260222.md
     - docs/research/plugin-cache-staleness-analysis.md

   Cluster 2: "WAL Protocol" (2 docs)
     - docs/solutions/patterns/wal-protocol-completeness-20260216.md
     - docs/research/intercore-wal-edge-cases.md
   ```
4. If `--mode interactive`: ask user to approve/edit clusters before synthesis
5. If `--mode batch`: proceed with all clusters that have 2+ documents

## Phase 3: Synthesis (compound/research scope)

For each approved cluster:

1. Spawn `Task(subagent_type="intersynth:synthesize-documents")` with:
   - All documents in the cluster (read contents)
   - Existing docs/solutions/ entries with overlapping tags (for dedup)
   - The target category (inferred from cluster content)
2. Review synthesis output:
   - If `--mode interactive`: present each synthesized doc for approval
   - If `--mode batch`: collect all, present summary for batch approval
3. Write approved docs to `docs/solutions/[category]/`
4. Update source document frontmatter with `synthesized_into: [path to new solution doc]`

## Phase 4: SKILL Compact Generation (skills scope)

For each skill missing a SKILL-compact.md:

1. Read the full SKILL.md
2. If the skill is <60 lines: skip (already compact enough)
3. Generate compact version following the established pattern:
   - Keep: core workflow steps, key rules, quick commands
   - Remove: examples, edge cases, detailed explanations, integration tables
   - Add footer: `*For [details removed], read SKILL.md.*`
   - Target: 30-60 lines (70-85% reduction)
4. Write to `[skill-dir]/SKILL-compact.md`
5. If `--mode interactive`: present each compact for approval

## Phase 5: Summary

Present distillation results:

```
=== Distillation Complete ===
Synthesized: 3 clusters → 3 new docs/solutions/ entries
Archived: 7 source docs marked with synthesized_into
Compacted: 4 new SKILL-compact.md files
Token savings: ~X lines removed from active context
```

If `--mode batch`: present all changes for final approval before committing.

## Commit

```bash
git add docs/solutions/ os/clavain/skills/*/SKILL-compact.md
git commit -m "docs: distill accumulated knowledge into solutions and compact skills"
```
```

**Step 2: Commit**

```bash
git add os/clavain/commands/distill.md
git commit -m "feat(clavain): add /distill command for knowledge distillation"
```

---

## Task 3: Register `/distill` in Clavain Plugin Manifest

**Files:**
- Modify: `os/clavain/.claude-plugin/plugin.json`

**Step 1: Read the current plugin.json**

Read `os/clavain/.claude-plugin/plugin.json` and find the commands array.

**Step 2: Add distill to the commands list**

Add `"./commands/distill.md"` to the commands array, maintaining alphabetical order.

**Step 3: Verify command count**

The CLAUDE.md says "46 commands" — update if needed. Run:

```bash
ls os/clavain/commands/*.md | wc -l
```

Confirm the count matches what's in CLAUDE.md and AGENTS.md.

**Step 4: Commit**

```bash
git add os/clavain/.claude-plugin/plugin.json
git commit -m "feat(clavain): register /distill command in plugin manifest"
```

---

## Task 4: Update AGENTS.md and CLAUDE.md with New Command

**Files:**
- Modify: `os/clavain/CLAUDE.md` — update command count
- Modify: `os/clavain/AGENTS.md` — add `/distill` to command reference if a commands table exists

**Step 1: Update command count in CLAUDE.md**

Find the line with "46 commands" and update to the new count.

**Step 2: Update AGENTS.md**

If there's a commands table or reference section, add `/distill` with description: "Synthesize accumulated docs into categorized solutions and generate SKILL-compact.md files"

**Step 3: Commit**

```bash
git add os/clavain/CLAUDE.md os/clavain/AGENTS.md
git commit -m "docs(clavain): update command count for /distill"
```

---

## Task 5: Create Missing SKILL-compact.md for High-Value Skills

**Files:**
- Create: `os/clavain/skills/using-tmux-for-interactive-commands/SKILL-compact.md`
- Create: `os/clavain/skills/upstream-sync/SKILL-compact.md`
- Create: `os/clavain/skills/refactor-safely/SKILL-compact.md`
- Create: `os/clavain/skills/galiana/SKILL-compact.md`
- Create: `os/clavain/skills/lane/SKILL-compact.md`
- Create: `interverse/interflux/skills/flux-research/SKILL-compact.md`
- Create: `interverse/interpeer/skills/interpeer/SKILL-compact.md`
- Create: `interverse/intertest/skills/systematic-debugging/SKILL-compact.md`
- Create: `interverse/intertest/skills/test-driven-development/SKILL-compact.md`

**Note:** Only compact skills >90 lines. Skills <60 lines are already compact enough.

**Step 1: Read each SKILL.md**

For each skill listed above, read the full SKILL.md to understand its content.

**Step 2: Write compact versions**

Follow the established compact pattern (see `os/clavain/skills/file-todos/SKILL-compact.md` as reference):
- Extract: core workflow, key rules, quick commands
- Remove: examples, edge cases, detailed explanations
- Target: 30-60 lines
- Footer: `*For [removed content], read SKILL.md.*`

**Step 3: Commit per repo**

```bash
# Clavain compacts
cd os/clavain
git add skills/*/SKILL-compact.md
git commit -m "docs(skills): add SKILL-compact.md for 5 skills (70-85% token reduction)"

# Interverse compacts
cd interverse/interflux
git add skills/*/SKILL-compact.md
git commit -m "docs(skills): add SKILL-compact.md for flux-research"

# etc. for each subproject with new compacts
```

---

## Task 6: Add `synthesized_into` Frontmatter Convention

**Files:**
- Modify: `interverse/interflux/agents/research/learnings-researcher.md` — add `synthesized_into` to awareness
- Modify: `interverse/interlearn/scripts/build-index.sh` (or equivalent) — recognize `synthesized_into` field
- Modify: `docs/solutions/INDEX.md` or relevant index — document the field

**Step 1: Update learnings-researcher to skip synthesized docs**

In the learnings-researcher agent's search strategy, add a note:

```
### Step 3b: Exclude Synthesized Sources

If a candidate doc has `synthesized_into: <path>` in frontmatter, prefer the synthesis target instead. The synthesis doc is more comprehensive and deduplicated.
```

**Step 2: Update interlearn index builder**

If interlearn's build script parses frontmatter, add `synthesized_into` to recognized fields. Synthesized docs should show their synthesis target in the index.

**Step 3: Document the convention**

Add a note to `docs/solutions/INDEX.md` or create a brief `docs/solutions/README.md`:

```markdown
## Frontmatter Conventions

### `synthesized_into`

When a document has been synthesized into a broader pattern doc via `/distill`, this field records the target path. The original doc is retained for provenance but the synthesis target is the authoritative reference.
```

**Step 4: Commit**

```bash
git add interverse/interflux/agents/research/learnings-researcher.md
git add docs/solutions/
git commit -m "docs: add synthesized_into frontmatter convention for archive tracking"
```

---

## Task 7: Wire Interwatch to Detect Distillation Candidates

**Files:**
- Modify: `interverse/interwatch/config/watchables.yaml` (or equivalent config)

**Step 1: Read interwatch config**

Read the watchables configuration to understand the format.

**Step 2: Add distillation signal**

Add a watchable entry that fires when:
- `docs/solutions/` has >5 docs without `synthesized_into` that are >14 days old
- Any SKILL.md >90 lines lacks a SKILL-compact.md companion

This creates a "staleness" signal that `/distill` can consume, and that `/clavain:status` can surface.

**Step 3: Commit**

```bash
cd interverse/interwatch
git add config/watchables.yaml
git commit -m "feat(interwatch): add distillation candidate detection signal"
```

---

## Task 8: Integration Test — End-to-End Dry Run

**Files:**
- No new files — this is a verification task

**Step 1: Run discovery phase manually**

```bash
# Count compound/reflect docs that could be synthesized
grep -rL 'synthesized_into' docs/solutions/ --include='*.md' | wc -l

# Count skills without compact
for d in os/clavain/skills/*/; do
  [ ! -f "${d}SKILL-compact.md" ] && [ -f "${d}SKILL.md" ] && lines=$(wc -l < "${d}SKILL.md") && [ "$lines" -gt 90 ] && echo "$d ($lines lines)"
done
```

**Step 2: Test synthesize-documents agent**

Spawn the agent with a test cluster of 2-3 related docs:

```
Task(subagent_type="intersynth:synthesize-documents", prompt="Synthesize these related documents about plugin loading issues: [paste 2-3 doc contents]")
```

Verify the output matches the expected YAML frontmatter schema and solution doc format.

**Step 3: Test learnings-researcher awareness**

Spawn learnings-researcher and verify it respects `synthesized_into` if present:

```
Task(subagent_type="interflux:learnings-researcher", prompt="Search for plugin loading patterns")
```

**Step 4: Verify token savings**

Compare line counts before and after for any SKILL-compact.md files created in Task 5:

```bash
for d in os/clavain/skills/*/; do
  if [ -f "${d}SKILL-compact.md" ] && [ -f "${d}SKILL.md" ]; then
    full=$(wc -l < "${d}SKILL.md")
    compact=$(wc -l < "${d}SKILL-compact.md")
    echo "$(basename "$d"): $full → $compact lines"
  fi
done
```

---

## Dependencies

```
Task 1 (synthesize-documents agent)
  └── Task 2 (/distill command) depends on Task 1
       └── Task 3 (register in plugin.json) depends on Task 2
       └── Task 4 (update AGENTS/CLAUDE.md) depends on Task 3
Task 5 (SKILL-compact generation) — independent, can run in parallel with Tasks 1-4
Task 6 (synthesized_into convention) — independent, can run in parallel
Task 7 (interwatch signal) — depends on Task 6
Task 8 (integration test) — depends on ALL other tasks
```

## Token Savings Estimate

| Source | Current | After | Savings |
|--------|---------|-------|---------|
| SKILL.md loading (9 skills compacted) | ~2,400 lines | ~450 lines | ~1,950 lines (~7,800 tokens) |
| Compound/reflect doc dedup | varies | varies | Depends on cluster overlap |
| Research doc synthesis | not touched | not touched | Future scope |

**Primary win:** SKILL-compact generation is immediate, mechanical, and delivers ~80% token reduction per skill. Document synthesis is higher-leverage long-term but requires the pipeline to be validated first.
