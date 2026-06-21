# Agentic-Frontier Roadmap Delta — 2026-06-21

**Method.** Multi-agent workflow (`roadmap-frontier-delta`, 91 agents): research the mid-2026 agentic-orchestration/coding frontier across 5 dimensions → map each finding against the live 79-item backlog + roadmap (classify covered/partial/gap) → adversarially verify each gap (default-skeptical, must earn survival) → synthesize. **44 credible findings → 41 real gaps → 24 survived verification.**

**Ground truth verified against `.beads/issues.jsonl` (3570 lines):**
- Fail-open chain **n35t / 0ly7 / qf1k / scx1 — all CLOSED.** ⚠️ Roadmap lines 21-24 list them as still-open P0/P1 → **roadmap is stale; re-baseline.**
- `6h7x` (close-gate) **OPEN** — the spine ~10 survivors gate on.
- `ioe7` (interlab→interspect loop) **CLOSED 2026-06-21** (this session) — now live, unmonitored.
- `xka6`, `9lp.37`, `n2ma`, `3kol` **OPEN**; `9lp.35` **OPEN** (large child tree, real primitive).

---

## Headline

**The frontier reinforces the corrective-first stance — it does not overturn it.** The field has now independently *named* Sylveste's own documented failure modes: "silent looks-done-but-not-wired" failures (SDD / VerifyMAS), separate-verifier-beats-self-critique (Kambhampati / CoVerRL), and the generator-verifier consensus trap on freshly-wired self-improvement loops.

**The one net-new urgency:** `ioe7` (the interlab→interspect mutation→adaptation loop) went **live today** and recalibrates on **agent-produced** evidence with **nothing watching its verifier-vs-generator agreement trend** — a corrective gap on just-wired infra, the platform's highest-leverage class. The roadmap's own instinct ("sequence the loop after the close-gate so it doesn't become a ghost") was right; now it needs an active monitor.

**The dominant risk across all 24 survivors is manufacturing ghost infrastructure ahead of its consumer.** So the correct move: **make the close-gate (`6h7x`) the spine**, hang verification/cost/policy wiring off it, and defer every additive capability behind a measured kill-rule.

---

## Prioritized delta (24 survivors)

### P1 — do these (all corrective)

| # | Item | Lev | Cost | Gates on | Frontier basis (evidence) |
|---|------|-----|------|----------|---------------------------|
| 1 | **Consensus-trap breaker on interspect's calibration loop** — extend the live `calibrate-audit.py` cron + 20-use canary to track verifier-generator *agreement-rate AND output-diversity*; fire when agreement trends UP while defect-escape fails to fall. | high | mod | `9lp.37` (holdout register — **hard block**, else trend uninterpretable) | CoVerRL consensus-trap (MODERATE — mechanism well-corroborated, cite post-cutoff) |
| 2 | **Make runtime-health/state-delta the SUBSTANCE of the `6h7x` close-gate** — `phase:done` requires boot + `/diag/health` subsystem checks + a state-delta assertion; enumerate the silent-failure classes integration-test-green misses (DI/registration, startup crash, conn failure, projection lag). Gate CONTRACT, not an interhelm lib call. | high | mod | `6h7x` reaching enforce; resolve `Sylveste-byw` drift first | SDD/VerifyMAS — spec-diff misses runtime-wiring failures (**HIGH** — matches own ghost-infra finding) |
| 3 | **Fix roadmap line-33 SWE-bench drift** — `ynh`/`9lx` are phantom/mislabeled; re-ground to real harness beads (`2ss`/`b7j`/`r8g`/`m71`). Fold into `tizx`. *(Quick-win.)* | med | quick | — | OpenAI Verified-contamination post-mortem prompted the audit (drift fix **HIGH**, verified locally) |
| 4 | **Fold native-worktree retirement audit into `n2ma`** — audit whether Claude Code's *native* worktree primitive can RETIRE the hand-rolled `GIT_INDEX_FILE` machinery (the layer behind the `4pth` stealth-revert disaster). Additive config → P2 sub-tasks gated after the audit. Preserve interlock as the coordination layer. | med | mod | verify native flags exist first | Worktrees = consensus isolation primitive (**MODERATE** — native CC flags post-cutoff, must verify) |

### P2 — sequence after the close-gate / their blockers (mostly corrective)

