# Intercom Vision — Architecture Review

**Date:** 2026-02-22
**Reviewer:** Flux-drive Architecture & Design Reviewer
**Document reviewed:** `/home/mk/projects/Demarch/apps/intercom/docs/intercom-vision.md` v0.1
**Context docs:** `docs/demarch-vision.md` v3.0, `apps/autarch/docs/autarch-vision.md` v1.1
**Codebase:** `/home/mk/projects/Demarch/apps/intercom/` (NanoClaw, current state)

---

## Summary

The Intercom vision is structurally sound at the macro level. Its three-horizon evolution plan has the right instinct — each horizon delivers standalone value — and the "Translate, don't duplicate" design principle is the correct anchor for a module that bridges two existing systems. The most significant structural problem is the Q1 option analysis (Open Question 1), which presents four options without resolving the one that has the highest architectural leverage. The Layer 2.5 framing is a useful diagnostic but names the wrong thing: the issue is not what layer Intercom occupies today, but what boundary conditions would force a layer promotion, and those conditions are not yet defined with enough precision to be actionable. The horizon boundaries mostly hold, but there is one hidden dependency between H1 and H2 that would force early investment if H2 is to ship without re-engineering H1's tool layer.

---

## 1. Boundaries and Coupling

### Q1 Option Analysis: Container Access to the Kernel

The vision identifies this as Open Question 1 and lists four options without evaluating them architecturally. This is the most consequential design decision in H1 and deserves resolution before implementation begins. Each option has a fundamentally different coupling profile.

**Option A: Mount the `ic` binary read-only into the container**

This is the lowest-friction path for H1 read-only queries and the one implied by the vision's tool descriptions (`demarch_run_status → ic run current/status --json`). The coupling profile is direct: the container binary-depends on a specific version of `ic`, its CLI interface, its output format, and its JSON schema. Any breaking change to `ic run current --json` fields silently breaks the Demarch toolkit.

The deeper problem is that the `ic` binary is a local SQLite client. Mounting it into a container does not give it access to the database unless the database path is also mounted. The vision does not address which database the tool queries. For a "main group" container that has the project root mounted at `/workspace/project`, the database is accessible. For any other group, it is not. This creates a topology gap that is invisible in the option description but would surface immediately in H1 implementation: the Demarch toolkit only works for main-group conversations.

