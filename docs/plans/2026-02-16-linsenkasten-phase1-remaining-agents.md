# Interlens Phase 1 — Remaining Agents, MCP, Severity
**Phase:** planned (as of 2026-02-16)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Complete Phase 1 of the Interlens lens agents — create 4 remaining cognitive review agents (fd-decisions, fd-people, fd-resilience, fd-perception), wire MCP integration for dynamic lens retrieval, and formalize severity guidance and deduplication.

**Architecture:** Four new `.md` agent files in `plugins/interflux/agents/review/` following the exact fd-systems template. MCP integration added as conditional instructions to all 5 lens agent files. Severity guidance and dedup rules confirmed in agent prompts + synthesis documentation.

**Tech Stack:** Markdown (agent files), prompt engineering

---

## Task 1: Create fd-decisions Agent (F1b)

**Files:**
- Create: `plugins/interflux/agents/review/fd-decisions.md`

**Step 1: Write the agent file**

Create `plugins/interflux/agents/review/fd-decisions.md` using the exact structure of fd-systems.md (108 lines). The file must have:

1. **YAML frontmatter** — same format as fd-systems:
   - `name: fd-decisions`
   - `description:` one-line summary + 2 `<example>` blocks
   - `model: sonnet`

Description one-liner: "Flux-drive Decision Quality reviewer — evaluates decision traps, cognitive biases, uncertainty handling, strategic paradoxes, and option framing in strategy documents, PRDs, and plans."

Example 1: Context: User wrote a migration plan with a "big bang" cutover. User asks to review for decision quality blind spots. Commentary: Migration plans involve irreversibility, optionality loss, and sunk cost traps — fd-decisions' core domain.

Example 2: Context: User wrote a PRD that chooses a specific technology stack without discussing alternatives. Commentary: Technology selection without explicit trade-off analysis risks anchoring bias and explore/exploit imbalance.

2. **Opening paragraph**: "You are a Flux-drive Decision Quality Reviewer. Your job is to evaluate whether documents adequately consider decision traps, cognitive biases, uncertainty management, and strategic trade-offs — catching blind spots where authors commit to choices without examining the decision process itself."

3. **`## First Step (MANDATORY)`** — identical to fd-systems (read CLAUDE.md/AGENTS.md, codebase-aware vs generic mode). Copy this section verbatim.

4. **`## Review Approach`** — 4 subsections:

**### 1. Decision Traps & Cognitive Biases**
- Check for anchoring bias: is the first option presented treated as the default without evaluating alternatives?
- Flag sunk cost reasoning: are past investments used to justify future commitments?
- Identify framing effects: would the decision change if the same information were presented differently?
- Check for confirmation bias: does the document seek evidence that supports a predetermined conclusion?
- Flag survivorship bias: are conclusions drawn only from successful examples, ignoring failures?

**### 2. Uncertainty & Optionality**
- Evaluate whether the document quantifies uncertainty or treats all scenarios as equally likely
- Check for premature commitment: are irreversible decisions made before they need to be?
- Identify missing option value: would keeping options open longer reduce risk?
- Flag overconfidence: does the document present estimates without confidence ranges?
- Check for scenario blindness: are alternatives to the happy path considered?

**### 3. Strategic Paradoxes & Trade-offs**
- Apply explore/exploit analysis: is the balance between learning and executing appropriate?
- Check for local vs global optimization: does this decision optimize a subsystem at the system's expense?
- Identify paradoxes where both sides of a trade-off have merit and neither is acknowledged
- Flag false dichotomies: are there really only two options, or is the framing artificially constrained?
- Evaluate temporal trade-offs: short-term gains vs long-term costs (and vice versa)

**### 4. Decision Process Quality**
- Check for reversibility analysis: which decisions can be undone, and at what cost?
- Flag decisions by committee without clear ownership or accountability
- Identify missing pre-mortems: what would make this decision look catastrophically wrong in 6 months?
- Check for decision fatigue: are too many decisions packed together, risking quality degradation?
- Evaluate whether the decision criteria are stated explicitly or left implicit

5. **`## Key Lenses`** — 12 curated lenses with comment explaining selection:

