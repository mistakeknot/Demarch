---
artifact_type: flux-drive-findings
reviewer: fd-safety
date: 2026-04-21
plan: docs/plans/2026-04-21-auto-proceed-authz-v2.md
bead: sylveste-qdqr.28
verdict: SHIP-WITH-CHANGES
---

# Safety Review — Auto-proceed authz v2 (token protocol + delegation chain)

## Threat model classification

**Deployment stage:** Pre-user / single-host developer tooling (zklw). Not public-network-facing.
**Untrusted inputs:** `CLAVAIN_AUTHZ_TOKEN` (env var, carrier of opaque string from any child process), `CLAVAIN_AGENT_ID` (env var, agent self-declaration), `--token` flag (CLI input), DB contents from `.clavain/intercore.db`.
**Credentials:** Ed25519 private key at `.clavain/keys/authz-project.key` (mode 0400, confirmed on disk). Used to both sign v1.5 authz rows and v2 tokens.
**Trust boundary:** Agents running on the same host, same user, sharing the same SQLite DB and key file. Out-of-band host attackers are explicitly out of scope per `docs/brainstorms/2026-04-19-auto-proceed-authz-design.md §Threat model recap`.
**Risk classification: High** — changes touch credential handling (key reuse), authorization enforcement (gate short-circuit), irreversible operations (publish, bead-close, git-push-main), and delegation authority chains.

---

## Findings

### 1. [P1] Token transport via env var — child-process inheritance and logging leakage

**Section:** Task 5 (`gate_token_consume`), Task 6 (`RequiresApproval`), Task 7 (README pattern)

`CLAVAIN_AUTHZ_TOKEN` is a single-use credential. As an env var it is inherited by every child process spawned by the gate wrapper, including the op itself (`bd close`, `ic publish --patch`, `git push`). If any child process logs its environment — common in debug modes for `ic`, `go test`, or subprocess scaffolding — the unconsumed opaque string appears in logs before `gate_token_consume` fires. The README pattern `export CLAVAIN_AUTHZ_TOKEN=<string>` also risks shell history capture if typed interactively.

There is a secondary issue: the plan does not specify that `gate_token_consume` **unsets** the env var on successful consume before invoking the op. Without unsetting, the token string remains in the environment for the entire duration of the op and any post-op hooks. A crashed or slow child that dumps its environment would expose an already-consumed string — low exploitability but meaningful for audit fidelity (consumed strings should be ephemeral).

**Concrete mitigation:**
- In `gate_token_consume`, after a successful consume (`GATE_CONSUMED=1`), immediately `unset CLAVAIN_AUTHZ_TOKEN` before calling `exec_op_then_record_and_sign`. This limits the window to the consume call itself.
- In `RequiresApproval` (Go, Task 6), call `os.Unsetenv("CLAVAIN_AUTHZ_TOKEN")` on successful consume before returning `false`. Document this as required behavior in `docs/canon/authz-token-model.md §Consume contract`.
- Add a note to the README against shell-history exposure: prefer `CLAVAIN_AUTHZ_TOKEN=$(clavain-cli policy token issue ...)` inline over explicit `export`.

---

### 2. [P1] `gate_token_consume` falls through on exit 7 (revoked) — security regression against revoke guarantees

**Section:** Task 5, `gate_token_consume` handler in `_common.sh`

The `gate_token_consume` function as specified treats exit codes 4, 5, and 8 in a single `case` arm that falls through to the legacy `gate_check` path. Exit 7 (revoked) is not in any explicit case arm — it falls to the `*` default arm which also falls through to `gate_check`. This means a token that has been explicitly revoked by an operator does **not** block the operation; it silently downgrades to policy check.

The stated semantics of revocation are that a revoke immediately invalidates all descendants before their consume lands. If a compromised or mistaken delegation is revoked and the agent presents that token, the gate should exit with an error, not silently fall through. The fall-through behavior inverts the operator's intent.

Separately, exit code 6 (proof-of-possession failure) also hits the `*` default, meaning a token presented by the wrong agent quietly proceeds to policy check rather than being treated as a suspicious event. This defeats the POP enforcement at the gate layer even though the DB layer correctly rejects the consume.

