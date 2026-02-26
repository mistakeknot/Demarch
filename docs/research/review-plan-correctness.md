# Correctness Review: ic Binary Install Path Plan

**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-24-ic-binary-install-path.md`
**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-24
**Files inspected:**
- `/home/mk/projects/Demarch/os/clavain/hooks/lib-intercore.sh`
- `/home/mk/projects/Demarch/os/clavain/hooks/lib-sprint.sh`
- `/home/mk/projects/Demarch/os/clavain/scripts/lib-routing.sh`
- `/home/mk/projects/Demarch/os/clavain/hooks/session-end-handoff.sh`
- `/home/mk/projects/Demarch/install.sh`

---

## Invariants Established Before Review

These invariants must hold across the changes:

1. **Silent degradation invariant.** When `ic` is absent, hooks must not silently drop state writes or produce wrong throttle decisions. Callers using `|| fallback` are safe. Callers that do not check return codes become unsafe if wrappers change from returning 0 to returning 1.
2. **Sentinel throttle invariant.** `intercore_sentinel_check` returning 0 means "allowed to proceed"; returning 1 means "throttled — skip this work". The two must not be conflated with "ic is missing".
3. **Build correctness invariant.** The `ic` binary install step must produce a working binary regardless of the working directory at install time.
4. **PATH isolation invariant.** `install.sh` must not assume `~/.local/bin` is on `$PATH` at the time of execution.
5. **Trap invariant.** Any EXIT trap registered in `install.sh` must not clobber existing traps and must not clean up resources that were not created in its conditional branch.

---

## Findings

### F1 — P1: Go Version Check Rejects Go 2.x (Task 2, Step 1)

**Location:** `install.sh` proposed Step 1 — Go prerequisite check

**Code from plan:**
```bash
go_ver=$(go version | grep -oP 'go(\d+\.\d+)' | head -1 | sed 's/go//')
go_major="${go_ver%%.*}"
go_minor="${go_ver#*.}"
if [[ "$go_major" -ge 1 ]] && [[ "$go_minor" -ge 22 ]]; then
    success "go ${go_ver} found (>= 1.22)"
else
    fail "go ${go_ver} found but >= 1.22 required"
    exit 1
fi
```

**Failure:** For Go 2.x, `go_major=2` and `go_minor=0`. The condition evaluates as `(2 >= 1) && (0 >= 22)` which is false. The installer exits 1 with "go 2.0 found but >= 1.22 required" — rejecting a version that is clearly sufficient.

This is not a today problem (Go 2 does not exist) but `install.sh` is meant to be long-lived and the logic is mechanically wrong for any major-version increment.

**Verified by test:**
```
go_ver="2.0": major=2, minor=0 -> FAIL
Correctly passing check: [[ "$go_major" -ge 2 ]] || { [[ "$go_major" -eq 1 ]] && [[ "$go_minor" -ge 22 ]]; }
```

**Fix:**
```bash
if [[ "$go_major" -ge 2 ]] || { [[ "$go_major" -eq 1 ]] && [[ "$go_minor" -ge 22 ]]; }; then
```

---

### F2 — P1: `grep -oP` Not Portable to macOS BSD grep (Task 2, Step 1)

**Location:** `install.sh` proposed Step 1 — Go version extraction

**Code from plan:**
```bash
go_ver=$(go version | grep -oP 'go(\d+\.\d+)' | head -1 | sed 's/go//')
```

**Failure:** macOS ships BSD grep which does not support the `-P` (PCRE) flag. On macOS this produces:
```
grep: invalid option -- P
```
`go_ver` becomes `""`. The arithmetic comparisons `[[ "" -ge 1 ]]` silently return false. The installer exits 1 with `fail "go  found but >= 1.22 required"` — an empty version string in the error message — even though Go may be present and sufficient. The installer is documented as curl-fetchable for broad developer use. macOS is a primary developer platform for Claude Code. The existing `lib-intercore.sh` already handles macOS via `stat -c/-f` fallbacks, confirming the project is macOS-aware.

**Fix:** Use POSIX-compatible `grep -Eo` which works identically on BSD and GNU grep:
```bash
go_ver=$(go version | grep -Eo 'go[0-9]+\.[0-9]+' | head -1 | sed 's/go//')
```
The PCRE `\d+` is equivalent to POSIX `[0-9]+` for version number extraction.

---

### F3 — P1: Caller Audit Is Incomplete — `lib-routing.sh:341` Is Not Listed (Task 1)

**Location:** `/home/mk/projects/Demarch/os/clavain/scripts/lib-routing.sh`, line 341

**Actual code in production:**
```bash
kernel_model=$(intercore_state_get "agency.models.${phase}" "$CLAVAIN_RUN_ID" 2>/dev/null) || kernel_model=""
```

**Finding:** The plan's "Callers already defensive" section lists exactly five call sites, all in `lib-sprint.sh`, and asserts "No caller depends on these raw functions returning 0 when `ic` is missing." This assertion is correct but based on an incomplete search. `lib-routing.sh:341` is a sixth caller.

**Is it actually safe?** Yes — the `|| kernel_model=""` fallback handles return 1 correctly. No breakage occurs.

**Why this is P1:** The plan's correctness argument rests on "all callers are defensive." The verification step (Task 1 Step 5) only runs `bash -n` (syntax check), which would pass regardless. Anyone who extends the wrapper using the plan as the source of truth has a stale caller baseline. The fix is to add a semantic grep to the commit checklist:

```bash
grep -rn 'intercore_state_get\|intercore_state_set\|intercore_sentinel_check[^_]' \
    os/clavain/ --include="*.sh"
