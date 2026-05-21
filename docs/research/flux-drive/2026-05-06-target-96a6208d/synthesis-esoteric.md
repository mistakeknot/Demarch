# Flux-Drive Synthesis — Esoteric Domains Track

**Target:** `/home/mk/projects/Sylveste/docs/research/flux-review/anthropic-cc-platform-gaps-sylveste/2026-05-06-target.md`
**Date:** 2026-05-06
**Track:** Esoteric (maximally unexpected domains)
**Agents:** fd-heian-warifu-tally-certificates, fd-yoruba-ifa-babalawo-verification-chain, fd-marshall-rebbelib-stick-chart-pedagogy
**Mode:** review (project agents only, MAX_CONCURRENT=3)

---

## Executive Summary

The three esoteric agents converged on a single meta-finding: **the prior-pass list under-specifies the *shape* of every primitive it names**. Each agent supplied a different shape-distinction the prior pass missed:

- **Warifu lens (Heian):** registry-shape vs warifu-shape (authority-at-verification-time vs authority-at-signature-time). All seven prior-pass items are silently registry-shaped; the artifact-durability test is missing.
- **Babalawo lens (Yoruba Ifá):** three-primitives-as-one (durable memory + peer review + trust scoring collapse into a *canon-arbitrated divergence-resolution protocol*). The prior pass treats them as independent; builders empirically integrated them anyway.
- **Rebbelib lens (Marshallese):** runtime-query vs training-time-compilation. Item 1 (durable memory) is one primitive in the prior pass and should be two; eight plugins want the compilation primitive that doesn't exist.

The three lenses are mutually compatible and produce a single composite reframing: **every prior-pass primitive needs three shape-decisions (registry-or-warifu, integrated-protocol-or-isolated-surface, runtime-or-compilation) before it can be specified as actionable infrastructure.** The prior pass made none of these three decisions explicitly.

---

## Headline Findings (P0/P1)

### P0-1 — All seven prior-pass primitives are silently registry-shaped (warifu)

The prior pass names what to build but not what shape. Without the artifact-durability test, every primitive defaults to registry-shape: validity at verification time depends on Anthropic's service still answering. This violates Sylveste PHILOSOPHY principle 1 ("evidence, not narratives") because registry receipts are tokens pointing at services, not artifacts.

**Concrete fix to target.md:** Add a row to success-criteria specifying, for each primitive, its artifact-durability classification and the failure mode under Anthropic service outage or vendor migration.

### P0-2 — Durable memory + peer review + trust scoring are one protocol, not three (babalawo)

The prior pass lists these as separate items. Empirically, intermem + interpeer + intertrust are coupled in every plugin that uses them — builders integrated what the platform fragmented. The Ifá protocol shows the integration is *canon-arbitrated divergence resolution*: when memory disagrees with peer review, resolution is by canonical-precedent-attestation, not by reputational standing. This is the meta-primitive the prior pass missed.

**Concrete fix to target.md:** Insert one item between prior-pass items 1 and 2: "Canon-arbitrated divergence-resolution protocol — the integration of durable memory, peer review, and trust scoring."

### P0-3 — Durable memory should be split into runtime-query and training-time-compilation (rebbelib)

The prior pass treats item 1 as a single primitive. Eight plugins (intermem, interknow, interlearn, interlore, interfluence, interlens, interscribe, interseed) want context shaping at session start, not runtime consultation. The Sylveste cost baseline ($2.93/landable change, 2,285-token preamble trim) demonstrates runtime consultation is a structural cost line. A compilation primitive — content absorbed into agent baseline before first turn — is the missing shape.

**Concrete fix to target.md:** Split item 1 into items 1a (runtime query API) and 1b (training-time compilation primitive), with the eight-plugin reclassification table provided.

### P1-1 — Cross-vendor AGENTS.md standardization needs both warifu and rebbelib tests (warifu + rebbelib)

Two agents converge here. Warifu test: can a Codex user verify an AGENTS.md without contacting Anthropic? Rebbelib test: is the file format separated from the compilation semantics? Without both, "open standard" fragments operationally even when nominally adopted.

**Concrete fix to target.md:** Success criterion 5 should require both tests stated explicitly, with vendor extension points documented.

### P1-2 — Trust scoring as routing consequence, not dashboard surface (babalawo)

Target.md groups trust under observability. Ifá practice shows the closed loop must close into routing-frequency, not a panel. Trust as observability without routing-input is the masquerade pattern PHILOSOPHY explicitly warns against.

