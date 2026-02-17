# Decision Quality Review: Intermem Architecture Options

**Document Reviewed:** `/tmp/intermem-brainstorm-context.md`
**Review Date:** 2026-02-16
**Reviewer:** fd-decision (Flux-drive Decision Quality Reviewer)
**MCP Status:** Interlens MCP unavailable — review uses fallback lens subset (12/288 lenses)

---

## Executive Summary

This brainstorm document does a strong job of framing the decision space and enumerating alternatives. However, it exhibits **moderate analysis paralysis** (P2), **missing reversibility analysis** (P1), and **implicit decision criteria** (P2) that could derail execution. The 13-system landscape research is thorough but risks becoming a **local optimization trap** — optimizing for feature coverage rather than ecosystem fit.

**Key Strengths:**
- Clear problem statement with 4 distinct architectural options
- Comprehensive landscape research (13 external systems analyzed)
- Explicit enumeration of 7 capability gaps
- Strong grounding in existing Interverse infrastructure (5 memory systems documented)

**Critical Gaps:**
- No explicit decision criteria or weighting (which capabilities matter most?)
- No reversibility analysis (which options can be undone if wrong?)
- No starter option or incremental path (MVP is missing)
- Landscape research findings don't map cleanly to decision criteria
- Multi-agent memory coordination is mentioned but underexplored given Interverse's existing interlock/intermute infrastructure

---

## Findings by Severity

### P0 Findings

None identified. No immediate, concrete risk requiring urgent mitigation.

---

### P1 Findings (Blind Spots — Entire Analytical Frame Missing)

#### P1-1: Missing Reversibility Analysis

**Location:** Option enumeration (lines 11-33)
**Lens Applied:** N-ply Thinking

**Issue:**
The document presents 4 options with pros/cons but does not classify them by **reversibility** — which decisions can be undone, and at what cost? This is critical because:

- **Option 4 (Replace Everything)** is explicitly flagged as "high risk, long timeline" but there's no analysis of the **exit cost** if it fails. Can you roll back to the old system? What happens to memories written during migration?
- **Option 2 (Consolidation Engine)** mentions "risk of divergence" but doesn't quantify the **temporal window** where this matters. How long before divergence becomes irreversible?
- **Option 1 (Federation Layer)** is presented as "lightweight, additive" but there's no analysis of whether adding federation creates **lock-in**. If the federation abstraction is leaky, can you remove it without breaking every consumer?

**What's missing:**
A **reversibility matrix** mapping each option to:
1. **One-way door threshold** — at what point does the decision become irreversible?
2. **Rollback cost** — if this option fails after 3 months, what's the effort to undo it?
3. **Escape hatches** — what pre-committed criteria would trigger an option change?

**Recommendation:**
Add a section: **"Reversibility & Decision Gates"**. For each option, specify:
- "This becomes irreversible when: [trigger]"
- "To roll back, we would need to: [steps]"
- "We'll abandon this option if: [signpost criteria]"

Without this, the team risks **commitment escalation** — continuing with Option 2 or 4 even after clear failure signals, because the sunk cost is too high.

**Relevant Question:**
The document asks: "What are the biggest risks and how to mitigate them?" (line 114) but doesn't answer this with decision-level mitigations (signposts, rollback plans). It's focused on implementation risks, not decision process risks.

---

#### P1-2: No Starter Option or Incremental Path

**Location:** Option enumeration (lines 11-33), Questions for Analysis (line 113)
**Lens Applied:** The Starter Option, Explore vs. Exploit

**Issue:**
The document asks "What's the minimum viable version that delivers the most value?" (line 113) but none of the 4 options are framed as MVPs. Each option is presented as a **complete architectural commitment**:

- Option 1: "memory router with semantic search across heterogeneous backends" — this is not a starter, it's a full federation layer
- Option 2: "single canonical store, dedupe/score/decay" — this is not a starter, it's a full consolidation engine
- Option 3: "metadata overlay with validation/decay/provenance" — this is not a starter, it's a full smart layer
- Option 4: "replace everything" — this is explicitly not a starter

