# Repository-aware Benchmark Expansion — Implementation Plan
**Bead:** iv-v81k
**Phase:** planned (as of 2026-02-17T00:00:00Z)

## Goal
Integrate repository-scale benchmarks into interbench with reproducible scoring and reporting.

### Task 1: Connectors
- Add adapters under `infra/interbench/adapters/benchmarks/` for MAFBench, PaperArena, RepoMaster-style tasks, GitTaskBench, and SWE-Bench++.
- Implement manifest-based normalization to a shared schema.

### Task 2: Runner updates
- Extend runner to support repo-level setup/cleanup phases and submission checks.
- Ensure deterministic scoring where supported.

### Task 3: Evaluation metrics
- Add metrics: pass@k, patch diff quality proxies, and completion latency.
- Add confidence bounds and minimum-run guardrails.

### Task 4: Ops and refresh cadence
- Add scheduled refresh jobs and cache invalidation policy.
- Add report artifact templates consumed by roadmap/research planning.
