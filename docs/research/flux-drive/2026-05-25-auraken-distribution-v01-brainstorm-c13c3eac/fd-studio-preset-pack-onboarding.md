<!-- run-uuid: fed42cc6-b03c-4e8e-a5a8-bc6e14fd3c7c -->

### Findings Index
- P1 | SPPO-1 | "install.sh contract" | Next-steps output describes components, not invocation — practitioner left without copy-pasteable first command
- P1 | SPPO-2 | "What We're Building" | No 'What to expect' section in INSTALL.md design — behavioral baseline absent
- P2 | SPPO-3 | "Bundle layout" | voice-rubric.md ships with no self-description — opaque to practitioners unfamiliar with register_check
- P2 | SPPO-4 | "MANIFEST.yaml schema (v1)" | Register drift documented in MANIFEST but not explained experientially in INSTALL.md
- P2 | SPPO-5 | "CHANGELOG seed" | CHANGELOG framed as development artifact — not oriented to net-new practitioners
- P2 | SPPO-6 | "install.sh contract" | Recovery path (wrong model behavior) absent from install.sh next-steps and INSTALL.md design
Verdict: needs-changes

### Summary
The v0.1 brainstorm designs an installer that correctly handles technical assembly but does not close the loop on the practitioner's onboarding experience. The install.sh next-steps print is described (step 6: "how to invoke /auraken, where logs go, how to uninstall") but the brainstorm does not specify that this output includes the exact Hermes command the practitioner should type first. A preset pack that delivers the presets but does not show the photographer which menu to open has failed the last step. The behavioral baseline — what does a correctly-working Auraken session look and feel like, in one paragraph — is absent from the distribution artifact design. This means practitioners cannot distinguish correct behavior from defects on their first session.

### Issues Found

SPPO-1. P1: Next-steps output describes components, not invocation — Section "install.sh contract" step 6 specifies printing "how to invoke /auraken, where logs go, how to uninstall." "How to invoke /auraken" is ambiguous — does it mean a description of the invocation mechanism, or the exact command? A net-new Auraken practitioner who has never seen the SKILL.md does not know whether to type `/auraken`, `auraken`, `!auraken`, or something else in their Hermes session. The brainstorm does not specify that the next-steps output includes a copy-pasteable example. Without this, first-run success depends on the practitioner's ability to infer invocation syntax from SKILL.md.

SPPO-2. P1: No 'What to expect' section in INSTALL.md design — The brainstorm specifies INSTALL.md content (install instructions, prerequisites, uninstall) but does not include a "What to expect" section that describes Auraken's distinctive behavior in one paragraph. Without this, a practitioner who successfully invokes Auraken cannot tell whether their first session is working correctly or whether the behavior they're seeing is what Auraken is supposed to do. The behavioral baseline — ask-first style, no method descriptions, lens selection without menus — should be in INSTALL.md so practitioners can recognize correct behavior on first contact.

SPPO-3. P2: voice-rubric.md ships with no self-description — Section "Bundle layout" includes `voice-rubric.md` as "extracted voice criteria for register_check." The bundle delivers this file to practitioners, but the brainstorm does not specify that voice-rubric.md has a self-describing header explaining what register_check is and when to use it. An external practitioner who opens voice-rubric.md and sees a list of voice criteria without context will interpret it as an internal development artifact and ignore it, missing the register verification capability entirely.

SPPO-4. P2: Register drift documented in MANIFEST but not explained experientially in INSTALL.md — Section "MANIFEST.yaml schema (v1)" includes `gpt-5.5` in the model matrix with a comment "observed register drift documented." A practitioner using gpt-5.5 who experiences degraded behavior has no artifact-level explanation of what register drift looks like experientially: does Auraken respond in a flatter voice? Ignore the ask-first constraint? Produce generic responses? Without this, practitioners cannot distinguish expected GPT register drift from a configuration error or a bug to report.

SPPO-5. P2: CHANGELOG framed as development artifact — Section "CHANGELOG seed" states the v0.1 entry will describe "what changed from the recon spike (mostly: structure + manifest + install script)." This framing is useful for contributors who know what the recon spike was, but meaningless to a net-new practitioner for whom v0.1 is the first contact. The CHANGELOG entry should include a "First release" summary oriented to practitioners: what Auraken is, what this bundle contains, and where to start — not what changed from an internal development artifact.

SPPO-6. P2: Recovery path absent from installer design — The install.sh next-steps (step 6) and INSTALL.md are not specified to include a recovery path for unexpected first-session behavior. If a practitioner using gpt-5.5 experiences register drift, or invokes Auraken and sees generic responses, they have no installer-provided path to: (a) verify which models were validated, (b) know whether their behavior is expected, or (c) know how to report it. INSTALL.md should include a troubleshooting section or at minimum a link to "known model behavior differences."

### Improvements

1. Specify that install.sh next-steps output includes a copy-pasteable first command — e.g., "To start your first Auraken session: open Hermes and type `/auraken hello`" — not a description of invocation but the exact text to type.

2. Add a 'What to expect' section to INSTALL.md design — one paragraph describing Auraken's distinctive behavioral contract (ask-first, no menus, lens selection without method descriptions) so practitioners can recognize correct behavior on first contact.

3. Specify that voice-rubric.md includes a two-sentence self-description at the top — "This file defines the register criteria used by register_check. If Auraken's responses feel off, run register_check to verify register fidelity."

4. Add a 'Model behavior notes' section to INSTALL.md — describing what register drift looks like experientially for GPT models (flatter tone, less distinctive questioning) and telling practitioners this is expected and documented, not a bug.

5. Reframe CHANGELOG v0.1.0 entry to be practitioner-oriented — open with "First public release of Auraken as a Hermes Agent distribution" before the technical diff from the recon spike.

<!-- flux-drive:complete -->