```
Review every match and confirm `|| fallback` is present.

---

### F4 — P2: `intercore_state_get` Return Code Asymmetry After Change (Task 1, Step 3)

**Location:** `lib-intercore.sh`, proposed `intercore_state_get`

**Proposed code:**
```bash
intercore_state_get() {
    local key="$1" scope_id="$2"
    if ! intercore_available; then printf ''; return 1; fi
    "$INTERCORE_BIN" state get "$key" "$scope_id" 2>/dev/null || printf ''
}
```

**Asymmetry:** When `ic` is absent, the function returns 1 (triggering caller `|| fallback`). When `ic` is present but `state get` fails (DB error, key not found with non-zero exit), the `|| printf ''` on line 2 makes the function return 0 — the exit code of `printf ''`. Callers' `|| fallback` does not trigger.

All current callers also guard with `[[ -z "$result" ]]` checks immediately after, so this does not corrupt data today. But the inconsistency is a latent trap for future callers who rely only on the exit code.

**Consistent fix:**
```bash
intercore_state_get() {
    local key="$1" scope_id="$2"
    if ! intercore_available; then printf ''; return 1; fi
    "$INTERCORE_BIN" state get "$key" "$scope_id" 2>/dev/null
}
```
This propagates the `ic` exit code. All existing callers already have `|| fallback` and are unaffected.

---

### F5 — P2: `intercore_sentinel_check` Returning 1 Conflates "Throttled" With "Missing ic" (Task 1, Step 4)

**Location:** `lib-intercore.sh`, proposed `intercore_sentinel_check`

**Context:** The 3-way exit code contract is documented in `intercore_sentinel_check_or_legacy`:
```
# Exit 0 = allowed, 1 = throttled, 2+ = error → fall through to legacy
```

The plan changes `intercore_sentinel_check` from `return 0` to `return 1` when `ic` is missing. This makes "missing `ic`" mean "throttled" by exit code, contradicting the documented semantic where 1 = "the sentinel is set — skip this work."

**Actual impact:** No hook calls `intercore_sentinel_check` directly (confirmed by grep — only the definition appears in `lib-intercore.sh`). All callers use `_or_legacy` or `_or_die` variants. The change is safe today.

**Semantic issue:** A future caller that reads the function signature and exit-code semantics would conclude "if ic is missing, I am throttled." The correct conclusion should be "if ic is missing, fall through to legacy." Using `return 2` (error/fallthrough) matches the documented 3-way contract and would be handled correctly by `_or_legacy` callers (exit 2+ = fall to legacy path).

**Fix:** Change `return 1` to `return 2` in the missing-ic branch of `intercore_sentinel_check`.

---

### F6 — P2: `INTERCORE_WARNED` Is Per-Process, Not Per-Session (Task 1, Step 1)

**Location:** `lib-intercore.sh`, proposed `INTERCORE_WARNED` global variable

**Plan's claim:** "A one-time stderr warning on first `intercore_available()` failure prevents message spam."

**Actual behavior:** Claude Code hooks are separate bash process invocations. `lib-intercore.sh` is sourced fresh per process. `INTERCORE_WARNED=false` resets on every source. There is no cross-process shared state.

**Interleaving showing the spam that still occurs:**

```
T=0  auto-stop-actions.sh starts, sources lib-intercore.sh
     INTERCORE_WARNED=false (in process A)
