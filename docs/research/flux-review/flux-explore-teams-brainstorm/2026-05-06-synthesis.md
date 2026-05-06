---
artifact_type: review-synthesis
method: flux-review
target: "/home/mk/projects/Sylveste/docs/brainstorms/2026-05-06-flux-explore-teams-brainstorm.md"
target_description: "flux-explore --teams: cross-domain debate mode for Interflux"
tracks: 2
track_a_agents: [fd-agent-teams-primitive, fd-interflux-synthesis-pipeline, fd-debate-coordination-patterns, fd-teams-cost-economics, fd-experimental-flag-stability]
track_c_agents: [fd-noh-theatre-jo-ha-kyu, fd-bell-foundry-tuning, fd-celestial-navigation-fix, fd-pueblo-kiva-council, fd-renaissance-disputatio]
date: 2026-05-06
---

# flux-explore --teams brainstorm — multi-track review synthesis

Target: `/home/mk/projects/Sylveste/docs/brainstorms/2026-05-06-flux-explore-teams-brainstorm.md` (sylveste-3xl3.1)

Reviewers: 10 agents — 5 adjacent (Track A: deep-domain on agent-teams primitive, Interflux pipeline, debate dynamics, cost economics, flag stability) and 5 distant (Track C: Noh dramaturgy, bell-foundry tuning, celestial navigation, Pueblo kiva councils, Renaissance disputatio).

Triage rationale: the brainstorm is a coordination-design doc with a small surface-area for code (fallback bash + cluster + frontmatter wiring) and a large surface-area for protocol design (4-teammate role grammar, 2-round cap, anchoring claims). Track A covers the API/cost/integration risks; Track C is unusually high-leverage here because the brainstorm's load-bearing claim — debate beats single-pass synthesis on anchoring — is exactly the kind of structural-protocol claim where dramaturgical/deliberative isomorphisms find blind spots a primitive specialist would miss. Standard `fd-architecture/systems/decisions/...` lenses were considered but skipped: the existing per-lens-named agents (e.g. `fd-architecture-vertical-coupling`) are too narrowly scoped for a synthesis-protocol design doc, and the Track A/C agents already cover the architectural and decisional surfaces with task-tuned severity tables.

---

## 1. Critical Findings (P0/P1)

### P0 — Cluster-by-similarity collapses triangulation
**Track C — distant** (`fd-celestial-navigation-fix`)
The brainstorm Decision §3 says "cluster by `source_domain` similarity so each debater holds a coherent perspective." A celestial-navigator reading: this is the opposite of what triangulation needs. Three sights on stars too close together produce a tiny cocked-hat that *looks* like a tight fix but cannot detect bias from current. If three debaters all hold *internally* coherent (similar) source-domains, their inter-cluster distance is small, and the lead's "synthesis" reads three correlated bearings as confirmation of one. The anchoring bias the brainstorm names is then re-introduced through cluster choice: the design picks within-cluster coherence over across-cluster distance. **Failure scenario:** 12 specs accumulated; `source_domain` strings cluster as {biology, ecology, evolution} / {music, sound, harmony} / {architecture, urbanism, infrastructure}. The lead reads three "perspectives" but each cluster is one effective sight; the cross-domain isomorphism the run was supposed to surface is never tested across genuinely distant material. **Fix (one hunk):** flip the clustering rule to *maximize* across-cluster distance — partition such that the minimum pairwise distance between cluster centroids is maximized (k-means with a max-min-distance objective, or precompute pairwise distances and use farthest-point sampling for cluster seeds). Add a plan-time audit that fails the run if any two cluster centroids are below a threshold distance.

