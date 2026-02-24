# Power User Guide

**Time:** 10 minutes to read, 2 minutes to install

**Prerequisites:** [Claude Code](https://claude.ai/download) installed and working

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
```

Then open Claude Code and install companion plugins:

```
/clavain:setup
```

This installs 12+ companion plugins for code review, phase tracking, doc freshness monitoring, and more.

## Your first session

### Finding work

```
/clavain:route
```

Route is the universal entry point. It:
- Resumes an active sprint if one exists
- Scans your beads backlog for ready work
- Classifies complexity and auto-dispatches to the right workflow
- Offers to start a fresh brainstorm if nothing is queued

### The sprint lifecycle

Clavain's sprint is a disciplined lifecycle that ensures you think before you code:

**Brainstorm** (`/clavain:brainstorm`): collaborative dialogue exploring the problem space. Asks questions, proposes approaches, captures decisions in a brainstorm doc.

**Strategize** (`/clavain:strategy`): structures the brainstorm into a PRD with discrete features, acceptance criteria, and trackable beads.

**Plan** (`/clavain:write-plan`): writes a bite-sized implementation plan with exact file paths, test commands, and commit messages. TDD by default.

**Execute** (`/clavain:work <plan>`): implements the plan task by task. Can dispatch to Codex agents for parallel execution or run sequentially with Claude subagents.

**Review** (`/clavain:quality-gates`): multi-agent code review. 7 specialized agents (architecture, safety, correctness, quality, user/product, performance, game design) analyze your changes in parallel.

**Ship** (`/clavain:land`): verify, commit, and push. Session reflection captures learnings for next time.

### Common commands

| Command | What It Does |
|---------|-------------|
| `/clavain:route` | Entry point: discover work or resume sprint |
| `/clavain:sprint` | Full lifecycle from brainstorm to ship |
| `/clavain:work <plan>` | Execute an existing plan |
| `/clavain:brainstorm` | Explore an idea collaboratively |
| `/clavain:quality-gates` | Run multi-agent code review |
| `/clavain:doctor` | Health check: verify everything works |
| `/clavain:status` | Sprint state, doc drift, agent health |
| `/clavain:help` | Full command reference |

### Beads (issue tracking)

Beads is a lightweight, git-native issue tracker. It stores issues alongside your code and syncs via git.

```bash
bd create --title="Add user auth" --type=feature --priority=2   # Create
bd ready                                                          # What's ready to work?
bd list --status=open                                            # All open issues
bd show iv-abc1                                                  # Issue details
bd close iv-abc1                                                 # Mark done
bd sync                                                          # Push to remote
```

Beads integrates deeply with Clavain: sprints track against beads, discovery scans beads for work, and phase transitions record on beads automatically.

### Multi-agent review

When you run `/clavain:quality-gates`, Clavain dispatches specialized review agents:

- **fd-architecture**: module boundaries, coupling, design patterns
- **fd-safety**: security threats, credential handling, trust boundaries
- **fd-correctness**: data consistency, race conditions, transaction safety
- **fd-quality**: naming, conventions, error handling, language idioms
- **fd-user-product**: UX friction, value proposition, edge cases
- **fd-performance**: rendering bottlenecks, data access, memory usage
- **fd-game-design**: balance, pacing, feedback loops (for game projects)

Each agent produces a verdict (CLEAN or NEEDS_ATTENTION). You only need to read the agents that flagged issues.

## What's next

Want the full platform (Go services, TUI tools)? See [Full Setup Guide](guide-full-setup.md).

Want to contribute to Demarch? See [Contributing Guide](guide-contributing.md).
