# Safety Review: install.sh

**Date:** 2026-02-24
**Reviewer:** Flux-Drive Safety Agent (fd-safety)
**File:** `/home/mk/projects/Demarch/install.sh`
**Risk Classification:** Medium
**Threat Model:** Public-facing curl-pipe-bash installer, internet-distributed, runs with the invoking user's full privileges.

---

## Threat Model Determination

This script is fetched directly from `raw.githubusercontent.com` and piped into bash with no integrity verification. The invoking user is typically a developer setting up their local environment; the script runs as that user (not root). There are no credentials handled within the script itself. The installation targets `~/.claude/plugins/cache` and invokes the `claude` CLI, `jq`, `git`, and optionally `bd`.

Key trust boundaries:
- **Fully untrusted:** the transport (HTTPS to GitHub raw) — no checksum or signature verification
- **Conditionally trusted:** the arguments passed by the invoker (flags `--help`, `--dry-run`, `--verbose` only)
- **Trusted:** the `claude`, `jq`, `git`, `bd` binaries already on the host PATH
- **Trusted:** `CACHE_DIR` is derived from `$HOME` which is under user control but not externally injectable

---

## Finding 1 — CRITICAL: `eval "$@"` is an Arbitrary Code Execution Vector

**Severity:** Critical
**Exploitability:** High when the script is saved and re-invoked; Medium in the common curl-pipe-bash pattern
**File:** `/home/mk/projects/Demarch/install.sh`, line 87

### Code

```bash
run() {
    if [[ "$DRY_RUN" == true ]]; then
        printf "${DIM}  [DRY RUN] %s${RESET}\n" "$*"
        return 0
    fi
    debug "exec: $*"
    eval "$@"
}
```

### Analysis

`eval "$@"` re-evaluates all positional parameters as shell code. In this function, `"$@"` is the arguments passed to `run()`, not to the script. The callers are hardcoded string literals:

```bash
run 'claude plugins marketplace add mistakeknot/interagency-marketplace 2>/dev/null || true'
run 'claude plugins install clavain@interagency-marketplace 2>/dev/null || true'
run 'bd init 2>/dev/null || true'
```

Because `run` is called with single-quoted string literals whose content is entirely author-controlled, there is no caller-controllable injection path in the current implementation. However, this is a dangerous pattern for the following reasons:

1. **Future maintenance hazard:** Any future contributor who adds a `run` call using a variable (e.g., `run "claude plugins install $PLUGIN_NAME"`) will silently introduce a command injection vulnerability. The function offers no protection against this.

2. **No need for eval here:** None of the current callsites contain shell constructs that require eval (no pipelines, no variable expansions, no redirections that depend on eval). The redirections `2>/dev/null` and the `|| true` suffix are shell constructs that only work inside eval — but this is itself the root of the problem. See Finding 2.

3. **Path to exploitation if `run` is ever extended to accept user input:** A script evolution like `run "claude plugins install $1"` would immediately allow arbitrary code execution via specially crafted arguments.

### Mitigation

Replace `eval "$@"` with direct execution for the common case. The `2>/dev/null || true` pattern in callers is the only reason eval appears necessary. The fix is to separate the suppression from the `run()` function:

```bash
run() {
    if [[ "$DRY_RUN" == true ]]; then
        printf "${DIM}  [DRY RUN] %s${RESET}\n" "$*"
        return 0
    fi
    debug "exec: $*"
    "$@"
}
```

Then update callers to handle suppression explicitly:

```bash
run claude plugins marketplace add mistakeknot/interagency-marketplace 2>/dev/null || true
run claude plugins install clavain@interagency-marketplace 2>/dev/null || true
run bd init 2>/dev/null || true
```

This is safe because `"$@"` in `run()` expands to the individual arguments, not a string to re-parse. Redirections and `|| true` in callers are still processed by the calling shell context before `run` is invoked.

**Residual risk after fix:** Zero for the injection class. The `|| true` remains caller-level, so the error-suppression behavior is identical.

---

## Finding 2 — HIGH: `|| true` Suppressions Mask Real Failures Without Verification

**Severity:** High (deployment safety)
**Exploitability:** Medium (silent failure leaves the user with a broken installation)
**File:** `/home/mk/projects/Demarch/install.sh`, lines 142, 149, 157

### Code

```bash
run 'claude plugins marketplace add mistakeknot/interagency-marketplace 2>/dev/null || true'
run 'claude plugins install clavain@interagency-marketplace 2>/dev/null || true'
run 'bd init 2>/dev/null || true'
```

### Analysis

All three `run` calls are silenced in two ways simultaneously:
- `2>/dev/null` discards stderr entirely — any error message from `claude plugins` is gone
- `|| true` forces exit code 0 regardless of what happened

The script then attempts post-hoc verification only for the `claude plugins install` step (line 174: checking `CACHE_DIR`). The marketplace add step has no verification at all. If `claude plugins marketplace add` fails (network issue, bad credentials, upstream registry unavailable), the subsequent `install` will silently fail too — but the install failure will look identical to a connectivity problem.

