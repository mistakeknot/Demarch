---
artifact_type: brainstorm
bead: sylveste-248r
stage: design
status: FOR REVIEW — not implemented
date: 2026-06-22
author: backlog design-draft agent (autonomous)
---

# Auraken Onboarding — Intake Flow + Bootstrap Protocol (design draft)

**Bead:** sylveste-248r (P0, `ux`, in_progress) — "Onboarding: intake flow + three-message bootstrap protocol"

**This is a design draft for human review. No code has been written. Several of the bead's premises conflict with the shipped Auraken architecture; this doc surfaces those conflicts and proposes a reconciled design rather than implementing the bead as literally worded.**

---

## 1. Problem

The bead proposes a two-part onboarding:

1. **Optional web intake** at `auraken.org/start` collecting name, age range, location, pronouns, "what brought them here," and "what domains they think about most." Seeds a profile before the first message.
2. **Three-message bootstrap arc** in conversation: msg 1 warm intro + specific question; msg 2 reflect + stakes; msg 3 first reframe. System prompt varies by bootstrap phase. Builder gets a fast-track.

The underlying real problem is genuine and independently confirmed by the 2026-03-30 flux-review (P1-1, "No cold-start strategy for dynamic lens selection"):

> "3 of 5 selection inputs require a profile that does not exist for new users. The first session degenerates to keyword search over a framework database. The first-session experience is the only chance to demonstrate value."
> — `docs/research/flux-review/auraken-use-case-landscape/2026-03-30-synthesis.md:53-61`

So: **a new user's first session is the highest-value, lowest-context moment, and the current design has nothing to bridge that gap.** That is the problem worth solving.

However, the bead was written against an *earlier product conception* (a hosted web companion app with a persistent profile store). Between then and now, Auraken pivoted to a **Hermes Agent overlay** distributed as a self-installed bundle. Three of the bead's mechanisms — web intake, profile seeding, phase-varying system prompts — assume infrastructure that the shipped product **does not have**. This draft's main job is to reconcile the intent with the architecture.

---

## 2. What actually ships today (verified against code/docs)

### 2.1 Auraken is a Hermes skill + a stateless lens MCP, not a hosted app

The shipped distribution (`apps/Auraken/integrations/hermes/dist/v0.1/`) is:

- **A SKILL.md** the user copies into their own Hermes profile (`skills/auraken/SKILL.md`).
- **An `auraken-lens` MCP server** that shells out to a Go binary and returns a single object `{lens, rationale, next_question}` (or `{empty: true}`).

Sources:
- PRD `docs/prds/2026-05-25-auraken-distribution-v01.md:14-15` ("Ship Auraken as a v0.1 distribution bundle: a self-contained, versioned directory … installable via a tagged GitHub release").
- Brainstorm `docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md:14-18` ("Auraken is shipped as a self-contained directory … anyone with a working Hermes install can drop into their setup").

**There is no `auraken.org` web frontend in any repo.** Searched `/Users/sma/projects` for `*auraken*web*`, `.tsx` under auraken paths, and `auraken.org/start` references in docs — zero hits. The public-flip audit (`docs/audits/2026-05-27-auraken-pre-public-flip-audit.md`) discusses only a private GitHub repo + release attachments; a landing page is explicitly **out of scope** (PRD line 144: "Landing page (auraken-web is separate)").

### 2.2 The current opening behavior is the *opposite* of a "warm intro"

The live SKILL.md (extracted from the 2026-04-20 backup, `home/mk/.hermes/skills/auraken/SKILL.md`) is explicit and load-bearing:

> "On invocation (`/auraken` with no problem stated), respond with a single short open question and stop. … No status announcement … no preamble, no list of problem types one could bring, **no description of what Auraken does.** The user invoked Auraken; they know what it's for."
> — SKILL.md:14

> "Never offer a menu of problem types the user could bring. **Never describe what Auraken does to them; demonstrate it.**"
> — SKILL.md:20

> "On thinking-through turns … the first move is a question, not a frame. Skip classifications ('this is a case of X'), preambles ('you're really asking about Y'), and pre-engagement summaries. They are answering-first in disguise."
> — SKILL.md:16

This is also geometrically enforced in v0.1: the "soundpost" decision makes the lens MCP return a *single object*, so there is structurally no menu to render (PRD line 15; brainstorm line 39).

