---
artifact_type: flux-drive-findings
reviewer: fd-correctness (Julik)
plan: docs/plans/2026-04-21-auto-proceed-authz-v2.md
date: 2026-04-21
bead: sylveste-qdqr.28
---

# Correctness Review — authz v2 token protocol

## Invariants Established Before Review

These must hold at all times for the plan's trust claim to be valid:

1. **Single-consume**: Every token row transitions from `consumed_at IS NULL` to `consumed_at IS NOT NULL` exactly once, atomically, with no window where two concurrent callers both observe it as unconsumed.
2. **Revoke-before-consume wins**: If `RevokeToken` commits before a `ConsumeToken` SQL reaches the row, the consume must fail with `ErrRevoked`. A consume that races a revoke must not silently succeed.
3. **Append-only signed fields**: The 12 fields in the signed payload (`id`, `op_type`, `target`, `agent_id`, `bead_id`, `delegate_to`, `expires_at`, `issued_by`, `parent_token`, `root_token`, `depth`, `created_at`) are written once at insert and never mutated. Only `consumed_at`, `revoked_at`, and `signature` may change after insert.
4. **Depth invariant**: `depth` of any row in `authz_tokens` is at most 3 (schema CHECK enforces this). A child's depth equals its parent's depth plus 1 at insert time. No row has `depth > 3`.
5. **Scope non-widening**: A delegated token's `op_type` and `target` are identical to its parent's. The database does not enforce this directly; the application layer in `DelegateToken` is the sole guard.
6. **Proof-of-possession**: Only the agent whose `CLAVAIN_AGENT_ID` matches `parent_token.agent_id` may call `DelegateToken`. The check is purely application-layer; the database has no FK between `agent_id` and any agents table.
7. **Idempotent consume-audit**: A successful `ConsumeToken` writes exactly one `authorizations` row. If the `authorizations` INSERT fails after the `authz_tokens UPDATE` commits, the DB is in a split state — consumed but not audited.
8. **Cascade revoke soundness**: After `RevokeToken(..., cascade=true)` commits, every row with `root_token = target.root_token` has `revoked_at IS NOT NULL`. No concurrent `ConsumeToken` that started before the revoke began may succeed after the revoke commits.
9. **Signature covers immutable fields only**: `CanonicalTokenPayload` must not include `consumed_at`, `revoked_at`, or (for root tokens) `signature`. Covering mutable fields would make every post-consume verify call fail.
10. **Clock-monotone expiry**: `expires_at` is compared against the `now` argument passed by the caller. The caller must use `time.Now().Unix()` (not `unixepoch()`) per intercore convention. Token issuance sets `expires_at = time.Now().Unix() + ttl.Seconds()`.

---

## Findings

### Finding 1 — Error-class discrimination introduces a TOCTOU window after 0-row UPDATE (P1)

**Severity:** P1 — high
**Plan sections:** Task 3 Step 4 (`ConsumeToken`), Must-Haves (atomic consume contract)

**Concern:**
The plan's `ConsumeToken` runs `UPDATE authz_tokens SET consumed_at=? WHERE id=? AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?`, then checks `RowsAffected()`. When `RowsAffected()` returns 0 the plan says "dispatch errors by querying row state after the UPDATE returns 0 rows." This diagnostic SELECT is a separate statement outside the UPDATE's implicit transaction. Under `SetMaxOpenConns(1)` with WAL mode, writes serialize but reads do not hold the write lock. The following interleaving is possible even with a single connection pool:

1. Goroutine A issues UPDATE; gets 0 rows (row is unconsumed but a concurrent revoke from goroutine B just committed `revoked_at=now`).
2. Goroutine A issues diagnostic SELECT; reads `revoked_at IS NOT NULL` and `consumed_at IS NULL`.
3. Goroutine A correctly returns `ErrRevoked`. No data corruption.

So far the result is correct. The problem arises in the mirror case:

1. Goroutine A issues UPDATE (token is valid, `consumed_at IS NULL`, not revoked, not expired). Gets 1 row affected — success.
2. Between the UPDATE commit and the `authz.Record` (audit INSERT): goroutine B runs `RevokeToken` (cascade). It sets `revoked_at` on every row with this `root_token`, including the row A just consumed.
3. Now the `authz_tokens` row has both `consumed_at` and `revoked_at` set. The plan says these are three distinct terminal states, but the schema does not enforce mutual exclusivity (`consumed_at IS NULL` is only in the WHERE of the consume UPDATE, not a CHECK constraint).

