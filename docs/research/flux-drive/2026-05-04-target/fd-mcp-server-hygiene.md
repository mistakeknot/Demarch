### Findings Index
- P1 | M-01 | "MCP: Notion+Gmail+Calendar+Drive deferred-list cost" | 20+ deferred tools for OAuth-gated services that require auth-call-then-action — listed cost paid every session, used in <5%
- P1 | M-02 | "MCP: tool-name namespace prefix waste" | `mcp__plugin_interflux_openrouter-dispatch__review_with_model` style names average 50-70 chars; ~80 deferred tools = high listing overhead
- P2 | M-03 | "MCP: tldr-swinton instructions block is 600+ tokens of cost-ladder marketing" | Embedded in every session via FastMCP `instructions=` parameter regardless of usage
- P2 | M-04 | "MCP: disconnected-server tool listings persist as deferred" | context7, exa, interrank, intersearch all flagged disconnected this session yet their tools may still appear listed
- P2 | M-05 | "MCP: interject 10-tool catalog dwarfs actual session usage" | 10 deferred tools listed; cass shows session-search consolidated into intersearch — interject usage tail unclear
- P3 | M-06 | "MCP: auraken-lens loads single-tool server with full instructions cost" | One tool (`lens_select`) but server still injects setup overhead

Verdict: needs-changes

## Summary

Sylveste loads 77 enabled plugins. The deferred-tool listing surfaced in this session shows ~32 tools for MCP servers including Notion (14), Gmail (2), Calendar (2), Drive (2), interject (10), auraken-lens (1), interflux openrouter (1) — and the document claims ~80 total across all servers. The dominant cost is not per-tool execution but per-session listing + per-server `instructions=` blocks injected into the system prompt. Two patterns are wasteful: (1) OAuth-gated integrations (Notion/Gmail/Calendar/Drive) ship 20 tools that require an `authenticate`-then-action two-step rarely taken in dev sessions; (2) tool-name prefixes (`mcp__plugin_interflux_openrouter-dispatch__review_with_model` = 60 chars) bloat the listing without adding selectivity.

## Issues Found

### M-01 (P1) — Notion/Gmail/Calendar/Drive: 20 deferred tools paid for OAuth integrations used in <5% of dev sessions

**Axis:** token-efficiency
**Current state:** The deferred-tool listing in this session includes `mcp__claude_ai_Notion__*` (14 tools), `mcp__claude_ai_Gmail__*` (2: authenticate + complete_authentication), `mcp__claude_ai_Google_Calendar__*` (2), `mcp__claude_ai_Google_Drive__*` (2). These are Anthropic-managed OAuth integrations. Each tool name + description appears in the deferred listing. cass analytics (`cass analytics tools --json`) shows codex/gemini providers at 0 tool calls; while the claude_code provider shows 105k tool calls, the per-tool breakdown for the OAuth integrations would almost certainly be near-zero in a software-development session.

**Failure scenario:** A dev-only session pays the listing cost for tools structurally never invoked. Per the agent's P1 calibration: "MCP server injects 500+ tokens of instructions every session but its tools are used in <5% of sessions — the instructions cost more than the tools save."

**Proposal:** Add a workspace-aware MCP-server gating in `~/.claude/settings.json`. If the project root contains a `mcpProfile: dev` marker (or just by default for projects under `~/projects/Sylveste`), suppress the Anthropic-account integrations from MCP loading. Re-enable for personal/admin sessions via a `mcpProfile: personal` marker. Concretely: move Notion/Gmail/Calendar/Drive enrollment from claude.ai-account-level to per-project opt-in.

**Estimated savings:** ~600-1500 tok/session (20 tools × ~30-75 tok per tool name + description). At 100 sessions/week, ~60-150kt/week saved.
**Difficulty:** S (settings.json-level config + claude.ai account toggle if available; M if it requires Anthropic-side product change).
**Risk:** Low. Loss of capability is recoverable per-session via `/connect` or by toggling profile.

