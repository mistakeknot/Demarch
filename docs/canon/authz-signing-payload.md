---
artifact_type: canon
bead: sylveste-qdqr
supersedes: (none)
superseded_by: (none)
---

# Authz audit signing — canonical payload (v1.5)

This document pins the **exact byte sequence** that Ed25519 signs for
each `authorizations` row. Signatures depend on byte-for-byte
agreement; any deviation in encoding produces non-verifying signatures
for correct rows and verifying signatures for tampered rows. This is
the spec. Implementations MUST match.

## Field order

Signed fields, in strict order:

```
id
op_type
target
agent_id
bead_id
mode
policy_match
policy_hash
vetted_sha
vetting
cross_project_id
created_at
```

12 fields. `sig_version` and `signature` and `signed_at` are metadata
about the signing itself and are NOT part of the signed payload. This
avoids a circular dependency and lets `sig_version` change without
invalidating old signatures. Because the row signature alone therefore cannot
detect a version downgrade, schema 36 additionally requires the signed legacy
manifest described below.

## Encoding rules

1. **Separator:** a single line feed byte (`\n`, 0x0A) between fields.
2. **Trailing newline:** none. The payload ends with the last field's
   bytes; no terminator.
3. **NULL representation:** the empty string. A SQL NULL and an empty
   string in the row both encode as zero bytes at that position.
4. **Unicode normalization:** NFC. All text fields (anything that isn't
   strictly hex/int) must be NFC-normalized before concatenation.
5. **Integer formatting:** decimal, no leading zeros, no leading `+`,
   no thousands separators. `created_at` uses its unsigned integer
   representation (SQLite INTEGER → Go int64 → `strconv.FormatInt`).
   Negative values are prohibited by the schema and signer rejects them
   explicitly.
6. **Vetting JSON:** the `vetting` column stores a JSON string. For
   signing, include the stored bytes verbatim — do NOT re-canonicalize
   the JSON at signing time. The row's stored value is authoritative.
   If the stored JSON is not NFC-normalized at store time, it is
   likewise not NFC-normalized at sign time (asymmetry forbidden; use
   the stored bytes exactly).
7. **Forbidden characters:** all control characters in [0x00, 0x1F],
   including `\r` and `\n`, are not permitted in field values. LF is reserved
   exclusively as the separator between fields; permitting it inside a value
   would make different field assignments share one payload. The signer
   MUST reject rows containing them rather than silently stripping or
   transliterating them. Reject them at insertion time too.

## Output format

`Sign()` returns the raw 64-byte Ed25519 signature. Callers that need
a text form use lowercase hex (no prefix, no separator). The
`signature BLOB` column stores raw bytes.

## Worked examples

### Example 1 — All fields populated

Row (column → value):

```
id              = "01HQ8YR7JCMV7K8WK5T6V9BGQF"
op_type         = "bead-close"
target          = "sylveste-qdqr"
agent_id        = "claude-opus-4-7"
bead_id         = "sylveste-qdqr"
mode            = "auto"
policy_match    = "bead-close#0"
policy_hash     = "f3f77555ffc398ff8af8e63f8518e3d9d6764fc7e487dfb9b3999755ccf10340"
vetted_sha      = "0a1e85a6f9b7119988109b796dd2ca14f46b28c9"
vetting         = "{\"shas\":{\"intercore\":\"0a1e85a\"}}"
cross_project_id = ""
created_at      = 1776616956
```

Canonical payload (12 lines joined by `\n`, no trailing newline, shown
with literal `\n` for clarity; real bytes are LF):

```
01HQ8YR7JCMV7K8WK5T6V9BGQF\n
bead-close\n
sylveste-qdqr\n
claude-opus-4-7\n
sylveste-qdqr\n
auto\n
bead-close#0\n
f3f77555ffc398ff8af8e63f8518e3d9d6764fc7e487dfb9b3999755ccf10340\n
0a1e85a6f9b7119988109b796dd2ca14f46b28c9\n
{"shas":{"intercore":"0a1e85a"}}\n
\n
1776616956
```

(Note the empty `cross_project_id` shows as a bare `\n` between lines
10 and 11 — this is the empty-string convention. Line 11 is literally
zero bytes followed by `\n`.)

### Example 2 — Optional fields absent (NULL)

Row:

