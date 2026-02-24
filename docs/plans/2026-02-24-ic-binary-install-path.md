# ic Binary in Install Path — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** iv-b7ecy
**Phase:** planned (as of 2026-02-24T18:49:00Z)

**Goal:** Build the `ic` binary from source during first-stranger setup, install to `~/.local/bin/`, and make `lib-intercore.sh` fail hard when `ic` is missing.

**Architecture:** Three changes: (1) `install.sh` gains Go prereq check + `ic` build step, (2) `clavain:setup` command gains ic check/build step, (3) `lib-intercore.sh` raw wrapper functions (`intercore_state_set/get`, `intercore_sentinel_check`) propagate errors instead of returning 0. The `_or_legacy` and `_or_die` variants are unchanged — they already handle missing `ic`. A one-time stderr warning on first `intercore_available()` failure prevents message spam.

**Tech Stack:** Bash (install.sh, lib-intercore.sh, setup.md), Go 1.22 (ic build)

---

## Task 1: Harden `lib-intercore.sh` wrapper functions

**Files:**
- Modify: `os/clavain/hooks/lib-intercore.sh:16-51` (intercore_available, state_set, state_get, sentinel_check)

**Context:** Currently `intercore_state_set` returns 0 (success) when `ic` is missing. `intercore_state_get` returns empty string with exit 0. `intercore_sentinel_check` returns 0 (allowed). This silently drops all state writes, reads, and sentinel checks. The `_or_legacy` and `_or_die` variants already handle missing `ic` correctly and MUST NOT be changed.

**Callers already defensive:** `lib-sprint.sh` uses `intercore_state_get ... || existing_tokens="{}"` and `intercore_state_set ... || true` everywhere. `session-end-handoff.sh` gates with `if intercore_available`. No caller depends on these raw functions returning 0 when `ic` is missing.

**Step 1: Add one-time warning flag to `intercore_available()`**

In `os/clavain/hooks/lib-intercore.sh`, add a flag variable and warning after line 16 (`INTERCORE_BIN=""`):

```bash
INTERCORE_BIN=""
INTERCORE_WARNED=false
```

Then inside `intercore_available()`, after the `return 1` on line 25, add the warning:

```bash
intercore_available() {
    if [[ -n "$INTERCORE_BIN" ]]; then return 0; fi
    INTERCORE_BIN=$(command -v ic 2>/dev/null || command -v intercore 2>/dev/null)
    if [[ -z "$INTERCORE_BIN" ]]; then
        if [[ "$INTERCORE_WARNED" != true ]]; then
            printf 'ic: not found — run install.sh or /clavain:setup\n' >&2
            INTERCORE_WARNED=true
        fi
        return 1
    fi
    # Binary exists — check health
    if ! "$INTERCORE_BIN" health >/dev/null 2>&1; then
        printf 'ic: DB health check failed — run '\''ic init'\'' or '\''ic health'\''\n' >&2
        INTERCORE_BIN=""
        return 1
    fi
    return 0
}
```

**Step 2: Change `intercore_state_set` to propagate failure**

Change line 38 from `return 0` to `return 1`:

```bash
intercore_state_set() {
    local key="$1" scope_id="$2" json="$3"
    if ! intercore_available; then return 1; fi
    printf '%s\n' "$json" | "$INTERCORE_BIN" state set "$key" "$scope_id" || return 1
}
```

**Step 3: Change `intercore_state_get` to propagate failure**

Change line 44 to return non-zero:

```bash
intercore_state_get() {
    local key="$1" scope_id="$2"
    if ! intercore_available; then printf ''; return 1; fi
    "$INTERCORE_BIN" state get "$key" "$scope_id" 2>/dev/null || printf ''
}
```

**Step 4: Change `intercore_sentinel_check` to propagate failure**

Change line 50 from `return 0` to `return 1`:

```bash
intercore_sentinel_check() {
    local name="$1" scope_id="$2" interval="$3"
    if ! intercore_available; then return 1; fi
    "$INTERCORE_BIN" sentinel check "$name" "$scope_id" --interval="$interval" >/dev/null
}
```

**Step 5: Verify no caller breaks**

Run: `bash -n os/clavain/hooks/lib-intercore.sh`
Expected: no output (syntax OK)

Verify callers are defensive:
- `lib-sprint.sh:378`: `intercore_state_get ... || existing_tokens="{}"` — handles failure ✓
- `lib-sprint.sh:386`: `intercore_state_set ... || true` — handles failure ✓
- `lib-sprint.sh:489`: `intercore_state_get ... || phase_tokens_json="{}"` — handles failure ✓
- `lib-sprint.sh:1140`: `intercore_state_get ... || existing="{}"` — handles failure ✓
- `lib-sprint.sh:1156`: `intercore_state_set ... || true` — handles failure ✓
- `lib-routing.sh:341`: `intercore_state_get ... || kernel_model=""` — handles failure ✓
- No hook calls raw `intercore_sentinel_check` — they all use `_or_legacy` or `_or_die` variants

