### Findings Index
- P1 | RB-01 | "Axis 1: Usability" | Stalled subagents (permission error, Write gate) have no Pelota/Hbs1 rescue mechanism — harness waits for full timeout before redirecting
- P2 | RB-02 | "Axis 2: Token Efficiency" | MEMORY.md and handoff docs accumulate without mRNA-decay half-life — stale entries never expire, budget overflow is manual
- P2 | RB-03 | "Axis 3: Replace LLM Orchestration" | Short-prefix routing not exploited — LLM decides destination even when first 3 tokens deterministically signal the route (signal-peptide analog)
- P2 | RB-04 | "Axis 2: Token Efficiency" | No-go decay analog absent — flux-drive agent findings that are never acted upon accumulate in SYNTHESIS.md without down-weighting the producing agent
- P2 | RB-05 | "Axis 1: Usability" | Stale artifacts (completed beads, finished sprints, superseded roadmaps) carry no ubiquitin-tag equivalent scheduling cleanup
- P3 | RB-06 | "Axis 2: Token Efficiency" | Synthesis waits for all agents to complete — no co-translational folding; downstream work cannot begin before upstream agent findings arrive
Verdict: needs-changes

---

### Summary

The cell's translation machinery and Sylveste's agent orchestration face structurally identical problems: expensive processors (ribosomes / LLMs) working on noisy substrates (mRNAs / user prompts), with rescue paths for stalls (Pelota/Hbs1 / permission error detection), decay rates for stale state (mRNA half-life / MEMORY.md expiry), and routing decisions made cheaply at the start (signal peptide / short-prefix classifier). Currently, Sylveste lacks all three: stalled subagents time out without rescue, stale memory accumulates past its useful lifetime, and routing decisions pay full LLM cost even when a 3-token prefix would suffice. The isomorphisms are specific and actionable — each maps to a concrete implementation pattern.

---

### Issues Found

**RB-01. P1: Stalled subagents have no Pelota/Hbs1 rescue mechanism**

- **Axis**: usability
- **Mechanism**: Pelota (DOM34 in yeast) and Hbs1 are the eukaryotic ribosome rescue factors. When a ribosome stalls at a problem codon (rare codon, mRNA truncation, stable secondary structure), Pelota/Hbs1 recognize the empty A-site, split the ribosome, and target the truncated peptide for degradation. The rescue decision is based on a single signal: is the A-site occupied? If not, rescue.
- **Current state**: When a subagent stalls on a `Write` permission gate (as observed in this session — 4 agents hit permission errors), the parent harness has no detection mechanism. The agent is dispatched with `run_in_background: true`; the harness polls for `.md` output files. If the agent hangs waiting for a permission prompt that never comes (in non-interactive mode), it just times out after 300s. The 300s is the entire rescue window. No intermediate signal is emitted.
- **Concrete failure**: /flux-review dispatches 4 agents that hit `Write` permission errors mid-review. Each waits 300s. Total blocked wall-clock: 4 × 300s = 20 minutes of silent stall. Parent session has no awareness until synthesis finds missing files and generates error stubs.
- **Pelota analog**: The empty A-site signal = an agent that has not produced any output (no writes to partial file) after N seconds into a phase where it should have written something. Detection:
  ```bash
  # In flux-watch.sh: add stall detection
  if [ $elapsed_since_last_write -gt 60 ] && [ ! -f "${OUTPUT_DIR}/${agent}.md.partial" ]; then
    # A-site is empty — trigger rescue
    log "STALL DETECTED: $agent — no output in 60s"
    kill_agent "$agent"
    write_error_stub "$agent" "stall-rescue: no output after 60s"
    emit_peer_finding "blocking" "$agent" "stall-timeout" "Agent stalled with no output; rescued after 60s"
  fi
  ```
