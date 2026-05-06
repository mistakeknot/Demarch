---
artifact_type: plan
bead: sylveste-3xl3.1
stage: plan
date: 2026-05-06
prd: docs/prds/2026-05-06-flux-explore-teams-synthesis-debate.md
brainstorm: docs/brainstorms/2026-05-06-flux-explore-teams-brainstorm.md
review_synthesis: docs/research/flux-review/flux-explore-teams-brainstorm/2026-05-06-synthesis.md
---

# Implementation Plan: flux-explore --teams (Synthesis-Debate Mode)

Sequenced execution plan for sylveste-3xl3.1 — features F1 through F6. Probes (F1) gate everything else; F2-F5 are the production code path; F6 is the empirical signal that decides whether `--teams` ships.

## Sequencing

```
F1 (probes) → gate → { F2, F3 } parallel → F4 → F5 → F6 → land
                ↓
         BLOCKING if probes surface design-breaking finding
```

- **F1 must finish before F2-F6.** If mailbox topology probe returns `star`, F4's blind-R1 design needs redesign; if TaskCompleted is post-only, F4's round cap moves to prompt-level only; if cost attribution is lead-only, F5's spawn-time session-ID capture path is required.
- **F2 and F3 can run parallel** (different files, no shared state).
- **F4 depends on F3** (uses team spawn helper) and on F1 probe outcomes (round-cap mechanism).
- **F5 depends on F4** (uses transcript path) and on F1 cost-attribution probe.
- **F6 depends on F2+F3+F4+F5** (needs end-to-end teams path runnable).

## File Map

| Path | Status | Purpose |
|------|--------|---------|
| `interverse/interflux/commands/flux-explore.md` | modify | Add `--teams` flag parsing in Step 0; replace Step 4 synthesis dispatch with branch on `teams_available` |
| `interverse/interflux/scripts/teams_detect.sh` | create | F2: env+version+runtime detection helper |
| `interverse/interflux/scripts/cluster_specs.py` | create | F3: max-distance cluster algorithm |
| `interverse/interflux/scripts/team_synthesize.py` | create | F4+F5: orchestrator + author + debate driver + cost capture + transcript writer |
| `interverse/interflux/scripts/benchmark_synthesis.py` | create | F6: subagent vs teams A/B harness + reviewer scoring |
| `interverse/interflux/scripts/cost_capture.sh` | create | F5: per-teammate session-cost aggregation (used by team_synthesize.py) |
| `docs/research/flux-explore-teams-probes/2026-05-06-mailbox.md` | create | F1: probe verdict |
| `docs/research/flux-explore-teams-probes/2026-05-06-task-completed.md` | create | F1: probe verdict |
| `docs/research/flux-explore-teams-probes/2026-05-06-cost-attribution.md` | create | F1: probe verdict |
| `interverse/interflux/tests/test_cluster_specs.py` | create | F3 unit tests (max-distance + audit + rebalance) |
| `interverse/interflux/tests/test_teams_detect.sh` | create | F2 detection tests with stubbed `claude --version` |

## Feature 1: Pre-Implementation Probes (sylveste-3xl3.1.4)

**Goal:** Three probe verdicts on disk before any production code lands. If any probe blocks, redesign — do not implement.

### F1.1: Mailbox topology probe
1. Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in a scratch directory.
2. Spawn Claude Code with a prompt: "Create a 3-teammate test team. Have teammate A post 'PROBE-MARKER-A' to the mailbox. After A posts, ask teammates B and C if they see the message — without you (the lead) intervening. Report YES/NO and the path the message took."
3. Inspect: did B and C see the message directly? If lead had to relay → star topology.
4. Write verdict + transcript excerpt to `docs/research/flux-explore-teams-probes/2026-05-06-mailbox.md` with frontmatter `probe: mailbox` and verdict `mesh | star | inconclusive`.

### F1.2: TaskCompleted authority probe
1. Read v2.1.32+ release notes / docs (`https://code.claude.com/docs/en/hooks#taskcompleted`).
2. If docs are explicit → record verdict from docs.
3. If ambiguous → write a TaskCompleted hook that returns exit code 2 ("reject"); spawn a 2-task team; check whether second task creation was blocked.
4. Verdict: `pre-veto | post-only | unknown`. Record at `docs/research/flux-explore-teams-probes/2026-05-06-task-completed.md`.

