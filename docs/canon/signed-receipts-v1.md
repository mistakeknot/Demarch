---
artifact_type: canon
bead: sylveste-ewy3.5
supersedes: (none)
superseded_by: (none)
---

# Signed Action Receipts — v1: HMAC-SHA256 over canonicalized receipt payload

Sylveste's foundational claim is "every action produces evidence." A receipt without a signature is a *log entry* — useful, but anyone with write access to the store can forge it post-hoc. A **signed receipt** is a portable, verifiable artifact: any party with the verification key can confirm the receipt was emitted by the Sylveste instance that holds the signing key, and that its fields have not been altered.

Industry observability platforms (Langfuse, Braintrust, Datadog Bits AI) assume trust in the platform. Cryptographic-attestation efforts (blockchain anchoring) are rare and slow. **Sylveste's edge: simple HMAC-SHA256 over a content-addressed receipt schema in a Dolt-backed store, verifiable by any holder of the master key.** No widely-adopted equivalent exists in the agent-tooling ecosystem as of 2026-Q2.

This document is the normative spec for v1 receipt schema, signing canonicalization, key handling, and verification semantics. It anchors `sylveste-ewy3.5` and is referenced from `docs/canon/intercom-transport-target.md` (Sprint↔Task evidence pipeline) and `docs/canon/gridfire-v1.md` (capability tokens whose use produces receipts).

## What this doc covers and does not cover

**v1 covers** — per-agent-action receipts:

- Receipts emitted when a Sylveste agent (Hermes, Hassease, Skaffen, Auraken, Codex-bridge, Clavain workflow agents) completes an action.
- Receipts are content-addressed, immutable, and HMAC-signed.
- Verification: any holder of the receipt + the agent's verification key can confirm the receipt was emitted by Sylveste and has not been altered.

**v1 does NOT cover** — these are distinct systems:

- **Authorization audit signing** — Ed25519 signatures over `authorizations` table rows. See `docs/canon/authz-signing-payload.md` + `authz-signing-trust-model.md`. Different table, different threat model, different crypto.
- **Capability tokens** — Gridfire-v1 (MCP OAuth Resource Indicators). See `docs/canon/gridfire-v1.md`. Tokens grant authority to *take* actions; receipts record actions that *were taken*.
- **A2A Task artifacts** — receipts surface as `Task.artifacts` per `docs/canon/intercom-transport-target.md`, but A2A defines the wire format; this doc defines the receipt body.
- **Public-key signing per-agent identity, delegation chains, threshold signatures, content-addressed merkle trees** — all v2 work, out of scope here.

## Receipt schema

A v1 receipt is a JSON object with these **signed fields**, in strict order:

```
receipt_id
timestamp
agent_id
model
tool_calls
parent_run_id
content_hash
schema_version
```

8 fields. Each field's semantics:

| Field | Type | Definition |
|---|---|---|
| `receipt_id` | string | ULID-style, monotonically sortable. Format: `rcpt_<26 char crockford-base32>`. Generated at receipt emission, never re-used. |
| `timestamp` | string | RFC 3339 UTC, microsecond precision. Example: `2026-05-23T19:42:01.234567Z`. |
| `agent_id` | string | Stable agent identity URI per intercom-transport-target.md. Example: `sylveste://agent/hassease`. |
| `model` | string | Model identifier including tier. Example: `claude-opus-4-7-mythos`. |
| `tool_calls` | array of objects | Each entry: `{"name": "<tool>", "args_hash": "<sha256 hex>", "result_hash": "<sha256 hex>", "duration_ms": <int>}`. Empty array = no tool calls. |
| `parent_run_id` | string \| null | A2A `Task.id` of the spawning run, if any. `null` if the action is sprint-root. |
| `content_hash` | string | SHA-256 hex of the action's primary output (e.g., the message body sent to the user, or the artifact written to disk). Stable across replays of identical content. |
| `schema_version` | int | Currently `1`. Increments on backward-incompatible schema changes. |

**Unsigned fields** (carried in the same JSON object, ignored by the canonicalizer):