**Concrete mitigation:**
- Add explicit case arms for exit 7 (revoked) and exit 6 (POP failure) that log a WARNING and **exit the gate with failure** (do not fall through):
  ```bash
  6) echo "authz: token POP failure — wrong agent presenting token; aborting" >&2; exit 6 ;;
  7) echo "authz: token revoked; op blocked" >&2; exit 7 ;;
  ```
- Document in `_common.sh` that only exit codes 2, 3, 4, 5, 8 are soft falls-through (token degradation). Exits 6 and 7 are hard failures.
- Add smoke test assertions for both.

---

### 3. [P1] Revoke cascade misses the token being revoked when it is itself a child (not the root)

**Section:** Task 3 (`RevokeToken`), Task 2 (schema), Must-Haves

The Must-Haves state: "`--cascade` sets `revoked_at=now` on the target row AND every row where `root_token = target.root_token`."

When the target is a child token (depth > 0), `target.root_token` is the root ancestor. The UPDATE `WHERE root_token = target.root_token` covers all tokens sharing that root — but the root token itself is NOT covered by this predicate because root tokens have `root_token = NULL` (per the schema spec: "NULL for roots"). The target row is updated separately by "the target row" clause, but the root token and any siblings of the revoked subtree that share `root_token` are handled. The actual root token row is left with `revoked_at = NULL`.

