# Flux-Drive Review System: Comprehensive Analysis for AgentDropout Implementation

**Date:** 2026-02-25  
**Purpose:** Detailed architectural understanding of flux-drive for implementing AgentDropout (post-triage redundancy filter)  
**Scope:** Skill definition, triage logic, dispatch mechanism, agent definitions, synthesis, budget controls, trust scoring

---

## 1. Flux-Drive Skill Definition & Workflow

### 1.1 High-Level Architecture

**File:** `/home/mk/projects/Demarch/interverse/interflux/skills/flux-drive/SKILL.md` (457 lines)

Flux-drive is a **4-phase, multi-agent review orchestrator** for documents and codebases:

- **Phase 1: Analyze + Triage** → Profile document, detect domain, select agents, score them
- **Phase 2: Launch** → Dispatch agents in parallel (Stage 1), monitor completion, optionally expand (Stage 2)
- **Phase 3: Synthesize** → Collect findings, deduplicate, write verdict
- **Phase 4: Cross-AI (Optional)** → Oracle review if available

### 1.2 Phase 1: Triage (Steps 1.0-1.3)

**Key Functions & Data Structures:**

| Step | Function | Output | File Path |
|------|----------|--------|-----------|
| 1.0 | Project understanding + domain detection cache check | `flux-drive.yaml` with `domains`, `content_hash`, `override` | `{PROJECT_ROOT}/.claude/flux-drive.yaml` |
| 1.0.1 | Deterministic domain detection | JSON: `{"domains": [...], "source": "deterministic"}` | via `scripts/detect-domains.py` |
| 1.0.2 | Staleness check via content hash | Cache freshness signal | via `scripts/content-hash.py --check <hash>` |
| 1.0.3 | Re-detect (if stale) | Updated `flux-drive.yaml` | Same location, new hash |
| 1.0.4 | Auto-generate project-specific agents | JSON: `{"status": "ok", "generated": [], "skipped": [], "orphaned": []}` | via `scripts/generate-agents.py --mode=regenerate-stale` |
| 1.1 | Document profile extraction | **Document Profile** struct with type, summary, languages, domains, divergence, complexity | In-memory for use in Step 1.2 |
| 1.2a.0 | Routing overrides check | Excluded agent list + warnings for cross-cutting exclusions | Read `.claude/routing-overrides.json` (optional) |
| 1.2a | Pre-filter agents by category | Candidate pool (reduced) | In-memory agent filter bitmask |
| 1.2b | Score agents (0-7 scale) | **Triage Table** with Agent, Category, Score, Stage, Est. Tokens, Reason, Action | In-memory scoring table |
| 1.2c | Budget-aware selection | Updated triage table with budget constraints applied | Final agent selection (Stage 1/2/Deferred) |
| 1.2d | Document section mapping | **Section Map** per agent (priority/context classifications) | In-memory, used in Phase 2 |
| 1.3 | User confirmation | Approval signal | Via AskUserQuestion |

### 1.3 Agent Roster

**Technical Agents (7):**
- `fd-architecture` — Boundaries, coupling, patterns, complexity
- `fd-safety` — Threats, credentials, trust, deploy risk
- `fd-correctness` — Data consistency, races, transactions, async
- `fd-quality` — Naming, conventions, tests, idioms
- `fd-user-product` — User flows, UX, value prop, scope
- `fd-performance` — Bottlenecks, resources, scaling
- `fd-game-design` — Balance, pacing, feedback loops

**Cognitive Agents (5)** — Document review only (`.md`/`.txt` inputs):
- `fd-systems`, `fd-decisions`, `fd-people`, `fd-resilience`, `fd-perception`

**Special Categories:**
- **Project Agents** (`.claude/agents/fd-*.md`) — Generated via `/flux-gen`
- **Cross-AI (Oracle)** — Via `oracle --wait` CLI (GPT-5.2 Pro)
- **Research Agents** (on-demand, not scored): `best-practices-researcher`, `framework-docs-researcher`, `git-history-analyzer`, `learnings-researcher`, `repo-research-analyst`

