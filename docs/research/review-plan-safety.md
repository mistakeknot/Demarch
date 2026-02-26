# Safety Review: ic Binary Install Path Plan

**Date:** 2026-02-24
**Reviewer:** Flux-Drive Safety Agent (fd-safety)
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-24-ic-binary-install-path.md`
**Baseline script:** `/home/mk/projects/Demarch/install.sh`
**Prior install.sh review:** `/home/mk/projects/Demarch/docs/research/safety-review-install-sh.md`
**Risk Classification:** Medium (new network fetch path, source-to-binary build step added; no auth or credentials changed; no irreversible data migration)

---

## Threat Model

This plan extends the existing curl-pipe-bash installer with three new behaviors:

1. Go toolchain prerequisite check
2. Source discovery with fallback to a sparse GitHub clone (new network fetch executed during curl-pipe invocation)
3. Build of a Go binary from cloned source, installed to `~/.local/bin/ic`
4. `ic init` database initialization (new persistent SQLite state)
5. `lib-intercore.sh` wrapper exit-code hardening (local bash library, no network dependency)

**Trust boundary assessment:**
- Public-facing: install.sh is curl-piped from `raw.githubusercontent.com`. The new clone step adds a second unauthenticated GitHub fetch inside a session that was already unauthenticated.
- No credentials: no secrets are stored, generated, or processed at any step. Go build output does not embed credentials. The ic database is local SQLite with no external service dependency.
- Untrusted inputs: GitHub repository content (install.sh transport and the cloned `core/intercore` source) is untrusted transport-layer material. The source code being compiled is the primary new trust surface introduced by this plan.
- Execution context: user-level, no sudo. `ic` runs as the invoking user. Nothing in the plan grants elevated privileges.
- Deployment path: install.sh is run manually by developers. Not a production service installer.

---

## Finding P0-1 — BLOCKER: `run bash -c "cd '$IC_SRC' && ..."` Is a Shell Injection Vector

**Severity:** P0 Blocker
**Finding type:** Security — command injection
**Location:** Plan Task 2 Step 2, line:
```bash
if run bash -c "cd '$IC_SRC' && go build -o '${HOME}/.local/bin/ic' ./cmd/ic"; then
```

### Analysis

`IC_SRC` is populated from two sources: a filesystem path check (relative path derived from CWD) or a `mktemp -d` result. In the happy path both are trusted. However:

1. **Single-quote escape:** The construction `"cd '$IC_SRC' && ..."` single-quotes `IC_SRC` inside a double-quoted outer string. If `IC_SRC` contains a single quote character, it terminates the inner quoting and injects raw shell syntax into the `bash -c` argument. `mktemp` output never contains quotes on standard Linux, but this becomes exploitable if `IC_SRC` is ever set from user-controlled input. Any future contributor who adds logic like `IC_SRC="${1:-$(mktemp -d)}"` would silently introduce a code injection path.

2. **Interaction with existing `eval "$@"` in `run()`:** The baseline safety review (Finding F1 in `docs/research/safety-review-install-sh.md`) already flagged `eval "$@"` in `run()` as Critical. The plan's `run bash -c "..."` callsite passes a compound shell string through `eval`. Variables `$IC_SRC` and `${HOME}` are expanded by the outer shell before reaching `eval`, so double-expansion of already-expanded values is the normal case and is harmless. But combined with `bash -c`, the eval layer means any un-expanded metacharacter in `$IC_SRC` (e.g., a path set via `IC_SRC=$(some_command_with_injection)`) would be re-parsed. The `eval` multiplies the injection surface.

3. **Quoting asymmetry is a maintenance hazard:** `$IC_SRC` is single-quoted while `${HOME}` is double-quoted in the same string literal. This inconsistency is subtle and error-prone; future edits to the line will likely introduce a quoting bug.

### Mitigation

Never pass `IC_SRC` as a string interpolated inside `bash -c`. Use a subshell with `cd` as a direct shell builtin:

```bash
if (
    cd "$IC_SRC" || { fail "Could not cd to $IC_SRC"; exit 1; }
    go build -o "${HOME}/.local/bin/ic" ./cmd/ic
); then
```

The subshell scopes the `cd` so it does not affect the parent shell's working directory. No re-parsing occurs. This eliminates the injection class entirely.

---

## Finding P0-2 — BLOCKER: New Callsite Inherits `eval "$@"` in `run()` Without Prerequisite Fix

**Severity:** P0 Blocker (conditional on sequencing)
**Finding type:** Security — eval propagation
**Location:** `install.sh:92-98` (current), Plan Task 2 Step 2

### Analysis

The baseline safety review (Finding F1) flagged `eval "$@"` in `run()` as a Critical maintenance hazard. The plan adds a new `run` callsite that passes a compound shell string:

```bash
if run bash -c "cd '$IC_SRC' && go build -o '${HOME}/.local/bin/ic' ./cmd/ic"; then
```

This is the first callsite in install.sh that passes a compound shell expression to `run` rather than a single command with arguments. Even if `IC_SRC` never contains metacharacters at runtime today, the `eval` means future edits to the string that accidentally introduce unquoted expansion will create silent code injection. The compound nature of the argument (multiple commands joined by `&&`) is itself only necessary because of `eval` — a direct `"$@"` invocation cannot express `&&` across two commands.

**Sequencing requirement:** Task 2 must not be implemented before `run()` is fixed to use `"$@"` instead of `eval "$@"`. Either:
- (a) Add a preparatory commit that fixes `run()` as a prerequisite to Task 2, or
- (b) Do not use `run bash -c` in the new step at all (use the subshell pattern from P0-1, which avoids `run` entirely for the build step).

Option (b) is simpler and does not require coordinating with the existing `run()` fix.

---

## Finding P1-1 — SHOULD FIX: Sparse Clone Targets `main` With No Commit Pin

**Severity:** P1
**Finding type:** Security — supply chain / transport integrity
**Location:** Plan Task 2 Step 2

### Code (from plan)

```bash
if run git clone --depth=1 --filter=blob:none --sparse \
    https://github.com/mistakeknot/Demarch.git "$IC_TMPDIR/Demarch" 2>/dev/null; then
    (cd "$IC_TMPDIR/Demarch" && git sparse-checkout set core/intercore)
    IC_SRC="$IC_TMPDIR/Demarch/core/intercore"
