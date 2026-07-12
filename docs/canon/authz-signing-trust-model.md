---
artifact_type: canon
bead: sylveste-qdqr
supersedes: (none)
superseded_by: (none)
---

# Authz audit signing — trust model (v1.5)

This document pins the exact trust claim of the v1.5 audit-signing system,
and what it does NOT cover. It is the normative answer to "what does a
valid signature on an `authorizations` row actually prove?"

## Claim

**Tamper-evident-post-write.** Any post-cutover row with an invalid or
missing signature is flagged as suspect by `clavain-cli policy audit
--verify`. An attacker who mutates row data (op_type, target, agent_id,
etc.) directly in the SQLite file cannot produce a matching Ed25519
signature without access to the project signing key.

At schema 36, the same command also requires a signed public legacy
manifest. That artifact binds the full project-public-key digest, the fixed
migration-033 marker payload, and the exact sorted set of every retained
`sig_version=0` row as canonical payload hashes. Audit validates that complete
set before applying any display filter, so changing a signed row to version 0
cannot turn it into trusted vintage.

## Non-claims

The v1.5 system does **not** claim:

1. **Tamper-proof-at-write.** An attacker with permission to invoke
   `clavain-cli policy sign` (i.e. read access to
   `.clavain/keys/authz-project.key`) can produce forged rows that
   verify cleanly. The signing key read path is minimized but not
   separated from the gate wrapper in v1.5 — the gate wrapper invokes
   `policy sign` as a sub-process after `policy record`. True
   separation of duties (out-of-band signer daemon) ships in v1.6.

2. **Protection against host compromise.** Root on the host reads the
   key file. If an adversary can read the key, signatures prove
   authenticity of the *signer*, not of the action. Host security is
   out of scope for this system.

3. **Protection against backup-file substitution.** Replacing the DB
   with an older snapshot (lower `PRAGMA user_version`, fewer rows) is
   detectable only if verification walks the migration-cutover marker;
   substituting a v1.5-era snapshot for another v1.5-era snapshot is
   **not** detectable through signatures alone. Snapshot integrity is a
   filesystem/OS concern.

4. **Cross-project chain-of-custody.** Each project holds its own key
   and signs its own records. A token issued in project A and consumed
   in project B writes rows signed by each project's key independently;
   no cross-project Merkle chain exists. v2 cross-project delegation
   may add one.

## What an attacker *can* still do

| Attack | v1.5 detects? | Mitigation lever |
|---|---|---|
| Direct SQL: rewrite `op_type`, `target`, `mode` on a signed row | Yes — `audit --verify` flags row | Run `--verify` periodically; alert on mismatch |
| Direct SQL: insert a new row with `sig_version>=1` and NULL signature | Yes — `audit --verify` rejects it | Require a zero-failure audit before release |
| Direct SQL: downgrade `sig_version` to 0 | Yes — exact legacy membership no longer matches the signed manifest | Require schema 36, a valid manifest, and zero audit failures |
| Direct SQL: mutate, insert, or delete a retained legacy row | Yes — its canonical hash or exact set membership changes | Keep the signed manifest outside the database and committed with the public key |
| Direct SQL: delete signed rows | No (signatures cover rows, not a chain) | Per-row deletion is not detectable via signatures alone; audit log should be append-only at the OS level (backup + WORM-ish policy) |
| Invoke `clavain-cli` to produce legitimate signed rows | No — signatures are valid | Access control on the CLI path and signing key (0400 perms); rotate key on suspected compromise |
| Steal key, sign forged rows offline | No | Key rotation + quarantine (`policy audit quarantine --before-key=<fp>`) flags all pre-breach rows |
| Replace key with attacker-controlled key | Partially — rotation history shows fingerprint change, but rows signed with the new key verify | Commit `authz-project.pub` to the repo so verifiers see the intended fingerprint; rotation is observable via git history of the pubkey |

## Deprecation path to v1.6 (separation of duties)

Future separation-of-duties work moves `policy sign` out of the gate-wrapper process into a
standalone watcher (systemd/launchd/cron job) that owns the signing
key. Gate wrappers write unsigned rows only; the watcher signs on its
own schedule. Post-v1.6 trust claim upgrades to **tamper-proof-at-rest
for rows written outside the watcher's privilege boundary**.

Interim guidance: document the trust claim honestly; do not market v1.5
signatures as "unforgeable." The `audit --verify` command will detect
retroactive tampering; that's real value, even if it does not prevent
write-time forgery by a privileged caller.

## Key distribution

- `authz-project.key` (private, 0400) — **never commit**. Keep one canonical
  signing copy for each audit domain; verifier hosts do not receive it.
- `authz-project.pub` (public, 0444) — **commit** to the repo so
  verifiers agree on the expected fingerprint.
- `authz-legacy-manifest.json` (public, 0444) — **commit** beside the public
  key. It is create-exclusive and has no overwrite or re-anchor command.
- A verifier needs the committed public key, signed legacy manifest, and a
  signed snapshot of the canonical authorization DB. The public artifacts
  establish identity and vintage membership but cannot supply the rows being
  audited.
- `KeyFingerprint(pub)` = first 8 bytes of `sha256(pub)` as hex.
  Shown in audit output + git logs of pub file changes.

`policy doctor --require-signer --project-root=<root>` is the preflight for a
signing host. It requires schema 36, a clean full-ledger audit, the public key,
valid legacy manifest, private mode 0400, and matching fingerprint without
printing private-key paths or material.

**Rotation limitation:** the current verifier loads only the active public key
and authorization rows do not store a signer key ID. `policy rotate-key`
therefore refuses to run when any signed authorization history exists. Rotation
remains available only before the first signature; retained histories require
multi-key verification or an explicit re-sign migration first. `policy
quarantine` records an event; the current verifier does not yet enforce that
event against historical rows.

For the Sylveste operating baseline, zklw is the sole canonical signer and owns
the sole writable authorization ledger. Mac is verifier-only: it uses the
Git-tracked public key and legacy manifest plus a signed snapshot of zklw's
authorization DB, and it does not hold the private key. Any signer-required operation initiated on Mac
must be handed off to zklw and recorded in the canonical ledger there. Do not
copy the private key to Mac unless and until the system has real ledger
replication with a single canonical write path or a remote-signing service.

## Out-of-scope

- Multi-principal identity (who is "the user" vs "the agent") — see v2 token model.
- Multi-host writable ledgers and active-active signing — the current Sylveste
  topology deliberately uses one signer and one canonical ledger.
- Certificate transparency / witness servers — not in scope; single-host trust.
- HSM-backed signing — deferred indefinitely; file-based key is sufficient for the single-user threat model.
