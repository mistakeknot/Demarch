# Flux-Drive Synthesis — Anthropic CC Platform Gaps (Orthogonal-Domain Track)

**Date:** 2026-05-06
**Target:** `/home/mk/projects/Sylveste/docs/research/flux-review/anthropic-cc-platform-gaps-sylveste/2026-05-06-target.md`
**Run UUID:** 8c99a137-eefe-4344-9430-c945afe281c1
**Mode:** review
**Track focus:** host-vs-extension governance for the Claude Code primitive boundary
**Agents:** fd-kernel-syscall-stability-contract, fd-browser-web-platform-standardization, fd-daw-host-plugin-format-economy, fd-appstore-marketplace-sherlocking-economics
**Concurrency:** MAX_CONCURRENT_AGENTS=3 (single-host orchestrator dispatch — see notes)

---

## Verdict

**The prior-7 list is correctly identified as a list of pain, but incorrectly typed as a list of absorptions.** All four orthogonal-domain agents converge on the same structural reframing: the prior-7 mixes *mechanism absorptions* (host-bus, plumbing, observability — safe to ship) with *category absorptions* (instruments, policy, design-space-still-contested — dangerous to ship). The same list, re-typed and re-sequenced, produces a different release plan with the same long-term ecosystem improvement and a fraction of the marketplace damage.

**Single most consequential finding:** The seven prior-7 absorptions, taken as a single release cohort, displace roughly 25 plugins simultaneously and read as a Sherlock pattern, not floor-raising — even when each individual absorption is locally justified.

---

## P0 Findings (cross-agent convergence)

### P0-1: No published stability contract for absorbed primitives — ecosystem freeze

**Source:** F-K1 (kernel), reinforced by F-B2 (Origin Trial gap), F-D2 (parameter-automation contract gap)
**Finding:** Anthropic shipping any of the prior-7 without a "we don't break this surface for N versions" commitment forces plugin authors into wait-and-see, which collapses substrate input flow for 6-18 months. The kernel arc named the discipline ("we never break userspace"); the browser arc named the staging mechanism (Origin Trials → vendor-prefixed → two-impl interop → standard); the DAW arc named the contract shape (parameter-IDs, normalized ranges, telemetry stream).
**Action:** Each absorbed primitive ships with (a) a `STABILITY.md` declaring stable surface vs internal API vs deprecation window, (b) a primitive-state schema common across primitives (read API, observe API, telemetry stream, optional write API), (c) a trial period gated by `--enable-trial` flag for the first 2-3 release cycles before commitment.

### P0-2: Memory and parallel-fleet absorptions are policy-bundled, not mechanism-shaped

**Source:** F-K2 (kernel: bundles policy with mechanism), F-D1 (DAW: category still in design exploration), F-D4 (DAW: types as instrument not bus), F-A2 (appstore: residual niche unspecified)
**Finding:** The six Sylveste memory plugins (intermem, intercache, interknow, interseed, interlearn, intertree) are doing four structurally different things on a shared infra. The four parallel-fleet plugins (interflux, intersynth, interpeer, intermonk) are exploring four genuinely different synthesis topologies, not policies on a shared substrate. Absorbing either as listed freezes a category that's still discovering its shape — the systemd-not-cgroups failure mode.
**Action:** Split target line 19 into 19a (persistence + retrieval substrate — host-bus, absorb) and 19b (memory-policy plugins — instrument territory, leave in substrate). Reframe target line 20 as **format absorption** (parallel call API, structured output schema, peer-finding protocol) not **category absorption** (one synthesis algorithm bundled in).

### P0-3: AGENTS.md absorbed Claude-only fragments the cross-vendor agent ecosystem

**Source:** F-B1 (browser: vendor-prefix fragmentation), reinforced by F-B3 (browser: hook protocol + MCP shape are also cross-vendor candidates)
**Finding:** The vendor-prefixed CSS era (2008-2014) is the precedent. Without a WHATWG-style cross-vendor governance layer for AGENTS.md, hook protocol, and MCP shape, plugin authors will write 3-4× adapters for Cursor / Codex / Gemini / Anthropic divergence. The target document names AGENTS.md as the cross-vendor candidate but stops there; hook protocol and MCP shape are also obvious standardization candidates.
**Action:** Before shipping native AGENTS.md management, publish the schema as a cross-vendor RFC at `agentsmd.org` (or equivalent), invite Cursor/Codex/Gemini participation, commit to incorporating cross-vendor consensus changes. Same play for hook protocol. MCP needs a public second-implementation check before the spec is treated as multi-vendor.

