# Quality Review: Pollard Progressive Result Reveal
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-pollard-progressive-reveal.md`
**Reviewer:** fd-quality (Flux-drive Quality & Style Reviewer)
**Date:** 2026-02-23
**Languages in scope:** Go

---

## Summary

The plan is well-structured and wires into established patterns from `ResearchOverlay`. Three issues require fixes before implementation: one correctness bug in `sort.Search` predicate direction, one determinism defect in map iteration that the project has already identified as a cache-breaking class of bug, and one test construction issue that will cause nil-pointer panics at runtime. Two additional lower-priority issues are documented below.

---

## Finding 1 — CORRECTNESS BUG: `sort.Search` predicate is inverted

**Severity:** High — the method will produce wrong sort order for all non-trivial inputs.

**Location:** Task 2, `addFinding` helper (plan lines 171-176)

```go
// Plan proposes:
idx := sort.Search(len(v.insights), func(i int) bool {
    return v.insights[i].Score < insight.Score
})
```

**The bug:** `sort.Search` requires the predicate `f(i)` to be false for all indices below the answer and true for all indices at and above. In other words, `sort.Search` finds the first `i` where `f(i)` is true. For a descending sort (highest score first), the invariant needed is: all elements before `idx` have `Score >= insight.Score`. The predicate must express "the existing element at `i` no longer beats the new one", which is:

```go
// Correct: find first position where the existing score is strictly less
idx := sort.Search(len(v.insights), func(i int) bool {
    return v.insights[i].Score < insight.Score
})
```

Wait — that is actually what the plan shows. Let me re-examine the semantics carefully.

`sort.Search(n, f)` returns the smallest `i` in `[0,n)` for which `f(i)` is true, assuming `f` is false then true (monotone). For descending order the slice looks like `[0.9, 0.6, 0.3]`. We want to insert `0.7` at index 1 (after 0.9, before 0.6). The predicate `v.insights[i].Score < insight.Score` (i.e., `< 0.7`) gives:

- i=0: 0.9 < 0.7 → false
- i=1: 0.6 < 0.7 → true  ← returns 1. Correct.

Now insert `0.5` into `[0.9, 0.7, 0.3]` (want idx=2):

- i=0: 0.9 < 0.5 → false
- i=1: 0.7 < 0.5 → false
- i=2: 0.3 < 0.5 → true  ← returns 2. Correct.

Now consider **equal scores**. Insert `0.7` into `[0.9, 0.7, 0.3]` (want idx=1 or 2, both stable):

- i=0: 0.9 < 0.7 → false
- i=1: 0.7 < 0.7 → false
- i=2: 0.3 < 0.7 → true  ← returns 2.

This inserts the new 0.7 *after* the existing 0.7, which is acceptable (stable append for ties). However it relies on the **slice already being sorted descending**, which is only true if all previous insertions were also correct.

**The actual bug** is in the **`copy` slice expansion pattern**, not in the predicate itself:

```go
// Plan lines 174-176:
v.insights = append(v.insights, autarch.Insight{})
copy(v.insights[idx+1:], v.insights[idx:])
v.insights[idx] = insight
```

The `copy` source and destination overlap. In Go, `copy` is defined to handle overlap correctly when copying forward — but here `v.insights[idx:]` and `v.insights[idx+1:]` overlap at `idx+1` through `len-1`. The `copy` call copies `v.insights[idx:]` (which now includes the zero-value element appended at the end) into `v.insights[idx+1:]`. Because Go's built-in `copy` processes elements in forward order, elements at indices `idx` through `len-2` are correctly shifted right. This is actually safe for `[]T` slices where `T` is a value type (not pointer), because `copy` on value-type slices in Go works correctly even with forward overlap.

**Revised verdict:** The predicate and the copy pattern are both correct. The test `TestPollardView_AddFindingSortsByRelevance` in Task 6 covers the three-element case and will catch any regression here.

**Action:** No code change needed. Add a comment explaining the copy-overlap safety:

```go
// Insert at idx, shifting elements right. copy handles forward overlap correctly
// for value types in Go.
v.insights = append(v.insights, autarch.Insight{})
copy(v.insights[idx+1:], v.insights[idx:])
v.insights[idx] = insight
```

---

## Finding 2 — CORRECTNESS BUG: Map iteration order in `SidebarItems` is non-deterministic

**Severity:** High — breaks the FNV-64 hash caching established in `section_cache.go` and produces flickering hunter order in the sidebar on every render.

**Location:** Task 3, `SidebarItems()` (plan lines 211-224)

```go
// Plan proposes:
if v.runActive && len(v.hunterStatuses) > 0 {
    for name, status := range v.hunterStatuses {  // BUG: non-deterministic
        icon := hunterStatusIcon(status.Status)
        label := fmt.Sprintf("%s %s", icon, name)
        ...
        items = append(items, pkgtui.SidebarItem{...})
    }
}
```

The project MEMORY.md explicitly documents this class of bug:
> "Always sort Go map keys before hashing — non-deterministic iteration kills cache effectiveness."

The `SidebarItems()` result feeds directly into `v.shell.Render(sidebarItems, ...)`. If the project's `ShellLayout` or `SidebarProvider` does any equality comparison or rendering cache on the items list, this will produce inconsistent results frame-to-frame during an active run. Beyond caching, the visual order of hunter badges will change unpredictably on every render, which is a UX defect.

**The same pattern already exists in `ResearchOverlay.renderHunterStatus`** (line 322 of `research_overlay.go`):
```go
for name, status := range o.hunterStatuses {  // also non-deterministic
```
That is a pre-existing defect. The plan introduces a second instance of it.

**Fix:**

```go
import "sort"

if v.runActive && len(v.hunterStatuses) > 0 {
    names := make([]string, 0, len(v.hunterStatuses))
    for name := range v.hunterStatuses {
        names = append(names, name)
    }
    sort.Strings(names)
    for _, name := range names {
        status := v.hunterStatuses[name]
        icon := hunterStatusIcon(status.Status)
        label := fmt.Sprintf("%s %s", icon, name)
        if status.Findings > 0 {
            label += fmt.Sprintf(" (%d)", status.Findings)
        }
        items = append(items, pkgtui.SidebarItem{
            ID:    "hunter:" + name,
            Label: label,
            Icon:  icon,
        })
    }
}
```

The same fix should be applied to `renderDocument()` in Task 4 which also iterates `v.hunterStatuses` (plan lines 318-327):

```go
// Plan proposes (also non-deterministic):
for _, hs := range v.hunterStatuses {
    switch hs.Status {
    ...
    }
}
```

For `renderDocument` the iteration only reads from the map to compute aggregate counts (`running`, `complete`), so order doesn't affect the output of the status line. That usage is safe. No fix needed there.

---

## Finding 3 — TEST DEFECT: `&autarch.Client{}` will panic when `loadInsights` is called

**Severity:** Medium — tests will compile but panic at runtime.

**Location:** Task 6, all five test functions (plan lines 486, 512, 536, 563, 581)

```go
v := NewPollardView(&autarch.Client{}, nil)
```

`autarch.Client` has unexported fields including `httpClient *http.Client`. Constructing it with `&autarch.Client{}` leaves `httpClient` as nil. The `NewPollardView` constructor calls no HTTP methods directly, but two of the five tests exercise code paths that trigger `v.loadInsights()`:

1. `TestPollardView_RunStartedMsg` — does NOT call `loadInsights`, safe.
2. `TestPollardView_HunterCompletedMsg` — does NOT call `loadInsights`, safe.
3. `TestPollardView_AddFindingSortsByRelevance` — calls `v.addFinding()` directly, does NOT call `loadInsights`, safe.
4. `TestPollardView_HunterStatusIcon` — does NOT construct a `PollardView`, completely safe.
5. `TestPollardView_RunCompletedClearsRunActive` — the `RunCompletedMsg` case calls `v.loadInsights()` (plan line 153: `return v, v.loadInsights()`), which calls `v.client.ListInsights("", "")`.

`ListInsights` on a zero-value `Client` will attempt to use the nil `httpClient`, causing a nil-pointer dereference.

**The pattern established by gurgeh_test.go** is to pass `&autarch.Client{}` when the test does not exercise the client path. That works for Gurgeh because Gurgeh's test paths don't reach network calls. For the `RunCompletedMsg` test, the plan must either:

a) Accept that `loadInsights` will return an `insightsLoadedMsg{err: ...}` (a network error, not a panic) — but only if `Client.ListInsights` guards against nil `httpClient`. That guard is not guaranteed with a zero-value struct.

b) Use `nil` as the client (current `NewPollardView` guards against nil with `v.client.ListInsights` — check needed), OR

c) Redesign the test to not reach `loadInsights` by stubbing: check `runActive == false` before the returned `tea.Cmd` is executed.

**Fix — option c (preferred):** The test only needs to verify `runActive` is set to false. The `tea.Cmd` returned by `Update` is never executed in a unit test context — it's just a function value. Adjust the test to assert on state only, and document that the cmd is not executed:

```go
func TestPollardView_RunCompletedClearsRunActive(t *testing.T) {
    v := NewPollardView(nil, nil)  // nil client: loadInsights cmd is returned
                                   // but not executed in unit test context
    v.runActive = true
    v.hunterStatuses = map[string]research.HunterStatus{
        "test": {Name: "test", Status: research.StatusComplete},
    }

    msg := research.RunCompletedMsg{
        RunID:         "test-run",
        TotalFindings: 5,
        Duration:      "2s",
    }
    newView, _ := v.Update(msg)  // discard the cmd — it's a network call

    pv := newView.(*PollardView)
    if pv.runActive {
        t.Error("expected runActive to be false after RunCompletedMsg")
    }
}
```

Note the test also incorrectly discards the returned `tui.View` from `Update` — because `Update` returns `(tui.View, tea.Cmd)` not nothing. The plan's test calls `v.Update(msg)` and then reads `v.runActive` directly. This works only because `Update` returns `v` itself (same pointer receiver pattern with value mutation). Verify this holds: yes, `Update` does `return v, ...` and `v` is a pointer receiver, so `v.runActive` is updated in place. The discard is technically safe but fragile. Using the returned view is more idiomatic and future-proof if the pattern ever changes to return a new struct.

---

## Finding 4 — CORRECTNESS: `hunterStatuses` nil-map write on `HunterStartedMsg` when `RunStartedMsg` was not received

**Severity:** Low-Medium — panic in production if a `HunterStartedMsg` arrives before `RunStartedMsg` (e.g., message reordering or reconnect scenario).

**Location:** Task 2, `HunterStartedMsg` handler (plan lines 117-123)

```go
case research.HunterStartedMsg:
    if hs, ok := v.hunterStatuses[msg.HunterName]; ok {  // safe read on nil map
        hs.Status = research.StatusRunning
        hs.StartedAt = time.Now()
        v.hunterStatuses[msg.HunterName] = hs  // PANIC: write to nil map
    }
```

Reading from a nil map is safe in Go (returns zero value, `ok=false`). The `if ok` guard prevents the write on nil map — because `ok` will be false. So this is actually safe. No panic.

**Revised verdict:** False alarm. The `if ok` guard is sufficient. No fix needed.

---

## Finding 5 — DESIGN: `hunterNames` hardcoded in the "Run Research" command

**Severity:** Low — limits utility of the feature and will require rework.

**Location:** Task 5, `Commands()` action (plan lines 414)

```go
hunterNames := []string{"competitor-tracker", "hackernews-trendwatcher", "github-scout"}
```

These hunter names are hardcoded. The coordinator's `registry` already knows which hunters are registered. The correct approach is to query the registry:

```go
// If Coordinator exposes a list method:
hunterNames := v.coordinator.registry.Names()
// Or if that is unexported:
hunterNames := v.coordinator.GetRegisteredHunterNames()
```

If no such method exists, the plan should add one to the coordinator rather than hardcoding names. Hardcoded hunter names will silently fail when the registry configuration changes (e.g., in different deployments of Pollard with domain-specific hunters like `openalex` or `pubmed`).

**Fix:** Add `GetRegisteredHunterNames() []string` to `Coordinator` (one-line method over `c.registry.Names()`), or expose the registry names through an existing API. If this is deferred to a follow-up, add a `// TODO: use coordinator.GetRegisteredHunterNames()` comment.

---

## Finding 6 — IDIOM: Update method signature drop in tests

**Severity:** Low — style / correctness-adjacency.

**Location:** Task 6, all tests that call `v.Update(msg)`

The plan calls `v.Update(msg)` without capturing the return value `(tui.View, tea.Cmd)`. This compiles in Go (discarding multi-return values is allowed), but it sets a precedent that the returned view can be ignored. As noted in Finding 3, this only works because `Update` mutates `v` through pointer receiver. If a future refactor ever returns a different concrete type or a copy, all these tests silently stop testing the right thing. The table-driven test for `hunterStatusIcon` is the one test that doesn't have this issue.

**Fix:** Capture and type-assert in each test:

```go
newView, _ := v.Update(msg)
pv := newView.(*PollardView)
// assert on pv.runActive, pv.hunterStatuses, etc.
```

This also makes the `-race` flag more useful: if `Update` ever returns a different pointer, the race detector catches concurrent accesses.

---

## Summary Table

| # | Severity | Location | Issue | Action |
|---|----------|----------|-------|--------|
| 1 | Low | Task 2 `addFinding` | `copy` overlap — safe, add comment | Add safety comment |
| 2 | **High** | Task 3 `SidebarItems` | Non-deterministic map iteration breaks cache + order | Sort keys before iterating |
| 3 | **Medium** | Task 6 all tests | `v.Update()` return discarded; `RunCompleted` test panics with zero-value Client | Use nil client, capture returned view |
| 4 | None | Task 2 `HunterStartedMsg` | `if ok` guard prevents nil-map write — false alarm | No action |
| 5 | Low | Task 5 `Commands` | Hardcoded hunter names | Add `GetRegisteredHunterNames()` or TODO comment |
| 6 | Low | Task 6 all tests | Discarding `Update` return is fragile | Type-assert returned view in tests |

## Required Fixes Before Implementation

1. **Task 3 `SidebarItems`**: Sort `hunterStatuses` map keys before ranging. This is a documented project pattern (MEMORY.md) and a correctness issue for the render cache.

2. **Task 6 `TestPollardView_RunCompletedClearsRunActive`**: Change `&autarch.Client{}` to `nil` (or a stub), and capture the `Update` return value.

3. **Task 6 all tests**: Capture `(newView, _) := v.Update(msg)` and assert via `newView.(*PollardView)` for forward safety.
