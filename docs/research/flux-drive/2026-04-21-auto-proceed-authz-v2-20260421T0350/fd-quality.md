---
reviewer: flux-drive/fd-quality
plan: docs/plans/2026-04-21-auto-proceed-authz-v2.md
bead: sylveste-qdqr.28
date: 2026-04-21
scope: Go quality, idioms, naming, error handling, test strategy
---

# Quality Review — authz v2 token protocol plan

Reference files examined:
- `core/intercore/pkg/authz/sign.go`
- `core/intercore/pkg/authz/keys.go`
- `os/Clavain/cmd/clavain-cli/authz.go`
- `os/Clavain/scripts/gates/_common.sh`
- `os/Clavain/scripts/gates/bead-close.sh`
- `core/intercore/internal/publish/approval.go`
- `core/intercore/internal/db/db.go`

---

## Strengths

The plan is architecturally coherent and shows clear awareness of the existing codebase. Specific strengths:

- **`SetMaxOpenConns(1)` carried through**: explicitly called out in Task 3 and in the "discipline" section. This is the correct serialization strategy for modernc.org/sqlite atomic-consume correctness. No locking layer to invent.
- **Atomic consume design**: using `UPDATE ... WHERE consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ? AND id = ?` + `RowsAffected()` discrimination is idiomatic and matches the documented SQLite constraint (no CTE-wrapped RETURNING). Concretely correct.
- **`tokenSignedFields` constant-list design**: mirrors `signedFields` in `sign.go` verbatim, with the same "do not reorder" discipline. The plan is explicit that `CanonicalTokenPayload` is a separate function with a separate field list. This is the right call; crossing them would be a category error.
- **E2E test matrix (Task 8)**: 13 named scenarios at the Bash level, including cross-project rejection, double-consume, revoke-cascade, and a v1.5-regression guard. This is thorough coverage for an integration harness.
- **`IssueSpec` struct for `IssueToken`**: using a spec struct rather than positional args for the issue path is correct Go practice. The plan inconsistency in `DelegateToken` (see F-02) is the one deviation.
- **Payload stability commitment**: the discipline note "Never reuse the v1.5 canonical payload function for tokens" is operationally sound and matches the v1.5 pattern where `signedFields` is unexported and frozen.
- **Commit discipline**: `.28` child-bead tags are on every commit message; this matches the intent of bead-scoped commits and keeps `git log` navigable by bead.

---

## Findings

### F-01 — P1 — Sentinel error count vs. discrimination value (Task 3, `token.go`)

**Concern:** Nine sentinel errors is at the upper end of what a package should expose without a typed error. Three of them (`ErrAlreadyConsumed`, `ErrExpired`, `ErrRevoked`) all mean "this token is in a terminal non-usable state" — callers that need to fall through to the legacy path in `RequiresApproval` or the gate wrapper will `errors.Is` each separately, and the branches will be:

```go
if errors.Is(err, authz.ErrAlreadyConsumed) || errors.Is(err, authz.ErrExpired) || errors.Is(err, authz.ErrRevoked) {
    // fall through
}
```

This is repetitive and will proliferate across `approval.go`, `authz_token.go`, and the gate wrapper. It also means adding a fourth terminal state in v2.1 requires callers to add another `||` branch.

**Suggested fix:** Keep all nine sentinels for exit-code discrimination in the CLI layer, but add a helper in the same package:

```go
// IsTokenNotUsable reports whether err indicates the token exists but
// cannot be consumed (consumed, expired, or revoked). Callers that need
// to fall through to a legacy approval path use this rather than
// checking each sentinel individually.
func IsTokenNotUsable(err error) bool {
    return errors.Is(err, ErrAlreadyConsumed) ||
        errors.Is(err, ErrExpired) ||
        errors.Is(err, ErrRevoked)
}
```

`approval.go` and the gate fallthrough both call `IsTokenNotUsable`. The CLI handler still maps each sentinel to its exit code via the existing `switch errors.Is(err, ...)` chain. This keeps discrimination where it belongs (the CLI boundary) without burdening call-sites in the library layer.

---

### F-02 — P1 — `DelegateToken` positional args break the spec-struct convention (Task 3, `token.go`)

