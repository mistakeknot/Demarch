---
artifact_type: flux-drive-findings
reviewer: fd-architecture
bead: sylveste-qdqr.28
subject_plan: docs/plans/2026-04-21-auto-proceed-authz-v2.md
date: 2026-04-21
severity_counts: {P0: 0, P1: 3, P2: 4, P3: 3}
---

# Architecture Review — Auto-proceed authz v2 (token protocol + delegation chain)

Reviewed against: actual v1.5 code in `core/intercore/pkg/authz/` and `os/Clavain/scripts/gates/`, `core/intercore/internal/publish/approval.go`, `core/intercore/internal/db/db.go`, and the plan at `docs/plans/2026-04-21-auto-proceed-authz-v2.md`.

---

## Strengths

**Atomic consume is correctly modeled.** The plan correctly identifies the modernc.org/sqlite CTE-RETURNING limitation and uses `UPDATE ... WHERE consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?` with `RowsAffected()`. Combined with `SetMaxOpenConns(1)`, this gives single-process linearization without needing advisory locks.

**Signing separation is principled.** Keeping `CanonicalTokenPayload` wholly distinct from `CanonicalPayload` (different field list, different sig_version) is structurally correct. The risk of cross-verification — where a v1.5 sig is accepted as a v2 token — is eliminated by design rather than by convention.

**Cascade revoke denormalization is right for SQLite.** Denormalizing `root_token` avoids recursive CTE traversal (which SQLite supports but modernc.org/sqlite has historically had edge cases with), giving a single-index UPDATE for the cascade.

**Gate wrapper fall-through policy is safe.** `gate_token_consume` never fails the gate on its own; any token-path error falls through to legacy `gate_check`. This preserves the v1 safety floor during the transition window and avoids a single new dependency blocking every auto-proceed op.

**Proof-of-possession check is on the critical path.** `CLAVAIN_AGENT_ID == parentToken.AgentID` as a ship-blocker guard on `DelegateToken` is the right place for this check — done in Go library code before the DB write, not solely in a shell gate that can be bypassed.

**Cutover marker in `authorizations` is clever.** The migration-034 synthetic row lets `policy audit` distinguish "v2 DB with no tokens issued" from "pre-v2 DB" without an extra schema column or out-of-band file.

---

## Findings

### 1. `approval.go` receives a direct `ConsumeToken` call — breaking intercore's published-API boundary

**Severity: P1**
**Plan section: Task 6 — `core/intercore/internal/publish/approval.go`**

The plan instructs `RequiresApproval` to open `.clavain/intercore.db` itself, load the project pubkey, and call `authz.ConsumeToken` directly. Today, `approval.go` already does its own DB open (line 100 of the existing file). That was acceptable for a read-only query. Making it also perform a consuming write from inside the `publish` package means the `internal/publish` package now drives a mutable, security-critical state transition — atomic consume — outside the intercore kernel's normal request path.

The specific risk is double-open: `ic publish --patch` may itself have the DB open through the kernel path (`db.Open`), and `approval.go` opens a second raw `sql.Open` connection. Both use `SetMaxOpenConns(1)` separately, but they are different connection pools. SQLite WAL mode tolerates multiple readers, but two *writers* from the same process (one being a consume UPDATE) can produce `SQLITE_BUSY` under the busy_timeout window. The `approval.go` open uses `_busy_timeout=5000` in the DSN, which may or may not be applied reliably (the intercore CLAUDE.md documents this as unreliable). A publish flow that opens the DB twice for the same SQLite file is fragile.

Suggested fix: expose a `ConsumePublishToken(db *sql.DB, pub ed25519.PublicKey, pluginSlug string) (bool, error)` function that is called by the `ic publish` command *after* it has opened the DB through the normal kernel path. `RequiresApproval` should remain stateless with respect to token consumption — it should receive the already-consumed result as a parameter, not drive the consume itself. This keeps the consume within the kernel-owned DB connection and preserves the single-writer invariant.

---

### 2. `CLAVAIN_AUTHZ_TOKEN` in `approval.go` creates a hidden dependency on process environment in a package that previously had none

**Severity: P1**
**Plan section: Task 6, Step 2 — token path in `RequiresApproval`**

`RequiresApproval(pluginRoot string)` currently has one input: the plugin filesystem path. Its contract is purely functional — given a path, return bool. Task 6 adds a hidden ambient input: `os.Getenv("CLAVAIN_AUTHZ_TOKEN")`. This turns a deterministic function into a context-sensitive one. The callers of `RequiresApproval` in `ic publish` have no visibility that an env var now changes its behavior, which makes the function untestable without environment setup and makes auditing the approval logic harder.