The `success "Marketplace added"` and `success "Clavain installed"` messages on lines 144 and 151 are printed unconditionally (if not `$DRY_RUN`) — they do not represent actual verification of success. A user seeing these green check marks has no reason to investigate further, even if both commands failed.

The `bd init` suppression is lower risk because `bd` is optional and the code block is gated on `HAS_BD`. But if `bd init` fails for a non-obvious reason (permissions, corrupt state), the user gets no signal.

### Mitigation

Capture exit codes explicitly and provide actionable error output:

```bash
# Marketplace add — capture stderr for error reporting
if ! claude plugins marketplace add mistakeknot/interagency-marketplace 2>/tmp/demarch-install-err.txt; then
    warn "Marketplace add returned non-zero. Continuing (may already exist)."
    debug "$(cat /tmp/demarch-install-err.txt)"
fi
```

For `claude plugins install`, the existing directory check on line 174 is the right shape but should also capture and surface the error:

```bash
if ! claude plugins install clavain@interagency-marketplace 2>/tmp/demarch-install-err.txt; then
    fail "Plugin install failed: $(cat /tmp/demarch-install-err.txt)"
    exit 1
fi
```

The "already added" / "already installed" idempotency case should be handled by parsing exit codes or error strings, not by blanket `|| true`.

---

## Finding 3 — MEDIUM: No Transport Integrity Verification

**Severity:** Medium
**Exploitability:** Medium (requires MitM or GitHub compromise)
**File:** `/home/mk/projects/Demarch/install.sh` (installation documentation)

### Analysis

The documented installation method is:

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
```

This is the standard curl-pipe-bash pattern. While `-fsSL` handles HTTPS, there is no checksum or signature verification. If the script content changes (GitHub compromise, DNS spoofing, MitM on a misconfigured client), the user executes arbitrary code with their user privileges.

This is a well-understood limitation of the curl-pipe-bash deployment model. For Demarch's current threat model (developer tool, primarily developer machines, not a production service installer), this risk is within acceptable bounds given that GitHub HTTPS transport provides meaningful protection. However, it should be documented.

### Mitigation (proportional to threat model)

At minimum, document a checksum verification step in the README for users who want to verify before running:

```bash
# Verify before running (optional but recommended)
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh -o /tmp/demarch-install.sh
sha256sum /tmp/demarch-install.sh  # Compare against published hash at docs/install-checksums.txt
bash /tmp/demarch-install.sh
```

For a stronger posture, publish per-release checksums in `docs/install-checksums.txt` and pin the install URL to a specific commit SHA rather than `main`:

```bash
curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/<COMMIT_SHA>/install.sh | bash
```

This is a residual risk acceptable at Medium for a developer tool. Flag for reassessment if Demarch ever targets enterprise or production deployment contexts.

---

## Finding 4 — LOW: Argument Parsing Does Not Prevent Unknown Argument Injection in Piped Context

**Severity:** Low
**Exploitability:** Low (theoretical only in the curl-pipe-bash context)
**File:** `/home/mk/projects/Demarch/install.sh`, lines 41-55

### Code

```bash
for arg in "$@"; do
    case "$arg" in
        --help|-h)
            ...
            ;;
        --dry-run) DRY_RUN=true ;;
        --verbose) VERBOSE=true ;;
        *)
            printf "${RED}Unknown flag: %s${RESET}\n" "$arg"
            printf "Run with --help for usage.\n"
            exit 1
            ;;
    esac
done
```

### Analysis

The argument parsing is correctly locked down — unknown flags exit with code 1. This is the correct defensive posture. No injection risk exists here.

The `--help` handler on line 44 uses `sed -n '2,/^$/p' "$0"` which reads from `$0` (the script itself). In a curl-pipe-bash invocation, `$0` is typically `bash` or `-bash`, not a file path. This means `--help` in a piped context will silently print nothing (or a bash error), not the usage message. This is a documentation/usability issue, not a security issue.

### Mitigation

Embed the usage string as a heredoc constant rather than reading from `$0`, so it works consistently in both invocation modes:

```bash
show_help() {
    cat <<'EOF'
install.sh — Curl-fetchable installer for Demarch (Clavain + Interverse)

Usage:
  curl -fsSL https://raw.githubusercontent.com/mistakeknot/Demarch/main/install.sh | bash
  bash install.sh [--help] [--dry-run] [--verbose]

Flags:
  --help      Show this usage message and exit
  --dry-run   Show what would happen without executing
  --verbose   Enable debug output
EOF
}
```

---

## Finding 5 — LOW: `CACHE_DIR` Expansion Under `set -u` with Missing `$HOME`

**Severity:** Low
**Exploitability:** Very low (only on misconfigured systems without `$HOME`)
**File:** `/home/mk/projects/Demarch/install.sh`, line 38

### Code

```bash
CACHE_DIR="${HOME}/.claude/plugins/cache"
```

### Analysis

Under `set -euo pipefail` (line 13), an unset `$HOME` would cause the script to abort at line 38 with an "unbound variable" error before any installation occurs. This is actually safe behavior — an unset `$HOME` indicates a seriously broken environment and failing early is correct.

However, the error message produced by bash (`install.sh: line 38: HOME: unbound variable`) is cryptic. A user on a minimal system (e.g., running via `sudo` without preserving env) would not understand what went wrong.

### Mitigation

Add an explicit check before the variable assignment:

```bash
if [[ -z "${HOME:-}" ]]; then
    fail "HOME environment variable is not set. Cannot determine plugin cache path."
    exit 1
