---
artifact_type: reflection
bead: sylveste-6h7x
stage: reflect
date: 2026-07-11
---

# Runtime Evidence Close Gate

## Result

The runtime-evidence/v1 contract now blocks `reflect -> done` and managed bead
closure until the newest typed receipt proves build/install identity, a fresh
collector-started boot, healthy required subsystems, a unique live event, an
observed state delta, isolated resources, and complete cleanup. Missing,
shared, stale, malformed, or unverifiable evidence fails closed.

## Published Release

- Intercore: `11f2e57e32a833f78ff5e0895b0fc8c78f9880ec`, `ic 0.3.3`
- Clavain: `33d8d29087ff60efefa5e8903aaa4a274ce5ed6b`, plugin `0.6.263`
- Marketplace: `f10c288`, Clavain `0.6.263`
- Binary source: Clavain `04551d9dcf7d5f4fcc06cb2810fee4ddc8024855`
- Darwin CLI SHA-256: `db3bc2e12b6bdcb330ccfa0e088a7c99440e46fea4dd919852681d2a788de988`
- Linux CLI SHA-256: `66d88b03de6e247032d43a97f40219d36fa4b138461655d03b8e01aef17e4f2e`
- Darwin ic SHA-256: `689b838df306a5a82ae2d07f80788c88883f5882eaedd6fd9d4159a67e1162c2`
- Linux ic SHA-256: `143a8f4366664210bb6aa403982fd70dc73c2670ce7c77eab7d3f5c7916151f5`

All three shipped Clavain binaries report the same source revision,
`vcs.modified=false`, `-trimpath=true`, and the expected GOOS/GOARCH. The
tracked release manifest verifies their digests and the Intercore source head.
Both Claude installations record Clavain `0.6.263` at commit `33d8d29`, and
both Codex installation doctors are green against their canonical source.

## Live Canaries

### Clavain (darwin-arm64)

- Source canary completed all paths at Intercore `11f2e57` and Clavain
  `372cc3c` before the jq compatibility-only patch.
- Final installed canary used the published binaries at Clavain `33d8d29`.
- Missing proof: advance, verify, and canonical close all blocked; zero
  artifacts registered.
- Shared runtime: collection and advance blocked on nonce mismatch; cleanup
  independently verified; zero artifacts registered.
- Valid runtime: run `bc9l12sq` completed at `done`; proof
  `sha256:375fd96e49abbf89764a40efd232e0292a3247a114e7cac39f64cb7114660fec`;
  one typed artifact; cleanup verified.

### zklw (linux-amd64)

- Final installed canary used the published binaries at Intercore `11f2e57`
  and Clavain `33d8d29` under jq 1.7.
- Missing proof: advance, verify, and canonical close all blocked; zero
  artifacts registered.
- Shared runtime: collection and advance blocked on nonce mismatch; cleanup
  independently verified; zero artifacts registered.
- Valid runtime: run `znfceqpk` completed at `done`; proof
  `sha256:0ed0ade368e3061acf198d96340bad9c8bd11d3e4fe7d5648d73ec40c7821707`;
  one typed artifact; cleanup verified.

## Verification

- Intercore: full `go test ./...` and `go vet ./...` passed.
- Clavain Go: all tests except the sandbox-forbidden loopback test passed
  locally; that test passed in the live source canary.
- Clavain structural suite: 736 passed, 1 skipped.
- Darwin, Linux, and Windows builds succeeded; the Windows test binary also
  compiled.
- Release staging, late-build preservation, clean-source refusal, compose
  platform selection, canary argument handling, shell syntax, and shellcheck
  gates passed.
- Independent review found no remaining release or runtime-gate blocker.

## Reflection

Source-green is not release-green: the old installed binaries lacked the new
gate even while source tests passed. Release identity therefore has to include
installed byte digests and the actual plugin cache commit.

Packaging every worktree file made ignored binaries and unrelated worktrees a
deployment input. Publishing now rejects untracked files and copies only Git
tracked content; compose resolves the shipped wrapper or platform binary.

The zklw canary caught a jq 1.7 parser incompatibility that the Mac's jq 1.8
accepted. Cross-host live execution, not another source assertion, found the
last release defect.

Claude's update command advanced the version and cache bytes but left stale
commit metadata on zklw. A data-preserving reinstall corrected the record;
future deployment evidence must compare version, commit, and digest together.

The separate A:L3 natural-receipt target remains observational work. This gate
prevents false closure; it does not fabricate the ten no-touch receipts.

## Managed Close Receipt

Pending collection and terminal close for adopted run `ahpywy66`.
