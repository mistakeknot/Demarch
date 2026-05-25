<!-- flux-drive:complete -->

## Findings Index

- P0 | F-SYS-01 | F3 / F2 | Circular schema dependency — Go binary output shape and MCP server schema are mutually constraining with no declared resolution order
- P1 | F-SYS-02 | F8 / F4 | install.sh source-of-truth gap — release artifact has no declared dev-tree source; F7 and F8 disagree on its origin
- P1 | F-SYS-03 | F1 / F9 | Open feedback loop — MANIFEST.yaml `compatibility_evidence` declared in F1 but written by F9; no feature owns the write-back step
- P1 | F-SYS-04 | F4 | Fresh-user bootstrap gaps — profile_dir nonexistence and Hermes-installed-but-no-profile case both unhandled by install.sh AC
- P2 | F-SYS-05 | F2 / F3 | Soundpost invariant enforcement is split across two features with no cross-feature contract test
- P2 | F-SYS-06 | F1 / F6 / F7 | SKILL.md divergence risk — three features can independently mutate the skill file; none owns canonical authority
- P2 | F-SYS-07 | F1 / Non-goals | MCP schema extensibility for excluded_from_v01 items is undeclared; thinker-profile and voice-corpus hooks are absent
- P3 | F-SYS-08 | F7 / F3 | Build pipeline pace-layer mismatch — bundle assembly (F7) and binary build (F3) run at different cadences with no declared sync protocol

## Verdict

**BLOCKING — one P0, two P1s with installation-flow consequences.** The circular schema dependency between F2 and F3 (F-SYS-01) means neither feature has a stable interface to build against first; the PRD's implicit build order (F1 → F2 → F3 → F4 → F7 → F8 → F9 with F5/F6 parallel) hides this cycle. The F8/F4 source-of-truth gap (F-SYS-02) means install.sh could diverge between what the developer tests and what the release ships. The MANIFEST feedback loop (F-SYS-03) is a real open loop — F1 creates a structural promise that no feature is explicitly tasked with resolving before the release is cut.

## Summary

The PRD decomposes cleanly into nine features and has strong individual acceptance criteria, but the inter-feature dependency graph contains structural problems a linear read of F1–F9 obscures. The two most acute issues are a mutual dependency between F2 and F3 (each feature's AC demands the other's output shape be stable first) and the fact that install.sh appears in both F4 (as a dev artifact being written) and F8 (as a release asset being published) with no feature declaring which is canonical. The feedback from F9 smoke tests back into F1's `compatibility_evidence` is also an open loop — acknowledged in the PRD as a design intent but not assigned to any feature as an explicit task. The excluded_from_v01 items (thinker-profile, voice-corpus) have no extension hooks in the v0.1 MCP schema, creating a silent breaking-change risk at v0.3.

## Issues Found

### P0 | F-SYS-01 | Circular schema dependency: F2 ↔ F3

**Evidence**: F2 AC: "The MCP tool's output schema is `{lens, rationale, next_question, empty: bool}` — never a list." F3 AC: "Each binary passes a contract test: emits the single-object response shape for known thinking-through input."

**The cycle**: F2 (server.py rewrite) shells out to the F3 Go binary. The MCP schema in F2 is defined by what F3 outputs. The F3 contract test validates against the schema defined in F2. Neither feature can be written and tested in isolation: F2 needs F3 to produce valid JSON before its pytest suite can pass the "graceful error on missing binary" path beyond a stub; F3 needs F2's schema to be stable before its contract test is meaningful. The PRD's dependency section lists `benl.1 Go package` as an upstream dependency but does not acknowledge that benl.1's output contract is co-defined with F2, not pre-existing.

**Second-order effect**: If F3 is built first (binary produces `{lens, rationale, next_question}`) and F2 is rewritten after to add the `empty: bool` field as a required schema field, all existing F3 binary tests that emit `{lens, rationale, next_question}` silently fail the schema check without failing the binary's own `--version` smoke test. The mismatch is invisible until F9.

