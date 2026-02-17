---
module: interkasten
date: 2026-02-16
problem_type: data_integrity_pattern
component: sync/engine
symptoms:
  - "Conflict resolution writes to filesystem without crash recovery"
  - "Process crash between writeFileSync and updateEntityAfterSync causes merge drift"
  - "Next pull re-detects stale conflict, creating infinite merge loop"
root_cause: wal_bypass
resolution_type: pattern
severity: high
tags: [wal, crash-recovery, write-ahead-log, conflict-resolution, data-integrity, typescript]
---

# WAL Protocol Completeness: Every Write Path Needs Protection

## Problem

The interkasten sync engine uses a Write-Ahead Log (WAL) protocol for crash recovery. The clean pull path correctly followed the WAL sequence, but conflict resolution (`handleConflict()`) wrote directly to the filesystem without WAL protection.

If the process crashed between `writeFileSync` and `updateEntityAfterSync`, the local file had merged content but the database still had stale hashes. On restart, the next poll would detect a false conflict and re-merge, potentially creating merge drift.

## Anti-Pattern

```typescript
// Clean pull — correctly uses WAL
async executePull() {
  const walEntry = walCreatePending(this.db, { ... });
  writeFileSync(entity.localPath, content, "utf-8");
  walMarkTargetWritten(this.db, walEntry.id);
  updateEntityAfterSync(this.db, entity.id, { ... });
  walMarkCommitted(this.db, walEntry.id);
  walDelete(this.db, walEntry.id);
}

// Conflict resolution — MISSING WAL
async handleConflict() {
  writeFileSync(entity.localPath, mergedWithFm, "utf-8");  // Unprotected!
  updateEntityAfterSync(this.db, entity.id, { ... });
  await this.pushUpdate(...);  // Side effect
}
```

## Correct Pattern

```typescript
async handleConflict() {
  // WAL-protected local write
  const walEntry = walCreatePending(this.db, {
    entityMapId: entity.id,
    operation: "merge",
    newContent: result.merged,
  });

  writeFileSync(entity.localPath, mergedWithFm, "utf-8");
  walMarkTargetWritten(this.db, walEntry.id);

  updateEntityAfterSync(this.db, entity.id, { ... });
  walMarkCommitted(this.db, walEntry.id);

  // Side effect BEFORE WAL delete — if push fails, WAL entry survives for retry
  await this.pushUpdate(entity.id, entity.notionId, result.merged, notionHash);

  walDelete(this.db, walEntry.id);  // Only after all effects complete
}
```

## Key Insight: WAL Delete Placement

The WAL delete must happen **after** all compensating side effects (like pushing merged content to Notion), not just after the local write is committed. This is because:

1. If Notion push fails after WAL delete, there's no record that the push is pending
2. On restart, the entity looks fully synced but Notion has stale content
3. This creates a silent divergence that only surfaces when someone reads the Notion page

**Rule: WAL entry lifetime = first mutation → last side effect.**

## General Rule

When a system uses WAL/journaling for crash recovery, **every write path** must participate — not just the "happy path." Common places where WAL gets skipped:

- Conflict resolution handlers (added later, copy-pasted without WAL)
- Error recovery paths (ironically, the recovery code lacks its own recovery)
- Migration/upgrade paths (one-time writes assumed safe)
- Cleanup/GC paths (deletion without journaling)

Audit technique: grep for all `writeFileSync` / `fs.write` / `UPDATE` calls and verify each one has a corresponding WAL entry.

## Cross-Reference

- WAL protocol documented in `CLAUDE.md` key patterns section
- Conflict resolution strategy types in `server/src/sync/merge.ts`
- See also: `docs/solutions/patterns/guard-fallthrough-null-validation-20260216.md` (same sprint, same review)
