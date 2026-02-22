# PRD: Flux-Drive Intermediate Finding Sharing

**Bead:** iv-905u
**Sprint:** iv-firp
**Brainstorm:** docs/brainstorms/2026-02-22-flux-drive-intermediate-findings-brainstorm.md

## Problem

Parallel flux-drive reviewer agents work in complete isolation — if one agent discovers a critical issue, others can't adjust their analysis until after synthesis. This leads to contradictory recommendations, wasted tokens on invalidated analyses, and lower-quality reviews.

## Solution

A shared findings bus (JSONL file) that agents write to when they discover high-severity issues, and read from at natural checkpoints before finalizing their reports. The synthesis agent reads the full findings timeline for richer contradiction detection and convergence tracking.

## Features

### F1: Finding Schema & JSONL Transport

**What:** Define the finding data format and provide read/write utilities for the shared findings file.

**Acceptance criteria:**
- [ ] Finding schema defined: `severity` (blocking|notable), `agent`, `category`, `summary`, `file_refs[]`, `timestamp`
- [ ] Findings written to `{output_dir}/findings.jsonl` as one JSON object per line (append-only)
- [ ] Helper function `write_finding()` available in flux-drive dispatch context
- [ ] Helper function `read_findings()` returns parsed array of findings, optionally filtered by severity
- [ ] Empty/missing findings file handled gracefully (returns empty array)
- [ ] Concurrent appends from multiple agents do not corrupt the file (JSONL append-only guarantees this)

### F2: Agent Checkpoint Instructions

**What:** Add finding-write and finding-read instructions to each reviewer agent's task prompt so agents participate in the findings bus.

**Acceptance criteria:**
- [ ] Each reviewer agent prompt includes a "Peer Findings Protocol" section with:
  - Write instruction: append blocking/notable findings to `findings.jsonl` when discovered
  - Read instruction: check `findings.jsonl` before writing final report
- [ ] Blocking findings: agents MUST acknowledge in their report and adjust analysis if relevant
- [ ] Notable findings: agents SHOULD consider and note if they affected conclusions
- [ ] Finding write includes all schema fields (severity, agent name, category, summary, file refs)
- [ ] Agents that find no blocking/notable issues write nothing (no noise)
- [ ] The `findings.jsonl` path is passed as a variable in the agent task prompt (not hardcoded)

### F3: Timeline-Aware Synthesis

**What:** Enhance the synthesis agent to read the findings timeline alongside agent reports, enabling convergence detection and richer contradiction resolution.

**Acceptance criteria:**
- [ ] Synthesis agent receives `findings.jsonl` path as additional input
- [ ] Synthesis reads findings timeline and includes in analysis context
- [ ] Synthesis identifies which agents adjusted based on peer findings (convergence)
- [ ] Synthesis flags remaining contradictions that agents did not resolve despite peer findings
- [ ] Synthesis attributes finding discovery to the originating agent in the verdict
- [ ] Empty findings file handled gracefully (synthesis proceeds as before)
- [ ] Verdict format unchanged — findings context enriches analysis but doesn't alter the machine-readable output

### F4: `fetch_peer_findings` MCP Tool

**What:** An MCP tool in the interflux server that provides programmatic access to the findings bus, enabling future extensibility and tooling integration.

**Acceptance criteria:**
- [ ] New `fetch_peer_findings` tool registered in interflux MCP server
- [ ] Accepts parameters: `output_dir` (required), `severity_filter` (optional: "blocking"|"notable"|"all", default "all")
- [ ] Returns parsed JSON array of findings matching the filter
- [ ] Returns empty array if findings file doesn't exist
- [ ] Tool description clearly documents the finding schema
- [ ] Works with the standard flux-drive output directory structure

## Non-goals

- **Intermute integration** — No network transport for MVP; file-based only
- **Early termination** — Agents don't abort mid-analysis based on peer findings; they adjust at checkpoints
- **Agent re-dispatch** — No spawning follow-up agents based on findings
- **Cost tracking** — No measurement of tokens saved by early adjustments
- **Finding enforcement** — Checkpoint pull is advisory; no mechanism to verify agent compliance
- **Cross-review persistence** — Findings are per-review session, not persisted across reviews

## Dependencies

- **interflux flux-drive skill** — Must understand current dispatch and synthesis flow
- **intersynth synthesis agent** — Must understand current verdict format and dedup rules
- **interflux MCP server** — Must understand current tool registration pattern
- No external library dependencies — pure prompt engineering + file I/O + one MCP tool

## Open Questions

1. **Finding dedup** — Should synthesis dedup findings that multiple agents discovered independently, or does the existing cross-agent dedup in synthesis already handle this?
2. **Checkpoint timing** — Single checkpoint (before final report) or multiple (mid-analysis too)?
3. **Finding size limits** — Cap on findings count or summary length per agent?
