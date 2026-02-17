# PRD: Framework and Benchmark Freshness Automation

**Bead:** iv-wrtg  
**Date:** 2026-02-17

## Problem
Framework releases and benchmark papers move quickly, but roadmap updates lag; stale assumptions increase technical debt and reduce experimental relevance.

## Goal
Build automated freshness checks that trigger review tasks when major OSS releases or new benchmark papers appear.

## Core Capabilities

### F0: Signal ingestors
- Add periodic checks for release pages/packagings for ADK, LangGraph, AutoGen, agno, smolagents, CrewAI, OpenHands.
- Add arXiv and publication feed for papers in agentic research.

### F1: Impact classification
- Classify changes as: docs, features, API break, benchmark implication.
- Route impact changes to a dedicated interwatch review bead.

### F2: Review workflow
- Auto-create low-friction P2/P3 investigation beads with links to source diffs.
- Add stale-ness indicators in roadmap and module summaries.

### F3: Monitoring and alerting
- Add run logs with last-seen versions and missed-check counters.
- Define escalation threshold for missed windows beyond 14 days.

## Non-goals
- Continuous model-agnostic re-evaluation of every benchmark run.
- Auto-merging framework-driven changes without review.

## Dependencies
- `interwatch` for tracker updates and alerts
- `interflux`/`clavain` to consume review recommendations