---

## 2. Triage Logic (Step 1.2)

### 2.1 Scoring Algorithm

**Specification File:** `/home/mk/projects/Demarch/interverse/interflux/docs/spec/core/scoring.md`

```
final_score = (base_score + domain_boost + project_bonus + domain_agent_bonus) * trust_multiplier
max_possible = (3 + 2 + 1 + 1) * 1.0 = 7
```

#### Components:

**Base Score (0-3):** Intrinsic relevance to document content
- 3 = Core domain (primary focus, >30% of content)
- 2 = Adjacent domain (secondary concern, 10-30% of content)
- 1 = Tangential (marginal, <10% of content)
- 0 = Irrelevant (always excluded, bonuses cannot override)

**Domain Boost (0-2):** Applied only if base_score ≥ 1, based on domain profile injection criteria
- ≥3 bullets → +2
- 1-2 bullets → +1
- 0 bullets → +0

**Project Bonus (0-1):** Project has CLAUDE.md/AGENTS.md
- +1 if project-scoped (always for generated agents)
- +0 otherwise

**Domain Agent Bonus (0-1):** Project-specific agents matching detected domain
- +1 if agent is generated AND domain matches specialization
- +0 otherwise

**Trust Multiplier (0.05-1.0):** Interspect feedback (historical acceptance rate)
- Loaded via `_trust_scores_batch(project)` from `lib-trust.sh`
- Defaults to 1.0 if no data
- Multiplicative (prevents trust from overriding base relevance)

**Decay formula:** `weight * (1.0 / (1.0 + days_old/30))`
- 0 days → 1.0
- 30 days → 0.5
- 90 days → 0.25

### 2.2 Pre-Filtering (Step 1.2a)

**For file/directory inputs:**

| Agent | Skip If | Passes If |
|-------|---------|-----------|
| fd-correctness | No data keywords | Mentions: databases, migrations, concurrency, async, transactions |
| fd-user-product | Not product-related | Is PRD/proposal/user-facing, or mentions: flows, UX, customer |
| fd-safety | Not deploy-related | Mentions: security, credentials, auth, deployments, permissions, secrets |
| fd-game-design | Not game-related | Domain detected OR keywords: gameplay, balance, player, quest |
| fd-systems, fd-decisions, fd-people, fd-resilience, fd-perception | Not `.md`/`.txt` | **Only** for document inputs, NEVER code/diffs |
| fd-architecture, fd-quality, fd-performance (file/dir) | — | Always pass |

**For diff inputs:** Use routing patterns from domain profiles (priority file patterns + hunk keywords)

### 2.3 Dynamic Slot Ceiling

```
base_slots       = 4

scope_slots:
  - single file:           +0
  - small diff (<500):     +1
  - large diff (500+):     +2
  - directory/repo:        +3

domain_slots:
  - 0 domains detected:    +0
  - 1 domain detected:     +1
  - 2+ domains detected:   +2

generated_slots:
  - has flux-gen agents:   +2
  - no agents:             +0

total_ceiling = min(base + scope + domain + generated, 12)
```

### 2.4 Stage Assignment

**Stage 1:** Top 40% of total slots (rounded up, min 2, max 5)
**Stage 2:** All remaining selected agents
**Expansion Pool:** Agents scoring ≥2 but not selected

**Tiebreaker for Stage 1:** Project > Plugin > Cross-AI

### 2.5 Budget-Aware Selection (Step 1.2c)

**File:** `/home/mk/projects/Demarch/interverse/interflux/config/flux-drive/budget.yaml`

**Default budgets:**
- plan: 150K
- brainstorm: 80K
- prd: 120K
- spec: 150K
- diff-small: 60K
- diff-large: 200K
- repo: 300K

