# Task 6: Add printUsage Entry and AGENTS.md Documentation

## Summary

Two documentation-only changes to expose the `ic situation` command in user-facing help text and developer reference docs.

## Changes Made

### 1. `core/intercore/cmd/ic/main.go` — printUsage entry

Added a single line to the `printUsage()` function's Commands block:

```
  situation snapshot [opts]      Unified observation layer (OODAR)
```

Placed after `publish init` and before `compat status`, keeping it near the end of the command list where newer commands are grouped. The `situation` case already existed in the main switch statement (line 135-136), routing to `cmdSituation` in `cmd/ic/situation.go`.

### 2. `core/intercore/AGENTS.md` — CLI reference section

Added a new `### Situation` subsection between `### Portfolio` and `### Config & Agency`:

```markdown
### Situation

Unified observation layer for OODAR loops.

\```
ic situation snapshot                      JSON snapshot of all active runs, dispatches, events, queue depth
ic situation snapshot --run=<id>           Scoped to a specific run (includes budget)
ic situation snapshot --events=50          Control event history depth (default: 20)
\```
```

This follows the same format as other CLI command sections in AGENTS.md (heading, one-line description, code block with command variants and descriptions).

## Verification

- `go build -o ic ./cmd/ic` — compiles successfully with no errors
- No functional code changes, documentation only
- The `cmdSituation` implementation already exists in `cmd/ic/situation.go`

## Files Modified

- `/home/mk/projects/Demarch/core/intercore/cmd/ic/main.go` (1 line added in printUsage)
- `/home/mk/projects/Demarch/core/intercore/AGENTS.md` (11 lines added as new section)
