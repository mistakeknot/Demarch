# Intermap Live Changes Hardening — Brainstorm

**Bead:** iv-54iqe
**Phase:** brainstorm
**Date:** 2026-02-28
**Status:** Decided

## What We're Building

A hardening iteration for Intermap's `live_changes` MCP tool that preserves the existing API while improving correctness and repeated-call performance. Scope includes symbol annotation reliability, non-silent error handling, and low-risk latency wins for repeated identical calls.

## Why This Approach

The current tool already exists and is integrated. A compatibility-preserving hardening pass gives faster, safer value than a redesign: we reduce operational risk, keep existing callers stable, and target the highest-confidence issues first.

## Key Decisions

1. **Approach:** Incremental hardening of the current `live_changes` path; no breaking API changes.
2. **Primary quality gate:** Balanced gate requiring both correctness improvements and measurable latency improvement.
3. **Success criteria rigor:** Strong gate, not best-effort.
4. **Performance threshold:** Require `>=30%` median latency reduction for repeated identical calls.

## Acceptance Gate

Work is complete only when all are true:
- Regression tests cover symbol overlap behavior for changed code regions.
- Silent exception swallowing is removed; failures are logged/observable.
- Benchmarks demonstrate `>=30%` median latency reduction on repeated identical `live_changes` invocations.

## Boundaries

- Keep public tool contract stable.
- Prefer low-risk optimizations and correctness fixes over architectural rewrite.
- Defer broader redesign ideas to follow-up beads if needed.

## Alignment

This choice advances Clavain/Intermap reliability-first execution by improving correctness and operator trust while preserving delivery momentum.

## Conflict/Risk

Risk: a strict 30% threshold may require deeper optimization than planned; if so, split remaining performance work into follow-up beads instead of lowering correctness standards.
