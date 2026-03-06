# Phase 5 (Round 2): Sublation — Two Consumers, One Codebase

## The Synthesis

The contradiction dissolves when you stop asking "how should plugins be packaged?" and start asking **"why must the developer's organizational model be the agent's operational model?"**

Both monks assumed that the physical structure of the code (directories, manifests, namespaces) must also be how the agent encounters the system. Monk A said: keep the uniform structure, let infrastructure handle discovery. Monk B said: restructure by workflow because the agent thinks in tasks. Both were fighting over who gets to own the *one* organizational model — developer or agent.

But databases solved this problem decades ago. The table structure serves the data modeler. Views serve the consumer. They are independently optimized. The same data, different access patterns.

### The Two-Layer Model

**Layer 1 — Developer packaging (uniform directories):** Keep the monorepo's uniform structure. 49 directories, each with CLAUDE.md, AGENTS.md, src/, tests/. This serves the developer's conceptual model and enables the infrastructure Monk A correctly identified (Tool Search, lazy loading, progressive disclosure all require homogeneous artifacts). Boundary changes remain cheap — mkdir and mv. The developer never sees or manages workflow bundles.

**Layer 2 — Agent composition (dynamic tool surfaces):** The agent never sees "plugins." The agent sees **tool surfaces** composed dynamically per-task from an index built on the uniform structure. When the agent needs coordination, Tool Search surfaces the relevant tools from interlock + intermux + interpath — but presents them as a single coherent tool surface with unified documentation, not three separate plugin contexts.

The critical innovation is the **composition layer** between packaging and agent: a system that reads the uniform plugin structure, indexes all tools/skills/hooks, and serves them to agents as task-relevant bundles without the agent needing to know or care about plugin boundaries.

### Why This Is Different From "Just Build Better Tool Search"

Monk A's position was: Tool Search solves the problem. This synthesis says: Tool Search solves the *token* problem but not the *selection* problem. The 18-point accuracy gap (74% vs 92%) exists because the agent receives tool candidates from *different namespaces* and must reason about which namespace owns which step.

The composition layer addresses selection cost by presenting tools from multiple plugins as a **unified context** — a single document explaining "here are the tools for coordination, here is how they work together" — rather than three separate contexts the agent must mentally merge. This is the difference between a database view (pre-joined, consumer-ready) and a SQL query against raw tables (consumer does the joins).

### Why This Is Different From "Reorganize By Workflow"

Monk B's position was: package by workflow. This synthesis says: workflow bundles are as brittle as domain boundaries because agent workflows are emergent. You cannot predict every composition pattern.

Dynamic composition solves this because the bundles are not pre-defined packages — they are generated at query time. When a new workflow emerges (e.g., interlock + interflux for locked code review), the composition layer generates a new tool surface from the existing uniform structure. No directory moves. No package restructuring. No architect decision required. The uniform structure is the *substrate* from which any workflow view can be generated.

### What This Requires

1. **Tool Search evolution**: From "find relevant tools" to "compose coherent tool surfaces." The index already exists; the composition logic is the engineering target. This is the 18-point accuracy gap made concrete as an engineering specification.

2. **Workflow context documents**: Pre-composed contexts for common workflows (coordination, research, code review) that present tools from multiple plugins as a unified surface. These are *views*, not *packages* — they reference the underlying plugins but don't move or restructure code.

3. **Agent-side progressive disclosure**: The agent loads a workflow context (5-7 tools, unified documentation), not 49 plugin manifests. If it needs tools outside the initial surface, it queries for more — the same way an IDE workspace starts with a project scope and expands on demand.

### What This Preserves

- **From Round 2 Monk A**: Uniform structure stays. No tiers, no classification, no governance overhead. Boundaries remain cheap to create and destroy. Infrastructure is the mechanism.
- **From Round 2 Monk B**: The agent is a first-class consumer whose cognitive model is respected. Selection cost is addressed, not just token cost. The "workflow is the unit" insight is preserved — but as a dynamic composition, not a static package.
- **From Round 1 Monk A**: Sovereignty of each plugin is preserved. No consolidation. The monorepo's uniform structure IS the cheap-sovereignty infrastructure.
- **From Round 1 Monk B**: The agent doesn't pay for 49 conceptual separations. The packaging overhead is absorbed by the composition layer.

