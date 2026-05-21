# Findings — fd-heian-warifu-tally-certificates

**Target:** `/home/mk/projects/Sylveste/docs/research/flux-review/anthropic-cc-platform-gaps-sylveste/2026-05-06-target.md`
**Lens:** Heian/Kamakura warifu (割符) split-tally certificates, kugen (公験), kanmotsu (官物) — authority-at-signature-time, on-face scope encoding, graceful degradation under issuer collapse.

---

## P0 — All seven prior-pass deprecation targets are silently registry-shaped

**Finding.** Every primitive in the prior-pass list (target.md lines 18-25: durable memory, parallel agent fleet, multi-session coordination, cost/context observability, code recon, task tracker, managed AGENTS.md surface) is implicitly proposed as a *registry-model* primitive — its validity at verification time depends on the issuing service (Anthropic) still running, reachable, and willing to respond. Heian provincial administration faced this exact question in the 9th–11th centuries: when the central court's capacity fluctuated, registry-stored authority evaporated; warifu solved it by *vesting authority at signature time inside the artifact itself* (the matched halves, the calligraphic seal patterns, the on-face scope inscription).

**Failure scenario.** The user migrates from Claude Code to Codex or Cursor 18 months from now, or Anthropic deprecates one of these primitive surfaces. The 63-plugin ecosystem's accumulated evidence trail — every closed bead, every reflect doc, every cost receipt — is registry-durable, not artifact-durable. A bead that "exists" only via Anthropic's hosted task-tracker service is a token, not evidence. Sylveste PHILOSOPHY principle 1 ("every action produces evidence. Receipts, not narratives") collapses to "every action produces a token pointing at a service that may not answer."

**Concrete on-target translation.** The prior-pass list (target.md §"Initial findings") names *what* to ship but not *what shape*. For each of the seven, the artifact-durability test must be specified before commitment:

| Primitive | Warifu test | Registry-shape failure |
|---|---|---|
| Durable memory | Can a third-party tool read & verify the memory artifact offline? | Hosted vector store — silent loss on outage |
| Task tracker | Is the bead a self-contained file with embedded provenance? | Hosted tracker — beads vanish on migration |
| AGENTS.md surface | Does file include enough context for a vendor-neutral compiler? | Anthropic-only interpretation runtime |
| Cost/context observability | Are receipts cryptographically self-authenticating? | Dashboard-only — no portable audit trail |
| Code recon cache | Is the cache content-addressed & vendor-neutral? | Anthropic-keyed cache — re-pay on switch |
| Parallel agent fleet | Do findings carry their own provenance signatures? | Findings exist only in synthesis context |
| Multi-session coordination | Is the lock state a verifiable artifact? | Hosted lock service — split-brain on outage |

**Smallest viable fix.** Add an explicit row to target.md's success-criteria table: "For each primitive, classify as registry-shape or warifu-shape, with the artifact-durability test specified." Prior-pass list (lines 18-25) becomes structurally weaker without this annotation; with it, the prior pass is recoverable into actionable specifications.

---

## P1 — Cross-vendor AGENTS.md standardization (target.md §5, success criterion 5) is proposed without the warifu test

**Finding.** Target.md success criterion 5 ("Strategic / business-model angles ... open-sourced or standardized cross-vendor (e.g., AGENTS.md across Codex/Cursor/Gemini)") frames standardization as a strategic question without asking the warifu test: *can a Codex user, with no live connection to Anthropic, validate that an AGENTS.md was correctly authored under the standard?* If the answer requires querying an Anthropic-hosted schema service or canonical interpretation runtime, the standard is registry-shaped — Anthropic technically "open" while practically gating.

**Failure scenario.** Anthropic publishes "AGENTS.md v1 spec," vendors adopt it nominally, then Anthropic ships v1.1 with extended attributes resolved through a hosted resolver. Codex-authored AGENTS.md files start failing validation in Claude Code six months later. The standard fragments while still being labeled "open." This reproduces the late-Heian fragmentation — provincial offices nominally followed Engishiki but their kugen (公験) interpretations diverged once central enforcement weakened.

