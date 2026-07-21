---
artifact_type: research
bead: Sylveste-b15
goal: 7b585d72
stage: digest
---

# Claude Code Capability Digest #1 — 2.1 Series → Sylveste Opportunities

First mapping pass of the cc-changelog watcher loop (charter:
`docs/goals/2026-07-21-cc-changelog-watcher-charter.md`). Source:
`anthropics/claude-code` CHANGELOG.md fetched 2026-07-21, latest **2.1.216**;
watcher baseline recorded at that version on zklw. Scope: capability-class
entries ("Added/New/Introducing") across the 2.1 series, filtered for
Sylveste relevance. Future digests cover only the delta bead's range.

## Candidate beads filed (this pass)

| Bead | Capability (version) | Why it matters here |
|---|---|---|
| Sylveste-sqq | Hook exec-form `args: string[]` + PostToolUse `continueOnBlock` (2.1.139) | No-shell hook spawning kills the quoting/portability bug class the test-baseline goal just spent a day on; continueOnBlock lets auto-publish failures feed back to Claude for self-correction |
| Sylveste-oqo | `claude agents --json` (2.1.145), `--cwd` (2.1.141), `/resume` for bg (2.1.144) | intermux can drop scraping for a supported structured source |
| Sylveste-nko | `MessageDisplay` hook (2.1.152), `terminalSequence` (2.1.141), `subagentStatusLine` effort (2.1.214) | interline display surfaces: render-time transforms, hook-emitted desktop notifications/titles/bells, effort-aware agent rows |
| Sylveste-nwv | `claude plugin tag` (2.1.118), dependency enforcement + projected context cost (2.1.143), `plugin init` (2.1.157) | ic publish: validated release tags, encode Clavain↔companion dependencies, emit per-release context-cost figures |
| Sylveste-uiw | OTEL `workflow.run_id` (2.1.202), `agent_id`/`parent_agent_id` spans (2.1.145) | interspect routing evidence gets first-class attribution instead of transcript scraping |
| Sylveste-23k | `CLAUDE_CODE_SESSION_ID` in Bash env (2.1.132) | Sideband scripts self-key the interband envelope; simplifies Sylveste-zlc legacy-path retirement |
| Sylveste-u59 | `fallbackModel` ×3 (2.1.166), `Tool(param:value)` rules (2.1.178), `sandbox.credentials` (2.1.187) / `deniedDomains` (2.1.113) | Encode the routing degradation chain + capability-routing spawn constraints + sandbox hardening in config, not prose |

## Already adopted (no action)

- **`/goal` command (2.1.139)** — the goal-native Clavain/intercore cycle is
  built on it.
- **Dynamic workflows (2.1.154)** — flux-melange's workflow fast-path.
- **Introducing Sonnet 5 (2.1.197) / Fable 5 (2.1.170) / Opus 4.8
  (2.1.154)** — capability-routing doctrine already spans these; AgMoDB
  refresh below.

## Noted, not actioned (watch for evidence of need)

- `--safe-mode` / `disableBundledSkills` (2.1.169) — tool-time overhaul may
  want these as levers.
- `claude ultrareview` non-interactive (2.1.120) — CI-side review candidate
  once a repo wants cloud review in its pipeline.
- `alwaysLoad` MCP option (2.1.121) — deferral posture is currently right;
  revisit if a server's tool schemas prove hot-path.
- `requiredMinimumVersion` managed settings (2.1.163) — relates to the
  DISABLE_AUTOUPDATER pin strategy; revisit at next pin review.
- WebSearch/subagent session caps (2.1.212), memory-pressure reaping
  (2.1.193) — defaults look sane; flux-drive fan-outs stay under them.
- Runtime-truncation and OTEL knobs (2.1.214, 2.1.193) — pull in when
  interspect's OTEL ingestion (Sylveste-uiw) lands.

## AgMoDB refresh (this pass)

`src/lib/agent-seeds.ts` `claude-code` entry: supportedModels was missing
claude-fable-5 (2.1.170) and claude-sonnet-5 (2.1.197, now the CC default) —
both slugs live-verified against the agmodb.com models sitemap; description
updated to mention background agents and dynamic workflows. Committed on
zklw as ee1d3bb and pushed to the repo's current working branch
**self-host-pg** (mid PG-migration); the main-branch merge — which is what
auto-deploys agmodb.com — is mk's call.

## Loop mechanics (how the next digest happens)

`cc-changelog-watch.timer` (zklw, Tue 05:17 weekly) diffs the changelog
against `~/.local/state/cc-changelog-watch/last-seen` and keeps at most one
open `cc-changelog:` bead carrying the raw delta. Working that bead =
producing the next digest: map delta capabilities to plugins, file
candidate beads, refresh AgMoDB, advance this doc (or a dated sibling).
