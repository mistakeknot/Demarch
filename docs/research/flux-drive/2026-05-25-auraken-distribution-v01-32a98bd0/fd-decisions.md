# fd-decisions review — 2026-05-25-auraken-distribution-v01

Target: docs/prds/2026-05-25-auraken-distribution-v01.md
Reviewer: fd-decisions (decision-quality lens)
Date: 2026-05-25

## Summary

The PRD makes several good-faith transparency moves — `tested: false` labels, honest `excluded_from_v01` list, labeled convenience shortcut — but three structural problems undercut its decision quality. The Go-binary dependency (benl.1) is asserted as resolved when the source package has no shipped state whatsoever; the "voice quality before public exposure" dependency on `lfdy` and `whyj` is buried in bead metadata and invisible in the PRD; and the "9 features" decomposition hides a meaningful ordering constraint that could force a costly mid-flight pivot if F2 hits the Go-binary gap.

## Findings

### F-DEC-1: Go binary dependency (benl.1) is phantom infrastructure [P0]
- **Evidence:** F2 AC: "shell out to the `auraken-lens` Go binary"; F3 AC: "Build the `auraken-lens` Go binary from `benl.1`"; Dependencies section: "benl.1 Go package built and tagged at `auraken-lens@v0.1.0` (internal — same Sylveste monorepo)." The bead `sylveste-benl.1` ("Extract lens library to Go package") has `status: open` with no notes, no started_at, no shipped artifacts. No `.go` files exist anywhere under `apps/Auraken/`. The current `server.py` still imports `auraken.lenses` from the Python source.
- **Recommendation:** Before F2/F3 can be planned, gate them explicitly on `sylveste-benl.1` shipping. Either (a) treat benl.1 as a prerequisite feature with its own AC inside this epic, (b) explicitly open-question whether the binary should be built from the Python implementation via PyInstaller/Nuitka as a stopgap, or (c) rename the dependency to "Python subprocess shell-out" and note Go binary as v0.2 aspiration. The current framing implies the Go binary exists; it does not.
- **Lens:** Assumption laundering — a dependency is referenced as though it is an internal engineering detail when it is actually an unstarted upstream work item with non-trivial complexity.

---

### F-DEC-2: Voice-quality blocking dependencies (lfdy, whyj) absent from PRD [P0]
- **Evidence:** The heh8 bead description explicitly states: "sylveste-lfdy (multi-model voice generalization) — needed before public exposure, since CLIProxyAPI exposes GPT-family models alongside Claude. sylveste-whyj (Signal corpus ingest for voice fidelity) — needed before public exposure for the same reason." Both beads are `open` with no started_at. Neither appears anywhere in the PRD's Dependencies section, Non-goals, or Open Questions. The PRD states its goal as shipping "a v0.1 distribution bundle" that "any user with a working Hermes Agent install can install." A public distribution without multi-model voice fidelity ships a degraded product to the first external user on GPT-family models.
- **Recommendation:** Add lfdy and whyj to the Dependencies section with an explicit decision: (a) v0.1 is Claude-model-only and MANIFEST clearly gates on that, or (b) v0.1 ships untested on GPT-family with MANIFEST `tested: false` and an explicit disclaimer in INSTALL.md, or (c) lfdy/whyj are v0.1 prerequisites and the scope/timeline expands accordingly. The current PRD lets implementers discover this constraint during F6/F9 when it is too late.
- **Lens:** Hidden prerequisite — load-bearing blocking conditions that were visible in upstream planning documents were not surfaced when the PRD was drafted, leaving a decision that looks resolved (v0.1 scope) when it is not.

---

