# fd-user-product: Auraken Hermes Distribution v0.1 — User-Product Review

**Reviewer perspective:** PM who has shipped install-pipelines and developer-facing distributions.
**PRD:** `docs/prds/2026-05-25-auraken-distribution-v01.md`
**Date:** 2026-05-25

Severity scale: P0 (user can't use) / P1 (gates install or blocks first success) / P2 (UX degradation) / P3 (polish)

---

## F-UP-1 · P0 · No discovery surface defined — user has no way to find Auraken

**PRD section:** Problem / Non-goals
**Evidence:** The Problem statement frames the gap as an internal one: "The recon artifacts are scattered, unversioned, and not installable by a third party." Non-goals explicitly exclude "Landing page (auraken-web is separate)." Neither the feature set nor the AC specifies where a new user lands before they read INSTALL.md.

**Observation:** A conference attendee hears about Auraken. Where do they go? The PRD ships a GitHub release and an INSTALL.md inside the bundle tarball — but neither of those is findable without already knowing the GitHub repo URL. The release page is not linked from any discoverable surface named in this PRD. agentskills.io submission is deferred. auraken-web is out of scope. The README at the repo root is not mentioned. Result: install infrastructure ships but no one can find the front door.

**Recommendation:** Add F-DISC (even a one-liner): the repo root `README.md` must carry, at minimum, a one-paragraph description and a link to the release INSTALL.md. This is a five-minute artifact that unlocks every other investment. Alternatively, gate F8 (GitHub release) on the repo README containing a findable entry point — make it an AC: `README.md` links to the release page with one sentence of "what is this."

**User-product lens:** Every distribution shipped without a discovery surface is a distribution shipped for the team, not users. The install.sh is a dead letter if the user never reaches it.

---

## F-UP-2 · P0 · No user-facing value proposition — v0.1 does not answer "why install this?"

**PRD section:** Problem, Solution, F5 INSTALL.md
**Evidence:** Problem states: "The recon artifacts are scattered, unversioned, and not installable by a third party." This is a Sylveste-internal problem. Solution states: "Ship Auraken as a v0.1 distribution bundle… v0.1 = the bundle as artifact." F5 prerequisites are: working Hermes install, profile, optional CLIProxyAPI. F5 AC does not require a value proposition statement.

**Observation:** A user reading INSTALL.md sees: prerequisites, two-step install, first-turn behavior, uninstall. What they never see: why they should want this. "What is Auraken" and "what does having it installed change about my Hermes experience" are absent from every AC across all 9 features. The SKILL.md (F6) presumably carries behavioral description, but SKILL.md is a machine-facing format for Hermes registration — not a human-facing "here's why this matters."

**Recommendation:** Add one required section to INSTALL.md: `## What Auraken does` (2–4 sentences; user-facing, not behavioral-contract language). AC: section exists, does not use the word "behavior" or "contract," gives a concrete example of what a Hermes session feels different with Auraken installed vs. without. This section is the first thing a user reads before prerequisites.

**User-product lens:** If a user can't explain to a colleague in one sentence what they installed and why, the distribution has not shipped a product — it has shipped a binary.

---

## F-UP-3 · P1 · F9 voice-rubric scoring is untestable without a rubric scale definition

**PRD section:** F9 Acceptance Criteria
**Evidence:** "At minimum, claude-opus-4-7 transcript is captured and scored against voice-rubric.md (target: 8/10 recognizably Auraken)"

**Observation:** The 8/10 score is unverifiable without: (a) a defined scale (what is 1? what is 10?), (b) a scorer (who scores? the developer who wrote it? a blind reviewer?), (c) a scoring procedure (holistic impression? per-criterion checklist?). voice-rubric.md (F6) has a two-section schema with examples and anti-patterns, but F6's AC does not require a numeric scale or scoring procedure. F9 borrows a number from a rubric that doesn't yet define numbers. A CI gate on "8/10" with no rubric scale is a CI gate that will always pass because any score is unfalsifiable.

**Recommendation:** Either (a) extend voice-rubric.md AC (F6) to require a numeric scale with anchor definitions (1 = violates mandatory form; 5 = neutral; 10 = exemplary), or (b) replace the F9 score target with a checklist-based gate: "transcript does not trigger any anti-pattern from voice-rubric.md § Mandatory Form." Option (b) is CI-executable; option (a) requires a human rubric review step, which is fine if that step is named in the AC.

**User-product lens:** A score without a rubric is a vibe-check that ships whatever the author felt good about. For a behavioral-contract-enforcement system, that's exactly the thing being avoided architecturally (soundpost over declarative contract) but reintroduced manually at the test layer.

---

## F-UP-4 · P1 · First-invocation success signal is not defined for the user

**PRD section:** F4 install.sh, F5 INSTALL.md
**Evidence:** F4 AC: "Step 6 output includes the literal string `/auraken what are you working through?` (or similar opening invocation) — not a list of capabilities." F5 AC: "'What to expect on first turn' section gives 2-3 sentences describing Auraken's opening behavior so users can distinguish correct behavior from defects."

**Observation:** The install-complete transmissive close tells users what to type. But the AC for the "what to expect" section says 2-3 sentences of "opening behavior" — it does not require specifying a concrete success signal that a non-expert can compare against actual output. If a user types `/auraken what are you working through?` and gets a response, they do not know whether Auraken is active and working (vs. the base Hermes model responding without the skill). There is no AC requiring a visually or textually distinct first-turn marker indicating Auraken's presence.

**Recommendation:** Add AC to F5: "What to expect on first turn must specify at least one observable signal that confirms Auraken is installed and active (e.g., presence of a question as the first output token, absence of a list of options, Hermes showing skill attribution)." This should be a concrete observable, not a description of personality.

**User-product lens:** Install confidence is built by a success signal the user can see, not by behavioral tendencies they have to infer across multiple turns.

---

## F-UP-5 · P1 · Prerequisite failure modes are not covered in INSTALL.md AC

**PRD section:** F5 INSTALL.md AC, F4 install.sh AC
**Evidence:** F5 AC requires: prerequisites section naming Hermes version range, profile, optional CLIProxyAPI. F4 AC covers: Hermes binary not found, binary not found post-staging. Neither AC covers: wrong Hermes version (Hermes installed but too old), profile does not exist, Anthropic API access not configured (no key), Go toolchain absent (relevant if user tries to build from source after binary download fails).

**Observation:** These are the four most common first-install failure modes in developer tool distributions. The install.sh AC covers the binary-not-found case and rollback on staging failure. But INSTALL.md has no AC requiring "troubleshooting" or "common failure modes" content. A user who has Hermes but the wrong version gets a clear error from install.sh (F4 covers version check) but INSTALL.md gives them no recovery path in prose.

**Recommendation:** Add AC to F5: "INSTALL.md includes a Troubleshooting section covering at minimum: (1) Hermes version too old — link to Hermes upgrade path, (2) profile not found — how to create one, (3) install.sh exits with non-zero after binary download — manual verification steps." The Anthropic API access failure is Hermes's problem to surface, not Auraken's, but it should be noted as a dependency.

**User-product lens:** A troubleshooting section is not polish — it is the difference between a user who retries and one who files a GitHub issue or abandons.

---

## F-UP-6 · P1 · Trajectory collection consent is unspecified — Open Question #4 has no user-facing implication mapped

**PRD section:** Open Questions #4, Non-goals
**Evidence:** Open Question #4: "Trajectory disclosure default — opt-in (user must enable) vs documented-opt-out (default-on, disclosed). Plan phase decides." Non-goals: "Trajectory-collection centralized backend (file-based JSONL is sufficient for v0.1)."

**Observation:** Even with local-only JSONL trajectory storage, the user installs software that records their conversations to disk without explicit disclosure in the install flow. The PRD defers this to plan phase but does not specify: (a) where in the install flow consent is surfaced, (b) what language is used, (c) what happens if the user declines. The install.sh AC (F4) has no AC for a consent or disclosure step. INSTALL.md AC (F5) has no AC for a data-collection disclosure. This is not a regulatory edge case — it is the question "does Auraken write files about what I said to it, and where, and can I turn it off?"

**Recommendation:** Before plan phase, resolve Open Question #4 with a specific user-facing implication: at minimum, INSTALL.md must disclose that trajectory JSONL files are written to `<path>` and that `install.sh --uninstall` offers to remove them. Add this to F5 AC: "INSTALL.md discloses trajectory collection: file location, what is recorded, and how to disable or purge." The F4 AC already covers the uninstall trajectory-removal confirmation dialog — that's good — but the install-time disclosure is missing.

**User-product lens:** Local-only storage does not eliminate the expectation of disclosure. A user who discovers conversation logs they didn't know about is an uninstall and a trust breach.

---

## F-UP-7 · P2 · "Recognizably Auraken" in F9 is subjective without a scorer definition

**PRD section:** F9 AC
**Evidence:** "scored against voice-rubric.md (target: 8/10 recognizably Auraken)" — see F-UP-3. Distinct issue: who scores?

**Observation:** F9 AC does not specify: (a) whether the scorer is the author, a blind reviewer, or an automated checker, (b) whether inter-rater reliability has been validated, (c) what happens if the score is 7/10. This is separate from the rubric-scale gap (F-UP-3): even with a defined scale, an author-scored rubric is not a test — it is a self-assessment.

**Recommendation:** Add to F9 AC: "Score is assigned by a reviewer who was not the primary author of the SKILL.md for this release, using voice-rubric.md." For v0.1 (manual release), a named second reviewer is sufficient. If CI is added in v0.2, automate against the anti-pattern checklist instead of a numeric score.

**User-product lens:** Behavioral consistency is the core Auraken claim. Testing it with the author's own score is the same structural problem as a developer self-certifying their own security audit.

---

## F-UP-8 · P2 · F7 byte-identical determinism AC does not exclude embedded timestamps from Go binaries

**PRD section:** F7 build-dist.sh AC, F3 prebuilt binaries
**Evidence:** F7 AC: "Running the script twice produces byte-identical output (deterministic file ordering, no timestamps in files)." F3 AC: "Build script produces all four binaries deterministically."

**Observation:** Go binaries embed build timestamps by default unless `-trimpath` and `-buildvcs=false` flags are set, and CGO-enabled builds can embed additional non-deterministic data. The F3 AC says "deterministically" but does not require `-trimpath` or equivalent flags. F7's byte-identical AC covers file ordering and text-file timestamps but the Go binary is a binary file — the two-pass SHA256 comparison will fail if binary build is not reproducible-build-compliant. A user who verifies checksums.txt after re-downloading a binary rebuilt on a different CI run will get a mismatch.

**Recommendation:** Add to F3 AC: "Build flags include `-trimpath` and `CGO_ENABLED=0` (or equivalent reproducible-build flags); two separate `go build` invocations at the same commit produce SHA256-identical binaries." This is a testable AC.

**User-product lens:** A user who is security-conscious enough to run `sha256sum -c` (the recommended two-step path) will be confused by a checksum mismatch on a binary that hasn't changed. That confusion erodes trust in the integrity mechanism the PRD specifically calls out as a P0 fix.

---

## F-UP-9 · P2 · Non-goal "no demo instance" means users install blind — trust gap not mitigated

**PRD section:** Non-goals
**Evidence:** "Public demo instance / Discord or Telegram bot (separate sub-bead of heh8 for v0.2)" and "agentskills.io submission (waits until v0.2 has a demo)"

**Observation:** The non-goal is reasonable for v0.1 scope. But the combination of: no demo, no agentskills.io listing, no video, no GIF in README, and install.sh being a curl|bash (even de-emphasized) means users are being asked to run an installer for software they have never seen in action. The SKILL.md and voice-rubric.md help Hermes understand Auraken; they do not help a human decide whether to install. The PRD does not name a mitigation for this trust gap.

**Recommendation:** Add to F8 (GitHub release) AC or F5 (INSTALL.md) AC: "Release assets or release description include a transcript excerpt (≥1 annotated example exchange) showing Auraken behavior on a real thinking-through turn." This is a static artifact, not a live demo, and is achievable from F9's transcript output. A 10-line annotated exchange is the minimum viable trust signal for "install this on your AI agent."

**User-product lens:** The install.sh P0 fix (non-atomic, pre-verification curl|bash) is the right call. But security without trust is a harder sell, not an easier one. The user who reads "sha256sum before running" and also sees no evidence of what they're installing will opt out.

---

## F-UP-10 · P3 · F5 INSTALL.md "copy-pasteable commands" AC allows ambiguous profile name placeholder

**PRD section:** F5 INSTALL.md AC
**Evidence:** "All commands in INSTALL.md are copy-pasteable (no placeholders for user to fill in beyond an obvious profile name)"

**Observation:** "Beyond an obvious profile name" is not testable. What makes a placeholder "obvious"? `<your-profile>` is obvious to an experienced Hermes user; `profile` is obvious to no one who has never used Hermes. The carve-out defeats the copy-pasteable goal without constraining what the placeholder looks like.

**Recommendation:** Tighten the AC: "All commands are copy-pasteable. Where user-specific substitution is required (e.g., Hermes profile name), the placeholder is formatted as `YOUR_PROFILE_NAME` in all caps and explained in the immediately preceding sentence." This is testable: a reviewer counts non-explained placeholders.

**User-product lens:** Minor, but first-install drop-off on "I didn't know what to substitute" is measurable and common. The PRD is otherwise careful about copy-pasteable install paths; the carve-out should be equally precise.

---

## Summary

| Finding | Severity | Area |
|---|---|---|
| F-UP-1 No discovery surface | P0 | Distribution reach |
| F-UP-2 No user-facing value proposition | P0 | Value clarity |
| F-UP-3 Voice score untestable (rubric scale missing) | P1 | AC testability |
| F-UP-4 First-invocation success signal undefined | P1 | Install UX |
| F-UP-5 Prerequisite failure modes not covered | P1 | Install resilience |
| F-UP-6 Trajectory consent not specified | P1 | User trust / data disclosure |
| F-UP-7 Scorer identity not specified (voice rubric) | P2 | AC testability |
| F-UP-8 Go binary determinism AC incomplete | P2 | Integrity verification |
| F-UP-9 No-demo trust gap not mitigated | P2 | User trust |
| F-UP-10 "Obvious placeholder" AC not testable | P3 | Install UX |

**Counts:** P0: 2 · P1: 4 · P2: 3 · P3: 1

---

## Highest-leverage finding

**F-UP-2 (P0): v0.1 ships no user-facing value proposition.**

The PRD is internally coherent on the engineering problem (non-installable artifact) and solves it well. But the user-facing product question — "what do I get by installing this that I don't have without it, in one sentence" — is answered nowhere across 9 features. INSTALL.md's AC requires prerequisites, two-step path, first-turn behavior, and uninstall. It does not require a "what Auraken does" section. The voice-rubric.md and SKILL.md are machine-legible and author-legible, but neither is written for the person deciding whether to install. Until the bundle can answer "why install this" in 2–4 sentences written for a Hermes user who has never heard of Auraken, the distribution infrastructure ships a product that can only be adopted by people who already believe in it.
