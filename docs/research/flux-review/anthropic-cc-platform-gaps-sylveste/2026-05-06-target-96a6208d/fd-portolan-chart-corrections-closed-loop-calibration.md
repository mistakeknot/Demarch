<!-- flux-run-uuid: 3507b048-2a14-484a-ad19-b1066bab6c97 -->
<!-- dispatch-mode: orchestrator-embodied (Task tool unavailable in nested skill context) -->

### Findings Index
- P0 | P-1 | "Design philosophy / OODARC, not OODA" | The Reflect-Compound back-half is not just missing — it has no publication cadence
- P1 | P-2 | "Initial findings #4 (cost/context/token observability)" | Per-instance instrumentation without fleet-wide corrections feed
- P1 | P-3 | "Tier 2 (routing calibration with closed loop)" | Authority weights without dated decay
- P1 | P-4 | "Initial findings #1 (durable memory) / #7 (AGENTS.md)" | Memory graduation conflates observed and inferred
- P1 | P-5 | "Initial findings #2 (synthesis)" | Rutter equivalent missing — no narrative voyage log feeds back to chart
- P2 | P-6 | "Anti-patterns / cross-domain isomorphisms" | No hazard-marker primitive — known-bad regions cannot be marked stably across the ecosystem
- P1 | P-7 | "Strategic angle / structural reframing" | The 8th primitive: the corrections feed itself, with cadence and decay, distinct from observability

Verdict: needs-changes

---

## Summary

The prior pass identifies "cost/context/token observability" as a deprecation target and "routing calibration with closed loop on outcomes" as a tier-2 target. From the portolan / Notice-to-Mariners lens, these are the *instrumentation* half of the loop. The platform has no *publication cadence* — no corrections feed that takes observed deviations and republishes calibrated charts to every captain in the fleet on a regular cycle. PHILOSOPHY.md mandates closed-loop calibration but the review keeps stopping at "observability." Observability without a corrections cadence is a chart room with no printer; every captain keeps their own corrections and the fleet silently drifts. The 8th primitive the prior pass missed is the **corrections feed** — distinct from observability, distinct from memory, distinct from routing.

## Issues Found

### 1. P0 | Reflect-Compound has no publication cadence

PHILOSOPHY.md names OODARC: Observe → Orient → Decide → Act → Reflect → Compound. The review correctly identifies that Anthropic ships the Act half. But it understates what's missing in the Reflect-Compound half. The portolan lens shows there are *two* missing pieces:

1. The narrative observation log (rutter / routier) — the voyage's account of where the chart was wrong. cass session export and reflect docs are pieces of this.
2. The published correction (Notice to Mariners) — the dated, authoritative, distributed update to the chart that every captain consumes before the next voyage.

Sylveste has #1 (in fragments). It does not have #2. There is no platform mechanism that says "every Friday, the corrections from this week's reflects are aggregated, vetted, and published as updates to the routing model / trust scores / gate thresholds, with a dated chart issue number."

Failure scenario: A reflect entry on 2026-04-21 finds that the priming-effect overlay degrades fd-correctness reviews. The fix is recorded in a doc. Six months later, a similar review primes the same way — the corrections never reached the helm. The chain "observed → published → next-voyage-uses-it" was broken at "published."

Fix: Native primitive — call it `chart-issue` — that takes corrections from the observability layer and publishes dated updates that propagate to every active session at the next opportunity. Cadence: weekly default, configurable. Issue number is monotonic and immutable. Every routing decision, every gate threshold, every memory authority weight cites the chart-issue it was computed from.

