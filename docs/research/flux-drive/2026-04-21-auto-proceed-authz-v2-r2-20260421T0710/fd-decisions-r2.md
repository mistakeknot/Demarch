---
artifact_type: flux-drive decision review r2
source: docs/plans/2026-04-21-auto-proceed-authz-v2.md (r2)
prior_review: docs/research/flux-drive/2026-04-21-auto-proceed-authz-v2-20260421T0350/fd-decisions.md
date: 2026-04-21
reviewer: fd-qdqr
revision: r2
---

# Flux-drive Decision Review: Auto-proceed Authorization v2 — Revision 2

## Executive Summary

r2 incorporates 10 material convergent changes from the r1 flux-drive review. Two P0 bugs are fixed (cascade-revoke NULL semantics, transactional consume). Eight P1 gaps are addressed by explicit API commits, decision-gate specification, documentation locks, and instrumentation. Overall coherence improved: fewer implicit dependencies, more transparent lock-in points. **VERDICT: OVERALL → READY with 3 residual concerns noted below.**

---

## Part 1: P1 Findings — Verification Against r2

### Finding 1: Linear-Chain Runtime Lock-in

**r1 Concern:** Code interfaces lock in chain assumptions (`DelegateToken` single parent, `Token.ParentToken string` singular, scope-narrowing compares to one parent) without documenting cost of DAG migration.

**r2 Changes:**
```
From Architecture section:
"Linear-chain runtime lock-in is documented explicitly in Task 1's canon doc —
v2.x DAG migration will require signature changes in `DelegateToken` +
`Token.ParentToken` type widening."

From Must-Haves (point about DelegateToken):
"DAG migration in v2.x will need: (a) multi-parent representation
([]string or many-to-many join table), (b) widened `parent_token` on wire,
(c) multi-parent scope-narrowing rules (intersection of parent scopes).
Task 1 canon doc pins exactly where chain assumptions live so the v2.x
diff is discoverable."

From Task 1, Step 1(c) — Delegation subsection:
"DAG explicitly deferred; document the locations that hard-assume chain:
(i) `DelegateToken`'s single-parent signature,
(ii) `Token.ParentToken string` field,
(iii) scope-narrowing compares against one parent row,
(iv) cascade revoke predicate assumes single `root_token`.
v2.x DAG migration must revisit all four."
```

**Verdict: RESOLVED** — r2 adds explicit, discoverable documentation of the four chain-specific interfaces and notes that v2.x migration requires signature changes. This moves the concern from "implicit lock-in" to "documented, transparent constraint." The cost is visible at implementation time (Task 3 code will reference Task 1 canon doc), not deferred to v2.x planning.

---

### Finding 2: 95% Marker-Removal Threshold Ungrounded

**r1 Concern:** Removal of `.publish-approved` marker is gated on "≥95% token adoption" without defining measurement window, baseline, or decision criteria.

**r2 Changes:**
```
From Architecture section:
"`.publish-approved` marker: v1.5 made `RequiresApproval()` consult authz
records first, marker as fallback + deprecation warning. v2 upgrades the
warning to a louder stderr banner and *instruments the adoption rate* —
Task 6 adds a 30-day rolling measurement
(`SELECT count(*) FROM authorizations WHERE op_type='ic-publish-patch'
AND created_at > now-30d GROUP BY (vetting JSON 'via' field)` split into
`token` vs `marker`). Marker removal deferred to v2.x and gated on a
concrete measurement window, not a vague 95%."

From Must-Haves:
"Task 6 installs a 30-day rolling measurement of `ic publish --patch`
approvals by path (`token` vs `marker` vs `authz-record`). The baseline
is collected during Task 6 implementation (current state: 100% marker).
Marker-full-removal is gated on this telemetry — not a vague '95%'.
The decision gate is:
  *if token+authz-record share ≥90% over a 14-day window AND marker < 10%
  of window, open removal bead.
  If between 10-20% marker, keep deprecation warning for another 14-day window.
  If ≥20%, investigate why adoption stalled.*"
```

