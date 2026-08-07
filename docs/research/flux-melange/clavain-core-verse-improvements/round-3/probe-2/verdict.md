# Verdict — round-3 / probe-2 — fd-menu-engineering-triage

Menu-engineering triage of the interverse cold-spot fleet (60 plugins; excludes the 10
previously deep-dived: interflux, interpath, interdoc, interlock, intermux, interpeer,
interkasten, interpub, interspect, interphase; excludes `_shared` support dir and external
canongraph/interjawn).

Demand evidence: Claude Code `installed_plugins.json`, live `~/.agents/skills/` links,
`agent-rig.json` profile membership, marketplace listing, per-repo git recency (all repos
committed within ~2 weeks, so recency is NOT a differentiator — everyone gets cooked;
only orders distinguish).

## Census

**Counts: 27 stars · 24 puzzles · 3 plowhorses · 6 dogs (60 total)**

| Plugin | Class | One-line evidence |
|---|---|---|
| cujgel | star | Installed; `cuj-verification` skill live; 7 commands |
| interboxd | puzzle | Real Letterboxd impl, but off-marketplace, off-rig, uninstalled — personal item |
| interbrowse | puzzle | Installed w/ 8 skills in repo, but no README and zero skills linked — demand unverifiable |
| intercache | dog | Auto-starts MCP via rig `mcp` profile; 0 skills/cmds; hook unregistered; no documented consumer |
| intercept | puzzle | Real adaptive-gate runtime w/ tests; invisible to marketplace/rig; overlaps Clavain gates |
| interchart | puzzle | Live ecosystem diagram site; installed; `agents/` dir is docs, not agents — labeling lie, low pull |
| intercheck | star | Rig default; `quality` skill live; syntax hooks on every session |
| intercraft | star | `agent-native-architecture` skill live; rig recommended |
| intercut | plowhorse | Recommended + installed; 1 command, trivial cost, modest value — keep, don't invest |
| interdeep | star | `deep-research` skill live; rig research profile |
| interdeploy | puzzle | Real Vercel auto-fix loop; marketplace-only, zero installs/rig placement |
| interdev | star | Rig default; `mcp-cli` skill live |
| interfer | star | Runs the documented local MLX server (port 8421, AGENTS.md) — infrastructure, ordered daily |
| interfluence | dog | DEPRECATED in favor of intervox, yet installed AND in rig `optional` — the load-bearing dog |
| interform | star | `distinctive-design` + `ui-polish` skills live; rig design |
| intergraph | puzzle | Ambitious ecosystem graph w/ SQLite store; off-marketplace, off-rig, uninstalled |
| interhelm | star | 3 skills live (diagnostic-maturation, runtime-diagnostics, smoke-test-design); rig ops |
| interject | puzzle | Ambient discovery MCP; optional profile only, no visible consumption |
| interknow | puzzle | Knowledge compounding MCP; research profile; qmd overlap unresolved |
| interlab | star | `autoresearch` + `autoresearch-multi` skills live; rig ops |
| interlearn | puzzle | "Solved before" querying; optional-only; overlaps interknow/QMD/cass |
| interleave | puzzle | Spec+library pattern plugin; optional-only; pattern may be used, plugin isn't |
| interlens | puzzle | 288-lens MCP; optional-only, though flux-melange probes use the lens corpus indirectly |
| interline | star | Statusline is load-bearing UI; rig recommended; installed |
| interloop | puzzle | Proof-loop plugin w/ own dev marketplace; zero installs, zero rig profiles |
| interlore | puzzle | Philosophy observer; marketplace-only, uninstalled |
| intermap | star | `intermap` skill live + MCP; rig observability |
| intermem | star | `memory-synthesis` + `memory-tidy` skills live; rig docs |
| intermix | puzzle | Skaffen eval harness; niche but real; optional |
| intermonk | star | `dialectic` skill live; rig research |
| intername | plowhorse | Agent naming; recommended + installed; cheap charm, low stakes |
| internext | star | Rig default; `next-work` skill live |
| interplug | star | `troubleshoot` + `validate` + `create-plugin` live; plugin-dev profile |
| interpulse | star | `pressure` skill live; rig observability; SessionStart hooks |
| interrank | puzzle | AgMoDB MCP; review profile; single-project dependency |
| interscout | dog | Deprecated 2026-04-27 "early enough to retire cleanly" — dir still in fleet, retirement never executed |
| interscribe | star | `interscribe` skill live; rig docs |
| intersearch | puzzle | Shared embedding infra; optional; overlaps interknow/QMD |
| interseed | puzzle | Full MCP server implementation; marketplace-listed but uninstalled and profile-less |
| intersense | dog | ARCHIVED 2026-03-26, no plugin.json — yet still installed in Claude Code (ghost) and cited by interflux's marketplace blurb |
| intership | plowhorse | Spinner verbs; recommended + installed; pure garnish, near-zero cost |
| intersight | star | `design-analyze` skill live; rig design |
| intersite | dog | GSV personal portfolio-site generator; off-marketplace, no README, no install path — occupies a fleet slot for one patron |
| interskill | star | `skill` + `audit` skills live; plugin-dev profile |
| interslack | star | `slack-messaging` skill live; rig ops |
| interstat | puzzle | Token benchmarking hooks; optional-only; overlaps tool-time/intertrack |
| interstate | puzzle | v0.5.0, installed, real skills; but absent from every rig profile |
| intersynth | puzzle | Synthesis engine in review profile; 0 skills, 3 agents — consumed only via interflux |
| intertest | star | Rig default; 3 discipline skills live (TDD, debugging, verification) |
| intertrace | star | `intertrace` skill live; rig review |
| intertrack | star | `feature-report` + `metrics` skills live; rig observability |
| intertree | star | `tree` skill live; rig docs |
| intertrust | puzzle | Trust scoring; recommended profile; 1 command, no visible consumption loop |
| intervoice | dog | DEPRECATED (superseded by intervox) yet still published in marketplace at v0.1.1 |
| intervox | puzzle | Tested successor (52 tests) to two deprecated plugins — installed NOWHERE, in NO profile |
| interwatch | star | `doc-watch` skill live; v0.6.1; rig recommended |
| lattice | puzzle | Ontology engine w/ SessionStart hook; off-marketplace/rig; third overlapping graph plugin |
| tldr-swinton | star | `tldrs` CLI in daily AGENTS.md workflow; rig default |
| tool-time | star | `tool-time` skill live; rig default |
| tuivision | puzzle | TUI testing MCP; optional-only; niche but unique capability |

