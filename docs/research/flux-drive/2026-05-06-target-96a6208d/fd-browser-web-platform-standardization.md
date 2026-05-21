<!-- flux-drive:complete -->
<!-- run_uuid: 8c99a137-eefe-4344-9430-c945afe281c1 -->
<!-- agent: fd-browser-web-platform-standardization -->

# fd-browser-web-platform-standardization — Findings

## Findings Index
- F-B1 (P0): AGENTS.md absorbed without WHATWG-style cross-vendor governance — vendor-prefix fragmentation imminent
- F-B2 (P0): No Origin Trial equivalent for risky primitives — ossification or churn, no middle path
- F-B3 (P1): Hook protocol and MCP shape are the obvious cross-vendor candidates, but document lists only AGENTS.md
- F-B4 (P1): No polyfill viability for older Claude Code versions — forced upgrade cliff per primitive
- F-B5 (P2): "Two interoperable implementations" rule never invoked — primitives ship before there's evidence the shape works
- F-B6 (P3): Deprecation runway for displaced plugins is unspecified

## Verdict
The target's strategic angle (target line 39: "open-sourced or standardized cross-vendor (e.g., AGENTS.md across Codex/Cursor/Gemini)") names the right opportunity but treats it as one item among many. Three primitives in the prior-7 are cross-vendor standardization candidates, not Claude-Code-only absorptions. Conflating them costs the ecosystem the standards play.

## Summary
The browser-engine arc has a clean playbook: feature lives as **vendor-prefixed extension** → graduates to **vendor-prefix-removed but vendor-only** → graduates to **two-implementation interop** → becomes **WHATWG/W3C standard** with deprecation runway for the displaced extension. The target document collapses these stages into one: "Anthropic absorbs the primitive." Without staging, two failure modes follow:

1. **Fragmentation by vendor** (the vendor-prefixed CSS era, 2008-2014) — Anthropic ships AGENTS.md; Cursor ships `.cursor/agents.md`; Codex ships `codex.md`. Each is *almost* the same. Plugin authors write 3x adapters. Users pick a vendor instead of composing them.
2. **Ossification before validation** — A primitive ships in CC v3.0 with a shape that hasn't been pressure-tested; CC v4.0 needs to break it but can't because plugin authors built against it. Compare: HTML's `<marquee>` and `<blink>` are eternal because removing them breaks pages.

