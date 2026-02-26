# fd-recursive-ring-architecture Review

**Reviewer:** fd-recursive-ring-architecture (distributed systems architect)
**Document:** `/home/mk/projects/Demarch/docs/research/autarch-autonomy-gap-analysis.md`
**Date:** 2026-02-25
**Scope:** Whether Intercore's run/phase/gate/dispatch model can represent the proposed recursive ring architecture, and where the document is honest (or not) about infrastructure gaps.

---

## Executive Summary

The gap analysis correctly identifies that Autarch's UX assumes operator-level interaction where executive-level interaction is needed. However, its central architectural proposal -- recursive rings of autonomous agencies -- is underspecified about how those rings map to Intercore primitives. The document implies that "most of these already exist as primitives" (line 211), but the actual mapping reveals three categories: things that genuinely exist, things that exist but are being stretched beyond their design intent, and things that require new infrastructure the document does not acknowledge.

Verdict: **4 findings, 2 at P1, 1 at P0, 1 at P2.** The recursive ring model has a viable path using Intercore's parent/child run model, but the document understates the coordination gap and entirely omits the failure mode analysis that any distributed system with hierarchical delegation requires.

---

## [P0] Rings Cannot Recurse Without a New Delegation Primitive

**The claim:** "The rings compose recursively" (line 224). A portfolio ring (Bigend) manages concurrent research/design/execution cycles, each of which is a ring, and a meta ring (Interspect) observes all rings.

**What Intercore actually has:** The `runs` table has a `parent_run_id` column. A portfolio run (created via `ic run create --projects=a,b,c`) creates one parent run with empty `project_dir` and N child runs, each with `parent_run_id` pointing back. The gate system enforces `children_at_phase` -- a parent cannot advance past a phase until all children have reached it. Children can also have `upstreams_at_phase` dependency ordering.

**The gap:** This is a single level of nesting. There is no support for a child run having its own children (grandchild runs). The schema permits it -- `parent_run_id` is just a foreign key -- but the portfolio relay (`portfolio/relay.go`) polls child databases by opening read-only SQLite connections to `<project_dir>/.clavain/intercore.db`. A "ring within a ring" would require the inner ring's parent run to also be a child of the outer ring's parent run, and the relay would need to recursively traverse N levels of databases.

Specific problems with recursive rings:

1. **Relay depth.** `portfolio.Relay.Run()` aggregates dispatch counts and phase status across children. It has no recursive descent. An inner ring's portfolio relay would need its own separate relay process, or the outer relay would need to understand that some children are themselves portfolios. Neither is implemented.

2. **Gate evaluation depth.** `CheckChildrenAtPhase` in `gate.go` (line 271-297) checks direct children only. If a child is itself a portfolio, its status is "active" until all of *its* children complete -- but the outer gate has no visibility into why the child is still active or whether it is making progress. The outer ring cannot distinguish "child ring is working" from "child ring is stuck."

3. **Budget composition.** A parent run can set `token_budget` and `budget_enforce`. But if a child run is itself a portfolio with its own budget, there is no budget hierarchy. The inner ring's budget is independent of the outer ring's budget. Token spend in the inner ring does not decrement the outer ring's budget unless someone manually reconciles via `ic cost reconcile`.

4. **ID collision in the state table.** State keys like `agency.gates.<phase>` and `agency.models.<phase>` are scoped by `scope_id` (the run ID). Nested rings would each have their own run IDs, so this part works. But `active-dispatch-count` (used by the relay) is keyed by the portfolio run ID. Multiple relay processes updating state for different portfolio levels could interleave writes if they share the same database.

**Recommendation:** The document should be explicit that recursive rings require extending the portfolio model. The minimum viable extension is: (a) recursive relay that descends into child portfolios, (b) transitive gate checks (`children_at_phase` that understands portfolio children), and (c) budget hierarchy with cascade enforcement. None of these are cosmetic changes. Estimate this as a kernel epic, not an OS-layer configuration change.

---

## [P1] Autonomous Phase Advancement (Gap 6) Conflicts with Intercore's Gate Model

**The claim:** "All phase advancement is kernel-driven. Apps observe phase transitions; they don't control them." (line 103)

**What Intercore actually has:** The `Advance()` function in `machine.go` is a pull-based operation. Something must call `ic run advance <id>` for a phase transition to happen. The kernel does not autonomously advance runs. When `auto_advance` is true on a run, `Advance()` will evaluate gates and advance if they pass -- but it still requires an external caller to initiate the check.

