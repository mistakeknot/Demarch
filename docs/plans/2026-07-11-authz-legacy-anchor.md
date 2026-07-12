---
artifact_type: plan
bead: sylveste-mn13
stage: implementation
---

# Authz Legacy Anchor Implementation Plan

> **For Codex:** Execute this plan test-first and commit each repository after its logical unit is green.

**Bead:** `sylveste-mn13`

**Goal:** Make the three retained unsigned authorization rows cryptographically classifiable so changing any signed row to `sig_version=0` makes `policy audit --verify` fail on both zklw and Mac.

**Architecture:** Intercore schema 36 makes a signed legacy manifest mandatory for authorization verification. The manifest is a public, Git-tracked artifact beside `authz-project.pub`; it binds the full public-key digest, the fixed migration-033 marker payload, and the exact sorted legacy membership as canonical row hashes. Clavain creates it only through an explicit expected-count/digest ceremony on the zklw signer and validates the complete unfiltered ledger snapshot before applying display filters.

**Tech Stack:** Go 1.25, Ed25519, SHA-256, SQLite, Bash integration tests.

**Prior Learnings:** The v1.5 signing review already identified the unsigned-vintage ambiguity. Live inspection showed timestamps cannot recover membership because two of the three retained rows postdate the migration-033 marker. zklw remains the only signer; Mac remains verifier-only.

---

## Must-Haves

**Truths**
- Every schema-36 authorization ledger has a valid signed legacy manifest, including an explicit empty manifest for fresh ledgers.
- A signed row changed to `sig_version=0` fails verification even when audit output filters exclude that row.
- Mutation, insertion, or deletion of an anchored legacy row fails verification.
- Missing, altered, symlinked, wrong-key, or noncanonical manifests fail closed.
- Unknown signature versions fail closed; version 1 is the only signable post-cutover version.
- Nonempty legacy history is never accepted or anchored without an exact operator-reviewed count and digest.
- zklw alone creates the manifest; Mac verifies the same manifest and signed database snapshot without a private key.

**Artifacts**
- `core/intercore/pkg/authz/legacy_manifest.go` defines the canonical manifest, digest, signing, verification, and safe file-loading contract.
- `core/intercore/internal/db/db.go` and `internal/db/schema.sql` advance the irreversible ledger state to schema 36.
- `os/Clavain/cmd/clavain-cli/authz_sign.go` implements proposal, one-time creation, and global verification.
- `.clavain/keys/authz-legacy-manifest.json` is the project-specific public anchor created during the zklw ceremony.

**Key Links**
- The manifest signature verifies under the same Git-tracked public key used for authorization rows.
- The manifest hashes use `authz.CanonicalPayload`, so row signing and legacy classification share one byte contract.
- Canonical field values reject every ASCII control character, including LF; LF exists only as the payload field separator.
- `runPolicyVerify` validates schema, manifest, marker, and the full legacy set before applying `--since`, `--op`, `--agent`, or `--bead` filters.
- Deployment installs a schema-36-aware `clavain-cli` before `ic init` migrates the production ledger.

## Task 1: Intercore Manifest Contract

**Files:**
- Create: `core/intercore/pkg/authz/legacy_manifest.go`
- Create: `core/intercore/pkg/authz/legacy_manifest_test.go`

1. Write failing table tests for deterministic sorting, domain-separated canonical bytes, full public-key digest binding, fixed marker binding, exact legacy row hashes, duplicate-ID rejection, and Ed25519 sign/verify.
2. Run `go test ./pkg/authz -run 'LegacyManifest' -count=1` and confirm the new tests fail for missing APIs.
3. Implement the minimal manifest types and helpers. Hash each legacy entry over the bytes `"intercore-authz-legacy-row-v1" + NUL + CanonicalPayload(row)` and sign a deterministic unsigned struct representation.
4. Add failing tamper tests for row mutation, membership insertion/deletion, marker mutation, wrong key, malformed hex, and unsupported versions.
5. Implement strict parsing and bounded regular-file loading with symlink rejection.
6. Run focused tests green and commit Intercore.

<verify>
- run: `go test ./pkg/authz -count=1`
  expect: exit 0
</verify>

## Task 2: Schema-36 Seal

**Files:**
- Modify: `core/intercore/internal/db/db.go`
- Modify: `core/intercore/internal/db/schema.sql`
- Modify: `core/intercore/internal/db/db_test.go`
- Create: `core/intercore/internal/db/migrations/036_authz_legacy_anchor.sql`

1. Write a failing v35-to-v36 migration test proving all authorization rows remain byte-for-byte unchanged and no nonempty baseline is silently created.
2. Write a failing fresh-schema test expecting schema 36.
3. Advance the schema constants and add the no-data seal migration marker documentation.
4. Run migration tests twice to prove idempotence and commit Intercore.

<verify>
- run: `go test ./internal/db -count=1`
  expect: exit 0
- run: `go test ./... -count=1`
  expect: exit 0
</verify>

## Task 3: Reviewed Anchor Ceremony

