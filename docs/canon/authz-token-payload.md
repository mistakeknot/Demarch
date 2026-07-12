---
artifact_type: canon
bead: sylveste-qdqr.28
supersedes: (none)
superseded_by: (none)
---

# Authz token canonical payload — sig_version=2

This document pins the **exact byte sequence** that Ed25519 signs for each `authz_tokens` row under `sig_version=2`. Signatures depend on byte-for-byte agreement; any deviation in encoding produces non-verifying signatures for correct rows and verifying signatures for tampered rows. This is the spec. Implementations MUST match.

The v1.5 canonical payload (see `docs/canon/authz-signing-payload.md`) governs `sig_version=1` for `authorizations` rows. The two payloads share encoding rules (NFC, LF separators, no embedded or trailing LF, UTF-8, and no control characters) but have **different field lists**. Distinct `sig_version` values prevent cross-payload replay — a signature produced over a sig_version=1 payload cannot verify as a sig_version=2 payload even if the byte sequences happened to coincide, because the verifier dispatches on `sig_version` before computing the expected payload.

## 1. Field order

Signed fields, in strict order:

```
id
op_type
target
agent_id
bead_id
delegate_to
expires_at
issued_by
parent_token
root_token
depth
created_at
```

12 fields. `consumed_at`, `revoked_at`, `sig_version`, and `signature` are **NOT** part of the signed payload. They are metadata about the token's lifecycle and the signing itself. Excluding them:

