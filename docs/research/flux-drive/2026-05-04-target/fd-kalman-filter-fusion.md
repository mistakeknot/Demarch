### Findings Index
- P1 | KF-01 | "Axis 3: Replace LLM Orchestration" | Skill routing pays full LLM cost on every invocation — no multi-sensor fusion gate
- P2 | KF-02 | "Axis 3: Replace LLM Orchestration" | Bead deduplication lacks innovation-gated LLM escalation — cosine similarity alone would route 85%+ of cases
- P2 | KF-03 | "Axis 3: Replace LLM Orchestration" | Agent triage (flux-engine) has no steady-state convergence — all inputs treated as high-innovation
- P2 | KF-04 | "Axis 2: Token Efficiency" | Voice fidelity scoring (interfluence) uses LLM compare; no cheap-sensor pre-filter using embedding cosine + n-gram overlap
- P3 | KF-05 | "Axis 3: Replace LLM Orchestration" | No process-noise retraining cadence for cheap classifiers — static signals drift silently as codebase evolves
Verdict: needs-changes

---

### Summary

Sylveste currently dispatches LLM calls for all routing decisions without any multi-sensor fusion gate. The Kalman filter isomorphism maps directly: each routing decision has 3-4 cheap sensors (regex, embedding cosine, frequency, recency) with measurable false-positive rates; the Kalman gain determines when the LLM (expensive "GPS sensor") must be invoked vs. when cheap-sensor agreement suffices. Innovation gating — invoking LLM only when the innovation sequence (sensor disagreement) exceeds a threshold — is entirely absent. The intercept project already demonstrates this pattern for decision gates; the same architecture extends to skill routing, bead dedup, agent triage, and voice fidelity. Current state pays full LLM cost for the ~90% steady-state case where cheap sensors converge.

---

### Issues Found

**KF-01. P1: Skill routing pays full LLM cost on every invocation — no multi-sensor fusion gate**

- **Axis**: ml-routing-replacement
- **Mechanism**: Kalman gain K = P_pred·H^T · (H·P_pred·H^T + R)^-1. When sensor variance R is low (sensors agree), K → 0 and the prior dominates — no LLM needed. When R is high (sensors disagree), K → 1 and the LLM update is trusted.
- **Current state**: Skill routing in Clavain (invoked per user turn) uses LLM reasoning to select among 100+ skills. The `clavain:route` skill dispatches a full Sonnet call to select the appropriate skill handler. No pre-filtering step exists. At $2.93/landable-change with ~785 sessions, skill routing is estimated to consume 300-500 tok/turn on classification alone.
- **Cheap sensors for skill routing** (per-sensor false-positive rate estimates):
  1. Regex prefix match on `/command` invocation token — FP rate ~2% (commands that match but mean something else in context)
  2. Embedding cosine similarity to skill description embeddings — FP rate ~8% (adjacent skills)
  3. Recent session frequency (which skills were used in last 10 turns) — FP rate ~15% (recency bias)
  4. Token-count signal (short inputs → usability skills, long structured inputs → planning skills) — FP rate ~20%
- **Kalman fusion**: Weight sensors by inverse variance. When regex+embedding agree (combined FP ~0.5%), innovation sequence is low → skip LLM. When they disagree → innovation exceeds threshold → invoke LLM.
- **Estimated steady-state hit rate**: ~88% of turns, cheap-sensor agreement > 0.85 threshold
- **Proposal**: Add `interflux:route:pre-filter` as a deterministic first pass — regex match on `/cmd` prefix, embedding cosine vs. 100-skill embedding index, frequency prior. Fuse with confidence weights. Only escalate to LLM when fused confidence < 0.85 (i.e., innovation sequence exceeds threshold). XGBoost or logistic regression on the fused signal.
- **Estimated savings**: ~300-400 tok/turn for the 88% case = ~264-352 tok/turn net reduction across all turns. At 2,285 tok/session baseline, this could represent a 10-15% additional reduction.
- **Difficulty**: M (multi-PR: embedding index build, fusion layer, fallback gate)
- **Risk**: Edge cases where short-prefix match is ambiguous (e.g., `/work` vs. `/work-plan`) will fall through to LLM — acceptable if fallback is clean. Sensor drift if skill list changes without re-indexing.

