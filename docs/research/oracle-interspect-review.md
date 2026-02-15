# Oracle Strategic Review: Interspect Design

**Model:** GPT-5.2 Pro (via Oracle browser mode)
**Date:** 2026-02-15
**Input:** Interspect design doc (v2) + 7 flux-drive review reports (~52K tokens)

---

## 1) STRATEGIC ASSESSMENT

Building some Interspect is the right next step; building the full self-modifying engine is not.

**What's "right" now:** ship Interspect as an observability + recommendation layer first, and treat autonomous modification as a later (optional) capability. Your v2 design already points this direction (propose-mode default, v1 scope limited to Types 1-3, SQLite, reporting UX). That's the correct pivot because it de-risks the entire bet while still delivering compounding value.

**Why "full autonomy" is still the wrong immediate bet (even in a single-user install):**

- **The dominant failure mode isn't "one bad diff,"** it's slow drift driven by weak proxies (override/FP rates) and incomplete coverage of misses. The measurement review is blunt: override rate != wrongness, dismissals != false positives, and without a recall counterweight you Goodhart yourself into "quiet agents."
- **The dominant security risk isn't the obvious one.** It's prompt injection + excessive agency interacting with "write access" and git mechanics. The safety/self-mod reviews' core point is: if meta-rules aren't mechanically enforced, the rest is theater. Your v2 adds a protected-paths manifest and removes the 0.9 bypass, which is directionally correct -- but you're still building a system whose first serious incident will collapse trust.
- **Operationally, anything that touches hooks + evidence + canaries is a correctness minefield.** The original JSONL concurrency issues are solved by SQLite in v2, but the meta-problem remains: Interspect sits in the critical path and must be boringly reliable. That's not where you want to take big experimental swings.

**Opportunity cost (what you're not doing if you build "full Interspect" now):**

1. **Evals as CI / regression harness** for prompts and agent workflows. This is the real flywheel: you can't safely self-improve (or even manually improve) without repeatable evals.
2. **Upstream agent quality + topology** (flux-drive prompts, triage logic, better defaults). You'll get more ROI per engineering hour by improving baseline agents than by building an autonomy framework that (initially) mostly learns "be quieter."
3. **UX for debugging:** if the user can't answer "what changed and why" in 10 seconds, you've built a trust bomb. You've added the commands in v2; shipping them before autonomy is the correct ordering.

**Recommendation:** Ship Interspect as an observability-first product, and treat autonomy as a gated experiment that earns its way in via data.

---

## 2) SIMPLIFICATION OPPORTUNITIES

Even v2 is still heavier than it needs to be for v1 value. The core value proposition is:

> "Turn my day-to-day friction (overrides/dismissals/corrections/outcomes) into actionable suggestions and safe, reversible adaptations."

You can keep that while cutting more.

### Cut from v1 without losing the core value

**A. Drop Tier 1 (session-scoped self-mods) entirely**
- It's complexity (statefulness, intra-session verification, "why did behavior change mid-session?") for marginal gain.
- You can still log Tier-1-worthy patterns and surface them in the report, but don't auto-adjust prompts in-memory.
- Rationale: the feedback-loops review flagged "incomplete observe-after-act" and double-counting risks. v2 addresses them, but the cheapest fix is: don't do it yet.

**B. Collapse "confidence function" into simple counting rules**
- Your weighted_sum is still arbitrary until calibrated; you already call this out as an open question. A simpler and safer v1 rule is:
  - Persistent suggestion requires:
    - >=3 sessions, and
    - >=2 projects (or >=2 languages), and
    - >=N events of the same typed pattern (e.g., override(agent_wrong) for prompt tuning).
- That's easier to reason about, and easier to debug when users ask "why did this fire?"

**C. Cut canary auto-revert**
- For v1, make canary monitoring "detect and alert" instead of "detect and revert." Auto-revert adds:
  - dependency/revert-chain complexity (even if you have group IDs),
  - edge cases around human edits, and
  - a new class of "why did my rig change back?" confusion.
- Instead: store metrics, alert on degradation via `/interspect:status`, and provide a one-command revert. You get 80% of the safety with 20% of the complexity.

**D. Defer prompt tuning (Type 3) until you have an eval corpus**
- Your shadow testing design is much better than v1 (eval-corpus first, bias mitigations), but it's still a lot of machinery that can give false confidence if the corpus/judge aren't real. Cut Type 3 from v1 and ship only:
  - Type 1: sidecar/context overlays
  - Type 2: routing overrides
- Those two already deliver personalization and noise reduction.

**E. Don't run on session-start as a blocking hook**
- This avoids sentinel/ordering interactions with auto-compound and drift-check entirely and removes a whole class of "sometimes it doesn't run" bugs noted in the feedback-loops review.

### What to keep (non-negotiable)
- SQLite evidence store with WAL mode + 90-day retention (you already moved there for correctness reasons).
- Evidence sanitization + provenance (non-auditable evidence is worse than no evidence).
- Reporting UX: `/interspect`, `/interspect:status`, `/interspect:evidence`, `/interspect:health`.
- Protected paths manifest as mechanical enforcement.

---

## 3) NOVEL IMPROVEMENT IDEAS (patterns the design isn't fully using)

### A) Alternative evidence collection strategies

**1) "Outcome-first" evidence, not "interaction-first" evidence**
- You're still heavily centered on overrides/dismissals. In production coding assistants, the most robust signals are downstream outcomes:
  - test failures introduced vs avoided,
  - CI red/green deltas,
  - defect escapes (you reference Galiana for this -- lean into it harder),
  - time-to-resolution for certain classes of findings.
