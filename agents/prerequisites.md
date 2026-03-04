# Prerequisites & Conventions

## Required Tools

All pre-installed on this server:

| Tool | Used by | Purpose |
|------|---------|---------|
| `jq` | interbump, hooks | JSON manipulation |
| `uv` | tldr-swinton, interject, intersearch, intercache, interfin | Python package management |
| `go` (1.24+) | intermute, intercore, interlock, interbench | Go builds and tests |
| `node`/`npm` | interkasten | MCP server build |
| `python3` | tldr-swinton, tool-time, interject, intercache | CLI tools, analysis scripts |
| `bd` | all | Beads issue tracker CLI |

## Secrets

In environment or dotfiles — never commit:

- `INTERKASTEN_NOTION_TOKEN` — Notion API token for interkasten sync
- `EXA_API_KEY` — Exa search API for interject and interflux research agents
- `TAVILY_API_KEY` — Tavily search API for interject
- `BRAVE_API_KEY` — Brave search API for interject
- `SEARXNG_URL` — Self-hosted SearXNG instance URL for interject
- `SLACK_TOKEN` — Slack API for interslack

## Go Module Path Convention

All first-party Go modules declare canonical module paths matching `github.com/mistakeknot/<module-name>`, where `<module-name>` matches the directory basename (e.g., `core/intercore` declares `github.com/mistakeknot/intercore`).

- **Replace directives** use relative filesystem paths from the module's own directory (e.g., `../../core/intermute`), never symlinks.
- **CI guard**: `scripts/check-go-module-paths.sh` validates all in-scope `go.mod` files. Excludes `research/`, `.external/`, and `testdata/` directories.
- Third-party or vendored modules (under `.external/`, `research/`) are exempt from this convention.