- **Hbs1 analog**: The harness component that fires the rescue — reads agent transcript JSONL, looks for permission error messages, and emits a structured event for the user.
- **Estimated savings**: Reduces stall wait from 300s to 60s per stalled agent. For 4 stalled agents: 4 × 240s = 16 minutes recovered. UX: user gets partial results in 2 minutes instead of 10 minutes.
- **Difficulty**: S (modify flux-watch.sh to add stall detection + error stub path)
- **Risk**: False-positive stall detection for genuinely slow agents (large file reads). Use adaptive threshold: start at 60s, extend by 30s if `ps aux` shows agent process still running.

---

**RB-02. P2: MEMORY.md and handoff docs accumulate without mRNA-decay half-life**

- **Axis**: token-efficiency
- **Mechanism**: mRNA half-life. In eukaryotic cells, mRNA stability is controlled by 5' cap status, poly-A tail length, and AU-rich elements in the 3' UTR. Unstable mRNAs (half-life ~30 min) are rapidly degraded; stable mRNAs (half-life hours) persist. The cell encodes stability directly in the transcript. Sylveste has no equivalent: all memory entries are equally "stable."
- **Current state**: MEMORY.md is 132 lines against a 120-line budget. The overflow is noted in both the target document and feedback memory. `/intermem:tidy` is a manual operation. Handoff docs accumulate in `docs/handoffs/` with no expiration. The MEMORY.md system has no mechanism to mark entries with a half-life or last-accessed timestamp.
- **mRNA decay rate estimate**:
  - Active project state (current sprint, active beads): half-life = indefinite (stable mRNA analog)
  - Lesson-learned entries: half-life = 90 days (accessed rarely after 90 days)
  - Infrastructure notes: half-life = 180 days (stable but eventually superseded)
  - Handoff docs: half-life = 30 days (highly perishable)
  - Feedback memories: half-life = indefinite (behavior modification = constitutively expressed)
- **Proposal**: Add `expires_after: 90d` frontmatter to MEMORY.md topic files. SessionStart hook reads `expires_after` + `last_accessed` → if `now - last_accessed > expires_after`, mark entry as `[STALE]` and emit a one-line warning instead of including full content. Add `last_accessed: ISO8601` to each file, updated on read. The `/intermem:tidy` skill reads stale entries and prompts for archive vs. delete.
- **Estimated savings**: MEMORY.md would stabilize near budget (120 lines) instead of growing unchecked. At ~12 lines per stale entry removed: 1-2 entries/month = ~12-24 lines recovered. Token savings: ~100-200 tok/session from shorter MEMORY.md (reduced auto-load cost).
- **Difficulty**: S (add frontmatter schema to memory files + SessionStart hook staleness check)
- **Risk**: Incorrect expiry on a still-relevant entry causes loss of important context. Mitigate: archive to `docs/archive/` rather than delete; `/intermem:tidy` shows the entry before archiving.

---

**RB-03. P2: Short-prefix routing not exploited — signal-peptide pattern absent**

- **Axis**: ml-routing-replacement
- **Mechanism**: Signal Recognition Particle (SRP) and signal peptide. The first 20-25 amino acids of a nascent protein encode a hydrophobic signal sequence. The SRP recognizes this sequence co-translationally (while the ribosome is still working) and routes the protein to the ER membrane — before the full protein is synthesized. The routing decision is made from a short prefix, not the full sequence.
- **Current state**: Sylveste's skill routing processes the full user input with LLM reasoning to decide which skill to invoke. For inputs like `/recall anything about beads`, `/bd list`, `fix typo in CLAUDE.md`, the first 2-3 tokens deterministically signal the route:
  - `/recall` → `clavain:recall` (100% deterministic from first token)
  - `bd ` (with trailing space) → beads workflow (99% from first 3 chars)
  - `fix typo` → edit workflow (95% from first 2 words)
  - `/sprint` → `clavain:sprint` (100% from first token)
  - `/flux-` → interflux skill family (99% from first 7 chars)
