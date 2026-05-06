# fd-build-system-caching Review

## Findings Index

- P1 | BSC-1 | "Action Hermeticity" | Timestamped OUTPUT_DIR in agent prompts defeats all cross-run prompt cache hits
- P2 | BSC-2 | "Content Addressing" | Temp file paths include epoch timestamp, defeating intra-session cache
- P2 | BSC-3 | "Action Graph" | Tool results (Read, git status) not shared across parallel fan-out
- P2 | BSC-4 | "Remote Cache" | No cross-session findings cache keyed by content hash
- P2 | BSC-5 | "Incremental Builds" | Re-running /flux-drive after small fix re-executes all agents from scratch

Verdict: needs-changes

---

## Summary

The flux-drive dispatch pipeline has **zero cross-run cache utilization** due to runtime timestamps embedded in every agent prompt. From a Bazel/Buck perspective, this is equivalent to embedding `$(date +%s)` in every action's inputs — no hermetic actions, no cache hits across builds. The codebase already has content-hash infrastructure for domain detection caching (`structural_hash` in `.claude/flux-drive.yaml`), proving the pattern is feasible, but this pattern is not applied to agent dispatch. A build engineer would estimate 30-50K tokens wasted per re-run on unchanged targets due to cache misses that could be hits.

---

## Issues Found

### BSC-1. P1: Timestamped OUTPUT_DIR Defeats All Cross-Run Prompt Cache Hits

**Axis:** Token-efficiency

**Discipline Reference:** In Bazel, hermetic actions guarantee same-input produces same-output, enabling content-addressed caching. Any non-deterministic input (timestamps, system state) defeats hermeticity. Actions that embed `$(date)` in their inputs can never cache.

**Current State:**
- `SKILL.md` lines 112-117 generate a run-specific timestamp:
  ```
  RUN_TS = $(date +%Y%m%dT%H%M)
  OUTPUT_DIR = {OUTPUT_DIR}-{RUN_TS}
  ```
- This OUTPUT_DIR is embedded in every agent prompt (prompt-template.md):
  - `Write findings to {OUTPUT_DIR}/{agent-name}.md.partial`
  - `Peer findings file: {OUTPUT_DIR}/peer-findings.jsonl`
  - `bash {FINDINGS_HELPER} write "{OUTPUT_DIR}/peer-findings.jsonl" ...`
- Every run produces a unique OUTPUT_DIR string, even for identical document reviews
- Anthropic's prompt cache keys on system prompt content — different OUTPUT_DIR = different key = cache miss

**Evidence:**
- SKILL.md line 112: `RUN_TS = $(date +%Y%m%dT%H%M)`
- prompt-template.md line 10: `Write findings to \`{OUTPUT_DIR}/{agent-name}.md.partial\``
- findings-helper.sh line 35: timestamp embedded in every finding: `'{severity:$sev, agent:$agt, ..., timestamp:$ts}'`

**Proposal:**
1. Use content-addressed OUTPUT_DIR: `OUTPUT_DIR = flux-drive-{sha256(target_path + agent_roster)[:12]}`
2. Alternatively, use a stable path with per-run isolation via subdirectory: `OUTPUT_DIR/run-{RUN_TS}/`
3. Template agent prompts with `{OUTPUT_BASE}` (stable) and `{RUN_DIR}` (run-specific), keeping the majority of the prompt stable

**Estimated Savings:**
- Current cross-run cache hit rate: ~0%
- With content-addressed paths: ~60-80% for unchanged document reviews
- At 150K tokens/run budget, 20% repeat reviews, 70% potential cache: **~21,000 tokens/session saved**

**Difficulty:** S — Single PR changing path generation logic in SKILL.md and prompt-template.md

**Risk:** Breaking change for scripts that glob `docs/research/flux-drive/*-YYYYMMDD*`. Mitigate with symlink: `latest -> {content-addressed-dir}`

---

### BSC-2. P2: Epoch Timestamp in Temp File Paths

**Axis:** Token-efficiency

**Discipline Reference:** In Buck, file artifacts are identified by content hash, not path. Two builds reading the same file content get the same cache entry regardless of working directory.

**Current State:**
- `launch.md` line 64-72 generates temp files with epoch timestamp:
  ```bash
  TS=$(date +%s)
  REVIEW_FILE="/tmp/flux-drive-${INPUT_STEM}-${TS}.md"
  ```
- This path is embedded in agent prompts: `**File path**: \`{REVIEW_FILE}\``
- Same document content gets different REVIEW_FILE path on each run
- Agent prompt varies even when document hasn't changed

