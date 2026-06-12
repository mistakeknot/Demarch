<!-- run-uuid: fed42cc6-b03c-4e8e-a5a8-bc6e14fd3c7c -->

### Findings Index
- P0 | IKP-1 | "install.sh contract" | Auraken-lens binary verification absent before MCP config write
- P1 | IKP-2 | "install.sh contract" | No partial-install rollback (trap EXIT) — failed install worse than none
- P1 | IKP-3 | "install.sh contract" | No post-install smoke test — assembly failure invisible until first session
- P1 | IKP-4 | "auraken-lens binary distribution" | Binary distribution mechanism deferred with no placeholder verification in installer
- P2 | IKP-5 | "Open Questions" | Platform support matrix undeclared — macOS silent failure risk unresolved
- P2 | IKP-6 | "Bundle layout" | CHANGELOG.md in bundle but seeded empty — no v0.1 content until release, creating a gap window
Verdict: risky

### Summary
The install.sh contract describes an installer that performs several dependent operations (version check → skill copy → venv setup → MCP registration) but the brainstorm does not specify: (1) what happens on mid-run failure, (2) whether the auraken-lens binary is verified before the MCP config entry is written, or (3) how the practitioner confirms the assembly succeeded. The lens binary distribution mechanism is explicitly deferred to plan phase, meaning the installer design is incomplete on its most mechanically complex dependency. A failed install that silently exits 0 while writing a broken MCP config is the worst outcome: the practitioner's Hermes profile is degraded with no diagnostic path.

### Issues Found

IKP-1. P0: Auraken-lens binary verification absent before MCP config write — The install.sh contract (§"install.sh contract", step 5) describes building and registering the auraken-lens MCP server and writing a  config snippet, but does not specify that the installer verifies the binary exists and is executable before writing the config entry. If the build step fails silently and the config is written anyway, every subsequent Hermes invocation loads with a broken MCP registration. The practitioner's previously-working Hermes setup now errors on every startup. No rollback path is described.

IKP-2. P1: No partial-install rollback specified — The install.sh contract performs: (1) Hermes version check, (2) profile selection, (3) skill copy, (4) MCP venv setup + build, (5) MCP config write, (6) next-steps print. If step 4 or 5 fails after step 3 has completed, skills are installed but MCP is not, leaving the profile in a partially-installed state. The brainstorm does not specify a  rollback that removes copied skills if later steps fail. A partially-assembled pickup system produces noise, not music — this is the installer equivalent.

IKP-3. P1: No post-install smoke test step — Step 6 of install.sh prints "next steps: how to invoke /auraken, where logs go, how to uninstall" (§"install.sh contract"), but the brainstorm does not describe a smoke test invocation (e.g., run  or invoke the MCP server once with a test prompt and verify exit 0). Without this, 80% of assembly failures are invisible until the practitioner opens a real Hermes session.

IKP-4. P1: Lens binary distribution mechanism deferred with no installer placeholder — §"auraken-lens binary distribution" explicitly defers the choice between (a) pre-built binaries in release assets vs (b)  as prerequisite. The install.sh contract (step 5: "Builds + registers the auraken-lens MCP server") assumes the binary is either present or buildable, but does not specify what happens if neither is true. The installer will hit an undefined state for any practitioner who lacks Go toolchain and for whom pre-built binaries are not yet in the release assets.

IKP-5. P2: Platform support matrix undeclared in installer — §"Open Questions" item 4 defers the WSL2/macOS/Linux support matrix to plan phase with the note "probably just Linux for v0.1, with macOS as 'expected to work, untested'". The install.sh contract does not include a platform detection step that emits a clear "unsupported platform" or "untested platform" warning. A macOS practitioner gets silent behavior differences with no installer-level diagnostic.

IKP-6. P2: CHANGELOG.md seeded empty until release — §"Bundle layout" places CHANGELOG.md in the bundle root but §"CHANGELOG seed" states "v0.1.0 changelog entry written at release time." Between bundle creation and release, CHANGELOG.md is an empty placeholder. If a practitioner somehow installs a pre-release tarball, they find an empty CHANGELOG, which reads as a gap rather than a placeholder. Consider seeding the CHANGELOG with a "Release pending" entry at bundle creation time.

### Improvements

1. Add  to install.sh design — specify that on non-zero exit, copied skills are removed from the profile and any partial MCP config entries are reverted. This makes a failed install idempotent.

2. Add binary verification gate before MCP config write — install.sh should run  (or equivalent) and exit non-zero with a diagnostic if the binary is absent or non-executable, before writing any  config entry.

3. Add smoke test step to install.sh contract — after MCP registration, invoke  once with a minimal test prompt and verify exit 0. Print "Smoke test: passed" / "Smoke test: FAILED — see logs at X" before the next-steps output.

4. Add platform detection and gating — detect OS at install.sh startup; exit non-zero with "unsupported platform: . See INSTALL.md for supported platforms" for untested platforms, or emit a prominent warning for "expected to work, untested" platforms.

5. Resolve binary distribution mechanism before plan phase — the choice of (a) vs (b) should be made before install.sh is written, not deferred into it. The installer cannot be designed without knowing whether it will build from source or unpack a pre-built binary.

<!-- flux-drive:complete -->
