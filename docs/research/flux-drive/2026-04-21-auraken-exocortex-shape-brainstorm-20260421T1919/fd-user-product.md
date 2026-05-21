# fd-user-product — Auraken Exocortex Shape Brainstorm

**Reviewer:** Flux-drive User & Product Reviewer
**Date:** 2026-04-21
**Document reviewed:** `/tmp/flux-drive-auraken-exocortex-1919.md`
**Alignment check:** PHILOSOPHY.md (13 principles), VISION.md, handoff 2026-04-20, CLAUDE.md (Auraken subproject)

---

## Primary User and Job to Be Done

Primary user for Shape A: someone who brings real problems to a text interface and wants questions that crack them open — not summaries, not answers. The handoff calls this "general Auraken users" but that covers too wide a range without a more grounded archetype. The actual committed user is Alex Komoroske: founder, systems thinker, prolific writer, active Flux community participant. He consented to corpus use (with the caveat that proprietary-moat framing needs a direct conversation before his profile goes load-bearing).

Shapes B and C extend from Alex outward. The review below treats "Alex-as-archetype" as a named assumption everywhere, because the brainstorm itself flags this in Assumption 1.

---

## Findings Index

| ID | Priority | Shape | Finding |
|----|----------|-------|---------|
| UP-01 | P0 | B | Self-corpus problem validation is single-user anecdote, not validated pain |
| UP-02 | P0 | B/C | No measurable repeat-use signal defined for either shape — blocks schema v1 decision |
| UP-03 | P0 | A/B/C | Anti-dependency tension with Shape B is real and currently unresolved at schema level |
| UP-04 | P1 | C | Handcrafted-authoring UX has no comparable prior art cited; Evernote-graveyard pattern is strong prior against it |
| UP-05 | P1 | B/C | Pivot cost to Hermes roadmap is understated — corpus ingestion and authoring UX are each standalone product surfaces, not skill-pack additions |
| UP-06 | P1 | A | "General Auraken users" is not a defined segment; Shape A has no validated target user other than Alex |
| UP-07 | P1 | B | "Query your own writing" demo use case (recall) is categorically weaker than the diagnosis use case (inconsistency detection across time) — brainstorm conflates them |
| UP-08 | P1 | C | Profile-sharing legal surface area is presented as a future concern but it gates the network-effect moat that makes Shape C economically viable |
| UP-09 | P2 | C | Validation gate for user-authored profiles is entirely absent — no equivalent to Meadows 12-point rediscovery |
| UP-10 | P2 | B/C | Excluded user segments are not named anywhere in the brainstorm |
| UP-11 | P2 | A | PHILOSOPHY Principle 12 (the profile challenges itself) directly applies to Shape B; brainstorm does not surface this connection |

---

## Verdict

**Shape A** is the only shape ready to move toward schema v1. The problem is real (no AI builds a genuine model of how you think), the evidence is honest (mostly first-principles and Auraken VISION.md thesis, no live user data yet), and the engineering path is clear (thinker-profile schema → extraction pipeline → Meadows gate → fan out). The Hermes pivot absorbs Shape A cleanly.

**Shape B** has a genuine product instinct behind it but fails problem validation. There is one consenting user with one corpus. The most compelling Shape B use case (inconsistency detection across time, not recall) is not the use case that gets built first by default. Schema v1 should accommodate Shape B with a single field (`profile_origin`) but should not block on B's UX or pipeline until at least one concrete use case beyond Alex is interviewed.

**Shape C** is too early and too expensive for this sprint. The authoring UX is a separate product with a documented failure pattern (user-curated knowledge bases that go stale). The profile-sharing legal and consent surface area is not resolved. Shape C should be a named bead at most — not a schema constraint — until Shape A is shipping and Shape B has a second user.

**The schema v1 decision is safe to proceed on Shape A + the `profile_origin` field accommodation, with the recommendation that the schema NOT carry Shape B or C structural assumptions beyond that single field.**

---

## Issues Found

### UP-01 (P0) — Shape B problem validation is a population of one

**What the brainstorm says:** "Power users with substantial personal corpora. Alex's archetype: writer, researcher, anyone with 50K+ words of accumulated thinking who wants their past self queryable."

**The gap:** Alex is the only named, consenting instance. "Anyone with 50K+ words" is a demographic guess. The brainstorm correctly flags this in Assumption 1 ("Alex is representative") but then proceeds to develop Shape B at the same depth as Shape A without resolving the assumption.

