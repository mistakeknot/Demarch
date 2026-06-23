# Scoping: Multi-mcpServers capability spike (sylveste-x6e4)

**Date:** 2026-06-22
**Bead:** sylveste-x6e4 — "Multi-mcpServers capability spike (prereq for sylveste-7505)"
**Type:** scope spike (do-not-run; this is the scoping pass)
**Verdict:** **likely-moot** — the hypothesis is already proven by shipping production code.

---

## What the bead asked

> Spike: prove (or disprove) that Claude Code loads multiple `mcpServers` entries
> from a single `plugin.json`. The brainstorm 2026-04-08-interserve-consolidated-mcp
> claimed interflux proves this, but flux-drive strategy review P0-1 verified
> `interverse/interflux/.claude-plugin/plugin.json` has exactly ONE entry (exa).
> Every `interverse/*/plugin.json` has exactly one. The consolidation architecture
> depends on two-entry support working. Scope: scaffold a throwaway plugin with 2
> trivial `mcpServers` entries ... verify both load and both tools appear via
> session tool introspection. Deliverable:
> `docs/research/multi-mcpservers-capability-check.md` with PASS/FAIL.
> Blocks: sylveste-7505.

## Why this is (almost certainly) already answered — verified against code

The premise that "every `interverse/*/plugin.json` has exactly one entry" was true on
**2026-04-10** when flux-drive wrote P0-1
(`docs/research/flux-drive/2026-04-10-interserve-consolidated-mcp/synthesis.md`).
It is **no longer true**. The world moved under the bead.

1. **interflux now declares TWO mcpServers entries.**
   `interverse/interflux/.claude-plugin/plugin.json` (current `main`) has both:
   - `exa` → `${CLAUDE_PLUGIN_ROOT}/scripts/launch-exa.sh` (Python/npx stdio)
   - `openrouter-dispatch` → `${CLAUDE_PLUGIN_ROOT}/scripts/launch-openrouter.sh` (Node stdio)

   These are two genuinely distinct stdio servers with separate launchers and separate
   backing processes (`scripts/launch-exa.sh` vs `scripts/launch-openrouter.sh`,
   `mcp-servers/openrouter-dispatch/dist/index.js`). Not one server exposing two tools.

2. **It was added deliberately and survived a review pass.**
   - `1134d20` feat(fluxbench): multi-model activation — OpenRouter MCP, two-phase calibrate/qualify
   - `212b547` fix(v0.2.59): Phase 0 P0/P1 findings from interflux review campaign

   So the two-entry config is not an accident; it shipped as part of fluxbench multi-model
   activation and was kept through a subsequent review campaign.

3. **Both servers load and expose tools in a live session — direct runtime evidence.**
   The deferred-tool inventory of the session that produced this doc lists BOTH:
   - `mcp__plugin_interflux_exa__web_search_exa`, `…__web_fetch_exa`
   - `mcp__plugin_interflux_openrouter-dispatch__review_with_model`

   Tools namespaced `plugin_interflux_<serverkey>_…` for two different `<serverkey>`
   values is exactly the "both load, both tools appear via introspection" PASS condition
   the bead's method describes — observed in production, not a throwaway plugin.

**Net:** the throwaway-plugin experiment would be re-deriving a fact that interflux already
demonstrates in production. The capability question is PASS.

## The testable hypothesis (restated crisply)

> H: Claude Code loads every `mcpServers` entry in a single plugin's `plugin.json` and
> exposes each server's tools, namespaced per server — i.e. N>1 entries are supported.

This is the null we want to *fail to reject* for sylveste-7505 to be unblocked.
**It is already not-rejected** by the interflux evidence above.

## Pre-registered KILL RULE (Phase-1, ~1 hour)

Per platform doctrine (test-null-hypothesis-first), before any consolidation work the
capability claim gets one cheap confirmation gate:

- **Phase-1 measurement (≤1 hr):** Confirm, on the *current Claude Code version actually
  in use*, that interflux's two-server config still resolves to two distinct namespaced
  tool sets in a fresh session (tool-introspection grep for
  `mcp__plugin_interflux_exa__*` AND `mcp__plugin_interflux_openrouter-dispatch__*`).
  Optionally `claude mcp list` / session diagnostics to confirm two processes.
- **KILL (declare MOOT, do not scaffold throwaway plugin):** if both namespaces are
  present → capability confirmed; **close sylveste-x6e4 as done/moot** and let
  sylveste-7505 proceed on the unblocked premise. This is the expected outcome.
- **PROCEED to the original throwaway-plugin spike** ONLY if Phase-1 finds interflux
  collapsed to a single namespace (e.g. a CC version regression silently dropped the
  2nd entry). That is the only world where the bead's original method earns its hour.

The kill condition is deliberately inverted from a normal spike: here the expensive work
is *justified only by disconfirming evidence*, because the confirming evidence already exists.

## Method in brief (Phase-1 only)

1. Fresh `claude` session (or read the deferred-tool list of any current session).
2. Grep tool inventory for the two interflux server namespaces.
3. If desired, `claude mcp list` to see process-level registration.
4. Record PASS/FAIL in one paragraph. No new plugin scaffolding unless FAIL.

## Effort

- **Phase-1 confirmation:** ~1 hour (mostly session spin-up + introspection).
- **Original throwaway-plugin spike (only if Phase-1 FAILs):** ~half a day.

## Important caveat that the bead's framing misses

The *real* blocker for sylveste-7505 was never P0-1. It was **P0-2** in the same synthesis:

> Five of six in-scope Python plugins use the **low-level** `mcp.server.Server` class
> (`@server.list_tools()` / `@server.call_tool()`), which supports exactly ONE
> `list_tools` and ONE `call_tool` handler per instance. The PRD's
> `server.tool(name, handler, schema=...)` adapter contract is a FastMCP idiom, not the
> low-level SDK API in use.
> (refs: `intercache/src/intercache/server.py:63-281`, `intersearch/.../server.py:23,51`,
> `interdeep/.../server.py:17-58`, `interject/.../server.py:13-31`,
> `interseed/.../server.py:12-27`)

Multi-`mcpServers` support (P0-1, this bead) is the *easy* dependency and it is already
satisfied. The adapter-multiplexing problem (P0-2) is the architecturally hard one and is
**not** addressed by this spike. Confirming P0-1 does NOT unblock sylveste-7505 on its own —
it removes one of two P0s. Any "x6e4 done → 7505 ready" handoff should explicitly carry the
P0-2 caveat forward, or 7505 restarts on the same false-confidence the consolidation
brainstorm originally had.

Worth also noting: sylveste-7505's premise — "21 MCP servers → ~6, single process" — should
be re-validated against the **current** server count and against the
`docs/research/mcp-cold-start-breakdown-2026-04-18.md` measurements before treating
consolidation as a live perf win. Several plugins now use permanently-installed binaries
(see `scripts/launch-exa.sh` header) which already shaved the npx cold-start tax that
motivated consolidation; the consolidation ROI may itself be partly moot.

## Recommendation

**likely-moot.** Do the 1-hour Phase-1 confirmation, expect PASS, close sylveste-x6e4.
Do NOT scaffold the throwaway plugin (the original method) unless Phase-1 disconfirms.
Carry the P0-2 adapter-contract caveat into any sylveste-7505 reactivation; that — not
multi-server support — is the actual gate.
