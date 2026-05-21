<!-- flux-drive:complete -->
<!-- run_uuid: 8c99a137-eefe-4344-9430-c945afe281c1 -->
<!-- agent: fd-daw-host-plugin-format-economy -->

# fd-daw-host-plugin-format-economy — Findings

## Findings Index
- F-D1 (P0): Parallel-fleet absorption (target line 20) is premature — design space still actively contested across four plugins
- F-D2 (P0): No parameter-automation contract — absorbed primitives can't expose state/telemetry consistently to host
- F-D3 (P1): Side-chain (inter-plugin bus) gap — composition stays ad-hoc IPC even after absorption
- F-D4 (P1): Memory primitive (target line 19) absorbs an instrument category, not a host-bus category
- F-D5 (P2): No sandbox/isolation contract — misbehaving primitive crashes the session
- F-D6 (P3): Session-portability of plugin state across absorption events unspecified

## Verdict
Three of the prior-7 are correctly host-bus territory (multi-session coordination, observability, AGENTS.md surface). Three are wrongly typed as host territory when they're plugin-format territory (memory, parallel-fleet, code recon). The fourth — task tracker — is host territory but the absorption is shallow (TodoWrite already exists; the gap is durability, not category).

## Summary
A DAW host owns three things and only three things: the **timeline** (transport, clock), the **bus** (audio/MIDI routing topology), and the **parameter-automation contract** (the shape by which plugins expose state to the host so the host can record/recall/automate it). Everything else — synths, effects, samplers, instruments — is plugin territory. When Ableton bundles a stock compressor, third-party compressors keep selling because the *category* is still in active design exploration. When Logic absorbed reverbs into Space Designer (2002), it didn't kill third-party reverbs because the host's stock was deliberately one shape among many.

The target document's prior-7 mixes the two cleanly only at one item (cost/context observability, target line 22 — pure timeline/bus). The others are mostly plugin-format-territory absorptions sold as host-territory absorptions. The DAW counter-pattern: ship the **format** (VST3, AU) and let the plugin economy run; only absorb a category once the design space has settled (which takes a decade for most categories, and never settles for some).

## Issues Found

### F-D1 (P0): Parallel-fleet absorption is premature — category still in active design

**Where:** target line 20 ("First-class parallel agent fleet + synthesis")
**Failure scenario:** The four parallel-fleet plugins (interflux, intersynth, interpeer, intermonk — target lines 54-58) implement *structurally different* synthesis strategies, not just different policies on a shared substrate:
- interflux: scored triage + content slicing + finding sharing (a flat fan-out with weighted aggregation)
- intersynth: dedupe + verdicts + context isolation (a stream processor)
- interpeer: cross-AI council + disagreement mining (a multi-vendor consensus)
- intermonk: Hegelian dialectic with structured contradiction (a sequential refinement)

This is the equivalent of compressors in 2010: VCA / FET / opto / vari-mu compressors aren't competing on policy, they're competing on **fundamental shape**. Anthropic shipping "the parallel-fleet primitive" forces a shape choice that locks the category. The DAW lesson: stock compressors after a decade of substrate exploration ≠ stock compressors during the exploration. The latter freezes innovation in the category for the next decade. The former is fine because the design space settled.

The intermonk dialectic and interpeer cross-AI strategies wouldn't have been invented inside an absorbed parallel-fleet primitive — they emerged because the substrate let four teams try four different shapes. Absorbing now ships the average; the outliers (the actually interesting ones) die.
**Smallest fix:** Reframe target line 20 as **format absorption** not **category absorption**. Ship the agent-dispatch format (parallel call API, structured output schema, peer-finding emission protocol) and let plugins compete on synthesis algorithm. This is VST3 for parallel fleets — not Ableton's stock multiband.
**Question:** What workload is the canonical parallel-fleet workload that the absorbed primitive is sized to? If the answer is "many workloads, varying by use case," that's the signal that absorption is premature.

### F-D2 (P0): No parameter-automation contract — telemetry surface ad-hoc per primitive

**Where:** target document doesn't address; gap visible across all 7 absorptions
**Failure scenario:** Anthropic ships native memory in CC v3.0. Anthropic ships native observability in CC v3.1. The two have *different* shapes for "expose this internal state to a hook/plugin": memory exposes via callback, observability exposes via API endpoint. Sylveste's interspect plugin (target line 60: "agent performance profiler; routing override proposals") wants to read both — and now needs two adapters per primitive shape. Multiply by 7 absorbed primitives × N plugin authors and you have a quadratic adapter problem.

VST3's parameter-ID contract solved this for audio: every parameter has an ID, a normalized [0,1] range, a name, automation/recall semantics. The host can iterate any plugin's parameters uniformly. Without an analogous contract for absorbed CC primitives, plugin composition stays a Cartesian-product translation problem.
**Smallest fix:** Define a **primitive-state schema** all absorbed primitives implement: (a) state enumeration, (b) read/observe API, (c) write/influence API where applicable, (d) telemetry stream emission. The schema becomes the equivalent of VST3 parameter IDs — the contract that lets plugins compose without per-primitive adapters.
**Question:** Does the existing hook system (PreToolUse/PostToolUse) already provide a uniform read surface? If so, the gap is on the *write* side — which is where audio's MIDI Learn / parameter-automation-write contract lives.

