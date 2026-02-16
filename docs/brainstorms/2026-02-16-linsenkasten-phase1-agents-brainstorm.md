# Brainstorm: Interlens Phase 1 — Remaining Lens Agents + MCP + Severity
**Bead:** iv-lz3l (primary), iv-3brk, iv-03z2

## Context

Phase 0 is complete: fd-systems agent created, validated, triage pre-filter added. Phase 1 beads are unblocked (iv-lz3l's dependencies are all closed). This brainstorm covers the three remaining Phase 1 features:

- **F1b** (iv-lz3l): Create fd-decisions, fd-people, fd-resilience, fd-perception
- **F3** (iv-3brk): Wire Interlens MCP integration into lens agents
- **F4** (iv-03z2): Severity guidance and lens-aware deduplication

## What Exists

### Existing Template: fd-systems.md (108 lines)
- YAML frontmatter with name, description (2 examples), model: sonnet
- First Step (MANDATORY) — read project docs for codebase-aware mode
- Review Approach — 4 subsections (Feedback Loops, Emergence, Systems Dynamics, Unintended Consequences)
- Key Lenses — 12 curated from 288, with HTML comment explaining selection rationale
- Cognitive Severity Guidance — Blind Spot/Missed Lens/Consider Also → P1/P2/P3
- What NOT to Flag — defers to technical agents, excludes other cognitive domains
- Focus Rules — 5-8 findings, question-framed, section-specific

### Thematic Frames (28 frames, 288 lenses total)
fd-systems already covers: Core Systems Dynamics, Emergence & Complexity, parts of Resilience & Adaptation

### PRD Domain Mapping (F1b acceptance criteria)
- fd-decisions: Decision quality + uncertainty + paradox + strategic thinking
- fd-people: Trust + power + communication + leadership + collaboration
- fd-resilience: Resilience + innovation + constraints + creative problem solving
- fd-perception: Perception + sensemaking + time + transformation + information ecology

## Frame-to-Agent Mapping

### fd-decisions (Decision Quality Domain)
**Frames:** Strategic Decision Making (11), Navigating Uncertainty (17), Balance & Paradox (19)
**Total pool:** ~47 lenses → curate to 10-12
**Review focus:** Decision traps, cognitive biases, uncertainty handling, strategic paradoxes
**Key concepts:** Anchoring, framing effects, sunk cost, optionality, reversibility, OODA loops

### fd-people (Human Systems Domain)
**Frames:** Trust & Collaboration (28), Power & Agency (21), Communication & Dialogue (19), Leadership Dynamics (23), Organizational Culture & Teams (10), Network & Social Systems (9)
**Total pool:** ~110 lenses → curate to 10-12
**Review focus:** Trust dynamics, power structures, communication patterns, team culture, network effects
**Key concepts:** Psychological safety, authority gradients, Conway's Law, knowledge silos

### fd-resilience (Adaptive Capacity Domain)
**Frames:** Resilience & Adaptation (25), Creative Problem Solving (33), Boundaries & Constraints (19), Innovation & Creation (20), Innovation & Creative Destruction (10), Crisis & Opportunity (13), Resource Dynamics & Constraints (8)
**Total pool:** ~128 lenses → curate to 10-12
**Review focus:** Antifragility, creative constraints, resource allocation, innovation dynamics
**Key concepts:** Optionality, minimum viable, constraint-driven design, creative destruction

### fd-perception (Sensemaking Domain)
**Frames:** Perception & Reality (43), Knowledge & Sensemaking (15), Information Ecology (37), Time & Evolution (19), Temporal Dynamics & Evolution (7), Digital Transformation (14), Transformation & Change (44), Learning & Adaptation (29), Design & Detail (4)
**Total pool:** ~212 lenses → curate to 10-12
**Review focus:** Mental models, information quality, temporal reasoning, transformation patterns
**Key concepts:** Map vs territory, signal vs noise, paradigm shifts, temporal discounting

## Key Design Questions

### Q1: How to curate 10-12 lenses per agent from pools of 47-212?
**Approach:** Same criteria as fd-systems — select lenses that:
1. Form a complete analytical toolkit (not just "interesting" lenses)
2. Cover distinct failure modes (not redundant perspectives)
3. Are actionable in document review (not abstract philosophy)
4. Don't overlap with any other agent's key lenses

### Q2: How to structure MCP integration (F3)?
**Approach:** Conditional instructions in each agent prompt:
- If interlens MCP tools available → use `search_lenses` to find relevant lenses per section, use `detect_thinking_gaps` at end
- If MCP unavailable → fall back to hardcoded Key Lenses (the 10-12 curated ones)
- Emit a NOTE finding when using fallback: "MCP unavailable — review used fallback lens subset"

### Q3: How to handle severity deduplication (F4)?
**Approach:** The severity guidance already exists in fd-systems. For F4:
- Copy the same Cognitive Severity Guidance section to all 4 new agents (consistency)
- Deduplication happens in synthesis, not in individual agents — synthesis groups by `(lens_name, section, reasoning_category)` and keeps same-lens-different-concern as separate findings
- No code changes needed — this is prompt engineering in the synthesis step

### Q4: Should MCP integration be per-agent or shared?
**Per-agent.** Each agent has different search terms and different "relevant" lenses. fd-decisions searches for "decision uncertainty paradox", fd-people searches for "trust power communication". Shared MCP instructions would be too generic.

## Execution Strategy

**Critical path:** iv-lz3l (F1b) → then iv-3brk (F3) and iv-03z2 (F4) can run in parallel

**F1b execution order:**
1. Create all 4 agent files (parallelizable — no dependencies between them)
2. Validate agent count = 12 (7 existing + 5 lens agents)
3. Verify no lens overlap between agents

**F3 execution:** Add MCP conditional instructions to all 5 lens agents (fd-systems + 4 new)

**F4 execution:** Verify severity guidance in all 5 lens agents, add synthesis deduplication note

## Risk Mitigation

- **Lens overlap:** Use exact lens IDs from thematic frames JSON to verify no overlap
- **Quality parity:** Each new agent should match fd-systems' structure exactly — same sections, same tone, same focus rules
- **MCP graceful degradation:** Hardcoded lenses are the primary path; MCP is enhancement only
