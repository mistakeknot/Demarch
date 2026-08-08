# Round 4 / Probe 3 — Verdict: fd-firing-witness

## What the intersection revealed

The contradiction — instrumentation as *description* (contract) vs instrumentation as *part of the irreversible process* (firing) — turned out to be load-bearing in exactly one structural place: intercore's witness APIs are shaped so that the record is written **after and outside** the irreversible act, and every downstream instrument (replay, event tail, audit verifier) then treats the resulting record as evidentiary anyway.

Three emergent patterns no single parent produces:

1. **Certification converts gaps into lies.** The 15/16 nil-recorder gap (f-039) is, alone, missing data. It becomes a correctness bug only because `ic run replay` (run_replay.go:79-107) certifies completeness — exit 0, no sparsity signal, no completeness field — over a timeline it cannot know is sparse, while reconstruct.go:36 silently drops the coordination source entirely. A contract fix (add a completeness field) without firing discipline is decorative; a firing fix (record more events) without the contract change leaves replay certifying whatever fraction happens to be logged. The remediation must be both: replay must cross-check the `dispatches` table against the event stream and *refuse or annotate* certification when terminal dispatch rows lack terminal events.

2. **The most irreversible transitions are the least witnessed — by structure, not accident.** CancelByRun (bulk kill, dispatch.go:473-488) cannot fire the recorder even where wired, because it bypasses UpdateStatus. ClearLocks deletes the row that is its own best evidence. The inline sweep expires locks inside another caller's transaction where event emission was traded away. In each case the witness was sacrificed precisely where the transition is one-way and violent — because the witness write was *optional plumbing* (a nullable recorder, a callback, a separate handle), and optional plumbing is what gets dropped under transactional pressure. This is the contradiction living in code: the recorder's nil-ability is a contract statement ("instrumentation describes, optionally") that firing practice reads as "the stoke log is optional."

3. **A wrongly-scoped witness is worse than none.** The audit chain, if wired naively as the one witness for gate/dispatch transitions, forks under the multi-producer reality of run-scoped transitions and reports honest firings as tampered (audit.go:81-127 loadLastEntry race → VerifyIntegrity sequence-gap/hash-broken). The false-positive path retrains operators to ignore the verifier — the witness corrupts trust in every record, past and future. Meanwhile its one correlation field (trace_id) sits outside the checksum (audit.go:196-201), so the property that would justify it as the ONE witness is non-evidentiary.

## Audit-wiring compatibility verdict (review area 3)

**Question:** could wiring internal/audit to gate-mode resolutions + dispatch transitions close the 23 traceless weakening sites (f-101/f-102) with ONE witness?

**Verdict: formats compatible, topology and transactionality incompatible — feasible, but NOT one-witness as the package stands.**

- **Payload format: compatible.** `audit.Entry{EventType: state_change, Actor, Target, Payload, Metadata}` cleanly expresses both a gate resolution (target=run_id, payload={from_phase,to_phase,result,tier,reason}) and a dispatch transition (target=dispatch_id, payload={from,to,run_id}). The EventType enum is extensible; two new types or `state_change` suffice.
- **Storage: ready.** `audit_log` exists in schema.sql:366 and migration 020/023; the package is simply never imported (verified — the only `internal/audit` reference tree-wide is its own doc comment).
- **Chain topology: incompatible.** The hash chain is per-session with an in-memory snapshot (lastHash, sequenceNum) loaded at `New()`. Gate resolutions and dispatch transitions are run-scoped and produced by many short-lived CLI processes. session_id=run_id → concurrent producers fork the chain and VerifyIntegrity false-alarms. Needs either run-scoped chains with a single-writer rule, a DB-side sequence allocator (e.g., per-chain sequence via UPDATE...RETURNING inside the write tx), or fork-tolerant verification.
- **Transactionality: incompatible.** `Logger.Log` writes through its own `*sql.DB` with no tx admission (audit.go:130,172). The one place it would matter most — cmdGateOverride (gate.go:264-359), which already does read→invariant→update→event in ONE transaction — cannot include the audit entry in that transaction. Minimal wiring outside the tx reproduces the dispatch recorder's crash window.
- **Correlation: weakened by policy.** trace_id is excluded from the checksum for backward compat (audit.go:196-201); the cross-layer correlation that is the whole point of the one-witness design is rewritable without breaking the chain.

**Minimal wiring that WOULD close both holes with one witness** (four changes, all small):
1. `audit.LogQ(ctx, tx, entry)` — tx-admitting variant; call it from `phase` gate-resolution/override paths (which are already in-tx) and from `dispatch.UpdateStatus` (move the recorder call inside the tx, fixing the false doc comment at dispatch.go:236-237).
2. Chain scope = run (session_id := run_id) with sequence allocation inside the write tx (SELECT MAX(sequence_num)+1 ... INSERT under the same tx), making forks impossible rather than detectable.
3. Checksum policy v2 that includes trace_id (versioned chain: entries carry a policy_version; verifier branches on it).
4. Add EventTypes `gate_resolution` and `dispatch_transition`.

## Top 2 findings

1. **P1 — Replay certifies the curve with holes** (run_replay.go:79-107 + reconstruct.go:36): the 15/16 gap is known, but replay's unconditional exit-0 certification converts missing instrumentation into a false certificate that recovery and reexecute gating will trust; it also silently drops coordination events from the certified timeline. This is the finding where the record's *consumer* is the bug, not just the record.
2. **P1 — Audit chain false-tamper fork** (audit.go:81-127): the proposed one-witness remedy for the traceless-weakening holes, wired naively, manufactures tamper alarms on honest firings and thereby devalues the only tamper signal the system would have — the witness corrupting every later decision that trusts the record, which is the fused lens's core scenario verbatim.

## REMEDIATION

Make witnesses tx-internal and completeness-checkable: (1) add `audit.LogQ(ctx, tx, …)` and move dispatch/gate witness writes inside their existing transition transactions, with run-scoped chains and tx-allocated sequence numbers; (2) teach `ic run replay` to cross-check terminal `dispatches` rows against the event stream and encode sparsity in its output contract and exit code; (3) give coordination events a real cursor in `ic events tail` and emit buffered `.expired` events from the Reserve inline sweep; (4) replace ClearLocks' DELETE with a classified tombstone UPDATE (`force_unlocked` + prior-phase/idle evidence) written by the same statement that ends the lock.

## Verification commands run

- Full reads: internal/dispatch/dispatch.go, internal/coordination/store.go, internal/event/store.go, internal/audit/audit.go, internal/replay/reconstruct.go, internal/publish/state.go, cmd/ic/{dispatch,gate,coordination,events,publish,run_replay,run_lifecycle,scheduler_cmd}.go, internal/scheduler/{scheduler,store}.go
- `grep dispatch.New(` across cmd/ic — 16 call sites, 15 nil recorder (only run_lifecycle.go:137 wired), confirming f-039 arithmetic
- `grep internal/audit` tree-wide — zero imports (V4 re-confirmed); audit_log present in schema.sql:366 + migrations 020/023
- `grep ListEvents\(|ListAllEvents\(` — all consumers; coordination cursor hardcoded 0 at events.go:126,128
- `grep reaper|stall` — no reaper/stall-detector exists yet (f-158 obligations are design-time, not retrofit)
