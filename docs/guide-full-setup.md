# Full Setup Guide

**Time:** 30 minutes

**Prerequisites:**
- [Claude Code](https://claude.ai/download) installed
- Go 1.24+ (`go version`)
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
cd Demarch/core/intercore
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

## Step 4: Build Intermute (optional)

Intermute is the multi-agent coordination service. Only needed if you run multiple Claude Code sessions editing the same repository simultaneously.

```bash
cd Demarch/core/intermute
go build -o intermute ./cmd/intermute
cp intermute ~/.local/bin/
```

Start the service:
```bash
intermute serve
```

## Step 5: Build Autarch (optional)

Autarch provides TUI interfaces for agent monitoring and project management:
- **Bigend**: dashboard with agent status, sprint progress, system health
- **Gurgeh**: spec viewer with research overlay
- **Coldwine**: project planning with epics, stories, and tasks
- **Pollard**: competitive intelligence and market research

```bash
cd Demarch/apps/autarch
make build
```

Requires tmux for Coldwine's multi-pane layout.

## Step 6: Oracle setup (optional)

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

Expected output (all green):
```
Plugin loaded: clavain v0.6.76
MCP: context7 connected
Beads: bd v0.52.0 found
Companions: 12/12 installed
Hooks: 10/10 active
Health: ALL CLEAR
```

## What's next

Start working: `/clavain:route`

Read the workflow guide: [Power User Guide](guide-power-user.md)

Want to contribute? See [Contributing Guide](guide-contributing.md)
