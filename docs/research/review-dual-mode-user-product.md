# User & Product Review — Dual-Mode Plugin Architecture Brainstorm

Reviewer: fd-user-product
Date: 2026-02-20
Source: /root/projects/Interverse/docs/brainstorms/2026-02-20-dual-mode-plugin-architecture-brainstorm.md

---

## Primary User Definition

Two distinct users exist simultaneously, and the brainstorm knows this. The review evaluates whether the proposed architecture serves both honestly.

**User A — Standalone discoverer.** A developer who browses the interagency marketplace, sees "interflux: multi-agent code review engine," installs it, and expects it to work. Their job is: get better code reviews without buying into a platform. They have no Clavain, no beads, no ic. They have never heard of Interverse.

**User B — Integrated operator.** A developer already running Clavain with two or more companion plugins, who adds another module mid-sprint. Their job is: extend an existing workflow without surprising breakage or needing to re-learn what is "active."

The brainstorm explicitly serves both. The review examines whether it succeeds at each.

---

## 1. Standalone User Journey

### The Positive Case

The brainstorm's Layer 1 concept is sound in principle. If interflux delivers genuine multi-agent code review with zero dependency on beads/ic/Clavain, a standalone user gets real value. The interflux plugin.json description is reasonably honest: "17 agents (12 review + 5 research), 3 commands, 2 skills, 2 MCP servers. Companion plugin for Clavain." The phrase "Companion plugin for Clavain" appears in the plugin.json but NOT in the marketplace listing description, which stops at "7 review agents, 2 commands, 1 skill, 1 MCP server." Note the marketplace description is already stale relative to the plugin.json (7 agents vs 17, 1 skill vs 2, 1 MCP server vs 2) — a concrete trust problem before even addressing the dual-mode question.

The 90% standalone assessment for interflux reads as plausible. The MCP servers (qmd for semantic search, Exa for research) are already structured as progressive enhancements — interflux's CLAUDE.md confirms that Exa is optional with a fallback. A standalone user installing interflux and running a review would likely get working output.

### Where the Journey Breaks Down

**The nudge protocol is not designed for its actual trigger moment.** The brainstorm specifies nudging via stderr during hook execution. Claude Code's UI presents hook stderr output differently from agent response text — it may appear as a warning, a diagnostic, or be suppressed depending on the hook event type and Claude Code version. The brainstorm does not address the rendering context. A nudge that appears as a faint diagnostic blurb during a session-start hook, before the user has even run their first review, teaches nothing. A nudge that fires during or immediately after the user's first successful use, while they are still evaluating the plugin, has a chance of being read. The protocol specifies "once per session" and "via stderr" but does not specify the triggering event — session start vs. first invocation vs. first review completion.

**"Once per session" is too conservative and also potentially too aggressive.** For a standalone user who gets good value from interflux alone, a daily nudge about interphase is noise that degrades their experience over time. For a user who just installed interflux and had their first review, once per session might mean they see the nudge zero times in their first week if the plugin only nudges at session start and they use the tool mid-session. The nudge protocol needs a trigger event, not just a frequency cap.

**The integration manifest is machine-readable but not user-readable.** The brainstorm proposes adding an `"integration"` section to plugin.json. This is good for tooling. It is invisible to users browsing the marketplace today. If the marketplace listing does not surface what Layer 2 features unlock, a standalone user has no signal that their experience is intentionally partial. They experience it as "this plugin doesn't do phase tracking" rather than "this plugin can do phase tracking if you install interphase." The gap between the machine-readable manifest and the user-visible marketplace copy is unaddressed.

**The EXA_API_KEY dependency creates a first-use cliff.** The marketplace listing for interflux does not mention the EXA_API_KEY requirement. A standalone user who installs interflux and lacks this key will experience Exa silently not working, with an undocumented fallback to Context7 + WebSearch. They may not notice the degradation; they may think the research agents are slower or worse than described. This is a concrete example of a missing onboarding state the brainstorm does not mention.

**Retention signal is absent.** The brainstorm identifies the discoverability gap problem but does not propose a measurable success signal for standalone retention. How would we know if standalone users are getting enough value to keep the plugin installed? The "genuinely useful alone" design constraint is stated but not operationalized. A success criterion like "user invokes the plugin at least twice in 7 days" would give the architecture a testable outcome.

---

## 2. Integrated User Journey — Three-Layer Confusion Risk

### The Core Confusion Pattern

