# First-Stranger Experience Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Enable a developer who has never seen Demarch to install and run `/clavain:route` in under 5 minutes.

**Architecture:** Three deliverables — a user-facing root README, a curl-fetchable install script, and three tier guides — validated by running the full install on a clean environment. The install script wraps existing automation (modpack-install.sh, claude plugins CLI) into a single entry point.

**Tech Stack:** Bash (install script), Markdown (docs), Claude Code plugin CLI

---

### Task 1: Root README.md

**Files:**
- Modify: `README.md` (replace contents)

**Step 1: Read the current README**

Read `README.md` to understand what content to preserve in the Architecture section.

**Step 2: Write the new README**

Replace `README.md` with user-facing content. Structure:

```markdown
# Demarch

Autonomous software development agency platform — brainstorm, plan, execute, review, and ship with multi-agent orchestration.

## Quick Start

Install Clavain and 30+ companion plugins in one command:

\```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
\```

Then open Claude Code and run:

\```
/clavain:route
\```

## What You Get

- **Clavain** — AI workflow engine: brainstorm → strategy → plan → execute → review → ship
- **33+ companion plugins** — multi-agent code review, phase tracking, doc freshness, semantic search, TUI testing
- **Multi-model orchestration** — Claude, Codex, and GPT-5.2 Pro working together
- **Sprint management** — track work with Beads, auto-discover what to work on next

## Guides

| Guide | Who It's For | Time |
|-------|-------------|------|
| [Power User Guide](docs/guide-power-user.md) | Claude Code users adding Clavain to their workflow | 10 min read |
| [Full Setup Guide](docs/guide-full-setup.md) | Users who want the complete platform (Go services, TUI tools) | 30 min setup |
| [Contributing Guide](docs/guide-contributing.md) | Developers who want to modify or extend Demarch | 45 min setup |

## How It Works

Clavain orchestrates a disciplined development lifecycle:

1. **Discover** — scan backlog, surface ready work, recommend next task
2. **Brainstorm** — collaborative dialogue to explore the problem space
3. **Strategize** — structure ideas into a PRD with trackable features
4. **Plan** — write bite-sized implementation tasks with TDD
5. **Execute** — dispatch agents (Claude subagents or Codex) to implement
6. **Review** — multi-agent quality gates catch issues before shipping
7. **Ship** — land the change with verification and session reflection

## Architecture

Demarch is a monorepo with 5 pillars:

| Pillar | Layer | Description |
|--------|-------|-------------|
| [Intercore](core/intercore/) | L1 (Core) | Orchestration kernel — runs, dispatches, gates, events |
| [Intermute](core/intermute/) | L1 (Core) | Multi-agent coordination service (Go) |
| [Clavain](os/clavain/) | L2 (OS) | Self-improving agent rig — 16 skills, 55 commands |
| [Interverse](interverse/) | L2-L3 | 33+ companion plugins |
| [Autarch](apps/autarch/) | L3 (Apps) | TUI interfaces (Bigend, Gurgeh, Coldwine, Pollard) |

Additional infrastructure: [marketplace](core/marketplace/), [agent-rig](core/agent-rig/), [interbench](core/interbench/), [interband](core/interband/), [interbase](sdk/interbase/).

### Plugin Ecosystem

[VIEW INTERACTIVE DIAGRAM](https://mistakeknot.github.io/interchart/)

All plugins are installed from the [interagency-marketplace](https://github.com/mistakeknot/interagency-marketplace).

### Naming Convention

All module names are **lowercase** except **Clavain** (proper noun), **Demarch** (project name), **Interverse** (ecosystem name), and **Autarch** (proper noun).

## License

MIT
```

**Notes:**
- The `\` before triple backticks in the code blocks above is an escape for this plan document — do NOT include the backslash in the actual README.
- Preserve the interchart link from the current README.
- The plugin table from the current README moves to the interactive diagram link. Don't duplicate it.

**Step 3: Verify links**

Confirm that the guide paths (`docs/guide-power-user.md`, etc.) and pillar paths (`core/intercore/`, `os/clavain/`, etc.) resolve correctly.

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: replace README with user-facing landing page

Leads with Quick Start (curl install), What You Get, guide links.
Architecture section preserves monorepo structure at bottom."
```

---

### Task 2: install.sh

**Files:**
- Create: `install.sh`

**Step 1: Write the install script**

Create `install.sh` at the repo root. The script must:

