# Project Onboard Skill — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Create a Clavain skill that makes any project fully operational in the Demarch ecosystem with one command.

**Architecture:** A SKILL.md orchestration prompt (~200 lines) with template files in subdirectories. The skill is a sequencer: it introspects the repo, asks minimal questions, then delegates to existing tools (bd init, /clavain:init, /interpath:*) while generating the artifacts they can't (CLAUDE.md, AGENTS.md, PHILOSOPHY.md, docs/ tree, observability config).

**Tech Stack:** Clavain skill (markdown prompt), bash for introspection checks, AskUserQuestion for interview, template files for doc generation.

**Prior Learnings:**
- `docs/solutions/patterns/hybrid-cli-plugin-architecture-20260223.md` — skill is a thin orchestrator over existing CLI tools, not a reimplementation
- `docs/solutions/best-practices/stranger-perspective-doc-validation-20260228.md` — generated templates must use placeholders, not hardcoded values, to age gracefully
- `docs/canon/doc-structure.md` — CLAUDE.md is 30-60 lines (operations only), AGENTS.md is comprehensive (architecture, workflows), PHILOSOPHY.md at root

---

### Task 1: Create skill directory and SKILL.md

**Files:**
- Create: `os/clavain/skills/project-onboard/SKILL.md`

**Step 1: Create directory**

```bash
mkdir -p os/clavain/skills/project-onboard
```

**Step 2: Write SKILL.md**

Write the orchestration prompt. Structure:

```markdown
---
name: project-onboard
description: Use when onboarding a new or existing project into the Demarch ecosystem — introspects infrastructure, conducts guided interview, scaffolds docs and automation, seeds content via interpath
---

# Project Onboard

## Overview

One-command project setup. Introspects any repo, asks minimal questions with smart defaults,
then orchestrates full Demarch-level automation: beads tracking, doc scaffolding, observability,
and content seeding.

Safe to re-run — all operations are idempotent (skip what already exists).

**Announce at start:** "I'm using the project-onboard skill to set up this project."

## Preconditions

- Must be in a git repository
- Clavain must be installed (you're running this skill, so it is)
- `bd` CLI must be available (`command -v bd`)

## Phase 1: Introspect

Scan the project and report what exists vs what's missing.

Check each of these (✔ = exists, ✖ = missing):

```bash
# Git
git rev-parse --show-toplevel
git remote get-url origin 2>/dev/null

# Core docs
test -f CLAUDE.md
test -f AGENTS.md
test -f PHILOSOPHY.md
test -f CONVENTIONS.md

# Infrastructure
test -d .beads
test -d .clavain
test -d .interwatch

# Docs tree — check each subdir
for d in brainstorms plans research guides canon prd prds solutions audits \
         diagrams migrations policies reports traces; do
    test -d "docs/$d"
done

# Language detection (from file extensions)
# Check for: go.mod, Cargo.toml, package.json, pyproject.toml, setup.py,
#            *.go, *.rs, *.ts, *.py, *.java, etc.

# Project name inference
# Priority: package.json name > Cargo.toml [package] name > go.mod module >
#           pyproject.toml project.name > git remote basename > directory name

# Project type inference
# Monorepo: multiple go.mod/package.json/Cargo.toml files
# Library: has lib.rs, or src/index.ts with no pages/app dir, or setup.py with packages
# App: has main.go, cmd/, pages/, app/, or Dockerfile
# Plugin: has .claude-plugin/ directory
```

Present the checklist to the user.

## Phase 2: Guided Interview

Use AskUserQuestion. Skip questions whose answers were inferred from Phase 1.

**Question 1** (skip if README or manifest has description):
"What is this project? Give me a name and one-liner."
Default: inferred name from Phase 1.

**Question 2** (skip if languages detected):
"What languages and frameworks does this project use?"
Default: detected languages from Phase 1.

**Question 3** (skip if project type inferred):
"What type of project is this?"
Options: Library, Application, Monorepo, Plugin
Default: inferred from Phase 1.

**Question 4** (always ask — can't be inferred):
"What are the key goals for this project in the next month?"

**Question 5** (always ask):
"How is the project built and tested? What commands should agents use?"
Default: inferred from Makefile, package.json scripts, etc.

## Phase 3: Scaffold Infrastructure

Execute in order. Skip anything that already exists.

### 3a: Beads Init

```bash
if [ ! -d .beads ]; then
    bd init
    bd setup claude --project