The brainstorm establishes Layer 1 (standalone core), Layer 2 (ecosystem integration), and Layer 3 (orchestrated mode). These layers are architectural concepts for the builder. They are not surfaced to the user in any way. A user running Clavain + interflux + interphase + interwatch has no interface that tells them which layer is active for any given plugin at any given moment.

**Concrete scenario:** A user installs interflux while mid-sprint. They run a review. The review completes. Did phase tracking fire? Did a bead get linked? Did interwatch auto-trigger? If it worked, they don't know what happened. If it silently failed because the ic run context wasn't detected, they don't know that either. The three layers create invisible state that the user cannot inspect.

The brainstorm proposes the integration manifest for discoverability and the session-start ecosystem status as optional outputs. But "optional" is the wrong word if the goal is to prevent confusion. The absence of a clear active/inactive indicator for each integration point is the gap that will generate support questions.

**The interphase CLAUDE.md reveals an existing version of this problem.** interphase communicates with interline via a sideband file (`~/.interband/interphase/bead/${session_id}.json`). The interline statusline is the only user-visible indicator of phase state. A user who has interphase but not interline sees no indication that phase tracking is running. A user who has neither sees nothing. A user who has both sees the statusline. This is three different states with no user-facing explanation of which one they are in — precisely the three-layer confusion pattern applied to a production plugin pair.

**The brainstorm does not address the "partial ecosystem" state during a session.** A user mid-sprint who has beads but no ic, or ic but no Clavain, is in an undefined zone between Layer 2 and Layer 3. The ad-hoc guards (`ib_has_ic()`, `ib_in_ecosystem()`) correctly fail-open, but "fail-open" means "silently do nothing" — the user gets no signal that the integration layer they expected is not active.

### Layer 3 Creates a Category Error

Layer 3 (orchestrated mode) is only meaningful if the user understands that Clavain is the orchestrator and individual plugins are not running their own gate enforcement. A user who installs interflux after using Clavain may try to use the interflux `/flux-drive` command directly during a sprint, bypassing Clavain's sprint routing. The result is a review that produces findings but does not participate in the sprint gate system. From the user's perspective, the review "worked." From the ecosystem's perspective, the gate was not enforced. This is a workflow divergence the brainstorm identifies as a benefit (standalone always works) but does not flag as a failure mode for integrated users.

### What Would Help

A session-start summary of active integrations — "interflux: standalone core + interphase integration active, intercore not detected" — addresses this directly. The brainstorm raises this as an open question about nudge aggressiveness. It should be a requirement, not an open question, for the integrated user journey.

---

## 3. The Intermod Alternative

The user's question: "Why not have a shared folder (like ~/.intermod/) where shared Interverse modules live, and plugins discover them there, rather than vendoring?"

### What Intermod Would Actually Be

`~/.intermod/` would be a shared directory where common library files (interbase.sh, shared helpers, integration stubs) are installed once and referenced by multiple plugins. Plugins would discover them at runtime via a known path convention, rather than bundling a copy at publish time.

This mirrors how `~/.claude/plugins/cache/` works for the plugin manifests themselves, or how Python's `site-packages` works for shared libraries. It is a legitimate pattern.

### For the Standalone User: Intermod Is Worse

The vendoring approach is the right call for standalone users, and the brainstorm's reasoning is correct: a standalone user who installs interflux gets a complete, self-contained plugin. They do not need to know that interbase.sh exists. They do not need to install a separate "intermod" package to unlock it.

An intermod folder that the user must populate creates a new category of install failure. If `~/.intermod/interbase.sh` is missing, the plugin either crashes or silently degrades — identical to the current ad-hoc guard problem the brainstorm is trying to solve. The user-facing error ("intermod not found, falling back to stub") is not better than the current ("bd: command not found" swallowed silently).

Discoverability of the intermod convention would require marketplace documentation that does not currently exist and that the Claude Code plugin schema does not support. There is no `"sharedDependencies"` field in plugin.json. The user installing interflux would have no signal that `~/.intermod/` exists or matters.

### For the Integrated User: Intermod Has One Real Benefit

The one scenario where intermod wins is version skew management between integrated users. If 15 plugins all vendor interbase.sh v1.2, and interbase.sh is updated to v1.5, the integrated user has 15 different interbase versions running simultaneously. The brainstorm's open question #5 identifies this directly. An intermod folder with a single canonical interbase.sh copy means the integrated user updates once and all plugins benefit.

