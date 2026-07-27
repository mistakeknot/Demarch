# Plugin Enablement Policy

> Governs `~/.claude/enabledPlugins` on **both machines**. Companion to the 2026-07-16
> doctor cleanup and to `dotfiles-yadm.md`. Measured against the **plugin cache**, never
> source, by `ops/scripts/advertisement-budget.py` and checked daily (`rig-self-checks.md`).

| | enabled | budget | status |
|---|---|---|---|
| Clavain (laptop) | 44 of 85 | **29,496** | warn — 504 from the ceiling |
| zklw (dev server) | 62 of 77 | **29,360** | dormant — loaded by no session (see below) |

Ceiling is **30,000 rig-wide**, not per machine. See "One ceiling" below.

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
not.

This is live, not hypothetical: the guard was rebuilt 2026-07-26 (`mk-1wj0`) and now
diff-reports by default, merges nothing without approval, and exits **non-zero** when no
reference resolves. `claude plugin disable` writes explicit `false` and preserves the key —
verified on both machines — so it is the safe way to disable. Hand-editing the JSON is not.

After any deliberate enablement change, re-adopt the reference:

```bash
bash ~/.claude/hooks/guard-enabled-plugins.sh --adopt
```

Skipping that leaves the reference describing the *old* intent, so a restore would quietly
undo the change. This bit us on zklw: 13 freshly-disabled plugins still read `true` in the
reference until it was re-adopted.

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

## Machinery — repaired 2026-07-26

`guard-enabled-plugins.sh` read `~/projects/dotfiles/common/.claude/settings.json` and
exited 0 when absent. Dotfiles commit `848b445` (2026-03-28) renamed that path, so the hook
protected nothing for four months while appearing healthy in the SessionStart list.

Rebuilt under `mk-1wj0`: it diff-reports by default, merges nothing without `--approve`,
exits **non-zero** when no reference resolves, and carries a 13-test suite that fails if the
reference path stops resolving. The suite runs daily on both machines
(`ops/rig-self-checks.md`), which is the actual fix — the tests existed before and nothing
ran them.

It was **not** revived by repointing the path. The surviving 2026-05-17 reference held 75
entries against the live 85, and union-merging it would have silently enabled
`intertrack@interagency-marketplace` — the exact failure this policy exists to prevent.

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

## zklw — the machine this policy never reached

Everything above was written as rig-wide policy and applied to one machine. On
2026-07-26 the budget was measured on zklw for the first time: **52,537 chars**,
22,537 over the ceiling, 75 of 77 plugins enabled. Nobody knew, because until
that week nothing measured the budget anywhere.

Resolved the same day (`mk-zysa`). **52,537 → 29,360.**

### The free half: 4,659 chars, no decision required

zklw's caches trailed the marketplace. `clavain` was pinned at `0.6.284` — 89
live entries, **0 demoted** — while the marketplace was at `0.6.289`, where 41 of
those 89 are demoted. Seven plugins were behind in total.

```bash
claude plugin update <plugin>@<marketplace>     # the supported path
```

52,537 → 47,878. `clavain` alone accounted for 4,838; the other six netted +179
because some genuinely grew.

**Correction worth keeping:** `ic publish doctor` tells you a trailing install
"resolves itself on the next Claude Code restart". On zklw that was **false** —
sessions had been starting daily for days with `clavain` stuck at 0.6.284.
Claude Code does not silently upgrade installed plugins at session start;
`claude plugin update` is an explicit action. Tracked for correction as `mk-ja1j`.

This also prices a decision made the same day. Doctor now treats
installed-behind-marketplace as `info` rather than `error` because it self-heals.
That is still right for *alerting* — but 4,838 chars is what the trailing state
cost while it lasted. The two checks are complementary: one stopped shouting
about a condition that resolves, the other bills it.

### There is no usage data on zklw

The goal was to justify each disable against zklw's own instruments. **They are
dead.** `audit.log` holds 25 lines, last written 2026-07-14. `tool-time/
events.jsonl` last recorded 2026-07-14; `stats.json` regenerates daily and
reports `total_events: 0`. Invoking the hook by hand *does* append, so it works
and is simply never called. Cause unresolved after a bounded search (`mk-q6bl`).

So **every zklw decision below is a capability call**, not a counter call. Said
plainly because the alternative — implying evidence that does not exist — is how
the 34,141 / 46,416 / 36,837 baselines happened.

