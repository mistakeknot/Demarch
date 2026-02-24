---
title: "Bubble Tea Pointer Fields Are Safe Without Mutexes"
category: patterns
severity: medium
date: 2026-02-23
tags: [go, bubble-tea, concurrency, elm-architecture, caching, tui]
related: [go-map-hash-determinism-20260223]
---

## Problem

When adding a `*sectionCache` pointer field to a Bubble Tea `Model` struct, code review agents (both automated and human) frequently flag it as a concurrency bug: "multiple Model copies share the same cache pointer — needs a mutex."

This is a false positive in Bubble Tea's architecture, but it recurs in every review of pointer-bearing Model fields.

## Investigation

Bubble Tea uses the Elm architecture where:
- `Update(msg) (Model, Cmd)` — processes messages, returns new Model value
- `View() string` — renders the current Model to a string

Both are called sequentially on the **same goroutine** by the Bubble Tea runtime. The runtime never calls `View()` while `Update()` is running, and vice versa. Commands (`tea.Cmd`) run on separate goroutines but they only produce messages — they never access the Model directly.

This means:
1. `applyResize()` (called from `Update()`) can safely call `cache.invalidateAll()`
2. `renderDashboard()` (called from `View()`) can safely call `cache.getOrRender()`
3. These two never execute concurrently

The `*sectionCache` pointer is copied when Bubble Tea copies the Model value (it does this on every message dispatch), but all copies point to the same heap-allocated cache. Since only one copy is ever active at a time (the one in the current Update/View cycle), there's no race.

## Solution

No mutex needed. Use a plain pointer field:

```go
type Model struct {
    // ... other fields ...
    dashCache *sectionCache  // Safe: Bubble Tea serializes Update/View
}
```

Initialize in the constructor:

```go
func New(agg aggregatorAPI) Model {
    return Model{
        dashCache: newSectionCache(),
    }
}
```

The `-race` detector confirms this is safe — all tests pass with `-race` flag.

## When You DO Need a Mutex

A mutex IS needed when:
- A `tea.Cmd` goroutine writes to shared state (use `atomic` or channels instead)
- Multiple Bubble Tea programs share the same pointer (unusual but possible)
- External goroutines (e.g., a WebSocket listener) modify Model state directly

The `fallbackActive atomic.Bool` in Autarch's fallback pattern is an example where atomics ARE needed — `tea.Cmd` goroutines detect connection failures and set the flag, while `View()` reads it.

## Key Takeaway

In Bubble Tea, pointer fields on Model are safe without synchronization because Update and View are serialized. The Elm architecture's single-threaded message loop is the synchronization mechanism. Explain this in code review responses to avoid repeated false positive flags.