However, this benefit only matters if interbase.sh has meaningful version divergence behavior — if v1.5 is backward-incompatible with v1.2. For a library that is 30-50 lines of shell guards, this seems unlikely in the near term. The version skew risk is real but low-probability for the actual interbase.sh being proposed.

### Verdict on Intermod

Vendoring is correct for standalone users. The version-skew argument for intermod is worth revisiting if interbase.sh grows beyond a few dozen lines and accumulates breaking changes. The right time to revisit is when the first interbase.sh incompatibility actually occurs, not preemptively. Building the intermod infrastructure now would add installation complexity (who installs ~/.intermod? what bootstraps it?) without a demonstrated need.

If the architecture wants to hedge, the cleanest option is: vendor interbase.sh now, but write it with a self-detection stub that checks for `~/.intermod/interbase.sh` first and falls back to the bundled copy. This gives intermod adoption a path without mandating it.

---

## 4. Standalone % Assessment Honesty

### The Ratings Table

| Plugin | Brainstorm Rating | Assessment |
|--------|------------------|------------|
| tldr-swinton | 100% | Honest. The plugin is genuinely self-contained. |
| interflux | 90% | Plausible but potentially generous. The 10% loss is phase tracking and sprint gates — advanced features that most new users won't miss immediately. Honest for initial use; the gap may widen as users try to integrate with workflows. |
| interwatch | 75% | Plausible. Drift detection works standalone. Bead filing and auto-refresh via interpath are real integrations that provide meaningful additional value. |
| interfluence | 95% | Honest. Voice profiling is genuinely self-contained. |
| interject | 90% | Probably generous. Bead creation for findings is described as the integrated feature, but the research engine's actual value — ambient scanning that surfaces actionable findings — depends on a place to put those findings. Without beads or Notion, findings go to stdout and are likely forgotten. Might be 70-75% in practice. |
| interstat | 70% | Honest. Token measurement works standalone; sprint budget integration provides meaningful context for measurement results. |
| interlock | 30% | The most honest number in the table, and the most important finding. |
| interphase | 20% | Honest. The plugin's own CLAUDE.md says "observability only — functions never enforce or block." Without beads, there is nothing to observe. |
| interline | 40% | Honest. The statusline shows "nothing interesting" without bead context. |

### The Interlock Problem Is a Marketplace Trust Issue

The interlock marketplace listing reads: "Multi-agent file coordination — reserve files before editing, detect conflicts, exchange messages between agents. MCP server wrapping intermute with hooks, commands, skills, and git pre-commit enforcement. Companion plugin for Clavain."

The phrase "MCP server wrapping intermute" is the tell. A standalone user who installs interlock and does not have intermute running will find that every MCP tool call fails. The interlock plugin.json hardcodes `INTERMUTE_SOCKET=/var/run/intermute.sock` and `INTERMUTE_URL=http://127.0.0.1:7338`. Without intermute, the MCP server connects to nothing. The "companion plugin for Clavain" label is present but easy to read as "works with Clavain, also works alone." That is not the case.

The interlock CLAUDE.md confirms: "Join-flag gating: all hooks check ~/.config/clavain/intermute-joined." This means every hook silently no-ops without the intermute join. A standalone user gets a plugin that installs cleanly, shows 11 MCP tools, and then does nothing useful when called without intermute.

**Would a user installing interlock feel misled?** Yes, if they read the marketplace listing as describing what the plugin does by itself. The listing describes the feature set (file coordination, conflict detection, messaging) without indicating that all of it requires a running service (intermute) that is not described, not in the marketplace as a separate install, and not automatically started by the plugin. The brainstorm's four options for the interlock problem (don't publish standalone, build local mode, mark ecosystem-only, or accept the 30%) need resolution before the plugin remains on the marketplace with current copy.

The cleanest fix is marking it explicitly in the marketplace listing: "Requires intermute service (part of the Clavain ecosystem). Install Clavain first." This is honest and lets users self-select.

### Interphase at 20% Should Trigger a Different Question

Interphase at 20% standalone means the brainstorm is essentially acknowledging this plugin should not be installed without Clavain or beads. Yet it is on the marketplace as a standalone plugin. The marketplace description says "Companion plugin for Clavain — adds lifecycle state management on top of the core beads plugin." That is clear. What is unclear is why a user would install interphase directly rather than installing Clavain (which pulls it as a companion).

