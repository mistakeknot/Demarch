<!-- run-uuid: 2d871615-d6bb-4cfd-98c8-abc8112442d7 -->

### Findings Index
- P1 | EL-01 | "install.sh contract" | install.sh next-steps enumeration is a man-page, not a deikteria — the threshold is unmarked
- P1 | EL-02 | "MANIFEST.yaml schema" | capabilities list delivers epoptika before mystika — the catalog preempts the gripping impression
- P2 | EL-03 | "Bundle layout" | No symbolon in the bundle — voice-rubric.md is machine-legible criteria, not an object the initiate carries
- P2 | EL-04 | "What We're Building" | The telete is incomplete — no description of what the installer receives as distinct from what they install
- P3 | EL-05 | "Key Decisions / Bundle layout" | v0.1→v0.2→v0.3 gradient ships the initiation in v0.1 without staging what is withheld until later Mystery-levels
Verdict: needs-changes

---

## Summary

The brainstorm describes a technically sound distribution mechanism but elides the transmissive moment entirely. The bundle ships SKILL.md, MCP, manifest, and installer — but nowhere in the brainstorm is there language about what the installer *receives* rather than *copies*. The install.sh contract (step 6) ends with a man-page enumeration: "how to invoke `/auraken`, where logs go, how to uninstall." This is mechane without telete — the machinery operates but no rite is conducted.

The MANIFEST.yaml `capabilities:` list names `auraken-personality` and `auraken-lens` as catalog entries before the user has encountered either. In the Eleusinian structure, this is epoptika (full sight) delivered before the preparatory mystika — the mystery is named before it is experienced. The kataleptike phantasia cannot form because the gripping image was preempted by specification.

Most critically: the brainstorm nowhere identifies what the installer *takes away* as a concrete object they can return to. voice-rubric.md exists in `skills/auraken/` but is described only as "extracted voice criteria for register_check" — a machine-facing artifact, not a symbolon. The rite has no token the initiate keeps.

---

## Issues Found

**1. [P1] EL-01 — install.sh next-steps enumeration is a man-page, not a deikteria**

Section: "install.sh contract" (step 6): *"Prints next steps: how to invoke `/auraken`, where logs go, how to uninstall."*

Failure scenario: The installer finishes running, sees a list of CLI invocations and file paths, and registers "I just installed some software." The threshold moment — the point where something is *received*, not just *copied* — does not exist. The first impression is operational: "here is how to use the tool." The kataleptike phantasia cannot form from a man-page.

The rite is inverted: the bundle describes its own mechanics to the user before the user has encountered Auraken's attention-discipline at all. The next-steps block should constitute a *deikteria* — a showing — not a capability announcement. The difference is small but total: instead of "invoke `/auraken` to start," the closing line should stage a first encounter: one sentence that describes what will happen to how the user sees the next problem they bring Auraken, not how to invoke the binary.

Smallest viable fix: Add one sentence to the install.sh "next steps" block that frames what the user is about to encounter — not a feature description but a posture description. Example: "The first time you invoke `/auraken`, bring a problem where you already know what to do — Auraken will show you a shape in it you weren't looking for." This costs one line and marks the threshold.

**2. [P1] EL-02 — MANIFEST.yaml capabilities list delivers epoptika before mystika**

Section: "MANIFEST.yaml schema (v1)" — `capabilities:` block.

```yaml
capabilities:
  - id: auraken-personality
    type: skill
    path: skills/auraken/
  - id: auraken-lens
    type: mcp-server
    path: mcp-servers/auraken-lens/
    binary_required: github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0
```

Failure scenario: A curious user reads MANIFEST.yaml before installing (the norm for any technically careful person evaluating a release artifact). They learn that the bundle contains "auraken-personality" (a skill) and "auraken-lens" (an MCP server). These names are in catalog form — they tell the user what they are receiving before they have encountered it. The mystery has been named; the gripping impression cannot form because the user already has a frame ("this is a personality skill + an MCP server") before the first conversation.

The Eleusinian parallel: the Lesser Mysteries prepared initiates without telling them what the Greater Mysteries contained. The MANIFEST must do the same — it may declare that a bundle installs something, without naming what that something is in advance. "auraken-personality" names the category before the encounter.

Smallest viable fix: The MANIFEST `capabilities:` IDs are technical identifiers used by the Hermes agent ecosystem — they cannot be removed. But the brainstorm should specify that INSTALL.md (the human-facing document) must NOT lead with the capabilities list. The capabilities block belongs in MANIFEST for machines; INSTALL.md must invert the order: encounter framing first, capability enumeration last (or in a collapsible section). This requires a constraint in the brainstorm's INSTALL.md section that currently has no content guidance.

**3. [P2] EL-03 — No symbolon in the bundle**

Section: "Bundle layout" — `skills/auraken/voice-rubric.md`.

