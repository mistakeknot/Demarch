<!-- flux-drive:complete -->
<!-- run_uuid: 8c99a137-eefe-4344-9430-c945afe281c1 -->
<!-- agent: fd-appstore-marketplace-sherlocking-economics -->

# fd-appstore-marketplace-sherlocking-economics — Findings

## Findings Index
- F-A1 (P0): Prior-7 read as a Sherlock pattern, not floor-raising — top builders priced-in predation risk
- F-A2 (P0): No residual-niche statement per absorbed category — third-party authors over-defensively flee adjacent categories
- F-A3 (P1): Preferential-placement gap — absorbed primitives ship with default-surface advantages no plugin can match
- F-A4 (P1): Marketplace revenue model unstated — incentive alignment for absorption decisions is unmeasurable
- F-A5 (P2): "Sherlock survivors" template absent — no spec for what shape of plugin survives in each absorbed category
- F-A6 (P3): Strategic angle (target line 39) covers absorption but not non-absorption as competitive lever

## Verdict
The target document treats absorption as a unilateral platform decision. From the marketplace-economics lens, **the prior-7 as a sequence is the most consequential variable** — and the document doesn't sequence them, doesn't price them against developer-cohort retention, and doesn't name which residual niches survive each absorption. Shipping all seven as listed reads as "platform ate seven categories in one release," which is the Sherlock-pattern signature that costs platforms their top builders.

## Summary
Per-app Sherlocking is fine. Sparkle, Fantastical, Bartender, TextExpander all got Sherlocked at various points and recovered. **Pattern Sherlocking** kills marketplaces. When the App Store Sherlocked F.lux (Night Shift), 1Password (iCloud Keychain), and Dropbox-style sync (iCloud Drive) in the same general era, top developers internalized "Apple ships the floor for free, then takes the ceiling at WWDC" and shifted differentiation effort to non-Apple platforms.

The target document's prior-7 list, taken together, reads as **seven simultaneous Sherlock events**: memory (deprecates 6 plugins), parallel-fleet (5), coordination (3), observability (5), code recon (1), task tracker (1), AGENTS.md (4 + parts of others). Net: ~25 plugins displaced in one release cycle. Even if each individual absorption is justified, the aggregate signal to plugin authors is "the marketplace is a transition stage between unmet need and platform feature." Authors stop investing in categories adjacent to the prior-7 because they read the trajectory.

The sequencing of absorption matters more than the absorptions themselves. **Floor-raising sequence:** ship infrastructure (host-bus territory in fd-daw terms) early; ship category absorptions (instrument territory) late and only when the category has settled. **Sherlock sequence:** ship category absorptions first because they're more visible and demonstrable. The target document, by listing all 7 as one cohort, reads as the Sherlock sequence.

## Issues Found

### F-A1 (P0): Prior-7 reads as Sherlock pattern — top builders price in predation risk

