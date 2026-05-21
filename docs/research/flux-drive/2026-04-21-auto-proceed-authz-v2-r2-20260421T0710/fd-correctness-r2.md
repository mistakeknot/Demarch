---
artifact_type: flux-drive-findings
reviewer: fd-correctness (Julik)
plan: docs/plans/2026-04-21-auto-proceed-authz-v2.md (r2)
prior_review: docs/research/flux-drive/2026-04-21-auto-proceed-authz-v2-20260421T0350/fd-correctness.md
date: 2026-04-21
bead: sylveste-qdqr.28
---

# Correctness Review r2 — authz v2 token protocol

## Invariants (carried forward from r1; unchanged)

1. Single-consume: every `authz_tokens` row transitions `consumed_at IS NULL → IS NOT NULL` exactly once, atomically.
2. Revoke-before-consume wins: if `RevokeToken` commits first, a subsequent `ConsumeToken` must fail with `ErrRevoked`.
3. Append-only signed fields: the 12 payload fields are written once at insert, never mutated.
4. Depth invariant: `depth <= 3` enforced by CHECK constraint.
5. Scope non-widening: a child token's `op_type` and `target` match the parent's exactly.
6. Proof-of-possession: only the agent whose `callerAgentID` matches `token.AgentID` may delegate or consume.
7. Idempotent consume-audit: a successful `ConsumeToken` writes exactly one `authorizations` row, atomically with the UPDATE.
8. Cascade revoke soundness: after `RevokeToken(..., cascade=true)`, every row in the subtree has `revoked_at IS NOT NULL`.
9. Signature covers immutable fields only.
10. Clock-monotone expiry: `expires_at` is compared against the `now` parameter, set by caller as `time.Now().Unix()`.

---

## Section 1 — P0 Verdict

### Finding 2 (r1): Consume+audit not in a single transaction

**r2 change quoted:**

> Architecture: "Consume wraps two writes in one transaction: (1) atomic UPDATE … (2) INSERT INTO authorizations (…). A partial-failure between (1) and (2) must not leave a consumed token with no audit record — commit-or-rollback is non-negotiable."

> Must-Haves: "Consume wraps the token UPDATE and the authorizations INSERT in one BEGIN...COMMIT. A forced process kill after the UPDATE but before the INSERT rolls back both — the token remains consumable, the audit log has no orphaned record. Test TestConsumeToken_PartialFailure_Atomic forces this via a CONSUME_FAULT_INJECT_AFTER_UPDATE=1 hook gated behind a `// +build testfault` tag."

> ConsumeToken docstring (Task 3 Step 4): "(1) UPDATE authz_tokens SET consumed_at=? … (2) INSERT INTO authorizations … If (1) affects 0 rows, tx.Rollback …"

> Notes on discipline: "Always wrap consume (UPDATE + audit INSERT) in one transaction (r2 new rule)."

**Verdict: RESOLVED**

The r2 plan is unambiguous: both writes must occur inside one `BEGIN...COMMIT`. The partial-failure test (`TestConsumeToken_PartialFailure_Atomic`) is explicitly specified in the test matrix, and the `TestConsumeToken_NoAuditRowOnRollback` test confirms the rollback leaves no orphaned audit row. The Notes on Discipline section makes the rule permanent. Invariant 7 is now correctly guarded. No residual gap.

---

### Finding 13 (r1): Cascade revoke WHERE root_token=NULL matches zero children

**r2 change quoted:**

> Architecture: "root_token is denormalized so cascade revoke is UPDATE authz_tokens SET revoked_at=? WHERE id=? OR root_token=? passing target.id for both bindings (the disjunction covers both root revokes, where root_token IS NULL on descendants would otherwise fail to match via NULL semantics, and non-root revokes — a single index scan against tokens_by_root covers both)."

> Must-Haves: "clavain-cli policy token revoke --token=<id> [--cascade] sets revoked_at=now with the predicate WHERE id=? OR root_token=? (both bound to target.id). For a root token this revokes the root AND every descendant in one scan against tokens_by_root."

> RevokeToken docstring (Task 3 Step 4): "Cascade: UPDATE authz_tokens SET revoked_at=? WHERE (id=? OR root_token=?) AND revoked_at IS NULL — Both bind target.id to both positions in the cascade form — this correctly revokes root + descendants even when target.root_token IS NULL."

> Prior Learnings: "NULL = NULL is never true in SQL. … r2 uses WHERE id=? OR root_token=? with target.id bound to both positions."

> Notes on discipline: "Never compare a nullable column to a possibly-NULL parameter (r2 new rule)."

> Test matrix includes: `TestRevokeToken_CascadeFromRoot_NullRootToken` — "CRITICAL: revoke root (root_token IS NULL) → target + all descendants flagged; catches r1 NULL bug"

