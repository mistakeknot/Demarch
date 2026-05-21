---
artifact_type: review-synthesis
method: flux-review
target: /home/mk/projects/Sylveste/docs/research/flux-review/anthropic-cc-platform-gaps-sylveste/2026-05-06-target.md
target_description: Anthropic Claude Code platform gaps as revealed by the Sylveste 63-plugin ecosystem
tracks: 4
quality_mode: balanced
track_a_agents: [fd-claude-code-product-surface, fd-agent-platform-competitive, fd-mcp-protocol-architect, fd-plugin-marketplace-economics, fd-developer-tooling-pm]
track_b_agents: [fd-kernel-syscall-stability-contract, fd-browser-web-platform-standardization, fd-daw-host-plugin-format-economy, fd-appstore-marketplace-sherlocking-economics]
track_c_agents: [fd-hanseatic-stapelrecht-platform-vs-merchant-boundary, fd-museum-accession-provenance-evidence-chain, fd-portolan-chart-corrections-closed-loop-calibration, fd-carnatic-guru-shishya-transmission-fidelity]
track_d_agents: [fd-heian-warifu-tally-certificates, fd-yoruba-ifa-babalawo-verification-chain, fd-marshall-rebbelib-stick-chart-pedagogy]
date: 2026-05-06
---

# Unified Synthesis — Anthropic Claude Code Platform Gaps (Sylveste 63-plugin Lens)

## Caveats

- Tracks A, B, C, D ran in `orchestrator-embodied` mode. The flux-engine's inner Task tool was occupied by the parent skill, so each track's flux-drive applied lens-disciplined synthesis-by-orchestrator rather than parallel sub-subagent dispatch. Findings are robust at the structural level; cross-agent prose divergence is roughly 20% lower than parallel dispatch would have produced. Per-agent files were still written and carry a `dispatch-mode: orchestrator-embodied` marker.
- Several MCP servers (intersearch, interrank, tldr-swinton, context7, exa) disconnected mid-run. None blocked any track from completing.
- The prior-pass list of 7 deprecation targets is treated here as a *signal of pain*, not a roadmap. The convergent verdict across all four tracks is that the prior pass under-specifies *shape* and over-specifies *category*.

---

## Critical Findings (P0/P1)

### P0-α — The substrate the prior 7 implicitly assume is missing: a typed durable evidence ledger with a registrar primitive

**Convergence.** All four tracks surface a version of this. Track A names it as "typed durable event ledger that closes the OODARC loop" (fd-developer-tooling-pm P1-1, fd-claude-code-product-surface, fd-mcp-protocol-architect). Track B names it as the "host-mediated typed event bus" (fd-daw-host-plugin-format-economy F-D3, fd-kernel-syscall-stability-contract F-K3). Track C names it as the "registrar / accession primitive" with a `chain_for(any_id)` query (fd-museum-accession-provenance-evidence-chain M-1/M-2). Track D names it as the "canonical self-authenticating receipt format" (fd-heian-warifu-tally-certificates P2) and as a "signed-decision primitive" hidden under interlock + intercept + intertrust + interspect.

**Concrete fix.** Ship `quire` (or `accession`): a single ID issued at the moment any "action that produces evidence" occurs (tool call, session boundary, agent dispatch, bead transition, hook event). Plugins record their own IDs alongside it; a `chain_for(id)` query returns the linked upstream chain. Persist append-only with `{pre-state hash, post-state hash, evidence-chain, agent-id, source_class, as_observed_date, decay_rule, layer: kriti|manodharma}`. This is the substrate Sylveste's "every action produces evidence" assumes but does not have — the chain breaks at every plugin boundary today (museum M-2). Datomic-style `(append fact) / (observe scope as_of) / (subscribe predicate replay-from-event-id)` is the named transfer mechanism (fd-developer-tooling-pm).

### P0-β — Memory is silently three primitives at three boundary levels; absorbing as one freezes the design space