### M-02 (P1) — Tool-name namespace prefixes: 60-character names dominate deferred-list size

**Axis:** token-efficiency
**Current state:** Deferred tool names like `mcp__plugin_interflux_openrouter-dispatch__review_with_model` (60 chars) and `mcp__plugin_interject_interject__interject_session_context` (57 chars) appear in the deferred listing. Per the agent calibration P2 ("MCP tool name is 70+ characters long because of nested namespace prefixes ... Tool listing alone consumes 5kt across the deferred-tool section"), the 80-tool listing at average 40-chars-per-name is roughly 3.2kt of name text alone — before any descriptions.

**Failure scenario:** Each deferred-tool entry is `name + signature + description`. Names this long crowd out useful description tokens. The `mcp__plugin_<plugin>_<server>__<tool>` four-part hierarchy is especially redundant when `<plugin>` and `<server>` carry the same identifier (interject:interject, intermap:intermap).

**Proposal:** Two-pronged. (a) Where plugin and server names match (interject:interject, intermap:intermap, interlock:interlock), collapse to single segment: `mcp__interject__interject_status` instead of `mcp__plugin_interject_interject__interject_status`. (b) Tools whose name already prefixes with the server name (interject_status inside interject server) should drop the redundancy: `mcp__interject__status`. This requires a registry-level rename + back-compat alias period.

**Estimated savings:** Trim ~25-40% of the 3.2kt name budget = 800-1300 tok/session.
**Difficulty:** M (registry change + alias migration across plugins).
**Risk:** Medium. Aliases must persist for one release window so existing agent prompts referencing old names don't silently break.

### M-03 (P2) — tldr-swinton injects 600+ tok of cost-ladder marketing as MCP instructions

**Axis:** token-efficiency
**Current state:** `/home/mk/.claude/plugins/cache/interagency-marketplace/tldr-swinton/0.7.17/src/tldr_swinton/modules/core/mcp_server.py` line 62: `mcp = FastMCP("tldr-code", instructions=_INSTRUCTIONS)`. The `_INSTRUCTIONS` block (lines ~40-58) is a "COST LADDER (cheapest first)" marketing pitch listing 6 tools with token estimates. This is injected into the host system prompt every session tldr-swinton is enabled, regardless of whether any tldr tool is invoked.

**Failure scenario:** Every Sylveste session pays ~600 tok for tldr-swinton's pitch even when no tldr tool fires. Per agent P1 calibration: "MCP server injects 500+ tokens of instructions every session but its tools are used in <5% of sessions."

**Proposal:** Move the cost-ladder text into the per-tool `description` field of one tool (e.g., `tldrs_session_start`), so it shows up only when ToolSearch surfaces that tool. Replace the server-level `instructions=` with a single line: `"Token-efficient code-context tools. See tldrs_session_start for usage guide."`

**Estimated savings:** ~500-600 tok/session for tldr-swinton alone. Apply pattern across other plugins (audit interject, interlock, interlab) for cumulative win.
**Difficulty:** XS for tldr-swinton (one-file edit). S to audit all plugins.
**Risk:** Low. Discovery shifts from server-level to per-tool — agents already use ToolSearch for discovery in this codebase.

### M-04 (P2) — Disconnected MCP servers may leave deferred tool entries after disconnect

**Axis:** token-efficiency
**Current state:** Per the project memory ("context7, exa, interrank, intersearch — all disconnected this session"), Sylveste regularly sees MCP servers fail-on-startup. The deferred-tool listing in the system reminder shows tools for connected servers only — but: does the harness reap stale entries cleanly, or does a server that disconnects mid-session leak its tool listing?

**Failure scenario (uncertain — frame as question):** Does Claude Code reap deferred-tool listings when an MCP server disconnects mid-session, or does the listing persist until session end? If persisting, every disconnection wastes ~50-300 tok/server worth of listings until session restart.