---

**KF-02. P2: Bead deduplication lacks innovation-gated LLM escalation**

- **Axis**: ml-routing-replacement
- **Mechanism**: Steady-state Kalman filter (converged, minimal process noise). In a stable project, bead title embeddings form a well-characterized prior. New bead creation is a measurement update — cosine similarity to existing beads is a low-variance sensor.
- **Current state**: `bd search` before `bd create` is LLM-delegated — the agent reads `bd list` output and decides whether a new bead duplicates an existing one. This is a Sonnet-level call per `bd create` invocation. The bead list grows to ~100+ items; reading it costs ~500 tok each time.
- **Cheap sensors**:
  1. Title-cosine similarity (sentence-transformers on bead title) — FP rate ~5% at threshold 0.85
  2. Label-set overlap (both beads have same pillar + type labels) — FP rate ~12%
  3. Status filter (only compare against `open` beads) — reduces search space 60%
  4. Recency weight (beads created in last 30 days more likely to be duplicates) — FP rate ~18% standalone
- **Kalman-gain analog**: K is high only when cosine > 0.85 AND labels overlap AND status=open. All three sensors agreeing = steady-state convergence → reject as duplicate without LLM. Any sensor disagreeing = high innovation → optionally query LLM.
- **Proposal**: Pre-filter `bd create` with embedding lookup against open beads. If top match cosine > 0.85 with label overlap, surface the candidate to the user as "possible duplicate: [bead-id]" and let user confirm — no LLM needed. Only invoke LLM when 0.70 < cosine < 0.85 (uncertain zone = high innovation).
- **Estimated savings**: ~500 tok per `bd create` call saved in 85% of cases. With ~10 bead creates/session estimate: ~4,250 tok/session.
- **Difficulty**: S (single PR: add embedding index to bd, cosine pre-check in bd create flow)
- **Risk**: Embedding index must be kept in sync with bead mutations (close/archive). Index rebuild latency on large Dolt histories.

---

**KF-03. P2: Agent triage (flux-engine) treats all inputs as high-innovation — no convergence**

- **Axis**: ml-routing-replacement
- **Mechanism**: Observability matrix H. Some routing decisions are observable from cheap signals (what agents to dispatch for a `.py` file review vs. a `.md` brainstorm). The Kalman observability matrix H defines which state components are measurable from cheap outputs.
- **Current state**: `flux-engine` (interflux) triages which review agents to dispatch by running a Phase 1 analysis using Sonnet reasoning — reading CLAUDE.md, AGENTS.md, scoring agents 0-8. This is ~1,000-2,000 tok of Sonnet reasoning per review invocation, regardless of whether the input is a well-characterized file type.
- **Observable states** (cheap sensors can determine):
  1. File extension → primary domain agent (`.py` → fd-quality, `.sh` → fd-safety, `.md` → fd-systems/fd-decisions) — FP rate ~5%
  2. File size → small/medium/large → slot ceiling — FP rate ~3%
  3. Presence of security keywords (credential, token, secret) → fd-safety always included — FP rate ~1%
  4. Diff line count → slicing decision — FP rate ~0%
- **Unobservable from cheap signals** (must remain LLM-only): Domain detection (is this a game-simulation or ml-pipeline?), nuanced coupling analysis, new agent selection for novel input types.
- **Proposal**: Add a `triage-shortcut.sh` that handles the observable states (extension, size, security keywords) before dispatching Sonnet triage. For well-typed inputs (`.py`, `.sh`, `.md`, `.diff`), emit a pre-computed agent set covering 80% of correct selections. Only invoke Sonnet triage for novel file types or multi-domain inputs.
- **Estimated savings**: ~1,200 tok per flux-drive invocation saved for standard file types. With typical usage, this could be 10-15% of flux-drive operating cost.
- **Difficulty**: S (single PR in flux-engine Phase 1: add shortcut pre-filter before scoring loop)
- **Risk**: Pre-computed sets may miss domain-specific agents. Must define "standard file type" conservatively; err toward LLM for ambiguous cases.