**Smallest viable fix.** Target.md should require, as part of its strategic-angle success criterion, the warifu test stated explicitly: *"Verify that an artifact emitted under the standard is validated by a tool that has never contacted Anthropic, on a network with no path to Anthropic infrastructure."* If a primitive can pass this test, it is warifu-shaped; if not, the standard is theatrical.

**Question to the prior pass.** Does the proposed AGENTS.md standardization include a publicly versioned schema, an open-source reference validator, and explicit semantics for unknown-attribute handling? Without these three, the standard fails the warifu test.

---

## P2 — Five observability plugins collapse into one canonical receipt format (the structural reframing the prior pass missed)

**Finding.** The prior pass (target.md lines 65-69) groups interstat, intercept, interpulse, tool-time, and intertrust into "Cost, efficiency, observability (5)" as five separate primitives. The warifu lens reveals these are five instances of one missing primitive: a *canonical self-authenticating receipt format*. Each plugin currently emits private telemetry incompatible with the others; receipts cannot be aggregated, cross-validated, or migrated as a single corpus. Heian provincial administration solved exactly this problem by mandating a single warifu shape across kanmotsu (tax), kugen (land), and travel permits — different concerns, one artifact format.

**Failure scenario.** Three years from now, the user wants to answer: "What is the total verified cost of Sylveste development this quarter, traceable to specific landed changes, auditable by an outside observer?" Today's answer requires running interstat queries, joining against intercept logs, normalizing intertrust scores, and trusting the integrity of each plugin's private store. Under a canonical receipt format, the answer is a single SQL-able corpus of signed, scoped, time-bounded receipts.

**Concrete on-target translation.** Add to target.md's success-criteria list (after criterion 4): *"Identify whether two or more prior-pass items collapse into a single deeper primitive when viewed through any cross-domain lens."* The warifu lens supplies one specific instance: at minimum interstat + intercept + interpulse + tool-time + intertrust collapse into "canonical receipt format." This is the kind of structural reframing the prior pass was supposed to find but didn't.

**Smallest viable fix.** A single new success criterion line, plus a worked example showing the five-into-one collapse with named plugins.

---

## Hidden coupling the prior pass missed (warifu-specific)

The prior pass identifies "hidden coupling" as success criterion 4. The warifu lens surfaces a coupling the prior pass did not name: **interlock + intercept + intertrust + interspect all encode authority-at-signature-time**. interlock reservations are warifu (the matched halves prove "I held this when I started"); intercept gate verdicts are warifu (the local model's decision is signed at decision time, not re-litigated); intertrust scores are partial warifu (signed at observation time but not propagated as artifact); interspect routing-overrides are warifu (the override is itself a dated artifact). Recognizing these four as authority-at-signature-time primitives reveals that what's missing is not four separate observability surfaces but *one signed-decision primitive* — a hook contract that produces dated, scoped, signed artifacts at every decision point.

---

## Graceful degradation specification (per primitive)

For each of the prior-pass seven, name the degradation mode under Anthropic service outage:

1. Durable memory → if registry-shaped, blank session start; if warifu-shaped, local file replay.
2. Parallel agent fleet → if registry-shaped, no dispatch; if warifu-shaped, queued artifacts replay when service returns.
3. Multi-session coordination → if registry-shaped, split-brain; if warifu-shaped, last-known reservation honored locally.
4. Cost/context observability → if registry-shaped, blind operation; if warifu-shaped, local receipts continue accumulating.
5. Code recon → if registry-shaped, slow rebuild; if warifu-shaped, content-addressed cache continues serving.
6. Task tracker → if registry-shaped, work invisible; if warifu-shaped, local bead files remain authoritative.
7. AGENTS.md surface → if registry-shaped, vendor-locked interpretation; if warifu-shaped, file remains semantically valid for any compliant tool.

The prior pass should require this row-by-row specification. Without it, "durable" is a marketing word.

---

## Defers to peer agents

- fd-yoruba-ifa-babalawo-verification-chain on canon-arbitrated divergence resolution and reputational decay (this finding focuses on artifact authority and graceful degradation).
- fd-marshall-rebbelib-stick-chart-pedagogy on training-time vs runtime classification (this finding focuses on receipt portability and self-authentication).