```

### Analysis

The install.sh already operates under the curl-pipe-bash trust model, where users accept GitHub HTTPS transport as the root of trust. This plan adds a second, independent trust decision: a `git clone` targeting the `main` branch tip from inside a running script.

Two discrete risks compound:

1. **No commit pin:** The clone resolves `main` to whatever HEAD is at clone time. If the repository is compromised between when install.sh was fetched and when the clone runs, a user may install a different version of `ic` than the one associated with the install.sh they retrieved. A commit-pinned clone (`git clone` + `git checkout <sha>`) creates a coherent version contract between the install script and the source it builds.

2. **No post-clone integrity check:** The plan provides no mechanism to verify that the cloned source matches any expected content. `git clone` over HTTPS verifies TLS but does not prove repository integrity beyond what GitHub's own security provides.

3. **Stderr silenced:** `2>/dev/null` on the clone command means a user whose network intercepts `github.com` (misconfigured DNS, captive portal, MITM on HTTP downgrade) will see only the generic warn message and `ic` silently not installed. The silent failure is safe (no binary installed) but the diagnostic is poor.

### Mitigation

**Minimum (P1):** Pin the clone to a specific commit SHA. The install.sh can declare the pinned SHA as a constant, updated in lockstep with each release:

```bash
INTERCORE_COMMIT="<commit-sha-of-known-good-state>"
git clone --depth=1 --filter=blob:none --sparse \
    https://github.com/mistakeknot/Demarch.git "$IC_TMPDIR/Demarch" 2>/dev/null \
    && git -C "$IC_TMPDIR/Demarch" checkout "$INTERCORE_COMMIT" 2>/dev/null