```markdown
## Key Lenses

<!-- Curated from Interlens's Strategic Decision Making, Navigating Uncertainty, and Balance & Paradox frames.
     These 12 (of 288 total) were selected because they form a complete decision analysis toolkit:
     3 for decision traps/biases, 3 for uncertainty/optionality, 3 for paradox/trade-offs, 3 for process quality.
     Other cognitive domains (systems, people, perception) are reserved for their respective agents. -->

When reviewing, apply these lenses to surface gaps in the document's reasoning:

1. **Explore vs. Exploit** — The tension between learning new approaches and optimizing known ones
2. **Kobayashi Maru** — No-win scenarios where reframing the problem is the only escape
3. **N-ply Thinking** — Considering N levels of consequences before committing to a move
4. **Cone of Uncertainty** — How the range of possible outcomes narrows as you gather information
5. **Scenario Planning** — Preparing for multiple futures rather than betting on a single prediction
6. **Dissolving the Problem** — When the best solution is recognizing the problem doesn't need to exist
7. **The Starter Option** — Making the smallest possible commitment to learn the most before scaling
8. **Sour Spots** — Sweet spots' evil twin — combinations that look promising but deliver the worst of both
9. **Theory of Change** — Mapping the causal chain from action to intended outcome to test assumptions
10. **Jevons Paradox** — When efficiency gains increase rather than decrease overall consumption
11. **Signposts** — Pre-committed decision criteria that trigger a strategy change when observed
12. **The Snake Oil Test** — A systematic check for whether claims hold up to scrutiny
```

6. **`## Cognitive Severity Guidance`** — identical to fd-systems (Blind Spot → P1, Missed Lens → P2, Consider Also → P3). Copy verbatim.

7. **`## What NOT to Flag`** — same structure as fd-systems but with domain-appropriate exclusions:
- Technical implementation details (defer to fd-architecture, fd-correctness)
- Code quality, naming, or style (defer to fd-quality)
- Security or deployment concerns (defer to fd-safety)
- Performance or algorithmic complexity (defer to fd-performance)
- User experience or product-market fit (defer to fd-user-product)
- Lenses from other cognitive domains: feedback loops/emergence/systems dynamics (reserved for fd-systems), trust/power/communication (reserved for fd-people), innovation/constraints (reserved for fd-resilience), perception/sensemaking (reserved for fd-perception)
- Documents that are purely technical (code, configs, API specs) — cognitive review adds no value there

8. **`## Focus Rules`** — identical to fd-systems. Copy verbatim.

**Step 2: Validate structure**

```bash
head -1 plugins/interflux/agents/review/fd-decisions.md | grep -q "^---$"
grep -q "^## First Step" plugins/interflux/agents/review/fd-decisions.md
grep -q "^## Review Approach" plugins/interflux/agents/review/fd-decisions.md
grep -q "^## Key Lenses" plugins/interflux/agents/review/fd-decisions.md
grep -q "^## What NOT to Flag" plugins/interflux/agents/review/fd-decisions.md
grep -q "^## Focus Rules" plugins/interflux/agents/review/fd-decisions.md
```

---

## Task 2: Create fd-people Agent (F1b)

**Files:**
- Create: `plugins/interflux/agents/review/fd-people.md`

**Step 1: Write the agent file**

Same structure as Task 1, with these domain-specific differences:

- `name: fd-people`
- Description one-liner: "Flux-drive Human Systems reviewer — evaluates trust dynamics, power structures, communication patterns, team culture, and leadership gaps in strategy documents, PRDs, and plans."
- Example 1: Context: User wrote a reorg plan that moves teams without consulting them. Commentary: Reorganization without stakeholder involvement risks trust erosion, Conway's Law violations, and authority gradient blind spots.
- Example 2: Context: User wrote a process change that adds mandatory reviews by senior engineers. Commentary: Mandatory approval gates involve power dynamics, bottleneck risks, and psychological safety implications.

Opening paragraph: "You are a Flux-drive Human Systems Reviewer. Your job is to evaluate whether documents adequately consider trust, power, communication, and team dynamics — catching blind spots where authors design systems that look good on paper but ignore how people actually behave in organizations."

Review Approach — 4 subsections:

**### 1. Trust & Psychological Safety**
- Check for trust assumptions: does the proposal require trust that hasn't been established?
- Flag erosion risks: could this change undermine existing trust relationships?
- Identify missing psychological safety considerations: will people feel safe to disagree or report problems?
- Check for vulnerability mismatch: does the plan ask some parties to be more vulnerable than others?
- Evaluate whether feedback mechanisms exist for course-correcting trust failures

**### 2. Power & Authority Dynamics**
- Map explicit and implicit power structures in the proposed system
- Check for authority gradient problems: are decisions concentrated in too few hands?
- Flag accountability gaps: who is responsible when things go wrong?
- Identify Conway's Law implications: will the organizational structure produce the desired system structure?
- Check for power asymmetries that could enable exploitation or create bottlenecks

**### 3. Communication & Knowledge Flow**
- Evaluate whether communication channels match the information flow requirements
- Check for knowledge silos: does the proposal create or reinforce information asymmetries?
- Flag handoff risks: where do messages get lost, distorted, or delayed?
- Identify missing feedback loops in the communication structure
- Check whether the communication overhead scales with the proposed team structure

**### 4. Culture & Collaboration Patterns**
- Check for cultural assumptions: does the proposal assume a specific working culture that may not exist?
- Flag collaboration anti-patterns: forced pairing, meeting overload, committee-driven decisions
- Identify incentive misalignments: do individual incentives conflict with team goals?
- Check for in-group/out-group dynamics that could emerge from the proposed structure
- Evaluate whether the proposal accounts for remote/distributed team challenges

Key Lenses — 12 curated from Trust & Collaboration, Power & Agency, Communication & Dialogue, Leadership Dynamics, Organizational Culture & Teams, Network & Social Systems:

```markdown
## Key Lenses

<!-- Curated from Interlens's Trust & Collaboration, Power & Agency, Communication & Dialogue,
     Leadership Dynamics, Organizational Culture & Teams, and Network & Social Systems frames.
     These 12 (of 288 total) were selected because they form a complete human systems analysis toolkit:
     3 for trust/safety, 3 for power/authority, 3 for communication/knowledge, 3 for culture/collaboration.
     Other cognitive domains (systems, decisions, perception) are reserved for their respective agents. -->

When reviewing, apply these lenses to surface gaps in the document's reasoning:

1. **Psychological Safety** — Whether people feel safe to take interpersonal risks without fear of punishment
2. **Authority Gradient** — The power differential between decision-makers and those affected by decisions
3. **Conway's Law** — Organizations inevitably design systems that mirror their communication structures
4. **Knowledge Silos** — Information trapped in subgroups, invisible to the broader organization
5. **Incentive Misalignment** — When individual rewards pull against collective goals
6. **Bystander Effect** — The diffusion of responsibility that grows with group size
7. **Organizational Debt** — Accumulated structural compromises that slow future change
8. **Tribal Knowledge** — Critical understanding that exists only in people's heads, not in systems
9. **Dunbar Layers** — The natural limits on how many relationships a person can maintain at different depths
10. **Gift Culture** — Communities built on status through contribution rather than authority
11. **The Overton Window** — The range of ideas considered acceptable in the current context
12. **Learned Helplessness** — When repeated failures train people to stop trying even when conditions change
```

What NOT to Flag — same structure, with fd-people-specific exclusions for other cognitive domains (systems dynamics reserved for fd-systems, decision quality reserved for fd-decisions, etc.)

---

## Task 3: Create fd-resilience Agent (F1b)

**Files:**
- Create: `plugins/interflux/agents/review/fd-resilience.md`

**Step 1: Write the agent file**

- `name: fd-resilience`
- Description one-liner: "Flux-drive Adaptive Capacity reviewer — evaluates antifragility, creative constraints, resource allocation, innovation dynamics, and failure recovery in strategy documents, PRDs, and plans."
- Example 1: Context: User wrote an architecture plan with a single database and no fallback. Commentary: Single points of failure, missing redundancy, and no degradation strategy are antifragility blind spots.
- Example 2: Context: User wrote a resource allocation plan that front-loads all investment in one approach. Commentary: All-in resource commitment without staged investment risks creative destruction blindness and constraint violation.

