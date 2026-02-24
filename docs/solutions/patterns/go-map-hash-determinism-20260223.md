---
title: "Go Map Iteration Non-Determinism Kills Hash-Based Caching"
category: patterns
severity: high
date: 2026-02-23
tags: [go, hashing, caching, maps, determinism, performance, bubble-tea]
related: []
---

## Problem

When building a render cache that uses FNV-64 hashing to detect data changes, iterating Go maps (`map[string][]T`) directly into the hash produces non-deterministic output. Go randomizes map iteration order on every call, so identical data produces different hashes, causing 100% cache miss rate on map-keyed sections.

This was caught during plan review for Bigend's dashboard section cache (iv-t217). The hash functions for `kernel.Runs` and `kernel.Dispatches` — both `map[string][]icdata.Run/Dispatch` — iterated keys directly, making the cache useless for kernel sections.

## Investigation

The original code:

```go
func hashRuns(kernel *aggregator.KernelState, width int) uint64 {
    h := fnv.New64a()
    // ...
    for proj, runs := range kernel.Runs {  // Non-deterministic order!
        h.Write([]byte(proj))
        for _, r := range runs {
            h.Write([]byte(r.ID))
        }
    }
    return h.Sum64()
}
```

Every call to `hashRuns` with the same `kernel.Runs` data could return a different hash, because Go's `range` over maps visits keys in a random order. The hash is order-dependent (FNV feeds bytes sequentially), so different key orderings produce different hashes.

This doesn't affect slice-based sections (sessions, agents, activities) because slices have stable iteration order.

## Solution

Sort map keys before hashing:

```go
func hashRuns(kernel *aggregator.KernelState, width int) uint64 {
    h := fnv.New64a()
    // ...
    projects := make([]string, 0, len(kernel.Runs))
    for proj := range kernel.Runs {
        projects = append(projects, proj)
    }
    sort.Strings(projects)
    for _, proj := range projects {
        h.Write([]byte(proj))
        for _, r := range kernel.Runs[proj] {
            h.Write([]byte(r.ID))
        }
    }
    return h.Sum64()
}
```

The `sort.Strings` call adds ~O(n log n) per hash, but with typical n < 20 projects, this is negligible compared to the lipgloss rendering cost being avoided (~milliseconds vs microseconds).

## Verification

Test with repeated hashing to catch non-determinism:

```go
func TestHashRunsDeterministic(t *testing.T) {
    kernel := &aggregator.KernelState{
        Runs: map[string][]icdata.Run{
            "/proj/alpha": {{ID: "r1"}},
            "/proj/beta":  {{ID: "r2"}},
            "/proj/gamma": {{ID: "r3"}},
        },
    }
    h1 := hashRuns(kernel, 120)
    for i := 0; i < 100; i++ {
        h := hashRuns(kernel, 120)
        if h != h1 {
            t.Fatalf("non-deterministic on iteration %d", i)
        }
    }
}
```

100 iterations is sufficient — Go's map randomization triggers on most runs.

## Key Takeaway

Any time you hash map contents in Go, sort the keys first. This applies to: render caching, content-addressable storage, ETag generation, change detection, and test assertions on map-derived hashes.
