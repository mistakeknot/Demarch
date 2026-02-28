# Research Repo Index

Generated: 2026-02-28 (post-triage)

Owner: `Dicklesworthstone`

## Summary

- Owner repos discovered: 170 (original scan 2026-02-27)
- Kept after triage: 28 (score >= 85, relevance: integration or both)
- Removed: 142 (low relevance to Demarch)
- Disk reclaimed: ~4.4 GB (6.6 GB → 1.9 GB)

## Triage Criteria

Repos kept if: **score >= 85** AND **relevance_type in (integration, both)**. Scores from automated triage pipeline (`docs/research/dicklesworthstone-repo-triage-2026-02-27.csv`). Detailed assessments for top repos in `docs/research/assess-*.md`.

## Integration Philosophy

Do not replicate fully developed external projects. Adopt tools directly (e.g., `dcg` as a hook), port specific patterns/packages into Demarch's codebase, or take design inspiration. See `MEMORY.md` → "External Repos — Integration Philosophy".

## Assessed Repos (with detailed write-ups)

These repos have full integration assessments in `docs/research/`:

| Repo | Score | Verdict | Assessment |
|---|---:|---|---|
| [`beads_viewer`](https://github.com/Dicklesworthstone/beads_viewer) | 98 | port-partially | [assess-beads-viewer-repos.md](../docs/research/assess-beads-viewer-repos.md) |
| [`mcp_agent_mail`](https://github.com/Dicklesworthstone/mcp_agent_mail) | 98 | inspire-only | [assess-mcp-agent-mail-repos.md](../docs/research/assess-mcp-agent-mail-repos.md) |
| [`beads_viewer-pages`](https://github.com/Dicklesworthstone/beads_viewer-pages) | 96 | port-partially | [assess-beads-viewer-repos.md](../docs/research/assess-beads-viewer-repos.md) |
| [`claude_code_agent_farm`](https://github.com/Dicklesworthstone/claude_code_agent_farm) | 96 | port-partially | [assess-agent-farm-safety-repos.md](../docs/research/assess-agent-farm-safety-repos.md) |
| [`fastmcp_rust`](https://github.com/Dicklesworthstone/fastmcp_rust) | 96 | inspire-only | [assess-fastmcp-rust-repo.md](../docs/research/assess-fastmcp-rust-repo.md) |
| [`mcp_agent_mail_rust`](https://github.com/Dicklesworthstone/mcp_agent_mail_rust) | 96 | inspire-only | [assess-mcp-agent-mail-repos.md](../docs/research/assess-mcp-agent-mail-repos.md) |
| [`destructive_command_guard`](https://github.com/Dicklesworthstone/destructive_command_guard) | 95 | adopt | [assess-agent-farm-safety-repos.md](../docs/research/assess-agent-farm-safety-repos.md) |
| [`beads_viewer_for_agentic_coding_flywheel_setup`](https://github.com/Dicklesworthstone/beads_viewer_for_agentic_coding_flywheel_setup) | 97 | inspire-only | [assess-beads-viewer-repos.md](../docs/research/assess-beads-viewer-repos.md) |

## All Kept Repos

| Repo | Score | Stars | Lang | Relevance | Targets | Description |
|---|---:|---:|---|---|---|---|
| [`beads_viewer`](https://github.com/Dicklesworthstone/beads_viewer) | 98 | 1319 | Go | integration | clavain, autarch | Graph-aware TUI for Beads: PageRank, critical path, kanban, dependency DAG, robot-mode JSON API |
| [`mcp_agent_mail`](https://github.com/Dicklesworthstone/mcp_agent_mail) | 98 | 1738 | Python | both | intermute, clavain, interlock | Async agent coordination: identities, inboxes, threads, advisory file leases over FastMCP + Git + SQLite |
| [`beads_viewer_for_agentic_coding_flywheel_setup`](https://github.com/Dicklesworthstone/beads_viewer_for_agentic_coding_flywheel_setup) | 97 | 9 | HTML | integration | clavain, autarch | Minimal beads dashboard deployment template |
| [`beads_viewer-pages`](https://github.com/Dicklesworthstone/beads_viewer-pages) | 96 | 7 | HTML | integration | clavain, autarch | Static web dashboard: SQL.js WASM, force-graph dependency viz, Chart.js analytics |
| [`claude_code_agent_farm`](https://github.com/Dicklesworthstone/claude_code_agent_farm) | 96 | 668 | Shell | both | clavain, intermute, intercom, interlock | Parallel agent orchestration: lock-based coordination, tmux monitoring, auto-recovery |
| [`fastmcp_rust`](https://github.com/Dicklesworthstone/fastmcp_rust) | 96 | 13 | Rust | integration | clavain, interlock, interbase | Rust MCP server framework: cancel-correct async, zero-copy serialization |
| [`mcp_agent_mail_rust`](https://github.com/Dicklesworthstone/mcp_agent_mail_rust) | 96 | 22 | Rust | integration | intermute, clavain, interlock | Rust MCP multi-agent coordination: 34 tools, Git-backed archive, advisory locks |
| [`destructive_command_guard`](https://github.com/Dicklesworthstone/destructive_command_guard) | 95 | 585 | Rust | integration | clavain, intercheck, intercom | Pre-execution safety hook: blocks dangerous shell commands with modular security packs |
| [`agentic_coding_flywheel_setup`](https://github.com/Dicklesworthstone/agentic_coding_flywheel_setup) | 94 | 1168 | Shell | both | clavain, interphase | VPS bootstrap for multi-agent AI dev environments |
| [`beads_for_cass`](https://github.com/Dicklesworthstone/beads_for_cass) | 94 | 4 | HTML | integration | clavain, autarch | Beads analytics and prioritization patterns |
| [`flywheel_gateway`](https://github.com/Dicklesworthstone/flywheel_gateway) | 94 | 19 | TypeScript | both | intercore, intermute, intercom, clavain | Agent fleet orchestration: key rotation, WebSocket dashboard, DCG integration |
| [`meta_skill`](https://github.com/Dicklesworthstone/meta_skill) | 93 | 125 | Rust | both | clavain, interdoc, interbase | Skill management: dual SQLite+Git persistence, semantic search, bandit suggestions, MCP |
| [`beads_rust`](https://github.com/Dicklesworthstone/beads_rust) | 92 | 616 | Rust | both | clavain, intercom | Fast Rust beads: local-first issue tracking, SQLite + JSONL, git collaboration |
| [`coding_agent_session_search`](https://github.com/Dicklesworthstone/coding_agent_session_search) | 92 | 520 | Rust | both | intercom, clavain, intersearch | Unified TUI/CLI to index and search agent session history across 11+ providers |
| [`guide_to_openai_response_api_and_agents_sdk`](https://github.com/Dicklesworthstone/guide_to_openai_response_api_and_agents_sdk) | 92 | 3 | - | both | intercom, clavain, interbase | OpenAI Responses API, Agents SDK, tool orchestration, observability tracing |
| [`slb`](https://github.com/Dicklesworthstone/slb) | 92 | 58 | Go | both | clavain, interlock, intermute | Two-person rule CLI: peer review required before destructive commands |
| [`cross_agent_session_resumer`](https://github.com/Dicklesworthstone/cross_agent_session_resumer) | 91 | 14 | Rust | integration | intercom, clavain, interbase | Cross-provider session resume via canonical IR |
| [`your-source-to-prompt.html`](https://github.com/Dicklesworthstone/your-source-to-prompt.html) | 90 | 745 | HTML | both | tldr-swinton, intersearch, intercom | Local repo-to-prompt packing with context budgeting |
| [`llm_multi_round_coding_tournament`](https://github.com/Dicklesworthstone/llm_multi_round_coding_tournament) | 89 | 14 | Python | both | clavain, interflux, interpeer | Multi-model coding tournaments with iterative synthesis |
| [`ntm`](https://github.com/Dicklesworthstone/ntm) | 89 | 158 | Go | both | autarch, clavain, intermux | Named Tmux Manager: spawn, tile, coordinate AI agents with TUI command palette |
| [`post_compact_reminder`](https://github.com/Dicklesworthstone/post_compact_reminder) | 89 | 24 | Shell | integration | clavain, interdoc | Hook to re-read AGENTS.md after context compaction |
| [`ultimate_bug_scanner`](https://github.com/Dicklesworthstone/ultimate_bug_scanner) | 89 | 176 | Shell | both | clavain, intercheck, intercom | Static analysis: 1000+ bug patterns, auto-wiring into agent quality guardrails |
| [`frankensearch`](https://github.com/Dicklesworthstone/frankensearch) | 88 | 37 | Rust | both | tldr-swinton, intersearch, interbase | Two-tier hybrid search: Tantivy BM25 + semantic vectors, RRF ranking, SIMD |
| [`llm_docs`](https://github.com/Dicklesworthstone/llm_docs) | 88 | 13 | Python | both | interdoc, tldr-swinton | LLM-optimized doc distillation pipeline |
| [`automated_plan_reviser_pro`](https://github.com/Dicklesworthstone/automated_plan_reviser_pro) | 86 | 48 | Shell | integration | clavain, interdoc | Iterative spec refinement via Oracle extended reasoning |
| [`cass_memory_system`](https://github.com/Dicklesworthstone/cass_memory_system) | 86 | 253 | TypeScript | both | clavain, intermem, intermute | Cross-agent procedural memory: session history → persistent knowledge |
| [`franken_agent_detection`](https://github.com/Dicklesworthstone/franken_agent_detection) | 86 | 5 | Rust | integration | intercom, clavain, interbase | Filesystem-based detection of installed coding-agent connectors |
| [`gemini-api-updater-doc`](https://github.com/Dicklesworthstone/gemini-api-updater-doc) | 85 | 8 | - | both | intercom, clavain, interbase | Gemini API reference for LLM context correction |