- Concrete pattern: require at least one outcome delta (even a coarse one) before promoting beyond "suggestion." This aligns with eval-driven development norms (BDD-like loop: specify, run, iterate).

**2) Shadow-traffic without code changes ("counterfactual evaluation")**
- Before changing anything, run the candidate prompt/routing in a shadow execution path on real invocations and log "would-have-changed" deltas.
  - No autonomy risk.
  - Builds a dataset of paired comparisons: baseline vs candidate.
  - Lets you promote changes based on observed improvements, not just heuristic confidence.
- This is a common production pattern in recommender systems and is increasingly used in agentic tooling as "silent variant" evaluation.

**3) Evidence provenance signing (lightweight)**
- Your v2 adds hook_id, but you can go one step further without overkill: HMAC-sign each evidence row with a key stored outside the repo (root-owned). That makes "forge evidence to trigger a change" materially harder, even on a local box. This directly addresses the safety review's evidence poisoning concerns.

### B) Different safety architectures

**1) Privilege separation as the real boundary**
- Protected-paths + manifests + git hooks are better than nothing, but they're not a hard boundary if the agent can:
  - invoke `git commit --no-verify`,
  - write into `.git/`,
  - alter hook execution contexts.
- Real-world agent tooling is already getting burned by "agent writes to git config/hooks -> code execution." Cursor shipped a high-severity advisory specifically about a malicious agent writing .git settings/hooks leading to out-of-sandbox RCE. Your system is structurally adjacent to that risk.
- So: split Interspect into two processes:
  - an **unprivileged proposer** that can only write to a staging directory, and
  - a **privileged applier** that only applies a tiny allowlisted patch format (not arbitrary diffs) after verification.
- This also aligns with OWASP's warnings around prompt injection and excessive agency in LLM apps.

**2) Two-model / two-pass "change control"**
- Production assistants increasingly use:
  - Model A proposes change
  - Model B (or same model with a strict critic prompt) performs adversarial review: "how could this be unsafe / degrade recall / bias metrics?"
- Given how high prompt-injection success can remain against adaptive attackers in agent ecosystems, defense-in-depth matters more than heuristic sanitization.

### C) Simpler (and safer) feedback loops

**1) Feature-flag prompt overlays instead of editing canonical prompts**
- Instead of rewriting `agents/review/fd-safety.md`, maintain:
  - `agents/review/fd-safety.md` (upstream-ish, mostly stable)
  - `.clavain/interspect/overlays/fd-safety/<overlay-id>.md` (small deltas)
  - runtime concatenation: base + active overlays
- Benefits:
  - instant rollback = disable overlay
  - supports A/B testing (toggle overlays)
  - upstream updates become mergeable; you avoid long-lived forks of agent prompts
- This addresses the architecture review's "god module / coupling" concern by making Interspect changes more modular.

**2) Bandit learning for routing, not confidence thresholds**
- Routing is naturally a contextual bandit problem:
  - choose which agent(s) to run for project X,
  - observe reward signals (actionability, overrides-by-reason, defect escape proxy),
  - update policy.
- This often beats fixed thresholds and "confidence" formulas because it handles non-stationarity and project-specificity gracefully.