> **Mechanism found 2026-07-27** (`mk-q6bl`): zklw's CLI Claude Code has been
> **logged out since 2026-07-14**. `.credentials.json` was last written that day
> at 16:24, hours after the final recorded event at 03:01, and `claude -p` now
> returns `Not logged in · Please run /login`. Hook wiring is fine — the aborted
> run shows Claude Code invoking tool-time's hook — there have just been no
> authenticated CLI sessions to call it in.
>
> **These 13 calls therefore still stand unrevisited.** Re-running them against
> real usage needs an interactive `/login` on zklw, then roughly a week of
> recorded sessions. Until both happen, treat the table below as reasoned but
> unevidenced. `instrument-freshness` now fails daily on zklw until it records
> again, so this cannot quietly become permanent.

### 2026-07-27 correction: zklw's budget is paid by nobody

The 07-26 pass, and the goal that followed it, both assumed zklw pays its
advertisement budget. **It does not.** No Claude Code session runs on that
machine, and the remote bridge does not load plugin config at all:

```
strings ~/.claude/remote/srv/*/server | grep -c ...
  settings.json 0    enabledPlugins 0    plugins/cache 0
  installed_plugins 0    SKILL.md 0      marketplace 0
```

It references only `/proc` and `/sys`. It is pure transport; the session runtime,
and therefore the system prompt, lives on the client.

So zklw's 29,360 chars are loaded into nothing. **Disabling a plugin there saves
zero tokens today.** The 07-26 disables were not wasted — they are correct
preparation — but they should never have been described as reclaiming budget, and
the "22,537 chars over the ceiling" framing was measuring a cost nobody paid.

What zklw's `enabledPlugins` actually is: a **dormant configuration**, correct or
incorrect only with respect to a future in which CLI sessions resume.

### The hook classification, and why one bucket is empty

Every enabled plugin on zklw was classified against the hook audit. `claude
plugin details` labels hooks *"harness-only — no model context cost"*, which is
the key fact: **hooks carry no advertisement cost at all.** A plugin's cost is its
skills, commands, and agents.

| Class | Count | Meaning |
|---|---|---|
| Hook-independent | 38 | Value is skills/commands/agents; dead hooks change nothing |
| Hook-dependent, correct on resume | 19 | Value needs hooks; hooks return when sessions do |
| Hook-dependent, zero cost | 5 | Hooks are the entire delivery; free either way |
| **Hook-dependent and permanently wasteful** | **0** | — |

The five free ones — `security-guidance`, `intersynth`, `intership`,
`interline`, `explanatory-output-style` — advertise nothing at all. Disabling
them saves literally zero. Keep.

The nineteen include the cases the goal expected to condemn: `interspect` (514
tok, 18 skills that analyse evidence its hooks collect), `interlock` (82, file
reservation across sessions), `interstat`, `interwatch`, `tool-time`,
`interpulse`, `intercheck`, `interlearn`, `interphase`, `intermux`, `intertrack`,
`intermem`, `interknow`.

**The fourth bucket is empty, and that is the finding.** Nothing on zklw is
*permanently* hook-wasteful, because hook deadness there is not a property of any
plugin — it is a symptom of no sessions, and it ends the moment sessions return.
`interspect`'s skills are useless on zklw today for the same reason `clavain`'s
are: nothing runs.

**So no further disables were applied.** Disabling `interspect` would save 0
tokens now and remove a working plugin the moment login is restored. That is a
worse position than leaving it.

The real question is binary and it is mk's: **will zklw run Claude Code sessions
again?**

- **Yes** → the current config is correct preparation; fix the login and the
  07-26 calls apply as written.
- **No** → all 62 enabled plugins are dormant, not just the hook-bearing 24, and
  the honest action is to stop maintaining an enablement policy for that machine
  entirely rather than tuning one nobody loads.

### The line that was drawn: third-party first

Not a port of Clavain's answers. The principle is about **which lever exists**:

- **Third-party plugins get the strictest treatment, because disabling is the
  only durable lever.** We cannot slim what we do not publish — a plugin update
  overwrites any local edit. This is the same reasoning that settled `plugin-dev`
  on Clavain.
- **Our own `inter*` plugins keep the benefit of the doubt**, because demotion and
  example-relocation remain available. Disabling them is not the only option, so
  it should not be decided blind on a machine with no usage data.

Disabled on zklw, 2026-07-26 (13 plugins, −18,518):

