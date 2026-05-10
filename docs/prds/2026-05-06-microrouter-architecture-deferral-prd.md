---
artifact_type: prd
bead: sylveste-s3z6.19.10
stage: design
date: 2026-05-06
brainstorm: docs/brainstorms/2026-05-06-microrouter-architecture-decision-brainstorm.md
review_synthesis: docs/research/flux-drive/2026-05-06-microrouter-architecture-decision-brainstorm-a4dbb251/synthesis.md
---

> **⚠️ SUPERSEDED 2026-05-08** — This PRD operationalized a β-deferral decision that was invalidated the next day by `.19.1` Phase 1 measurement (commit `7f224cca`). The `.19` microrouter epic was closed because `agent-roles.yaml` covers only 6.2% of subagent dispatches — adding a learned router on top can't help at that scope. See `docs/brainstorms/2026-05-06-microrouter-heuristic-baseline.md` for the kill analysis.
>
> **What's still useful here**: the heuristic-stratified eval-split idea (would have applied to any post-coverage-extension router question), the "active deferral with pre-registered triggers" pattern (general-purpose project-management technique), and the F4 `/clavain:status` surfacing concept (would help any future deferred decision regardless of microrouter).
>
> **What's stale**: the `.19.10` bead, the F1–F4 child beads (`Sylveste-1mp6/5p7s/ngft/58tb`), the bead-body cascade work, and the auto-revert mechanics for the 2026-06-30 review date. None of those beads exist in canonical Dolt; the deferral deadline is moot because the architecture was killed not deferred.

# PRD — Microrouter Architecture Deferral Operationalization

## Problem

The architecture-decision brainstorm landed on "defer to β after `.19.9` ships + 4 sprints of pass@1 telemetry," but the brainstorm review surfaced 1 P0 + 9 P1 + 4 P2 findings showing the deferral is strategically sound but operationally incomplete. Without operational definitions, coordination protocol, and cascade governance, the deferral risks: (a) Schelling-trap pressure to declare β "ready" with weak data when the deadline hits, (b) wasted deferral time if D2 (heuristic-baseline measurement) returns "kill the epic" mid-flight, (c) opaque project state for future readers (especially `.19.8`-α-shelved), (d) a single point of failure if the named decision authority is unavailable on the 2026-06-30 review date.

## Solution

Convert the deferral from a "pause and wait" stance into an **active deferral with pre-registered triggers, parallel D2 measurement, two-sprint check-in cadence, and a documented escalation path**. Pin operational thresholds before accumulation begins so they cannot drift under deadline pressure. Punt the heuristic-controlled-circularity P0 (fd-systems) to `.19.1`'s design phase but pre-register heuristic-stratified eval split as a minimum requirement so the design phase cannot ship without addressing it. File D2 as a sibling bead runnable in parallel with `.19.9`. Update `.19.1`/`.19.2`/`.19.8`/`.19.9` bodies so future readers do not need to chase brainstorms to understand the state.

## Features

### F1: Bead-body updates for the deferral cascade

**What:** Update `.19.10` notes and the bodies of `.19.1`/`.19.2`/`.19.8`/`.19.9` so each bead reflects its post-deferral status. This is the mechanical work that makes the brainstorm + PRD load-bearing on the bead graph.

**Acceptance criteria:**
- [ ] `.19.10` notes section appended with: PRD path, decision summary, deadline + check-in cadence, escalation path, link to brainstorm + synthesis
- [ ] `.19.1` body updated to reflect: (a) v0 architecture is β not α, (b) blocked on `.19.9` + 4 sprints of pass@1 telemetry, (c) when resumed, MUST address heuristic-stratified eval split before any LoRA training (pre-registered minimum)
- [ ] `.19.2` body updated to reflect: label source = pass@1 from `.19.9` outcome column (NOT judge labels); blocked on `.19.9` + 4 sprints
- [ ] `.19.8` body updated with closing note: "α v0 commit shelved per `.19.10` (2026-05-06). Brainstorm contributions absorbed by downstream beads but the chosen architecture was deferred to β. See [link to .19.10 brainstorm]." Bead stays CLOSED — note clarifies state for future readers.
- [ ] `.19.9` body updated to add: critical-path role for the entire `.19` epic; success criteria includes the operational definitions pinned in this PRD (volume per cell, label-noise measurement, sprint-counting protocol); explicit linkage to the four mitigation options for caveat 1 — pick at minimum heuristic-stratified eval split.
- [ ] `.beads/issues.jsonl` regenerated via `bd export -o .beads/issues.jsonl`
- [ ] All updates land in a single commit referencing `sylveste-s3z6.19.10`

