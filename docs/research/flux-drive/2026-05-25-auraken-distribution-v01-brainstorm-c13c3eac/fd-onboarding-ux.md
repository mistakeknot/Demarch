<!-- flux-drive:complete -->
<!-- run_uuid: 57272bdd-9eb0-42d1-8ae7-ed79e4d7aa8a -->

# fd-onboarding-ux — Review

**Target:** docs/brainstorms/2026-05-25-auraken-distribution-v01-brainstorm.md
**Lens:** developer-experience-engineer perspective on the first-time-user journey from INSTALL.md → install.sh → first `/auraken` session.

## Findings Index

- F1 (P1) — First `/auraken` invocation: Hermes may print skill-load boilerplate that violates SKILL.md's "no preamble, no capability announcement" rule on the first contact
- F2 (P1) — INSTALL.md prerequisite framing is undefined: brainstorm does not say whether prerequisites (Hermes, Python 3.11+, optional Go) appear before or after the one-liner
- F3 (P1) — Platform-gap communication: brainstorm says macOS is "expected to work, untested" — placement of this caveat determines whether macOS users hit a silent install-to-wrong-dir scenario
- F4 (P2) — install.sh next-steps output is specified at a high level ("how to invoke /auraken, where logs go, how to uninstall") but no template — wide variance in quality possible
- F5 (P2) — Uninstall path is mentioned but not implemented or specified; "support burden" is the failure shape
- F6 (P2) — One-liner URL is fragile to repo rename or release-tag format change; published in blog posts becomes a dead-link liability
- F7 (P3) — `curl | bash` security caveat is named but the "download and inspect first" alternative is not given concretely
- F8 (P3) — Trajectory log location (`~/.hermes/auraken/trajectories`) is server.py's default but is not surfaced in install.sh's next-steps — users don't learn their thinking is being recorded

## Verdict

The onboarding flow is **promising but underspecified.** The brainstorm names every UX checkpoint but commits to none. The single most user-visible issue is F1 — the very first thing a user sees from `/auraken` may be Hermes scaffolding that contradicts the entire Auraken design (SKILL.md is explicit: no capability statement, no preamble). If the first impression is "Skill auraken loaded. Capabilities: lens_select. What's on your mind?" then v0.1 fails the spec on contact.

Plan phase needs: (a) explicit INSTALL.md outline (sections + order), (b) install.sh output template with exact strings for success and each abort path, (c) decision on macOS positioning, (d) a tested first-invocation transcript demonstrating no Hermes-side preamble leak.

## Summary

The brainstorm correctly identifies that v0.1 ships to users who already have Hermes. The journey is shorter than a from-zero install, but still spans: (1) discover the one-liner, (2) read INSTALL.md, (3) optionally inspect install.sh, (4) run it, (5) see output, (6) invoke `/auraken`, (7) get a response. Each step has a failure mode. The brainstorm names a handful (security caveat, version refusal) but glosses over the ones that determine whether v0.1 feels like a coherent product or a bag of scripts.

The bigger gap: there's no acceptance test for the onboarding flow itself. The recon spike includes `test-conversations.md` for behavioral correctness, but no equivalent for the install experience. Plan phase should produce an INSTALL-SMOKE.md — a walk-through script another developer can execute on a fresh machine and verify each output line matches the documented template.

## Issues Found

### F1 — P1 — First `/auraken` invocation may leak Hermes scaffolding

**Where:** SKILL.md lines 12–14 ("On invocation (`/auraken` with no problem stated), respond with a single short open question and stop. … No status announcement ('Auraken mode on'), no preamble") vs. apps/Auraken/integrations/hermes/README.md §3 acceptance criteria (no mention of suppressing skill-load output).

**Failure scenario:** User types `/auraken`. Hermes loads the skill, prints "Skill auraken loaded. Available tools: lens_select", then hands off to the model. The model responds per SKILL.md with "What's on your mind?" — but the user has already seen the preamble Hermes itself injected. SKILL.md's "no capability announcement" applies to the model's response; it does **not** constrain Hermes's runtime output. The user's first Auraken experience contradicts SKILL.md on first contact.

**Question:** Does Hermes 2026.4.0+ (the declared min) suppress skill-load output, or does install.sh need to set a config flag to do so? The recon README acceptance criteria don't check for this. The brainstorm doesn't either.

