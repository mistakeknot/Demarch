---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-03-29-reflect-compound-durable-changes.md"
target_description: "Design brainstorm for durable reflect/compound phases"
tracks: 4
date: 2026-03-29
---

# Synthesis: Reflect/Compound Durable Changes Review

16 agents across 4 tracks (adjacent, orthogonal, distant, esoteric) reviewed the brainstorm. This synthesis prioritizes findings that converged independently across tracks.

---

## Critical Findings (P0/P1)

### [P0] CLAUDE.md append is not idempotent — duplicates accumulate on re-runs

**Agents:** workflow-automation-idempotency (Track A)
**Track:** A (adjacent)

The reflect step's write to CLAUDE.md is described as "append." No upsert or content-addressable check exists. A session crash after write but before bead-close causes a re-run that duplicates the entry. Over months, near-duplicate entries accumulate from independently surfaced versions of the same lesson.

**Fix:** Before writing, grep the target for the core assertion. If a semantic match exists, update the existing entry (refresh date/context) rather than append. Require each routed entry to carry a unique identifier comment (e.g., `# [2026-03-29] binary-detection`) enabling exact-match dedup.

### [P0] CLAUDE.md has no capacity limit or consolidation trigger

**Agents:** spaced-repetition-decay (Track A), aviation-safety-crm (Track B), knowledge-management-sop (Track B), venetian-glassmaking (Track C), liturgical-calendar (Track C), tibetan-terma (Track D)
**Tracks:** A, B, C, D (4/4 convergence — see Cross-Track Convergence)

The brainstorm acknowledges bloat as an open question but provides no answer. At 3-5 sprints/week, CLAUDE.md accumulates 50+ append-only entries within 3 months. Attention density drops and later rules approach zero retrieval probability. The dead-file problem migrates from docs/reflections/ to CLAUDE.md.

**Fix:** Define a hard line budget per CLAUDE.md section (max 8-10 entries). Any append beyond the cap triggers a consolidation pass that merges duplicates, promotes enforceable rules to hooks, and archives stale entries. Add a periodic review cadence tied to the sprint lifecycle (every 5-10 sprints).

### [P0] No post-write verification — the gate checks metadata, not content

**Agents:** aviation-safety-crm (Track B), construction-commissioning (Track B), retrospective-facilitation (Track A)
**Tracks:** A, B (2/4 convergence)

Option B's durable change gate checks "at least 1 file outside docs/reflections/ was modified." This verifies a write was attempted, not that the content is correct. A malformed append (wrong section, inside a code block, truncated) passes the gate. Aviation calls this "paper closure without physical inspection."

**Fix:** After each write, read back the specific content and verify: (1) it appears verbatim, (2) exactly once, (3) in the correct section and not inside a fenced code block. Log verification result. Verification failure reopens the item.

### [P1] Procedural learnings default to CLAUDE.md instead of hooks — the enforcement gap

**Agents:** venetian-glassmaking (Track C), aviation-safety-crm (Track B), clinical-quality-improvement (Track B), wayfinding-polynesian-navigation (Track C), spaced-repetition-decay (Track A)
**Tracks:** A, B, C (3/4 convergence)

Learnings like "close child beads when parent ships" are behavioral rules enforceable at the moment of action. Routing them to CLAUDE.md (a passive-load document) instead of a hook (an active enforcement) means the rule is loaded at session start and forgotten by the time the action occurs. The path of least resistance is always CLAUDE.md because it requires no code.

**Fix:** Add an explicit classification gate: "Is this enforceable by code at the moment the mistake would occur? If yes, classify as `hook` or `code` regardless of simplicity. Only classify as `claude-md` if enforcement is not feasible." Make `hook` the default for anything phrased as "always do X when Y."

### [P1] No repeat-finding escalation — recurring learnings get re-routed without investigation

**Agents:** aviation-safety-crm (Track B), clinical-quality-improvement (Track B), zettelkasten-link-density (Track A)
**Tracks:** A, B (2/4 convergence)

The evidence table already shows repeated learnings ("close child beads"). The router will route them again each time they surface. No mechanism detects that a learning was previously routed and the route apparently failed. Aviation escalates repeat findings to systemic investigation; this design just re-appends.

**Fix:** Before routing, search CLAUDE.md git history and MEMORY.md for the learning's topic. If a match exists, flag as "REPEAT FINDING" and create a bead for systemic investigation rather than appending another line.

### [P1] No root-cause vs. symptom classification — learnings default to the softest target