**Where:** target lines 17-25 (the seven listed as one cohort)
**Failure scenario:** Hypothetical CC v3.0 release notes: "We're excited to ship native memory, parallel agent fleet, multi-session coordination, cost observability, code recon, task tracker, and AGENTS.md management — deprecating 25+ community plugins." Reaction from the top 5 plugin authors (the ones whose work is the marketplace's gravity): "Anthropic just demonstrated that the platform absorbs whatever achieves traction in the substrate. The expected NPV of investing in a new plugin is now penalized by P(absorption | success)." Top authors shift to:
- Building outside the CC ecosystem (Cursor, custom tooling)
- Building only categories the platform can't absorb (cross-vendor integrations, IP-laden domains, niche workflows)
- Building meta-tools that monitor the absorption arc itself

The marketplace becomes a long tail of bundled-primitive wrappers. The differentiated work moves elsewhere. This is the trajectory that turned the Mac App Store from "where Mac developers ship" (2011) into "where you get Apple's apps and a few survivors" (2018). The cause was not any single Sherlocking; it was the *accumulated pattern* across 5-7 years.

The target document's prior-7 compresses that 5-year arc into one release.

**Smallest fix:** Sequence the absorptions. Tier-1 (ship now): the ones with broad ecosystem benefit and weak per-plugin differentiation — observability (#4), AGENTS.md (#7), task tracker (#6). Tier-2 (ship later, after substrate convergence): coordination (#3). Tier-3 (do not absorb until design space settles, possibly never): memory (#1), parallel-fleet (#2), code recon (#5). Tier-3 ships as **format/protocol** standardization, not category absorption.

**Question:** Of the 25+ plugins the prior-7 displaces, how many of their authors are in the top decile of marketplace activity? If the displacement concentrates in top builders, the Sherlock-pattern reading is correct. If it concentrates in low-activity plugins, floor-raising reading is more defensible.

### F-A2 (P0): No residual-niche statement — defensive flight from adjacent categories

**Where:** target lines 19-25 list deprecation targets but no residual-niche shape per category
**Failure scenario:** Plugin author considers building "intermind" — a memory plugin with episodic-vs-semantic separation. Absorbed memory primitive (target line 19) doesn't ship that distinction. But the author can't tell whether:
- (a) Anthropic sees episodic/semantic as out-of-scope and welcomes plugins exploring it (residual niche exists, build the plugin)
- (b) Anthropic sees it as in-scope and will absorb it next cycle (no residual niche, don't build)
- (c) Anthropic hasn't decided and the next 18 months are coin-flip

Without a published residual-niche statement, the rational author choice is **don't build adjacent**. The category as a whole stagnates in the substrate beyond what Anthropic shipped — which means the substrate stops feeding evidence to Anthropic for the next absorption decision. The closed-loop the target document's PHILOSOPHY.md (lines 137-141) describes for system feedback applies recursively: marketplace evidence is the substrate for absorption decisions; killing the substrate's exploration starves Anthropic's own decision-making.

Apple's Notes-vs-Notion-vs-Bear-vs-Obsidian is the working example: Apple Notes is good-enough; the residual niches are extensibility (Obsidian), graph (Roam-style), sync model (iCloud-free). Apple has been clear-by-omission that those niches are open; third parties built into them. The Sherlock survivors of Apple Notes are visible.

**Smallest fix:** For each absorbed primitive, publish a one-page residual-niche statement: "We ship X. We don't ship Y, Z, W. Plugins exploring Y/Z/W are welcome and won't be absorbed in the [next 12-24 months / foreseeable future / commit to never]." The commitment varies by category but the statement structure is constant.

**Question:** Is Anthropic willing to commit to *not* absorbing a residual niche, or is the strategic flexibility worth more than the marketplace signal? If unwilling, the marketplace will infer from absence.

### F-A3 (P1): Preferential-placement gap — default-surface advantage no plugin can match

**Where:** target document treats absorption as capability-only; placement is implicit
**Failure scenario:** Anthropic ships native task tracker. The native version is invokable as `Claude task add` (zero friction). The interphase plugin (target line 95) requires `/interphase phase` invocation (multi-keystroke, plugin discovery cost, learning curve). Even if interphase is *better* on shape — say, it has bead integration that native lacks — the native version's placement advantage means most users never discover the better option. interphase loses on UX even when it wins on capability.

This is the iOS default-app problem: third-party browsers, mail clients, password managers existed long before iOS allowed default-app changes (2020-2021), but their adoption was capped by the default-Safari/Mail/Keychain placement. Even where capability was demonstrably better (1Password vs Keychain in 2015), placement won.

**Smallest fix:** Absorbed primitives MUST be replaceable as defaults. Concrete: shipping native task tracker requires also shipping a "default task tracker" config that lets users point `Claude task` at interphase if they prefer. Same pattern for memory, observability, AGENTS.md surface. The platform raises the floor without taking the placement.

**Question:** Does CC's plugin/skill model already support default-redirection (the way iOS does for browser/mail), or is placement structurally welded to the absorbed primitive?

### F-A4 (P1): Marketplace revenue model unstated — absorption incentives unmeasurable

**Where:** target line 39 names "marketplace economics" as a strategic angle, doesn't analyze it
**Failure scenario:** Two scenarios depending on revenue model (which the document doesn't specify):

Scenario A — **No platform-tax** (CC plugins are free, ecosystem is community-driven): Anthropic has no revenue incentive to leave categories in the marketplace. Every user-loved plugin is a missed in-product feature. Absorption rate is high; floor-raising sequence is unlikely; marketplace decays into a transitional substrate.

Scenario B — **Platform-tax exists** (some plugins are paid, Anthropic takes a cut): Anthropic earns from substrate vitality. Absorption decisions weigh marketplace revenue against user-experience improvement. Absorption rate is calibrated; floor-raising sequence is rational because it preserves revenue base.

The target document doesn't state which scenario applies, which means the absorption discipline analysis can't be grounded. The Sylveste plugins are predominantly free/open-source (target lines 43-124) — which suggests Scenario A, which suggests Anthropic faces no revenue counterweight to absorption. That's the structural condition for Sherlock-pattern emergence.

**Smallest fix:** Add a section to the target document: "Marketplace revenue model and its implications." If there's no platform-tax today, name the absorption-incentive structure honestly: Anthropic's only counterweight to absorption is reputation/ecosystem-trust. Plan absorption pacing accordingly.

**Question:** Is there any user-paying-for-plugin path on CC marketplace, or is everything free-to-install? If everything is free, this finding's severity is P0, not P1.

### F-A5 (P2): "Sherlock survivors" template absent

**Where:** target lines 154-161 (success criteria) ask for primitives missed; doesn't ask for survivor templates
**What's missing:** For each prior-7 absorption, a worked example of "what shape of plugin would still be viable post-absorption":
- Memory (#1): episodic/semantic separation, multi-modal (image+text) recall, federated cross-org memory sharing
- Parallel-fleet (#2): cross-AI council (Anthropic won't ship Codex orchestration), domain-specific synthesis (legal/medical/financial), debate-mode dialectic
- Coordination (#3): cross-machine fleet (Anthropic won't ship distributed CC), git-aware merge resolution
- Observability (#4): community-comparison benchmarks (target line 68), regulatory compliance reporting, organization-level rollups
- Code recon (#5): IP-restricted (proprietary code, defense), language-specific deep semantics
- Task tracker (#6): bead-integration (target line 95), org-level multi-project rollups
- AGENTS.md (#7): cross-vendor harmonization across Codex/Cursor/Gemini, regulatory-doc generation

These templates do two things: (a) they signal to plugin authors that the residual niches are real and explored, (b) they let Anthropic test its absorption shape — if a residual niche is genuinely unservable by the absorbed shape, the absorption shape is too narrow.

**Smallest fix:** Add a "Residual niches" subsection to the prior-7 in the target document. Each absorption gets 3-5 named survivor templates. This becomes the de facto contract with plugin authors.

### F-A6 (P3): Non-absorption as competitive lever — strategic angle missing

**Where:** target line 39 ("Strategic / business-model angles")
**What's missing:** The target frames absorption as the strategic move. Non-absorption is also a strategic move. If Anthropic *doesn't* absorb code recon (target line 23) and instead lets tldr-swinton flourish, that's a signal to the developer ecosystem that CC values the marketplace as a real differentiator from Cursor/Codex. Cursor's strategic position is partly weakened because they have no marketplace at this scale; absorbing aggressively gives that advantage back.

**Smallest fix:** Add a counter-argument section to the strategic angle: "Where non-absorption is the stronger competitive move." Code recon, dialectic synthesis, and cross-AI peer review are candidates — they signal "we have a marketplace; competitors don't" without Anthropic having to build everything.

## Improvements
- The target's success criteria (target line 159: "two strong counter-arguments") is the right shape; this finding feeds three counter-arguments (Sherlock-pattern at aggregate, residual-niche unspecified, non-absorption-as-lever).
- Run the prior-7 list through a spreadsheet: columns = (plugins displaced, top-author-affected, residual-niche named, placement-replaceable, polyfillable). The cells will reveal which absorptions are floor-raising and which are Sherlock-shaped *before* the release ships.
- Cite the Sparkle survival case explicitly: when macOS shipped native auto-update, Sparkle didn't die — it survived because the native version had a residual-niche gap (signing model, distribution channels). This is the pattern to reproduce, not to assume.
- The PHILOSOPHY.md "wired-or-it-doesn't-exist" frame (target line 138) inverts well here: an absorption is wired only if it has callers. Marketplace evidence (download counts, plugin co-installation patterns) is the call-graph for primitives. Surface that explicitly.