**Step 6: Commit**

```bash
git add os/clavain/hooks/lib-intercore.sh
git commit -m "feat(intercore): harden lib-intercore.sh — propagate errors instead of silent degradation"
```

---

## Task 2: Add Go prerequisite + ic build to `install.sh`

**Files:**
- Modify: `install.sh:128-177` (between jq check and beads section)

**Context:** `install.sh` is a curl-fetchable installer. It currently checks for `claude`, `jq`, `git` (optional), `bd` (optional). We're adding `go` as a hard requirement and building `ic` after plugin installation. The build requires the monorepo source — which is available when running `bash install.sh` from a clone, but NOT when piped from curl. For curl-pipe installs, we clone to a temp dir.

**Step 1: Add Go prerequisite check after jq check (after line 127)**

Insert after the jq check block:

```bash
# go (REQUIRED — builds intercore kernel)
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

**Step 2: Add ic build step after Beads init (after line 177)**

Insert a new section after the beads block:

```bash
# Step 4: Build intercore kernel (ic)
log "  Building intercore kernel (ic)..."

# Determine source directory
IC_SRC=""
if [[ -f "core/intercore/cmd/ic/main.go" ]]; then
    IC_SRC="core/intercore"
elif [[ -f "../core/intercore/cmd/ic/main.go" ]]; then
    IC_SRC="../core/intercore"
fi

if [[ -z "$IC_SRC" ]]; then
    # Curl-pipe mode: clone repo to temp dir
    IC_TMPDIR=$(mktemp -d)
    trap 'rm -rf "$IC_TMPDIR"' EXIT
    log "    Cloning intercore source..."
    if run git clone --depth=1 --filter=blob:none --sparse https://github.com/mistakeknot/Demarch.git "$IC_TMPDIR/Demarch" 2>/dev/null; then
        if ! (cd "$IC_TMPDIR/Demarch" && git sparse-checkout set core/intercore); then
            warn "Sparse checkout failed. Run '/clavain:setup' after cloning the repo to build ic."
            IC_SRC=""
        else
            IC_SRC="$IC_TMPDIR/Demarch/core/intercore"
        fi
    else
        warn "Could not clone intercore source. Run '/clavain:setup' after cloning the repo to build ic."
        IC_SRC=""
    fi
fi

if [[ -n "$IC_SRC" ]]; then
    # Ensure ~/.local/bin exists
    run mkdir -p "${HOME}/.local/bin"

    if run go build -C "$IC_SRC" -mod=readonly -o "${HOME}/.local/bin/ic" ./cmd/ic; then
        [[ "$DRY_RUN" != true ]] && success "ic built and installed to ~/.local/bin/ic"
    else
        fail "ic build failed"
        log "  Try manually: go build -C core/intercore -o ~/.local/bin/ic ./cmd/ic"
        exit 1
    fi

    # Initialize ic database
    if [[ "$DRY_RUN" != true ]]; then
        if "${HOME}/.local/bin/ic" init 2>/dev/null; then
            success "ic database initialized"
        else
            warn "ic init returned non-zero (may already be initialized — continuing)"
        fi

        if "${HOME}/.local/bin/ic" health >/dev/null 2>&1; then
            success "ic health check passed"
        else
            warn "ic health check failed — run 'ic health' to diagnose"
        fi
    fi

    # Check if ~/.local/bin is on PATH
    if ! echo "$PATH" | tr ':' '\n' | grep -qx "${HOME}/.local/bin"; then
        warn "~/.local/bin is not on your PATH"
        log "  Add to your shell config: ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
    fi
else
    warn "Skipping ic build (source not available)"
fi
```

**Step 3: Update verification section to check ic**

After the existing Clavain verification (around line 195), add:

```bash
# Verify ic
if command -v ic &>/dev/null; then
    if ic health >/dev/null 2>&1; then
        success "ic kernel healthy"
    else
        warn "ic found but health check failed"
    fi
elif [[ -x "${HOME}/.local/bin/ic" ]]; then
    warn "ic built but not on PATH. Add ~/.local/bin to PATH."
else
    warn "ic not found — kernel features will be unavailable"
