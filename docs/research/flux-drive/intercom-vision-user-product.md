# Intercom Vision — User & Product Review

**Reviewer:** Flux-drive User & Product Reviewer
**Target:** `/home/mk/projects/Demarch/apps/intercom/docs/intercom-vision.md`
**Date:** 2026-02-22
**Status:** Draft — brainstorm-grade response to a brainstorm-grade vision

---

## Primary User Identification

The vision document describes three distinct user populations that are treated as one undifferentiated group. Naming them separately is the first correction.

**User A — The Solo Developer-Owner (today's actual user)**
This is the person who built Demarch, runs Clavain sprints, reads Bigend, and already has SSH access. They are sending themselves messages via Telegram to interact with their own agency from mobile, from a coffee shop, or from a context where pulling up a terminal is inconvenient. Job-to-be-done: operate the agency without opening a laptop.

**User B — The Technical Collaborator (H2 target)**
A developer or technical PM on a small team who knows the project but doesn't have a terminal login. They want to ask about sprint status, approve a gate, or review findings. Job-to-be-done: stay informed about what the agency is doing and occasionally direct it, without needing Clavain access.

**User C — The Non-Technical Stakeholder (H3 target, speculative)**
A founder, PM, or stakeholder who wants to know "where are we on this?" or "should we build X next?" Job-to-be-done: get useful, formatted answers about project state without learning any tools.

The vision conflates these three users under the phrase "people who will never run `ic` or `/clavain:sprint`." That conflation creates product ambiguity: the right UX, access model, and capability set differs substantially across these three users.

---

## Section 1: Q1 Open Question — Container Access to Kernel

The vision presents three options for H1 tool access to the kernel:

- **(a)** Mount the `ic` binary read-only into containers
- **(b)** IPC-bridge all queries through the host
- **(c)** HTTP API on the host that containers can call

**Recommendation: Option (b) — IPC-bridge through the host, implemented now; optionally promoted to (c) later.**

Here is the analysis from a user experience and product standpoint.

### Option (a): Mount `ic` binary read-only

**Latency:** Low. Direct binary invocation, no round-trip to host.

**Data freshness:** Good. Every call hits the live SQLite WAL.

**User experience risk — critical:** This option breaks the architectural invariant the security model is built on. The vision's Design Principle 2 reads: "Every user message passes through a container sandbox. The host process handles channel I/O and event routing but never executes LLM-generated actions directly." Mounting `ic` inside the container means an LLM-generated shell command can call `ic run create`, `ic gate override`, or `ic dispatch kill` directly — at H1 read-only access you still mount write-capable binary. Restricting it to read-only `ic` subcommands requires either a custom wrapper binary, kernel-level restrictions (seccomp), or trusting that the container system prompt correctly instructs the agent not to call write subcommands. None of these are reliable. A jail-broken prompt, a confused agent, or a future H2 capability expansion invalidates the read-only guarantee. **This option optimizes latency at the cost of the security invariant that everything else depends on.**

**Conclusion:** Do not use option (a). The latency win is not worth breaking the execution sandbox.

### Option (c): HTTP API on the host

**Latency:** Low to medium. Local HTTP is faster than filesystem IPC polling.

**Data freshness:** Good. Host proxies to `ic`.

**User experience risk:** Introduces a new server surface to maintain. HTTP API versioning, authentication (even for loopback traffic), and error surface all add complexity. The vision notes Intercom is "Not an API gateway. It doesn't expose REST endpoints for programmatic access." Building an internal HTTP API on the host is heading in that direction even if it's loopback-only. The right time to build this is when there are multiple consumers who need concurrent, low-latency access — that is Horizon 3 territory.

**Conclusion:** Correct architecture for H3. Premature for H1.

### Option (b): IPC-bridge through the host

**Latency:** Medium. Filesystem polling adds round-trip latency. For a status query ("what's the current sprint?"), the sequence is: agent writes intent file → host watcher picks it up (poll interval, currently implied at ~100ms intervals based on the IPC watcher design) → host runs `ic` → host writes result to IPC output namespace → agent polls for result. Total latency: several hundred milliseconds to ~2 seconds depending on poll interval and timing.

**Data freshness:** Good. Host hits live SQLite on every query.

**User experience fit:** For conversational queries — "what's the current sprint?" "what should I work on next?" — a 1-second response latency is invisible. Users are not asking for real-time dashboards. They are asking questions in a conversation. A 1-2 second response is well within the conversational rhythm of messaging. This is not a TUI where sub-100ms render time matters. It is a Telegram message where the user sent a question and will not feel a 2-second gap as latency at all.

**Security fit:** Excellent. This is the existing IPC pattern. No new attack surface. The host validates intents before executing. The container cannot escalate to write operations unless the host's IPC handler explicitly allows it.

**What to optimize:** The IPC polling interval. If the current implementation polls for new input files at a fixed interval (e.g., 100-500ms), query responses to the host and back may feel sluggish when chained tool calls are involved (each step pays the poll tax twice). For H1, consider a targeted improvement: a dedicated "query" IPC channel with reduced poll interval (10-20ms) or a file-descriptor-based notification instead of interval polling. This optimization is mechanical and does not require architecture change.

**Conclusion: Option (b) is the right choice for H1 and H2.** It preserves the security model, matches conversational latency expectations, and uses the existing IPC infrastructure. Promote to option (c) only when Horizon 3 multi-user concurrency makes the HTTP surface worth maintaining.

**The "conversation-native, not CLI-over-chat" principle directly supports this.** Users are not asking for real-time streaming dashboards over messaging. A conversational query and a 1-2 second response is the correct UX contract. Optimizing for sub-100ms kernel access is solving the wrong problem.

---

## Section 2: The Three Horizons — User Story Analysis

### Horizon 1: Agency-Aware Assistant

**Who is the user at H1?** User A (the solo developer-owner, operating from mobile or a non-terminal context). Possibly User B if they have been given group access.

**Are the user stories compelling?**

- "What's the current sprint?" — Yes. This is a real job. Developer wants situational awareness without SSH. Genuine value.
- "What do we know about WebSocket performance?" — Depends on whether Pollard's research is queryable. If Pollard requires real-time search, this is not a status query, it is a search request. These have different latency and cost profiles. The vision bundles them without distinguishing.
- "What are the requirements for the auth feature?" — Yes, but only if the agent can locate the right artifact. Artifact naming conventions and search are not trivial. If the agent returns the wrong spec or an outdated one, the user experience fails silently. This user story requires artifact indexing, not just artifact reading.
- "How did the last code review go?" — Yes. Reading an Interflux verdict file and summarizing it is exactly the right use of a conversational agent. Low risk, high value.
- "What should I work on next?" — Partially. This requires the agent to understand priority context, which in turn requires Internext's tradeoff scoring to work correctly. The user story is compelling as a vision but may produce misleading recommendations if underlying data is stale or incomplete. A bad "next work" recommendation actively wastes the user's time.

**What is missing from H1's user stories?**

- **Disambiguation of "current sprint."** The user has mental model of "the thing I'm working on." The kernel has runs. If there are 3 active runs, the agent must choose or ask. The vision does not address this. A bad disambiguation (agent picks the wrong run) produces a confidently-wrong answer, which is worse than "I don't know."

- **Temporal context.** "How did the last code review go?" requires knowing what "last" means. A verdict file from 3 days ago may not be what the user wanted. The agent needs to anchor temporal queries. This is not handled in the tool design.

- **Negative answers.** What does the agent say if there is no current sprint? No recent review? No ready work? User stories only show the happy path. The "graceful failure" path matters more for daily use than the success path.

- **Cost of being wrong.** H1 is described as read-only. But an agent that says "your current sprint is in the execute phase" when it's actually blocked at a gate creates false confidence. The user makes a decision based on stale or misread state. Read-only is not zero-risk.

**H1 user stories are compelling for User A. They are not yet validated for User B**, who does not have the same mental model of Demarch's state and may not know what "beads," "gates," or "Interflux verdicts" are. H1 does not address the translation layer needed for non-developer users.

---

### Horizon 2: Agency Participant

**Who is the user at H2?** User A (developer-owner) doing gate approvals remotely. Potentially User B for read-triggered actions.

**Are the user stories compelling?**

- "Start sprints from chat." — Partially. Creating a bead from chat is straightforward. Starting an Intercore run requires context the user may not provide in a message. What project? Which phase chain? What feature description? A chat message like "let's refactor auth" becomes an LLM interpretation problem before it becomes a kernel problem. The vision does not address what happens when the message is ambiguous or missing required parameters.

- "Advance phases on approval." — Yes. This is the most compelling H2 user story. Gate approval via messaging reply is a natural fit for asynchronous human-in-the-loop. The user does not need to be at a terminal; they need to say "approved" in a chat. High value, narrow scope, low ambiguity.

- "Route findings to chat." — Yes. Push model (agency notifies user) is more reliable than pull model (user asks). When Interflux completes, pushing a summary to Telegram is exactly the right behavior. The user does not have to remember to check.

- "Capture insights from conversation." — Low priority, high risk. When a user says something in chat, deciding whether it is a "kernel discovery" or just conversation is an LLM judgment call. False positives pollute the discovery index. False negatives miss real insights. This user story requires robust intent detection with explicit user confirmation, not automatic capture.

- "Budget alerts." — Yes, but only if they are actionable. An alert that says "run is approaching budget — reply 'extend' to add 50k tokens" is useful. An alert that just says "budget warning" requires the user to switch context to terminal to act. The value depends entirely on whether the alert offers in-chat remediation.

**What is missing from H2's user stories?**

- **"Cancel run from chat."** If the user gets a budget alert and wants to kill a runaway run, they need cancellation from the same surface they received the alert on. The vision lists "pause, extend, or cancel" for budget alerts but the action toolset in H2 does not include a cancel tool.

- **"What is waiting for me?"** The most natural use of a bidirectional system is an inbox metaphor: the agency accumulates things that require human input (gates, approvals, decisions), and the user checks the inbox and acts on each one. The vision describes individual events (gate ready → notification → reply "approved") but not the inbox view. If three gates queue up while the user is offline, do they get three separate messages? Can they reply to a summary and clear all three?

- **The "approval by the wrong person" problem.** H2 assumes a single-user context. If a shared group is used for collaboration (which is plausible even before H3), any group member could reply "approved" to a gate message. The vision defers identity to H3, but the security gap opens in H2.

---

### Horizon 3: Distributed Agency Surface

**Who is the user at H3?** User B (technical collaborator) and potentially User C (non-technical stakeholder).

**Are the user stories compelling?**

- "Role-based access." — Necessary, not compelling. It is a prerequisite, not a user benefit. Reframe: "Engineering team can approve gates from chat without having SSH access."

- "Cross-channel continuity." — The most overambitious claim in the document. The vision says "a conversation started in Telegram can be continued in WhatsApp or CLI." This requires that conversation state is stored at the kernel level with a user identity that maps across channels. The kernel does not model users. Intercom has its own SQLite. WhatsApp and Telegram have different identity schemes. This is a significant cross-channel identity and session portability problem, and the vision treats it as one bullet point.

- "Multi-agent delegation." — Compelling as a capability. The user experience description ("user sees a synthesized response, not the raw multi-agent chatter") is exactly right. But the synthesis quality determines whether this is useful or confusing. If three agents disagree and synthesis averages them, the result may be confidently wrong.

- "Scheduled reporting." — Yes. This builds on Intercom's existing task scheduler and is the most immediately buildable H3 feature. Weekly sprint summaries via Telegram are valuable and the infrastructure exists.

- "Voice adaptation." — Valuable as a polish layer (H3+), not a compelling user story on its own. The user does not ask for "voice adaptation." They ask for "answers that make sense to me." This is a quality property, not a feature.

**What is missing from H3's user stories?**

- **Onboarding for new group members.** When User B joins a group and the agency sends them a message, what happens? Do they have any context for what the agency is, what the sprint is, what a "gate approval" means? H3 assumes users already understand the agency model.

- **Opt-out and notification fatigue.** If the agency pushes scheduled reports, budget alerts, gate requests, and review summaries to a Telegram group, that group becomes noisy fast. The vision does not address notification management, muting, or priority filtering.

- **User C's actual questions.** The vision identifies non-technical stakeholders as H3 users but does not include a single user story from their perspective. A founder asking "are we on track for the release?" or "how much did this cost?" is a very different query than a developer asking "what's the current sprint phase?" H3 needs at least one User C story to validate that the system actually serves that audience.

---

## Section 3: "What Intercom Is Not" — Exclusion Analysis

The five exclusions in the document are evaluated below.

**"Not a replacement for the CLI."**
Correct exclusion. Intercom does not need to replicate every `ic` subcommand in conversational form. However, there is a latent user need here that the exclusion papers over: User A, operating from mobile, sometimes needs to do something that is currently terminal-only. If the message interface cannot do it, they have no fallback short of SSH. The exclusion is right as a scope boundary, but it should be accompanied by an explicit list of "things users must still use the CLI for" so that expectation is set rather than discovered at the wrong moment.

**"Not an API gateway. It doesn't expose REST endpoints for programmatic access. That's Intermute's role."**
Correct exclusion for now. The architectural boundary between Intercom (conversational human access) and Intermute (programmatic agent access) is clean and worth preserving. The risk is that H3's multi-agent delegation (agents coordinating through Intermute) and Intercom's event bridge start to overlap in practice. Monitor the boundary; do not let H3 erode it.

**"Not a notification service. It's bidirectional. One-way alerting is a subset of what it does, not its purpose."**
This exclusion is doing the wrong work. "Not a notification service" suggests Intercom should not be used for one-way alerting. But one-way alerting is a high-value, low-risk capability that H2 explicitly requires (route findings to chat, budget alerts). The distinction the vision is trying to make — Intercom is bidirectional, not just a push pipe — is real and worth stating, but framing it as "not a notification service" undersells a legitimate use case that is already in scope.

**Reframe the exclusion as:** Intercom is not a *pure* notification service. Outbound notifications are built on the same infrastructure as bidirectional conversation, not bolted on separately.

**"Not a new orchestrator. It doesn't compete with Clavain's workflow or Coldwine's task coordination."**
Correct and important. The risk of Intercom becoming an orchestrator is real: as it gains the ability to start sprints, advance phases, and route events, it accumulates decision logic that currently lives in Clavain. The exclusion should be treated as a hard constraint, not just a design preference. Any H2 capability that requires Intercom to understand sprint policy (e.g., "should I start a sprint or just create a bead?") is a signal that orchestration logic is leaking into Intercom.

**"Not required."**
Correct but possibly misleading. If H2 ships gate approvals via messaging, teams that adopt it become dependent on it. A gate that is waiting for approval via Telegram is blocked until Intercom is available. "Not required" is only true if teams do not use the gate-approval flow. The vision should note: optional at the organizational level, but operationally critical once adopted for gate approvals.

**One exclusion that is missing:**

**"Not a team collaboration tool."** The vision describes H3 team scenarios (Product group, Engineering group, Stakeholders group) that look like Slack channels with agency integration. There is a real user need here, but also a real risk: if Intercom's group chat becomes the primary place where team members discuss the project, it becomes responsible for conversation threading, history, search, and retention — none of which are in scope. This boundary needs to be stated: Intercom routes agency state to people, not people to each other.

---

## Section 4: Problem Validation

**The stated problem:** "Demarch's current interaction model is agent-facing. Every module assumes the user is either a developer running Claude Code, an agent dispatched by the kernel, or a power user reading a TUI."

**Does this hold up?**

The problem statement is accurate in its description of the current state but unvalidated in its severity framing. Let the analysis distinguish the two parts.

**Part A — "The current model is agent-facing."** True. Clavain is a Claude Code plugin. Bigend is a TUI. Neither is usable without a terminal session. If you are not at a terminal, the agency is opaque. This is a structural fact, not an assumption.

**Part B — "People need messaging-based access."** This is where the problem validation is weak.

The vision describes three types of people who would benefit: a PM checking sprint status, a founder asking "what should we build next?", a team member reviewing flux-drive findings. These are described without reference to evidence. Are these real users who currently exist in the project's orbit? Or are they hypothetical personas constructed to justify the vision?

For User A (the solo developer-owner), the problem is easy to validate: the person who built this system already uses Telegram to message the assistant. The problem is real and present. The question is whether H1 tool integration solves a meaningful gap above what the current NanoClaw assistant already handles.

For User B (technical collaborator), the problem requires validation that:
- A real collaborator exists who needs agency access but cannot use the CLI
- The collaborator's actual queries are in scope of what H1 tools can answer
- The collaborator is blocked often enough that a messaging interface changes their workflow

For User C (non-technical stakeholder), the problem requires the most validation. The vision assumes a founder or PM "wants to review findings from the latest flux-drive run." This is a product assumption, not a validated user need. A stakeholder who does not understand what a flux-drive run is will not know to ask about it. The interface does not create the need; the need must pre-exist.

**The real question for product validation:**

Has anyone — in the development of Demarch — been blocked from doing something because they could not access the agency from a messaging interface? If yes, what specifically were they blocked from doing? That is the problem to solve in H1. Everything else is speculative.

**What is actually validated:**

NanoClaw (the current system) already runs a capable, container-isolated, multi-runtime assistant. People are already using it. The gap being filled by H1 is not "can we have a messaging assistant?" (that exists) but "can the assistant answer questions about the agency?" That is a narrower, more testable problem.

**Recommended validation test for H1:**

Before building any tool, run a shadow experiment: give User A (or a willing User B) access to the current NanoClaw assistant with a system prompt that says it can answer questions about the Demarch agency. Ask them to query sprint status using only shell commands already available to the container (the project is mounted read-only for the main group already). Document: (1) what queries they attempt, (2) what answers the agent gives, (3) what queries fail because of missing tools. That failure list is the tool backlog. Build exactly those tools, in that order.

---

## Section 5: User Needs That No Horizon Addresses

Three user needs are present in the scenario descriptions but not given a home in the horizon model.

**Need 1: "What changed since I last checked?"**

Users checking in after a period of inactivity need a delta, not a status snapshot. "The sprint is in the execute phase" is correct but unhelpful if the user knew that two days ago. "Since you last asked: the plan phase completed, execute started, two files were modified, and a gate check failed and was manually overridden" is the answer the user needs. None of the horizons address a "what changed" query pattern. The toolset (`demarch_run_status`, `demarch_sprint_phase`) returns current state, not delta state. This is a gap in the H1 tool design.

**Need 2: "Is this ready for me to review?"**

A recurring pattern in developer workflows: something is being worked on, and the user wants to know when it reaches a state where their input is useful. This is not "alert me when X happens" (which is the H2 event subscription model) — it is a standing query that the user can poll when convenient. "Is the flux-drive review done?" "Is the plan ready?" The H1 tools are designed for direct queries but not for this "is it done yet?" pattern. The answer requires state comparison, not state snapshot.

**Need 3: The audit question — "Show me what the agency decided and why."**

When something goes wrong in an autonomous sprint, the user's first question is not "what is the current state?" but "what happened, when, and who/what decided it?" This is an event history query: show me the gate evaluations, the model routing decisions, the phase transitions, with timestamps and rationale. None of the Demarch tools exposed in H1 serve this directly. `ic events` exists in the kernel, but surfacing it conversationally is not in the H1 tool set. This need is highest-value when trust in the agency is lowest — precisely when you most need to answer it.

---

## Section 6: Findings Summary

### Highest-Priority Issues

**1. Three users are conflated; the product needs to pick one for H1.**
The vision can describe all three user populations, but the H1 implementation must be optimized for one. The strongest validation exists for User A. Build H1 for User A, validate, then extend to User B in H2 with explicit identity and access controls.

**2. Option (b) for kernel access is right. The IPC poll latency concern is real but solvable without architecture change.**
Lower the IPC poll interval for query-type intents, or implement a lightweight file-descriptor notification alongside the polling loop. Do not mount the `ic` binary inside containers. Do not build an HTTP API surface until H3.

**3. The H1 tool set is missing three query patterns: delta queries, readiness queries, and audit queries.**
`demarch_run_status` returns a snapshot. Add `demarch_run_events` (paginated event log), `demarch_run_since` (delta since a timestamp or user-visible checkpoint), and `demarch_phase_ready` (is phase X done / is there anything for me to do?). These address User A's most common actual queries better than spec lookup or research tools.

**4. The "conversation-native" principle is stated but not operationalized.**
The vision correctly identifies this as a core principle. But none of the tool designs describe how a tool result gets converted to a natural language response. If `demarch_run_status` returns JSON and the agent formats it as a table with escaped pipes, the principle has failed. The system prompt for container agents in H1 must include explicit formatting guidance: "When reporting sprint status, write as if describing progress to a colleague, not as a status report." This is a detail that will determine whether H1 feels good or feels like CLI-over-chat.

**5. Gate approval UX (H2) needs full flow design before implementation.**
The vision lists this as open question 4. It is not just a UX question — it determines whether H2's most valuable capability (async human-in-the-loop gate approval) is safe to ship. The flow must specify: what does the approval message look like, what keywords are accepted, what happens on timeout, what happens if the wrong person replies, what happens if two people reply simultaneously, and how is the approval recorded in the kernel audit log. Shipping gate approval without these answers is shipping a trust primitive with an untested security contract.

**6. User C (non-technical stakeholder) has no validated use case in the document.**
H3's team audience is speculative. Before designing role-based access and cross-channel continuity for stakeholders, validate whether a real non-developer stakeholder has a real question they need answered that the agency can answer correctly. If the answer is "the PM just wants to know if we're on track," that is a one-sentence status summary, not a distributed agency surface problem.

### Issues to Monitor

- The "not a notification service" framing undersells a legitimate use case. Reframe.
- The "not required" claim becomes false once teams adopt gate approvals via chat. Acknowledge operational dependency as a consequence of adoption.
- H3 cross-channel continuity is substantially harder than described. Reserve it for a later vision revision when the identity model is worked out.
- The insight-capture user story in H2 (register user messages as kernel discoveries) requires explicit confirmation from the user, not autonomous capture. Flag as high misfire risk.

### What Would Prove H1 Works

- User A successfully answers 5 different sprint status queries in a Telegram conversation without switching to a terminal
- Answers are factually correct (match what `ic run current --json` returns) in at least 9 of 10 queries
- Responses read as conversational, not formatted as terminal output, without special casing in the system prompt
- Median response latency from message send to agent reply is under 10 seconds (messaging channel round-trip + container spawn + IPC round-trip)

### What Would Prove H1 Does Not Work

- Users frequently append "but is that actually current?" — indicating distrust in data freshness
- Users discover the agent gave wrong answers due to ambiguous run selection (multiple active runs)
- Users resort to sending shell commands directly ("can you run `ic run current --json` for me?") rather than using the natural language interface
- Responses consistently read as formatted data dumps rather than natural language

---

*This is a user and product review of a brainstorm-grade vision document. It does not evaluate implementation feasibility, security posture, or performance beyond what directly affects user outcomes. Architecture and engineering review should be conducted separately.*