fi
```

### 3b: Clavain Memory

Run `/clavain:init` if `.clavain/` doesn't exist.

### 3c: Generate CLAUDE.md

Only if CLAUDE.md doesn't exist. Use the template from `templates/CLAUDE.md.tmpl`.
Fill placeholders from interview answers and introspection results.

Key sections (following doc-structure.md boundary rule — operations only):
- Project name + one-liner
- Structure (detected from filesystem)
- Git Workflow (trunk-based default)
- Working Style (Demarch conventions)
- See AGENTS.md For (pointer to comprehensive guide)

Target: 30-60 lines. CLAUDE.md is loaded every session — keep it lean.

### 3d: Generate AGENTS.md

Only if AGENTS.md doesn't exist. Use the template from `templates/AGENTS.md.tmpl`.

Key sections (following doc-structure.md — comprehensive guide):
- Overview (project description, architecture)
- Agent Quickstart (how to start working)
- Directory Layout (detected from filesystem)
- Build & Test (from interview Q5)
- Coding Conventions (detected language-appropriate defaults)
- Bead Tracking (if beads were initialized)

### 3e: Generate PHILOSOPHY.md

Only if PHILOSOPHY.md doesn't exist. Use the template from `templates/PHILOSOPHY.md.tmpl`.
Seed with interview Q4 (key goals) as design principles.

### 3f: Generate CONVENTIONS.md

Only if CONVENTIONS.md doesn't exist. Use the template from `templates/CONVENTIONS.md.tmpl`.
Standard canonical doc paths following Demarch pattern.

### 3g: Create docs/ tree

```bash
for d in brainstorms plans research guides canon prd prds \
         solutions/patterns solutions/best-practices solutions/runtime-errors \
         audits diagrams migrations policies reports traces; do
    mkdir -p "docs/$d"
done
```

## Phase 4: Observability Setup

### 4a: Interwatch

Create `.interwatch/watchables.yaml` if it doesn't exist:

```yaml
watchables:
  - name: agents-md
    path: AGENTS.md
    generator: interdoc:interdoc
    staleness_days: 14
  - name: roadmap
    path: docs/roadmap.md
    generator: interpath:roadmap
    staleness_days: 30
  - name: philosophy
    path: PHILOSOPHY.md
    staleness_days: 90
```

### 4b: Intertree Registration

Register project in intertree hierarchy if interkasten tools are available.

## Phase 5: Content Seeding via Interpath

Use interview Q4 (key goals) to generate real content:

1. Write a brainstorm doc to `docs/brainstorms/` from key goals
2. Run `/interpath:vision` — generates vision doc from brainstorm
3. Run `/interpath:prd` — generates PRD from brainstorm + vision
4. Run `/interpath:roadmap` — generates roadmap from beads
5. Create initial beads from PRD features:
   ```bash
   bd create --title="<epic from PRD>" --type=epic --priority=1
   # For each feature in PRD:
   bd create --title="F1: <feature>" --type=feature --priority=2
   bd dep add <feature-id> <epic-id>
   ```

## Phase 6: Verify & Report

Present final status:

```
Project onboarding complete!

Infrastructure:
  ✔ Beads tracking initialized (.beads/)
  ✔ Git hooks installed (pre-commit, post-checkout, pre-push)
  ✔ Clavain memory scaffold (.clavain/)
  ✔ CLAUDE.md (30 lines)
  ✔ AGENTS.md (80 lines)
  ✔ PHILOSOPHY.md
  ✔ CONVENTIONS.md
  ✔ docs/ tree (15 directories)

Observability:
  ✔ Drift detection (.interwatch/)
  ✔ Intertree registered

Content:
  ✔ Vision doc
  ✔ PRD with N features
  ✔ Roadmap
  ✔ N beads created (1 epic + N features)

Next steps:
  - Run `/clavain:brainstorm` to explore your first feature
  - Run `/clavain:sprint` for the full development lifecycle
  - Run `/interwatch:watch` to check doc health anytime
```
```

**Step 3: Commit**

```bash
git add os/clavain/skills/project-onboard/SKILL.md
git commit -m "feat(clavain): add project-onboard skill — orchestration prompt"
```

### Task 2: Create CLAUDE.md template

**Files:**
- Create: `os/clavain/skills/project-onboard/templates/CLAUDE.md.tmpl`

**Step 1: Write template**

Template uses `{{PLACEHOLDER}}` markers filled by the skill at runtime:

```markdown
# {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

## Structure

{{PROJECT_STRUCTURE}}

## Git Workflow

Trunk-based development — commit directly to `main`.

## Working Style

When you have enough context to start implementing, do it. Write a 3-bullet inline assessment, not a plan file. For irreversible actions (publish, delete, merge, bead-close), always ask before proceeding.

## See AGENTS.md For

Architecture, build/test instructions, coding conventions, troubleshooting, and operational guides.
```

Target: ~20 lines before placeholder expansion. Will expand to 30-60 after filling.

**Step 2: Commit**

```bash
git add os/clavain/skills/project-onboard/templates/CLAUDE.md.tmpl
git commit -m "feat(clavain): add CLAUDE.md template for project-onboard"
```

### Task 3: Create AGENTS.md template

**Files:**
- Create: `os/clavain/skills/project-onboard/templates/AGENTS.md.tmpl`

**Step 1: Write template**