> E2E scenario 10: "Revoke-cascade from root (CRITICAL r2 fix): issue root (root_token IS NULL) → delegate depth-1 → delegate depth-2 → revoke --cascade <root.id> → consume each of the three (root, d1, d2) → assert all three exit 2 (class=revoked). If any succeed, the NULL-semantics bug from r1 has regressed."

**Verdict: RESOLVED**

The predicate change is precisely the fix r1 specified. `WHERE id=? OR root_token=?` with `target.id` bound to both positions correctly handles all four cases:

- (a) Root revoke: `id=rootID` matches the root row itself; `root_token=rootID` matches all children (descendants store `root_token = <root's id>`).
- (b) Non-root revoke (cascade off): `WHERE id=?` is the non-cascade path — no change, correct.
- (c) Non-root revoke (cascade on): `id=midID` matches the mid-chain row; `root_token=midID` — this matches zero rows because descendants' `root_token` points to the actual root, not mid-chain. See new issue section below for the residual gap this introduces.
- (d) Descendants of root target: `root_token=rootID` covers them all.

The critical NULL-semantics bug for root cascade is resolved. However see New Issue 1 below — the cascade-from-non-root behavior has a semantic gap worth calling out.

---

## Section 2 — P1 Verdict

### Finding 1 (r1): Post-UPDATE diagnostic SELECT for error classification is a separate statement

**r2 change quoted (Task 3 Step 4 ConsumeToken docstring):**

> "If (1) affects 0 rows, tx.Rollback; re-SELECT the row by id to classify the failure (not-found / already-consumed / revoked / expired / agent-mismatch) and return the matching ErrXxx."

The r2 text now explicitly places the diagnostic re-SELECT inside the transaction context (`tx.Rollback` implies the tx was open; `re-SELECT the row by id` is the next step). The original concern was that the diagnostic SELECT runs outside the UPDATE's implicit autocommit transaction, creating a TOCTOU window where the SELECT sees different state than the UPDATE saw.

Under the new transactional structure, the flow is:
1. `tx = db.Begin()`
2. `UPDATE ... WHERE id=? AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ? AND agent_id=?`
3. If `RowsAffected() == 0`: still inside `tx` → `SELECT state FROM authz_tokens WHERE id=?` → classify → `tx.Rollback()` → return error.
4. If `RowsAffected() == 1`: `INSERT INTO authorizations ...` → `tx.Commit()`.

With `SetMaxOpenConns(1)`, the transaction serializes all reads and writes. The re-SELECT at step 3 is under the same exclusive lock as the UPDATE, so it sees a consistent snapshot. The TOCTOU window no longer exists once the consume is transactional.

The r2 text could be slightly clearer about the fact that the diagnostic SELECT happens within `tx` (before `tx.Rollback`), not after. But the intent is plain from the surrounding context.

**Verdict: RESOLVED** (as a downstream consequence of the P0 transactional consume fix; no independent change was required)

---

### Finding 3 (r1): Cascade revoke serialization guarantee undocumented

**r2 change quoted:**

> Architecture: "SetMaxOpenConns(1) is the intercore convention — consume transactions serialize naturally. But only for the shared *sql.DB. Never call sql.Open a second time on the same file from the same process — it creates an independent connection pool that races against the first (SQLITE_BUSY territory)."

> Notes on discipline: now contains `RequiresApproval` and library code rules about not calling `sql.Open` internally.

The plan documents that `SetMaxOpenConns(1)` is the serialization backstop. The "open second DB" hazard is now explicit in Prior Learnings. The claim that relaxing `MaxOpenConns` is dangerous is implicit (the new rule forbids a second `sql.Open`).

**Verdict: PARTIAL**

The concern had two parts: (a) document the dependency on `SetMaxOpenConns(1)` for revoke-before-consume ordering; (b) add a `TestRevokeConsumeConcurrency` race test. Part (a) is addressed in the Architecture section. Part (b) is present in the test matrix as `TestRevokeVsConsume_Race` — "revoke + consume in parallel against same token → exactly one semantically wins; both leave consistent state." That directly covers the race. However, the plan still does not explicitly document what happens if `MaxOpenConns` is relaxed — it only forbids the second `sql.Open`. A developer who bumps `MaxOpenConns` to 2 for a performance experiment would not be warned. The risk remains latent. The test covers the current correct behavior but does not document the invariant's dependency on the pool size.

This is a documentation gap, not a code gap. The P1 rating was for an undocumented dependency. The test is new and valuable. Rating this PARTIAL rather than RESOLVED because the canon doc requirement (note in `authz-token-model.md` that pool size is load-bearing for revoke ordering) is mentioned only obliquely in the Architecture bullet, not as an explicit note in the spec doc.

