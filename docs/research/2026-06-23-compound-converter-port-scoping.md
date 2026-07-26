---
title: "Compound-Engineering Multi-Runtime Converter — Port-to-Clavain Scoping Report"
date: 2026-06-23
bead: Sylveste-ie6.7
source_repo: https://github.com/EveryInc/compound-engineering-plugin
source_commit: 16442e866edee5c89faa6c1b2754ac49fcecd631
source_branch: main
analyst: research session (Opus 4.8, 1M ctx)
---

# Compound-Engineering Multi-Runtime Converter — Port-to-Clavain Scoping Report

## Summary verdict

The compound-engineering (CE) converter is a **clean, well-factored Bun/TypeScript transpiler** that reads a standard Claude Code plugin (`.claude-plugin/plugin.json` + markdown skills/commands/agents + hooks.json + MCP config) into a normalized in-memory `ClaudePlugin` object, then runs it through a per-target **Converter** (pure function, Claude → in-memory `Bundle`) and **Writer** (effectful, `Bundle` → on-disk files with merge/cleanup semantics). It is fully self-contained — it never calls Claude Code internals, only the filesystem — so the *engine* (`parsers/claude.ts`, `targets/index.ts`, `utils/frontmatter.ts`, `utils/model.ts`) is reusable against any Claude-Code-shaped plugin, **including Clavain as-is**. Clavain's source tree (`os/Clavain/.claude-plugin/plugin.json`, `skills/*/SKILL.md`, `commands/*.md`, `agents/*.md`, `hooks/hooks.json`) is exactly the input shape the CE parser expects, so the parser would ingest Clavain with zero changes. The real cost is not the engine — it's that **a Codex Writer that fits Clavain's existing hand-rolled Codex install model already exists in CE form but disagrees with Clavain's**, and that the per-runtime conversion of *prose semantics* (Task-call syntax, slash-command rewriting, tool-name mapping, `.claude/` path rewriting) is the irreducibly hard, per-target, maintenance-heavy part. My lean is **no-go on porting the converter as a framework**; instead **steal the parser + frontmatter + model-tier utilities and the Codex Writer's merge/cleanup logic** to harden Clavain's existing single-target Codex path. That thinner approach captures ~80% of the value at ~20% of the cost and risk.

---

## 1. The conversion model

### Input shape (one normalized object)

The entire pipeline funnels through a single parser, `src/parsers/claude.ts` (lines 17–56), which reads `.claude-plugin/plugin.json` and produces a `ClaudePlugin` (`src/types/claude.ts:643–651`):

```
ClaudePlugin = {
  root, manifest,
  agents:   ClaudeAgent[]    // {name, description, capabilities?, model?, body, sourcePath}
  commands: ClaudeCommand[]  // {name, description?, argumentHint?, model?, allowedTools?, disableModelInvocation?, body, sourcePath}
  skills:   ClaudeSkill[]    // {name, description?, argumentHint?, disableModelInvocation?, userInvocable?, ce_platforms?, sourceDir, skillPath}
  hooks?:   ClaudeHooks      // {hooks: Record<event, ClaudeHookMatcher[]>}
  mcpServers?: Record<string, ClaudeMcpServer>
}
```

The parser is generic: it walks `agents/`, `commands/`, `skills/` (any `SKILL.md`), reads `hooks/hooks.json` and `.mcp.json`, and parses YAML frontmatter via `src/utils/frontmatter.ts` (a hand-rolled `---`-delimited splitter using `js-yaml`, lines 471–500). Nothing here is CE-specific except `ce_platforms` (a skill-frontmatter allowlist used to filter skills per target, `claude.ts:112` and `claude.ts:639–641`).

### Output shape (per-target `Bundle`)

Each target defines its own `Bundle` type — e.g. `CodexBundle` (`src/types/codex.ts:144–162`) carries `prompts`, `skillDirs`, `generatedSkills`, `agents`, `invocationTargets`, `mcpServers`, `hooks`, `externallyManagedSkillNames`. `OpenCodeBundle` carries `config` (a JSON object), `agents`, `commandFiles`, `plugins`, `skillDirs`. The Bundle is the in-memory handoff; the Writer turns it into files.

### Where per-runtime divergence lives

Divergence concentrates in two places:

1. **Component-mapping decisions** (in the Converter): e.g. CE's `convertClaudeToCodex` (`src/converters/claude-to-codex.ts:18–133`) decides Codex installs are **agents-only by default** (`includeSkills = false`, line 28) because Codex has its own native plugin install for skills/commands; only custom agents (emitted as TOML, `targets/codex.ts:1327–1334`) fill the gap. OpenCode by contrast emits skills as copied directories, commands as `.md` files, and hooks as a generated `.ts` plugin (`claude-to-opencode.ts:374–415`).

