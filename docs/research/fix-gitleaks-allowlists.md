# Fix Gitleaks Secret Scan Failures — All Repos

Date: 2026-02-25 (updated 2026-02-25)

## Problem

Four repos in the Demarch monorepo had gitleaks secret scan failures (13 findings total):

1. **Intercore** (`core/intercore`) — 8 findings: synthetic test fixtures (fake JWTs, API keys, GitHub PATs) in `redaction_test.go`, `state_test.go`, `test-integration.sh`, plus a quoted key in a research doc.
2. **Interject** (`interverse/interject`) — 3 findings of the same `EXA_API_KEY` in historical commits across `plugin.json`, `interject-scan.service`, and `interject-cron`.
3. **Intersynth** (`interverse/intersynth`) — 1 finding of a quoted `EXA_API_KEY` in `docs/research/audit-plugin-version-mismatches.md`.
4. **Clavain** (`os/clavain`) — 1 finding of a synthetic test fixture `"client_secret": "pi_456_secret_789"` in `galiana/evals/golden/synth-stale-docs/input/README.md`.

## Key Finding: `fingerprints` Not Supported in `.gitleaks.toml`

The original plan called for adding `fingerprints` entries to `[[allowlists]]` blocks in `.gitleaks.toml`. This does NOT work in gitleaks v8.24.2. Investigation revealed:

- **`[[allowlists]]` in `.gitleaks.toml`** only supports: `description`, `condition`, `commits`, `paths`, `regexTarget`, `regexes`, `stopWords`
- **`fingerprints` are NOT a valid field** in any `.gitleaks.toml` allowlist section (confirmed by reading the gitleaks Go source config struct at `config/config.go`)
- **Fingerprints belong in `.gitleaksignore`** — a separate file that gitleaks auto-discovers from the repository root directory
- The `[allowlist]` (singular) section also does not support `fingerprints` — same struct, same fields

### Tested approaches

| Approach | Result |
|----------|--------|
| `[[allowlists]]` with `fingerprints = [...]` | Silently ignored — leaks still found |
| `[allowlist]` with `fingerprints = [...]` | Silently ignored — leaks still found |
| `[allowlist]` with `commits = [...]` | Works — but allowlists entire commits, too broad |
| `.gitleaksignore` with fingerprints (one per line) | Works — precise per-finding suppression |

### Discovery path

Gitleaks auto-discovers `.gitleaksignore` from the repo path (last positional argument to `gitleaks git`). The `--gitleaks-ignore-path` / `-i` flag can override this, but defaults to `.` relative to the scanned repo.

## Changes Made

### Interject (`interverse/interject`)

**`.gitleaksignore`** (new file):
```
# EXA_API_KEY in deployment configs — key rotated, historical commits
b67f2474f9a05a000b9d196bea5b3526c17eb7d3:.claude-plugin/plugin.json:generic-api-key:41
6a2fda12c67a7fa470cef0b4b5b51b4700bb303c:config/interject-scan.service:generic-api-key:14
6a2fda12c67a7fa470cef0b4b5b51b4700bb303c:config/interject-cron:generic-api-key:6
```

**`config/interject-scan.service`** line 14 — removed hardcoded key:
```diff
-Environment=EXA_API_KEY=eba9629f-75e9-467c-8912-a86b3ea8d678
+Environment=EXA_API_KEY=
```

**`config/interject-cron`** line 6 — removed hardcoded key:
```diff
-EXA_API_KEY=eba9629f-75e9-467c-8912-a86b3ea8d678
+EXA_API_KEY=
```

