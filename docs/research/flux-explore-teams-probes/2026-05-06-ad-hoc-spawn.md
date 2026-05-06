---
artifact_type: probe
probe: ad_hoc_spawn
bead: sylveste-3xl3.1.4
date: 2026-05-06
verdict: ad-hoc-supported
verdict_basis: documentation
docs_url: https://code.claude.com/docs/en/agent-teams
---

# F1.4 — Ad-Hoc Teammate Spawn Probe

**Verdict: `ad-hoc-supported`** — natural-language spawn prompts are the *primary* documented spawn mechanism. Subagent definitions are an opt-in, not a requirement.

## Evidence

### Primary spawn pattern is ad-hoc (per docs)

From `https://code.claude.com/docs/en/agent-teams`, "Start your first agent team":

> "After enabling agent teams, **tell Claude to create an agent team and describe the task and the team structure you want in natural language**. Claude creates the team, spawns teammates, and coordinates work based on your prompt."

Example given:

> "I'm designing a CLI tool that helps developers track TODO comments across their codebase. Create an agent team to explore this from different angles: one teammate on UX, one on technical architecture, one playing devil's advocate."

No subagent definition file is referenced. The spawn is purely prompt-driven.

### "Best practices" reinforces ad-hoc usage

> "Spawn a security reviewer teammate with the prompt: 'Review the authentication module at src/auth/ for security vulnerabilities. Focus on token handling, session management, and input validation. The app uses JWT tokens stored in httpOnly cookies. Report any issues with severity ratings.'"

Again — the spawn carries the full prompt inline. No `.claude/agents/*.md` file is referenced.

### Subagent definitions are presented as an *option* for *reuse*

From "Use subagent definitions for teammates":

> "**When spawning a teammate, you can reference a subagent type** from any subagent scope: project, user, plugin, or CLI-defined. **This lets you define a role once**, such as a security-reviewer or test-runner, and **reuse it both as a delegated subagent and as an agent team teammate**."

The "can" + "lets you define a role once ... and reuse it" framing is permissive: definitions are the path when you want reusable canned roles. Ad-hoc prompts are the path when each teammate's role is bespoke (which is exactly the cluster-debate use case — each cluster has different specs and a different prompt body).

### Limitation note that affects subagent-definition path

> "The `skills` and `mcpServers` frontmatter fields in a subagent definition are not applied when that definition runs as a teammate."

Tools allowlist and model ARE applied when using a subagent definition; skills and MCP servers are dropped. For our use case (debaters need only Read + SendMessage + task tools, no MCP), this is acceptable either way — but it's a useful fact for choosing between ad-hoc and definition-based spawn.

## Plan implication

Plan F3.2 spawn helper can use ad-hoc prompts directly:

> "Build 5 teammate prompts: Orchestrator-lead / Author / 3 × Debater / Questioner."

These are all generated per-run from the cluster output — there is no reusable role being defined. Ad-hoc prompts are the right primitive. **The plan's F3.2 design is intact**; no fallback to writing transient `td-debate-{slug}-cluster-{N}.md` files in `.claude/agents/` is needed.

The plan's F1.4 contingency ("If `definition-file-required`: F3 fallback path is to write generated debater prompts to ephemeral `.claude/agents/td-debate-{slug}-cluster-{N}.md` files...") is **not needed and should be removed** from F3 implementation scope.

### Spawn API mechanics

The docs do not specify an explicit "spawn API". The pattern is conversational: the lead is instructed (via its prompt) to "spawn N teammates with these prompts" and Claude Code's harness handles the actual session creation. This means F3.2 does not call a Python/bash spawn function — it builds a prompt for the orchestrator-lead that lists the 5 teammates with their per-teammate spawn instructions, and the lead executes the spawn via natural language to its own harness.

This is a small but important refinement to F3.2: the helper's job is to **construct the orchestrator-lead's spawn prompt** (a markdown text payload), not to call any "spawn 5 teammates" API directly. The lead reads the payload and spawns teammates as instructed. F4's debate-driver code is therefore a thin file-writer + transcript-tail-reader rather than an active orchestrator.

## Status

No design-breaking finding. F3 cleared to proceed with the ad-hoc path; F1.4's contingency for definition-file fallback is removed from scope.
