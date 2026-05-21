---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-13-github-file-sync-brainstorm.md"
target_description: "GitHub bidirectional file sync — path-based correlation, hybrid push+poll, Git Contents API"
tracks: 2
track_a_agents: [fd-git-api-concurrency, fd-webhook-delivery-reliability, fd-three-way-merge-correctness, fd-filesync-reconciliation-coverage, fd-sync-scope-safety]
track_c_agents: [fd-double-entry-bookkeeping-reconciliation, fd-polynesian-wayfinding-reconciliation, fd-qanat-water-distribution, fd-tatami-modular-fitting, fd-scribal-collation-stemmatic]
date: 2026-04-13
bead: sylveste-911m
---

# Flux-Review Synthesis: GitHub Bidirectional File Sync

## Critical Findings (P0/P1)

### P0-1: EntityKey namespace mismatch breaks collision detection (Track A)

The filesystem adapter emits `fs:file:docs/README.md` while GitHub filesync emits `github:file:owner/repo:docs/README.md`. CollisionWindow compares raw EntityKey strings — these never match, so opposing events dispatch freely in an infinite ping-pong loop. The `entity_correlation` table from Task 1.2 does not exist in the codebase.

**Fix:** Implement entity correlation before filesync. CollisionWindow must resolve correlated keys before comparison.

### P0-2: AncestorStore destructive upsert destroys merge base (Track A + Track C convergent)

`ancestor/store.go:81-91` uses `INSERT ... ON CONFLICT DO UPDATE SET`, overwriting prior ancestor records. The double-entry bookkeeping agent (giornale must be append-only) and scribal collation agent (compounding archetype corruption) both independently identified this. A failed half-posted sync uses a corrupted ancestor for all future merges.

**Fix:** Add `generation` counter column; keep last 3 ancestor records per entity.

### P0-3: Null-ancestor first-sync dead-letters all pre-existing file pairs (Track A + Track C convergent)

`conflict/resolver.go:85-109` — when no AncestorStore record exists for a file present on both sides, `ResolveThreeWay` returns `ErrUnresolvable` for every file. Users pointing interop at repos where local docs/ already mirrors GitHub docs/ find the feature immediately unusable. The qanat agent (no water deed for pre-existing users) and three-way-merge agent both surfaced this.

**Fix:** Bootstrap protocol — when first sync detects a file on both sides with no ancestor, treat one side as synthetic ancestor or surface as explicit first-sync conflict.

### P0-4: Contents API SHA race causes silent data loss (Track A)

PUT endpoint requires current file SHA. On 409 Conflict (concurrent edit), the bus retries with stale SHA, exhausts max retries, dead-letters — the local edit is lost. Rate-limit retry logic (429/403) does not cover 409.

**Fix:** Re-fetch SHA + three-way merge + retry on 409, separate from rate-limit retry path.

### P1-1: Webhook handler must not block on Contents API calls (Track A + Track C convergent)

The current `processWebhookEvent` enqueues to channel (non-blocking). Push events that fetch file contents via API before returning 200 would block the webhook response. GitHub disables endpoints with sustained slow responses. The Polynesian wayfinding agent and webhook-reliability agent both identified this.

**Fix:** Document and enforce: push handler MUST only enqueue to channel. Add test that webhook returns within 100ms.

### P1-2: Out-of-band git operations corrupt ancestor chain (Track C)

Running `git pull` locally advances files to GitHub state. AncestorStore still holds pre-pull ancestor. Next three-way merge uses wrong base — produces silently wrong results. The scribal collation agent identified this as "contamination" (consulting a second exemplar outside the stemmatic chain).

**Fix:** On each sync cycle, verify ancestor hash matches content both sides held at last-confirmed sync. Re-bootstrap on mismatch.

### P1-3: Webhook silence treated as "no changes" (Track A + Track C convergent)

No webhook liveness detection. If endpoint becomes unreachable, system silently degrades to poll-only without alerting. The Polynesian wayfinding agent: clear skies ≠ confirmation of position.

**Fix:** Track `lastWebhookReceived` timestamp; warn if no webhook in >2x poll interval.

### P1-4: Tree-SHA polling scope not bounded (Track C)

Root tree SHA advances on any repo change (CI writes to `out/`, unsynced paths). Reconciliation triggers on every unrelated change, consuming rate limit budget.

**Fix:** Poll per-subtree SHA scoped to `sync_paths`, not root.

### P1-5: Unicode path normalization gap (Track C — tatami fitting)

macOS HFS+ normalizes to NFD; GitHub returns NFC. Same file creates different EntityKeys — phantom duplicate entities.

**Fix:** `normalizePath()` function at EntityKey construction: NFC normalization, forward-slash separators.

## Cross-Track Convergence

Three findings appeared independently in both tracks — the highest-confidence signals:

| Finding | Track A Agent | Track C Agent | Convergence |
|---------|--------------|---------------|-------------|
| AncestorStore destructive upsert | fd-three-way-merge-correctness | fd-double-entry-bookkeeping, fd-scribal-collation | 2/2 |
| Null-ancestor first-sync | fd-three-way-merge-correctness | fd-qanat-water-distribution | 2/2 |
| Webhook liveness gap | fd-webhook-delivery-reliability | fd-polynesian-wayfinding | 2/2 |

The AncestorStore findings are the highest-confidence convergent signal: both the domain expert (merge algorithm specialist) and two independent distant-domain agents (Venetian accounting, medieval philology) identified the same destructive-overwrite failure mode through completely different reasoning paths.

## Structural Insights (Track C)

Each distant-domain agent revealed a distinct architectural gap:

- **Double-entry bookkeeping** (1494 Venetian): AncestorStore as giornale must be append-only; tree-SHA polling as trial balance detects aggregate not entry-level divergence
- **Polynesian wayfinding**: Webhook and poll are heterogeneous detection channels with different reliability profiles — absence of signal ≠ absence of change
- **Persian qanat**: Rate limit budget is shared between read (poll) and write (sync) paths — heavy write burst starves reconciliation reads
- **Tatami fitting**: Path-based identity breaks on rename (delete+create destroys locally-modified file at old path) and on Unicode normalization differences
- **Scribal collation**: Ancestor records produced by prior merges become corrupted archetypes; SyncJournal lacks ancestor content for post-hoc re-evaluation

## Synthesis Assessment

- **Overall quality:** The brainstorm makes sound architectural choices (path-based correlation, hybrid detection, module-in-adapter) but has critical gaps in the entity correlation and ancestor management layers that would cause data loss in production.
- **Highest-leverage improvement:** Implement entity correlation (EntityKey namespace bridging) — this unblocks CollisionWindow, AncestorStore lookup, and self-originated event suppression for cross-adapter file entities. Everything else depends on it.
- **Surprising finding:** The AncestorStore destructive upsert (P0-2) — not visible from a sync-systems perspective, but immediately obvious to both the double-entry bookkeeping agent (ledgers must be append-only) and the philological agent (archetypes degrade across copy generations). This is the kind of finding that justifies distant-track review.
- **Semantic distance value:** The outer track produced 3 findings that the inner track missed entirely (out-of-band ancestor corruption, Unicode normalization, rename-destroys-local-modification) and independently confirmed 3 inner-track findings through different reasoning paths. The distant agents contributed qualitatively different insights — structural mechanisms, not vocabulary substitution.