- Prevents circular dependency (a signature can't sign itself).
- Allows `consumed_at` and `revoked_at` to mutate after sign without invalidating the signature — by design, since lifecycle transitions are the whole point of token state.
- Allows `sig_version` to change across canonical-payload upgrades without invalidating existing signatures under the prior version.

Do not reorder. A new field requires a new `sig_version` (3, 4, ...) and a parallel signer path; the old path continues to sign using the old field set for backward compatibility.

## 2. Encoding rules

Identical to v1.5 (`docs/canon/authz-signing-payload.md §Encoding rules`), restated here for completeness:

1. **Separator:** a single line feed byte (`\n`, 0x0A) between fields.
2. **Trailing newline:** none. The payload ends with the last field's bytes; no terminator.
3. **NULL representation:** the empty string. A SQL NULL and an empty string in the row both encode as zero bytes at that position.
4. **Unicode normalization:** NFC. All text fields must be NFC-normalized before concatenation. Fields that are strictly hex/int (`id`, `parent_token`, `root_token`) are not text but pass through NFC as a no-op.
5. **Integer formatting:** decimal, no leading zeros, no leading `+`, no thousands separators. `depth`, `expires_at`, `created_at` use their unsigned integer representation (Go `strconv.FormatInt(n, 10)`). Negative values are prohibited by the schema and signer rejects them explicitly.
6. **Forbidden characters:** every control character in `[0x00, 0x1F]`, including `\r` and `\n`, is forbidden in field values. LF is reserved exclusively as the separator between fields; permitting it inside a value would make different field assignments share one payload. The signer MUST reject rows containing control characters rather than silently stripping or transliterating them. Reject them at insertion time too.
7. **Output format:** `Sign()` returns the raw 64-byte Ed25519 signature. Callers that need a text form (e.g., for the opaque `<ulid>.<sighex>` string carried via env var) use lowercase hex (no prefix, no separator). The `signature BLOB` column stores raw bytes.

## 3. Worked examples

Three canonical cases cover the common shapes. Implementations MUST verify their `CanonicalTokenPayload()` function reproduces these byte sequences exactly. A golden-fixture test `TestCanonicalTokenPayload_GoldenFixtures` in `pkg/authz/token_test.go` ships alongside the implementation.

Below, `\n` is shown as the literal two-character sequence for reader clarity; real bytes are single LF (0x0A).

### Example 1 — Root issue (no delegation)

Row (column → value):

```
id            = "01J0GZ7W93K5PKQ42V7TCMWC2B"
op_type       = "bead-close"
target        = "sylveste-qdqr.28"
agent_id      = "claude-opus-4-7"
bead_id       = "sylveste-qdqr.28"
delegate_to   = NULL
expires_at    = 1776742800
issued_by     = "user"
parent_token  = NULL
root_token    = NULL
depth         = 0
created_at    = 1776739200
```

Canonical payload (12 lines joined by `\n`, no trailing newline):

```
01J0GZ7W93K5PKQ42V7TCMWC2B\n
bead-close\n
sylveste-qdqr.28\n
claude-opus-4-7\n
sylveste-qdqr.28\n
\n
1776742800\n
user\n
\n
\n
0\n
1776739200
```

Lines 6, 9, 10 are empty strings → zero bytes between their surrounding `\n` delimiters. Line 11 is the literal decimal `0` (not empty; `depth=0` is a real integer value).

### Example 2 — Depth-1 delegation (Claude → codex)

Claude holds the Example 1 token and delegates to codex. The child token is:

```
id            = "01J0GZ8X4M7Q3N8S6XW9Y2Z5CF"
op_type       = "bead-close"                       (same as parent)
target        = "sylveste-qdqr.28"                 (same as parent)
agent_id      = "codex"                             (the delegate recipient)
bead_id       = "sylveste-qdqr.28"                 (copied from parent)
delegate_to   = "codex"                             (explicit delegation marker)
expires_at    = 1776742800                          (clamped to parent's remaining; unchanged here)
issued_by     = "claude-opus-4-7"                   (the delegating agent)
parent_token  = "01J0GZ7W93K5PKQ42V7TCMWC2B"        (Example 1's id)
root_token    = "01J0GZ7W93K5PKQ42V7TCMWC2B"        (denormalized — parent IS the root, so root = parent.id)
depth         = 1
created_at    = 1776739260
```

Canonical payload:

```
01J0GZ8X4M7Q3N8S6XW9Y2Z5CF\n
bead-close\n
sylveste-qdqr.28\n
codex\n
sylveste-qdqr.28\n
codex\n
1776742800\n
claude-opus-4-7\n
01J0GZ7W93K5PKQ42V7TCMWC2B\n
01J0GZ7W93K5PKQ42V7TCMWC2B\n
1\n
1776739260
```

All 12 fields populated. `delegate_to` and `agent_id` are equal (line 4 and line 6) — this is intentional. `agent_id` is "who may present this token" (the authz identity at consume time); `delegate_to` is the delegation marker for audit queries like `SELECT * FROM authz_tokens WHERE delegate_to IS NOT NULL` (returns every delegation event across all chains).

### Example 3 — Publish-scoped root token

Used by `ic publish --patch` after an agent-authored commit passes through a sprint's quality gates. The issuer is the sprint orchestrator; the recipient agent consumes it during publish.

```
id            = "01J0GZ9A7P5R4M2T8YZ6W3X1DH"
op_type       = "ic-publish-patch"
target        = "clavain"                           (plugin slug)
agent_id      = "claude-opus-4-7"                   (the publisher)
bead_id       = "sylveste-qdqr.28"
delegate_to   = NULL
expires_at    = 1776742800
issued_by     = "user"
parent_token  = NULL
root_token    = NULL
depth         = 0
created_at    = 1776739200
```

Canonical payload:

```
01J0GZ9A7P5R4M2T8YZ6W3X1DH\n
ic-publish-patch\n
clavain\n
claude-opus-4-7\n
sylveste-qdqr.28\n
\n
1776742800\n
user\n
\n
\n
0\n
1776739200
```

Same shape as Example 1 (root issue) but with `op_type="ic-publish-patch"` and `target="clavain"` (plugin slug, not a bead id). The `bead_id` scopes the publish approval to the sprint's bead — an attacker who obtained this token cannot use it to publish an unrelated bead's commits because the gate wrapper passes `--expect-op=ic-publish-patch --expect-target=clavain` AND the `ic publish` handler checks `bead_id` matches the publish-target plugin's current sprint bead.

## 4. Why not JSON

Identical rationale to v1.5 (`docs/canon/authz-signing-payload.md §Why not JSON`):

1. **Go map iteration is not stable.** `map[string]any` in Go iterates in pseudo-random order; two `json.Marshal` calls on equivalent maps produce different bytes. Deterministic JSON requires a canonical library (not in stdlib) or manual key sorting.
2. **Number encoding is ambiguous.** `1776739200` vs `1776739200.0` vs `1.7767392e+09` — all valid JSON, different bytes. Signing needs ONE form.
3. **Whitespace is free.** Canonicalizers strip it, but the rule must be spelled out.

A LF-delimited ordered sequence avoids all of this. Spec tight, implementation trivial (`strings.Join(parts, "\n")` after NFC normalization and rejection of control characters in every field value).

## 5. Forbidden deviations

- No trailing newline.
- No BOM.
- No UTF-16 / UTF-32 encodings — UTF-8 only.
- No CRLF and no embedded LF. LF appears only between fields. Inputs with control characters must be rejected, not transliterated.
- No field reordering across signer versions. A new field requires a new `sig_version` and a parallel signer path; the old path continues to sign using the old field set for backward compatibility.
- No re-canonicalization of stored fields at sign time. Stored bytes are authoritative. If a field is not NFC-normalized at insertion time, it is likewise not NFC-normalized at sign time (asymmetry forbidden). The v2 schema does not have any field analogous to v1.5's `vetting` JSON blob that requires this caveat — all v2 fields are plain text or integer — but the discipline is stated for uniformity.

## 6. Implementation-level test

A reference-implementation test must verify that all three worked examples, when serialized by the production `CanonicalTokenPayload()` function, produce the exact byte sequences shown (after expanding `\n` literals into single LF bytes). This test ships as `TestCanonicalTokenPayload_GoldenFixtures` in `core/intercore/pkg/authz/token_test.go`.

Implementations that diverge from the golden fixtures are buggy by definition. Do not adjust the golden fixtures to match an implementation bug; adjust the implementation.

## 7. Relationship to sig_version=1 payload

| Aspect | sig_version=1 (authorizations) | sig_version=2 (authz_tokens) |
|---|---|---|
| Field count | 12 | 12 |
| Field list | id, op_type, target, agent_id, bead_id, mode, policy_match, policy_hash, vetted_sha, vetting, cross_project_id, created_at | id, op_type, target, agent_id, bead_id, delegate_to, expires_at, issued_by, parent_token, root_token, depth, created_at |
| Purpose | Audit row signing (record of what happened) | Token signing (capability to act) |
| Contains vetting JSON? | Yes, verbatim bytes | No |
| Key used | Project-wide `.clavain/keys/authz-project.key` | Same (v2 reuses the v1.5 key) |

The field-count coincidence (both 12) is not load-bearing. Shared field names (`id`, `op_type`, `target`, `agent_id`, `bead_id`, `created_at` — 6 of 12) produce identical canonical-payload segments for those positions, but the surrounding fields differ. Cross-payload replay would require an adversary to produce a sig_version=1 row whose canonical payload bytes exactly match a sig_version=2 payload they want to forge — computationally intractable given Ed25519 + the distinct surrounding fields, and the verifier's `sig_version` dispatch means even a hypothetical collision would not be accepted as the wrong type.

## References

- `docs/canon/authz-token-model.md` — normative semantics (lifecycle, scope, delegation, consume, revoke, threat model).
- `docs/canon/authz-signing-payload.md` — v1.5 canonical payload spec.
- `docs/canon/authz-signing-trust-model.md` — v1.5 trust claim carried forward into v2.
- `core/intercore/pkg/authz/token.go` — reference implementation of `CanonicalTokenPayload()`.
- `core/intercore/pkg/authz/token_test.go` — `TestCanonicalTokenPayload_GoldenFixtures`.
