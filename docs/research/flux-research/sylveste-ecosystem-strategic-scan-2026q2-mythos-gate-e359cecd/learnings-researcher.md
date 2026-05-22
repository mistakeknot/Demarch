---
type: strategic-scan
date: 2026-05-22
scope: "Institutional learnings relevant to Mythos-launch window (3-month horizon)"
coverage: "docs/solutions/, docs/research/assess-*.md, docs/research/, docs/brainstorms/, docs/plans/, docs/handoffs/"
key_findings: 10
synthesized_from: "flux-review platform update synthesis (2026-05-21)"
---

# Sylveste Ecosystem Strategic Scan: Institutional Learnings for Mythos Gate

## What We Already Know

### 1. Agent Routing & Calibration (L1-L2 coverage, L3-L4 gaps identified)

**Documented:** Interspect implements a graduated identification hierarchy for agent/model routing across Levels 1-2, well-covered by:
- `/home/mk/projects/Sylveste/docs/research/assess-identification-as-calibration.md` — frames routing as four-level escalation (metadata → prior traces → peer signal → benchmark probe). Level 2 (evidence-based overrides) is production; Levels 3-4 remain unimplemented.
- `lib-routing.sh` (Clavain) applies static metadata (model tier, safety floors, complexity classification) before evidence lookup.
- `routing-overrides.json` captures learned exclusions/promotions via counting-rule threshold detection over 90-day rolling windows.

**Gap:** Cross-project evidence aggregation (Level 3) has no infrastructure. Each project's `interspect.db` is isolated. Benchmark probes (Level 4) are not implemented.

**Relevance to Mythos:** Routing stability is load-bearing for multi-tier inference (Haiku → Sonnet → Opus escalation). Opus capacity constraints at launch require tight routing discipline.

---

### 2. Evidence Boundaries & Telemetry (Interspec, Intercore, Interstat, Interspect split)

**Documented:** 2026-05-21 flux-review synthesis (Finding 9) flags evidence/telemetry boundaries as blurry. Described as P2/P1 depending on scope.

**Current split:**
- Intercore: append-only kernel events (subprocess spawns, tool calls, exit status)
- Interspect: evidence analysis/profiling (routing patterns, confidence decay)
- Interstat: aggregate token metrics per agent×model (no sessions.db as of March 2026)
- Intertrack, Interpulse, Intercheck, Tool-time, Interrank: measurement silos without formal boundary spec

**Impact:** Routing, trust, and calibration decisions cannot rely on one authoritative flight recorder. Codex and Claude Code cannot compare their own effectiveness against a durable baseline.

**Relevance to Mythos:** v0.7+ autonomy claims require trustworthy evidence. Launch gates should enforce evidence-plane boundary definition before scaling agent autonomy.

---

### 3. Plugin Lifecycle & Inventory Drift (P1, not yet wired)

**Documented:** 2026-05-21 flux-review identified comprehensive inventory drift across ~60 live plugins:
- Some manifests declare fewer components than exist on disk.
- Marketplace entries don't map cleanly to current Interverse manifests.
- Zero/near-zero surface plugins still appear marketplace-live.
- Interspect described in docs as pillar but manifest doesn't expose claimed commands/hooks.
- Hook-loading contract contradictory (plugin.json vs. validation guidance).

**Verdict in synthesis:** Treat plugin inventory as generated supply-chain metadata. Add manifest ledger classifying every plugin by surface type and lifecycle tier.

**Follow-up beads filed:**
- `sylveste-b4ch` (P1) — Generate Interverse inventory from manifests and fail drift in doctor/CI
- `sylveste-i0sa` (P1) — Define Interverse plugin surface tiers and install profile packs

**Relevance to Mythos:** Codex needs native capability metadata, not translated Claude prompts. Install packs (core, review, docs, research, obs, mcp) must be defined before Codex integrates full Interverse.

---

### 4. Generated Agent Corpus Lifecycle (Hundreds of fd-* agents, stale index, L1-only loading)

**Documented:** 2026-05-21 flux-review Finding 4:
- `.claude/agents` is now platform state, not scratch output (~hundreds of `fd-*` agents, multi-megabyte corpus).
- Stale `.index.yaml`, many stub-tier agents, mixed generator versions.
- Prior research already calls out lifecycle gaps.

**Current behavior:** All agents eagerly loaded at SessionStart. Recall benefit of rare lenses is real but should be retrieved, not eagerly loaded.