### F1.3: Cost attribution probe
1. Spawn a parent Claude Code session (capture session ID).
2. From parent, spawn a subagent that does a Sonnet call (capture child session ID).
3. Run `interstat session-cost --session=<parent-id>` and check whether output total includes child cost.
4. Verdict: `aggregated | lead-only | unknown`. Record at `docs/research/flux-explore-teams-probes/2026-05-06-cost-attribution.md`.

### F1.4: Ad-hoc teammate spawn probe (P2-with-P0-tail from plan review)
The brainstorm rejected fd-* file reuse and committed to ad-hoc generated debater prompts. The agent-teams docs primarily describe spawn from subagent definition files. Verify ad-hoc spawn works before F3 commits to it.

1. Set up a 1-teammate ad-hoc spawn: orchestrator-lead receives a generated prompt (no `.claude/agents/*.md` file underlying it), spawns one teammate from that prompt.
2. Confirm the teammate runs at all (responds to a "echo PROBE-MARKER" prompt).
3. Verdict: `ad-hoc-supported | definition-file-required | unknown`. Record at `docs/research/flux-explore-teams-probes/2026-05-06-ad-hoc-spawn.md`.
4. **If `definition-file-required`:** F3 fallback path is to write generated debater prompts to ephemeral `.claude/agents/td-debate-{slug}-cluster-{N}.md` files (the `td-` prefix marks them as transient/team-debate, distinct from `fd-`), spawn from those files, then delete after run. This adds one step to F3.2 but preserves the design.

### F1 acceptance gate
- All four probe docs exist with frontmatter + verdict.
- If verdicts surface a design-breaking finding (mailbox=star AND no degraded design accepted, OR TaskCompleted=post-only AND prompt cap unverifiable, OR ad-hoc spawn fails AND definition-file fallback rejected), pause sprint, surface to user, do not advance.
- Otherwise: proceed to F2/F3.

## Feature 2: Detection + Fallback (sylveste-3xl3.1.5)

**Goal:** `interverse/interflux/scripts/teams_detect.sh` returns 0 (available) or 1 (unavailable) and writes `teams_status` to stdout.

### Steps
1. Create `scripts/teams_detect.sh` (executable):
   ```bash
   #!/usr/bin/env bash
   # teams_detect.sh — exit 0 if --teams available, 1 otherwise.
   # Stdout: one of "available" | "disabled" | "version_too_old" | "version_unparseable".
   set -u
   if [[ "${CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS:-0}" != "1" ]]; then
       echo "disabled"; exit 1
   fi
   v=$(claude --version 2>/dev/null | awk '{print $NF}')
   if [[ -z "$v" || ! "$v" =~ ^[0-9] ]]; then
       echo "version_unparseable"; exit 1
   fi
   if [[ "$(printf '2.1.32\n%s\n' "$v" | sort -V | head -1)" == "2.1.32" ]]; then
       echo "available"; exit 0
   fi
   echo "version_too_old"; exit 1
   ```
2. Modify `commands/flux-explore.md` Step 0 to parse `--teams`. Set `TEAMS_REQUESTED=true|false`.
3. Modify Step 4 (Synthesize) entry to:
   - If `!TEAMS_REQUESTED`: existing single-Sonnet path (no change).
   - If `TEAMS_REQUESTED`: run `teams_detect.sh`. If exit=1, log notice, set `teams_fallback=detection`, fall through to subagent path. If exit=0, proceed to F3+F4 path.
4. Synthesis frontmatter writer: ensure exactly one of `teams_used | teams_fallback:detection | teams_fallback:runtime_failure | teams_fallback:divergent_clusters` is written when `TEAMS_REQUESTED`.