2. **Prose/body transformation** (per-target `transformContentFor*` functions) — this is the AskUserQuestion-style branching the earlier research flagged. Each target rewrites the *text of skill/agent/command bodies* to use that runtime's invocation vocabulary:
   - **Tool-name mapping**: `src/converters/claude-to-opencode.ts:334–349` has a `TOOL_MAP` that renames Claude tools to OpenCode names. The `AskUserQuestion → question` mapping the prior research referenced lives here (`question: "question"` at line 346); OpenCode's permission/tool tables use it (`applyPermissions`, lines 670–789). Pi instead rewrites Claude task-tracking primitives wholesale: `TaskCreate/Update/List/Get/Stop/Output` and `TodoWrite/TodoRead` → `"the platform's task-tracking primitive"` (`claude-to-pi.ts:296–301`).
   - **Subagent-call syntax**: all three converters regex-rewrite `Task agent-name(args)` (the same `^(\s*-?\s*)Task\s+([a-z][a-z0-9:-]*)\(([^)]*)\)` pattern). Codex → `Use the $agent-name skill to: args` OR `Spawn the custom agent ...` if a TOML agent target exists (`utils/codex-content.ts:307–324`); Antigravity → `Use the @agent-name subagent to: args` (`claude-to-antigravity.ts:103–111`); Pi → `Run subagent with agent="..." and task="..."` (`claude-to-pi.ts:284–292`).
   - **Slash-command rewriting**: Codex `/foo` → `/prompts:foo` or `the foo skill` depending on whether `foo` is a known prompt vs skill target (`codex-content.ts:332–348`), with a path-name allowlist (`dev/tmp/etc/usr/var/bin/home`) to avoid mangling filesystem paths.
   - **Config-path rewriting**: `.claude/` → `.codex/` (Codex, `codex-content.ts:350–352`), `.claude/` → `.opencode/` and `~/.claude/` → `~/.config/opencode/` (OpenCode, `claude-to-opencode.ts:614–618`). Antigravity deliberately does **not** rewrite paths (unverified conventions, `claude-to-antigravity.ts:95–97`).

### Concrete before/after (from the code)

A Claude skill body containing:

```
Task ce-correctness-reviewer(review the diff for race conditions)
See ~/.claude/settings.json and run /ce-plan first.
```

Through **Codex** (`transformContentForCodex`, given an `agentTargets` entry for the reviewer):
```
Spawn the custom agent `ce-correctness-reviewer` with task: review the diff for race conditions
See ~/.codex/settings.json and run the ce-plan skill first.
```

Through **OpenCode** (`transformSkillContentForOpenCode` + `rewriteClaudePaths`): the `Task …` line is left structurally (OpenCode keeps `Task`), but `~/.claude/` → `~/.config/opencode/`, and fully-qualified agent refs like `compound-engineering:review:ce-correctness-reviewer` are flattened to `ce-correctness-reviewer` (`claude-to-opencode.ts:632–651`).

Through **Pi**:
```
Run subagent with agent="ce-correctness-reviewer" and task="review the diff for race conditions".
See ~/.claude/settings.json and run /ce-plan first.   (Pi rewrites /ce-plan → /ce-plan; no path rewrite)
```

The point: the *structural* conversion (frontmatter, file layout) is shared and cheap; the *semantic body rewriting* is bespoke per target, regex-driven, and brittle — it is the bulk of the per-target test surface (`tests/codex-converter.test.ts`, `tests/converter.test.ts`, etc., ~12 converter/writer test files).

---

## 2. The Target/Writer abstraction

The contract is a single interface, `TargetHandler` (`src/targets/index.ts:1218–1227`):

```ts
type TargetHandler<TBundle> = {
  name: string
  implemented: boolean
  defaultScope?: TargetScope          // "global" | "workspace"
  supportedScopes?: TargetScope[]
  convert: (plugin: ClaudePlugin, options) => TBundle | null   // pure
  write:   (outputRoot, bundle, scope?) => Promise<void>       // effectful
}
```

Targets register in a flat `Record` (`targets/index.ts:1229–1257`). The CLI commands (`convert.ts`, `install.ts`) are fully target-agnostic: they call `target.convert(plugin, options)` then `target.write(root, bundle, scope)` and never branch on target name except for one OpenCode scope quirk and a `codex` post-step (`ensureCodexAgentsFile`).