**Recommendation:** Introduce active packs backed by indexed agent registry. Load proven/core agents by default, retrieve generated/stub agents by target hash/domain/frequency.

**Follow-up bead:** `sylveste-7zw2` (P1) — Implement generated-agent retention, pack-scoped loading, and stale index refresh.

**Relevance to Mythos:** Claude Code startup latency regression is observable. Codex should not inherit always-on 500MB agent corpus. Cost reduction without losing rare-lens value is leverage.

---

### 5. Worktree-First Coordination (Fix exists upstream, nested checkouts can be stale)

**Documented:** 2026-05-21 flux-review Verification Caveat + Finding 5:
- Interlock worktree-migration fix exists (`f1c79a2 Replace session index isolation with worktrees`).
- But permanent nested `interverse/interlock` checkout can lag origin/main, masking stale hook code.
- Root-level cleanliness doesn't prove nested plugin repos are current. This is especially dangerous for coordination, authz, publish, and hook plugins.

**Recommendation:** Add nested checkout freshness to Sylveste doctor/status. Make worktree-based isolation the canonical platform primitive.

**Follow-up beads:**
- `sylveste-x1rf` (P1) — Add nested plugin checkout freshness gate to Sylveste doctor
- `sylveste-n2ma` (P1) — Make worktree-first coordination canonical across Clavain, Codex, and Intercore

**Relevance to Mythos:** Multi-agent safety depends on which nested hook implementation is actually installed. Stale worktree state is a silent failure mode Sylveste should prevent.

---

### 6. Flux-Review Engine Cost & Concurrency (10/13/16-agent modes, no cost budget enforcement)

**Documented:** 2026-05-21 flux-review Finding 7:
- Engine is short and skill-driven but assumes it can generate specs, create agents, write artifacts without budget constraint.
- 10/13/16-agent modes with high token estimates. May 4 work identified concurrency caps, content-addressed caching, embedding triage, stall rescue as wins.
- Architecture still assumes read-write access; no ephemeral read-only mode for remote targets.

**Recommendation:** Add read-only mode for remote/protected targets. Move fan-out toward scheduler contract with explicit concurrency, budget, cache key, retry, partial-results, timeout semantics.

**Follow-up beads:**
- `sylveste-2o0s` (P1) — Add flux-review ephemeral read-only mode and cost controls

**Relevance to Mythos:** Claude Code can spend large review budgets unpredictably. Codex cannot safely run full engine against protected targets. Cost observability is critical for launch phase.

---

### 7. SessionStart Hook Load & Mutation Budget (Large, many hooks, implicit behavior)

**Documented:** 2026-05-21 flux-review Finding 6:
- Clavain SessionStart does setup checks, cache rewrites, Beads health, service queries, context injection, state recording, cleanup.
- Interverse adds many more hooks, each with fail-open behavior.
- Hook behavior is implicit and not cleanly represented in capability metadata.

**Recommendation:** Split SessionStart into cached read model plus explicit repair commands. Add hook health ledger tracking latency, exit status, mutation category, injected context bytes.

**Follow-up bead:** `sylveste-z55b` (P1) — Refactor Clavain SessionStart into cached read model plus hook health ledger.

**Relevance to Mythos:** Claude Code startup/resume predictability is user-facing. Hook budget regressions should be visible in doctor and publish checks before Mythos launch.

---

### 8. Interflux → Intersynth Dependency (Under-specified contract)

**Documented:** 2026-05-21 flux-review Finding 8:
- Interflux delegates synthesis to Intersynth but dependency is under-specified.
- Intersynth plugin exposes agents rather than stable skill/command contract.
- Interflux does not declare versioned dependency contract.
- A standalone Interflux install can appear valid while synthesis behavior is missing or drifted.

**Recommendation:** Define synthesis interface (inputs, output schema, error behavior, version range, fallback mode, conformance tests).

**Follow-up bead:** `sylveste-te7b` (P1) — Define and enforce the interflux-intersynth synthesis contract.

**Relevance to Mythos:** Flux-review is the canonical Mythos-launch gate review tool. Interflux/Intersynth dependency clarity is non-negotiable.

---

### 9. Codex Interflux Skill Mapping (Quick fix, P1, 3/4 track convergence)

**Documented:** 2026-05-21 flux-review Finding 1:
- Codex installer still maps Interflux through older skill names (`flux-engine`, `flux-drive` instead of current `flux-drive`, `flux-review`).
- `os/Clavain/scripts/install-codex-interverse.sh` contains stale references.
- Current commands delegate to `interflux:flux-engine` and `interflux:flux-review-engine`, but command-to-skill contract is not normalized.