### F-DEC-3: "Tested: false is transparency" vs. "tested: false is a ship blocker" not adjudicated [P1]
- **Evidence:** F9 AC: "Untested models in MANIFEST are marked `tested: false` with rationale." Open Question 5: "v0.1 ships macOS untested, claimed in MANIFEST with honest `tested: false` annotation." The PRD treats this as a design virtue (transparency). But the heh8 bead's acceptance criterion 1 requires "known-working model matrix," which implies testing is required, not just disclosed. And Open Question 2 in the PRD (macOS) sits alongside a policy ("lean manual for v0.1") as though the policy resolves the question. It does not: the question is whether shipping `tested: false` on a platform is compatible with a quality bar for public distribution.
- **Recommendation:** Add a decision record: define what minimum testing coverage gate is required to ship v0.1 publicly. The decision must answer: Is a `tested: false` entry for any target platform (darwin-amd64, darwin-arm64, WSL2) a blocker or a caveat? Right now the PRD says "honest label" but the heh8 bead says "known-working model matrix." These are in tension.
- **Lens:** Ambiguity collapse — the phrase "tested: false with rationale" papers over an unresolved policy question about minimum viable evidence for a public release.

---

### F-DEC-4: Trajectory disclosure default deferred to plan phase — but it has architecture implications now [P1]
- **Evidence:** Open Question 4: "Trajectory disclosure default — opt-in (user must enable) vs documented-opt-out (default-on, disclosed). Plan phase decides." The current `server.py` writes trajectory JSONL unconditionally to `~/.hermes/auraken/trajectories`. F4 AC requires install.sh to offer `--uninstall` to "remove trajectories." F6 voice-rubric.md is explicitly for training signal. If the plan phase chooses opt-in, install.sh needs a different flow, INSTALL.md needs different copy, and the trajectory path in F9's smoke test needs a conditional. If opt-out wins, GDPR/privacy disclosure requirements enter INSTALL.md.
- **Recommendation:** Resolve this before plan phase begins, not during. The decision surface is narrow (two options with clear tradeoffs) and both outcomes have upstream impact on F4, F5, and F9 AC. Deferring to plan phase means the plan will make a reversible-seeming decision that has already been partially locked by F1 MANIFEST schema and F4 install.sh structure.
- **Lens:** Decision-criteria leakage — a policy question is deferred to a phase where engineering choices in adjacent features have already narrowed the option space.

---

