# Context Briefing: Plugin Modularity vs Consolidation

## The System

Demarch is a monorepo for an autonomous software development agency platform. The **Interverse** is its plugin ecosystem — currently 49 plugins across 5 pillars and 3 layers.

Architecture:
- Each plugin is its own git repo (separate origin, separate version)
- Each has: `.claude-plugin/plugin.json`, skills/, optional MCP servers, CLAUDE.md, AGENTS.md
- The monorepo root (`Demarch/`) contains all pillars: `interverse/` (plugins), `os/clavain/` (orchestrator), `core/` (kernel), `apps/` (applications), `sdk/` (shared)
- `interverse/` is gitignored in the monorepo — each plugin is independently version-controlled
- The developer always works from the monorepo root, so co-location is the lived experience even though repos are physically separate

## The Plugin Taxonomy (as articulated by the architect)

**Capability plugins** — do something novel:
- interflux: multi-agent code review
- intermonk: Hegelian dialectic reasoning
- interskill: skill authoring toolkit
- interwatch: documentation drift detection
- tldr-swinton: token-efficient code reconnaissance
- interstat: token usage analytics

**Routing/glue plugins** — connect things, coordinate, generate artifacts from state:
- interlock: multi-agent file coordination
- interpath: artifact generation (roadmaps, PRDs, changelogs from beads)
- intermap: code structure and impact analysis
- intermux: multi-agent session monitoring
- interserve: Codex delegation and section extraction
- intercache: semantic caching layer

The architect suspects routing plugins should be "abstracted up a layer with other plugins that do similar things."

## Pain Points (all four acknowledged)

1. **Cross-plugin changes:** A single feature often touches 3-4 plugins. Coordinating versions, testing, and deploying is a tax.
2. **Discovery & onboarding:** Hard to find what exists. New functionality gets built because nobody knew plugin X already did it.
3. **Publish & version overhead:** Bumping versions, publishing, keeping marketplace entries in sync — constant ceremony per-plugin.
4. **Context loading cost:** Each plugin has its own CLAUDE.md, AGENTS.md, SKILL.md chain. Agents spend tokens loading docs for 5 plugins to do one task.

## Key Beliefs

- Fine-grained modularity is correct — the current split reflects real conceptual boundaries
- Physical separation (separate repos) IS what enforces conceptual separation — they are inseparable
- The pain points are tooling problems, not architecture problems
- Would be falsified by: evidence of >30% token waste on loading overhead, OR evidence that cross-plugin features take 3x longer than intra-plugin changes

## Hidden Factor

The architect never experiences repo separation as friction because the monorepo co-locates everything. The "physical separation" is enforced through git (separate origins, separate versions) but the working directory is always unified. This means the architect's experience of "modularity works fine" may be conditional on the monorepo context — it might break down for external contributors, CI/CD systems, or agents that don't share the monorepo working directory.

## Scale Context

- 49 plugins currently, growing
- ~14 skills with SKILL-compact.md files (token optimization for loading)
- Token efficiency is a first-class concern (interstat tracks consumption, gen-skill-compact.sh reduces loading cost)
- The system is primarily consumed by AI agents, not human developers