```
id              = "01HQ8YRDABDCEFGHJKMNPQRSTV"
op_type         = "git-push-main"
target          = "origin/main"
agent_id        = "claude-opus-4-7"
bead_id         = NULL
mode            = "confirmed"
policy_match    = "git-push-main#1"
policy_hash     = "9b2a..."
vetted_sha      = NULL
vetting         = NULL
cross_project_id = NULL
created_at      = 1776617000
```

Canonical payload:

```
01HQ8YRDABDCEFGHJKMNPQRSTV\n
git-push-main\n
origin/main\n
claude-opus-4-7\n
\n
confirmed\n
git-push-main#1\n
9b2a...\n
\n
\n
\n
1776617000
```

Four lines (5, 9, 10, 11) are empty strings → zero bytes between their
surrounding `\n` delimiters.

### Example 3 — `migration.signing-enabled` cutover marker row

Row:

```
id              = "migration-033-cutover-marker"
op_type         = "migration.signing-enabled"
target          = "authorizations"
agent_id        = "system:migration-033"
bead_id         = NULL
mode            = "auto"
policy_match    = NULL
policy_hash     = NULL
vetted_sha      = NULL
vetting         = NULL
cross_project_id = NULL
created_at      = 1776618000
```

Canonical payload:

```
migration-033-cutover-marker\n
migration.signing-enabled\n
authorizations\n
system:migration-033\n
\n
auto\n
\n
\n
\n
\n
\n
1776618000
```

The fixed migration row is itself signed. Its canonical payload is bound into
the legacy manifest, but its timestamp is **not** a vintage boundary: retained
legitimate legacy rows are not necessarily a timestamp prefix. Verifiers trust
only the manifest's exact row-ID and canonical-payload-hash membership.

## Legacy manifest v1

The public `.clavain/keys/authz-legacy-manifest.json` artifact contains:

- schema `intercore.authz-legacy-manifest`, version 1;
- SHA-256 of the full decoded project public key;
- the fixed `migration-033-cutover-marker` ID and a domain-separated SHA-256
  of its canonical row payload;
- the exact sorted legacy set as row ID plus domain-separated SHA-256 of each
  canonical row payload;
- the signed legacy count, manifest SHA-256, and Ed25519 signature.

The signature covers a deterministic JSON body prefixed by the domain
`intercore-authz-legacy-manifest-v1` and a NUL byte. Marker and legacy-row
hashes use the corresponding `intercore-authz-cutover-marker-v1` and
`intercore-authz-legacy-row-v1` NUL-prefixed domains. The manifest signature
and digest fields are excluded from the signed body to avoid recursion.

Audit first loads the complete authorization table in one SQLite read snapshot,
validates this artifact and exact legacy membership, and only then applies
`--since`, `--op`, `--agent`, or `--bead` as display filters. Only signature
versions 0 and 1 are accepted for authorization rows; version 0 is valid solely
when authenticated by this manifest.

## Implementation-level test

A reference-implementation test must verify that all three worked
examples, when serialized by the production `CanonicalPayload()`
function, produce the exact byte sequences shown (after expanding the
`\n` literals). This test ships alongside the implementation in
`pkg/authz/sign_test.go` as `TestCanonicalPayload_GoldenFixtures`.

## Why not JSON

Several factors rule out JSON as the canonical form:

1. **Go map iteration is not stable.** `map[string]any` in Go iterates
   in pseudo-random order; two `json.Marshal` calls on equivalent maps
   produce different bytes. Deterministic JSON requires a canonical
   library (not in stdlib) or manual key sorting.
2. **Number encoding is ambiguous.** `1776616956` vs `1776616956.0` vs
   `1.776616956e+09` — all valid JSON, different bytes. Signing needs
   ONE form.
3. **Whitespace is free.** Canonicalizers strip it, but the rule must
   be spelled out.

A pipe-or-LF-delimited ordered sequence avoids all of this. Spec tight,
implementation trivial.

## Forbidden deviations

- No trailing newline.
- No BOM.
- No UTF-16 / UTF-32 encodings — UTF-8 only.
- No CRLF and no embedded LF. LF appears only between fields. Inputs with
  control characters must be rejected, not transliterated.
- No field reordering across signer versions. A new field requires a
  new `sig_version` and a parallel signer path; the old path continues
  to sign using the old field set for backward compatibility.
