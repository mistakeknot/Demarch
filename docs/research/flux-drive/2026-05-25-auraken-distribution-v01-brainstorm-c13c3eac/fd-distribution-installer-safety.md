<!-- flux-drive:complete -->
<!-- run_uuid: 57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a -->

# fd-distribution-installer-safety — Review

**Target:** docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md
**Lens:** release engineer perspective on install.sh atomicity, idempotency, rollback, and Hermes-profile corruption risk.

## Findings Index

- F1 (P0) — Step 5 MCP-registration is non-atomic: a partial failure between venv build and config snippet write leaves a broken half-configured profile
- F2 (P1) — install.sh idempotency contract is asserted but no mechanism is specified for the YAML `mcp_servers:` snippet write
- F3 (P1) — Hermes-version-gate ordering: profile-touching writes (step 4 copies `skills/auraken/`) precede or interleave with version validation (step 3) under one reading of the contract
- F4 (P1) — Profile-discovery fallback (`~/.hermes-*/profiles/` walk) is undefined when zero profiles exist or when the user's Hermes uses `~/.config/hermes/` instead
- F5 (P2) — Exit-path diagnostics: the contract does not require each abort to print "what broke and how to recover"
- F6 (P2) — Binary-prerequisite handling (lens binary absent + option (b) `go install` route) has no specified abort vs. continue contract
- F7 (P3) — No declared lockfile or in-flight marker to prevent two concurrent installs in the same profile

## Verdict

The install.sh contract is implementable, but **three P1/P0 issues block v0.1 ship** as currently written. The biggest is non-atomic MCP registration (F1) — a power-loss or Ctrl-C mid-step-5 can corrupt the profile without a documented recovery path. The brainstorm names six steps but leaves the failure-mode and ordering semantics implicit.

Recommendation: in the plan phase, write a **state-transition table** for install.sh — six steps × {touches?, atomic?, rollback?, exit-template} — and require it as the install.sh design doc.

## Summary

The contract reads cleanly at the bullet level but does not survive a partial-failure walk-through. Three of the six steps (4 = copy skill, 5 = build venv + register MCP, 6 = print next steps) mutate the user's profile, and only steps 1–3 are read-only. The brainstorm declares "idempotent" without specifying the mechanism (re-read existing snippet? check checksum? marker file?), which is the exact gap that lets a `bash -e` install.sh produce divergent state on retry.

## Issues Found

### F1 — P0 — Step 5 MCP-registration is non-atomic

**Where:** brainstorm §"install.sh contract", step 5.

**Failure scenario:** Step 5 says "Builds + registers the `auraken-lens` MCP server (reads `pyproject.toml`, installs into Hermes's MCP-server venv or system, writes a `mcp_servers:` config snippet)". This is at least three filesystem operations: (a) create/update a venv, (b) `pip install -e .` into it, (c) append a YAML block to `~/.hermes/config.yaml` (per the recon README). If (a) and (b) succeed but (c) is interrupted (Ctrl-C, OOM, write-permission denied), the user is left with: a working venv that's not registered, plus a `skills/auraken/` copy already done in step 4. Hermes silently does not see the MCP; `/auraken` partially works (skill loads, lens_select never returns). At 3 AM that user is grepping `~/.hermes/config.yaml`, sees nothing wrong, and has no idea step 5 broke.

**Smallest viable fix:** Require all step-5 writes to land on a side path (`~/.hermes/config.yaml.auraken-stage`) and atomically `mv` into place at the end of step 5. If `mv` fails, the staged file is the rollback artifact. Print its path on every step-5 abort.

**Tied to:** apps/Auraken/integrations/hermes/README.md install §3 (the current manual procedure documents editing `~/.hermes/config.yaml` directly with no atomicity).

### F2 — P1 — Idempotency mechanism unspecified

**Where:** brainstorm §"install.sh contract", lead sentence "Idempotent, prints what it's about to do, asks for confirmation".

**Failure scenario:** Re-running install.sh on an already-installed profile must produce identical state. The brainstorm asserts this but does not say how. Three concrete failure modes:
1. Step 4 (`cp -r skills/auraken/`) on second run: if the user edited their installed SKILL.md, plain `cp` clobbers their edits silently. Plain `cp -r -n` skips silently and leaves stale content.
2. Step 5(c) (`mcp_servers:` block append) on second run: append-without-dedup produces duplicate keys; YAML libraries handle duplicates by last-wins or first-wins depending on parser, and the brainstorm does not say which Hermes uses.
3. Step 5(a) venv on second run: if Python version changed between runs, the venv is stale; if unchanged, recreate is wasteful.

**Smallest viable fix:** install.sh declares an explicit **idempotency model** in INSTALL.md: marker-file based. On run-1, write `~/.hermes/profiles/<chosen>/.auraken-install/v0.1.0.stamp` (manifest hash). On run-2, read the stamp, diff against current MANIFEST, and skip steps already-completed-and-unchanged. If the user has edited installed SKILL.md, refuse the overwrite and exit cleanly with a one-line `--force` instruction.