Opening paragraph: "You are a Flux-drive Adaptive Capacity Reviewer. Your job is to evaluate whether documents adequately consider resilience, creative constraints, resource dynamics, and innovation patterns — catching blind spots where authors design for the happy path without building the capacity to adapt when conditions change."

Review Approach — 4 subsections:

**### 1. Resilience & Antifragility**
- Check whether the system merely survives disruption (resilient) or improves from it (antifragile)
- Flag single points of failure and missing redundancy
- Identify graceful degradation paths: what does partial failure look like?
- Check for recovery time assumptions: how long to return to normal after disruption?
- Evaluate whether the proposal includes stress testing or chaos engineering thinking

**### 2. Creative Constraints & Problem Solving**
- Check whether constraints are treated as obstacles or as creative drivers
- Flag over-resourcing: sometimes fewer resources produce better solutions
- Identify assumption locks: are inherited constraints still valid?
- Check for first-principles thinking: is the solution built from fundamentals or copied from precedent?
- Evaluate whether the proposal allows for serendipity and unexpected discoveries

**### 3. Resource Dynamics & Allocation**
- Check for resource concentration: is too much invested in a single approach?
- Flag staged investment opportunities: could a smaller bet test the hypothesis first?
- Identify resource bottlenecks that could constrain the entire system
- Check for diminishing returns: at what point does additional investment stop helping?
- Evaluate whether resource allocation matches priority (not just availability)

**### 4. Innovation & Creative Destruction**
- Check whether the proposal accounts for disruption to existing systems
- Flag preservation bias: is the status quo being protected at the cost of improvement?
- Identify transition costs: what must be destroyed to create the new thing?
- Check for innovation theater: is the proposal genuinely novel or superficially different?
- Evaluate whether the proposal includes mechanisms for killing underperforming initiatives

Key Lenses — 12 curated from Resilience & Adaptation, Creative Problem Solving, Boundaries & Constraints, Innovation & Creation, Innovation & Creative Destruction, Crisis & Opportunity, Resource Dynamics & Constraints:

```markdown
## Key Lenses

<!-- Curated from Interlens's Resilience & Adaptation, Creative Problem Solving, Boundaries & Constraints,
     Innovation & Creation, Innovation & Creative Destruction, Crisis & Opportunity, and Resource Dynamics & Constraints frames.
     These 12 (of 288 total) were selected because they form a complete adaptive capacity analysis toolkit:
     3 for resilience/antifragility, 3 for creative constraints, 3 for resource dynamics, 3 for innovation patterns.
     Other cognitive domains (systems, decisions, perception) are reserved for their respective agents. -->

When reviewing, apply these lenses to surface gaps in the document's reasoning:

1. **Antifragility** — Systems that gain from disorder rather than merely surviving it
2. **Graceful Degradation** — Designing for partial failure so the whole system doesn't collapse
3. **Redundancy vs. Efficiency** — The tension between backup capacity and lean operations
4. **Creative Constraints** — How limitations can drive innovation rather than prevent it
5. **First Principles** — Reasoning from fundamental truths rather than by analogy to existing solutions
6. **Assumption Locks** — Inherited constraints that are no longer valid but still shape decisions
7. **Diminishing Returns** — The point at which additional effort produces less and less value
8. **Staging & Sequencing** — Breaking large bets into smaller, reversible steps with learning checkpoints
9. **Resource Bottleneck** — The single constraint that limits throughput of the entire system
10. **Creative Destruction** — The necessary dismantling of the old to make room for the new
11. **MVP Thinking** — Finding the smallest experiment that tests the riskiest assumption
12. **Phoenix Moments** — Crises that create opportunities unavailable during stability
```

---

## Task 4: Create fd-perception Agent (F1b)

**Files:**
- Create: `plugins/interflux/agents/review/fd-perception.md`

**Step 1: Write the agent file**

- `name: fd-perception`
- Description one-liner: "Flux-drive Sensemaking reviewer — evaluates mental models, information quality, temporal reasoning, transformation patterns, and perceptual blind spots in strategy documents, PRDs, and plans."
- Example 1: Context: User wrote a competitive analysis that relies on a single data source. Commentary: Single-source analysis risks map/territory confusion, confirmation bias in information selection, and signal/noise conflation.
- Example 2: Context: User wrote a 3-year transformation roadmap with fixed milestones. Commentary: Long-range transformation plans risk temporal discounting, paradigm shift blindness, and illusion of control over future states.