### F2 tests (`tests/test_teams_detect.sh`)
- `claude` stubbed to return `2.1.31` → exit 1, stdout `version_too_old`.
- `claude` stubbed to return `2.1.32+build.5` → exit 0, stdout `available` (sort -V handles the suffix).
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` → exit 1, stdout `disabled`.
- `claude` stubbed to return `garbage` → exit 1, stdout `version_unparseable`.
- `claude` not on PATH → exit 1, stdout `version_unparseable` (graceful — guard against `set -u` empty-var early-exit).

### F2 no-regression regression test (P1 from plan review)
- Capture pre-change baseline: run existing `/interflux:flux-explore` on a small spec set without `--teams`. Save synthesis output + frontmatter keys + file structure to `tests/baseline-flux-explore-no-teams.txt`.
- Post-change check: same invocation without `--teams` → diff against baseline must be empty (frontmatter keys + synthesis path + file shape unchanged). Any diff fails the test. This is the "byte-identical" promise from PRD F2 AC #5; without this check, that AC ships as code-level only.

## Feature 3: Cluster Algorithm + Team Spawn (sylveste-3xl3.1.6)

**Goal:** `cluster_specs.py` partitions specs into 3 clusters maximizing across-cluster centroid distance, with audit + rebalance. Team spawn helper is a thin wrapper that takes the 3 clusters and produces 5 named teammates.

### F3.1 — `cluster_specs.py`
1. Input: list of spec JSON paths or pre-loaded dicts (each has `source_domain`, `focus`, `expected_isomorphisms`).
2. Build embedding for each spec by concatenating `source_domain + focus + expected_isomorphisms` and using a **lightweight bag-of-words / character-trigram cosine** as the distance function. (Avoid loading a heavy embedding model — ~12 specs is small enough that BoW cosine is sufficient signal for cluster separability. If experience shows otherwise, swap in a sentence-transformer call as a follow-up — bead-tracked, not now.)
3. Algorithm: farthest-point sampling for 3 cluster seeds (pick one at random; pick second as max-distance from first; pick third as max-min-distance from {first, second}); assign remaining specs to the seed they are closest to.
4. **Audit:** compute pairwise centroid distances for the 3 clusters. If `min(pairwise_centroid_distance) < threshold` (default 0.30, configurable), return `{"status": "divergent_clusters_too_close", "reason": "..."}` and let the caller fall back to subagent path.
5. **Always log centroid distances (P2 from plan review).** Print pairwise centroid distances and cluster sizes to stderr on every run regardless of pass/fail. This makes the threshold observable from the first smoke run, so calibration is data-driven rather than after-the-fact-on-failure-only.
6. **Rebalance:** if any cluster has < 3 specs, attempt rebalance by reassigning the largest cluster's outliers (highest within-cluster distance) to the smallest cluster, while keeping cluster identity. If rebalance keeps any cluster < 3 after one pass, return `{"status": "degraded_to_2_clusters", ...}` so the team spawns 4 teammates instead of 5.

### F3.2 — Team spawn helper (in `team_synthesize.py`)
1. Take 3 cluster outputs from F3.1.
2. Build 5 teammate prompts:
   - **Orchestrator-lead:** "Coordinate a 2-round debate between {debater names}. Mailbox routing only. Do NOT write the synthesis. After Round 2, hand the persisted transcript to the author."
   - **Author:** "Read the transcript at {transcript_path}. Write a synthesis with ≥3 distinct cross-domain isomorphisms each citing two source domains, and a mandatory 'Unresolved tensions' section. Do not infer beyond the transcript."
   - **3 × Debater:** for each cluster, prompt cites the cluster's specs by `name + source_domain + expected_isomorphisms` and instructs Round-1 blind commit.
   - **Questioner:** "You issue challenges only. No candidates. After Round 1 visibility opens, post one challenge to each debater (round-robin)."
3. Spawn the 5 teammates via Claude Code agent-teams API. Capture per-teammate session IDs into `team_session_ids.json` for F5 cost capture.
4. If spawn API returns error → write `teams_fallback=runtime_failure` to frontmatter; fall through to subagent path.

### F3 tests (`tests/test_cluster_specs.py`)
- 9 specs from 3 widely-separated domains → 3 balanced clusters; centroid distances above threshold.
- 9 specs all from biology → audit returns `divergent_clusters_too_close`.
- 7 specs from 3 domains (2-2-3 distribution) → rebalance; final clusters ≥ 3 each.
- 5 specs across 2 domains → returns `degraded_to_2_clusters`; downstream spawns 4 teammates.

## Feature 4: Debate Protocol + Transcript (sylveste-3xl3.1.7)

**Goal:** Run the 2-round protocol with blind R1, replies-first R2, refuse-to-commit fallback, and persisted transcript. Round cap is prompt-level canonical (with TaskCompleted as belt-and-braces if F1.2 verdict was `pre-veto`).

### F4.1 — Round 1 (blind state)
1. Orchestrator opens by sending a "Round 1: blind state" prompt to each debater simultaneously.
2. Mailbox visibility for Round-1 messages is gated: orchestrator does NOT broadcast Round-1 posts to peers. Each debater commits their candidates without seeing peers.
3. Each debater post must contain at least one named falsifiable claim of form "Domain-X-pattern P maps to Domain-Y-pattern Q via mechanism M, falsified by observation O." Orchestrator validates form before opening Round 1.5; if a post is malformed, send back one revision request.

### F4.2 — Round 1.5 (challenges)
1. Orchestrator opens mailbox visibility.
2. Issue pre-assigned round-robin challenges (A→B, B→C, C→A); questioner challenges all three.
3. Each challenge must reference the target debater's claim by name.

### F4.3 — Round 2 (replies first)
1. Each debater is prompted: "Reply to every Round-1 challenge directed at you. Only after all challenges have a reply may you propose new combinations or refinements."
2. Orchestrator gates Round-2 closure: every Round-1 challenge must have either a reply or be explicitly listed as orphaned in the debater's Round-2 post.
3. **TaskCompleted backup (if F1.2=pre-veto):** install a hook that vetoes Round-3+ task creation. If F1.2=post-only, skip the hook and rely on prompt-level cap.

### F4.4 — Refuse-to-commit fallback
1. After Round 2 ends, parse the transcript for isomorphism mechanism mentions per debater.
2. Compute coverage: count distinct mechanisms cited by ≥2 debaters.
3. If `mechanisms_with_2_plus_support == 0`: author writes a stub synthesis with content "no fix; clusters incompatible" + the per-cluster Round-2 candidates as appendix. Frontmatter: `teams_fallback=divergent_clusters`. Then fall through to subagent path for the actual synthesis (so the run still produces a usable doc).

### F4.5 — Transcript persistence (path-only author handoff enforced)
1. Orchestrator appends every mailbox event to `docs/research/flux-explore-debates/{slug}/transcript.md` with timestamps + sender + recipient(s).
2. Transcript write happens **before** author is invoked.
3. **Path-only handoff (P1 from plan review):** the author's spawn prompt receives `transcript_path` as the ONLY input — not transcript content. The orchestrator's outbound message to the author is asserted to contain only the path string and a "do not paste transcript here; read from disk" instruction. Author reads from disk via Read tool. This converts the integrity rule from documented to enforced.
4. Synthesis frontmatter contains `transcript: <relative_path>` linking to the persisted file.

### F4 acceptance evidence
- Smoke run on the existing `flux-explore-teams-brainstorm-{adjacent,distant}.json` spec sets: 5 teammates spawn, 2 rounds complete, transcript written, synthesis produced. Output committed to `docs/research/flux-explore-debates/2026-05-06-smoke/`.

## Feature 5: Multi-Isomorphism Synthesis + Cost Capture (sylveste-3xl3.1.8)

### F5.1 — Author prompt + acceptance check
1. Author's spawn prompt requires output sections: "Cross-Domain Isomorphisms" (≥3), per-isomorphism "Source Domains" (exactly 2), "Mechanism", "Mapping to Target", and final mandatory "Unresolved Tensions".
2. Post-write check (in `team_synthesize.py`): parse the synthesis MD; count `## Cross-Domain Isomorphism N:` headings; verify `## Unresolved Tensions` heading exists. If <3 isomorphisms or missing section: log warning, set frontmatter `synthesis_quality_check=fail`, do NOT silently fix — surface to caller.

