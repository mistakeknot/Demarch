---
name: interflux
description: "Multi-agent review and research with scored triage, domain detection, content slicing, intermediate finding sharing, and knowledge injection. 17 agents (12 review + 5 research), 4 commands, 2 skills, 2 MCP servers. Companion plugin for Clavain."
---
# Gemini Skill: interflux

You have activated the interflux capability.

## Base Instructions
# interflux — Development Guide

Multi-agent review and research engine for Claude Code. Companion plugin for [Clavain](https://github.com/mistakeknot/Clavain).

## Quick Reference

| Item | Value |
|------|-------|
| Repo | `https://github.com/mistakeknot/interflux` |
| Namespace | `interflux:` |
| Manifest | `.claude-plugin/plugin.json` |
| Components | 17 agents (12 review + 5 research), 4 commands, 2 skills, 2 MCP servers, 1 hook |
| License | MIT |

### Release workflow

- Run `scripts/bump-version.sh <version>` (or `/interpub:release <version>` in Claude Code) for any released changes.
- It updates `.claude-plugin/plugin.json`, `infra/marketplace/.claude-plugin/marketplace.json`, and discovered versioned artifacts.
- The command commits and pushes both plugin and marketplace repos atomically.
- Use patch bumps for routine user-facing updates (`0.2.x -> 0.2.x+1`).

## Architecture

```
interflux/
├── .claude-plugin/
│   ├── plugin.json                # Plugin manifest (name, version, MCP servers)
│   └── integration.json           # Ecosystem integration manifest (dual-mode)
├── agents/
│   ├── review/                    # 8 review agents (7 technical + 1 cognitive)
│   │   ├── fd-architecture.md
│   │   ├── fd-correctness.md
│   │   ├── fd-game-design.md
│   │   ├── fd-performance.md
│   │   ├── fd-quality.md
│   │   ├── fd-safety.md
│   │   ├── fd-systems.md           # Cognitive: systems thinking blind spots
│   │   ├── fd-user-product.md
│   │   └── references/           # Shared reference material (not agents)
│   │       └── concurrency-patterns.md
│   └── research/                  # 5 research agents
│       ├── best-practices-researcher.md
│       ├── framework-docs-researcher.md
│       ├── git-history-analyzer.md
│       ├── learnings-researcher.md
│       └── repo-research-analyst.md
├── commands/                      # 3 slash commands
│   ├── flux-drive.md              # /interflux:flux-drive — multi-agent review
│   ├── flux-gen.md                # /interflux:flux-gen — generate project-specific agents
│   └── flux-research.md           # /interflux:flux-research — multi-agent research
├── skills/
│   ├── flux-drive/                # Review orchestration skill
│   │   ├── SKILL.md               # Entry point — triage, scoring, dispatch
│   │   ├── phases/                # Phase-specific instructions
│   │   │   ├── launch.md          # Stage 1/2 dispatch, expansion decision
│   │   │   ├── launch-codex.md    # Codex delegation variant
│   │   │   ├── cross-ai.md        # Oracle/Codex cross-AI dispatch
│   │   │   ├── shared-contracts.md # Completion signal, findings index format
│   │   │   ├── slicing.md         # Content routing for large inputs
│   │   │   └── synthesize.md      # Findings aggregation, verdict
│   │   └── references/
│   │       ├── agent-roster.md    # Agent metadata and invocation guide
│   │       └── scoring-examples.md # Worked triage scoring examples
│   └── flux-research/
│       └── SKILL.md               # Research orchestration — triage, dispatch, synthesize
├── config/
│   └── flux-drive/
│       ├── domains/               # 11 domain detection profiles
│       │   ├── index.yaml         # Detection signals and scoring weights
│       │   ├── web-api.md
│       │   ├── cli-tool.md
│       │   ├── tui-app.md
│       │   ├── game-simulation.md
│       │   ├── data-pipeline.md
│       │   ├── claude-code-plugin.md
│       │   ├── library-sdk.md
│       │   ├── desktop-tauri.md
│       │   ├── mobile-app.md
│       │   ├── embedded-systems.md
│       │   └── ml-pipeline.md
│       └── knowledge/            # Durable review patterns (knowledge lifecycle)
│           ├── README.md
│           └── *.md              # Individual knowledge entries
├── hooks/
│   ├── hooks.json                 # Hook declarations (SessionStart)
│   ├── interbase-stub.sh          # SDK stub — sources live or falls back to no-ops
│   └── session-start.sh           # Sources interbase, emits ecosystem status
├── docs/
│   └── spec/                     # flux-drive protocol specification (v1.0.0)
│       ├── README.md             # Conformance levels, reading order
│       ├── core/                 # Required protocol documents
│       │   ├── protocol.md       # 3-phase lifecycle
│       │   ├── scoring.md        # Agent selection algorithm
│       │   ├── staging.md        # Stage expansion logic
│       │   └── synthesis.md      # Findings aggregation
│       ├── contracts/            # Required interface contracts
│       │   ├── findings-index.md # Agent output format
│       │   └── completion-signal.md # Agent completion protocol
│       └── extensions/           # Optional enhancements
│           ├── domain-detection.md # Weighted signal scoring
│           └── knowledge-lifecycle.md # Review memory with decay
├── scripts/
│   ├── content-hash.py            # Deterministic content hash for cache staleness
│   ├── generate-agents.py         # Deterministic agent file generation from domain profiles
│   ├── update-domain-profiles.py  # Regenerate domain profiles
│   └── validate-roster.sh        # Validate agent roster consistency
└── tests/
    └── structural/               # 120 pytest tests
        ├── conftest.py
        ├── helpers.py
        ├── test_agents.py
        ├── test_commands.py
        ├── test_content_hash.py       # Tests for content hash helper
        ├── test_generate_agents.py  # 23 tests for agent file generation
        ├── test_namespace.py      # Guards against stale clavain: refs
        ├── test_skills.py
        └── test_slicing.py
```

## How It Works

### flux-drive (Review Orchestration)

Three-phase protocol: **Triage** → **Launch** → **Synthesize**.

1. **Triage** — Detect project domains, profile input, score agents (base_score 0-3 + domain_boost 0-2 + project_bonus 0-1 + domain_agent 0-1), present roster for user approval
2. **Launch** — Dispatch Stage 1 agents in parallel, monitor completion, optionally expand to Stage 2 based on findings severity + adjacency scoring
3. **Synthesize** — Validate outputs, deduplicate findings, track convergence, compute verdict (safe/needs-changes/risky), generate findings.json + summary.md

See `docs/spec/README.md` for the full protocol specification.

### flux-research (Research Orchestration)

Three-phase protocol: **Triage** → **Launch** → **Synthesize**.

Uses a query-type affinity table to select research agents, dispatches in parallel, and synthesizes answers with source attribution. Progressive enhancement: uses Exa MCP for external research when available, falls back to Context7 + WebSearch.

### Domain Detection

LLM-based classification — a Haiku subagent reads README + build files + key source files and classifies the project into 11 known domains. Cached in `.claude/flux-drive.yaml` with `content_hash` for staleness detection. Staleness computed deterministically by `scripts/content-hash.py`.

11 domains defined in `config/flux-drive/domains/`. Each domain profile contains review criteria, agent specs, and Research Directives for external research agents.

### Agent Generation

`scripts/generate-agents.py` reads cached domain classification + domain profile markdown → writes `.claude/agents/fd-*.md` files. Deterministic template expansion (no LLM involvement). Three modes: `skip-existing`, `regenerate-stale` (checks `flux_gen_version` in frontmatter), `force`.

### Knowledge Lifecycle

Durable patterns from past reviews, stored in `config/flux-drive/knowledge/`:
- **Provenance tracking** — `independent` (re-discovered without prompting) vs `primed` (re-confirmed while in context)
- **Temporal decay** — entries not independently confirmed in 10 reviews are archived
- **Injection** — top 5 relevant entries injected into agent prompts via semantic search (qmd)

## Intermediate Finding Sharing

During parallel flux-drive reviews, agents can share high-severity findings via `{OUTPUT_DIR}/peer-findings.jsonl`.

**Severity levels:**
- `blocking` — contradicts another agent's analysis (MUST acknowledge)
- `notable` — significant finding that may affect others (SHOULD consider)

**Helper script:** `scripts/findings-helper.sh`
- `write <file> <severity> <agent> <category> <summary> [file_refs...]`
- `read <file> [--severity blocking|notable|all]`

**Timeline in synthesis:** The synthesis agent reads the findings timeline for convergence tracking and contradiction detection.

**Command:** `/interflux:fetch-findings <output_dir> [--severity ...]` — inspect shared findings.

## MCP Servers

| Server | Type | Purpose |
|--------|------|---------|
| **qmd** | stdio | Semantic search for project documentation. Used for knowledge injection and doc retrieval. |
| **exa** | stdio | External web research via Exa API. Progressive enhancement — requires `EXA_API_KEY`. Falls back to Context7 + WebSearch if unavailable. |

## Protocol Specification

The flux-drive review protocol is formally specified in `docs/spec/` (flux-drive-spec 1.0.0). The spec extracts the abstract protocol from this reference implementation into standalone, framework-agnostic documents.

Three conformance levels:
- **Core** — 3-phase lifecycle, base scoring (0-4), staging, contracts, synthesis
- **Core + Domains** — adds domain detection, domain_boost/domain_agent_bonus scoring (0-7)
- **Core + Knowledge** — adds provenance-tracked review memory with temporal decay

See `docs/spec/README.md` for the full document index and reading order.

## Component Conventions

### Review Agents (fd-*)

- 8 agents: 7 technical (auto-detect language) + 1 cognitive (fd-systems, documents only)
- YAML frontmatter: `name`, `description` (with `<example>` blocks), `model: sonnet`
- Each reads project CLAUDE.md/AGENTS.md for codebase-aware review
- Findings output uses the Findings Index contract: `SEVERITY | ID | "Section" | Title`
- Verdict: `safe | needs-changes | risky`
- **Cognitive agents** (fd-systems) are pre-filtered: only activate for `.md`/`.txt` document reviews (PRDs, brainstorms, plans, strategy docs), never for code or diffs. Use cognitive severity mapping: Blind Spot → P1, Missed Lens → P2, Consider Also → P3

### Research Agents

- 5 agents for different research tasks (best practices, framework docs, git history, learnings, repo analysis)
- Orchestrated by flux-research skill, not invoked directly
- Research Directives in domain profiles guide their search terms

### Commands

| Command | Description |
|---------|-------------|
| `/interflux:flux-drive` | Multi-agent document/code review |
| `/interflux:flux-research` | Multi-agent research with source attribution |
| `/interflux:flux-gen` | Generate project-specific review agents from detected domains |
| `/interflux:fetch-findings` | Inspect shared findings from parallel reviews |

## Testing

```bash
# Run all structural tests (103 tests)
cd /root/projects/Interverse/plugins/interflux && uv run pytest tests/ -q

# Key test suites
uv run pytest tests/structural/test_namespace.py -v  # Guards against stale clavain: refs
uv run pytest tests/structural/test_agents.py -v     # Agent structure validation
uv run pytest tests/structural/test_skills.py -v     # Skill structure validation
uv run pytest tests/structural/test_slicing.py -v    # Content routing tests
```

## Validation Checklist

```bash
# Count components
ls agents/review/*.md | wc -l         # Should be 8
ls agents/research/*.md | wc -l       # Should be 5
ls commands/*.md | wc -l              # Should be 3
ls skills/*/SKILL.md | wc -l          # Should be 2

# Domain profiles
grep -l '## Research Directives' config/flux-drive/domains/*.md | wc -l  # Should be 11

# Manifest
python3 -c "import json; d=json.load(open('.claude-plugin/plugin.json')); print(list(d['mcpServers'].keys()))"  # ['qmd', 'exa']

# Namespace check — no stale clavain: references
uv run pytest tests/structural/test_namespace.py -v
```

## Measurement Definitions

Standard definitions for token metrics used across interflux and companion plugins.

### Token Types
| Type | Field | Description |
|------|-------|-------------|
| Input | `input_tokens` | Tokens sent to the model (prompt + system + tool results) |
| Output | `output_tokens` | Tokens generated by the model |
| Cache Read | `cache_read_tokens` | Previously cached input tokens reused (free for billing) |
| Cache Creation | `cache_creation_tokens` | New tokens added to cache this turn |
| Total | `total_tokens` | All tokens (input + output + cache_read + cache_creation) |

### Cost Types
| Type | Formula | Use For |
|------|---------|---------|
| Billing tokens | `input_tokens + output_tokens` | Cost estimation, budget enforcement |
| Effective context | `input_tokens + cache_read_tokens + cache_creation_tokens` | Context window decisions |

**Critical:** Billing tokens and effective context can differ by 600x+ due to cache hits being free for billing but consuming context. Budget caps use billing tokens (what costs money). Context overflow checks use effective context (what fits in the window).

### Scopes
| Scope | Granularity | Source |
|-------|-------------|--------|
| Per-agent | Single Task dispatch | interstat `agent_runs` table |
| Per-invocation | All agents in one flux-drive run | interstat `v_invocation_summary` |
| Per-session | All tokens in a Claude Code session | Session JSONL |
| Per-sprint | All sessions in a Clavain sprint | Future: interbudget |

### Budget Configuration
See `config/flux-drive/budget.yaml` for token budgets per review type, per-agent defaults, slicing multipliers, and enforcement mode.

## Dual-Mode Architecture

interflux supports both standalone (Claude Code marketplace) and integrated (Interverse ecosystem) operation via the interbase SDK.

### Files
- `hooks/interbase-stub.sh` — sources live SDK or falls back to inline no-ops
- `hooks/session-start.sh` — sources stub, emits ecosystem status
- `hooks/hooks.json` — registers SessionStart hook
- `.claude-plugin/integration.json` — declares standalone/integrated feature surface

### How It Works
- **Standalone**: User installs interflux from marketplace. Stub falls back to no-ops. All review/research features work. No ecosystem features (phase tracking, nudges, sprint gates).
- **Integrated**: User has `~/.intermod/interbase/interbase.sh` installed. Stub sources the live SDK. Session-start hook reports `[interverse] beads=... | ic=...`. Nudge protocol suggests missing companions.

### Testing
```bash
# Standalone (no ecosystem)
INTERMOD_LIB=/nonexistent bash hooks/session-start.sh 2>&1
# Expected: no output

# Integrated (with ecosystem)
bash hooks/session-start.sh 2>&1
# Expected: [interverse] beads=active | ic=...
```

## Known Constraints

- **No build step** — pure markdown/JSON/Python/bash plugin
- **Phase tracking is caller's responsibility** — interflux commands do not source lib-gates.sh; Clavain's lfg pipeline handles phase transitions
- **Exa requires API key** — set `EXA_API_KEY` env var; agents degrade gracefully without it
- **qmd must be installed** — semantic search used for knowledge injection; if unavailable, reviews run without knowledge context