T=0  interspect-session-end.sh starts, sources lib-intercore.sh
     INTERCORE_WARNED=false (in process B)
T=1  process A calls intercore_available(): ic not found
     prints "ic: not found — run install.sh or /clavain:setup" to stderr
     INTERCORE_WARNED=true (in process A only)
T=1  process B calls intercore_available(): ic not found
     INTERCORE_WARNED is still false in process B
     prints "ic: not found — run install.sh or /clavain:setup" to stderr
     INTERCORE_WARNED=true (in process B only)
```

With 5 concurrent hooks on a Stop cycle, the user sees up to 5 identical warnings.

**Additional complication:** `lib-intercore.sh` has no double-source guard. When `session-end-handoff.sh` sources `lib-intercore.sh` at line 32, then later sources `lib-sprint.sh` at line 121 (which re-sources `lib-intercore.sh` at line 12), `INTERCORE_WARNED` is reset to `false`. Any suppression from earlier in the same process is lost.

**Severity:** Cosmetic only. The warnings contain correct information. The plan's stated goal of spam prevention is simply not achieved at the scope it implies.

**Fix options:**
- Use a sentinel file `/tmp/clavain-ic-warned-$PPID` keyed on the parent PID to group all hooks in the same session invocation.
- Or rephrase the plan: "suppresses repeated warnings within a single hook invocation's call chain," which is the actual scope of effect.

---

### F7 — P2: Sparse-Checkout Subshell Failure Is Unchecked Under `set -e` (Task 2, Step 2)

**Location:** `install.sh` proposed ic build step, curl-pipe path

**Code from plan:**
```bash
if run git clone --depth=1 --filter=blob:none --sparse https://github.com/mistakeknot/Demarch.git "$IC_TMPDIR/Demarch" 2>/dev/null; then
    (cd "$IC_TMPDIR/Demarch" && git sparse-checkout set core/intercore)
    IC_SRC="$IC_TMPDIR/Demarch/core/intercore"
else
    warn "Could not clone intercore source. ..."
    IC_SRC=""
fi
```

**Failure:** The sparse-checkout runs as a bare statement inside the `then` branch. `install.sh` uses `set -euo pipefail`. A bare subshell `(...)` that exits non-zero (e.g., git version too old for sparse-checkout, network failure mid-clone) causes the parent script to exit immediately under `set -e` — before reaching `IC_SRC=` or the `warn` message. The user sees an abrupt exit with no diagnostic message.

In dry-run mode the behavior is different: `run git clone` is a no-op (returns 0), so the `then` branch is entered. The sparse-checkout subshell then runs against the empty `$IC_TMPDIR/Demarch` directory (no `.git` dir), fails, and the script exits. `IC_SRC` is never set; the dry-run output does not show the expected "would build ic" message.

**Fix:**
```bash
if (cd "$IC_TMPDIR/Demarch" && git sparse-checkout set core/intercore 2>/dev/null); then
    IC_SRC="$IC_TMPDIR/Demarch/core/intercore"
else
    warn "git sparse-checkout failed. Run '/clavain:setup' after cloning the repo."
    IC_SRC=""