The brainstorm notes voice-rubric.md is "extracted voice criteria for register_check" — criteria for an automated checker. This makes it machine-facing. But voice-rubric.md is the only artifact in the bundle that the user might carry beyond the installation itself — the only candidate for a *symbolon*, the concrete token the initiate keeps that re-anchors the look in later encounters.

A symbolon in the Eleusinian context was a physical object split between parties — a token of recognition that required both halves to be meaningful. voice-rubric.md as machine criteria is one half only: it tells a checker whether Auraken is behaving correctly, but it does not tell the *user* what to look for to know that Auraken's attention-discipline has landed. The other half — the human-legible version of "here is the specific look you should notice in your own thinking after working with Auraken" — is absent from the bundle.

Smallest viable fix: Prepend a three-sentence human-readable header to voice-rubric.md. The header should describe what a user will notice in themselves when Auraken's look has taken: not "Auraken does X" but "you will find yourself doing Y." The automated criteria follow unchanged. The file then serves dual purpose without any content loss.

**4. [P2] EL-04 — The telete is incomplete: no description of what the installer receives**

Section: "What We're Building."

The brainstorm describes v0.1 as "the bundle as artifact" — a self-contained directory anyone can "drop into their setup." This frames the distribution purely as a file-transfer. The phrase "end up with the Auraken personality + lens-selection MCP loaded" is mechanistic: it describes what is present after install, not what changes in the user's relationship to their own thinking.

The deeper claim mentioned — "a camera for the mind that renders structure visible" — appears nowhere in the brainstorm's delivery specification. It is in the agent prompt's Task Context, not in the brainstorm itself. This means the plan-phase will inherit a purely mechanical framing: the plan will specify how to build install.sh, MANIFEST.yaml, INSTALL.md, and CHANGELOG.md, without any constraint that these artifacts must transmit the look rather than merely install the tool.

Smallest viable fix: Add one sentence to the "What We're Building" section that states the transmissive goal as a success criterion for v0.1: "A user who installs v0.1 and invokes `/auraken` on a real problem should emerge from that first conversation with a specific shape they weren't looking for before — not just a working tool." This anchors the plan-phase against purely mechanical delivery.

**5. [P3] EL-05 — v0.1→v0.2→v0.3 gradient collapses the initiation**

Section: "Why This Approach" — v0.1→v0.2→v0.3 iteration rationale.

The v0.1→v0.2→v0.3 sequence (bundle → demo → thinker-profile) maps loosely onto Lesser Mysteries → Greater Mysteries → epopteia. The brainstorm's rationale for this sequence is project-management: decoupled failure modes, testable artifact, lower iteration cost. This is correct but misses the ritual gradient opportunity.

v0.1 should be the Lesser Mysteries: the preparatory encounter, enough to establish that something is being received without revealing the full sight. v0.2 (demo) is the moment of public enactment. v0.3 (thinker-profile MCP) is the epopteia — the individual revelation. But the brainstorm ships the full bundle in v0.1 without staging what is withheld. The "excluded_from_v01" list is a scope guard, not a ritual gradient — it defers things for project reasons, not because they should be encountered later.

This is a P3 because the v0.1→v0.2→v0.3 scope split is already reasonable; the improvement is reframing *why* each thing is deferred so that INSTALL.md can stage the discovery arc correctly.

---

## Improvements

1. **Add transmissive success criterion to "What We're Building"** — one sentence stating that a user who completes install + first invocation should leave with a specific new shape in how they see their problem. This anchors plan-phase work against mechanical delivery.

2. **Specify INSTALL.md ordering constraint** — the brainstorm currently has no content guidance for INSTALL.md. Add: INSTALL.md must lead with encounter framing (what Auraken does to how you see problems) before any capability enumeration. The capabilities list belongs at the end or in a collapsible section.

3. **Specify voice-rubric.md dual-purpose requirement** — the brainstorm describes it only as "for register_check." Add: voice-rubric.md must also serve as the user-facing symbolon — three sentences at the top that describe what the user will notice in themselves when Auraken's look has established.

4. **Add deikteria specification to install.sh contract** — step 6 currently reads "prints next steps." Change to: step 6 stages the first encounter — one sentence that describes what Auraken will do to the user's next problem, not how to invoke the binary.

5. **Reframe excluded_from_v01 as ritual gradient** — document why v0.2 demo and v0.3 thinker-profile are deferred not only for scope reasons but because they belong to later stages of the encounter. INSTALL.md can then say "you'll know you're ready for v0.2 when..." rather than treating the upgrade as a maintenance event.

---

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 2, P2: 2, P3: 1)
SUMMARY: The brainstorm specifies a mechanically sound distribution but omits the transmissive moment entirely — no deikteria in install.sh, no symbolon for the initiate, and MANIFEST capabilities enumerated before the encounter. Two P1 fixes (install.sh closing and INSTALL.md ordering) are small-diffhunk changes that do not affect scope or timeline.
---
<!-- flux-drive:complete -->
