<!-- run-uuid: fed42cc6-b03c-4e8e-a5a8-bc6e14fd3c7c -->

### Findings Index
- P1 | FGSD-1 | "MANIFEST.yaml schema (v1)" | excluded_from_v01 uses internal bead IDs — opaque to external practitioners
- P1 | FGSD-2 | "install.sh contract" | No Hermes prerequisite check — assumption undeclared and unverified
- P2 | FGSD-3 | "Install path assumption" | Additive-overlay principle absent from distribution artifacts
- P2 | FGSD-4 | "MANIFEST.yaml schema (v1)" | Hermes-only scope not stated as explicit non-goal for other agent frameworks
- P2 | FGSD-5 | "Out of Scope (v0.1)" | Out-of-scope list lives only in brainstorm — unclear which items surface in MANIFEST vs INSTALL.md
- P2 | FGSD-6 | "Distribution mechanism" | agentskills.io deferral rationale (demo not yet live) undocumented in distribution artifacts
Verdict: needs-changes

### Summary
The brainstorm demonstrates exemplary scope discipline internally — the excluded_from_v01 list, the "Out of Scope (v0.1)" section, and the additive-overlay principle are all clearly stated. The gap is that this discipline lives in the brainstorm and the internal MANIFEST design, but the brainstorm does not specify how scope information migrates to the practitioner-facing artifacts (INSTALL.md, README, the human-readable MANIFEST fields). The single most impactful gap: the excluded_from_v01 list uses internal bead IDs as the only identifier for deferred features. An external practitioner reading  knows what the feature is but cannot decode when "v0.3" arrives or what the bead ID means. The scope boundaries are real; they need to be legible to practitioners who have no access to the internal tracker.

### Issues Found

FGSD-1. P1: excluded_from_v01 uses internal bead IDs — opaque to external practitioners — The MANIFEST.yaml schema (§"MANIFEST.yaml schema (v1)") shows  entries formatted as . The bead ID  is interpretable only by someone with access to the internal beads tracker. An external practitioner who wants thinker-profile-mcp cannot determine: (a) whether it is actively planned or aspirational, (b) when v0.3 is expected, or (c) where to track progress. The excluded_from_v01 list is intended as doctrine ("it answers 'is this in v0.1?' without re-litigating each time") but it cannot serve that function for external practitioners if the entries are opaque.

FGSD-2. P1: No Hermes prerequisite check — assumption undeclared and unverified — §"Install path assumption" states "v0.1 assumes the user has Hermes already installed via the upstream install.sh. We do NOT vendor Hermes." The install.sh contract (§"install.sh contract", step 1) detects the Hermes install location, which will fail if Hermes is absent — but the failure mode is not specified. The brainstorm does not describe a pre-flight check at the top of install.sh that runs , exits non-zero with a clear message if Hermes is not found, and points the practitioner to the upstream installer. Without this, the first-time installer experience for the most common mistake (missing prerequisite) is an undiagnosed mid-run failure.

FGSD-3. P2: Additive-overlay principle absent from distribution artifacts — §"Install path assumption" states two first-class principles: "We do NOT vendor Hermes" and "We do NOT compete with hermes-agent.nousresearch.com." These principles protect downstream forks and set clear expectations for the distribution's relationship to Hermes. They are stated in the brainstorm but the brainstorm does not specify that they appear in INSTALL.md or a distribution README. A practitioner who forks the distribution and vendored Hermes would have no artifact-level statement that this is out-of-scope behavior.

FGSD-4. P2: Hermes-only scope not stated as explicit non-goal for other agent frameworks — The brainstorm establishes that v0.1 is Hermes-only, but the MANIFEST.yaml schema (§"MANIFEST.yaml schema (v1)") does not include a  or equivalent field. Silence about other agent frameworks (Claude Code native, Codex, etc.) invites confusion. A practitioner who wants to install Auraken into a non-Hermes setup has no clear artifact-level statement that this is out of scope for v0.1.

FGSD-5. P2: Out-of-scope list scope not fully specified for distribution artifacts — §"Out of Scope (v0.1)" and the MANIFEST.yaml  both carry scope information, but the brainstorm does not specify which items from the Out of Scope list appear in INSTALL.md's Prerequisites or What's Not Included sections vs. only in MANIFEST.yaml. External practitioners reading INSTALL.md (not MANIFEST.yaml) may not encounter the full scope picture.

FGSD-6. P2: agentskills.io deferral rationale undocumented in distribution artifacts — §"Distribution mechanism" defers agentskills.io submission to v0.2 "after demo is up. Don't submit a tarball whose demo doesn't exist yet." This rationale is sound but internal. An external practitioner who searches agentskills.io and finds nothing has no artifact-level explanation of why the secondary channel is absent. INSTALL.md could note "agentskills.io listing pending — submit v0.2 after demo is available."

### Improvements

1. Replace bead IDs in excluded_from_v01 with human-readable descriptions and target version milestones — e.g., . Bead IDs can appear as secondary references in comments but should not be the primary identifier.

2. Add a Prerequisites section as the first section of INSTALL.md — should include:  check with minimum version, link to upstream Hermes installer, and list of optional prerequisites (Go toolchain if using binary option b).

3. Add the additive-overlay principle to the distribution README as a framing statement — one paragraph explaining that Auraken extends a working Hermes install and does not modify the Hermes core, with a link to the upstream Hermes project.

4. Add a  field to MANIFEST.yaml — explicitly listing non-Hermes agent frameworks as out of scope for v0.1 so practitioners using other frameworks have a clear artifact-level signal.

5. Mirror the full Out of Scope list in INSTALL.md under a "What's not included in v0.1" section — practitioners reading INSTALL.md should not need to parse MANIFEST.yaml to understand the distribution's boundaries.

<!-- flux-drive:complete -->
