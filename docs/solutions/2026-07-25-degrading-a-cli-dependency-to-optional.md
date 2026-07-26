---
artifact_type: solution
goal: a5e8bd5c
stage: compound
category: resilience
tags: [cli-wrapper, fallback, capability-vs-backend, health-checks, api-design, testing, alwe, cass]
---

# Finishing the job: degrading *every* capability, not just the easy ones

Companion to
[`2026-07-24-cli-dependency-as-optional-accelerator.md`](2026-07-24-cli-dependency-as-optional-accelerator.md),
which covered making a CLI dependency optional for the capabilities that mapped
cleanly onto a local index. This one covers the leftovers — and the API and
health-model consequences of actually finishing.

Solved 2026-07-25 under goal `a5e8bd5c` in `os/Alwe`.

## The trap: "optional dependency" that is only 60% optional

The first pass gave `search` and `context_for_file` a local fallback and declared
cass optional. Two of five tools (`timeline`, `export_session`) still returned
"requires cass, which is not available". That is worse than an honest hard
dependency, because the *claim* is that the tool degrades gracefully while a
third of it doesn't.

If you are going to call a dependency optional, enumerate every capability and
check each one. The residual is the deliverable, not a footnote.

## Pattern: derive the leftovers from what you already store

Neither leftover needed new storage.

**Activity windows from file mtime.** The obvious implementation filters on
message timestamps. Resist it if they are stored as text: lexicographic RFC3339
comparison breaks for producers emitting offsets rather than `Z`, and adding a
numeric column to an FTS5 table means recreating it — a full reindex. File mtime
is already numeric, already indexed, and is often the *more* honest signal: an
append-only log is only written while its producer runs.

```sql
-- window on mtime (indexed), then per-file detail by rowid range
SELECT path, messages, mtime_ms, rowid_lo, rowid_hi
  FROM files WHERE mtime_ms >= :cutoff ORDER BY mtime_ms DESC;
SELECT MIN(ts), MAX(ts) FROM messages WHERE rowid BETWEEN :lo AND :hi;
```

**Rendering from the source file, with no index at all.** Export is a pure
function of the transcript. Making it a method on the index would read as
consistent with its neighbours and would be wrong: it would mean a source file
indexed thirty seconds from now cannot be rendered today, reintroducing the
freshness gap the local path exists to close.

```go
// Package-level on purpose: needs the file, not the catalog.
func ExportMarkdown(path string) (string, error)
```

Pin it with a test that nils out the index:

```go
svc.local = nil
md, err := svc.ExportSession(ctx, path)   // must still work
```

**Generalisation:** when a new function's natural signature differs from its
neighbours', check whether the difference is the point before smoothing it out.

## Pattern: `degraded` means capability lost, not backend missing

Once either backend alone can serve every capability, "a backend is missing"
stops being a degradation. Model the two separately:

```go
type Health struct {
	Healthy        bool   // at least one backend can answer
	Degraded       bool   // a capability is unavailable  → only when none can
	ReducedRanking bool   // answers come from the weaker backend
	Notice         string // one line, for humans and agents
}
```

Two rules learned the hard way:

- **Keep the old signal under a new name.** `Degraded` previously carried "you
  are getting weaker results". Redefining it without adding `ReducedRanking`
  would have silently dropped real information.
- **A redefinition is a user-visible change, not a bug fix.** Anything gating on
  `degraded` now sees `false` where it saw `true`. Say so in the report.

## Pattern: delete the bool that cannot tell the truth

The old probe was:

```go
func (o *CassObserver) IsAvailable(ctx context.Context) bool   // deleted
```

It was wrong twice over: it collapsed "reachable" and "self-reports healthy" into
one bit, and it probed at the CLI's strict default staleness threshold, so on a
longer indexing cadence it returned `false` for most of every cycle while the CLI
answered every query fine.

Deleting it beat deprecating it — nothing outside the module imported the
package, and a helper that returns a plausible-but-wrong bool is a footgun for
the next caller. Leave a comment where it was explaining why there is no such
helper, and carry its regression coverage onto the surviving path rather than
dropping the test.

```go
// There is deliberately no IsAvailable helper. A single bool cannot express the
// backend's state without lying: it reports itself unhealthy when its index is
// merely stale, while still answering every query.
```

## Testing: real data catches what fixtures assume away

Added `realdata_test.go` asserting against actual files on disk:

- the local index's line numbers are true file lines (checked against the raw
  file, on real hits);
- snippets shaped like the other backend's resolve to the same line;
- rendering survives real-world shapes — nested reasoning blocks, multi-MB tool
  results, truncated final lines from crashed sessions.

Skip rather than fail when no real data is present, so CI stays green — but
record in the project's agent-facing doc that these are load-bearing, because
tests that skip are easy to delete by accident.

## Traps

- **Measure the measurement.** An exit-code check loop mis-captured `$?` and
  reported three spurious failures; the commands were fine. Before believing a
  surprising result, verify the harness.
- **Verify the claim, not just the acceptance conditions.** The conditions stubbed
  the CLI to a retryable error exit. Removing it from `PATH` entirely was the
  stronger check, cost one command, and is what the goal actually claimed.

## See also

- `os/Alwe/docs/charter-local-session-index.md`
- `os/Alwe/docs/reflection-a5e8bd5c.md`
- Predecessor solution: `2026-07-24-cli-dependency-as-optional-accelerator.md`