### D) Lessons from production AI coding assistants

**1) Treat prompt injection as a first-class design input**
- Anthropic's own write-up on browser-use prompt injection makes the key point: once an agent processes untrusted content, the attack surface explodes and "not solved" is the baseline assumption. Your evidence store is untrusted content in practice.
- Implication: prefer architectures where untrusted text cannot directly influence "generate diffs," only "raise flags that a human/eval harness interprets."

**2) Evals are the product, not the tooling**
- The OpenAI evals guidance (and broader industry trend) is: reliability comes from continuously running evals and iterating, not from clever online scoring alone. If Interspect becomes a self-mod engine without a real eval harness, it will drift.

---

## 4) RISK PRIORITIZATION: the 3 remaining gaps that matter most

### Risk #1 -- "Mechanical enforcement" is still too soft

Even in v2, your protected-path approach is mostly process (hooks/manifests). The reviews' core safety critique remains: if the system can ever touch the enforcement mechanism (directly or indirectly), you don't have a safety gate -- you have a suggestion.

**Why it matters most:** this is the single point of total compromise. If it fails, everything else is irrelevant.

### Risk #2 -- Metric validity + calibration is still the determining factor for success/failure

You improved the design (override-reason taxonomy, finding density, defect escape cross-check), but the measurement review's fundamental warning stands: proxy metrics can reward "quiet agents" rather than "correct agents." And the confidence function/judge are explicitly uncalibrated open questions.

**Why it matters:** bad measurement doesn't cause obvious failures; it causes quiet drift that users notice only after weeks.

### Risk #3 -- Interspect as a "critical path" subsystem (operational reliability)

The correctness review was essentially a catalog of "this will corrupt itself under normal use" in v1. v2 fixes the big one (SQLite), but you're still building a system that requires:
- concurrent-safe hook execution,
- long-lived state,
- monitoring and revert semantics.

Any bug here can break the user's main workflow, not just the "interspect feature."

**Why it matters:** operational fragility is what will cause early disablement, even if the idea is good.

---

## 5) IMPLEMENTATION ADVICE: what I'd do differently + fastest path to value

### The fastest path to value (and trust)

**Step 1: Ship "Interspect Reports" as the product**
- Evidence capture (only high-signal, low-effort signals)
- SQLite store
- `/interspect`, `/interspect:status`, `/interspect:evidence`, `/interspect:health`
- Zero modifications applied automatically

This directly addresses the product review's "visibility and debugging are blocking."

**Step 2: Add "overlay system" (not prompt rewriting)**
- Context overlays (Type 1) and routing toggles (Type 2) implemented as enable/disable artifacts.
- No direct edits to canonical agent prompts.
- Rollback = disable overlay, not git revert.

This is safer, easier to audit, and reduces coupling with upstream prompt evolution.

**Step 3: Only then, add autonomy as "shadow-traffic first"**
- Before a change auto-applies, it must win in shadow evaluation on real traffic (counterfactual logging). This reduces reliance on uncalibrated confidence thresholds and small shadow test sets.

### What I'd do differently than the current design

1. **Hard privilege boundary (even if minimal):** proposer cannot write to the repo at all; only writes patch specs to a staging folder. A deterministic applier enforces allowlists. This is the cleanest answer to the safety reviewers' "unenforceable meta-rules" critique.

2. **Default to branch-based changes rather than committing to main.** Even in propose mode, have Interspect create a branch and present the diff. This makes "review after the fact" unnecessary; it's review-before-merge. It also prevents repo history pollution if users reject changes. (Git-based undo is good; git-based change review is better.)

3. **Treat the eval corpus as a hard prerequisite for prompt tuning.** No eval corpus -> no prompt tuning. Don't "synthetic your way" into believing you have coverage; synthetic tests are useful, but they're not a substitute for a living eval suite tied to real failure modes.

4. **Make "rare agents" propose-only permanently until proven.** Your canary expiration behavior doesn't work for rarely-invoked components. For rare components, the correct default is: do not auto-apply because you cannot validate.

---

## Bottom Line

- **Yes** to Interspect as an evidence + reporting + overlay system. It's the observability + compounding engine you'll need anyway.
- **No** (for now) to "self-modifying by default" as the main value proposition. The real moat is evals + observability + safe change control, not autonomy.
- If you want the fastest path to value: **ship the audit/debug UX first**, then overlays as safe experiments, then autonomy.
