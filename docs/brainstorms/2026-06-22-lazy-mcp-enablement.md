---
date: 2026-06-22
bead: sylveste-krop
spike: D (per-project / per-skill lazy MCP enablement)
status: scoping
companion_measurement: docs/research/mcp-cold-start-breakdown-2026-04-18.md (spike C, sylveste-116u)
related_beads: [sylveste-7505, sylveste-x6e4, sylveste-116u]
verified_against:
  - ~/.claude/settings.json (enabledPlugins, mcpServers)
  - ~/.claude/plugins/cache/interagency-marketplace/interdev/0.2.0/skills/working-with-claude-code/references/settings.md
  - ~/projects/Sylveste/**/.claude-plugin/plugin.json (17 enabled + MCP-declaring)
---

# Per-project / per-skill lazy MCP enablement — design spike D

## What was asked

Scope what it would take to make MCP server loading lazy or per-project-filtered, so a
session only pays the startup cost (cold-start wall time + RSS) for servers it actually
needs. The bead poses three concrete sub-questions:

1. What does `~/.claude/settings.json` support for MCP server filtering?
2. Is there a hook/capability to disable a server per-project without removing the plugin?
3. Skill-level activation — only load (e.g.) `tldr-swinton` when a skill that needs it fires?

This doc answers all three against the actual config surface and pairs the answer with the
spike-C cold-start data, then states a testable hypothesis + kill rule for any follow-on.

## Bottom line up front

- The **cost is real and already measured**: 17 enabled plugins declare MCP servers in this
  environment (verified: cross-ref of `enabledPlugins:true` × `plugin.json` with `mcpServers`).
  Spike C measured ~6.2 s cumulative cold-start, ~1.2 s parallel-bound, **~970 MB RSS**.
- **Sub-question 1 — partial native support, wrong target.** The settings keys
  `enabledMcpjsonServers` / `disabledMcpjsonServers` / `enableAllProjectMcpServers` govern
  **only `.mcp.json`-defined servers** (project-scoped approval gating). They do **not** apply
  to plugin-declared (`plugin.json`→`mcpServers`) servers, which is where all 17 live. So the
  obvious-looking knob does not touch the actual cost.
- **Sub-question 2 — YES, a coarse lever exists today, no new code.** `enabledPlugins` is a
  `{"plugin@marketplace": bool}` map that is honored at **project scope**
  (`.claude/settings.json`) as well as user scope. Setting a plugin to `false` in a project's
  settings disables that plugin **and its MCP server**. This is the cheapest win and needs zero
  loader changes — but it is plugin-granular, not server-granular: you lose the plugin's
  commands and skills too.
- **Sub-question 3 — NO native mechanism.** Skill-triggered MCP activation does not exist.
  MCP servers spawn at session start, before any skill fires. There is no documented hook
  (`SessionStart` runs *after* MCP launch and cannot retroactively suppress a server). This
  sub-question is **out of reach without Claude Code core changes** and should be dropped from
  scope, not designed around.

**Recommendation: this is a settings-only quick win (project-scope `enabledPlugins` deny-lists)
plus one small measurement, NOT an architectural project.** The "lazy loading" framing
(sub-questions 1 and 3) is largely moot against the current harness; the durable win is a
curated per-project plugin allow-list, and that is mostly a documentation + defaults exercise.

## Mechanism inventory (verified, file:line)

### What settings.json actually supports

From `working-with-claude-code/references/settings.md` (interdev 0.2.0 cache):

| Key | Scope it touches | Applies to plugin MCP servers? |
|-----|------------------|-------------------------------|
| `enableAllProjectMcpServers` | `.mcp.json` servers | No |
| `enabledMcpjsonServers` | `.mcp.json` servers (allow) | No |
| `disabledMcpjsonServers` | `.mcp.json` servers (deny) | No |
| `allowedMcpServers` / `deniedMcpServers` | **managed-settings.json only** (enterprise) | Yes, but enterprise-only, all-scope |
| `useEnterpriseMcpConfigOnly` | managed-settings.json | restricts to managed-mcp.json |
| `enabledPlugins` | user **and** project `.claude/settings.json` | **Yes (whole plugin on/off)** |

Two load-bearing facts verified locally:

- `~/.claude/settings.json` has `mcpServers` with only 3 user-scope entries (`oracle`,
  `lowbeer`, `mcp_agent_mail`). The other 17 come from plugins, not user MCP config — so the
  `*Mcpjson*` keys are irrelevant to them.
- `enabledPlugins` in `~/.claude/settings.json` is a dict of 80 entries
  (`"name@marketplace": bool`), already used to disable plugins (e.g.
  `claude-md-management@... : false`). The reference doc confirms this key is valid in
  **project** `.claude/settings.json` too. This is the existing per-project lever.

### The interesting non-obvious option: `deniedMcpServers`

`deniedMcpServers` *does* deny by server name across all scopes — but it is documented as a
**managed-settings.json** (enterprise/admin) key. On a single-developer machine it could be
abused as a per-machine global denylist, but it is **not per-project** and is admin-scoped,
so it does not serve the spike's goal. Worth a one-line empirical check (does Claude Code honor
it in user settings.json?) but do not design around it.

## The one real unknown — and it is the whole spike

Both this scoping and the spike-C doc converge on a single empirical gap (spike C line 289,
333): **how many of the 17 servers does a typical session actually invoke?**

Everything downstream depends on this number:

- If a typical session uses **3–5** servers → a curated per-project `enabledPlugins` denylist
  cuts ~70% of the 970 MB RSS and most of the cold-start with zero code. Clear win.
