# CI Test Coverage Matrix

**Bead:** iv-be0ik.2
**Last updated:** 2026-02-26

## Coverage Summary

| Classification | Count | Description |
|---------------|-------|-------------|
| **tests** | 22 | CI runs real tests |
| **smoke-only** | 0 | CI builds but no tests |
| **no-ci** | ~27 | Secret scan only (shell-only plugins, no test suite) |

## Repos With Test CI

### Core (L1)
| Repo | Tests | Framework |
|------|-------|-----------|
| core/intercore | `go test -race` + schema drift | Go |
| core/intermute | `go test -race` | Go |
| core/interband | `go test -race` | Go |
| core/interbench | `go test -race` | Go |

### Apps (L3)
| Repo | Tests | Framework |
|------|-------|-----------|
| apps/autarch | `go test -race` | Go |
| apps/intercom | `vitest` + skill matrix | Node/TypeScript |

### OS (L2)
| Repo | Tests | Framework |
|------|-------|-----------|
| os/clavain | `pytest` + `bats` + shellcheck | Python/Bash |

### SDK
| Repo | Tests | Framework |
|------|-------|-----------|
| sdk/interbase | `go test -race` + `pytest` + bash tests + conformance | Go/Python/Bash |

### Interverse Plugins
| Plugin | Tests | Framework |
|--------|-------|-----------|
| interlock | `go test -race` | Go |
| intermap | `go test -race` | Go |
| intermux | `go test -race` | Go |
| interserve | `go test -race` | Go |
| tldr-swinton | `pytest` | Python |
| intercache | `pytest` | Python |
| interject | `pytest` | Python |
| intermem | `pytest` | Python |
| intersearch | `pytest` | Python |
| interflux | `pytest` (structural) | Python |
| interpath | `pytest` (structural) | Python |
| interwatch | `pytest` (structural) | Python |
| interphase | `bats` + shellcheck | Bash |
| interstat | `bats` + shellcheck | Bash |
| tool-time | `pytest` | Python |

## Shell-Only Plugins (No Test CI)

These plugins are hooks/skills/commands only (no compilable source, no test suite). They have `secret-scan.yml` but no test CI:

intercheck, intercraft, interdev, interdoc, interfin, interfluence, interform, interkasten, interknow, interlearn, interleave, interlens, interline, intername, internext, interpeer, interplug, interpub, interpulse, intersense, intership, interskill, interslack, interspect, intersynth, intertest, intertree, intertrust, tuivision

If any of these adds a test suite in the future, add a `ci.yml` workflow.
