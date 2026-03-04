# Development Workflow

Each subproject under `apps/`, `os/`, `core/`, `interverse/`, and `sdk/` is an independent git repo with its own `.git`. The root `Demarch/` directory also has a `.git` for the monorepo skeleton (`scripts/`, `docs/`, `.beads/`, `CLAUDE.md`, `AGENTS.md`). **Git commands operate on whichever `.git` is nearest** — always verify with `git rev-parse --show-toplevel` if unsure which repo you're in. To work on a specific module:

```bash
cd interverse/interflux  # from repo root
# Each module has its own CLAUDE.md, AGENTS.md, .git
```

## Running and Testing by Module Type

**Plugins (hooks/skills/commands only):**
```bash
claude --plugin-dir /root/projects/Demarch/interverse/<name>
# Structural tests (if present):
cd interverse/<name> && uv run pytest tests/structural/ -v
```

**MCP server plugins** (intercache, interdeep, interflux, interfluence, interject, interkasten, interlock, intermap, intermux, tldr-swinton, tuivision):
```bash
# Build/install the server first, then test via Claude Code.
# Entrypoints vary — check each module's local AGENTS.md. Examples:
cd interverse/interkasten/server && npm install && npm run build && npm test
cd interverse/interlock && bash scripts/build.sh && go test ./...
cd interverse/tldr-swinton && uv tool install -e .  # installs `tldrs` CLI
```

**Kernel** (intercore):
```bash
cd core/intercore
go build -o ic ./cmd/ic   # produces the `ic` CLI binary
go test ./...              # run all tests
./ic --help                # verify
```

**Service** (intermute):
```bash
cd core/intermute
go run ./cmd/intermute     # starts on :7338
go test ./...              # run all tests
```

**Infra** (interbench):
```bash
cd core/interbench && go build -o interbench . && ./interbench --help
```

## Publishing

Three entrypoints to the same engine — use whichever fits your context:

**1. Go CLI (preferred when `ic` is built):**
```bash
cd interverse/interflux
ic publish --patch               # auto-increment patch version
ic publish 0.2.1                 # bump to exact version
ic publish --dry-run             # preview only
ic publish doctor --fix          # detect and auto-repair drift
```

**2. Claude Code slash command:**
```
/interpub:release <version>
```

**3. Shell wrapper (terminal fallback):**
```bash
cd interverse/interflux
scripts/bump-version.sh 0.2.1            # bump + commit + push
scripts/bump-version.sh 0.2.1 --dry-run  # preview only
```

All three call the same underlying engine. `/interpub:*` and other slash commands are **Claude Code slash commands** — run them inside a Claude Code session, not from a terminal.

## Cross-repo Changes

When a change spans multiple repos (e.g., adding an MCP tool to interlock that requires an intermute API change):

1. Make changes in each repo independently
2. Commit and push the **dependency first** (e.g., intermute before interlock)
3. Reference the same Interverse-level bead in both commit messages
4. Always verify you're in the right repo: `git rev-parse --show-toplevel`
