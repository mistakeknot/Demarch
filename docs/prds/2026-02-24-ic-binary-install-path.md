**Bead:** iv-b7ecy

# PRD: ic Binary in Install Path

## Problem

Fresh Demarch installs silently run without the Intercore kernel because `lib-intercore.sh` gracefully degrades when `ic` is missing. Every wrapper function returns success, falling back to temp files — losing atomicity, deduplication, and audit trails. Users don't know anything is wrong.

## Solution

Build the `ic` binary from source during installation (both `install.sh` and `clavain:setup`), install it to `~/.local/bin/ic`, and make `lib-intercore.sh` fail hard with a clear error message when `ic` is not found.

## Features

### F1: Add Go prerequisite + ic build to install.sh

**What:** The curl-pipe installer checks for Go, builds `ic` from source, installs to `~/.local/bin/`, and runs `ic init`.

**Acceptance criteria:**
- [ ] `install.sh` checks `command -v go` and exits 1 with clear message if missing
- [ ] Go version check: exits if below 1.22 (`go version` parsed)
- [ ] Creates `~/.local/bin/` if it doesn't exist
- [ ] Runs `go build -o ~/.local/bin/ic ./core/intercore/cmd/ic` from the repo clone
- [ ] Runs `ic init` after successful build
- [ ] Verifies `ic health` passes before continuing
- [ ] Dry-run mode shows what would happen without building
- [ ] Handles the case where install.sh is piped from curl (needs to clone repo first for Go source)

### F2: Add ic build step to clavain:setup

**What:** The setup command checks for `ic` on PATH and builds it from source if missing or outdated.

**Acceptance criteria:**
- [ ] Setup checks `command -v ic`
- [ ] If missing: builds from `core/intercore/` source (requires knowing repo root)
- [ ] If present: runs `ic health` to verify it works
- [ ] Reports success/failure clearly to the user
- [ ] Works when invoked from any project directory (finds Demarch repo root)

### F3: Harden lib-intercore.sh failure propagation

**What:** Wrapper functions in `lib-intercore.sh` propagate `intercore_available()` failures instead of silently returning 0.

**Acceptance criteria:**
- [ ] `intercore_state_set` returns 1 (not 0) when `intercore_available` fails
- [ ] `intercore_state_get` returns empty string AND non-zero exit when `intercore_available` fails
- [ ] `intercore_sentinel_check` returns 1 (not 0) when `intercore_available` fails
- [ ] All callers of these functions audited and updated to handle errors
- [ ] `_or_legacy` functions retain their fallback behavior (they already handle missing ic)
- [ ] `_or_die` functions retain their exit-on-throttle behavior
- [ ] First failure emits a clear message to stderr: `"ic not found — run install.sh or /clavain:setup"`
- [ ] Message is emitted once per session (not on every call) via a flag variable

## Non-goals

- Pre-built binary distribution (goreleaser) — future optimization
- Auto-update mechanism for `ic` binary
- Modifying Intercore Go source code
- Version mismatch detection (installed vs source) — future feature
- macOS/Windows support — Linux only for now

## Dependencies

- `iv-t712t` (First-stranger experience) — already closed, provides install.sh framework
- Go 1.22+ toolchain on the user's system
- `core/intercore/` Go source in the repo

## Open Questions

- **Curl-pipe install flow**: When `install.sh` is piped from curl, the Go source isn't available locally. Options: (a) clone the repo to a temp dir, build, clean up; (b) skip ic build in curl-pipe mode, defer to `clavain:setup`; (c) use `go install github.com/mistakeknot/interverse/infra/intercore/cmd/ic@latest`
- **PATH awareness**: If `~/.local/bin` isn't on PATH, should install.sh add it to `~/.bashrc`/`~/.zshrc`? Or just warn?