### F5.2 — Cost capture
1. At spawn time, record each teammate's Claude Code session ID into `team_session_ids.json`.
2. After Round 2 completes (regardless of synthesis vs fallback path), invoke `scripts/cost_capture.sh team_session_ids.json`:
   - **If F1.3 verdict = `aggregated`:** call `interstat session-cost --session=<lead-id>` and trust the parent-aggregated total.
   - **Else (lead-only OR unknown):** call `interstat session-cost --session=<id>` per teammate and sum.
3. **Transient-empty handling (P1 from plan review).** Per-teammate query may return zero rows because the teammate's session log hasn't flushed yet. `cost_capture.sh` logic:
   - For each teammate session, query interstat. If rows present → add to total.
   - If rows missing for ANY teammate after one retry with 5-second grace window → mark run as `synthesis_cost_usd: incomplete` and write `cost_attribution_gap: teammate <id> log not flushed`. Do NOT sum what's available and present it as final — this is the silent understate path the brainstorm review flagged.
   - If interstat query itself errors (not just empty) → also `incomplete` with the error reason.
4. Pre-flight cost preview: before team spawn:
   - Compute estimate: `teammate_count × estimated_per_session × expected_rounds`.
   - **TTY detection (P2 from plan review):** if `[ -t 0 ]` (interactive), print preview and sleep 3 sec (Ctrl-C window). If non-interactive (subagent calling), skip the sleep entirely. Env var `INTERFLUX_TEAMS_PREVIEW_SLEEP=0` overrides to skip.
   - Always log the estimate to stderr regardless of TTY.

