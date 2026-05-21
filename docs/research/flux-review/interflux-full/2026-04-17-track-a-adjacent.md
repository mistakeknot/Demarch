---
artifact_type: track-findings
track: A
distance: adjacent
target: /home/mk/projects/Sylveste/interverse/interflux
target_description: interflux plugin (multi-agent review + research engine, 17 agents, 7 commands, 338 code files, 60M)
date: 2026-04-17
model: opus (review)
agents_applied_as_perspectives:
  - fd-cc-plugin-architect (Claude Code plugin architecture)
  - fd-multi-agent-orchestration (parallel agent dispatch patterns)
  - fd-python-cli-ecosystem (setuptools/pyproject, script packaging)
  - fd-mcp-integration (stdio servers, env-gated enablement)
  - fd-hook-lifecycle (SessionStart/PostToolUse patterns)
---

# Track A — Adjacent (Domain-Expert Findings)

## A-P0-1: PostToolUse hook fires on every Edit/Write in the entire session, globally

Location: `hooks/hooks.json` lines 17-38; `hooks/check-compact-drift.sh`.

The PostToolUse hooks for both `Edit` and `Write` matchers fire on every single file edit in any project the user is working in. The matcher has no path-scoping — an Edit to a file in `~/projects/SomeOtherProject/` triggers `check-compact-drift.sh`, which then attempts to stat interflux-internal paths. With a 5-second timeout per invocation, a 200-edit session pays up to 1000s of wall time (amortized, because most exits are fast), but every edit pays the fork+bash+stat latency even with no drift to check. This is the plugin-architecture version of a "hot loop" anti-pattern: a low-value diagnostic check bolted onto a high-frequency event. Scope the matcher to paths inside the interflux plugin itself (`${CLAUDE_PLUGIN_ROOT}/**`) or move it to `PreCompact` where it costs once per session.

## A-P0-2: MCP server silently exits with code 0 on missing API key

Location: `mcp-servers/openrouter-dispatch/index.ts` lines 5-9; `scripts/launch-exa.sh` (same pattern).

When `OPENROUTER_API_KEY` is unset, the server prints to stderr and then `process.exit(0)`. From Claude Code's MCP manager perspective, exit code 0 without a working stdio handshake looks like a clean shutdown, not a failure — the MCP listing shows the server as "available" but calls silently hang or return MCP transport errors. Correct convention: exit with non-zero (e.g. 78 = EX_CONFIG per sysexits) so Claude Code reports "openrouter-dispatch: unavailable (missing config)". The caller currently has no way to distinguish "MCP is down" from "MCP is up but rejecting".

## A-P1-3: `find ~/.claude/plugins/cache -path '*/clavain/*/scripts/...'` coupling is brittle

Location: `skills/flux-drive/phases/launch-codex.md` lines 9, 13, 44; `phases/launch.md` line 25; `references/progressive-enhancements.md` lines 68-69.

Every cross-plugin library source (clavain's `lib-routing.sh`, `dispatch.sh`, interspect's `lib-trust.sh`, interserve templates) resolves via globbed `find` against `~/.claude/plugins/cache`. This path is cache-managed by Claude Code (versioned by marketplace sync). Three failure modes:
1. **Version skew** — `lib-routing.sh` signature changes and interflux silently falls through to defaults without warning.
2. **Multiple versions cached** — `head -1` picks first match by filesystem order, which is non-deterministic (ext4 dir ordering).
3. **Stale cache after unpublish** — a removed clavain version still resolves until cache eviction.

Proper pattern: each companion plugin should expose a discovery manifest (e.g. `~/.claude/plugins/manifest.json`) with `api_version` that interflux checks. Or better: these shared libs should live in an `intercore` library package that all plugins depend on explicitly (the MEMORY notes this is already the pillar — but interflux bypasses it via path globbing).

## A-P1-4: Composer code path is dead on arrival but still guards logic branches

Location: `phases/launch.md` lines 17-19; Phase 0 prior findings already flagged this.

The fix already in flight is "remove Composer dead code" (deferred to Phase 4 blueprint). Adjacent-expert view: the `COMPOSER_ACTIVE=1` / `_COMPOSE_LIB_SOURCED=1` sentinel check structure appears in multiple phase files as **authoritative-when-present** branching. Removing Composer means auditing every skip-guard that depends on it — a grep across the phases directory shows at least 4 such branches. Partial removal leaves ghost conditionals that future readers must decode. This should be a single atomic change, not a gradual deprecation.