**Smallest viable fix:** Plan phase: (a) run `/auraken` on a fresh install and capture the literal byte stream Hermes emits before the model token; (b) if Hermes prints scaffolding, document the config flag that suppresses it (and have install.sh set it) or surface the limitation in INSTALL.md's "known issues" section so users aren't surprised.

### F2 — P1 — INSTALL.md prerequisite ordering undefined

**Where:** brainstorm §"install.sh contract" line 91 ("Detects Hermes install location") and §"Distribution mechanism" lines 99–101 (the one-liner).

The brainstorm tells us install.sh detects Hermes presence and validates the version — but doesn't tell us what INSTALL.md does. A typical low-quality install doc puts the one-liner at the top, then lists prerequisites after. A user copy-pastes the one-liner before reading; install.sh fails because Hermes isn't installed; user is stuck reading error output instead of the docs.

**Failure scenario:** First-screen of INSTALL.md is the curl-bash one-liner. User runs it. install.sh aborts with "Hermes not found" (step 1 fails). The user has to scroll down to read the prerequisite list they already skipped.

**Smallest viable fix:** INSTALL.md outline: (1) one-line "what this installs" framing, (2) prerequisites checklist (Hermes ≥X.Y, Python 3.11+, optional Go for binary), (3) supported platforms (Linux confirmed; macOS expected; Windows/WSL noted), (4) one-liner with curl-bash and the secure "download first" alternative, (5) what install.sh does (steps 1–6), (6) what to do after, (7) uninstall, (8) troubleshooting. Order matters: prereqs before commands.

### F3 — P1 — macOS-untested caveat placement

**Where:** brainstorm §"Open Questions" #4 ("WSL2 / macOS / Linux support matrix for v0.1. … Probably just Linux for v0.1, with macOS as 'expected to work, untested' — surface in MANIFEST").

**Failure scenario:** macOS user reads the README, sees "supported platforms: Linux, macOS, Windows/WSL" (or similar phrasing), runs the one-liner, install.sh appears to succeed (no version check refused it; macOS does have `bash`, `curl`, `python3`), step 5 writes the MCP config to `~/.hermes/config.yaml`. But on macOS, the Hermes config might live in `~/Library/Application Support/hermes/` (XDG convention is not standard on macOS). Install completes; `/auraken` doesn't exist in Hermes. No error surfaces.

The MANIFEST.yaml surface is correct (fd-versioning-compatibility F3 covers it). But UX-side: where does the macOS caveat appear in the user's reading order? If it's only in MANIFEST.yaml, a macOS user never sees it because the one-liner doesn't print the manifest.

**Smallest viable fix:** INSTALL.md's "supported platforms" section explicitly states "Linux: tested. macOS: expected to work; report issues. Windows: not supported; use WSL2." install.sh prints this on macOS at run time too: if `uname -s` returns Darwin, print a one-line "macOS support is untested in v0.1 — proceed with the expectation that you may be the first to hit issues."

### F4 — P2 — install.sh next-steps template missing

**Where:** brainstorm §"install.sh contract" step 6 ("Prints next steps: how to invoke `/auraken`, where logs go, how to uninstall").

The brainstorm names the three pieces of info to surface but provides no template. Wide variance possible:

Bad: "Install complete. Run /auraken to start. Logs in ~/.hermes/. Uninstall: see docs."

Good: explicit commands, file paths, and a follow-up doc link.

**Failure scenario:** User runs install.sh, sees a vague success message, doesn't know exactly what to type next. They try `auraken`, `auraken --help`, `hermes auraken` before discovering it's a slash-command inside hermes. Their first impression is "this thing is poorly documented" before they've even seen Auraken work.

**Smallest viable fix:** Plan phase produces a literal template for the install.sh success-output:
```
Auraken v0.1.0 installed to ~/.hermes/profiles/<chosen>/

Try it:
  $ hermes
  > /auraken

Logs: ~/.hermes/auraken/trajectories/<date>.jsonl
Uninstall: bash ~/.hermes/profiles/<chosen>/.auraken-install/uninstall.sh
Docs: https://github.com/mistakeknot/Sylveste/tree/main/apps/Auraken
```

### F5 — P2 — No uninstall mechanism specified

**Where:** brainstorm step 6 mentions "how to uninstall" in the install.sh output, but no uninstall.sh appears in the bundle layout (lines 32–48).