**Concrete fix to target.md:** Specify trust scoring's contract as the consultation-frequency derivative, not the score itself.

---

## Structural Reframings (success criterion 2)

The prior pass requested at least one structural reframing of its 7 items. The esoteric track produced three:

### Reframing A — The prior 7 are all registry-shaped runtime queries

Apply both warifu and rebbelib lenses simultaneously: every prior-pass item is a *registry-model runtime-query primitive*. The structural reframing collapses the prior 7 into: "Anthropic's offering is one shape (registry runtime), and what's missing is two other shapes (warifu artifact, training-time compilation)." This is bigger than the seven items individually — it's a shape gap, not an inventory gap.

### Reframing B — Five observability plugins are one canonical receipt format

(warifu) interstat + intercept + interpulse + tool-time + intertrust collapse into one self-authenticating receipt format. Five plugins die when one primitive ships. The prior pass missed this because it treated observability as a category, not as a shape.

### Reframing C — Three primitives integrate into one divergence-resolution protocol

(babalawo) durable memory + peer review + trust scoring are three views of a canon-arbitrated divergence-resolution protocol. The integration is what the 63-plugin ecosystem keeps re-implementing privately.

---

## Counter-Arguments — Things NOT to Build Natively (success criterion 3)

The rebbelib lens generated four; the babalawo and warifu lenses sharpen them:

1. **Voice/style conditioning should NOT be a runtime API** (rebbelib). Voice is training-time. A runtime voice API perpetuates the cost line the preamble trim addressed. Build compilation; let interfluence feed it.

2. **AGENTS.md should NOT have a runtime interpretation surface** (rebbelib + warifu). AGENTS.md is a training-time artifact. A runtime interpretation surface couples vendors to a runtime semantics that fragments operationally. Build compilation; let AGENTS.md remain inert at runtime.

3. **Cognitive lenses (288 FLUX) should NOT be a runtime tool catalog** (rebbelib). Catalog query is per-consultation cost; a small compiled subset is the rebbelib pattern. The catalog exists for training, not runtime.

4. **Trust scoring should NOT be a runtime dashboard** (rebbelib + babalawo). The dashboard duplicates the closed-loop consequence in human-readable form; without compilation into routing, the dashboard is theatrical.

5. **(Composite) Plugin marketplace should NOT remain a runtime-tool marketplace** (rebbelib). Many plugins are compilable inputs, not runtime competitors. Repositioning the marketplace as behavior-input feeders is structurally more defensible than letting native runtime APIs deprecate the layer.

---

## Cross-Domain Isomorphisms (success criterion 4)

Three isomorphisms with named mechanisms (not surface analogies):

### Isomorphism A — Heian warifu (split-tally certificate)

Mechanism: matched halves + on-face scope inscription + dated calligraphic seal patterns. Authority is structurally embedded in the artifact at signature time. Verification is local, requires no contact with the issuing office. The Heian state's central court fluctuated dramatically across three centuries; warifu remained valid throughout because they were artifact-durable, not registry-durable.

Transfer to Claude Code: every primitive must produce artifacts that pass an offline-verification test. The receipt format must include scope, expiration, signing context — at signature time, not at verification time.

### Isomorphism B — Yoruba Ifá babalawo verification chain

Mechanism: 256-odu canon memorized by every babalawo + independent re-casting (multiple babalawos consulted in parallel) + canon-arbitrated divergence resolution (when readings disagree, resolution is by which odu the canonical corpus more strongly supports, not by which babalawo has higher reputation) + reputational decay propagates through apprenticeship lineages, not just individuals. Diaspora-survival evidence: Cuban Lucumí and Brazilian Candomblé practitioners cross-check readings against Yoruba originals despite four centuries of separation.

