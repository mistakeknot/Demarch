<!-- run-uuid: 1e048f43-8f72-4292-93bf-951314f97a39 -->
### Findings Index
- P1 | PGC-1 | "install.sh contract" | Top-note absent — install.sh prints utilitarian next-steps with no Auraken voice
- P1 | PGC-2 | "Key Decisions / Bundle layout" | INSTALL.md and MANIFEST.yaml are administrative scaffold, not composed identity surface
- P2 | PGC-3 | "MANIFEST.yaml schema" | Signature vs. accord undeclared — capabilities list makes no distinction between identity-defining and substitutable
- P2 | PGC-4 | "Distribution mechanism" | Stranger's skin untested — brainstorm names Linux as the test surface, macOS as "expected to work, untested"
Verdict: needs-changes

### Summary

The v0.1 brainstorm is structured around what is inside the vessel (SKILL.md, auraken-lens MCP, MANIFEST.yaml) but gives no attention to the opening composition — the sensory sequence a stranger encounters in their first 60 seconds. The install.sh next-steps text is described by its function ("prints next steps: how to invoke /auraken, where logs go, how to uninstall") rather than its voice. INSTALL.md is treated as documentation infrastructure. MANIFEST.yaml is a schema artifact. None of these surfaces are composed as part of the Auraken identity. The bundle's top-note is silent: the first ten seconds deliver Hermes ergonomics, not Auraken presence. The heart-note (SKILL.md voice, lens-selection behavior) may be correct, but it only reaches the user after they invoke `/auraken` — which requires them to read the utilitarian next-steps and know what to do.

### Issues Found

**1. [P1] PGC-1 — Top-note absent from install.sh next-steps (Section: "install.sh contract")**

The install.sh contract (step 6) is described as: "Prints next steps: how to invoke /auraken, where logs go, how to uninstall." This is a functional description, not a voice description. A utilitarian next-steps block ("Run /auraken in your Hermes session to begin. Logs are at ~/.hermes/logs/. To uninstall, remove skills/auraken/ from your profile.") delivers zero Auraken top-note. The first encounter between a stranger and Auraken — the moment install.sh exits and the user reads the terminal — is Hermes-colored, not Auraken-colored.

Failure scenario: A user installs Auraken, reads the terminal output, and has no signal from the install experience itself that something distinctive just arrived. They invoke `/auraken` because they were told to. If the first interaction is weak or the model register-drifts on a cold start, the user has nothing to compare against — no anticipation was built in the install moment. The composition arrives flat because the top-note was silent.

This matches the P1 calibration exactly: "post-install next-steps text printed by install.sh is utilitarian with no character — first 10 seconds of contact reveal no Auraken voice."

Smallest fix: Write the next-steps text in the brainstorm rather than deferring to implementation. Draft: instead of "Run /auraken in your Hermes session to begin," write something that names what is distinctive: "Type /auraken and notice: the response will name the lens it's applying and why. That's not standard Hermes — that's the auraken-lens MCP doing its work." Two sentences that tell the user what to look for, in a register that previews what they'll encounter. This is a writing task, not an engineering task, and should be resolved before the install.sh is authored.

**2. [P1] PGC-2 — Packaging surface composed as scaffold, not identity (Section: "Bundle layout")**

The brainstorm names four packaging-surface files: MANIFEST.yaml, INSTALL.md, install.sh, CHANGELOG.md. None of them are described as composed artifacts. MANIFEST.yaml is described by its schema. INSTALL.md is described by its content (user-facing install instructions). CHANGELOG.md is "bumps documented here from v0.2 onward." The brainstorm treats these files as infrastructure that holds the real content (SKILL.md, auraken-lens) rather than as part of the composition.

A Grasse perfumer designs the bottle as part of the composition: the label, the bottle shape, the cap resistance, the first waft when the cap is removed — all are part of the fragrance encounter. A distribution bundle's INSTALL.md, its CHANGELOG.md tone, and its MANIFEST.yaml field comments are the equivalent surfaces. If they are written in a neutral technical register, the bundle smells of documentation, not of Auraken, from the moment it is unboxed.

Failure scenario: A user downloads the tarball, opens INSTALL.md, and reads generic documentation prose. They proceed through installation. They invoke `/auraken`. The first response — if it's working — delivers Auraken voice. But the user's frame was set by INSTALL.md's neutral tone: they are in "configure a tool" mode, not in "encounter a distinctive mind" mode. The composition's top-note was squandered on the packaging.

Smallest fix: Add a single constraint to the brainstorm's bundle layout description: "INSTALL.md, MANIFEST.yaml comments, and install.sh printed text are composed in Auraken's register — they are part of the distribution's identity surface, not neutral infrastructure." This is a doctrine note, not a file change. It shapes what gets written during plan/implementation phase.