**Concern:** `IssueToken` correctly uses `IssueSpec` for clarity on optional fields. `DelegateToken` is specified with five positional parameters:

```go
func DelegateToken(db *sql.DB, priv ed25519.PrivateKey, parentID, callerAgentID, toAgentID string, requestedTTL time.Duration) (Token, string, error)
```

The `parentID / callerAgentID / toAgentID` trio will be confusing at every call site — three adjacent strings with no labels. Positional string ambiguity is a known Go footgun (compiler cannot catch `(parentID, toAgentID, callerAgentID)` transposition). The v2.1 cross-project extension will likely need a `ProjectID` field here; adding it will require a signature break.

**Suggested fix:** Introduce `DelegateSpec`:

```go
type DelegateSpec struct {
    ParentID      string
    CallerAgentID string // proof-of-possession check: must equal parent.AgentID
    ToAgentID     string
    RequestedTTL  time.Duration
}

func DelegateToken(db *sql.DB, priv ed25519.PrivateKey, spec DelegateSpec) (Token, string, error)
```

The CLI handler constructs the spec from flags. This mirrors `IssueSpec` exactly, is extensible, and eliminates the argument-order ambiguity.

---

### F-03 — P2 — `(Token, string, error)` triple return vs. method on Token (Task 3, `token.go`)

**Concern:** Both `IssueToken` and `DelegateToken` return `(Token, string, error)` where the string is the opaque `<ulid>.<sighex>` carrier. This is non-standard (Go convention is to return at most one non-error value for a "primary result"). The caller must track two values after every issue/delegate:

```go
tok, opaqueStr, err := authz.IssueToken(db, priv, spec)
```

The opaque string is always deterministically computable from `Token.ID` and `Token.Signature`. Returning it separately creates a state-synchronization risk: a caller could capture only `opaqueStr` and discard `tok`, losing the typed row, or vice versa.

**Suggested fix:** Return only `(Token, error)`. Add `EncodeTokenString(t Token) string` or a method `(t Token) String() string` that encodes on demand. The CLI handler calls `t.String()` after `IssueToken` to write to stdout. This matches how `KeyFingerprint` works in keys.go (takes the key, returns the derived string), and removes the trilateral return entirely.

Note: if the opaque string must be persisted somewhere the Token struct cannot reach (e.g., piped directly to an env var before the DB round-trips), keep the triple but document the invariant explicitly in the function doc comment: "string == EncodeTokenString(tok); both values are consistent".

---

### F-04 — P1 — Exit code sprawl into Go: codes 2–8 are shell-script concerns leaking through Go (Task 4, `authz_token.go`)

**Concern:** The plan prescribes mapping eight distinct error types to eight distinct exit codes (0/2/3/4/5/6/7/8). The existing `authz.go` uses only three codes (0/1/2/3) and maps them via three sentinel errors (`ErrPolicyConfirm`, `ErrPolicyBlocked`, `ErrPolicyMalformed`) caught in `main.go`. The v2 plan adds five more CLI-exit codes that the gate wrapper's `case` statement must enumerate. This is justified for `consume` (the gate wrapper dispatches on 0 vs. 2 vs. 3 semantically), but codes 6 (POP failure), 7 (revoked), and 8 (cross-project) are consumed only by `stderr + human log`; the wrapper falls through to legacy `gate_check` on any non-zero non-0 result. Codes 6/7/8 thus carry no machine-distinguishable value at the wrapper level beyond "not 0".

**The real question:** Does any consumer outside the human operator use exit codes 6, 7, 8 differently from each other? If no: collapse them to a single "hard reject" exit code (e.g., exit 5 = "signature/auth failure, no fallthrough") and distinguish reason via stderr JSON. If yes (e.g., a future script does `if rc == 7 then revoke cascade`), keep them but document the machine-consumer contract explicitly in `docs/canon/authz-token-model.md`.

**Suggested fix:** Determine which codes have machine consumers now. For the current scope: 0 (success), 2 (consumed, fall-through), 3 (expired, fall-through), and 4 (not found, fall-through) are the meaningful distinctions for the gate wrapper. Codes 5/6/7/8 are all "hard fail, no fallthrough" — expose them as exit 5 with a `reason` field in stderr JSON. This keeps the exit-code surface at 0/2/3/4/5, matching the 5-code model typical for CLI tools.

