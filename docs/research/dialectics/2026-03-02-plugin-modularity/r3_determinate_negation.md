# Phase 4 (Round 3): Determinate Negation

## 4.0 Internal Tensions

**Monk A undermines itself with the foreign key analogy.** Foreign keys work because the database enforces referential integrity — you *cannot* insert an order with a nonexistent customer_id. The enforcement mechanism is the schema itself. Tool composition has no such enforcement. An agent CAN call `reserve_files` without first calling `resolve`. The foreign key analogy works for routing (pointing at related tools) but fails for the sequencing problem, which is exactly where the accuracy gap lives. Monk A acknowledges the sequencing objection ("This looks like a comprehension failure") and answers with "each tool's own docs handle use time." But the sequencing problem is *between* tools — neither tool's own docs specify the cross-tool ordering contract.

**Monk B undermines itself with the litmus test.** "If you can write composition docs in one sentence, the plugins are independent. If you need pages, they're coupled." But this proves too much. Kubernetes pod, service, and ingress are separate API resources requiring pages of composition documentation (sequencing, state coherence, error handling). Nobody argues they should be one resource. The depth of composition documentation measures the complexity of the *interface*, not the incorrectness of the *boundary*. Complex interfaces between genuinely independent components are a real phenomenon — Monk B collapses them into a single category with incorrectly-drawn boundaries.

## 4.1 Surface Contradiction

Monk A: The composition paradox is a false dilemma. Shallow metadata closes the gap. Selection is routing, not comprehension.
Monk B: The paradox is real and fatal. Deep docs are required, and that documentation IS the consolidation specification.

## 4.2 Shared Assumptions

1. **Both assume the accuracy gap has a single cause.** Monk A says it's discovery. Monk B says it's comprehension/sequencing. Neither considers that the gap might decompose into BOTH — some portion discovery (closeable with shallow metadata) and some portion sequencing (requiring deeper docs or consolidation). The gap may be heterogeneous.

2. **Both assume the 18-point gap is about the composition layer.** But the gap (74% → 92%) compares Tool Search with 50+ tools vs 5-7 native tools. It measures the cost of SCALE, not the cost of BAD BOUNDARIES. Even perfectly drawn boundaries at scale would show degradation. The gap is partially inherent to large tool surfaces.

3. **Both treat all plugin pairs as having the same composition depth.** In reality, composition depth is a spectrum: interflux+intermonk need zero docs, interlock+interpath need moderate docs, some pairs might need pages. The ecosystem contains the full spectrum.

4. **Neither considers that the agent can LEARN sequencing from experience.** In-context learning, few-shot examples, and tool call histories can teach sequencing without explicit composition documentation. The accuracy gap may close through usage patterns, not docs.

## 4.3 Determinate Negation

**Monk A fails because** the routing/comprehension distinction is clean in theory but messy in practice. The agent calling `reserve_files` before `resolve` is not a discovery failure (found both tools) and not a per-tool comprehension failure (understood each tool's docs). It is a *cross-tool sequencing* failure that falls in the gap between Monk A's two categories. Shallow metadata says "these tools are related" but not "call this one first." Once you add sequencing hints, you cross from routing into specification.

**Monk B fails because** the isomorphism between composition docs and consolidation specs is real for *some* plugin pairs but not all. The claim that "depth of docs = degree of coupling" ignores that some cross-boundary complexity reflects the *domain's* complexity, not the *boundary's* incorrectness. Multi-agent coordination is inherently complex regardless of packaging. Consolidating interlock + intermux + interpath would still require internal documentation of the same sequencing contracts. The docs don't go away — they change from "inter-module" to "intra-module." The coupling is in the domain, not in the packaging.

The failures point the same direction: **the real question is not "how deep should composition docs be?" but "what kind of cross-tool knowledge does the agent actually lack?" — and the answer varies per plugin cluster.**

## 4.4 The Hidden Question

**Is the accuracy gap caused by missing routing metadata, missing sequencing knowledge, or something else — and does the answer vary per plugin cluster?**

## 4.5 Boydian Decomposition

### Atomic Components
- The accuracy gap (74% → 92%) has multiple causes, not one
- Some gap is discovery/routing (tool not surfaced) — closeable with shallow metadata
- Some gap is sequencing (wrong call order) — requires cross-tool knowledge
- Some gap is inherent to scale — irreducible regardless of composition
- Composition documentation depth varies per plugin pair (spectrum, not binary)
- Deep composition docs and module internal docs are structurally similar but not proof of incorrect boundaries
- Domain complexity and boundary complexity are conflated by both monks
- Agent in-context learning can acquire sequencing from examples, not just docs
- The incidental/essential composition distinction (Monk B) is sharp and useful

### Surprising Cross-Connections
- "Selection vs use" (Monk A) + "incidental vs essential composition" (Monk B) = **a 2x2 matrix**: some tools need only routing (incidental + selection), some need sequencing hints (essential + selection), some need deep docs (essential + use). Composition depth should vary per tool relationship.
- "Doc depth as litmus test" (Monk B) + "it's just routing" (Monk A) = **doc depth as an empirical coupling metric with thresholds**: 1 sentence = independent, 1 paragraph = related, 1 page = coupled. Different actions at each level.
- In-context learning + co-occurrence signals = **the composition layer can be LEARNED from agent usage traces**, not just authored. Successful sessions become training data for routing and sequencing.

### Adjacent Domain Material
- **Compiler optimization passes**: Independent implementations with strict sequencing constraints. Compilers don't merge all passes; they specify pass ordering as metadata. Routing with sequencing — exactly the middle ground.
- **K8s operators**: CRDs compose via ownership references (shallow). But operators requiring choreographed sequencing typically get combined into a higher-level operator. Supports Monk B for essential composition, Monk A for incidental.

## 4.6 Sublation Criteria

- **Preserve from A:** The gap is partially routing/discovery, and shallow metadata closes that portion. Selection vs use is real. Co-occurrence and collaborative filtering are powerful shallow signals. Not all plugin pairs need the same depth.
- **Preserve from B:** Incidental/essential composition distinction is sharp and useful. Essential composition (sequencing, shared state, error propagation) is structurally similar to module specification. Doc depth as coupling metric is a genuinely new operational tool.
- **Dissolve:** The assumption that the gap has a single cause and therefore a single solution. The assumption that all plugin pairs need the same composition treatment.
- **Answer:** The composition layer should have heterogeneous depth per plugin pair. Doc depth IS the measurement mechanism that Round 1 couldn't find for determining coupling. Some plugins need only routing hints; others need composition docs deep enough that consolidation becomes the honest response.