**Per-agent defaults (when <3 interstat runs):**
- review agents: 40K
- cognitive agents: 35K
- research agents: 15K
- oracle: 80K
- generated agents: 40K

**Key Rules:**
- Stage 1 agents are **protected** (always run)
- Stage 2 agents are deferred first when budget is tight
- **Exempt agents** (never dropped): `fd-safety`, `fd-correctness` (T8.1 mitigation)
- Slicing discount: multiply estimate by 0.5 when document slicing active
- Minimum agents: 2 (always)
- Sprint budget override: `FLUX_BUDGET_REMAINING` env var (soft enforcement)

---

## 3. Agent Dispatch Mechanism (Phase 2: Steps 2.0-2.3)

**File:** `/home/mk/projects/Demarch/interverse/interflux/skills/flux-drive/phases/launch.md`

### 3.1 Pre-Launch Setup (Step 2.0)

```bash
mkdir -p {OUTPUT_DIR}  # Must be absolute path
find {OUTPUT_DIR} -maxdepth 1 -type f -name "*.md" -delete  # Clean stale outputs
```

### 3.2 Knowledge & Context Injection (Steps 2.1-2.1d)

| Step | Purpose | Input | Output |
|------|---------|-------|--------|
| 2.1 | Retrieve knowledge entries from qmd MCP | Agent domain keywords + document summary | Up to 5 knowledge entries per agent |
| 2.1a | Load domain-specific review criteria | Detected domains (1-3 max) | Domain Context block per agent |
| 2.1b (diff only) | Apply diff slicing | Diff file ≥1000 lines → per-agent hunks | Per-agent slice files |
| 2.1c (doc ≥200 lines) | Apply document slicing | Document sections + agent focus → Interserve classify | Per-agent content files |
| 2.1d | Load interspect overlays | Agent name → Type 1 overlays | Overlay Context block |
| 2.1e | Apply trust multiplier | Interspect lib-trust.sh → _trust_scores_batch | Adjusted agent scores |

### 3.3 Stage 1 Dispatch (Step 2.2)

```bash
Task(subagent_type: interflux:review:fd-{agent-name}):
  run_in_background: true
  prompt: |
    [Agent prompt template from launch.md]
    {REVIEW_FILE} or {REVIEW_FILE_{agent-name}} if sliced
    {DOMAIN_CONTEXT}
    {OVERLAY_CONTEXT}
    ...
```

**Agent output contract:**
- File: `{OUTPUT_DIR}/{agent-name}.md.partial` → rename to `.md` on completion
- Ending line: `<!-- flux-drive:complete -->`
- Structure:
  ```markdown
  ### Findings Index
  - SEVERITY | ID | "Section" | Title
  Verdict: safe|needs-changes|risky

  ### Summary
  ### Issues Found
  ### Improvements
  ```

### 3.4 Research Context Escalation (Step 2.2a - Optional)

Trigger conditions:
- Stage 1 finding references library version + questions best practice
- Finding flags pattern as "possibly deprecated"
- Finding identifies pattern but uncertain about framework recommendation

**Dispatch:** 1-2 research agents (foreground, wait for result, max 60s)
**Inject into Stage 2:** Research result as additional context

### 3.5 Domain-Aware Expansion Decision (Step 2.2b)

**Domain Adjacency Map:**
```yaml
fd-architecture: [fd-performance, fd-quality]
fd-correctness: [fd-safety, fd-performance]
fd-safety: [fd-correctness, fd-architecture]
fd-quality: [fd-architecture, fd-user-product]
fd-user-product: [fd-quality, fd-game-design]
fd-performance: [fd-architecture, fd-correctness]
fd-game-design: [fd-user-product, fd-correctness, fd-performance]
```

**Expansion Scoring:**
```
expansion_score = 0
if any P0 in adjacent domain: += 3
if any P1 in adjacent domain: += 2
if Stage 1 agents disagree:  += 2
if agent has domain criteria: += 1
```

