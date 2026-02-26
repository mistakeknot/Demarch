# Task 3: Add ic Build Step to Clavain Setup Command

## Task Summary

Added Intercore kernel (`ic`) build and verification to the Clavain modpack setup command (`/home/mk/projects/Demarch/os/clavain/commands/setup.md`).

## Changes Made

### 1. Step 5b: Build Intercore Kernel (ic) -- Lines 151-197

Inserted a new section between Step 5 (Beads init) and Step 6 (Verify Configuration). The step follows a graceful degradation pattern:

- **Check first**: `command -v ic && ic health` -- if already present and healthy, just report status and skip.
- **Go toolchain gate**: Checks `go version`; warns and skips if Go not available (>= 1.22 required).
- **Source discovery**: Checks 4 locations in priority order:
  1. `core/intercore/cmd/ic/main.go` (Demarch monorepo root)
  2. `../core/intercore/cmd/ic/main.go` (one level up)
  3. `../../core/intercore/cmd/ic/main.go` (two levels up)
  4. `~/projects/Demarch/core/intercore/cmd/ic/main.go` (standard clone location)
- **Build**: `go build -C <dir> -mod=readonly -o ~/.local/bin/ic ./cmd/ic`
- **Init + verify**: `ic init && ic health`
- **PATH check**: Warns if `~/.local/bin` is not on `$PATH`.

### 2. Step 6 Verification -- Line 287

Added `ic kernel` to the companions check block in the verification section:

```bash
echo "ic kernel: $(command -v ic >/dev/null 2>&1 && ic health >/dev/null 2>&1 && echo 'healthy' || echo 'not available')"
```

This runs after the `beads` check and before the closing code fence, consistent with the existing pattern for companion checks.

### 3. Step 7 Summary Template -- Line 303

Added `ic kernel:` line to the summary output template:

```
Beads:             [status]
ic kernel:         [healthy/not available]
```

## Verification

- Read back the full file (311 lines) and confirmed:
  - All markdown code fences are properly opened and closed
  - Step numbering is consistent: 1, 2, 2b, 3, 4, 5, 5b, 6, 7
  - No orphaned or broken HTML comments
  - The new section follows the same style as existing steps (code blocks, conditional logic, warn-and-skip pattern)

## Design Decisions

- **`-mod=readonly`**: Prevents `go build` from modifying `go.sum` in the intercore source tree. This is appropriate for a setup command that should be non-destructive to source trees.
- **`~/.local/bin` target**: Standard user-local binary location. Consistent with XDG conventions and avoids requiring sudo.
- **Graceful skip on missing prerequisites**: The step warns but does not fail if Go or intercore source is missing. This matches the existing pattern where `qmd` and `oracle` are reported as optional/missing rather than blocking setup.
- **Health check as gate**: Uses `ic health` rather than just `command -v ic` to verify the binary is actually functional, not just present on disk.

## File Modified

- `/home/mk/projects/Demarch/os/clavain/commands/setup.md` -- 3 insertions (Step 5b section, verification line, summary line)