Blast radius: low for H1 if topology gap is accepted; medium if database access needs to expand to non-main groups (requires a mount strategy that affects every group's security model).

**Option B: IPC bridge through the host**

The vision already uses filesystem-based IPC for agent-to-host communication (`container/shared/ipc-tools.ts`). Extending this to agency queries is architecturally consistent — the container writes an intent file, the host process executes the `ic` command and writes the result back. This keeps all `ic` execution on the host, where the database is available, and keeps the container's execution surface narrow.

The cost is latency (two filesystem round-trips per query) and serialization design (request/response correlation over files is more complex than the current fire-and-forget IPC). However, this option has the strongest coupling properties: the container never depends on `ic` directly, the host is the sole `ic` executor, and adding H2 write operations (demarch_create_issue, demarch_approve_gate) follows the same pattern with no new security surface.

This is the structurally preferred option. The vision already endorses it for H2 write operations ("The container agent doesn't call `ic` directly — instead, it writes an IPC intent file, and the host process validates and executes it. This preserves the security boundary."). Option B simply applies this same discipline to H1 read operations, making the H1/H2 surface uniform rather than split.

**Option C: HTTP API on the host that containers can call**

This introduces a persistent server process — either embedded in the host or as a sidecar. The NanoClaw host is currently a Node.js process with no HTTP server. Adding one for container queries creates a new attack surface (any container can call any endpoint if network isolation is not explicitly configured), requires container network-to-host routing (which varies between Docker on Linux, Docker Desktop, and Podman), and adds a new failure mode: the API server can be up while the host process is degraded, or vice versa.

The practical overhead of HTTP for local IPC is not justified by the read-only use case. HTTP would be appropriate if Intercom were exposing queries to external consumers. For container-to-host communication where filesystem IPC already exists and works, adding HTTP is accidental complexity.

Option C should be rejected for H1. It belongs in a different category: if Demarch ever exposes an HTTP API to external consumers (not in scope for any horizon in this vision), that is a separate module concern, not Intercom's.

**Option D: Pre-populated state snapshot**

This is the only option that avoids all runtime coupling. Before spawning a container, the host queries kernel state, serializes it to a JSON snapshot, and mounts it read-only into the container. The Demarch toolkit reads from this file, not from `ic`.

The fatal flaw is staleness. A container that runs for 30 minutes (the configured idle timeout) with a state snapshot from spawn time will serve increasingly stale answers. A user asking "what's the current sprint phase?" at minute 28 gets data from minute 0. For static artifacts (spec documents, verdict files, research), staleness is acceptable. For live run state (phases, dispatches, events), it is not.

Option D is viable as a complement to Option B (pre-populate read-heavy static data at spawn, use IPC for live queries) but not as a standalone solution for the full Demarch toolkit.

**Recommendation:** Use Option B for all live kernel queries (run status, sprint phase, dispatch state, events). Use Option D as a performance optimization for static artifacts that do not change during a container's lifetime (spec artifacts, research findings, Interflux verdict files). Option A should be rejected — it creates a database topology gap and binary coupling. Option C should be rejected — it adds an HTTP server where filesystem IPC already exists.

This is not a significant implementation burden. The IPC extension for query/response correlation (a request UUID written to the intent file, the host writes the response to a per-UUID response file) is a small addition to the existing `ipc.ts` infrastructure.

### H1 to H2 Hidden Dependency: The IPC Request/Response Correlation Problem

The vision describes H1 tools as "thin wrappers that call existing CLIs" and H2 as "intent submission via IPC." But these are not actually two different mechanisms — they are the same mechanism at different privilege levels. H1 read queries through IPC require the same request/response correlation infrastructure as H2 write intents. If H1 is implemented with Option A (binary mount) and H2 is implemented with Option B (IPC bridge), the codebase ends up with two different tool invocation paths that must both be maintained as new tools are added.

This is the hidden dependency: H2's IPC write model requires building the correlation infrastructure that H1 also needs if it is going to use Option B. Choosing Option B for H1 means building the correlation machinery once in H1, which H2 then extends. Choosing Option A for H1 means H2 will need to refactor H1's tool layer when the IPC bridge is added — the "degrade gracefully" principle is satisfied for end-users, but not for the implementation.

The vision should be updated to make this explicit: Option B for H1 reads is not just architecturally cleaner, it is prerequisite infrastructure for H2 that gets amortized over H1 development.

### Integration Map Coupling Assessment

The integration map lists 19 integration points across 16 modules. Several of these have coupling risks worth flagging:

**Clavain "Write" (H2): Intent submission: start sprint, advance phase.** The vision correctly identifies that Intercom should not call kernel primitives directly for policy-governing operations and should instead route through Clavain. The current write-path contract in the Autarch vision describes four intent types (start-run, advance-run, override-gate, submit-artifact). Intercom's H2 intent submission should reuse these same intent types rather than defining its own. If Intercom defines `demarch_start_run` as an IPC intent that the host maps to `ic run create` directly (bypassing Clavain), it violates the write-path contract that Autarch apps are being migrated toward. The vision should be explicit: Intercom's H2 write path goes through Clavain's CLI, not directly to `ic`.

**Beads "Write" (H2): bd create, bd close from chat-initiated work.** Beads sit outside the kernel write-path contract described in the Autarch vision (the four Autarch intents do not include bead operations). The vision does not clarify whether bead writes from Intercom route through Clavain (as `bd` calls on the host after IPC) or through some future Interbus intent. This is a coupling question that should be resolved in H2 planning: does every write that Intercom initiates go through Clavain's policy layer, or are some writes considered "safe enough" to execute directly?

**Interbus (H3): "Both" direction.** Interbus is listed as a bead (`iv-psf2`) — it does not exist yet. The H3 architecture diagram shows Intercom with an `Interbus subscriber` component, but if Interbus is not available by the time H3 is planned, H3's event delivery model falls back to direct module polling (the same polling pattern described in H2's event bridge). The vision should acknowledge this dependency and describe the H3 fallback if Interbus remains unbuilt.

**Intermute (H3): "Both" directions.** Intermute is a Go service (`core/intermute/`). Intercom (Node.js) would need a client integration. This is not mentioned in the vision and represents a language-boundary crossing that requires a decision: HTTP, gRPC, or some other IPC mechanism. The vision should not assume this is straightforward.

---

## 2. Pattern Analysis

### The Autarch Contract Violation Is Deliberate and Should Be Named

The vision notes that Intercom "breaks the Autarch contract in a fundamental way" and correctly identifies the specific violations: execution environment, dispatch model, persistence, agent lifecycle. But it presents this as an observation rather than a design decision. This matters because the Autarch vision is actively migrating Gurgeh and Coldwine toward the "apps are swappable" contract, and Intercom is moving in the opposite direction — adding runtimes, channels, and swarm coordination.