**Adding a new target requires, at minimum, four files:**

1. `src/types/<target>.ts` — the Bundle + per-component types (~30–160 lines; Codex's is 162, Pi's analog is smaller).
2. `src/converters/claude-to-<target>.ts` — `convert*` + the `transformContentFor<Target>` body rewriter (Antigravity's is 207 lines, Codex's 287, Pi's 359 — most of the length is the prose-rewrite regexes and name-dedup helpers).
3. `src/targets/<target>.ts` — the Writer. This is where the genuine engineering lives: Codex's writer is **975 lines**, almost entirely **idempotent merge + legacy-cleanup logic** (install manifests, managed-block markers in `config.toml`, `_managed` index in `hooks.json`, symlink-ownership checks under `~/.agents/skills/`, timestamped legacy-backup moves). OpenCode's writer delegates the common merge/cleanup to a shared `targets/managed-artifacts.ts`.
4. One line in the `targets` registry (`targets/index.ts`).

Plus optional plumbing: detection path in `src/utils/detect-tools.ts` (a `detectableTools` array entry, lines 23–80) and home-resolution in `resolve-home.ts`/`resolve-output.ts`. So the honest answer is **4 core files + ~2 plumbing edits + a test file**, and the Writer is 5–10× the size of the Converter because **safe, repeatable, multi-plugin-coexisting on-disk installs are the hard problem**, not the format translation.

---

## 3. The Model-tier abstraction

There are **two distinct mechanisms**, and CONCEPTS.md's "Model tier" entry is mostly a *content-authoring convention*, not converter code:

- **In the plugin content** (the "tier" idea): skills declare a semantic cost class — *extraction / generation / ceiling* — by tier name, and reference it rather than a model id, so model names never hardcode into skill bodies. When a runtime can't select models per agent, "every role runs on the inherited model and cost control falls back to structure: read budgets and output caps" (CONCEPTS.md, *Model tier*). This is a discipline the *skill authors* follow; the converter doesn't enforce it.

- **In the converter** (`src/utils/model.ts`, 61 lines): when a frontmatter `model:` field *does* appear, it's normalized. `CLAUDE_FAMILY_ALIASES` (lines 406–410) maps bare aliases (`haiku/sonnet/opus`) to canonical ids; `addProviderPrefix` (433–441) prepends a provider (`anthropic/`, `openai/`, `google/`, `qwen/`, `minimax/`) by name pattern; `normalizeModelWithProvider` (451–461) combines them for OpenCode's provider-prefixed ids.

The graceful-degradation trick on runtimes without per-agent model selection is in the **converter logic, not model.ts**: `claude-to-opencode.ts:417–444` writes a `model:` line **only for primary agents**, and **omits it entirely for subagents** so they inherit the parent session's provider (comment + issue #477 at lines 424–429: writing `anthropic/claude-haiku-4-5` on a subagent throws `ProviderModelNotFoundError` when the user runs a non-Anthropic provider). Codex and Pi agents (`renderCodexAgentToml`, `convertAgent` in pi) **carry no model field at all** — they inherit unconditionally. That is the degradation strategy: *drop the model selector and inherit* rather than translate it.

**Relevance to Clavain:** Clavain barely uses this — only **4 occurrences of `model: haiku`** across all agents/commands (grep of `os/Clavain/agents` + `commands`), and skills carry no `model:` field. So the model-tier machinery is near-irrelevant for a Clavain port; the omit-on-subagent rule is the only piece worth keeping, and it's three lines.

---

## 4. Dependencies & build

- **Runtime**: Bun (shebang `#!/usr/bin/env bun`, `src/index.ts:1`; `Bun.spawn` for git clone in `install.ts:566`). Scripts run via `bun run src/index.ts <cmd>` (`package.json` scripts). It is **not** plain Node — it relies on Bun's TS execution and `bun-types` (`tsconfig.json` `types: ["bun-types"]`) and `bun test`.
- **Production deps**: exactly **two** — `citty` (CLI framework, `^0.1.6`) and `js-yaml` (`^4.1.0`). Everything else (`semantic-release`, `@types/js-yaml`, `bun-types`) is dev-only.
- **TS config**: ES2022 / ESNext / `moduleResolution: Bundler`, strict (`tsconfig.json`).
- **Self-containment**: **Fully self-contained.** It touches only `fs`, `path`, `os`, and (for the GitHub-install path) `git clone` via subprocess. It never imports or calls Claude Code, the Claude CLI, or any Anthropic SDK. The only "Claude-aware" coupling is reading the `.claude-plugin/plugin.json` convention and the markdown/frontmatter layout — i.e. it depends on the *plugin format*, not the *runtime*. This is the single most important finding for portability: **the engine has no Claude Code runtime dependency.**

---

## 5. Porting to Clavain

Clavain (`os/Clavain/`) is itself a Claude Code plugin: `.claude-plugin/plugin.json` (name `clavain`, v0.6.254) with `skills`/`commands`/`agents` arrays, **76 skill files, 55 commands, 13 agents, 32 hooks, 65 scripts (bash + Python), `hooks/hooks.json`**. It already ships a **hand-rolled Codex install** (`.codex/agent-install.sh`, `.codex/INSTALL.md`, `scripts/codex-bootstrap.sh`, the `/codex-bootstrap` command, and a "wrapper sync" model) — a *completely different architecture* from CE's converter. Clavain skills use `AskUserQuestion` (10+ files), so the tool-name-mapping problem is real for Clavain too.

### Reuse as-is vs. rebuild

| CE component | Reuse for Clavain? | Why |
|---|---|---|
| `parsers/claude.ts` | **As-is** | Clavain's tree is exactly the `ClaudePlugin` input shape. Ingests with zero changes. Only `ce_platforms` is CE-specific (harmless; absent → "available everywhere"). |
| `utils/frontmatter.ts` | **As-is** | Generic `---` + js-yaml splitter. |
| `utils/model.ts` | **Mostly skip** | Clavain has 4 `model: haiku` lines total; the alias table + omit-on-subagent rule is trivial to inline. |
| `targets/index.ts` (TargetHandler interface, CLI driving) | **Reuse as pattern** | Clean abstraction, but Clavain only needs **one** target (Codex), so the registry/`--to all`/detect-tools machinery is overkill. |
| `targets/codex.ts` Writer (merge/cleanup) | **Steal the logic, not the file** | The 975-line idempotent-install + managed-block + hooks-merge + legacy-cleanup logic is genuinely valuable and is exactly what Clavain's hand-rolled `agent-install.sh` lacks. **But it writes the CE-shaped layout, and it conflicts with Clavain's existing wrapper-sync model** — reconciling the two is the main integration cost. |
| `converters/claude-to-codex.ts` + `utils/codex-content.ts` (body rewrites) | **Rebuild/adapt** | The regexes assume CE naming (`ce-` prefixes, `workflows:` aliases — `claude-to-codex.ts:193–208`, `WORKFLOW_ALIAS_OVERRIDES`). Clavain's namespacing (`clavain:`, `interX:` companions) differs, so the slash/Task/agent-ref rewriters need Clavain-specific rules. The `AskUserQuestion`/tool-name handling for Codex isn't even in CE's Codex path (it's OpenCode's `TOOL_MAP`) — Clavain would need to author its own. |
| OpenCode / Antigravity / Pi / Copilot / Droid / Kiro converters | **Discard** | Clavain targets only Claude Code + Codex. |
| Bun runtime + citty CLI | **Reconsider** | Clavain has **no Node/Bun build step today** — it's markdown + bash + Python. Introducing a Bun/TS toolchain is a new dependency class for a repo that is otherwise interpreted. |

### Effort & risks

**T-shirt size of a faithful converter-framework port: L–XL.** Not because the format translation is hard, but because: (a) you inherit a Bun/TS build into a markdown+bash+Python repo (new toolchain, CI, publish surface); (b) the Codex Writer's 975 lines of merge/cleanup must be **reconciled against Clavain's already-shipped hand-rolled Codex install** (`agent-install.sh` + wrapper-sync), and two competing "managed install" models in the same `~/.codex/` tree is a foot-gun (double-registration, conflicting cleanup, the exact `externallyManagedSkillNames` class of bug CE itself fought, `claude-to-codex.ts:77–110`); (c) the body-rewrite regexes need a Clavain-specific rewrite and a full test suite, because a wrong rewrite silently corrupts skill prose.

**Main risks:**
1. **Two Codex install models colliding.** Highest risk. CE's writer assumes *it* owns `~/.codex/skills/<plugin>/`, `agents/<plugin>/`, the `install-manifest.json`, and the `_managed` hooks block. Clavain's bootstrap assumes a wrapper-sync layout. Adopting CE's writer means migrating/retiring Clavain's existing path, with backup/rollback for users who already installed the old way.
2. **Regex brittleness on Clavain's denser namespacing.** Clavain has `clavain:*` plus a dozen `interX:` companion references; CE's rewriters were tuned for `ce-`/`workflows:` and would mis-handle these without new rules + fixtures.
3. **Toolchain drift.** A Bun/TS subproject in an otherwise interpreted plugin is ongoing maintenance (Bun version pinning, `bun test`, the `release:*` semantic-release scripts) that the rest of Clavain doesn't pay.
4. **Tool-name gaps.** CE's Codex path doesn't translate `AskUserQuestion`; Clavain uses it. New per-tool mapping work with no upstream reference to copy.

### Is the converter even the right abstraction for Clavain?

**No — not the full framework.** The converter abstraction earns its keep when you support **6+ heterogeneous targets** (OpenCode, Codex, Pi, Antigravity, Copilot, Droid, Kiro — exactly CE's matrix). Clavain supports **two runtimes, one of which (Claude Code) needs no conversion at all** and the other (Codex) it already half-supports. The registry/detect-tools/`--to all`/per-target-Bundle indirection is pure overhead at N=1 real conversion target.

**The thinner approach that gets ~80% of the value:** keep Clavain's single-purpose Codex path, but **transplant the three genuinely hard-won pieces of CE's engine into it**:
1. **The parser + frontmatter utils** (so Clavain stops re-deriving plugin structure in bash and reads its own manifest the same robust way).
2. **The Codex Writer's idempotent-install + managed-block + hooks-merge + legacy-cleanup logic** (the part Clavain's `agent-install.sh` most lacks — safe re-install, no clobbering user config, clean upgrades). Reimplement it to match Clavain's *existing* layout rather than CE's, or adopt CE's layout and migrate once.
3. **A Clavain-tuned `transformContentForCodex`** — the Task/slash/agent-ref/path/`AskUserQuestion` rewriters, with Clavain's namespacing rules and a fixture-based test suite.

That is an **M**, mostly Writer-hardening + a focused regex rewriter, with no new multi-target framework and (optionally) no Bun dependency if reimplemented in Clavain's existing Python.

---

## Recommendation

**Lean: NO-GO on porting the converter as a framework; GO on harvesting its parser, frontmatter, model-omit rule, and especially its Codex Writer merge/cleanup logic into Clavain's existing single-target Codex path.**

- **Full converter-framework port — t-shirt size L–XL.** Net-negative for Clavain: it pays the cost of N-target indirection and a new Bun/TS toolchain to support effectively one conversion target, while creating a high-risk collision with Clavain's already-shipped hand-rolled Codex install.
- **Recommended thinner approach — t-shirt size M.** Lift `parsers/claude.ts` + `utils/frontmatter.ts` (reuse as-is), reimplement the Codex Writer's idempotent install/cleanup discipline against Clavain's layout, and author a Clavain-tuned Codex body-rewriter with tests. Optionally keep it in Clavain's existing Python rather than adding Bun. This captures the durable value — *safe, repeatable, non-clobbering Codex installs and correct prose translation* — which is precisely the part Clavain is weakest on, without adopting machinery it doesn't need.

**Decisive factor for the go/no-go:** the converter's value is concentrated in the **Writer's safety machinery** (idempotent installs, managed-block markers, ownership-gated cleanup), not in the multi-target plumbing. Clavain should buy the former and skip the latter.

### Cited files read (commit 16442e86)

- `CONCEPTS.md` (full)
- `src/index.ts`, `src/commands/convert.ts` (1–232), `src/commands/install.ts` (1–576)
- `src/parsers/claude.ts` (1–272)
- `src/types/claude.ts` (1–680), `src/types/codex.ts` (1–162)
- `src/converters/claude-to-codex.ts` (1–287), `claude-to-opencode.ts` (1–815), `claude-to-antigravity.ts` (1–207), `claude-to-pi.ts` (1–359)
- `src/utils/codex-content.ts` (1–392), `src/utils/model.ts` (1–461), `src/utils/frontmatter.ts` (1–536), `src/utils/detect-tools.ts` (1–111)
- `src/targets/index.ts` (1–1257), `src/targets/codex.ts` (1–975), `src/targets/opencode.ts` (1–1180)
- `package.json`, `tsconfig.json`
- Clavain ground-truth: `os/Clavain/.claude-plugin/plugin.json`, `os/Clavain/hooks/hooks.json`, `os/Clavain/.codex/`, `os/Clavain/commands/codex-bootstrap.md`, component counts under `os/Clavain/{skills,commands,agents,hooks,scripts}`
