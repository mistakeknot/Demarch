# probe-2 findings — fd-kernel-contract: event-delivery-at-most-once (f-018 fix contract)

SEVERITY | lens | path:line | finding [t]

P1 | fd-kernel-contract | core/intercore/cmd/ic/events.go:157-160 | cursor persisted per batch after stdout encode, before consumer processing; sole production consumer (interverse/interspect/hooks/lib-interspect.sh:2541-2575) crashes or skips between `ic events tail` exit and `_interspect_insert_evidence` → whole batch silently dropped — at-most-once-on-crash [t]

P1 | fd-kernel-contract | core/intercore/docs/product/intercore-vision.md:338 | vision specifies the opposite contract: "`ic events tail` is a read-only operation — it does not advance the cursor. The consumer must explicitly advance its cursor after processing events by calling `ic events cursor set <consumer> <event_id>`" — neither the read-only behavior nor the `cursor set` subcommand exists (cursor subcommands: list, reset, register only; events.go:182-192). Implementation contradicts its own vision doc, and the vision doc already contains the correct fix [t]

P1 | fd-kernel-contract | core/intercore/cmd/ic/events.go:158 | silent per-event loss without any crash: the consumer loop tolerates per-event insert failures with `|| true` (lib-interspect.sh:2574) and skips lines failing jq parse (lib-interspect.sh:2548-2556), but the cursor for those events was already advanced by the tail process before the loop ran — error tolerance in the consumer becomes permanent data loss [t]

P2 | fd-kernel-contract | core/intercore/cmd/ic/events.go:268,753 | ephemeral cursor TTL is 24h in code but 7 days in the vision doc (intercore-vision.md:343); neither value appears in contracts/events/README.md — TTL is an undocumented API parameter that silently resets consumers to `0,0,0,0,0` (loadCursor error path, events.go:717-731), replaying from event zero on next poll [t]

P2 | fd-kernel-contract | core/intercore/cmd/ic/events.go:115-117 | mixing manual `--since-*` replay flags with `--consumer` does not load the cursor but STILL saves it (events.go:158) — a manual historical replay silently rewrites the consumer's high-water mark; no guard [t]

P2 | fd-kernel-contract | core/intercore/docs/product/intercore-vision.md:345 | vision promises `ic events prune --older-than=<duration>` with the guarantee "no event is pruned while any durable consumer's cursor still points before it" — no prune subcommand exists, so durable-consumer registration currently buys no protection and event tables grow unbounded [t]

P2 | fd-kernel-contract | core/intercore/internal/event/store.go:106-244 | no global monotonic event sequence: cursor is a composite 5-tuple over per-table AUTOINCREMENT ids; `created_at` is unixepoch seconds (tie-prone, unusable as cursor). Contracts README documents sources but never documents the composite-cursor shape as API — consumers must infer it from the cursor JSON payload [t]

P2 | fd-kernel-contract | interverse/interspect/hooks/lib-interspect.sh:111,206 | `idx_evidence_source_event_id` is a NON-UNIQUE index and `_interspect_insert_evidence` (lib-interspect.sh:3090) is a plain INSERT — the consumer is not idempotent; switching to at-least-once (replay-capable) delivery today would duplicate evidence rows on every replay [t]

P3 | fd-kernel-contract | core/intercore/cmd/ic/events.go:712-733 | `loadCursor` swallows both "cursor missing" and "cursor JSON corrupt" into the same `0,0,0,0,0` result — a corrupt cursor silently triggers full replay from event zero instead of an error [t]

P3 | fd-kernel-contract | core/intercore/cmd/ic/events.go:143-154 | `sinceInterspect` is loaded and saved (events.go:116,159) but never advanced and never used in any query — dead cursor slot carried in the persisted payload; harmless but documents that the 5-tuple cursor shape was designed for sources that never joined the UNION [t]