Today, that external caller is Clavain's hooks. The `session-start.sh` hook and the dispatch completion reactor call `ic run advance` when certain conditions are met. This is L2 (React) behavior: events trigger automatic reactions, but the reaction logic lives in the OS layer (bash hooks), not the kernel.

**The gap for autonomous rings:** If a ring is supposed to be "autonomous -- it runs without human intervention in normal operation" (line 218), something must continuously poll or watch the run state and call `ic run advance` when gates pass. The kernel itself has no daemon, no watcher, no event loop. `ic` is a CLI binary that opens the database, does its work, and exits (this is a design principle, not an accident -- see the Demarch vision doc line 63).

Options the document should acknowledge:

1. **Polling relay per ring.** Like `ic portfolio relay` but for phase advancement. The relay already polls child state every 2 seconds. Extending it to also call `ic run advance` on children whose gates pass would make the relay the autonomous driver. But this means every ring needs a running relay process -- rings are no longer lightweight coordination structures but require dedicated sidecar processes.

2. **Event-driven advancement via dispatch completion hooks.** Clavain already does this: when a dispatch completes, the reactor checks if it was the last active agent and calls advance. This works for single-level runs. For recursive rings, the inner ring's completion event must bubble up to the outer ring's advancement logic. The kernel's event bus (`dispatch_events`, `phase_events`) supports cursor-based consumption, but there is no cross-database event subscription. Inner ring events are in the inner ring's database.

3. **Phase actions as cron.** The `phase_actions` table (schema v14) allows registering commands to execute when a phase is entered. This is the closest thing to autonomous advancement -- but actions are triggered by the phase *entry*, not by gate conditions being satisfied asynchronously. They solve "when I enter phase X, do Y" but not "when gate conditions for leaving phase X are met, advance."

**Recommendation:** The document should be honest that autonomous phase advancement requires either (a) a persistent relay/watcher process per ring, or (b) a kernel-level event subscription + auto-advance daemon. The current architecture is event-driven at the OS layer, not the kernel layer. This is a deliberate design choice (mechanism vs policy), but it means "autonomous rings" need an OS-layer process management solution that does not currently exist.

---

## [P1] Interspect's Feedback Loop into Ring Composition is Structurally Vague

**The claim:** "A meta ring (Interspect) observes all rings and proposes improvements" (line 229) and "Self-improving -- Interspect profiles each ring and proposes optimizations" (line 222).

**What Interspect actually does (per the vision doc):** Interspect collects evidence events into `interspect_events` (schema v7). It reads the kernel's event stream, correlates outcomes with human signals (dismissals, overrides, corrections), and proposes overlays. Today, Phase 1 (evidence collection) is shipped. Phase 2 (overlays) is designed but not implemented.

**The gap:** The Interspect vision describes per-agent profiling: "fd-safety produces no actionable findings on this Go CLI project? Exclude it from the review fleet." This is agent-level optimization. The gap analysis proposes ring-level optimization: "Interspect profiles each ring and proposes optimizations." These are different granularities.

Ring-level optimization would require Interspect to answer questions like:
- "The design ring consistently takes 3x longer than the execution ring. Should we allocate more budget to design?"
- "The research ring produces findings that the design ring never uses. Should we reduce research scope?"
- "Inner ring X failed on its last 3 runs. Should the outer ring stop delegating to it?"

