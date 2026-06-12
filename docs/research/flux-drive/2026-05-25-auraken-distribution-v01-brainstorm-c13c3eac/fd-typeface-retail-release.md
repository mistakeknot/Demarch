<!-- run-uuid: fed42cc6-b03c-4e8e-a5a8-bc6e14fd3c7c -->

### Findings Index
- P1 | TRR-1 | "Distribution mechanism" | One-liner curl URL routes through live repo path — not stable if repo is renamed
- P1 | TRR-2 | "MANIFEST.yaml schema (v1)" | Model compatibility matrix conflates tested and inferred compatibility without qualifier
- P1 | TRR-3 | "auraken-lens binary distribution" | Option (b) uses go install pointing to HEAD — tarball is not self-contained
- P2 | TRR-4 | "Distribution mechanism" | Release tag scheme uses forward slash — curl/tar behavior may differ across platforms
- P2 | TRR-5 | "Versioning" | v0.x breaking-change policy unstated in MANIFEST — practitioners who pin v0.1.0 have no artifact-level warning
- P2 | TRR-6 | "Distribution mechanism" | Signed checksums mentioned but verification instructions absent from INSTALL.md design
Verdict: needs-changes

### Summary
The distribution artifact design has three areas where practitioners are likely to be misled by silence or imprecision. First, the model compatibility matrix lists `gpt-5.5` and `gpt-5.4` without distinguishing tested combinations from inferred ones — and the brainstorm's own note ("observed register drift documented") shows the distinction matters. Second, binary distribution option (b) — `go install github.com/mistakeknot/Sylveste/...` — points to the live repository at whatever version HEAD is at install time, making the v0.1 tarball non-self-contained in a way that contradicts its purpose. Third, the curl one-liner routes through the GitHub repo root rather than a direct release asset URL, creating URL fragility if the repo is renamed or moved. All three are the type of trust-destroying defect that produces refund requests from working designers who pinned a version and got different behavior six months later.

### Issues Found

TRR-1. P1: One-liner curl URL routes through live repo path — not stable if repo is renamed — Section "Distribution mechanism" specifies the one-liner as `curl -fsSL https://github.com/mistakeknot/Sylveste/releases/download/auraken-distribution/v0.1.0/install.sh | bash`. GitHub releases at this URL pattern redirect through the repo root, meaning the URL breaks if the Sylveste repo is renamed, transferred, or made private. A direct release asset URL (via `github.com/mistakeknot/Sylveste/releases/download/...` resolved to the CDN path) is stable against repo renames. The brainstorm does not specify verifying that the URL is direct-asset rather than repo-routed.

TRR-2. P1: Model compatibility matrix conflates tested and inferred compatibility — Section "MANIFEST.yaml schema (v1)" lists `claude-opus-4-7`, `claude-haiku-4-5-20251001`, `gpt-5.5`, `gpt-5.4` under `models:` without distinguishing which were tested vs. which are inferred to work. The brainstorm's own note — "observed register drift documented" for GPT models — demonstrates the distinction is real and consequential. A practitioner installing for gpt-5.5 who reads the compatibility matrix expects validated behavior; what they get is "expected to drift." The type designer equivalent: claiming "weights correctly in InDesign 2024" for a font tested only in Illustrator. MANIFEST.yaml should use a `tested:` / `expected:` sub-field distinction.

TRR-3. P1: go install option points to HEAD — tarball not self-contained — Section "auraken-lens binary distribution" presents option (b) as `go install github.com/mistakeknot/Sylveste/...` as a prerequisite. As written, this installs whatever is at HEAD in the Sylveste repo at install time, not the binary pinned to the v0.1 release. A practitioner who installs v0.1 six months after release via option (b) may get v0.2 binary behavior paired with v0.1 SKILL.md — exactly the scenario MANIFEST.yaml's compatibility range exists to prevent. If option (b) is retained, it must specify the exact module path with a version tag: `go install github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0`.

TRR-4. P2: Release tag scheme uses forward slash — Section "Distribution mechanism" uses the GitHub release tag `auraken-distribution/v0.1.0` with a forward slash. Git tags with forward slashes are interpreted as nested tag refs by some tooling; `git fetch --tags` may store this as a subtree reference. The curl one-liner embeds this tag in the URL path, which may render differently in GitHub's release UI vs. the CDN asset path. This does not break in the common case but creates ambiguity for practitioners using non-standard curl/tar configurations. Consider a flat tag scheme: `auraken-v0.1.0`.

TRR-5. P2: v0.x breaking-change policy unstated in MANIFEST — Section "Versioning" states "v0.x = pre-1.0 — breaking changes allowed across minors" and that "v0.1 → v0.2 may break installs (intentional)." This is correct SemVer behavior, but the MANIFEST.yaml schema (§"MANIFEST.yaml schema (v1)") does not include a field that surfaces this policy to practitioners who read the manifest without the brainstorm. A practitioner who pins v0.1.0 in an automated setup script will encounter a breaking v0.2 update with no prior MANIFEST-level warning. Adding a `stability: pre-release` or `breaking_changes_policy: allowed_across_minor` field makes the policy legible at the artifact level.

TRR-6. P2: Signed checksums mentioned but verification instructions absent — Section "Distribution mechanism" specifies "Release assets: tarball of dist/v0.1/, signed checksums, install.sh" but INSTALL.md content (§"install.sh contract", §"INSTALL.md") is not specified to include instructions for verifying the checksums. Practitioners who want to verify the tarball before piping install.sh to bash have no artifact-level procedure. INSTALL.md should include a "Verify the download" section with the exact command to check the signed checksum against the downloaded tarball.

### Improvements

1. Add `tested:` / `expected:` distinction to the models compatibility matrix — e.g., `claude-opus-4-7: {status: tested, notes: "primary validation target"}` and `gpt-5.5: {status: expected, notes: "register drift observed — see INSTALL.md for behavior notes"}`.

2. Pin the go install path to a version tag — `go install github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0` instead of an unversioned path. This makes option (b) as self-contained as option (a).

3. Use a direct CDN asset URL for the one-liner — verify that the install.sh URL resolves to a direct asset path (`objects.githubusercontent.com/...`) rather than a redirect through the repo root before publishing.

4. Consider a flat release tag scheme — `auraken-v0.1.0` rather than `auraken-distribution/v0.1.0` to avoid forward-slash ambiguity in git tooling.

5. Add a `stability` field to MANIFEST.yaml — `stability: pre-release` with a `breaking_changes_policy: allowed_across_minor` note so practitioners who read only the manifest know to expect breaking changes in minor bumps.

6. Add a "Verify the download" section to INSTALL.md — with the exact `sha256sum -c` or `gpg --verify` command practitioners run before executing install.sh.

<!-- flux-drive:complete -->
