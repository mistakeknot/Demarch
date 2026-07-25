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

`cujgel` (enabled but not installed — 0 chars), `explanatory-output-style`, `gopls-lsp`,
`pyright-lsp`, `rust-analyzer-lsp`, `swift-lsp`, `typescript-lsp`, `security-guidance`,
`warp`, `interpub`.

LSP plugins register language servers without advertising descriptions. Leave them.

### Off by default

| Plugin | chars | Rationale |
|---|---|---|
| `plugin-dev` | 6,877 | 0 skill invocations, 0 MCP, 4 agent dispatches in 30 days. The single worst cost-to-use ratio in the rig. Enable while authoring a plugin, disable after. |

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

These three are enabled today and are the next candidates after `plugin-dev`. None is
disabled by this document — each needs a decision.

| Plugin | chars | Note |
|---|---|---|
| `interbrowse` | 3,885 | **Hold on.** Session `2f8c3e0e` enabled it deliberately on 07-24 for jawnsight research. Disabling would undo a teammate's live change. |
| `interhelm` | 1,834 | No recorded use. Surface is agent + commands, so counters are weak evidence — decide on capability. |
| `interfluence` | 1,107 | No recorded use. Voice-profile work is episodic. |

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

## Verifying

```bash
# Advertisement budget against the cache, live vs demoted, per plugin
python3 <scratchpad>/budget2.py

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
