---
artifact_type: research-synthesis
method: repo-research-analyst
target: "Sylveste repository operational state vs. strategic positioning"
date: 2026-05-22
scope: "Pillar maturity, P0 epics, closed-loop wiring, flux-review findings, velocity"
---

# Sylveste Ecosystem Strategic Scan — Q2 2026 Mythos-Gate Readiness

**Summary:** Sylveste has built most of the right architectural pieces but is now suffering from scale-induced inventory and coordination problems. The platform has outgrown manual manifest discipline and checkout-freshness assumptions. The leverage in the next 3 months is not new capability — it's platform consolidation and wiring of existing components into functioning closed-loop systems.

---

## 1. Pillar Maturity Status (6 Pillars, 3 Layers)

**Actual breakdown:** 60 Interverse plugins across 3 layers: L1 kernel (Intercore), L2 OS (Clavain, Skaffen, Zaka, Alwe), L3 apps (Auraken, Autarch, Intercom, Khouri, Meadowsyn, interblog, intersite). Two substantial epics sit outside the traditional 6-pillar framework: Auraken→Hermes personality overlay and Ockham governance layer.

**Promotion Criteria Registry snapshot (per subsystem):**
- **Intercore (Persistence):** M2 — event integrity proven over 1,000+ runs; crash recovery and schema migration still pending 60–90 day observation windows.
- **Interlock (Coordination):** M2 — < 5% reservation conflict rate, 10+ concurrent agents without deadlock; conflict auto-resolution and adaptive timeout tuning pending.
- **Interject (Discovery):** M2 — 20%+ promotion rate on 50+ discoveries; interest profile convergence and auto-create accuracy still in-flight.
- **Interflux (Review):** M2 — 60%+ finding precision, < 30% false positive rate; cross-model disagreement yield and agent self-retirement pending.
- **Interop (Integration):** M1 — Notion sync working; 90%+ conflict resolution and bidirectional latency < 5s not yet observed at scale.
- **Hassease (Execution):** M0 → M1 transition in-flight (signal daemon not yet shipping). Cost-routed model delegation entirely future.
- **Interweave (Ontology):** M1 — query structure exists; 60%+ hit rate and cross-system entity resolution pending 30–45 day windows.
- **Factory Substrate (Measurement):** M1 — 30–40% attribution chain completeness; 80%+ requirement and FluxBench drift detection still pending.
- **Ockham (Governance):** M1 — authority event accuracy and zero unauthorized actions still requiring 45–90 day windows.
- **Interspect (Routing):** M2 — gate pass rate > 70%, model cost ratio < 80% of Opus baseline; override accuracy and canary precision pending 60 day observation.

**Key gap:** Most subsystems are M1–M2 (Built → Operational), but the transition from M2 → M3 (Calibrated) requires 45–90 day observation windows with specific evidence thresholds. **The system is _not_ at M3 Calibrated on any core subsystem yet.** M2 means the code is there and basic operation works. M3 requires proof of adaptive behavior (calibration, self-adjustment, learning) over time.

---

## 2. Open P0 Epics: Status, Age, Blockers, and Leverage

**15 P0 issues tracked; 12 open, 3 in-progress. Recent 60-day velocity: 1,202 commits, ~155 closed beads.**