fi
```

**Also:** `mktemp -d` is not wrapped in `run()`, so a real temporary directory is created even in `--dry-run` mode. This is harmless (the EXIT trap cleans it up) but inconsistent with the dry-run contract of "no real side effects."

---

### F8 — P2: `bash -c "cd '$IC_SRC'"` Single-Quote Quoting Is Fragile (Task 2, Step 2)

**Location:** `install.sh` proposed ic build step

**Code from plan:**
```bash
if run bash -c "cd '$IC_SRC' && go build -o '${HOME}/.local/bin/ic' ./cmd/ic"; then
```

**Failure condition:** If `IC_SRC` contains a single-quote character (path like `/home/user/it's/intercore`), the shell command becomes malformed:
```
cd '/home/user/it's/intercore' && go build ...
```
This is a syntax error or, in adversarial conditions, a command injection vector.

**Practical risk:** Low but nonzero. `IC_SRC` is set from either a hardcoded relative path or `mktemp -d` output — neither source produces single quotes. However, the `../core/intercore` path check could theoretically resolve through a symlink with a single quote in the path on some systems.

**Better fix — eliminate the subshell entirely.** `go build -C` was added in Go 1.20 and is within the >= 1.22 requirement:
```bash
if run go build -C "$IC_SRC" -o "${HOME}/.local/bin/ic" ./cmd/ic; then
```
`run()` expands `"$IC_SRC"` as a single argument. Spaces and all shell-special characters in the path are handled correctly by word-splitting rules. No subshell, no quoting hazard.

---

## Trap Analysis (Confirmed Not an Issue)

The plan adds `trap 'rm -rf "$IC_TMPDIR"' EXIT` to `install.sh`. Confirmed by grep: `install.sh` has no existing EXIT trap. The new trap is the first and only EXIT handler — no clobbering issue. The invariant holds.

---

## Summary Table

| ID | Severity | Task | Finding |
|----|----------|------|---------|
| F1 | P1 | Task 2 | Go 2.x version check is logically incorrect — rejects valid future major versions |
| F2 | P1 | Task 2 | `grep -oP` not portable to macOS BSD grep — breaks install on a primary developer platform |
| F3 | P1 | Task 1 | `lib-routing.sh:341` is an unchecked sixth caller of `intercore_state_get` — plan's caller audit is incomplete |
| F4 | P2 | Task 1 | `intercore_state_get` has asymmetric return codes: missing ic=1, ic DB error=0 |
| F5 | P2 | Task 1 | `intercore_sentinel_check` returning 1 for missing-ic conflates "throttled" with "error/unavailable" |
| F6 | P2 | Task 1 | `INTERCORE_WARNED` is per-process — N concurrent hooks still emit N warnings |
| F7 | P2 | Task 2 | Sparse-checkout subshell failure is unchecked under `set -e` — abrupt exit with no diagnostic |
| F8 | P2 | Task 2 | `bash -c "cd '$IC_SRC'"` uses single-quote quoting; `go build -C` is correct and eliminates the subshell |

---

## Correctness Verdict

**Task 1 (lib-intercore.sh hardening):** Correct in intent and safe for all verified callers. The exit-code change from 0 to 1 does not break any existing caller. F4 and F5 are semantic improvements that cost nothing to fix in the same diff. F3 requires extending the verification step to include a grep across all hook scripts before commit.

**Task 2 (install.sh):** Has two blocking issues (F1, F2) that cause install failures on macOS and will cause failures on any future Go 2.x release. Both are one-line fixes. F7 and F8 prevent silent failures and remove a code smell.

**Task 3 (setup.md):** Not reviewed — it is markdown interpreted by Claude, not executed Bash. No mechanical invariants to check.

**Recommended actions before implementation:**
1. Fix F2 (`grep -Eo`) and F1 (major-version logic) in Task 2 — both are blocking.
2. Add semantic grep to Task 1 Step 5 to catch F3 (and any future callers).
3. Fix F7 (check sparse-checkout result) and F8 (use `go build -C`) — low-cost, removes fragility.
4. Fix F4 (drop `|| printf ''`) and F5 (use `return 2` for missing-ic) — one line each, semantic cleanup.