The correct framing is: Intercom is an Autarch app in location (`apps/`) but not in contract. This should be stated explicitly in the vision rather than as a footnote in the "Architectural Positioning" section. The practical consequence is that no shared component library (`pkg/tui` in Autarch's case) will emerge from Intercom unless its execution model is explicitly factored — and there is no indication this is planned.

This is not a problem to fix, but it is a boundary condition to name: Intercom should not be expected to conform to Autarch's "swappable" contract, and future work in the Autarch direction (shared components, intent submission APIs) should not be designed with Intercom as a target consumer unless the messaging/container execution layer is explicitly scoped out.

### Write-Path Discipline Needs an Explicit Rule

The Autarch vision defines a write-path contract: apps do not call kernel primitives directly for policy-governing operations. They submit intents to the OS. The Intercom vision endorses this principle in the H2 description ("The container agent doesn't call `ic` directly") but does not extend it to a rule that covers all of Intercom's host-level operations.

Consider: the H2 event bridge ("Poll ic events tail --consumer=intercom") is a direct kernel read. The H1 tools call `ic run current/status --json` directly (if Option A is chosen). Are these write-path violations? No — reads are explicitly exempt from the Autarch write-path contract. But the vision should state this clearly, because as H2 write capabilities are added, the line between "read from ic" and "write through Clavain" will be crossed frequently and inconsistently without an explicit rule.

The rule the vision should encode: all kernel reads (ic run, ic dispatch, ic events) are permitted at the host level without routing through Clavain. All kernel writes that have policy implications (run creation, phase advancement, gate override, artifact registration) route through Clavain. Bead operations are explicitly categorized (are they policy-governing or not?). This rule, stated once in the vision, prevents H2 implementation from making inconsistent choices tool by tool.

### Naming: Demarch Toolkit

The vision proposes a "Demarch toolkit" as the set of agent tools that bridge to kernel state. This name has a coupling risk: if the toolkit is scoped to the Demarch platform rather than to the Intercom host's integration surface, it implies external consumers might use it. In practice, the toolkit is Intercom-specific (it routes through Intercom's IPC bridge, not through any public interface). Naming it the "Intercom toolkit" or "agency toolkit" avoids implying external reusability that is not planned. This is a minor naming point but it reflects the vision's correct "translate, don't duplicate" principle: the toolkit translates for Intercom's conversational context, not for general programmatic access.

---

## 3. Simplicity and YAGNI

### Horizon 1 Is the Right Scope for Q1

The H1 implementation is appropriately scoped. Seven tool types covering the most common queries, all implemented as thin CLI wrappers. No new persistence, no new protocol, no new infrastructure beyond the IPC extension. The vision does not over-specify H1 — it names capabilities without prematurely locking in implementation patterns. This is correct for a brainstorm-grade document.