| Bead | Title | Status | Age | Blocker | Leverage if shipped |
|------|-------|--------|-----|---------|-------------------|
| `sylveste-22oi` | Auraken → Hermes overlay: strategic epic | Open | ~2mo | Depends on Signal transport (benl.6); Lens selection MCP (4vbg) | Personality-driven routing + Telegram surface |
| `sylveste-248r` | Onboarding: intake flow + 3-message bootstrap | In-progress | ~1.5mo | Needs Meadowsyn polish; signal UX flow | Sub-60min time-to-first-change for external users |
| `sylveste-2nfd` | Design transport interface abstraction (Intercom) | Open | ~3mo | Abstract over Signal/gRPC/HTTP; signature of remaining work | Codex, Hermes, and heterogeneous agent protocols |
| `sylveste-benl` | Auraken → Skaffen Go migration [epic] | Open | ~2.5mo | Lens library port (benl.1), style fingerprinting (benl.2), user identity DB (benl.10), Signal transport (benl.6) | Self-directed Go agents + lower latency |
| `sylveste-heh8` | Deploy Auraken-as-Hermes on Signal | Open | ~1.5mo | Hermes overlay + Hassease daemon M1 | Working agent on production surface |
| `sylveste-iaqg` | Interflux pre-launch readiness [epic] | Open | ~2.5mo | Test scaffolding, kill-switch tests, telemetry, contract pinning, link checks, rollback | Safe public review engine |
| `sylveste-myyw` | Autonomy A:L3 — all three calibration loops | Open | ~2mo | Routing override collection + anomaly flagging; gate-tier outcomes; phase-cost anomaly receipts | Closed-loop cost calibration at Mythos launch |
| `sylveste-nr6x` | Hassease: multi-model code daemon (Signal-native, cost-routed) | In-progress | ~2mo | Forge tool whitelist (nr6x.1 shipped); execution sandboxing | Codex + Hermes dispatch to cheaper models |
| `sylveste-oyrf` | Longitudinal cost-calibration + Mythos artifacts | Open | ~1.5mo | Depends on A:L3 wiring; cost-trajectory.csv generation + `.github/workflows/oyrf-cost-calibration.yml` | Public proof of cost efficiency |
| `sylveste-3rod` | Mythos launch readiness [meta-epic] | In-progress | ~4mo | Gates on all above + docs, brand, Ops stack | Launch gate itself |

**Convergence:** Hermes overlay, Skaffen Go migration, and Hassease daemon are all **parallel-path blockers** for Mythos. All three depend on Signal transport abstraction (benl.6). Autonomy A:L3 (routing + calibration) is the critical path for the cost story.

---

## 3. Closed-Loop Calibration: Wired vs. Dead-on-Arrival

**PHILOSOPHY.md declares:** Any prediction system must have all four stages (defaults → collect → calibrate → fallback) to count as "closed-loop." Shipping 1–2 stages without 3–4 is incomplete work.

**Actual status:**

| Loop | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Status |
|------|---------|---------|---------|---------|--------|
| **Routing** | ✓ defaults exist | ✓ interspect collects verdicts in events | ○ calibration file schema exists but not auto-triggered | ○ routing-calibration.json read on compose, but file stale | **2.5/4 wired** |
| **Gate thresholds** | ✓ hardcoded phase-gate tiers | ✓ `ic gate signals` extracts TP/FP/TN/FN | ✓ `calibrate-gate-tiers` drains history | ✓ SessionEnd hook configured to run it | **4/4 wired** ✓ |
| **Phase-cost** | ✓ sprint default estimates | ✓ Interstat collects per-phase actuals | ✓ `calibrate-phase-costs` reads history | ✓ SessionEnd hook configured | **4/4 wired** ✓ |
| **Fleet budget** | ✓ baseline estimates | ✓ interstat collects per-agent actuals | ✓ `scan-fleet.sh --enrich-costs` blends registry + delta | ✓ estimates fallback to hardcoded | **4/4 wired** ✓ |
| **Routing override** | ✓ defaults in compose.go | ✓ interspect records outcomes | ○ override proposals draft-stage; not auto-generated | ○ no auto-apply mechanism | **1.5/4 wired** |

**Key finding:** Gate-threshold and phase-cost calibration are _fully wired_. Routing calibration is _partially wired_ — the machinery exists but the lifecycle trigger is missing (routing-calibration.json file must be manually refreshed). Override proposals exist as brainstorms but no auto-generation or application.

**Dead-on-arrival risk:** Hassease (M0 → M1) and Ockham governance (M1 → M2) both have calibration-like components (model selection, authority ratcheting) but no evidence-collection paths wired into runtime yet. These will need stages 2–4 added before they can prove autonomy.

---

