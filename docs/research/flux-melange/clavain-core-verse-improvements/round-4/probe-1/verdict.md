# f-151 Verdict: intercache MCP auto-start — demote or prove?

**Lens:** fd-menu-engineering-triage (every item earns its slot against demand AND cost data; retirement is a success outcome)

**VERDICT: DEMOTE.** Remove intercache from the default-install path (rig `mcp` profile) and make the MCP server opt-in. Zero consumers found after exhaustive search; cost is measured and per-session.

---

## Demand evidence (all negative)

1. **Usage telemetry — the decisive number.** `~/.claude.json → pluginUsage`:
   - `intercache@interagency-marketplace`: `usageCount: 0` across **20,852 startups**
   - `intercache@inline`: `usageCount: 0` across 20,864 startups
   - The plugin has been installed and auto-started ~20k times and no component of it has ever recorded a use.
2. **No code callers.** Grep for all 8 exposed tool names (`cache_lookup`, `cache_store`, `cache_invalidate`, `cache_warm`, `cache_stats`, `session_track`, `session_diff`, `cache_purge`), the MCP namespace (`mcp__intercache`, `mcp__plugin_intercache`), the launcher (`launch-intercache`, `intercache-mcp`), and the store path (`.intercache`) across all of Sylveste — excluding intercache itself — returns only docs, brainstorms, plans, sprint transcripts, and one inventory test fixture. No skill, command, hook, agent, or script invokes any tool.
3. **The store has never existed.** `~/.intercache` does not exist on this machine (0 files). The server has never persisted a blob. A cache with no writes and no reads is not a cache.
4. **Proposed consumers never landed.** The brainstorm (`docs/brainstorms/2026-02-23-intercache-brainstorm.md:81-85`) specified three integrations: tldr-swinton read-through, Clavain SessionStart `cache_warm`, and git post-commit invalidation. None exist in code. The shipped `hooks/post-commit.sh` is a stub — it checks `command -v intercache-mcp` and merely echoes; it never calls the server, isn't registered in `plugin.json`, and isn't installed into any repo.
5. **Who COULD query it:** the tool surface (hash-validated file-content cache, session read-tracking, embeddings) is designed for agent read-dedup — tldr-swinton and Clavain session lifecycle are the natural fits. But "could" has been true since 2026-02-23 without a single wire being connected.
6. **Installed, not chosen.** The only Clavain references are install machinery: `agent-rig.json` `mcp` profile (line ~257), `scripts/install-codex-interverse.sh:118`, `commands/setup.md:88`. Demand is manufactured by the installer.

## Cost evidence (measured, not estimated)

From `docs/research/mcp-cold-start-breakdown-2026-04-18.md` (4/4 runs, April 2026):

- **401ms p50 cold start** (372–422ms), rank #10 of 17 timed servers — bash launcher → `uv run intercache-mcp`
- **36MB RSS** per session, one process per Claude Code session
- **8 tool schemas** injected into the deferred tool list every session
- Multiplied by 20,852 startups ≈ **2.3 hours of cumulative session-start latency** and ~750 GB·sessions of resident memory, spent on a server that was never called
- The launcher exits 0 silently if `uv` is missing, so the cost is invisible either way — no error ever surfaces the waste.

## Why not PROVE / why not REPOSITION

- **PROVE:** no consumer could be named. The evidence above is the search.
- **REPOSITION was considered** (the capability — content-addressed cross-session read cache — is genuinely well-built: 1,200 LOC, real tests, path-traversal guards). But reposition requires a placement with a pull, and the two natural placements have both already failed to materialize in 5+ months: tldr-swinton never adopted read-through, and Clavain's SessionStart never called `cache_warm`. A puzzle piece nobody has reached for since February is not "mis-placed" — it is un-ordered. Demote now; re-listing is cheap the day a real consumer is wired. Per the lens: **retirement from the default menu is the success outcome**, not an admission of failure.

## Fleet MCP pattern (worth more than the single plugin)

Cross-referencing every interverse `plugin.json` `mcpServers` block against `installed_plugins.json` and `pluginUsage` telemetry:

**Installed, auto-starting MCP servers with usageCount = 0 — 6 total:**

| Server | Cold start p50 | RSS | Note |
|--------|---------------:|----:|------|
| intercache | 401ms | 36MB | this probe |
| interdeep | 779ms | 38MB | heaviest zero-demand Python server (trafilatura+playwright imports) |
| tldr-swinton `tldr-code` | 519ms | 42MB | CLI heavily used; the MCP variant never |
| tuivision | 190ms | 97MB | heaviest RSS of the six |
| interlens | 59ms | 60MB | cheap to start, expensive to hold |
| intermap | 3ms | 8MB | near-free; launcher also broken (go not on PATH) |

Aggregate: **~1,950ms p50 and ~281MB RSS of zero-demand session-start cost** per session. Caveat on method: `usageCount` counts any plugin component use, so `==0` is conservative (over-inclusive for "plugin unused," exact for "nothing in the plugin earned demand"). Plugins with usageCount > 0 (interject, interrank, intersearch, interknow/qmd, interfluence, interflux, interkasten, interlab, interlock, intermux) may still have unconsumed MCP servers — telemetry can't distinguish — but they at least have plugin-level demand. A further 22 installed interverse plugins have usageCount = 0 without MCP servers (menu clutter, not process cost). The pattern is systemic: the rig installs the full menu by default, and roughly a third of it has never been ordered.

## f-156 add-on: interbrowse demand signage

interbrowse is installed (marketplace + inline) and its signage is genuinely good — `plugin.json` carries 8 registered commands, 8 skills, 2 agents, and keyword-rich description ("ux-teardown", "competitive-analysis", "a11y-audit"). Discoverability is not the problem. Demand is: `usageCount: 0` for the marketplace entry across 20,852 startups, `1` for the inline entry. Exactly one documented consumer exists anywhere in Sylveste: cujgel invokes `interbrowse:teardown` (`interverse/cujgel/README.md:36`, `interverse/cujgel/prompts/02-teardown.md:8`), and the platform-feedback doc names it among "25 plugins that survive up-stack." So: well-signposted, referenced by one sibling plugin, essentially unordered by users. Unlike intercache it has no MCP server, so its cost is menu clutter only — keep it installed (the cujgel pull is real), but treat it as a demand-generation problem (no top-of-funnel command in Clavain points to it) rather than a cost problem.

## REMEDIATION

REMEDIATION: remove `intercache@interagency-marketplace` from the `mcp` profile in `os/Clavain/agent-rig.json` (~line 257) and from the plugin list in `os/Clavain/scripts/install-codex-interverse.sh:118`; mark it "opt-in — install manually if you wire a consumer" in `os/Clavain/commands/setup.md:88`; then apply the same demote-or-wire test to the other five zero-demand MCP servers (interdeep, tldr-code, tuivision, interlens, intermap) for a combined ~2s p50 session-start and ~281MB RSS recovery; keep intercache the plugin published — re-listing requires one named, wired consumer (the tldr-swinton read-through from the original brainstorm is the candidate).
