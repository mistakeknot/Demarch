<!-- flux-run-uuid: 3507b048-2a14-484a-ad19-b1066bab6c97 -->
<!-- dispatch-mode: orchestrator-embodied (Task tool unavailable in nested skill context) -->

### Findings Index
- P1 | C-1 | "Tier 2 (voice/style conditioning) + Tier 2 (project artifact generation)" | Voice (interfluence) and philosophy (interlore) are one missing primitive: the bani stamp
- P1 | C-2 | "Initial findings #7 (managed AGENTS.md) / Cross-vendor angle" | Cross-vendor AGENTS.md transmission strips lineage
- P1 | C-3 | "Initial findings #1 (memory graduation)" | Manodharma petrified as kriti — session-specific improvisation graduates to durable doctrine
- P1 | C-4 | "Anti-patterns / structural reframing" | Missing teaching-chain primitive — plugins inherit from skills with no navigable lineage
- P2 | C-5 | "Specialty / niche grouping (interlens, interfluence, interlore)" | No gharana-affiliation in marketplace — plugin lineage commitment is invisible
- P1 | C-6 | "Initial findings #2 (parallel fleet) + #5 (code recon)" | Skill/agent inheritance has no parampara stamp — derivative agents lose their teacher's bani
- P2 | C-7 | "Plugin / skill development grouping" | Skill-authoring plugins (interskill, interplug) do not enforce kriti/manodharma layering

Verdict: needs-changes

---

## Summary

The prior pass treats voice (interfluence) and philosophy (interlore) as separate tier-2 candidates. From the parampara lens these are one primitive: the **bani stamp**. A Carnatic vidwan's authority comes from a named lineage commitment that constrains improvisation within the bani's character while leaving specific notes free. Sylveste plugins inherit from skills, which inherit from project doctrine, which inherits from PHILOSOPHY.md — but nowhere is the lineage navigable, attributable, or signed. The result is that downstream agents cannot tell which improvisations are bani-faithful and which are foreign. The structural reframing: voice + philosophy + skill-inheritance + AGENTS.md authorship are all aspects of one absent primitive — the lineage-stamped artifact.

## Issues Found

### 1. P1 | Voice and philosophy unify as the bani stamp

Tier 2 lists voice/style conditioning and project artifact generation as separate candidates. Sylveste already has interfluence (voice) and interlore (philosophy observer). These look like adjacent concerns. From the parampara lens they are one concern: the substantive commitment to a bani that constrains both how you write (voice) and what design moves are coherent (philosophy).

A Carnatic vidwan does not have a "voice" separate from a "philosophy." Their bani determines both — the gamakas (ornamentations), the kalpana svaras (improvisation patterns), the choice of compositions, the teaching emphasis. A vidwan trained in the Semmangudi bani sounds different from one in the Madurai Mani bani because their bani commits them to different aesthetic-and-structural choices simultaneously.

Failure scenario: An agent writes documentation in Sylveste's voice (interfluence applied) but proposes a design move that violates Sylveste's philosophy (interlore would have caught it). The voice surface looks correct; the underlying commitment is foreign. The artifact passes voice review and fails philosophy review — but the user has to run both, and the cross-check is not enforced.

Fix: Native primitive — the **bani stamp** — that unifies voice profile and philosophy commitment as a single signature on artifacts. interfluence and interlore become two interfaces against one primitive, not two primitives. Cross-check is automatic: an artifact stamped with bani X is rejected if its voice OR its philosophy violates the bani's character.

This is a structural reframing the prior pass missed by treating voice and philosophy as adjacent rather than identical at the primitive level.

### 2. P1 | Cross-vendor AGENTS.md strips lineage

The review's strategic-angle question asks about cross-vendor AGENTS.md adoption. From the parampara lens, the risk is that AGENTS.md authored under one project's bani is consumed by Codex, Cursor, Gemini without the bani signature surviving the transmission.

A kriti detached from its bani is just notes. A Carnatic recital where the vidwan's bani is unattributed is musically incoherent — the listener cannot tell which choices are tradition-faithful and which are deviation. AGENTS.md without a bani stamp behaves identically: a Codex agent reading Sylveste's AGENTS.md cannot tell which patterns are core (kriti) and which are local Sylveste improvisation (manodharma).

Failure scenario: Sylveste's AGENTS.md says "every action produces evidence." A Codex agent reading this in 2027 cannot tell if "evidence" means hook events (Sylveste-specific) or audit logs (general practice). Without the bani stamp, the agent guesses. The behavior diverges silently from what Sylveste's authors intended.

Fix: Cross-vendor AGENTS.md standard must include a `parampara` or `lineage` field that names the bani (PHILOSOPHY.md hash, source skill chain, original authoring agent identity). Receiving agents under a different bani treat the lineage-stamped sections as kriti (preserve verbatim) and produce their own manodharma (improvisation) explicitly tagged as such.

This is a strict requirement on the prior pass's #7 — managed AGENTS.md without lineage is the kriti-detached-from-bani failure.

### 3. P1 | Manodharma petrified as kriti

intermem auto-memory graduates session-specific facts to AGENTS.md. interlore proposes PHILOSOPHY.md updates from observed pattern drift. From the parampara lens, both risk transcribing a vidwan's manodharma (this performance's improvisation) as if it were the underlying kriti (the fixed composition).

A session-specific judgment ("this codebase prefers 4-space indentation") is manodharma — a performance choice in this session's context. If it graduates without the improvisation marker, downstream agents treat it as kriti and propagate it as if it were core grammar.

Failure scenario: A 2026 session about a frontend project graduates the auto-memory fact "uses Tailwind v3." By 2027 the project migrated to Tailwind v4. Agents read the petrified fact as kriti and write v3-syntax CSS. The improvisation is now corrupted doctrine.