**Agents:** clinical-quality-improvement (Track B), retrospective-facilitation (Track A), lichen-symbiont-memory (Track D)
**Tracks:** A, B, D (3/4 convergence)

The routing taxonomy classifies by target type, not by depth. "Close child beads when parent ships" routed to CLAUDE.md is symptom-level (remind the agent). A hook on `bd close` is root-cause level (enforce the check). Without a root-cause question, learnings default toward advisory targets. The lichen agent frames this as "overlay vs. substrate modification" — comments describe the problem, structural code changes prevent it.

**Fix:** Add a root-cause question before routing: "Is this a behavioral reminder (symptom) or a systemic gap (root-cause)?" Symptom-level goes to claude-md/memory. Root-cause goes to hook/code. For code-level learnings, explicitly prefer structural changes (fix the code) over code comments (describe the fix).

### [P1] No specificity gate — vague learnings pass classification and pollute targets

**Agents:** retrospective-facilitation (Track A), aviation-safety-crm (Track B), edo-metsuke (Track D)
**Tracks:** A, B, D (3/4 convergence)

The brainstorm identifies "learnings are too generic" as a failure mode but the router has no quality gate on the learning itself before routing. "Plan more carefully for large refactors" passes classification and lands in CLAUDE.md as unactionable noise.

**Fix:** Each learning must pass a when/where/what test: "When [trigger], do [action] in [location] because [consequence]." Learnings that fail are refined, not routed.

### [P1] Code-comment placements are undiscoverable — no catalog or index

**Agents:** tibetan-terma (Track D), wayfinding-polynesian-navigation (Track C), typographic-marginalia (Track C)
**Tracks:** C, D (2/4 convergence)

Learnings routed to code comments at point-of-use are only discoverable by re-encountering that exact file. An agent debugging a related problem in a different file has no way to know the knowledge exists. The brainstorm replaces one set of dead files with scattered, uncataloged inline annotations.

**Fix:** Every code-comment or hook placement must append a structured entry to a fixed-location index file (e.g., `docs/learnings-index.jsonl`) with fields: date, learning summary, target file, target symbol, retrieval condition. The audit log in Option E must be mandatory, not optional.

### [P1] No deferred-learning mechanism — items that cannot be implemented immediately are lost

**Agents:** construction-commissioning (Track B), clinical-quality-improvement (Track B)
**Tracks:** B

A learning routed to `code` in os/Clavain/ during a session focused on apps/Autarch/ cannot be implemented. No deferral mechanism exists. The learning falls out of the session without record. Construction commissioning calls these "warranty items" — tracked, assigned, not lost.

**Fix:** Introduce a `deferred` routing status. When a code/hook learning cannot be implemented in the current session, create a bead with the learning content and target, record the bead ID in the audit log. Surface deferred items at next sprint start.

---

## Cross-Track Convergence

Findings ranked by convergence score (number of independent tracks that surfaced the same issue).

### 4/4: CLAUDE.md bloat / capacity limits / periodic review

- **Track A:** spaced-repetition-decay — frames as attention-window competition; P(retrieval|need) drops toward zero as line count grows
- **Track B:** aviation-safety-crm — frames as checklist fatigue; compliance drops beyond cognitive bandwidth; knowledge-management-sop — frames as SOP without content owner or pruning governance
- **Track C:** liturgical-calendar — frames as loss of re-encounter; entries become "liturgically inaudible" background noise; venetian-glassmaking — frames as undifferentiated text that masters skim past
- **Track D:** tibetan-terma — frames as dgongs gter overload; all knowledge loaded into mindstream with no location-anchored alternative

Every track independently concluded that CLAUDE.md as an append-only sink will reproduce the dead-file problem at a higher-stakes location. The convergent fix: capacity limits per section, mandatory periodic review tied to sprint cadence, and a structural distinction between universal principles (CLAUDE.md) and location-specific knowledge (code comments).

### 3/4: Procedural learnings belong in hooks, not CLAUDE.md

- **Track A:** spaced-repetition-decay — frames as retrieval-priority mismatch; hooks have P(retrieval|need) near 1.0, CLAUDE.md does not
- **Track B:** aviation-safety-crm — frames as advisory vs. mandatory corrective action; clinical-quality-improvement — frames as symptom-level vs. system-redesign intervention
- **Track C:** venetian-glassmaking — frames as furnace geometry vs. written manual; wayfinding — frames as harbor-placard knowledge vs. at-sea knowledge

