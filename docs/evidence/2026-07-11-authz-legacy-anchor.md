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
- Clavain artifact commit: `48398993caaf515bc5396cee7e859b1dbe88fe41`
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

The source releases were pushed before migration. Marketplace commit
`636576b28a6cae8473325ec5384afcce24c23ba4` publishes Clavain `0.6.269`.
Both hosts had their source, installed, and Claude Code cache binaries updated
and fingerprinted before the zklw write freeze. The previous zklw
`factory-stream.service` process was stopped before binary replacement.

Frozen pre-migration checks:

- WAL checkpoint: `(0, 0, 0)` with zero WAL bytes
- SQLite `quick_check`: `ok`
- Schema/counts: schema 35, 218 total, 3 legacy, 215 signed
- Independent SQLite backup:
  `/home/mk/.clavain/repairs/Sylveste-authz-schema36-20260712T181537Z/intercore-schema35.db`
- Backup SHA-256:
  `ba5b7179103f611e71b54ba7bc00a0081d28db032f88d104b2cb47f11b78dddf`
- Backup verification: `quick_check=ok`, schema 35, and identical counts

The final released-binary inspection reproduced the reviewed count and digest.
`ic init` then advanced the canonical DB to schema 36, and
`policy anchor-legacy` created the manifest with the exact reviewed inputs.

Post-migration checks:

- Signer doctor: `status=ok`, `role=signer`, schema 36
- Audit: 218 passed, 0 failed
- Vintage counts: 3 pre-signing, 1 marker, 214 post-signing
- Manifest SHA-256:
  `4020f06edf093731da41b752db2bc6fd7789e0d545a4318365d31abe9d3f1cd3`
- Manifest file SHA-256:
  `cf685a2073ebca792819e6af07277d7eed6da72b76ac9abaa6acdec56ebe4a14`
- Manifest mode and size: `0444`, 1117 bytes
- Manifest signature:
  `ea22071b8567a3ca707cabb8d8e188a23c34598bd7f6ba35add8ecd9cf09af441c2d3bb9d1d4bf621c733c2814b5ad753b083ce075996e8f21c2acdde285de09`

The disposable live-copy attack downgraded signed row
`7bf41f5cab723bb78ee456c58942bdc4` to `sig_version=0`, removed its
signature and signing timestamp, and applied a nonmatching audit display
filter. Verification still exited 1 because the exact legacy set no longer
matched the signed manifest.

The final snapshot is taken only after this manifest/evidence publication,
bead closure, and Dolt/Git pushes, so no managed authorization write is
omitted. Its hash is written beside the rollback material on zklw after that
finalization fence, avoiding another Git operation that would mutate the
ledger being attested.