**Recommendation**: Add a feature F0 (or a pre-work AC in F1) that declares the canonical wire schema as a JSON Schema file under `dist/v0.1/schemas/lens-response.schema.json`. Both F2 (server.py) and F3 (Go binary contract test) reference this file as the authoritative spec. Neither feature owns the schema; F1 owns it. This resolves the cycle by extracting the shared invariant to a single source of truth.

**Lens**: Circular causality / shared invariant extraction

---

### P1 | F-SYS-02 | install.sh source-of-truth gap between F4 and F8

**Evidence**: F4 AC: "Running install.sh twice in a row produces no errors..." — F4 is clearly writing/testing an install.sh. F7 AC: "`bash apps/Auraken/dist/build-dist.sh v0.1` produces `dist/v0.1/`" — the bundle assembly script must include install.sh in the output. F8 AC: "Release assets include... install.sh for the one-liner shortcut" — F8 publishes install.sh directly as a release asset, parallel to the tarball.

**The gap**: F4 writes and tests install.sh. F7 (build-dist.sh) bundles something into `dist/v0.1/`. F8 publishes `install.sh` directly. Three features touch install.sh, but no feature declares:
1. Where install.sh lives in the dev tree (F4's AC doesn't specify a path).
2. Whether F7 copies the dev-tree install.sh into `dist/v0.1/` or generates it from a template.
3. Whether the F8 release asset is the F7-assembled version or the dev-tree version.

**Concrete failure mode**: A developer tests install.sh in the dev tree (F4), F7 assembles the bundle copying the same file, but F8 uploads install.sh from the dev tree directly (not from the tarball). If F7 performs any path substitution or variable injection during assembly (e.g., hardcoding the release tag), the dev-tree install.sh and the F8 release asset diverge. The one-liner curl shortcut then runs a different install.sh than what was tested.

**Recommendation**: F4's AC must specify the canonical source path for install.sh (e.g., `apps/Auraken/integrations/hermes/install.sh`). F7's AC must explicitly state that it includes install.sh from that path (and whether it performs substitutions). F8's AC must state it uploads from the F7-assembled tarball, not from the dev tree directly. One feature owns the canonical source; the others reference it.

**Lens**: Source-of-truth locality / single-writer principle

---

### P1 | F-SYS-03 | MANIFEST compatibility_evidence is an open feedback loop

**Evidence**: F1 AC: "Every claim in `compatibility:` has a corresponding row under `compatibility_evidence:`." F9 AC: "Captured transcripts are referenced in MANIFEST `compatibility_evidence.<model>.smoke_transcript`."

**The loop**: F1 creates MANIFEST.yaml with `compatibility_evidence` entries. F9 runs smoke tests and writes transcript paths back into MANIFEST. But F9's AC says "Captured transcripts are referenced in MANIFEST" — it does not say F9 writes to MANIFEST, nor does F1's AC allocate a placeholder row that F9 will fill. The feedback loop (F1 declares, F9 validates and writes back) is implied by the feature pair but not stated as a sequenced handoff with a defined update mechanism.

**Second-order problem**: F1 must ship a `tested: false` skeleton row in MANIFEST for every model. F9 must update those rows with actual transcript paths and voice scores. If F7 (build-dist.sh) runs between F9's test execution and the MANIFEST update, the bundle is assembled with stale `tested: false` rows. F8 then releases a MANIFEST that doesn't reflect the F9 results. The PRD's Open Question #6 (CI integration timing) directly intersects this: manual release makes the F9 → F1 write-back window undefined.

**Recommendation**: Add an explicit AC to F9: "After test completion, F9 updates `dist/v0.1/MANIFEST.yaml` `compatibility_evidence` rows for all tested models (setting `tested: true`, `smoke_transcript`, and `voice_score`)." Add an AC to F7 or F8: "build-dist.sh / release process runs only after F9 has executed and written back to MANIFEST." The feedback loop must be sequenced, not left as an emergent coupling.

**Lens**: Feedback loop closure / information latency

---

