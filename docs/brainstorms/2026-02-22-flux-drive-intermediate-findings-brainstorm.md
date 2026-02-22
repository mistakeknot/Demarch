# Flux-Drive Intermediate Finding Sharing

**Bead:** iv-905u
**Sprint:** iv-firp
**Phase:** brainstorm (as of 2026-02-22T18:21:30Z)
**Date:** 2026-02-22
**Status:** brainstorm

## What We're Building

A mechanism for parallel flux-drive reviewer agents to share high-severity findings in real-time, so agents can adjust their analysis based on peer discoveries rather than operating in complete isolation until the synthesis phase.

**The problem:** When 7 flux-drive agents analyze an artifact in parallel, each works in total isolation. If fd-safety discovers a critical vulnerability, fd-architecture can't adjust its recommendations. Contradictions are only caught in synthesis — after all agents have consumed their full token budgets. This wastes tokens and produces lower-quality reviews.

**The solution:** A shared findings file that agents write to when they discover significant issues, and read from at natural checkpoints before finalizing their reports. The synthesis agent also reads the findings timeline for richer contradiction detection.

## Why This Approach

### Transport: File-based (intermute optional)

Flux-drive currently uses file-system isolation exclusively — each agent writes to `{output_dir}/{agent-name}.md`. Adding intermute as a hard dependency mid-review introduces network calls, failure modes, and complexity that isn't justified for same-session agents sharing a filesystem.

**Decision:** Primary transport is `{output_dir}/findings.jsonl` — a shared append-only file. Intermute integration is deferred to a future iteration for cross-session and multi-machine scenarios.

**Why JSONL:** Avoids read-modify-write races when multiple agents append concurrently. Each agent appends one line — no locking needed.

### Consumption: Checkpoint pull

Agents check for peer findings at natural breakpoints (before writing their final report), rather than being interrupted by an orchestrator. This preserves agent autonomy — they decide how to incorporate findings into their analysis.

**Why not orchestrator injection:** Would require the dispatcher to manage running agent state and interruption mechanics. The Task tool doesn't support injecting context into running background agents. Checkpoint pull works within existing Claude Code primitives.

### Severity: Two levels

- **blocking** — contradicts or invalidates part of another agent's analysis. Agents MUST acknowledge blocking findings in their report.
- **notable** — significant finding that may affect other agents' conclusions. Agents SHOULD consider notable findings.

Informational findings stay in per-agent reports only. This keeps the shared channel high-signal.

### Synthesis: Timeline-aware

The synthesis agent reads both final agent reports AND the findings timeline. This lets it:
- See which agents adjusted based on peer findings (convergence signal)
- Detect remaining contradictions that agents didn't resolve
- Attribute finding priority to the discovering agent

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transport | JSONL file, intermute deferred | Matches existing file-based pattern, no new dependencies |
| Consumption | Checkpoint pull | Preserves agent autonomy, works with Task tool constraints |
| Severity levels | 2 (blocking, notable) | Low noise, clear agent obligations |
| Synthesis | Timeline-aware | Richer contradiction detection, convergence tracking |
| Finding scope | Per-review session | Findings don't persist across reviews (no intermute for MVP) |

## Design Details

### Finding Schema

```jsonl
{"severity":"blocking","agent":"fd-correctness","category":"api-conflict","summary":"POST /api/agents endpoint already exists with incompatible session_id semantics","file_refs":["internal/http/handlers_agents.go:34"],"timestamp":"2026-02-22T10:23:00Z"}
{"severity":"notable","agent":"fd-safety","category":"auth-bypass","summary":"No authentication on internal admin endpoints","file_refs":["internal/http/router.go:89"],"timestamp":"2026-02-22T10:24:15Z"}
```

### Agent Prompt Addition (checkpoint instruction)

Added to each reviewer agent's task prompt:

```
Before writing your final report, check for peer findings:
1. Read {output_dir}/findings.jsonl if it exists
2. For each "blocking" finding: acknowledge it in your report and adjust your analysis if it affects your domain
3. For each "notable" finding: consider whether it changes any of your recommendations
4. If you discover a blocking or notable finding during your analysis, append it to {output_dir}/findings.jsonl
```

### Synthesis Enhancement

The synthesis agent receives an additional input:

```
Findings timeline: {output_dir}/findings.jsonl
Use this to:
- Identify which agents adjusted their analysis based on peer findings
- Flag remaining contradictions that agents did not resolve
- Attribute finding discovery to the originating agent
```

### What Changes Where

| Component | Change | Scope |
|-----------|--------|-------|
| `interverse/interflux/` flux-drive skill | Add findings file path to agent prompts | Prompt modification |
| `interverse/interflux/` flux-drive skill | Pass findings path to synthesis agent | Prompt modification |
| `interverse/intersynth/` synthesis agent | Read findings timeline, detect convergence | Agent prompt update |
| Agent task prompts (fd-*) | Add checkpoint instruction block | Per-agent prompt addition |
| `interverse/interflux/` MCP server | `fetch_peer_findings` tool (optional, for programmatic access) | New MCP tool |

### What Does NOT Change

- Agent dispatch mechanism (still Task tool with `run_in_background`)
- Agent output format (still markdown reports with Findings Index)
- Verdict computation (still deterministic from synthesis)
- intermute (no changes for MVP)

## Open Questions

1. **Finding dedup in synthesis** — If fd-safety writes a blocking finding and fd-correctness also discovers the same issue independently, the findings file will have duplicates. Should the synthesis agent dedup, or is that already handled by existing dedup rules?

2. **Checkpoint timing** — "Before writing final report" is clear, but should agents also check mid-analysis (e.g., after analyzing 50% of files)? More checkpoints = faster reaction but more file reads.

3. **Agent compliance** — Checkpoint pull is advisory. An agent may ignore findings or fail to write them. Should there be any enforcement, or is this acceptable for MVP?

4. **Finding size limits** — Should there be a max findings count or summary length to prevent one verbose agent from dominating the shared channel?

## Scope

**In scope (MVP):**
- Findings JSONL file format and schema
- Checkpoint instruction in agent prompts
- Timeline-aware synthesis
- Basic `fetch_peer_findings` MCP tool

**Out of scope (future iterations):**
- Intermute integration for cross-session persistence
- Automatic early termination when blocking finding invalidates an agent's entire analysis
- Finding-based agent re-prioritization (e.g., dispatching a follow-up agent)
- Cost tracking of tokens saved by early adjustments

## References

- Gap analysis: `docs/research/orchestration-gap-analysis.md` (Gap 2)
- Flux-drive architecture: `interverse/interflux/`
- Synthesis engine: `interverse/intersynth/`
- Intermute service: `core/intermute/`
- Parent epic: iv-pt53 (Interoperability)