**Files:**
- Modify: `os/Clavain/cmd/clavain-cli/authz_sign.go`
- Modify: `os/Clavain/cmd/clavain-cli/authz_sign_test.go`
- Modify: `os/Clavain/cmd/clavain-cli/authz.go`
- Modify: `os/Clavain/cmd/clavain-cli/main.go`

1. Write failing tests for `policy anchor-legacy --inspect`, including stable count, IDs, manifest digest, marker digest, and full public-key digest.
2. Write failing creation tests requiring exact `--expect-count` and `--expect-digest`, a schema-36 DB, a signer private key, and a nonexistent regular destination.
3. Implement inspection on schema 35 or 36 and transactional reinspection before create-exclusive manifest write.
4. Write failing refusal tests for changed history, existing output, verifier-only hosts, invalid signed rows, and arbitrary marker identity.
5. Implement the minimal command without `--force`, overwrite, re-anchor, or accept-current paths.
6. Run focused tests green and commit Clavain.

<verify>
- run: `go test ./... -run 'AnchorLegacy' -count=1`
  expect: exit 0
</verify>

## Task 4: Fail-Closed Verification

**Files:**
- Modify: `os/Clavain/cmd/clavain-cli/authz_sign.go`
- Modify: `os/Clavain/cmd/clavain-cli/authz_sign_test.go`
- Modify: `os/Clavain/tests/authz-v15-e2e_test.sh`

1. Write the direct downgrade regression first and observe the current false pass.
2. Add failing cases for clearing/not clearing the old signature, legacy mutation/insertion/deletion, missing or altered manifest, marker deletion/mutation/duplication, unknown signature versions, and filtered-out tampering.
3. Refactor verification to open one read transaction, validate schema 36 and the complete anchor state globally, then filter only report presentation.
4. Restrict `policy sign` to `sig_version = 1`.
5. Run unit and v1.5 E2E tests green and commit Clavain.

<verify>
- run: `go test ./... -count=1`
  expect: exit 0
- run: `bash ../../tests/authz-v15-e2e_test.sh`
  expect: exit 0
</verify>

## Task 5: Bootstrap, Doctor, and Documentation

**Files:**
- Modify: `os/Clavain/scripts/authz-init.sh`
- Modify: `os/Clavain/scripts/gates/_common.sh`
- Modify: `os/Clavain/README.md`
- Modify: `docs/canon/authz-signing-trust-model.md`
- Modify: `docs/canon/authz-signing-payload.md`

1. Add tests proving fresh zero-legacy bootstrap creates an explicit empty anchor and nonempty legacy bootstrap stops for operator review.
2. Update doctor and signer gates to require schema 36 and a valid manifest without exposing private paths or key material.
3. Document the exact threat claim, ceremony, and remaining deletion/rollback/key-holder limits.
4. Run the complete Intercore and Clavain quality gates and commit each repository separately.

<verify>
- run: `go test ./... -race -count=1`
  expect: exit 0
- run: `go vet ./...`
  expect: exit 0
</verify>

## Task 6: Release and Live Migration

**Files:**
- Create: `.clavain/keys/authz-legacy-manifest.json`
- Create: `docs/evidence/2026-07-11-authz-legacy-anchor.md`

1. Push Intercore and publish the next patch release.
2. Update/build Clavain against that exact Intercore checkout, bump its patch version, push, and publish release artifacts.
3. Pause managed authorization writers and drain stale shell and agent sessions on both hosts. Install the released schema-36-aware `clavain-cli` and `ic` on zklw and Mac before migration; record each resolved path, version, and binary SHA-256 so no old verifier remains in service.
4. Keep the canonical ledger quiescent, run `wal_checkpoint(TRUNCATE)`, create a SQLite-safe backup through the SQLite backup API, and verify and hash that backup before migration. Do not treat a raw copy of the main database file as sufficient while WAL mode is enabled.
5. Run `anchor-legacy --inspect` on the canonical ledger and the pre-migration Mac snapshot. Confirm both proposals match the reviewed three IDs, count, digest, marker digest, and public-key digest.
6. Run `ic init` only on zklw, then create the signed manifest with the exact expected values. Never copy the private key.
7. Prove the migrated zklw audit clean, commit and push the public manifest and evidence document, close `sylveste-mn13` through the managed gate, and complete the Dolt and Git pushes. Treat those managed operations as the last allowed ledger writes before cross-host proof.
8. Drain and freeze writers again, checkpoint WAL, run a full zklw audit, and create the final SQLite-safe signed snapshot. Hash the database and a deterministic ordered authorization-row projection, then replicate that final snapshot to Mac.
9. Prove clean audits on both hosts, require identical schema/count/ordered-row hashes, and prove downgrade rejection only on disposable copies. The final Mac comparison must occur after the manifest, evidence, bead, Dolt, and Git operations in step 7, not from an earlier snapshot.
10. Record whether the sprint naturally produced an A:L3 receipt; do not synthesize one for acceptance.

<verify>
- run: `clavain-cli policy doctor --project-root="$PWD"`
  expect: exit 0
- run: `clavain-cli policy audit --verify --json --project-root="$PWD"`
  expect: exit 0
</verify>
