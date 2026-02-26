# Cache Companion Plugin Discovery

**Bead:** iv-umx1i

## Problem

Clavain's `lib.sh` has 6 `_discover_*_plugin()` functions, each running a separate `find` on `~/.claude/plugins/cache`. Each call takes ~75ms (mostly bash overhead from sourcing lib.sh and subshell for find), totaling ~450ms on session start. The in-process `_CACHED_*` vars avoid repeated finds within a single hook invocation, but across hooks (session-start.sh, auto-stop-actions.sh, lib-discovery.sh, lib-gates.sh) the cache is lost.

## Solution

Replace individual `find` calls with a **single batched `find`** that discovers all companions at once, writing results to a cache file. Individual `_discover_*_plugin()` functions become thin readers of the cache. The cache file also persists across hook invocations within the same session.

## Tasks

- [x] **Task 1: Add `_discover_all_companions()` batch function to lib.sh**
  - Single `find` call with `-path p1 -o -path p2 -o ...` for all 6 companions
  - Parse results into `_CACHED_*` variables in one pass
  - Write results to `~/.cache/clavain/companion-roots.env` (key=value format, one per line)
  - Guard: if cache file exists and is from this session (check `CLAUDE_SESSION_ID` marker), read it instead of running `find`

- [x] **Task 2: Refactor individual `_discover_*_plugin()` functions to use batch cache**
  - Each function: check `_CACHED_*` var first (existing pattern), then try env-var override (`*_ROOT`), then call `_discover_all_companions()` which populates all caches at once
  - First discover call pays the cost, all subsequent calls are free (both in-process and cross-hook via file)

- [x] **Task 3: Add cache invalidation**
  - session-start.sh already runs cleanup of old plugin versions (lines 34-48). After cleanup, delete the cache file so it gets regenerated with current paths.
  - No TTL needed — the session cleanup handles staleness.

- [x] **Task 4: Verify syntax and test**
  - `bash -n hooks/lib.sh`
  - Manual test: source lib.sh, call each discover function, verify correct paths returned
  - Verify cache file written, second invocation reads from file

## Design Decisions

- **env file format** (not JSON): simpler to read/write in bash, no jq dependency for hot path
- **`~/.cache/clavain/`** (XDG cache dir): appropriate for ephemeral, regenerable data
- **Session-scoped**: cache file includes session marker to avoid cross-session staleness
- **No lock file**: writes are atomic (write to temp, mv), reads tolerate partial/missing file

## Files Changed

- `os/clavain/hooks/lib.sh` — batch discover function + refactored individual functions
- `os/clavain/hooks/session-start.sh` — invalidate cache on plugin cleanup (1 line)