### F3 — P1 — Version-gate ordering vs. profile mutation

**Where:** brainstorm steps 1–4. Step 3 says "Validates the Hermes version … Refuses if below". Step 4 copies SKILL.md into the profile.

**Failure scenario:** If the gate is ordered after step 4, a refusal in step 3 (after step 4 already ran) has already mutated the profile. The brainstorm's bullets number 1–6 imply step 3 precedes step 4 — confirm this in install.sh and verify **no profile-mutating syscall happens before step 3 succeeds**. The risk is real because step 2 ("asks which profile to install into") is an interactive prompt where some installers helpfully `mkdir -p` the chosen directory before validation.

**Question:** Does the install.sh design treat "no profile writes until version gate passes" as an invariant? If not, please add it.

**Smallest viable fix:** Add explicit `PROFILE_WRITES_OK=0` guard variable in install.sh; only set to 1 after step 3 passes; any function that touches `$PROFILE_DIR/` asserts the guard and aborts otherwise.

### F4 — P1 — Profile-discovery fallback ambiguity

**Where:** brainstorm steps 1 and 2.

**Failure scenario:** Step 1 walks `~/hermes-*/hermes-agent` (binary discovery); step 2 walks `~/.hermes-*/profiles/` (profile discovery). Two undefined cases:
1. **Zero profiles found:** Hermes is installed (binary exists) but never initialized (no profile yet). Does install.sh `mkdir` a fresh `~/.hermes/profiles/default/` and treat that as the install target, or refuse with "run hermes init first"? The latter is safer; the former risks creating a profile in a location Hermes itself doesn't expect.
2. **Non-default config dir:** Hermes supports `HERMES_CONFIG_DIR` env override on systems where the user set one at hermes-install time. The brainstorm's profile walk would miss this entirely. Result: install.sh appears to succeed against a wrong default-dir profile while the user's actual Hermes runs from a different dir.

**Question:** Does the brainstorm assume Hermes profiles always live under `~/.hermes-*/`? If so, please note this assumption in MANIFEST.yaml or INSTALL.md as a supported-environments precondition.

**Smallest viable fix:** Honor `HERMES_CONFIG_DIR` env in install.sh step 1; default to `~/.hermes` only when env is unset; document in INSTALL.md.

### F5 — P2 — Exit-path diagnostic contract

**Where:** brainstorm §"install.sh contract", step 6 ("Prints next steps: how to invoke `/auraken`, where logs go, how to uninstall").

The brainstorm covers the **success-exit** diagnostic. It does not require **failure-exit** diagnostics. Every abort path should print "what broke + minimal recovery" — e.g., step 3 refusal should print the parsed Hermes version, the required range, and "upgrade with: hermes self-update" or equivalent.

**Smallest viable fix:** Add to install.sh contract: "Every non-zero exit prints (a) which step failed, (b) the parsed inputs that caused the failure, (c) one recovery command or a doc link." Bash trap-on-ERR pattern handles this in <10 lines.

### F6 — P2 — Binary-prerequisite handling under option (b)

**Where:** brainstorm §"auraken-lens binary distribution", "(a) Vendors a pre-built binary … OR (b) Documents `go install …` as a prerequisite".

Under option (b), the user is expected to have run `go install` before invoking install.sh. install.sh should detect this and abort cleanly (vs. continuing through step 5 and registering a broken MCP). Required: install.sh probes `$(command -v auraken-lens)` before step 5 and refuses with a clear `go install` instruction if absent. The brainstorm defers (a)/(b) to plan phase but does not flag this install.sh-side dependency.

**Smallest viable fix:** Plan-phase decision: option (a) with (b) as fallback. install.sh detects either case and adapts its preflight check.

### F7 — P3 — No concurrent-install lock

**Where:** brainstorm install.sh contract (omission).

If two terminal windows simultaneously run install.sh against the same profile, both can pass step 3, both copy SKILL.md, both attempt step 5's YAML write. The first writer wins; the second produces interleaved or duplicate keys.

**Smallest viable fix:** `flock -nx "$PROFILE_DIR/.auraken-install.lock"` at the top of install.sh; refuse if already locked.

## Improvements

- **State-transition table as plan-phase deliverable.** One markdown table, six rows (one per step), four columns (touches, atomic, rollback, exit-template). Force the gaps into the open before install.sh code starts.
- **Document the "checksum stamp" idempotency model in MANIFEST.yaml schema.** Add `installation_state` as a known concept so v0.2 has a migration story.
- **Make `--dry-run` a v0.1 requirement, not v0.2.** The brainstorm's "prints what it's about to do, asks for confirmation" already implies dry-run capability; promote it to a flag so QA and demos can exercise install.sh without state.
- **Decide CHANGELOG location early (open question 2).** F1's atomic-config-write pattern is easier with a `dist/v0.1/CHANGELOG.md` (bundle-local) the installer can reference from the marker file.
