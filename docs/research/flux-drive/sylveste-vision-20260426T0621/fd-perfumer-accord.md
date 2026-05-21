# fd-perfumer-accord — Review of sylveste-vision.md v5.0

**Lens:** Grasse-trained perfumer in the formal accord tradition.
**Decision question:** If Sylveste is a composition, what are its top notes, heart notes, and base notes — and does the document describe a stable accord or a hopeful list of ingredients?

## Domain Framing
A perfumer composes for time. Top notes are the immediate impression that fade in minutes. Heart notes carry the working middle hour and define what the composition is. Base notes are the long evening that tells you what the perfume actually was. A great accord is judged by its dry-down — what survives twelve hours later. A common amateur error is celebrating an ingredient list while neglecting the proportion and evolution that determine character. Subtraction is the master discipline.

## P0 Findings

### P0-1: The doc has no identifiable heart note
Reading the vision, the immediate impression (top notes) is strong: "evidence that compounds," "earned trust through receipts not claims," "the bottleneck is infrastructure, not intelligence." This is a vivid opening. The base notes are also clear: layered survival, open source, two-brand architecture. But the heart note — what Sylveste actually smells like during the working middle of a sprint — is hard to locate. Is the heart note Clavain's discipline? Skaffen's runtime? The flux-drive review pattern? The interflux fleet? The doc lists six pillars and ten subsystems without naming which one is the working middle. A new reader can recite the pitch and the architecture but cannot answer "what is the daily-driver feeling of using Sylveste."
**Fix:** Designate a heart-note capability — the one thing that, if you removed it, would change what Sylveste is. Candidates: the kernel-driven sprint lifecycle, the evidence-loop discipline, the multi-agent review pattern. Pick one and elevate it as the heart of the accord.

### P0-2: Subtraction discipline is missing
The "Where We Are" section celebrates 64 plugins, 81 modules, ~589 review agents, 17 skills. The "What's Next" section adds six more themes. Nothing in the doc names a sunset, a deprecation, a consolidation, or a removal. A perfumer composing without subtraction produces a muddy blend — every accord clearer than the doc. The plugin count is presented as growth; the cost growth ($1.17 → $2.93) is also presented as growth-in-scope. No countervailing pressure toward simplicity is named at the strategic level.
**Fix:** Add a discipline of subtraction to the vision — e.g., quarterly review of capabilities below a usage threshold for sunsetting; the count is reported alongside an effective-count (proven-tier agents only) so growth and quality are visible separately.

## P1 Findings

### P1-1: SF and garden registers compete on the same surface
"Two brands, one architecture" is the doc's most confident composition claim — Sylveste (SF register) for infrastructure, Garden Salon (organic register) for experience, Meadowsyn as bridge. The doctrine asserts the registers don't mix: "Garden-salon language does not appear in kernel, OS, or plugin documentation." Good — this is a layering claim. But the same vision document mixes registers (Sylveste's heart-note candidate is unclear precisely because the doc tries to do both jobs). A perfumer would say: this is one composition trying to be two perfumes. Either the SF register dominates and the garden becomes a future commitment with its own future doc, or the garden gets a present voice in this doc that the kernel sections don't have.
**Fix:** Either commit the vision doc fully to the SF register and link out to a separate Garden Salon vision (preserving the register layering doctrine), or admit the vision doc is itself the bridge and accept that the layering claim is for downstream artifacts only.

### P1-2: External validation citations function as volatile additions, not base notes
The Symbolica Arcgentica and stigmergy paper citations appear under "External Validation." They support specific claims (orchestration > raw capability; stigmergy scales). But they sit as a sub-section between operational sections, contributing scent that fades — the reader doesn't carry these citations into the rest of the doc. A base-note treatment would weave the validation throughout: when the doc claims layered architecture beats monolithic, the citation is right there.
**Fix:** Distribute external validation into the claims they support, rather than concentrating them in one section. Or designate them as base notes that explicitly bookend the doc.

### P1-3: V4 → v5 evolution shifts the accord and the brand language hasn't caught up
V4 was the routing/evidence-via-Interspect story. V5 expands to four new evidence sources. This is a real composition change — what was a single-distillate evidence story is now a five-ingredient blend. The brand pitch ("evidence that compounds") still works, but the dry-down has changed: the long story is no longer "Interspect makes routing better" but "five evidence sources together produce earned trust." The doc presents this as continuous evolution; from a composition perspective, it's a reformulation that warrants a name change or at least a tasting note.
**Fix:** Acknowledge the v4→v5 reformulation explicitly. Either re-pitch the accord (new heart note, new dry-down) or add a tasting note explaining what changed.

### P1-4: Plugin count celebrated without composition assessment
"64 companion plugins, 81 total modules. Each independently installable." This is the ingredient inventory. A composition assessment would ask: which plugins are top notes (recently added, attention-grabbing), heart notes (the daily drivers), base notes (the deep infrastructure)? Without that breakdown, the count is just a sum. The interflux registry has tier data (stub/generated/used/proven) — that data is not surfaced in the vision.
**Fix:** Decompose the plugin count by tier or usage level. Report the heart of the fleet, not the inventory.

## P2 Findings

### P2-1: "What This Is Not" is a strong base note
The "What This Is Not" section is one of the doc's best — it tells the reader what survives subtraction. This is the closest thing in the doc to subtraction discipline. Build on it.

### P2-2: Origins paragraph is a colophon and reads as one
The Origins section grounds the doc in real prior work (superpowers, etc.). This is a base note in the right place; recommend it stays exactly as is.

### P2-3: Where-we-are over-celebrates count
"1,456 beads tracked, 1,239 closed" reads as growth. A composition assessment would also ask: what fraction of those closed beads represent reversed decisions? The system that builds itself also unbuilds itself, and that signal is invisible in the count.

## Cross-track signal
Converges with **fd-dispatch-economics** on the fleet-bloat / sunset-discipline gap; with **fd-trust-mechanics** on what survives a subsystem replacement (dry-down for trust transfer); with the broader doc-quality observation that count metrics dominate composition metrics.

## Summary
The opening of Sylveste is excellent and the base notes are honest. The middle is muddier — the doc lists capabilities at the level of detail an architect needs without designating which capability defines what Sylveste *is*. Subtraction discipline is the missing master signature. A great accord wears a single character through twelve hours; this composition wears six pillars equally and asks the reader to pick.
