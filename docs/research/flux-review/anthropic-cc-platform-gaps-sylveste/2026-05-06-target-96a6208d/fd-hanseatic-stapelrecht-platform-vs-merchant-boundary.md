<!-- flux-run-uuid: 3507b048-2a14-484a-ad19-b1066bab6c97 -->
<!-- dispatch-mode: orchestrator-embodied (Task tool unavailable in nested skill context) -->

### Findings Index
- P1 | H-1 | "Initial findings (prior pass)" | Stapelrecht inversion — three of the prior 7 are merchant function, not substrate
- P1 | H-2 | "What this review is for / Cross-domain isomorphisms" | Cog-hull dimension is the hook event schema, not AGENTS.md
- P0 | H-3 | "Initial findings #5 (token-efficient code recon)" | Native code-recon = herring-pricing seizure; collapses tldr-swinton, intermap, intersearch as competitors
- P1 | H-4 | "Initial findings #1 (durable agent memory)" | Memory is not one substrate — accession (registrar) belongs to League, semantic retrieval to merchant houses
- P2 | H-5 | "Anti-patterns / Strategic angles" | No Kontor boundary specified — projects/teams/marketplaces have no named jurisdiction
- P1 | H-6 | "Initial findings #7 (managed AGENTS.md)" | Bruges-shift gap — AGENTS.md may already be the wrong harbor; the standard moving to MCP descriptor schema
- P2 | H-7 | "63 manifests grouping" | Privilege asymmetry unspecified — does Anthropic differentially access plugin authors vs first-party plugins?

Verdict: needs-changes

---

## Summary

The prior pass mixed substrate (loses value when fragmented) with merchant function (gains value from diversity) under one "deprecation" frame. From the Hanseatic substrate-vs-superstructure lens, three of the seven targets are mis-classified, and the highest-leverage move is not in the seven at all — it is naming the cog-hull dimension (a single format whose cross-vendor adoption compounds for years). The review's framing of "deprecate" is itself the herring-pricing mistake: the League did not deprecate the Bergen merchant; it standardized weights and let merchants compete on cargo. Anthropic's analog is to standardize the wire format and forbear from the application layer.

## Issues Found

### 1. P1 | Three prior targets are merchant function, not substrate

The prior pass lists seven primitives for native build. Three fail the Hanseatic test — they gain value from diversity rather than losing it from fragmentation:

- **#5 Token-efficient code recon** — tldr-swinton's specific compression scheme is differentiated cargo. Other vendors will produce different recon strategies (semantic, structural, AST-based, embedding-based). Standardizing this freezes one approach as platform default and converts every alternative recon plugin into a competitor against a free first-party.
- **#2 First-class parallel agent fleet + synthesis** — interflux's triage-score-budget-stage pattern is one synthesis discipline among many (debate, dialectic, council, weighted-voting). Native build picks a winner before the design space is mapped.
- **Tier 2 voice/style conditioning** — interfluence is a merchant-house service. Voice is identity, not interoperability. League stamping voice would be the herring-pricing seizure.

Failure scenario: Anthropic ships native code-recon. tldr-swinton, intermap, intersearch lose adoption. The plugin authors stop iterating. Five years later, the native recon has not improved because the differentiated competition was foreclosed. The platform is locked to one compression scheme that aged poorly. The prior pass treats this as a feature ("deprecates tldr-swinton") rather than a strategic risk.

Fix: Tag each of the seven with `belongs_to: {league, kontor, merchant}`. Only league-tagged primitives proceed to native-build candidates. The other tags get standardized interfaces (a recon-API contract) that plural plugins can implement.

### 2. P1 | Cog-hull dimension is hook event schema, not AGENTS.md

The review surfaces AGENTS.md as a candidate cross-vendor standard. From the cog-hull lens this is plausible but probably not the highest-leverage move. The Hansa cog standardized the *physical artifact that touches every harbor* — the hull dimensions, not the bills of lading written in the cabin.

The Claude Code equivalent is the **hook event schema**. Every plugin, every observation, every cost record, every routing decision — they all flow through hook events. If Anthropic published a stable, versioned hook event schema (PreToolUse, PostToolUse, SessionStart, SessionEnd, UserPromptSubmit) with documented field semantics, every tool that consumes those events (interstat, interspect, interpulse, tool-time, intercept, half of interlock) becomes interchangeable. AGENTS.md is the bill of lading; the hook event is the cog.

A hook event schema also has the right diversity property: any vendor can emit hook events from their CLI agent, and any vendor's tooling can consume them. AGENTS.md is harder — the *content* is opinionated, and competing IDEs already have their own (.cursorrules, etc.). The format is the easier standard.

Failure scenario: Anthropic spends a quarter standardizing AGENTS.md cross-vendor. Cursor and Codex sign on with reservations. Six months later, the actual interop pain is that interstat cannot read Codex hook events because the schema differs by vendor. The cog standard never shipped.

Fix: Treat AGENTS.md and hook event schema as *parallel* cross-vendor candidates. The review's success criterion #1 should require naming both, with the cog-hull primitive picked deliberately rather than by default to the most-talked-about candidate.

### 3. P0 | Native code-recon converts plugin authors into competitors

