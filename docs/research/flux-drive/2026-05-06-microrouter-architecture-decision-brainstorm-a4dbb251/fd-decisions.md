# fd-decisions findings — microrouter architecture decision brainstorm

## P0 findings

None

## P1 findings

### Finding 1 — Reversibility framing obscures a hard fork commitment (P1)

The document frames the deferral as "shelved" (α) and "preserved as a contingency" (γ), suggesting clean state. However, the decision creates an irreversible fork:

- **`.19.8` state is now locked into "α-as-v0 was explored but not implemented."** The bead is closed with α-v0 commit in place. Future work re-opening this bead will inherit that framing. Even though "no `.19.2`/`.19.3` started," the design-time work that led to `.19.8` closure (the findings from 2026-05-04/05 brainstorms, the schema revisions) is now deprecated-in-place — not deleted, but superseded. A future reader re-visiting `.19.8` will find circular reasoning: "why is this closed if α-v0 is in the code?" Answer: "because we deferred to β." That answer only makes sense if someone later re-reads the entire `.19.10` handoff. Without that, the state is opaque.
- **γ-as-contingency without contingency conditions is a footgun.** Section "Why γ is preserved" lists three triggers (label noise >30%, volume < N, strategic priority flip). But only trigger 1 is measurable by a machine reading interspect logs. Triggers 2 and 3 are human judgment calls. If `.19.9` ships and telemetry is noisy, who decides "noisy enough"? The document pre-registers "~30%" as a placeholder but explicitly says "TBD." That means the decision point isn't actually deferred — it's delegated to a future moment with no pre-committed threshold. Result: either the thresholds get hardened later (adding friction), or someone has to make a judgment call in crisis mode when β telemetry is failing.

**What would help:** Lock `.19.8` body to a note saying "α-v0 exploration complete; see `.19.10` for decision deferral to β." This makes `.19.8` an immutable record rather than a state that misleads future readers. And hardcode the contingency thresholds in the body of `.19.9` (the telemetry bead) rather than leaving them as placeholders in `.19.10`.

---

### Finding 2 — Sunk-cost semantics: "zero cost" today is true, but hides buried cost of `α` design work (P1)

The document correctly notes "None of `.19.2`/`.19.3`/`.19.4` has started" so re-entry cost = zero. But this misses a category of sunk cost that *is* real:

- **`.19.8` itself (the design revision) spent 3–5 days absorbing findings P0-B/C/D/E from a full flux-review.** That work was spent to *establish α-as-v0* with justified corrections (calibration freeze, held-out-agents, per-tier recall gates). Now α is shelved, so those corrections are documented but not implemented. Some of them (like the per-tier recall gate) will carry forward to β, so they're not wasted. But others (the judge family separation for α specifically) are now orphaned.
- **The real re-entry cost if α ever resurrects:** Someone has to re-read `.19.8`, the 2026-05-04 brainstorm, and the 2026-05-05 revision to understand why α was chosen, what constraints were placed on it, and why it's suddenly being revived. That archeological work is non-zero and non-obvious.

**Implication for decision quality:** The document's "zero cost" claim is too narrow. It should acknowledge: "Implementation cost = zero; design-recovery cost if α resumes = hours of reading + re-justification." This is not a blocker, but it reframes the decision as "we are preserving a design for future use" rather than "we are shelving a fully-reversible choice."

---

### Finding 3 — Decision deadline is soft and conditional on a cascade of unknowns (P1)

The document sets "~2026-06-30 (soft target)" and three escalation triggers. This is the core reversibility hinge. Examining it:

1. **Trigger 1 ("label noise > 30%")**: Requires `.19.9` to define "label noise" operationally and emit a metric. The document does not say `.19.9` *has* done this or even that `.19.9`'s spec includes a noise-detection mechanism. Section "Open questions" defers this to `.19.1` and `.19.2` phases. Result: the decision deadline is contingent on a design that doesn't yet exist. If `.19.9` ships without a noise metric, Trigger 1 becomes unobservable.

2. **Trigger 2 ("priority flip")**: Explicitly a human judgment. No way to pre-commit to this; it's a re-open condition that's always true in principle.

3. **Trigger 3 ("D2 shows <5% headroom")**: Contingent on D2 (the heuristic-baseline measurement) actually running. D2 is marked "independent epic-survival check, runnable in parallel" but the document does not commit to when or whether D2 *will* run. If D2 never runs, Trigger 3 never fires. The decision timeout then becomes just "soft target ~2026-06-30," which is a calendar date, not a decision rule.