### F2: D2 (heuristic-baseline measurement) as a sibling bead with concrete eval protocol

**What:** File the 2026-05-05 brainstorm's D2 / Approach E as its own bead under `.19`, runnable in parallel with `.19.9`. Pin a concrete eval protocol so D2 is not a vague "measure heuristic vs oracle" lump.

**Acceptance criteria:**
- [ ] New bead created: `sylveste-s3z6.19.12` (or next available index under `.19`) — type=task, priority=P1, labels include `routing`, `heuristic-baseline`, `epic-survival-check`
- [ ] Body specifies eval protocol:
  - Workload: replay shadow over the existing `.beads/` verdict corpus (closed beads with verdict_status)
  - Per-verdict record: `(heuristic_recommendation, what_was_actually_used, judge_flag_outcome)`
  - Heuristic hit-rate computed per `(agent, complexity_tier)` cell
  - Oracle upper bound: synthesized from `verdict_outcome` aggregation OR from manual relabeling of a 200-sample stratified subset (whichever has lower noise)
  - Headroom = oracle_accuracy − heuristic_accuracy, broken down by tier and by routing-eligible vs sonnet-floored agents
- [ ] Decision rule pre-registered:
  - **Headroom < 5% on routing-eligible traffic** → close the entire `.19` epic with `19-CLOSE` ceremony bead; reverse the dormant-five prune (D1 from 2026-05-05) if it shipped
  - **Headroom 5-15% concentrated in stable-7** → narrow `.19.1` resumption to a stable-7-only learned router; long tail stays heuristic
  - **Headroom > 15% OR concentrated in long tail** → `.19.1` resumes as content-feature classifier (per 2026-05-05 brainstorm framing)
- [ ] Coordination point with deferral: D2 result is a CHECKPOINT (not a gate). If D2 says "kill epic" before 2026-06-30, immediately re-open `.19.10` and close epic. If D2 says "epic survives," continue deferral. If D2 hasn't run by 2026-06-30, run it BEFORE resuming `.19.1`.
- [ ] **Active alert mechanism (post-review patch):** D2 result publication MUST trigger an `.19.10`-bound notice via `bd update sylveste-s3z6.19.10 --notes "D2 result published: <verdict>"` AND set bd state field `d2_result=<verdict>` on `.19.10`. The deferral check-in protocol (F3) reads this field at each check-in. If the verdict is `kill-epic`, the next session-start hook runs `/clavain:route sylveste-s3z6.19.10` automatically (forces re-entry). Without this active path, D2 can publish a kill verdict that sits unread for weeks.
- [ ] Bead is independently runnable: doesn't block on `.19.9`, doesn't block `.19.9`. Work can land any time.
- [ ] Acceptance includes: result doc at `docs/research/2026-MM-DD-microrouter-heuristic-baseline-d2.md`

### F3: Cascade keep-alive cadence + backup decision authority + escalation mechanism

**What:** Establish the active-deferral mechanics so the deferral does not drift. Two-sprint check-in cadence, named backup authority for the deadline, auto-revert behavior if the deadline passes without explicit human decision.

**Acceptance criteria:**
- [ ] `bd state` field on `.19.10`: `deferral_check_in=YYYY-MM-DD` set to first check-in date (2026-05-20 = ~2 sprints from now)
- [ ] `bd state` field on `.19.10`: `deferral_deadline=2026-06-30`
- [ ] `bd state` field on `.19.10`: `decision_authority_primary=arouth1`
- [ ] `bd state` field on `.19.10`: `decision_authority_backup=arouth1` (single-operator project; backup defaults to primary but field is explicit; future contributors with delegation will populate this)
- [ ] `bd state` field on `.19.10`: `auto_revert_action=surface-forced-reentry` (post-plan-review patch — Path C; changed from `auto-close-epic` which violated CLAUDE.md rule b requiring human confirmation for epic closes). When deadline passes, `/clavain:status` (per F4 follow-up) surfaces "deadline exceeded — re-enter via `/clavain:route`"; close still requires explicit human action.
- [ ] **F4 follow-up bead filed**: `/clavain:status` enhancement that reads the deferral state fields and surfaces the appropriate notice (healthy / check-in due / overdue / stale / approaching / exceeded). Filed as a sibling under `.19` epic so the surfacing serves any future deferrals on the bead graph, not just this one. Plan T8 owns the bead-creation step.
- [ ] `.19.10` final notes include: explicit pointer to the state-field protocol and the F4 follow-up bead ID so any future reader can find the cadence without reading the PRD.