**Evidence:**
- launch.md line 64: `TS=$(date +%s)`
- launch.md line 72: `REVIEW_FILE="/tmp/flux-drive-${INPUT_STEM}-${TS}.md"`
- prompt-template.md line 98: `**File path**: \`{REVIEW_FILE}\``

**Proposal:**
1. Use content-hash in temp file name: `REVIEW_FILE="/tmp/flux-drive-${INPUT_STEM}-$(sha256sum INPUT_FILE | cut -c1-12).md"`
2. Or use a stable path with cleanup-before-write (already documented as an option in SKILL.md line 119-120)

**Estimated Savings:**
- Per-agent: ~500 bytes of prompt text stabilized
- Aggregate over 12 agents: ~6K characters = ~1,500 tokens per run
- Enables prompt cache hit for repeated file reviews

**Difficulty:** XS — Config change to path generation

**Risk:** Low. Content-addressed temp files are idempotent.

---

### BSC-3. P2: Tool Results Not Shared Across Parallel Agent Fan-Out

**Axis:** Token-efficiency

**Discipline Reference:** In Bazel, when multiple actions need the same input file, the file is read once and its content-addressed blob is shared. Actions declare inputs; the build system deduplicates reads.

**Current State:**
- Each agent independently reads:
  - `{REVIEW_FILE}` via Read tool (duplicated 12x for 12 agents)
  - CLAUDE.md, AGENTS.md (duplicated per agent that reads them)
  - `git status` output (if agent checks it)
- The orchestrator reads these files in Phase 1, but doesn't pass content to agents
- prompt-template.md line 100 tells agents: "Your FIRST action must be to Read this file"
- 12 parallel agents = 12 independent Read tool calls for the same document

**Evidence:**
- prompt-template.md line 100: `Your FIRST action must be to Read this file using the Read tool.`
- shared-contracts.md line 89-90: mentions "agents Read from temp files" — no content passing
- fd-architecture.md line 9-11: "Read `CLAUDE.md`, `AGENTS.md`, and architecture docs in the project root"

**Proposal:**
1. **Phase 2.5: Pre-fetch scratch area.** Before dispatch, create `{OUTPUT_DIR}/.scratch/`:
   ```
   .scratch/document.md      # full document content
   .scratch/claude-md.txt    # CLAUDE.md content
   .scratch/agents-md.txt    # AGENTS.md content
   .scratch/git-status.txt   # git status output
   .scratch/manifest.json    # {file_hash: content_hash} for staleness
   ```
2. Agent prompts reference pre-fetched content: "Document content is in `.scratch/document.md`. Do NOT re-read `{INPUT_FILE}` — use the scratch copy."
3. Content is written once by orchestrator, read many times by agents
4. No duplicate Read tool calls → fewer API round-trips, stable prompts

**Estimated Savings:**
- Typical document: ~2,000 lines = ~8K tokens
- 12 agents × 1 Read call avoided (content in scratch) = ~12 fewer tool round-trips
- Cache read efficiency: content stays in prompt cache TTL window
- Net: ~10-15K tokens/run from avoided re-reads and better cache behavior

**Difficulty:** M — Multi-file change: launch.md pre-fetch logic, prompt-template.md reference scratch, cleanup in synthesize.md

**Risk:** Scratch directory must be cleaned before dispatch (to avoid stale content from previous runs). Launch.md already has cleanup logic (line 14).

---

### BSC-4. P2: No Cross-Session Findings Cache (Remote Cache Analog)

**Axis:** Token-efficiency + ML-routing-replacement

**Discipline Reference:** In Bazel, remote cache stores action outputs keyed by `hash(inputs + action)`. Same inputs → skip execution, read cached output. The flux-drive equivalent: if `fd-architecture` reviewed `file.md` yesterday and the file hasn't changed, reuse findings instead of re-running the agent.

**Current State:**
- Domain detection HAS content-hash caching (domain-detection.md lines 102-119):
  ```yaml
  structural_hash: "sha256:abc123..."
  detected_at: "2026-02-14T17:00:00+00:00"
  domains: [...]
  ```
- But agent FINDINGS are not cached. Every `/flux-drive file.md` runs all agents from scratch.
- Knowledge compounding (synthesize.md lines 512-594) captures patterns but not findings cache.
- interstat tracks token usage (estimate-costs.sh) but not finding output.

**Evidence:**
- domain-detection.md line 107: `structural_hash: "sha256:abc123..."` — content hashing exists
- synthesize.md line 175-208: findings.json generated per-run, not cached cross-session
- No `findings-cache.yaml` or equivalent in the codebase (verified via Grep)