This is the 8th primitive. It is not observability (#4). It is not memory (#1). It is the cadence layer that makes observation actionable across the fleet.

### 2. P1 | Per-instance instrumentation without fleet-wide corrections feed

The prior pass's #4 deprecates interstat, intercept, interpulse, tool-time. All four instrument *per-session*. None publishes a fleet correction. interstat reports last-week token efficiency; it does not say "the platform's default cost ceiling has been adjusted from $3.10 to $2.93 because last week's data contradicted the prior estimate" with a chart-issue number, an effective-date, and an automatic propagation.

Failure scenario: A user reads interstat and sees their cost is high. They adjust their behavior. The platform default for the next user is unchanged. The platform learns nothing across users. Each captain corrects their own chart and the fleet's master chart stays wrong.

Fix: Native primitive must include both per-session instrumentation *and* periodic platform-default recomputation with published corrections. Treat the platform's defaults as a chart that is published, not a constant that is hardcoded.

### 3. P1 | Authority weights without dated decay

intertrust scores, intermem auto-memory facts, and interknow patterns all carry confidence/authority weights. Portolan tradition required dated decay: a coastline observed in 1620 has lower authority next decade than one observed last month. Without decay, the chart silently rots.

The review describes durable memory as "graduates stable auto-memory facts to AGENTS.md/CLAUDE.md." There is no decay rule. Once graduated, a fact stays at full authority indefinitely.

Failure scenario: An auto-memory fact ("project uses TypeScript 5.3 strict mode") graduates in 2026. By 2028 the project has migrated to TypeScript 6.1 with looser settings. The fact is still in CLAUDE.md at full authority because nothing decays it. Agents follow it. Quality drops silently.

Fix: Every authority-bearing artifact carries `as_observed_date` and a `decay_rule` (or `revalidation_required_after`). The native memory primitive must enforce dated decay or the corrections cadence cannot operate.

This is also a P1 because it interacts with #1 above: a corrections feed that does not decay old corrections republishes outdated guidance forever.

### 4. P1 | Observed and inferred conflated in memory graduation

Portolan tradition rigorously separated solid-line (observed by named captain on dated voyage) from dotted-line (inferred from prevailing currents). When a chart copyist transcribed dotted as solid, the chain broke silently — the next captain navigated as if the inferred line were observed.

The review's #1 (memory graduation) and #7 (managed AGENTS.md) do not specify how observed and inferred are distinguished:
- A hook-event-derived fact ("fd-safety found 3 issues") is observed.
- An agent-synthesized inference ("the project does not use TLS in dev") is inferred.

If both graduate to AGENTS.md without source-class survival, downstream agents treat both as observed.

Failure scenario: An agent infers from an agent-synthesized summary that "this project does not need authentication tests." That inference graduates. The next agent reads it as a confirmed observation. Tests are skipped. A vulnerability ships.

Fix: Every persisted authority-bearing artifact carries `source_class: observed | inferred | synthesized`. Graduation rules differ by source class — observed graduates faster, inferred requires corroboration. AGENTS.md surfaces the class explicitly per fact.

### 5. P1 | Rutter equivalent missing

The portolan rutter was the narrative voyage log: "rounded Cape St. Vincent on the 12th day, current set us NE at 3 knots stronger than charted, observed shoals at lat X long Y." The chart workshop read rutters and updated charts.

Sylveste has /reflect, cass exports, and reflect-from-bead docs. These are partial rutters. They are not consumed by a chart workshop because there is no chart workshop primitive. /reflect creates a doc; nothing reads the doc to produce a chart-issue.

Failure scenario: Reflect docs accumulate. interlearn indexes them. Search retrieves them on demand. The platform does not actively consume them on a cadence to update routing/gate/memory defaults. The rutter is filed in the cabin and never reaches the chart workshop.

Fix: Native primitive that consumes rutter equivalents (reflects, post-mortems, after-action reviews) on cadence and produces chart-issue corrections. This is the natural pair to #1 — without rutter consumption, the corrections feed has no input.

### 6. P2 | No hazard-marker primitive

Portolan charts marked rocks, shoals, and unreliable coasts with stable symbols whose meaning never changed across centuries. Once a hazard was charted, it propagated to every subsequent chart without rediscovery.

The review does not address: when a known-bad pattern is discovered (a security anti-pattern, a routing failure mode, a brittle test that always flakes), how does it get marked across the ecosystem stably? interspect proposes routing exclusions. interknow holds patterns. intertest holds test patterns. None has the stability-across-decades property of a portolan hazard symbol.

Failure scenario: A pattern is identified in 2026 ("never call X with Y argument — silent corruption"). It enters interknow. Two years later, after a refactor, interknow's index has churned and the pattern is buried. An agent calls X with Y. Silent corruption returns.

Fix: Hazard-marker primitive — a stable, ecosystem-wide registry of known-bad patterns with permanent IDs, that every relevant tool consults. Cf. Notice to Mariners' permanent corrections (vs temporary ones). Permanent corrections never expire.

### 7. P1 | The 8th primitive: corrections feed with cadence and decay

The review explicitly asks for primitives the prior pass missed. The portolan lens names one: a **corrections feed** that has:
- Defined cadence (weekly, monthly)
- Monotonic immutable issue numbers
- Source-class survival (observed vs inferred)
- Dated decay on every authority-bearing fact
- Mandatory consumption — every active session pulls the latest issue at session start
- Hazard-marker permanence (some corrections never expire)

This is *not* observability (per-session instrumentation), *not* memory (durable storage), *not* routing (decision logic). It is the cadence layer that connects them — the thing that turns "observe + remember + decide" into a closed loop.

Failure scenario: All seven prior-pass primitives ship. Each works in isolation. Across them, defaults drift, decay never applies, corrections accumulate in reflect docs that nothing consumes. Five years in, the platform's defaults are based on 2026 data and the platform has no mechanism to know.

This is the structural reframing for the closed-loop half of OODARC: cadence is a primitive, not an implementation detail. The prior pass treats cadence as something each plugin handles separately. From the portolan lens, cadence is a single platform primitive whose absence makes the loop never close.

## Improvements

1. Add an 8th primitive to the deprecation roadmap: corrections feed with cadence. Specify cadence default (weekly), issue numbering, decay rules, source-class survival.
2. Treat platform defaults (cost ceilings, routing thresholds, gate verdicts) as published charts rather than hardcoded constants. Each default cites its chart-issue.
3. Mandate `as_observed_date` and `decay_rule` on every authority-bearing artifact. Untyped authority weights are P1 anti-pattern.
4. Mandate `source_class: observed | inferred | synthesized` on every persisted fact. Conflation is a chain break (cf. Museum Registrar finding M-3).
5. Define the rutter consumer — what reads /reflect docs and produces chart-issue updates? Currently nothing does.
6. Add hazard-marker registry as a permanent-corrections layer separate from interknow's churning patterns.

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 7 (P0: 1, P1: 5, P2: 1)
SUMMARY: The missing 8th primitive is a corrections feed with cadence — distinct from observability, memory, and routing. Without it, OODARC's Reflect-Compound back-half stays open per-session and the platform defaults drift silently. Authority weights need dated decay and observed-vs-inferred source classes.
---

<!-- flux-drive:complete -->