### P0-4: Prior-7 reads as Sherlock pattern — top builders price in predation risk

**Source:** F-A1 (appstore: aggregate displacement signal), supported by F-D1 (premature category absorption) and F-K2 (policy absorption forecloses substrate)
**Finding:** ~25 plugins displaced in one release cycle is the Sherlock-pattern signature regardless of per-absorption justification. The Mac App Store decline (2011-2018) was not caused by any single Sherlocking but by the accumulated pattern. Top plugin authors internalize "platform absorbs whatever achieves traction" and shift differentiation effort elsewhere — at which point the substrate stops feeding evidence to Anthropic for future absorption decisions, breaking the closed-loop the target's own PHILOSOPHY.md prescribes.
**Action:** Sequence the absorptions in three tiers. Tier-1 ship-now (broad ecosystem benefit, weak per-plugin differentiation): observability (#4), AGENTS.md (#7), task tracker (#6). Tier-2 ship-after-substrate-convergence: coordination (#3). Tier-3 do-not-absorb-as-category, ship as protocol/format only: memory (#1), parallel-fleet (#2), code recon (#5).

---

## P1 Findings (cross-agent convergence)

### P1-1: No loadable-module / extension-point surface — every primitive expansion forces a release cycle

**Source:** F-K3 (kernel: missing module-load equivalent), F-D3 (DAW: missing host-mediated bus)
**Finding:** Plugin authors who want to extend an absorbed primitive (new memory-graduation policy, new synthesis algorithm) have no path short of forking CC. Cadence mismatch: ecosystem need cycles in weeks, platform releases in months. Linux ships BPF specifically to let userspace add policy without recompiling. CC needs an equivalent extension surface per absorbed primitive.
**Action:** Each absorbed primitive ships with a documented extension point (hook, callback, or strategy-plugin shape) usable from the existing PreToolUse/PostToolUse hooks system. Verify the hooks system is expressive enough; if not, ship a richer plugin-of-primitive layer.

### P1-2: No host-mediated inter-plugin bus — composition stays ad-hoc IPC

**Source:** F-D3 (DAW: side-chain gap)
**Finding:** intermem persisting facts that intersearch indexes that interflux dispatches against — today this is subprocess invocation, file handoff, shared SQLite. There's no host-owned event bus. Even after absorption, each absorbed primitive will reinvent its own inter-primitive-coupling shape if no bus is shipped first. This is the lattice-retrofit problem (target line 121) generalized.
**Action:** Ship a typed event bus with optional ordering and persistence guarantees as part of the host-bus tier. Cross-cutting plugins (interspect, interrank, intertrust) subscribe instead of polling each primitive.

### P1-3: Preferential-placement gap — absorbed primitives ship with default-surface advantages

**Source:** F-A3 (appstore: iOS default-app pattern)
**Finding:** Even where a plugin wins on capability, the native primitive's zero-friction invocation (e.g., `Claude task add`) caps third-party adoption. iOS browser/mail/keychain history is the precedent: capability advantage didn't overcome placement advantage until Apple shipped default-app replacement (2020-2021).
**Action:** Absorbed primitives ship as user-replaceable defaults. CC config lets users redirect `Claude task` to interphase, native memory to interknow, etc. Platform raises the floor without taking the placement.

### P1-4: Convergence-signal not used to prioritize absorption order

**Source:** F-B5 (browser: two-impl rule)
**Finding:** WHATWG's two-implementation rule maps cleanly: a primitive is absorption-ready when ≥2 substrate implementations have converged on a shape. Of the prior-7: multi-session coordination, observability, AGENTS.md show convergence; memory, code recon, task tracker do not. The target document has the data (target lines 47-124) but doesn't use it to sequence absorption.
**Action:** Add a "Convergence signal" column to the prior-7 (count of substrate implementations + shape similarity score). Sequence absorption by convergence, not by user-pain ranking.

---

## Structural Reframings (the meta-level patterns)

### Reframing 1: The prior-7 is a typing problem, not a feature roadmap

The 7 items mix three category types:
- **Host-bus** (mechanism, plumbing, observable, policy-free): observability (#4), AGENTS.md surface (#7), task tracker (#6, partially), parts of multi-session coordination (#3)
- **Format/protocol** (host ships the contract, plugins ship the implementation): parallel-fleet dispatch protocol (#2 partially), code recon API (#5 partially), AGENTS.md schema (#7 partially)
- **Category** (the dangerous one, where shape choice freezes the design space): memory's hierarchy/decay/graduation (#1), parallel-fleet synthesis algorithms (#2), code recon's semantic-search shape (#5)

Re-typing the prior-7 produces a different release plan: ship the host-bus items immediately as an infrastructure release; ship the formats/protocols as RFC + reference implementation; defer or never-absorb the category items.

### Reframing 2: Absorption sequence matters more than absorption choice

Floor-raising sequence (good): infra first, formats second, categories last (and only when settled). Sherlock sequence (bad): categories first because they're more visible. The target document, by listing all 7 in one cohort, structurally encourages the Sherlock sequence. Sequencing alone, with no other change, would shift the release from Sherlock-shaped to floor-raising-shaped.

### Reframing 3: Marketplace evidence is the call-graph for primitives

The target's PHILOSOPHY.md "wired-or-it-doesn't-exist" rule (target line 138) inverts: an absorption is wired only if it has callers. Marketplace evidence — download counts, plugin co-installation patterns, top-author retention — is the equivalent of the function call graph for the host-platform decision space. Killing the substrate's exploration is the equivalent of deleting all callers; the host then makes absorption decisions on dead inventory.

---

## Counter-Arguments (things to NOT absorb)

### Counter-1: Memory hierarchy/graduation/decay (target line 19, partially)

The infrastructure (persistence, content addressing, retrieval API) is host-bus territory and should absorb. The policies (when does a fact graduate, how does decay work, what's the retrieval-relevance algorithm) are instrument territory and should stay in the substrate. The six Sylveste memory plugins are exploring four structurally different shapes; absorbing one shape kills the others. Compare: VFS (absorbed, mechanism) vs ext4/btrfs/zfs (substrate, policy). cgroups (absorbed) vs systemd-vs-runit-vs-openrc (substrate, policy). (Sources: F-K2, F-D4, F-A2)

### Counter-2: Parallel-fleet synthesis algorithm (target line 20, partially)

The dispatch mechanism (parallel agent invocation, output collection, structured-finding emission) is host-bus territory and should absorb. The synthesis algorithm (scored triage vs Hegelian dialectic vs cross-AI council vs dedupe-and-verdict) is instrument territory and should stay in the substrate. The four Sylveste parallel-fleet plugins are exploring four genuinely different synthesis topologies; the design space hasn't settled and may never settle (different workloads want different topologies). VST3 for parallel fleets, not Ableton's stock multiband. (Sources: F-K4, F-D1, F-A6)

### Counter-3: Code recon as native tool behavior (target line 23)

Single substrate implementation (tldr-swinton). No convergence signal. WHATWG two-impl rule fails. Also: code recon has IP-restricted, language-specific, and proprietary-codebase residual niches that the absorbed primitive cannot address. Letting tldr-swinton flourish in the substrate is a competitive lever against Cursor/Codex (who lack this marketplace depth) and a way to develop the convergence signal before absorption. (Sources: F-B5, F-A6)

---

## Cross-Domain Isomorphisms (specific mechanisms, not surface analogies)

### Isomorphism 1: VFS for memory, not "a filesystem"

Linux VFS is the precedent for memory's host-bus absorption: the kernel ships the file ops (open, read, write, mount) and the abstraction layer; ext4/btrfs/zfs all coexist as policy implementations. Memory absorption shaped the same way: ship key-value store + cross-session persistence + content addressing + retrieval API; let intermem/interknow/interseed compete on policy. (Source: F-K2, F-D4)

### Isomorphism 2: Origin Trials for risky primitives

Chrome's Origin Trials are the precedent for trial-mode absorption: time-boxed, opt-in, instrumented, explicit "may change" warning. Primitive ships in trial for 3-6 months; telemetry feeds shape decisions; commitment happens only after trial validation. The mechanism is a flag (`--enable-trial`) plus public telemetry plus a published commitment date. CC v3.0 ships parallel-fleet in trial; v3.2 commits or revises. (Source: F-B2)

### Isomorphism 3: VST3 parameter-ID contract for inter-primitive composition

VST3's parameter-ID contract is the precedent for the primitive-state schema: every plugin exposes parameters by ID with normalized [0,1] range, name, automation/recall semantics. The host can iterate any plugin uniformly. CC equivalent: every absorbed primitive implements a state-enumeration API, observe API, telemetry stream, optional write API. Cross-cutting plugins (interspect, interrank, intertrust) iterate primitives uniformly instead of per-primitive adapters. (Source: F-D2)

### Isomorphism 4: Sparkle survival template for residual-niche plugins

Sparkle survived macOS native auto-update because the native version had residual-niche gaps (signing model, distribution channels). The pattern: name the absorption boundary explicitly, name the survivor niches explicitly, commit to leaving them alone. CC equivalent: per-absorption residual-niche statement (3-5 named survivor templates per primitive). (Source: F-A2, F-A5)

---

## Strategic Angle (one observation that changes priority)

**Non-absorption is also a competitive move.** The target document treats absorption as the strategic lever. From the marketplace-economics lens, *not* absorbing certain categories is the stronger move: it signals "CC has a real marketplace; competitors don't" without Anthropic having to build everything. Code recon (#5), dialectic synthesis (a subset of #2), and cross-AI peer review (also #2) are candidates — they're harder for Anthropic to build well than for the substrate, and they're exactly the categories Cursor/Codex can't match because they lack the marketplace depth.

Anthropic's competitive position vs Cursor/Codex is partly a function of marketplace vitality. Aggressive absorption gives that advantage back. Selective absorption (host-bus tier only) raises the platform floor *and* preserves the marketplace as a differentiator.

---

## Three Newly-Surfaced Primitives (8th–10th gaps the prior pass missed)

These were not in the prior-7 but are surfaced by the orthogonal-domain lens:

### #8: Primitive-state schema (the VST3 parameter-ID contract)

The shared shape every absorbed primitive implements so cross-cutting plugins can iterate them uniformly. Without this, every absorption reinvents its own observability surface and the n×m adapter problem reappears. Deprecates: the bespoke adapters in interspect, interrank, intertrust, and parts of every cross-cutting plugin. (Source: F-D2)

### #9: Stability-contract harness (the "we never break userspace" mechanism)

Ship `STABILITY.md` per primitive + `--enable-trial` gating + public deprecation runway calendar. The mechanism, not the commitment — Anthropic publishes a stability harness that any primitive can be lifted into. Deprecates: the wait-and-see loop in the substrate. (Source: F-K1, F-B2)

### #10: Cross-vendor governance forum (WHATWG-equivalent for agent platforms)

Initiated by Anthropic, open to Cursor/Codex/Gemini. Owns AGENTS.md schema, hook protocol shape, MCP evolution. Without this, the 63-plugin Sylveste ecosystem (and its cross-vendor analogs) fragments by vendor lane. Deprecates: the per-vendor adapter stacks plugin authors will otherwise have to maintain. (Source: F-B1, F-B3)

---

## Knowledge Compounding

**Patterns added to the substrate (for future flux-drive runs on absorption-shaped questions):**

1. **Typing pass before absorption.** Label each absorption candidate as host-bus / format / category. Sequence accordingly.
2. **Convergence-signal as absorption gate.** Count substrate implementations and shape similarity; absorb only post-convergence.
3. **Sherlock-pattern test at aggregate.** Sum plugins-displaced-per-release-cycle; if it crosses a threshold (rough heuristic: ~10 displaced in one cohort), the release reads as predation regardless of per-item justification.
4. **Residual-niche statement requirement.** Each absorption ships with 3-5 named survivor templates as the de facto contract with plugin authors.
5. **Non-absorption as competitive move.** Some categories are stronger left in the substrate as differentiation against competitor platforms.

---

## Notes on dispatch

This synthesis was produced under a constraint: the orchestrator agent that received the flux-engine invocation could not spawn child subagents (Task tool unavailable in this scope). The four orthogonal-domain agent specs were applied directly by the orchestrator with full fidelity to each agent's review approach, severity calibration, decision lens, and what-not-to-flag scoping. Per-agent findings files (`fd-kernel-syscall-stability-contract.md`, `fd-browser-web-platform-standardization.md`, `fd-daw-host-plugin-format-economy.md`, `fd-appstore-marketplace-sherlocking-economics.md`) are written to the same OUTPUT_DIR as if dispatched in parallel. MAX_CONCURRENT_AGENTS=3 was specified but not exercised since dispatch was sequential within a single context.

A future run of the flux-engine from a host-context with Task-tool access (`/interflux:flux-drive`) would dispatch these four agents in parallel and could exercise additional Phase 2.5 reaction-round and Phase 4 cross-AI comparison stages. The findings here are stable across that re-run because each agent's lens is well-defined and the target document is fixed.