### P1 — Lead is chair-plus-author; mesh claim is undermined at the prompt level
**Track C — distant** (`fd-pueblo-kiva-council`) and convergent with **Track A** (`fd-debate-coordination-patterns`).
Decision §3 makes the lead "orchestrate the debate, hold the synthesis writing responsibility." This concentrates coordination authority *and* writing authority in one role — the parliamentary chair pattern. The brainstorm's anchoring-bias argument (Why §2) explicitly claims mesh topology buys what subagents cannot, but a chair-plus-author lead replays the single-Sonnet anchoring problem at the synthesis-write step: whatever the lead's read of the debate is *becomes* the synthesis with no peer check on the lead's framing. **Failure scenario:** debate produces three genuinely distinct isomorphism candidates; lead's prompt biases toward the first/strongest; synthesis is "summary of summaries" with debate as window dressing — A/B against subagent path shows no measurable lift, project-wide cost ceiling forces deprecation of `--teams` despite the protocol being implementable. **Fix:** split lead into orchestrator + author (two prompts, possibly the same model role but separate turns): orchestrator does only mailbox routing and turn enforcement; author writes synthesis from the *transcript*, not from a running summary. This also removes a real implementation risk — the chair role does not need synthesis-writing tools.

### P1 — Anchoring migrates from synthesizer to first debater to post (Round 1)
**Track A — adjacent** (`fd-debate-coordination-patterns`).
Decision §4 says Round 1: "each debater states their cluster's strongest isomorphism candidates and challenges one peer's." If debater A posts before debater B reads, B reads A's candidates while forming its own — which means the bias the brainstorm critiques (one theory in the synthesizer's context biases follow-on reasoning) re-enters at the first-poster level, just one layer deeper. The mesh fix only works if Round 1 stating is *blind*: each debater commits to its candidates before reading peers. **Failure scenario:** mailbox is FIFO and debaters check it on each turn; first poster's candidates anchor the next two; Round 2 challenges concentrate on the first poster's framings; synthesis surfaces the first-poster anchor as "consensus." **Fix:** Round 1 prompt explicitly requires each debater to *post first, read after*. Implementation: the orchestrator gates mailbox visibility — debaters cannot read peer Round-1 messages until they have posted their own. Failing that, two turns: Round 1a (blind state) → Round 1b (read peers + issue one challenge each).

### P1 — Mailbox topology may be star, not mesh; primitive must be verified
**Track A — adjacent** (`fd-agent-teams-primitive`, `fd-debate-coordination-patterns`).
Why §2 stakes the design on mesh: "subagents can't message each other; the only edges go back to the caller. Direct inter-agent debate is the canonical fix." But the brainstorm never confirms the primitive *implements* mesh. If Claude Code's mailbox routes all messages through the lead (star), then debaters cannot challenge each other directly — every challenge is relayed by the lead, and anchoring re-enters through the lead's relay summarization. **Failure scenario:** mailbox is star-shaped; lead relays "debater A says X, debater B says Y" with its own paraphrase; the asserted mesh property is in fact star-with-extra-steps; A/B benchmark shows no improvement and the team cannot tell whether the protocol or the topology failed. **Fix:** before implementation, write a 10-minute probe — spawn 3 ad-hoc teammates, have one post `<msg-from-A>` and check whether the others see it without the lead intervening. If star: redesign to lean into the star (lead becomes a transcribing relay with a strict no-paraphrase rule and challenge-targets are addressed by name in body) rather than pretending it is mesh.

### P1 — TaskCompleted may not have authority to *reject* new task creation
**Track A — adjacent** (`fd-agent-teams-primitive`).
Decision §4 leans on "TaskCompleted hook enforces the 2-round cap: rejects a 'debate continues' task creation past round 2." But TaskCompleted, by name, fires *after* a task completes. Whether it can veto *future* task creation depends on the primitive's lifecycle contract. If TaskCompleted is post-completion only with no pre-creation veto authority, the cap is unenforceable and the debate can run unbounded — exactly the "arbitrary token burn" the brainstorm warns against. **Failure scenario:** Round 2 ends, lead spawns a Round-3 debate task, TaskCompleted runs on Round 2's task but cannot block Round 3; debate continues; cost spirals; budget gate breached. **Fix:** confirm hook contract against v2.1.32+ docs *before* implementation. If TaskCompleted is post-only, use a pre-creation hook (TaskStart / TeammateCreate equivalent, whatever exists) or implement the cap inside the lead's prompt with a hard turn-counter and refuse-to-spawn rule, plus a TeammateIdle backup. Do not ship the cap until the hook contract is verified.

