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
- Clavain: `1cdccbc83c12ab8dc580a3ed8d6394bd16187acd`, plugin `0.6.265`
- Marketplace: `807acbf050a5550b1b259e7b3c57d240baad2593`, Clavain `0.6.265`
- Binary source: Clavain `04551d9dcf7d5f4fcc06cb2810fee4ddc8024855`
- Darwin CLI SHA-256: `db3bc2e12b6bdcb330ccfa0e088a7c99440e46fea4dd919852681d2a788de988`
- Linux CLI SHA-256: `66d88b03de6e247032d43a97f40219d36fa4b138461655d03b8e01aef17e4f2e`
- Darwin ic SHA-256: `689b838df306a5a82ae2d07f80788c88883f5882eaedd6fd9d4159a67e1162c2`
- Linux ic SHA-256: `143a8f4366664210bb6aa403982fd70dc73c2670ce7c77eab7d3f5c7916151f5`

All three shipped Clavain binaries report the same source revision,
`vcs.modified=false`, `-trimpath=true`, and the expected GOOS/GOARCH. The
tracked release manifest verifies their digests and the Intercore source head.
Both Claude installations record Clavain `0.6.265` at commit `1cdccbc`, and
both Codex installation doctors are green against their canonical source.

## Live Canaries

### Clavain (darwin-arm64)

- The final installed canary exercised Intercore `11f2e57` and exact Clavain
  source head `1cdccbc` through the published `0.6.265` cache.
- Missing proof: advance, verify, and canonical close all blocked; zero
  artifacts registered.
- Shared runtime: collection and advance blocked on nonce mismatch; cleanup
  independently verified; zero artifacts registered.
- Valid runtime: run `wx6m6yy2` completed at `done`; proof
  `sha256:35dd03e7a415917670dc2694e4044add5a06300f4f71c6846a1db5a5ae924ac0`;
  one typed artifact; cleanup verified.

### zklw (linux-amd64)

- The final installed canary exercised Intercore `11f2e57` and exact Clavain
  source head `1cdccbc` through the published `0.6.265` cache under jq 1.7.
- Missing proof: advance, verify, and canonical close all blocked; zero
  artifacts registered.
- Shared runtime: collection and advance blocked on nonce mismatch; cleanup
  independently verified; zero artifacts registered.
- Valid runtime: run `16xaofac` completed at `done`; proof
  `sha256:157c5f954cf5eda291906c14004aa87a49b1db531460846cc11e2afa62efcd45`;
  one typed artifact; cleanup verified.

## Verification

- Intercore: full `go test ./...` and `go vet ./...` passed.
- Clavain Go: all tests except the sandbox-forbidden loopback test passed
  locally; that test passed in the live source canary.
- Clavain structural suite: 738 passed, 1 skipped.
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
`sylveste-npc5` tracks making that repair automatic.

The first managed close also exposed Beads' bounded label storage truncating a
monolithic durable receipt summary. Clavain `0.6.265` now persists six bounded
fields with the schema marker written last. The closed bead was repaired from
its immutable state event, and the shipped audit reconstructs either the split
format or the legacy JSON format without accepting partial state.

The separate A:L3 natural-receipt target remains observational work. This gate
prevents false closure; it does not fabricate the ten no-touch receipts.

## Managed Close Receipt

- Adopted run: `ahpywy66`, rooted at the Clavain repository.
- Receipt proof:
  `sha256:9f001a921988ba14b85a8a6b1da3e218a60244d983d96f23e85fa91eaf00d9fc`.
- Collected source head: `c41e06b36ba1949c44b8ff0223196ad28b99409b`
  (Clavain `0.6.264`); verified at `2026-07-11T16:35:28.808486076Z`.
- Host fingerprint:
  `sha256:a3db95290585356568423c85413c533f20f34c769a5bf2074389831848b67280`.
- Intercore event 2 passed the hard `runtime_evidence` condition and advanced
  `reflect -> done`; the run is `done/completed`.
- `sylveste-6h7x` closed at `2026-07-11T16:35:31Z` through the canonical
  wrapper. Corrective dependents `Sylveste-4b5.2` and `Sylveste-4b5.11` are
  also closed from the observed boot/health/state-delta and shared-runtime
  refusal evidence.
- The final `runtime-evidence-audit.sh --json` result covers one bead with
  zero findings.

The separate policy-audit signer was not provisioned on zklw, so the wrapper's
authorization row remains unsigned even though the runtime proof and close
gate passed. `Sylveste-rkm` tracks defining one multi-host key-ownership
contract and making policy-audit verification green without committing private
key material.
