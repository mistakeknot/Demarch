# Correctness Review: install.sh

**File reviewed:** `/home/mk/projects/Demarch/install.sh`
**Date:** 2026-02-24
**Reviewer:** Julik (Flux-drive Correctness Reviewer)

---

## Invariants the Script Must Preserve

Before listing findings, the invariants that must hold:

1. `--help` must print correct usage and exit 0, in all invocation contexts the header documents.
2. `--dry-run` must cause zero side effects — no filesystem writes, no network calls that mutate state.
3. Running the script twice on a system that already has Clavain installed must be safe (idempotent).
4. The beads init conditional must skip correctly when `bd` is absent or the working directory is not a git repo.
5. Errors during installation must not be silently swallowed when they indicate a real failure.
6. The verification step must actually verify that installation succeeded, not just that a directory exists.

---

## Finding 1 — `--help` Breaks When Piped (MEDIUM)

**Claim:** The header documents `curl -fsSL ... | bash` as a valid invocation.

**Reality:** `--help` is non-functional in the piped invocation context, and in the specific case where `bash -s -- --help` is used after piping, the `--help` handler reads garbage.

**Mechanism:**

```bash
--help|-h)
    sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
    exit 0
    ;;
```

When the script runs as `bash install.sh --help`, `$0` is `"install.sh"` — the script file. `sed` reads it correctly and prints the comment block. This works.

When the script is fetched via `curl ... | bash`, the shell's `$0` is `"bash"` — the binary at `/usr/bin/bash`. If a user attempts `curl ... | bash -s -- --help`, the shell still sets `$0 = "bash"`. `sed` then attempts to read the bash binary as text and emits binary garbage (measured at ~10 KB of binary output). It does not exit with a useful error — it exits 0 after spewing garbage, because `sed` successfully opened and processed the file.

Additionally: passing flags to a piped `curl | bash` invocation is inherently broken. You cannot pass `--help` to the script being piped, only to `bash` itself. The header comment documents `curl ... | bash` as the primary install method, but provides no guidance that `--help` only works in the `bash install.sh` form. This is a misleading documentation claim, not just a code bug.

**Concrete failure sequence:**
1. User reads header, sees `curl -fsSL ... | bash` as the primary install method.
2. User wants to preview first, tries `curl -fsSL ... | bash -s -- --help`.
3. `$0 = "bash"`. `sed -n '2,/^$/p' /usr/bin/bash` opens the ELF binary.
4. Terminal receives ~10 KB of binary garbage. Script exits 0.
5. User has no idea what flags exist.

**Fix:** Replace the `$0`-based help with a heredoc that is independent of file identity:

```bash
--help|-h)
    cat <<'USAGE'
install.sh — Curl-fetchable installer for Demarch (Clavain + Interverse)

Usage:
  curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
  bash install.sh [--help] [--dry-run] [--verbose]

Flags:
  --help      Show this usage message and exit
  --dry-run   Show what would happen without executing
  --verbose   Enable debug output
USAGE
    exit 0
    ;;
```

This works regardless of `$0` and is immune to the pipe invocation problem.

---

## Finding 2 — `--dry-run` Does Not Protect Against Prerequisite Exits (LOW-MEDIUM)

**Claim:** `--dry-run` shows "what would happen without executing."

**Reality:** If `claude` or `jq` is absent, the script exits with an error before `DRY_RUN` is used for anything. A user on a machine without Claude Code who wants to preview what the installer does cannot do so.

```bash
# Lines 99-116 — runs regardless of DRY_RUN
if command -v claude &>/dev/null; then
    success "claude CLI found"
else
    fail "claude CLI not found"
    exit 1      # <-- exits before any installation output is shown
fi
```

In a strict `--dry-run` semantics, the check itself is acceptable (it is read-only), but the hard exit means the dry-run user never sees the "Installing..." section at all. This is a documentation mismatch: the flag promises to show what would happen, but on a clean machine (the most common dry-run scenario), it shows nothing beyond "claude not found."

**Fix (minimal):** Add a `--dry-run` bypass around the `exit 1` calls in prerequisite checks, or downgrade them to `warn` under `--dry-run`:

```bash
else
    fail "claude CLI not found"
    if [[ "$DRY_RUN" != true ]]; then
        exit 1
    fi
    warn "  (dry-run: continuing anyway to show install steps)"
fi
```

---

## Finding 3 — `--dry-run` Runs `git rev-parse` as a Condition Check (INFORMATIONAL)

**Reality:** The beads init block at line 155:

```bash
if [[ "$HAS_BD" == true ]] && git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
```