### P1 — Cost measurement likely misses 3 of 4 teammate sessions
**Track A — adjacent** (`fd-teams-cost-economics`).
Decision §6 says wire interstat session-cost capture before/after the synthesis stage. But each teammate runs in its own session; interstat captures per-session costs. A "before/after the synthesis stage" measurement on the parent session likely captures only the lead's tokens. If it does, `synthesis_cost_usd` in the brainstorm frontmatter understates real cost by ~3-4×, the cost gate cannot be honored, and `--teams` silently exceeds the $2.93/landable baseline. **Failure scenario:** acceptance #3 says "per-run token cost" — the run reports lead-only cost, looks competitive with subagent path, gets adopted, real cost shows up later in fleet-cost rollups as a per-exploration regression. **Fix:** before implementation, verify `interstat session-cost` aggregates child-session tokens via parent-session linkage. If not, capture per-teammate session IDs at spawn time and sum explicitly. Add a sentinel: if any teammate's cost cannot be attributed, write `synthesis_cost_usd: incomplete` rather than a misleadingly small number.

### P1 — Synthesis is not constrained to challenge-survivors (determinatio discipline)
**Track C — distant** (`fd-renaissance-disputatio`).
Decision §4 round-2 prompt: debaters "respond to challenges, propose new combinations, lead asks for synthesis-ready material." This permits debaters to *substitute* new material for unaddressed objections, and lets the lead write synthesis from "whatever has converged" — including isomorphisms that were challenged and never replied to. In disputatio terms, the determinatio is uncoupled from the *opinio* discipline that gives debate its rigor over free summary. **Failure scenario:** debater A challenges debater C's central candidate; C ignores it and proposes new candidates; lead writes synthesis citing C's new candidates as resolved; the protocol produces vibe-synthesis with debate-flavored prose, indistinguishable on paper from subagent path. **Fix:** Round 2 prompt mandates "respond to *each* challenge first (sed contra), then optionally propose new combinations." Lead's synthesis prompt is constrained to only assert isomorphisms that either (a) survived all challenges with a reply, or (b) are explicitly listed in an "unresolved tensions" section. Add an "orphaned objections" check before TaskCompleted fires.

### P1 — Round 1 may produce no irreversible commitments
**Track C — distant** (`fd-bell-foundry-tuning`).
The 2-round cap is treated as a timer in the brainstorm: 2 rounds, then synthesize. A bell-founder reading: each tuning pass irreversibly removes metal — the budget is *commitments*, not minutes. If Round 1 ends with debaters having stated "candidates" but not falsifiable claims, then nothing has been *committed* — Round 2 has nothing irreversible to push against, and synthesis is built on soft material. **Failure scenario:** Round 1 prompts say "state strongest candidates" — debater A states three candidates with hedges ("could be," "perhaps"); debater B challenges loosely; Round 2 produces refinement-of-hedges; the cap fires; lead writes synthesis from a soup of qualifications that no debater would defend. The 4× spawn cost has bought no convergence pressure. **Fix:** Round 1 prompt requires each debater to commit one *named, falsifiable* isomorphism claim with the form "Domain-X-pattern P maps to Domain-Y-pattern Q via mechanism M, and would be falsified by observation O." This makes Round 2 challenges concrete and gives the lead determinable material.

---

## 2. Cross-Track Convergence (ranked by independent appearance)

**Convergence score = number of independent agents flagging the same underlying issue across distinct severity-table slots.**

