# Dependency Update Policy

**Bead:** iv-446o7.2
**Status:** Active
**Last updated:** 2026-02-26

## Automated Updates

All production repos use GitHub Dependabot with weekly cadence (Mondays). Updates are grouped by minor/patch to reduce PR noise.

### Coverage

| Ecosystem | Repos | Config |
|-----------|-------|--------|
| Go (gomod) | 11 repos (intercore, intermute, interband, interbench, autarch, intermap, interlock, intermux, interserve, clavain, interbase) | `.github/dependabot.yml` |
| Python (pip) | 4 repos (interject, intersearch, tldr-swinton, interstat) | `.github/dependabot.yml` |
| Node (npm) | 6 repos (autarch, intercom, interfluence, interkasten, interlens, tuivision) | `.github/dependabot.yml` |
| Rust (cargo) | 1 repo (intercom) | `.github/dependabot.yml` |
| GitHub Actions | All 20 repos | `.github/dependabot.yml` |

### Grouping Rules

- **Minor + patch**: Grouped into single PR per ecosystem per repo
- **Major**: Individual PRs (require manual review)
- **GitHub Actions**: Grouped separately

## Vulnerability Response SLA

| Severity | Response Time | Action |
|----------|--------------|--------|
| Critical (CVSS >= 9.0) | 24 hours | Patch or mitigate immediately |
| High (CVSS 7.0-8.9) | 7 days | Patch in next release cycle |
| Medium (CVSS 4.0-6.9) | 30 days | Patch when convenient |
| Low (CVSS < 4.0) | 90 days | Bundle with regular updates |

## Review Policy

- **Auto-merge eligible**: Patch updates with passing CI, no breaking changes
- **Manual review required**: Major version bumps, security advisories, deps with known compatibility issues
- **Pinning policy**: Pin exact versions in Go (go.sum), lock files in Python (uv.lock), Node (package-lock.json). Never commit floating ranges for production deps.

## Repos Without Dependabot

Shell-only plugins (most Interverse plugins) have no package manager deps and don't need Dependabot. If a plugin adds a `pyproject.toml`, `go.mod`, or `package.json`, add Dependabot config.