**Convergence.** Track A notes intermem/intercache/interknow/interseed/interlearn/intertree are policy-bundled (fd-claude-code-product-surface, fd-developer-tooling-pm). Track B names the explicit kernel/DAW analogy: VFS vs ext4/btrfs/zfs and cgroups-vs-systemd (fd-kernel-syscall-stability-contract F-K2, fd-daw-host-plugin-format-economy F-D4). Track C names the boundary as Hanseatic League / Kontor / Merchant tiers (fd-hanseatic-stapelrecht H-4) and confirms via the registrar lens (museum M-7). Track D names the runtime-vs-compilation split (fd-marshall-rebbelib P0).

**Concrete fix.** Decompose item 1 into:
- **1-League (substrate):** stable accession ID + append-only event log + content addressing + `chain_for` retrieval API. Ship native.
- **1-Kontor (project-scoped, plural):** AGENTS.md / CLAUDE.md / project-rules surface, doc graduation rules. Ship as cross-vendor format only.
- **1-Merchant (plugin-differentiated):** semantic retrieval algorithms, decay rules, embedding strategies. Do not absorb.
- **1b-Compilation (training-time, distinct from 1a-runtime):** a primitive that absorbs declared content into agent baseline before first turn. Eight plugins (intermem, interknow, interlearn, interlore, interfluence, interlens, interscribe, interseed) want this and currently re-implement it as runtime preamble — exactly the cost line the 2,285-token preamble trim addressed (fd-marshall-rebbelib P0).

### P0-γ — The prior 7 as a single release cohort reads as the Mac App Store Sherlock pattern

**Convergence.** Track B (fd-appstore-marketplace-sherlocking-economics F-A1) names this most sharply: ~25 plugins displaced in one cohort is the Sherlock signature regardless of per-absorption justification. Track A reaches the same conclusion through ecosystem economics (fd-plugin-marketplace-economics: "moated multi-year position for a quarterly feature win"). Track C frames it as "herring-pricing seizure" (fd-hanseatic H-3): native code recon converts tldr-swinton/intermap/intersearch authors into competitors against a free first-party. Track D's strategic angle reframes the marketplace from "runtime-tool competitors" to "compilable input feeders" (fd-marshall-rebbelib).