## A-P1-5: Openrouter rate-limit state is per-process, lost on every MCP launch

Location: `mcp-servers/openrouter-dispatch/index.ts` lines 11-30.

`tokenBucket` and `cumulativeSpendUsd` are in-process variables. MCP stdio servers are spawned per-session (sometimes per-tool-call, depending on Claude Code's lifecycle). A user who invokes 10 flux-review runs in a row with separate processes sees 10 × `OPENROUTER_RATE_LIMIT` requests/min — not the configured 20/min. The `SPEND_CEILING_USD` is similarly per-process, so a session-wide $1.00 ceiling is effectively unbounded across separate invocations. For real rate-limiting and real spend caps, state must persist to disk (e.g., a lock-file at `~/.config/interflux/openrouter-state.json`) and use atomic read-modify-write under flock — exactly like `findings-helper.sh` already does for JSONL appends.

## A-P2-6: Plugin description redundantly enumerates counts that drift from code

Location: `.claude-plugin/plugin.json` line 5 (description).

The description reads "17 agents (12 review + 5 research), 7 commands, 1 skill (unified flux-drive with review/research modes), 2 MCP servers (exa, openrouter-dispatch)". Prior phase findings flagged this; the adjacent-expert view adds: Claude Code surfaces this string in plugin listings and `/help` output. When counts drift, users see stale metadata in the UI itself, not just in docs. The version string is already auto-bumped by `scripts/bump-version.sh`; the counts should be auto-derived by that same script (it already enumerates files to bump versioned artifacts) and refused when they mismatch.

## A-P2-7: `hooks/hooks.json` bakes the stub path for `interbase-stub.sh` into prod

Location: `hooks/session-start.sh` line 9; `hooks/interbase-stub.sh`.

The session-start hook sources `interbase-stub.sh`, which is a no-op file. The comment says "live or stub" but no discovery logic upgrades to live when present — every session runs the stub. Either `interbase` is vestigial (delete the indirection) or the discovery mechanism is missing (add a `find ~/.claude/plugins/cache -path '*/interbase/*/lib/interbase.sh'` with fallback to stub). Dead indirection masks whether interbase even exists as a working package.

## A-P2-8: `skills/` directory still contains `flux-research/` even though manifest skips it

Location: `.claude-plugin/plugin.json` (skills array has only `./skills/flux-drive`); `skills/flux-research/` directory still present.

Prior phase finding. Adjacent expert adds: Claude Code's skill auto-discovery does NOT read from the manifest; it scans for `SKILL.md` files and registers what it finds (confirmed in the system-reminder skill list — `interflux:flux-research` is loaded). So leaving `skills/flux-research/SKILL.md` on disk means this skill loads whether the manifest says so or not. The test-dependency rationale is valid, but the skill should be renamed (e.g., `flux-research-legacy`) so its discovery side-effect is visible in the skill list.

## A-P2-9: `flux-review.md` command is 551 lines — the largest in the plugin

Location: `commands/flux-review.md`.

Flux-review is a single command file with 551 lines covering arg parsing, config merging, track count triage, track definitions, model routing tables, fan-out, fan-in, synthesis, and cost estimates. This is monolithic. The adjacent-expert pattern for large commands is to **move most of it into a skill** — the command becomes a thin dispatcher that invokes a skill. Compare: `flux-drive.md` command is 9 lines and the skill is where all the logic lives. `flux-review` is structurally misshapen — it should be a `skills/flux-review/` skill the same way flux-drive is.

## A-P2-10: Progressive-enhancement pattern has no telemetry for adoption

Location: All `references/progressive-enhancements.md` sections.

Every progressive enhancement (qmd, lib-routing, lib-interspect, intertrust, overlays) silently skips when its dependency isn't found. Valuable as a non-blocking pattern — **but** there is no signal anywhere of how often these skips happen in production. If 90% of users never have qmd installed, then the entire qmd retrieval code path is documentation dressing with zero real-world usage. Add a skip-event emit (`~/.config/interflux/enhancement-skips.jsonl`) so the maintainer can see which enhancements actually land. Without this, the progressive pattern is unfalsifiable.

## Verdict

Interflux has real plugin-architecture debt. The most serious issues are (1) an unscoped PostToolUse hook that taxes every edit globally, (2) MCP servers that exit cleanly on failure instead of signaling error, and (3) cross-plugin coupling via glob-find that has three silent-failure modes. The dead-code removals and count-drift issues are routine cleanup; the hook scoping and MCP exit-code conventions are architectural.
