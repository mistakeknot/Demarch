# Project Onboard Skill Brainstorm

**Date:** 2026-03-03
**Status:** Brainstorm complete — ready for strategy

## What We're Building

A Clavain skill called `project-onboard` that makes any project "fully operational" in the Demarch ecosystem. It handles both greenfield repos and existing projects by introspecting first, then filling gaps. The goal: run one command and get the same level of automation, workflow, and self-improvement that Demarch has.

## How It Works

### Phase 1: Introspect

Scan the project to detect what already exists:
- Git repo? Remote? Branch structure?
- CLAUDE.md / AGENTS.md / PHILOSOPHY.md?
- .beads/ directory and database?
- .clavain/ memory scaffold?
- docs/ structure (and which subdirs)?
- .interwatch/ drift detection?
- Languages, frameworks, project type (from files)
- Project name (from git remote, directory name, or package.json/Cargo.toml/go.mod)

Report a checklist: ✔ exists / ✖ missing for each component.

### Phase 2: Guided Interview (with smart defaults)

Ask questions only for what can't be inferred. Smart defaults from repo scan.

Core questions (skip if answerable from repo):
1. **Project description** — name + one-liner (default: inferred from README or repo name)
2. **Languages/frameworks** — (default: detected from file extensions)
3. **Project type** — library / app / monorepo / plugin (default: inferred from structure)
4. **Key goals** — what are you building toward in the next month?

### Phase 3: Scaffold Infrastructure

Create everything that's missing (idempotent — safe to re-run).

**Delegate to existing tools (don't reimplement):**
- `bd init` → .beads/, git hooks, database (already handles everything)
- `bd setup claude --project` → beads workflow instructions in CLAUDE.md
- `/clavain:init` → .clavain/ memory scaffold (learnings/, scratch/, contracts/)

**NOTE:** Plugin installation, MCP server verification, ic kernel build, and plugin conflict management are all handled by `/clavain:setup` which the user has already run. Do NOT duplicate these.

**What project-onboard owns (nothing else does this):**

Core docs (seeded with real content from interview + repo scan):
- `CLAUDE.md` — project structure, git workflow, working style (follows Demarch conventions)
- `AGENTS.md` — comprehensive dev guide, architecture, dependencies
- `PHILOSOPHY.md` — design principles, goals, tradeoffs

Full docs/ tree:
```
docs/
├── brainstorms/
├── plans/
├── research/
├── guides/
├── canon/
├── prd/
├── prds/              # archive
├── solutions/
│   ├── patterns/
│   ├── best-practices/
│   └── runtime-errors/
├── audits/
├── diagrams/
├── migrations/
├── policies/
├── reports/
└── traces/
```

Observability:
- `.interwatch/watchables.yaml` — drift detection for AGENTS.md, roadmap, key docs
- Interspect DB initialization
- Interstat tracking wiring

Intertree registration:
- Register project in the hierarchy via intertree tools

### Phase 4: Seed Content via Interpath

Use interview answers (especially "key goals") to generate real artifacts:
1. Run a quick brainstorm from the goals → `docs/brainstorms/`
2. `/interpath:vision` → vision doc from brainstorm
3. `/interpath:prd` → PRD from brainstorm + vision
4. `/interpath:roadmap` → roadmap from beads (created from PRD features)
5. Create initial beads from PRD feature list (epic + child tasks)

### Phase 5: Optimize & Verify

- Run `/interdoc:interdoc` or equivalent to review/polish generated CLAUDE.md and AGENTS.md
- Verify all components are wired correctly
- Present final status report

## Why This Approach

- **Introspect-first** makes it work for both new and existing projects
- **Guided interview with smart defaults** balances personalization with speed
- **Full Demarch docs tree** because Demarch grew into it organically and every directory serves a purpose — new projects shouldn't have to rediscover that structure
- **Seeded content** because empty templates are demoralizing and rarely get filled in
- **Interpath integration** because generating vision/PRD/roadmap from real goals makes the project feel alive immediately
- **Observability from day one** because the self-improvement loop only works if drift detection is watching

## Key Decisions

1. **Scope: both greenfield and existing projects** — introspect first, fill gaps (idempotent)
2. **Interactivity: guided interview with smart defaults** — infer what you can, ask what you can't
3. **Docs structure: full Demarch tree** — all subdirectories, not a minimal subset
4. **Content: seeded from interview + repo scan** — not empty templates
5. **Beads: delegate to `bd init` + `bd setup claude`** — hooks come for free, no manual installation
6. **Delegate, don't duplicate** — `/clavain:init` for .clavain/, `/clavain:setup` already handled plugins/MCP/ic. This skill only owns what nothing else does.
7. **Observability: full stack** — interwatch, interstat, interspect from day one
8. **Kickoff: seed first sprint** — end with brainstorm → vision → PRD → roadmap → initial beads
9. **Lives as Clavain skill** — tightly integrated, assumes full Interverse ecosystem

## Open Questions

1. **CONVENTIONS.md** — should we generate one? Demarch has it for canonical doc paths. Might be useful for any project.
2. **Serena/TLDRs config** — should onboarding also set up `.serena/project.yml` and `.tldrs/` cache? These are tooling-specific, not project-specific.
3. **Git hooks conflict** — if the project already has git hooks (husky, lefthook, etc.), `bd init` hooks might conflict. How to handle?
4. **Monorepo handling** — for monorepos, should onboarding run per-module or just at the root? Demarch has per-module CLAUDE.md/AGENTS.md but that's a lot for initial setup.
5. **Template versioning** — when Demarch conventions evolve, how do onboarded projects stay current? Could tie into interwatch drift detection.