---

### Finding 5 (r1): `delegate_to` field semantics underspecified

**r2 change quoted (Task 1 Step 1 delegation semantics):**

> "Linear-chain runtime lock-in: … DelegateToken's single-parent signature … Task 1 canon doc pins exactly where chain assumptions live so the v2.x diff is discoverable."

> Prior Learnings: "Linear-chain runtime lock-in: DelegateToken returns a single token with one parent_token, and depth += 1 is implicit in the spec struct's zero default."

The r2 plan adds the "linear-chain runtime lock-in" note and pins DAG migration touch points. But the specific `delegate_to` field semantics issue — that a root token's `delegate_to` is always empty even after delegation, so `delegate_to==""` cannot be read as "never delegated" — is not explicitly addressed in the revised text. The field appears in the `tokenSignedFields` list without clarifying annotation. The payload spec section (Task 1 Step 2) shows worked example (i): `root issue: parent_token="", root_token="", depth=0, delegate_to=""` which correctly shows the root has empty `delegate_to`. But the r1 concern was about a future auditor misreading this.

**Verdict: PARTIAL**

The r2 plan does not add the requested "NOTE box" to `authz-token-payload.md` clarifying that `delegate_to` in a row is the child-agent designation at issue time, not a post-fact annotation. The worked examples are correct and will help, but the explicit warning against the `delegate_to=="" → never delegated` misread is absent. The risk is low-severity (P1 in r1, and documentation-only), but the canon doc is the normative reference and should carry the explicit warning.

---

### Finding 8 (r1): gate_token_consume fall-through on already-consumed tokens

**r2 change quoted (Task 5 Step 1 gate_token_consume):**

> "4 → auth-failure (sig-verify / POP / scope-widen / caller-mismatch / cross-project / expect-mismatch): HARD FAIL."
> "The key r2 change: auth-failure (exit 4) is a hard gate failure, not a fall-through."

> Must-Haves: "On auth-class failure (revoked / POP-failure / scope-mismatch / cross-project / sig-verify), fails the gate rather than falling through — the operator's revoke-intent is honored even when a legacy path could have granted approval. On token-state failure (expired / already-consumed) or missing-token: falls through to legacy gate_check."

Wait — the Must-Haves section groups "revoked" into auth-class failures (hard-fail), but the Task 5 Step 1 shell code puts exit-code 2 (which covers already-consumed, expired, AND revoked) into the fall-through branch:

```
2 → token-state (consumed/expired/revoked): fall through to legacy check.
```

And the comment justification reads: "Revoked is indistinguishable from consumed/expired here because the CLI stderr line carries the class; wrappers log it but all three mean 'token can't authorize, try legacy'. This is safe: a revoked token defeats token-path auth, and the legacy policy still enforces its own rules."

The r1 concern was specifically about already-consumed tokens: a second invocation of the same gate with the same token falls through and the legacy gate may permit the op. The r2 plan explicitly preserves this fall-through for exit code 2 (which includes already-consumed). The justification given is that "the legacy policy still enforces its own rules" — which may or may not refuse the op.

**Verdict: PARTIAL**