### P1 | F-SYS-04 | Fresh-user bootstrap: two unhandled edge cases in F4

**Evidence**: F4 AC item 3: "If the Hermes binary is not found, install.sh exits with a clear actionable error before touching any files." F4 AC item 1: "Running install.sh twice in a row produces no errors." No AC item covers profile_dir not yet existing or Hermes being installed but having no profile.

**Gap 1 — profile_dir doesn't exist**: install.sh step 1 "detects Hermes install + profile." If Hermes is installed but the user has not yet created a profile (a plausible fresh-install state for users following the docs), profile detection fails. The PRD does not specify whether install.sh (a) errors with instructions to create a profile first, (b) creates the default profile, or (c) installs into a default path without a profile. Each is a valid choice with different behavioral implications.

**Gap 2 — Hermes installed, version fails compatibility check**: F4 step 2 verifies Hermes version against MANIFEST. If the user's Hermes is below the minimum version, install.sh should exit. But the AC only tests for "Hermes binary not found" — a version-mismatch error path is unspecified, including whether it outputs the minimum required version and the upgrade path.

**End-to-end flow implication**: INSTALL.md (F5) lists "working Hermes install with version range" as a prerequisite. If install.sh doesn't gate on this, a user who skips reading INSTALL.md and runs the one-liner on an old Hermes gets a silent or cryptic failure from the MCP registration step, not a clear error from install.sh.

**Recommendation**: Add two F4 ACs: (a) "If Hermes is installed but no profile is found, install.sh exits with a message naming the command to create a profile;" (b) "If the detected Hermes version is below MANIFEST `compatibility.hermes_agent.min`, install.sh exits before touching files with the version found, the version required, and the upgrade URL."

**Lens**: End-to-end flow integrity / graceful degradation at system boundary

---

### P2 | F-SYS-05 | Soundpost invariant has no cross-feature contract test

**Evidence**: F2 AC specifies the MCP output schema and a pytest suite. F3 AC specifies a per-binary contract test. F9 AC specifies an E2E test that "confirms the lens MCP response shape is the single-object soundpost." But no single test exercises the full path: F3 binary → F2 shell-out → MCP tool call → response shape.

**The gap**: F2's pytest tests the server with a real or stubbed binary (the AC says "verifies... shape contract holds for thinking-through input" but does not say whether it uses the real binary or a stub). F3's contract test exercises the binary directly. Neither test exercises the integration layer: the real binary called from the real server.py returning the correct schema to a real MCP client. F9 runs the full E2E, but F9 comes last — the soundpost invariant can break at the F2/F3 seam and not be caught until F9.

**Recommendation**: Add an AC to F2 or F3: "An integration test (not stub) exercises the real binary called from server.py and validates the MCP response matches the schema in `dist/v0.1/schemas/lens-response.schema.json`." This closes the gap between unit coverage at each layer and E2E coverage at F9.

**Lens**: System-level invariant enforcement / test-layer mismatch

---

### P2 | F-SYS-06 | SKILL.md has three potential owners; canonical authority is undeclared

**Evidence**: F6 AC: "SKILL.md is identical to or curated-from the recon-spike SKILL.md; any divergences are documented in the bundle CHANGELOG." F7 AC: build-dist.sh copies from `integrations/hermes/skills/auraken/` into `dist/v0.1/`. F1 AC: the MANIFEST declares capabilities including the auraken skill. No feature declares which copy is canonical if they diverge.

**The triangle**: The recon-spike SKILL.md lives at `integrations/hermes/skills/auraken/SKILL.md`. F6 "copies/curates" it into `dist/v0.1/skills/auraken/SKILL.md`. F7 then assembles the bundle from the dev tree — but which tree: the pre-F6 `integrations/hermes/skills/auraken/` or the post-F6 `dist/v0.1/skills/auraken/`? If F6 curates (makes deliberate changes) into `dist/v0.1/`, and F7 copies from `integrations/hermes/`, the bundle ships the un-curated version.