**Plan-review note (Path C, 2026-05-06):** The original PRD revision had a session-start hook design with BLOCKING escalation. Plan review found 3 P0s in that design — SessionStart hooks can't actually block sessions per Claude Code spec, the script crashed under `set -euo pipefail` due to a grep/pipefail interaction, and `auto-close-epic` violated CLAUDE.md. Path C keeps the bd state fields (durable record + future tooling input) and delegates surfacing to a follow-up `/clavain:status` enhancement (F4 bead). Operator-invoked surfacing is the right model — it puts a human in the loop for the decision, which is what CLAUDE.md's bead-close rules require for epic actions.

### Operational definitions (pinned in PRD, referenced from `.19.9` body)

These are pre-registered numbers that the strategy phase commits to. Once `.19.9` ships, these are the gates for "is β telemetry ready":

**"4 sprints" definition (AND-gate, not OR-gate):**
- One sprint = one calendar week
- Cumulative volume threshold: ≥80 verdicts per (agent_category, complexity_tier) cell for the stable-7 agents; ≥20 verdicts per cell for long-tail (defined as agents with use_count ≥3 over the accumulation window)
- Both must be satisfied before β is "ready": **4 calendar weeks AND sufficient volume per cell**, whichever finishes later
- **Rationale (volume thresholds):** ≥80/cell on stable-7 derives from rule-of-thumb LoRA stability (rank-16 needs ~1K-2K total examples, 7 stable agents × 80 ≈ 560 base + long-tail = ~1K). ≥20/cell on long-tail allows per-cell sanity but accepts higher variance for those cells. Numbers are pre-registered floors — strategy phase chose them; `.19.1` design phase MAY tighten but not loosen.
- **Rationale (calendar gate):** prevents over-eager closure on bursty weeks. Bursty repos can hit volume in 2 weeks but won't have seen 4 weeks of agent-population drift, which is the main motivation for telemetry vs judge labels.

**"Label noise > 30%" measurement protocol:**
- Sample 200 closed beads from the accumulation window; manually relabel pass@1 (clean-pass / regression-within-N=4-sprints / ambiguous)
- Label noise = (count where manual_label ≠ automated_label) / 200
- Threshold: >30% noise → escalate to γ contingency; 15-30% → strategy phase decides whether to ship β with caveats or escalate; <15% → β is the architecture
- Measurement run: at end of accumulation window AND at the first sprint check-in (early-warning signal)
- **Rationale:** 30% is the floor where LoRA classification training stops being useful (label noise dominates signal). 15% is the threshold where bias correction techniques become reliable. Numbers from rule-of-thumb in classification literature; pre-registered for audit.

**"5% headroom" threshold for D2 (heuristic-baseline):**
- Headroom = oracle_pass_rate − heuristic_pass_rate, computed on routing-eligible traffic only (excludes sonnet-floored agents)
- Bootstrap CI (95%) over 200 samples × 1000 resamples; threshold compares lower bound, not point estimate
- <5% (lower bound) → close epic; ≥5% → continue per F2 acceptance criteria
- **Rationale:** 5% lower-bound is the minimum headroom that justifies multi-week LoRA training when the heuristic is already deployed and free. Below 5%, the cost-benefit fails. The 2026-05-05 brainstorm proposed ~5% as a judgment call; this PRD pre-registers it as the bootstrap-lower-bound threshold to make it operationally specific.

### Caveat 1 mitigation pre-registration (co-required, post-PRD-review patch)

The brainstorm review's P0 (β has heuristic-controlled circularity) named four mitigations: off-policy randomized traffic, manual-override weighting, heuristic-stratified eval split, loss penalty for heuristic agreement. The PRD review (2-agent flux-drive on this doc) flagged that eval-split-only is a thermometer, not a thermostat — it measures the gap but doesn't close it. To address that P0, this PRD now **co-requires two mitigations** instead of one:

**Required #1 (diagnostic): heuristic-stratified eval split.** Per-strata recall on heuristic-easy and heuristic-hard cases must both be reported. Pure eval methodology; no training-loop changes; cheap to add. This is a measurement gate — `.19.1` design phase MUST include it before `.19.3` ships any LoRA model.

**Required #2 (corrective): off-policy randomized traffic during `.19.9` accumulation window.** During the 4-week accumulation, randomize the model choice for **5-10% of routing-eligible calls** (excludes sonnet-floored agents). The randomized fraction breaks the heuristic→outcome→router loop by injecting non-heuristic-controlled outcomes into the training corpus. Without this, β's anchor is not "ground-truth pass@1" but "pass@1 conditional on heuristic's choice."

- **Rationale (5-10% range):** below 5% the off-policy fraction is too small to dent the heuristic-imitation tendency; above 10% the randomization itself causes too many bad-routing incidents in production. 5-10% is a defensible band; `.19.5` resolver design picks the exact number.
- **Implementation locus:** `.19.5` (resolver integration) — not `.19.1` (training design). The randomization happens at routing time, not training time. Adds a feature requirement to `.19.5`'s scope: "support a configurable off-policy fraction with audit logging."
- **Failure mode:** if `.19.5` cannot be modified to support off-policy randomization (e.g., resolver chain ordering precludes it), fall back to **manual-override weighting** as Required #2 instead. That requires session telemetry on user manual model overrides, which may already be in `.19.9` scope; check at `.19.9` design.
- **Hard fallback:** if neither active mitigation is viable by `.19.5` design phase, **escalate to γ-contingency**. Eval-split-only without any active correction is not sufficient.

The remaining two mitigations (loss penalty for heuristic agreement, full manual-override weighting if not used as Required #2) stay open for `.19.3` training design. They're additive on top of the two co-required mitigations, not substitutes.

## Non-goals

- Re-opening the α/β/γ architecture choice. The deferral stays.
- Specifying the full `.19.9` interspect-task-outcome schema. That belongs in `.19.9`'s own design.
- Implementing D1 (dormant-five reviewer prune). Orthogonal; can ship anytime under interflux epic.
- Building the heuristic baseline measurement now. F2 files the bead; the work runs when scheduled.
- Designing the LoRA training loss. Belongs to `.19.1`/`.19.3` resumption.

## Dependencies

- **`.19.9`**: critical-path P0 for unblocking β; this PRD elevates its role but doesn't change its scope (other than the operational-definition cross-references in F1)
- **bd CLI** for state field management (`bd set-state`, `bd state`, `bd update --notes`)
- **Sprint orchestrator** for the keep-alive cadence (Step 7 / status checks need to surface the `deferral_check_in` field)

## Decisions closed during PRD review

These were Open Questions in the first PRD draft; closed during the post-review patch (Path A: active enforcement):

1. **Auto-revert default on deadline miss** — chosen: **surface forced re-entry, do NOT auto-close**. Plan review revised this from the original `auto-close-epic` choice (which violated CLAUDE.md rule b requiring human confirmation for epic closes). When 2026-06-30 passes, `/clavain:status` (per F4) surfaces "deadline exceeded — re-enter via `/clavain:route sylveste-s3z6.19.10`". The actual close, extension, or re-decision requires explicit human action. Rationale: a deferral that quietly extends is still better than an automated close that violates the project's bead-close discipline.
2. **Sprint-counting protocol** — chosen: **AND-gate on calendar AND volume** (changed from OR). 4 weeks AND ≥80/cell stable-7 AND ≥20/cell long-tail must all be satisfied. If volume isn't reached at 4 weeks, the deferral extends until volume or the deadline (2026-06-30), whichever comes first. Rationale: closes the Schelling-trap gameability of the OR-gate.
3. **`.19.8` body link** — chosen: **link to `.19.10`** (the bead, not the PRD path). More durable. F1 acceptance criterion 4 already specified this; confirmed.

## Open Questions

1. **Backup decision authority** — single-operator project today. If a backup ever exists, what's the delegation mechanism? (Punt; F3 leaves the field present and pointing at primary as a placeholder.)
2. **D2 result archive location** — `docs/research/2026-MM-DD-microrouter-heuristic-baseline-d2.md` is a placeholder. Confirm dir convention.