```markdown
# {{PROJECT_NAME}} — Agent Development Guide

## Overview

{{PROJECT_DESCRIPTION}}

## Agent Quickstart

1. Read this file (AGENTS.md) — you're doing it now.
2. Run `bd ready` to see available work.
3. When done: `bd close <id>`, commit, `bd sync`, push.

## Directory Layout

{{DIRECTORY_LAYOUT}}

## Build & Test

{{BUILD_TEST_COMMANDS}}

## Coding Conventions

{{CODING_CONVENTIONS}}

## Bead Tracking

All work is tracked using beads (`bd` CLI). See `.beads/` for the database.

- `bd ready` — show available work
- `bd create --title="..." --type=task` — create new issue
- `bd close <id>` — mark complete
- `bd sync` — sync with git remote

## Key Dependencies

{{DEPENDENCIES}}
```

**Step 2: Commit**

```bash
git add os/clavain/skills/project-onboard/templates/AGENTS.md.tmpl
git commit -m "feat(clavain): add AGENTS.md template for project-onboard"
```

### Task 4: Create PHILOSOPHY.md and CONVENTIONS.md templates

**Files:**
- Create: `os/clavain/skills/project-onboard/templates/PHILOSOPHY.md.tmpl`
- Create: `os/clavain/skills/project-onboard/templates/CONVENTIONS.md.tmpl`

**Step 1: Write PHILOSOPHY.md template**

```markdown
# {{PROJECT_NAME}} — Philosophy

## Design Principles

{{DESIGN_PRINCIPLES}}

## Key Goals

{{KEY_GOALS}}

## Tradeoffs

These are explicit bets we're making:

{{TRADEOFFS}}
```

**Step 2: Write CONVENTIONS.md template**

```markdown
# {{PROJECT_NAME}} Conventions

Canonical documentation paths. Do not introduce compatibility aliases or fallback filenames.

## Documentation Paths

- Roadmap: `docs/roadmap.md`
- Vision: `docs/{{PROJECT_SLUG}}-vision.md`
- PRD: `docs/PRD.md` (or `docs/prds/*.md` for multiple)

## Enforcement Rules

- Do not use non-canonical paths for documentation.
- New docs, commands, and scripts must reference canonical paths only.
```

**Step 3: Commit**

```bash
git add os/clavain/skills/project-onboard/templates/PHILOSOPHY.md.tmpl
git add os/clavain/skills/project-onboard/templates/CONVENTIONS.md.tmpl
git commit -m "feat(clavain): add PHILOSOPHY.md and CONVENTIONS.md templates"
```

### Task 5: Create interwatch template

**Files:**
- Create: `os/clavain/skills/project-onboard/templates/watchables.yaml.tmpl`

**Step 1: Write template**

```yaml
# Drift detection configuration — created by /clavain:project-onboard
# interwatch scans these signals and alerts when docs go stale.

watchables:
  - name: agents-md
    path: AGENTS.md
    generator: interdoc:interdoc
    staleness_days: 14

  - name: roadmap
    path: docs/roadmap.md
    generator: interpath:roadmap
    staleness_days: 30

  - name: philosophy
    path: PHILOSOPHY.md
    staleness_days: 90

  - name: conventions
    path: CONVENTIONS.md
    staleness_days: 90
```

**Step 2: Commit**

```bash
git add os/clavain/skills/project-onboard/templates/watchables.yaml.tmpl
git commit -m "feat(clavain): add interwatch watchables template for project-onboard"
```

### Task 6: Register skill in plugin.json

**Files:**
- Modify: `os/clavain/.claude-plugin/plugin.json`

**Step 1: Add skill entry**

Add `"./skills/project-onboard"` to the `skills` array in alphabetical order (after `./skills/lane`, before `./skills/refactor-safely`).

**Step 2: Update skill count in description**

Update `"15 skills"` to `"16 skills"` in the description field.

**Step 3: Run manifest check**

```bash
python3 -c "import json; json.load(open('os/clavain/.claude-plugin/plugin.json'))"
```
Expected: no output (valid JSON).

**Step 4: Commit**

```bash
git add os/clavain/.claude-plugin/plugin.json
git commit -m "feat(clavain): register project-onboard skill in plugin manifest"
```

### Task 7: Update Clavain CLAUDE.md skill count

**Files:**
- Modify: `os/clavain/CLAUDE.md`

**Step 1: Update overview line**

Change `15 skills` to `16 skills` in the overview description.

**Step 2: Commit**

```bash
git add os/clavain/CLAUDE.md
git commit -m "docs(clavain): update skill count to 16"
```

### Task 8: Generate SKILL-compact.md

**Files:**
- Create: `os/clavain/skills/project-onboard/SKILL-compact.md`

**Step 1: Generate compact version**

Run the compact skill generator:

```bash
bash os/clavain/scripts/gen-skill-compact.sh os/clavain/skills/project-onboard/SKILL.md
```

If the script doesn't exist or fails, manually create a compact version (~80 lines) that preserves the phase structure but strips examples and verbose instructions.

**Step 2: Verify compact exists**

```bash
test -f os/clavain/skills/project-onboard/SKILL-compact.md && echo "OK"
```

**Step 3: Commit**

```bash
git add os/clavain/skills/project-onboard/SKILL-compact.md
git commit -m "feat(clavain): add SKILL-compact.md for project-onboard"
```
