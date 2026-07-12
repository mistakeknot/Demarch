# Schema 36 Authorization Legacy Anchor Evidence

Date: 2026-07-11
Bead: `sylveste-mn13`

## Objective

Make `sig_version` part of the trusted authorization-history boundary so a
signed row cannot be downgraded to legacy vintage and escape verification.
Retain the three legitimate unsigned rows through one signed, immutable
manifest created by the canonical zklw signer.

## Released Source

- Intercore: `b109d13d851a973e1b6837aaa28dbde9dbf5542f`
  (`ic 0.3.5`, schema 36)
- Clavain release source: `8dc0741ba4d8d20ec66f5321a2655fe36470f30e`
- Clavain artifact commit: `4839899`
- Clavain version: `0.6.269`
- Release manifest Intercore revision:
  `b109d13d851a973e1b6837aaa28dbde9dbf5542f`
- Darwin arm64 SHA-256:
  `2fdee15306e69ce12de46fcaf30c9e98086ff05bf67e8b191cc691bf6553687b`
- Linux amd64 SHA-256:
  `d0fa053dfc94e3718d078c917c8066d18dc9169e3a1dc516bf96a924fc219a1b`

## Pre-Migration Baseline

- Schema: 35
- Authorization rows: 218
- Legacy rows: 3
- Signed rows including the fixed cutover marker: 215
- Public-key SHA-256:
  `3d1c3001d533c5a9337ee1524646689711df91fe38a5727c73d4202e7254757c`
- Reviewed legacy count: 3
- Reviewed manifest SHA-256:
  `4020f06edf093731da41b752db2bc6fd7789e0d545a4318365d31abe9d3f1cd3`
- Fixed cutover-marker SHA-256:
  `6fdd1d2067880663d04cb0abdc89197e26889f7268acf31b7062c77d5ea8a840`
- Legacy IDs:
  - `06368bcfc6a5f1f7de625a46cdf90013`
  - `8ca52f7a0720eb184efcc355f166aaf0`
  - `d44721d3a358fd6ce7cb100b895c03e9`

## Verification Before Rollout

- Intercore `go test ./...`: pass
- Intercore `go test -race ./...`: pass
- Intercore GitHub CI and secret scan at `b109d13`: pass
- Clavain `go test ./...`: pass
- Clavain `go test -race ./...`: pass
- Clavain structural tests: 738 passed, 1 skipped
- Authz v1, v1.5, v2, and gate smoke suites: pass
- Release-provenance Bats suite: 16/16 pass
- Independent final code review: no release-blocking findings

## Live Rollout

To be completed from the frozen zklw signer during deployment:

- SQLite backup path and SHA-256
- Final inspected proposal from the released binaries
- Created manifest SHA-256 and signature verification
- Post-migration schema, row counts, and audit summary
- Deliberate downgrade-copy rejection
- Final SQLite snapshot SHA-256
- Mac verifier snapshot match and verifier-only doctor result

The final snapshot is taken only after source/manifest/evidence publication,
bead closure, and Dolt/Git pushes, so no managed authorization write is omitted.