**Proposal:**
1. **Findings cache format:**
   ```yaml
   # {PROJECT_ROOT}/.claude/flux-drive-cache.yaml
   entries:
     - key: "fd-architecture:sha256(document):claude-sonnet-4-6"
       findings_hash: "sha256(findings.json)"
       verdict: "needs-changes"
       finding_count: 3
       created_at: "2026-05-04T10:00:00Z"
       ttl_days: 30
   ```
2. **Staleness:** Invalidate when `sha256(document)` changes OR agent definition changes OR model changes
3. **Lookup:** At dispatch time, check cache. If hit and not stale, skip agent, inject cached verdict into synthesis.
4. **Write-through:** After agent completes, write entry to cache.

**Estimated Savings:**
- Repeat reviews of unchanged documents: 100% agent token savings (cached)
- Estimated 20% of reviews are near-duplicates (same file, minor context change)
- At 40K tokens/agent, 12 agents, 20% reuse: **~96K tokens/session saved on repeat reviews**

**Difficulty:** L — New cache infrastructure, invalidation logic, synthesis integration

**Risk:** Cache coherence — must invalidate on agent .md file changes, not just document changes. Use agent content hash as part of cache key.

---

### BSC-5. P2: Re-Running /flux-drive After Small Fix Re-Executes All Agents

**Axis:** Usability + Token-efficiency

**Discipline Reference:** In Bazel, a source change only rebuilds actions that transitively depend on that file. If you change `auth.go`, only actions that read `auth.go` (directly or transitively) re-execute. Unchanged actions return cached outputs.

