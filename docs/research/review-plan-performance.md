# Performance Review: Bigend Dirty Row Tracking Plan
**File reviewed:** `docs/plans/2026-02-23-bigend-dirty-row-tracking.md`
**Reviewed:** 2026-02-23
**Reviewer:** Flux-drive Performance Reviewer

---

## Context and Performance Profile

Bigend is a Bubble Tea TUI dashboard (interactive, not batch). The tick rate is
every 2 seconds (`tea.Tick(2*time.Second, ...)`), which triggers a `Refresh()`
call followed by `updateLists()` and eventually `View()` → `renderDashboard()`.
This is a low-frequency update loop by TUI standards. The user sees the display
change every 2 seconds at most; a key press triggers immediate re-render.

The rendering the plan is trying to skip: 6 lipgloss sections per frame,
spanning at most ~50 items (5 sessions, 5 agents, 10 activities, 10 dispatches).
The dashboard renders on every call to `View()`, which Bubble Tea calls on every
`Update()` return — that includes key presses, tick messages, and resize events.

The optimization has real value at keypress latency (interactive feel) but its
benefit on 2-second ticks is minimal since lipgloss rendering at this scale
takes well under 1 ms. The analysis below focuses on whether the implementation
is correct and whether the overhead it adds is proportional to the benefit.

---

## Findings by Severity

---

### P1 — CORRECTNESS BUG: hashRuns and hashDispatches produce non-deterministic hashes

**Location:** `section_cache.go` lines ~275-307 (plan Task 1, Step 3)

```go
func hashRuns(kernel *aggregator.KernelState, width int) uint64 {
    h := fnv.New64a()
    // ...
    for proj, runs := range kernel.Runs {   // map iteration — non-deterministic order
        h.Write([]byte(proj))
        for _, r := range runs {
            h.Write([]byte(r.ID))
```

```go
func hashDispatches(kernel *aggregator.KernelState, width int) uint64 {
    // ...
    for proj, dispatches := range kernel.Dispatches {  // same problem
```

The plan's own notes section acknowledges this: "Go map iteration is
non-deterministic, but this is fine — the hash will still be consistent within
a single View() call because GetState() returns the same snapshot. Between
ticks, if the map order changes but the data hasn't, we get a cache miss (false
negative) which just costs one extra render — acceptable."

This analysis is wrong. The consequence is not just one extra render per data
change — it is a cache miss on *every single tick where the map happens to
iterate in a different order*, even with no data change at all. On a 2-second
tick loop with 5+ projects in `kernel.Runs`, Go's map randomization will cause
hash churn on most frames for the Runs and Dispatches sections specifically.
This eliminates the cache hit rate for those two sections entirely, meaning the
advertised 90% skip rate is only achievable for the sessions/agents/activity
sections, not for the kernel-heavy use case that is the primary motivation for
this optimization (kernel-connected = busier dashboard = more dispatches/runs).

**Fix:** Sort the keys before iterating, or build a sorted slice of (key,
value) pairs first. This is a one-liner per function:

```go
// Collect and sort project keys
projKeys := make([]string, 0, len(kernel.Runs))
for proj := range kernel.Runs {
    projKeys = append(projKeys, proj)
}
sort.Strings(projKeys)
for _, proj := range projKeys {
    runs := kernel.Runs[proj]
    // hash as before
}
```

The sort is O(p log p) where p is the number of projects — bounded at tens of
items, not thousands. This is cheaper than the lipgloss render it avoids.

---

### P2 — ALLOCATION OVERHEAD: Six fnv.New64a() + six make([]byte, 8) per View() call

**Location:** `section_cache.go`, all six hash functions

```go
func hashStats(state aggregator.State, width int) uint64 {
    h := fnv.New64a()           // heap allocation
    b := make([]byte, 8)        // heap allocation
```

This pattern repeats in all six hash functions. Each `View()` call on the
dashboard tab allocates 6 hashers and 6 byte slices. FNV-64a hashers from
`hash/fnv` are small structs allocated on the heap because they implement the
`hash.Hash64` interface (interface dispatch prevents stack allocation). The
`[]byte` slices are also heap-allocated.