The 20% standalone plugins are essentially ecosystem-internal components that happen to be distributed individually. Publishing them as standalone marketplace items creates the expectation of standalone utility. The honest product decision is either to build the standalone value (the brainstorm correctly identifies "interphase should provide lightweight phase tracking even without beads") or to gate marketplace visibility behind "also install Clavain."

---

## 5. Discoverability Gap — Does the Integration Manifest + Nudge Protocol Actually Solve It?

### What the Brainstorm Claims

The integration manifest in plugin.json serves three purposes: discoverability (tooling can suggest missing companions), documentation (users see what they gain), and testing (integration matrix is explicit). The nudge protocol delivers one-time companion suggestions at runtime via stderr.

### What It Actually Solves

The integration manifest solves the **tooling discoverability problem**. If `/doctor` or a marketplace UI reads the manifest and says "install interphase for phase tracking," that is a meaningful improvement over the current silence. The manifest is a necessary condition.

The nudge protocol solves the **in-session discoverability problem for users who are already using the plugin**. A user mid-session who has been using interflux for a week and sees "install interphase for automatic phase tracking after reviews" has context to act on it.

### What It Does Not Solve

**Pre-install discoverability.** A user browsing the marketplace today sees the description string. They do not see the integration manifest. They do not know what Layer 2 features exist before installing. The brainstorm assumes the marketplace UI will evolve to consume the manifest, but that evolution is not planned or described. The marketplace listing for interflux in the current marketplace.json still says "7 review agents" when the plugin has 17. Manifest drift is already a problem.

**The ecosystem entry point.** A user who finds interflux finds one review plugin. They do not find a "start here" landing page for the Interverse ecosystem. Clavain is on the marketplace, but there is no signal in interflux's listing that Clavain is the recommended starting point for ecosystem users. The brainstorm frames "Companion plugin for Clavain" as the label, but this label is underspecified: does "companion" mean "works better with" or "requires"?

**Nudge delivery reliability.** The brainstorm specifies stderr hook output. If the nudge fires in a `UserPromptSubmit` hook or `SessionStart` hook, the user may see it as a system message. If it fires in a `Stop` hook, it appears at the end of a session when the user is done reading. The brainstorm does not specify hook event context for nudges, so the implementation will choose one, and it may choose wrong.

**The nudge acknowledgment loop.** "Once per session" with a session temp file means the state is lost between sessions. A user who has seen the nudge 30 times will see it again tomorrow. The brainstorm should specify a durable (not temp-file) nudge dismissal mechanism — either a config file in `~/.config/interverse/nudges-dismissed` or a companion detection check that stops nudging once the companion is installed. The "once per session" rule implies nudges are always appropriate for non-integrated users, which degrades the experience for users who have made an informed decision not to install companions.

**Actionability.** The nudge says "install interphase for automatic phase tracking after reviews." The user now needs to know how to install interphase. In a Claude Code session, the answer is `/plugin install interphase`, but this is not in the nudge text. A nudge that does not include the action instruction is noise.

### Summary of Discoverability Gap Status

The integration manifest is a necessary building block that does not yet exist. The nudge protocol is a runtime complement with insufficient specification for the delivery context, frequency policy, and action instruction. Together they address about half the discoverability problem. The other half — pre-install marketplace clarity, ecosystem entry point, and manifest-to-listing parity — is unaddressed.

---

## Flow Analysis

### Standalone Install Flow — Missing States

1. User installs interflux from marketplace
2. MCP servers start (qmd, exa-mcp-server)
3. **Missing: EXA_API_KEY check** — what does the user see if Exa fails to start? Does `npx -y exa-mcp-server` fail silently or with an error the user sees?
4. User runs `/flux-drive` review
5. **Missing: first-use onboarding state** — no "here's what just happened" output describing what agents ran and what integrations are available
6. Review completes with findings
7. **Missing: companion nudge trigger event** — the brainstorm does not specify when during this flow the nudge fires
8. User closes session — nudge state is in temp file, lost

The happy path for standalone interflux probably works. The error paths (missing API key, MCP server startup failure, first-use confusion) are undefined.

### Integrated Install Flow — Missing States

1. User with Clavain + interphase installs interflux mid-sprint
2. interflux installs and starts MCP servers
3. **Missing: ecosystem detection on first load** — does interflux detect the ecosystem state on session start, or only on first invocation?
4. User runs `/flux-drive` review inside a Clavain sprint
5. **Missing: gate integration signal** — does the review output indicate whether sprint gate enforcement fired?
6. Review completes
7. **Missing: bead-linked findings confirmation** — if bead linking happened, does the user know? If it didn't, do they know why?