**Why it blocks schema v1:** If Shape B structural assumptions enter schema v1 (corpus_origin, user_corpus_path, self_corpus_extraction fields), they represent a design commitment to a product shape with one user's anecdote behind it. The cost is not just engineering time — it's that future validators will assume Shape B is a validated direction and build toward it.

**Recommendation:** Before schema v1 ships, identify whether Shape B's core problem ("my past self is inaccessible to my present thinking") appears in any population beyond Alex. Two sources available without new research: (1) Obsidian/Roam power-user discourse (Reddit, Discord, forums) — these communities have articulated the "can't find my own notes when I need them" pain in extreme detail; (2) PKM tool churn patterns — people who abandon Roam after 6 months often cite "I stopped trusting my own database." If those communities are citing the inconsistency-across-time problem (not just retrieval), Shape B has a validated wedge. If they only cite retrieval, Shape B is in the same graveyard as every other PKM tool.

---

### UP-02 (P0) — No repeat-use signal defined for either Shape B or C

**What the brainstorm says:** Nothing. There is no measurable success signal for "users will actually use this repeatedly."

**Why it blocks schema v1:** PHILOSOPHY Principle 9 is that accumulation creates value — the tenth conversation is better than the first. For Shape A this is survivable because the conversation loop is natural (users keep bringing problems). For Shape B, the repeat-use question is sharper: after the first "query my corpus" session, when does a user return? The natural frequency of "I want to talk to my past self" is unclear. For Shape C, the frequency question is even more fraught: after spending 4 hours building a thinker-profile for a niche philosopher, when does the user get enough value to justify returning?

**Recommendation:** Before any Shape B or C sprint begins, define one metric per shape that distinguishes "used it once out of curiosity" from "uses it because it's load-bearing for their actual work." For Shape B: Does the user initiate corpus-grounded sessions at least once per week after the first month? For Shape C: Does the user's handcrafted profile get invoked in more than 30% of their Auraken sessions after profile completion?

---

### UP-03 (P0) — Anti-dependency tension with Shape B is identified but not resolved at schema level

**What the brainstorm says:** "Shape B risks becoming the engine, not the camera — user leans on Auraken to remember instead of building their own memory." It notes "the line: does retrieval replace the user's thinking, or prompt it?" but leaves the question open.

**Why this is P0:** PHILOSOPHY Principles 1, 2, and 7 (camera-not-engine, preserve cognitive struggle, anti-dependency by design) are not advisory — they are the product's differentiation thesis from every PKM and AI memory tool that has shipped. If Shape B is implemented as "Auraken retrieves your past writing when you need it," it is functionally identical to what Mem, Reflect, and a dozen other AI memory tools already do. The differentiation evaporates.

**The resolution path exists but is not named in the brainstorm.** The camera-not-engine version of Shape B is not retrieval — it is inconsistency detection delivered as a question. Instead of "here is what you wrote about X in March," the Shape B camera version is "you've framed this as a resource problem three times before. The last time you did that, it turned out to be a trust problem. What's different this time?" The user's corpus is used to generate a provocation, not a retrieval result. The user still does the cognitive work. This distinction is not cosmetic — it determines the entire interaction design, the schema fields that need to exist, and whether Shape B actually honors the PHILOSOPHY.

**Recommendation:** The brainstorm should resolve this before schema v1. Concretely: Shape B schema fields should distinguish between `retrieval_mode: prompt` (generates a question using corpus context) and `retrieval_mode: recall` (surfaces a corpus excerpt directly). The product should launch Shape B in `prompt` mode only, with `recall` mode as a deliberate opt-in that triggers a disclosure: "This will surface past writing directly rather than prompting you to think about it." Whether `recall` mode belongs in the product at all is a PHILOSOPHY decision, not a schema decision — but the schema must not foreclose it.

---

### UP-04 (P1) — Shape C handcrafted authoring UX has no comparable prior art cited; Evernote-graveyard pattern is strong prior against it

**What the brainstorm says:** "Handcrafting produces usable profiles. Curation discipline (spotting overfitting, rarity-weighting, scope-metadata consistency) is nontrivial. Asking users to do it well is a UX research question with no data yet."

**The problem:** The brainstorm correctly identifies this as an open question, but doesn't weigh it against available evidence. The Evernote-graveyard pattern is documented: user-maintained knowledge bases with complex internal structure (tags, notebooks, templates) are consistently abandoned within 6-12 months because maintenance cost exceeds retrieval value. The Roam/Obsidian community has a term for this: "second-brain debt." Shape C asks users to perform curation that is more cognitively demanding than Roam tagging — they must evaluate overfitting, apply rarity-weighting, and maintain scope-metadata consistency. These are tasks that even Auraken's internal team (one builder) is treating as nontrivial engineering problems.

