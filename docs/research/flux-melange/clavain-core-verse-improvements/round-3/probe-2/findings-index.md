# Findings Index — round-3 / probe-2

Lens: `fd-menu-engineering-triage` (menu engineering: stars / puzzles / plowhorses / dogs).
Target: interverse cold-spot fleet (~60 plugins minus the 10 previously deep-dived).
Demand evidence used: `~/.claude/plugins/installed_plugins.json`, `~/.agents/skills/` live links,
`os/Clavain/agent-rig.json` profiles, `core/marketplace/.claude-plugin/marketplace.json`, per-repo git log.

```
SEVERITY | fd-menu-engineering-triage | path | finding [t]
```

CRITICAL | fd-menu-engineering-triage | os/Clavain/agent-rig.json:124 | Load-bearing dog: DEPRECATED interfluence is wired into the installer's `plugins.optional` list, so `install-codex-interverse.sh` can install a plugin whose own README says "Replaced by intervox"; it is also currently installed in Claude Code while the successor intervox is installed nowhere and appears in no rig profile [2026-08-06]
CRITICAL | fd-menu-engineering-triage | interverse/intersense | Ghost install: intersense was ARCHIVED 2026-03-26 (ARCHIVED.md, no `.claude-plugin/plugin.json`) yet remains installed in Claude Code (`intersense@interagency-marketplace` in installed_plugins.json + cache) — an archived plugin still occupies a slot on the menu [2026-08-06]
HIGH | fd-menu-engineering-triage | core/marketplace/.claude-plugin/marketplace.json | Registry lie: interflux's marketplace description still says "Domain detection via intersense, knowledge via interknow" — intersense was archived in March; the registry advertises a dependency that no longer exists [2026-08-06]
HIGH | fd-menu-engineering-triage | interverse/ | f-033 confirmed: 7 plugin dirs missing from marketplace.json — interboxd, intercept, intergraph, interscout, intersense, intersite, lattice (plus `_shared` support dir). Two of them (intercept's gate runtime, lattice's SessionStart reharvest hook) carry runtime machinery invisible to all install/discovery paths [2026-08-06]
HIGH | fd-menu-engineering-triage | core/marketplace/.claude-plugin/marketplace.json:1051-1068 | Deprecated-but-listed: intervoice entry still published at v0.1.1 with "[DEPRECATED — use intervox]" description — a dog kept on the printed menu; retirement should mean removal from marketplace, not a footnote [2026-08-06]
MEDIUM | fd-menu-engineering-triage | interverse/intercache | Dog on auto-start: intercache is in the rig `mcp` profile and installed, meaning its MCP server launches every session, but it ships 0 skills/commands, its post-commit hook is unregistered (no hooks.json in plugin.json), and no consumer is documented — kitchen capacity consumed with no evidence of orders [2026-08-06]
MEDIUM | fd-menu-engineering-triage | interverse/intervox | Hidden star shelved: intervox (tested closed-loop voice engine, 52 tests, supersedes two deprecated plugins) is in the marketplace but absent from every rig profile and not installed anywhere — the successor lost the slot to its own deprecated predecessor [2026-08-06]
MEDIUM | fd-menu-engineering-triage | interverse/interseed, interverse/interloop, interverse/interlore, interverse/interdeploy | Puzzle cluster: four real implementations (interseed has a full MCP server; interdeploy a 3-cycle auto-fix loop) published in marketplace but present in zero rig profiles and zero installs — unpromoted items with no placement strategy [2026-08-06]
MEDIUM | fd-menu-engineering-triage | interverse/interscout | Dead weight on disk: interscout deprecated 2026-04-27 ("pre-public, early enough to retire cleanly") but the repo dir still sits in the fleet — retirement announced, never executed [2026-08-06]
LOW | fd-menu-engineering-triage | os/Clavain/agent-rig.json | Duplication/overlap risk flagged, not confirmed: intercept (adaptive decision gates) overlaps Clavain's own `scripts/gates/`; interstate (LLM-legibility) overlaps interwatch/interdoc doc surfaces; lattice (ontology graph) overlaps intergraph (ecosystem graph) and canongraph (entity graph) — three graph plugins with no documented boundary [2026-08-06]
LOW | fd-menu-engineering-triage | interverse/interbrowse | Interbrowse ships 8 skills + 2 agents and is installed, but has no README and zero skills linked into ~/.agents/skills — inventory without signage; demand unverifiable [2026-08-06]
LOW | fd-menu-engineering-triage | interverse/intersite, interverse/interboxd | Single-patron items: intersite (GSV portfolio site generator) and interboxd (personal Letterboxd discovery) are personal-project plugins off-marketplace — fine as experiments, but they dilute the fleet census and should live outside the interverse menu or be clearly marked personal [2026-08-06]
```