The convergent insight: the brainstorm's taxonomy treats all six targets as peers, but they are not equivalent. Hooks enforce; CLAUDE.md advises. Learnings phrased as "always X when Y" are enforcement candidates and should default to hooks.

### 3/4: Specificity and root-cause depth required before routing

- **Track A:** retrospective-facilitation — when/where/what test
- **Track B:** aviation-safety-crm — corrective action specificity; clinical-quality-improvement — symptom vs. root-cause classification
- **Track D:** edo-metsuke — directive ambiguity produces inconsistent enforcement; lichen-symbiont — overlay vs. substrate distinction

The convergent insight: the brainstorm solves placement but not content quality. Routing a vague or symptom-level learning to a durable target just makes it durably vague.

### 3/4: Stale entries and expiration — knowledge without lifecycle management

- **Track A:** institutional-memory-erosion — entries reference fixed bugs, removed features, changed APIs
- **Track C:** liturgical-calendar — entries outlive their instructive function; typographic-marginalia — file references go stale when code moves
- **Track D:** tibetan-terma — concealment decay; no relevance conditions on placed knowledge

The convergent insight: the brainstorm designs knowledge placement without knowledge retirement. Stale entries are more harmful than absent entries because they carry false authority.

### 2/4: Post-write verification needed

- **Track A:** retrospective-facilitation — formatting and placement errors
- **Track B:** aviation-safety-crm — inspector sign-off; construction-commissioning — physical inspection vs. paper closure

### 2/4: Code-comment and hook placements need a discovery index

- **Track C:** wayfinding — practice-embedded knowledge invisible during audit; typographic-marginalia — commentary separated from text
- **Track D:** tibetan-terma — kha byang (prophetic catalog) required for sa gter (earth-treasure) retrieval

### 2/4: Escape hatch will be gamed without calibration

- **Track B:** workflow-automation-idempotency — bypass culture pattern
- **Track D:** edo-metsuke — inspection fatigue drives metsuke-bypass; liturgical-calendar — lower-friction exit becomes default path

---

## Domain-Expert Insights (Track A)

**spaced-repetition-decay** produced the clearest model of the retrieval problem: CLAUDE.md entries have exactly one retrieval opportunity per session (system prompt processing). Context-triggered learnings that need to fire at a specific workflow moment (e.g., ship-time, triage-time) will never fire from a passive-load target. The fix — a "trigger context" field in classification that routes context-dependent learnings to hooks — is the most operationally specific recommendation from any agent.

**zettelkasten-link-density** surfaced the atomicity constraint: compound learnings ("sprint planning needs better scope control") cannot be partially deprecated. If a learning contains "and" joining two insights, it must be split before routing. Also identified cross-target duplication as a first-order problem: the same learning existing in CLAUDE.md, a memory file, and a code comment — all slightly different, none authoritative.

**institutional-memory-erosion** uniquely identified model-dependency risk: learnings that implicitly assume current model behavior (context window size, attention patterns) will go stale on model transitions without any signal. Tagged `model-context` entries enable systematic re-evaluation during upgrades.

**workflow-automation-idempotency** identified configuration drift between router-written and manually-written CLAUDE.md entries. The fix — a designated `## Learned Rules` section for router output, separate from hand-maintained content — prevents interleaving conflicts.

**retrospective-facilitation** recommended a hard cap of 3 routed learnings per session, citing retro research that >5 action items per session results in none being completed well.

---

## Parallel-Discipline Insights (Track B)

**aviation-safety-crm** delivered the strongest P0: the `memory` target in the routing taxonomy is advisory, not behavioral. Routing a recurring mistake to memory is the equivalent of "noting" a safety finding without corrective action. The fix — splitting `memory` into `memory:advisory` and flagging recurring mistakes as requiring `hook` or `claude-md` — adds a critical safeguard.

**clinical-quality-improvement** introduced severity and preventability as missing classification dimensions. Not all learnings are equivalent: a session-corrupting dispatch bug and a regex edge case should not get the same routing treatment. High-severity learnings should create a bead in addition to the durable change, tracking whether the underlying issue was actually fixed.

**construction-commissioning** contributed the strongest operational pattern: individual learning tracking. Each extracted learning needs a stable identity (sprint-scoped index) and individual status tracking through the lifecycle (classified, routed, written, verified). Batch processing loses all items on a single write failure.

**knowledge-management-sop** identified the taxonomy gap problem: the six-category taxonomy was derived from 18 existing files. Novel learning types that do not fit will be force-fitted. A `taxonomy-gap` escape hatch that routes to a staging file for human review prevents miscategorization.

