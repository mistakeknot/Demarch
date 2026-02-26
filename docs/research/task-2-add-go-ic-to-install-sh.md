# Task 2: Add Go Prerequisite Check and ic Build Step to install.sh

## Summary

Modified `/home/mk/projects/Demarch/install.sh` to add Go as a hard prerequisite and an `ic` (intercore kernel) binary build step. The installer grew from 280 lines to 378 lines across four discrete changes.

## Changes Made

### Step 1: Go Prerequisite Check (lines 129-146)

Added after the jq check block and before the git (WARN) check. Go >= 1.22 is a hard requirement — the installer exits with actionable error messages if Go is missing or too old.

The version parsing extracts major/minor from `go version` output using grep + sed, then does integer comparison. It handles Go 2.x (future-proofing) and Go 1.22+.

```bash
# go (REQUIRED -- builds intercore kernel)
if command -v go &>/dev/null; then
    go_ver=$(go version | grep -Eo 'go[0-9]+\.[0-9]+' | head -1 | sed 's/go//')
    go_major="${go_ver%%.*}"
    go_minor="${go_ver#*.}"
    if [[ "$go_major" -ge 2 ]] || { [[ "$go_major" -eq 1 ]] && [[ "$go_minor" -ge 22 ]]; }; then
        success "go ${go_ver} found (>= 1.22)"
    else
        fail "go ${go_ver} found but >= 1.22 required"
        log "  Update Go: ${BLUE}https://go.dev/dl/${RESET}"
        exit 1
    fi
else
    fail "go not found"
    log "  Go >= 1.22 is required to build the intercore kernel."
    log "  Install: ${BLUE}https://go.dev/dl/${RESET}"
    exit 1
fi
```

### Step 2: ic Build Step (lines 267-330, "Step 5")

Placed after the Beads init block (Step 4) and before the Verification section. This is the largest addition. Three-phase source resolution:

1. **Local detection**: Checks `core/intercore/cmd/ic/main.go` (monorepo root) and `../core/intercore/cmd/ic/main.go` (subproject).
2. **Sparse clone fallback**: For curl-pipe mode where the repo isn't present, does a minimal `git clone --depth=1 --filter=blob:none --sparse` and sets up sparse checkout for just `core/intercore`.
3. **Build and init**: Builds with `go build -C "$IC_SRC" -mod=readonly` to `~/.local/bin/ic`, then runs `ic init` and `ic health`.

Key design decisions:
- Uses `go build -C` (Go 1.21+) so the build works without `cd`-ing into the source directory.
- `-mod=readonly` prevents accidental `go.sum` modifications.
- Installs to `~/.local/bin/ic` (XDG-compliant user binary location).
- Checks if `~/.local/bin` is on PATH and warns if not.
- `ic init` failure is a warning (may already be initialized), not an error.
- `ic health` failure is a warning, not a fatal error.
- Sparse clone failure is a warning with instructions to run `/clavain:setup` later.
- Dry-run mode is respected throughout (via the `run` wrapper and explicit `$DRY_RUN` checks).
- Temporary clone directory is cleaned up via `trap ... EXIT`.

### Step 3: ic Verification Block (lines 350-361)

Added after the Clavain verification and before the Next steps section. Three-tier check:

1. `command -v ic` succeeds: run `ic health` and report.
2. `ic` not on PATH but `~/.local/bin/ic` is executable: warn about PATH.
3. Neither found: warn that kernel features will be unavailable.

### Step 4: Updated Next Steps (lines 367-371)

Changed from 3 steps to 4 steps:
- Added step 1: "Ensure ~/.local/bin is on PATH" (new, needed for ic).
- Added step 3: "Install companion plugins: /clavain:setup" (new).
- Removed old step 3 "/clavain:doctor" (verification is now done inline).
- Renumbered remaining steps.

## Verification

- `bash -n install.sh` passed with no syntax errors.
- The script was NOT executed (per instructions).
- Final file is 378 lines (was 280).

## Structural Observations

The installer now has the following prerequisite check order:
1. `claude` CLI (REQUIRED)
2. `jq` (REQUIRED)
3. `go` >= 1.22 (REQUIRED)
4. `git` (WARN)
5. `bd` / Beads CLI (OPTIONAL)

And the following installation steps:
1. Add marketplace
1b. Update marketplace
2. Install Clavain
3. Install Interverse companion plugins (modpack)
4. Beads init (conditional)
5. **Build intercore kernel (ic)** -- NEW

The verification section now checks:
- Clavain plugin installation
- **ic kernel health** -- NEW

## File

`/home/mk/projects/Demarch/install.sh` (378 lines)
