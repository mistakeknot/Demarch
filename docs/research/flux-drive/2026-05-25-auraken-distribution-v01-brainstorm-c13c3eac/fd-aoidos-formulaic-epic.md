<!-- run-uuid: 1e048f43-8f72-4292-93bf-951314f97a39 -->
### Findings Index
- P1 | AFE-1 | "MANIFEST.yaml schema" | Capabilities schema has no extension grammar — adding v0.3 thinker-profile requires schema migration, not slot-filling
- P2 | AFE-2 | "install.sh contract" | install.sh is a bespoke type-scene, not a reusable formula — future sibling distributions must reinvent it
- P2 | AFE-3 | "auraken-lens binary distribution" | Binary acquisition is not a named type-scene — it is a deferred decision, not a defined formulaic slot
- P3 | AFE-4 | "INSTALL.md" | Proem absent — INSTALL.md opens in medias res with instructions, no identity-establishing formula
Verdict: needs-changes

### Summary

The v0.1 bundle layout has a sound directory structure (skills/, mcp-servers/, MANIFEST.yaml, install.sh) that could function as a formulaic template for v0.2/v0.3. But the MANIFEST.yaml capability schema is shaped for exactly the v0.1 capabilities — adding a third capability kind (thinker-profile MCP, deferred to v0.3) would require a schema decision, not a slot-fill. The install.sh type-scene is correct but not factored: a sibling Hermes distribution (not Auraken) could not reuse it without forking the whole script. The binary acquisition step is a deferred decision rather than a defined formulaic slot. The structure is a good first draft for a formula but is not yet a formula.

### Issues Found

**1. [P1] AFE-1 — Capabilities schema has no extension grammar (Section: "MANIFEST.yaml schema")**

The v0.1 capability schema has exactly two entries, both following the same shape: `id, type, path, optional binary_required`. The two types are `skill` and `mcp-server`. v0.3 introduces `thinker-profile-mcp` (bead sylveste-i0px). This is a new capability kind — distinct from a skill and distinct from a standalone MCP server. The current schema does not define whether `thinker-profile` would be `type: mcp-server` with additional fields, or a new type, or a sub-entry under an existing capability.

A formulaic metrical slot admits substitution: any noun of the right metrical weight fills the epithet's position. The MANIFEST capability slot as currently specified does not admit thinker-profile without a question: does `type: mcp-server` cover it? Does `binary_required` apply? Does it need a new field (e.g., `depends_on: auraken-personality`)? The schema answers none of these.

Failure scenario: A v0.3 implementer reads the v0.1 MANIFEST.yaml schema to understand how to add thinker-profile. The schema has no extension grammar — `type:` has two exemplified values and no documented range. The implementer either guesses (adds a third type value without doctrine), or falls back to re-reading the brainstorm (which defers the decision to v0.3). Every v0.3 implementer must re-read the whole rather than filling a known slot.

Smallest fix: Add a comment to the MANIFEST.yaml schema's capability section: `# type: skill | mcp-server | [future: thinker-profile]` and add `depends_on: []` as an optional field (empty list by default) for capabilities that require another capability to be installed first. This pre-defines the extension slot that v0.3 will need. Two YAML comment lines and one optional field.

**2. [P2] AFE-2 — install.sh is a bespoke type-scene, not a reusable formula (Section: "install.sh contract")**

The install.sh contract is described in six numbered steps: (1) detect Hermes install, (2) ask which profile, (3) validate version, (4) copy skills/, (5) build + register MCP, (6) print next steps. This is structurally a type-scene — the formulaic unit that recurs in epic (the arming scene, the feast scene, the ship-launch scene). A type-scene can be filled by different characters and content while maintaining its shape.

But the install.sh contract as described is Auraken-specific at multiple steps: step (4) copies `skills/auraken/`, step (5) reads `pyproject.toml` for the auraken-lens MCP specifically, step (6) mentions `/auraken` by name. A hypothetical sibling distribution (a different Hermes overlay) would need to fork the entire script and replace every Auraken-specific reference. The type-scene is present in spirit but not factored: the variables are not externalized.

This is P2 rather than P1 because it affects future distributions, not v0.1's correctness. But the cost of factoring increases with each version that inherits the bespoke implementation.

