# Systems Thinking Review: Dual-Mode Plugin Architecture

**Source document:** `/root/projects/Interverse/docs/brainstorms/2026-02-20-dual-mode-plugin-architecture-brainstorm.md`
**Review type:** fd-systems (Flux-drive Systems Thinking)
**Gate output:** `/root/projects/Interverse/.clavain/quality-gates/fd-systems.md`
**Date:** 2026-02-20

---

## Overview

The dual-mode architecture brainstorm proposes a three-layer plugin model (Standalone Core, Ecosystem Integration, Orchestrated Mode), a shared SDK (`interbase.sh`) vendored into each plugin at publish time, an integration manifest extension to `plugin.json`, and a companion nudge protocol. The document is coherent at the implementation level. It correctly diagnoses the current pain (ad-hoc guards duplicated across 20+ plugins) and proposes a well-structured remedy.

The systems review identifies four material gaps and two enrichment opportunities. The two highest-severity findings concern (1) a compounding version drift loop that the document misframes as a static question, and (2) a reductionist assumption about testing that does not hold in an emergent multi-plugin environment.

---

## Findings

### S-01 — P1 | Version Drift Is a Compounding Loop, Not a Static Distribution

**Section:** "Key Decisions — 3. Shared Integration SDK (interbase)" + Open Question 5
**Lenses:** Compounding Loops, Behavior Over Time Graph

The document treats interbase.sh version skew as a snapshot question: "when a plugin ships v1.2 but the ecosystem has moved to v1.5, is each-plugin-ships-what-it-ships sufficient?" This frames the problem as a point-in-time variance when it is actually a reinforcing feedback loop.

**The causal chain:**

Plugins with high ecosystem integration (interphase, intercore-adjacent) publish frequently because kernel events are their primary value. Their interbase.sh advances rapidly. Plugins with high standalone percentage (tldr-swinton at 100%, interfluence at 95%, interstat at 70%) publish infrequently because their core value does not depend on interbase.sh. Their interbase.sh accumulates drift relative to the ecosystem. Over time, the plugins most likely to be installed standalone are exactly those that ship the most stale interbase.sh.

The `interbump` mechanism updates interbase.sh only at publish time. This is the correct mechanism, but it creates a feedback loop where the publish frequency differential between ecosystem-heavy and standalone-heavy plugins grows monotonically. At T=0 all plugins are synchronized. At T=6mo interphase might be on v1.4 while tldr-swinton is still on v1.1. At T=12mo, `ib_emit_event` argument signatures may have diverged.

The failure mode is not a crash — it is silent capability degradation when a standalone user later installs a companion. A standalone user's interflux (interbase.sh v1.1) and their newly installed interphase (interbase.sh v1.4) are both loaded in the same Claude Code session. Both call `ib_in_sprint` but with different internal implementations. The user sees inconsistent behavior that is undiagnosable from outside the plugins.

**Key question:** What mechanism detects that a running plugin's vendored interbase.sh is significantly version-lagged, and surfaces that during session start rather than silently degrading?

---

### S-02 — P1 | "Test Interbase Once, Trust It Everywhere" Assumes Aggregate Behavior Mirrors Individual Behavior

**Section:** "Key Decisions — 5. Testing Architecture"
**Lenses:** Simple Rules, Emergence

The document claims: "The `interbase.sh` guards are the single point of failure isolation — if they work correctly, all plugins degrade correctly. Test interbase once, trust it everywhere."

This is a reductionist claim in an emergent system. Each plugin adds local rules on top of interbase.sh: conditional sourcing, guard overrides for specific code paths, layered additional checks. The aggregate behavior of 20+ plugins each applying local rules to a shared base script is not predictable from testing the base in isolation.

Consider three concrete examples from the existing plugin set:
- interflux's design decision: "Phase tracking is the caller's responsibility — interflux commands do not source lib-gates.sh." If interflux similarly overrides or skips certain interbase.sh guards, the isolation contract breaks.
- interlock's join-flag gating: "all hooks check `~/.config/clavain/intermute-joined`". This is a local guard that interacts with interbase.sh's `ib_in_ecosystem()` check. The combination is not tested by testing either in isolation.
- interstat at 70% standalone calls `ib_emit_event` for sprint budget integration. If interstat's vendored interbase.sh version differs from the ic CLI version in the ecosystem, the silent-return-0 guard swallows the incompatibility.