**Current State:**
- User reviews `plan.md`, gets P1 finding "missing error handling in auth section"
- User fixes the auth section (20 lines changed out of 500)
- User re-runs `/flux-drive plan.md`
- All 12 agents re-execute from scratch
- fd-performance (which found no issues and doesn't care about auth) re-runs anyway
- No incremental mode: `--skip-passing` or `--only-affected-sections` don't exist

**Evidence:**
- SKILL.md has no `--incremental` or `--only-affected` flag
- launch.md Step 2.2 unconditionally launches "Stage 1 agents (top 2-3 by triage score)"
- No diff-based agent selection: "these agents saw this section before and passed"

**Proposal:**
1. **Finding-aware triage (v1):** At dispatch, check findings cache (BSC-4). If an agent's previous run had verdict=safe and document sections it reviewed haven't changed, skip it.
2. **Section-level invalidation (v2):** For sliced documents (>200 lines), track which sections each agent reviewed. If a section changed, only re-run agents whose `section_map` included it.
3. **User-facing flag:** `--incremental` to opt-in (default: full re-run for safety)

**Estimated Savings:**
- Typical "fix one issue and re-run" scenario: 80% of agents unchanged
- 12 agents × 40K tokens × 80% skip rate = **~384K tokens saved per incremental re-run**
- UX improvement: re-run completes in 30s instead of 5 minutes

**Difficulty:** L — Requires findings cache (BSC-4) + section tracking + triage logic changes

**Risk:** False negatives — if agent is wrongly skipped, a real issue is missed. Mitigate: never skip safety-critical agents (fd-safety, fd-correctness).

---

## Improvements

### IMP-1. Action Graph Visualization

**Axis:** Usability

**Proposal:** Add `--dry-run` mode that outputs the action graph without executing:
```
$ /flux-drive --dry-run file.md

Action Graph:
├─ [fetch] Read file.md (2.3KB)
├─ [fetch] Read CLAUDE.md (1.1KB)
├─ [analyze] Profile document (Step 1.1)
├─ [triage] Score 12 agents (Step 1.2)
├─ [dispatch:parallel] Stage 1
│   ├─ fd-architecture (est: 42K tokens, cache: MISS)
│   ├─ fd-safety (est: 38K tokens, cache: MISS)
│   └─ fd-correctness (est: 35K tokens, cache: HIT → skip)
└─ [synthesize] Merge findings (Step 3)

Estimated: 115K tokens (42K cacheable)
```

This helps users understand the "build" before committing tokens.

**Difficulty:** S | **Savings:** UX friction reduction, no token savings

---

### IMP-2. Content-Hash Manifest for Staleness

**Axis:** Token-efficiency

**Proposal:** Generate `.claude/flux-drive-manifest.json` after each run:
```json
{
  "document_hash": "sha256:abc...",
  "agent_hashes": {
    "fd-architecture": "sha256:def...",
    "fd-safety": "sha256:ghi..."
  },
  "findings_hashes": {
    "fd-architecture": "sha256:jkl...",
    "fd-safety": "sha256:mno..."
  },
  "timestamp": "2026-05-04T10:00:00Z"
}
```

At next run, compare hashes to determine which agents need re-execution. This is the minimal infrastructure needed for incremental builds (BSC-5).

**Difficulty:** S | **Savings:** Enables BSC-4/BSC-5 savings (~100K+ tokens on repeat reviews)

---

### IMP-3. Prompt Template Factoring

**Axis:** Token-efficiency

**Proposal:** Factor agent prompts into stable prefix + variable suffix:

**Stable prefix (cacheable):**
```
# fd-architecture Agent

You are a Flux-drive Architecture reviewer. [full agent instructions...]

## Review Approach
[...]

## Output Format
Write findings to `.partial` file. [format instructions...]
```

**Variable suffix (per-run):**
```
## This Review

Document: /tmp/flux-drive-xyz.md (sha256:abc...)
Output: /home/user/project/docs/research/flux-drive/plan/fd-architecture.md
Peer findings: peer-findings.jsonl
```

Anthropic's cache keys on prefix stability. Longer stable prefix = higher cache hit rate.

**Difficulty:** M | **Savings:** ~20% better cache hit rate = ~30K tokens/run

---

## Action Graph Sketch: /flux-drive Fan-Out

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                     flux-drive Orchestrator                   │
                    └──────────────────────────────────────────────────────────────┘
                                                │
                         ┌──────────────────────┼──────────────────────┐
                         │                      │                      │
                    ┌────▼────┐           ┌─────▼─────┐          ┌─────▼─────┐
                    │ Phase 1 │           │  Phase 2  │          │  Phase 3  │
                    │ Analyze │           │  Launch   │          │ Synthesize│
                    └────┬────┘           └─────┬─────┘          └─────┬─────┘
                         │                      │                      │
           ┌─────────────┼─────────────┐        │                      │
           │             │             │        │                      │
      ┌────▼───┐   ┌─────▼────┐   ┌────▼───┐    │                      │
      │ Read   │   │ Profile  │   │ Triage │    │                      │
      │ files  │   │ document │   │ agents │    │                      │
      └────────┘   └──────────┘   └────────┘    │                      │
           │                                     │                      │
           │  HASH-UNSTABLE INPUTS:              │                      │
           │  - OUTPUT_DIR contains timestamp    │                      │
           │  - REVIEW_FILE contains epoch       │                      │
           │  - findings-helper embeds timestamp │                      │
           │                                     │                      │
           └─────────────────────────────────────┼──────────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
              ┌─────▼─────┐               ┌──────▼──────┐              ┌──────▼──────┐
              │ Stage 1   │               │   Stage 1   │              │   Stage 1   │
              │ Agent 1   │               │   Agent 2   │              │   Agent 3   │
              │ (parallel)│               │  (parallel) │              │  (parallel) │
              └─────┬─────┘               └──────┬──────┘              └──────┬──────┘
                    │                            │                            │
                    │  DUPLICATED READS:         │                            │
                    │  Each agent independently  │                            │
                    │  reads REVIEW_FILE,        │                            │
                    │  CLAUDE.md, AGENTS.md      │                            │
                    │                            │                            │
                    └────────────────────────────┼────────────────────────────┘
                                                 │
                                           ┌─────▼─────┐
                                           │ Synthesis │
                                           │  Agent    │
                                           └─────┬─────┘
                                                 │
                                           ┌─────▼─────┐
                                           │ findings  │
                                           │   .json   │ ◄── NOT CACHED
                                           └───────────┘     cross-session
```

**Hash-stable inputs that COULD enable caching:**
- Document content hash (sha256 of file)
- Agent definition hash (sha256 of .md file)
- Model identifier
- Domain detection result hash

**Cache key proposal:**
```
findings_cache_key = hash(
  document_content_hash,
  agent_definition_hash,
  model_id,
  domain_detection_hash
)
```

---

## Cache Hit Rate Improvement Estimates

| Change | Current Hit Rate | Projected Hit Rate | Token Savings |
|--------|-----------------|-------------------|---------------|
| BSC-1: Content-addressed OUTPUT_DIR | 0% | 60-80% | 21K/run |
| BSC-2: Content-addressed temp files | 0% | 70-90% | 1.5K/run |
| BSC-3: Pre-fetch scratch area | N/A | N/A | 10-15K/run |
| BSC-4: Cross-session findings cache | 0% | 30-50% | 96K/repeat-run |
| BSC-5: Incremental re-run | 0% | 80%+ | 384K/incremental |

**Total potential savings:** ~520K tokens for a user who reviews a document, fixes issues, and re-runs. This is a 70%+ reduction from the current ~750K token spend for review-fix-review cycle.

---

<!-- flux-drive:complete -->