```

**Stronger (P2):** After clone, verify a checksum of `core/intercore/go.sum` or a sentinel file before building. This adds maintenance burden but is appropriate if ic ever handles sensitive data.

---

## Finding P1-2 — SHOULD FIX: `trap` Cleanup Is Fragile on mktemp Failure and Signals

**Severity:** P1
**Finding type:** Deployment safety — temp directory lifecycle
**Location:** Plan Task 2 Step 2

### Code (from plan)

```bash
IC_TMPDIR=$(mktemp -d)
trap 'rm -rf "$IC_TMPDIR"' EXIT
```

Three specific defects:

1. **No mktemp failure check.** If `mktemp -d` fails (disk full, `/tmp` noexec, permissions), `IC_TMPDIR` is empty. The trap becomes `trap 'rm -rf ""' EXIT`. On most systems `rm -rf ""` is a no-op, but on some implementations an empty argument is treated as `.` or not rejected, which would delete the working directory. Add `|| { warn ...; IC_SRC=""; }` after mktemp.

2. **Single `EXIT` trap clobbers any prior trap.** The current install.sh has no prior `EXIT` trap, so this is not an immediate bug. It is a latent hazard: any future contributor who adds a cleanup handler before this block will have their handler silently replaced. Use the compose pattern: `existing_trap=$(trap -p EXIT); trap "${existing_trap:+$existing_trap; }rm -rf \"$IC_TMPDIR\"" EXIT`.

3. **No SIGINT/SIGTERM handling.** `trap ... EXIT` does not fire when a signal is sent to the shell before the trap is registered, or when a parent process sends SIGKILL (untrappable). For SIGINT (Ctrl+C, which is common during a slow clone), the EXIT trap may not fire in all bash versions. Add `INT TERM`:

```bash
_ic_cleanup() { [[ -n "${IC_TMPDIR:-}" ]] && rm -rf "$IC_TMPDIR"; }
trap _ic_cleanup EXIT INT TERM
```

### Mitigation (consolidated)

```bash
IC_TMPDIR=$(mktemp -d 2>/dev/null) || {
    warn "Could not create temp directory — skipping ic build"
    IC_SRC=""
}
if [[ -n "${IC_TMPDIR:-}" ]]; then
    _ic_cleanup() { [[ -n "${IC_TMPDIR:-}" ]] && rm -rf "$IC_TMPDIR"; }
    trap _ic_cleanup EXIT INT TERM
    ...
fi
```

---

## Finding P1-3 — SHOULD FIX: PATH Check Pattern Is Fragile

**Severity:** P1
**Finding type:** Operational correctness
**Location:** Plan Task 2 Step 2

### Code (from plan)

```bash
if ! echo "$PATH" | tr ':' '\n' | grep -qx "${HOME}/.local/bin"; then
    warn "~/.local/bin is not on your PATH"
```

`grep -qx` matches exact lines. A user with `~/.local/bin/` (trailing slash) or a PATH entry that is a resolved symlink will get a false-positive warning even though the binary is reachable.

No security issue. The suggested export line is correctly escaped for the `log()` function's `printf "%b\n"` format.

### Mitigation

Use the standard POSIX double-colon pattern, which handles trailing slashes and avoids a subprocess:

```bash
if [[ ":${PATH}:" != *":${HOME}/.local/bin:"* ]]; then
    warn "~/.local/bin is not on your PATH"
    log "  Add to your shell config: ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