5. **Ground review verdict in concrete pass/fail** — `/clavain:quality-gates` downgrades any unverified "clean" → `needs-verification` unless corroborated by the test/type/runtime artifact `6h7x` requires; reuse `9lp.35`'s VerificationStep. *(corrective; blocks on `6h7x`+`0ly7`)* — **HIGH** (Kambhampati, replicated).
6. **Wire clavain policy engine into a fail-CLOSED PreToolUse hook** — make `evaluatePolicy` actually fire before tool calls; consolidate `jm4` floor + cache-guard into one `{block|allow}` primitive. Drop the probabilistic framing. *(corrective; blocks on `rkm`+`6h7x`)* — pattern **HIGH**, "Policies on Paths" cite MODERATE.
7. **Pre-dispatch parallelizability + cost gate folded INTO the `3kol` Conductor spec** — parallel only across independent repos; intra-repo fan-out requires a spec-scope conflict check (intermap + interlock dry-run) *before* spawn; price the token multiplier; "don't transfer research-mode parallelism to coding." Not standalone. *(corrective)* — **HIGH** pattern (15× figure advisory only).
8. **Conflict-economics telemetry on the parallel dispatcher** — extend the existing dispatch log to record conflict-rate + merge-resolution-time per fan-out width (operationalize the orphaned toctou recommendation). Controller deferred to P3, gated on a non-trivial measured rate. *(corrective; child of `3kol`)* — mechanism MODERATE, numbers LOW (ship the instrument, not the numbers).
9. **`campaign.md` route-to-fallback-on-verified-failure** — replace blind retry/skip/abort with a VerificationStep-gated mid-chain gate. *(corrective; consumes `9lp.35`)* — **HIGH** (exponential chain-decay math).
10. **LLM-judge bias doc-hygiene + gate-hardening rider** — down-rate the unhedged "40%/15%/5-7%" figures to model-dependent ranges (a fact-correction today); add verbosity-anchor + cross-family-judge as acceptance criteria riding the *existing* judge bead. Reconcile the `fyo3.3`-closed-vs-`vision.md:24`-"same-model" contradiction (a closed-but-unwired cross-model switch = silent self-enhancement). *(corrective, quick-win)* — MODERATE (direction solid, percentages one-model).
11. **Make the close-gate parallel-safe (false-green guard)** — `6h7x`'s live-server test must FORBID green when validating against a *shared* runtime (port/DB/.env/migration) under N parallel worktrees. Cheap guard; full per-instance broker deferred to P3 under `3kol`. *(corrective; child of `6h7x`)* — mechanism HIGH, bites-today LOW.
12. **Audit-plane correlation layer** — join tool-call telemetry ↔ dispatch decision ↔ signed receipt under one trace/run_id. *(additive; under `owjn`)* — **TWO hard gates: all 3 feeds (`ewy3.2.1`/`9lp.35`/`7ttr`) live + a named first consumer (the `6h7x` ghost-scan).** MODERATE.
13. **Trust-card: glanceable per-task human-review surface** — render annotated-diff + pass/fail checklist + VerificationStep verdict from existing evidence (no bead currently emits a *human-facing* artifact). Defer screenshots/recordings as hype. *(additive; hard-block on `9lp.35`/`.6`)* — MODERATE (SDD solid, Antigravity-Artifacts cite post-cutoff).
14. **ACE coding-skill playbook vs compound-baseline bake-off** — kill-gated SPIKE: append-only Generator/Reflector/Curator skill memory vs the existing `intermem`+`interknow`+`/compound` baseline on a fixed corpus; pre-registered kill rule. *(additive; under `a4oj`, auto-kills if `a4oj.12` lands and delta collapses)* — LOW/MODERATE (high overlap with baseline — hence kill-gated).
15. **Pass@k harness extension + test-time-compute spike** — Phase 1: emit pass@k in interfer's `code_correctness.py` on the *actual local checkpoint* vs *clean* Terminal-Bench, with a kill rule. Phase 2 (RTV/PDR) hard-blocked on Phase-1 gain + `xka6` enforce. *(additive)* — MODERATE for frontier, local-transfer UNVERIFIED (the explicit risk).
16. **Skaffen compaction verification + context-rot working-set instrumentation** — Phase A (corrective): measure actual token-reduction from the closed Skaffen compaction + per-turn working-set vs a 15-40% band; note cache-hit (40-90%) and compaction (15-40%) are independent levers. Phase B (proactive ceiling) only if Phase-A shows the trigger fires in the rot zone. *(hard-gate on `104h`/`benl` evidence wiring; needs a live Skaffen loop)* — context-rot **HIGH** (Chroma 18-model study), Factory figures MODERATE band.