**Recommendation**: F6's AC should specify that its output is `dist/v0.1/skills/auraken/SKILL.md` and that F7 includes that file verbatim (not the source in `integrations/hermes/skills/auraken/`). Alternatively, F6 should update the source-of-truth in `integrations/hermes/skills/auraken/` and F7 copies from there. Either model works; the PRD must pick one.

**Lens**: Single-writer principle / authority chain

---

### P2 | F-SYS-07 | v0.3 thinker-profile has no extension hook in v0.1 MCP schema

**Evidence**: F1 MANIFEST schema specifies `capabilities[].type` constrained to `{skill, mcp-server, binary, asset}`. Non-goals include "Thinker-profile MCP (sylveste-i0px — planned for v0.3)." F2 fixes the MCP tool output schema to `{lens, rationale, next_question, empty: bool}`.

**The gap**: The thinker-profile MCP (v0.3) will almost certainly need to add fields to the lens response (e.g., a `thinker_frame` or `profile_context` field), require a new MANIFEST capability type, and potentially add a new MCP tool. None of these are modeled in the v0.1 schema as extensible. If the MANIFEST `capabilities[].type` is validated against a closed enum (F1's AC: "one of {skill, mcp-server, binary, asset}"), adding `profile-server` at v0.3 is a schema break. If the MCP response schema is not versioned, adding a `thinker_frame` field at v0.3 breaks clients that validated against the v0.1 single-object shape.

**Recommendation**: (a) Add `capabilities[].type` to the JSON Schema as `enum` with an `x-extensible: true` marker or by using `oneOf` with an open `string` fallback; (b) version the MCP response schema (`lens-response.schema.json`) with a `schema_version` field so v0.3 can introduce `lens-response.schema.v2.json` without changing the `lens_select` tool contract; (c) note in F1 MANIFEST schema spec that `capabilities[].depends_on` and `min_distribution_version` must be sufficient to express the thinker-profile dependency graph.

**Lens**: Extensibility / pace-layer compatibility across version generations

---

### P3 | F-SYS-08 | Build pipeline pace-layer mismatch: F3 and F7 run at different cadences

**Evidence**: F3: "Build script... produces all four binaries deterministically." F7: "build-dist.sh... produces `dist/v0.1/` as a curated, deterministic release directory." F3 says binaries are built and tagged at `auraken-lens@v0.1.0`. F7 says the bundle is assembled deterministically. But the two scripts are not declared as calling each other.

**The mismatch**: F3's build-binaries.sh produces binaries (large, platform-specific, likely not committed to git). F7's build-dist.sh assembles the bundle from dev-tree files. If binaries are expected to be in the bundle tarball (F8 release assets), F7 must either (a) call F3 internally, (b) read pre-built binaries from a known path, or (c) reference the GitHub release assets by URL and skip bundling the binaries. None of these options is declared. The F8 AC lists binaries in checksums.txt but doesn't specify whether they're inside the tarball or separate release assets.

**Recommendation**: F7's AC should specify whether it includes the pre-built binaries in the bundle or references them externally. F8's AC should clarify the release asset structure (single tarball containing everything, or separate binary assets + script tarball). A single sentence resolves this, but without it, the assembly and release steps are underspecified.

**Lens**: Pace-layer mismatch / artifact dependency graph

## Improvements

1. **Resolve F-SYS-01 first** by adding a pre-work step (or F1 subtask) that declares the canonical wire schema as a versioned JSON Schema file. Both F2 and F3 reference it; neither owns it.
2. **Add two missing F4 ACs** for profile_dir nonexistence and Hermes version mismatch — these are the most likely real-user failure modes for a first install.
3. **Assign the MANIFEST write-back step to F9 explicitly** and sequence F7/F8 after F9 completes. The feedback loop is the right design; it just needs to be closed.
4. **Declare install.sh's canonical source path in F4** and have F7 and F8 reference it rather than each implicitly picking a copy.
5. **Add a single versioned field (`schema_version`) to the MCP response shape** now to avoid a breaking-change at v0.3.