### Cancellation / Abandonment Paths

The brainstorm does not address what happens when a nudge fires and the user cannot act on it (e.g., they are on a corporate machine where they cannot install new plugins, or the companion plugin is not available). The nudge should degrade to a URL or documentation reference, not repeat indefinitely.

---

## Findings Summary

### Blocking Issues (would prevent confident release)

**UP-01. Interlock marketplace listing does not match standalone value.** A user installing interlock without intermute gets a non-functional plugin with no error guidance. The marketplace listing must indicate the intermute dependency or the plugin must be marked ecosystem-only. This is a trust problem that will generate negative first-impressions.

**UP-02. The nudge protocol is underspecified for delivery context.** No trigger event, no durable dismissal, no action instruction in nudge text. The current specification would produce a nudge that appears at an undefined moment, repeats indefinitely, and gives the user no actionable next step.

**UP-03. Marketplace listing for interflux is stale.** The marketplace.json still says "7 review agents, 1 skill, 1 MCP server" while the actual plugin has 17 agents, 2 skills, and 2 MCP servers. If the integration manifest exists in plugin.json but marketplace.json is not regenerated from it, the manifest is worthless for pre-install discoverability.

### Significant Issues (should be addressed before rollout)

**UP-04. No user-visible integration status for Layer 2/3 transitions.** An integrated user has no way to know which integrations are active for a given plugin in a given session. The session-start ecosystem summary should be a requirement for the integrated user journey, not an open question.

**UP-05. Interphase at 20% and interlock at 30% are in the marketplace without standalone value justifying the listing.** The brainstorm correctly identifies this as a problem and lists options. A decision is required before the dual-mode architecture is implemented, because the architecture cannot fix a plugin that has no standalone mode.

**UP-06. Interject's 90% standalone assessment is too generous.** The research engine produces findings that have nowhere to go without beads or a persistent store. Standalone interject produces stdout output that users likely cannot act on systematically. A realistic assessment is closer to 70%.

**UP-07. Pre-install discoverability is not addressed.** The integration manifest helps tooling but requires marketplace UI evolution that is not described or planned. Today's user sees only the description string.

### Improvements (desirable but not blocking)

**UP-08. Intermod hedging.** Vendoring is correct now. Write interbase.sh with a `~/.intermod/` self-detection check as a forward-compatibility measure so intermod adoption has a migration path without a flag day.

**UP-09. Nudge should include the install command.** "install interphase for automatic phase tracking after reviews — run `/plugin install interphase`" is actionable. "install interphase" is not.

**UP-10. Durable nudge dismissal.** Replace temp-file session tracking with a `~/.config/interverse/nudge-state.json` that persists across sessions and stops nudging once a companion is installed or the user has dismissed the nudge explicitly.

**UP-11. First-use output for standalone users.** The first review completion should output a concise summary: "Review complete. X agents ran. Available integrations: install interphase for phase tracking, interwatch for drift monitoring." This is the highest-value discoverability moment and the current specification misses it entirely.

---

## Evidence Assessment

- The standalone value assessments are stated as percentages with no user research backing them. They read as honest builder intuition, which is appropriate for a brainstorm. However, interlock at 30% and interphase at 20% are not brainstorm estimates — they are product decisions that should be treated as such before implementation.
- The claim "Standalone must be genuinely useful — Not a demo version" is a design constraint, not a validated outcome. No evidence is cited that standalone users have been tested or that the Layer 1 features produce the kind of value that drives retention.
- The discoverability gap is well-diagnosed. The proposed solutions (manifest + nudges) are plausible but underspecified. The brainstorm would benefit from a single user test: install interflux fresh, run a review, and observe what the user knows vs. does not know about available integrations.

---

## Verdict

The dual-mode architecture is the right direction. The vendoring approach is correct. The integration manifest is a necessary foundation. The nudge protocol concept is sound but needs a complete specification before implementation.

The blocking issue before this architecture is built is the interlock/interphase marketplace listing problem. The architecture cannot fix a plugin whose standalone mode does not exist — it can only wrap it in a better-specified degradation pattern. The standalone % table is the most honest part of the brainstorm, and acting on it (either building standalone modes or re-listing ecosystem-only plugins accurately) is the prerequisite work.

**Recommended next step:** Before implementing interbase.sh or the integration manifest, resolve interlock's marketplace listing and define the interphase standalone value proposition. These are product decisions that take one day to make and prevent the architecture from being built on a false premise.
