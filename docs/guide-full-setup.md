# Full Setup Guide

**Time:** 30 minutes

**Prerequisites:**
- [Claude Code](https://claude.ai/download) installed
- Go 1.24+ (`go version`) — intercore works with 1.22+, but intermute and autarch require 1.24
- Node.js 20+ (`node --version`)
- Python 3.10+ (`python3 --version`)
- jq (`jq --version`)
- tmux (optional, for Autarch Coldwine)

## Step 1: Install Clavain + Interverse

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
```

Then open Claude Code and install companion plugins:

```
/clavain:setup
```

## Step 2: Install Beads CLI

Beads is the git-native issue tracker that powers Clavain's work discovery and sprint tracking.

```bash
go install github.com/mistakeknot/beads/cmd/bd@latest
```

Verify:
```bash
bd version
```

Initialize in your project:
```bash
cd your-project
bd init
```

## Step 3: Build Intercore (orchestration kernel)

Intercore (`ic`) provides the orchestration kernel: runs, dispatches, gates, and agent lifecycle management.

```bash
git clone https://github.com/mistakeknot/Demarch.git
cd Demarch
# From the repo root:
cd core/intercore
go build -o ic ./cmd/ic
```

Move to your PATH:
```bash
cp ic ~/.local/bin/
```

Verify:
```bash
ic version
```

## Step 4: Codex CLI (optional)

If you also use the Codex CLI, the main installer (`install.sh`) automatically installs Codex skills when it detects `codex` on PATH. Verify:

```bash
ls ~/.agents/skills/
```

Expected: `clavain`, `interdoc`, `tool-time`, `tldrs-agent-workflow`

If you installed Codex after running the main installer, set up skills manually:

```bash
bash os/clavain/scripts/install-codex-interverse.sh install
```

Restart Codex after installation. See the [Codex Setup Guide](guide-codex-setup.md) for details, migration from legacy patterns, and troubleshooting.

## Step 5: Build Intermute (optional)

Intermute is the multi-agent coordination service. Only needed if you run multiple Claude Code sessions editing the same repository simultaneously.

```bash
# From the repo root:
cd core/intermute
go build -o intermute ./cmd/intermute
cp intermute ~/.local/bin/
```

Start the service:
```bash
intermute serve
```

## Step 6: Build Autarch (optional)

Autarch provides TUI interfaces for agent monitoring and project management:
- **Bigend**: dashboard with agent status, sprint progress, system health
- **Gurgeh**: spec viewer with research overlay
- **Coldwine**: project planning with epics, stories, and tasks
- **Pollard**: competitive intelligence and market research

```bash
# From the repo root:
cd apps/autarch
go build ./cmd/...
```

Requires tmux for Coldwine's multi-pane layout.

## Step 7: Oracle setup (optional)

Oracle enables cross-AI review by sending prompts to GPT-5.2 Pro via a headless browser. This powers the `/interpeer` escalation workflow.

Setup requires:
- Chrome/Chromium
- Xvfb (for headless operation)
- A ChatGPT account

See the [Oracle CLI reference](https://github.com/mistakeknot/oracle-cli) for detailed setup instructions.

## Verification

Run the full health check:

```
/clavain:doctor
```

Expected: all checks green. The output includes plugin version, MCP connections, beads CLI, companion plugin count, and hook status.

## What's next

Start working: `/clavain:route`

Read the workflow guide: [Power User Guide](guide-power-user.md)

Want to contribute? See [Contributing Guide](guide-contributing.md)