**Decision:**
- ≥3 → **Recommend expansion** (specific agents shown)
- 2 → **Offer expansion** (user choice)
- ≤1 → **Recommend stop** (default)

### 3.6 Completion Monitoring (Step 2.3)

**Polling loop:** Check `{OUTPUT_DIR}/` for `.md` files every 30s, up to 5 minutes
**Retry logic:** If `.md.partial` exists but `.md` missing:
- Check if `.md` already exists (pre-retry guard)
- Retry once (foreground, timeout 300s)
- Create error stub if second attempt fails

---

## 4. Synthesis & Deduplication (Phase 3)

**File:** `/home/mk/projects/Demarch/interverse/intersynth/agents/synthesize-review.md`

### 4.1 Synthesis Subagent Invocation

```bash
Task(intersynth:synthesize-review):
  OUTPUT_DIR={dir}
  VERDICT_LIB={path to lib-verdict.sh}
  MODE=flux-drive
  CONTEXT="Reviewing {INPUT_TYPE}: {INPUT_STEM}"
  FINDINGS_TIMELINE={OUTPUT_DIR}/peer-findings.jsonl (optional)
```

Returns: Compact ~15-line summary

Writes:
- `{OUTPUT_DIR}/synthesis.md` — human-readable report
- `{OUTPUT_DIR}/findings.json` — structured data
- `.clavain/verdicts/{agent-name}.json` — structured verdicts via lib-verdict.sh

### 4.2 Deduplication Rules (5 rules applied in order)

1. **Same file:line + same issue → Merge:** Use highest severity, credit all agents
2. **Same file:line + different issues → Keep separate:** Tag co-located, cross-reference
3. **Same issue + different locations → Keep separate:** Cross-reference with `cross_references`
4. **Conflicting severity → Use highest:** Record all positions in `severity_conflict`
5. **Conflicting recommendations → Preserve both:** Include both in `descriptions` map

**Additional:**
- Track convergence: "N/M agents"
- Keep most specific version when merging
- Discard findings matching `PROTECTED_PATHS`

### 4.3 Convergence with Document Slicing

When slicing is active:
- Only count agents that received relevant section as `priority` in convergence
- If 2+ agents agree across different priority sections → boost convergence by 1
- Tag with `"slicing_boost": true` in findings.json

### 4.4 Findings Timeline (Optional, peer-findings.jsonl)

If `FINDINGS_TIMELINE` file exists:
- Tracks discovery order and cross-agent adjustments
- Detects remaining contradictions
- Attributes first discoverer in `"discovered_by"` field

---

## 5. Trust Scoring & Interspect Integration

**File:** `/home/mk/projects/Demarch/interverse/interspect/hooks/lib-trust.sh`

### 5.1 Trust Feedback Recording

```bash
_trust_record_outcome "$session_id" "$agent" "$project" "$finding_id" "$severity" "$outcome" "$run_id"
```

- `outcome`: "accepted" or "discarded"
- `severity`: P0 (weight 4x), P1 (2x), P2 (1x), P3 (0.5x)
- Fails silently (never blocks workflow)

### 5.2 Trust Score Computation

```bash
TRUST_SCORES=$(_trust_scores_batch "$PROJECT")
# Returns: tab-separated "agent\tscore" lines (0.05-1.0)
```

**Factors:**
- High precision (>80% accepted, 10+ reviews): 0.85-1.0
- Medium precision (50-80%): 0.50-0.85
- Low precision (<50%): 0.05-0.50
- Decay: half-life ~30 days (multiplicative)

### 5.3 Integration with Flux-Drive

**Step 2.1e:** Load trust scores before ranking agents

```bash
INTERSPECT_PLUGIN=$(find ~/.claude/plugins/cache -path "*/interspect/*/hooks/lib-trust.sh" 2>/dev/null | head -1)
if [[ -n "$INTERSPECT_PLUGIN" ]]; then
    source "$INTERSPECT_PLUGIN"
    TRUST_SCORES=$(_trust_scores_batch "$PROJECT")
fi
# For each agent: final_score = raw_score * trust_scores[agent] (default 1.0)
```

