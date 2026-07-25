---
artifact_type: melange-synthesis
method: flux-melange
target: "Brainstorm: fd-integration reviewer improvement (wire, ground, generalize) plus agent-registry extraction"
target_description: "docs/brainstorms/2026-07-16-fd-integration-improvement-brainstorm.md — two-track goal: pilot fd-integration into the interflux review pipeline (wire → ground → generalize) and extract a reviewer-agent identity registry"
goal: "Find the best architecture for how fd-integration gets its tracer evidence at review time, including alternatives not yet considered; score candidate shapes against the pilot-first/migrate-under sequencing and the hybrid hub+inference substrate already decided, and stress-test whether the agent-invoked recommendation survives contact with better alternatives."
weights: balanced
rounds_run: 3
halt_reason: DRY
total_fusions: 0
emergent_findings: 0
runtime: claude
date: 2026-07-17
---

# Flux-Melange Synthesis — fd-integration evidence architecture + registry extraction

**The eye of distance.** Three rounds (0–2), two base-lens assay rounds plus one probe round, halted DRY (novel-cluster rate fell 0.67 → 0.33; round 2 yielded no new clusters). Twenty-four findings, one refuted (f-003), twenty-three upheld. Zero fusions attempted, zero emergent. Ranking below is by **HEAT = novelty × risk.product**, re-scored from a fresh read of the merged ledger — not by severity, and not by the per-round triage estimates.

**Re-scoring note.** I lifted the identity-continuity cluster (f-004/f-006/f-012) from novelty 0 to 1: the triage scored them 0 because three lenses converged, but the specific mechanism — a bare `TEXT NOT NULL` trust column with no FK and a deliberately-twice-changed identity representation — is more than commodity knowledge; it is a named, load-bearing gap. Their risk.product stays at max (9). I confirmed f-003's refutation (the freshness-contract axiom over-reached: the tracer libs scanning live working-tree state is a design fact, not a defect relative to a diff that is itself the working tree). Everything else tracks the ledger scores within ±1.

**Headline finding.** The review's core question — *does the agent-invoked recommendation survive contact with better alternatives?* — resolves to **yes, but the brainstorm reached the right answer for incomplete reasons, and the strongest objection is not architectural at all.** Candidate (a) (agent-invoked, single shared entry script) survives on cost grounds, but two facts the brainstorm never engaged reshape the decision: (1) flux-drive **already** has an orchestrator-side pre-computation hook (Composer/`compose_dispatch`) that makes candidate (b) far cheaper than the brainstorm assumes (f-002), and (2) the deferral trigger for (b) — "revisit if a second evidence-based agent appears" — **fires inside this very plan**, because Track 2's registry is built to onboard exactly such agents (f-015/f-019). The recommendation should be reframed from "agent-invoked, revisit later" to "agent-invoked **behind a shared entry script whose signature already anticipates orchestrator injection**," so the (b) migration is a call-site swap, not a rewrite.

---

## 1. Novelty × Risk Frontier

The Pareto front on (novelty, risk.product) among upheld findings. Two leads: a **max-novelty / mid-risk** point and a **mid-novelty / max-risk** point. Severity shown FOR REFERENCE ONLY.

### Lead A — max novelty (3), mid risk (6): f-022 · HEAT 18

**Claim.** `interflux/scripts/flux-agent.py` is a *live* grant/promote/record registrar over `.claude/agents/fd-*.md` that already implements several of the exact registry verbs Track 2 proposes to build fresh (`promote`≈grant, `prune`≈attainder, `record`≈augmentation) — but the brainstorm names only "five files / four owners" and treats `.index.yaml` as inert data rather than this tool's live output.

**Lens.** fd-heraldic-registry (pre-modern heraldry / office-of-arms), round 1, STEER-WIDE probe.

**Risk decomposition.** blast_radius 2 × likelihood 3 = **6**. Blast is bounded (Track 2 is greenfield; the harm is duplicated effort and a sixth identity scheme, not a production outage). Likelihood is high (3): the brainstorm's own "Registry plugin boundary" open question gestures at absorbing `.index.yaml` as passive data, so it is actively on a path to re-implement a live tool's grant semantics without reconciling them.