None of these are agent-level signals. They are ring-level signals that require:
1. Identifying which events belong to which ring (the `run_id` column in `interspect_events` helps, but only if ring = run, which the document assumes without stating).
2. Comparing ring-to-ring metrics (cross-run analysis, which Interspect's Phase 1 schema does not index for).
3. Proposing ring composition changes (not just overlay files on agent prompts, but changes to which rings exist, their phase chains, and their delegation relationships).

The gap analysis treats Interspect as a ring-aware optimizer without acknowledging that Interspect was designed as an agent-aware optimizer. Bridging this gap is tractable (run-scoped metrics are derivable from dispatch-scoped metrics), but it is engineering work the document should call out.

**Recommendation:** Add a section explicitly mapping Interspect signals to ring-level decisions. Identify which existing signals (gate pass rate, sprint completion rate, finding density) can be aggregated to ring scope versus which require new ring-level evidence types.

---

## [P2] Ring Failure Modes Are Entirely Absent

**The claim:** Each ring is "budget-constrained" and "escalation-capable" (lines 219-220).

**What happens when an inner ring fails:** The gap analysis does not address this at all. This is a critical omission for any recursive delegation architecture.

Intercore's run model has three terminal statuses: `completed`, `cancelled`, `failed`. When a child run fails, the portfolio gate `CheckChildrenAtPhase` checks this:

```go
if child.Status == StatusCompleted || child.Status == StatusCancelled {
    continue // completed/cancelled children don't block
}
```

Note: `StatusFailed` is NOT in this continue clause. A failed child blocks the portfolio gate forever. The comment in the code (line 278) confirms this is intentional: "Failed children DO block -- portfolio should not advance past a failed child."

This means:
1. **If an inner ring fails, the outer ring is permanently blocked** until someone intervenes (cancels the child or resolves the failure).
2. **There is no auto-remediation path in the kernel.** The kernel blocks. The OS layer would need to detect the block, decide what to do (retry, skip, escalate), and execute the decision. This is exactly the L3 (Auto-remediate) behavior the document says Demarch is "pushing toward" but has not shipped.
3. **Budget exhaustion in an inner ring is a failure mode.** If `budget_enforce` is true and the inner ring exceeds its token budget, `CheckBudgetNotExceeded` fails. The inner ring is stuck at a gate it can never pass. The outer ring sees the child as "active but not advancing" with no diagnostic information about why.
4. **Timeout/liveness.** There is no concept of "this ring has been stuck for too long." The kernel tracks `created_at` and `updated_at` on runs, but there is no stale-run detection or automatic cancellation. A ring that silently stalls (no dispatches, no failures, just... nothing happening) is invisible to the outer ring.

**Recommendation:** The document's "Architectural Requirements" section (line 203) should include a ring failure protocol with at least these cases: inner ring failure, inner ring budget exhaustion, inner ring stall/timeout, and cascading failure (inner ring failure causes outer ring budget overrun). For each case, specify whether the kernel handles it (mechanism) or the OS handles it (policy), and what new primitives are needed.

---

## Findings That Are Not Findings

The following areas were reviewed and found to be either correctly represented in the document or outside the scope of this review:

**Phase chain flexibility.** The document proposes that different rings have different phase chains. Intercore supports this via `ic run create --phases='["research","score","report"]'`. Custom phase chains are validated (`ParsePhaseChain` requires >= 2 phases, no duplicates, alphanumeric names). Gate rules can be customized per-run via `--gates` or `--gates-file`. This is a genuine strength -- rings can have heterogeneous lifecycles without kernel changes.

**Budget constraints on rings.** Token budgets (`token_budget`, `budget_warn_pct`, `budget_enforce`) exist and work at the run level. The document correctly identifies this as an existing primitive (line 219).

**Observable ring activity.** The event bus (`dispatch_events`, `phase_events`) supports cursor-based consumption with consumer names. An outer ring can subscribe to an inner ring's events via `ic events tail <run_id> --consumer=outer-ring`. The document's claim that rings are "observable" (line 221) is supportable with existing primitives, for single-level rings at least.

**Agency specs per ring.** The `ic agency load` command stores agent configurations, model overrides, gate rules, and capabilities in the state table, scoped by run ID. Each ring-as-run could have its own agency spec, providing the "each ring is configured independently" property the document implies.

---

## Summary of Recommendations

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| R1 | P0 | Recursive rings require kernel extensions to parent/child model | Acknowledge as kernel epic; specify relay depth, transitive gates, budget hierarchy |
| R2 | P1 | Autonomous advancement requires persistent process per ring | Specify whether relay, daemon, or event-subscription model; each has different ops cost |
| R3 | P1 | Interspect is agent-scoped, not ring-scoped | Map existing signals to ring scope; identify new ring-level evidence types needed |
| R4 | P2 | No failure mode analysis for ring architecture | Add failure protocol: inner ring failure, budget exhaustion, stall detection, cascade |

The recursive ring model is architecturally coherent and maps more naturally to Intercore's primitives than the document gives itself credit for (custom phase chains, per-run gate rules, agency specs, event bus). But the document's claim that "most of these already exist as primitives" undersells the infrastructure gap on recursion, autonomous advancement, and failure handling. The gap between "portfolio runs with custom phases" and "recursive autonomous rings with failure recovery" is a meaningful engineering effort that the document should scope honestly.