fi
```

---

## Finding P1-4 — SHOULD FIX: `go build` May Fetch Module Dependencies From Network

**Severity:** P1
**Finding type:** Security — supply chain (third network trust dependency)
**Location:** Plan Task 2 Step 2

### Analysis

`go build ./cmd/ic` satisfies module dependencies by downloading from the Go module proxy (`proxy.golang.org`) if modules are not already in the local cache (`$GOPATH/pkg/mod`). This creates a third network dependency: GitHub (install.sh) → GitHub (clone) → Go module proxy (dependencies). Go's checksum database (`sum.golang.org`) provides integrity verification for module downloads, but only if `go.sum` is present and committed in `core/intercore`.

Key questions the plan does not answer:
- Is `core/intercore/go.sum` committed and included in the sparse checkout?
- Does the sparse checkout `set core/intercore` include `go.sum` at the correct path?

If `go.sum` is absent, `go build` operates in TOFU mode for new dependencies — no integrity verification on first install.

### Mitigation

Verify and document that `core/intercore/go.sum` is committed. Add `-mod=readonly` to the build invocation:

```bash
go build -mod=readonly -o "${HOME}/.local/bin/ic" ./cmd/ic
```

`-mod=readonly` causes the build to fail if `go.mod` or `go.sum` would need updating. This prevents a compromised repository from silently adding new dependencies that `go build` would fetch and link. The build failure is actionable (the user sees why), unlike a silent supply chain fetch.

---

## Finding P2-1 — NICE TO HAVE: `ic init` Failure Warning Misleads on Non-Idempotent Errors

**Severity:** P2
**Finding type:** Operational clarity
**Location:** Plan Task 2 Step 2

### Code (from plan)

```bash
if "${HOME}/.local/bin/ic" init 2>/dev/null; then
    success "ic database initialized"
else
    warn "ic init returned non-zero (may already be initialized — continuing)"
fi
```

If `ic init` fails for any reason other than "already initialized" (not-writable path, disk full, wrong architecture binary), the user receives a false-positive reassurance. Stderr is suppressed (`2>/dev/null`), so no diagnostic output reaches the user. The `ic health` check immediately after may then also fail, leaving the user with a non-functional install and no clear path to diagnosis.

### Mitigation

Capture and classify the error:

```bash
if ic_init_out=$("${HOME}/.local/bin/ic" init 2>&1); then
    success "ic database initialized"
else
    if echo "$ic_init_out" | grep -qi "already\|exists"; then
        success "ic database already initialized"
    else
        warn "ic init returned error: ${ic_init_out}"
        warn "Run '${HOME}/.local/bin/ic init' manually to diagnose"
    fi