If machine discrimination of 6/7/8 is explicitly needed, keep them, but add a comment block in `authz_token.go`:

```go
// Exit codes for cmdPolicyTokenConsume.
// Codes 2–4 are used by gate wrappers for fallthrough logic.
// Codes 5–8 are informational hard-fails; wrappers treat them identically.
// Any machine consumer of 6/7/8 must be listed here.
const (
    exitConsumeOK         = 0
    exitAlreadyConsumed   = 2
    exitExpired           = 3
    exitNotFound          = 4
    exitSigVerify         = 5
    exitPOPFailure        = 6
    exitRevoked           = 7
    exitCrossProject      = 8
)
```

---

### F-05 — P2 — `now int64` parameter in `ConsumeToken` and `RevokeToken` (Task 3, `token.go`)

**Concern:** Passing `now int64` directly rather than `time.Time` is a testability trade-off the plan makes explicitly. The concern is that the `int64` leaks Unix-seconds semantics into the function signature (what unit? is it milliseconds? microseconds?). `approval.go` and `db.go` both use `time.Now().Unix()` at the call site and pass the result as `int64` — which is fine for internal helpers. But these are exported functions. The existing pattern in `sign.go` passes no time at all (created_at is in the struct). The existing pattern in `approval.go` uses `time.Now().Unix()` locally.

**Suggested fix (option A — simpler, matches codebase):** Change the parameter to `time.Time` and convert inside:

```go
func ConsumeToken(db *sql.DB, pub ed25519.PublicKey, tokenStr string, now time.Time) (Token, error)
```

Tests pass `time.Now().Add(...)` rather than `time.Now().Unix() + delta`. This is more readable, eliminates the unit ambiguity, and `time.Time.Unix()` is called once inside the function where the context is clear.

**Suggested fix (option B — minimal change):** Keep `int64` but rename parameter to `nowUnix` and add a doc comment:

```go
// nowUnix is the current time as Unix seconds (time.Now().Unix()).
// Pass a fixed value in tests to simulate expired/valid states.
func ConsumeToken(db *sql.DB, pub ed25519.PublicKey, tokenStr string, nowUnix int64) (Token, error)
```

Option A is cleaner; Option B is the smallest delta from the plan.

---

### F-06 — P2 — `Token.Signature []byte` field included in signed struct creates confusion (Task 3, `token.go`)

**Concern:** The plan stores `Signature []byte` as a field on the `Token` struct, alongside the 12 fields that form the canonical payload. The comment "not part of signed payload" is the only guard against a future contributor calling `CanonicalTokenPayload(t)` on a token that already has `Signature` set and wondering why the round-trip breaks or, worse, accidentally including the signature bytes in the payload via a refactor. v1.5's `SignRow` avoids this because the signature is NOT a field of `SignRow` at all — it is returned separately by `Sign` and stored in the DB column `signature`, never in the struct.

**Suggested fix:** Mirror v1.5's design: keep `Token` as the DB-row projection (without `Signature`), and return `(Token, []byte, error)` from `SignToken`, where the `[]byte` is the signature. `IssueToken` stores both; `GetToken` returns `(Token, []byte, error)` so callers that need to verify have both halves. Alternatively, use two structs:

```go
// Token is the canonical row projection used for payload computation.
// It does NOT include Signature — see SignedToken.
type Token struct { ... } // 15 fields, no Signature

// SignedToken pairs a Token with its DB-stored signature.
type SignedToken struct {
    Token
    Signature []byte
}
```

`ConsumeToken` returns `SignedToken`; `CanonicalTokenPayload` takes `Token`. This makes it impossible to accidentally include the signature in the payload.

---

### F-07 — P3 — `CanonicalTokenPayload` vs `CanonicalPayload` naming collision risk (Task 3, `token.go`)

