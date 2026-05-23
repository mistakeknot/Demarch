# Interverse Plugin Profiles

Interverse plugins are grouped into install profiles so Claude Code and Codex can start with a small daily-use surface and opt into heavier packs explicitly.

## Profiles

- `default`: daily workflow pack for Beads, coordination, TDD, docs, local code context, and next-work selection.
- `review`: multi-agent review, synthesis, integration tracing, model ranking, and quality gates.
- `docs`: AGENTS.md generation, product artifacts, doc freshness, memory synthesis, and project hierarchy.
- `research`: deep research, knowledge compounding, search, and dialectic reasoning.
- `ops`: statusline, Slack, runtime diagnostics, native-app operator loops, tmux/activity surfaces, and experiments.
- `observability`: context pressure, feature metrics, project mapping, profiling, and dashboards.
- `plugin-dev`: plugin lifecycle, skill authoring, MCP CLI, publishing, and agent-native architecture.
- `design`: distinctive interface design and automated UI/UX analysis.
- `mcp`: MCP-heavy companions that should stay opt-in for startup and context performance.
- `all`: every non-internal, non-deprecated first-party plugin.

## Installer Contract

The `default` profile is intentionally smaller than the historical recommended set. Optional profiles are additive operator choices:

```bash
bash ~/.codex/clavain/scripts/install-codex-interverse.sh install --profile review
bash ~/.codex/clavain/scripts/install-codex-interverse.sh install --profile docs
bash ~/.codex/clavain/scripts/install-codex-interverse.sh install --profile all
```

Claude Code uses the same profile vocabulary through Clavain's `scripts/modpack-install.sh`:

```bash
bash scripts/modpack-install.sh --profile=review
bash scripts/modpack-install.sh --profile=docs
```

The inventory ledger emits each plugin's primary profile, visibility, and pack memberships. Deprecated and internal plugins must not appear in ordinary user-facing packs.