- If sessions use **10+** servers, or usage is unpredictable across projects → per-project
  curation saves little and risks "tool not available when I needed it" friction. The win
  evaporates and the right answer is the spike-C server-side fixes (R1/R2/R3: Go launcher fix,
  interrank lazy-load, npx→install) which help *all* sessions regardless.

This is directly measurable from existing telemetry — `~/.claude/interstat/metrics.db` and
session transcripts record `mcp__*` tool calls per session. No new instrumentation needed;
just an aggregation query over recent sessions.

## Testable hypothesis

> **Across a representative sample of recent Sylveste sessions, the median session invokes
> ≤5 distinct MCP servers, and the per-project set of invoked servers is stable enough that a
> hand-curated `enabledPlugins` denylist in `.claude/settings.json` would suppress ≥8 of the 17
> servers for that project without removing any server the project's sessions actually call.**

If true: ship per-project `enabledPlugins` denylists (settings-only), document the pattern,
done. If false: lazy/per-project enablement is the wrong lever; redirect effort to the
spike-C server-side cold-start fixes which are project-agnostic.

## Pre-registered KILL RULE (Phase-1 measurement first)

Per platform doctrine (test-null-hypothesis-first), Phase 1 is a **measurement, not a build**:

**Phase 1 (hours):** Query `~/.claude/interstat/metrics.db` (and/or `intersearch`/cass session
index) for `mcp__<server>__*` tool-call counts grouped by session and by project, over the
last 30 days or ~50 sessions. Produce: (a) distribution of distinct-servers-per-session, (b)
per-project invoked-server set, (c) the count of "loaded but never invoked" servers per session.

**KILL conditions — close `sylveste-krop` and do NOT build per-project tooling if ANY hold:**

1. **Median session invokes >7 distinct MCP servers** → per-project curation can't suppress
   enough to matter; the cost is broadly distributed. Redirect to spike-C R1/R2/R3 instead.
2. **Per-project invoked-set instability** — the set of servers a project uses varies so much
   session-to-session that any static denylist would, in >20% of sessions, suppress a server
   that session then needs → friction cost exceeds the RSS/startup saving.
3. **The session-perf pain is not reproducible** — if a fresh cold-start measurement on current
   hardware (M5 Max 128GB) shows parallel-bound start <800 ms and RSS headroom is ample (it is:
   970 MB on a 128 GB box is <1%), then there is **no user-perceptible problem to solve** and
   the spike is moot regardless of server counts.

Kill condition 3 is the most likely trap: the original "6/14 servers disconnected mid-work"
observation (2026-04-18) was on a *constrained* environment. On the user's 128 GB workstation,
970 MB of MCP RSS is noise. **If the only beneficiary is a memory-constrained cloud/CI sandbox,
say so explicitly and scope it to that, not to the daily-driver workstation.**

## Method (if Phase 1 passes the kill gate)

1. **Settings-only deliverable (days, not weeks):** For the 2–3 highest-traffic project roots,
   write a curated `.claude/settings.json` `enabledPlugins` block that disables MCP-declaring
   plugins the project's sessions never invoke. Validate by launching a session in that project
   and confirming (a) the suppressed servers don't spawn (`ps`/`pgrep`), (b) no skill or command
   the project relies on breaks (the plugin loss is the cost — confirm it's acceptable).
2. **Document the pattern** in AGENTS.md / a short ops note: "to trim MCP cost per project, add
   an `enabledPlugins` denylist; note it disables the whole plugin, not just its server."
3. **Optional, only if plugin-loss is unacceptable for some plugin:** file an upstream feature
   request for server-granular plugin MCP toggling (a `disabledPluginMcpServers` analog to
   `disabledMcpjsonServers`). This is a Claude Code core ask, not a Sylveste build — track it,
   don't build it.

## Effort

- Phase 1 measurement: **hours** (one telemetry query + a fresh cold-start re-measure on M5 Max).
- Phase 2 settings rollout (only if it survives the gate): **days** (curate + validate 2–3
  project denylists, write the ops note).
- Skill-level lazy activation (sub-question 3): **not scoped** — no native mechanism; would be
  a Claude Code core change. Explicitly out of scope.

## Honest recommendation: park

Lean toward **park**, bordering on likely-moot, for three reasons:

1. **The expensive interpretations are already foreclosed.** Sub-question 1's settings keys
   don't touch plugin servers; sub-question 3 has no mechanism. What remains (sub-question 2)
   is a coarse `enabledPlugins` denylist that needs no design spike — it needs a 30-line
   settings block once someone confirms the per-project usage pattern.
2. **The companion measurement (spike C) already did the hard part** and concluded the bigger,
   project-agnostic wins are server-side (R1 Go launcher fix, R2 interrank lazy-load, R3
   npx→install). Those help every session and don't carry the "plugin disappeared when I needed
   it" failure mode. If session-perf is the real goal, those beads should jump the queue ahead
   of per-project curation.
3. **Kill-condition 3 is probably already met on the user's hardware.** 970 MB RSS on 128 GB
   and a ~1.2 s parallelized cold-start are not a daily-driver problem. The genuine beneficiary
   is the ephemeral cloud sandbox — and for that, a single global "minimal MCP" project profile
   beats per-project curation.

Net: don't run a multi-week project. Run the **Phase-1 telemetry query** (a few hours). If it
shows a clean 3–5-server median with stable per-project sets *and* there's a real
memory-constrained target, ship the settings-only denylist. Otherwise close `sylveste-krop`
MOOT and route session-perf energy to spike-C R1/R2/R3.