**Debug output (FLUX_DEBUG=1):**
```
Trust: fd-safety=0.85, fd-correctness=0.92, fd-game-design=0.15, fd-quality=0.78
```

---

## 6. Routing Overrides & Interspect Evidence

**File:** `.claude/routing-overrides.json` (Step 1.2a.0)

```json
{
  "version": 1,
  "overrides": [
    {
      "agent": "fd-game-design",
      "action": "exclude",
      "scope": {
        "domains": ["web-api"],
        "file_patterns": ["internal/handlers/*.go"]
      },
      "canary": {
        "status": "active",
        "created": "2026-02-24T10:00:00Z",
        "expires": "2026-03-09T10:00:00Z"
      },
      "confidence": 0.85
    }
  ]
}
```

**Scope logic (AND):**
- If `scope.domains` set: check document domain matches any in list
- If `scope.file_patterns` set: check input file matches any glob
- If both: BOTH must match
- If `**` only: global override + warning about cross-cutting agents

---

## 7. Files & Directory Structure

### Core Skill Files:

```
/home/mk/projects/Demarch/interverse/interflux/skills/flux-drive/
├── SKILL.md                    (457 lines — main orchestration)
├── SKILL-compact.md            (Condensed reference)
├── phases/
│   ├── launch.md               (Phase 2 dispatch protocol)
│   ├── synthesize.md           (Phase 3 dedup & verdict)
│   ├── cross-ai.md             (Phase 4 Oracle integration)
│   ├── slicing.md              (Document/diff slicing)
│   ├── shared-contracts.md     (Output format contract)
├── references/
│   ├── agent-roster.md         (Agent details & subagent_type)
│   ├── scoring-examples.md     (4 worked examples)
├── config/
│   ├── budget.yaml             (Budget by INPUT_TYPE)
│   ├── agent-roles.yaml
│   ├── domains/                (Domain profiles)
│   │   ├── index.yaml
│   │   ├── web-api.md
│   │   ├── game-simulation.md
│   │   └── ...
│   ├── knowledge/              (Knowledge base for injection)
```

### Synthesis Files:

```
/home/mk/projects/Demarch/interverse/intersynth/
├── agents/
│   ├── synthesize-review.md    (Synthesis orchestrator)
│   └── synthesize-research.md
├── hooks/
│   └── lib-verdict.sh          (Verdict writing utilities)
```

### Interspect Integration:

```
/home/mk/projects/Demarch/interverse/interspect/
├── hooks/
│   ├── lib-trust.sh            (Trust scoring engine)
│   ├── lib-interspect.sh       (Core DB & utility)
│   ├── interspect-session.sh   (SessionStart hook)
│   ├── interspect-verdict.sh   (PostToolUse verdict feedback)
│   └── interspect-evidence.sh  (PostToolUse dispatch evidence)
```

### Project-Level Configuration:

```
{PROJECT_ROOT}/
├── .claude/
│   ├── flux-drive.yaml         (Domain cache + override)
│   ├── routing-overrides.json  (Agent exclusions)
│   ├── flux-drive-budget.yaml  (Project-level budget override)
│   └── agents/
│       ├── fd-*.md             (Generated project agents)
├── docs/research/flux-drive/   (OUTPUT_DIR for flux-drive runs)
│   └── {INPUT_STEM}/
│       ├── fd-*.md             (Agent findings)
│       ├── summary.md          (Synthesis report)
│       ├── findings.json       (Structured findings)
│       └── oracle-council.md   (Cross-AI review)
```

### Flux-Gen Specs (Saved Prompts):

```
/home/mk/projects/Demarch/.claude/flux-gen-specs/
├── mcp-agent-mail-research.json
```