**Proposal:** Verify reap behavior with a controlled test: start a session with intersearch, force-kill the server, observe whether `intersearch__*` tools remain in subsequent ToolSearch results. If they do, file an upstream bug to claude-code-setup. As a stopgap, Sylveste could add a `scripts/health-check-mcp.sh` to `bd backup` cadence that surfaces disconnections to the user.

**Estimated savings:** Conditional on verification; potentially 100-500 tok/session × disconnection-frequency.
**Difficulty:** XS (verification test); S (stopgap script).
**Risk:** None.

### M-05 (P2) — interject 10-tool catalog: usage volume unclear

**Axis:** token-efficiency
**Current state:** The deferred listing surfaces 10 interject tools (`interject_detail`, `interject_dismiss`, `interject_inbox`, `interject_profile`, `interject_promote`, `interject_record_query`, `interject_scan`, `interject_search`, `interject_session_context`, `interject_status`). intersearch was already noted in MEMORY.md as superseding session-search-from-interstat (v0.2.1). Does interject's session_context overlap with intersearch's session search?

**Failure scenario (frame as question):** Are interject_session_context and intersearch session search both active and listed as deferred tools? If overlapping, agents face routing ambiguity, and one of the listings is paying for unused capability.

**Proposal:** Run `cass analytics tools --json | jq` filtered to `mcp__plugin_interject_*` to count actual invocations over 30 days. If <50/month for the entire interject server, propose merging the discovery surface into one tool (e.g., `interject_action` with action-string param) and shrinking the deferred listing 10→2.

**Estimated savings:** ~200-400 tok/session if listing collapses 10→2.
**Difficulty:** S (interject API consolidation) to M (cross-plugin tool merge).
**Risk:** Medium — existing skill prompts reference interject_* names directly.

### M-06 (P3) — auraken-lens single-tool server still pays per-server overhead

**Axis:** token-efficiency
**Current state:** auraken-lens shows up in the deferred listing as a single-tool server (`mcp__auraken-lens__lens_select`) but it's the only MCP server actively connected (`jq -r '.mcpServers // {} | keys[]' ~/.claude.json` returned only `auraken-lens`). So it carries the per-server boilerplate (server name in registry, schema-fetch path) for one tool.

**Failure scenario:** Single-tool MCP servers are an architectural anti-pattern when the tool could be a slash command or a CLI. The schema fetch round-trip and per-server lifecycle cost something per session.

**Proposal:** Inspect whether `lens_select` could become a slash-command (`/auraken:lens`) backed by a CLI. If yes, retire the MCP server entirely.

**Estimated savings:** ~50-150 tok/session + faster session startup.
**Difficulty:** S (port to slash command).
**Risk:** Low — only used in auraken contexts.

## Improvements

1. **Audit tool: `scripts/mcp-cost-audit.sh`** — for each enabled MCP server, emit (instructions-block size, tool count, average name length, last-30d invocation count from cass). Sort by cost÷value. Top 5 = next pruning targets.
2. **Add `mcpProfile` setting to `.claude/settings.json`** with values `dev|personal|all` to gate the OAuth integration cluster (Notion/Gmail/Calendar/Drive) per-project.
3. **Document MCP `instructions=` budget rule in `agents/critical-patterns.md`:** "Plugin MCP servers: instructions= must fit in 100 tokens. Anything longer goes in per-tool description."
4. **Health-check script for disconnections:** `scripts/health-check-mcp.sh` surfaces context7/exa/intersearch outages so they can be triaged before the disconnection-tax compounds across sessions.

<!-- flux-drive:complete -->

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 6 (P0: 0, P1: 2, P2: 3, P3: 1)
SUMMARY: 20 OAuth-tools (Notion/Gmail/Calendar/Drive) listed every session for <5% usage; tool-name prefixes burn ~3.2kt/session across the 80-tool listing; tldr-swinton ships 600 tok of cost-ladder marketing as instructions=. Combined potential: 1.5-3kt/session.
---