**3. [P2] PGC-3 — Signature vs. accord undeclared in capabilities (Section: "MANIFEST.yaml schema")**

The `capabilities` list in MANIFEST.yaml has two entries: `auraken-personality` (skill) and `auraken-lens` (mcp-server). The schema gives them equal weight — both are capabilities, both have an id, type, path, binary_required. But from a perfumer's perspective, these are not the same kind of material. `auraken-personality` is the signature accord — the character-defining material that, if removed or substantially altered, means the composition is no longer Auraken. `auraken-lens` is a heart-note material — distinctive but potentially substitutable in a future version without losing core identity.

The brainstorm does not draw this distinction. A v0.2 developer who wants to replace `auraken-lens` with a different lens-selection mechanism cannot tell from the MANIFEST schema whether this would retain or destroy Auraken identity. The schema offers no `identity_role: signature|heart|accord|base` field.

Smallest fix: Add an `identity_role:` field to each capability entry in the schema. Values: `signature` (removal = identity loss, requires new distribution name), `heart` (changes require lineage note but not rename), `accord` (freely substitutable in minor versions). For v0.1: `auraken-personality: signature`, `auraken-lens: heart`. One field addition to the schema, one value per capability. Costs one line per capability in MANIFEST.yaml.

**4. [P2] PGC-4 — Stranger's skin untested (Section: "Open Questions")**

The brainstorm names Linux as the test surface for v0.1, macOS as "expected to work, untested." The stranger's-skin test — does the composition arrive correctly on skin that is not the perfumer's own bench — is deliberately deferred. A Grasse perfumer knows that a fragrance that works perfectly on the developer's own model (claude-opus-4-7, CLIProxyAPI, Linux, known Hermes profile) may perform differently on a stranger's skin (gpt-5.5, fresh Hermes profile, macOS, no context). The model matrix in MANIFEST.yaml acknowledges `openai: gpt-5.5, register drift documented` — but the brainstorm gives no guidance on what install.sh or the bundle should do when the model is not the primary validation target.

Failure scenario: A user on macOS with Hermes installed via the macOS method (which may use a different profile path convention) runs install.sh. The profile detection (step 2: "lists profiles in ~/.hermes-*/profiles/") finds nothing or finds the wrong path. Install fails or installs into the wrong profile. The stranger's skin rejects the composition. The user has no recovery path — INSTALL.md's troubleshooting section is not described in the brainstorm.

Smallest fix: Add "INSTALL.md includes a Troubleshooting section covering: profile not found, MCP registration failure, register-drift indicators on non-primary models" to the brainstorm's bundle layout description. This is a documentation scope item that should be explicit in v0.1 rather than implicit.

### Improvements

1. **Draft the install.sh next-steps text in the brainstorm, not the plan.** The top-note is the highest-leverage, lowest-cost identity signal in the entire distribution. Writing it late (in implementation) means it gets written by whoever implements install.sh, in whatever register is convenient. Writing it now, as part of the brainstorm, means it sets the tone for every other packaging surface.

2. **Add a packaging-surface doctrine note to the bundle layout section.** One sentence: "INSTALL.md, CHANGELOG.md opening, and install.sh terminal output are Auraken identity surfaces, not neutral infrastructure — they are composed in Auraken's register." This costs nothing and prevents the most common failure mode (packaging written in a generic docs voice).

3. **Consider whether the excluded_from_v01 scope (no thinker-profile, no voice-corpus-refresh) preserves the core opening.** The brainstorm asserts it does, but doesn't test the claim. A thinker-profile MCP — deferred to v0.3 — might be a top-note material (something that establishes "this agent knows you") rather than a base-note. If so, v0.1 without it may feel incomplete on first encounter. Worth a single paragraph of analysis in the brainstorm.

4. **Walk through the first 60 seconds explicitly as a design exercise.** User downloads tarball → opens INSTALL.md (neutral or composed?) → runs install.sh → sees confirmation prompt (neutral or Auraken-registered?) → install completes → reads next-steps (top-note!) → invokes /auraken → receives first response (heart-note). Each step should be audited for voice before v0.1 ships.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 4 (P0: 0, P1: 2, P2: 2, P3: 0)
SUMMARY: The brainstorm designs the bundle's contents correctly but treats all packaging surfaces (INSTALL.md, install.sh next-steps, MANIFEST comments) as neutral infrastructure rather than composed identity. Two P1 gaps: install.sh's next-steps text has no Auraken voice (top-note absent) and the packaging surface is described by function rather than composition. Both are writing tasks, not engineering tasks, and should be resolved before implementation begins.
---
<!-- flux-drive:complete -->
