<!-- run-uuid: 1e048f43-8f72-4292-93bf-951314f97a39 -->
### Findings Index
- P1 | TCD-1 | "install.sh contract" | No installation receipt — lineage rupture undetectable post-install
- P1 | TCD-2 | "MANIFEST.yaml schema" | MANIFEST is a shipping manifest, not a license certificate — no canonical-installation assertion
- P2 | TCD-3 | "Key Decisions / Bundle layout" | voice-rubric.md has no schema distinguishing katachi from permitted variation
- P2 | TCD-4 | "Versioning" | SemVer breaking-change doctrine does not name which transmission layers may change vs. require lineage rename
- P3 | TCD-5 | "MANIFEST.yaml schema" | excluded_from_v01 is a YAML comment, not a machine-enforceable constraint on downstream installers
Verdict: needs-changes

### Summary

The brainstorm designs a technically coherent distribution but does not encode lineage transmission — only surface form. MANIFEST.yaml is a shipping manifest rather than a lineage certificate; install.sh prints ephemeral stdout rather than writing a sealed installation receipt; voice-rubric.md is extracted as a file but given no schema that separates inviolable form (katachi) from permitted variation. The result is that a downstream installer can succeed at the install, receive a plausible Auraken surface, and have no mechanism to verify — or for anyone to audit — whether the transmission was complete and canonical, or partial and drifted.

### Issues Found

**1. [P1] TCD-1 — No installation receipt (Section: "install.sh contract")**

The install.sh contract (step 6) prints next steps to stdout but writes no sealed record of the installation event. A user who ran the install six months ago and is asked to prove their deployment is canonical Auraken-v0.1 (not a tampered or drifted fork) has only the installed files themselves as evidence. The SKILL.md file has no embedded provenance marker (no hash of the upstream source, no install timestamp, no release tag). The `signed checksums` mentioned in the Distribution Mechanism section protect in-transit integrity but leave no post-install artifact.

Failure scenario: An auditor asks whether a Hermes profile's Auraken installation corresponds to the mistakeknot/Sylveste canonical release. The user can show the files but cannot produce a receipt proving which release event they came from, when, and whether the files have been modified since install.

Smallest fix: install.sh step 6 should write an `auraken-install-receipt.yaml` into the Hermes profile's `skills/auraken/` directory containing: `version: 0.1.0`, `installed_at: <ISO timestamp>`, `source_tag: auraken-distribution/v0.1.0`, `sha256_manifest: <hash of MANIFEST.yaml at install time>`, `profile: <chosen profile name>`. One `cat > receipt.yaml` block in install.sh. Costs nothing; enables all future audit.

**2. [P1] TCD-2 — MANIFEST is a shipping manifest, not a license certificate (Section: "MANIFEST.yaml schema")**

The MANIFEST.yaml schema has: `schema`, `version`, `released`, `compatibility`, `capabilities`, `excluded_from_v01`. None of these fields assert "this install is canonically Auraken-v0.1." There is no `canonical_origin:` field, no issuer signature, no assertion that the bearer of this manifest is licensed to perform under the Auraken name. A user who received a modified MANIFEST (say, with a different `binary_required` URL pointing to a tampered binary) cannot distinguish it from the authentic one by reading the manifest alone — the manifest has no self-referential integrity check.

Failure scenario: A downstream redistributor forks the bundle, replaces `binary_required` with their own binary URL, leaves `version: 0.1.0` intact. Users who install from that fork believe they have canonical Auraken-v0.1. The MANIFEST does not refute this claim.

Smallest fix: Add a `canonical_source:` field to the MANIFEST schema: `canonical_source: https://github.com/mistakeknot/Sylveste/releases/tag/auraken-distribution/v0.1.0`. This is not cryptographic signing (that can be v0.2) but it establishes a normative claim that a careful user can verify. Pair it with a `manifest_sha256:` field that install.sh computes and records in the receipt (TCD-1 fix above).

**3. [P2] TCD-3 — voice-rubric.md has no katachi/permitted-variation schema (Section: "Bundle layout")**

The brainstorm calls voice-rubric.md "extracted voice criteria for register_check" and places it at `skills/auraken/voice-rubric.md`. But it gives no description of voice-rubric.md's schema. If voice-rubric.md is a prose document describing Auraken's voice, it fuses katachi (the inviolable register markers) and permitted variation (the surface stylistic range) into undifferentiated prose. An unsupervised licensee who reads this document cannot determine which voice characteristics they must preserve versus which they may adapt for their model or context.