Opening paragraph: "You are a Flux-drive Sensemaking Reviewer. Your job is to evaluate whether documents adequately consider mental models, information quality, temporal reasoning, and perceptual biases — catching blind spots where authors confuse their model of reality with reality itself."

Review Approach — 4 subsections:

**### 1. Mental Models & Map/Territory**
- Check whether the document acknowledges the difference between its model and reality
- Flag reification: are abstractions being treated as concrete things?
- Identify model lock-in: is one mental model dominating when multiple perspectives would be more accurate?
- Check for narrative fallacy: is the document constructing a compelling story that oversimplifies causation?
- Evaluate whether the key assumptions underlying the mental model are stated explicitly

**### 2. Information Quality & Signal/Noise**
- Check for information source diversity: does the analysis rely on too few or too similar sources?
- Flag metrics fixation: are easily measurable things being prioritized over important but hard-to-measure things?
- Identify Goodhart's Law risks: will measuring this metric cause it to stop being a good measure?
- Check for missing information: what data would change the conclusion if it were available?
- Evaluate whether the proposal distinguishes between leading and lagging indicators

**### 3. Temporal Reasoning & Transformation**
- Check for temporal discounting: are long-term consequences given appropriate weight?
- Flag change blindness: does the proposal assume the current environment will persist?
- Identify paradigm shift exposure: what changes in the landscape would invalidate the strategy?
- Check for transformation sequencing: does the order of changes account for dependencies and readiness?
- Evaluate whether the proposal includes sensing mechanisms to detect when conditions have changed

**### 4. Perceptual Biases & Sensemaking**
- Check for attentional bias: what is the document focusing on, and what is it ignoring?
- Flag availability heuristic: are recent or vivid events overweighted relative to base rates?
- Identify false pattern recognition: are coincidences being interpreted as causal relationships?
- Check for perspective limitation: whose viewpoint shapes the analysis, and whose is missing?
- Evaluate whether the document accounts for how different stakeholders perceive the same situation

Key Lenses — 12 curated from Perception & Reality, Knowledge & Sensemaking, Information Ecology, Time & Evolution, Temporal Dynamics & Evolution, Digital Transformation, Transformation & Change, Learning & Adaptation, Design & Detail:

```markdown
## Key Lenses

<!-- Curated from Interlens's Perception & Reality, Knowledge & Sensemaking, Information Ecology,
     Time & Evolution, Temporal Dynamics & Evolution, and Transformation & Change frames.
     These 12 (of 288 total) were selected because they form a complete sensemaking analysis toolkit:
     3 for mental models, 3 for information quality, 3 for temporal reasoning, 3 for perceptual biases.
     Other cognitive domains (systems, decisions, people) are reserved for their respective agents. -->

When reviewing, apply these lenses to surface gaps in the document's reasoning:

1. **Map vs. Territory** — The fundamental gap between our models of reality and reality itself
2. **Narrative Fallacy** — The human tendency to construct stories that oversimplify complex causation
3. **Reification** — Treating abstract concepts as if they were concrete, tangible things
4. **Goodhart's Law** — When a measure becomes a target, it ceases to be a good measure
5. **Signal vs. Noise** — Distinguishing meaningful information from random variation
6. **Leading vs. Lagging Indicators** — Whether metrics predict the future or merely report the past
7. **Temporal Discounting** — Systematically undervaluing future consequences relative to present ones
8. **Paradigm Shift** — When the underlying model of reality changes, not just the data within it
9. **Change Blindness** — Failing to notice gradual changes that would be obvious if they happened suddenly
10. **Availability Heuristic** — Overweighting vivid, recent, or emotionally salient information
11. **Perspective Taking** — Actively modeling how different stakeholders perceive the same situation
12. **Streetlight Effect** — Searching for answers where it's easy to look rather than where they're likely to be found
```

---

## Task 5: Verify Agent Suite (F1b completion)

**Step 1: Structural validation**

