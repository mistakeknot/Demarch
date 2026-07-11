---
artifact_type: reflection
bead: Sylveste-rkm
stage: reflect
date: 2026-07-11
---

# Authorization Trust Baseline

## Result

The Sylveste authorization path now fails closed around one canonical signer.
zklw owns the only private project key and writable authorization ledger. The
Mac has the same tracked public anchor and a read-only SQLite verifier snapshot,
but no private key. A real managed Bead close and a real Dolt push both produced
signed receipts and completed only after their policy predicates passed.

The current canonical ledger contains 218 authorization rows. All 218 pass
verification: three retained pre-signing rows, one signed cutover marker, and
214 post-signing rows. No post-signing row is unsigned.

## Published Identity

- Intercore source: `85ceeac89aad24c07651afae9da71fbc295d8557`
  (`ic 0.3.4`)
- Clavain release: `61cfca6c23b99fd317003917f753508b437e74ea`
  (plugin `0.6.266`)
- Clavain binary source: `3f83d56b48f1ff056ff743c5152bf2b2f4e809cc`
- Clavain test-only CI follow-up: `1616fecf281008c4a9f03399d4d1b8eee9c35c4a`
- Marketplace: `2d82ec65d64e1049abdd74f9cbe3695db7baf054`
- Sylveste trust model and public anchor:
  `9f3014e6ea1730cc9bc25d04e63f199c457c36a8`
- Project signer fingerprint: `3d1c3001d533c5a9`

Installed `ic` SHA-256 values:

- Darwin arm64: `0df94711b4ffc39b64ee5cdfe59650bc5af86bcd5a88810e3a81912fa74079dd`
- Linux amd64: `8f8cafca79833113b224ad395e273af1c38d880651361b9db4ef5da7da6c412d`

Tracked Clavain CLI SHA-256 values:

- Darwin arm64: `8d5c2edda3c9b5b8ccd305913010969fc764c1eaa402571f011fc94eff5094b9`
- Linux amd64: `89093cf770b5648a1536fcc527d653b171aaf82daefc88c31698ea7768fc9102`
- Windows amd64: `e18f4b4a368e8059f2f4de0950f05d54231a6b486a72426a64ccd03dce34e34a`

Both Claude installations record plugin `0.6.266` at release commit `61cfca6`.
zklw initially updated the cache bytes while retaining stale installed commit
metadata; a data-preserving uninstall/reinstall corrected the receipt. The
cached release manifests on both hosts retain the binary source revision,
Intercore revision, and exact platform digests above.

## Ledger Repair

The guarded repair began only after both new binaries were installed and the
live preconditions still matched the read-only audit:

- Canonical zklw ledger: schema 34, 212 rows, 208 signed, four unsigned.
- zklw home fallback: schema 35, six unsigned rows and completed run
  `ahpywy66`.
- Mac project ledger: empty schema 0.
- Mac home ledger: schema 35, four authorization rows and four real runs.

The repair took SQLite backups, migrated the canonical ledger to schema 35,
imported exactly three missing historical close receipts from the fallback,
signed the five eligible unsigned rows, and retained the three explicit
pre-signing rows. The fallback remains unchanged at six authorization rows and
run `ahpywy66`; neither host home ledger was deleted or replaced.

Rollback and audit artifacts are retained under:

- zklw: `/home/mk/.clavain/repairs/Sylveste-authz-20260711T230125Z`
- Mac: `/Users/sma/.clavain/repairs/Sylveste-authz-20260711T230125Z`

The final canonical backup is
`canonical-v35-final.db`, SHA-256
`61ee18994dd2ba6e4c0aec2fd54fd373f085c38716c4e0d5ca2aaa3e6e3e3348`.
The Mac verifier was refreshed from that SQLite backup and independently
reports 218 passed, zero failed. `policy doctor --require-signer` fails on the
Mac as required. The private key remains zklw-only with mode 0400.

## Live Receipts

`Sylveste-rkm` closed at `2026-07-11T23:24:22Z` through the deployed wrapper.
Its authorization row is:

- ID: `3b5c97650919c2e2f3901435c0b0397e`
- Operation: `bead-close`
- Agent: `mk@zklw`
- Mode: `auto`
- Policy match: `bead-close#0`
- Signature: Ed25519, 64 bytes, `sig_version=1`

The subsequent canonical tracker push also ran through the signed wrapper:

- ID: `7bf41f5cab723bb78ee456c58942bdc4`
- Operation: `bd-push-dolt`
- Agent: `mk@zklw`
- Mode: `auto`
- Policy match: `bd-push-dolt#3`
- Signature: Ed25519, 64 bytes, `sig_version=1`

The final zklw audit reports 218 total, 218 passed, zero failed, three
pre-signing, one marker, and 214 post-signing rows.

## Verification

- Intercore passed full `go test ./...`, `go vet ./...`, and
  `go test -race ./...` on both hosts.
- Clavain release-binary verification passed with three artifacts and the
  pinned Intercore revision.
- Clavain Go tests and vet passed. The structural suite passed 738 tests with
  one skip.
- Live authz E2E passed; v1.5 passed all four scenarios; v2 passed all 20
  scenarios; the complete gate smoke suite passed.
- GitHub `Plugin Tests` and `Secret Scan` passed at `1616fec`. The test-only
  follow-up fixed a pre-existing Bash fixture scope collision and GNU/BSD
  `stat` portability without changing the published runtime payload.
- Both Codex installer doctors report `status=ok` on both hosts. zklw uses the
  physical canonical source `/home/mk/projects/Clavain`; the Sylveste path is
  a symlink alias to that same checkout.
- `ic publish status` reports `0.6.266` for plugin, marketplace, and installed
  state on both hosts. `ic publish doctor --json` exits zero on both hosts;
  zklw retains only warnings for unrelated unregistered local plugins and
  cache inventory.
- The established Interverse quality scan exited zero with valid JSON for 61
  plugins. Its average PQS, approximately 0.701, is telemetry rather than a
  deterministic threshold.
- The generated roadmap is identified as `sylveste-monorepo-roadmap`, covers
  99 percent of active IDs, and the roadmap/backlog tests pass 6/6.

## Remaining Work

The single-signer baseline is trustworthy under its documented host model, but
it does not solve every future trust problem:

- `sylveste-mn13` is the next P1: cryptographically anchor legacy vintage so a
  signed row cannot be downgraded to `sig_version=0`.
- `sylveste-5xpi` is the second P1: add key IDs, archived verifier keys, and
  quarantine semantics before rotation is allowed.
- `sylveste-dan6` and `sylveste-otv9` retain remote-signing/replication and
  historical-home-ledger cleanup as P2 work.
- `sylveste-4jmp` tracks making the quality scan frozen and non-mutating; the
  current scanner can update plugin lockfiles while benchmarking.

The A:L3 no-touch proof remains an observational 0/10 gate. This repair
prevents false authorization and produces trustworthy receipts; it does not
fabricate the ten natural evidence-qualified sprints.