## Abduction Test

Starting from "the developer's packaging and the agent's tool surface should be independently optimized, connected by a composition layer":

- **Monk A is predictable**: "Infrastructure solves everything" — can't see that infrastructure must also address the *composition* problem, not just discovery and loading.
- **Monk B is predictable**: "Restructure for the agent" — can't see that restructuring is unnecessary when composition can be dynamic.

Both are partial views. Monk A correctly identifies the substrate (uniform structure). Monk B correctly identifies the consumer (agent workflows). Neither can see that the substrate and the consumer need a *mediation layer* rather than one imposing its model on the other. **Passes.**

Abduction type: **(c) creative** — the two-layer model with dynamic composition is a genuinely new operational principle, not a recombination of the monks' positions.

## Validation Predictions

- **Monk A**: "This preserves my core insight — uniform structure, no classification, infrastructure as mechanism. The composition layer is just the next piece of infrastructure I was always arguing for. I endorse this."
- **Monk B**: "This takes seriously my claim that the agent is the primary consumer and that selection cost matters. The workflow context documents are essentially what I was asking for — tools presented as coherent task surfaces. But I'm suspicious that 'dynamic composition' is hand-waving for 'we'll figure it out later.'"

## New Contradictions

1. **The composition layer is itself a classification system.** Workflow context documents must be authored — who decides which tools belong in the "coordination" context? This may recreate the governance overhead Monk A warned about, just at the view layer instead of the packaging layer.
2. **Dynamic composition quality depends on Tool Search quality.** If Tool Search can't compose coherent surfaces (currently 74% accuracy), the two-layer model degrades to "the agent still picks from ambiguous candidates" — Monk B's original complaint.
3. **The 18-point accuracy gap may be fundamental.** If LLM tool selection has inherent limits at scale regardless of presentation, neither packaging nor composition can close it. The correct response might be: accept 74% and design for graceful degradation.
4. **Views can diverge from storage.** Workflow contexts that reference multiple plugins can become stale when plugins evolve. Who maintains the views? (Same as database view maintenance.)

## Existence Proof: Interchart Domain Overlays

This synthesis is not purely theoretical. Interchart already implements the two-layer model for *visualization*:

- **Layer 1 (uniform substrate):** interchart scans all plugins identically — the uniform CLAUDE.md/AGENTS.md structure makes them scannable.
- **Layer 2 (dynamic views):** Plugins are grouped into 11 domain overlays via pattern matching on descriptions + forced curation groups. A plugin can belong to multiple overlapping domains (e.g., interstat is in both `analytics-quality-stack` and `analytics-observability`).
- **Views, not packages:** Overlays don't restructure code — they're a visualization layer over the existing directory structure.

The synthesis proposes applying interchart's architecture to the *agent's tool loading surface*: same uniform substrate, same dynamic grouping (via Tool Search + workflow contexts), same overlapping membership — but the output is coherent tool surfaces with unified documentation instead of SVG convex hulls.

Interchart's hybrid governance model (pattern inference + forced curation groups) also addresses contradiction #1: the composition layer doesn't need a full classification system, just patterns that catch most cases with manual overrides for edge cases. This is the same `OVERLAP_DOMAIN_RULES` + `FORCED_OVERLAP_GROUPS` pattern, applied to tool routing.

## Model Update

- **Before (Round 1):** Plugins should have packaging strength proportional to domain independence (stranger test).
- **After (Round 2):** Developer packaging and agent tool surfaces are independent concerns. Keep uniform directory structure for the developer. Build a composition layer that presents dynamically generated, workflow-coherent tool surfaces to the agent. The 18-point accuracy gap (74% → 92%) is the engineering target for this composition layer.
- **Because:** Round 1 assumed one organizational model must serve both consumers. Round 2 Monk A showed uniform structure serves the developer; Round 2 Monk B showed the agent needs workflow-coherent surfaces. The insight that these can be decoupled — like database tables and views — dissolves the competition for "whose model wins."