**Recommendation:** Normalize skill IDs across plugin.json, command frontmatter, Codex installer mappings, docs. Add doctor assertion that every generated Codex link target exists.

**Follow-up bead:** `sylveste-wkjf` (P0) — Normalize interflux skill IDs across Claude manifest, commands, and Codex installer.

**Execution order:** First (small fix, high-confidence, direct Codex impact).

**Relevance to Mythos:** Codex is the secondary host surface for Mythos launch. Broken skill linking blocks Codex integration testing.

---

### 10. Drift Detection as Generalized Primitive (Interwatch/Interpath documented, not yet unified)

**Documented in memory + docs/handoffs/:
- Interwatch/interpath pattern: detect stale doc/config state, alert, repair.
- Applied to individual doc families (CLAUDE.md, AGENTS.md, plugin manifests, routing configs).
- Not yet generalized into a reusable platform primitive.

**Relevant patterns:** `/home/mk/projects/Sylveste/docs/solutions/patterns/` contains hook system adapter pattern, schema upgrade deployment, cross-hook marker coordination.

**Gap:** No unified drift detection framework. Each subsystem (plugin inventory, nested checkouts, evidence boundaries, generated agents) implements its own stale-state detection.

**Relevance to Mythos:** Platform state complexity is growing. Unified drift detection would unlock faster debugging and safer auto-repair.

---

## What We Forgot We Knew

### 1. Session Portability → Intercom Coordination Gap

**Past learning:** Dicklesworthstone batch 2 (March 1, 2026) assessed `cross_agent_session_resumer` (casr):
- Canonical session IR (messages, tool calls, metadata) could inform intercom's cross-agent conversation state.
- Intercom currently uses interlock for file-level coordination; session-level model could be useful for longer-running sprints.
- **Verdict:** adopt (tentative), monitor for stability.

**Currently in flight:** DeepSeek V4 spike handoff (May 17) mentions session detachment, worktree isolation, but does not reference casr or session-resumption patterns.

**Compounded knowledge:** Session portability assessment exists but isn't wired into Clavain's multi-sprint orchestration. If Mythos launch requires longer agent sessions (>1-2 hours), session resumption becomes critical.

---

### 2. Token Accounting (Context vs. Billing Split)

**Past learning:** `/home/mk/projects/Sylveste/docs/solutions/patterns/token-accounting-billing-vs-context-20260216.md` documents the distinction:
- Billing tokens (charged by API providers) ≠ context tokens (count toward window limits).
- Cache-hit tokens are billed at 10% but count fully toward cost estimation.
- Preamble tokens (system + memory + routing) are constant overhead, not per-turn.

**Currently in flight:** Microrouter redesign (May 4-11 brainstorms, heuristic baseline) focuses on latency/throughput but does not explicitly cost-gate routing decisions.

**Compounded knowledge:** Token accounting patterns are documented but routing decisions in Interspect and Clavain don't consistently apply the billing-vs-context split when evaluating cost thresholds.

---

### 3. Evidence Decay Policy (90-day rolling window documented, not universally applied)

**Past learning:** `/home/mk/projects/Sylveste/docs/solutions/patterns/decay-policy-standard-demarch-20260307.md` establishes 90-day rolling-window decay for all time-series evidence.

**Currently in flight:** Interspect applies this correctly (Level 2 evidence). Interstat delta aggregation (per memory) uses weighted averages but the decay window is not explicit in the estimate-costs.sh script.

**Compounded knowledge:** Decay policy exists but newer subsystems (interstat, interrank, intercheck) may not be enforcing it consistently.

---

## What We Should Learn Next (Mythos-launch leverage)

### Priority 1: Durable Execution Backend Assessment

**Open question:** Has Sylveste assessed Temporal, Restate, or Inngest as backends for agent runtime durability?

**Why it matters:** Long-running agent sessions (multi-step research, code review feedback loops, iterative planning) need durable execution. Clavain's current bead-driven model is plan-based, not execution-durable. Mythos agent autonomy at Level 3+ requires fault-tolerant execution primitives.

**Recommendation:** Assess durable-execution frameworks (Temporal, Restate, Inngest) against Sylveste's requirements. File outcome in assess-*.md. Verdict: adopt, inspire-only, or defer based on (a) integration surface, (b) cost per agent-second, (c) observability/evidence pipeline compatibility.

