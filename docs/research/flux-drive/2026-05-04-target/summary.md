## Flux Drive Review — 2026-05-04-target (Track B: Orthogonal)

**Reviewed**: 2026-05-04 | **Agents**: 4 launched, 4 completed | **Verdict**: needs-changes

Track B agents apply operational patterns from parallel professional disciplines — search engine ranking, hermetic build caching, incremental compilation, and IDE quick-action UX. All 4 agents converged on `needs-changes`.

---

### Verdict Summary

| Agent | Status | Summary |
|-------|--------|---------|
| fd-search-engine-ranking | NEEDS_ATTENTION | Agent triage and skill routing both skip cheap candidate-gen; full LLM judgment on every call; CASS CTR signal unused |
| fd-build-system-caching | NEEDS_ATTENTION | Zero cross-run cache utilization due to timestamp hermeticity violations; no content-addressed findings cache |
| fd-compiler-incremental-build | NEEDS_ATTENTION | Per-turn full re-orientation on idle loops; manifest pattern exists in gen-skill-compact.sh but not generalized; O(n) status rebuilds |
| fd-ide-quick-actions | NEEDS_ATTENTION | 58 plugins share "inter" prefix; 6 review collisions; 232-option flat listing with no ranking or progressive disclosure |

---

### Critical Findings (P0)

None.

---

### Important Findings (P1)

**SER-01** (fd-search-engine-ranking — ml-routing-replacement):
Agent triage evaluates ALL 679+ Project Agents via LLM without cheap candidate-gen. In Google's two-tower architecture, expensive cross-encoder reranking only applies to top-k from BM25/embedding retrieval. Sylveste skips retrieval entirely.
- Current: ~40K tok/review for triage scoring; Proposal: intersearch top-30 retrieval + LLM rerank
- Savings: 35K tok/review (85%); Difficulty: M

**BSC-1** (fd-build-system-caching — token-efficiency):
Timestamped OUTPUT_DIR (SKILL.md line 112: `RUN_TS = $(date +%Y%m%dT%H%M)`) embedded in every agent prompt defeats all cross-run prompt cache hits. Bazel equivalent: embedding `$(date +%s)` in action inputs.
- Current: 0% cross-run cache utilization; Proposal: content-addressed OUTPUT_DIR via sha256
- Savings: 21K tok/session; Difficulty: S

**IC-01** (fd-compiler-incremental-build — token-efficiency):
SessionStart hooks fire `bd prime`, `heal-dolt.sh`, `bd stats` on every startup/resume/clear regardless of whether state changed. TypeScript watch mode only recompiles changed files.
- Current: 500-800 tok/turn idle; 10-16K tok/hr on idle loops
- Proposal: `.claude/session-state.json` with git SHA + bead mtime + memory hash; skip if unchanged
- Savings: 10-16K tok/hr; Difficulty: S

**IDE-01** (fd-ide-quick-actions — usability):
58 of 60+ plugins share "inter" prefix — typing `/inter` yields 116 options (minimal disambiguation). IntelliJ convention: 3-5 chars → <10 options.
- Proposal: semantic short-prefix aliases in plugin.json; Difficulty: S

**IDE-02** (fd-ide-quick-actions — usability):
6 distinct "review" commands with no inline disambiguation. IntelliJ never shows two actions with the same display name without contextual scoping.
- Savings: -150 tok/session; Difficulty: S–M

**IDE-03** (fd-ide-quick-actions — usability):
7 "status" commands with no context-aware routing or disambiguation.
- Proposal: context-aware routing (sprint context → sprint-status); Difficulty: M

---

### Issues to Address

- [ ] [SER-01 — fd-search-engine-ranking] Two-stage retrieval for agent triage (P1, M)
- [ ] [BSC-1 — fd-build-system-caching] Content-address OUTPUT_DIR to fix hermeticity (P1, S)
- [ ] [IC-01 — fd-compiler-incremental-build] Session-warm dirty-bit cache (P1, S)
- [ ] [IDE-01 — fd-ide-quick-actions] Semantic short-prefix aliases for plugins (P1, S)
- [ ] [IDE-02 — fd-ide-quick-actions] Review command disambiguation (P1, S-M)
- [ ] [IDE-03 — fd-ide-quick-actions] Status command context routing (P1, M)

---

### Key P2 Improvements

- SER-02: Skill routing retrieval stage (-6.5K tok/turn, L)
- SER-03: CASS CTR feedback into tier scoring (M)
- BSC-2: Content-addressed temp file paths (-1.5K tok/run, XS)
- BSC-3: Pre-fetch scratch area for fan-out (-10-15K tok/run, M)
- BSC-4: Cross-session findings cache (-96K tok/repeat-review, L)
- IC-02: Dirty-bit roadmap generation (95% bd-list reduction, S)
- IC-03: Flux-drive triage memoization (-2.5K tok/iterative-review, M)
- IC-06: Generalize manifest pattern from gen-skill-compact.sh (S)
- IDE-06: Progressive disclosure for 232-option listing (-500 tok/session, M)

---

### Cross-Agent Convergence

- **Agent triage cost** (SER-01 × IC-03 × BSC-4): 3 agents independently flagged full-LLM-dispatch-with-no-caching as the root. Highest-confidence finding.
- **Timestamp hermeticity** (BSC-1 × BSC-2 × IC-01): 2 agents flagged non-deterministic inputs defeating cache; 1 flagged idle re-orientation using same timestamps. Same root pattern.
- **Manifest pattern isolated** (IC-06 × BSC-2): Both agents noted gen-skill-compact.sh has the correct pattern — not generalized.

---

### Files
- Summary: `docs/research/flux-drive/2026-05-04-target/summary.md`
- Individual reports: `fd-search-engine-ranking.md`, `fd-build-system-caching.md`, `fd-compiler-incremental-build.md`, `fd-ide-quick-actions.md`