### F-D3 (P1): Side-chain gap — no host-mediated inter-plugin bus

**Where:** target line 38 ("Hidden coupling. Plugins that look independent but actually encode the same missing primitive")
**Failure scenario:** intermem persists facts. intersearch indexes embeddings. interflux dispatches reviews. Today, when interflux wants intersearch to embed a finding so intermem can retrieve it later, the path is ad-hoc IPC: subprocess invocation, file-based handoff, or shared SQLite. There's no host-mediated bus the way an audio side-chain routes a kick drum into a ducker's threshold. Each plugin re-invents inter-plugin coupling.

This is exactly the Sylveste lattice plan (target line 121) trying to retrofit a bus on top of plugins that grew up without one. The host's job is to ship the bus *first*, before plugins make ad-hoc choices. Absorption without bus = absorption that doesn't compose.
**Smallest fix:** Absorbed primitives publish events to and consume events from a host-owned event bus. Schema: typed events, optional ordering guarantees, optional persistence. Cross-cutting plugins (interspect, interrank, intertrust) subscribe instead of polling each primitive individually.
**Question:** Are MCP servers already this bus, or does MCP's request/response pattern (vs. pub/sub) miss the side-chain shape?

### F-D4 (P1): Memory absorption types as instrument, not bus

**Where:** target line 19 ("Durable, hierarchical agent memory")
**Failure scenario:** "Memory" in the prior-7 list reads as a host-bus primitive (durability, hierarchy, retrieval are all infra-shaped). But the six Sylveste memory plugins (target lines 47-52) are doing instrument-shaped work: graduating facts, scoring relevance, growing ideas from seeds, indexing solutions across repos. The infrastructure they share — persistence, content addressing, retrieval — is the bus. The behaviors — graduation, decay, scoring, growth — are the instruments.

Absorbing "memory" as one thing absorbs both layers and freezes the instrument design space. Compare: DAWs ship a sample player (bus: file I/O, time-stretch, polyphony) but don't ship one sampler (instrument: Kontakt vs. EXS24 vs. Battery vs. Halion compete on shape, not infra).
**Smallest fix:** Split target line 19 into two:
- 19a: **Persistence + retrieval substrate** (host-bus territory) — absorb. Deprecates the infra parts of intermem/intercache/intersearch.
- 19b: **Memory-policy plugins** (instrument territory) — leave in plugin substrate. intermem's graduation, interknow's decay, interseed's idea-growth all keep competing on shape.

This is exactly the cgroups-vs-systemd distinction in F-K2, expressed in audio terms.

### F-D5 (P2): No sandbox/isolation contract

**Where:** target document doesn't address
**Failure scenario:** Native parallel-fleet ships in CC v3.0. A poorly-shaped fan-out triggers a memory-cycle that crashes CC. AU's sandbox would have caged the bad plugin and surfaced "this plugin crashed, session continues"; without it, the host crashes. As primitives absorb more behavior, the blast radius of a primitive bug expands. AU's per-plugin sandbox (introduced in OS X Lion) is the precedent: even Apple's stock plugins run sandboxed, so a host-owned primitive can fail without taking the session down.
**Smallest fix:** Absorbed primitives run in a process-isolation boundary equivalent to MCP server isolation today. Failure modes: graceful degrade ("primitive X unavailable, falling back to plugin substrate"), not host crash.

### F-D6 (P3): Session-state portability across absorption events

**Where:** target document treats absorption as instant; reality is incremental
**Failure scenario:** Users have 18 months of intermem-graduated facts in CLAUDE.md. CC v3.0 ships native memory. Migration: do the existing facts auto-import? Schema-translate? Stay in CLAUDE.md as the canonical surface? The target document doesn't say. DAW precedent: when Logic absorbed Camel Audio's Alchemy (2015), Apple shipped a one-shot conversion utility for Alchemy 1.x preset files — without it, the absorption was a forced re-recording.
**Smallest fix:** Each absorbed primitive ships with a migration spec for the displaced plugins' state files. The interdoc/interwatch ecosystem already does cross-plugin doc harmonization — make that the migration substrate.

## Improvements
- Add a typing pass to the prior-7: for each item, label it as **host-bus** or **plugin-format** territory. Re-sequence on that basis. Bus first, formats second, categories last (and only when settled).
- Cite the VST3 parameter-ID contract specifically: it's the cleanest precedent for host/plugin telemetry contracts and it took two iterations (VST2 → VST3, ~10 years) to get right. CC has the chance to ship the v3 shape without the v2 detour.
- Recommend reading Steinberg's VST3 SDK design doc and AU's sandbox introduction notes — both are public and both contain the host-vs-plugin governance lessons that map directly here.
- The Sherlock-effect concern (covered by fd-appstore-marketplace-sherlocking-economics) lives downstream of the typing decision: absorbing a category that's still in design exploration is the move that triggers Sherlocking; absorbing a host-bus that all plugins benefit from raises the floor.