**Why it leads.** This is the highest-novelty upheld finding in the run and it directly reframes Track 2's build-vs-extend decision. `flux-agent.py` keys on `name = f.stem` — a *fourth* bare-string identity scheme the brainstorm's fragmentation count omits. But note the counterweight from its own cluster: f-024 (same lens) verifies `flux-agent.py:274` only globs `.claude/agents/fd-*.md` (Project Agents), so it never sees plugin-shipped agents like fd-integration. "Just extend flux-agent.py" is therefore not a free lunch either — plugin-agent coverage is a scope-widening sub-task. The finding's value is that it forces the boundary question to be answered against a *live registrar* rather than against inert config.

*Severity (reference): P1.*

### Lead B — mid novelty (2), max risk (9): f-007 · HEAT 18

**Claim.** Directly verified by re-running the command: `git rev-parse --show-toplevel` from inside `interverse/intertrace` returns intertrace's own root, **not** the Sylveste root — confirming the exact P0 boundary case the brainstorm names (intertrace as a nested standalone repo) but never resolves in the design. A naive `.git`-boundary upward walk terminates here and never reaches `docs/companion-graph.json` or `docs/contract-ownership.md`.

**Lens.** fd-federation-discovery-generalization (workspace-root detection / config fallback), round 0.

**Risk decomposition.** blast_radius 3 × likelihood 3 = **9**. Blast is maximal: this is the "First Step (MANDATORY)" of the agent — if the hub docs 404, the agent has no grounding and the entire generalize stage silently degrades to prose review, which is the exact failure the brainstorm opens with. Likelihood is maximal: intertrace *is* a nested standalone repo (verified), so the boundary case is not hypothetical — it is the default topology for the pilot's own home repo.

**Why it leads.** Highest risk.product in the run, at real (2) novelty because it converts a named-but-unresolved requirement into a re-verified concrete failure with an exact terminating directory. It anchors a three-finding convergent cluster (f-007/f-008/f-009): the sibling `/intertrace` skill already passes an **unassigned** `$MONOREPO_ROOT` into all three tracer scans (f-009), meaning the silent-404 the brainstorm wants to fix already has a live, unaudited instance *in the codepath slated for fusion* — and f-008 shows Open Question 4's "reuse intersense-style detection" is miscategorized (intersense does domain classification, not root-finding).

*Severity (reference): P0.*

### Frontier interior (not on the front, but adjacent and load-bearing)

- **f-021** (novelty 3, risk 4, HEAT 12) — the *project*-key axis: `trust_feedback` keys on `(agent, project)` where `project = basename(git-toplevel)`, uncanonicalized. Two repos sharing a basename (fork, differently-nested clone) silently pool trust history. The registry track inventories only the agent axis. Max-novelty, and it opens a whole second identity namespace the design ignores.
- **f-009** (novelty 2, risk 6, HEAT 12) and **f-010** (novelty 2, risk 6, HEAT 12) sit just inside the front — the undeclared-`$MONOREPO_ROOT` instance and the severity-vs-confidence-tier label-space collision (interflux's P0–P3 severity slot vs. intertrace's P1–P3 *evidence-strength* scheme colliding in the same three-letter label space, with no separate carrier field for the confidence tier the brainstorm promises).

---

## 2. Top Fusions

**Zero fusions attempted; zero emergent findings.** (`fusion_stats: {attempted: 0, emergent: 0}`.)

The controller never issued a FUSE directive. Round 1's targeting chose PROBE-DISAGREEMENT (the f-002 ↔ f-015 tension) and STEER-WIDE (novel-cluster rate still ≥ 0.6), both of which pay off in *breadth* rather than *intersection*. The one place a fusion was structurally available — the tension between fd-evidence-substrate-architect (f-002: Composer precedent) and fd-qanat-delivery (f-015: second-consumer trigger) — was routed to an **adjudication pass** instead of a fusion lens. That adjudication (f-019/f-020) is the closest thing the run produced to an emergent finding, but by construction it introduces no new location or defect of its own (it inherits its parents' blind spots, per its own failure-mode declaration), so it is a reconciliation, not a fusion.

**Negative results (independent here, not fused):**

- **fd-evidence-substrate-architect × fd-qanat-delivery:** independent here. They target the same decision point ("Tracer invocation path") and were *adjudicated* (ruled compounding, not contradictory — see §5) rather than fused into a hybrid intersection-detector. A true fusion might have asked what a shape looks like that is *both* orchestrator-amortized (substrate axiom) *and* apportioned across contending consumers (qanat axiom) — e.g., a scheduled shared-channel pre-run. That shape was never generated.
- **fd-heraldic-registry × fd-registry-identity-fragmentation:** independent here. Both own identity, converge on f-005, but were never fused; the heraldic lens's "project-key" second-roll insight (f-021) and the fragmentation lens's "consumer-cardinality" insight (f-004) would, fused, produce a combined *migration-cost-across-both-namespaces* estimate the run never computed.
- **fd-diplomatics-provenance × fd-federation-discovery:** independent here. The confidence-tier-must-travel-with-the-payload axiom (f-010/f-013) and the graceful-degradation-must-be-distinguishable-from-silent-failure axiom (f-009) share a spine — *a fallback-produced or inference-produced finding must carry a marker* — but no fusion lens drew the line between them.

