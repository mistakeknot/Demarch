---
date: 2026-05-06
status: proposal-ready
target_audience: Anthropic Claude Code team (filed by user when ready)
source_bead: sylveste-a4oj.9.2
related_bead: sylveste-a4oj.9.1 (shipped infrastructure)
---

# Feature request: per-turn skill-listing trim via UserPromptSubmit hook

## Summary

Add a Claude Code hook output capability that lets a `UserPromptSubmit` hook **suppress unused skills from the system prompt** for the current turn. Mirrors the existing **deferred MCP tools** mechanism (where MCP tool schemas are not loaded until `ToolSearch` retrieves them) but applied to skills.

## Problem

Claude Code's system prompt currently loads the full skill listing on every turn. Per a typical user-installed plugin set, this is **~150 skills × ~40-80 tokens each = ~8 kt of input per turn**. Most turns produce "no skill applicable" — the listing is paid context for a routing decision that is largely deterministic (60-90% per [internal study](https://github.com/mistakeknot/Sylveste/blob/main/docs/research/flux-review/sylveste-improvements-multi-axis/2026-05-04-synthesis.md), tracks A/B/C/D 4/4 convergence). A 2026-05-29 ecosystem-wide re-audit independently re-confirmed this magnitude: ~150 skill descriptions still repeat the same `Use when / TRIGGER / SKIP / Examples` framing (~3-4 kt/session of pure boilerplate), and the plugin set has only grown (57 interverse plugins, zero retired) — so the listing is not self-limiting and a one-time static prune will not hold. This is fresh evidence that per-turn trimming, not a static cut, is the right shape.

Existing `UserPromptSubmit` hook shape (`hookSpecificOutput.additionalContext`) can only **add** context. There is no mechanism to **remove** skills the hook knows are not needed.

## Proposed shape

Extend `UserPromptSubmit` hook output:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "...",
    "skillFilter": {
      "include": ["clavain:work", "interpath:roadmap"],
      "exclude": []
    }
  }
}
```

Semantics:
- If `skillFilter.include` is set: only those skills appear in the system prompt for this turn; all others move to a deferred-skill listing (name + description omitted; available via a `SkillSearch` tool analogous to `ToolSearch`).
- If `skillFilter.exclude` is set: those skills move to deferred; all others remain.
- Either field can be set; precedence: include > exclude.
- Missing field: existing behavior (full listing loaded).

## Hook author responsibilities

- The hook decides which skills are relevant from the user prompt (e.g., via prefix table, embedding cosine, keyword houses).
- The hook MUST NOT exclude built-in skills the harness needs for core operation (Claude Code can document the protected set).
- A miss-and-trimmed turn is recoverable via `SkillSearch` (Claude can pull a deferred skill on demand, same as deferred MCP tools today).

## Why this matters

- Per-session savings: ~5-8 kt input × 30-50 turns/session = 150-400 kt/session savings under realistic workflows
- Per-week at scale: ~1.5 Mt/week of routing inference (the current cost of LLM-based skill deliberation per turn)
- Compounds with deterministic prefix routers (already shipped via `scripts/skill-prefix-router-hook.sh` in this repo) — those can confidently emit `skillFilter.include` for slash-command turns

## Backward compatibility

- Hooks that don't return `skillFilter` see no behavior change.
- Existing `additionalContext` continues to function unchanged.
- Existing `decision: block` semantics unchanged.

## Empirical grounding

A 30-day cass extraction over this user's sessions ([investigation](https://github.com/mistakeknot/Sylveste/blob/main/.beads/issues.jsonl) — sylveste-a4oj.9.2 close-reason) showed:
- 51% of skill invocations are direct slash commands → deterministically routable
- 30% are autonomous mid-task → harness-internal, no hook can help
- 12% are imperative-with-slash-mid-prompt → routable via prefix scan (shipped)
- 6% are pure conversational triggers → require LLM deliberation (no router can replace)

Of the routable ~60-65% surface, today's hooks cannot reduce input-token cost without `skillFilter`.

*Methodology note:* token-savings figures in this request are derived from direct session/transcript observation (cass extraction), not from bead-tracker rollups — the project's beads DB has had data-loss events, so per-bead cost aggregates are not a reliable source for the numbers quoted here.

## Alternatives considered

1. **Naive keyword router** (POLY-2 houses: WORK/REVIEW/RESEARCH/MEMORY) — rejected. 95.6% false-positive rate at the population level (24.5% of all prompts match, only 4.4% of matches lead to skill invocation).
2. **Hint-injection only** (currently shipped) — saves only output-side deliberation tokens (~100-300/turn at best), partly offset by hint cost. Does not reach the ~7.8 kt/session input-side savings the synthesis projected.
3. **Per-project skill curation** — possible today via `enabledPlugins`, but coarse: it disables the plugin globally for all turns, not per-turn relevance. Loses skill availability for the rare-but-needed turns.

## Open questions

- Should `skillFilter` apply to **slash-command resolution** as well, or only to system-prompt listing? (i.e., if I `exclude` a skill, can the user still type `/that-skill` and have it resolve?) Recommend: filter affects listing only; slash-command resolution remains unconditional.
- Should there be a `SkillSearch` tool symmetric to `ToolSearch` for retrieving deferred skill descriptions on demand? Recommend: yes, for parity.
- Telemetry: hook authors will want to see whether their `skillFilter` choices are reducing `SkillSearch` invocations (good signal) or increasing them (over-aggressive trim).

## Companion implementation already in this repo

`scripts/gen-skill-prefix-table.py` + `scripts/skill-prefix-router-hook.sh` (shipped 2026-05-06 under sylveste-a4oj.9.1) already build a deterministic prefix table and emit `additionalContext` hints. Adding `skillFilter` output is a one-line change to the hook once Claude Code accepts the field.