**Verdict: RESOLVED** — r2 replaces the vague "95%" with (1) a 30-day rolling-measurement baseline collected during Task 6, (2) explicit decision thresholds (90%+ adoption → open removal bead; 10-20% → re-measure; 20%+ → investigate), and (3) a time window (14-day windows, not one-shot). This transitions the concern from "assumption without evidence" to "instrumentation with explicit gates." The decision is now measurable and actionable.

**Additional scrutiny:** The measurement query is specified but Task 6 subtasks are not detailed in the plan excerpt. Need to verify Task 6 actually instruments the `via` telemetry column in `authorizations` rows. (Plan revision note mentions this but full Task 6 spec would need inspection.)

---

### Finding 3: Single Project-Wide Key Anchor

**r1 Concern:** v2 inherits v1.5's single project key for all agents, with no explicit documentation of v2.x refactoring cost.

**r2 Changes:**
```
From Architecture section:
"Same-project-only in v2; cross-project delegation deferred to v2.1."

From Must-Haves:
"Cross-project tokens are refused: `policy token consume` from a project
whose `.clavain/intercore.db` does not contain the token row exits 4
(auth-failure, class=cross-project) with a stderr message pointing at
`docs/canon/authz-token-model.md §v2.1` for the roadmap."

From Task 1, Step 1(g) — Same-project scope:
"Same-project scope: v2 refuses cross-project consumption. Document the
v2.1 upgrade path (cross-project-id column + multi-project pubkey registry
+ registry-lookup in consume path)."
```

**Verdict: PARTIAL** — r2 addresses cross-project scope *policy* (refusing cross-project tokens in v2) and documents the v2.1 upgrade path. However, the original r1 concern was about the *single project-wide key* (v1.5 plumbing reused, all agents trust the same key-holder). r2 does not explicitly document that v2.x *per-agent-type key management* requires changes to the `LoadPubKey` lookup pattern (as noted in r1 Finding 2).

**Why this matters:** The refactoring cost for v2.x is higher than r2 implies. If v2.x needs per-agent keys, the `VerifyToken` path changes from `LoadPubKey(projectDir)` (one key) to `LoadPubKey(projectDir, agentType)` (registry lookup). r2 documents the cross-project restriction but not the key-management refactoring that cross-project implies.

**Remaining gap:** Add to Task 1 canon doc a "Trust Model" section noting: "v2 uses a single Ed25519 key for all agents within a project. Cross-project delegation (v2.1) will require per-project or per-agent-type keys and a registry lookup in consume paths. The `signer_agent_id` column may need to be added to disambiguate which agent issued a token if multi-signer scenarios emerge."

---

## Part 2: New Decision-Quality Issues from r2

### Issue 1: Exit-Code Collapse (9→5)

**Finding:** r2 collapses the 9-code classification to 5 codes (0/1/2/3/4) by semantic class. Trade-off: simpler wrapper logic vs. less granular error discrimination.

**r2 specification (Task 1, Step 1(e)):**
```
"Exit-code table (0/1/2/3/4; 5 codes total, down from r1's 9) —
error-class discrimination via stderr classifier line, not numeric code."
```

**5-class mapping (Task 3, Step 3):**
- **Exit 0:** nil error (success)
- **Exit 1:** unexpected error (I/O, DB, programmer)
- **Exit 2:** token-state-invalid (already-consumed | expired | revoked)
- **Exit 3:** not-found (malformed string | valid ULID not in DB)
- **Exit 4:** auth-failure (sig-verify | POP-mismatch | scope-widen | cross-project | caller-mismatch | expect-mismatch | depth-exceeded)

**Analysis:**

