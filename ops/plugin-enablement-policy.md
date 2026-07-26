# Plugin Enablement Policy

> Governs `~/.claude/enabledPlugins` on Clavain. Companion to the 2026-07-16 doctor
> cleanup and to `dotfiles-yadm.md`. Measured against the **plugin cache**, never source.

Every enabled plugin's skill, command, and agent `description` fields are concatenated into
the system prompt at session start. That is the **advertisement budget** — paid on every
session whether or not the plugin is used. Disabling a plugin removes its descriptions
entirely; demoting a command (`disable-model-invocation: true`) removes the description
while keeping the command typeable.

## The rule that matters

**Disable by setting `false`. Never delete the key.**

`~/.claude/hooks/guard-enabled-plugins.sh` union-merges a reference file over the live one:

```js
live.enabledPlugins = { ...refPlugins, ...livePlugins };
```

Live wins only for keys present in **both**. A key *missing* from live silently adopts the
reference's value — including `true`. An explicit `false` is drift-proof; a deleted key is
not. (That hook is currently dead — see "Known-broken machinery" — but write for the
revived case.)

## Where drift actually comes from

Investigated 2026-07-25 (bead `mk-uf0n`). The answer is **concurrent sessions**, not a
rogue process.

`interbrowse` flipped `false → true` and `cujgel` was added at settings.json mtime
`2026-07-24 23:52` local. Session `2f8c3e0e` made both Edits at audit-log timestamp
`2026-07-25T06:52Z` — the same instant, expressed in UTC. The earlier "no session owned
this change" conclusion was a **timezone artifact**: a local mtime compared against UTC log
rows looks like a different day.

The change was legitimate. That session was working on jawnsight (the cujgel campaign) at
mk's direction. It simply had no way to record intent where the next session would see it.

Four or more sessions run concurrently on this machine, all sharing one global
`settings.json`. Treat unexplained toggles as **a teammate**, not corruption — check
`~/.claude/audit.log` for the matching UTC instant before assuming a mechanism.

**Ruled out, with evidence:**

| Suspect | Verdict |
|---|---|
| `guard-enabled-plugins.sh` | Dead since 2026-03-28 — reference path renamed away |
| `settings-watchdog.sh` | Same dead path; not installed on Clavain, not running |
| `com.arouth.claude-plugin-cleanup` (launchd, Sun 09:30) | Prunes stale **cache version dirs** only; never opens settings.json |
| Marketplace refresh / plugin install | No evidence; every entry-count change traced to a session Edit |

## Known-broken machinery

`guard-enabled-plugins.sh` reads `~/projects/dotfiles/common/.claude/settings.json` and
exits 0 when absent. Dotfiles commit `848b445` (2026-03-28) renamed that path to
`.claude/settings.json`. The hook has therefore protected nothing for four months while
appearing healthy in the SessionStart list. Tracked as `mk-1wj0`.

**Do not revive it by simply repointing the path.** The surviving reference is from
2026-05-17 and holds 75 entries against the live 85. Union-merging it would silently enable
`intertrack@interagency-marketplace`, which is exactly the failure this policy exists to
prevent. Any revival must diff-then-approve.

## What the instruments can and cannot see

| Surface | Instrument | Coverage |
|---|---|---|
| Skills | `~/.claude/audit.log`, `"tool":"Skill"` rows | Good |
| MCP tools | `~/.claude/tool-time/events.jsonl` | Good — `audit.log` logs **zero** `mcp__` rows |
| Agents | `audit.log`, by name match | Partial |
| **Commands** | — | **None.** No `SlashCommand` rows exist anywhere |

A `0` in the skill column is not proof of disuse for a command-heavy plugin. Weigh command
plugins on capability, not on counters.

## Default-enabled

Counts are 30-day, measured 2026-07-25. `chars` is advertisement cost from the cache.

### Load-bearing — always on

| Plugin | chars | Rationale |
|---|---|---|
| `clavain` | 7,133 | 88 skill invocations — the most-used plugin in the rig. Sprint spine. |
| `interflux` | 12,858 | 70 invocations. flux-drive/flux-melange are the default analysis path. |
| `cloudflare` | 4,397 | 27 MCP calls. Wrangler tokens do **not** work against the raw API — this MCP is the only path to 45 zones. |
| `github` | 0 | 36 MCP calls; no advertisement cost. |
| `interknow` | 88 | 23 MCP calls (qmd) over 3,210 docs. Cheapest ratio in the rig. |
| `intermux` | 186 | 20 MCP calls. Cross-session visibility. |
| `interlock` | 697 | Multi-session file reservation. Four-plus concurrent sessions make this mandatory. |
| `interspect` | 668 | Routing evidence collector; hooks run continuously. Already demoted 11 of 18 commands. |
| `context7` | 0 | 10 MCP calls, zero advertisement cost. |
| `interrank` | 0 | 11 MCP calls, zero cost. |

