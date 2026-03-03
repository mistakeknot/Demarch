# The Composition Paradox Is Real: Deep Documentation Is Consolidation's Confession

## I. What Composition Documentation Actually Contains

Let me be precise about what we are talking about. When someone writes a "workflow context document" for the coordination surface — interlock, intermux, interpath — they must specify:

1. **Call ordering**: `who_is_editing` before `reserve_files` before work before `release_files`
2. **Shared state assumptions**: that the reservation state interlock maintains must be consistent with the editing state intermux reports
3. **Error propagation**: what happens when `resolve` succeeds but `reserve` fails — who cleans up, and in what order
4. **Precondition chains**: that `reserve_files` assumes paths have been resolved through interpath, that resolved paths are in a format interlock expects, that the identity interlock uses matches the identity intermux tracks

This is not metadata. This is not a helpful hint layered on top of independent tools. This is a **system specification**. It defines the contract between components — the invariants that must hold for the system to function. The 18-point accuracy gap exists precisely because agents lack this specification, and they cannot infer it from tool schemas alone.

## II. The Opponent's Strongest Case

The strongest version of the shallow-composition argument goes like this: "Lots of independent things compose. Unix pipes compose. HTTP APIs compose. The existence of a composition pattern doesn't prove the components are one thing — it proves they have a well-defined interface. Write the interface documentation, keep the components separate, get the benefits of both."

This is genuinely compelling. It is also wrong, and the reason it is wrong is the distinction between **incidental** composition and **essential** composition.

Unix pipes compose incidentally. `grep` does not know about `sort`. Neither has preconditions that reference the other's state. You can use them independently and they are fully functional. The composition documentation for Unix pipes is: "stdout goes to stdin." That's it. One sentence. Shallow composition works because the coupling is shallow.

Now try writing the composition documentation for the coordination surface in one sentence. You cannot. You need the four categories I listed above. The depth of the documentation required is a **direct measurement of the coupling between the components**. This is not a metaphor. It is a formal relationship.

## III. Why The Paradox Is Real

The Round 2 auditor identified something precise: "The composition layer's quality is inversely proportional to its necessity." Let me restate this more aggressively.

The composition documentation for tightly coupled plugins must contain:
- The sequencing contract (what order to call things)
- The state coherence contract (what shared assumptions hold)
- The error handling contract (what happens when part of the sequence fails)
- The identity and format contracts (what one plugin assumes about another's outputs)

Now describe what a **module's internal documentation** contains for its subcomponents:
- The sequencing contract (what order to call internal functions)
- The state coherence contract (what shared assumptions hold between subsystems)
- The error handling contract (what happens when part of the pipeline fails)
- The identity and format contracts (what one subsystem assumes about another's outputs)

These are the same document. The composition documentation and the consolidation specification are **isomorphic**. Writing one is writing the other. The only difference is whether you put a namespace boundary in the middle — and that namespace boundary is the thing causing the 18-point accuracy gap.

This is the paradox, and it cannot be dissolved. The documentation that would make the two-consumer architecture work IS the documentation that proves the architecture is wrong.

## IV. Distributed Systems Literature Already Knows This

I do not need to invent this argument. The microservices literature has a precise term for services that must be called in a specific order with shared state assumptions: a **distributed monolith**. Sam Newman defines it explicitly — if you cannot deploy or change one service without coordinating with others, you have a distributed monolith with all the costs of distribution and none of the benefits of independence.

Chris Richardson's choreography-vs-orchestration framework makes the same point from a different angle. Choreographed services that require participants to know the full sequence — where each service must understand its position in a multi-step workflow — exhibit **temporal coupling**. The canonical recommendation is: either introduce an orchestrator (which IS consolidation under a different name) or redesign the boundaries so services are truly independent.

API design literature treats required call ordering as a recognized coupling smell. An API where you must call endpoint A before endpoint B, where B's correctness depends on A's side effects, is considered a **leaky abstraction** — the internal implementation sequence has leaked into the public interface. The standard remedy is to either combine the operations or hide the sequence behind a facade. Both are consolidation.

The agent calling `interlock.reserve_files` without first calling `interpath.resolve` is not making a "discovery error" that better documentation fixes. It is encountering a **temporal coupling violation** that exists because the system boundary is drawn in the wrong place.

## V. The Litmus Test

Here is a practical test anyone can apply. For any pair of plugins, try to write the composition documentation. Measure its length and complexity.

- **interflux + intermonk**: No composition documentation needed. They do not interact. Genuinely independent. Keep them separate. Everyone agrees.
- **interlock + intermux + interpath**: The composition documentation specifies call ordering, shared state, error propagation, precondition chains. It is pages long. It is a system specification. These are one thing wearing three namespaces.

The depth of composition documentation is a **litmus test for coupling**. If you can write it in one sentence, the plugins are independent. If you need pages, they are coupled. If the pages describe sequencing, shared state, and error propagation, they are a single system that has been incorrectly decomposed.

The Round 2 synthesis proposed writing these pages as "workflow context documents." I accept that this would improve agent accuracy. I also observe that once written, these documents are **indistinguishable from the internal documentation of a consolidated module**. The synthesis team proposed writing the consolidation specification and calling it "composition infrastructure." The label is different. The artifact is identical.

## VI. The Uncomfortable Version

Let me push this to its most uncomfortable form.

The "Two Consumers, One Codebase" architecture's entire value proposition rests on the claim that plugins can be independently understood and independently consumed. The accuracy gap proves they cannot — at least not for the coupled clusters. The proposed remedy is documentation that explains how they depend on each other. But documentation of mutual dependence is the definition of coupling. And coupled components behind separate interfaces is the definition of accidental complexity.

Every hour spent writing composition documentation for coupled plugins is an hour spent maintaining the fiction that they are separate. That fiction has a measured cost: 18 points of accuracy. The composition documentation does not close this gap — it is the gap's confession, written down.

Consolidate the coupled clusters. Keep the genuinely independent plugins independent. Let the depth of required composition documentation be the decision criterion. This is not a judgment call. It is a measurement.