- `signature` — the HMAC-SHA256 output (64 hex chars).
- `signature_alg` — `"hmac-sha256-v1"`.
- `key_id` — identifier of the signing key. Format: `<agent_id>#<rotation_epoch>`. Example: `sylveste://agent/hassease#2026-q2`.
- `signed_at` — RFC 3339 UTC timestamp of signing. Distinct from `timestamp` (which is the action's logical time).

## Canonicalization

Signatures depend on byte-for-byte agreement. To sign:

1. Serialize the 8 signed fields as a JSON object in **strict declared order** (not alphabetical, not insertion-order — the order listed above).
2. Encoding:
   - UTF-8, no BOM.
   - Keys are unquoted-by-position — actually, keys ARE quoted as standard JSON strings; the rule is the *array order* of keys in the serialized object matches the declared order above.
   - String values: standard JSON string with `\"`, `\\`, `\n`, `\r`, `\t`, `\b`, `\f`, `\uXXXX` for control chars. No optional whitespace.
   - Number values: integers as decimal, no leading zeros, no exponent. Floats are not used in the v1 schema; if a future field requires fractional values, the spec must be updated.
   - Object/array values: recursively canonicalized by these rules. Inside `tool_calls[]`, each object's keys appear in this order: `name`, `args_hash`, `result_hash`, `duration_ms`.
   - No trailing newline.
3. Compute HMAC-SHA256 over the canonical UTF-8 bytes using the active per-agent key (see Key handling).
4. Encode the HMAC output as 64 lowercase hex characters.
5. Attach as the `signature` field. Set `signature_alg`, `key_id`, `signed_at`.

Implementations MUST NOT pretty-print, sort keys differently, omit fields, or include the unsigned fields in the canonical bytes. A verifier MUST recompute the canonical bytes from the signed fields and compare HMAC outputs in constant time.

## Key handling

- **One signing key per agent identity per rotation epoch.** Example: Hassease has signing key `sylveste://agent/hassease#2026-q2`. The same agent identity may have past keys (`#2026-q1`) usable for verification of older receipts but not for new signing.
- **Key storage:** plugin-local secret store at `.clavain/keys/receipts/<agent>/<epoch>.key`. Permissions 0600. Owner: the Sylveste instance process user.
- **Public verification keys:** the verification side of HMAC is symmetric (anyone with the key can sign), so v1 verification keys are NOT published. v1 verification is in-instance only. Third-party verification ships in v2 with public-key crypto.
- **Rotation policy:** new key per calendar quarter, OR after suspected compromise, OR after any audit-failure event. Old keys retained for verification until the receipts they signed have aged out of the trust window (default: 24 months).
- **Key derivation:** v1 generates keys with `crypto/rand` (256 bits). Keys are not derived from a master secret in v1; v2 may move to HKDF-derived per-agent keys from a project-level secret.

## Verification semantics

CLI contract: `ic receipt verify <receipt_id>` (Intercore command; rationale: receipts are kernel evidence, intercore owns the kernel surface).

Exit codes:
- `0` — receipt found, signature valid, schema_version supported.
- `1` — receipt not found.
- `2` — receipt found, signature invalid (canonical bytes do not match HMAC).
- `3` — receipt found, signature valid, but `schema_version` unsupported by this `ic` binary.
- `4` — receipt found, signature uses a `key_id` not present in the local keystore (verification not possible; not the same as invalid).

**Critical rule:** exit codes 2, 3, and 4 all surface to the operator with explicit messages. Never silently accept an unverifiable receipt as valid. The "default-deny" stance from Gridfire-v1 applies symmetrically here.

Bulk verification: `ic receipt verify --since <duration>` walks the receipts in chronological order and emits a JSONL summary. Used by CI gates and by the routing-calibration loop to detect store tampering.

## Trust claim

A v1 signature proves: **the Sylveste instance holding key `key_id` at signing time emitted this receipt with these field values.**

A v1 signature does NOT prove:

1. **The agent was honest about its action.** An agent could fabricate `content_hash` to point at content it didn't produce. Detecting agent dishonesty is a separate problem (the L0–L5 trust ladder and the closed-loop calibration system).
2. **The action actually happened in the external world.** A signed receipt for "sent a message to user X" proves the receipt was issued; it does not prove the message arrived. End-to-end delivery proofs are out of scope.
3. **Cross-instance authority.** A receipt signed by `sylveste://agent/hassease#2026-q2` proves nothing about a different agent identity, even if that other agent runs in the same project. Each agent's authority is keyed to its own signing key.
4. **Tamper-proof-at-write.** The signing key is held by the same process that emits the receipt. An adversary with code execution in the Sylveste process can sign arbitrary receipts. v2 moves signing to an out-of-band signer daemon to add separation of duties.
5. **Replay protection.** Two receipts with identical content fields will sign identically (they MAY share `receipt_id` only if the IDs were re-used erroneously; normally `receipt_id` differs). v1 does not bind receipts to a sequence number. v2 adds a per-agent monotonic counter to detect replay.

This trust shape mirrors `docs/canon/authz-signing-trust-model.md` for the authz system: **tamper-evident-post-write, not tamper-proof-at-write.**

## Storage

Receipts live in the Sylveste Dolt store under table `action_receipts` with primary key `receipt_id`. Each row carries:

- All 8 signed fields as typed columns.
- The unsigned fields (`signature`, `signature_alg`, `key_id`, `signed_at`).
- A `payload_canonical` BLOB containing the exact bytes the HMAC was computed over (avoids re-canonicalization at verify time and lets verifiers detect canonicalization-rule drift).
- A `dolt_sha` column populated by the Dolt commit hash that introduced the row (content-addressing).

Receipt writes are part of the normal Dolt commit flow; receipts emitted within a single agent action share a Dolt commit. Receipt-row deletion is forbidden by schema (no DELETE permission); decay is by archival, not removal.

## v1 → v2 migration path

v2 strengthens v1's "instance-scoped HMAC" model into "agent-identity-scoped public-key signatures." The migration is **additive**:

1. **v1 receipts remain verifiable** during v2 transition. v2-aware tooling accepts both `hmac-sha256-v1` and `ed25519-v2` signatures based on the `signature_alg` field.
2. **v2 adds Ed25519 per-agent keys.** Public verification keys published at `https://<deployment>/.well-known/receipt-keys/<agent>.pem` (or local file URI for offline deployments). Third-party verification becomes possible.
3. **v2 adds replay protection.** New signed field: `agent_sequence` (monotonic int per agent identity). Receipts with non-monotonic sequence numbers are rejected.
4. **v2 adds delegation chains.** A receipt may carry a `delegation_chain` field listing the parent capability tokens (Gridfire-v1 Resource Indicators) under which authority was claimed. Verification walks the chain.
5. **v2 adds out-of-band signer.** Signing moves to a separate process with read-only access to the receipts table and exclusive access to the keys. Separation of duties.

v2 is **post-Mythos** work. v1 is the Mythos launch surface.

## Acceptance criteria

This canon doc satisfies acceptance criterion #1 of `sylveste-ewy3.5`. Implementation gates are separate follow-up beads (filed alongside this doc):

1. Implement the canonicalizer + HMAC signer as a Go package under `core/intercore/internal/receipt/`. Includes round-trip tests with golden vectors.
2. Add `action_receipts` table to the Dolt schema with INSERT-only permissions.
3. Wire one closed-loop flow (recommendation: routing calibration in `interverse/interspect/`) to emit signed receipts. Calibration receipts are a natural first surface — they already produce structured artifacts.
4. Implement `ic receipt verify <id>` and `ic receipt verify --since <duration>` per the contract above.
5. Performance budget: signing adds <5ms per receipt, verification <10ms. Measured under load with `ic receipt benchmark`.
6. Failure-mode documentation: key rotation mid-run, signing-key unavailable, schema-version mismatch. All deny-by-default with explicit operator-visible errors.

## References

- HMAC spec: RFC 2104 — Keyed-Hashing for Message Authentication: https://datatracker.ietf.org/doc/html/rfc2104
- ULID spec: https://github.com/ulid/spec
- Authorization audit signing (distinct system): `docs/canon/authz-signing-payload.md` + `authz-signing-trust-model.md`
- Capability tokens (action-grant side): `docs/canon/gridfire-v1.md`
- A2A artifact carrier: `docs/canon/intercom-transport-target.md` (§Sylveste-sprint↔A2A-Task adapter)
- PHILOSOPHY: `PHILOSOPHY.md` § "Receipts Close Loops" + § "Evidence Earns Authority"
- Synthesis source: `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Moat opportunity #6, best-practices-researcher Finding "What's NOT Happening")
- Beads: `sylveste-ewy3.5` (this doc), `sylveste-ewy3` (parent epic). Implementation follow-ups filed alongside.
