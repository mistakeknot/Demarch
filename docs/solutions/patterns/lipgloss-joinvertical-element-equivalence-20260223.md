---
title: "lipgloss.JoinVertical Treats Separate Elements and Newline-Joined Strings Identically"
category: patterns
severity: low
date: 2026-02-23
tags: [go, lipgloss, bubble-tea, tui, refactoring, string-composition]
related: [bubble-tea-pointer-cache-safety-20260223]
---

## Problem

When refactoring `lipgloss.JoinVertical` call sites — for example, extracting inline section rendering into sub-functions — a common review concern is whether changing from separate elements to a single newline-joined string alters the visual output.

Original (separate elements):
```go
sections = append(sections, title, strings.Join(lines, "\n"), "")
return lipgloss.JoinVertical(lipgloss.Left, sections...)
```

Refactored (single element from sub-function):
```go
sections = append(sections, title + "\n" + strings.Join(lines, "\n"), "")
return lipgloss.JoinVertical(lipgloss.Left, sections...)
```

A correctness review flagged this as a P1 output fidelity regression during Bigend's section cache refactoring (iv-t217).

## Investigation

Tested empirically with lipgloss:

```go
a := lipgloss.JoinVertical(lipgloss.Left, "Title", "line1\nline2", "")
b := lipgloss.JoinVertical(lipgloss.Left, "Title\nline1\nline2", "")
// a == b → true
```

`JoinVertical` joins its arguments with `"\n"`. So `["Title", "body"]` produces `"Title\nbody"`, which is identical to passing `"Title\nbody"` as a single argument. The function operates on the final string content, not on element boundaries.

## Solution

These are safe refactoring transformations for `lipgloss.JoinVertical`:

- Merging adjacent elements: `["a", "b"]` → `["a\nb"]` (safe)
- Splitting elements at newlines: `["a\nb"]` → `["a", "b"]` (safe)
- Extracting sub-functions that return `title + "\n" + body` instead of separate elements (safe)

This does NOT apply to `JoinHorizontal`, where element boundaries determine column alignment.

## Verification

The `TestDashboardCacheSkipsReRender` test confirms output stability — two consecutive renders of the same state produce identical strings, validating that the sub-function extraction doesn't change output.

## Key Takeaway

When refactoring `lipgloss.JoinVertical` call sites, element boundaries don't matter — only the final concatenated string content matters. This makes it safe to extract render sub-functions that return combined title+body strings without worrying about spacing regressions.