**Concern:** Within the `authz` package, `CanonicalPayload` (v1.5, signs `SignRow`) and `CanonicalTokenPayload` (v2, signs `Token`) are now siblings. The suffix `Token` disambiguates, but at a glance in IDE autocomplete both functions appear when typing `authz.Canonical` — a contributor implementing a new feature may grab the wrong one. The v1.5 discipline note ("Never reuse the v1.5 canonical payload function for tokens") acknowledges this risk but relies on documentation rather than naming to enforce the boundary.

**Suggested fix:** The names are acceptable given the discipline note. However, consider prefixing on the v1.5 function for symmetry and future-proofing:

- Rename `CanonicalPayload` → `CanonicalAuthzPayload` (v1.5)
- Keep `CanonicalTokenPayload` (v2)

This is a callers-only rename across `sign.go`, `approval.go`, and existing tests — a mechanical change with no logic delta. If this rename feels like churn given that v1.5 is shipped and stable, the status quo is acceptable with a package-level `// NOTE:` comment at the top of token.go pointing to the distinction. Explicitly do not merge the two into one function with a switch on sig_version.

---

### F-08 — P1 — Concurrency test N=8 may not stress modernc.org/sqlite serialization adequately (Task 3, `token_test.go`)

**Concern:** The plan specifies `N=8 goroutines racing consume; assert exactly 1 success, 7 ErrAlreadyConsumed`. With `SetMaxOpenConns(1)`, SQLite serializes at the connection level, so all 8 goroutines queue against a single connection. At N=8 on a fast machine, the window for observing the race is narrow but reproducible. The concern is not correctness under `SetMaxOpenConns(1)` — the UPDATE-where-consumed_at-IS-NULL contract is sound — but rather that this test would also pass under a *broken* implementation that uses application-level locking instead of the SQL WHERE clause (since application locking also serializes 8 goroutines correctly). The test does not distinguish "atomic SQL" from "application mutex" implementations.

**Suggested fix:** Add a second test that intentionally breaks the connection limit:

```go
// TestConsumeToken_Atomic_NoAppLock verifies the atomic guarantee does NOT
// rely on application-level locking. Opens db with MaxOpenConns(8) to
// allow concurrent connections, then races 8 consumes. Exactly one must
// succeed; the rest must return ErrAlreadyConsumed. This catches the
// "application mutex instead of SQL WHERE" anti-pattern.
func TestConsumeToken_Atomic_NoAppLock(t *testing.T) { ... }
```

This test may be flaky on some platforms due to SQLite WAL contention; if it proves unreliable, guard it with `t.Skip("flaky under high contention; run manually")` and document it as a manual correctness check.

---

### F-09 — P2 — CLI test scope: handler unit tests vs. dispatch integration (Task 4, `authz_token_test.go`)

**Concern:** The plan says "one table-driven test per handler" in `authz_token_test.go`. The existing `authz_test.go` pattern exercises handlers via direct function calls (`cmdPolicyCheck(args)`) with a temp DB, which is white-box unit testing of the handler function. This does NOT exercise the `cmdPolicy` switch dispatch (`case "token": return cmdPolicyToken(args[1:])`). A typo in the switch case would not be caught. The plan adds a new two-level dispatch (`cmdPolicy` → `cmdPolicyToken` → `cmdPolicyTokenConsume`) that the handler-only tests bypass entirely.

**Suggested fix:** Add one black-box dispatch test per new subcommand that calls through the full dispatch chain:

```go
func TestDispatch_PolicyToken_Consume_ExitCode(t *testing.T) {
    // Build the binary (or call main's dispatch function directly if exported).
    // Invoke: cmdPolicy([]string{"token", "consume", "--token=<tok>"})
    // Assert return value is the expected sentinel error.
}
```

This test catches dispatch wiring errors (wrong case string, wrong args slice) without needing to spin up a subprocess. One test function covering `issue`, `consume`, `delegate`, and `revoke` dispatch is sufficient.

---

### F-10 — P2 — Bash gate: `GATE_CONSUMED` global without `local -n` or clear reset guarantee (Task 5, `_common.sh`)

**Concern:** The plan's `gate_token_consume` sets a global `GATE_CONSUMED=0` at entry and `GATE_CONSUMED=1` on success. The existing `_common.sh` convention already uses globals (`GATE_POLICY_HASH`, `GATE_POLICY_MATCH`, `GATE_MODE`), so this is consistent with the established pattern. However, `GATE_CONSUMED` is not exported at the end of the function, while the others are (`export GATE_POLICY_HASH GATE_POLICY_MATCH`). If a subshell is involved in the gate wrapper chain, `GATE_CONSUMED` will not propagate.