## Top 3 retirement candidates

1. **interfluence** — remove from `agent-rig.json` optional list AND uninstall from Claude Code.
   It is deprecated, its hook is self-disabled, and its presence in the installer makes it a
   load-bearing dog: the machinery actively serves an item the kitchen stopped cooking.
2. **intersense** — uninstall the ghost (`intersense@interagency-marketplace` still installed
   + cached despite being archived with no plugin manifest), and fix interflux's marketplace
   description that still cites it. Archive or delete the dir.
3. **intervoice** (marketplace entry) + **interscout** (fleet dir) — both publicly deprecated
   but never removed: intervoice still published in marketplace.json, interscout's dir still in
   the fleet. Execute the retirements that were announced.

## Top 3 hidden gems

1. **intervox** — the measured closed-loop voice engine supersedes two deprecated plugins,
   ships 52 tests, and is installed nowhere while deprecated interfluence holds its slot.
   Promote: swap into rig optional in interfluence's place.
2. **intercept** — adaptive fail-open decision gates with shadow canaries and an inspectable
   local classifier; fully implemented and tested, but invisible to marketplace and rig.
   Either publish it or fold it into Clavain's gates — currently duplicate latent capacity.
3. **intergraph** — autonomous ecosystem graph answering exactly the question this probe
   series asks by hand every round ("how does the ecosystem actually fit together"). Off-menu;
   if it works, it should be generating this census.

## REMEDIATION

Warranted. Minimal menu actions, in order:
1. `agent-rig.json`: replace `interfluence` with `intervox` in `plugins.optional` (one-line swap).
2. Uninstall `interfluence` and `intersense` from Claude Code; remove intersense cache entry.
3. `marketplace.json`: delete the `intervoice` entry; fix interflux description (drop intersense).
4. Decide the 7 off-menu dirs (f-033 confirmed): publish intergraph/intercept/lattice or move
   interboxd/intersite to a personal area; execute interscout/intersense retirement.
5. Demote-or-prove intercache: remove from rig `mcp` profile unless a consumer is documented.

REMEDIATION: agent-rig.json optional swap (interfluence→intervox), uninstall interfluence+intersense,
marketplace cleanup (intervoice entry, interflux blurb), and a publish-or-remove decision on the
7 off-marketplace dirs.