```bash
cd /root/projects/Interverse/plugins/interflux
# Agent count should be 12 (7 existing technical + 5 cognitive)
ls agents/review/*.md | wc -l

# All 5 cognitive agents exist
for agent in fd-systems fd-decisions fd-people fd-resilience fd-perception; do
    test -f agents/review/$agent.md && echo "OK: $agent" || echo "MISSING: $agent"
done

# All agents have required sections
for agent in agents/review/fd-{decisions,people,resilience,perception}.md; do
    echo "=== $(basename $agent) ==="
    grep -q "^---$" "$agent" && echo "  frontmatter: OK" || echo "  frontmatter: MISSING"
    grep -q "^## First Step" "$agent" && echo "  first-step: OK" || echo "  first-step: MISSING"
    grep -q "^## Review Approach" "$agent" && echo "  review-approach: OK" || echo "  review-approach: MISSING"
    grep -q "^## Key Lenses" "$agent" && echo "  key-lenses: OK" || echo "  key-lenses: MISSING"
    grep -q "^## Cognitive Severity" "$agent" && echo "  severity: OK" || echo "  severity: MISSING"
    grep -q "^## What NOT to Flag" "$agent" && echo "  not-to-flag: OK" || echo "  not-to-flag: MISSING"
    grep -q "^## Focus Rules" "$agent" && echo "  focus-rules: OK" || echo "  focus-rules: MISSING"
done
```

**Step 2: Verify no lens overlap**

Check that no lens name appears in more than one agent's Key Lenses section. Extract lens names from each agent and compare:

```bash
for agent in agents/review/fd-{systems,decisions,people,resilience,perception}.md; do
    echo "=== $(basename $agent .md) ==="
    grep -E '^\d+\.' "$agent" | sed 's/^[0-9]*\. \*\*//' | sed 's/\*\*.*//'
done
```

Manually verify: no lens appears in two agents.

**Step 3: Commit all 4 new agents**

```bash
cd /root/projects/Interverse/plugins/interflux
git add agents/review/fd-decisions.md agents/review/fd-people.md agents/review/fd-resilience.md agents/review/fd-perception.md
git commit -m "feat(F1b): create 4 remaining cognitive review agents

Add fd-decisions, fd-people, fd-resilience, fd-perception. Each has 12 curated
lenses from Interlens's thematic frames, with no lens overlap between agents.

Bead: iv-lz3l"
```

---

## Task 6: Wire MCP Integration (F3)

**Files:**
- Modify: `plugins/interflux/agents/review/fd-systems.md`
- Modify: `plugins/interflux/agents/review/fd-decisions.md`
- Modify: `plugins/interflux/agents/review/fd-people.md`
- Modify: `plugins/interflux/agents/review/fd-resilience.md`
- Modify: `plugins/interflux/agents/review/fd-perception.md`

**Step 1: Add MCP section to each agent**

Insert the following section **before** `## Focus Rules` in each of the 5 lens agent files:

```markdown
## MCP Enhancement (Optional)

If the Interlens MCP server is available (tools like `search_lenses`, `detect_thinking_gaps` are listed in available tools), enhance your review:

1. **Per-section lens search**: For each section you review, call `search_lenses` with 2-3 keywords from that section to find relevant lenses beyond the hardcoded Key Lenses above
2. **Gap detection**: After completing your review, call `detect_thinking_gaps` with a summary of the lenses you applied to identify uncovered analytical frames
3. **Incorporate MCP results**: If MCP surfaces a lens not in your Key Lenses list that is clearly relevant, include it in your findings with a note: "Additional lens via MCP: {lens_name}"

**When MCP is unavailable** (tools not listed, or calls fail): Use the hardcoded Key Lenses above as your complete lens set. Include a NOTE finding at the end of your review:

> **NOTE**: MCP server unavailable — review used fallback lens subset ({N}/288 lenses). Install interlens-mcp for full coverage.

MCP is an enhancement, not a requirement. The hardcoded Key Lenses are sufficient for a thorough review.
```

**Step 2: Verify MCP section in all agents**

```bash
for agent in agents/review/fd-{systems,decisions,people,resilience,perception}.md; do
    grep -q "MCP Enhancement" "$agent" && echo "OK: $(basename $agent)" || echo "MISSING: $(basename $agent)"
done
```