fi
CACHE_DIR="${HOME}/.claude/plugins/cache"
```

---

## Finding 6 — LOW: `debug` Logging Outputs to Stdout via `printf`

**Severity:** Low (operational)
**File:** `/home/mk/projects/Demarch/install.sh`, lines 63-66

### Code

```bash
debug() {
    if [[ "$VERBOSE" == true ]]; then
        printf "${DIM}  [debug] %s${RESET}\n" "$*"
    fi
}
```

### Analysis

All logging functions including `debug` write to stdout (the default for `printf`). In a curl-pipe-bash invocation, stdout is the bash process's stdin — but since the script is fully downloaded before execution (due to how piped bash works), this does not create a code injection issue.

The practical operational concern: if the script is ever used in a context where its stdout is captured (e.g., `output=$(bash install.sh --verbose)`), debug output would be mixed into the captured value. This is a minor usability issue.

### Mitigation

Direct all logging output to stderr:

```bash
debug() {
    if [[ "$VERBOSE" == true ]]; then
        printf "${DIM}  [debug] %s${RESET}\n" "$*" >&2
    fi
}
```

The same applies to `log`, `success`, `warn`, and `fail`. All user-facing status output belongs on stderr; stdout should be reserved for machine-parseable output if any is ever added.

---

## Deployment Risk Assessment

### Pre-Deploy Checklist

These invariants must hold before distributing the updated script:

| Check | Pass Criteria |
|-------|--------------|
| `bash -n install.sh` | Zero syntax errors |
| `shellcheck install.sh` | Zero warnings at SC2 level or higher |
| `--dry-run` produces expected output with no side effects | All `run` calls print `[DRY RUN]` prefix, no files created |
| `--help` works in both `bash install.sh --help` and `curl ... \| bash` contexts | Usage text printed in both modes |
| Script is idempotent: running twice yields same state | Second run does not error on "already installed" |
| Test on a machine without `bd` installed | `HAS_BD=false` path, no failure |
| Test on a machine without an existing Claude config | `~/.claude/` does not exist, script creates cleanly |

### Rollback Feasibility

The script is an installer — it makes two mutations to the user's environment:
1. `claude plugins marketplace add` — adds a marketplace entry to Claude config
2. `claude plugins install clavain@interagency-marketplace` — installs files into `~/.claude/plugins/cache/`

Both are reversible:
```bash
claude plugins uninstall clavain
claude plugins marketplace remove mistakeknot/interagency-marketplace
```

There is no database migration, no schema change, and no file outside `~/.claude/` is modified. Rollback is straightforward and documented in the `claude` CLI help.

**Verdict:** Deployment risk is Low. The installation is fully reversible. The only irreversible consequence of a bad install is user confusion from silent failure.

---

## Summary: Risk by Finding

| ID | Title | Severity | Exploitable Now | Fix Complexity |
|----|-------|----------|-----------------|----------------|
| F1 | `eval "$@"` in `run()` | Critical | No (but maintenance hazard) | Low — 5-line change |
| F2 | `|| true` masking real failures | High | Yes (silent broken install) | Low — add exit code checks |
| F3 | No transport integrity verification | Medium | Medium (requires MitM) | Medium — checksum docs |
| F4 | `--help` broken in piped context | Low | No | Low — embed help string |
| F5 | Cryptic error on missing `$HOME` | Low | No | Low — guard clause |
| F6 | Logging on stdout | Low | No | Low — add `>&2` |

---

## Go / No-Go Verdict

**No-Go for distribution as-is.** Two changes are required before this script should be linked from public documentation:

1. **Replace `eval "$@"` with `"$@"`** (Finding 1). This is the highest-priority change because `eval` is a footgun that will eventually be misused as the script grows. The fix is trivial and eliminates an entire vulnerability class.

2. **Add exit-code checking for `claude plugins install`** (Finding 2). The success messages are currently misleading. At minimum, the installation step must not print "Clavain installed" when the underlying command failed. The existing directory-check verification on line 174 is on the right track but is the only gate, and it is too coarse.

All other findings are Low severity and can be addressed in follow-up without blocking distribution. They should be filed as beads.