The audit row from step A's `authz.Record` call will land, so the consume event is audited. The inconsistency is that `policy audit --tokens` will show a row as both consumed and revoked, making the tree renderer's state ambiguous for every report that joins the two columns.

**Suggested fix:** Add a CHECK constraint: `CHECK (consumed_at IS NULL OR revoked_at IS NULL)` on `authz_tokens`. This prevents the concurrent-revoke-after-consume split. Additionally, `RevokeToken` (cascade path) should use `WHERE root_token=? AND consumed_at IS NULL` to skip already-consumed rows rather than unconditionally overwriting. Document the chosen mutual-exclusion policy (consumed wins, or revoked wins) in `authz-token-model.md`.

---

### Finding 2 — Consume+audit is not a single transaction; partial failure corrupts invariant 7 (P0)

**Severity:** P0 — blocker
**Plan sections:** Task 3 Step 4 (`ConsumeToken`), Notes on discipline ("Always record the consume as an authorizations row")

**Concern:**
The plan directs `ConsumeToken` to (a) UPDATE `authz_tokens` (consumed), then (b) INSERT into `authorizations` (audit row). These are described as sequential statements, not as a single `BEGIN...COMMIT` transaction. Under modernc.org/sqlite with `SetMaxOpenConns(1)`, autocommit is the default for individual `db.Exec` calls that are not wrapped in an explicit `db.Begin`. If the process crashes, the OS kills the process, or the `authz.Record` INSERT returns an error (constraint violation, disk full, etc.) between steps (a) and (b):

- The token is consumed (can never be re-consumed — `consumed_at` is set).
- No audit row exists.
- Invariant 7 is permanently violated: this consume event is invisible to `policy audit`.

This is not recoverable without manual DB surgery. In a security-sensitive audit trail, a permanently un-audited consume is as bad as a forged token.

The concurrency test in Task 3 (`N=8 goroutines racing consume; expect exactly 1 success, 7 ErrAlreadyConsumed`) validates single-consume atomicity but does not exercise the partial-failure window between steps (a) and (b). The test will pass even with the bug present.

**Concrete interleaving that causes corruption:**
1. `ConsumeToken` goroutine issues UPDATE; gets 1 row affected. Token is consumed.
2. `authz.Record` call is attempted; the `authorizations` table has a disk-full error (or the BLOB column has a constraint violation, or the process receives SIGKILL).
3. Transaction is not rolled back because the UPDATE was autocommitted.
4. DB is now in: token consumed, no audit row.