### P3 — deferred / watch-items / spikes

17. **Conductor (`3kol`) topology doc-hygiene** — write a non-empty description recording the structural rule (flat depth-1 fan-out, no recursive sub-coordinators); do NOT pin the volatile 25-thread integers or re-derive flux-review's MAX_CONCURRENT from them. *(corrective, quick-win)*
18. **Cache-aware effective-cost term in B2 routing** — compute effective per-call cost from observed cache_read/input split; freeze byte-stable per-tier prefixes. *(additive; HARD child of `xka6` — do not start before enforce)*
19. **Contamination-resistant benchmark re-pin** — re-pin to SWE-bench Pro / Terminal-Bench 2.0 *only after* the existing harness feeds a live `routing.yaml` decision (`m71`). Deferred — swapping evals before a consumer exists = ghost. *(additive)*
20. **VerifyLoop feasibility — self-generated-oracle vs TDD baseline** — Phase-0 three-arm bake-off on `r8g`; graduates only on a real attributable lift, sequenced after `6h7x`+gate fixes. *(additive, large, high ghost risk)* — ReVeal pattern MODERATE, marginal-lift-over-TDD UNDEMONSTRATED.
21. **interrank benchmark source-provenance ranking input** — down-weight vendor-self-reported scores; invariant test. *(corrective; child of `s3z6`, gated on `s10` kill decision; data-gated — must first measure the offset)*
22. **Local lint-triage classifier feasibility** — measure-only `s10` child; high moot-probability (two structurally-identical siblings already died on regex-covers-most). *(additive, likely-moot)*
23. **CoAgent live-external-state concurrency watch-item** — track only; trigger on a first observed shared-live-state-mutation workload where worktree isolation is impossible; **kill by ~2026-09** if none appears. *(additive, weakest evidence — single ~1-week-old preprint)*

*(Item 24 = the LLM-judge `fyo3.3` reconciliation sub-task, folded into #10.)*

---

## What the frontier VALIDATES (keep prioritizing)

- **`6h7x` close-gate** — the single most-validated bead; SDD/VerifyMAS/silent-failure-detection all name it as *the* frontier gap; ~10 survivors gate on it. **Make it the spine.**
- **`n35t`/`scx1`/`0ly7`/`qf1k` fail-open fix** — reinforced by external-verifier-beats-self-critique; **already CLOSED** (roadmap stale).
- **`xka6` B2 shadow→enforce** — cleanest narrow loop; becomes the hard dep for two additive levers (cache-cost, pass@k).
- **`owjn`/`104h`/`tizx`** — measurement-substrate-first directly validated ("auditability is the enterprise blocker", "done≠wired").
- **`ioe7`** — confirmed live + confirmed the #1 new monitoring gap.
- **`9lp.35` VerificationStep** — the reusable primitive 3 survivors should CONSUME, not re-implement.
- **Local-specialist track (`s10`/`s3z6`/interrank)** — open-weight near-parity validates it; keep `s10`'s kill-rule discipline.
- **`n2ma` worktree-per-task + interlock** — right file-isolation + coordination split; worktrees solve FILE not RUNTIME/LOGICAL conflicts, so interlock isn't redundant.

## What was deliberately DROPPED (anti-hype)

Bigger-context-windows (rot makes them worse); cross-runtime compaction primitive (no consumer); topology-envelope probe + re-deriving MAX_CONCURRENT (regresses a tuned cost gate); runtime-isolation epic / devcontainer broker (premature, no consumer); probabilistic policy-violation float; Antigravity screenshots/recordings as trust artifacts; standalone chain-depth-cap policy (no consumer); dual-order pairwise judge scoring (path is single-doc); the 73%/15×/17× headline numbers as facts; routing.yaml CI-lint (guards an impossible failure); immediate benchmark swap.

## Meta — verify before acting

All arXiv IDs (Policies-on-Paths `2603.16586`, test-time-compute `2604.16529`, CoAgent `2606.15376`) and the CoVerRL/Managed-Agents/native-worktree-flags claims are **post-cutoff and unverified** — treat the *patterns* as load-bearing, the *cites/versions/numbers* as decorative. Benchmark deltas (80%→23%, +6.7/+12.2pp, Factory 15.1%/39.4%, ~90% cache-read) are single-source — used as bands, never imported as facts. **Precondition risks:** Skaffen instrumentation needs a live loop; conflict telemetry needs real multi-agent CODE dispatch exercised; `9lp.35` must be completable as a *general* cross-plugin gate (3 survivors depend on it).