**The one exception:** The brainstorm mentions "a dead relative's letters, a fictional character the user wants to dialogue with." These are emotionally motivated corpus inputs, not intellectually maintained systems. Emotional motivation sustains maintenance cost in ways that productivity motivation does not. This is actually the strongest Shape C wedge — not "build a profile of a niche philosopher" but "build a conversational presence from a person who no longer exists." That use case has no competition and carries its own motivation. The brainstorm buries this.

**Recommendation:** Separate Shape C into two sub-shapes: C1 (intellectually motivated thinker-councils, high abandonment risk) and C2 (emotionally motivated presence-building, potentially much stronger). If Shape C gets any sprint attention, start with C2. It validates the pipeline without requiring the full authoring UX, and it has a population of users (grief tech, legacy preservation, family archive projects) that Shape C1 does not.

---

### UP-05 (P1) — Pivot cost to Hermes roadmap is understated

**What the brainstorm says:** "How much of the Hermes pivot needs to harden before exocortex shapes are addressable? Does exocortex pull Auraken back toward a standalone product and away from the overlay?"

**The gap:** The brainstorm names this tension but doesn't quantify it. The Hermes overlay model (personality + MCP + skill packs) maps cleanly onto Shape A: thinker-profiles are MCP server data, the persona is a skill pack, the conversation model is personality configuration. Shape B requires corpus ingestion UX — a new surface that does not exist in the Hermes skill-pack model. It would need either (a) an MCP server that accepts file uploads and runs the extraction pipeline, or (b) a separate web/CLI interface that preprocesses corpora before they are available to Hermes. Either path is a new product surface, not a skill pack. Shape C requires an authoring UX that is even further from the Hermes model — it is essentially a profile editor, which is a standalone tool.

**Concrete cost:** The Hermes pivot has two shipped artifacts (auraken-lens MCP server, auraken personality SKILL.md) and a long unblocked list (sylveste-22oi epic). Shape B work before Hermes stabilizes means either parallel-tracking two surfaces or deferring the Hermes stabilization. That is a strategic sequencing question the brainstorm should answer, not defer to flux-review.

**Recommendation:** Lock Shape B and C out of the current sprint. Schema v1 (sylveste-2xzz) should accommodate them with `profile_origin` but carry no Shape B/C implementation assumptions. The gate for Shape B work to begin is: Hermes overlay is stable enough that a new MCP server (corpus ingestion) can be added without disrupting the core personality + lens server configuration.

---

### UP-06 (P1) — Shape A has no validated target user beyond Alex

**What the brainstorm says:** Shape A "serves general Auraken users — the cognitive-augmentation-companion target."

**The gap:** "General Auraken users" is not a population that currently exists. Auraken has no live users yet (launch deferred per memory note: "Sylveste launch deferred 3 months"). The target user for Shape A is implicitly "Alex, generalized." The VISION.md is detailed about the product thesis and intellectual lineage, but it does not contain evidence that a non-Alex user population has validated the core value proposition (dynamic lens selection + cognitive profile accumulation through conversation).

**This is not a blocker for schema v1** — the schema work is internal infrastructure. But it is relevant to the brainstorm's framing of Shape A as the "validated" shape. It is validated by thesis, by intellectual lineage, and by the quality of its design principles. It is not yet validated by user behavior.

**Recommendation:** The language in the brainstorm should distinguish between "Shape A is the only internally coherent shape" (true) and "Shape A is validated by user evidence" (not yet true). This distinction matters for priority-setting and for how the team communicates confidence levels on each shape externally.

---

### UP-07 (P1) — "Query your own writing" conflates recall and diagnosis; the weak demo is the default

**What the brainstorm says:** Shape B can "recall forgotten connections, surface inconsistency between past-self and present-self, dialogue with user-as-past-thinker, flag when new writing diverges from established voice."

**The problem:** These four capabilities have wildly different product value. "Recall forgotten connections" is retrieval — weak, PKM-style, already done. "Surface inconsistency between past-self and present-self" is diagnosis — strong, differentiating, consistent with PHILOSOPHY. "Dialogue with user-as-past-thinker" is persona construction — novel, potentially powerful. "Flag when new writing diverges from established voice" is editorial assistance — useful but narrow.

The brainstorm lists them as equivalent features. They are not. The weakest one (retrieval) is also the easiest to implement and the most likely to be built first if the shape is not more precisely scoped.