The r2 plan correctly hardens auth-failures (exit 4) to hard-fail. But the already-consumed path still falls through. The r1 finding was specifically about this: an operator revoking a token intends to prevent the operation; but a consumed token cannot be revoked (it's already terminal), so the fall-through for already-consumed is defensible. The r2 comment addresses revoked tokens by noting "the legacy policy still enforces its own rules" — but this relies on the legacy policy being configured correctly, and gives no audit signal that the second attempt used the legacy path. The r1 suggestion for a `CLAVAIN_AUTHZ_TOKEN_STRICT=1` mode was not adopted.

The plan partially addresses the concern: auth-failures are hardened (the main attack vector), but already-consumed fall-through remains with a documented justification. For the ic-publish-patch gate specifically, the double-publish concern remains if legacy policy permits it. The E2E test matrix (scenario 8) explicitly tests double-consume rejection at the token level but does not test the fall-through-to-legacy behavior after double-consume.

---

### Finding 9 (r1): Migration 034 cutover marker uses random ID — not idempotent

**r2 change:** No change is visible in the r2 migration SQL for Task 2 Step 1. The cutover marker still reads:

```sql
INSERT INTO authorizations (
    id, op_type, target, agent_id, mode, created_at, sig_version
) VALUES (
    lower(hex(randomblob(16))),
    'migration.tokens-enabled',
    ...
);
```

The fixed-ID pattern with `INSERT OR IGNORE INTO` was the r1 suggestion. The r2 plan does not adopt it.

**Verdict: NOT RESOLVED**

The random ID makes the migration marker non-idempotent. If the migration branch runs twice (which cannot happen in practice due to the `user_version` guard, but can happen in tests that create and drop DBs programmatically), two markers will be inserted. More practically, `TestMigration034_CutoverMarker` tests for the presence of `op_type='migration.tokens-enabled'` — if the test framework tears down and re-migrates the DB, the count could be > 1. The test name `TestMigration034_FreshDBSkipsCutover` remains misleading (r1's second sub-concern).

This is the same P1 gap as r1. The fix is a one-line change: replace `lower(hex(randomblob(16)))` with `'migration-034-cutover-marker'` and add `INSERT OR IGNORE`. No architectural reason prevents this.

---

### Finding 12 (r1): --expect-op / --expect-target flags missing from CLI handler spec

**r2 change quoted:**

> Must-Haves: "clavain-cli policy token consume --token=<str> --expect-op=<o> --expect-target=<t> exits 0 on success …"

> Task 4 Step 3: "cmdPolicyTokenConsume(args) → flags --token (else reads $CLAVAIN_AUTHZ_TOKEN) --expect-op --expect-target (both optional but recommended; wrappers always pass)."

> Error class: `ErrExpectMismatch = errors.New("authz-token: --expect-op/--expect-target did not match token scope")`

> ExitCode mapping: `ErrExpectMismatch` → exit 4 (auth-failure class).

> ConsumeToken signature: `ConsumeToken(db *sql.DB, pub ed25519.PublicKey, tokenStr, callerAgentID, expectOp, expectTarget string, now int64) (Token, error)`

> Notes on discipline for must-haves: The consume handler flags now include `--expect-op` and `--expect-target` as explicitly listed flags.

**Verdict: RESOLVED**

Both flags are now defined on `cmdPolicyTokenConsume` and the scope-check is performed by `ConsumeToken` (pre-transaction, per the docstring). The error sentinel `ErrExpectMismatch` maps to exit code 4 (auth-failure). The tests `TestConsumeToken_ExpectOpMismatch` and `TestConsumeToken_ExpectTargetMismatch` cover both cases. The r1 concern about a scope mismatch silently succeeding is closed.

---

## Section 3 — New Issues Introduced by r2

### New Issue 1 — Cascade-from-non-root with the `WHERE id=? OR root_token=?` predicate revokes only the target row, not its descendants (P1)

**Severity:** P1 — functional gap in stated behavior

**Plan text:**

> Must-Haves: "For a non-root, the same predicate reduces to WHERE id=? (because no row has its id as another's root)."

This is the plan's own justification for why cascade-from-non-root works. But the claim "no row has its id as another's root" is the issue.

The `root_token` column stores the **first ancestor (depth=0)** — not the immediate parent. When you have:
- Root R: `id=R, root_token=NULL`
- Child C1: `id=C1, parent_token=R, root_token=R`
- Child C2: `id=C2, parent_token=C1, root_token=R` (not C1 — it stores R, the first ancestor)

Now issue `RevokeToken(db, C1.id, cascade=true, now)`:

Predicate: `WHERE (id=C1 OR root_token=C1) AND revoked_at IS NULL`

- `id=C1` matches the C1 row. Correct.
- `root_token=C1` matches rows where `root_token` equals `C1.id`. But C2's `root_token` is `R`, not `C1`. So C2 is NOT revoked.

Result: `--cascade` on a non-root node revokes only that node, silently leaving all its descendants active. This is exactly the pre-r2 NULL bug reborn for a different case — the predicate is correct for root nodes but incorrect for mid-chain cascade.

E2E scenario 11 ("Revoke-cascade from mid-chain") tests this:

> "issue root → d1 → d2 → d3 → revoke --cascade <d1.id> → consume d1, d2, d3 → all exit 2"

If `d2.root_token = R` (not `d1`), then `WHERE id=d1 OR root_token=d1` will match only `d1`. `d2` and `d3` will have `root_token=R`, and `root_token=d1` will match zero additional rows. The e2e test as written will fail against this implementation.

The plan's statement "no row has its id as another's root" is incorrect for any non-root node that has descendants — those descendants' `root_token` points to the ultimate root, not to the mid-chain node.

**Concrete interleaving showing the gap:**

1. R issued (root_token=NULL, depth=0).
2. C1 delegated from R: C1.root_token = R.id, depth=1.
3. C2 delegated from C1: C2.root_token = R.id (denormalized to first ancestor), depth=2.
4. `RevokeToken(C1.id, cascade=true)` runs `WHERE (id=C1 OR root_token=C1)`. C2.root_token is R.id, not C1.id. C2 is not matched.
5. C2 remains unconsumed and unrevoked. `ConsumeToken(C2)` succeeds. Invariant 8 violated.

**Fix required:** For cascade from a non-root node, the predicate must be:

```sql
WHERE (id=? OR (root_token=? AND parent_token=?))
```

Or more correctly, for the "revoke this subtree" semantic, the code needs to identify all descendants by walking the `parent_token` chain, or by rethinking the denormalized field.

The simplest correct fix: change `root_token` denormalization so every row stores the **subtree root of the cascade target**, not necessarily the depth-0 root. But this conflicts with the current schema where `root_token` is always the depth-0 ancestor.

The better fix (matching the plan's existing schema) is: for non-root cascade revoke, the SQL predicate cannot be expressed as a single flat WHERE because descendants of a mid-chain node can only be found by walking `parent_token`. Use a recursive CTE:

```sql
WITH RECURSIVE sub AS (
  SELECT id FROM authz_tokens WHERE id = ?      -- anchor: the target
  UNION ALL
  SELECT t.id FROM authz_tokens t
  JOIN sub s ON t.parent_token = s.id
)
UPDATE authz_tokens SET revoked_at = ?
WHERE id IN (SELECT id FROM sub) AND revoked_at IS NULL
```

Note: the plan's Prior Learnings says "modernc.org/sqlite does NOT support CTE-wrapped UPDATE ... RETURNING" — but this CTE wraps UPDATE with an IN clause (not RETURNING), which is supported by modernc.org/sqlite. The RETURNING constraint is specifically about the RETURNING clause, not CTEs in general.

Alternatively: if the semantic is "cascade from root always, never from mid-chain", document that explicitly and change the CLI to reject `--cascade` on non-root tokens (check `token.Depth == 0`). This is the simplest fix that matches the actual behavior of the predicate.

**This also means E2E scenario 11 as written will fail**, which provides a useful regression signal — but the plan should not ship with a stated "all exit 2" expectation it cannot meet.

---

### New Issue 2 — `TestConsumeToken_PartialFailure_Atomic` fault-injection mechanism is underspecified for implementation (P2)

**Severity:** P2 — implementation ambiguity

**Plan text (Task 3 Step 5 and Must-Haves):**

> "Test TestConsumeToken_PartialFailure_Atomic forces this via a CONSUME_FAULT_INJECT_AFTER_UPDATE=1 hook gated behind a `// +build testfault` tag."

The mechanism is named but not specified to the level an executor can implement it unambiguously. Specifically:

1. **Where does the hook live?** The fault injection must be inserted *after* the `UPDATE ... SET consumed_at=?` within the transaction but *before* the `INSERT INTO authorizations`. This means the hook is inside `ConsumeToken` in `token.go`. But `token.go` is library code — injecting `os.Getenv("CONSUME_FAULT_INJECT_AFTER_UPDATE")` into library code violates the rule "no `os.Getenv` inside library code" stated in Notes on Discipline.

2. **Build tag consistency:** The plan says `// +build testfault` but Go 1.17+ uses `//go:build testfault`. The old `// +build` syntax is deprecated. Using the wrong form means the tag is silently ignored in Go 1.21+, and the fault injection runs in all builds instead of only test builds. This is a security defect if it lands that way.

3. **Return-what error?** If the hook fires, what does `ConsumeToken` return? The plan says `TestConsumeToken_PartialFailure_Atomic` asserts "UPDATE rolled back; token still consumable" and `TestConsumeToken_NoAuditRowOnRollback` asserts "no orphan." But the test must also be able to distinguish fault-injection failures from genuine INSERT failures. If the hook returns `errors.New("testfault: injected")`, it will be classified as exit code 1 (unexpected), which is correct but the test should assert this explicitly.

**Suggested clarification:**

The plan should specify:
- The hook lives in a sibling file `token_testfault.go` with `//go:build testfault` (note: no space before `go:build`).
- The hook is a package-level variable: `var consumeFaultAfterUpdate func() error = nil` (nil in normal builds; set by the testfault file).
- The `token_testfault.go` file reads `os.Getenv("CONSUME_FAULT_INJECT_AFTER_UPDATE")` and assigns a sentinel function — this is the only place env is read, isolating the violation.
- The verify block for Task 3 adds: `cd core/intercore && GOTOOLCHAIN=local go test ./pkg/authz/ -run TestConsumeToken_PartialFailure_Atomic -tags testfault -v`

Without this level of spec, implementors have two plausible interpretations: inline env-check inside `ConsumeToken` (violates library rule), or a testable-interface injection that requires a different calling convention. The current spec is ambiguous.

---

### New Issue 3 — `ExitCode` switch has no `default` arm for `ErrDepthExceeded` when triggered from within the transaction re-SELECT (P2)

**Severity:** P2 — exhaustiveness gap

**Plan text (Task 3 Step 3):**

```go
func ExitCode(err error) int {
    switch {
    case err == nil:
        return 0
    case errors.Is(err, ErrAlreadyConsumed),
         errors.Is(err, ErrExpired),
         errors.Is(err, ErrRevoked):
        return 2
    case errors.Is(err, ErrNotFound),
         errors.Is(err, ErrBadTokenString):
        return 3
    case errors.Is(err, ErrSigVerify),
         errors.Is(err, ErrProofOfPossession),
         errors.Is(err, ErrCallerAgentMismatch),
         errors.Is(err, ErrCrossProject),
         errors.Is(err, ErrScopeWidening),
         errors.Is(err, ErrDepthExceeded),
         errors.Is(err, ErrExpectMismatch):
        return 4
    default:
        return 1
    }
}
```

The `ExitCode` function itself looks exhaustive: all 11 named errors are covered, and `default: return 1` catches anything else (DB errors, I/O errors, context cancellations, etc.). That part is correct.

The gap is narrower: when `ConsumeToken`'s 0-rows diagnostic re-SELECT classifies the failure as `agent_id` mismatch (a case not enumerated in the WHERE-clause failure classes in the docstring), the plan says "not-found / already-consumed / revoked / expired / agent-mismatch." The re-SELECT check for agent mismatch compares `row.AgentID != callerAgentID` — this returns `ErrCallerAgentMismatch`, which maps to exit 4. That is correct.

However: the diagnostic re-SELECT path cannot distinguish between "consumed_at IS NOT NULL" (already consumed) and "revoked_at IS NOT NULL" (revoked) if both are set simultaneously (the plan does not enforce a CHECK constraint preventing both from being set; r1 Finding 1's second part). In the current r2 plan, `consumed_at` and `revoked_at` can theoretically both be set (an already-consumed row later had cascade revoke run on it per the plan's TOCTOU notes: "If consume lands first, it succeeds; the subsequent cascade still sets revoked_at on the already-consumed row (harmless for audit; the consume is final)"). In that state, the re-SELECT diagnostic would see both set and return whichever it checks first. If the re-SELECT returns `ErrAlreadyConsumed`, that is correct (consume was authoritative). If it returns `ErrRevoked`, it is misleading. The plan does not specify the priority of the diagnostic check when multiple columns are set.

**This is a mild P2.** The fix: in the diagnostic re-SELECT, check `consumed_at IS NOT NULL` first, then `revoked_at IS NOT NULL`. Document this priority order in a comment inside `ConsumeToken`. The plan should add: "If both consumed_at and revoked_at are set, the diagnostic returns ErrAlreadyConsumed (consume wins)."

---

### New Issue 4 — `DelegateToken`'s in-transaction depth re-SELECT is under-specified: which lock does it hold? (P2)

**Severity:** P2 — latent correctness risk if pool grows

**Plan text (Task 3 Step 4):**

> "Depth: parent.Depth + 1 <= 3 … also re-SELECT parent.Depth inside the insert transaction to defeat concurrent-delegate races under MaxOpenConns=1."

> "Under MaxOpenConns=1 transactions serialize, but the CHECK constraint alone would allow both. The in-transaction re-SELECT of parent.depth is belt-and-suspenders; strict correctness already falls out of MaxOpenConns=1 + transactional INSERT, but the re-SELECT documents intent and survives future pool-size changes."

The plan acknowledges the re-SELECT is "belt-and-suspenders" but claims it "survives future pool-size changes." This is incorrect.

Under `MaxOpenConns=1`, the re-SELECT inside the transaction is safe because only one goroutine can hold the connection at a time — a concurrent `DelegateToken` cannot run its own SELECT until this transaction releases. But under `MaxOpenConns=2` (or any value > 1), two goroutines can both enter their respective `DelegateToken` transactions, both re-SELECT `parent.depth=2`, both compute `depth=3`, and both INSERT — CHECK constraint allows depth=3 so both succeed. The re-SELECT does not acquire a row-level lock in SQLite WAL mode (SQLite does not have row-level locks); it is a plain SELECT inside the transaction, not a `SELECT ... FOR UPDATE`.

The plan's claim that the re-SELECT "survives future pool-size changes" is false. The re-SELECT only documents intent — it does not provide any concurrency guarantee beyond what `MaxOpenConns=1` already provides.

**This is a documentation accuracy issue, not a current code bug** (the code is correct under `MaxOpenConns=1`). The plan should not claim the re-SELECT provides protection beyond the pool-size constraint. The correct statement is: "The re-SELECT verifies depth at transaction time; correctness depends on `MaxOpenConns=1`. Any increase to pool size requires a schema-level enforcement strategy (e.g., a unique constraint on `parent_token` to enforce one-child-per-parent at the DB level, or explicit application-layer locking)."

---

### New Issue 5 — `callerAgentID` check inside the WHERE clause vs. diagnostic re-SELECT: `agent_id` mismatch is silent before consuming (P1)

**Severity:** P1 — security-relevant behavior gap

**Plan text (Task 3 Step 4 ConsumeToken):**

The UPDATE WHERE clause includes `AND agent_id = ?` (the `callerAgentID` parameter). If the caller's agent ID does not match, the UPDATE affects 0 rows. The diagnostic re-SELECT then classifies this as `ErrCallerAgentMismatch`.

This is structurally correct. However, there is a subtle ordering issue: the signature verification (`VerifyToken`) happens **before** the transaction opens. If the signature verifies but `agent_id` mismatches, the caller knows:
1. The token is cryptographically valid (signature passes).
2. The token is not for them (agent_id mismatch, exit 4).

This is the correct and intended behavior per the POP design. But the plan specifies the `agent_id` check is in the WHERE clause rather than as an explicit pre-flight check. This means the only way to get `ErrCallerAgentMismatch` is if the UPDATE affects 0 rows AND the re-SELECT shows `agent_id != callerAgentID` AND none of the other conditions (consumed, revoked, expired) are true.

The problem: if the token is both already-consumed AND has an agent_id mismatch, the diagnostic re-SELECT returns `ErrAlreadyConsumed` (consumed_at check fires first, assuming the documented priority order from New Issue 3). The caller learns the token is consumed, not that they were the wrong agent. This is an information leak: an agent can probe whether a token ID was consumed by presenting it with any agent ID. If consumed, exit 2; if not consumed but wrong agent, exit 4 (with `ErrCallerAgentMismatch`). This is a distinguishing oracle.

**The distinguishing oracle is unavoidable at exit code level** (exit 2 vs 4 reveals state), but the plan should acknowledge it in `authz-token-model.md §threat-model` so it is a documented decision, not an oversight. The alternative (return the same exit code 4 for all failure modes when agent_id is wrong) would prevent consumers from knowing whether their own tokens are still active, which is worse for usability.

**Minimum fix:** Add one sentence to the threat model section: "A caller presenting a token with a mismatched agent_id can distinguish already-consumed tokens (exit 2) from agent-mismatch on an active token (exit 4). This is an intended distinguishing oracle — denying it would prevent legitimate agents from diagnosing state. It does not expand the attacker's capability, since knowing a token is consumed provides no usable authority."

---

### New Issue 6 — Gate fall-through on exit code 2 (revoked) conflicts with Must-Haves (P1)

**Severity:** P1 — contradiction between two sections of the plan

**Plan text conflict:**

Must-Haves states:

> "On auth-class failure (revoked / POP-failure / scope-mismatch / cross-project / sig-verify), fails the gate rather than falling through"

This explicitly puts "revoked" in the hard-fail category.

But Task 5 Step 1 `gate_token_consume` shell implementation assigns exit code 2 (which covers revoked, consumed, and expired) to the fall-through branch:

```bash
2)
    echo "authz: token unusable (state): ${out}" >&2
    echo "authz: falling back to policy check" >&2
    return 0
    ;;
```

The code comment acknowledges this: "Revoked is indistinguishable from consumed/expired here because the CLI stderr line carries the class; wrappers log it but all three mean 'token can't authorize, try legacy'."

This is a direct contradiction with the Must-Haves claim. The Must-Haves says "revoked → hard fail." The implementation says "revoked → fall through." The implementation comment argues for fall-through on grounds that "the legacy policy still enforces its own rules." That reasoning may be defensible, but the Must-Haves text should match the implementation.

One of these two must change:
- Option A: change the shell implementation to hard-fail on revoked (exit 2 when class=revoked). This requires the shell wrapper to parse the `ERROR token-invalid: revoked` classifier from stderr to distinguish revoked from consumed/expired. The plan says the shell wrapper should discriminate on exit code (5 classes), not on the stderr class string — so this would require either a new exit code (e.g., exit 5 = revoked, separate from exit 2 = consumed/expired) or parsing stderr.
- Option B: change the Must-Haves text to accurately state that revoked falls through to legacy (and explain that legacy policy enforcement is the guard).

Option A is the security-correct behavior: a revoked token represents operator intent to block an operation. Falling through to legacy potentially honors the op anyway. Option B is a documentation fix that accepts the current fall-through behavior.

This is a P1 because the Must-Haves and implementation disagree on a security-relevant behavior, and the plan as written will be ambiguous to an implementor.

**Suggested resolution:** Decide which behavior is intended and make both sections consistent. If fall-through is the intent, remove "revoked" from the hard-fail list in Must-Haves and add a note explaining the rationale (legacy policy is the guard for revoked tokens). If hard-fail is the intent, change exit code 2 to be split: `revoked → exit 5 (hard-fail)` and `consumed/expired → exit 2 (fall-through)`, or parse the stderr class string in the shell wrapper.

---

## Summary Table

| r1 # | r1 Sev | Short title | r2 Verdict |
|------|--------|-------------|------------|
| 2    | P0     | Consume+audit not transactional | RESOLVED |
| 13   | P0     | Cascade revoke WHERE NULL matches zero children | RESOLVED |
| 1    | P1     | Post-UPDATE diagnostic SELECT TOCTOU | RESOLVED (downstream of P0 fix) |
| 3    | P1     | SetMaxOpenConns(1) revoke serialization undocumented | PARTIAL |
| 5    | P1     | delegate_to field semantics underspecified | PARTIAL |
| 8    | P1     | gate_token_consume fall-through on consumed token | PARTIAL |
| 9    | P1     | Migration 034 cutover marker not idempotent | NOT RESOLVED |
| 12   | P1     | --expect-op/--expect-target flags missing from CLI spec | RESOLVED |
| 4    | P2     | DelegateToken fan-out not prevented | (not addressed; no regression; P2 deferred) |
| 6    | P2     | RevokeToken not idempotent | RESOLVED (AND revoked_at IS NULL predicate added) |
| 7    | P2     | TTL clamping clock skew | (not addressed; no regression; P2 deferred) |
| 10   | P2     | RequiresApproval opens DB twice | RESOLVED (explicit db *sql.DB parameter) |
| 14   | P2     | Concurrency test does not race at SQL level | RESOLVED (TestConsumeToken_PartialFailure_Atomic + TestRevokeVsConsume_Race added) |
| 11   | P3     | Payload spec missing exclusion rationale | (not addressed; P3 deferred) |

### r2 Verdict Counts
- RESOLVED: 6 (Findings 2, 13, 1, 12, 6, 10/14)
- PARTIAL: 3 (Findings 3, 5, 8)
- NOT RESOLVED: 1 (Finding 9)
- Not addressed (P2/P3, no regression): 3 (Findings 4, 7, 11)

### New Issues Introduced by r2
| # | Sev | Short title |
|---|-----|-------------|
| New 1 | P1 | Cascade-from-non-root predicate is wrong: child.root_token=ancestor-root, not parent.id |
| New 6 | P1 | gate_token_consume Must-Haves vs. implementation contradict on revoked fall-through |
| New 5 | P1 | callerAgentID oracle: consumed token distinguishable from agent-mismatch |
| New 2 | P2 | PartialFailure_Atomic fault-injection mechanism underspecified (library-code env read, build-tag syntax) |
| New 3 | P2 | ExitCode diagnostic priority: simultaneous consumed+revoked state has unspecified return order |
| New 4 | P2 | DelegateToken in-tx re-SELECT incorrectly claimed to survive pool-size changes |

---

## Top 3 Remaining Concerns

**1. Cascade-from-non-root is silently broken (New Issue 1, P1)**

`WHERE id=? OR root_token=?` with `target.id` fixes root cascades but breaks mid-chain cascades. A `--cascade` revoke on a depth=1 node leaves that node's descendants (depth=2, depth=3) with `root_token=<the root, not the mid-chain node>`, so they are not matched and not revoked. E2E scenario 11 as written will fail. The plan must either restrict `--cascade` to root tokens only (and document this), or use a recursive CTE for the non-root case. This is a regression relative to the stated "cascade revoke soundness" invariant.

**2. Must-Haves and shell implementation contradict on revoked-token behavior (New Issue 6, P1)**

Must-Haves groups "revoked" with hard-fail auth-class failures. The `gate_token_consume` implementation assigns revoked (exit 2) to the fall-through path. These cannot both be correct. An implementor following Must-Haves will build one thing; an implementor following the shell code will build another. The contradiction must be resolved before implementation begins.

**3. Migration 034 cutover marker is not idempotent (Finding 9, NOT RESOLVED)**

The random-ID `INSERT` pattern means a migration that runs twice (e.g., in test setups that call `Migrate()` on a fresh DB, tear it down, and call it again) inserts two marker rows. The 033 migration pattern uses `INSERT OR IGNORE` with a fixed ID string. The 034 migration should do the same. This is a one-line fix with no architectural trade-off.

---

`OVERALL: CHANGES-NEEDED`

Two new P1 issues (cascade-from-non-root predicate regression, Must-Haves/implementation contradiction on revoked) plus one unresolved P1 (migration marker idempotency) block a clean implementation pass. The P0 fixes are correct. The `--expect-op/--expect-target` and transactional consume issues are well resolved.