**Decision quality issue:** The document conflates three types of decision deadlines: metric-driven (Trigger 1, fragile), judgment-driven (Trigger 2, always open), and contingent (Trigger 3, depends on a parallel bead that may not run). None of them are *committed* deadlines — all are subject to deferral. This is not necessarily wrong, but it's opaque. A reader three months from now won't know whether June 30 is a firm gate or a soft guideline.

**Improved framing:** Separate "soft review cadence (~2026-06-30)" from "hard re-open triggers" and rank the triggers by observability. Make clear that Trigger 3 depends on D2's completion, and D2's status should be tracked as a blocking dependency.

---

### Finding 4 — Single decision authority under deferral uncertainty (P1)

The document names **arouth1** as the sole decision authority. The interview format (AskUserQuestion on 2026-05-06) is the "canonical authority surface per the 2026-05-04 handoff."

This is sound for *this session's* decision, but creates a distributed-authority problem for the deferral:

- **If arouth1 is unavailable in June when the decision deadline arrives, who re-opens `.19.10`?** The document does not say. It's implied that "the same user who made the deferral makes the next call," but that's a fragile assumption for a multi-month timeline. 
- **The handoff structure amplifies the risk.** The decision authority is justified by reference to a prior handoff directive ("Resolve α vs β vs γ via AskUserQuestion"). That directive is *in a different document*. Future work depends on discovering and re-reading that directive to understand why arouth1 is the authority.

**What would help:** Explicit co-signer or escalation path. For example: "If arouth1 unavailable by 2026-06-15, escalate to [name] for deadline extension or authority transfer." Or: "Re-open decision is automatic if any Trigger fires; no human authority needed — process is: escalate to `.19.9` lead for Trigger 1, file bead for Trigger 2, close epic on Trigger 3."

---

### Finding 5 — Anchoring on α/β/γ may have missed a fourth path: "run D2 in a gated sandbox" (P2 → P1 escalation)

The 2026-05-05 revision (the predecessor) explicitly proposed D2 (heuristic-baseline measurement) as a separate epic-survival check. The current document says:

> This deferral has a concrete next action (`.19.9` becomes critical-path P0...). It's not a freeze; it's a re-prioritization to the prereq that all three architectures benefit from.

But then in "What this does NOT do":

> Does not run D2 (heuristic-baseline measurement). D2 is still a worthwhile sanity check...D2 should be a separate bead under `.19` (file as a follow-up).

This is a genuine missed frame: **The document does not consider the option of "run D2 in parallel, and if D2 kills the epic, close `.19` without ever building β."** Instead, the decision is binary: defer to β *or* escalate to γ. But the real decision space is ternary: defer-to-β *or* escalate-to-γ *or* kill-epic-after-D2.

The decision document treats D2 as orthogonal to the α/β/γ choice ("the deferral decision is independent"). But this is actually a hidden coupling: if D2 proves the heuristic is good-enough (the 2026-05-05 Approach E / "~5% headroom" outcome), then the entire `.19` epic should close, and both β-deferral and γ-contingency become moot.

**Why this matters:** The current framing locks `.19` into "we will implement a learned router" with only the architecture in question. It doesn't preserve the option to *not* build a router at all if D2 says the heuristic is sufficient. That option should appear in the decision table as a row, not buried in "open questions."

---

## P2 findings

### Finding 1 — Trigger threshold "~30% label noise" is a placeholder dressed as a decision criterion (P2)

Section "Why γ is preserved" sets the contingency threshold at "label noise > 30%." The follow-up in "Open questions" explicitly says: "(TBD; ~30% pre-registered as a placeholder)."

A placeholder dressed as a number is a weak decision-quality failure. It has three harms:

1. **Operationalization gap:** Who measures label noise, and how? LoRA training loss divergence? Human review sampling? If `.19.9` ships without defining the measurement protocol, the threshold becomes unenforceable.
2. **Blame shifting:** When β telemetry arrives, if noise is 28% vs 32%, the decision-maker has to justify why the threshold wasn't ~28% or ~35%. The placeholder nature of the number provides cover for that justification to be post-hoc.
3. **Audit trail loss:** Three months from now, no one will remember that "30%" was a placeholder. It will be read as a pre-committed gate that was applied (or not) based on some inference about what the user "probably meant."

**Better:** Defer the threshold-setting to the "Done when" checklist for `.19.9` or a new D2-focused bead. Record the threshold decision in that bead's body with reasoning ("why 30% and not 25%?"). If the threshold is genuinely unknowable until data arrives, say so explicitly: "We will set label-noise threshold after the first sprint of `.19.9` data, based on LoRA training stability diagnostics."

