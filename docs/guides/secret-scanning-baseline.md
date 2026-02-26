# Secret Scanning Baseline

This guide defines the Demarch baseline for `iv-446o7.1`:

- PR and scheduled secret scanning
- Standardized scanner/config
- Auditable waiver process with expiration
- Backfill scan workflow for existing history

## Scanner Stack

- **Scanner:** `gitleaks` CLI (`v8.24.2`, pinned in workflow template)
- **Config:** `.gitleaks.toml` (extends gitleaks default rules)
- **Waiver gate:** `scripts/validate-gitleaks-waivers.sh`

## Managed Baseline Files

The baseline sync writes these files into each product repo:

- `.github/workflows/secret-scan.yml`
- `.gitleaks.toml`
- `scripts/validate-gitleaks-waivers.sh`

All managed files include this marker:

`demarch-managed: secret-scan-baseline v1`

Files without the marker are treated as unmanaged and are not overwritten.

## Rollout Commands

Dry-run all product repos:

```bash
scripts/sync-secret-scan-baseline.sh
```

Apply to all product repos:

```bash
scripts/sync-secret-scan-baseline.sh --apply
```

Apply to one repo:

```bash
scripts/sync-secret-scan-baseline.sh --repo core/intercore --apply
```

## Waiver Policy

Inline waivers are allowed only with explicit metadata:

```text
gitleaks:allow reason=<slug> owner=<team-or-user> expires=YYYY-MM-DD
```

Example:

```bash
export DUMMY_TOKEN="fake-value" # gitleaks:allow reason=test-fixture owner=@intercore expires=2026-06-30
```

Rules:

- `reason` is mandatory.
- `owner` is mandatory.
- `expires` is mandatory and must not be in the past.
- Expired/malformed waivers fail CI.

## Backfill Procedure

Run a backfill scan (recent history by default, `180 days`):

```bash
scripts/backfill-secret-scan.sh
```

Run full-history backfill:

```bash
scripts/backfill-secret-scan.sh --full-history
```

Outputs:

- Markdown summary: `docs/reports/security/secret-scan-backfill-YYYY-MM-DD.md`
- Raw JSON/log artifacts: `docs/reports/security/secret-scan-backfill-YYYY-MM-DD/`

## Response Playbook for Findings

When a secret is detected:

1. Revoke/rotate the secret immediately.
2. Remove the secret from current code.
3. Assess whether git history rewrite is required.
4. Add or update tracking in Beads with remediation owner.
5. If suppression is unavoidable, add time-bound waiver metadata and open follow-up.