At 2-second tick intervals this is negligible. However, Bubble Tea calls
`View()` on every key press and every message type, not just on data ticks.
For key navigation, hover, filter typing, and overlay toggles, `renderDashboard`
is not called if the active tab is not `TabDashboard` — but when it is,
interactive key rate could be 10-30 calls per second if the user is typing.
At that rate the 12 allocations per frame are still not a problem (a few hundred
bytes, trivially GC'd), but the plan should not claim this is zero-cost.

**More important:** the `[]byte` buffer re-use within each function is fine
(the same `b` is reused for all `PutUint64` calls within one function), but
there is no sharing across functions. If this becomes a measured concern, a
`sync.Pool` of `[8]byte` + hasher pairs eliminates the GC pressure. But this
is not warranted now.

**Verdict:** Acceptable at current tick frequency and item counts. Not worth
optimizing pre-measurement. The plan's claim that this overhead is "acceptable"
is correct — but only because the baseline rendering cost is also low, not
because the hash overhead is zero.

---

### P2 — REDUNDANT WORK: hashStats iterates state.Sessions twice for activeCount

**Location:** `section_cache.go` lines ~233-239, and `renderDashboard.go`
`renderStatsRow()` lines ~564-571 (existing code reproduced in plan)

```go
// In hashStats:
var activeCount int
for _, s := range state.Sessions {
    if s.UnifiedState == icdata.StatusActive || s.UnifiedState == icdata.StatusWaiting {
        activeCount++
    }
}

// In renderStatsRow (when no kernel):
activeCount := 0
for _, s := range state.Sessions {
    if s.UnifiedState == icdata.StatusActive || s.UnifiedState == icdata.StatusWaiting {
        activeCount++
    }
}
```

The hash function reproduces the exact computation that the render function
already does. When the cache misses (data has changed), both loops run. This
is a minor issue given the 5-session limit shown in the dashboard, but it
represents a structural defect in the design: the hash functions encode
*rendering logic* (the exact aggregation formula) rather than *data identity*.

This matters for a correctness reason too: if `renderStatsRow` changes its
aggregation logic (e.g., starts counting `StatusBlocked` as active), the hash
function will not automatically track that change and will produce false cache
hits showing stale data.

**Better approach:** The hash functions should ideally hash *raw data fields*
that the renderer reads, not pre-aggregate them. The `activeCount` computation
in `hashStats` should be removed; instead hash each session's `UnifiedState`
field. The hash will then capture any status change regardless of how the
renderer uses it.

However, note that `hashSessions` already hashes `UnifiedState` per session
(in `sectionSessions`). The stats hash is a *different* section key
(`sectionStats`) that only hashes counts and aggregates, not individual session
states. This means: a session can change from `StatusIdle` to `StatusWaiting`
and `hashStats` will correctly detect it (activeCount changes), but if two
sessions swap statuses with no net activeCount change, `hashStats` misses the
change while `hashSessions` catches it. That is acceptable — the stats section
only shows counts.

**Verdict:** The logic duplication is a maintenance hazard but not a
correctness bug for the current renderer. The cost at 5 sessions is a few
nanoseconds. Flag for code review but not a blocker.

---

### P3 — MINOR: sectionCache uses map[sectionID]sectionEntry for 6 fixed entries

**Location:** `section_cache.go`

```go
type sectionCache struct {
    entries map[sectionID]sectionEntry
}

func newSectionCache() *sectionCache {
    return &sectionCache{entries: make(map[sectionID]sectionEntry, 6)}
}
```

With exactly 6 known sections (sectionStats=0 through sectionActivity=5), a
fixed-size array would be more cache-friendly and eliminate the map overhead:

```go
const numSections = 6

type sectionCache struct {
    entries  [numSections]sectionEntry
    valid    [numSections]bool
}

func (c *sectionCache) getOrRender(id sectionID, hash uint64, renderFn func() string) string {
    if c.valid[id] && c.entries[id].hash == hash {
        return c.entries[id].rendered
    }
    s := renderFn()
    c.entries[id] = sectionEntry{rendered: s, hash: hash}
    c.valid[id] = true
    return s
}

func (c *sectionCache) invalidateAll() {
    c.valid = [numSections]bool{}
}
```

This removes: map hashing on lookup, map bucket traversal, interface
indirection on the key, and the need to iterate the map for invalidation. The
`invalidateAll()` in the current plan uses a `for range delete` loop, which
is itself a map scan. A zeroed array is a single `memclr`.

The performance difference is detectable but not felt at 6 entries and 2-second
ticks. The main argument for the array is that it is simpler and eliminates a
potential allocation category entirely. If the plan is being implemented fresh,
prefer the array. If the map is already written and tested, the cost of
switching is not worth the benefit.

**Verdict:** Optional improvement. Worth doing at implementation time; not
worth a refactor after the fact.

---

### P3 — MINOR: hashRuns/hashDispatches traverse all Runs/Dispatches regardless of display limit

**Location:** `section_cache.go` lines ~275-285

```go
func hashRuns(kernel *aggregator.KernelState, width int) uint64 {
    // ...
    for proj, runs := range kernel.Runs {
        h.Write([]byte(proj))
        for _, r := range runs {        // ALL runs, not just displayed ones
            h.Write([]byte(r.ID))
            h.Write([]byte(r.Status))
            h.Write([]byte(r.Phase))
            h.Write([]byte(r.Goal))
        }
    }
```

The rendered `renderRunsSection()` skips done/cancelled runs and has no hard
display cap (it renders everything not done/cancelled). Hashing all runs
including done/cancelled ones means: when a run transitions to "done", the hash
changes correctly, but so does any field on a done run (Goal being edited in
the backend, for example). This is overly sensitive but not incorrect.

For `hashDispatches`, the renderer caps at 10 entries:
```go
for i, e := range entries {
    if i >= 10 { break }
```
But `hashDispatches` hashes all dispatches with no cap. So changes to dispatch
entry 11+ cause cache misses even though they are not visible. At dozens of
concurrent dispatches this becomes measurable hash work with no render benefit.

**Fix for dispatches:** Mirror the cap from the renderer. Sort the dispatches
by the same key used in rendering (status then createdAt), then only hash the
first 10.

---

### P4 — OBSERVATION: The 90% skip rate claim depends on idle system state

The plan's stated goal is "90%+ skip rate on stable frames". This is achievable
only when the system is idle (no active runs, no agent state changes). In the
primary use case — a live kernel with agents actively working — the activity
feed, runs section, and dispatches section will change on every 2-second tick
as token counts, run phases, and dispatch statuses update. The stats section
will also change as `TotalTokensIn`/`TotalTokensOut` increment.

In a busy kernel scenario, 4 of 6 sections will likely miss on every tick.
Only `sectionSessions` and `sectionAgents` are stable unless sessions
start/stop. The realistic skip rate under active use is closer to 30-40%
(2 stable sections out of 6).

This does not make the optimization wrong — skipping even 2 of 6 lipgloss
renders saves real work at keypress rate. But the framing of 90% should be
revised: 90% is achievable only on an idle dashboard (no kernel, stable
sessions, no new activity). Under load, the benefit is narrower.

---

### P4 — OBSERVATION: View() is called on every Bubble Tea message, not just on data ticks

The plan is scoped to `renderDashboard()` being called on every `View()`. But
`View()` is only called for `TabDashboard`. Key events that route to other
handlers (`promptMode`, `filterActive`, runPane navigation) call `return m, cmd`
which triggers `View()` — but if the active tab is not `TabDashboard`, the
cache is never consulted and the savings do not apply.

Tab switches invalidate the cache (`invalidateAll()`), so the first render
after switching back to the dashboard always does a full re-render. This is
correct and unavoidable.

More importantly: the footer renders `time.Since(m.lastRefresh).Round(time.Second)`
on every `View()` call, including when the dashboard cache hits on all 6
sections. The footer is not cached. This means the terminal will always receive
a full redraw on every tick regardless of section caching, because Bubble Tea
sends the full frame string to the terminal on every `View()` return — it has
no concept of partial-frame diffs. The section cache only saves the Go-side
CPU cost of calling lipgloss, not the terminal I/O cost.

This is not a criticism of the plan; it is a correct optimization target. Lipgloss
string construction has real cost (multiple `fmt.Sprintf`, style application,
`JoinVertical`/`JoinHorizontal`). The benefit is CPU cycles and GC pressure,
not reduced terminal write bytes.

---

## Summary Table

| ID | Issue | Severity | Impact |
|----|-------|----------|--------|
| 1  | hashRuns/hashDispatches iterate maps non-deterministically, causing constant cache churn on kernel data | P1 | Eliminates skip rate for runs/dispatches sections — the most valuable sections to cache under load |
| 2  | Six fnv.New64a() + six make([]byte,8) per View() | P2 | Acceptable; ~12 heap allocs per frame, ~200 bytes total |
| 3  | hashStats re-implements activeCount loop from renderStatsRow | P2 | Maintenance hazard; correct for current renderer but will silently diverge on logic changes |
| 4  | sectionCache map[sectionID] vs fixed array for 6 entries | P3 | Optional; fixed array is cleaner and faster, worth doing at implementation time |
| 5  | hashDispatches hashes beyond display cap of 10 | P3 | Causes false misses when off-screen dispatches change; bounded cost |
| 6  | 90% skip rate claim is idle-system-only | P4 | Framing issue; realistic busy-kernel skip rate is ~30-40% |
| 7  | Section cache saves CPU cost, not terminal I/O | P4 | Observation, not a bug; footer always changes, full frame always sent |

---

## Required Fix Before Implementation

**Only one fix is required (P1):** Sort map keys before hashing in `hashRuns`
and `hashDispatches`. Without this fix, the cache will produce near-zero hit
rate for both sections under any kernel-connected scenario, defeating the
optimization for exactly the case it is most needed.

All other findings are either acceptable trade-offs (P2), maintenance notes
(P3), or observations about realistic expectations (P4).

---

## Recommended Changes to Plan

1. Add sort step to `hashRuns` and `hashDispatches` before the map iteration loop.
   Add a test case `TestHashRunsStableAcrossMapOrders` that constructs a
   `map[string][]Run` and verifies the hash is identical regardless of insertion
   order.

2. In `hashDispatches`, mirror the 10-entry cap from `renderDispatchesSection`.
   Sort by `(UnifiedStatus, CreatedAt desc)` before hashing, matching the
   renderer's sort order, then hash only the first 10 entries.

3. Update the plan's stated skip rate to "90%+ on idle systems; 30-40% under
   active kernel load" to set correct expectations.

4. Consider the fixed-array `sectionCache` at implementation time (low cost
   to do it right the first time, non-trivial to refactor after tests are
   written against the map API).