Transfer to Claude Code: durable memory + peer review + trust scoring become one protocol, with canonical-precedent-attestation as the divergence-resolution rule. The diaspora-survival test (cross-vendor concordance after Anthropic's hypothetical absence) is the durability standard.

### Isomorphism C — Marshallese rebbelib stick-chart pedagogy

Mechanism: rebbelib is a training artifact made on the beach, used to teach wave-pattern reading; the navigator memorizes patterns then sails *without* the chart. Mattang teaches abstract refraction principles; meddo teaches specific island chains; rebbelib teaches general ocean dynamics. The chart's purpose is to compile knowledge into the navigator's perception, not to be consulted at sea. Korent Joel and successor ri-meto (master navigators) demonstrate the practice survives despite the wider tradition's near-loss.

Transfer to Claude Code: a training-time compilation primitive (content absorbed into agent baseline before first turn) is structurally distinct from a runtime query API and deprecates a different cluster of plugins (eight identified). The cost asymmetry is dramatic at session-volume scale.

---

## Strategic / Business-Model Angle (success criterion 5)

**The marketplace shape changes when compilation ships.** If Anthropic ships only runtime APIs (durable memory query, trust dashboard, AGENTS.md interpretation), the marketplace remains runtime-tool-vs-native and many plugins die. If Anthropic also ships training-time compilation, plugins providing compilable inputs (voice, lens, philosophy, style, naming, agent precedent) shift from "competing with the model" to "feeding the model better baseline behavior" — a structurally different and more defensible position.

**Lineage propagation as marketplace dynamic** (babalawo): track plugin author lineages, not just download counts. Established lineages gain trust faster; the marketplace develops Ifá-style apprenticeship economics rather than flat search-rank dynamics.

**Cross-vendor "open standard" theater is the warifu trap.** Standardizing AGENTS.md without specifying both file format (portable) and compilation semantics (canonical with documented vendor extensions) lets Anthropic claim openness while gating practical portability. The warifu test (verifiable without contacting issuer) and the rebbelib test (file format separated from compilation behavior) must both be passed for the claim to hold.

---

## Hidden Coupling the Prior Pass Missed (success criterion 4)

Three couplings, one per lens:

- **(warifu)** interlock + intercept + intertrust + interspect all encode authority-at-signature-time. They are four implementations of one signed-decision primitive.
- **(babalawo)** intermem + interpeer + intertrust + intermonk + interspect are five implementations of one canon-arbitrated divergence-resolution protocol.
- **(rebbelib)** intermem + interknow + interlearn + interlore + interfluence + interlens + interscribe + interseed are eight implementations of one training-time compilation primitive.

The three couplings overlap (intermem appears in all three; intertrust in two; interspect in two). The overlap is itself the deepest finding: **the missing primitive is a single integrated shape with three faces — signed-decision artifacts that compile into baseline behavior and resolve divergence by canonical precedent.** The prior pass under-specified all three faces because it treated them as separate categories of plugin.

---

## Suggested Additions to target.md

Concrete deltas the prior-pass document should adopt before next track:

1. **Insert (between items 1 and 2):** "Canon-arbitrated divergence-resolution protocol — durable memory + peer review + trust scoring as one integrated primitive."
2. **Split item 1:** into 1a (runtime query) + 1b (training-time compilation), with eight-plugin reclassification table.
3. **Annotate every prior-pass item:** with shape decisions (registry-vs-warifu, runtime-vs-compilation, isolated-vs-integrated).
4. **Add to success criteria:** "For each primitive, specify graceful-degradation behavior under Anthropic service outage or vendor migration."
5. **Add to success criteria:** "For each primitive, run the diaspora-survival test (cross-vendor concordance after Anthropic absence)."
6. **Add to success criteria:** "Surface couplings where 3+ prior-pass items collapse into a single deeper primitive when viewed through any cross-domain lens."

---

## Out-of-scope notes (explicit handoffs)

- Modern infrastructure analogies (operating systems, databases, IDEs, browsers) deferred to orthogonal/distant-track agents in other flux-drive runs.
- Modern peer-review systems (academic, code review, consensus protocols) deferred to orthogonal/distant-track agents.
- Modern training-vs-inference, embeddings, RAG, fine-tuning analogies deferred to orthogonal/distant-track agents.
- The esoteric track's value is *that the mechanisms are precolonial and non-software*, so the structural transfer is uncontaminated by current tooling assumptions.

---

## Files in this run

- `/home/mk/projects/Sylveste/docs/research/flux-drive/2026-05-06-target-96a6208d/fd-heian-warifu-tally-certificates.md`
- `/home/mk/projects/Sylveste/docs/research/flux-drive/2026-05-06-target-96a6208d/fd-yoruba-ifa-babalawo-verification-chain.md`
- `/home/mk/projects/Sylveste/docs/research/flux-drive/2026-05-06-target-96a6208d/fd-marshall-rebbelib-stick-chart-pedagogy.md`
- `/home/mk/projects/Sylveste/docs/research/flux-drive/2026-05-06-target-96a6208d/synthesis.md` (this file)