Each spec is a saved Sonnet prompt with 5 agent definitions (fd-persistence-durability, fd-messaging-protocol, fd-coordination-identity, fd-tool-surface, fd-workflow-macros) covering a specific domain. The spec avoids re-running 25K+ tokens per regeneration.

---

## 8. Where AgentDropout Should Be Inserted

### 8.1 Key Insertion Point: Between Stage 1 Completion and Stage 2 Expansion Decision

**Current Flow:**
```
Step 2.2a (optional):  Research context (if needed)
   ↓
Step 2.2b:            Domain-aware expansion decision
   ├─ Read Stage 1 findings
   ├─ Compute expansion_score per Stage 2/pool agent
   ├─ Recommend/offer expansion
   └─ User approves/denies
   ↓
Step 2.2c:            Launch Stage 2 (if expanded)
```

**AgentDropout should insert BEFORE Step 2.2b:**

```
Step 2.2a (optional):    Research context
   ↓
Step 2.2a.5 [NEW]:       AgentDropout filter
   ├─ Load Stage 1 findings + convergence data
   ├─ Identify overlapping agents
   ├─ Score redundancy vs value
   ├─ Mark low-confidence agents for dropout
   ├─ Produce dropout report
   └─ Update Stage 2 / expansion pool
   ↓
Step 2.2b:              Domain-aware expansion decision (on filtered pool)
   ├─ Read Stage 1 findings
   ├─ Compute expansion_score on FILTERED agents only
   ├─ Recommend expansion
   └─ User approves
```

### 8.2 Data Structures Available at Dropout Decision Point

**Input:**
- `{OUTPUT_DIR}/{agent-name}.md` — All Stage 1 findings with Findings Index
- **Findings Index format:**
  ```
  - SEVERITY | ID | "Section" | Title
  Verdict: safe|needs-changes|risky
  ```
- Agent triage scores from Phase 1 (in session memory)
- Stage 2 / expansion pool agent list with scores
- `CONVERGENCE_DATA` — N/M agents per finding (from synthesis preprocessing)

**Output:**
- Updated `expansion_pool` (removed low-confidence agents)
- Dropout report (which agents + why)
- Modified `stage_2_candidates` list

### 8.3 Dropout Scoring Formula (Proposed)

**For each Stage 2 / expansion pool agent:**

```
dropout_score = 0

# Redundancy signals (higher = more redundant)
if agent domain overlaps ≥2 other Stage 1 agents:  dropout_score += 3
if agent has domain adjacency to Stage 1 agent:    dropout_score += 1
if Stage 1 found 0 P0/P1 in agent's domain:        dropout_score += 2
if Stage 1 agents have high convergence (≥2/3):    dropout_score += 2

# Value preservation (blocks dropout)
if agent is exempt (fd-safety, fd-correctness):   dropout_score = -999 (never dropout)
if agent has high trust score (≥0.85):            dropout_score -= 2
if agent covers thin section (<5 lines):          dropout_score -= 1

# Final decision
if dropout_score ≥ 5 AND agent.stage == 2:   CANDIDATE FOR DROPOUT
if dropout_score ≥ 4 AND agent NOT in top-40% Stage 1 boundary: CANDIDATE FOR DROPOUT
```

### 8.4 Intersection with Budget Controls

**Current budget logic (Step 1.2c):**
- Stage 1 agents are **protected** (always run)
- Stage 2 agents are deferred first when budget tight
- Exempt agents (`fd-safety`, `fd-correctness`) never deferred

**Proposed AgentDropout interaction:**
- AgentDropout runs AFTER Stage 1 completes (post-evidence)
- Dropout candidates are a **subset** of already-deferred agents
- Exempt agents remain protected (skip dropout filtering entirely)
- If budget was already too tight to launch an agent, dropout doesn't re-rank it

---

## 9. Evidence & Findings Available for Dropout Decisions

### 9.1 What Each Agent Output Contains