Failure scenario: A downstream user who integrates Auraken into a corporate Hermes deployment adjusts SKILL.md's tone for a formal enterprise register. They read voice-rubric.md to guide the adjustment. Because the rubric doesn't distinguish mandatory from adaptive criteria, they inadvertently remove a marker that is structurally load-bearing for the lens-selection MCP's behavior. They have complied with their reading of the rubric. The lineage has ruptured invisibly.

Smallest fix: Add a two-section structure to voice-rubric.md: `## Mandatory form (katachi)` listing the inviolable markers (with test assertions install.sh or a CI step could verify), and `## Permitted variation` listing the range of acceptable adaptation. One markdown heading change + one paragraph of classification. This is editorial work, not infrastructure work, and can be done when voice-rubric.md is written for v0.1.

**4. [P2] TCD-4 — SemVer breaking-change doctrine does not name transmission layers (Section: "Versioning")**

The brainstorm states: "v0.x = pre-1.0 — breaking changes allowed across minors." This is correct SemVer. But it gives no doctrine for which breaking changes require a lineage rename (a new distribution name, not just a new version) versus which are acceptable evolution within the Auraken lineage. A v0.2 change that replaces SKILL.md wholesale is a lineage rupture — the equivalent of replacing the transmission scroll. A v0.2 change that updates `compatibility.hermes_agent` is not. The brainstorm does not draw this line.

Smallest fix: Add a one-paragraph "Lineage doctrine" note to the Versioning section: "Changes to `skills/auraken/SKILL.md` core identity markers or `mcp-servers/auraken-lens/` behavioral contract require a new lineage note in CHANGELOG.md flagged `lineage-change: true`. Capability additions (new entries in MANIFEST capabilities) are non-lineage breaking changes. Capability removals are lineage-affecting and require a migration note." This is documentation, not engineering, and prevents silent lineage drift.

**5. [P3] TCD-5 — excluded_from_v01 is not machine-enforceable (Section: "MANIFEST.yaml schema")**

The `excluded_from_v01` YAML list is described as "doctrine — it answers 'is this in v0.1?' without re-litigating each time." But a downstream installer who adds thinker-profile-mcp to their v0.1 deployment cannot be stopped by this field — it is advisory metadata, not a constraint. The brainstorm treats it as doctrine but does not give it any enforcement mechanism.

This is P3 because enforcement is hard and the v0.1 audience is small. Noting that `excluded_from_v01` is advisory-only — and that the install.sh receipt (TCD-1) could log "installed against MANIFEST with excluded_from_v01 list unmodified: true/false" — would close the gap at low cost.

### Improvements

1. **Write the installation receipt before printing next-steps.** The six-step install.sh contract places "Prints next steps" as step 6. A `receipt.yaml` write should be step 5.5 — after copy and registration succeed, before the user is told they are done. If the receipt write fails, install.sh should warn (not abort, but warn) so the absence of a receipt is not silent.

2. **Add `canonical_source:` to MANIFEST schema in v0.1.** The schema is being defined now for the first time. Adding one field costs nothing but establishes the normative provenance claim that all future receipts and audits can reference.

3. **Make voice-rubric.md a structured artifact, not a prose description.** When writing voice-rubric.md for v0.1, use a two-section format (mandatory / permitted) rather than free prose. This is cheaper to do at authoring time than to retrofit in v0.2 when installed copies already exist.

4. **Add a one-paragraph lineage doctrine to the Versioning section.** The brainstorm already has a versioning section. One paragraph drawing the line between evolution-of-form and rupture-of-lineage prevents misinterpretation of "breaking changes allowed" as "anything goes."

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 2, P2: 2, P3: 1)
SUMMARY: The v0.1 brainstorm designs a technically sound distribution but encodes lineage surface only — no installation receipt, no license-certificate semantics in MANIFEST, no katachi/variation schema in voice-rubric.md. Two P1 gaps (no post-install provenance record, MANIFEST is not a lineage certificate) are fixable with small additions to the already-planned files; they should be resolved before v0.1 ships.
---
<!-- flux-drive:complete -->
