# probe-2 verdict — minimal durable-consumer contract for `ic events`

Lens: fd-kernel-contract. Cluster: event-delivery-at-most-once (f-018, f-071). Builds on settled f-039/f-040 (nil recorders, post-commit fire-and-forget).

## Key discovery: the contract is already written — in the wrong place

`core/intercore/docs/product/intercore-vision.md:336-349` already specifies the correct
contract: read-only `tail`, explicit `ic events cursor set` after processing, durable vs
ephemeral cursors, `ic events prune --older-than` with durable-cursor protection, stable
per-source event IDs. The implementation diverges from it on every point (tail auto-advances,
`cursor set` doesn't exist, prune doesn't exist, TTL is 24h not 7d). The fix is therefore
**converge code to vision**, then promote the semantics section into `contracts/events/` where
consumers actually look. No new design needed — this is the minimal contract.

## Delivery semantics (target)

1. **Read-only tail.** `ic events tail` never mutates cursor state. Batch = all events with
   per-source `id > cursor[source]`, per-source sub-limits as today (store.go:106-244).
2. **Explicit ack.** After the consumer durably processes a batch, it calls
   `ic events cursor set <consumer> [--phase=N] [--dispatch=N] [--discovery=N] [--review=N]`.
   Only named sources advance; unset sources keep their position. Ack = cursor advance; there is
   no per-event ack (per-source high-water mark is sufficient because ids are per-source monotonic).
3. **At-least-once.** Crash between read and ack → same events re-emitted on next poll.
   Consumers MUST be idempotent. Document this in contracts/events/README.md.
4. **Replay on reconnect.** Existing `--since-phase/--since-dispatch/--since-discovery/--since-review`
   flags already provide replay; add the guard that explicit `--since-*` combined with `--consumer`
   never saves the cursor (closes events.go:115-117 footgun) or reject the combination with exit 3.
5. **TTL.** Ephemeral cursors: 7 days (align code to vision, events.go:268,753 — or align vision to
   24h, but pick one and document it in contracts/events/README.md). Durable (`register --durable`):
   no expiry. `cursor set` preserves the registered durability (existing `cursorTTL` behavior).
6. **Pruning.** `ic events prune --older-than=<duration>`: delete rows where
   `created_at < cutoff AND id < MIN(durable cursor per source)` per event table; ephemeral cursors
   do not block pruning (vision:343-345). Refuse nothing — just never delete ahead of a durable cursor.
   No daemon; OS schedules it.

## Command-surface changes (minimal, no new subsystems)

- `ic events cursor set <consumer> [--phase=N] [--dispatch=N] [--discovery=N] [--review=N]` — NEW
  (the vision-doc'd ack verb; ~40 lines in events.go using existing state store).
- `ic events tail` — drop the implicit save at events.go:157-160; add `--auto-advance` legacy flag
  for one release so existing scripts (Clavain test bats, bigend-style one-shot tails) don't break
  silently. Emit a stderr deprecation note when `--auto-advance` is used.
- `ic events prune --older-than=<duration> [--dry-run]` — NEW. `--dry-run` prints per-table row
  counts and the blocking durable cursor, which doubles as the "consumer lag monitoring" hook the
  vision doc asks operators to watch.
- `ic events cursor list` — already exists; document output format in contracts README.

## Contract-doc edits

- NEW `contracts/events/delivery.md` (hand-written, sits beside generated schemas): delivery
  guarantee (at-least-once, consumer idempotency REQUIRED), composite per-source cursor shape and
  why (no global sequence; `created_at` is second-resolution, never a cursor), TTL values,
  prune protection rule, replay recipe (`tail --since-*` without `--consumer`).
- `contracts/events/README.md`: link delivery.md; add the cursor payload JSON shape as a documented
  type; fix the "Key consumers" table to note interspect consumes via ack-based cursor.
- `docs/product/intercore-vision.md:343`: reconcile TTL number with code (one sentence).

## Migration path for the existing cursor store

No schema migration. Cursors are JSON blobs in the `state` table (key=`cursor`); the 5-tuple
payload shape is unchanged, and `cursor set` writes the same shape via the same `state.Set`.
Behavioral migration only:

1. Ship `cursor set` + `--auto-advance` (default ON with deprecation warning) in release N.
2. Migrate the one live consumer (lib-interspect.sh, below) to read → process → `cursor set`.
3. Release N+1: flip default to read-only (`--auto-advance` becomes no-op kept for compat).
Existing registered cursors (incl. `interspect-consumer --durable`, registered at
lib-interspect.sh:170-171,347-348) keep their positions throughout.

## Dependency ordering vs f-039/f-040 (recorder gaps)

Independent code paths, but the guarantee is only as strong as the stream:

1. **First: f-039/f-040 recorder wiring.** With 15/16 `dispatch.New` sites passing nil recorders,
   `dispatch_events` only receives rows from `ic run advance` — a replay-capable consumer still
   misses every spawn/poll/wait/kill/retry transition, no matter how good the delivery semantics.
   The one wired recorder fires post-commit fire-and-forget with errors swallowed at Debug, so even
   it can silently skip. Fixing delivery first would harden delivery of a stream with holes and
   could falsely certify completeness.
2. **Then: this contract** (read-only tail + cursor set + prune).
3. **Consumer idempotency can land in parallel** (it's in interverse, disjoint repo path).
Prune protection depends on nothing above and can ship any time after `cursor set`.

## Consumer compatibility (lib-interspect.sh)

**Not at-least-once-safe as written.** `_interspect_insert_evidence` is a plain INSERT and
`idx_evidence_source_event_id` is non-unique (lib-interspect.sh:206,3090) — replay duplicates
evidence rows. The fix is small because the dedup key already exists conceptually:

- `CREATE UNIQUE INDEX ... ON evidence(source_event_id, source_table) WHERE source_event_id IS NOT NULL`
  + `INSERT OR IGNORE` in `_interspect_insert_evidence` (dedupe on kernel event id + source table).
- Restructure `_interspect_consume_kernel_events` (lib-interspect.sh:2532-2582): read without
  consumer-side advance, track per-source max id in the loop, then one
  `ic events cursor set interspect-consumer --phase=N --dispatch=N ...` after the loop.
  The per-event `|| true` tolerance becomes safe (replayed next poll) instead of lossy.
- Same pattern for `_interspect_process_disagreement_event` (review events cursor).
The review-event consumer path (`_interspect_consume_review_events`) should get the same
unique-key treatment on its evidence inserts.

## REMEDIATION

Warranted. File one remediation bead (or three linked):

1. intercore: implement `ic events cursor set`, read-only `tail` with `--auto-advance` legacy flag,
   `--since-*`+`--consumer` guard, TTL reconciliation; add cursor-advance and replay tests
   (events_test.go currently has none — f-071 evidence).
2. intercore: implement `ic events prune --older-than [--dry-run]` with durable-cursor floor;
   write `contracts/events/delivery.md`; update contracts README + vision TTL line.
3. interverse/interspect: unique dedup index + `INSERT OR IGNORE` in `_interspect_insert_evidence`,
   restructure `_interspect_consume_kernel_events` to explicit ack.
Sequenced after the f-039/f-040 recorder-wiring remediation.