**Recommendation:** The Shape B MVP should be defined as the inconsistency-detection use case, not the retrieval use case. Concretely: user is mid-conversation about a strategic problem; Auraken notices the framing matches a pattern in past writing; Auraken surfaces a question that references the pattern without recalling the text directly. This is the camera version. The retrieval version ("here is what you wrote about this in March") is the engine version and should be explicitly deferred.

---

### UP-08 (P1) — Profile-sharing legal surface is not a future concern; it gates the economic case for Shape C

**What the brainstorm says:** "If profile-sharing ships, consent becomes a product-level legal question, not a curation-ops question."

**The problem:** Shape C's economic case rests on network effects via profile-sharing. Without profile-sharing, Shape C is a premium add-on for lone-wolf researchers — a small market with high support cost. The moat ("platform play") only exists if profiles transfer across users. But the legal surface (third-party corpus extraction → shared profile → downstream users invoke extracted frames) is a chain with at least two unresolved consent steps. The brainstorm notes this but treats it as a future sequencing concern. It is actually a gate on the economic thesis.

**Recommendation:** The Shape C economic thesis should be restated without profile-sharing as a near-term assumption. The restated thesis: "Shape C's moat is the authoring substrate, not network effects. Users will pay for the ability to create bespoke profiles for their own use, even if those profiles are never shared." If that standalone case is compelling enough to justify the authoring UX investment, Shape C has a defensible position. If it requires profile-sharing to be economic, Shape C should be deferred until the legal path is clear.

---

### UP-09 (P2) — No validation gate exists for user-authored profiles in Shape C

**What the brainstorm says:** "Shape C has no validation gate — user-authored profiles ship at whatever quality the user accepts. Does the product need a 'profile health score' surfaced to the user, and what does unhealthy mean?"

**The concern:** The Meadows rediscovery gate (12 leverage points extracted from her essays) is a concrete, verifiable quality bar. A user-authored profile of a niche philosopher has no equivalent anchor — the user is the ground truth, and users reliably overfit to what they find interesting rather than what is structurally distinctive about a thinker's moves. An overfitted profile produces conversations that feel like confirmation bias, not genuine reframing.

**Recommendation:** Shape C should define a minimum profile health check before any authoring UX is built. Candidate check: can the profile, when applied to a problem the thinker never wrote about directly, produce a frame that the user finds surprising and useful rather than merely confirmatory? This is structurally similar to the Meadows gate 2 (applying frameworks from essays where they appear implicitly). If the user can't identify a single surprising application, the profile is too thin or too overfit to be load-bearing.

---

### UP-10 (P2) — Excluded user segments are not named

**What the brainstorm says:** Nothing about who is explicitly excluded.

**Who is excluded by the "Alex archetype":** Users who are not writers by practice, users without substantial prior corpora, users who have not already internalized a frameworks vocabulary (Cynefin, OODA, leverage points), users who prefer concrete task completion over conceptual reframing, users who would experience "inconsistency detection" as criticism rather than insight, users for whom cognitive struggle is not a value but a source of anxiety. This is a large population.

**Why this matters:** Shape A's VISION.md includes "Make systems thinking personal, persistent, and accessible to everyone." The "everyone" claim conflicts with the evident complexity of the onboarding assumption (user already has frameworks vocabulary, tolerates and values the cognitive-struggle experience). The product as designed is accessible to a subset. That subset is real and valuable. The conflict between the mission statement and the actual accessible population should be named, not hidden.

**Recommendation:** The mission's "everyone" should be qualified in internal product docs as "anyone willing to engage with structured reframing" — which is still a large market but is honest about what the product requires of users. This is not a UX fix; it's a positioning clarity fix that prevents scope creep from trying to broaden accessibility in ways that undermine the core experience.

---

### UP-11 (P2) — PHILOSOPHY Principle 12 applies directly to Shape B and is not surfaced

**What the brainstorm says:** Nothing.

**What Principle 12 says:** "The cognitive profile is not a growing collection of facts. It is a living model with confidence levels, evidence thresholds, and active invalidation... Stale models are more dangerous than thin models."

**Why this matters for Shape B:** A user's self-corpus is a historical artifact. Writing from two years ago may describe beliefs the user has since revised. If Shape B ingests a corpus without temporal confidence weighting, the profile will treat two-year-old frames as equivalent to current frames. A "dialogue with user-as-past-thinker" interaction pattern makes this concrete and valuable. But an "inconsistency detection" interaction pattern that flags a contradiction between past and present writing — without distinguishing between "this is a genuine unresolved contradiction" and "you changed your mind and the profile doesn't know it yet" — will feel like a malfunctioning system, not a useful mirror.

