<!-- run-uuid: 1e048f43-8f72-4292-93bf-951314f97a39 -->
### Findings Index
- P0 | REL-1 | "Distribution mechanism" | curl-pipe-bash one-liner has no pre-execution integrity check
- P1 | REL-2 | "MANIFEST.yaml schema" | MANIFEST has no self-signed hash or provenance assertion — authentica is absent from the vessel
- P2 | REL-3 | "Bundle layout" | Dev-tree to dist-tree copy has no automation or verification — substitution can occur unobserved
- P2 | REL-4 | "auraken-lens binary distribution" | Deferred binary distribution decision leaves the lens relic unattached to the vessel during transport
Verdict: risky

### Summary

The distribution design achieves convenience (GitHub release + curl-pipe-bash) but not custody integrity. The curl-pipe-bash one-liner executes before the user can verify any seal — the vessel arrives at the shrine and is opened before its authentica is read. MANIFEST.yaml travels inside the tarball but contains no self-referential hash or signature that would let a careful receiver verify that the MANIFEST matches what the distributor sealed. The dev-to-dist copy step is described as "curated copy + version stamps" with no automation, creating a boundary at which substitution could occur unobserved. These are not hypothetical risks for v0.1's small audience, but they establish habits and precedents that scale badly.

### Issues Found

**1. [P0] REL-1 — curl-pipe-bash has no pre-execution integrity check (Section: "Distribution mechanism")**

The brainstorm's one-liner install is: `curl -fsSL https://github.com/.../install.sh | bash`. The INSTALL.md adds a "review before piping to bash" caveat, but the primary documented path is pipe-to-bash. The tarball's "signed checksums" are release assets — but the user who uses the one-liner never downloads the checksum file, never runs `sha256sum -c`, and never verifies the signature before running the installer. The curl-pipe-bash idiom fetches and executes in a single pipeline; there is no pause point for seal inspection.

Failure scenario: A GitHub release asset (install.sh) is compromised — either via a supply-chain attack on the Sylveste repo, a CDN compromise, or a DNS hijack of github.com. The user runs the one-liner. install.sh executes with arbitrary code before any integrity check. The "signed checksums" in the release assets are never consulted. The user has no detection mechanism.

This matches the P0 calibration exactly: "curl-pipe-bash install path has no integrity check before execution."

Smallest fix: Replace the one-liner in INSTALL.md with a two-step canonical install that downloads the tarball and checksum separately, verifies before executing: `curl -fsSL .../install.sh -o install.sh && curl -fsSL .../SHA256SUMS -o SHA256SUMS && sha256sum -c SHA256SUMS --ignore-missing && bash install.sh`. Keep the one-liner as a convenience footnote with an explicit "skips integrity verification" warning. The one-liner is not removed — it is demoted to a convenience path, not the canonical path.

**2. [P1] REL-2 — MANIFEST.yaml contains no authentica (Section: "MANIFEST.yaml schema")**

The MANIFEST.yaml schema includes: `schema`, `version`, `released`, `compatibility`, `capabilities`, `excluded_from_v01`. None of these fields contain a hash or signature that ties this specific MANIFEST copy to the release event at mistakeknot/Sylveste. The MANIFEST travels inside the tarball and says "version: 0.1.0, released: 2026-05-XX" — but these are claims, not attestations. A modified MANIFEST with the same version string is indistinguishable from the canonical one.

Analogy: The authentica is a document sealed inside the reliquary vessel, written in the hand of a known bishop, asserting "this relic is authentic." MANIFEST.yaml is the shipping manifest glued to the outside of the crate — it says what's inside but is not sealed.

Failure scenario: A downstream redistributor mirrors the release, modifies `binary_required:` to point to their own binary, and re-distributes. The MANIFEST still says `version: 0.1.0`. A user who installs from the mirror has no mechanism to detect that their MANIFEST differs from the canonical one — `sha256: <hash of original MANIFEST>` is not present in the MANIFEST itself.

Smallest fix: Add a `manifest_sha256:` field to the MANIFEST schema. The value is computed by the release pipeline: `sha256sum MANIFEST.yaml`. install.sh downloads MANIFEST.yaml separately from the tarball, recomputes its hash, and compares to the value in the release's SHA256SUMS file. This creates an authentica — the MANIFEST self-attests its own integrity, and the release SHA256SUMS file is the bishop's seal.

