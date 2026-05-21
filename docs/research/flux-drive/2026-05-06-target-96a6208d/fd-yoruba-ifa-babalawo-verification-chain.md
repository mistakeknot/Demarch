# Findings — fd-yoruba-ifa-babalawo-verification-chain

**Target:** `/home/mk/projects/Sylveste/docs/research/flux-review/anthropic-cc-platform-gaps-sylveste/2026-05-06-target.md`
**Lens:** Yoruba Ifá divination — 256 odu canon, babalawo verification chain, independent re-casting, canon-arbitrated divergence resolution, reputational decay across diaspora.

---

## P0 — Three-primitives-as-one: durable memory + peer review + trust scoring collapse into a canon-arbitrated divergence-resolution protocol

**Finding.** The prior pass (target.md lines 18-27) lists durable memory (item 1), parallel agent fleet + synthesis (item 2), and treats trust/observability scoring as separate concerns scattered across the second tier. The Ifá babalawo verification chain demonstrates these are not three primitives — they are three views of one integrated protocol. A babalawo's reading is durable memory (the 256 odu corpus). Verification happens by independent re-casting (peer review). Divergences are resolved against the canon, not the casters' personal standing — and casters whose readings systematically fail cross-check stop being consulted (reputational decay = trust scoring as routing input). The 63-plugin ecosystem's empirical pairing of intermem + interpeer + intertrust (target.md lines 47-62) shows builders converged on this integration — but each plugin re-implements the integration privately because the prior pass treats them as independent.

**Failure scenario.** Memory says "use pattern X." Peer review (interpeer/intermonk) produces divergent finding "use pattern Y." Trust scores rate X's author higher than Y's. *No protocol resolves this.* The user arbitrates manually; the resolution collapses to "whoever the user trusts more wins" — exactly the failure mode an integrated canon-arbitrated protocol prevents. Multiply this across 63 plugins and 19 Clavain skills, and divergent suggestions accumulate as quiet drift, with the user's attention as the single bottleneck.

**Smallest viable fix.** Add a primitive to the prior-pass list named *"canon-arbitrated divergence resolution"* — the meta-primitive that integrates durable memory, peer review, and trust scoring. The fix to target.md is one new bullet between items 1 and 2 (or as an item 1.5): *"A divergence-resolution protocol: when memory, peer review, and trust scoring disagree, the resolution rule is canonical-precedent-attestation (older + more widely cross-checked wins), not reputational standing."* This collapses three plugin clusters into one integration point.

**Concrete plugin collapse.** Under this primitive: intermem (memory), interpeer + intermonk (peer review), intertrust + interspect (trust + routing) become *one* protocol, not five plugins. The integration cost moves from 63-plugin perimeter to one canonical contract.

---

## P1 — Trust scoring is treated as observability surface, not as routing consequence

**Finding.** Target.md's prior-pass list groups intertrust under item 1 (memory) tangentially and otherwise leaves trust scoring as a metric. The Ifá protocol shows that reputational decay produces cost-stable behavior *because bad readers simply stop being asked* — no central authority enforces demotion. The closed loop is: cast → cross-check → divergence → reputational adjustment → routing-frequency change. A trust primitive that exposes scores but does not feed them back into routing decisions creates the masquerade pattern Sylveste PHILOSOPHY explicitly warns against (target.md line 140: "Stages 1-2 without 3-4 is 'constant masquerading as intelligence'").

**Failure scenario.** Anthropic ships a "trust score" panel showing each agent's historical accuracy. Users see the panel; routing logic does not consult it. Low-trust agents continue being dispatched at the same frequency. The dashboard exists; the calibration loop does not close. This is the half-OODA failure (Act without Reflect-Compound, target.md line 139) at the protocol level — the loop's measurement closes but the loop's *consequence* does not.

**Smallest viable fix.** Add to target.md's "second tier" list (line 27) a phrasing that distinguishes trust-as-observability from trust-as-routing-input: *"Trust scoring as routing consequence, not dashboard surface — low-trust agents are consulted less often automatically, with the consultation-frequency derivative as the contract, not the score itself."* The contract is the derivative, not the metric.

---

## P2 — AGENTS.md/CLAUDE.md as per-project surface without canonical precedent corpus

**Finding.** Target.md item 7 ("Managed AGENTS.md / CLAUDE.md surface") frames AGENTS.md as a per-project documentation primitive. The Ifá analog of AGENTS.md is each diviner's personal selection from the 256 odu — but those personal selections only have integrity *because they reference back to a shared canon every diviner has memorized*. Per-project AGENTS.md without a canonical Anthropic-published agent-precedent corpus produces 63 incompatible private canons that cannot cross-check against each other. This reproduces the fragmentation failure mode that distributed oral traditions specifically avoid.

**Failure scenario.** A new agent encounters a CLAUDE.md instruction: "always defer to the project's prevailing convention on X." Without a canonical precedent corpus, "prevailing convention" is a private inference per project; cross-project consistency drifts; behaviors vary unpredictably across the monorepo. Two agents working on adjacent modules produce contradictory output because each interpreted "prevailing convention" against a private canon.

**Smallest viable fix.** Target.md item 7 should specify two things, not one: *"per-project AGENTS.md/CLAUDE.md surface + a canonical agent-precedent corpus that per-project files inherit from and may locally override."* The corpus is the missing meta-primitive — without it, AGENTS.md is private canon, not shared canon.

**Concrete plugin collapse.** Under this primitive: interdoc, interscribe, interwatch, intermem (graduation), interlore (philosophy detection) all collapse into "fragments of canonical agent-precedent corpus" — they're all currently building local canon because no shared canon exists.

---

## Diaspora-survival test (the durability test the prior pass should adopt)

The strongest evidence for Ifá's protocol design is *concordance across forced diaspora*: Cuban Lucumí and Brazilian Candomblé practitioners can cross-check readings against Yoruba originals despite four centuries of separation. The equivalent test for any Claude Code primitive is: *if Anthropic disappeared tomorrow, could two practitioners on different vendors (Codex, Cursor, Gemini) cross-check each other's outputs against a shared canon and resolve divergences?* This is a stricter test than warifu (which asks "verifiable offline") because it asks "verifiable across forks/vendors with shared canonical reference." Apply this test to each of the prior-pass seven; the ones that pass are real primitives, the ones that fail are vendor-locked.

---

## The lineage propagation pattern (for plugin marketplace economics)

A babalawo's reputation propagates to their lineage of trainees. The plugin marketplace analog: when a plugin author builds reputation, their *style* propagates — other plugin authors fork patterns, copy idioms, inherit conventions. This is currently invisible — the marketplace tracks plugin downloads, not author-style propagation. A primitive that surfaced lineage relationships (which plugins are stylistic descendants of which) would change marketplace dynamics: established lineages would gain trust faster than isolated submissions, reproducing the Ifá apprenticeship economy. Strategic-angle implication: Anthropic's marketplace economics should track author lineage, not just download counts.

---

## Defers to peer agents

- fd-heian-warifu-tally-certificates on artifact-shape and graceful-degradation under issuer collapse (this finding focuses on the integrated canon-plus-cross-check-plus-reputation protocol).
- fd-marshall-rebbelib-stick-chart-pedagogy on training-time vs runtime knowledge representation (this finding focuses on distributed memorized canon and independent re-casting).
