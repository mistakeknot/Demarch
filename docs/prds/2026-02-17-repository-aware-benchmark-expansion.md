# PRD: Repository-aware Benchmark Expansion for SWE Tasks

**Bead:** iv-v81k  
**Date:** 2026-02-17

## Problem
Current benchmark coverage is narrow for repository-level coding behavior. We need deeper, fresher coverage for maintenance and integration quality.

## Goal
Extend interbench coverage with a focused SWE benchmark suite including MAFBench, PaperArena, RepoMaster/GitTaskBench patterns, and SWE-Bench++.

## Core Capabilities

### F0: Dataset adapters
- Add dataset connectors for MAFBench, PaperArena, RepoMaster/GitTaskBench, and SWE-Bench++.
- Normalize task schema and expected output format for interbench.

### F1: Scoring and ranking
- Add pass/fail, patch quality, and time-to-solution scoring.
- Track confidence bands with minimum sample sizes.

### F2: Automation
- Add nightly/weekly benchmark refresh where upstream sources publish updates.
- Add reproducibility checks and fixture snapshots.

### F3: Decision integration
- Feed results into `interflux` routing and model-cost experimentation loops.
- Add one summary artifact consumed by `interphase` for roadmap planning.

## Non-goals
- Full benchmark-suite infrastructure replacement.
- Publishing external benchmark results publicly.

## Dependencies
- `infra/interbench` for run orchestration and schema
- API or dataset access points for each benchmark source
- `interstat` for token and cost joins