**File:** `{OUTPUT_DIR}/{agent-name}.md`

```markdown
### Findings Index
- P0 | P0-1 | "Architecture" | Circular dependency in auth module
- P1 | P1-2 | "Data" | Missing transaction boundary
Verdict: needs-changes

### Summary
[3-5 lines]

### Issues Found
P0-1. SEVERITY: Circular dependency — module A imports module B which imports module A
P1-2. SEVERITY: Transactions — user creation not wrapped in transaction

### Improvements
IMP-1. Add integration test for cross-module dependencies
```

### 9.2 Convergence Data (From Synthesis Preprocessing)

During synthesis (Step 3.2), before dedup rules applied:

```json
{
  "finding_id": "P0-1",
  "title": "Circular dependency in auth module",
  "agents_who_found_it": ["fd-architecture", "fd-quality"],
  "convergence": "2/4",  // 2 of 4 Stage 1 agents found this
  "severity": "P0",
  "section": "Architecture"
}
```

### 9.3 Agent Domain Coverage Map

**Available from Step 1.2 (triage):**

```
fd-architecture: base_score=3, domain_boost=+2, final_score=5, domain_coverage="boundaries+coupling+patterns"
fd-safety:       base_score=3, domain_boost=+1, final_score=4, domain_coverage="auth+credentials"
fd-correctness:  base_score=0, domain_boost=–,  final_score=0, domain_coverage="—" (filtered)
fd-quality:      base_score=2, domain_boost=+1, final_score=3, domain_coverage="conventions+idioms"
```

---

## 10. Exempt Agents (Never Dropout)

Per `/home/mk/projects/Demarch/interverse/interflux/config/flux-drive/budget.yaml`:

```yaml
exempt_agents:
  - fd-safety
  - fd-correctness
```

**Rationale (T8.1 mitigation):** These agents cover critical domains (security + data consistency). Even if Stage 1 didn't flag P0/P1, they provide security/correctness validation that cannot be safely dropped.

---

## 11. Summary: Integration Points for AgentDropout

### 11.1 Critical Files to Modify/Reference

| File | Modification | Purpose |
|------|--------------|---------|
| `phases/launch.md` | Add Step 2.2a.5 | Insert dropout filter between research context & expansion |
| `phases/synthesize.md` | Reference | Retrieve convergence data pre-dedup |
| `docs/spec/core/staging.md` | NEW section | Document dropout algorithm & interaction with staging |
| `config/flux-drive/budget.yaml` | Reference | Check exempt_agents list |
| `SKILL.md` | Update Phase 2 overview | Mention dropout as optional post-Stage-1 filter |

### 11.2 Data Flow for Dropout Implementation

```
Phase 1 Output:
├─ triage_scores: agent → (base_score, domain_boost, project_bonus, final_score)
├─ stage_assignment: agent → (Stage 1 | Stage 2 | Expansion Pool)
├─ domain_adjacency_map: agent → [adjacent agents]
└─ exempt_agents: [fd-safety, fd-correctness]

Phase 2.0-2.2a Output:
├─ stage_1_findings: {agent} → findings_index (SEVERITY | ID | Section | Title)
├─ stage_1_verdicts: {agent} → verdict (safe|needs-changes|risky)
├─ convergence_map: finding_id → convergence_count (N/M agents)
└─ domain_coverage_summary: {domain} → [agents that found issues]

Phase 2.2a.5 [NEW] Input:
├─ All of above
├─ stage_2_candidates: [agent names with scores]
└─ expansion_pool: [agent names with scores ≥2]

Phase 2.2a.5 [NEW] Output:
├─ dropout_candidates: [(agent, dropout_score, reason)]
├─ filtered_stage_2: stage_2_candidates minus dropouts
├─ filtered_expansion_pool: expansion_pool minus dropouts
└─ dropout_report: human-readable summary

Phase 2.2b Input (Modified):
├─ Use filtered_stage_2 & filtered_expansion_pool
├─ Compute expansion_score on filtered agents only
└─ Present to user with dropout summary
```