The mapping groups errors with *different operator responses* into the same exit code:
- **Exit 2 collapse:** `already-consumed`, `expired`, `revoked` — all are "token can't authorize," but semantically different. Consumed is idempotent (safe to retry); expired implies clock skew or timeout; revoked is intentional denial. Wrapper logs the stderr `ERROR token-invalid: <class>` line, but the shell caller (e.g., `case "$rc" in 2)` only sees "2" without parsing stderr.
- **Exit 4 collapse:** Groups `sig-verify` (cryptographic failure, potentially system-critical) with `caller-mismatch` (bearer-token rejection, user-correctable). Also groups `scope-widen` (data inconsistency, investigate) with `expect-mismatch` (user passed wrong flags, rerun).

**Question:** Does the stderr classifier line adequately preserve discrimination for decision-making?

r2 notes: "error-class discrimination via stderr classifier line, not numeric code." The design expects wrappers to parse stderr (`ERROR token-invalid: revoked` vs `ERROR token-invalid: expired`). But shell scripts that use `case "$rc" in 2)` won't parse stderr by default — they'll just see "2" and either:
1. Log the error and fall through (current gate_token_consume spec in Task 5 does this: "2 → token-state... fall through")
2. Hard-fail without detail

The problem: if a token is revoked intentionally (operator wants to deny), falling through to legacy auth is *wrong*. But the collapse makes it indistinguishable from expired (which is safe to fall through). r2's solution is that the CLI prints the classifier to stderr, so a human operator *reading logs* can see the difference. But automated decision logic in scripts cannot reliably discriminate.

**Verdict: ACCEPTABLE but FRAGILE** — The 5-code design works if:
1. All fall-through decisions (exit 2) are safe regardless of the root cause (consumed / expired / revoked are all "try legacy path")
2. stderr is always logged / monitored (not true for all automated gates)
3. Future code that needs to discriminate (e.g., "don't fall through on revoke") has explicit `--check-revoke` flags or separate verify calls

r2's gate_token_consume (Task 5) handles this by falling through on exit 2 (token-state) but hard-failing on exit 4 (auth-failure). This is safe *if* the revoke-semantics are "revocation = token-state, not auth-failure." But conceptually, revocation is closer to "you're not allowed" (auth-failure) than "try again later" (token-state). The design works but is conceptually misaligned.

**Risk mitigation:** Requires clear documentation in Task 1 that "exit 2 encompasses three distinct conditions with different semantics; fall-through decisions must be safe for all three." The plan does not add this warning.

---

### Issue 2: Hard-Fail on Auth-Failure at Gate

**Finding:** r2 commits to hard-failing (returning non-zero exit) on exit 4 (auth-failure) in gate wrappers, rather than falling through to legacy auth.

**r2 specification (Task 5 gate_token_consume spec):**
```
"4 → auth-failure (sig-verify / POP / scope-widen / caller-mismatch /
      cross-project / expect-mismatch): HARD FAIL. The operator's auth
      intent was malformed or the token is unusable for the op. Falling
      through would let a mismatched token's presence silently not matter."
```

**Analysis:**

This is a significant semantic change from the handoff. Previously, a stale or malformed token would be silently ignored (fall through); now it hard-fails the gate. Rationale: if someone sets `CLAVAIN_AUTHZ_TOKEN=<garbage>` (typo, stale, wrong-op), the gate should reject rather than silently ignore and continue to the legacy path.

**Reversibility question:** If this turns out to be too strict (e.g., a legitimate use case requires "try token, fall back to legacy on auth-failure"), how hard is it to change?

- **Code change:** Straightforward — change the gate_token_consume function to return 0 on exit 4 (fall through) instead of returning non-zero.
- **Blast radius:** Any production gate that has been wired for hard-fail will suddenly start accepting auth-failures and falling through. This could unexpectedly bypass intent. A safer rollback would add a `--strict` flag defaulting to true, so opt-out is explicit.
- **Signpost:** The plan does not include a signpost condition (e.g., "if we get >N auth-failures per sprint, reconsider the hard-fail default").

**Verdict: CONSCIOUS CHOICE, REVERSIBLE BUT NOT CHEAP** — The hard-fail is a deliberate security posture (defend against silent failures), not an accidental lock-in. Reverting requires deliberate opt-in. No immediate concern, but the plan should add a "Rollback notes" section noting that reverting requires explicit flag changes and audit-log review.

---

### Issue 3: `DelegateSpec` Struct Commitment

**Finding:** r2 replaces positional string args with a struct, committing the v2 API.

**r2 specification (Task 3, Step 1 types):**
```go
type DelegateSpec struct {
    ParentID       string        // ULID of parent token
    CallerAgentID  string        // from $CLAVAIN_AGENT_ID at CLI layer
    ToAgentID      string        // recipient (child) agent
    RequestedTTL   time.Duration // clamped against parent remaining
}
```

**Analysis:**

Struct adds maintainability (named fields, no positional confusion). But it commits the v2 API shape. Future extensions (e.g., `CrossProjectID` in v2.1, `DelegateUntilTime` vs `RequestedTTL` in v2.2) are additive (backward-compatible); renaming or removing fields is breaking.

**Question:** Is the struct versioned as a stable API?

r2 does not explicitly mark `DelegateSpec` as "v2 stable API, additive-only for v2.x." Without this note, a future refactor might rename `ParentID` to `SourceTokenID` (more precise) or `ToAgentID` to `RecipientAgent` (consistency with naming conventions), breaking any code passing the struct by field order or reflection.

**Verdict: ACCEPTABLE** — Go convention is that structs are stable by default; this is not a concern in the language. However, the plan should add a code comment marking the struct: `// DelegateSpec is stable for v2+; field additions are OK, renamings require major version bump.`

---

### Issue 4: Transactional Consume as Rigid Contract

**Finding:** r2 specifies `BEGIN...COMMIT` wrapping both the token UPDATE and the audit INSERT. This locks in a specific transactional boundary.

**r2 specification (Must-Haves, atomic consume contract):**
```
"Consume wraps the token UPDATE and the authorizations INSERT in one
`BEGIN...COMMIT`. A partial-failure between (1) and (2) must roll back (1)."
```

**Analysis:**

The boundary is well-justified (atomic visibility: either both writes land or neither). But if v2.x needs to add a third write (e.g., telemetry increment, metrics update, signer-audit log), the boundary expands. If the third write is expensive (external service call), the transaction becomes longer. If the third write has different durability semantics (e.g., "log this consume to a distributed event log, but don't fail if the event log is down"), the transaction semantics conflict.

**Question:** Is the boundary intentionally locked at "these two writes, never more"?

r2 does not add a comment like "this transaction boundary includes exactly these two operations; additions require careful analysis of durability vs atomicity tradeoffs." Without this note, a future developer might assume the boundary is flexible.

**Verdict: ACCEPTABLE** — The boundary is correct for v2. If v2.x needs to add writes, the implementation will naturally surface the tension (external service hang, distributed coordination complexity). No immediate change needed, but Task 3 code comments should note "Consume transaction is bounded to token UPDATE + authorizations INSERT; further additions require careful design of durability/atomicity tradeoffs."

---

### Issue 5: `via` Telemetry as Decision Input

**Finding:** r2 makes the marker-removal decision depend on a `via` telemetry stream collected during Task 6. Fallback story?

**r2 specification (Must-Haves, Task 6 subsection):**
```
"Task 6 installs a 30-day rolling measurement of `ic publish --patch`
approvals by path (`token` vs `marker` vs `authz-record`).
...
The baseline is collected during Task 6 implementation (current state: 100% marker)."
```

**Analysis:**

The decision gate depends on successfully collecting the `via` telemetry. If Task 6 implementation has issues (schema change doesn't propagate, queries break, data is garbage), the decision gate has no input. What happens then?

r2 says the baseline is "collected during Task 6 implementation (current state: 100% marker)" — this implies the measurement starts immediately when Task 6 lands. But if the measurement is broken or incomplete, v2.x planning will have stale data.

**Question:** Is there a fallback if telemetry collection fails?

r2 does not specify a manual override path (e.g., "if telemetry is unavailable, default to 'keep marker' for another sprint" or "use sampled audit-log analysis instead"). This is a single point of failure: if the telemetry is broken, the removal decision is blocked.

**Verdict: ACCEPTABLE WITH CAVEAT** — The instrumentation is sound, but the plan should add a "Fallback" note: "If Task 6's telemetry queries fail or are incomplete, v2.x planning defaults to keeping the `.publish-approved` marker and re-measuring the following sprint. A manual audit-log sample can be used as a proxy if the automated measurement is unavailable."

---

### Issue 6: "5-Class Exit Code, Not a Versioned API"

**Finding:** r2's architecture notes say "Adding a new library error does NOT add a new exit code — it maps to an existing class." This constrains future error expressivity.

**r2 specification (Architecture section, exit code policy):**
```
"Exit code policy (reviewed-down in r2): **0** success; **1** unexpected error
(I/O, DB, programmer); **2** token-state-invalid... **3** not-found... **4** auth-failure..."

From Task 3 notes: "Rationale: 11 library errors for test expressivity;
5 exit codes for wrapper simplicity. `ExitCode()` is the single mapping
point — tests assert both the library error and the exit code to catch drift."
```

**Analysis:**

The design assumes that new errors will map to existing classes. For example, if a future version needs a new error `ErrTokenBlacklisted` (token was explicitly blocked by admin), the mapping would be `ErrTokenBlacklisted → exit 4 (auth-failure)`. This is reasonable, but it forecloses the option to add exit 5, 6, etc. later.

**Question:** Is the 5-code invariant meant to survive forever, or just v2+?

r2 does not explicitly state whether the 5-code limit is a permanent constraint or a v2-specific choice. If a v3 needs new error classes with distinct exit codes, the plan should have a migration path.

**Verdict: ACCEPTABLE** — The constraint is reasonable for v2; new errors can be classified into existing classes. But the plan should add a note: "The 5-class exit code space (0/1/2/3/4) is intended for v2. If v3+ needs new error classes with distinct operator responses, a version-negotiation mechanism (e.g., `CLAVAIN_AUTHZ_PROTOCOL_VERSION` env var) should be introduced to allow per-agent exit-code tables."

---

## Part 3: Overall Decision-Coherence Check

**Question:** Do the r2 changes pull in the same direction (safer defaults, fewer implicit dependencies, more explicit gating) or do any conflict?

**Analysis:**

**Alignment detected:**
1. **Cascade-revoke NULL fix** + **transactional consume** = atomicity and correctness improved ✓
2. **Linear-chain lock-in documented** + **DelegateSpec struct** = explicit API contracts ✓
3. **95% marker threshold instrumented** + **decision-gate specified** = measurable gates instead of vague assumptions ✓
4. **Hard-fail on auth-failure** + **caller-identity verification** = security posture strengthened ✓
5. **Exit-code collapse** + **stderr classifier** = surface simplification with detail preserved in logs ✓

**Tensions detected:**
1. **Exit-code collapse (5 codes)** vs. **error-class granularity** — the design assumes stderr parsing for detail, but some wrappers won't parse stderr. Acceptable if wrappers document their assumptions.
2. **Hard-fail on auth-failure** vs. **graceful fallback on token-state** — the design assumes revocation is token-state, not auth-failure. Conceptually misaligned but operationally safe if fall-through is safe for all token-state cases.
3. **Single project-wide key** vs. **v2.1 cross-project roadmap** — key-management refactoring cost is understated in r2. Acceptable if Task 1 canon doc adds a "Trust Model" section.

**Verdict: COHERENT** — The changes are internally consistent and pull in the direction of safer, more explicit design. Residual tensions are acknowledged below.

---

## Part 4: Residual Concerns for v2.x Planning

### Concern 1: Per-Agent Key Management in v2.1+

**Impact:** If v2.1 cross-project delegation is introduced and per-agent keys are needed, the `LoadPubKey` pattern changes from singleton to registry lookup. This affects `VerifyToken` and any delegated-token-verification paths.

**Action:** Task 1 canon doc should add a "Trust Model" section explicitly stating v2's single-key assumption and the v2.1 refactoring cost.

### Concern 2: Exit-Code Discrimination in Scripts

**Impact:** Wrappers that need to distinguish `revoked` from `expired` from `consumed` (all exit 2) cannot do so without parsing stderr. If a future gate needs "hard-fail on revoke but fall-through on expired," the 5-code design is insufficient.

**Action:** Task 5 gate_token_consume spec should document: "Exit 2 fall-through is safe for all token-state cases: already-consumed (idempotent retry), expired (clock-skew recovery), revoked (operator denied access, and legacy auth will also deny). If future gates need to distinguish revocation intent, add a `--verify-not-revoked` flag that calls `policy token verify` before gate_check."

### Concern 3: Telemetry Collection as Single Point of Failure

**Impact:** Marker-removal decision in v2.x is blocked if Task 6's telemetry is broken or incomplete.

**Action:** Task 6 implementation should include explicit error-handling and fallback documentation (manual audit-log analysis, re-measurement windows, etc.).

---

## Summary Table: r1 P1 Findings → r2 Verdict

| Finding | r1 Severity | r2 Verdict | Notes |
|---------|------------|-----------|-------|
| Linear-chain lock-in | P1 | RESOLVED | Task 1 canon doc pins all 4 chain-specific interfaces + v2.x refactoring cost |
| 95% marker threshold | P1 | RESOLVED | Replaced with 30-day rolling measurement + explicit decision thresholds (90%/10-20%/20%+) |
| Single project-wide key | P1 | PARTIAL | Cross-project policy documented; per-agent key refactoring cost still understated |
| Depth cap (3) | P1 | RESOLVED (implicit) | Architecture section confirms 3 is CHECK constraint + CLI enforcement + in-tx re-SELECT |
| Token format `<ulid>.<sighex>` | P1 | RESOLVED (implicit) | Format pinned; architecture notes say format is stable for v2 |
| Exit-code API unversioned | P1 | PARTIAL | 5-code mapping defined; versioning strategy deferred to v3+ |
| Same-project restriction | P2 | RESOLVED | Cross-project refusal explicit; v2.1 upgrade path documented |
| Signer trust limitation | P2 | RESOLVED (implicit) | Proof-of-possession bounds noted; v1.6 out-of-band signer deferred |

---

## New Issues from r2 (P1–P2)

| Issue | Severity | Verdict | Residual Action |
|-------|----------|---------|-----------------|
| Exit-code collapse 9→5 | P2 | ACCEPTABLE | Add stderr-parsing requirement to wrapper docs |
| Hard-fail on auth-failure | P2 | ACCEPTABLE | Add rollback note + signpost criteria |
| DelegateSpec struct | P3 | ACCEPTABLE | Add code comment "v2-stable API, additive-only" |
| Transactional consume boundary | P3 | ACCEPTABLE | Add code comment "exactly these two writes; additions need design review" |
| `via` telemetry as decision input | P2 | ACCEPTABLE | Add fallback documentation to Task 6 spec |
| 5-class exit code invariant | P3 | ACCEPTABLE | Add v3+ versioning note for future protocol versions |

---

## OVERALL ASSESSMENT

**Count by Verdict:**
- **RESOLVED:** 3 (linear-chain lock-in, 95% threshold, same-project restriction)
- **PARTIAL:** 1 (single project-wide key — cross-project policy OK, key-management cost understated)
- **ACCEPTABLE (residual action noted):** 6 (all new issues from r2)
- **NOT RESOLVED:** 0

**Top 3 Remaining Concerns:**
1. **Per-agent key management not explicitly scoped for v2.1** — r2 documents cross-project refusal but not the key-registry refactoring that cross-project implies. Task 1 canon doc needs a "Trust Model" section.
2. **Exit-code collapse assumes stderr parsing** — Wrappers that need nuanced error discrimination (revoke vs. expire) cannot use exit codes alone. Should be documented, not a blocker.
3. **Telemetry collection is a single point of failure for v2.x marker-removal decision** — Task 6 spec should include explicit fallback path if measurement fails.

**Readiness for Implementation:**
- Task 1 (spec-lock) is ready; add Trust Model section to canon doc.
- Task 2 (migration) is ready as-is; P0 NULL-semantics fix is present.
- Task 3 (primitives) is ready; add code comments for transaction boundary and future v2.1 signatures.
- Task 4 (CLI) is ready as-is.
- Task 5 (gates) is ready; add stderr-parsing assumption to gate_token_consume spec.
- Task 6 (telemetry) is ready pending explicit Task 6 subtask spec for `via` column + fallback behavior.

---

## OVERALL: READY

**Conditions for sign-off:**
- [ ] Task 1 canon doc includes explicit "Trust Model" section covering v2 single-key assumption + v2.1 per-agent refactoring cost
- [ ] Task 3 code comments mark transaction boundary as "token UPDATE + authorizations INSERT only; further additions require design review"
- [ ] Task 5 gate_token_consume spec adds note on stderr-parsing requirement and revoke-vs-expire fallthrough semantics
- [ ] Task 6 spec includes explicit telemetry-failure fallback (manual audit-log sampling, re-measurement window)

r2 is materially stronger than r1. The two P0 fixes (cascade-revoke NULL semantics, transactional consume) are critical for correctness. The P1 gaps are addressed by explicit documentation and instrumentation, moving from implicit to transparent. No design regressions detected.