Fix: Memory graduation must preserve the kriti/manodharma distinction explicitly. Every graduated fact carries `layer: kriti | manodharma` and a bani-stamp. Manodharma facts can be project-local but never become cross-project canon. Kriti facts require multi-session corroboration AND explicit promotion (not auto-graduation).

This complements the registrar/portolan findings (M-3, P-4) — append-only persistence and observed-vs-inferred classes are necessary but not sufficient. The kriti/manodharma distinction is the *layer* axis on top of those.

### 4. P1 | Missing teaching-chain primitive

A Carnatic disciple can name their teacher's teacher's teacher. This chain is the public warrant for their authority. In Claude Code, plugins inherit from skills, skills inherit from project doctrine, project doctrine inherits from PHILOSOPHY.md. But this inheritance is not navigable.

The review's success criterion #2 asks for a structural reframing of the prior 7 as instances of X. From this lens, the X is: 5 of the 7 are aspects of *missing teaching-chain primitive* — durable memory (chain of facts), parallel fleet synthesis (chain of agent contributions), AGENTS.md (chain of conventions), routing calibration (chain of decisions), task tracker (chain of work).

Failure scenario: A user adopts a Sylveste plugin (e.g., interflux). It depends on conventions in PHILOSOPHY.md. The user does not know this. Their AGENTS.md does not have the parampara stamp. interflux behavior diverges from Sylveste's intent. Debugging requires walking back through five layers of implicit inheritance.

Fix: Native primitive — the **lineage chain** — that makes inheritance navigable. Every artifact (plugin, skill, agent, AGENTS.md, PHILOSOPHY.md) declares its parents. A `lineage_for(artifact)` query returns the full chain. This complements the registrar finding (M-1) — accession joins horizontally across plugins; lineage joins vertically through inheritance.

The structural reframing: registrar (M-1) + lineage chain are the two skeletal primitives the prior 7 implicitly assume.

### 5. P2 | No gharana-affiliation in marketplace

Carnatic vidwans are publicly identified with their bani. The marketplace (concert circuit, recordings, reviews) treats bani as a substantive commitment that licenses certain interpretations. Sylveste's plugin marketplace has no gharana surface — plugins are listed by name and category, not by bani affiliation.

Failure scenario: Two memory plugins exist with the same surface API. One commits to append-only provenance; the other allows in-place updates. A user picks based on README. The bani difference (which determines fitness for chain-of-evidence applications) is invisible.

Fix: Marketplace primitive — `bani` or `lineage` field on plugin manifests that names the doctrinal commitments. Plugins committed to "append-only / closed-loop / receipts-not-narratives" are findable by that commitment, not just by feature name.

This is a marketplace economics observation that the strategic-angle success criterion missed: bani affiliation is a competitive moat for plugins and a retrieval axis for users.

### 6. P1 | Skill/agent inheritance lacks parampara stamp

flux-gen generates agents from task prompts. These agents inherit from a parent agent template, which inherits from a skill, which inherits from project doctrine. The generated agent files (e.g., the four distant-domain agents under review) carry minimal lineage metadata — `source_spec`, `generated_at`, `flux_gen_version` — but no bani stamp pointing to the doctrinal chain that authorizes the agent's claims.

Failure scenario: A user copies a Sylveste-generated agent into their own repo. The agent's lens depends on PHILOSOPHY.md commitments (closed-loop, evidence chain, appendable provenance). In the new repo without those commitments, the agent's findings reference doctrine that doesn't apply. The findings still feel authoritative because the agent's prose is.

Fix: flux-gen output must include a parampara field — explicit pointers to the project doctrine, the originating spec, and the bani commitments the agent's lens presupposes. Receiving environments check the bani against their own; mismatches surface as warnings.

### 7. P2 | Skill-authoring plugins do not enforce kriti/manodharma layering

interskill, interplug, and interpub are the skill-authoring stack. None enforces the kriti/manodharma distinction in skill design. Skills mix mandatory steps (kriti — must run verbatim) and improvisation guidelines (manodharma — adapt to context) without formal layer marking.

Failure scenario: A skill author writes "always run X" intending kriti. A downstream user's agent treats it as guidance and skips it under context pressure. The skill's behavior degrades silently.

Fix: SKILL.md schema includes explicit kriti/manodharma layer markers per step. Authoring-stack plugins enforce the markers at validation time.

This is a small fix that compounds — every existing skill that adds the markers becomes more reliable across users.

## Improvements

1. Unify interfluence and interlore as a single bani-stamp primitive. Voice + philosophy = one commitment surface.
2. Add `parampara` / `lineage` field to AGENTS.md cross-vendor schema. Lineage stripping at vendor boundaries is the kriti-detached-from-bani failure.
3. Memory graduation must preserve kriti/manodharma layer. Auto-graduation of manodharma is the petrification mistake.
4. Add `lineage_for(artifact)` as a native query. Make inheritance navigable.
5. Add `bani` field to plugin manifests for marketplace retrieval and competitive differentiation.
6. flux-gen output requires parampara metadata pointing to the doctrinal chain.
7. SKILL.md schema enforces kriti/manodharma layer markers per step.

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 7 (P0: 0, P1: 5, P2: 2)
SUMMARY: Voice and philosophy unify as one missing bani-stamp primitive; cross-vendor AGENTS.md strips lineage at vendor boundaries; auto-memory graduation petrifies manodharma as kriti. The structural reframing: 5 of the 7 prior targets are aspects of a missing teaching-chain primitive complementary to the registrar.
---

<!-- flux-drive:complete -->