The one YAGNI risk in H1 is the "research on demand" capability (`demarch_research → Pollard query or future Interbus discovery.query intent`). This conflates two different integration surfaces (Pollard's current API versus a future Interbus intent that does not exist). For H1 implementation, this should be scoped to whichever surface actually exists: either Pollard's current output format or the kernel's discovery index, not both and not a future one. The vision's hedging here ("or future Interbus") creates implementation ambiguity that will cause unnecessary design discussion when H1 is planned.

### H3 Capabilities Are Too Early to Specify

The H3 section describes role-based access, cross-channel continuity, multi-agent delegation via Intermute, scheduled reporting, and Interfluence voice adaptation. These are five distinct capability tracks, each with significant implementation depth. Specifying them in the same document as H1 (which has near-term implementation intent) creates a risk: teams may design H1 components to accommodate H3 requirements that are speculative.

Specifically: the H3 diagram shows `Swarm coordinator` and `Synthesis pipeline` inside the Container Orchestrator. If these are designed into H1's container orchestration layer (even as empty stubs), they add complexity that serves no H1 or H2 consumer. The vision's own principle ("Degrade gracefully — each horizon adds capability but none are prerequisites") argues against designing for H3 during H1 implementation.

The recommendation is not to remove H3 from the vision — it is appropriate brainstorm-grade content. The recommendation is to add a boundary statement to the H3 section: H3 does not influence H1 or H2 design decisions. No H1 or H2 component should be designed to accommodate H3 requirements.

### H2 Event Bridge: Polling vs. Push

The H2 event bridge ("Poll ic events tail --consumer=intercom") is described as a simple polling loop. The vision also raises this as Open Question 2 ("should Intercom use Autarch's signal broker pattern, or is a simple poll loop sufficient?"). The Autarch vision explicitly classifies the signal broker as a "rendering optimization" that is optional and removable: "If the signal broker is removed entirely, the system works identically — TUI updates are slightly slower."

For Intercom's event bridge, the stakes are slightly different: users in Telegram or WhatsApp are expecting near-real-time notification of significant events (phase advances, budget alerts, review completions). A 5-second poll interval is probably acceptable for these event types — they are not rendering at 60 fps. The simple poll loop is sufficient for H2. The signal broker pattern adds complexity that Intercom does not need until the event volume is large enough that a single consumer cursor per event type becomes a bottleneck.

Open Question 2 should be closed: use the simple poll loop for H2. Revisit if event volume or latency requirements change in H3.

---

## 4. The Layer 2.5 Framing

The vision proposes that Intercom might eventually occupy a "Layer 2.5" position between the OS and the apps. This is a useful diagnostic — it captures the correct intuition that Intercom is not a pure rendering surface — but the framing has two problems.

**Problem 1: "Layer 2.5" is an informal classification that does not map to the formal layer model.**

The three-layer model (L1 kernel, L2 OS + drivers, L3 apps) is defined by survival properties and dependency direction:
- L1 (Intercore): survives if everything above it is replaced
- L2 (Clavain + Interverse): opinions survive even if the host platform changes; UX adapters are rewritten
- L3 (Autarch): survives being replaced entirely — the kernel and OS are unaffected

A "Layer 2.5" does not have a defined survival property. If Intercom were promoted, what would survive? If Intercom is replaced, does anything break that is not in L3? Today, no. In H3 (if Clavain routes gate-approval requests through Intercom), yes — removing Intercom would break gate approval workflows. That is the actual threshold condition for promotion: another L2 module depends on Intercom as infrastructure.

**Problem 2: The framing is premature given where the three horizons actually land.**

H1 and H2 do not change Intercom's dependency profile. Nothing in L1, L2, or the other L3 apps depends on Intercom after H1 or H2. Intercom gains read and write access to the kernel, but no other module depends on it. H3 is where the inflection point might occur — specifically, if Clavain sends gate-approval requests through Intercom, or if Interflux routes review summaries through Intercom. The vision identifies this correctly: "The answer changes if Intercom evolves into a communication substrate."

**Better framing:**

Rather than "Layer 2.5," the vision should define the promotion criteria explicitly:

> Intercom remains a Layer 3 app until at least one of the following conditions is met:
> (a) Another Layer 2 module (Clavain, an Interverse driver) has a hard dependency on Intercom for a production workflow
> (b) Intercom's removal would break a workflow that does not involve a messaging channel
>
> Until then, Intercom lives under `apps/` regardless of its internal complexity. Complexity within a layer boundary is not grounds for promotion.

This is more useful than "Layer 2.5" because it gives the team a concrete decision gate: when condition (a) or (b) is met, evaluate promotion. Before that, do not promote.

---

## 5. Horizon Boundary Evaluation

### H1 Boundaries: Clean

H1 is read-only, container-scoped, and does not require new persistence, new event subscriptions, or new protocol surfaces at the host level. The only extension needed is IPC query/response correlation (if Option B is chosen). The boundary is clean.

One naming clarification: the vision says the H1 toolkit "works in all three runtimes (Claude, Gemini, Codex) because they're implemented in the shared container code." This is correct for the Gemini and Codex runtimes, which use the shared `executor.ts` tool execution layer. For the Claude runtime (Claude Agent SDK), tool implementation is different — Claude uses MCP tools, not the shared tool executor. The H1 toolkit description should clarify whether the Demarch toolkit tools are implemented in `container/shared/` (covering Gemini and Codex) or also in the Claude runtime's MCP tool layer. If only shared code, the Claude runtime needs additional work.

### H2 Boundaries: One Structural Risk

H2 adds two new surfaces: intent submission from containers, and event subscription at the host. Both are well-described. The structural risk is in the event bridge's consumer identity.

The vision specifies: "Poll ic events tail --consumer=intercom." The `--consumer` flag maintains a cursor position in the kernel event log so each consumer reads each event exactly once. This is correct. But the vision does not address what happens when multiple Intercom instances run (e.g., in development, or if horizontal scaling is ever considered). Two processes sharing the same consumer cursor will each receive only half the events. The vision should note that the event bridge consumer cursor is a singleton resource and that only one Intercom host process should own it at any given time. This is a simple constraint to state, but it affects deployment topology.

### H2 to H3 Dependency on Interbus

H3 is explicitly described as building on "the Interbus integration mesh (bead iv-psf2)." If Interbus is unbuilt when H3 is planned, H3's multi-module event subscription falls back to direct module polling — the same pattern as H2's event bridge, extended to more sources. This is fine, but the vision should not describe H3 as requiring Interbus. The correct framing is: H3 uses Interbus if available, direct polling if not. H3 capabilities (role-based access, cross-channel continuity) do not inherently require a message bus — they require coordination, which can be achieved through polling with slightly higher latency.

---

## 6. Open Questions Assessment

The vision lists six open questions. One above (Q2: event delivery latency) has been addressed. Assessments for the remaining five:

**Q1: Container access to kernel.** Addressed in Section 1 above. Resolution: Option B for live queries, Option D for static artifacts. Close this question before H1 implementation begins.

**Q3: Multi-user identity.** The correct answer is Intercom's own database, not Intermute. Intermute coordinates agents, not human users. Intercom already has a SQLite database with group and session tables — user identity (a mapping from messaging JID to user profile, role, and preferences) belongs there. Intermute would only be involved if Intercom needs to coordinate with other agents about a specific user's request, which is an H3 concern.

**Q4: Gate approval UX.** This is a UX question, not an architecture question. The architecture constraint is that gate approval goes through the write-path contract (IPC intent → host → Clavain → ic gate override). The UX mechanism (inline buttons, reply keyword, timeout handling) is an implementation detail that Telegram's Grammy library and WhatsApp's Baileys library handle differently. This question belongs in H2 planning, not in the vision.

**Q5: Interbus vs. direct integration for H2.** Resolution: proceed with direct `ic` calls for H2 and retrofit to Interbus if/when it exists. The write-path contract (Clavain as the policy gate for mutations) must be maintained regardless of whether Interbus exists. The retrofit cost is adding an Interbus client at the host level and replacing direct `ic` calls with bus intents — this is a host-level change that does not affect the container toolkit.

**Q6: Token attribution.** This is a real architectural question without an obvious answer. The correct framing is: Intercom conversations and kernel runs are different cost units and should not be conflated. An Intercom agent that queries kernel state is spending tokens that belong to the Intercom conversation, not to the kernel run being queried. If the user asks "what is the sprint status?" and the agent calls `demarch_run_status`, the tokens spent answering that question are Intercom's cost, not Intercore's. The kernel run's token budget should only be debited when Intercom directly contributes work to a run (e.g., submitting a human approval that advances a phase). This distinction should be stated in the H2 budget alerts section, because the alerts themselves will need to know which budget they are reporting on.

---

## Must-Fix Before H1 Implementation

1. **Resolve Q1 (container kernel access) as Option B + Option D.** Do not begin H1 implementation until the IPC query/response correlation mechanism is designed. If Option A is chosen instead, document the database topology gap explicitly and accept that Demarch toolkit tools only work in main-group conversations.

2. **State whether the H1 Demarch toolkit covers the Claude runtime.** The Claude runtime uses MCP tools, not the shared executor. If H1 toolkit tools are implemented only in `container/shared/`, they do not work in Claude runtime containers. This is either a scope limitation that should be stated, or an additional implementation surface that should be planned.

3. **Define the write-path rule for H2 explicitly.** "All policy-governing mutations route through Clavain; direct `ic` reads are permitted" should be stated as a rule in the vision, not implied. Bead operations should be explicitly categorized.

## Optional Cleanup for H2 Planning

4. **Close Q2 (event delivery latency)** as "simple poll loop is sufficient." Remove the Autarch signal broker as a candidate — it is an in-process rendering optimization for TUI consumers, not an appropriate mechanism for a separate host process.

5. **Replace "Layer 2.5" framing** with explicit promotion criteria: what conditions would force a layer reclassification, and what are the concrete indicators that those conditions are being approached.

6. **Scope H3 explicitly out of H1/H2 design influence.** Add a boundary statement to the H3 section.

7. **Note the event bridge singleton constraint** for H2: one Intercom host process owns the `--consumer=intercom` cursor at a time.

---

*Reviewed against: `CLAUDE.md` (Demarch monorepo), `docs/demarch-vision.md` v3.0, `apps/autarch/docs/autarch-vision.md` v1.1, `apps/intercom/CLAUDE.md`, `apps/intercom/AGENTS.md`, `apps/intercom/docs/intercom-vision.md` v0.1, `apps/intercom/src/` source layout, `apps/intercom/container/shared/` source layout.*
