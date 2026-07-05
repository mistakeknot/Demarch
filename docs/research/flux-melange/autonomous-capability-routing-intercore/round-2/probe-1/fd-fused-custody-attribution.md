# FUSED Review: fd-fused-custody-attribution (round 2, probe 1)

**Lens:** fd-eval-calibration-metrics × fd-assay-hallmark
**Target:** docs/brainstorms/2026-07-05-autonomous-capability-routing-intercore.md
**North star:** maximize verified novelty×risk surface until dry
**Constraint:** intersection-only — every finding requires BOTH parent lenses; excludes f-034, f-035, f-036, f-010, f-008.

## Findings Index

- [P1] Orphaned BLAKE3 custody hash: CXDB already computes and stores a content hash at `set-artifact` time, but nothing in Phase 3/4's design reads it back — the plan re-derives a *weaker*, unhashed custody model from scratch
- [P2] `session_source` witness classifier (bootstrap/self-building/normal, existing B3 weighting) has no analog in Phase 4's `plan_execution_outcome` — pilot-era plan-pass-rate rows will silently pool at full statistical weight alongside mature-era rows once autonomy widens

## Findings

### [P1] Orphaned BLAKE3 custody hash makes Phase 3's "sealed artifact" weaker than the codebase's own existing precedent

**Where:** `os/Clavain/cmd/clavain-cli/phase.go:339-381` (`cmdSetArtifact`), `os/Clavain/cmd/clavain-cli/cxdb_client.go:350-380` (`cxdbRecordArtifact`), vs. plan Phase 3 (brainstorm lines 60-64, "Criteria stored as a run artifact (`set-artifact acceptance-criteria`)").