fi
```

**Step 4: Update next-steps to mention ic**

Update the next-steps section to reference `ic`:

```bash
log "${BOLD}Next steps:${RESET}"
log "  1. Ensure ~/.local/bin is on PATH:  ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
log "  2. Open Claude Code in any project:  ${BLUE}claude${RESET}"
log "  3. Install companion plugins:        ${BLUE}/clavain:setup${RESET}"
log "  4. Start working:                    ${BLUE}/clavain:route${RESET}"
```

**Step 5: Verify syntax**

Run: `bash -n install.sh`
Expected: no output (syntax OK)

**Step 6: Test dry-run mode**

Run: `bash install.sh --dry-run`
Expected: Shows Go version check, "[DRY RUN] would build ic", no actual build

**Step 7: Commit**

```bash
git add install.sh
git commit -m "feat(install): add Go prerequisite check and ic binary build step"
```

---

## Task 3: Add ic build step to `clavain:setup`

**Files:**
- Modify: `os/clavain/commands/setup.md` (add new step between Step 5 and Step 6)

**Context:** The setup command is a markdown file that Claude Code interprets as a skill. It runs interactively. We add a step that checks for `ic`, builds it if missing, and verifies health. This handles existing users who already have Clavain installed but don't have `ic`.

**Step 1: Add Step 5b after Beads init (after line 149)**

Insert a new step:

```markdown
## Step 5b: Build Intercore Kernel (ic)

Check if the `ic` binary is available:
```bash
command -v ic && ic health
```

If `ic` is not found or health check fails:

1. Check for Go toolchain:
```bash
go version
```
If Go is not found: warn "Go >= 1.22 is required to build ic. Install from https://go.dev/dl/" and skip this step.

2. Find the intercore source. Check these paths in order:
```bash
# If in the Demarch monorepo
ls core/intercore/cmd/ic/main.go 2>/dev/null
# If in a subproject with Demarch parent
ls ../core/intercore/cmd/ic/main.go 2>/dev/null
ls ../../core/intercore/cmd/ic/main.go 2>/dev/null
# Standard clone location
ls ~/projects/Demarch/core/intercore/cmd/ic/main.go 2>/dev/null
```

If source not found: warn "intercore source not found. Clone https://github.com/mistakeknot/Demarch and re-run setup." and skip this step.

3. Build and install:
```bash
mkdir -p ~/.local/bin
go build -C <intercore_source_dir> -mod=readonly -o ~/.local/bin/ic ./cmd/ic
```

4. Initialize and verify:
```bash
ic init
ic health
```

5. PATH check:
```bash
echo "$PATH" | tr ':' '\n' | grep -qx "$HOME/.local/bin"
```
If not on PATH: warn "Add ~/.local/bin to your PATH: export PATH=\"$HOME/.local/bin:$PATH\""

If `ic` is already present and healthy: report "ic kernel: healthy (version X.Y.Z)"
```

**Step 2: Update Step 6 verification to include ic**

In the verification section (around line 226), add ic to the MCP/companions check:

```bash
echo "ic kernel: $(command -v ic >/dev/null 2>&1 && ic health >/dev/null 2>&1 && echo 'healthy' || echo 'not available')"
```

**Step 3: Update Step 7 summary to include ic**

Add to the summary template:

```
ic kernel:         [healthy/not available]
```

**Step 4: Verify the markdown renders correctly**

Read back the file and confirm the step numbering is consistent and the bash blocks are properly fenced.

**Step 5: Commit**

```bash
git add os/clavain/commands/setup.md
git commit -m "feat(setup): add ic kernel build step to clavain:setup"
```

---

## Task 4: Integration testing

**Files:**
- Read: `os/clavain/tests/shell/test_seam_integration.bats` (reference for patterns)
- Run: install.sh, setup, lib-intercore.sh syntax checks

**Step 1: Syntax-check all modified files**

Run:
```bash
bash -n os/clavain/hooks/lib-intercore.sh
bash -n install.sh
```
Expected: no output for both

**Step 2: Verify ic is buildable from source**

Run:
```bash
cd core/intercore && go build -o /tmp/ic-test-$$ ./cmd/ic && /tmp/ic-test-$$ health && rm /tmp/ic-test-$$
```
Expected: build succeeds, health check passes (or shows DB not initialized — that's OK)

**Step 3: Test lib-intercore.sh error propagation**

Run (simulating missing ic):
```bash
(
    export PATH="/usr/bin:/bin"  # remove ic from PATH
    source os/clavain/hooks/lib-intercore.sh
    intercore_state_set "test" "test" '{"x":1}'
    echo "state_set exit: $?"
    result=$(intercore_state_get "test" "test")
    echo "state_get exit: $?, result: '$result'"
    intercore_sentinel_check "test" "test" "60"
    echo "sentinel_check exit: $?"
)
```
Expected:
```
ic: not found — run install.sh or /clavain:setup
state_set exit: 1
state_get exit: 1, result: ''
sentinel_check exit: 1
```
Note: warning should appear only once (first call).

**Step 4: Test install.sh dry-run**

Run: `bash install.sh --dry-run`
Expected: Shows Go check, dry-run ic build message, no actual changes

**Step 5: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address integration test findings"
```
