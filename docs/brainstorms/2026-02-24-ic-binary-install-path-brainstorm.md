**Bead:** iv-b7ecy

# ic Binary in Install Path

## What We're Building

Build the `ic` (intercore) binary from source during first-stranger setup and install it to `~/.local/bin/ic` so it's on PATH. Make `lib-intercore.sh` fail hard when `ic` is missing instead of silently degrading to temp-file fallbacks.

## Why This Matters

Currently `lib-intercore.sh` gracefully degrades when `ic` is missing — every wrapper function (`intercore_state_set`, `intercore_sentinel_check`, `intercore_lock`, etc.) returns 0 (success) when `ic` isn't found. This means a fresh install silently runs without the kernel: no atomicity, no deduplication, no audit trails, no locks. The system *appears* to work but is missing its foundation.

This blocks `iv-xftvq` (Hook Cutover) — migrating hooks from temp files to `ic` requires `ic` to actually be present.

## Key Decisions

1. **Install location: `~/.local/bin/ic`**
   - Standard XDG user bin, no sudo needed
   - Most distros include `~/.local/bin` on PATH by default
   - Consistent with `go install` convention
   - `lib-intercore.sh` still uses `command -v ic` (no hardcoded paths)

2. **Build triggers: install.sh AND clavain:setup**
   - `install.sh`: For new users (curl-pipe install). Builds `ic` after installing Clavain plugin.
   - `clavain:setup`: For existing users. Checks for `ic`, builds if missing.
   - Both paths: `go build -o ~/.local/bin/ic ./core/intercore/cmd/ic` then `ic init`

3. **Go is a hard prerequisite**
   - `install.sh` checks `command -v go` and exits with a clear error if missing
   - Go is already needed for `bd` (Beads CLI) — same user base
   - Minimum: Go 1.22 (matches `core/intercore/go.mod`)

4. **Hard fail when ic is missing**
   - `intercore_available()` continues returning 1 (unchanged)
   - Wrapper functions stop returning 0 on failure — they propagate the error
   - Error message: `"ic not found — run install.sh or /clavain:setup"`
   - Need to audit all hook callers to handle the new error propagation

## Scope

### In Scope
- Add Go prerequisite check to `install.sh`
- Add `ic` build + install step to `install.sh`
- Add `ic` build + health check step to `clavain:setup`
- Change `lib-intercore.sh` wrapper functions to propagate `intercore_available()` failures
- Ensure `~/.local/bin` directory exists (create if needed)
- Run `ic init` after first build to create the DB

### Out of Scope
- Pre-built binary distribution (future optimization)
- Auto-update mechanism for `ic`
- Changing the `ic` binary name or command structure
- Modifying `intercore` Go code itself

## Risk: Breaking Existing Hooks

Changing wrapper functions from "return 0 on missing ic" to "propagate error" could break hooks that don't expect errors. All callers of these functions must be audited:

- `intercore_state_set/get` — callers ignore return value? Or depend on 0?
- `intercore_sentinel_check` — callers use `|| exit 0` pattern already
- `intercore_lock/unlock` — callers may depend on fallback behavior
- `intercore_check_or_die` — already handles the fallback internally

The `_or_legacy` and `_or_die` functions already have fallback logic built in. The risk is mainly with direct `intercore_state_*` callers.

## Prior Art

- Seam tests: `go build -o /tmp/ic-seam-$$ ./cmd/ic` (temp location, prepend to PATH)
- `bd` installation: `go install github.com/mistakeknot/beads/cmd/bd@latest` (GOPATH/bin)
- `install.sh` already checks `claude`, `jq`, `git` (precedent for prerequisite checks)

## Open Questions

- Should `clavain:setup` auto-rebuild `ic` when the installed version is older than the source? (Version check: `ic version` vs source `const version`)
- Should the build use `go install` (to GOPATH/bin) or `go build -o` (to explicit path)?