## Feature 6: A/B Benchmark Harness (sylveste-3xl3.1.9)

### F6.1 — `benchmark_synthesis.py`
1. Takes a target spec set (e.g., from a recent `flux-explore` run's `.claude/flux-gen-specs/{slug}-round-*.json` or this very brainstorm's adjacent+distant spec set).
2. Runs subagent synthesis (existing path) on the spec set; captures synthesis doc + token cost.
3. Runs teams synthesis (new path) on the same spec set; captures synthesis doc + per-teammate aggregated cost.
4. **Reviewer with anti-position-bias (P2 from plan review).** Spawn the Sonnet reviewer agent twice with order swapped:
   - Run 1: synthesis labels are A=subagent, B=teams.
   - Run 2: synthesis labels are A=teams, B=subagent.
   Average the two scores (or use as cross-check — disagreement on verdict between runs flags the comparison as `inconclusive`).
   Rubric prompts (each run):
   - Count distinct cross-domain isomorphisms named.
   - Count those with two-domain support cited.
   - Note presence and content of unresolved-tensions section.
   - Identify any isomorphism present in one but not the other.
5. Writes comparison report to `docs/research/flux-explore-teams-benchmarks/{slug}/{YYYY-MM-DD}-comparison.md` with: scores from both runs, average, token totals, verdict (`teams-wins | subagent-wins | tie | inconclusive`). Flag `inconclusive` when the two runs reach different verdicts.

### F6.2 — Run the benchmark
1. Pick benchmark target: the existing `flux-explore-teams-brainstorm-adjacent.json` + `-distant.json` spec sets (10 specs total) — already on disk from the brainstorm review run, no extra generation cost.
2. Execute `benchmark_synthesis.py` with these specs.
3. Read the verdict; record into `bd note` on this bead.

## Test Strategy

- **Unit tests:** F2 (detect), F3 (cluster) — small Python/bash test files. Run via `pytest interverse/interflux/tests/` and `bash interverse/interflux/tests/test_teams_detect.sh`.
- **Smoke test:** F4 acceptance evidence (one full teams-mode run on real specs).
- **Benchmark:** F6 is itself the empirical test of the whole feature's value proposition.
- **Fallback paths:** verify each fallback writes the correct `teams_fallback` frontmatter — `disabled`, `version_too_old`, `runtime_failure`, `divergent_clusters` — by stubbing inputs.

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| F1 probes block (mailbox=star) | Plan documents redesign path: lean into star with strict no-paraphrase relay rule; pause sprint, file follow-up bead. |
| Agent-teams API spec drifts | Frontmatter signal `teams_fallback=runtime_failure` keeps users running; alert on aggregated rate of fallback. |
| Embedding cosine signal too weak for clustering | F3 audit with permissive threshold catches degenerate clusters; threshold tightened only after observed failures. |
| Cost attribution probe returns `unknown` | Assume lead-only (worst case for safety): always sum per-teammate; switch to parent-aggregation later if probe re-runs and confirms. |
| F6 verdict = `subagent-wins` or `tie` | This IS the desired empirical signal — `--teams` does not ship as default; opt-in remains. Bead 3xl3.1 still closes (acceptance criteria = measurement happened, not "teams won"). |

## Lessons-Learned Hooks

If F6 verdict is `teams-wins`: file follow-up bead to make `--teams` the default for design brainstorms (over-tracks with synthesis), opt-out flag instead of opt-in. This is currently scoped out (non-goal) and only revisited on positive empirical signal.

If F6 verdict is `subagent-wins`: file `bd compound` doc capturing why the experiment failed (anchoring at debater level? cluster-distance too coarse? round cap too tight?) for future agent-teams iterations.