**This is a direct contradiction with the bead's "msg 1 = warm intro + specific question."** A warm intro that explains/welcomes is exactly the "preamble / capability statement" the voice forbids. The "specific question" half is compatible; the "warm intro" half is not, as worded.

### 2.3 There is no persistent profile store to "seed"

v0.1 ships with **no cross-session memory**:

- Thinker-profile MCP (the reasoning-frame extraction layer) is deferred to **v0.3** (PRD Non-goals line 138; brainstorm line 157).
- Trajectory capture is file-based JSONL only, and is itself a v0.1 open question, not a queryable profile (brainstorm Open Questions #6, #7; PRD Non-goals line 143).
- The `lens_select` MCP call is **stateless** — it takes the current message and returns lenses; nothing in SKILL.md describes reading a stored profile.

So "Seeds profile before first message" has **no store to write into** in the shipped architecture. The flux-review already flagged this: a profile "does not exist for new users" and even the *bootstrapped* minimal profile only materializes "by conversation 2" (synthesis line 59) — and that finding assumed the older hosted-app design that has since been deferred.

### 2.4 Auraken ≠ Amtiskaw

Memory notes (referenced in the distribution brainstorm Provenance, line 172) distinguish Auraken (the public cognitive-augmentation product) from Amtiskaw (mistakeknot's personal agent). "Builder gets fast-track" in the bead likely means the product author / a builder persona — this needs the human to confirm which it is, because it changes whether the fast-track is a maintained feature or a personal convenience.

---

## 3. The core reconciliation question

> **Is this onboarding bead for the shipped Hermes-overlay product, the deferred hosted product (v0.2 demo / future web app), or both?**

The mechanisms cleave cleanly along that line:

| Bead mechanism | Hermes-overlay (today) | Hosted web app (deferred) |
|---|---|---|
| `auraken.org/start` web intake form | **N/A** — no web surface | Yes, the natural home |
| Seed profile before first message | **N/A** — no profile store | Yes, once thinker-profile (v0.3) exists |
| Three-message bootstrap arc | **Partially viable** — but must be SKILL.md prose, not phase-varying system prompts | Yes, with phase state in the app |
| System prompt varies by bootstrap phase | **N/A** — Hermes loads SKILL.md statically; Auraken cannot mutate its own system prompt per turn | Yes, the app controls the system prompt |
| Builder fast-track | Possible via an env flag / alt SKILL variant | Possible via the intake form |

This is the **single most important decision** the human must make, because it determines whether this is a ~half-day SKILL.md edit or a multi-sprint feature that depends on v0.2/v0.3 infrastructure.

This same pattern — proposing a design against a remembered architecture that has since shipped differently — is exactly what sibling bead **sylveste-sk5s** (shipped-state reconciliation gate) exists to catch. I flag it here per that bead's intent.

---

## 4. Proposed design

I propose splitting the bead into **two tracks** that map to the two product surfaces, and shipping the cheap, high-value one now.

### Track A — "Bootstrap discipline in SKILL.md" (shippable against current product)

A new **`## Onboarding` section in SKILL.md** that encodes a *first-session arc* as voice discipline, not as system-prompt phase machinery. The shipped product has no way to vary its system prompt per turn, so the arc must live as guidance the model follows within the single static skill.

Concretely, the arc maps the bead's three messages onto the existing OODARC turn structure, honoring the no-preamble / no-menu / question-first rules:

- **Turn 1 (cold open).** Keep the existing single short open question (`"what are you working through?"`). The *only* onboarding-specific change: when there is no prior context in the conversation (genuine cold start), the opening question may be **slightly more inviting in register** (warmth via tone, never via preamble) — e.g. still one sentence, still a question, no "welcome to Auraken." This satisfies "warm" without violating "no preamble / never describe what Auraken does."
- **Turn 2 (reflect + stakes).** After the user's first substantive message, before reaching for a lens, surface a **specific reflection grounded in their own words** plus a stakes-clarifying probe. This is the existing "Reflections" move (SKILL.md:72) pulled earlier in the relationship to do double duty as light calibration. This is also where the flux-review's "2-3 calibration questions" intent (synthesis line 59) lands — but framed as *one* organic probe, not a survey, to stay inside the voice.
- **Turn 3 (first reframe).** Deliver the first genuine lens-driven reframe-as-question via the normal `lens_select` path. The bead's "first reframe" is just the normal product working — the onboarding contribution is *sequencing* (don't reframe before you've reflected and understood stakes), not a new behavior.

Critically, this is **soft sequencing, not a state machine.** The model already adapts depth per turn ("Adaptive depth," SKILL.md:40). Onboarding guidance biases the first three turns toward reflect-before-reframe; it does not hard-gate. A user who arrives with a fully-formed problem and wants an immediate reframe gets it — preserving the "match the user's register" rule (SKILL.md:68).

**Why prose-discipline and not system-prompt phases:** Hermes loads SKILL.md as static instruction; Auraken cannot rewrite its own system prompt between turns. "System prompt varies by bootstrap phase" is simply not a capability of the overlay. The equivalent that *is* achievable is "the skill instructs the model to treat the first three substantive turns as a bootstrap arc." That is the honest, shippable version of the bead's intent.

**Builder fast-track (Track A version):** an `AURAKEN_BOOTSTRAP=off` env var (read by the install/SKILL wiring) that skips the onboarding sequencing for users who already know the product. Cheap, optional, reversible. Confirm with human whether "builder" means this.

### Track B — "Web intake + profile seeding" (deferred; depends on v0.2/v0.3)

The literal bead — `auraken.org/start` form, profile seeding before first message, phase-varying system prompts — is a **hosted-app feature**. It should be re-filed as a child of the v0.2 demo-instance work (the deferred sub-bead under sylveste-heh8) and the v0.3 thinker-profile work (sylveste-i0px), because:

- It needs a web surface that does not exist (`auraken.org`).
- It needs a profile store that is explicitly deferred to v0.3.
- It needs app-controlled system prompts, which the overlay cannot provide.

Track B's design, when its dependencies land:

- **Intake form** collects the bead's fields (name, age range, location, pronouns, "what brought you here," "domains you think about most"). Two cautions from the flux-review carry directly here:
  - **Privacy / contextual integrity** (synthesis P1-5, line 96): collecting domains up front risks cross-domain linking the user never consented to. The form must scope what each field is used for, and domains should be opt-in per-domain, not a single blanket capture.
  - **GDPR lifecycle** (synthesis P0-1, line 19): any stored intake profile needs deletion/export from day one. An intake form is the first place PII enters the system.
- **Profile seeding** writes the intake into the thinker-profile store as **low-confidence, self-reported** entities (epistemic status `speculative`, per synthesis P1-11, line 162) — explicitly *not* treated as established patterns, and phrased as questions when surfaced, so a self-reported "I'm an analytical thinker" doesn't get injected as fact.
- **Phase-varying system prompt** is legitimate here because the app owns the prompt. The three-message arc becomes real state (`bootstrap_phase ∈ {1,2,3,done}`) the app tracks and uses to select prompt variants.

---

## 5. How this composes with existing flux-review findings

The 2026-03-30 synthesis is the authoritative source on what onboarding must respect. Mapping:

- **P1-1 cold-start** (line 53) — Track A directly addresses the "first session degenerates to keyword search" failure by sequencing reflect-before-reframe so the first session demonstrates the reflection capability even with zero profile.
- **Concierge-medicine "domain-triggered intake"** (line 416) — the right pattern for Track B: intake is *per-domain and just-in-time*, not a giant upfront form. This argues against collecting "domains you think about most" all at once in the web form; collect lightly, deepen per-domain on first use.
- **P1-3 distress circuit breaker** (line 74) and **P1-8 competence boundary** (line 129) — onboarding is a likely entry point for users in acute distress ("what brought you here" can surface a crisis). The bootstrap arc must defer to the distress/boundary rules: if turn 1 surfaces acute distress, drop the bootstrap sequencing and follow the competence-boundary protocol instead.
- **P1-11 epistemic confidence** (line 162) — intake data is self-reported and must enter at the lowest confidence tier.

---

## 6. Recommendation

1. **Ship Track A now** as a SKILL.md `## Onboarding` section (soft three-turn bootstrap sequencing + optional builder bypass). ~Half-day, reversible, no new infra, demonstrably improves the first-session experience the flux-review flagged.
2. **Re-file Track B** (web intake + profile seeding + phase-varying prompts) as children of the deferred v0.2 demo and v0.3 thinker-profile beads. Do **not** build it against the current overlay — it has no surface to live in.
3. **Do not implement the bead as literally worded.** `auraken.org/start` and "seeds profile before first message" describe infrastructure that does not exist; building stubs for it now would be sunk work.

---

## 7. Decisions the human must confirm

1. **Product surface scope.** Is sylveste-248r for (a) the shipped Hermes overlay only, (b) the deferred hosted app only, or (c) both, split into Tracks A and B as proposed? *(This is the load-bearing decision; everything else follows from it.)*
2. **Warm-intro vs. no-preamble.** The bead says "msg 1 = warm intro." The shipped voice forbids preamble and self-description. Confirm that "warm" should be delivered through *register/tone of the single opening question*, not through a welcome/explainer. (If the human actually wants a real welcome message, that is a deliberate voice-doctrine change to SKILL.md and should be made consciously.)
3. **Soft sequencing vs. hard phase machine.** Confirm the bootstrap arc should be *soft guidance* (model biases first three turns, but a ready user can jump straight to a reframe), not a hard-gated state machine that withholds reframes until turn 3.
4. **"Builder gets fast-track" — what is "builder"?** The product author? A "builder/maker" user persona? An internal dogfood path? This determines whether the fast-track is a maintained product feature or a personal convenience env flag (and whether it belongs in the public bundle at all).
5. **Bead disposition.** OK to (a) narrow sylveste-248r to Track A, and (b) file Track B as new children of the v0.2/v0.3 beads? Or keep 248r as the umbrella and add Track A/B as children?

## 8. Open questions

1. **Calibration depth.** The flux-review suggests "2-3 calibration questions" by conversation 2. Track A proposes *one* organic probe to protect the voice. Is one enough to bootstrap useful lens selection, or does cold-start lens quality actually need more explicit calibration (trading some voice purity for selection accuracy)? This is an empirical question — wants a measurement once Track A is live.
2. **Does turn-1 register-warmth survive the soundpost contract?** The lens MCP returns `{empty: true}` on a cold `/auraken` with no problem stated, so turn 1 is pure SKILL.md behavior. Confirm the install-time "transmissive close" (PRD F4 step 6) and the turn-1 opening don't double up into something that reads as preamble.
3. **Where does bootstrap state live for Track A?** Track A claims "no state," relying on the model reading conversation length from context. Is that reliable across Hermes context-window resets and long sessions, or does even soft sequencing need a tiny trajectory marker ("bootstrap complete")? Leaning no-state for v0.1 simplicity; flag if that proves flaky.
4. **Builder fast-track in a public bundle.** If "builder" is the author, should an `AURAKEN_BOOTSTRAP=off` path even ship in the public distribution, or stay an internal-only override? (Distribution-hygiene question — the public bundle is meant to be audience-neutral, per PRD Non-goals line 145.)
5. **Track B privacy default.** When Track B is built, is intake-profile capture opt-in (user must enable) or documented-opt-out? Mirrors the unresolved trajectory-disclosure question from the distribution brainstorm (Open Question #7) — should be decided consistently across both.

---

## Provenance / sources verified

- Bead `sylveste-248r` — read from `.beads/issues.jsonl` (P0, in_progress, label `ux`, no parent).
- Live opening behavior — `home/mk/.hermes/skills/auraken/SKILL.md` extracted from `migration-notes/backups/zklw-auraken-20260420-201328.tar.gz` (lines cited inline).
- Distribution architecture — `docs/prds/2026-05-25-auraken-distribution-v01.md`, `docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md`.
- Cold-start / onboarding-adjacent findings — `docs/research/flux-review/auraken-use-case-landscape/2026-03-30-synthesis.md` (P1-1, concierge-intake, P1-3/5/8/11).
- Public-flip / no-web-surface confirmation — `docs/audits/2026-05-27-auraken-pre-public-flip-audit.md` + filesystem search (no `auraken.org`/web frontend in repo).
- Vision frame — `docs/brainstorms/2026-03-30-auraken-vision-expansion-brainstorm.md`.
- Reconciliation-gate intent — sibling bead `sylveste-sk5s`.