This is the explicit Hanseatic herring-pricing mistake — the League seizing a merchant function and provoking member revolts. The plugin marketplace economics depend on plugin authors believing they have durable revenue space. If Anthropic ships native code-recon (item #5), the signal to authors is: "any plugin Anthropic finds useful enough to learn from will be absorbed." This is not paranoid — it is the documented history of the platform-vs-app tension on every two-sided platform from iOS Sherlocking through Slack-killing-feature-X.

The marketplace dynamic damage is asymmetric: building native recon recovers ~20% of plugin time savings for users *once*. Losing tldr-swinton/intermap/intersearch's authors means the next 20% (and the 20% after) never gets built. Anthropic's expected value from absorbing #5 is negative once author-attrition is priced in.

Failure scenario: tldr-swinton's author publishes their next plugin not on Anthropic's marketplace but as a standalone CLI. Other plugin authors notice. Within a year, the marketplace concentrates on plugins Anthropic has explicitly disclaimed (dialectic reasoning, Slack integration, Notion bridges) and the high-value categories (memory, recon, synthesis) develop outside the marketplace. Anthropic's marketplace becomes the toy section.

Fix: Include in this review's success criteria: "for each native-build candidate, name the plugin authors whose adoption the platform now depends on, and the public commitment that absorbs their work fairly." This is the missing strategic angle that turns the prior pass from a list into a defensible roadmap.

### 4. P1 | "Memory" is not one substrate

Item #1 lumps intermem, intercache, interknow, interseed, interlearn, intertree as "deprecates with durable hierarchical memory." From the Hanseatic lens, this conflates the registrar function (League — accession, ID, provenance) with the merchant function (Kontor or House — semantic retrieval, idea gardens, project hierarchy).

- **League level (substrate):** stable accession ID, append-only event log, durable cross-session content addressing, provenance chain. These lose value when fragmented because two plugins that both write "memory" cannot reconcile without a shared ID space.
- **Kontor level (project-scoped, plural):** AGENTS.md / CLAUDE.md / project-rules surface, doc graduation rules, project hierarchy, idea-garden semantics. These are project-flavored and benefit from competition.
- **Merchant level (plugin-differentiated):** semantic retrieval algorithms, decay rules, embedding strategies, summarization styles. These should *not* be unified — they are where retrieval research will make progress.

Failure scenario: Anthropic ships "durable hierarchical memory" as one feature. interknow's temporal-decay-with-provenance gets folded into a default that applies one decay curve. Six months later, the tradeoff between "pattern with citation" and "pattern with frequency" is invisible because the platform default chose one. The research design space collapses to whatever Anthropic picks first.

Fix: Decompose item #1 into three primitives at three boundary levels (League ID + ledger, Kontor doc surface, Merchant retrieval). Only the first qualifies for native build. The second qualifies for cross-vendor standard (AGENTS.md format). The third stays in plugins.

### 5. P2 | Kontor boundary unspecified

The review never names where Anthropic-platform authority ends and project / team / marketplace authority begins. Each native primitive needs a Kontor specification: "this primitive is platform-controlled in scope X, project-controlled in scope Y, plugin-controlled in scope Z."

Without this, every shipped primitive will produce a year of disputes about who owns the configuration surface. The Bergen Kontor worked because everyone knew Lübeck law applied inside the compound and Norwegian law outside. Claude Code has no such map.

Fix: For each of the seven, write three lines: "Anthropic owns: ..., Project owns: ..., Plugin owns: ...". This is a 60-minute exercise that prevents months of governance ambiguity.

### 6. P1 | Bruges-vs-Antwerp shift — AGENTS.md may already be the wrong harbor

The League's center moved from Bruges to Antwerp not because Bruges did anything wrong but because the trade flows changed (Atlantic, not Baltic). The AGENTS.md format made sense for a world where the agent reads a project file at session start. The actual emerging trade flow is **multi-session, cross-agent, cross-vendor coordination** — interlock, intermux, intername, intertrust, interspect.

The next harbor — the one the prior pass underestimates — is the **multi-agent coordination protocol**. File reservations, agent identity, trust scoring, routing telemetry. AGENTS.md will still exist, but its weight relative to the coordination protocol is shrinking the way Bruges's weight relative to Antwerp shrank.

Failure scenario: Anthropic invests heavily in cross-vendor AGENTS.md standardization in 2026. By 2027, the ground truth of who-edits-what / who-owns-which-file / which-agent-is-active has migrated to cross-agent coordination, and Anthropic has no first-party answer there. interlock and intermux become the de facto standard outside Anthropic's control.

Fix: Re-rank the deprecation list by *future* trade-flow weight, not current plugin count. Coordination primitives outweigh memory primitives by 2030. The review's success criterion #5 (strategic angle) should explicitly answer: "what is the harbor that grows over the next 5 years?"

### 7. P2 | Privilege asymmetry unspecified

The League granted Hanseatic privileges — special access in foreign ports — to member merchants. Anthropic's marketplace has implicit asymmetries (first-party plugins ship with Claude Code; third-party plugins require explicit installation). The review does not surface whether this asymmetry should be formalized, eliminated, or extended.

Marketplace economics will collapse if Anthropic ships first-party plugins that compete with marketplace plugins on the same surface. The review's success criterion #5 should specify: what is the explicit privilege contract between Anthropic-shipped functionality and plugin-author functionality?

## Improvements

1. Add a substrate/Kontor/merchant column to the prior 7 deprecation table. Force the classification.
2. Replace "deprecates X" framing with "absorbs API contract of X, lets X reimplement against the contract." This converts plugin authors from competitors-to-be-killed into reference implementations of the standard.
3. Explicitly name two cog-hull candidates (hook event schema, AGENTS.md) and pick one with reasoning, not by default.
4. For each native-build candidate, list the plugin authors whose continued investment the platform depends on and the public commitment that protects them.
5. Add a Bruges-vs-Antwerp section: which 2030 trade flows is the prior pass under-weighting? Multi-agent coordination is the leading candidate.

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 7 (P0: 1, P1: 4, P2: 2)
SUMMARY: Three of the prior-pass seven are merchant function, not substrate; cog-hull dimension is hook-event schema rather than AGENTS.md; native code-recon is the herring-pricing mistake that converts plugin authors into competitors.
---

<!-- flux-drive:complete -->