**Failure scenario:** User installs v0.1, decides Auraken isn't for them, wants to clean up. They follow the printed uninstall instructions. If those instructions are "rm -rf ~/.hermes/skills/auraken && hand-edit ~/.hermes/config.yaml to remove the mcp_servers block", users either fail (and leave dead config) or break their Hermes config (clipping the wrong YAML keys). Support load: weekly "I broke Hermes" issues.

**Question:** Is the install.sh output telling users to run `uninstall.sh` that doesn't exist, or telling them to do manual cleanup the brainstorm hasn't designed?

**Smallest viable fix:** Either (a) ship `dist/v0.1/uninstall.sh` with a clean removal path (reverses install.sh's six steps; reads the install marker file from fd-distribution-installer-safety F2), or (b) downgrade the install.sh next-steps output to honest "Uninstall: manual — see INSTALL.md §Uninstall" and write that section to a tested cookbook level.

### F6 — P2 — One-liner URL fragility

**Where:** brainstorm line 101:
```
curl -fsSL https://github.com/mistakeknot/Sylveste/releases/download/auraken-distribution/v0.1.0/install.sh | bash
```

**Failure scenario:** A future event renames the repo (Sylveste → something), reorganizes monorepo to a subdir, or changes the release-tag format. Every blog post, tweet, and INSTALL.md that quoted the one-liner has a dead link. No 301 redirect happens automatically.

**Question:** Is the `auraken-distribution/v0.1.0` tag format the chosen convention for the foreseeable future? Should the one-liner go through a vanity domain (`get.auraken.sh`) that the project controls and can redirect?

**Smallest viable fix:** Two options:
- (a) Set up a redirector (e.g., a `mistakeknot/sylvst.com` Cloudflare worker the memory file already references) that resolves `get.auraken.sh` to the current canonical GitHub release URL. The published one-liner uses the redirector.
- (b) Accept the fragility for v0.1; document in INSTALL.md that the one-liner is canonical at release time and may need updating for older posts.

### F7 — P3 — Secure-alternative path not concrete

**Where:** brainstorm line 101 ("with the standard 'review before piping to bash' caveat in INSTALL.md").

The brainstorm names the caveat but doesn't give the alternative commands. A typical user who wants to inspect first will need:
```
curl -fsSL https://.../install.sh -o install.sh
less install.sh        # review
bash install.sh        # run after review
```

**Failure scenario:** User reads "review before piping to bash" and doesn't know the canonical two-step. They either pipe to bash anyway (defeating the caveat) or DIY a download that they re-pipe insecurely.

**Smallest viable fix:** INSTALL.md presents the two commands side by side: the one-liner and the "download then run" alternative as a clearly-labeled section.

### F8 — P3 — Trajectory recording not surfaced

**Where:** server.py:139–148 (TrajectoryCapture writes a JSONL record per `lens_select` call) and apps/Auraken/integrations/hermes/README.md acceptance criterion 4 ("Trajectories accumulate to $AURAKEN_TRAJECTORY_DIR").

**Failure scenario:** User installs Auraken. Every thinking-through turn writes a JSON line containing their message text + selected lenses to `~/.hermes/auraken/trajectories/`. The user doesn't know this until they happen to `ls` that directory. Privacy-surprise risk — Auraken's pitch is "thinking partner", not "thinking surveillance".

**Smallest viable fix:** install.sh next-steps output (per F4) includes a line: "Trajectory logging: enabled by default at ~/.hermes/auraken/trajectories/. Disable with `export AURAKEN_TRAJECTORY_DIR=/dev/null` in your shell." Or: INSTALL.md has a "Data collection" section that names what's logged, where, and how to opt out.

## Improvements

- **INSTALL-SMOKE.md as a plan-phase deliverable.** A literal walk-through transcript: "On a fresh Ubuntu 22.04 VM with Hermes 2026.4.0 installed, run this; expect this output line-by-line." Catches F1, F2, F4 in one pass.
- **install.sh output template is the deliverable.** Brainstorm's "prints next steps" is too vague to test; the template is testable and reviewable.
- **Decide the macOS story before v0.1 ships.** Even "we don't support macOS" is a story; the brainstorm's "expected to work, untested" reads as an avoided decision.
- **Surface trajectory recording in install.sh.** Privacy-visible behavior should not be discovered by `ls`; it should be in the success-output the user reads.
- **Use the install marker file (fd-distribution-installer-safety F2) as the uninstall.sh input.** Reverses the six steps deterministically; no hand-edited YAML.