## 4. Recent Flux-Review Findings (2026-05-21 synthesis)

The 4-track flux-review identified **10 critical findings**, 11 follow-up beads filed. Three have immediate traction; seven require coordinated work:

**Highest-confidence quick wins:**
1. **Codex Interflux skill mapping stale** (P0, 3/4 track convergence) — `flux-engine` and `flux-research` skill names don't match current `flux-drive` and `flux-review`. Blocks Codex linking. _Fix: normalize manifest, add doctor assertions._
2. **Nested checkout freshness gate missing** (P1, 4/4 convergence) — interlock worktree fix exists upstream but nested repos can lag. Platform doctor/status cannot detect stale nested hooks. _Fix: add freshness check before multi-agent work._

**Core structural changes (P1, all tracks):**
- Interverse inventory has outgrown manual manifest discipline — 60+ plugins, manifest/marketplace drift, unclear lifecycle tiers. _Fix: generated inventory ledger + drift gates._
- Plugin installation too monolithic for Codex/Claude Code — default install assumes "more plugins better." _Fix: define install packs (core, review, docs, research, ops, observability, incubating)._
- Generated review agents (hundreds of fd-* stubs) loading eagerly but rarely used. _Fix: agent registry with active packs, retrieve by domain/frequency._
- Flux-review fan-out cost unpredictable; no read-only mode for remote targets. _Fix: scheduler contract with concurrency/budget/cache/retry; ephemeral read-only mode._

**Deeper work (P1–P2):**
- Hook health budget missing — SessionStart does setup, cache, Beads checks, services, context, state; no latency/mutation budget tracking. _Fix: cached read model + hook health ledger._
- Interflux/Intersynth dependency under-specified (no versioned contract, no fallback mode). _Fix: define synthesis interface inputs/outputs/error behavior._
- Evidence and telemetry boundaries blurry across Interspect/Interstat/Intertrack/Interpulse — no authoritative flight recorder. _Fix: repackage evidence plane boundary; consolidate telemetry._
- No root-level affected-module runner for verification — agents rediscover test commands per module. _Fix: root task graph mapping changed paths to test/lint commands._

**Convergence signal:** All 4 tracks independently surfaced inventory/drift as the single highest-leverage change. The adjacent-platform and obsolete-assumption tracks both called out "Sylveste has outgrown early assumptions that one-size-fits-all."

---

## 5. Velocity and Completeness (Last 60 Days)

- **Git commits:** 1,202 over last 60 days (average ~20/day).
- **Beads closed:** ~155 (from `bd list --status closed` sample).
- **Recent work ratio:** ~80% shipped capability + bug fixes; ~15% research/spikes; ~5% infrastructure.
- **Completed P0s (last 30 days):** Interflux bug cluster (9lp.1–9lp.4, 9lp.30), Ockham Wave 2 wiring (axo3, nzhl), Skaffen compile fixes, generated agent engineering fixes, Signal tool whitelist (nr6x.1).
- **In-progress high-risk items:** Mythos launch readiness (3rod), Hassease daemon (nr6x, in-progress), Autonomy A:L3 wiring, Onboarding bootstrap flow.

**Velocity pattern:** Steady completion on P0 bug clusters and P0 feature work (Ockham, Skaffen). But **4 months old** P0 epics (Auraken→Hermes, Skaffen Go migration, Interflux pre-launch) are still blocked on shared blockers (transport abstraction, Hermes overlay structure). This is a coordination/design problem, not velocity problem.

---

## Where Is the Leverage? (3 Prioritized Workstreams)

### 🎯 **1. Consolidate Plugin Inventory and Drift Gates (BLOCKING)**
**Why this first:** The flux-review identified this as the single highest-leverage change. It unlocks the next three.
- **What:** Generated manifest ledger classifying all 60 plugins by surface type (core workflow, review tool, docs, MCP-only, research, archived). Marketplace reconciliation. Hook loading contract clarification.
- **Why:** Codex, Claude Code, and published docs all inherit stale assumptions about plugin load/scope. Nested checkout freshness also depends on knowing which plugin repos need updating.
- **Timeline:** 1–2 weeks. Bead: `sylveste-b4ch` (P1), `sylveste-i0sa` (P1), `sylveste-wkjf` (P0, quick-win Codex skill fix).
- **Success signal:** Doctor can validate manifest consistency; Codex and Claude Code can use install packs without discovering 60 plugins.