- **Estimated short-prefix coverage**: Based on the slash command surface (100+ skills), approximately 60-70% of user inputs begin with a `/command` or a beads-family prefix that is deterministically routable from the first token.
- **Proposal**: Add an SRP-equivalent pre-router in Clavain that runs before any LLM is invoked:
  ```python
  SIGNAL_PEPTIDE_TABLE = {
    r'^/recall': 'clavain:recall',
    r'^bd ': 'beads-workflow',
    r'^/sprint': 'clavain:sprint',
    r'^/flux-': 'interflux:*',  # family route, still need sub-routing
    r'^/work': 'clavain:work',
    r'^fix typo': 'edit-workflow',
    # ... 20-30 high-frequency prefixes
  }
  def srp_route(input_text):
    for pattern, destination in SIGNAL_PEPTIDE_TABLE.items():
      if re.match(pattern, input_text, re.I):
        return destination  # Route decided from prefix; skip LLM
    return None  # No signal peptide detected; invoke LLM
  ```
- **Estimated savings**: For 60% of inputs, skip LLM routing entirely. At ~300-500 tok/routing call × 60% = 180-300 tok/turn saved. This is the same finding as KF-01 (Kalman framing) — the signal-peptide lens gives a different implementation path (prefix table instead of sensor fusion).
- **Difficulty**: S (build prefix table + pre-router; fallback to LLM for unmatched inputs)
- **Risk**: Signal peptide table becomes a maintenance burden as skill surface grows. Mitigate: auto-generate from skill manifest command prefixes.

---

**RB-04. P2: No-go decay analog absent — unacted findings accumulate without agent down-weighting**

- **Axis**: token-efficiency
- **Mechanism**: No-go decay (NGD). When a ribosome stalls on a defective mRNA (rare codon, truncated ORF), the no-go decay pathway degrades the mRNA and down-weights its translation. The cell effectively learns: "this transcript is unproductive — reduce resource allocation." In Sylveste, there is no equivalent for agents that produce findings that are never acted upon.
- **Current state**: The agent tier registry (`.claude/agents/.index.yaml`) tracks `use_count` and `last_used` for tier promotion (generated → used → proven). There is no tracking of "findings produced" vs. "findings acted upon." An agent that consistently produces P3 improvements that are never implemented is treated identically to one whose P1 findings drive fixes. The flux-agent.py script increments `use_count` on invocation — not on finding-action rate.
- **Finding-action rate estimate**: CASS session analytics could surface: for each agent, how many findings appear in SYNTHESIS.md vs. how many appear in subsequent commit messages or bead closures? This ratio is the no-go decay signal.
- **Proposal**: Add a `finding_action_rate: float` field to `.index.yaml`. After each synthesis, the flux-agent.py `record` command estimates acted-upon findings by checking git log and bead closures for references to finding IDs (e.g., KF-01, MPC-01). If `finding_action_rate < 0.1` over 5+ uses, downgrade agent tier and reduce its triage score for future reviews.
- **Estimated savings**: Reduces future dispatch of low-signal agents → fewer tokens spent on unproductive reviews. Estimated 1-2 low-signal agents per 10 in the roster → 10-20% triage budget savings over time.
- **Difficulty**: M (requires finding-action tracking in flux-agent.py + git/bead cross-reference)
- **Risk**: Finding-action rate is noisy — some good findings are deferred intentionally. Use a 0.1 floor with a 5-use minimum before any tier downgrade.

---

**RB-05. P2: Stale artifacts carry no ubiquitin-tag equivalent — cleanup is ad hoc**

- **Axis**: usability
- **Mechanism**: Ubiquitin tagging. The ubiquitin-proteasome system marks proteins for degradation by attaching ubiquitin chains (poly-Ub). The tag schedules degradation: the protein continues to function until the proteasome processes it. The key property: tagging and degradation are decoupled — you can mark something for future cleanup without stopping it now.
- **Current state**: Completed beads remain in the `open` pool until manually closed. Finished sprints leave skill invocation logs in place. Superseded roadmaps (docs/roadmap-v1.md) are referenced in AGENTS.md but may be stale. Handoff docs accumulate (16 handoff files listed in untracked status). No artifact carries a "scheduled for cleanup" tag that the next session can act on.
- **Ubiquitin-tag analog**: Add a `scheduled_for_cleanup: reason` field to:
  - Bead frontmatter (when a bead is resolved but not yet formally closed by the LLM)
  - Handoff docs (add `expires_after: 14d` frontmatter — handoff is superseded when next session starts)
  - Roadmap docs (add `superseded_by: [doc]` when a new version is written)
