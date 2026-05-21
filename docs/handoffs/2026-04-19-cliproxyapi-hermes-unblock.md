---
date: 2026-04-19
session: b218464d
topic: CLIProxyAPI Hermes unblock + Auraken repo honesty pass
beads: [sylveste-heh8, sylveste-khb8]
---

## Session Handoff — 2026-04-19 CLIProxyAPI unblock + Auraken doc corrections

### Directive

> Your job is to install Hermes on zklw pointed at the local CLIProxyAPI, load the auraken skill + auraken-lens MCP, and run one end-to-end message via Telegram. Start by picking a Hermes install path (vendored source at `/home/mk/projects/Sylveste/apps/Auraken/research/hermes-agent/` at cfa87e7, or check for a maintained pip/uv install). Point Hermes at `http://127.0.0.1:8317/v1` with bearer auth from `~/.cli-proxy-api/local-api-key`. Verify with a `/auraken` invocation that produces a real reframe, not a canned Claude Code reply.

- Beads: `sylveste-khb8` — resolution path validated (CLIProxyAPI installed + smoke-tested), remaining = systemd unit for persistence + Hermes install + acceptance run against `test-conversations.md`. `sylveste-heh8` — depends on khb8, no direct work needed until khb8 closes.
- Fallback A: if Hermes install is painful, test `curl` against CLIProxyAPI with test-conversations.md prompts + SKILL.md injected manually. Slower UX but validates the intelligence layer separately from transport.
- Fallback B: if systemd is a lift, start with nohup + redirected logs; systemd-ify as a polish pass.

Before modifying Auraken repo docs: verify filesystem state first (`feedback_docs_match_codebase_not_memory`). Before architecture recs in Auraken/Hermes space: re-read `project_auraken_hermes_pivot.md` (`feedback_reanchor_to_pivot_memory`).

### Dead Ends

- Anthropic API direct — viable unblock, but inverts `feedback_claude_max_preference`; CLIProxyAPI preserves Max and is the long-term-quality answer.
- GLM Coding Plan — hard single-concurrent-request limit breaks multi-agent parallelism. Disqualified as Hermes backend. May still be useful as a standalone Claude Code backend elsewhere.
- Codex exec subprocess shim — `codex exec` inherits the ChatGPT OAuth Responses API bugs (#5879/5736/5718); doesn't help. Dead for now.
- SSH tunnel for Claude OAuth callback — didn't route from laptop to zklw. Workaround: `curl "http://localhost:54545/callback?code=...&state=..."` directly on zklw after user pasted the failed redirect URL back.
- Python daemon resurrection (heh8 original option 1) — contradicted the 2026-04-16 pivot which explicitly rejected "option A (wrapper daemon with its own runtime)." User caught this drift early in the session.
- First Auraken doc rewrites overclaimed on MCP servers — listed 5 (lens_select, profile_gen, style_fingerprint, discrimination_tracker, forge_mode) as though shipped when only `auraken-lens` exists. Caught during "presentable to Ade Oshineye" review. Corrected in commit 8835792.

### Context

- **CLIProxyAPI on zklw**: managed by systemd user service `cliproxyapi.service` (unit at `~/.config/systemd/user/cliproxyapi.service`). Survives logout + reboot (linger=yes), auto-restarts on crash. Binary `~/tools/cliproxyapi/cli-proxy-api`. Config `~/tools/cliproxyapi/config.yaml`. Listening `127.0.0.1:8317`. Local API key at `~/.cli-proxy-api/local-api-key` (mode 0600). Logs: `journalctl --user -u cliproxyapi -f`.
- **OAuth tokens**: `~/.cli-proxy-api/claude-arouth1@gmail.com.json` + `~/.cli-proxy-api/codex-a.r.r.qvs@gmail.com-pro.json`. Auto-refreshes every 15m.
- **Cloaking is load-bearing**: CLIProxyAPI injects Claude Code's system prompt (~1370 tokens) into every non-Claude-Code client's Claude request. This is what keeps Max bucket routing working. Do not disable.
- **Claude Code OAuth scope is `user:sessions:claude_code`** (client_id `9d1c250a-e61b-44d9-88ed-5944d1962f5e`). Same as Claude Code itself → tokens land in the `claude -p` bucket. Hermes-native's generic OAuth path hit a different bucket and failed. Architecture detail, not a config knob.
- **Codex path bypasses khb8's blockers**: `gpt-5.4` (the model Hermes-native couldn't reach) works through CLIProxyAPI. Different HTTP route to OpenAI, not a bug-workaround.
- **Auraken repo is its own git repo** with remote `mistakeknot/auraken` (separate from Sylveste monorepo). Recently switched SSH→HTTPS per CONVENTIONS.md.
- **Four new commits on `mistakeknot/auraken` main** this session: 3715f44 README, 377bd9d AGENTS+CLAUDE, 8835792 overclaim correction, 356116e PROVIDER.md.
- **New feedback memories this session**: `feedback_long_term_quality_default.md`, `feedback_reanchor_to_pivot_memory.md`, `feedback_docs_match_codebase_not_memory.md`.
- **Key file paths**:
  - `/home/mk/projects/Sylveste/apps/Auraken/integrations/hermes/PROVIDER.md` — CLIProxyAPI runbook (install, OAuth, smoke tests, gotchas).
  - `/home/mk/projects/Sylveste/apps/Auraken/integrations/hermes/test-conversations.md` — Phase 2 acceptance scenarios.
  - `/home/mk/projects/Sylveste/apps/Auraken/integrations/hermes/skills/auraken/SKILL.md` — the personality.
  - `/home/mk/projects/Sylveste/apps/Auraken/integrations/hermes/mcp-servers/auraken-lens/` — shipped MCP server.
  - `/home/mk/projects/Sylveste/apps/Auraken/research/hermes-agent/` — vendored Hermes at cfa87e7 (origin/main is 4876 commits ahead; pulling main unlikely to fix codex bugs).
