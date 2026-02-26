# Task 1: Harden lib-intercore.sh Wrapper Functions

**Date:** 2026-02-24
**File:** `/home/mk/projects/Demarch/os/clavain/hooks/lib-intercore.sh`
**Status:** Complete

## Summary

Applied 5 targeted changes to harden the raw wrapper functions in `lib-intercore.sh`. These changes make failure propagation explicit and add a one-time warning when the `ic` binary is not found. No `_or_legacy`, `_or_die`, dispatch, run, lock, gate, event, agency, or action wrappers were modified.

## Changes Applied

### Change 1: INTERCORE_WARNED flag (line 17)

Added `INTERCORE_WARNED=false` after `INTERCORE_BIN=""` to support one-time warning dedup.

**Before:**
```bash
INTERCORE_BIN=""
```

**After:**
```bash
INTERCORE_BIN=""
INTERCORE_WARNED=false
```

### Change 2: intercore_available() one-time warning (lines 25-29)

When `ic` binary is not found, the function now emits a warning to stderr on the first call only, then sets `INTERCORE_WARNED=true` to suppress subsequent warnings. Previously it returned silently.

**Before:**
```bash
    if [[ -z "$INTERCORE_BIN" ]]; then
        return 1
    fi
```

**After:**
```bash
    if [[ -z "$INTERCORE_BIN" ]]; then
        if [[ "$INTERCORE_WARNED" != true ]]; then
            printf 'ic: not found — run install.sh or /clavain:setup\n' >&2
            INTERCORE_WARNED=true
        fi
        return 1
    fi
```

### Change 3: intercore_state_set — propagate failure (lines 43-44)

Changed both `return 0` to `return 1` so callers can detect that state was NOT persisted.

**Before:**
```bash
    if ! intercore_available; then return 0; fi
    printf '%s\n' "$json" | "$INTERCORE_BIN" state set "$key" "$scope_id" || return 0
```

**After:**
```bash
    if ! intercore_available; then return 1; fi
    printf '%s\n' "$json" | "$INTERCORE_BIN" state set "$key" "$scope_id" || return 1
```

### Change 4: intercore_state_get — propagate failure (line 49)

Changed `return` (implicit 0) to `return 1` so callers can distinguish "empty because unavailable" from "empty because key not found".

**Before:**
```bash
    if ! intercore_available; then printf ''; return; fi
```

**After:**
```bash
    if ! intercore_available; then printf ''; return 1; fi
```

### Change 5: intercore_sentinel_check — propagate failure (line 55)

Changed `return 0` to `return 1` so callers know the sentinel check was not actually performed.

**Before:**
```bash
    if ! intercore_available; then return 0; fi
```

**After:**
```bash
    if ! intercore_available; then return 1; fi
```

## Verification

- `bash -n os/clavain/hooks/lib-intercore.sh` passes (no syntax errors).
- Git diff confirms exactly 5 change sites, no unintended modifications.
- All `_or_legacy` and `_or_die` variants are untouched (they already have correct failure handling).
- All dispatch, run, lock, gate, event, agency, and action wrappers are untouched.

## Rationale

The previous `return 0` behavior in `state_set`, `state_get`, and `sentinel_check` silently swallowed failures. Callers that checked the return code would believe the operation succeeded when it was actually skipped. This was the correct "fail-open" behavior during initial rollout (where missing `ic` was common), but now that the system is maturing, callers should be able to detect and handle missing intercore explicitly.

The one-time warning in `intercore_available()` gives operators a single diagnostic hint without flooding stderr on every hook invocation (a single session may call `intercore_available()` dozens of times).

## Diff Summary

```
+INTERCORE_WARNED=false

 intercore_available():
+  one-time warning to stderr when ic not found

 intercore_state_set():
-  return 0  →  return 1  (both lines)

 intercore_state_get():
-  return    →  return 1

 intercore_sentinel_check():
-  return 0  →  return 1
```