Additionally, `approval.go` sits in `core/intercore/internal/publish` — an `internal/` package. The env-var convention (`CLAVAIN_AUTHZ_TOKEN`) originates in the OS/Clavain layer (bash gate wrappers). Having the kernel's internal publish package directly read a Clavain-layer env var couples the two layers through an implicit side channel that no import graph enforces.

Suggested fix: thread the token string as an explicit parameter: `RequiresApproval(pluginRoot, tokenStr string) bool`. The `ic publish` command (in `core/intercore/cmd/ic/publish.go`) reads `os.Getenv("CLAVAIN_AUTHZ_TOKEN")` at its own layer boundary and passes it down. This keeps `approval.go` testable with table-driven inputs and keeps the environment-reading concern at the delivery layer (CLI command), not in the policy logic.

---

### 3. `policy token` namespace now encompasses policy rules, key management, AND token lifecycle — the `policy` prefix has become a misnomer

**Severity: P1**
**Plan section: Task 4 — CLI namespace, and Prior Learnings section**

The current `cmdPolicy` dispatcher, as read from the actual source, covers: `check`, `record`, `explain`, `audit`, `list`, `lint` (policy rules), `init-key`, `sign`, `verify`, `rotate-key`, `quarantine` (key lifecycle), and now `token {issue,consume,delegate,revoke,list,show,verify}` (token lifecycle). That is three distinct conceptual domains welded under one namespace.

The v1.5 key additions were already a stretch — `init-key` is not a policy concept. After v2, `policy token` is a full lifecycle manager for cryptographic bearer tokens. A developer looking for token commands will not intuitively reach for `clavain-cli policy token`. More concretely, the `cmdPolicy` function will need a usage string listing 18+ subcommands, and the switch statement covering all three domains will be 40+ cases.

The handoff document explicitly forbids `authz` as a top-level (the brainstorm wording is superseded). However, that constraint was set to preserve the existing CLI surface. The more important question is whether the `policy` prefix continues to communicate accurately at 3 domains. A middle path that does not require renaming existing subcommands: group the token verbs under a second top-level `token` alongside `policy`, dispatch from `main.go`, and document `policy token` as a deprecated alias pointing to `token`. This requires zero renaming of existing commands, adds one dispatcher level, and gives the token domain a clean home.

If the constraint against a new top-level is firm, the finding degrades to P2 (future maintainability debt). The current plan's choice is internally consistent with the stated handoff constraint; flag it as a constraint that should be revisited before v3 adds a fourth domain.

---

### 4. `GATE_CONSUMED=1` short-circuit creates a parallel execution path in every gate wrapper — divergence risk is proportional to wrapper count

**Severity: P2**
**Plan section: Task 5 — gate wrapper modification pattern**

The plan's wrapper pattern is:

```bash
gate_token_consume "<op>" "<target>"
if [[ "$GATE_CONSUMED" == "1" ]]; then
    exec_op_then_record_and_sign "$@"
    exit $?
fi
gate_check "<op>" "<target>"
exec_op_then_record_and_sign "$@"
```

The two branches diverge after the `if`. Both call `exec_op_then_record_and_sign` (or its equivalent), but the actual wrappers (`bead-close.sh`, `git-push-main.sh`, etc.) do not currently share a common `exec_op_then_record_and_sign` function. Looking at the real `ic-publish-patch.sh`, the post-op sequence is three separate calls: `ic publish --patch`, `gate_record`, `gate_sign`. In each wrapper, those three lines must be replicated in the token-path branch as well.

With four wrappers modified, that is four places where the post-op sequence can drift — a gate_sign call omitted in the token branch, a gate_record omitted on error path, etc. The existing `_common.sh` does not have a `gate_exec_and_record` composite.

Suggested fix: extract a `gate_run_op_and_audit <cmd...>` function in `_common.sh` that runs the op and always calls `gate_record` and `gate_sign` regardless of which auth path was taken. Both branches call the same function. This compresses the duplicated post-op sequencing into one place and ensures token-path and policy-path leave identical audit trails. The plan's intent (audit parity) is good; the risk is in the implementation-level parallelism without a shared post-op helper.

---

### 5. Consume landing a `sig_version=1` audit row couples the token lifecycle to the v1.5 signing scheme for all future versions

**Severity: P2**
**Plan section: Must-Haves — "A v2 consume-audit row lands as `sig_version=1` authorizations"**

The plan states that a token consume event lands as a `sig_version=1` authorizations row (v1.5-shaped). The rationale is that the token itself is `sig_version=2`; the consume event is just a regular authz row. This is correct for v2 but creates a structural forward trap: if `sig_version=1` rows are ever deprecated (e.g., in a v3 that drops the v1.5 signing scheme), the consume audit trail for all v2-era tokens becomes orphaned from the signing path.

