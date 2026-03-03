# The Structure Is the Mechanism

## I. What a Plugin Boundary Actually Is

A plugin boundary in the Demarch monorepo is not a deployment unit, not a version contract, not a team ownership boundary. It is a *directory*. Specifically, it is a directory with a uniform internal structure — CLAUDE.md, AGENTS.md, src/, tests/, MCP server — that sits alongside 48 siblings in interverse/, each independently version-controlled but all co-located under a single working tree. The developer works from the root. The agent works from the root. The directory convention is the entire mechanism that makes "49 plugins" possible at a cost indistinguishable from "1 project with 49 subdirectories."

This is the load-bearing insight that Round 1's Monk A arrived at: the number 49 is incidental. The uniform structure is load-bearing. What makes splitting tractable — and what made the four historical extractions (interknow from interflux, etc.) succeed without drama — is that every plugin is the same shape. You know where to look. The agent knows where to look. Splitting is a mkdir and some mv commands. Merging is the reverse. The transaction cost of changing boundaries approaches zero precisely because the structure is homogeneous.

## II. The Opponent's Best Case

The strongest argument for explicit tiered classification runs like this: agents cannot afford 49 tool registrations. Anthropic's own data shows accuracy degrading from 92% to 60% with large tool surfaces. Someone must pay for this, and currently the agents pay while the architect benefits. Tiered packaging — sovereign, modular, internal — would let the system load only what matters for a given task. Without classification, every agent interaction bears the weight of every plugin.

This is not a frivolous argument. The cost is real, the degradation is measured, and the who-pays-vs-who-benefits tension is genuine. I take this seriously enough to demolish it precisely.

## III. Why Tiered Classification Fails Here

The tiered classification proposal fails on three independent axes: ontological, operational, and temporal.

**Ontologically**, the tiers reify a distinction that does not exist in the system's actual dependency graph. What makes a plugin "sovereign" versus "internal"? The Round 1 synthesis proposed a "stranger test" — can an external contributor work on this without reading siblings' docs? All three validators correctly identified this as measuring documentation quality, not architectural independence. But the deeper problem is that sovereignty is not a property of a plugin; it is a property of a *task*. Interlock is sovereign when you are building a file-locking feature. It is deeply coupled when you are debugging an intermute transport issue that surfaces through interlock's reservation system. Classification freezes a task-relative property into a permanent label. This is a category error.

**Operationally**, tiers create a governance surface that must be maintained. Who decides which tier a plugin occupies? When does a plugin move between tiers? What happens when a "modular" plugin grows an independent community — does it get promoted? What happens when a "sovereign" plugin accumulates deep dependencies — does it get demoted? Every tier transition is a decision that requires review, produces disagreement, and consumes exactly the kind of architect attention that should be spent on infrastructure. The classification system becomes work that produces no code, no capabilities, and no user value. It is pure organizational overhead masquerading as architecture.

**Temporally**, classification systems applied to software become Goodhart targets. Demarch's own PHILOSOPHY.md warns explicitly: "No single metric stays dominant. Diverse evaluation resists Goodhart pressure." A tier label is a metric. The moment "sovereign" means "gets independent packaging and better agent treatment," every plugin maintainer has an incentive to document their way into sovereignty. The stranger test, as Monk B noted, is directly gameable — write enough docs and anything passes. But even a more rigorous test would succumb. The classification crystallizes at assessment time and rots thereafter. The system described in PHILOSOPHY.md — closed-loop, calibrating, rotating — is the antithesis of a static tier assignment.

## IV. Uniform Structure as Infrastructure

The correct response to agent context cost is not to sort plugins into treatment groups. It is to make the uniform structure so cheap to navigate that sorting is unnecessary.

This is not hypothetical. The infrastructure already exists or is in active development:

**Tool Search** cuts token overhead 85% (77K to 8.7K tokens) while improving accuracy from 49% to 74%. This is Anthropic's own measurement on exactly the problem the tiers are supposed to solve. The agent does not need to know that interlock is "sovereign" and intercache is "internal." It needs to search for "file locking" and get interlock's tools loaded on demand. The uniform structure makes this search trivial — every plugin exposes capabilities the same way.

**Dynamic Context Loading** achieves 98% token reduction by providing high-level summaries first and drilling down only when needed. The uniform CLAUDE.md/AGENTS.md structure across all 49 plugins is *precisely* the layered summary format that dynamic loading exploits. A heterogeneous tier system would require the loading infrastructure to understand three different packaging formats instead of one.

**Activation events and lazy registration** are the MCP-level equivalent: tools exist but are not loaded until semantically relevant. The MCP community's own discussion on hierarchical tool management identifies flat tool lists as the problem and search-based discovery as the solution — not reclassification of the tools themselves.

The uniform directory convention is what makes all three mechanisms work. Every plugin has the same shape, so a single search index covers all of them. Every plugin declares capabilities the same way, so a single lazy loader handles all of them. Every plugin's CLAUDE.md follows the same template, so progressive disclosure works identically for all of them. Introduce tiers — sovereign gets independent packaging, modular gets bundled, internal gets inlined — and you now need three discovery mechanisms, three loading strategies, three documentation formats. You have traded one problem (flat tool surface) for a harder problem (heterogeneous tool surface with classification maintenance).

## V. The Uncomfortable Extreme

Push this to its limit: the correct number of tiers is one. Not because all plugins are equal — they manifestly are not. Interlock has a more independent problem domain than intercache. Interflux serves external users in ways interphase never will. These differences are real. But the response to real differences is not to encode them in a classification system. It is to build infrastructure that handles differences *dynamically*, at query time, based on what the agent actually needs right now.

The filesystem does not classify files into "important" and "unimportant" tiers with different storage mechanisms. It provides a uniform interface — open, read, write, close — and lets the consumer decide what matters. The uniform interface is what makes the filesystem scale to millions of files without a taxonomy department.

Demarch's interverse/ is a filesystem for agent capabilities. The uniform structure — CLAUDE.md, AGENTS.md, src/, tests/ — is the inode. Tool Search is `find`. Lazy loading is demand paging. The entire infrastructure stack assumes and rewards homogeneity. Introducing tiers is introducing a type system into a filesystem that succeeds precisely because it is untyped at the organizational level and richly typed at the interface level (MCP tool schemas, capability declarations, dependency manifests).

## VI. The Argument Skeleton

**Premise 1:** The agent context cost problem is real and measured (92% to 60% accuracy degradation with large tool surfaces).

**Premise 2:** This problem has two possible solutions: (a) reduce the number of artifacts the agent sees by classifying them into tiers, or (b) reduce the cost of discovering relevant artifacts through search and lazy loading infrastructure.

**Premise 3:** Solution (a) requires a classification system that must be created, maintained, governed, and kept current. Classification systems applied to software architecture become stale, create governance overhead, and succumb to Goodhart pressure.

**Premise 4:** Solution (b) requires uniform structure across all artifacts so that a single discovery mechanism works for all of them. Anthropic's Tool Search already demonstrates 85% token reduction and 25-point accuracy improvement on this exact problem.

**Premise 5:** The monorepo's uniform directory convention is precisely the homogeneous substrate that makes solution (b) work. The four historical plugin extractions demonstrate that this structure makes boundary changes cheap.

**Conclusion:** Finish the infrastructure — Tool Search integration, lazy loading, activation events — and stop trying to sort plugins into tiers. The uniform structure is not a problem to be solved by classification. It is the solution that makes classification unnecessary.

The monorepo already chose. The 49 identical directory shapes are not 49 problems waiting for a taxonomy. They are 49 proofs that the mechanism works. Build the discovery layer. The sorting will take care of itself.