| Plugin | chars | Rationale |
|---|---|---|
| `pr-review-toolkit` | 10,761 | 22% of zklw's entire budget in 7 entries. Claude Code's own projection agrees: ~2,680 always-on tokens. Review work is served by `/code-review` and flux-drive. |
| `notion` | 1,898 | ODST client engagements. The OneDrive context path is `/Users/arouth/...` — Mac-only by construction. |
| `hookify` | 1,261 | Hook authoring; done interactively where mk works. |
| `interfluence` | 1,107 | Voice/stylometry for mk's own writing — a Mac activity. Already a capability call on Clavain. |
| `interjawn` | 590 | **Security, not budget.** Embedded DB credentials; the reason it is off on Clavain applies more forcefully on a server. |
| `feature-dev` `agent-sdk-dev` `claude-md-management` `claude-code-setup` `commit-commands` `frontend-design` `code-simplifier` `code-review` | 2,901 | The 2026-07-16 doctor-cleanup set, never applied here. |

**Third-party advertisement on zklw is now 0.** Everything it pays for is ours,
and therefore slimmable rather than only disableable.

### Kept on zklw, deliberately

The `inter*` long tail Clavain disabled stays on: `intertrace` 920,
`tldr-swinton` 837, `interplug` 629, `intercraft` 519, `intertest` 455,
`interlab` 403, `interskill` 402, `interdeep` 398, `interdev` 391, and ~10 more
at 100–350 each. Roughly 5,600 chars.

zklw is where these are developed and published. Turning them off on the
development machine to buy headroom, with no usage data and a slimming pass still
available, is the wrong order of operations.

`intertrack` (284) is enabled here and **absent from Clavain's settings
entirely** — the exact key the guard's union-merge test was written around. Left
enabled, flagged: it should be a deliberate entry on both machines or neither.

### One ceiling, 30,000, for both machines

The obvious move after seeing 52,537 was to give the dev server its own larger
number. **Rejected.** A per-machine ceiling derived from what a machine currently
spends is the same mistake as widening a warn band to make today's reading green:
the threshold ends up describing the rig instead of constraining it.

The substantive argument is that zklw has no *plugin* need Clavain lacks. Its
distinct roles — publish signer, canonical repo host, autosync, hermes agents —
are served by binaries and services, not advertised entries. Both machines now sit
136 chars apart under the same ceiling, which is evidence one contract fits.

The reasoning lives in `rig-budget-eval.py` beside the constant, so the next
person to consider a second number reads why there is not one.

### Reversibility

Every change used `claude plugin disable`, which writes an explicit `false` and
**preserves the key** — verified: 77 keys before and after, 15 now false. That
matters because the guard union-merges a reference over live, and a key *missing*
from live adopts the reference's `true`. Explicit `false` is drift-proof.

Backups on zklw:

```
~/.claude/settings.json.bak-enablement-20260726-222641
~/.claude/plugins/installed_plugins.json.bak-enablement-20260726-222641
~/.claude/settings.reference.json.bak-adopt-20260726-223024
```

The guard reference was re-adopted after the change (0 differing keys). Without
that, a restore-from-reference would have silently re-enabled all 13.

Re-enable any one of them in a line:

```bash
ssh zklw 'claude plugin enable pr-review-toolkit@claude-plugins-official'
```

## `claude plugin details` is not a usable cross-check per plugin

It was tried as an independent instrument, on the strength of agreeing with ours
to within 10 tokens on `pr-review-toolkit` (2,680 vs 2,690). That agreement was a
coincidence of composition.

Across all 42 plugins enabled on Clavain the **totals** agree to 4% — 7,364
tokens (ours) against 7,044 (theirs). **Per plugin the ratio runs from 0.00 to
4.26**, which is precisely where a cross-check would be needed:

| Plugin | ours | claude | ratio |
|---|---|---|---|
| `interspect` | 167 | 712 | **4.26** |
| `cloudflare` | 1,099 | 1,769 | 1.61 |
| `interflux` | 1,348 | 356 | **0.26** |
| `cujgel` | 312 | 84 | 0.27 |
| `intersynth` | 161 | 0 | 0.00 |

Two mechanisms, both verified:

1. **It does not account for `disable-model-invocation`.** `interspect` has 11
   demoted commands; theirs counts all 18 skills, ours counts the 7 that still
   advertise. Demotion is the rig's main reclamation lever, so the one instrument
   that cannot see it cannot audit the work.
2. **It under-counts agents in subdirectories.** It reports `Agents (0)` for
   `interflux`, which ships **25 agent files, 18 of them nested** under
   `agents/research/` and similar. That is the same non-recursive-glob bug
   `advertisement-budget.py` had in its first version and fixed.

Aggregate agreement plus per-plugin divergence in both directions is the
signature of errors cancelling, not of two instruments measuring the same thing.
**Use it for a sanity check on a total; never to decide about one plugin.**

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