### 11.3 MVP Dropout Algorithm (Minimal Viable Product)

```bash
# Pseudocode for Step 2.2a.5

for each agent in stage_2_candidates + expansion_pool:
    if agent in exempt_agents:
        continue  # Never dropout exempt agents
    
    dropout_score = 0
    
    # Count redundancy: how many Stage 1 agents cover this agent's domain?
    overlapping = count_agents_in_same_domain(agent, stage_1_agents)
    if overlapping >= 2:
        dropout_score += 3
    
    # Check if Stage 1 already covered this agent's domain thoroughly
    convergence = max_convergence_in_domain(agent.domain, stage_1_findings)
    if convergence >= 2/3:  # At least 2 of 3+ Stage 1 agents found issues
        dropout_score += 2
    
    # Check Stage 1 severity in this domain
    max_severity = max_severity_in_domain(agent.domain, stage_1_findings)
    if max_severity < P1:  # Only P2/P3 in this domain
        dropout_score += 2
    
    # Preserve high-trust agents
    trust_score = interspect_trust_scores[agent]
    if trust_score >= 0.85:
        dropout_score -= 2
    
    # Decision
    if dropout_score >= 5:
        mark_for_dropout(agent, reason=f"redundancy score {dropout_score}")
```

---

## 12. Related Features & Dependencies

### 12.1 Interspect Integration (iv-ynbh dependency)

- **Trust feedback table:** `trust_feedback(ts, session_id, agent, project, finding_id, severity, outcome, review_run_id, weight)`
- **Trust scoring:** `_trust_scores_batch(project)` → agent → score (0.05-1.0)
- **Evidence recording:** `_interspect_read_evidence(agent, project)` → recent session evidence
- **Command:** `/interspect:status` — live agent trust status

**For AgentDropout:** Use trust scores as a modifier (high trust = protected from dropout)

### 12.2 Budget Controls (iv-8m38 dependency)

- **Enforcement:** soft (warn) vs hard (block)
- **Exempt agents:** `fd-safety`, `fd-correctness` (never dropped by budget or dropout)
- **Slicing multiplier:** 0.5x for domain-specific agents when document slicing active

**For AgentDropout:** Exempt agents are protected; dropout doesn't override this

### 12.3 Interserve Classification (for document/diff slicing)

- `classify_sections(file_path, agents=[])` → per-agent priority/context classification
- Used in Step 2.1b/2.1c to create per-agent content files

**For AgentDropout:** Consider which agents received content as priority vs context (context-only agents are candidates for dropout)

---

## 13. Key Insights for Implementation

1. **Dropout is a POST-EVIDENCE filter:** It runs after Stage 1 completes and can see which agents actually found issues. This is strictly better than pre-filtering.

2. **Exempt agents must be honored:** `fd-safety` and `fd-correctness` have T8.1 (threat model) justification. They cannot be dropped regardless of redundancy signals.

3. **Convergence is the key signal:** If Stage 1 agents agree (high convergence) on findings in a domain, Stage 2 agents in that domain are candidates for dropout.

4. **Trust scores scale redundancy risk:** An agent with low trust score (0.15) is a better dropout candidate than an agent with high trust (0.85) even if both are technically redundant.

5. **Budget interaction is subtle:** AgentDropout is NOT a budget enforcement mechanism. It's a post-evidence quality filter. Budget enforcement happens in Step 1.2c; dropout happens in Step 2.2a.5.

6. **Domain adjacency map is the topology:** The adjacency map in Step 2.2b (expansion scoring) is the same topology AgentDropout should use. An agent adjacent to a successful Stage 1 agent is a dropout candidate.

7. **Thin sections need preservation:** If a Stage 2 agent covers a section that Stage 1 only lightly touched (context-only classification), it should resist dropout.

---

**End of Analysis**
