# Wave 1 Remaining: Solution Doc Classification Summary

Reviewed 25 solution docs from smaller Interverse modules. Of these:

- **5 already fully covered** in MEMORY.md or existing guides (E8, E9 intercore learnings; agent-rig trio already in its CLAUDE.md; plugin version drift and hook stdin API in troubleshooting guide)
- **2 candidates for prune** — E8 and E9 intercore sprint learnings are 100% superseded by MEMORY.md entries
- **10 need propagation** into living documentation:
  - **data-integrity-patterns.md**: silent `_ = json.Marshal/Unmarshal` two-tier strategy (intermute)
  - **multi-agent-coordination.md**: advisory-only enforcement pattern (interlock), parallel agents miss cross-cutting schema bugs (tldr-swinton)
  - **shell-and-tooling-patterns.md**: awk sub() $0 mutation fallthrough (interlearn), beads daemon stale startlock recovery (bd hang fix)
  - **plugin-troubleshooting.md**: ghost plugin enabledPlugins in settings.json (tldr-swinton), hooks-vs-skills separation principle (tldr-swinton)
  - **MEMORY.md**: marketplace cached clone stale (interfluence), new plugins not auto-installed (interkasten), Bash background mode argument corruption (codex dispatch)
- **8 fine as-is** — module-specific docs (agent-rig architecture, tuivision xterm.js patterns, tool-time event contract, tldr-swinton engine optimizations) that don't need propagation beyond their own module
- **Top cross-cutting lessons** to propagate first: advisory-only enforcement (concurrency), silent JSON error handling (Go/SQLite), awk $0 mutation (shell), Bash background mode corruption (Claude Code), and the hooks-vs-skills separation principle (plugin design)