1. Parse flags: `--help`, `--dry-run`, `--verbose`
2. Check prerequisites: `claude` (Claude Code CLI), `jq`, `git`
   - For each missing tool: print what's missing and a one-line install hint
   - If `claude` is missing: exit with error (can't continue)
   - If `jq` is missing: exit with error (modpack-install needs it)
   - If `git` is missing: warn but continue (not strictly required for plugin install)
3. Check optional tools: `bd` (beads CLI)
   - If missing: warn with install hint (`go install github.com/mistakeknot/beads/cmd/bd@latest`), continue
4. Add marketplace (idempotent):
   ```bash
   claude plugins marketplace add mistakeknot/interagency-marketplace 2>/dev/null || true
   ```
5. Install clavain plugin (idempotent):
   ```bash
   claude plugins install clavain@interagency-marketplace 2>/dev/null || true
   ```
6. If CWD is a git repo and `bd` is available: run `bd init` (idempotent — bd init is safe to re-run)
7. Run verification checks:
   - Verify clavain is installed: check `~/.claude/plugins/cache/interagency-marketplace/clavain/` exists
   - Verify plugin.json is readable
   - Count installed companion plugins (from cache directory)
8. Print success message:
   ```
   Demarch installed successfully!

   Next steps:
     1. Open Claude Code in any project: claude
     2. Run: /clavain:setup     (installs companion plugins)
     3. Run: /clavain:route     (start working)

   Guides:
     Power user:   https://github.com/mistakeknot/Demarch/blob/main/docs/guide-power-user.md
     Full setup:   https://github.com/mistakeknot/Demarch/blob/main/docs/guide-full-setup.md
     Contributing: https://github.com/mistakeknot/Demarch/blob/main/docs/guide-contributing.md
   ```

**Implementation notes:**
- Use `set -euo pipefail` at the top
- Color output (green checkmarks, red errors, yellow warnings) with TTY detection
- `--dry-run` prints what would happen without executing
- Match the style of `os/clavain/scripts/modpack-install.sh` for consistency (same color variables, log function pattern)
- Do NOT attempt to run `/clavain:setup` from the script — that requires an active Claude Code session. Instead, tell the user to run it as their first command.

**Step 2: Make executable and test locally**

```bash
chmod +x install.sh
bash install.sh --help
bash install.sh --dry-run
```

Verify: `--help` prints usage, `--dry-run` shows what would happen without side effects.

**Step 3: Test idempotency**

Run `bash install.sh` twice. Second run should complete with "already installed" messages for each step.

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: add curl-fetchable install script for Clavain + Interverse

Checks prerequisites, adds marketplace, installs clavain plugin.
Idempotent, --help, --dry-run. Delegates companion install to /clavain:setup."
```

---

### Task 3: Power User Guide

**Files:**
- Create: `docs/guide-power-user.md`

**Step 1: Write the guide**

Target audience: Claude Code user who wants to add Clavain. Already has Claude Code installed.

Structure:
```markdown
# Power User Guide

**Time:** 10 minutes to read, 2 minutes to install

**Prerequisites:** Claude Code installed and working

## Install

\```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
\```

Then in Claude Code:
\```
/clavain:setup
\```

## Your First Session

### Finding Work
\```
/clavain:route
\```

Route discovers available work from your beads backlog, resumes active sprints,
or offers to start a fresh brainstorm.

### The Sprint Lifecycle
[Explain: brainstorm → strategy → plan → execute → review → ship]
[One paragraph per phase with the slash command]

### Common Commands

| Command | What It Does |
|---------|-------------|
| `/clavain:route` | Entry point — discover work or resume |
| `/clavain:sprint` | Full lifecycle from brainstorm to ship |
| `/clavain:work <plan>` | Execute an existing plan |
| `/clavain:brainstorm` | Explore an idea collaboratively |
| `/clavain:quality-gates` | Run multi-agent code review |
| `/clavain:doctor` | Health check — verify everything works |
| `/clavain:status` | See sprint state, doc drift, agent health |
| `/clavain:help` | Full command reference |

### Beads (Issue Tracking)

[Brief intro to bd: create, list, ready, close, sync]

### Multi-Agent Review

[Brief intro to flux-drive: what agents run, how to read verdicts]

## What's Next

Want the full platform? See [Full Setup Guide](guide-full-setup.md).
Want to contribute? See [Contributing Guide](guide-contributing.md).
```

**Step 2: Commit**

```bash
git add docs/guide-power-user.md
git commit -m "docs: add power user guide for Clavain workflow"
```

---

### Task 4: Full Setup Guide

**Files:**
- Create: `docs/guide-full-setup.md`

**Step 1: Write the guide**

Target audience: User who wants the complete Demarch platform including Go services.

Structure:
```markdown
# Full Setup Guide

**Time:** 30 minutes

**Prerequisites:**
- Claude Code installed
- Go 1.24+ (`go version`)
- Node.js 20+ (`node --version`)
- Python 3.10+ (`python3 --version`)
- jq (`jq --version`)
- tmux (optional, for Autarch Coldwine)

## Step 1: Install Clavain + Interverse

[Same curl command as README]
[Run /clavain:setup]

## Step 2: Install Beads CLI

\```bash
go install github.com/mistakeknot/beads/cmd/bd@latest
bd init
\```

## Step 3: Build Intercore

\```bash
cd core/intercore
go build -o ic ./cmd/ic
# Move to PATH:
cp ic ~/.local/bin/
\```

## Step 4: Build Intermute (Optional)

[Only needed for multi-agent file coordination]
\```bash
cd core/intermute
go build -o intermute ./cmd/intermute
\```

## Step 5: Build Autarch (Optional)

[TUI tools for agent monitoring and project management]
\```bash
cd apps/autarch
make build
\```

## Step 6: Oracle Setup (Optional)

[Cross-AI review via GPT-5.2 Pro]
[Brief — link to oracle-cli.md for details]

## Verification

\```bash
claude
> /clavain:doctor
\```
[Expected output: all green]
```

**Step 2: Commit**

```bash
git add docs/guide-full-setup.md
git commit -m "docs: add full setup guide with Go stack and optional services"
```

---

### Task 5: Contributing Guide

**Files:**
- Create: `docs/guide-contributing.md`

**Step 1: Write the guide**

Target audience: Developer who wants to modify or extend Demarch.

Structure:
```markdown
# Contributing Guide

**Time:** 45 minutes for full setup

**Prerequisites:** Everything in [Full Setup Guide](guide-full-setup.md)

## Clone the Monorepo

\```bash
git clone https://github.com/mistakeknot/Demarch.git
cd Demarch
\```

Note: Each subproject (os/clavain, interverse/interflux, etc.) keeps its own
.git. The monorepo is the development workspace, not a git monorepo.

## Development Workflow

### Trunk-Based Development

We commit directly to `main`. No feature branches unless explicitly discussed.

### Making Changes

1. Read the subproject's CLAUDE.md and AGENTS.md
2. Create a bead: `bd create --title="What I'm doing" --type=task`
3. Work: code, test, review
4. Commit with bead reference
5. Push to main

### Plugin Development

[How to test locally: claude --plugin-dir /path/to/plugin]
[How to validate: /plugin-dev:plugin-validator]
[How to publish: /interpub:release <version>]

### Running Tests

| Pillar | Command |
|--------|---------|
| Autarch | `cd apps/autarch && go test -race ./...` |
| Intermute | `cd core/intermute && go test -race ./...` |
| Intercore | `cd core/intercore && go test -race ./...` |
| Plugins | `bash -n hooks/*.sh` (syntax check) |

### Code Review

PRs are reviewed with multi-agent flux-drive. To self-review:
\```
/clavain:quality-gates
\```

## Architecture Overview

[Link to CLAUDE.md for monorepo structure]
[Link to individual pillar AGENTS.md files]
[Naming conventions: all lowercase except Clavain, Demarch, Interverse, Autarch]
```

**Step 2: Commit**

```bash
git add docs/guide-contributing.md
git commit -m "docs: add contributing guide with dev setup and workflow"
```

---

### Task 6: Cross-Link and Final Polish

**Files:**
- Modify: `README.md` (verify links work)
- Modify: `docs/guide-power-user.md` (add cross-links)
- Modify: `docs/guide-full-setup.md` (add cross-links)
- Modify: `docs/guide-contributing.md` (add cross-links)

**Step 1: Verify all internal links resolve**

Check that every `[link](path)` in all four documents points to a real file:
- `docs/guide-power-user.md` exists
- `docs/guide-full-setup.md` exists
- `docs/guide-contributing.md` exists
- `core/intercore/` directory exists
- `os/clavain/` directory exists
- `install.sh` exists

**Step 2: Ensure consistent cross-linking**

Each guide should end with "What's Next" linking to the other guides. README links to all three. Verify the table in the README matches the actual guide titles.

**Step 3: Commit**

```bash
git add README.md docs/guide-power-user.md docs/guide-full-setup.md docs/guide-contributing.md
git commit -m "docs: add cross-links between README and tier guides"
```

---

### Task 7: First-Run Validation

**Files:**
- Modify: `install.sh` (fix any issues found)
- Modify: any guide docs (fix any issues found)

**Step 1: Test install.sh on current machine**

```bash
bash install.sh --dry-run
```

Verify: output shows each step that would run, no errors.

```bash
bash install.sh
```

Verify: completes without errors, prints success message.

**Step 2: Verify the success moment**

Open Claude Code and run `/clavain:route`. Confirm it either:
- Shows discovery results (beads to work on), OR
- Offers "Start fresh brainstorm"

**Step 3: Test edge cases**

- Run `install.sh` again (idempotency test)
- Run `install.sh --help` (usage output)
- Temporarily remove `jq` from PATH, run install.sh, verify clear error message

**Step 4: Document validation results**

Update bead iv-1opqc notes with validation findings:
```bash
bd update iv-1opqc --notes="Validated on [date]. Results: [pass/fail]. Issues found: [list]"
```

**Step 5: Fix any issues found**

If install.sh or guides have problems, fix them and recommit.

**Step 6: Final commit**

```bash
git add install.sh docs/
git commit -m "fix: address issues found during first-run validation"
```