This means revoking a depth-1 token with `--cascade` does NOT revoke the root. An attacker who obtained the root token string can still consume it after the cascade. The intended use case (operator revokes a delegated codex token to cut off that codex session while preserving Claude's root authority) may be correct, but the implementation must be explicit about this asymmetry and test it.

The broader concern: a revoke from a non-root node says "cascade" but only revokes peers and descendants sharing the root, not the root itself. This is unintuitive and underdocumented. The spec does not distinguish `revoke --cascade <root>` from `revoke --cascade <child>`.

**Concrete mitigation:**
- Define in `docs/canon/authz-token-model.md` whether `--cascade` from a child token revokes the root: either (a) cascade always walks to root first and revokes everything, or (b) cascade only revokes the named token and its descendants, never ancestors.
- If (b), the index `tokens_by_root` does not cover the cascade of a child token's descendant subtree alone — the index is on `root_token` which for a depth-2 token points to the root, not to the depth-1 parent. The cascade would revoke more than intended (all siblings). Add a test `TestRevokeToken_CascadeFromChild_DoesNotRevokeRoot`.
- Add a `TestRevokeToken_Cascade_ChildScope` test that explicitly verifies which rows are revoked when the target is a depth-1 token.

---

### 4. [P1] TOCTOU window between signature verification and atomic consume

**Section:** Task 3 (`ConsumeToken`), Must-Haves

The `ConsumeToken` function as planned loads the row by ID, verifies the signature, then runs the atomic UPDATE. These are two separate DB operations. Between the `SELECT` (to load the row for `VerifyToken`) and the `UPDATE` (atomic consume), another goroutine or process can:

1. Revoke the token — the revoke lands between the SELECT and UPDATE; the UPDATE's `WHERE revoked_at IS NULL` catches this. This case is handled correctly.
2. Modify the `expires_at` directly in the DB (host attacker, out-of-scope but noted per the brainstorm). No additional risk here.
3. Swap the `signature` column between SELECT and UPDATE — the signature was already verified against the loaded row, but the UPDATE does not re-verify. If an attacker can do a DB write between SELECT and UPDATE, they could set `signature = NULL` on the row; the UPDATE still lands (it does not check `signature IS NOT NULL`). This is a host-attacker scenario and is out of scope, but it means consume does not validate the signature at the same moment it claims the row.

The more realistic concern within the threat model is: the row is loaded from DB, verified, then the UPDATE atomically checks `consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?`. The signature check happens before the atomic claim. This means a valid-signature but already-consumed token (e.g., presented by two concurrent callers) will both pass signature verification but only one will succeed at the UPDATE. The loser receives `ErrAlreadyConsumed`. This is correct and the race test covers it.

However, the verified-then-consume separation means that the signature is not part of the WHERE clause. A row inserted by an attacker with a NULL or invalid signature but otherwise valid fields (consumed_at IS NULL, not expired, not revoked) would fail `VerifyToken` and return `ErrSigVerify` — that is correct. The only edge case is if `VerifyToken` is called with the wrong public key (misconfigured after rotation) and returns false — the function returns `ErrSigVerify` before the UPDATE, which means a legitimate token is rejected but not consumed, allowing retry. This is the correct safe-failure mode.

**Concrete mitigation:**
- Wrap the SELECT + VerifyToken + UPDATE in a single serialized transaction (or at minimum document that `SetMaxOpenConns(1)` makes these operations serial). The plan notes `SetMaxOpenConns(1)` but does not require the transaction wrapper for ConsumeToken explicitly.
- Add to `docs/canon/authz-token-model.md §Atomic consume contract` that signature verification and the UPDATE must happen in the same serialized call (no concurrent ConsumeToken calls can interleave, ensured by `SetMaxOpenConns(1)` and single-connection SQLite).

---

### 5. [P2] `sig_version` field discrimination — no enforcement at consume path

**Section:** Task 3 (`CanonicalTokenPayload`, `VerifyToken`), Trust claim

The plan correctly creates a separate `CanonicalTokenPayload` function for v2 tokens (12 token-shaped fields) vs `CanonicalPayload` for v1.5 authorization rows (12 different fields, overlapping names: both have `id`, `op_type`, `target`, `agent_id`, `bead_id`, `created_at`). The `sig_version` column distinguishes which payload function applies.

The risk is: at consume time, the code loads the row and calls `VerifyToken(pub, token, sig)`. `VerifyToken` implicitly uses `CanonicalTokenPayload`. If a bug or future code path calls `Verify` (the v1.5 function) instead of `VerifyToken` on a v2 token, the signature will fail, which is the safe outcome — no false positive. However, in the opposite direction: if someone crafts a v1.5 authz row whose 12-field payload happens to produce the same byte sequence as a v2 token's payload, the signature from the v1.5 row would verify under `VerifyToken`. The two field lists share 6 out of 12 names, and the payload bytes differ because v1.5 has `mode`, `policy_match`, etc. while v2 has `expires_at`, `depth`, etc. — so collision is not practically achievable. But the discrimination relies entirely on calling the right function, not on a domain separator in the signed payload itself.

**Concrete mitigation:**
- Prefix the canonical payload with a domain separation header. Specifically: prepend `"sylveste-authz-v2-token\n"` (13 bytes + LF) to `CanonicalTokenPayload`, and `"sylveste-authz-v1-row\n"` to the existing `CanonicalPayload`. This makes cross-payload replay cryptographically impossible rather than structurally unlikely. A new `sig_version=3` later would use `"sylveste-authz-v3-...\n"`. Costs nothing, eliminates the class of cross-version signature confusion entirely.
- If a domain separator is not added now, document in `docs/canon/authz-token-payload.md` that the implicit separation relies on field-list differences and pin a test asserting that a v1.5 signature on an equivalently-fielded row does NOT verify under `VerifyToken` (and vice versa).

---

### 6. [P2] `ParseTokenString` — missing length cap enables allocation-amplifying inputs

**Section:** Task 3 (`ParseTokenString`), Task 4 (CLI handler)

The opaque token string `<ulid>.<sighex>` has a known fixed length: 26 chars (ULID) + 1 dot + 128 chars (64-byte hex) = 155 chars. `ParseTokenString` as specified validates ULID format and hex decode with wrong-siglen detection. However, the plan does not cap the input length before any of these operations.

A token string of 1 MB (arbitrary `a.` followed by 1M hex chars) would pass the split-on-dot step, attempt `hex.DecodeString` on 1M chars (512 KB allocation), then fail `wrong-siglen`. In a gate wrapper called from a shell script, the string comes from `$CLAVAIN_AUTHZ_TOKEN` which is bounded by the OS environment size limit (~128 KB on Linux). At the CLI, `--token=<str>` comes from argv which has similar limits. The actual risk is low in this deployment, but the function should state its length invariant explicitly.

**Concrete mitigation:**
- Add a length check at the top of `ParseTokenString`: `if len(s) > 256 { return ..., ErrBadTokenString }`. 155 is exact; 256 provides a small margin. Document the expected length in the function comment.
- The `EncodeTokenString` function should similarly assert that the ULID is exactly 26 chars and the signature is exactly 64 bytes (both guaranteed by their respective types, but defensive assertion costs nothing).

---

### 7. [P2] `gate_token_consume` trusts `--expect-op` and `--expect-target` scope matching without verification against the DB row at gate layer

**Section:** Task 5 (`gate_token_consume`), Task 4 (`cmdPolicyTokenConsume`)

The gate wrapper calls `clavain-cli policy token consume --token=... --expect-op=<op> --expect-target=<target>`. The scope matching (verifying that the token's `op_type` == `--expect-op` and `target` == `--expect-target`) happens inside the CLI subprocess. The gate wrapper receives only the exit code. This is correct architecture — the CLI does the authoritative check.

However, the `ConsumeToken` Go function as planned does not list `--expect-op` / `--expect-target` in its function signature (`ConsumeToken(db *sql.DB, pub ed25519.PublicKey, tokenStr string, now int64) (Token, error)`). The scope enforcement is in the CLI handler (`cmdPolicyTokenConsume`), not in the library function. This means:
1. A caller that uses `authz.ConsumeToken` directly (e.g., `RequiresApproval` in Task 6) must re-implement the scope check or it will consume tokens issued for unrelated ops.
2. Task 6's `RequiresApproval` plan shows calling `authz.ConsumeToken` but checking `scope matches op=ic-publish-patch target=<plugin-slug>` only as prose — the verification of op/target match must be explicit code, not just checked by the CLI handler.

**Concrete mitigation:**
- Add `ExpectedOp` and `ExpectedTarget` to `ConsumeToken`'s signature (or pass them as part of a `ConsumeSpec` struct), so that scope verification is atomic with the consume. This prevents any caller from accidentally bypassing scope matching.
- Alternatively: have `ConsumeToken` return the consumed `Token` struct and require callers to check `token.OpType` and `token.Target` themselves, but document this as a required post-consume validation in `docs/canon/authz-token-model.md §Consume contract`. Either way, the plan must call it out explicitly for the `RequiresApproval` implementation.

---

### 8. [P2] `CLAVAIN_AGENT_ID` proof-of-possession is env-var self-declaration — no binding to actual agent identity

**Section:** Trust claim, Task 3 (`DelegateToken`), Task 4 (`cmdPolicyTokenDelegate`)

The proof-of-possession check for delegation is: `os.Getenv("CLAVAIN_AGENT_ID") == parentToken.AgentID`. This check correctly prevents an agent that does not know the expected string from delegating. However, `CLAVAIN_AGENT_ID` is a self-declared env var — any process can set it to any value before calling `clavain-cli policy token delegate`. On a shared shell environment, a malicious or buggy script can inherit and override the env var.

This is explicitly documented as a known limitation ("single-host = single-trust-domain") and is consistent with the overall threat model. However, the trust claim in the plan ("A delegated agent cannot widen scope") is dependent on the parent's `agent_id` matching the environment claim, which is not cryptographically bound to any identity. If Claude's root token has `agent_id = "claude-opus-4-7"` and a subprocess sets `CLAVAIN_AGENT_ID=claude-opus-4-7`, it can delegate Claude's token to itself.

The brainstorm §Q5 disposition defers per-agent keys to a future milestone. That deferral is reasonable. However, the trust claim in the plan should be reworded to make this explicit. Currently "A delegated agent cannot widen scope" implies security enforcement that is actually operational discipline on the same host.

**Concrete mitigation:**
- Reword the v2 trust claim in `docs/canon/authz-token-model.md` to: "Proof-of-possession is enforced via `CLAVAIN_AGENT_ID` string matching against the parent token's `agent_id`. This provides correct chain-of-custody for cooperative agents on the same host; it does not prevent a process on the same host from impersonating an agent identity by setting the env var. Per-agent cryptographic identity is deferred to v2.2."
- This is a documentation gap, not an architectural blocker, given the stated threat model.

---

### 9. [P3] Cascade revoke via `root_token` index misses tokens issued before the `root_token` column existed (schema migration edge case)

**Section:** Task 2 (schema), Task 3 (`RevokeToken`)

The cascade revoke is `UPDATE authz_tokens SET revoked_at=? WHERE root_token = <target.root_token>`. Root tokens have `root_token = NULL`. The cascade for a root token requires a separate clause: `WHERE id = <root.id> OR root_token = <root.id>`. The plan states "sets `revoked_at=now` on the target row AND every row where `root_token = target.root_token`" which for a root token would be `WHERE root_token = NULL` — which matches every root token in the table, not just the one being revoked.

This is a schema-logic error in the Must-Haves: if `root_token = NULL` for root tokens, then `WHERE root_token = target.root_token` when `target` is a root token equals `WHERE root_token = NULL`, which would cascade-revoke all root tokens. The correct predicate for revoking a root token and its children is `WHERE id = <root.id> OR root_token = <root.id>`.

**Concrete mitigation:**
- Fix the Must-Haves and `RevokeToken` spec: when the target is a root token (its `root_token` field is empty/NULL), the cascade predicate must be `WHERE id = ? OR root_token = ?` with the same root token ID in both placeholders.
- When the target is a child token (its `root_token` is non-empty), cascade means "revoke this token and all tokens that share the same root" which requires: `WHERE root_token = <target.root_token> OR id = <target.root_token>` (to include the root itself if operator intends full cascade) or explicitly not the root (partial cascade). Decide and document.
- Add test `TestRevokeToken_Cascade_RootToken_DoesNotRevokeAllRoots`.

---

### 10. [P3] Cutover marker in `authorizations` lacks a signature at migration time — partial audit integrity window

**Section:** Task 2 (migration 034)

The cutover marker is inserted via `INSERT INTO authorizations (...) VALUES (...)` during the migration DDL itself (inside a `tx.ExecContext` call). The `policy sign` command signs unsigned rows after the fact. Between migration and the first `policy sign` run, the cutover marker exists unsigned. The v1.5 `verifyWithPub` logic treats an unsigned post-cutover row as a `Failed` verification.

This is a narrow window (migration runs once, sign runs shortly after via `authz-init.sh`). However, if the `--with-token-demo` flag or `policy sign` is never run, the cutover marker row stays unsigned and `policy audit --verify` will report a verification failure on the first row of the v2 era. This is a confusing operational experience.

**Concrete mitigation:**
- Modify the `authz-init.sh` script to automatically sign the cutover marker row after migration, rather than deferring to `--with-token-demo`. This can be a non-optional step: `clavain-cli policy sign --op=migration.tokens-enabled`.
- Or: generate and insert the cutover marker with a pre-computed signature at migration time (sign the canonical payload in Go within the migration branch, insert the signature directly). This eliminates the window entirely.

---

### 11. [P3] `--issued-since` bulk revoke bypasses TTL — can revoke already-consumed tokens, creating misleading audit state

**Section:** Task 4 (`cmdPolicyTokenRevoke`)

The `--issued-since` flag revokes all not-yet-consumed tokens since a timestamp. The plan says "bulk-revokes all not-yet-consumed tokens since a timestamp." However, revoking a token that has already been consumed adds `revoked_at` to a row that also has `consumed_at` set. The token is already terminal (consumed is final), but the audit row now shows both `consumed_at` and `revoked_at` set — an ambiguous state not covered by the lifecycle model (issued → consumed OR revoked OR expired; not consumed-then-revoked).

**Concrete mitigation:**
- Define in `docs/canon/authz-token-model.md` that revoke is a no-op on already-consumed tokens: the `WHERE` clause for bulk revoke should include `AND consumed_at IS NULL`.
- Similarly, single-token `RevokeToken` should either refuse to revoke an already-consumed token (return an error) or silently succeed (idempotent no-op). Choose and document which.

---

### 12. [P3] `authz-init.sh --with-token-demo` emits the demo token string to stdout

**Section:** Task 7

The demo path prints `echo "Demo token issued: $TOKEN"` to stdout. If `authz-init.sh` is run in a CI context with captured stdout, the token string is in CI logs. Demo tokens should be short-TTL (5m per the plan), limiting the window, but the log capture is indefinite.

**Concrete mitigation:**
- Print the demo token to stderr instead of stdout, or redact it after the TTL: `echo "Demo token issued: [expires in 5m, not shown in logs]" >&2` and separately print to the terminal only if `-t 1` (tty present).
- Document in the script comment that demo tokens must not be used in real workflows.

---

## What the plan does right — Strengths

These elements are well-designed and should be preserved:

1. **Atomic consume with `WHERE consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?`.** The predicate combines all terminal state checks into the UPDATE itself, making double-consume and post-revoke consume impossible without a SELECT-then-UPDATE race. The `RowsAffected()` discrimination is the correct pattern for `modernc.org/sqlite`.

2. **`CanonicalTokenPayload` as a completely separate function from `CanonicalPayload`.** The plan explicitly prohibits using the v1.5 function for v2 tokens. The note "Never reuse the v1.5 canonical payload function for tokens" is prominent and belongs in the implementation discipline.

3. **Key permission enforcement at `LoadPrivKey` (0400 check).** Rejecting keys with too-broad permissions on load, not on a periodic check, is the right place. This is already shipped in v1.5 and v2 inherits it correctly.

4. **`parent_token REFERENCES authz_tokens(id) ON DELETE RESTRICT`.** Prevents cascaded deletes from silently orphaning child tokens. Revoke is the intended mechanism; deletion is not permitted.

5. **Depth cap enforced at both schema (CHECK constraint) and CLI layer.** Belt-and-suspenders for depth-3 is correct. Neither layer alone is sufficient (DB constraint blocks bad inserts; CLI gives a user-friendly error earlier).

6. **Cross-project rejection with a named error (`ErrCrossProject`) and a specific exit code (8).** Surfacing this as a distinct error class rather than a generic "not found" prevents silent security boundary violations.

7. **Golden-fixture canonical payload tests matched against worked examples in `docs/canon/authz-token-payload.md`.** Byte-level fixture tests for the signing payload are the right approach; they catch field-order bugs and encoding deviations that unit tests on individual fields would miss.

8. **Concurrency test (`TestConsumeToken_Atomic_FirstWins`) with N=8 goroutines + `-race` flag.** This is the correct way to exercise the single-connection serialization assumption. Keeping it as a mandatory test (not just in e2e) is good discipline.

---

## Finding summary

| ID | Severity | Title |
|----|----------|-------|
| 1 | P1 | Token env var not unset after consume — child-process leakage window |
| 2 | P1 | Revoked/POP-failure exit codes fall through to legacy gate_check |
| 3 | P1 | Cascade revoke semantics undefined for non-root targets; root_token=NULL collision |
| 4 | P1 | SELECT + VerifyToken + UPDATE not wrapped in transaction — TOCTOU documentation gap |
| 5 | P2 | No domain separator in signed payloads — cross-payload replay not cryptographically prevented |
| 6 | P2 | ParseTokenString has no length cap — unbounded allocation on malformed input |
| 7 | P2 | ConsumeToken library function has no scope enforcement — callers must re-implement check |
| 8 | P2 | CLAVAIN_AGENT_ID POP is env-var self-declaration — trust claim overstated |
| 9 | P3 | Cascade WHERE clause incorrect for root token target (WHERE root_token=NULL matches all roots) |
| 10 | P3 | Migration 034 cutover marker is unsigned at migration time |
| 11 | P3 | --issued-since bulk revoke can set revoked_at on already-consumed tokens |
| 12 | P3 | Demo token emitted to stdout in authz-init.sh |

**Counts:** P0: 0, P1: 4, P2: 4, P3: 4. Total: 12.

**Verdict: SHIP-WITH-CHANGES.** No P0 ship-blockers. The four P1s must be addressed before the gate wrappers carry real authority: items 2 (revoked fall-through) and 3 (cascade semantics) are the highest-blast-radius bugs because they can silently authorize revoked operations or incorrectly revoke unintended tokens at scale.