---

**KF-04. P2: Voice fidelity scoring (interfluence) uses full LLM comparison — no cheap pre-filter**

- **Axis**: token-efficiency
- **Mechanism**: Innovation gating. The Kalman innovation z̃ = z - H·x̂ measures surprise. If embedding cosine between reference and generated text is already > 0.90, innovation is low — LLM comparison adds marginal signal.
- **Current state**: `interfluence` voice fidelity scoring dispatches an LLM compare (Sonnet) to evaluate generated text against the user's voice profile. This runs per session-close or on-demand. Cost: ~800-1,200 tok per comparison.
- **Cheap sensors**:
  1. Embedding cosine (sentence-transformers on reference corpus vs. generated text) — low FP for high-similarity case
  2. N-gram overlap on distinctive triad patterns — precise for specific voice quirks
  3. Em-dash frequency delta — measurable structural signal
  4. Sentence-length distribution KL-divergence — ~15% FP rate standalone
- **Proposal**: Pre-filter with embedding cosine + n-gram overlap. If cosine > 0.88 and n-gram overlap > 0.75 for distinctive patterns → rate as "high fidelity" without LLM. Only invoke LLM when cosine < 0.75 (genuine divergence) or 0.75-0.88 (uncertain zone = high innovation).
- **Estimated savings**: ~900 tok per comparison saved in ~70% of cases where voice is consistent. Per session: ~630 tok.
- **Difficulty**: S (single PR: add pre-filter to interfluence compare path)
- **Risk**: Voice profile embedding must match the reference style corpus. Profile drift over time (process noise) requires periodic re-embedding.

---

**KF-05. P3: No retraining cadence for cheap classifiers — sensor drift is silent**

- **Axis**: token-efficiency (operational overhead)
- **Mechanism**: Process noise Q in Kalman filter models uncertainty in state evolution. As codebase evolves (new plugins, renamed skills, bead label taxonomy changes), cheap-sensor embeddings drift. Without a retraining cadence, FP rates rise silently until LLM escalation frequency spikes.
- **Current state**: No mechanism exists to detect when cheap sensors are stale. The intercept project (xgboost distillation) also has no documented retraining trigger.
- **Proposal**: Add a process-noise monitor: track LLM escalation rate per routing decision. If escalation rate for a decision type rises above 25% (was 10%), trigger retraining signal via `interject` notification. Retraining = re-embed skill descriptions, rebuild bead cosine index, re-calibrate thresholds.
- **Estimated savings**: Prevents gradual quality degradation that would require manual diagnosis. Estimated maintenance: 2-4 hours/quarter if automated.
- **Difficulty**: M (requires escalation telemetry + retraining hook)
- **Risk**: False-positive retraining triggers if codebase undergoes intentional large-scale refactor.

---

### Improvements

1. **KF-I1**: Implement a shared `lib-fusion.sh` that other routing decisions (skill routing, bead dedup, triage) can call — fuses N cheap sensors with inverse-variance weights and returns (confidence, innovation_score) to standardize the Kalman-gain pattern across the codebase.
2. **KF-I2**: Instrument existing routing call sites to log (input, sensor_votes, was_llm_called) to a lightweight SQLite table — this builds the training dataset for future xgboost distillation (following the intercept pattern).
3. **KF-I3**: Define a `routing-observability.yaml` that lists which routing decisions are fully observable from cheap signals (file-extension → agents) vs. partially observable (domain detection) vs. unobservable (novel input types) — prevents futile attempts to replace LLM on unobservable decisions.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 1, P2: 3, P3: 1)
SUMMARY: Skill routing and agent triage pay full LLM cost on every invocation despite 3-4 cheap sensors that, fused via Kalman-gain analog, would route 85-90% of cases deterministically. Innovation-gating — the core Kalman mechanism — is entirely absent from all routing decisions in Sylveste. Highest-ROI fix is a pre-filter for skill routing (M difficulty, ~300-400 tok/turn savings) and bead dedup (S difficulty, ~4,250 tok/session savings).
---

<!-- flux-drive:complete -->