**3. [P2] REL-3 — Dev-tree to dist-tree copy has no automation or verification (Section: "Bundle layout")**

The brainstorm describes: "The existing source files at `apps/Auraken/integrations/hermes/{skills,mcp-servers}/` stay as the development tree; v0.1 is a curated copy + version stamps." The word "curated copy" implies a human manually copies files from dev tree to dist tree and adds version stamps. There is no mention of a build script, a CI job, or a file-identity check that verifies the dist tree matches the dev tree at a given commit.

Failure scenario: A developer updates `apps/Auraken/integrations/hermes/skills/auraken/SKILL.md` in the dev tree but forgets to propagate to `dist/v0.1/skills/auraken/SKILL.md`. The dist tree silently diverges from the dev tree. The released tarball contains stale content. This is the "dev-tree leakage" P2 — the boundary between dev and dist is porous and unmonitored.

Smallest fix: Add a `scripts/build-dist.sh` that copies from dev tree to dist tree, stamps version, and outputs a `dist-manifest.sha256` file that CI can verify. The script need not be complex — `rsync + version-stamp + sha256sum` is sufficient. The key is that the copy is automated and its output is verifiable, not manually curated.

**4. [P2] REL-4 — Binary distribution decision is deferred, leaving the relic unattached (Section: "auraken-lens binary distribution")**

The brainstorm defers the binary distribution decision (option a: vendor pre-built binaries; option b: document `go install` as a prerequisite) to the plan phase. This deferral means that at brainstorm time, the chain of custody for the most sensitive piece of the distribution — the Go binary that implements lens selection — is undefined. A vendored binary (option a) travels with the vessel and its integrity is covered by the tarball's signed checksums. A `go install` prerequisite (option b) means the binary is fetched separately, from a different source, at install time, with no connection to the release's signed checksums.

Failure scenario (option b path): User runs install.sh. install.sh calls `go install github.com/mistakeknot/Sylveste/...@v0.1.0`. The Go module proxy serves a different version than expected (proxy cache poisoning, or the tag was moved). The installed binary does not match the one tested against the distribution. The MANIFEST claims `binary_required: github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0` but install.sh's actual install behavior cannot be verified against this claim.

Recommendation: The brainstorm already identifies option a as "friendlier." From a chain-of-custody perspective, option a is not just friendlier — it is the only option that keeps the relic attached to the vessel during transport. Decision should be resolved in plan phase with a strong preference for option a. If option b is chosen, install.sh must verify the installed binary's hash against a value published in the release assets.

### Improvements

1. **Make the two-step install (download + verify + run) the canonical install path** in INSTALL.md, with the one-liner as a convenience shortcut that is clearly labeled "skips signature verification." This is a documentation choice, not an engineering choice.

2. **Add `manifest_sha256:` to MANIFEST.yaml schema now,** before the schema is frozen. Adding it after v0.1 ships requires a schema migration. The field's value is computed at release time and adds < 100 bytes to the manifest.

3. **Write `scripts/build-dist.sh` as part of v0.1 scope**, not as a v0.2 improvement. The "curated copy + version stamps" step is currently manual and invisible. Automating it is one shell script.

4. **Resolve the binary distribution question before plan phase closes.** The brainstorm notes "Likely answer: option a." Confirm it as the decision in the plan document. The chain-of-custody analysis clearly favors option a.

5. **Consider whether v0.1 → v0.2 supersession has a retirement ritual.** The brainstorm says "no in-place mutation of v0.1 after release" (sibling v0.2/ dir). But it does not describe what signals to a user that their v0.1 install is superseded. A `superseded_by:` field in MANIFEST.yaml (added when v0.2 ships) would let install.sh check at invocation time whether the installed version is still canonical.

--- VERDICT ---
STATUS: fail
FILES: 0
FINDINGS: 4 (P0: 1, P1: 1, P2: 2, P3: 0)
SUMMARY: The distribution design has a P0 gap — curl-pipe-bash executes before any integrity check — and a P1 gap — MANIFEST.yaml is not an authentica and provides no self-referential provenance. Both are fixable before v0.1 ships with minimal engineering cost; the P0 in particular should block release until the canonical install path includes a verify step.
---
<!-- flux-drive:complete -->