### Cheap enough not to argue about (< 800 chars, keep on)

`intersearch` 768 · `interwatch` 716 · `intersynth` 647 · `interstate` 543 ·
`interkasten` 464 · `interject` 417 · `interstat` 331 · `interdoc` 269 · `interpulse` 191 ·
`interline` 189 · `intercheck` 178 · `internext` 174 · `tool-time` 174 · `interphase` 168 ·
`interlearn` 139 · `intermem` 114 · `intercut` 101 · `intertrust` 90 · `intership` 89

Collectively ~5,800. Individually none is worth a release. Revisit only as one batched pass.

`intertrust` and `interdoc` stay on despite zero counters — they are **engines invoked by
interwatch and flux-drive**, not user-facing surfaces. Do not re-purge on counter evidence.

### Zero advertisement cost — on because free

`explanatory-output-style`, `gopls-lsp`, `pyright-lsp`, `rust-analyzer-lsp`, `swift-lsp`,
`typescript-lsp`, `security-guidance`, `warp`, `interpub`.

LSP plugins register language servers without advertising descriptions. Leave them.

> **Correction, 2026-07-26.** This section previously listed `cujgel` as
> "enabled but not installed — 0 chars". That was true when measured on 07-24 and
> **false two days later**: its cache appeared and it now bills **1,250 chars**.
> The whole rig-wide total moved 28,246 → 29,496 on that alone.
>
> The general lesson is worth more than the correction: **enablement and cost are
> separated in time.** A plugin switched on in `settings.json` costs nothing until
> Claude Code installs it, so a zero in this document is a statement about the
> moment it was written, never a property of the plugin. Anything recorded as free
> because it was uninstalled must be re-measured, not trusted. This is exactly why
> the budget is now a scheduled check rather than a number in a document.

### `cujgel` — stays on, at 1,250 chars

Decided 2026-07-26. Eight entries, ~156 chars each:

```
197 cujgel-engine · 165 provoke · 162 discover · 157 teardown
150 capture · 149 derive · 137 consume · 133 validate
```

**Kept enabled.** Two reasons, and the second is the one that settles it:

1. It is in active use — a sibling session is running the jawnsight campaign
   against it (`mk-rsup`, P1).
2. **There is nothing to trim.** No `<example>` blocks in descriptions, no
   duplicate command wrappers, no demotable entries — the two levers used
   everywhere else in this document do not apply. At ~156 chars per entry these
   descriptions are already lean, so the only available action is *removing
   functionality*, not reclaiming waste.

Disabling a plugin someone is actively using, to buy 4% headroom, is the wrong
trade. The cost is real and now measured every day rather than assumed.

### Off by default

Disabled 2026-07-26. Backup: `~/.claude/settings.json.bak-plugindev-off-20260726-003128`.

| Plugin | chars | Rationale |
|---|---|---|
| `plugin-dev` | 6,877 | 0 skill invocations, 0 MCP, 4 agent dispatches in 30 days. The single worst cost-to-use ratio in the rig. Its three agents carry 2,839 chars of `<example>` blocks that we cannot durably fix — a plugin update overwrites any edit — so disabling is the only lever that holds. Enable while authoring a plugin, disable after. |
| `interfluence` | 1,107 | Voice-profile and corpus stylometry. No recorded use in 30d. Caveat: its surface is commands, which no instrument measures — this was a capability call, not a counter call. |

Plus the 41 already disabled in the 2026-07-16 doctor cleanup and its 07-20 follow-up:

`Notion`, `agent-sdk-dev`, `claude-code-setup`, `claude-md-management`, `code-review`,
`code-simplifier`, `commit-commands`, `cwc-makers`, `feature-dev`, `frontend-design`,
`hookify`, `intercache`, `interchart`, `intercraft`, `interdeep`, `interdev`, `interform`,
`interjawn`, `interlab`, `interleave`, `interlens`, `intermap`, `intermonk`, `intername`,
`interpeer`, `interplug`, `interscribe`, `intersense`, `intersight`, `interskill`,
`interslack`, `intertest`, `intertrace`, `intertree`, `jetty`, `notion`,
`pr-review-toolkit`, `rust-analyzer`, `tldr-swinton`, `tuivision`, `vercel`.

`interjawn` stays off specifically because it embeds database credentials.

### Currently on, but situational

| Plugin | chars | Note |
|---|---|---|
| `interbrowse` | 1,772 | **Hold on.** Session `2f8c3e0e` enabled it deliberately on 07-24 for jawnsight research. Disabling would undo a teammate's live change. |
| `interhelm` | 1,225 | Kept on 2026-07-25. No recorded use, but its surface is agent + commands and commands are unmeasured — weak evidence, so decided on capability. Description slimmed instead (`e9a14c31`). |