---

### Finding 2 — "4 sprints" volume threshold is also a placeholder (P2)

The decision references "4 sprints of pass@1 data" as a volume requirement. This appears in multiple places:

- "`.19.9` is closed AND four full sprints of pass@1 data have been written"
- "Pass@1 definition: bead clean-close...within **N=4 sprints**"
- "Conditional on `.19.1` Phase 2 + `.19.2`. If content-feature classifier path, the corpus is per-agent-frontmatter, not per-task-text"

The 2026-05-05 revision explains the 4-sprint choice: "(Conservative N: catches slow-burn regressions; doubles minimum data-accumulation time)."

This is a more defensible threshold than "30% noise" (it has justification), but it still has a reversibility problem: **4 sprints is ~4 weeks assuming weekly sprints. But the document doesn't pin sprint duration, cadence, or what "one sprint of data" means operationally** (number of verdicts? number of distinct agents? coverage of all complexity tiers?). If Sylveste's sprint cadence changes, or if "one sprint" naturally accumulates 1K verdicts in some phases and 100 in others, the threshold becomes ambiguous retrospectively.

---

## P3 findings (notes / nits)

### Note 1 — Missing contingency for ".19.9 itself is deferred or deprioritized"

Section "Open questions" calls out:

> **What if `.19.9` itself is deferred or de-prioritized?** Then this whole decision becomes "epic indefinitely paused."

This is a real risk and is correctly identified. But the decision document doesn't pre-commit an answer. The text says "the strategy phase should set a re-decision deadline if `.19.9` doesn't make progress in N weeks." That's good, but "N weeks" is another placeholder. A tighter version: "If `.19.9` has 0 commits by 2026-05-27, re-open `.19.10` and escalate to either (a) commit resource to `.19.9`, or (b) close the `.19` epic and kill β-deferral."

---

### Note 2 — Acceptance criteria compliance

The bead prompt specifies four required acceptance criteria for `.19.10`:

1. **Explicit α/β/γ evaluation table with cost/risk/coverage tradeoffs** — ✓ Present (lines 51–66). Well-structured, covers all axes.
2. **Decision deadline** — ⚠ Present but soft and conditional (lines 32–38). The deadline is ~2026-06-30, but three of the four components ("triggers") are either unobservable (Trigger 1 depends on `.19.9` design) or judgment-driven (Triggers 2–3). The deadline is real but fragile.
3. **Named decision authority** — ✓ Present. arouth1, via interview format, 2026-05-06.
4. **Re-entry cost estimate (if `.19.3` LoRA already ran)** — ✓ Present (lines 40–49). Clear: zero if α never started; ~half-day compute if α had shipped.

All four are met, though #2 is the weakest structurally.

---

### Note 3 — Internal consistency: γ-as-contingency implies β failure is plausible

The document treats γ as a "fallback if β telemetry doesn't accumulate cleanly." This is sound risk management, but it's worth noting that it implicitly admits **β might fail to produce usable training data in the timeframe.** The document explains why (label noise, insufficient volume), but it doesn't quantify the probability of β failure or the cost of the pivot to γ if it does happen.

A stronger version would estimate: "P(β telemetry fails) ≈ X%; if it does, cost of pivot to γ ≈ Y days of engineering." This isn't required for decision quality, but it would strengthen the reversibility claim.

---

## Verdict

**NEEDS_ATTENTION**

**Summary:** The decision itself is sound (deferring to β is well-justified), the evaluation table is strong, and the contingency (γ) is appropriately documented. However, the reversibility framing is weaker than claimed. The deferral creates three concrete risks: (1) α-design work is now orphaned-in-place, creating recovery friction if α ever resumes; (2) contingency triggers are partly unobservable (depend on `.19.9` design not yet written) or judgment-driven (unquantified); (3) the decision deadline is soft and conditional on a cascade of parallel decisions (D2, `.19.9` spec, sprint cadence). The document doesn't acknowledge that it's deferring under uncertainty rather than truly shelving, and it doesn't adequately prepare future work to either enforce the deadline or recognize when it's been missed.

**Before closing `.19.10`:** Harden the contingency trigger definitions (especially "label noise >30%" and "4 sprints of data") by pushing the threshold-setting to `.19.9`'s "Done when" checklist. Add an explicit re-decision deadline: if `.19.9` hasn't shipped by [date], re-open `.19.10` and re-evaluate. Move the option "kill epic if D2 shows <5% headroom" into the main decision table as a fourth row, not a deferred consideration. Update `.19.8` body to note it is now "documented but not implemented" to reduce future archeological work.