- **Proposal**: SessionStart hook reads all artifacts with `scheduled_for_cleanup` or past `expires_after` → emits a compact summary: "3 artifacts pending cleanup: [list]." This decouples marking (cheap, done inline) from cleanup (deferred to a focused tidy session).
- **Estimated savings**: Reduces cognitive overhead of finding stale docs; prevents MEMORY.md from referencing superseded artifacts. UX friction reduction: ~5 minutes/session currently spent on manual staleness checks.
- **Difficulty**: XS (add frontmatter schema + SessionStart hook scan — purely additive)
- **Risk**: Tag inflation — everything gets tagged, nothing gets cleaned. Enforce: only tag when a concrete expiry or supersession event has occurred.

---

**RB-06. P3: Synthesis waits for all agents — no co-translational folding**

- **Axis**: token-efficiency
- **Mechanism**: Co-translational folding. Proteins begin folding while the ribosome is still translating downstream domains. The N-terminal domain folds before the C-terminal domain is even synthesized. This dramatically reduces total processing time. Sylveste's synthesis is post-translational: it waits for all agents to complete before any synthesis work begins.
- **Current state**: `phases/synthesize.md` reads all `{OUTPUT_DIR}/*.md` files after `flux-watch.sh` confirms all N agents complete. No progressive synthesis path exists. The `interflux:fetch-findings` skill is listed as available but is used for manual fetching, not streaming synthesis.
- **Proposal**: Add a streaming synthesis mode: as each agent writes its `.md.partial` → `.md` completion signal, the synthesis subagent can begin building the SYNTHESIS.md Findings Index section. When all agents complete (or timeout hits), finalize the prose synthesis. This is co-translational: the index (N-terminal domain) folds while downstream agents (C-terminal domains) are still running.
- **Estimated savings**: For 16-agent reviews, reduces total review time by the time to synthesize the first 50% of findings. Estimated: 2-3 minutes saved per large review.
- **Difficulty**: M (requires streaming synthesis subagent that reads completions incrementally)
- **Risk**: Early synthesis findings may be revised by later peer findings (peer-findings.jsonl protocol). Must re-read JSONL before finalizing.

---

### Improvements

1. **RB-I1**: Add `signal_peptide: [prefix_patterns]` to each skill manifest — this auto-generates the SRP routing table (RB-03) from the source of truth rather than maintaining a separate regex file.
2. **RB-I2**: Instrument CASS session indexer to track finding IDs mentioned in commit messages and bead notes — this builds the data pipeline needed for no-go decay (RB-04) without requiring a new database.
3. **RB-I3**: The `/intermem:memory-tidy` skill should read `expires_after` frontmatter and surface a ranked list of stale entries by expiry urgency — turning the mRNA-decay model (RB-02) into a concrete tidy workflow.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 6 (P0: 0, P1: 1, P2: 4, P3: 1)
SUMMARY: Sylveste's agent orchestration lacks all three translation-regulation mechanisms: stalled subagents have no Pelota/Hbs1 rescue path (300s silent timeout vs. 60s detection), stale memory accumulates without mRNA-decay half-life (MEMORY.md 132/120 lines), and routing pays full LLM cost even when first-token signal peptides would route 60-70% of inputs deterministically. The signal-peptide pre-router (S difficulty, ~180-300 tok/turn) and stall-rescue detection (S difficulty, 16+ minutes recovered per stalled review) are the two highest-ROI fixes.
---

<!-- flux-drive:complete -->