### 🎯 **2. Wire Autonomy A:L3 Routing Calibration (COST STORY)**
**Why this second:** Mythos launch needs to prove cost efficiency. A:L3 is the gate criterion. Two calibration loops already wired (gates, phase-cost); routing is 2.5/4 wired.
- **What:** Finish routing-calibration.json auto-write on session end. Auto-generate override proposals from canary data. Add anomaly flagging for 2x cost drift. Prove 10 consecutive sprints with no manual calibration.
- **Why:** Mythos narrative hinges on "Sylveste proves cost efficiency through closed-loop calibration." Without this, the launch story is speculative.
- **Timeline:** 2–3 weeks. Bead: `sylveste-myyw` (P0), `sylveste-oyrf` (P0).
- **Success signal:** `data/cost-trajectory.csv` updates every 6 hours; Mythos landing page shows live closed-loop chart.

### 🎯 **3. Unblock Parallel P0 Epics via Transport Abstraction (HERMES + CODEX)**
**Why this third:** Hermes overlay, Skaffen Go, and Hassease daemon all block on Signal/gRPC transport. Clearing this unblocks the biggest user-facing launches.
- **What:** Design and ship transport interface abstraction (sylveste-2nfd). Add Signal support to Intercom (benl.6). Enable Codex to dispatch via Hermes personality.
- **Why:** Hermes on Signal and Hassease daemon (cheaper model routing) are both high-leverage Mythos features. Both depend on the same transport work.
- **Timeline:** 3–4 weeks. Bead: `sylveste-2nfd` (P0), `sylveste-benl.6` (P0), `sylveste-heh8` (P0).
- **Success signal:** Auraken running on Signal; Codex can route to Hassease; onboarding flow works end-to-end.

---

## Flags and Observations

**Subsystem-level M0 inventory:** Hassease (execution) is M0 → M1 in-flight. Ockham governance is M1 but the evidence path for M2 transition (authority ratcheting, self-tuning) is not yet observable. Both need stage-2 evidence collection wiring before they can advance.

**Wired-or-it-doesn't failures:** Routing override proposals exist as concept but no runtime path invokes them. They are currently library code without callers — not inventory, not capability yet.

**Nested checkout age problem verified:** The flux-review identified that interlock had a real upstream fix, but the permanent nested `interverse/interlock` checkout was one commit behind and running stale code. This is exactly the failure Sylveste architecture should prevent. The fix exists; the problem is that root-level git status doesn't prove nested repos are current.

**Install pack urgency:** Codex and Claude Code both pay discovery and MCP costs for capabilities they don't use. Defining `core`, `review`, `research` install profiles would reduce default load without losing rare-lens value.

---

## Recommended Q2 Execution Order

1. **Normalize Interflux skill IDs + validate manifests** (1 week, unblocks Codex).
2. **Generate plugin inventory ledger + drift gates** (1–2 weeks, unblocks everything downstream).
3. **Add nested checkout freshness check** (1 week, safety).
4. **Wire routing calibration auto-generation + SessionEnd trigger** (2 weeks, cost story).
5. **Design and ship transport abstraction** (3 weeks, unblocks Hermes + Skaffen + Hassease).
6. **Close Hermes overlay, Signal integration, Hassease M1** (parallel, 3–4 weeks).
7. **Prove 10 consecutive sprints of autonomous calibration** (ongoing, 60+ days).

**Critical path to Mythos:** Steps 1–4 + 5 must land before step 7 proof cycle. Total ~8–10 weeks of focused execution on the three workstreams above. The platform has the pieces; the work is assembly and wiring.