### F-DEC-5: F2 → F3 dependency is implicit but critical to the build order [P1]
- **Evidence:** F2 AC requires the Go binary at a resolved path; F3 builds the binary; F9 tests the full install. The feature list presents them in order but the PRD says nothing about sequencing. A developer reading F2 in isolation could attempt implementation and discover mid-feature that the binary it shells out to does not yet exist (F3 isn't done). More critically, F3 builds from `benl.1` (see F-DEC-1 above), so the real sequence is: benl.1 ships → F3 → F2 → F4 → F7 → F9. This is a six-step linear chain that the PRD does not surface.
- **Recommendation:** Add an explicit "Implementation sequence" note to the PRD (not a plan, just the blocking order): benl.1 → F3 → F2 → (F1, F4, F5, F6 parallelizable) → F7 → F8 → F9. Any parallelization assumption in plan-phase resourcing will otherwise produce false confidence.
- **Lens:** Implicit ordering constraint — the AC are individually sound but the cross-feature dependency chain is invisible at the PRD level, creating a planning blind spot.

---

### F-DEC-6: Python-vendor vs. Go-binary decision may be rationalizing sunk direction, not resolving it [P2]
- **Evidence:** The Solution section frames the Go binary shell-out as resolving a "P0" (monorepo-relative imports). The actual P0 is the import path; the Go binary is one solution. The alternative — fixing the Python import to be installable via a released PyPI package or vendored wheel — is never mentioned. The `sylveste-benl.1` bead (the Go package) has been `open` since at least April 2026 with no progress. The PRD's Problem section says "MCP server's import paths are monorepo-relative (P0)" but the Solution jumps directly to "shell out to the auraken-lens Go binary" without documenting why the Python-installable path was rejected. The recon spike `server.py` still uses `auraken.lenses` via AURAKEN_SRC env var — a workaround that could also be formalized.
- **Recommendation:** Add a one-paragraph decision record to the Solution section: "Python-installable package considered and rejected because X; Go binary chosen because Y." The current PRD presents the Go binary as the only option, but the option space is wider, and benl.1's non-existence makes the "Go binary" framing potentially a direction rather than a decision.
- **Lens:** False resolution — the technical approach is presented as settled when the upstream work to realize it has not started and an alternative path exists.

---

### F-DEC-7: Two-step install vs. one-liner is decision theatre with an obscured real question [P2]
- **Evidence:** F5 AC: "Two-step install path is the first install instruction users see. One-liner appears only after the two-step, labeled 'convenience shortcut' with a warning." The PRD Solution states this "resolves" a "pre-verification curl|bash" P0. But this is a UX ordering decision masking the actual unresolved question: who verifies the checksums and how? `sha256sum -c` only works if users have a trusted reference checksum — which requires either (a) checksums signed by a known key (F8's `checksums.txt.asc`), (b) checksums displayed on a trusted web page, or (c) checksums embedded in a trusted release artifact. The PRD's Open Question 2 defers the GPG signing identity question. If signing identity is deferred, step 2 of the "safe" two-step is theatrically safe but not actually verified against a trusted root.
- **Recommendation:** Link the install documentation decision (F5) explicitly to the signing identity decision (Open Question 2). The two-step approach is only meaningfully safer than the one-liner if F8's signing workflow is resolved first. Consider making Open Question 2 a prerequisite for F5 AC finalization rather than a plan-phase deferral.
- **Lens:** Proxy decision — the "two-step vs. one-liner" framing resolves a visible UX concern while leaving the underlying trust-chain question open, creating the appearance of a security improvement that depends on an unresolved upstream choice.

---

### F-DEC-8: "9 features" count obscures a missing F0 [P2]
- **Evidence:** The nine features cover scaffolding, implementation, build, install, docs, skill assets, assembly, release, and E2E test. There is no feature for "fix monorepo-relative imports in the existing server.py to be distribution-ready" as a standalone deliverable — the closest is F2's rewrite, which conflates import-fix with soundpost-response-shape with shell-out-to-Go-binary. These are three distinct decisions bundled into one feature: (a) decouple from monorepo Python path, (b) enforce soundpost shape at schema level, (c) switch execution model from direct import to subprocess. Each can fail independently and has different rollback cost.
- **Recommendation:** Consider splitting F2 into F2a (decouple from monorepo path, can use Python subprocess or stub) and F2b (shell-out to Go binary). F2a can ship before benl.1 exists using a Python subprocess or an env-var-configured Python path that ships as a released package. F2b becomes the Go-binary integration. This splitting de-risks the critical path: F2a is the actual P0 fix; F2b is a capability improvement.
- **Lens:** Artificial feature bundling — distinct decisions with different risk profiles and blockers are collapsed into a single feature number, obscuring the granularity needed for honest scheduling and rollback planning.

---

### F-DEC-9: agentskills.io submission deferred but SKILL.md schema requires compliance now [P3]
- **Evidence:** Non-goals: "agentskills.io submission (waits until v0.2 has a demo)." F6 AC: "SKILL.md is identical to or curated-from the recon-spike SKILL.md... with valid agentskills.io-compatible YAML frontmatter." The PRD defers submission but requires the submitted artifact to already conform to agentskills.io schema. If agentskills.io updates its schema between v0.1 and v0.2, the v0.1 SKILL.md will need revision before submission anyway.
- **Recommendation:** Either (a) confirm the agentskills.io schema is frozen and pin the version explicitly in F6 AC, or (b) note that SKILL.md schema conformance will need a re-validation pass before v0.2 submission. This is low-stakes but prevents a "we deferred submission, so we don't need to track schema drift" assumption from forming.
- **Lens:** Option-value erosion — the deferral creates a false sense that the deferred work is cost-free to resume; schema drift between v0.1 and v0.2 could impose re-work on what looked like a completed feature.

## Bottom Line

The single highest-leverage finding is F-DEC-1: the Go binary that F2, F3, and the entire distribution premise depend on does not exist (benl.1 is open with no progress), which means the PRD's defined scope cannot be executed as written — the first planning session will surface this gap and require a scope decision that the PRD should have resolved.