The per-plugin test matrix (`test-standalone.sh`, `test-integrated.sh`, `test-degradation.sh`) is correct and necessary. But the claim that it is sufficient because interbase.sh is tested once in isolation is not warranted by the architecture. The session-level emergent behavior — multiple plugins with potentially different interbase.sh versions active simultaneously — is not covered.

**Key question:** Are session-level integration tests planned that verify the behavior of two or more plugins loaded simultaneously with different interbase.sh versions?

---

### S-03 — P2 | The Intermod Alternative Inverts the Failure Mode, Not Eliminates It

**Section:** "Open Questions" (the intermod question is implicit, not directly addressed in the document)
**Lenses:** Hysteresis, Schelling Traps, Pace Layers

The document justifies vendoring over a centralized shared folder on two grounds: no install-order problem, and no dependency resolution in Claude Code. The intermod alternative (centralized shared folder analogous to the Claude Code plugin cache) is not analyzed for its distinct systems dynamics.

**Vendoring vs. centralized intermod — failure mode comparison:**

Under vendoring: failure mode is drift in space (each plugin carries its own version, failures are localized to individual plugins, rollback is per-plugin publish). This is S-01 above.

Under a centralized intermod: failure mode is synchronization in time. A breaking change to the shared interbase.sh immediately changes the behavior of all installed plugins without any plugin author having reviewed or tested the change. A single bad commit to intermod takes down all 20+ plugins simultaneously. Recovery requires pushing a fix to the centralized location — no per-plugin rollback is possible.

This is a Schelling trap: each individual plugin author rationally prefers centralized intermod because it eliminates drift and reduces maintenance burden. But the collective outcome is worse — the ecosystem becomes a single point of failure for every plugin in every user's Claude Code session.

The hysteresis question is absent from the document: once 20+ plugins are installed and depend on a centralized intermod, what is the cost of reverting to vendoring? Each plugin publisher must re-vendor at their next release, creating a transition period where some plugins use the old centralized path and others use the new vendored path. That window is the highest-risk period for behavioral inconsistency.

**The stronger argument for vendoring** (not made in the document) is the failure-localization argument: vendoring localizes failures in space (one plugin has a stale interbase.sh) whereas centralization concentrates them in time (all plugins break together on every breaking interbase.sh change). This framing also clarifies the hybrid: centralized for additive/backward-compatible changes (safe to roll forward), vendored for breaking changes (safe to roll back per-plugin).

---

### S-04 — P2 | The Three-Layer Model Conflates Pace-Medium and Pace-Fast Elements

**Section:** "Key Decisions — 1. The Three-Layer Plugin Model"
**Lens:** Pace Layers

The three layers (Standalone Core, Ecosystem Integration, Orchestrated Mode) are defined by feature scope, not by rate of change. Pace layer analysis requires identifying which layers change at different speeds and verifying that fast layers are built on slow foundations — not the reverse.

**Natural pace layers in the Interverse ecosystem:**
- Slow: The kernel event bus, `ic` CLI protocol, bead schema — these are foundational and should be stable across months
- Medium: interbase.sh guard functions and ecosystem detection — these update when the kernel evolves (weeks to months)
- Fast: Individual plugin features, companion nudge text, discovery hints — these update when plugin authors ship (days to weeks)

The document's Layer 2 (Ecosystem Integration) conflates pace-medium and pace-fast elements. Phase tracking via interphase is pace-medium (tied to the kernel protocol). Companion nudges — the text "install interphase for automatic phase tracking after reviews" — are pace-fast (marketing copy that should be updatable without a kernel release). Both are bundled in vendored interbase.sh.

**The consequence:** updating the nudge text for interflux requires a full `interbump` publish cycle, even though the nudge is pure cosmetic text. The fast layer (nudge copy) is now coupled to the medium layer (interbase.sh) at every publish. This is a pace layer inversion.

**Suggested separation:** `interbase-core.sh` (guards, ecosystem detection — pace-medium/slow) and inline plugin strings or a separate `interbase-nudge.sh` (nudge text — pace-fast). This would allow nudge text to be updated per-plugin without triggering an interbase.sh version bump, and would reduce the coupling surface that drives the version drift loop in S-01.

---

### S-05 — P2 | The Nudge Protocol Has an Uninvestigated Aggregate Cobra Effect

**Section:** "Key Decisions — 4. Companion Nudge Protocol"
**Lenses:** Causal Graph, Unintended Consequences