The consume row's tie to the token is through a reference to `root_token` in the plan's gate-wrapper flow description. But `authorizations` has no `root_token` column — the link is informal (stored in the consume audit row's `policy_match` or `bead_id` field, presumably, since `authorizations` has no token FK column). This means `policy audit --tokens` must reconstruct the join by convention, not by schema constraint.

Suggested fix: add a `token_id TEXT REFERENCES authz_tokens(id)` column to `authorizations` in migration 034 as a nullable FK. Consume-audit rows populate it; all other rows leave it NULL. This makes the join explicit, survives any future changes to field encoding conventions, and gives `policy audit --tokens` a first-class schema path instead of a string-matching reconstruction.

---

### 6. Schema carries full DAG columns (`root_token`, `depth`, `parent_token`) for a feature (cross-project DAG delegation) not shipped in v2 — partial YAGNI

**Severity: P2**
**Plan section: Architecture section — "Same-project-only in v2; cross-project delegation deferred to v2.1 with schema already DAG-ready"**

`root_token`, `depth`, and `parent_token` are in the schema. The rationale is that these fields are needed even for v2's linear chain. That is correct: `root_token` is needed for cascade revoke, `depth` for the cap check, `parent_token` for ancestry. So their presence is justified by v2 functionality.

What v2.1 adds is not these three fields but `cross_project_id` (cross-project scoping) and a multi-project pubkey registry. Neither of those is in the v2 schema. The plan's claim that the schema is "DAG-ready" refers to the delegation link structure. However, a DAG (multiple parents per token) requires `parent_token` to be a many-to-many junction or a denormalized array — neither is in the current schema. The current `parent_token` is a single FK, which supports only trees (linear chains). "DAG-ready" overstates the schema's capability: it is tree-ready, which covers v2.1 (still linear but cross-project). True DAG would require a separate junction table.

This is a documentation/framing issue more than a code issue. The YAGNI violation is minor: the three columns exist but are fully used by v2. The fix is editorial: change "DAG-ready" to "linear-chain-ready, tree-extensible" in the canon doc and deferred-work note to avoid misleading future implementors who encounter the schema and assume multiple parents per token are already supported.

---

### 7. Test strategy has three locations for overlapping coverage of atomic consume — no clear ownership boundary

**Severity: P2**
**Plan section: Task 3 `token_test.go`, Task 4 `authz_token_test.go`, Task 8 e2e**

`TestConsumeToken_Atomic_FirstWins` (pkg/authz), a table-driven CLI test for `consume` exit code 2 (authz_token_test.go), and e2e scenario 7 (double-consume rejection) all exercise the same invariant: exactly one consume wins among concurrent callers. The Go unit test runs with a real in-process SQLite; the CLI test shells out to the binary with a temp DB; the e2e test does the same through the full gate wrapper.

The CLI-level test adds no new coverage of the atomicity property — atomicity is a DB-level guarantee, and the CLI handler is a thin translator of the library's exit code. The CLI test's value is in verifying exit-code translation (exit 2 for `ErrAlreadyConsumed`), not in re-testing the race. Running an 8-goroutine race in the CLI test would be both slow and structurally incorrect (it's testing the binary's I/O, not the library's serialization).

Suggested fix: scope the CLI test to one happy-path consume and one already-consumed non-concurrent call (verifying exit code translation only). Move all concurrency/atomicity coverage to `TestConsumeToken_Atomic_FirstWins` with the `t.Parallel()` + `sync.WaitGroup` harness. The e2e double-consume test should remain as a full-stack integration check (sequential, not parallel) that verifies the audit row count. This avoids three partial tests of the same invariant and clarifies that the library owns atomicity, the CLI owns exit-code mapping, and e2e owns end-to-end audit trace.

---

### 8. `CanonicalTokenPayload` duplicates `validateText` / `rejectControlChars` without sharing the helper — duplication is bounded but should be explicit

**Severity: P3**
**Plan section: Task 3 Step 1 — `CanonicalTokenPayload` implementation sketch**

The actual `sign.go` defines `validateText` and `rejectControlChars` as package-private functions. `CanonicalTokenPayload` in `token.go` needs the same NFC+control-char rejection logic. The plan says "NFC + LF join; reject control chars per v1.5 rules" — which implies re-implementing or calling the existing helpers.

Since both files are in `package authz`, `token.go` can call `validateText` and `rejectControlChars` directly without any interface or export change. This is the right answer: no new abstraction, no duplication, just a package-private call. The plan does not make this explicit, which risks an implementor copy-pasting the functions and creating two sources of truth for the control-char rejection set.

Suggested fix: add a single sentence to the Task 3 implementation note: "Call the existing `validateText` and `rejectControlChars` helpers from `sign.go` — both are in `package authz` and are accessible without export." This is a docs fix, not a structural one. If the field dispatch in `CanonicalTokenPayload` uses a `Token.fieldBytes(name)` method mirroring `SignRow.fieldBytes`, it should share the helper for the `created_at` integer validation too (`r.CreatedAt < 0` guard).

---

### 9. Inline DDL divergence from SQL migration files — v2 is not the right moment to close this gap, but it should be tracked

**Severity: P3**
**Plan section: Task 2 Step 1 — "migrations/NNN.sql files are documentation only since ≥021"**

The plan correctly identifies that real DDL lives inline in `db.go` since migration 021. Migration 034 follows the established convention. The concern is that the SQL files and `db.go` can drift silently — a schema change made to `db.go` without updating the `.sql` file produces misleading documentation. There is no automated check that the two stay in sync.

V2 is not the right moment to restructure this (it would touch 13 migration branches), and the plan is correct to carry the convention forward. However, a lightweight sync check would prevent the gap from widening further.

Suggested fix: add a comment block in `db.go` immediately before each inline migration branch, e.g., `// Source: migrations/034_authz_tokens.sql — keep in sync`. Then add a CI step: `diff <(grep -A200 'migration 034' core/intercore/internal/db/migrations/034_authz_tokens.sql | head -N) <(extract from db.go)`. If the full diff is impractical, at minimum ensure the .sql file's CREATE TABLE column list is byte-identical to the inline DDL via a test fixture comparison.

---

### 10. `RequiresApproval` precedence chain is a Chain of Responsibility — but it needs an explicit error-vs-fallthrough contract

**Severity: P3**
**Plan section: Task 6, Must-Haves — `RequiresApproval` precedence**

The three-path chain (token → v1.5 record → marker) is a correct Chain of Responsibility. The existing two-path version (v1.5 record → marker) already follows this pattern in `approval.go`. V2 prepends a third handler. The concern is not the chain length — three is fine — but the fallthrough contract for the token path.

The plan says: "On ErrAlreadyConsumed/ErrExpired/ErrRevoked/etc., log and fall through to v1.5 path." This means `ErrAlreadyConsumed` silently escalates to the v1.5 authz path. That is operationally surprising: if a token was already consumed (e.g., double-publish attempt), the operator expects a hard rejection, not a silent fallback to policy check. The gate wrapper in Task 5 rejects double-consume with exit 2; but `RequiresApproval` in `ic publish` would silently skip it.

Suggested fix: distinguish between "token not present" (fall through is correct) and "token present but rejected" (hard stop is correct). The rule: if `CLAVAIN_AUTHZ_TOKEN` is set and non-empty, a token-path failure of `ErrAlreadyConsumed`, `ErrRevoked`, or `ErrSigVerify` should return `true` (approval required) with a loud stderr message, not fall through to the v1.5 authz-record path. Only `ErrExpired` and "DB unavailable" errors justify fall-through (token expired → maybe a fresh authz record was also issued). This collapses the ambiguous middle cases and makes the double-consume rejection consistent between the gate wrapper path and the direct `ic publish` path.

---

## Cross-cutting notes

**ULID dependency.** `github.com/oklog/ulid/v2` is justified: its Crockford base32 encoding gives human-readable sortable IDs useful in `policy audit --tokens` tree output, and its monotonic randomness ensures lexicographic ordering matches temporal ordering within a session. A `crypto/rand` + hex alternative would produce 32-char strings that lack time-sortability. ULID is stdlib-adjacent, no CGO, and auditable. Justified, not YAGNI.

**Signature-only consume path.** The plan correctly notes that `ConsumeToken` loads only the public key. This mirrors the v1.5 `Verify` discipline and keeps the private key out of the consume hot path. Correct.

**`SetMaxOpenConns(1)` + WAL linearizes single-process consumes.** Correct for the current single-project, single-process topology. If v2.1 cross-project delegation requires consuming from a remote project's DB, this assumption needs revisiting — but that is explicitly deferred.

**`--issued-since` bulk revoke.** The plan's `cmdPolicyTokenRevoke` lists `--issued-since` as a flag for bulk-revoke of unconsumed tokens since a timestamp. This is not mentioned in the Must-Haves or schema. If it touches only `authz_tokens` rows (no `authorizations` cascade), it is a safe additive. If it is expected to also write revoke audit rows to `authorizations`, that needs to be explicit. Recommend adding a one-line Must-Have clarifying whether bulk revoke writes one audit row per revoked token or a single batch audit row.
