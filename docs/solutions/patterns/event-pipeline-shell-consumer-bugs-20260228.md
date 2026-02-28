---
title: "Event Pipeline Shell Consumer Bugs"
category: patterns
tags: [intercore, interspect, shell, events, cursor, quality-gates]
created: 2026-02-28
severity: high
confidence: verified
trigger: "Adding new event consumers in shell that call ic state or _interspect_insert_evidence"
---

# Event Pipeline Shell Consumer Bugs

## Context

When wiring the disagreement → resolution → routing signal pipeline (iv-5muhg), the implementation passed all Go tests and integration tests but had 4 bugs caught only by quality-gate review agents. Three were in shell code that's hard to unit test.

## Lessons

### 1. Hook ID Allowlist (Critical — Silent Pipeline Failure)

`_interspect_insert_evidence` validates `hook_id` against `_interspect_validate_hook_id()` allowlist. New hook IDs must be added to this allowlist or every evidence write silently returns 1 (swallowed by `|| true`). The entire pipeline was inert as shipped.

**Pattern**: Any time you add a new caller of `_interspect_insert_evidence` with a new hook_id string, grep for `_interspect_validate_hook_id` and add the new ID to the case statement.

**File**: `interverse/interspect/hooks/lib-interspect.sh` — `_interspect_validate_hook_id()`

### 2. `ic state set` Argument Order (Cursor Never Persisted)

`ic state set <key> <scope_id>` reads the value from **stdin**, not from a positional argument. Writing `ic state set "$key" "$value" ""` passes `$value` as `scope_id` and `""` as an @filepath, meaning the value is silently discarded.

**Correct**: `echo "$value" | ic state set "$key" "$scope_id"`
**Wrong**: `ic state set "$key" "$value" "$scope_id"`

**Pattern**: Always pipe values to `ic state set` via stdin. Check `cmdStateSet` in `cmd/ic/main.go` for the argument spec.

### 3. Scope ID Consistency (Get/Set Mismatch)

`ic state get "$key" ""` and `ic state set "$key" "global"` use different scope IDs, so they read/write different keys. Must use the same scope ID in both calls.

**Pattern**: Use a named constant or variable for the scope ID, don't inline different strings.

### 4. Error Swallowing in Go Store Methods

`_ = insertReplayInput(...)` discards the error, breaking the replay-completeness invariant. All other `Add*Event` methods propagate this error with `if err := insertReplayInput(...); err != nil { return ..., fmt.Errorf(...) }`.

**Pattern**: When adding new store methods, match the existing error-handling pattern. `_ =` in a store method is a code smell.

## Detection

These bugs were caught by 4 parallel quality-gate agents (fd-architecture, fd-quality, fd-correctness, fd-safety) reviewing the unified diff. Go tests and integration tests passed — the bugs were in shell code and cross-boundary contracts that are hard to test automatically.

Key insight: **the safety agent found the most critical bug** (F1 — allowlist). It traced the trust boundary from `_interspect_process_disagreement_event` → `_interspect_insert_evidence` → `_interspect_validate_hook_id` and noticed the new hook_id wasn't in the case statement. This is the kind of cross-function invariant that's invisible to grep-based testing.

## Applicability

- Any new interspect evidence source (new hook_id)
- Any new `ic state` consumer in shell
- Any new Go store method that calls `insertReplayInput`
- Cross-language pipelines where shell calls Go CLI commands