The `git rev-parse` call is not wrapped in `run()`. It executes unconditionally even under `--dry-run`. This command is read-only (it only inspects the git index), so there is no state mutation. The dry-run contract is technically preserved.

However, the double redirect `&>/dev/null 2>&1` is redundant. `&>/dev/null` redirects both stdout and stderr to `/dev/null`. The subsequent `2>&1` then redirects stderr to stdout, which is already `/dev/null` — a no-op. This does not cause a bug but is misleading to a reader trying to understand the intent.

**Fix:** Use either `&>/dev/null` or `>/dev/null 2>&1`, not both.

---

## Finding 4 — ALL Installation Errors Are Silently Swallowed (HIGH)

**Claim:** The script uses `set -euo pipefail` at line 13, which should cause it to fail fast on errors.

**Reality:** Every installation command passed to `run()` includes `|| true` appended to the command string:

```bash
run 'claude plugins marketplace add mistakeknot/interagency-marketplace 2>/dev/null || true'
run 'claude plugins install clavain@interagency-marketplace 2>/dev/null || true'
run 'bd init 2>/dev/null || true'
```

Inside `run()`:
```bash
eval "$@"
```

`eval` executes the string `claude plugins marketplace add ... 2>/dev/null || true`. The `|| true` is part of the evaled string, so the entire pipeline always exits 0, regardless of what `claude plugins` does. `set -e` never fires on these lines.

Combined with `2>/dev/null`, which hides all stderr output, the result is:
- If `claude` is installed but the marketplace is already locked, you get silence and a success tick.
- If `claude plugins install` returns a non-zero exit for any reason (network error, auth failure, corrupted cache), you get silence and a success tick.
- If the `bd init` writes to a read-only filesystem, you get silence and a success tick.

The `set -euo pipefail` on line 13 provides a false safety guarantee. It protects only the scaffolding code (argument parsing, prerequisite detection), not the actual work.

**This is the most dangerous finding.** An install that silently fails leaves the user in a broken state they cannot diagnose.

**Fix:** Remove `|| true` from the run() calls. Let `run()` propagate failures:

```bash
run() {
    if [[ "$DRY_RUN" == true ]]; then
        printf "${DIM}  [DRY RUN] %s${RESET}\n" "$*"
        return 0
    fi
    debug "exec: $*"
    eval "$@"      # now failure propagates to set -e
}
```

Then handle known-safe idempotent cases explicitly:

```bash
# For marketplace: check if already added before adding
log "  Adding interagency-marketplace..."
if ! claude plugins marketplace list 2>/dev/null | grep -q 'interagency-marketplace'; then
    run 'claude plugins marketplace add mistakeknot/interagency-marketplace'
fi
```

If the `|| true` is intentional because `claude plugins` has no good idempotency guarantees, then at minimum: capture exit codes and warn rather than silently continue.

---

## Finding 5 — Verification Check Is Not Reliable (MEDIUM)

**Claim (line 174-178):**
```bash
elif [[ -d "${CACHE_DIR}/interagency-marketplace/clavain" ]]; then
    success "Clavain installed successfully!"
else
    fail "Installation may have failed. Run 'claude plugins list' to check."
    exit 1
fi
```

The check is: does the directory `~/.claude/plugins/cache/interagency-marketplace/clavain` exist?

**Problems with this check:**

1. **Stale directory from prior run.** If Clavain was installed previously (any version), the cache directory exists. If the current install attempt failed silently (see Finding 4), the directory still exists from the prior run. The verification reports success even though the new install failed.

2. **Directory presence does not imply working plugin.** The cache directory could exist in a corrupted state (partial clone, interrupted download, `.orphaned_at` marker present). The AGENTS.md critical pattern #3 explicitly calls this out: `.orphaned_at` markers block plugin loading, and removing them is a separate manual step. The verification does not check for `.orphaned_at`.

3. **Version not checked.** The directory `clavain/` is checked, but not `clavain/<version>/`. A downgraded or outdated version would pass verification.

4. **Marketplace not verified.** Step 1 (marketplace add) has no corresponding verification. Only step 2 (clavain install) is checked, and even that check is for the cache path, not for the marketplace registration.

**Failure scenario:**

- First run: `claude plugins install clavain@interagency-marketplace` times out silently (Finding 4), but a prior install of v0.1.0 left `~/.claude/plugins/cache/interagency-marketplace/clavain/0.1.0/`. Directory exists.
- Verification passes.
- User proceeds assuming v0.2.0 is installed. It is not.

**Fix:** Use `claude plugins list` output to verify, rather than filesystem presence:

```bash
if claude plugins list 2>/dev/null | grep -q 'clavain'; then
    success "Clavain installed successfully!"
else
    fail "Installation may have failed. Run 'claude plugins list' to check."
    exit 1
fi
```

This is a functional check, not a filesystem artifact check. If `claude` is not on PATH at this point (impossible given earlier prerequisite check), this still works because the script would have already exited.

---

## Finding 6 — Idempotency Claim Is Conditional on Unknowns (MEDIUM)

**Claim:** The script can be run twice safely.

**Reality:** Idempotency is asserted but not enforced. The script appends `|| true` to all installation commands, which means:

- If `claude plugins marketplace add` on a re-run returns a "already exists" error code, `|| true` swallows it — safe.
- If it returns a "already exists" error AND corrupts state in some way, `|| true` swallows that too.
- If `claude plugins install` on a re-run triggers a cache wipe-and-reinstall (plausible for version mismatches), `|| true` hides any failure from that process.

The script's idempotency is entirely dependent on `claude plugins` being idempotent internally. This is a dependency on undocumented CLI behavior. The `|| true` pattern delegates the idempotency guarantee to the tool rather than the installer.

**The beads init case is the clearest non-idempotency risk:** `bd init 2>/dev/null || true` — if `bd init` is not idempotent (e.g., it resets a `.beads/` database on re-run), running the installer twice in a project that already has beads initialized could corrupt the beads state. The `|| true` hides the result.

**Fix:** Check before acting, rather than act and suppress errors. For beads:

```bash
if [[ "$HAS_BD" == true ]] && git rev-parse --is-inside-work-tree &>/dev/null; then
    if [[ ! -d ".beads" ]]; then
        log "  Initializing Beads in current project..."
        run 'bd init'
        ...
    else
        debug "Skipping bd init (.beads/ already exists)"
    fi
fi
```

---

## Finding 7 — `eval` Usage Is Correct but Unnecessarily Broad (INFORMATIONAL)

The `run()` function uses `eval "$@"` to execute commands. All current call sites pass a single pre-formed string argument with a fully-quoted shell command. This works correctly: `eval` sees a well-formed command string.

However, `eval` is broad. If a future call site passes user-controlled input or constructs a command via string interpolation, `eval` becomes a shell injection vector. The current inputs are all hardcoded string literals, so there is no current injection risk.

A safer pattern for this use case:

```bash
run() {
    if [[ "$DRY_RUN" == true ]]; then
        printf "${DIM}  [DRY RUN] %s${RESET}\n" "$*"
        return 0
    fi
    debug "exec: $*"
    "$@"     # positional expansion, not eval
}
```

But this requires callers to pass commands as arrays (`run claude plugins install clavain@interagency-marketplace`) rather than single strings. The current call sites use single-string quoting (`run 'command with args'`), which passes the entire command as `$1`. Switching to positional expansion would require refactoring all call sites. This is a future hygiene item, not a current bug.

---

## Summary Table

| # | Finding | Severity | Invariant Broken |
|---|---------|----------|-----------------|
| 1 | `--help` reads bash binary when piped, outputs garbage | MEDIUM | `--help` must work in all documented invocation contexts |
| 2 | `--dry-run` exits before showing install steps if prerequisites absent | LOW-MEDIUM | Dry-run should preview all steps |
| 3 | Double-redirect `&>/dev/null 2>&1` is redundant | INFORMATIONAL | — |
| 4 | All installation errors silently swallowed by `|| true` + `2>/dev/null` | HIGH | `set -euo pipefail` safety guarantee is illusory |
| 5 | Verification checks stale filesystem path, not functional install | MEDIUM | Verification must confirm working state |
| 6 | Idempotency delegates to undocumented `claude plugins` behavior | MEDIUM | Running twice must be safe |
| 7 | `eval` usage is correct but fragile for future extension | INFORMATIONAL | — |

---

## Priority Order for Fixes

1. **Finding 4 first.** Remove `|| true` from `run()` call sites. Silent failure is the worst outcome for an installer — it leaves users with a broken system they believe is working. A failed install that says "failed" is far better than one that says "succeeded" but installed nothing.

2. **Finding 1 second.** Replace `$0`-based help with a heredoc. This is a two-minute fix and corrects a documented invocation that produces binary garbage.

3. **Finding 5 third.** Switch verification from filesystem presence to `claude plugins list` output. This correctly reflects actual installation state rather than cache artifacts.

4. **Finding 6 fourth.** Add `[[ ! -d ".beads" ]]` guard before `bd init` to make that step provably idempotent regardless of `bd`'s own behavior.

5. **Finding 2 last.** The dry-run/prerequisite interaction is low priority because dry-run is a developer convenience, not a user-facing safety net.