**What's missing:**
A **starter option** that delivers value in week 1 without committing to a final architecture. For example:
- "Read-only federation MCP tool that queries auto-memory + compound docs (no write, no embeddings, no decay). Proves the UX before building infrastructure."
- "Add a single hook to auto-memory that logs retrieval frequency. Gather data on what memories are actually used before designing decay/validation."

**Why this matters:**
The document is stuck in **explore mode** (13 external systems researched, 7 gaps identified, 4 options enumerated) but hasn't shifted to **exploit mode** (pick the smallest reversible commitment and learn from it). This is classic **analysis paralysis**.

**Recommendation:**
Add **Option 0: Instrumentation & Learning**. Before building any architecture, add lightweight instrumentation to existing memory systems:
- Track what memories are retrieved and when
- Track what memories are ignored or outdated
- Track retrieval latency and token costs

This shifts the decision from "which architecture?" to "what problem is worth solving first?" — grounding the choice in **empirical evidence** rather than landscape research.

**Relevant Lens:**
**Explore vs. Exploit** — the document is deep in exploration (13 systems analyzed) but hasn't defined the **transition criteria** to exploitation (when do we stop researching and start building?). Without a starter option, the team risks indefinite exploration.

---

### P2 Findings (Missed Lens — Frame Mentioned but Underexplored)

#### P2-1: Implicit Decision Criteria

**Location:** Questions for Analysis (lines 108-115), Landscape Research (lines 69-96)
**Lens Applied:** Theory of Change

**Issue:**
The document asks "Which option (1-4) best fits the Interverse ecosystem given its existing infrastructure?" (line 110) but doesn't specify **the criteria for "best fits."** The 7 gaps identified in the landscape research (lines 89-96) seem like they should inform the decision, but there's no explicit mapping:

- Is **cross-project knowledge sharing** (gap 1) more important than **forgetting discipline** (gap 2)?
- Does **multi-agent memory coordination** (gap 6) override **security** (gap 4)?
- Which gaps are must-haves vs nice-to-haves for the MVP?

**What's observed:**
The document presents Option 2 (Consolidation Engine) as the most feature-complete (can add decay/validation, single source of truth), which suggests an **implicit bias toward feature maximalism** as the decision criterion. But feature coverage may not be the right lens for Interverse — given the existing 5 memory systems, **ecosystem fit** and **non-disruption** might be more important.

**Recommendation:**
Add a **Decision Criteria Table** that explicitly ranks the 7 gaps by importance (P0/P1/P2) and maps each option to how well it addresses them. For example:

| Capability | Priority | Option 1 | Option 2 | Option 3 | Option 4 |
|------------|----------|----------|----------|----------|----------|
| Cross-project sharing | P1 | ✓ | ✓ | ✓ | ✓ |
| Forgetting discipline | P1 | ✗ | ✓ | ✓ | ✓ |
| Multi-agent coordination | P0 | ? | ✓ | ? | ✓ |
| Security | P2 | ✗ | ✓ | ✓ | ✓ |
| Memory validation | P1 | ✗ | ✓ | ✓ | ✓ |

Without this, the decision becomes **gut feel** rather than **evidence-based**.

---

#### P2-2: Anchoring Bias Toward Option 2 (Consolidation Engine)

**Location:** Option enumeration (lines 17-22), Landscape Research (lines 70-87)
**Lens Applied:** Framing Effects, Confirmation Bias

**Issue:**
Option 2 (Consolidation Engine) is framed with the most feature coverage and the strongest language:
- "Single source of truth" (a design ideal)
- "Can add all missing features" (completeness)
- "Cleanest retrieval" (aesthetic appeal)

By contrast:
- Option 1 is framed as "lowest common denominator" (negative framing)
- Option 3 is framed as "more complex than it looks" (risk framing)
- Option 4 is framed as "massive migration, high risk" (deterrent framing)

**What's observed:**
The landscape research heavily features **claude-mem** (28.6k stars, 10x token savings, 5 lifecycle hooks) and **MemCP** (4-graph architecture, 218x token reduction, 341 tests) — both of which are **consolidation architectures**. This creates an **anchoring effect**: the first systems presented in the research are consolidation systems, which primes the reader to see Option 2 as the "industry standard."