The Origin Trial mechanism (Chrome's time-boxed, opt-in, instrumented preview) is the missing layer in the target document. It's how browsers ship risky primitives in production without committing to their shape. Anthropic's equivalent would be: "this primitive is in trial through CC vN+2; the API can change between point releases; trial telemetry feeds shape decisions."

## Issues Found

### F-B1 (P0): AGENTS.md absorbed Claude-only fragments the cross-vendor agent ecosystem

**Where:** target line 25 ("Managed AGENTS.md / CLAUDE.md surface") and line 39 (strategic-angle prompt)
**Failure scenario:** Anthropic ships native AGENTS.md management in Claude Code v3.0 with a specific shape (frontmatter schema, section ordering, harmonization rules). The shape works for CC. Cursor reads AGENTS.md too — but its shape needs are slightly different (Cursor has different agent-spawn semantics, different memory boundaries). Cursor ships its own variant. Codex/Gemini do likewise. The result is a four-way fragmentation where plugin authors maintain four parallel agent-doc files with subtly different schemas. The vendor-prefixed CSS era took six years to recover from. The agent-doc fragmentation could take longer because there's no WHATWG to drive convergence.
**Smallest fix:** Before shipping, Anthropic publishes the AGENTS.md schema as an RFC at `agentsmd.org` (or equivalent), invites Cursor/Codex/Gemini participation, and commits to adopting any spec changes that emerge from cross-vendor consensus. The interdoc plugin already does cross-AI compatible generation (target line 78) — Anthropic standardizing locks in compatibility; Anthropic absorbing without standardizing breaks it.
**Question:** Is there an active or proposed cross-vendor working group for agent-config files that the target document hasn't surfaced? If so, shape the absorption around its output. If not, the absorption window is also the standards-creation window.

### F-B2 (P0): No Origin Trial equivalent — primitives ship before validation

**Where:** target document is silent on this; success criteria (target lines 154-161) don't require it
**Failure scenario:** Anthropic ships "first-class parallel agent fleet" (target line 20) in CC v3.0 with a fan-out shape derived from internal use cases. Three months later, ecosystem feedback reveals that the orchestrator-of-orchestrators pattern (which interflux supports via flux-review's track-of-tracks) doesn't fit the shipped shape. CC v3.1 needs to extend the API. But plugin authors are already on v3.0. CC commits to backward compat (good), which means the v3.0 shape is forever (bad). This is the WebSocket-vs-Server-Sent-Events trap: ship one before you know which workloads matter, and you carry the wrong one forever.
**Smallest fix:** For each prior-7 primitive, ship in **trial mode** for the first 2-3 release cycles: API guarded by a `--enable-trial` flag, telemetry instrumented, explicit "may change between releases" warning. Plugin authors can build against trial APIs but understand the contract. Chrome's Origin Trials run 6-9 months; CC equivalent could run 3-6 months given faster release cadence.
**Question:** Does Anthropic's release cadence support trial periods, or is the v3.0/v3.1 distance too short to validate before committing?

### F-B3 (P1): Hook protocol and MCP shape are cross-vendor standards material

**Where:** target line 25 names AGENTS.md as the cross-vendor candidate; the broader list is missing
**Failure scenario:** Anthropic absorbs hook-protocol and MCP-shape as Claude-Code-specific ergonomics. Cursor and Codex implement their own hook systems. The 63-plugin Sylveste ecosystem can't run on Cursor without 63 ports. Plugin marketplace economics break: every plugin must pick a vendor lane. This is the iOS-vs-Android API divergence applied to agent platforms.
**Smallest fix:** Add hook-protocol and MCP-shape to the cross-vendor standardization list. MCP is already partly there (Anthropic published the spec). Hook protocol is the next obvious candidate — it's structurally identical to browser extension event hooks, which converged via WebExtensions API. Shape the standardization the same way: shared API + per-vendor implementation + extension-format compatibility.
**Question:** Is MCP truly multi-vendor today (Cursor + Anthropic + others actually implementing it), or is Anthropic the only implementer with the spec published as a fig leaf?

### F-B4 (P1): No polyfill viability — forced upgrade cliff per primitive

**Where:** target document doesn't address backward compatibility; absorption implies "new CC version, new primitive"
**Failure scenario:** A team is on CC v2.x for stability reasons (regulated industry, locked toolchain). CC v3.0 ships native parallel-fleet. The team's interflux plugin still works on v3.0 but is now redundant — except they can't get the native version's quality without upgrading. Polyfill path: interflux runs on v2.x and emulates the v3.0 native API so v3.0-built plugins also work on v2.x. Without this path, the ecosystem fragments by version (CC-v2-plugins vs CC-v3-plugins).
**Smallest fix:** For each absorbed primitive, document what a polyfill would need (which APIs to shim, what fidelity is achievable, what's strictly impossible). Let plugin authors maintain the polyfill on older CC. Web ecosystem precedent: core-js, modernizr, regenerator-runtime — third-party polyfills extended browser features back to older versions for a decade.
**Question:** Are the prior-7 primitives polyfillable in principle (so the substrate can backport them) or do they require host privileges (so polyfilling is impossible and cliff-upgrade is the only path)?

### F-B5 (P2): "Two interoperable implementations" rule never invoked

**Where:** target line 17 (single-perspective survey) → line 33 (multi-track review)
**What's missing:** WHATWG's discipline: a feature isn't a standard until two browsers ship it interoperably. For Claude Code primitives, the equivalent test is: *has this been implemented twice (in plugins or by competitors) and converged on a shape?* Of the prior-7:
- Memory: yes, six implementations (intermem/intercache/interknow/interseed/interlearn/intertree) — divergent shapes, no convergence yet → **not yet standards-ready**
- Parallel fleet: yes, four implementations (interflux/intersynth/interpeer/intermonk) — partial convergence on triage+dispatch → **shape is coalescing**
- Multi-session coordination: yes, three implementations (interlock/intermux/intertrack) — convergent on file-reservation pattern → **standards-ready**
- Cost/observability: yes, four implementations (interstat/intercept/interpulse/tool-time) — convergent on hook-based collection → **standards-ready**
- Code recon: one (tldr-swinton) — **not standards-ready, single implementation**
- Task tracker: zero in Sylveste (TodoWrite is built-in, target line 24) — **no convergence yet**
- AGENTS.md: yes, four implementations (interdoc/interscribe/interwatch/intermem) — convergent on harmonization pattern → **standards-ready**

**Implication:** Prioritize absorption of the convergent ones (multi-session coordination, observability, AGENTS.md). Defer the divergent ones (memory, code recon, task tracker) until shape converges in the substrate.
**Smallest fix:** Add a column to the prior-7 table: "Convergence signal" (count of substrate implementations + shape similarity score). Use it to sequence absorption.

### F-B6 (P3): Deprecation runway for displaced plugins unspecified

**Where:** target lines 19-25 (each absorption listed without a runway)
**What's missing:** When `<marquee>` was deprecated, browsers gave authors years of warning before removing rendering support. When Chrome deprecated SyncXHR-on-page-unload, Origin Trials measured impact and the runway was sized to that data. The target document deprecates 30+ plugins implicitly — but doesn't spec the runway any displaced plugin gets to migrate users, gracefully sunset, or pivot to a residual niche.
**Smallest fix:** Each absorbed primitive ships with a `DISPLACED_PLUGINS.md` listing affected plugins, the migration path users should take, and the recommended sunset window for the displaced plugin (e.g., 12 months of co-existence before flagging as redundant).

## Improvements
- The phrase "deprecates plugin X" (target lines 19-25) is too binary. Replace with "supersedes" + a spec for what shape of competing plugin survives. Web Platform precedent: when CSS Grid shipped, jQuery's grid-emulation libraries didn't all die — flexbox-fallback and IE11-fallback variants survived for years on a residual-niche basis.
- Add an explicit "standards posture" section: which primitives Anthropic should publish as cross-vendor specs, which ship as CC-only ergonomics, which are vendor-prefixed (CC-only but shaped to portable later).
- The "What gets deprecated" framing in the prior-7 list (target lines 19-25) is the absorption-side; pair it with "What gets standardized" so the cross-vendor opportunity isn't lost.
- Cite WebExtensions API as the precedent for unified plugin-protocol across competing engines — exactly the play the agent-platform ecosystem needs and currently lacks.