**What:** `cmdSetArtifact` already computes a real content hash (`blake3.Sum256(data)`) and writes it into CXDB as `ArtifactRecord.BlobHash` (`cxdb_client.go:360-375`) whenever any artifact — including the acceptance-criteria file Phase 3 proposes — is registered via `set-artifact`. This is a genuine custody primitive: a sealed, content-addressed witness of what the criteria said at seal time. But the write path is fail-open at every step (`cxdbEnsureRunning()` returns silently if CXDB isn't up, `os.ReadFile` errors are swallowed, `cxdbConnect()` errors return silently) and — checked across the entire `clavain-cli` package — `BlobHash`/`ArtifactRecord` is **never read back** anywhere; it is write-only telemetry. Phase 3/4 don't reference it at all: the plan's own custody design ("criteria stored as a run artifact," a plan-conformance verdict, `plan_execution_outcome` counts) reinvents a *second*, hash-less sealing story for the exact same artifact instead of reconciling against the hash that's already silently being computed next to it.

**Evidence:**
```go
// cxdb_client.go:355-361
data, err := os.ReadFile(path)
if err != nil {
    return // File doesn't exist yet — skip silently
}
hash := blake3.Sum256(data)
```
`grep -rn "BlobHash\|ArtifactRecord" os/Clavain/cmd/clavain-cli/*.go` shows only write sites (`cxdb_client.go:158,375`) and a marshal round-trip unit test (`cxdb_client_test.go`) — zero read/compare call sites in production code.

**Intersection justification:** The custody parent alone would say "seal the criteria artifact" (f-034) — satisfied on paper, since `set-artifact` already exists and a hash is already computed. The measurement parent alone would say "bind a version/hash into each outcome row" (this is the P0 example in the charter, but framed abstractly). Neither parent alone catches that a *working hash-computation mechanism already exists in this exact codepath* and is orphaned — the custody lens sees "hash computed, looks sealed" and stops; the measurement lens sees "no hash in the outcome schema" as an abstract gap to design from zero. Only holding both together reveals that this isn't a gap to fill with new design, it's a **reconciliation bug**: an existing, already-computed custody witness (BlobHash) is sitting one file away from the exact measurement surface (plan_execution_outcome) that needs it, and the plan's authors evidently didn't grep for it before proposing a fresh mechanism. An independent witness would need to reconcile `ArtifactRecord.BlobHash` (captured at seal time) == a hash recomputed from the criteria artifact read at validation time, surfaced as a field on `plan_execution_outcome`.

**Suggestion:** Phase 3 acceptance criteria should add: "the plan-conformance validator dispatch reads the criteria artifact's current content hash and includes it in the outcome record; `/interspect:calibrate` treats a hash mismatch as an automatic exclusion from the pass-rate sample (not silently poolable)." One field addition (`criteria_blob_hash` on `plan_execution_outcome`) plus a read-back call to CXDB's existing `ArtifactRecord` lookup — not new hashing infrastructure.

**Verdict:** NEEDS_ATTENTION

---

### [P2] The B3 witness classifier that already exists for per-agent evidence has no counterpart for plan-pass-rate evidence

**Where:** `interverse/interspect/hooks/lib-interspect.sh:3049` (`_interspect_classify_session_source`), `:3574-3580` (weighted hit-rate using `source_weight`), vs. plan Phase 4 (brainstorm lines 66-71, `plan_execution_outcome` → `/interspect:calibrate` aggregation) and Rule 6 (pilot 2-3 items).

**What:** The existing B3 calibration path already has a custody-grade answer to "is this evidence trustworthy to count at full weight": `_interspect_classify_session_source` tags every session as `bootstrap` (0.5x weight), `self-building` (0.7x weight), or `normal` (1.0x weight), and `score_subset` (`lib-interspect.sh:3574`) uses those weights when computing `weighted_hit_rate` — specifically so that evidence generated while the system was still calibrating itself doesn't get pooled at the same trust level as steady-state evidence. Phase 4's `plan_execution_outcome` design has no mention of tagging pilot-era rows (Rule 6's 2-3 item pilot) with an analogous source class. This is distinct from f-008 (pilot sample size is too small to be statistically meaningful) — the finding here is that a *witness/weighting mechanism for exactly this problem already exists in the codebase* for a sibling evidence stream, and Phase 4 doesn't reuse or extend it, so once the pilot "passes" and autonomy widens, the 2-3 pilot outcomes and the post-widening outcomes get pooled at identical weight in the same `(author_tier, executor_tier)` cell with no custody marker distinguishing "trust-establishing rehearsal" from "steady-state operation."

**Evidence:**
```bash
# lib-interspect.sh:3046-3049
# Bootstrap sessions get 0.5x weight, self-building 0.7x, normal 1.0x.
_interspect_classify_session_source() {
```
No `plan_execution_outcome`-side equivalent exists anywhere in the plan or in current interspect schema (`grep -n "plan_execution_outcome" interverse/interspect/hooks/lib-interspect.sh` returns zero hits — the evidence type doesn't exist yet, confirming this is a from-scratch design that skipped precedent).

**Intersection justification:** The measurement parent alone owns "is the pilot big enough" (f-008) — a sample-size question, already excluded. The custody parent alone would ask "was the pilot properly witnessed as a rehearsal" in the abstract (the charter's own finding #4, "pilot as custody rehearsal"). Neither alone surfaces that this project **already built and shipped** the exact fix (weighted-by-provenance aggregation) for the sibling per-agent metric, and Phase 4 is free-designing a parallel metric without wiring to it. That's only visible by tracing one concrete mechanism (`_interspect_classify_session_source` / `source_weight`) from its role in the existing trust graph (which sessions get discounted and why) into its absence from the new measurement graph (plan-pass-rate has no such discount) — a reuse-of-precedent gap that only shows up at the intersection of "what custody machinery already exists" and "what the new statistic is missing."

**Suggestion:** Phase 4 acceptance criteria should add: tag each `plan_execution_outcome` row with the same `session_source` classification already computed for its session (reuse `_interspect_classify_session_source`, don't reinvent), and have `/interspect:calibrate`'s plan-pass-rate aggregation apply the existing `source_weight` table so pilot-era rows are discounted rather than silently promoted to full trust once the 2-3-item gate closes.

**Verdict:** NEEDS_ATTENTION