Smallest fix: Add a preamble to install.sh (in the brainstorm's description) that names its variables: `DIST_NAME`, `DIST_VERSION`, `SKILL_DIR`, `MCP_SERVER_DIR`, `INVOKE_NAME`. The script body then references `$SKILL_DIR` instead of `skills/auraken/` and `$INVOKE_NAME` instead of `/auraken`. Steps (1)-(6) remain identical in structure but are filled by variables rather than literals. A sibling distribution would source the same script with different variable values. This is a two-hour refactor if done in v0.1; it is a breaking change if done in v0.2 after downstream scripts have forked.

**3. [P2] AFE-3 — Binary acquisition is not a defined formulaic slot (Section: "auraken-lens binary distribution")**

The brainstorm defers the binary distribution decision (vendor vs. go-install) to the plan phase. From a formulaic perspective, this means that install.sh step (5) — "builds + registers the auraken-lens MCP server" — contains an undefined slot. The type-scene has a gap in it: the "how the hero arms himself" moment is described as "the hero will arm himself in some way to be decided."

A formulaic performer filling this type-scene in a future performance (a v0.2 implementer extending the install.sh) has no pattern to follow. They encounter a branch point where v0.1 made a decision (vendor or go-install) but did not name it as a decision or document which path was taken and why. The formula is incomplete.

Smallest fix: The brainstorm should close this decision before plan phase, as it notes: "Likely answer: option a for v0.1 with option b as fallback in INSTALL.md." Converting "likely answer" to "decision: option a" makes the binary acquisition a named step in the formulaic type-scene: "step 5a: copy vendored binary from release assets to Hermes MCP bin dir, verify sha256, register." This names the slot concretely. Future versions can fill the slot differently (option b, or a package manager, or a container) without re-opening the v0.1 decision.

**4. [P3] AFE-4 — Proem absent from INSTALL.md (Section: "Bundle layout")**

An Homeric epic opens with a proem — the invocation of the Muse and the naming of the poem's subject ("Sing in me, Muse, of that ingenious hero who traveled far and wide..."). The proem establishes identity before the narrative begins. The brainstorm describes INSTALL.md as containing "user-facing install instructions" — which implies it opens with prerequisites or a download command, not with a statement of what Auraken is and what lineage it belongs to.

A user who arrives at INSTALL.md without prior knowledge (a cold install from the GitHub release page) begins reading in medias res: prerequisites, then commands, then next steps. The distribution's identity is not named in the opening. The work begins without naming the work.

This is P3 because INSTALL.md is documentation and its absence does not break the install. But it is the most visible surface of the distribution for a new user and costs nothing to add.

Smallest fix: Add a two-paragraph opening to INSTALL.md: (1) What Auraken is — one sentence naming its lineage (Hermes Agent overlay, personality + lens-selection, from the Sylveste project). (2) What installing it adds — what will be different in a Hermes session after install. Then the prerequisites and commands follow. The proem names the work before the recitation begins.

### Improvements

1. **Name the capability type range in the MANIFEST schema comment.** Add `# type: skill | mcp-server` plus a note: "New capability kinds should be added here with a PR to the MANIFEST schema documentation before adding entries." This costs one comment line and prevents schema drift across versions.

2. **Externalize install.sh variables in v0.1.** The six-step type-scene is the right shape. Making it formulaic (variables for all distribution-specific strings) costs two hours in v0.1 and saves significant cost in every future sibling distribution. The brainstorm should name this as a design goal: "install.sh is authored as a reusable template with distribution-specific values injected via variables."

3. **Resolve the binary distribution decision before plan phase.** The brainstorm itself says "Likely answer: option a." Converting a likely answer to a decision costs nothing and removes the undefined slot from the formulaic template.

4. **Write the INSTALL.md proem before implementation.** Like the install.sh next-steps text, the proem is a writing task that sets a precedent for all future versions. Writing it early is cheaper than retrofitting it.

5. **Evaluate whether the v0.1 → v0.2 → v0.3 sprint cadence is itself formulaic.** The brainstorm describes each version's additions (v0.2: demo, v0.3: thinker-profile). Does this follow a consistent type-scene pattern (each version: adds capability + validates on new model + writes migration note in CHANGELOG)? If so, naming that pattern now would make each version's planning faster and its structure predictable — each sprint fills the same slot structure.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 4 (P0: 0, P1: 1, P2: 2, P3: 1)
SUMMARY: The v0.1 bundle layout has the right directory structure to become a formulaic template but is not yet one — the MANIFEST capability schema has no extension grammar, install.sh uses distribution-specific literals rather than externalized variables, and the binary acquisition step is an undefined slot. The P1 gap (no extension grammar in MANIFEST) is fixable with two comment lines before the schema is frozen; the P2 gaps are refactoring tasks best done in v0.1 before implementation patterns are established.
---
<!-- flux-drive:complete -->