Additionally, the fallthrough logic reads:

```bash
if [[ "$GATE_CONSUMED" == "1" ]]; then
```

If `gate_token_consume` is called but `CLAVAIN_AUTHZ_TOKEN` is unset, `GATE_CONSUMED` remains `0` (reset inside the function). But if the function is called from a subshell context (e.g., `out=$(gate_token_consume ...)`), the assignment is in a subprocess and the parent shell never sees `GATE_CONSUMED=1`. The plan's gate wrapper calls `gate_token_consume` directly (not in a subshell), so this is only a latent risk, not a current defect.

**Suggested fix:** Add `export GATE_CONSUMED` at the end of `gate_token_consume`, matching the export pattern of `GATE_POLICY_HASH` and `GATE_POLICY_MATCH`. Add a comment:

```bash
# GATE_CONSUMED must be exported because downstream hooks may run in subshells.
export GATE_CONSUMED
```

Also add a smoke test case that calls `gate_token_consume` from a subshell and asserts the parent sees the expected value after — this catches the subshell propagation failure early.

---

### F-11 — P3 — Commit message `.28` child-bead suffix: granularity mismatch with v1.5 style (Task 1–8 commits)

**Concern:** v1.5 commits used `(sylveste-qdqr)` (the epic ID). The v2 plan uses `(sylveste-qdqr.28)` (the child-bead ID). The child-bead suffix is more precise and locates the commit within the bead tree, which is an improvement. However, `git log --grep=sylveste-qdqr` will now match both v1.5 commits (epic suffix) and v2 commits (child-bead suffix), because `qdqr.28` contains `qdqr` as a substring. Conversely, `git log --grep=sylveste-qdqr.28` will match only v2. This asymmetry is fine and arguably intentional. The only risk is if tooling (e.g., `interstat` or a cost-query script) parses bead IDs from commit messages with an exact match and misses the child-bead variant.

**Suggested fix:** No change required if tooling uses substring match. If tooling uses exact match, adopt a separator that is not a substring of the parent: e.g., `(sylveste-qdqr #28)` or document that `.28` is the canonical child format. Verify against `interstat` cost-query script before the first v2 commit lands.

---

### F-12 — P3 — `docs/canon/authz-token-payload.md` worked examples need explicit sig-version tagging (Task 1, Step 2)

**Concern:** The plan specifies three worked examples in `authz-token-payload.md`. v1.5's `authz-signing-payload.md` (implied reference) covers only `sig_version=1`. The token payload spec covers `sig_version=2`. The plan does not specify that each example must include the `sig_version` field in the example header or that the encoding doc must make the `sig_version` discrimination explicit. If a reader cargo-cults the payload format without noticing the version distinction, they may attempt to verify a v2 token with `CanonicalPayload` (v1.5) — no runtime error, just a silent verify-false.

**Suggested fix:** The spec document should include an explicit preamble:

> This document covers `sig_version=2` tokens only. Do not apply these encoding rules to `authorizations` rows (`sig_version=1`). See `authz-signing-payload.md` for v1.5. Verifying a `sig_version=2` token with the v1.5 `CanonicalPayload` function will always fail; that failure is correct behavior, not a bug.

Add a cross-reference block in `authz-signing-payload.md` pointing at the token payload doc. This is documentation discipline, not a code concern, but the spec is the contract — underspecified examples are a future maintenance tax.

---

### F-13 — P1 — `RequiresApproval` token path: `ConsumeToken` called inside `RequiresApproval` without explicit `CLAVAIN_AGENT_ID` check (Task 6, `approval.go`)

**Concern:** The plan's Task 6 pseudo-code for `RequiresApproval`:

```go
if tok := os.Getenv("CLAVAIN_AUTHZ_TOKEN"); tok != "" {
    // ... Call authz.ConsumeToken. On success, return false.
}
```