---

## 3. Taste Calls

Only two findings carry a non-zero taste score; both are **−taste smells to fix**, and both are elegant diagnoses of the *same* structural irony. No +taste elegance was recorded to preserve (the brainstorm is a design doc, not code; the lenses scored form-of-the-design, and found the form self-undermining twice).

### −taste (smell) — f-018 · taste_kind: `smell`

**The stage that promises the cure leaves the disease as an open question.** Track 1 step 2's *stated goal* is to eliminate the disconnected-codepaths split between the `/intertrace` skill and the agent — yet the "Single tracer codepath" open question leaves the unifying mechanism undecided. The skill computes `changed_files` from a bead-scoped `git log --grep` resolution; a review-time agent needs a diff-scoped resolution. Two different input computations feed the same tracer functions with no unification specified. The smell: *the same defect the stage is meant to cure is left as an open question inside the very stage that promises the cure.* Fix by making the shared entry script own the input-resolution boundary (accept a resolved file list; let each caller compute it), so there is one library entry point and two thin callers.

### −taste (asymmetry) — f-014 · taste_kind: `asymmetry`

**The fix mirrors the single-point-of-failure it condemns.** Track 2's registry is designed as sole source of truth replacing five files across four owners — but nothing names a check that would catch *the registry itself* silently diverging from ground truth. The motivating incident (fd-integration got a model-routing line in `agent-roles.yaml:49` but zero mention in `agent-roster.md`, and nothing noticed) proves the current fragmentation has no corroborating witness — and the registry fix doesn't add one either. The asymmetry: *the cure relocates the single point of failure rather than eliminating it.* Fix by giving the registry a cheap corroboration path — a lint/CI check that the registry's roster reconciles against each consumer's live view, so a half-grant is caught at grant-time (the heraldic lens's collision-check axiom, arrived at independently).

---

## 4. Convergence Spine

High-convergence findings are **high-confidence commodity** — trustworthy, low-novelty. These are the load-bearing facts multiple independent lenses reached from different domains; build on them without re-litigating.

**c-identity-key-continuity — f-004 / f-006 / f-012 (three lenses, three tiers).** The single most-corroborated result. Registry-identity-fragmentation (adjacent), fd-registry-identity-fragmentation again (f-006), and diplomatics-provenance (distant) all land on: fd-integration's pilot-phase trust rows accumulate under the literal string `fd-integration`; `trust_feedback.agent` is a bare `TEXT NOT NULL` with no FK; the roster path changes identity representation **twice** (hand entry → registry swap); and nothing states whether accumulated trust rows and findings remain attributable across the swap. This directly threatens the ≥20-row / ≥60%-accept success criterion — the evidence the pilot exists to gather can be silently orphaned at migration. **Trust this: decide the identity-key carry-forward before the pilot starts writing rows.**

**c-roster-taxonomy-gap — f-001 / f-005 (two lenses).** fd-integration is a *third* agent category — a plugin-shipped, non-interflux Plugin Agent registered via intertrace's `plugin.json` — that `agent-roster.md`'s Project-vs-interflux-Plugin taxonomy has no slot for. The "five files / four owners" count also misses `plugin.json`'s own `agents` array as a distinct identity-truth source. **Trust this: the wire step must add a taxonomy category, not just a roster row.**

**c-federation-discovery — f-007 / f-008 / f-009 (one lens, three verified instances).** Covered as Lead B above; the convergence is *internal* to the federation lens across three distinct code locations, which is why it reads as commodity-strength despite f-007's mid novelty.

**c-composer-precedent / c-second-consumer-contention — f-002 / f-015 / f-019 / f-020.** The adjudicated cluster (see §5): the objections to "agent-invoked, revisit later" compound rather than contradict, and the revisit trigger arrives inside the plan. High confidence that the *reasoning* behind the recommendation is incomplete, even though the recommendation itself survives.

---

## 5. Live Disagreements

**No disagreements remain open at halt** (`open disagreements at halt: []`). The one contradiction the run surfaced was adjudicated in round 1 and closed.

**The resolved disagreement (recorded here because it is the primary signal about the review's core question):** f-002 (fd-evidence-substrate-architect) vs. f-015 (fd-qanat-delivery), both at the "Tracer invocation path" open question. f-002 argued the Composer precedent makes candidate (b) *cheap* (so the brainstorm never costed it). f-015 argued the trigger for (b) is *already met* (a second tracer consumer effectively exists). The PROBE-DISAGREEMENT directive in round 1 dispatched an adjudication lens, which ruled:

- **f-019 — compounding, not contradictory.** Both hold. They are independent objections to the same conclusion: the brainstorm defers a check to a trigger that arrives inside the same committed plan, *while* skipping a costing exercise against infrastructure (Composer) that exists today. This is the run's central verdict on the goal.
- **f-020 — premise correction.** f-015's "a second consumer already exists today" over-reached: the `/intertrace` skill is a tracer-library consumer but *not* a second dispatchable evidence-based agent (separate `plugin.json` arrays, no `subagent_type`, no trust row, bead-scoped post-ship not review-time). The substantive point survives (Track 2 is built to onboard future evidence-based agents, so the trigger fires imminently regardless), but the framing needed the skill-vs-agent distinction.

**What this means for the recommendation:** the agent-invoked shape survives, but "revisit later" is a permanent decision wearing a temporary label (the substrate lens's own axiom). The honest move is to make candidate (a)'s entry script forward-compatible with candidate (b)'s orchestrator injection *now* — the Composer hook (`launch.md` Step 2.0.4) is the injection point, and it is live.

---

## If You Read One Thing

**f-007** — argmax(HEAT) tie with f-022 at 18, broken toward f-007 on risk (max 9 vs. 6) since |taste| is 0 for both. *`git rev-parse --show-toplevel` from inside intertrace returns intertrace's own root, not Sylveste's — the agent's MANDATORY first step 404s on its own home repo's default topology, and the sibling `/intertrace` skill already carries an unassigned `$MONOREPO_ROOT` proving the failure is live, not theoretical.* Resolve federation root-discovery before anything downstream; it gates the entire generalize stage and it is already broken in the codepath you plan to fuse into.

---

## Caveats

- **No fusions were attempted (0/0).** The run never issued a FUSE directive; the one available lens tension was routed to adjudication instead. Genuinely emergent, cross-lens intersection findings — a shape that is simultaneously orchestrator-amortized and consumer-apportioned; a combined migration cost across the agent *and* project identity namespaces — were not generated. This is the largest unreached region.
- **Halted DRY after 3 rounds on a falling gain curve** (round 0 yield 9 / novel-cluster 0.67; round 1 yield 2 / novel-cluster 0.33). Round 2 produced no new clusters. The frontier is well-mapped for the shapes the base lenses cover, but the loop stopped before a DEEPEN pass on the two highest-HEAT clusters (federation-discovery, flux-agent-existing-registrar) that could have produced implementation-grade detail.
- **f-003 refuted (freshness contract), excluded from all views.** The evidence-substrate lens asserted a freshness-contract axiom that over-reached: the tracer libs scan live working-tree state, which is the correct target when the artifact under review *is* the working tree. A freshness gap would only bite if evidence were captured upstream and consumed later — which is exactly the orchestrator-injection (candidate b) shape, so this axiom is latent, not currently violated.
- **Goal-named alternative shapes are surfaced but under-scored.** The review goal explicitly asked to score MCP tool surface (f-011), hook-time capture and event-driven tracing (f-016), and evidence-as-a-service. The lenses *flagged* that the brainstorm never scored these (correctly — they are absent), and noted intertrace has an empty `hooks.json` stub ready to receive a hook-time shape and a standing "no MCP server" design decision. But no lens produced a full scoring of these shapes against the sequencing/substrate constraints. The synthesis inherits that gap: these shapes are identified as unscored, not themselves scored.
- **Verification was not budget-clamped** — all cited code locations carry grep/command-verified evidence (the federation-boundary and flux-agent.py findings were independently re-run). No findings rest on unverified LLM impression except where a lens explicitly reasons about the *design doc's* omissions (which are verifiable by absence).
- **Single-runtime run (claude), balanced weights.** No model-diversity cross-check on the scoring; a second runtime might weight the novelty of the heraldic-registry findings (f-021/f-022, both novelty 3) differently.