**What would reveal this bias:**
Reframe Option 1 with equivalent positive language:
- "Respects Conway's Law — memory architecture matches team boundaries"
- "Zero migration risk — existing systems stay battle-tested"
- "Extensible — add capabilities without breaking consumers"

Does Option 1 still seem inferior? If not, the original framing was biased.

**Recommendation:**
Add a **Framing Check** section that presents the same option in both positive and negative frames, then asks: "Does the decision flip based on framing alone?" If yes, the decision criteria are not robust.

---

#### P2-3: Landscape Research as Justification vs. Discovery

**Location:** Landscape Research (lines 69-96), Interverse-Specific Considerations (lines 98-106)
**Lens Applied:** Confirmation Bias, The Snake Oil Test

**Issue:**
The landscape research is comprehensive (13 systems) but there's no evidence it's being used for **discovery** (learning what's possible) vs. **justification** (finding examples that support a pre-chosen option). Key symptoms:

1. **No negative findings:** None of the 13 systems are flagged as "tried this, didn't work, here's why." All are presented as successful implementations.
2. **No failure modes:** ShieldCortex has a 6-layer security pipeline — has anyone stress-tested it? MemCP claims 218x token reduction — in what scenarios does it fail to deliver?
3. **No ecosystem mismatch analysis:** Interverse has **5 existing memory systems** (auto-memory, compound, interfluence, .clavain/learnings, CLAUDE.md/AGENTS.md). The landscape systems are mostly **greenfield implementations** (building from scratch). Is the research even applicable to a brownfield migration?

**What's missing:**
A **Snake Oil Test** for each landscape system:
- "We tested claude-mem's 10x token savings claim by replaying our last 50 sessions. Actual savings: 2.3x. The gap comes from their assumptions about memory density."
- "MemCP's 4-graph architecture assumes causal edges are extractable. We ran it on 10 Interverse compound docs — only 3 had extractable causal chains."

Without empirical validation, the landscape research is just **feature tourism** — collecting cool ideas without knowing if they work in practice.

**Recommendation:**
Add a **Validation Experiments** section:
- "Before choosing Option 2, we'll run claude-mem against Clavain's last 100 auto-memory writes to measure actual token savings."
- "Before choosing Option 1, we'll implement a read-only federation tool and measure retrieval latency across 5 projects."

This shifts the decision from **"which architecture sounds best?"** to **"which architecture performs best in our environment?"**

---

#### P2-4: Multi-Agent Memory Coordination Underexplored

**Location:** Interverse-Specific Considerations (line 100), Questions for Analysis (line 112)
**Lens Applied:** N-ply Thinking, Jevons Paradox

**Issue:**
The document mentions "intermute provides messaging" and "interlock provides file reservation coordination" (line 100) and asks "How should intermem handle multi-agent memory (concurrent writes, conflict resolution)?" (line 112) — but this is **understated given Interverse's architecture**.

**What's underexplored:**

1. **Concurrent agent memory writes:** If 3 Clavain review agents are running in parallel (interflux, intercraft, interdoc), and all write to intermem at the same time, what happens?
   - Does intermem use interlock for write coordination?
   - Does it queue writes and serialize them?
   - Does it allow concurrent writes and resolve conflicts later?

2. **Memory ownership attribution:** If Agent A writes a memory and Agent B retrieves it, does B know the provenance? This is listed in the 7 gaps (gap 7: "No memory provenance") but not explored in the options:
   - Option 1 (Federation) can't add provenance without backend buy-in
   - Option 2 (Consolidation) can add provenance but at migration cost
   - Option 3 (Smart Layer) can add provenance as metadata overlay

3. **Memory as a coordination primitive:** What if memory isn't just *data* but a **coordination mechanism**? For example:
   - Agent A writes: "I'm about to refactor auth.go"
   - Agent B retrieves this before editing auth.go
   - This is memory + interlock combined — has this been considered?

**Why this matters:**
Interverse is explicitly multi-agent (5 concurrent review agents in Clavain, interlock for file coordination, intermute for messaging). If intermem doesn't deeply integrate with this architecture, it becomes **yet another siloed system** rather than a **force multiplier**.

**Recommendation:**
Add a **Multi-Agent Coordination** subsection under each option:
- "Option 1: Federation reads are lock-free, but concurrent writes to backends are uncoordinated. Risk: duplicate memories from parallel agents."
- "Option 2: Consolidation can use intermute for write serialization. Benefit: single writer, no conflicts. Cost: bottleneck if agents wait on lock."
- "Option 3: Smart Layer can track agent attribution in overlay without backend changes. Benefit: provenance without migration. Cost: overlay writes are uncoordinated unless intermem integrates interlock."

Without this analysis, the team risks building a memory system that **works well for single-agent workflows but breaks under Clavain's multi-agent orchestration**.

---

### P3 Findings (Consider Also — Enrichment Opportunities)

#### P3-1: Apply Pre-Mortem to Each Option

**Location:** Option enumeration (lines 11-33)
**Lens Applied:** Kobayashi Maru, Scenario Planning

**Suggestion:**
Add a **Pre-Mortem** section: "It's 6 months from now. We chose [Option X] and it failed catastrophically. What happened?"

**Example pre-mortems:**

- **Option 1 (Federation):** "Backend APIs diverged (auto-memory added new features, compound changed schema). Federation layer became a compatibility shim with 500 lines of adapter code. Token overhead from abstraction negated any retrieval benefits."

- **Option 2 (Consolidation):** "Migration took 4 months. Halfway through, interfluence added a new learning type that didn't fit the canonical schema. We either break backward compat or add a schema escape hatch, defeating the 'single source of truth' goal."

- **Option 3 (Smart Layer):** "Overlay drifted from source. A compound doc was deleted but overlay still had metadata. Agents retrieved stale confidence scores for non-existent memories. Debugging was nightmare — two systems, each blaming the other."

- **Option 4 (Replace Everything):** "We spent 8 months building intermem. Clavain was blocked on memory features the entire time. By the time intermem shipped, the team had written 200 new auto-memory entries and 15 compound docs using the old system. Migration debt doubled during the rewrite."

**Why this helps:**
Pre-mortems force the team to **visualize failure modes** before committing. If Option 2's pre-mortem is scarier than Option 1's, that's a signal — even if Option 2 has better feature coverage on paper.

---

#### P3-2: Apply Sour Spots Lens to Combinations

**Location:** Option enumeration (lines 11-33)
**Lens Applied:** Sour Spots

**Suggestion:**
The document treats the 4 options as mutually exclusive, but what if a **hybrid** is worse than any single option?

**Sour spot example:**
- "We start with Option 1 (Federation) for speed, intending to migrate to Option 2 (Consolidation) later. But federation creates an **abstraction barrier** that makes migration harder. Now we're stuck with federation overhead AND migration complexity — the worst of both worlds."

**What to check:**
- Can Option 1 → Option 2 transition work, or does federation lock you in?
- Can Option 3 (Smart Layer) + Option 1 (Federation) coexist, or does the overlay break federation assumptions?
- If Option 4 (Replace Everything) is too risky, can you do Option 3 first as a stepping stone? Or does the overlay become technical debt during replacement?

**Recommendation:**
Add a **Transition Matrix** showing whether Option A → Option B is feasible, risky, or impossible. This reveals sour spots where incremental commitment isn't possible.

---

#### P3-3: Apply Signposts for Decision Triggers

**Location:** Questions for Analysis (line 114)
**Lens Applied:** Signposts

**Suggestion:**
The document asks "What are the biggest risks and how to mitigate them?" (line 114) but doesn't define **observable criteria** that would trigger a strategy change.

**Example signposts:**

- "If retrieval latency exceeds 200ms in Option 1 (Federation), we'll migrate to Option 2 (Consolidation)."
- "If migration complexity in Option 2 exceeds 4 engineer-weeks, we'll fall back to Option 3 (Smart Layer)."
- "If overlay drift in Option 3 causes more than 5 stale memory incidents per month, we'll consolidate to Option 2."

**Why this helps:**
Signposts remove **emotional attachment** from the decision. Instead of debating "should we abandon this?" every 2 weeks, the team pre-commits to **objective criteria**. When latency hits 201ms, the decision is automatic.

---

#### P3-4: Token Budget as a First-Class Constraint

**Location:** Interverse-Specific Considerations (line 102)
**Lens Applied:** Cone of Uncertainty, Theory of Change

**Suggestion:**
The document mentions "interstat tracks token budgets. Memory injection must be token-aware" (line 102) but doesn't quantify the **token budget constraint** for memory retrieval.

**What's missing:**
- "Current auto-memory injection is 200 lines × 4 tokens/line = 800 tokens per session. Acceptable overhead: 1000-1500 tokens."
- "Landscape research shows claude-mem achieves 10x savings (80 tokens) but requires embedding overhead. Net savings: TBD."
- "If Option 1 (Federation) adds 200 tokens of abstraction overhead, the 10x savings becomes 2.5x. Is that still worth it?"

**Why this matters:**
Token efficiency is **measurable** and ties directly to cost and latency. It's one of the few decision criteria that can be benchmarked empirically before building anything. Use it as a **tiebreaker** when other criteria are ambiguous.

**Recommendation:**
Add a **Token Budget Analysis** table:

| Option | Estimated Injection Overhead | Retrieval Latency | Net Token Savings |
|--------|------------------------------|-------------------|-------------------|
| Option 1 (Federation) | +200 tokens (abstraction) | ~150ms | TBD |
| Option 2 (Consolidation) | +50 tokens (embeddings) | ~50ms | 8-10x |
| Option 3 (Smart Layer) | +100 tokens (metadata) | ~100ms | 5-7x |
| Option 4 (Replace) | 0 tokens (optimized) | ~30ms | 12-15x |

If Option 2 delivers 10x savings but costs 4 months of migration, what's the **break-even point** (number of sessions before savings justify the migration cost)?

---

## Cross-Cutting Patterns

### Pattern 1: Exploration vs. Exploitation Imbalance

**Observation:**
The document is **deep in exploration mode** (13 external systems researched, 7 gaps identified, 4 options enumerated) but hasn't defined the **transition criteria** to exploitation (when do we stop researching and start building?).

**Risk:**
Without a clear **decision deadline** or **starter option**, the team risks indefinite exploration — always finding "one more system to analyze" or "one more gap to consider."

**Mitigation:**
Add a **Decision Timeline**:
- "By [date], we'll commit to one option or a starter option."
- "By [date], we'll have built a prototype and gathered empirical data."
- "If no option is clearly superior by [date], we'll default to Option 1 (lowest risk, most reversible)."

---

### Pattern 2: Feature Coverage vs. Ecosystem Fit

**Observation:**
The landscape research emphasizes **feature coverage** (decay, validation, provenance, security) but the decision question is **ecosystem fit** ("Which option best fits the Interverse ecosystem given its existing infrastructure?").

**Risk:**
The team might choose Option 2 (Consolidation) because it has the most features, even if Option 3 (Smart Layer) or Option 1 (Federation) fits better with Interverse's **existing 5 memory systems**.

**Mitigation:**
Reframe the decision: **"Which option delivers the most value with the least disruption?"** This shifts the focus from feature maximalism to incremental improvement.

---

### Pattern 3: Missing Theory of Change

**Observation:**
The document asks "Which option delivers the most value?" but doesn't map **architectural choice → user behavior change → desired outcome**. For example:

- If we choose Option 2 (Consolidation), what **user behavior** changes?
  - Agents retrieve memories faster? (measurable: latency)
  - Agents retrieve **better** memories? (measurable: relevance score)
  - Agents trust memories more? (measurable: how often they ignore/override memories)

**Risk:**
Without a theory of change, the team risks building infrastructure that doesn't change outcomes. For example, if agents already ignore 80% of retrieved memories (low trust), adding decay/validation (Option 2) won't help — the problem is **memory quality**, not memory quantity.

**Mitigation:**
Add a **Theory of Change** section:
- "Current problem: Agents retrieve 10 memories per session, use 2, ignore 8. 80% waste."
- "Hypothesis: The ignored memories are stale or low-relevance."
- "If we choose Option 2 (Consolidation + decay), we expect: retrieval drops to 5 memories, agents use 4, ignore 1. 20% waste."
- "Validation: Track retrieval → usage ratio before/after intermem."

---

## Recommended Next Steps

1. **Add a Reversibility Matrix** (addresses P1-1)
   For each option, specify: one-way door threshold, rollback cost, escape hatches.

2. **Define a Starter Option** (addresses P1-2)
   Create Option 0: lightweight instrumentation on existing systems to gather empirical data before committing to architecture.

3. **Explicit Decision Criteria Table** (addresses P2-1)
   Rank the 7 gaps by priority (P0/P1/P2) and score each option against them.

4. **Framing Check** (addresses P2-2)
   Reframe each option in positive/negative language and check if the decision flips.

5. **Validation Experiments** (addresses P2-3)
   Test landscape research claims (token savings, retrieval latency) against Interverse's actual data.

6. **Multi-Agent Coordination Analysis** (addresses P2-4)
   For each option, specify how it integrates with interlock/intermute for concurrent agent writes.

7. **Pre-Mortem for Each Option** (addresses P3-1)
   Visualize failure modes 6 months out to surface hidden risks.

8. **Token Budget Analysis** (addresses P3-4)
   Quantify token overhead and net savings for each option to enable empirical comparison.

9. **Theory of Change** (addresses Pattern 3)
   Map architectural choice → user behavior change → measurable outcome.

10. **Decision Timeline** (addresses Pattern 1)
    Set a deadline for exploration → exploitation transition, with a fallback to "lowest risk, most reversible" option.

---

## Final Assessment

**Strengths:**
This is a well-structured brainstorm document with strong enumeration of alternatives and comprehensive landscape research. The 4 options are architecturally distinct, and the 7 gaps provide a clear capability roadmap.

**Critical Weaknesses:**
The document lacks **decision hygiene**: no explicit criteria, no reversibility analysis, no starter option, and no validation of landscape research claims. This creates risk of **analysis paralysis** (exploring forever) or **commitment escalation** (picking Option 2 or 4 and sticking with it even after failure signals).

**Overall Severity:** Moderate (P2 risk).
The decision won't fail catastrophically if these gaps aren't addressed, but it will likely take longer, cost more, and deliver less value than an evidence-based, reversible approach.

**Recommendation:**
Before moving to PRD or implementation, add 2-3 sections addressing the P1 findings (reversibility, starter option) and run 1-2 validation experiments (token savings, retrieval latency) to test landscape research claims against Interverse's actual environment.

---

## Appendix: Lens Reference

**Lenses Applied in This Review (12 of 288 total):**

1. **Explore vs. Exploit** — The tension between learning new approaches and optimizing known ones
   *Applied to: exploration/exploitation imbalance, missing starter option*

2. **Kobayashi Maru** — No-win scenarios where reframing the problem is the only escape
   *Applied to: pre-mortem analysis*

3. **N-ply Thinking** — Considering N levels of consequences before committing to a move
   *Applied to: reversibility analysis, multi-agent coordination*

4. **Cone of Uncertainty** — How the range of possible outcomes narrows as you gather information
   *Applied to: token budget analysis*

5. **Scenario Planning** — Preparing for multiple futures rather than betting on a single prediction
   *Applied to: pre-mortem analysis*

6. **Dissolving the Problem** — When the best solution is recognizing the problem doesn't need to exist
   *(Not applied — no reframing opportunities found)*

7. **The Starter Option** — Making the smallest possible commitment to learn the most before scaling
   *Applied to: missing MVP, incremental path*

8. **Sour Spots** — Sweet spots' evil twin — combinations that look promising but deliver the worst of both
   *Applied to: hybrid option analysis*

9. **Theory of Change** — Mapping the causal chain from action to intended outcome to test assumptions
   *Applied to: implicit decision criteria, missing user behavior change mapping*

10. **Jevons Paradox** — When efficiency gains increase rather than decrease overall consumption
    *(Not applied — no efficiency paradoxes found)*

11. **Signposts** — Pre-committed decision criteria that trigger a strategy change when observed
    *Applied to: missing decision triggers*

12. **The Snake Oil Test** — A systematic check for whether claims hold up to scrutiny
    *Applied to: landscape research validation*

**Additional Lenses via MCP:** Not available (MCP server unavailable).

---

**NOTE**: MCP server unavailable — review used fallback lens subset (12/288 lenses). Install interlens-mcp for full coverage.