**Recommendation:** Shape B schema should include temporal confidence weighting on extracted frames — corpus items have a date, and frames extracted from older corpus items should carry lower confidence until corroborated by newer material or by user acknowledgment. This is an extension of Principle 12's epistemic status ladder (speculative → emerging → established → confirmed) applied to time-indexed corpus inputs. This is a schema-level decision that should be included in sylveste-2xzz scope if Shape B's `profile_origin` field is included.

---

## Improvements

**Improvement 1: Name the smallest testable slice per shape**

Shape A MVP: one thinker-profile (Meadows) extracted, validated against the 12-point gate, applied invisibly in five real conversations, and measured by whether the user's framing shifts (not whether they report satisfaction). This is already the defined critical path. Confirm it explicitly.

Shape B MVP: one session where a user's past writing is used to generate a single question (not a retrieval result) that the user finds surprising and useful. Success signal: the user says some version of "I hadn't connected those." This can be tested with Alex as the sole user. Single session, single corpus, no authoring UX, no ingestion pipeline — just a manually prepared extraction fed into a prompt. If that interaction does not feel different from a session without the corpus, Shape B has a fundamental problem that no pipeline will fix.

Shape C MVP: one user-authored profile of an emotionally significant person (not an intellectual thinker-council), applied in three conversations. Success signal: user initiates a Shape C session unprompted in week two. This tests whether the motivation sustains beyond novelty. Cannot be tested with Alex — requires finding one Shape C user who is not already in Auraken's intellectual orbit.

**Improvement 2: Resolve the retrieval/prompt split before schema v1 locks**

Schema v1 should carry a field that distinguishes Shape B interaction modes at the schema level, not as a post-hoc UX decision. Proposed field under the corpus section:

```
corpus_interaction_mode: prompt | recall | both
```

`prompt` mode: corpus is used to generate questions only. User never sees a direct retrieval result.
`recall` mode: corpus excerpts can be surfaced directly. Triggers disclosure.
`both`: user can invoke either. The schema records which mode is active per session.

This is a one-field addition that prevents the default implementation from landing in `recall` mode because it was easier to build.

**Improvement 3: Separate Shape C into C1 and C2 before any sprint planning**

C1 (intellectual thinker-councils): High authoring UX cost, high abandonment risk, requires profile-sharing for network effects, legal surface unresolved. Not ready.

C2 (emotionally motivated presence-building): Lower authoring UX cost (user is deeply motivated, tolerates friction), no profile-sharing required, consent is clean (user owns or has clear personal claim to corpus), no Meadows-style validation problem (user is the ground truth). Potentially ready as a spike after Shape A ships.

**Improvement 4: Add a pivot-cost gate to the brainstorm**

The brainstorm's Tension 6 names the Hermes pivot cost but defers resolution to this review. The gate should be explicit: Shape B and C sprint work is blocked until the Hermes overlay is stable enough that a new MCP server can be added without disrupting the core configuration. Concretely, this means: auraken-lens MCP server is deployed and stable on zklw, auraken personality SKILL.md is loaded and validated in at least five real sessions, and sylveste-heh8 deployment bead is closed. Until those three conditions hold, exocortex shapes are a named future direction, not an active sprint track.

---

## Summary

The brainstorm is well-structured and intellectually honest about its assumptions. The three-shape framing is useful. The tensions section is the strongest part — it names the real conflicts rather than papering over them.

The core product-review concern is that Shape B and Shape C are not yet ready to influence schema v1 decisions beyond a single `profile_origin` field. Shape B's problem validation rests on one user. Shape C's economic thesis requires profile-sharing, which is legally unresolved. Both shapes require new product surfaces (corpus ingestion UX, authoring UX) that are orthogonal to the Hermes-overlay pivot and would compete for sprint capacity.

The anti-dependency tension with Shape B is the sharpest finding. If Shape B lands as a retrieval system, it violates the product's core differentiation from every AI memory tool already on the market. The camera version of Shape B (inconsistency detection delivered as a question) is both philosophically coherent and genuinely differentiating — but it requires an explicit design decision at the schema level, not just a product-intent footnote.

Schema v1 should proceed on Shape A. The `profile_origin` field should accommodate Shape B and C without carrying their structural assumptions. The smallest testable slice of Shape B can be manually piloted with Alex without any schema work. Shape C should be deferred to a named bead.

<!-- flux-drive:complete -->