## Situational-enable cheat sheet

Turn on for the task, turn off after. Extends the 2026-07-16 list.

| Doing this | Enable | Cost |
|---|---|---|
| Authoring or validating a plugin | `plugin-dev` | 6,877 |
| Building a diagnostic/debug HTTP server | `interhelm` | 1,834 |
| Voice-profile or corpus stylometry work | `interfluence` | 1,107 |
| Competitive research / UX teardown | `interbrowse` | 3,885 |
| Slack integration work | `interslack` | — |
| Chart or diagram generation | `interchart` | — |
| Notion engagement IA (ODST clients) | `Notion` | — |
| Deploying to Vercel | `vercel` | — |

After the task: set the key back to `false`. Do not delete it.

## Result, 2026-07-26

| | chars |
|---|---|
| Measured at start of the 07-25 pass | 46,416 |
| `plugin-dev` + `interfluence` disabled | −7,984 |
| interflux 0.2.84 (fd-* examples relocated) | −7,466 |
| interbrowse 0.5.1 (8 wrappers demoted, 2 agents slimmed) | −2,113 |
| interhelm 0.2.4 (runtime-reviewer slimmed) | −607 |
| Subtotal at end of the 07-26 pass | 28,246 |
| `cujgel` installed (was enabled-but-uninstalled, so free) | +1,250 |
| **Current, measured 2026-07-26** | **29,496** |

Zero files deleted. Every demoted command remains user-invocable and listed in its plugin's
index. Remaining known win: Clavain's `plan-reviewer`, 887 chars (`mk-hpkv`) — needs a
worktree on `main`, since the shared checkout sits on a feature branch.

**This table is a log, not a live number.** It was wrong within 48 hours of being
written, because a plugin got installed. The number that is true today comes from
running the instrument:

```bash
python3 ~/projects/Sylveste/ops/scripts/advertisement-budget.py
```

and it is checked daily by the `advertisement-budget` rig-health check
(`ops/rig-self-checks.md`). Prefer either over any figure written down here.

**Measuring after a publish:** publishes run on zklw, so the Mac's cache keeps serving the
previous version until Claude Code restarts. Until then the script reports the pre-publish
number and is not wrong — the old descriptions really are what this session loaded. Measure
the published state by pointing the script at the plugin repos instead.

## This policy has only ever been applied to Clavain

Found 2026-07-26, the first time the budget was measured on the other machine:

| | enabled | total |
|---|---|---|
| Clavain | 44 of 85 | 29,496 |
| **zklw** | **75 of 77** | **52,537** (~13,134 tok) |

Everything above — the 07-16 doctor cleanup, the 07-25/26 disables, the
demotions — was written as rig-wide policy and applied to one machine. zklw runs
**22,537 chars over the ceiling** in every session and nobody knew, because until
now nothing measured it anywhere but here.

Top costs on zklw that are already disabled on Clavain:

```
10,761  pr-review-toolkit      1,898  notion       1,261  hookify
 1,107  interfluence             761  feature-dev    660  agent-sdk-dev
```

**One of these is free.** zklw caches `clavain 0.6.284` — 89 live entries, 0
demoted — while the marketplace is at `0.6.289`, where 41 of those 89 are
demoted. A Claude Code restart on zklw picks up the newer cache and reclaims
**~4,838 chars with no decision required**.

That is worth noting against a decision made the same day: `ic publish doctor`
now treats installed-behind-marketplace as `info` rather than `error`, because it
self-heals on restart. That remains right for *alerting* — but this is what the
trailing state costs while it lasts, and the budget check is what makes it
visible. The two checks are complementary: one stopped shouting about a
self-healing condition, the other prices it.

Tracked as `mk-zysa`. Until it is acted on, zklw reports `advertisement-budget`
FAIL at every session start. That is correct and should not be tuned away.

## Verifying

```bash
# Advertisement budget against the cache, live vs demoted, per plugin.
# Formerly a scratchpad script called budget2.py, which is how three baselines
# (34,141 / 46,416 / 36,837) got published and later retired as wrong.
python3 ~/projects/Sylveste/ops/scripts/advertisement-budget.py
python3 ~/projects/Sylveste/ops/scripts/advertisement-budget.py --json   # for tooling

# Who changed enabledPlugins, and when — audit.log is UTC, mtimes are local
grep '"tool":"Edit"' ~/.claude/audit.log | grep settings.json

# MCP usage by server (audit.log cannot see MCP)
python3 -c 'import json,collections;c=collections.Counter(
  json.loads(l).get("tool","").split("__")[1] for l in open(
  "'$HOME'/.claude/tool-time/events.jsonl") if "mcp__plugin_" in l);print(c.most_common())'
```

Back up before editing, and keep the change reversible in one line:

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak-$(date +%Y%m%d-%H%M%S)
```