**Step 3: Commit**

```bash
cd /root/projects/Interverse/plugins/interflux
git add agents/review/fd-*.md
git commit -m "feat(F3): wire Interlens MCP integration into lens agents

All 5 cognitive agents now have conditional MCP instructions: use search_lenses
and detect_thinking_gaps when available, fall back to hardcoded Key Lenses when not.

Bead: iv-3brk"
```

---

## Task 7: Verify Severity Guidance and Deduplication (F4)

**Step 1: Confirm severity guidance in all agents**

```bash
for agent in agents/review/fd-{systems,decisions,people,resilience,perception}.md; do
    grep -q "Blind Spot" "$agent" && grep -q "Missed Lens" "$agent" && grep -q "Consider Also" "$agent" \
        && echo "OK: $(basename $agent)" || echo "MISSING: $(basename $agent)"
done
```

All 5 agents should have identical Cognitive Severity Guidance sections (copied from fd-systems).

**Step 2: Verify synthesis deduplication awareness**

Check that `phases/synthesize.md` Step 3.3 already handles deduplication by section + agent. The existing dedup rule ("keep the most specific one") works for cognitive agents too. No changes needed to synthesis if the grouping already works by `(section, agent)`.

If synthesis needs a cognitive-specific note, add after the existing dedup bullet:

```markdown
- **Cognitive agent dedup**: When multiple cognitive agents flag the same section with similar reasoning, keep findings that reference different lenses as separate entries. Deduplicate only when the same lens AND the same concern appear from multiple agents.
```

**Step 3: Commit if changes made**

```bash
cd /root/projects/Interverse/plugins/interflux
git add skills/flux-drive/phases/synthesize.md
git commit -m "feat(F4): add cognitive agent deduplication guidance to synthesis

Lens-aware dedup: same lens + same concern → merge, same lens + different
concern → keep separate. Severity guidance already in all 5 lens agent prompts.

Bead: iv-03z2"
```

---

## Task 8: Update SKILL.md Triage (housekeeping)

**Step 1: Update cognitive filter for all 5 agents**

The cognitive filter in SKILL.md already lists all 5 agent names (fd-systems + "future cognitive agents: fd-decisions, fd-people, fd-resilience, fd-perception"). Now that the agents exist, update the wording from "future cognitive agents" to just list them:

In `skills/flux-drive/SKILL.md`, change:
```
fd-systems (and future cognitive agents: fd-decisions, fd-people, fd-resilience, fd-perception)
```
to:
```
fd-systems, fd-decisions, fd-people, fd-resilience, fd-perception
```

**Step 2: Commit**

```bash
cd /root/projects/Interverse/plugins/interflux
git add skills/flux-drive/SKILL.md
git commit -m "chore: update cognitive filter — agents now exist

Remove 'future' qualifier from triage pre-filter now that all 5 cognitive
agents are implemented.

Bead: iv-lz3l"
```

---

## Task 9: Validate on Test Documents

**Step 1: Run fd-decisions on the PRD**

Invoke fd-decisions (via general-purpose subagent with the full agent prompt) on `docs/prds/2026-02-15-interlens-flux-agents.md`.

Expected: 3-8 findings with P1-P3 severities, each referencing a specific section and a decision-quality lens.

**Step 2: Run fd-people on the brainstorm**

Invoke fd-people on `docs/brainstorms/2026-02-16-interlens-phase1-agents-brainstorm.md`.

**Step 3: Run fd-resilience on the plan**

Invoke fd-resilience on this plan file.

**Step 4: Run fd-perception on a third document**

Pick another doc from `docs/` and run fd-perception.

**Step 5: Evaluate**

At least 3/4 test runs should produce actionable findings. If not, iterate on the agent prompts.

---

## Task 10: Close Beads

**Step 1: Close all three beads**

```bash
bd close iv-lz3l  # F1b: Create remaining 4 agents
bd close iv-3brk  # F3: MCP wiring
bd close iv-03z2  # F4: Severity and deduplication
```

**Step 2: Verify interflux agent count**

```bash
ls /root/projects/Interverse/plugins/interflux/agents/review/*.md | wc -l
# Expected: 12 (7 technical + 5 cognitive)
```