**Expected scope:** 1-2 assess docs, ~1 week of research spike.

---

### Priority 2: Eval/Calibration Backend Parity

**Open question:** Have we assessed Braintrust, Langfuse, or Arize as alternatives/complements to Interspect?

**Why it matters:** Interspect v0.6 handles single-project routing evidence. If Mythos scales multi-agent research fleets (32-agent research, 6-phase rollout per project memory), we need enterprise-grade eval infrastructure. Building Interspect + cross-project aggregation in-house vs. adopting a mature platform is a high-leverage decision.

**Recommendation:** Assess Braintrust (LLM-first eval platform), Langfuse (open-source observability), Arize (enterprise ML monitoring) against our evidence requirements and team capacity. File in assess-*.md.

**Expected scope:** 1-2 assess docs, evaluate proof-of-concept integration costs.

---

### Priority 3: Multi-Agent Interop Standard (MCP vs. A2A vs. AGNTCY)

**Open question:** Which protocol should Sylveste standardize on for agent-to-agent communication? MCP (tool-focused), A2A (OpenAI Agents SDK), or AGNTCY (emerging standard)?

**Why it matters:** Intercom currently relies on Interlock (file-based coordination) and Intermute (messaging). As agent count grows and Codex integrates, a protocol-agnostic interop layer becomes load-bearing. The 2026-05-21 flux-review flagged "Interflux depends on Intersynth without formal contract" — this is symptomatic of broader interop underspecification.

**Recommendation:** Assess MCP as primary protocol (already integrated), A2A as secondary (OpenAI agents), AGNTCY as emerging standard. Document protocol choice in philosophy.md. File in assess-*.md.

**Expected scope:** 1 assess doc, protocol decision ahead of Codex full integration.

---

### Priority 4: Drift Detection Unification

**Open question:** Should Interwatch/Interpath patterns be generalized into a reusable platform primitive?

**Why it matters:** We're re-implementing stale-state detection in plugin inventory, nested checkouts, evidence boundaries, generated agents. A unified drift-detection framework would unlock faster debugging and safer auto-repair, reducing manual intervention at launch.

**Recommendation:** Design drift-detection abstraction. Document in patterns/. Prototype on 2-3 high-value use cases (nested checkouts, plugin inventory, evidence boundaries). File follow-up bead.

**Expected scope:** 1 design doc + implementation bead (P1).

---

### Priority 5: Build-Decision Rationales (Why we didn't adopt X)

**Open question:** Are there documented cases where Sylveste chose "build" over "buy/adopt" and why?

**Why it matters:** The philosophy says "adopt mature tools, don't rebuild." If we have recent cases where we rejected a mature tool in favor of building in-house, documenting the rationale helps avoid repeating the decision and clarifies when to override the philosophy.

**Recommendation:** Audit recent architectural decisions (Interspect, Interstat, Intertrack, flux-review) and document "build vs. buy" rationale in philosophy.md or architecture.md. Call out assumptions that may have aged.

**Expected scope:** ~1-2 hours of structured review.

---

## Recommended Mythos-Gate Sequence

1. **Codex Interflux skill mapping** (P0, 1-2 hours) — unblocks Codex testing.
2. **Plugin inventory/drift gates** (P1, ~1 week) — data foundation for next steps.
3. **Nested checkout freshness** (P1, ~2-3 days) — prevents silent stale-state failures.
4. **Evidence-plane boundary definition** (P1, ~1-2 weeks) — prerequisite for v0.7+ autonomy.
5. **Durable execution backend assessment** (P1, ~1 week) — if long-running sessions are Mythos-critical.
6. **Build-decision rationale audit** (P1, ~2-3 hours) — philosophy clarity before scaling.

---

## Cross-Cutting Observations

**Converging pattern:** Sylveste has built most pieces well (Beads, Intercore, Clavain, Interverse, Interspect, Flux-review). The performance problem is now second-order: too many pieces are loaded, discovered, or trusted as if the ecosystem were small. Platform inventory and lifecycle tiers are the single highest-leverage change before Mythos launch.

**Most important finding:** Stale nested checkouts can mask upstream fixes. Platform safety requires freshness gates, not just post-incident review. This is the class of failure Sylveste should prevent.

**Cost opportunity:** Generated agent corpus and Flux-review fan-out should be retrieved and scheduled, not eagerly loaded. Active packs + Flux-review scheduler controls unlock token savings without losing rare-lens value.