fi
```

---

## Finding P2-2 — NICE TO HAVE: `INTERCORE_WARNED` Resets on Re-Source

**Severity:** P2
**Finding type:** Operational safety — state pollution in sourced library
**Location:** Plan Task 1 Step 1

### Code (from plan)

```bash
INTERCORE_BIN=""
INTERCORE_WARNED=false
```

`lib-intercore.sh` is sourced, not executed. Top-level assignments execute on every source. If any hook chain re-sources the file after `INTERCORE_WARNED` has been set to `true`, the flag resets to `false` and the warning fires again, defeating the dedup logic.

In practice, Claude Code hook invocations are separate processes, so re-sourcing in the same process is unlikely. But it is worth guarding:

```bash
INTERCORE_BIN="${INTERCORE_BIN:-}"
INTERCORE_WARNED="${INTERCORE_WARNED:-false}"
```

This uses the existing value if set, initializing only on first source.

---

## Finding P2-3 — NICE TO HAVE: `ls` Used for Existence Check in Skill

**Severity:** P2
**Finding type:** Operational robustness
**Location:** Plan Task 3 Step 1

### Code (from plan)

```bash
ls core/intercore/cmd/ic/main.go 2>/dev/null
ls ../core/intercore/cmd/ic/main.go 2>/dev/null
```

In a skill (markdown interpreted by Claude Code) these are illustrative bash commands. `ls` is a poor existence check — it produces output and exits 2 on missing files. In bash scripts, prefer `[[ -f path ]]`. If this skill is ever converted to a literal script, the `ls` form will generate noise on standard paths that don't exist.

No security issue. Style note only.

### Mitigation

Use `[[ -f path ]] && echo "found"` in bash examples within the skill. `ls` is fine for human-facing diagnostics but not for programmatic existence checks.

---

## Summary: Risk by Finding

| ID | Title | Severity | Exploitable Now | Fix Complexity |
|----|-------|----------|-----------------|----------------|
| P0-1 | `bash -c "cd '$IC_SRC' && ..."` injection | P0 Blocker | Medium (env manipulation + metachar path) | Low — subshell instead of bash -c |
| P0-2 | New callsite inherits `eval "$@"` without prerequisite fix | P0 Blocker (conditional) | Medium (same as P0-1 path) | Low — fix `run()` first or avoid `run bash -c` |
| P1-1 | Clone targets `main`, no commit pin | P1 | Medium (repo compromise between fetch and clone) | Medium — pin SHA constant |
| P1-2 | `trap` fragile: no mktemp check, single EXIT trap, no SIGINT | P1 | Low (disk-full edge case + cleanup leak on Ctrl+C) | Low — guard clauses + named cleanup function |
| P1-3 | PATH check pattern gives false warnings | P1 | No (operational UX only) | Trivial — `[[ ":$PATH:" ]]` |
| P1-4 | `go build` may fetch modules from network without `-mod=readonly` | P1 | Low (Go sum.golang.org mitigates) | Low — add build flag |
| P2-1 | `ic init` failure warning misleading on non-idempotent errors | P2 | No | Low — capture and classify stderr |
| P2-2 | `INTERCORE_WARNED` resets on re-source | P2 | No | Trivial — `:-` default form |
| P2-3 | `ls` used for existence check in skill | P2 | No | Trivial |

---

## Deployment Risk Assessment

### Rollback Feasibility

All mutations introduced by this plan are reversible:

- `~/.local/bin/ic` — reversible: `rm ~/.local/bin/ic`
- ic SQLite database — reversible: locate via `ic health 2>&1 | grep db:` then `rm <path>`
- `lib-intercore.sh` exit-code hardening — reversible: `git revert` the commit
- No changes to `~/.claude/`, no external service mutations, no schema migration

Rollback is executable under incident pressure in under 30 seconds. No irreversible data change is introduced.

### Pre-Deploy Checklist

| Check | Pass Criteria |
|-------|--------------|
| `bash -n install.sh` | Zero syntax errors |
| `run()` does not use `eval "$@"` OR build step does not use `run bash -c` | Confirmed by code review |
| `IC_SRC` never derived from user-controlled input | Code review: only mktemp or hardcoded relative paths |
| `core/intercore/go.sum` committed and in sparse checkout | `git -C $IC_TMPDIR ls-files core/intercore/go.sum` returns non-empty |
| `bash install.sh --dry-run` shows Go check, dry-run build, no actual changes | All `run` calls print `[DRY RUN]` prefix |
| `IC_TMPDIR` cleaned on Ctrl+C (SIGINT) | Manual test: kill during slow clone, verify `/tmp/tmp.*` not left behind |
| PATH check correctly detects `~/.local/bin` with and without trailing slash | Manual test |
| `ic init` failure shows actionable error | Test on system with existing DB and on system with unwritable path |

### Post-Deploy Verification

```bash
# Verify binary installed and healthy
~/.local/bin/ic health && echo "ic: OK"

# Verify PATH advisory
export PATH="$HOME/.local/bin:$PATH"
command -v ic && ic health

# Verify idempotency (run install.sh twice)
bash install.sh --dry-run  # second run should not re-clone or error
```

---

## Go / No-Go Verdict

**No-Go for implementation as written.** Two changes are required before Task 2 can be safely implemented:

1. **Fix `run bash -c "cd '$IC_SRC' && ..."` (P0-1).** Replace with a subshell pattern. This is a two-line change that eliminates the injection class.

2. **Ensure `eval "$@"` in `run()` is fixed before the new callsite is added, OR avoid using `run bash -c` entirely (P0-2).** Using a subshell (P0-1 fix) inherently avoids the `run bash -c` pattern, so fixing P0-1 also satisfies P0-2.

After those two fixes, the plan is safe to implement. The P1 findings (commit pinning, trap hardening, `-mod=readonly`) are strongly recommended and should be addressed in the same implementation task rather than deferred. The total additional effort is approximately 15 lines of bash.
