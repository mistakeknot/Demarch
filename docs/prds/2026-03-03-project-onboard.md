# PRD: Project Onboard Skill

## Problem

Setting up a new project (or onboarding an existing one) with Demarch-level automation requires manually running 6+ tools in the right order, creating docs from scratch, and knowing which directories to create. This friction means most projects never get fully operational — they're missing drift detection, seeded roadmaps, or proper CLAUDE.md/AGENTS.md, which degrades every subsequent session.

## Solution

A Clavain skill (`project-onboard`) that introspects any repo, asks minimal questions with smart defaults, then orchestrates all setup in one flow — from beads to observability to interpath-generated artifacts. Idempotent, so safe to re-run on partially set up projects.

## Features

### F1: Project Introspection
**What:** Scan the repo to detect existing infrastructure and report what's present vs missing.
**Acceptance criteria:**
- [ ] Detects: git repo, remote, CLAUDE.md, AGENTS.md, PHILOSOPHY.md, .beads/, .clavain/, docs/ subdirs, .interwatch/, languages, project name
- [ ] Reports a ✔/✖ checklist to the user
- [ ] Infers project name from git remote, directory name, or manifest files (package.json, Cargo.toml, go.mod, pyproject.toml)
- [ ] Infers languages from file extensions present in the repo
- [ ] Infers project type (library/app/monorepo/plugin) from structure

### F2: Guided Interview
**What:** Ask the user only what can't be inferred, with smart defaults pre-filled from introspection.
**Acceptance criteria:**
- [ ] Skips questions whose answers were inferred (e.g., don't ask language if detected)
- [ ] Asks via AskUserQuestion with pre-filled defaults shown in option descriptions
- [ ] Core questions: project description, languages/frameworks, project type, key goals for next month
- [ ] "Key goals" is always asked (can't be inferred)
- [ ] Collects enough context to seed CLAUDE.md, AGENTS.md, and the initial brainstorm

### F3: Infrastructure Scaffold
**What:** Create all missing infrastructure by delegating to existing tools and generating seeded docs.
**Acceptance criteria:**
- [ ] Runs `bd init` if .beads/ doesn't exist (creates DB, installs git hooks)
- [ ] Runs `bd setup claude --project` to inject beads workflow into CLAUDE.md
- [ ] Runs `/clavain:init` if .clavain/ doesn't exist (learnings/, scratch/, contracts/)
- [ ] Generates CLAUDE.md with real content: project name, structure, git workflow, working style
- [ ] Generates AGENTS.md with real content: architecture overview, detected conventions, build/test commands
- [ ] Generates PHILOSOPHY.md with stated goals and design principles
- [ ] Creates full docs/ tree (brainstorms/, plans/, research/, guides/, canon/, prd/, prds/, solutions/{patterns,best-practices,runtime-errors}, audits/, diagrams/, migrations/, policies/, reports/, traces/)
- [ ] All operations are idempotent — skips anything that already exists
- [ ] Does NOT duplicate work done by /clavain:setup (plugins, MCP, ic kernel)

### F4: Observability Setup
**What:** Configure drift detection, profiling, and tracking infrastructure.
**Acceptance criteria:**
- [ ] Creates `.interwatch/watchables.yaml` with staleness signals for AGENTS.md (14d), roadmap (30d), and other key docs
- [ ] Initializes interspect DB if not present
- [ ] Wires interstat tracking for the project
- [ ] Registers project in intertree hierarchy
- [ ] All operations are idempotent

### F5: Content Seeding via Interpath
**What:** Generate real artifacts from interview answers so the project starts with content, not empty directories.
**Acceptance criteria:**
- [ ] Creates a brainstorm doc from the "key goals" interview answer
- [ ] Runs `/interpath:vision` to generate a vision doc
- [ ] Runs `/interpath:prd` to generate an initial PRD
- [ ] Runs `/interpath:roadmap` to generate a roadmap
- [ ] Creates initial beads (epic + feature children) from PRD features
- [ ] All interpath commands receive the brainstorm and prior artifacts as context

### F6: Optimize & Verify
**What:** Polish generated docs and verify everything is wired correctly.
**Acceptance criteria:**
- [ ] Reviews/optimizes generated CLAUDE.md and AGENTS.md for quality
- [ ] Verifies all components exist and are consistent (beads DB, docs tree, watchables, etc.)
- [ ] Presents a final status report showing everything that was created/verified
- [ ] Report includes actionable next steps (e.g., "run /clavain:brainstorm to start your first feature")

## Non-goals

- Plugin installation or MCP server setup (handled by `/clavain:setup`)
- ic kernel build (handled by `/clavain:setup`)
- Per-module onboarding for monorepos (root-only for v1; per-module is a future iteration)
- Custom template system (use Demarch conventions as the single source of truth)
- CI/CD pipeline setup (project-specific, not a Clavain concern)

## Dependencies

- `bd` CLI installed and dolt server running (for beads init)
- Clavain installed (prerequisite — user is running a Clavain skill)
- Interpath plugin installed (for vision/PRD/roadmap generation)
- Interwatch plugin installed (for drift detection config)
- Intertree plugin installed (for hierarchy registration)

## Open Questions

1. **CONVENTIONS.md** — should we generate one? Demarch has it for canonical doc paths.
2. **Git hooks conflict** — if existing hooks (husky, lefthook) are present, how does `bd init` handle it? May need to detect and warn.
3. **Template versioning** — when Demarch conventions evolve, how do onboarded projects stay current? Tie into interwatch?