The nudge protocol is designed to drive companion installation. The intended causal chain: user runs plugin → nudge appears → user installs companion → ecosystem adoption grows.

**The uninvestigated reverse chain:** nudge appears repeatedly → user associates plugin with nagging → user disables or uninstalls plugin → ecosystem adoption falls.

The document applies one safeguard: "once per session, not per invocation." But it does not specify:
1. Whether nudges expire after N sessions without user action (a user who has seen 20 nudges for interphase and not installed it has probably made a deliberate choice)
2. Whether "once per session" means once-per-companion or once-total (two recommended companions = two stderr lines per session from one plugin)
3. The session-level aggregate when multiple plugins each nudge independently

**The aggregate nudge calculation:** If a user installs 5 plugins and each has 2 recommended companions not installed, the per-session nudge volume is up to 10 stderr lines. The document's "unobtrusive" characterization assumes a small installed base. It does not hold at 10+ installed plugins with 2-3 missing companions each. The nudge volume scales as O(plugins * missing_companions), not as a constant.

**The cobra effect risk:** An aggressive nudge protocol could suppress the standalone adoption it is designed to promote. Users who install a plugin and immediately see nudges to install more plugins may disengage before experiencing the standalone value.

**Key question:** Is there a session-level nudge coordinator that enforces a total nudge budget across all installed plugins, or does each plugin independently decide to nudge?

---

### S-06 — P3 | Low-Standalone Plugins Have No Designed Crumple Zone During the Transition Period

**Section:** "Key Decisions — 6. Per-Plugin Standalone Assessment"
**Lenses:** Hysteresis, Crumple Zones

The document identifies interlock (30%), interphase (20%), and interline (40%) as needing improved standalone value. The recommended action is to build meaningful local-only modes. This is correct but ignores the transition dynamics.

A user who installs interlock today gets a poor standalone experience and may form a lasting negative impression before the standalone mode is improved. If they review the plugin in the marketplace, that negative signal persists after the quality improves. This is hysteresis in reputation: user perception does not return to neutral when plugin quality improves. The document's option "(a) don't publish it standalone" for interlock implicitly acknowledges the risk but does not frame it as a hysteresis problem requiring a designed solution.

**Missing crumple zone design:** When a low-standalone plugin is installed without ecosystem dependencies, instead of silently providing degraded functionality, it should aggressively route the user toward the integrated value prop: show a companion discovery screen, provide one-command install instructions for the key dependency, and make the integrated value tangible before the user forms their standalone impression. The nudge protocol partly serves this role but is not connected to the standalone-percentage assessment in the document.

---

## Summary Table

| ID | Severity | Lens(es) | Section | Key Risk |
|----|----------|----------|---------|----------|
| S-01 | P1 | Compounding Loops, BOTG | interbase vendoring | Version drift is a reinforcing loop, not a static variance — slow-publishing standalone plugins accumulate skew monotonically |
| S-02 | P1 | Simple Rules, Emergence | Testing architecture | "Test interbase once" assumes no local overrides — session-level emergent behavior with multiple plugins is untested |
| S-03 | P2 | Hysteresis, Schelling Traps, Pace Layers | Intermod alternative | Centralization inverts but does not eliminate the failure mode — the stronger vendoring argument (failure localization) is not made |
| S-04 | P2 | Pace Layers | Three-layer model | Layer 2 conflates medium-pace (guards) and fast-pace (nudge text) — creates unnecessary coupling and amplifies S-01 drift |
| S-05 | P2 | Causal Graph, Cobra Effect | Nudge protocol | Aggregate nudge volume scales with installed plugins and missing companions — no session-level cap or expiration mechanism |
| S-06 | P3 | Hysteresis, Crumple Zones | Standalone assessment | Low-standalone plugins have no designed transition state — reputation hysteresis will persist after quality improves |

---

## Relationship to Other Agents

- S-01 and S-02 have technical implementation implications — defer to fd-architecture for the interbase.sh versioning and session-level test design
- S-05 (nudge aggregate volume) has a correctness dimension if the session temp file tracking is per-plugin without a shared namespace — defer to fd-correctness
- S-06 crumple zone design is a product concern — defer to fd-user-product if that agent is run

**NOTE:** MCP server unavailable — review used fallback lens subset (12/288 lenses). Install interlens-mcp for full coverage.