`ConsumeToken` verifies the token signature but does NOT check whether the calling agent matches the token's `agent_id`. That check is `ConsumeToken`'s responsibility, not the caller's, but the plan does not specify it as part of `ConsumeToken`'s contract. The plan says proof-of-possession (`CLAVAIN_AGENT_ID == parent.AgentID`) is enforced in `DelegateToken`, not in `ConsumeToken`. For the root-consume case (non-delegated token), a token issued `--for=claude` can be consumed by any agent that has the token string and the project pubkey, because `ConsumeToken` only checks signature and lifecycle state, not `agent_id`.

This is a scope question: is `agent_id` in the token a "who may present" field enforced at consume time, or a "who was intended" annotation field for audit purposes only? The plan's "Must-Haves" says "`agent_id` (who may present this token)" — suggesting enforcement — but `ConsumeToken`'s spec does not include an agent check.

**Suggested fix:** Either:
(a) Add `callerAgentID string` to `ConsumeToken` and enforce `token.AgentID == callerAgentID` before the atomic UPDATE — making the function enforce the "who may present" semantics. The gate wrapper passes `$CLAVAIN_AGENT_ID`.
(b) Explicitly document in the token model that `agent_id` is an audit annotation, not an enforcement field at consume time — and gate enforcement lives in the Bash wrapper and `RequiresApproval`.

Option (a) is safer but means every consume call must know the caller's agent ID, which requires `approval.go` to read `$CLAVAIN_AGENT_ID`. Option (b) matches the current plan text but weakens the "who may present" claim. This must be resolved before Task 3 implementation; the model doc (Task 1) should state which option applies.

---

## Severity Summary

| ID    | Severity | Topic |
|-------|----------|-------|
| F-01  | P1       | Sentinel error ergonomics — `IsTokenNotUsable` helper needed |
| F-02  | P1       | `DelegateToken` positional args — use `DelegateSpec` |
| F-03  | P2       | Triple return `(Token, string, error)` — prefer method |
| F-04  | P1       | Exit code sprawl 2–8 — codes 6/7/8 have no machine consumer; collapse or document |
| F-05  | P2       | `now int64` param — prefer `time.Time` for exported API |
| F-06  | P2       | `Token.Signature` in signed struct — split into `Token` + `SignedToken` |
| F-07  | P3       | `CanonicalPayload` vs `CanonicalTokenPayload` naming — add package-level note |
| F-08  | P1       | Concurrency test N=8 — add `NoAppLock` variant with MaxOpenConns(8) |
| F-09  | P2       | CLI tests cover handlers only — add one dispatch-chain test |
| F-10  | P2       | `GATE_CONSUMED` not exported — add `export GATE_CONSUMED` |
| F-11  | P3       | Commit suffix `.28` vs epic — verify tooling before first commit |
| F-12  | P3       | Token payload doc needs explicit sig-version preamble |
| F-13  | P1       | `ConsumeToken` missing `agent_id` enforcement — resolve "who may present" semantics |

**Count:** P0: 0, P1: 5, P2: 5, P3: 3

---

## Priority Order for Pre-Implementation Resolution

1. **F-13 (P1)**: resolve "who may present" in the token model before writing any Go — it affects `ConsumeToken`'s signature and the model doc.
2. **F-02 (P1)**: `DelegateSpec` — purely additive change to the plan, no downstream impact.
3. **F-04 (P1)**: exit code policy — decide before `authz_token.go` is written; changing exit codes post-implementation requires updating gate wrappers and tests.
4. **F-01 (P1)**: `IsTokenNotUsable` helper — trivially added to `token.go` during Task 3.
5. **F-08 (P1)**: concurrency test — add during Task 3 alongside the N=8 test.
6. **F-06 (P2)**: `Token` / `SignedToken` split — affects `IssueToken`, `GetToken`, `ConsumeToken` return types; decide before Task 3 writing starts.
7. **F-03 (P2)**: triple return — can be resolved at Task 3 time if F-06 is adopted (splitting removes the signature from `Token` naturally).
8. **F-05 (P2), F-09 (P2), F-10 (P2)**: can be addressed during their respective tasks without plan revision.
9. **F-07 (P3), F-11 (P3), F-12 (P3)**: low-risk; address during Task 1 (doc spec) and Task 3.