**`.gitleaks.toml`** — unchanged (reverted to original; fingerprints don't belong here).

### Clavain (`os/clavain`)

**`.gitleaksignore`** (new file):
```
# Synthetic test fixtures in galiana eval golden files — not real secrets
c49353fc1e9763b0df8b9582f7da78c9ffc51bcf:galiana/evals/golden/synth-stale-docs/input/README.md:generic-api-key:66
```

**`.gitleaks.toml`** — unchanged.

### Intercore (`core/intercore`)

**`.gitleaksignore`** (new file):
```
# Synthetic test fixtures in redaction engine tests — not real secrets
f127495eb5a8259cf32fdc58a89ff66d748797cc:internal/redaction/redaction_test.go:jwt:84
f127495eb5a8259cf32fdc58a89ff66d748797cc:internal/redaction/redaction_test.go:generic-api-key:116

# Synthetic test fixtures in state payload validation tests — not real secrets
164ae2607cc928b6c0786311ab1372381ce2ae57:test-integration.sh:generic-api-key:65
164ae2607cc928b6c0786311ab1372381ce2ae57:internal/state/state_test.go:generic-api-key:254
164ae2607cc928b6c0786311ab1372381ce2ae57:internal/state/state_test.go:github-pat:255
164ae2607cc928b6c0786311ab1372381ce2ae57:internal/state/state_test.go:generic-api-key:256
164ae2607cc928b6c0786311ab1372381ce2ae57:internal/state/state_test.go:jwt:257

# Quoted API key in research doc — not a live credential
541bc24f845600f27da30964ffe45a2bc3504478:docs/research/fd-safety-review-interspect.md:generic-api-key:159
```

### Intersynth (`interverse/intersynth`)

**`.gitleaksignore`** (new file):
```
# Quoted EXA_API_KEY in research doc — not a live credential (key rotated)
dd196698097a8334e9ef04815f83b755ad4d1057:docs/research/audit-plugin-version-mismatches.md:generic-api-key:164
```

## Verification

All 4 repos pass gitleaks with zero findings after the changes:

```
$ /tmp/gitleaks git --no-banner --config core/intercore/.gitleaks.toml --log-opts="--all" core/intercore
10:08PM INF 120 commits scanned.
10:08PM INF scanned ~4101654 bytes (4.10 MB) in 620ms
10:08PM INF no leaks found

$ /tmp/gitleaks git --no-banner --config interverse/interject/.gitleaks.toml --log-opts="--all" interverse/interject
9:28PM INF 34 commits scanned.
9:28PM INF scanned ~926413 bytes (926.41 KB) in 298ms
9:28PM INF no leaks found

$ /tmp/gitleaks git --no-banner --config interverse/intersynth/.gitleaks.toml --log-opts="--all" interverse/intersynth
10:09PM INF 28 commits scanned.
10:09PM INF scanned ~66641 bytes (66.64 KB) in 175ms
10:09PM INF no leaks found

$ /tmp/gitleaks git --no-banner --config os/clavain/.gitleaks.toml --log-opts="--all" os/clavain
9:28PM INF 614 commits scanned.
9:28PM INF scanned ~11922304 bytes (11.92 MB) in 1.95s
9:28PM INF no leaks found
```

## Commits

- **Intercore**: `d683eb9` — `fix(ci): allowlist test fixture secrets in gitleaks scan`
  - Files: `.gitleaksignore` (new)
  - Pushed to `main` on `github.com/mistakeknot/intercore`

- **Interject**: `0a0a27d` — `fix(ci): allowlist historical EXA_API_KEY findings and remove hardcoded key`
  - Files: `.gitleaksignore` (new), `config/interject-scan.service`, `config/interject-cron`
  - Pushed to `main` on `github.com/mistakeknot/interject`

- **Intersynth**: `d069b2f` — `fix(ci): allowlist quoted API key in research doc`
  - Files: `.gitleaksignore` (new)
  - Pushed to `main` on `github.com/mistakeknot/intersynth`

- **Clavain**: `9917cac` — `fix(ci): allowlist synthetic test secret in galiana eval fixture`
  - Files: `.gitleaksignore` (new)
  - Pushed to `main` on `github.com/mistakeknot/Clavain`