**Suggested fix:** Wrap both the `authz_tokens UPDATE` and the `authorizations INSERT` in a single explicit `db.BeginTx / tx.Commit`. This is the standard intercore transaction pattern (see `db.go`'s `Migrate` method). The entire consume operation is either fully committed or fully rolled back. The test matrix must add a `TestConsumeToken_AuditRowWrittenAtomically` case that injects an error on the `authorizations INSERT` and asserts the token row is also not consumed.

---

### Finding 3 — Cascade revoke does not prevent a concurrent consume from landing between the batch UPDATE and commit (P1)

**Severity:** P1 — high
**Plan sections:** Task 3 Step 4 (`RevokeToken`), Must-Haves ("clavain-cli policy token revoke --cascade sets revoked_at=now on the target row AND every row where root_token = target.root_token (one UPDATE)")

**Concern:**
The plan states cascade revoke is one `UPDATE authz_tokens SET revoked_at=? WHERE root_token=?` (one index scan). With `SetMaxOpenConns(1)`, all SQL is serialized through a single connection, so the revoke UPDATE and a concurrent consume UPDATE cannot literally interleave at the SQL level — one will wait for the other's implicit transaction to complete.

However, the plan is silent about whether the caller wraps either operation in an explicit `BEGIN...COMMIT`. If both operations are issued as autocommit (the default for `db.Exec` in Go's `database/sql`), then:

- Autocommit means each `db.Exec` is its own transaction — immediate acquire + release of the WAL write lock.
- `SetMaxOpenConns(1)` ensures only one goroutine has the connection at a time, so the two SQLite operations do serialize.
- Therefore: under the stated configuration, a `ConsumeToken` that starts after `RevokeToken`'s UPDATE commits will correctly see `revoked_at IS NOT NULL` and fail.

The actual risk is that this serialization guarantee is fragile in two ways:

1. If `SetMaxOpenConns(1)` is ever relaxed (e.g., for read performance) without re-examining consume/revoke, the guarantee breaks silently.
2. If the caller of `RevokeToken` issues the UPDATE inside a larger transaction that has not yet committed (e.g., part of a multi-step revocation workflow), a concurrent `ConsumeToken` may not see the revoke. The plan does not document this dependency.

**Suggested fix:** Document in `authz-token-model.md` §"Concurrency contract" that the `SetMaxOpenConns(1)` constraint is load-bearing for revoke-before-consume ordering, and that relaxing it requires explicit locking or serializable isolation. Add a `TestRevokeConsumeConcurrency` test that races `RevokeToken` and `ConsumeToken` with `N=100` iterations under `-race`, asserting that a revoke started before consume completes always wins or ties (never produces a consumed+unrevoked row when revoke happened first in wall-clock time).

---

### Finding 4 — Depth check race: two concurrent DelegateToken calls on a depth=2 parent can both produce depth=3 children without violating the DB CHECK constraint, but together they produce two children at depth=3 when the parent intended only one (P2)

**Severity:** P2 — medium
**Plan sections:** Task 3 Step 4 (`DelegateToken`), Must-Haves ("depth > 3 is refused at CLI layer and database layer (CHECK constraint)")

**Concern:**
The depth cap (max depth=3) is enforced by reading `parent.depth` and inserting `depth = parent.depth + 1`. The schema CHECK is `depth <= 3`, which catches the insertion of `depth=4`. But the "fan-out" problem is not caught: if two goroutines both call `DelegateToken` on the same `depth=2` parent:

1. Both read `parent.depth = 2`.
2. Both compute `child.depth = 3`.
3. Both INSERT with `depth=3` — both succeed (the CHECK allows depth=3).
4. The parent now has two children at depth=3.

This is not a schema violation. The cap prevents depth=4; it does not prevent multiple siblings at depth=3. This is fine for the purpose of depth-capping (no fourth level is ever reached). However, the plan states the delegation chain is "linear chain, max depth 3" — the word "linear" implies at most one active child per token. The schema does not enforce linearity (one parent can have arbitrarily many children).

The impact is low for the stated use case (Claude delegating to one Codex child) but becomes meaningful if the token is passed to multiple agents simultaneously — each can independently delegate, creating a fan-out that the model calls "chain" but the schema permits as a DAG. The tree renderer in `policy audit --tokens` uses `WHERE parent_token=?` recursively, which will display all siblings correctly, but the model doc says "DAG deferred." This is a semantic inconsistency in the model.

**Suggested fix:** Either (a) enforce linearity at the application layer in `DelegateToken` by checking `SELECT COUNT(*) FROM authz_tokens WHERE parent_token=? AND revoked_at IS NULL` and returning `ErrDepthExceeded` or a new `ErrAlreadyDelegated` if >0 exists, or (b) update `authz-token-model.md` to acknowledge that "chain" means a depth cap, not a fan-out prohibition, and that multiple siblings at any depth are permitted. Option (b) is lower risk and accurately describes the schema.

---

### Finding 5 — Signature verification is TOCTOU-free due to append-only signed fields, but the signed payload includes `delegate_to` which is set at issue time and cannot be updated (P1 design gap)

**Severity:** P1 — design gap, not a runtime race, but a forward-compatibility blocker
**Plan sections:** Task 1 Step 2 (token payload spec), Task 3 Step 1 (`CanonicalTokenPayload`), Must-Haves (sig verification order)

**Concern:**
The plan's signed payload includes `delegate_to` — "NULL (root) or child agent id." For a root token issued via `IssueToken`, `delegate_to` is empty (NULL → empty string). For a delegated token issued via `DelegateToken`, `delegate_to` is set at insert time to the child agent's ID.

This is correct for a linear chain where each token has at most one destination. But consider: when `IssueToken` creates a root token, `delegate_to` is empty, because the issuer does not yet know which child agent will receive a delegation. Then `DelegateToken` creates a *new child row* (correct) — it does not modify the parent row's `delegate_to`. So the parent row's `delegate_to` stays empty even after delegation occurs.

This means `delegate_to` in the signed payload for a root token is always empty — it does not identify the child agent — it is only meaningful for the child token's own signed payload. This is probably the intended semantics, but `authz-token-model.md` must make this explicit: the `delegate_to` field in a token row refers to "the agent this token was issued to delegate to," not "the agent who was actually given a child delegation after the fact."

The risk: if a future reader misinterprets `root.delegate_to = ""` as "this root token was never delegated," and uses that as an audit signal, they will get wrong answers for any root token that has children (all root tokens that were ever delegated have `delegate_to = ""`). The signal for "was this token delegated" is `SELECT COUNT(*) FROM authz_tokens WHERE parent_token = ?`, not the `delegate_to` column.

**Suggested fix:** Add a NOTE box to `authz-token-payload.md` and `authz-token-model.md` clarifying that `delegate_to` in a row is the child-agent designation at that row's issue time, not a post-fact annotation of delegation. Document that querying `parent_token` is the correct way to check whether a token has been delegated. No schema or code change required; this is a spec clarity issue with downstream audit correctness implications.

---

### Finding 6 — `RevokeToken` is not idempotent; second call overwrites `revoked_at` with a different timestamp (P2)

**Severity:** P2 — medium
**Plan sections:** Task 3 Step 4 (`RevokeToken`), question 10 in the review prompt

**Concern:**
The plan describes `RevokeToken` as `UPDATE authz_tokens SET revoked_at=? WHERE id=?`. A second call with a different `now` timestamp will overwrite the original `revoked_at`. This is observable in the audit trail: `policy audit --tokens` will show a different revocation time than the actual first revocation event.

For the cascade path: `UPDATE authz_tokens SET revoked_at=? WHERE root_token=?` has the same property — a second cascade revoke will silently update all `revoked_at` values including already-revoked rows.

If the audit relies on `revoked_at` as the definitive revocation timestamp, overwriting it with a later value is misleading and could cause compliance questions ("did this token expire before or after this audit event?").

**Suggested fix:** Change the revoke UPDATE to `WHERE id=? AND revoked_at IS NULL` (non-cascade) and `WHERE root_token=? AND revoked_at IS NULL` (cascade). This makes `RevokeToken` idempotent — a second call is a no-op and returns `revokedCount=0` without error, which is the correct semantic for "already revoked." Add a `TestRevokeToken_Idempotent` test asserting that calling `RevokeToken` twice on the same token produces the same `revoked_at` timestamp (the first call's value persists).

---

### Finding 7 — TTL clamping "parent remaining" is computed against issuer clock, which may differ from consumer clock (P2)

**Severity:** P2 — medium
**Plan sections:** Task 3 Step 4 (`DelegateToken`), Must-Haves ("child TTL = min(requested, parent remaining)")

**Concern:**
`DelegateToken` computes parent remaining TTL as `parent.expires_at - time.Now().Unix()` on the issuer's machine. The consumer later validates `expires_at > now` where `now` is `time.Now().Unix()` on the consumer's machine. If issuer and consumer clocks differ by more than the minimum TTL floor, the child token may appear expired to the consumer before the parent expires on the issuer.

More acutely: if the delegation happens late in the parent's lifetime (e.g., parent issued with 60-minute TTL and delegate happens at minute 59), the child is issued with ~1 minute TTL. If the consumer's clock is 30 seconds ahead of the issuer, the child has only ~30 seconds effective lifetime. This is not a race — it is a design gap that the plan does not document.

The plan also does not specify a minimum TTL floor for issued tokens (question 8 in the review prompt). A token issued with `--ttl=1s` and delegated at the same instant to a consumer on a different machine with +2s clock drift arrives already expired.

**Suggested fix:** (a) Define a minimum TTL floor (recommend 30 seconds) enforced at issue time by `IssueToken` and `DelegateToken`. Tokens with `requestedTTL < floor` are rejected with a clear error, not silently clamped. (b) Document in `authz-token-model.md` that clocks are assumed to be within ±N seconds of each other (recommend ±10 seconds). Implementations MAY add a grace period on the consumer side: `expires_at > now - 10` instead of `expires_at > now`. This is a trade-off (slightly relaxed expiry vs. clock-skew resilience); either choice should be explicit.

---

### Finding 8 — `gate_token_consume` fall-through on already-consumed or expired tokens silently bypasses the token path and falls to legacy gate_check (P1)

**Severity:** P1 — high
**Plan sections:** Task 5 Step 1 (`gate_token_consume`), Must-Haves ("gate_token_consume at the front of the chain")

**Concern:**
The proposed `gate_token_consume` implementation falls through to the legacy `gate_check` on exit codes 2 (already-consumed), 3 (expired), and 4/5/8 (not-found, bad-sig, cross-project). The intent per the plan is: "On mismatch, log and fall through (legacy gate_check still runs)."

This is the correct design for an incomplete or wrong token, but there is an important correctness gap for already-consumed tokens: if an attacker or a bug causes the same token string to appear in the environment for a second operation, the gate falls through to `gate_check` — which may permit the operation on its own policy grounds. The token's single-use guarantee is per the token itself, not per the gate invocation. A second invocation of the same gate with the same `$CLAVAIN_AUTHZ_TOKEN` will succeed via the legacy path if the policy permits it, with no indication in the gate output that the token was already spent.

This is particularly sharp for `ic-publish-patch.sh`: a publish-scoped token presented for a second publish invocation is rejected at the token level (exit 2) but the publish may still proceed via the v1.5 authz record or marker file. An operator reading the audit will see one token consume event and one v1.5 authz record event and may not realize the second publish was not token-authorized.

**Suggested fix:** On exit code 2 (already-consumed), the gate should write a prominent stderr warning that explicitly states: "Token was already consumed; this invocation is proceeding via legacy policy check, not via token authorization." Add a new env var `CLAVAIN_AUTHZ_TOKEN_STRICT=1` that causes exit code 2, 3, 5 (bad sig) to fail the gate outright instead of falling through. Make `--strict` the behavior for the publish gate specifically, since double-publish is a high-stakes operation.

---

### Finding 9 — Migration 034 cutover marker uses `lower(hex(randomblob(16)))` for ID, making the marker non-idempotent across migration retries (P1)

**Severity:** P1 — high
**Plan sections:** Task 2 Step 1 (migration SQL), Task 2 Step 4 (`TestMigration034_CutoverMarker`)

**Concern:**
The migration 034 cutover marker uses `lower(hex(randomblob(16)))` as its `id`, which generates a new random value on every execution. Compare this to migration 033's cutover marker: it uses the fixed string `'migration-033-cutover-marker'` with `INSERT OR IGNORE` — making it idempotent. The plan's 034 SQL uses a random ID, so if the migration function runs twice (e.g., due to a crash after `PRAGMA user_version = 34` but before `tx.Commit()` — impossible in the current code since both are in the same TX, but the pattern matters for future-proofing and test clarity), two cutover markers would be inserted.

Additionally, `TestMigration034_FreshDBSkipsCutover` is described as "fresh DB at v34 still has the marker (path through migration)" — but a fresh DB that starts at schema version 0 will run through all migration branches, so v34 is only reached after migration runs the INSERT. This test verifies a correct result but tests the path through `Migrate`, not a "skip" — the name is misleading and may hide a test that doesn't actually test what it says.

**Suggested fix:** Use a fixed string ID for the 034 marker: `'migration-034-cutover-marker'` with `INSERT OR IGNORE` — exactly mirroring the 033 pattern. This makes the migration idempotent and the test expectations deterministic. Rename `TestMigration034_FreshDBSkipsCutover` to `TestMigration034_MarkerPresentAfterMigration` to accurately describe what is tested.

---

### Finding 10 — `RequiresApproval` token consume path opens the DB twice in the same process with two separate `*sql.DB` instances (P2)

**Severity:** P2 — medium
**Plan sections:** Task 6 Step 2 (token-path implementation in `RequiresApproval`)

**Concern:**
The existing `checkAuthzApproval` function opens the SQLite DB with `sql.Open("sqlite", dbPath+"?_busy_timeout=5000")`, creates a `*sql.DB`, runs a query, then closes it. The plan's Task 6 adds a token consume path that will also open the DB via `authz.ConsumeToken(db, ...)`. This means `RequiresApproval` will open and close two separate `*sql.DB` handles to the same SQLite file within a single call — one for the v1.5 authz record check and one for the token consume.

Under WAL mode with `SetMaxOpenConns(1)` per connection pool, having two sequential (not concurrent) `*sql.DB` instances pointing at the same file is safe if they don't overlap. However, the plan's pseudocode in Task 6 Step 2 shows:

```go
if tok := os.Getenv("CLAVAIN_AUTHZ_TOKEN"); tok != "" {
    // Open .clavain/intercore.db from pluginRoot upward.
```

This suggests the token path opens its own DB connection. If the token consume returns an error that causes fall-through to `checkAuthzApproval`, which also opens the DB, both handle errors that might be because the DB is locked by the other. The `busy_timeout` should prevent deadlock, but the two opens make the error path harder to reason about, and the `*sql.DB` from the token path must be explicitly closed before the v1.5 path opens its own connection (or they must share one).

**Suggested fix:** Refactor `RequiresApproval` to open the DB once at the top, pass the `*sql.DB` to both the token-consume path and the v1.5 authz-record path, and close it once at the end. This also removes the double `db.SetMaxOpenConns(1)` call (which is redundant but harmless). The db.go `Open` function sets `SetMaxOpenConns(1)` on the shared intercore DB; the approval path should use the same handle if possible, or at minimum open once and share.

---

### Finding 11 — Signed payload includes `expires_at` but not `consumed_at` or `revoked_at`; this is correct, but the payload spec must explicitly document why (P3)

**Severity:** P3 — low (documentation gap; not a correctness defect)
**Plan sections:** Task 1 Step 2 (`authz-token-payload.md`), Task 3 Step 1 (`CanonicalTokenPayload`)

**Concern:**
The 12 signed fields include `expires_at` but exclude `consumed_at` and `revoked_at`. This is the correct design: those two columns are mutable post-issue, and signing them would make every post-consume verification fail. However, a reviewer or future implementer reading the payload spec without this explanation might ask: "Why is `expires_at` signed but `consumed_at` is not?" The answer — `expires_at` is set at issue time and never changes; `consumed_at` and `revoked_at` are lifecycle mutations — needs to be explicit.

The plan's `Token` struct includes a comment on `ConsumedAt`: "not part of signed payload" and similarly for `RevokedAt`. This is good in the Go code. The canon spec (`authz-token-payload.md`) must carry the same clarity, because the spec is the ground truth for cross-language re-implementations.

**Suggested fix:** Add a "Non-signed fields" section to `authz-token-payload.md` that lists `consumed_at`, `revoked_at`, and `signature` (the signature itself cannot be part of its own payload) and explains why each is excluded. One sentence each is sufficient.

---

### Finding 12 — `policy token consume` from the shell gate does not pass `--expect-op` / `--expect-target` in the plan's CLI spec for `cmdPolicyTokenConsume`, but `gate_token_consume` assumes these flags exist (P1)

**Severity:** P1 — high (implementation contract gap)
**Plan sections:** Task 4 Step 3 (handler spec for `cmdPolicyTokenConsume`), Task 5 Step 1 (`gate_token_consume` shell implementation)

**Concern:**
The shell function `gate_token_consume` calls `clavain-cli policy token consume --token="$CLAVAIN_AUTHZ_TOKEN" --expect-op="$op" --expect-target="$target"`. But the CLI handler spec in Task 4 Step 3 describes `cmdPolicyTokenConsume` as only taking `--token` (or `$CLAVAIN_AUTHZ_TOKEN`). The `--expect-op` and `--expect-target` flags do not appear in the handler spec.

This means either:
(a) `--expect-op` and `--expect-target` will fail at parse time with "unknown flag" when the gate wrapper calls the CLI — breaking all gate integrations.
(b) The handler spec is incomplete and the flags need to be added to `cmdPolicyTokenConsume` (they perform scope validation: "does this token's `op_type` and `target` match what the gate expects?").

If option (b) is the intent, then `cmdPolicyTokenConsume` needs to: load the row, compare `row.OpType == expectedOp` and `row.Target == expectedTarget`, and return a new error code (suggest exit 9: scope mismatch) if they do not match. This scope validation is security-critical — without it, a token issued for `op=bead-close target=foo` can be presented to any gate and the gate's consume call will succeed (the token is consumed under the wrong scope).

**Suggested fix:** Add `--expect-op` and `--expect-target` flags to `cmdPolicyTokenConsume`. Document a new exit code 9 (scope mismatch) in the Must-Haves exit-code table. The `authz.ConsumeToken` Go function should accept `expectedOp, expectedTarget string` parameters and return `ErrScopeMismatch` (a new error sentinel) if the row's fields do not match, before issuing the UPDATE. Add `TestConsumeToken_ScopeMismatch` to the test matrix.

---

### Finding 13 — `root_token` is NULL for root tokens but the cascade revoke uses `WHERE root_token=?`; this means revoking a root token via the cascade path silently revokes nothing (P0)

**Severity:** P0 — blocker
**Plan sections:** Task 2 Step 1 (DDL: `root_token TEXT` with no NOT NULL), Must-Haves ("clavain-cli policy token revoke --cascade sets revoked_at=now on the target row AND every row where root_token = target.root_token")

**Concern:**
The schema definition has `root_token TEXT` (nullable). For a root token (depth=0), `root_token` is NULL per the plan: "root_token: first ancestor; NULL for roots." For a child token, `root_token` is set to the ID of the depth=0 ancestor.

Now trace what happens when `RevokeToken(db, rootID, cascade=true, now)` is called on a root token:

1. The function looks up the target row: `root_token = NULL` (it's a root).
2. The plan says the cascade UPDATE is `UPDATE authz_tokens SET revoked_at=? WHERE root_token = target.root_token`.
3. `target.root_token` is NULL (the root token's own `root_token` column is NULL).
4. `WHERE root_token = NULL` in SQL is always false — it should be `WHERE root_token IS NULL`, and even then, `IS NULL` would match ALL root tokens in the table, not just this root's subtree.

The result: a cascade revoke on a root token only revokes the root row itself (via the separate `WHERE id=?` path, if the plan has one), and revokes zero of its children. The children all have `root_token = rootID` (not NULL), so `WHERE root_token = NULL` matches none of them.

This is a silent complete failure of the cascade revoke guarantee for the most common case (revoking a root token to invalidate all its delegations).

**Concrete interleaving showing impact:**
1. Root token R is issued. `R.root_token = NULL`.
2. Child token C1 is delegated from R. `C1.root_token = R.id`.
3. Child token C2 is delegated from C1. `C2.root_token = R.id`.
4. `RevokeToken(db, R.id, cascade=true, now)` runs `UPDATE SET revoked_at=? WHERE root_token = NULL`. Matches zero rows (R's root_token is NULL; C1/C2's root_token is R.id, not NULL).
5. R itself is revoked only if there is a separate `WHERE id = R.id` clause.
6. C1 and C2 are NOT revoked. A consume on C1 or C2 succeeds — `revoked_at IS NULL`.

**Suggested fix:** The cascade revoke logic must handle the root case explicitly:

```go
revokeRootID := tokenID  // if target is a root, cascade by its own ID
if target.RootToken != "" {
    revokeRootID = target.RootToken
}
// Now: UPDATE ... SET revoked_at=? WHERE root_token = revokeRootID OR id = revokeRootID
```

Alternatively, change the schema so root tokens store their own ID in `root_token` (i.e., `root_token` is always non-NULL: root tokens have `root_token = id`). This simplifies all cascade queries to `WHERE root_token = ?` uniformly, at the cost of a mild self-referential redundancy. This is the more robust approach. The plan's worked example (ii) in `authz-token-payload.md` says "root_token=\<same ulid as parent\>" for a depth-1 delegation, which means `root_token` for the child equals the parent's ID — but says nothing about the root row itself. Clarify this in the spec and make it consistent.

**Add `TestRevokeToken_CascadeFromRoot` to the test matrix explicitly.** The existing `TestRevokeToken_Cascade` should be tested as "revoke root → all descendants flagged" and must fail currently if the NULL-root-token bug is present.

---

### Finding 14 — The consume concurrency test uses `t.Parallel()` + goroutines but may not exercise the actual DB serialization under test conditions (P2)

**Severity:** P2 — medium
**Plan sections:** Task 3 Step 5 (concurrency test, `TestConsumeToken_Atomic_FirstWins`)

**Concern:**
The plan specifies: "Concurrency test uses `t.Parallel()` + `sync.WaitGroup` + N=8 goroutines racing consume; assert exactly 1 success, 7 `ErrAlreadyConsumed`." `t.Parallel()` makes the test run concurrently with other tests in the same package, not concurrently within itself. The goroutine-based race within `TestConsumeToken_Atomic_FirstWins` is the actual concurrency under test, and that is correct.

However: the test uses a shared `*sql.DB` with `SetMaxOpenConns(1)`. Under this constraint, the 8 goroutines will serialize at the connection pool level — they do not actually race at the SQLite level; they form a queue. The first goroutine to acquire the connection consumes the token; the remaining 7 each acquire the connection in turn and see `consumed_at IS NOT NULL`. The test will always pass because no actual concurrent SQL is ever issued — it is a sequential test dressed as a concurrent one.

This is not a safety problem (the behavior is correct), but the test does not validate the scenario it claims to validate. A genuine race test would require `SetMaxOpenConns(>1)` during the test, which breaks the intercore convention. The alternative is to use `-count=1000 -race` and rely on the Go race detector to catch any unsynchronized reads/writes in the Go layer.

**Suggested fix:** Augment the test comment to acknowledge that `SetMaxOpenConns(1)` serializes the SQL and explain what the test actually validates: "verifies that sequential consume attempts on the same token return exactly 1 success and N-1 ErrAlreadyConsumed, regardless of goroutine scheduling order." This is worth testing. Run the test with `-race` to catch any unsynchronized access in the Go wrapper. If the concern is genuine SQL-level concurrent access, add a separate integration test that opens the same DB file with two `*sql.DB` instances and races them.

---

## Strengths

**Atomic consume WHERE clause is sound.** The single-row `UPDATE ... WHERE id=? AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?` with `RowsAffected()` discrimination is the correct pattern for SQLite-backed single-use tokens. The plan correctly identifies that this is a known-good pattern for the `modernc.org/sqlite` driver and avoids the CTE-RETURNING limitation.

**`SetMaxOpenConns(1)` as a serialization backstop.** The plan explicitly calls out this constraint and leverages it correctly for write serialization. The existing `db.go` implementation confirms this is an established intercore invariant, not a new claim.

**Signed fields are append-only.** The 12 fields in `CanonicalTokenPayload` are all set at insert time and never mutated. This eliminates the TOCTOU class of signature-verify-then-consume races that would otherwise be serious.

**Separate `authz_tokens` table is the right call.** The decision to use a separate table rather than extending `authorizations` cleanly isolates the token lifecycle from the audit trail and avoids the `sig_version` type collision that the handoff doc flags.

**Exit-code discipline.** The plan's mapping of domain errors to distinct process exit codes (0/2/3/4/5/6/7/8) is well-structured and testable. The test matrix covers every error class.

**Proof-of-possession is a named ship-blocker.** Calling out `CLAVAIN_AGENT_ID == parent.AgentID` as a P0 constraint in the brainstorm and reproducing it in the plan's Must-Haves and Notes on discipline gives it appropriate weight.

**Cascade revoke by index scan.** The `tokens_by_root` composite index (`root_token, consumed_at, revoked_at`) is correctly designed for the cascade UPDATE predicate. One index scan for all descendants is efficient and does not require a recursive CTE.

**Migration idempotency via `isDuplicateColumnError`.** The existing migration chain pattern (tolerate duplicate-column errors) is well-established. Migration 034 should follow this pattern for any `ALTER TABLE` operations.

---

## Summary Table

| # | Severity | Short title |
|---|----------|-------------|
| 2 | P0 | Consume+audit not in a single transaction — partial failure leaves token consumed but un-audited |
| 13 | P0 | Cascade revoke WHERE root_token=NULL matches zero children — silent revocation failure |
| 1 | P1 | Post-UPDATE diagnostic SELECT for error classification is a separate statement — consumed+revoked split possible |
| 3 | P1 | Cascade revoke serialization guarantee undocumented — depends on SetMaxOpenConns(1) remaining load-bearing |
| 5 | P1 | `delegate_to` field semantics underspecified — root token always has empty `delegate_to` even after delegation |
| 8 | P1 | gate_token_consume falls through on already-consumed token — second gate invocation bypasses token authorization |
| 9 | P1 | Migration 034 cutover marker uses random ID — not idempotent, breaks INSERT OR IGNORE pattern |
| 12 | P1 | `--expect-op`/`--expect-target` flags assumed by gate wrapper not present in CLI handler spec |
| 4 | P2 | DelegateToken fan-out not prevented — "chain" model allows multiple siblings at max depth |
| 6 | P2 | RevokeToken not idempotent — second call overwrites revoked_at timestamp |
| 7 | P2 | TTL clamping uses issuer clock; no minimum TTL floor; clock skew can pre-expire child tokens |
| 10 | P2 | RequiresApproval opens DB twice — two *sql.DB handles to same file in the same call |
| 14 | P2 | Concurrency test does not actually race at SQL level under SetMaxOpenConns(1) |
| 11 | P3 | Payload spec does not explain why consumed_at/revoked_at are excluded from signed fields |