---

## Structural Insights (Track C)

**venetian-glassmaking** produced the most direct metaphor for the core problem: routing "close child beads when parent ships" to CLAUDE.md is writing the furnace temperature limit in a manual rather than encoding it in the furnace chamber geometry. The manual can be ignored; the geometry cannot. This frames the entire brainstorm as solving a documentation problem when it should solve an enforcement problem.

**wayfinding-polynesian-navigation** introduced context-injection hooks as a missing target type. Current taxonomy has `hook` (enforcement) but not `hook:context-inject` (surface relevant knowledge at the moment of relevant action without blocking). "Triage should check git history for open beads" should fire as a context injection when triage begins, not sit in CLAUDE.md as permanent background.

**typographic-marginalia** contributed the palimpsest risk: if two sprints produce learnings about the same function, the second write may overwrite the first annotation. Code comments must always append (with dates), never replace. Also identified gloss density limits — a function with 15 comment lines and 8 code lines has become its own commentary.

**liturgical-calendar** reframed the escape hatch: instead of "no actionable learnings" (a negative assertion easy to game), require a positive assertion: "the following existing entries were confirmed accurate this sprint." This turns zero-learning sprints into positive confirmation passes rather than exits.

---

## Frontier Patterns (Track D)

**lichen-symbiont-memory** delivered the most structurally novel finding: the brainstorm's entire target taxonomy consists of removable overlays (text files, JSON configs, comments). If someone stripped all router-written content, codebase behavior would be unchanged. The lichen's bioweathering IS the knowledge — it modifies the substrate. A `structural-code-change` target (refactor the code so the mistake is architecturally prevented) is categorically stronger than any documentary target and should be first-class in the taxonomy.

**tibetan-terma-concealment** introduced the kha byang (prophetic catalog) pattern: earth-treasures (sa gter) placed in code files without a discovery catalog are unfindable. The audit log is the kha byang — it must be mandatory, not optional, and must include retrieval conditions. Also introduced confidence classification (validated/provisional/hypothesis) to prevent misdiagnosed learnings from being placed as authoritative knowledge.

**edo-metsuke-surveillance** framed the entire brainstorm as "sankin-kotai without metsuke" — presence is required (CLAUDE.md loads every session) but compliance is voluntary (no verification that rules influence behavior). The smallest viable metsuke: annotate new entries with `# verify-by: <sprint-id>` and have `/doctor` surface unverified entries. Also identified that hook-class placements need higher governance standards than memory-class placements — a bad hook can halt the entire workflow.

---

## Synthesis Assessment

### Highest-leverage improvement

Add a root-cause/enforcement classification gate to the router prompt. One sentence: "If this learning can be enforced by a hook or code change at the moment the mistake would occur, route it there — not to CLAUDE.md." This single gate addresses the most convergent finding (3/4 tracks), prevents CLAUDE.md bloat (4/4 tracks), and shifts the system from documentation-first to enforcement-first. It requires no code changes — just a prompt modification to the reflect command.

### Surprising finding

The lichen-symbiont agent's observation that none of the brainstorm's targets produce irreversible behavioral change. Every proposed target — CLAUDE.md, hooks, memory, code comments — is a removable overlay. The brainstorm never asks: "Can the code be changed so this class of mistake is structurally impossible?" Adding `structural-code-change` as a first-class routing target reframes the entire system from "where do we document learnings" to "how do we prevent the failure class." No inner-track agent (A or B) surfaced this distinction — they accepted the brainstorm's premise that documentation-level targets were the design space.

### Semantic distance value

The outer tracks (C/D) contributed qualitatively different insights from inner tracks (A/B). Tracks A and B operated within the brainstorm's framing: improve the router, add gates, manage capacity. Tracks C and D challenged the framing itself:

- **Track C** contributed context-injection hooks (wayfinding), append-not-replace semantics (marginalia), and the furnace-geometry-vs-manual distinction (venetian) — all structural patterns that reframe the problem from "better documentation" to "better enforcement."
- **Track D** contributed the overlay-vs-substrate distinction (lichen), the mandatory discovery catalog (terma), and the compliance-verification layer (metsuke) — all meta-patterns about knowledge durability that no domain expert would surface because they accept documentary knowledge as the natural output form.

The 4/4 convergence on CLAUDE.md bloat validates inner-track findings. But the outer-track insight that the entire design space is overlays — and that structural code changes are categorically stronger — is the finding that most changes the design direction. Semantic distance paid for itself.