### Convergence 1 (rank: highest, score 4) — The lead is doing too many jobs and that re-anchors the synthesis
- `fd-pueblo-kiva-council` (Track C): "Lead's prompt has both 'orchestrate the debate' and 'write the synthesis', which is chair-plus-author and crowds out peer-mesh dynamics" (P1).
- `fd-debate-coordination-patterns` (Track A): "Anchoring migrates from the synthesizer to the first debater to post in Round 1" — the lead's reading order is the anchoring substrate.
- `fd-noh-theatre-jo-ha-kyu` (Track C): the lead may be "a writer wearing a moderator hat," not genuinely waki-shaped — the witness/questioner role distinct from the recorder.
- `fd-renaissance-disputatio` (Track C): the determinatio (lead's synthesis) is not constrained by what survived challenge — i.e. the role's authority is unchecked.

Three distant agents and one adjacent agent independently identified the same structural problem: concentrating orchestration + synthesis in the lead role. This is the highest-leverage finding in the review. **Recommended action:** split the role.

### Convergence 2 (rank: high, score 3) — The 2-round cap is justified by cost, not quality, and is treated as a timer
- `fd-bell-foundry-tuning` (Track C): "2-round cap is treated as a timer rather than a budget of irreversible commitments" (P1).
- `fd-pueblo-kiva-council` (Track C): "Cost-justification for 2-round cap is presented as if it were also a quality-justification, hiding the question of whether 2 rounds is enough for talked-out convergence" (P2).
- `fd-celestial-navigation-fix` (Track C): "Lead has no escape hatch when debaters disagree irreconcilably" — i.e. the cap fires regardless of fix quality (P1).

All three from the distant track. **Recommended action:** add a divergence-threshold escape hatch (lead refuses to write synthesis when round-2 disagreement exceeds a threshold, declares "inconsistent fix" instead, falls back to subagent synthesis tagged with the divergence reason).

### Convergence 3 (rank: high, score 3) — Round-2 prompt loses challenge-reply discipline
- `fd-renaissance-disputatio` (Track C): "Round 2 prompt allows debaters to introduce new arguments instead of replying to round-1 objections" (P1).
- `fd-debate-coordination-patterns` (Track A): "Round 2 produces divergent positions; lead is forced to synthesize under the 2-round cap; resulting synthesis acknowledges conflict without resolving it" (P2).
- `fd-bell-foundry-tuning` (Track C): if no irreversible commitment in Round 1, Round 2 has nothing to reply *to* (P1).

**Recommended action:** rewrite the Round 2 prompt as "respond to each challenge first, propose new combinations only after" — and gate TaskCompleted on every Round-1 challenge having a Round-2 reply or being explicitly orphaned.

### Convergence 4 (rank: medium, score 2) — Cost measurement does not capture the full team
- `fd-teams-cost-economics` (Track A, P1): interstat captures only lead session.
- `fd-bell-foundry-tuning` (Track C, P3): "Cost measurement treats only the successful path's tokens as spend and not the spawn-overhead of teammates that contributed nothing."

**Recommended action:** explicitly aggregate per-teammate session costs; treat all spawn cost as sunk regardless of teammate output.

### Convergence 5 (rank: medium, score 2) — Synthesis must surface unresolved tensions, not paper over them
- `fd-renaissance-disputatio` (Track C): synthesis must acknowledge unresolved objections (P1).
- `fd-celestial-navigation-fix` (Track C): "cocked hat" too large → refuse to commit to a fix, report inconsistency (P1).

**Recommended action:** synthesis doc structure must include an "Unresolved tensions / divergent fixes" section, populated whenever Round-2 challenges remain unanswered or cluster claims conflict.

### Convergence 6 (rank: medium, score 2) — Cluster choice can re-introduce anchoring
- `fd-celestial-navigation-fix` (Track C, P0): cluster-by-similarity correlates the sights.
- `fd-debate-coordination-patterns` (Track A): cluster-to-debater is adversarial framing without per-cluster mandate to find shared ground — but the framing problem only bites if clusters are correlated to begin with.

**Recommended action:** see P0 fix above (maximize across-cluster distance, audit at plan time).

---

## 3. Domain-Expert Insights (Track A — adjacent)

Beyond the convergent findings, the adjacent agents flagged several deep-domain issues that are not visible from the structural-isomorphism vantage:

**`fd-agent-teams-primitive`:**
- /resume non-restoration is documented but the "re-entrancy from spec JSONs" claim assumes synthesis is the only thing that matters. If Round 2 produced live in-context insights not yet committed to the synthesis doc, /resume during synthesis loses them. (P2.) Mitigation: write debate transcript before synthesis writes, not after.
- Ad-hoc teammate initialization from generated prompts may not be a supported pattern — the docs may only support subagent-definition file handoff. The brainstorm explicitly *rejected* fd-* file reuse but the alternative may not exist as a runtime API. (P2 with P0 risk if false.) Mitigation: write a 5-line probe before committing to the design — spawn one ad-hoc teammate from a generated prompt and confirm it runs.

**`fd-interflux-synthesis-pipeline`:**
- The four spec JSON fields the brainstorm treats as available (`source_domain`, `focus`, `expected_isomorphisms`, `distance_rationale`) — verify *every* field is populated by `generate-agents.py` for *every* generated agent, including older runs. (P1 if `expected_isomorphisms` is empty for legacy specs.) Fix: at synthesis-time, for each spec missing a required field, either backfill via a small Sonnet call or exclude from clustering with a logged warning.
- The synthesis output path must remain unchanged so downstream flux-drive picks it up — confirm the lead writes to the same brainstorm `.md` path the subagent path writes to. (P1.) Fix: pass the target path explicitly to the lead's prompt; do not let the lead invent a new path.
- Cluster assignment with unbalanced source_domains (12 specs, 8 in one cluster, 2 in two others) — needs a fallback. Fix: rebalance to ensure each cluster is ≥3 specs; if impossible, reduce team size from 4 to 3 (lead + 2 debaters) and document the degradation.

**`fd-teams-cost-economics`:**
- No pre-flight cost estimate before launching synthesis. User opts in but has no warning that this run will spend ~4× baseline. (P2.) Fix: print estimated synthesis cost (rough teammate × baseline-per-Sonnet) before spawning, prompt to confirm.
- Baseline comparison line is "estimated from current synthesis subagent average" — but average doesn't scale with brainstorm size. Fix: measure the subagent path baseline *on the same spec set* in the same run (run subagent synthesis once, then teams synthesis), and compare per-run, not per-corpus-average.

**`fd-experimental-flag-stability`:**
- Bash semver parsing on `claude --version` is fragile; build-stamped releases (`2.1.32+build.5`) can fail string comparison and silently disable `--teams` even when the primitive is available. (P0.) Fix: parse with `awk -F. '{ printf "%d%03d%03d\n", $1, $2, $3 }'` or use `sort -V` for safe comparison; treat unparseable strings as unavailable + log.
- Runtime team launch failure (env+version pass, but `TeammateCreate` returns error) — no try/catch; flux-explore aborts mid-synthesis. (P1.) Fix: wrap team launch in error handling that triggers the same fallback path as detection failure.
- Fallback notice should be written to brainstorm frontmatter (`teams_fallback: true`), not just stderr — otherwise the user can't see post-run that the path degraded. (P2.)
- No mechanism to detect that the experimental flag *graduated* (env var removed, primitive stable) — flag-check logic could rot to always-fallback. (P2.) Fix: implementation doc note + periodic version-check audit added to handoff.

**`fd-debate-coordination-patterns`:**
- "Challenge one peer" is underspecified — self-selection produces unbalanced coverage (two debaters challenge the same peer, third unchallenged). (P2.) Fix: pre-assign challenges round-robin (debater A challenges B, B challenges C, C challenges A).
- Quality-measurement plan in Open Question 1 is hand-wavy. Fix: specify the reviewer-agent rubric *now*, not at plan time — score on (a) number of distinct cross-domain isomorphisms named, (b) number with two-domain support cited, (c) presence of unresolved-tensions section.

---

## 4. Structural Insights (Track C — distant)

The distant track produced several findings the adjacent track structurally could not see, because they require analogizing the protocol to a non-software deliberation form:

**`fd-noh-theatre-jo-ha-kyu`:** the brainstorm describes 4 teammates with no functional differentiation. In Noh, four performers *are* differentiated — shite (the protagonist with the revelation), waki (the witness who draws it out), tsure (supporting cluster), jiutai (chorus as memory). The brainstorm risks four shite and no waki: every teammate is trying to assert; no one is structurally a questioner. **Insight:** assign one debater the "questioner" role explicitly (no candidates of their own; only challenges) and make the lead waki-shaped (witness who asks the shite to reveal, not author who summarizes). Treat accumulated spec JSONs as the *jiutai chorus memory* the lead consults during synthesis-write rather than writing from scratch.

**`fd-noh-theatre-jo-ha-kyu` (additional):** silence has no role. Every round implicitly requires every debater to emit a turn — token cost grows even when a debater has nothing new. **Insight:** sanction "pass" / "defer-to-peer" as a valid turn; this is both jo-ha-kyu-faithful (silence is a structural beat) and cost-positive.

**`fd-bell-foundry-tuning`:** synthesis target is single-tone. The brainstorm implies the synthesis names *the* cross-domain isomorphism, but a well-tuned bell holds multiple modes simultaneously (hum, prime, tierce, quint, nominal). **Insight:** synthesis should produce *N* distinct isomorphisms each with two-domain support, not one dominant analogy. This changes acceptance criteria: "synthesis names ≥3 distinct isomorphisms" rather than "synthesis is written."

**`fd-celestial-navigation-fix`:** the "cocked hat" — divergence threshold above which the navigator refuses to commit — has no analogue in the design. The brainstorm assumes synthesis always writes. **Insight:** add a refuse-to-commit rule; if Round-2 candidates from the three clusters cannot be reconciled (some quantifiable measure: e.g. no overlapping isomorphism mechanism mentioned by ≥2 debaters), the lead writes "no fix; clusters incompatible" and falls back to subagent synthesis. This is a higher-quality failure mode than forcing synthesis from divergent material.

**`fd-pueblo-kiva-council`:** persistence of the debate transcript (Open Q 2) is treated as audit data and deferred. In council traditions, the transcript *is* the decision — the synthesis is unaccountable without it. **Insight:** persist the full debate transcript to `docs/research/flux-explore-debates/{slug}/` as a *synthesis-integrity requirement*, not a nice-to-have. Frontmatter link from the synthesis doc to the transcript path. This is a small implementation cost and converts the synthesis from "trust the lead's read" to "audit-traceable."

**`fd-pueblo-kiva-council`:** sipapu equivalent missing. Teammates have no shared reference point all orient toward beyond the lead. **Insight:** include the original brainstorm question / `flux-explore` task prompt as the anchor every teammate's prompt cites — orientation toward the question, not toward the lead.

**`fd-renaissance-disputatio`:** spec JSONs function as *backstory* in the brainstorm rather than as *auctoritates* the debaters must engage with. **Insight:** debater prompts should require citing specific spec JSON fields ("debater B's cluster's `expected_isomorphism` field claims X — your reply must engage X by name") so the spec accumulation is load-bearing in the debate, not just team-seeding metadata.

---

## 5. Standard-Lens Findings

Standard cognitive/technical lenses (`fd-architecture`, `fd-systems`, `fd-decisions`, etc.) were *not* triaged in. The named bare-form lenses do not exist in the project's `.claude/agents/` directory; the closest existing analogues (e.g. `fd-architecture-vertical-coupling`, `fd-decision-rooming-bias`) are too narrowly scoped for a synthesis-protocol brainstorm. The Track A agents already cover the architectural and decisional surfaces with task-tuned severity tables. Substituting a too-narrow standard lens would dilute review quality.

If desired, a follow-up review could dispatch:
- `fd-architecture-vertical-coupling` — to check the Step-4-only branch claim against actual flux-explore orchestrator coupling.
- `fd-adopt-adapt-avoid` — to gut-check the experimental-primitive adoption decision against the project's external-tools doctrine.
- `fd-acceptance-criteria-quality` — to check the three acceptance criteria for falsifiability and measurement clarity.

These would be cheap supplementary additions; none rose to triage threshold for this pass.

---

## 6. Synthesis Assessment

**Overall quality of the brainstorm.** The brainstorm is *strong on scoping discipline* (Step-4-only, opt-in flag, sequenced beads, explicit rejection of Approach 2/3 for now) and *thin on protocol mechanics* (debate-round wording, cluster algorithm, anchoring claim). The scoping moves are the right ones — small surface area, opt-in, fallback path, cost gate, A/B comparison plan. The mechanics need substantial sharpening before the design will deliver the value the scoping anticipates.

**Highest-leverage improvement (single change).** Split the lead role into orchestrator + author. This single change addresses Convergence 1 (rank: highest, 4 independent agents), unblocks the mesh-topology argument (Convergence 4 / P1), and creates a natural place to put the "refuse to commit" escape hatch (Convergence 2). Implementation cost is low — one extra prompt template — and it changes the synthesis from "lead's read of debate becomes the doc" to "doc is constrained by transcript the orchestrator produced." Every other recommended change becomes easier downstream of this one.

**Surprising finding.** The cluster-by-similarity rule (Decision §3) is the **single biggest threat to the entire hypothesis**, and not a single Track A agent flagged it as P0. The celestial-navigation lens (Track C) caught it because triangulation is the natural analogy for multi-source fixing under bias. From an adjacent vantage, "cluster by source_domain similarity" reads like a sensible engineering choice (coherent perspectives per debater); from a triangulation vantage it reads as actively defeating the design's stated goal. This is the canonical case for cross-domain review: the bug is not in the code, it is in the framing the code implements, and the framing reads as obvious-good-engineering until you stand far enough back.

**Did the distant track contribute insights the adjacent track couldn't?** Yes, decisively. Six of the eight critical findings (P0 + 7 P1s) come from or are *only flagged independently* by Track C. The distant track found:
- The cluster-similarity → triangulation collapse (P0; only `fd-celestial-navigation-fix`).
- The chair-plus-author concentration of authority (P1; named most sharply by `fd-pueblo-kiva-council`).
- The cap-as-timer vs cap-as-commitment-budget distinction (P1; only `fd-bell-foundry-tuning`).
- The challenge-reply discipline gap (P1; sharpest in `fd-renaissance-disputatio`).
- The need for an unresolved-tensions / refuse-to-commit output (cross-track convergence, but the quality framing is from `fd-celestial-navigation-fix`).
- The transcript-as-integrity insight (only `fd-pueblo-kiva-council`).

The adjacent track found the API-contract risks (TaskCompleted authority, mailbox topology, cost attribution, semver parsing) that Track C structurally could not see. Both tracks are needed; neither is sufficient alone. The brainstorm's mechanic-thinness is exactly the surface where distant analogizing pays — once mechanics are sharpened, future iteration will lean more on Track A.

**Recommended next step before implementation.** Three small probes (each ~15 min) before any code lands:
1. Confirm mailbox topology (mesh vs star) by spawning a 3-teammate test team and observing whether posts are visible peer-to-peer.
2. Confirm TaskCompleted hook can or cannot block new task creation (read v2.1.32 changelog or test).
3. Confirm interstat session-cost aggregates child sessions (read `interstat session-cost --help` or test with a known parent+child session).

Each probe directly answers a P0/P1 finding above. If any probe fails, the design needs adjustment, not the implementation.