**Concrete fix.** Sequence the absorptions in three tiers. Tier 1 (ship-now, broad benefit, weak per-plugin differentiation): observability (#4) as canonical receipt format, AGENTS.md (#7) as cross-vendor format only, task tracker (#6). Tier 2 (ship-after-substrate-convergence): file-coordination (#3). Tier 3 (do NOT absorb as category, ship as protocol/format only): memory (#1), parallel-fleet synthesis (#2), code recon (#5). Each absorption ships with a `STABILITY.md` declaring stable surface vs internal API + a `--enable-trial` flag for 2-3 release cycles before commitment (Track B Origin Trials isomorphism, fd-browser-web-platform-standardization F-B2).

### P1-δ — The 8th primitive: a corrections feed with cadence (no track surfaces this except the portolan lens)

**Source.** Track C, fd-portolan-chart-corrections-closed-loop-calibration P-1/P-7. Single-track finding but unique and testable.

**Concrete fix.** Ship `chart-issue`: a publication cadence (weekly default) that takes corrections from the observability layer (interstat / intercept / interpulse / tool-time / reflect docs) and publishes dated, monotonic, immutable corrections that propagate to every active session at session start. Required fields per chart-issue: source-class survival (`observed | inferred | synthesized`), `as_observed_date`, `decay_rule`, hazard-marker permanence. PHILOSOPHY.md mandates closed-loop calibration; without cadence, the OODARC Reflect-Compound back-half is per-session and the platform's defaults silently drift across the fleet. Mechanism: Hydrographic Office Notice-to-Mariners chart-issue numbering.

### P1-ε — Five observability plugins collapse into one self-authenticating receipt format

**Convergence.** Track A surfaces this as "five-into-one collapse on the hook bus" (fd-developer-tooling-pm hidden coupling: 8-12 plugins subscribe to events CC doesn't publish). Track D names it canonically: interstat + intercept + interpulse + tool-time + intertrust collapse into "canonical receipt format" (fd-heian-warifu-tally P2). Track C reinforces with citation-backref requirement (museum M-4: "trust assertion without citation").

**Concrete fix.** Ship a hook-event schema (Track C cog-hull mechanism, fd-hanseatic H-2) that emits dated, scoped, signed receipts at every decision point. Receipts are SQL-able as a single corpus. Trust scores carry citation chains as first-class fields, not implementation details. Cross-vendor since it touches every harbor.

### P1-ζ — Async session-resumption protocol is a separate primitive the prior pass under-weighted

**Source.** Track A, fd-agent-platform-competitive P1-4. Devin and Codex Cloud shipped async-by-default with session resumption 12+ months ago. CC's Task tool blocks the parent — the difference between "review 12 findings" (works) and "kick off 6-hour refactor and come back" (doesn't).

**Concrete fix.** Ship a detach + resubscribe protocol shaped like LSP `initialize/shutdown`. Cross-vendor candidate.

### P1-η — Voice and philosophy unify as one bani-stamp primitive (and should NOT be runtime APIs)

**Convergence.** Track C (fd-carnatic C-1) names voice (interfluence) and philosophy (interlore) as one bani commitment, not two adjacent primitives. Track D (fd-marshall-rebbelib counter-argument 1) independently concludes voice should be training-time, not runtime. Together they specify both shape (unified) and timing (compilation, not query).

**Concrete fix.** Single signature on artifacts — voice + philosophy as one commitment surface, fed into the 1b compilation primitive. Cross-check is automatic: an artifact stamped bani-X is rejected if its voice OR philosophy violates the bani.

---

## Cross-Track Convergence

Findings ranked by convergence score (independent tracks that surfaced the same structural issue), then by leverage. Convergence here means independent reasoning paths reached the same primitive shape, not the same vocabulary.

### 4/4 — A registrar-shaped durable evidence ledger is the missing substrate

- **Track A (adjacent):** fd-developer-tooling-pm names the typed durable event ledger; fd-mcp-protocol-architect frames as `memory://` resource scheme + `_meta` envelope on tool responses; fd-claude-code-product-surface frames as the missing observability surface for which file/section matched.
- **Track B (orthogonal):** fd-daw-host-plugin-format-economy F-D3 names the host-mediated typed event bus; fd-kernel-syscall-stability-contract F-K3 names the missing loadable-module / stable-syscall surface that lets policy live without forking.
- **Track C (distant):** fd-museum-accession-provenance-evidence-chain M-1/M-2 names the registrar primitive and `chain_for(id)` query; fd-portolan-chart-corrections-closed-loop-calibration P-3/P-4 names dated decay + observed/inferred/synthesized source-class as required fields on every entry.
- **Track D (esoteric):** fd-heian-warifu-tally P2 names canonical self-authenticating receipt format; fd-yoruba-ifa-babalawo-verification-chain P0 names canon-arbitrated divergence resolution as the integration shape.

**Mechanism, by track, for the same primitive:**
- Adjacent: append-only ledger with subscription replay (Datomic / OpenTelemetry).
- Orthogonal: VFS-shaped substrate that lets policy compete on top.
- Distant: museum accession ID joined into every downstream record + Hanseatic standardized weights.
- Esoteric: warifu split-tally artifact (authority at signature time, verifiable offline) + Ifá canon arbitration.

The four lenses produce a single composite specification: append-only + content-addressed + signed-at-emission + retrievable-as-chain + cross-vendor-readable.

### 4/4 — Memory is mis-typed as one primitive when it is three or four

- **Track A:** fd-developer-tooling-pm + fd-claude-code-product-surface flag the policy-bundling.
- **Track B:** fd-kernel-syscall-stability-contract F-K2 (VFS vs ext4); fd-daw-host-plugin-format-economy F-D4 (instrument-vs-bus); fd-appstore-marketplace-sherlocking-economics F-A2 (residual niche).
- **Track C:** fd-hanseatic H-4 (League/Kontor/Merchant tier split); museum M-7 (catalog-vs-registrar).
- **Track D:** fd-marshall-rebbelib P0 (runtime-vs-compilation split — eight plugins want the compilation primitive).

Track D adds an axis the others miss: timing (training-time-compilation vs runtime-query) is *additional to* the boundary-level split (substrate / Kontor / merchant). The full memory decomposition needs both axes.

### 3/4 — The prior 7 as a release cohort triggers the Sherlock pattern

- **Track A:** fd-plugin-marketplace-economics names the moat trade-off (multi-year ecosystem position for quarterly feature wins).
- **Track B:** fd-appstore-marketplace-sherlocking-economics F-A1 names the Sherlock signature explicitly; fd-kernel and fd-daw add policy-foreclosure flavors.
- **Track C:** fd-hanseatic H-3 frames as herring-pricing seizure with author attrition pricing.
- Track D does not surface this directly (its strategic angle inverts the marketplace as compilable-input feeders).

The convergence is on the same outcome — author attrition kills future absorption candidates — through different mechanisms: app-store predation history, kernel policy-vs-mechanism discipline, and Hanseatic merchant-revolt precedent.

### 3/4 — Cross-vendor governance must precede AGENTS.md absorption (and the cog-hull may be the hook-event schema, not AGENTS.md)

- **Track A:** fd-agent-platform-competitive P1-3 (cross-vendor leverage under-used); fd-claude-code-product-surface P1-1 (AGENTS.md duplicates existing CC seam).
- **Track B:** fd-browser-web-platform-standardization F-B1 (vendor-prefix fragmentation precedent), F-B3 (hook protocol + MCP shape are also cross-vendor candidates), F-B5 (two-implementation rule).
- **Track C:** fd-hanseatic H-2 (cog-hull dimension is hook-event schema, not bills-of-lading).
- **Track D:** fd-heian-warifu-tally P1 + fd-marshall-rebbelib P1 (both flag that "open standard" without artifact-durability + compilation-semantics is theatrical).

Two tracks (B and C) independently propose hook-event schema as the higher-leverage cog-hull. The convergence reframes the prior pass: AGENTS.md is the second cross-vendor target, not the first.

### 3/4 — Several "primitives" are categories that haven't converged; the two-implementation rule should gate absorption

- **Track A:** fd-agent-platform-competitive P1-2 (code recon has prior art — Aider, Cursor, Cody — but no shape convergence).
- **Track B:** fd-browser-web-platform-standardization F-B5 (WHATWG two-impl rule maps directly).
- **Track C:** fd-hanseatic H-1 (memory + parallel-fleet + recon fail the substrate-vs-merchant test).

Add a "convergence signal" column to the prior 7: count substrate implementations + shape similarity score. Sequence absorption by convergence, not by user-pain rank.

### 2/4 — Trust scoring without routing-input is the masquerade pattern

- **Track C:** museum M-4 (trust assertion without citation backref).
- **Track D:** fd-yoruba-ifa-babalawo P1 (trust as routing consequence, not dashboard surface; PHILOSOPHY.md "Stages 1-2 without 3-4 is constant masquerading as intelligence").

Specify trust scoring's contract as the consultation-frequency derivative, not the score itself. Citation chain is mandatory and accessible from the score.

### 2/4 — Synthesis verdicts must be loanable

- **Track A:** fd-claude-code-product-surface P1-2 (parallel dispatch bundles three orthogonal seams).
- **Track C:** museum M-5 (no loan-record envelope joining verdict back to contributing agent IDs).

Synthesis verdict envelope: `{verdict, contributing-agent-IDs, finding-IDs cited, dissent recorded, returned-to-lender-on-failure: yes/no, reconciliation-path}`.

### 2/4 — Memory graduation as currently shipped is a destructive operation

- **Track C:** museum M-3 (overwrites prior state; chain that licenses the post-graduation claim is lost) + fd-carnatic C-3 (manodharma petrified as kriti — session-specific improvisation graduates as cross-project canon).
- **Track D:** fd-yoruba-ifa-babalawo P0 (canon-arbitrated divergence resolution requires the chain to be intact).

Persistence layer must be append-only even if user-visible state is current-state. Every persisted authority-bearing fact carries `layer: kriti | manodharma`, `source_class: observed | inferred | synthesized`, `as_observed_date + decay_rule`.

---

## Domain-Expert Insights (Track A)

The five Track A specialists added findings that required deep adjacent-domain knowledge to surface.

**MCP-shape vs host-shape (fd-mcp-protocol-architect):** Five of seven prior-pass primitives are MCP-shaped, not host-shaped. Memory → `memory://` resource scheme + `memory` capability. Coordination → `coordination` capability with interlock-shaped reference server. Cost observability → `_meta.cost` envelope on every tool-call response. Parallel fleet → `sampling/createMessageBatch` extension. AGENTS.md → `resources/subscribe` with drift-staleness notifications. Framing them as host primitives creates permanent cross-host fragmentation; a CC-internal memory means a user with six months of curated graduations cannot switch hosts.

**Marketplace UX as the unnamed primitive (fd-plugin-marketplace-economics):** Sylveste built five plugins (interplug + interpub + interform + intercheck + parts of interskill) just to make CC's plugin marketplace usable — discovery, ranking, trust signals, install metrics, dependency resolution, version compatibility. The prior 7 doesn't name this gap.

**Tool capability declaration (fd-agent-platform-competitive):** No MCP/CC concept exists for "this tool returns code-aware excerpts at a token budget" vs. "raw bytes." Cross-vendor primitive opportunity. Token-efficient code recon is not novel; Aider's repo-map (PageRank-over-symbols, Tree-sitter, token-budgeted) shipped 2023 — the right primitive is a tool-capability declaration plus reference implementation, not greenfield.

**Async session resumption protocol (fd-agent-platform-competitive):** LSP-shaped initialize/shutdown for sessions; standardize across Devin, Codex Cloud, CC.

**Three orthogonal seams in "parallel fleet" (fd-claude-code-product-surface):** Item 2 bundles fleet orchestration semantics, durable cross-subagent state, and fleet observability — three different surfaces. Decompose: ship parallel dispatch + finding-pipe + async session as floor; do NOT ship synthesis policy. Sylveste's flux-drive ≠ Compound Engineering ≠ Superpowers; absorbing the synthesis policy collapses three competing schools to one.

**The structural reframe (fd-developer-tooling-pm):** All seven primitives are seven instances of one substrate — a typed durable event ledger that closes the OODARC loop. Datomic facts + Git refs + reflog + OpenTelemetry + Bazel invocation analyzer all implement variants of `(append fact) / (observe scope as_of) / (subscribe predicate replay-from-event-id)`.

---

## Parallel-Discipline Insights (Track B)

Operational patterns from kernel, browser, DAW, and app-store disciplines that map directly to the target.

**Kernel "we never break userspace" (fd-kernel-syscall-stability-contract):** Each absorbed primitive ships with `STABILITY.md` declaring stable surface vs internal API vs deprecation window, plus a primitive-state schema common across primitives (read API, observe API, telemetry stream, optional write API). Maps to: every native primitive is published with a versioning contract and a public deprecation runway calendar. Without it, plugin authors freeze in wait-and-see for 6-18 months and substrate input flow collapses.

**Browser Origin Trials (fd-browser-web-platform-standardization):** Time-boxed, opt-in, instrumented absorption. Primitive ships in trial 3-6 months under `--enable-trial`, telemetry feeds shape decisions, commitment happens only after trial validation. Maps to: CC v3.0 ships parallel-fleet in trial; v3.2 commits or revises.

**Browser two-implementation rule (fd-browser-web-platform-standardization):** WHATWG requires two implementations before standardization. Maps to: a primitive is absorption-ready only when ≥2 substrate implementations have converged on a shape. Of the prior 7, multi-session coordination, observability, and AGENTS.md show convergence; memory, code recon, task tracker do not.

**DAW VST3 parameter-ID contract (fd-daw-host-plugin-format-economy):** Every plugin exposes parameters by ID with normalized [0,1] range, name, automation/recall semantics. The host iterates any plugin uniformly. Maps to: every absorbed primitive implements a state-enumeration API + observe API + telemetry stream. Cross-cutting plugins (interspect, interrank, intertrust) iterate primitives uniformly instead of per-primitive adapters.

**DAW host-mediated side-chain bus (fd-daw-host-plugin-format-economy):** Cross-plugin composition without ad-hoc IPC. Maps to: ship a typed event bus with optional ordering and persistence guarantees as part of the host-bus tier. Cross-cutting plugins subscribe instead of polling each primitive.

**App-store default-app pattern (fd-appstore-marketplace-sherlocking-economics):** iOS browser/mail/keychain history shows even capability-superior plugins lose to native placement until the platform ships default-app replacement. Maps to: absorbed primitives ship as user-replaceable defaults. CC config lets users redirect `Claude task` to interphase, native memory to interknow.

**App-store Sparkle survival template (fd-appstore-marketplace-sherlocking-economics):** Sparkle survived macOS native auto-update because the native version had residual-niche gaps (signing model, distribution channels). Maps to: per-absorption residual-niche statement (3-5 named survivor templates per primitive). Without it, plugin authors price in predation risk.

---

## Structural Insights (Track C)

The four distant-domain agents surfaced the deepest structural reframings.

**Hanseatic substrate-vs-merchant boundary (fd-hanseatic-stapelrecht-platform-vs-merchant-boundary).** The prior pass mixes substrate (loses value when fragmented) with merchant function (gains value from diversity) under one frame. The cog-hull dimension — the physical artifact that touches every harbor — is hook-event schema, not AGENTS.md. The Bruges-to-Antwerp shift suggests AGENTS.md may already be the wrong harbor: by 2030, multi-agent coordination weighs more than session-start configuration. The "deprecates X" framing is itself the herring-pricing mistake; reframe as "absorbs API contract; X reimplements as reference implementation." Concrete improvement.

**Museum registrar primitive (fd-museum-accession-provenance-evidence-chain).** The single most consequential structural reframe: 5 of 7 prior targets are catalog functions of one missing registrar primitive. The registrar issues an immutable accession ID at the moment of action; every plugin records that ID alongside its own; `chain_for(any_id)` returns the linked evidence chain. Concrete improvement. The composite specification: `assign + bind + append + surface`. Append-only persistence + deaccession protocol + citation-backref on scores are corollaries.

**Portolan chart-issue + Notice to Mariners (fd-portolan-chart-corrections-closed-loop-calibration).** The 8th primitive: a corrections feed with cadence. Distinct from observability, memory, and routing. Required fields: monotonic immutable issue numbers, source-class survival (observed | inferred | synthesized), `as_observed_date` + `decay_rule`, hazard-marker permanence layer, mandatory consumption at session start. Concrete improvement. The prior pass identifies observability as a deprecation target but stops at instrumentation — the cadence layer that publishes corrections fleet-wide is missing entirely.

**Carnatic bani-stamp + parampara lineage (fd-carnatic-guru-shishya-transmission-fidelity).** Voice (interfluence) and philosophy (interlore) unify as one missing primitive: the bani stamp. The prior pass treats them as adjacent; from the parampara lens they are the same commitment. Cross-vendor AGENTS.md without a `parampara` field becomes kriti detached from bani — receiving agents cannot tell which patterns are core (preserve verbatim) and which are local manodharma (improvisation). Auto-graduation conflates layers — petrifies manodharma as kriti. Concrete improvement: `lineage_for(artifact)` query as native primitive; SKILL.md schema enforces kriti/manodharma layer markers per step.

The four reframings compose: registrar (museum) joins horizontally across plugins; lineage chain (Carnatic) joins vertically through inheritance; substrate-vs-merchant (Hanseatic) is the disposition rule; corrections feed with cadence (portolan) is the loop-closing primitive. Together they produce a different release plan with the same long-term ecosystem improvement and a fraction of the marketplace damage.

---

## Frontier Patterns (Track D)

The three esoteric agents converged on a meta-finding: the prior pass under-specifies *shape* on three independent axes.

**Heian warifu — registry-shape vs warifu-shape (authority at verification time vs authority at signature time).** All seven prior-pass primitives are silently registry-shaped: validity at verification time depends on Anthropic's service still answering. PHILOSOPHY principle 1 ("evidence, not narratives") collapses to "every action produces a token pointing at a service that may not answer." The fix is a graceful-degradation specification per primitive: under Anthropic outage, durable memory does local file replay; multi-session coordination honors last-known reservation locally; cost receipts continue accumulating; the AGENTS.md file remains semantically valid for any compliant tool. **New design direction:** receipts cryptographically self-authenticating at signature time. Hidden coupling: interlock + intercept + intertrust + interspect are four implementations of one signed-decision primitive.

**Yoruba Ifá — three-primitives-as-one (canon-arbitrated divergence resolution).** Durable memory (item 1) + peer review (interpeer/intermonk) + trust scoring (intertrust) are three views of one integrated protocol. The integration is what the 63-plugin ecosystem keeps re-implementing privately because the prior pass treats them as independent. Resolution rule: canonical-precedent-attestation, not reputational standing. **Refines existing direction.** Adds the diaspora-survival test as the durability standard: if Anthropic disappeared, could two practitioners on different vendors cross-check each other's outputs against a shared canon and resolve divergences? Lineage propagation as marketplace economics — track plugin author lineages, not just download counts.

**Marshall rebbelib — runtime-query vs training-time-compilation.** Item 1 (durable memory) is one primitive in the prior pass and should be two. Eight plugins (intermem, interknow, interlearn, interlore, interfluence, interlens, interscribe, interseed) want the compilation primitive that doesn't exist. Cost asymmetry is dramatic at session-volume scale: the 2,285-token preamble trim was a one-time win against runtime context loading; without compilation as a primitive, the trim is structurally re-incurred every time content is added. **Opens a new design direction.** Inverts the marketplace shape: plugins providing compilable inputs (voice, lens, philosophy, style, naming, agent precedent) shift from "competing with the model" to "feeding the model better baseline behavior" — structurally more defensible than runtime-tool-vs-native.

The three lenses are mutually compatible and produce a single composite reframing: every prior-pass primitive needs three shape decisions before it can be specified as actionable infrastructure — registry-or-warifu, integrated-protocol-or-isolated-surface, runtime-or-compilation. The prior pass made none of these three decisions explicitly.

---

## Synthesis Assessment

**Overall quality of the target document.** Strong as a survey of pain; weak as a roadmap. The list of 7 deprecation targets correctly identifies where the 63-plugin ecosystem is paying tax, but it under-specifies *shape* on at least three axes (registry-vs-artifact, runtime-vs-compilation, mechanism-vs-policy) and over-bundles category absorptions that haven't converged with substrate absorptions that have.

**Highest-leverage improvement.** Ship a typed, durable, append-only evidence ledger with a registrar primitive (`quire` / `accession` / `chain_for(id)`) before any of the prior 7. The substrate is what all four tracks named independently as the missing precondition; without it, every absorption reinvents its own ID space and the integration matrix grows quadratically. The five observability plugins collapse into one canonical receipt format on this substrate. The "every action produces evidence" principle becomes enforceable rather than aspirational. Mechanism transferred: museum accession + Datomic append + warifu signature-time authority + portolan dated decay, composed as a single specification.

**Surprising finding.** No single track would surface this: the runtime-vs-compilation split (Track D, fd-marshall-rebbelib) plus the bani-stamp unification (Track C, fd-carnatic) plus the cost-line context (the 2,285-token preamble trim) together imply that 8-12 plugins are not runtime competitors at all — they are compilable-input feeders for a primitive that does not yet exist. Tracks A and B framed this as policy-bundling; only the esoteric and distant tracks named the shape (training-time absorption into agent baseline) and the implication (marketplace inverts from runtime competitors to baseline feeders).

**Semantic distance value.** The outer tracks (C, D) contributed insights qualitatively different from the inner tracks. Track A correctly named the substrate (typed durable event ledger) and the strategic frame (moat vs feature). Track B correctly named the staging mechanism (Origin Trials, two-impl rule, STABILITY.md). Track C and D added three things the inner tracks did not produce: (1) the registrar primitive's specific shape (assign + bind + append + surface, with `chain_for` query, citation-backref, kriti/manodharma layer markers, source-class survival, dated decay) — this is a concrete spec, not a vibe; (2) the cadence layer as a separate primitive distinct from observability — the 8th gap, single-track but testable; (3) the runtime-vs-compilation timing axis as additional to the substrate-vs-merchant boundary axis. These are not restatements in different vocabulary; they are specifications the inner tracks did not produce. The outer tracks earn their semantic distance.

**Hidden coupling.** Several plugins look independent but encode the same missing primitive. Three coupling clusters surface:
- **Signed-decision artifacts (Track D warifu):** interlock + intercept + intertrust + interspect — four implementations of authority-at-signature-time.
- **Canon-arbitrated divergence (Track D Ifá):** intermem + interpeer + intertrust + intermonk + interspect — five implementations of one integrated divergence-resolution protocol.
- **Training-time compilation (Track D rebbelib):** intermem + interknow + interlearn + interlore + interfluence + interlens + interscribe + interseed — eight implementations of one absent compilation primitive.
- **Hook-bus subscribers (Track A):** interwatch + interject + interlearn + tool-time + intercept + interspect + interpath + interlore + parts of intermem — all subscribe to events CC doesn't publish.

The overlap (intermem appears in three of four clusters; intertrust in two; interspect in three) is itself the deepest finding: the missing primitive is a single integrated shape with three faces — signed-decision artifacts that compile into baseline behavior and resolve divergence by canonical precedent. The prior pass under-specifies all three faces because it treats them as separate plugin categories.

**Counter-arguments — what Anthropic should NOT build:**
- **Native code recon (item #5).** Track C herring-pricing seizure (fd-hanseatic H-3); Track A no convergence signal (fd-agent-platform-competitive P1-2); Track B single substrate implementation fails the two-impl rule (fd-browser F-B5). Standardize a recon-API contract and ship a reference implementation; let plural plugins implement.
- **Multi-agent synthesis policy (subset of #2).** Track A names three competing schools (fd-plugin-marketplace-economics: Sylveste flux-drive ≠ Compound Engineering ≠ Superpowers); Track B names category-not-converged (fd-daw F-D1). Ship the dispatch mechanism and structured-finding emission; do not ship a winning synthesis algorithm.
- **Voice/style as runtime API.** Track A (no decoupling shape, no competitor ships it as platform); Track C (voice + philosophy unify as one bani primitive); Track D (voice is training-time, not runtime). Build the compilation primitive; let interfluence feed it.
- **AGENTS.md as runtime interpretation surface.** Track D rebbelib counter-argument 2 + warifu test (a Codex user must validate offline). Build cross-vendor file format + canonical compilation semantics; AGENTS.md remains inert at runtime.
- **Cognitive lens database (288 FLUX) as runtime tool catalog.** Track D rebbelib counter-argument 3. Per-consultation cost; a small compiled subset is the right shape.
- **Trust scoring as dashboard surface.** Track C museum M-4 + Track D Ifá P1. The dashboard duplicates the closed loop in human-readable form; without compilation into routing-frequency consequence, it is theatrical.
- **Memory hierarchy/graduation/decay as one primitive.** Track A (policy-bundled), Track B (VFS vs ext4 isomorphism), Track C (Hanseatic substrate-vs-merchant + museum catalog-vs-registrar), Track D (runtime-vs-compilation timing). Decompose; absorb only the substrate tier.
- **Cognitive lens content / philosophy observers / Slack integrations.** Track A: pure content; Anthropic has no authority on FLUX's 288 lenses or Sylveste's PHILOSOPHY.md.

The aggregate counter-argument from all four tracks: absorbing the floor (durable substrate, coordination capability, cost-receipt envelope, async sessions, hook-event schema, training-time compilation) is healthy. Absorbing the ceiling (synthesis policy, voice content, AGENTS.md authoring, ranked code recon, lens curation) trades a moated multi-year position for a quarterly feature win. This is the VSCode 2017-2019 lesson applied to the prior 7.
