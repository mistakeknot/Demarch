---
name: intermap
description: "Project-level code mapping: project registry, call graphs, architecture analysis, agent overlay. MCP server with 6 tools."
---
# Gemini Skill: intermap

You have activated the intermap capability.

## Base Instructions
# intermap — Agent Guide

Project-level code mapping: project registry, call graphs, architecture analysis, agent overlay. MCP server with 6 tools.

## Canonical References
1. 'PHILOSOPHY.md' — direction for ideation and planning decisions.
2. 'CLAUDE.md' — implementation details, architecture, testing, and release workflow.

## Philosophy Alignment Protocol
Review 'PHILOSOPHY.md' during:
- Intake/scoping
- Brainstorming
- Planning
- Execution kickoff
- Review/gates
- Handoff/retrospective
- Upstream-sync adoption/defer decisions

For brainstorming/planning outputs, add two short lines:
- 'Alignment:' one sentence on how the proposal supports the module north star.
- 'Conflict/Risk:' one sentence on any tension with philosophy (or 'none').

If a high-value change conflicts with philosophy, either:
- adjust the plan to align, or
- create follow-up work to update 'PHILOSOPHY.md' explicitly.

## Execution Rules
- Keep changes small, testable, and reversible.
- Run validation commands from 'CLAUDE.md' before completion.
- Commit only intended files and push before handoff.


