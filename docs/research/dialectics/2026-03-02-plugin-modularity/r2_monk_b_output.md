# The Unit of Packaging Is the Agent's Cognitive Transaction

## I. Ontological Claim: What a Plugin Actually Is

A plugin is not a concept. A plugin is not a domain boundary. A plugin is not what makes sense on a whiteboard. A plugin is a unit of work that an agent can load, comprehend, and execute within a single cognitive transaction. If the agent cannot hold the plugin's full operational context — its tools, its state model, its interaction patterns with adjacent systems — then you have not created a plugin. You have created a tax.

The 49-plugin architecture of Demarch is a tax collection system. Every plugin registration is a toll booth. Every CLAUDE.md is a document the agent must read. Every tool definition is a slot consumed in a context window that does not grow to meet the architect's ambitions. The architect drew 49 boxes because 49 concepts exist. The agent does not think in concepts. The agent thinks in tasks. And tasks do not respect your boxes.

## II. The Opponent's Strongest Case

The strongest argument for uniform fine-grained structure is that it is *legible*. A developer opens the repo, sees 49 directories, and knows where things live. Each plugin has clear ownership, a single responsibility, a testable surface. Dependency direction is explicit. The architecture diagram is clean. When something breaks, you know which box to open.

Furthermore, the opponent argues, infrastructure will close the gap. Tool Search reduces token cost by 85%. Lazy loading means agents only activate what they need. Tiered packaging can hide internal tools. The developer gets conceptual clarity; the agent gets progressive disclosure. Everyone wins.

This is the strongest version of the opposing case. It is wrong.

## III. Why Infrastructure Cannot Solve the Agent Cost Problem

Tool Search reduces *token* cost. It does not reduce *selection* cost. These are fundamentally different cognitive operations.

When an agent faces a task, it must first determine which tools are relevant. Tool Search converts this from "scan all 49 plugin definitions" to "query an index and receive candidates." The tokens are cheaper. But the *decision* — "which of these candidates is the right one for my current step?" — still degrades with surface area. Anthropic's own research demonstrates this: accuracy drops from 92% with 5-7 tools to 60% with large tool surfaces. Tool Search does not shrink the tool surface. It shrinks the *description* of the tool surface. The agent still must choose among candidates that span artificial boundaries.

Consider the concrete case. An agent needs to coordinate work across multiple Claude Code sessions. This requires interlock (file reservations, message passing), intermux (session monitoring, output search), and interpath (path resolution across contexts). Three plugins. Three CLAUDE.md files. Three AGENTS.md files. Three separate tool namespaces. The agent must hold all three mental models simultaneously to accomplish one task: *coordination*.

Tool Search will helpfully surface tools from all three plugins. The agent will then spend context reasoning about which namespace owns which part of the operation. It will make mistakes at the boundaries — calling `interlock.reserve_files` when it should have first called `interpath.resolve` to normalize the paths, then checking `intermux.who_is_editing` to avoid conflicts. The workflow is one thing. The packaging makes it three things. The agent pays for this fragmentation in accuracy, not tokens.

Progressive disclosure and lazy loading are solutions to the *token budget* problem. They are not solutions to the *cognitive fragmentation* problem. You can defer loading a tool definition. You cannot defer the agent's need to understand that three separate tools form one workflow. That understanding must be present at decision time, and it is present as confusion.

## IV. The Deeper Principle: Agent Cognitive Cost as Primary Constraint

The history of software architecture is the history of optimizing for the wrong consumer. We built SOAP because it was legible to enterprise architects. We built microservices because they were legible to platform teams. In each era, the *actual consumer* of the interface paid for the *producer's* organizational preferences.

Demarch's actual consumer is an AI agent. Not a developer browsing the repo. Not an architect drawing boxes. An agent with a fixed context window, degrading accuracy under tool proliferation, and zero ability to intuit that three separately-packaged things are actually one workflow.

User-centered design has always demanded that you organize for the consumer's mental model, not the producer's. When the consumer was a human using a GUI, we learned (painfully, over decades) to organize by task, not by database table. Nobody builds a UI with 49 menu items mapped to 49 backend services. You build it around what the user is trying to do. The agent is the user. The agent is trying to *coordinate sessions*, not trying to *use interlock, then intermux, then interpath*.

The correct unit of packaging is the agent's cognitive transaction: the minimum context bundle that lets an agent accomplish a complete workflow without crossing package boundaries mid-task. If coordination requires three current plugins, coordination is one plugin. If research requires interdeep + interflux + interknow, research is one plugin. The workflow is the package. The task is the boundary.

## V. The Uncomfortable Extreme

Here is where I push this to its most uncomfortable conclusion: **many of the 49 plugins should not exist as independent packages at all.**

Not because they are bad code. Not because the concepts are wrong. But because *no agent workflow terminates within their boundaries*. Interpath has no workflow that doesn't involve another plugin. Interlock has no workflow that doesn't involve intermux. These are not plugins. These are *implementation details of actual plugins* that were promoted to top-level entities because the architect found the concept independently interesting.

The architect's conceptual satisfaction is not a design requirement. It is a design *hazard*. Every concept that the architect finds satisfying enough to name, package, and register is a concept the agent must now learn, differentiate, and select among. The architect's delight is the agent's confusion.

ChatGPT learned this. They shipped a plugin marketplace, discovered that agents collapsed above 3 active plugins, and deprecated the entire concept. They did not build better Tool Search. They did not build tiered loading. They recognized that the fundamental unit of consumption was wrong and removed it. Demarch is building the same architecture ChatGPT abandoned, with the same confidence that infrastructure will paper over the same structural problem.

## VI. Reasoning Skeleton

**Premise 1:** LLM agent accuracy degrades as a function of tool surface area, not token count. (Empirical: Anthropic data, 92% → 60%.)

**Premise 2:** Tool Search and lazy loading reduce token cost but do not reduce tool surface area at selection time. (Architectural: candidates still surface from fragmented namespaces.)

**Premise 3:** Agent workflows in Demarch routinely cross 3-4 plugin boundaries. (Empirical: coordination, research, monitoring tasks.)

**Premise 4:** Each plugin boundary adds cognitive load: separate documentation, separate tool namespaces, separate mental models. (Structural: 3 CLAUDE.md + 3 AGENTS.md + 3 skill definitions per cross-cutting task.)

**Step 1:** If accuracy degrades with surface area (P1), and infrastructure doesn't reduce surface area (P2), then infrastructure cannot prevent accuracy degradation.

**Step 2:** If workflows cross boundaries (P3), and boundaries add cognitive load (P4), then fine-grained packaging directly increases the cognitive cost of common tasks.

**Step 3:** The alternative — packaging by workflow — reduces both surface area (fewer packages) and boundary crossings (workflow stays within one package).

**Conclusion:** The correct packaging unit is the agent's cognitive transaction — the workflow — not the developer's conceptual domain. Optimizing for developer legibility when the primary consumer is an agent is architectural malpractice. The 49-plugin structure is not a feature of good design. It is a monument to the wrong user.
