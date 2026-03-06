# Phase 5: Sublation — Sovereign by Design, Not by History

## The Synthesis

The contradiction dissolves when you stop asking "how many plugins should there be?" and start asking **"what packaging strength does each plugin's problem domain require?"**

Both monks assumed plugins must be packaged uniformly. The correct answer is heterogeneous boundary strength — but the *mechanism* for determining boundary strength is not git history (which measures attention allocation, not independence potential). It is **domain independence**: can this plugin's problem domain be understood, contributed to, and evolved without requiring knowledge of its siblings?

### Why Git History Fails as a Mechanism

An earlier version of this synthesis used commit counts to classify plugins. The architect corrected this: intermux and intercache have low commit counts because they haven't been prioritized yet, not because they lack independent problem domains. Git history in a young codebase with a single developer measures *where attention went first*, not *what deserves independence*. It confuses the architect's backlog with the architecture's structure.

### The Stranger Test

The correct mechanism is the **stranger test**: could an external contributor work on this plugin without reading 4 other plugins' documentation?

- **Passes the stranger test:** interflux (code review is a self-contained domain), intermonk (dialectic reasoning is orthogonal to everything), interskill (skill authoring has its own spec). A stranger can clone one repo, read its AGENTS.md, and contribute.
- **Fails the stranger test:** If intermux requires understanding interlock's reservation protocol to make any meaningful change, it is not an independent problem domain — it is a feature of interlock's domain. If intercache's invalidation semantics are defined by interpath's routing decisions, same conclusion.
- **The architect must answer:** For each plugin, "can a stranger contribute here without reading siblings?" The answer determines packaging strength.

### Tiered Packaging (Revised)

| Tier | Packaging | Determined By |
|------|-----------|---------------|
| **Sovereign** | Own repo, own version, own release cycle | Passes stranger test — has its own problem domain, own users, own use cases |
| **Modular** | Own directory in a domain repo, own namespace, shared version | Has conceptual identity but stranger needs sibling context to contribute meaningfully |
| **Internal** | Module within a parent plugin | Implementation detail whose requirements are fully derived from parent |

The classification is **prospective** (based on the plugin's problem domain) not **retrospective** (based on commit history). A plugin with 0 commits but a genuine independent problem domain stays sovereign. A plugin with 50 commits that always changes in lockstep with a sibling is modular.

### What This Changes

**The unit of analysis shifts.** "Plugin" is no longer a uniform concept. The system recognizes tiers of packaging strength. Sovereignty is preserved (Monk A) but only for plugins whose problem domains pass the stranger test. Consolidation (Monk B) is applied to plugins that fail it — not as punishment but as acknowledgment that their docs, versions, and release cycles are *naturally* shared with siblings.

**The monorepo's role clarifies.** It is the natural home for modular-tier packages — things that deserve conceptual identity (a name, a namespace, documentation) but not packaging independence (separate repo, separate version, separate CI). Sovereign plugins live in their own repos. This is a design decision, not a promotion to be earned.

**Infrastructure investment targets both tiers.** Sovereign plugins need the loading infrastructure Monk A advocates (Tool Search, lazy loading, activation events). Modular plugins need the boundary enforcement Monk B implicitly recommends (static analysis like Packwerk, not repo separation). Both investments are correct — they just apply to different tiers.

**Agent context cost addressed from both directions.** Modular-tier plugins consolidated into domain repos = fewer manifests and AGENTS.md files to load. Sovereign plugins use Tool Search / lazy loading = only activated when relevant. The 5-7 active tool limit is respected through routing, not through eliminating capabilities.

**Priority does not determine architecture.** The architect can prioritize interflux over intermux for the next 6 months without that meaning intermux should be absorbed. The backlog and the architecture are independent axes. This is the key insight the first synthesis missed.

## Abduction Test

Starting from "plugins should have packaging strength proportional to domain independence (stranger test), not development history":
- Monk A is predictable: treats all boundaries as load-bearing because they assume sovereignty is about *packaging* when it's about *problem domain*
- Monk B is predictable: treats low-activity boundaries as evidence of non-independence when they're evidence of *deferred priority*

Both are partial views. Monk A is right that sovereignty protects future optionality. Monk B is right that some plugins share a problem domain. Neither can see that *which* plugins share a domain is determined by conceptual analysis, not by commit frequency. **Passes.**

Abduction type: **(b) conditional-creative**, pushing toward **(c)** — the stranger test as a sovereignty mechanism is a genuinely new operational principle for plugin architecture, not just a recombination.

## Validation Predictions

- **Monk A:** "Preserves my core insight that physical boundaries resist erosion and that consolidation is irreversible. The stranger test is a better sovereignty criterion than I had — it protects plugins that *will* be independently evolved even if they haven't been yet."
- **Monk B:** "Preserves my core insight that some boundaries are fictions. But I now see that fictionality should be determined by domain analysis, not headcount. If a stranger can contribute to intermux without reading interlock, it's genuinely independent regardless of commit count."

## New Contradictions

1. **The stranger test is subjective.** Who decides whether a stranger "needs" to read sibling docs? The architect's judgment is precisely the thing the synthesis was trying to replace with a mechanism. Is there a way to make the stranger test empirical?
2. **Domain independence may change over time.** A plugin that passes the stranger test today might fail it after a refactor that introduces shared state. Is the classification stable enough to base packaging decisions on?
3. **Agent gateway problem persists.** Even with tiered packaging, the agent still needs to discover and route between plugins. Does the system need an explicit routing layer (Uber DOMA-style) or is Tool Search sufficient?
4. **The tension between sovereign plugins and the monorepo working directory.** If sovereign plugins have their own repos but the architect always works from the monorepo root, does the separate repo actually provide mechanical ratchet benefits? Or does the monorepo nullify the boundary erosion protection?

## Model Update

- **Before:** All plugins deserve the same packaging (either all sovereign or consolidate to ~10).
- **After:** Plugins should have packaging strength proportional to their problem domain's independence (stranger test), not their development history.
- **Because:** The first synthesis confused attention allocation with architectural structure. A plugin with 0 commits but its own problem domain (intermux monitoring) deserves sovereignty if a stranger can work on it independently. A plugin with 50 commits that requires reading 4 siblings to understand is modular regardless of its activity level. Priority is not architecture.
