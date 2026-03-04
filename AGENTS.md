# Demarch — Agent Development Guide

Open-source autonomous software development agency platform (Intercore, Clavain, Interverse, Autarch, Interspect).

## Quick Reference

```bash
bd ready                                  # See available work
git rev-parse --show-toplevel             # Verify which repo you're in
cd interverse/<name> && uv run pytest tests/structural/ -v  # Plugin tests
cd core/intercore && go test ./...        # Kernel tests
ic publish --patch                        # Publish plugin (Go CLI)
scripts/bump-version.sh <ver>             # Publish plugin (shell)
bd close <id> && bd sync && git push      # Complete work
```

## Topic Guides

| Topic | File | Covers |
|-------|------|--------|
| Architecture | [agents/architecture.md](agents/architecture.md) | Overview, glossary, directory layout, dependency chains, compatibility |
| Session Protocol | [agents/session-protocol.md](agents/session-protocol.md) | Agent quickstart, instruction loading order, landing the plane, memory provenance |
| Design Doctrine | [agents/design-doctrine.md](agents/design-doctrine.md) | Philosophy filters, anti-patterns, brainstorming/planning guidelines |
| Development Workflow | [agents/development-workflow.md](agents/development-workflow.md) | Running/testing by module type, publishing, cross-repo changes |
| Plugin Publishing | [agents/plugin-publishing.md](agents/plugin-publishing.md) | Publish gate, version bumping (interbump), ecosystem diagram |
| Beads Workflow | [agents/beads-workflow.md](agents/beads-workflow.md) | Bead tracking, label taxonomy, recovery scripts, roadmap |
| Critical Patterns | [agents/critical-patterns.md](agents/critical-patterns.md) | Six must-know patterns from production failures |
| Prerequisites | [agents/prerequisites.md](agents/prerequisites.md) | Required tools, secrets, Go module path convention |
| Operational Guides | [agents/operational-guides.md](agents/operational-guides.md) | Guide index, prior solutions search, operational notes |

## Session Close Protocol

1. File beads for remaining work (`bd create`)
2. Run quality gates (tests, linters, builds)
3. Close/update beads (`bd close <id>`)
4. **Push** — `git pull --rebase && bd sync && git push`
5. Verify `git status` shows "up to date with origin"

Work is NOT complete until `git push` succeeds. See [agents/session-protocol.md](agents/session-protocol.md) for full details.

<!-- bv-agent-instructions-v1: beads commands and workflow covered in agents/beads-workflow.md -->
