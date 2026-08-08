# Sylveste Backlog - Detailed Inventory

**Companion to:** [sylveste-roadmap.md](sylveste-roadmap.md) (strategic roadmap)
**Last synced:** 2026-08-08

This file contains every live P2-P4 item in the canonical Beads tracker.
It is generated from [roadmap.json](roadmap.json); do not hand-edit it.

---

## P2 - Next

### a2a
- **sylveste-ewy3.4.1.4** OAuth2 Resource Indicators authentication on /messages + /tasks _(blocked)_

### auraken
- **sylveste-0rmf** Prompt-injection defense for external content (2-of-3 verdict combiner)
- **sylveste-2l1.4** Build anchor scenario regression suite from daily_dilemmas
- **sylveste-2l1.5** Extract REDDIT_threaded sample (5K posts) for coverage index
- **sylveste-2l1.6** AITA near-miss density analysis (270K moral dilemmas)
- **sylveste-muf** Research: ambient recommendation UX — window shopping vs. over-indexed personalization _(deferred)_

### clavain
- **sylveste-clha** Build /clavain:office-hours adversarial pre-plan gate (gstack import)
- **sylveste-dan6** Design remote signer or canonical ledger replication for Mac-originated operations
- **sylveste-lfru** Wire /clavain:ship -> interpath:changelog + interdoc + interwatch:refresh chain
- **sylveste-otv9** Retire ambiguous home-ledger fallback without losing historical runs

### epic
- **sylveste-bcok** interop: Notion + Auraken + Clavain + GitHub integration bridge

### fd
- **sylveste-u9cp** INSTALL.md must lead with encounter framing, not capability enumeration; add substrate-readiness scan _(blocked)_
- **sylveste-zjz3** install.sh step 6 must be a transmissive close, not capability enumeration _(blocked)_

### harvest
- **Sylveste-ie6.7** Transplant Compound's Codex Writer safety logic into Clavain's Codex install path

### infra
- **Sylveste-6f7** zklw Go toolchain (1.23.8) too old to build intercore (go 1.25.0) + darwin release binaries — blocks canary-registering ic and Clavain publish from zklw
- **Sylveste-bzy** 5 interverse plugins dual-tracked: force-added into monorepo AND published from independent repos (interfer, interhelm, intersight, interseed, intership)

### intercore
- **Sylveste-nwv** ic publish: adopt 'claude plugin tag' release tagging + plugin dependency metadata + projected context cost surfacing

### interfer
- **Sylveste-0gi** DeepSeek V4 Flash on flash-moe — port effort vs wait-for-hardware decision
- **Sylveste-2ss** Flash-MoE holistic benchmark suite — quality, latency, memory, reliability _(blocked)_
- **Sylveste-6ru** Qwen3.6-35B-A3B quantization sweep (DWQ vs nvfp4 vs OptiQ vs plain) _(blocked)_
- **Sylveste-bov** flash-moe decode regression — 5 tok/s actual vs 12.9 tok/s spec
- **sylveste-dczo** Promote Track B5 to enforce mode _(blocked)_
- **Sylveste-ep8** Evaluate Qwen3.6-27B-OptiQ-4bit (released 2026-04-25) _(blocked)_
- **Sylveste-wfz** Fix test_polar_transform_range TurboQuant test failure
- **sylveste-yfot** Benchmark speculative decoding with 9B draft model _(deferred)_

### interfer 2ss
- **Sylveste-r8g** Add SWE-bench Lite runner to code_correctness harness _(blocked)_

### interfer+interflux
- **Sylveste-k8c** Local inference backend for flux-review agents — server-mode bridge _(blocked)_

### interfere
- **sylveste-m71** Publish Pareto frontier analysis: speed vs quality across local models _(blocked)_
- **sylveste-qbv** Experiment: LayerSkip / self-speculative early exit

### interflux
- **sylveste-9lp.15** P2: Structured disagreement as first-class output — disagreement_profile in findings schema
- **sylveste-9lp.17** P2: Passage-level citation in research synthesis — attribute claims to source passages, not agents
- **sylveste-9lp.18** P2: Evaluation rubrics — track finding recall, precision, coverage over time
- **sylveste-9lp.19** P2: Difficulty-aware slot ceiling — replace static formula with content-signal estimator _(blocked)_
- **sylveste-9lp.20** P2: Embedding-based dedup pass — cosine similarity on finding titles for conceptual duplicates
- **sylveste-9lp.21** P2: Typed agent-state log — JSONL per agent replacing in-prompt state tracking
- **sylveste-9lp.22** P2: Trust model diagnostics — explain low scores and feed back into prompt tuning
- **sylveste-9lp.32** BP-C1: lib_registry.py + registry-write consolidation (5 atomic-mutate sites + scoring algorithm extraction)
- **sylveste-9lp.32.7** BP-C1.C: extract scripts/_fluxbench_score.py from fluxbench-score.sh heredoc (180 lines)
- **sylveste-9lp.33** BP-C3: sanitize_untrusted.py fuzz tests + TrustedContent NewType — full 4-channel integration
- **sylveste-9lp.35** BP-C2: explicit dispatch state machine + VerificationStep primitive + run_uuid + decisions.log _(blocked)_
- **sylveste-9lp.35.6** BP-C2.B: run_uuid quire-mark + decisions.log per-run
- **sylveste-9lp.37** Holdout Register — name the ground-truth source for every calibration loop _(blocked)_
- **sylveste-fyo3.6** P2: Hard budget enforcement mode — test and enable blocking behavior
- **sylveste-lrnk** Editor-of-record protocol for shared design-doc sections + n6zw close-predicate
- **sylveste-wyoi** Brainstorm-to-roadmap lift discipline — checklist step in /interpath:roadmap

### interlab
- **sylveste-4jmp** Make plugin quality sweep read-only and reproducible

### interline
- **Sylveste-nko** Exploit new display surfaces: MessageDisplay hook, terminalSequence, subagentStatusLine effort field

### intermux
- **Sylveste-oqo** Replace session scraping with native 'claude agents --json' (2.1.145) + agent view integration

### interspect
- **sylveste-sfhq** Telemetry fusion: wire tool-time stats into interspect evidence

### interstat+galiana
- **sylveste-z7zh** Landed-work recap report (Goodhart-aware)

### interverse
- **Sylveste-ktz** Post-baseline small-fix bundle: date -d fallbacks (Sylveste-a3a) + ic publish --cwd hard-error (Sylveste-1zu) + legacy /tmp sideband retirement (Sylveste-zlc)

### interwatch
- **sylveste-mxns** 6 doc(s) drifted from source (weekly scan)

### microrouter
- **sylveste-5p7s** F2: D2 heuristic-baseline measurement — sibling to .19.9, parallel-runnable _(deferred)_
- **sylveste-s3z6.19.5** Resolver integration in Clavain — wire into routing.yaml _(blocked)_
- **sylveste-s3z6.19.6** Privacy-routing extension — sensitive tasks always engage router _(blocked)_

### routing
- **Sylveste-2bg** Re-measure heuristic coverage after agent-roles.yaml extension _(blocked)_

### spike
- **Sylveste-0gi.2** DeepSeek V4 → flash-moe 5-day feasibility spike (C-prime)

### spike-pivot
- **Sylveste-0gi.2.7** RunPod H200 rental for DeepSeek V4 baseline logit capture (Day-3 unblock)

### sylveste
- **sylveste-00qu** beads: 3 UX/correctness issues (bd dolt push help-on-no-remote, missing embedded-DB bootstrap from issues.jsonl, persistent 0755 permission warning)
- **sylveste-05rf** Auraken lens cleanup: cross-referencing pairs that may be authoring drift not distinct lenses
- **Sylveste-06i** Ecosystem research scan: 31-component research-possibilities agenda (3 lenses) _(in progress)_
- **Sylveste-06i.2** MAST-taxonomy classification pass over interflux/interlock failure logs
- **Sylveste-06i.3** Covert-channel / steganographic collusion audit for interlock messaging
- **sylveste-06yf** Refactor interfer onto MCP SDK or scope out of consolidation (prereq for sylveste-7505)
- **sylveste-0h8** Competitive Landscape: Close Clavain routing gaps vs LiteLLM/OpenRouter
- **Sylveste-0pk** /model-routing economy|quality seds flatten routing-table v2 phase overrides
- **sylveste-104h** Skaffen evidence contract — consume Clavains proven schema (add run_id attribution) _(blocked)_
- **sylveste-10na** F9: E2E install smoke + compatibility_evidence transcripts _(blocked)_
- **sylveste-129h** Cache-corrected cost-per-landable-change as second-line north-star
- **sylveste-18a.10** Two-stage LLM bash safety classifier for Skaffen trust evaluator
- **sylveste-18a.11** Persistent agent memory system for Skaffen
- **sylveste-18a.12** MCP HTTP/SSE transport for Skaffen
- **sylveste-18a.3** Fork subagent cache optimization for parallel OODARC spawns
- **sylveste-18a.5** Permission bubble mode for nested Skaffen agent chains _(blocked)_
- **sylveste-1j30** F7: interlens MCP adapter — swap JSON backend to ontology-queries _(blocked)_
- **sylveste-1mb8** Auraken-Hermes: cross-provider validation (does selector transfer beyond Claude?)
- **sylveste-1nvc** Generic thinker-profile extraction pipeline _(blocked)_
- **sylveste-2131** F1: Core daemon + event bus (SyncJournal, CollisionWindow, AncestorStore) _(blocked)_
- **sylveste-22oi.3** Auraken v0.2: GPG signing pipeline for checksums.txt.asc
- **sylveste-22oi.7.3** Cognitive profile: extraction pipeline (trajectory + conversation -> entities) _(blocked)_
- **sylveste-22oi.7.4** Cognitive profile: auraken-profile MCP server (mirror auraken-lens) _(blocked)_
- **sylveste-22oi.7.5** Cognitive profile: epistemic engine (promotion + half-life decay + harpoon test) _(blocked)_
- **sylveste-22oi.7.7** Cognitive profile: pattern-awareness SKILL behaviors (Journeys 2/7/21 + harpoon hook) _(blocked)_
- **sylveste-2fhj** rig-hook-wiring.py is tracked but declared in neither installer and not in the health surface
- **Sylveste-2fu3** shadow-work: 17-line hook repair awaiting mk's commit in a third-party-org repo
- **sylveste-2o0s** Add flux-review ephemeral read-only mode and cost controls
- **sylveste-2xzz** Thinker-profile schema v1 (YAML + validation harness)
- **Sylveste-2ys** clavain create-agent-skill command references a missing skill
- **sylveste-301b** Diagnose interstat tool_selection_events ↔ agent_runs session_id join gap
- **sylveste-34r2** F5.2: Go-Python persistent worker bridge _(blocked)_
- **sylveste-35x5** Migrate interlens to high-level MCP TS SDK (prereq for sylveste-7505)
- **sylveste-39p5** F5: TypeScript plugin adapters (interfluence,interlens,interrank,tuivision) _(blocked)_
- **sylveste-3v97** F1: Bundle scaffolding + MANIFEST.yaml v1 schema (auraken-distribution v0.1) _(blocked)_
- **sylveste-3xgz** Fresh-session remeasure: validate ~1,482b skill_listing reduction from sylveste-zppj
- **sylveste-3xl3.1.19** F6.2: Run live A/B benchmark on flux-explore-teams-brainstorm-{adjacent,distant}.json corpus
- **sylveste-3xl3.1.23** F5.3: Resolve teammate session UUIDs from team config + project session JSONLs
- **sylveste-3xl3.1.24** F4.6: Inbox-as-transcript adapter for team_synthesize.py finalize
- **sylveste-3xl3.1.25** F4.7: Pre-allow Bash mkdir/Write/Read for teammates in flux-explore --teams
- **sylveste-3xl3.2** flux-drive convergent finding triangulation via agent teams
- **sylveste-3xl3.3** /clavain:debate + intermonk:dialectic agent-teams upgrade
- **sylveste-3xl3.4** Wire TeammateIdle/TaskCreated/TaskCompleted hooks into Interspect evidence pipeline
- **sylveste-3xl3.7** flux-explore --teams Approach 2: target-mode review-debate _(blocked)_
- **sylveste-3z91** F4: interspect activation CLI (per-subsystem + fleet rollup) _(deferred)_
- **Sylveste-41r** Wire OPENROUTER_API_KEY into openrouter-dispatch MCP server env
- **Sylveste-4b5.10** LLM-judge bias doc-hygiene + gate-hardening rider (no new judge epic)
- **Sylveste-4b5.12** Audit-plane correlation layer (deferred, three-feed + consumer gated)
- **Sylveste-4b5.13** Trust-card: glanceable per-task human review surface from existing evidence
- **Sylveste-4b5.14** ACE coding-skill playbook vs compound-baseline bake-off (measurement-gated spike) _(blocked)_
- **Sylveste-4b5.15** Pass@k harness extension + kill-gated test-time-compute scaling spike _(blocked)_
- **Sylveste-4b5.16** Skaffen compaction verification + context-rot working-set instrumentation _(blocked)_
- **Sylveste-4b5.5** Ground review verdict in concrete pass/fail signal (downgrade unverified 'clean') _(blocked)_
- **Sylveste-4b5.6** Wire clavain policy engine into a real fail-CLOSED PreToolUse interdiction hook _(blocked)_
- **Sylveste-4b5.7** Pre-dispatch parallelizability + cost gate folded into the 3kol Rimsky spec
- **Sylveste-4b5.8** Conflict-economics telemetry on the parallel dispatcher (Rimsky, child of 3kol)
- **Sylveste-4b5.9** campaign.md route-to-fallback-on-verified-failure (replace blind retry/skip/abort) _(blocked)_
- **sylveste-4li0** interop: daemon adapter construction from config
- **sylveste-4rwh** Add Break stage to trust lifecycle (Earn → Compound → Break → Epoch → Demote)
- **Sylveste-4vol** secret scanner: the X_SECRET_Y= class still slides past the generic rule
- **sylveste-4wq6** Extend auraken-lens trajectory schema: capture lenses_offered + user question choice (training signal) _(blocked)_
- **sylveste-5boi** Signal command: log (recent forge sessions)
- **sylveste-5hx7** Signal command: diff (re-show pending changes)
- **sylveste-5jn8** Auraken lens_select latency: 12-20s per call is real UX cost (dogfood finding)
- **sylveste-5lla** Load-path independence audit of the evidence-infra ring
- **Sylveste-65j** Record generating-model provenance in flux-drive fd-* output format
- **Sylveste-6ko4** Re-measure auto-stop-actions timeout rate once clavain 0.6.294 is resolved in-session
- **sylveste-6m1k** F3: interserve-ts adapter framework _(blocked)_
- **sylveste-6zhe** Add Sylveste affected-module build and test runner
- **sylveste-7505** Consolidated interverse MCP server _(blocked)_
- **sylveste-7aj8** Interspect skill calibration
- **sylveste-7aj8.9** interspect skillcal: collector coverage — no_redirect/tokens drop ~97% of rows
- **sylveste-7g96** F3: Prebuilt auraken-lens Go binaries for 4 platforms (v0.1.0) _(blocked)_
- **sylveste-7zw2** Implement generated-agent retention, pack-scoped loading, and stale index refresh
- **Sylveste-84by** git-autosync-promote reports NEEDS-REBASE for lanes that are strict ancestors of main
- **sylveste-8tfd** Two hook scripts are present on both machines and registered nowhere
- **sylveste-8ucm** F5.3: Core query templates (4 pure queries) _(blocked)_
- **Sylveste-8umf** Unknown clavain-cli flags are silently ignored instead of rejected
- **sylveste-9g6v** F2: Beads adapter — bidirectional bd CLI sync _(blocked)_
- **Sylveste-9yoh** intercore: ic sweep — wire the 4 implemented-never-wired subsystems (scheduler engine, stall detector, RecoverPending, audit chain) with per-subsystem witness obligations (f-158)
- **sylveste-a4oj** Multi-axis improvement: usability, token efficiency, ML-routing replacement (flux-review 2026-05-04) _(blocked)_
- **sylveste-a4oj.9** Phase 2 — Dirty-bit and routing replacement infrastructure (S-difficulty bundle)
- **sylveste-am7w** Meadows profile (validation anchor — 12 leverage points rediscovery test) _(blocked)_
- **sylveste-b1ha** Persona/lens database: unify fd-agents + Auraken lenses
- **sylveste-benl.11** Decommission Auraken Python runtime
- **sylveste-bvoy** publish drift: shipped artifact behind committed source (2026-08-02)
- **Sylveste-byw** interhelm/intersight: resolve dual tracking between umbrella and standalone repos
- **Sylveste-c7a** interline: interphase sideband writer redundancy — cutover checklist for interphase retirement
- **Sylveste-cayt** Clavain: gate-mode 3-file fix — unify bash/Go defaults, emit gate_mode_resolved via ic events record, write failure-direction policy into contracts/ (f-101/f-102/f-108)
- **sylveste-cnxf** Redesign gsvdotcom: ACRNM-inspired technical document aesthetic
- **sylveste-cqa** Port interblog content collections to /blog/ with one-way sync
- **Sylveste-d3m** Adopt --to auto --class across Clavain dispatch (phase 1: shadow wiring)
- **sylveste-dd6t** Rate limiting for forge code commands
- **Sylveste-ddp3** rig-hook-wiring.py and rig-hook-duplication.py are tracked but declared in neither installer
- **sylveste-dsbl** F3: Schema + DDL migration 001 — 7-entity ontology with all G3-G9 fields locked _(blocked)_
- **sylveste-dvu** Unified user identity: composite identity table
- **Sylveste-dvw** Research spike: execute pre-registered F6b flux-drive triage A/B (sylveste-g939)
- **sylveste-dz94** Run test-conversations.md acceptance on Claude-family models (Opus + Haiku) _(blocked)_
- **sylveste-e8te** F5: INSTALL.md + canonical two-step install path _(blocked)_
- **Sylveste-e9c** Make beads post-merge handler run 'bd import' so git pull auto-syncs Dolt (real fix behind the sync-guard advisory)
- **sylveste-ewy3.1.1** Temporal Cloud dev namespace setup + credentials path
- **sylveste-ewy3.1.2** Wire first Skaffen test-dispatch as Temporal Workflow + mirror to Intercore event log
- **sylveste-ewy3.1.3** Mythos+1mo decision gate: Temporal full-migration vs. dual-path
- **sylveste-ewy3.2.1** OTEL alignment audit + feature-flagged emission in interspect-evidence.sh _(blocked)_
- **sylveste-ewy3.2.2** Langfuse Cloud Hobby setup + 14-day dual-write spike from interspect-evidence
- **sylveste-ewy3.2.3** Mythos+1mo decision gate: Langfuse primary vs SQLite + Langfuse shadow
- **sylveste-f314** Appleton profile (structure-rich corpus test) _(blocked)_
- **sylveste-fa1m** Gmail purchase import pipeline (fbz successor)
- **sylveste-fd7x.7** Resolve intersite plugin repository remote/publish target _(blocked)_
- **sylveste-fij2** F5: Local filesystem adapter — fsnotify, SHA-256 change detection _(blocked)_
- **Sylveste-fsdy** Two hook scripts are present on both machines and registered nowhere
- **Sylveste-g1cu** publish drift: shipped artifact behind committed source (2026-08-03)
- **sylveste-g939** F6b: flux-drive triage backend swap + A/B execution + ship decision _(blocked)_
- **sylveste-gd3q** Repackage Interspect and consolidate evidence telemetry boundaries
- **sylveste-gfp2** Style mirroring for early conversations (pre-fingerprint)
- **Sylveste-gtqg** New plugin repos start unprotected — nothing enforces the branch-protection policy as an invariant
- **Sylveste-hni3** Clavain: SYLVESTE_EXEMPLAR_ROOT detection helper routed through ensure_repo, codex-auto-refresh, check-install-updates (f-084/f-085/f-052)
- **Sylveste-hvkl** dotfiles vendors obra/superpowers as a split tree — pin an upstream ref instead?
- **sylveste-i0px** Auraken thinker-profile system (proprietary reasoning moat) _(blocked)_
- **sylveste-i8gp** Evidence pipeline wiring — activate sylveste-xcn4 and close the flywheel _(blocked)_
- **sylveste-islh** F3: Interspect activation aggregator (race-fixed cursor + dedup) _(deferred)_
- **sylveste-j0yv** F5.5: Shared resolution primitives _(blocked)_
- **sylveste-j7gy** F5: Plugin manifest annotations + 5-plugin reference adoption _(deferred)_
- **sylveste-j7vl** cc-changelog: unreviewed Claude Code releases (2.1.216 → 2.1.220)
- **sylveste-jqxf** AI Factory Wave 1 foundation (ysxe successor)
- **sylveste-jum2** Precompile interrank TypeScript at publish time (drop tsx runtime) _(blocked)_
- **Sylveste-keb3** Six beads differ between the machines in ways no import can reconcile
- **Sylveste-kp9o** Khouri lane frozen 109 days — mk to decide on f985d94
- **Sylveste-kq4** Interband sideband parity from sprint-advance _(in progress)_
- **sylveste-lbvq** F4: Python plugin adapters (intercache,interdeep,interfer,interject,intersearch,interseed) _(blocked)_
- **sylveste-lf3b** Rename fd-agent personas with misleading lexical-prefix collisions
- **sylveste-lfdy.1** Wire jetty.io as eval substrate for Auraken voice + behavioral signature scoring _(blocked)_
- **sylveste-llen** Strengthen natural-language feedback loop for self-improvement
- **sylveste-lny4** Self-dispatch loop for AI factory (ysxe.3 successor)
- **sylveste-lon1** Cross-model dispatch scoring + integration (9lp.9 successor)
- **sylveste-lwp7** lattice: apply_lifecycle_transition mutates et.families in registered EntityType
- **sylveste-m2p** F4: Garden Salon agent bridge for interseed _(blocked)_
- **sylveste-m36b** F6: SKILL.md curation + voice-rubric.md (Mandatory Form / Permitted Variation) _(blocked)_
- **sylveste-mblb** F2: Subsystem emit helper (Go + bash) with durable session sentinel _(deferred)_
- **sylveste-mj11.1** Hallmark log: immutable advancement_events table for trust-tier transitions
- **sylveste-mj11.2** Tier-weight aggregation specification + conflict-resolution rule
- **sylveste-mj11.3** Interspect substrate-independence and suhba-window classification per subsystem
- **sylveste-mj11.4** Break invariant tuple schema and per-subsystem calibration
- **sylveste-mj11.5** Break Synaxis cadence + chain-of-custody schema + axis-set publication
- **sylveste-mj11.6** Dormancy/degradation rubric, Bauschinger-positive demotion, tarbiya pathway, non-conformance disposition
- **sylveste-npc5** Repair stale Claude plugin commit metadata during deploy
- **sylveste-nr6x.4** L4: Signal-native tool approval transport
- **sylveste-nr6x.5** L5: Skaffen integration — sovereign agent lifecycle
- **sylveste-nyx** Hidden /about page with mission/vision from GSV identity repo
- **sylveste-o8wo** Fix subagent Write permission for flux-gen-specs and docs/research/flux-* directories
- **sylveste-oej5** F10: auraken-lens Go CLI binary wrapper (cmd/auraken-lens) _(blocked)_
- **sylveste-owjn.3** Extend observation.Snapshot to a true superset (artifacts map + phase-advance history) so ic situation snapshot fully replaces lib-sprint.sh ad-hoc queries
- **Sylveste-oxcv** A negative-control proof cannot tell 'assertion failed' from 'fork failed', so 7 of 9 results are unknown
- **sylveste-p6so** F8: GitHub release auraken-distribution/v0.1.0 + signed checksums + CHANGELOG _(blocked)_
- **sylveste-pexq** Audit Python MCP servers for lazy top-level imports _(blocked)_
- **sylveste-pf4** intersite-blog: blog fold-in + full pipeline enforcement
- **sylveste-pfi** F5: Signal feeds + graduation workflow _(blocked)_
- **sylveste-q2k** F6: Autonomy ratchet state machine _(blocked)_
- **Sylveste-qgvl** intercore: wire audit chain to gate-mode resolutions + dispatch transitions (run-scoped chains, LogQ tx variant, checksum policy v2 — f-188)
- **sylveste-qhn1** interverse hygiene: root go.work + 3 READMEs + DEPENDENCIES.md + HOOKS-REGISTRY.md
- **Sylveste-qm2** interlock tier-2: embedding-based semantic conflict detection in pre-edit hook
- **sylveste-qroh** F6: interrank TASK_DOMAIN_MAP FluxBench integration _(blocked)_
- **Sylveste-r3xs** Adopt --to auto --class at remaining dispatch call sites (phase 1.5)
- **Sylveste-rgj** Research spike: null test — does multi-agent coordination beat single-strong-model on our task mix?
- **Sylveste-rhw** Route charter-vs-plain-goal from goal risk properties (wire classifyComplexity + spend signal into the goal-form fork)
- **sylveste-rom** Full pipeline enforcement: MDX stripping, HMAC webhook, preview gating
- **sylveste-rsj** EPIC: Sylveste SOTA — Garden Salon Architecture
- **sylveste-rsj.3** Roguelike-Inspired Agent Architecture — structural patterns from NLE/BALROG/Arcgentica for Garden Salon
- **sylveste-rsj.3.14** Run BALROG TextWorld baseline: raw model vs Skaffen-orchestrated progression comparison
- **sylveste-rsj.3.5** Evaluate Agentica SDK as complementary agent framework — type-safe multi-agent with stateful REPL
- **sylveste-rsj.8** Stigmergic coordination substrate — pheromone fields with decay on shared documents
- **sylveste-s01c** Drop lattice->attp local-path replace (close iv-v5ayb residual)
- **sylveste-s288** F4: install.sh — atomic, gated, transmissive close _(blocked)_
- **sylveste-sn7** Tuivision: token-efficient terminal state encoding
- **sylveste-sn7.10** Add ROI (region-of-interest) encoding — high fidelity for active regions only
- **sylveste-sn7.14** Fix alternate screen buffer detection for cursor position
- **Sylveste-so2i** intercore: ClearLocks staleness guard + --dry-run + classified tombstone event (f-060, f-192)
- **sylveste-t5x4** auraken-thinker MCP server (sibling to auraken-lens) _(blocked)_
- **sylveste-td2o** Brainstorm-summary feedforward into plan review (review <- plan,brainstorm)
- **sylveste-tfj7** F7: Challenger slot mechanism for unqualified candidates _(blocked)_
- **Sylveste-tfvr** bd cannot open the beads database in Nartopo and mediumsetting: pending schema migrations on dirty tables
- **sylveste-ttlq** rig-autosync-freshness.py is tracked but declared in neither installer nor the health surface
- **sylveste-ttwz** Triage Python MCP servers for Go port candidates (hot-path first) _(blocked)_
- **sylveste-u28h** CPVO + DWSQ domain-general north star metrics (rsj.4 successor)
- **sylveste-u74g** F7: build-dist.sh — deterministic bundle assembly _(blocked)_
- **sylveste-uhjv** audit.log producer dormant — log-tool-invocation.sh not wired into settings.json
- **sylveste-ukd3** lattice-web V0 — static browse + search at interverse/lattice/web/ _(blocked)_
- **sylveste-ung7** Reconsider sylveste-7505 consolidation given spike C findings (cold-start math doesn't favor it) _(blocked)_
- **sylveste-ungg** Local plan-phase check in /work + /execute-plan (intercore-independent)
- **sylveste-usj** F5: Tier 1 INFORM signals + pleasure signals _(blocked)_
- **sylveste-usvf** F5: Proactive model surfacing — SessionStart + weekly schedule _(blocked)_
- **sylveste-uzpo** Interface evidence instrumentation — 5 cross-subsystem signals
- **sylveste-v3ck** Demotion-rehearsal as M3+ promotion precondition
- **sylveste-v4t2** Meadowsyn experiment suite (jpum successor)
- **Sylveste-v7f** Add kimi as a flux-melange peer runtime (HTTP transport, no CLI) _(in progress)_
- **sylveste-vsi4** F6: MCP server + Claude Code plugin _(blocked)_
- **sylveste-w8zv** Rename github upstream mistakeknot/interweave → mistakeknot/lattice + update go.mod
- **Sylveste-wch** Beads Session Close Protocol text is wrong: 'bd backup sync' does not flush Dolt→JSONL — protocol must use 'bd export > .beads/issues.jsonl'
- **sylveste-wdf2** Doc monitoring automation (replaces interscout shape)
- **sylveste-wdf2.2** L2: PreToolUse hook surfaces drift on doc access; auto-fire on Certain
- **sylveste-wlk** Publish seed experiments after voice review
- **Sylveste-wrz** Clavain: restore README count line + publish project-onboard update (0.6.252)
- **Sylveste-ws38** auraken local history is unrelated to its remote — hook fix cannot be pushed
- **Sylveste-x2c** Research spike: re-test 'MLX has no concurrent inference' premise (mlx-lm 0.18+) before sylveste-4wl burns on it
- **sylveste-x6e4** Multi-mcpServers capability spike (prereq for sylveste-7505) _(deferred)_
- **sylveste-xd0n** Forge mode on Signal transport
- **sylveste-xfsr** F3: GitHub adapter — App webhooks, Issues, PRs, repo files _(blocked)_
- **sylveste-xka6** Promote B2 complexity routing dispatch-side shadow -> enforce + quality-evidence _(blocked)_
- **sylveste-xmav** F4: Notion adapter — pages, databases, webhooks (port from interkasten) _(blocked)_
- **sylveste-xoki.1** Codex discovery hygiene: fix stale skill/frontmatter and cache noise
- **sylveste-xoki.2** Agent evidence receipts for Codex and Claude Code
- **sylveste-xoki.3** Plugin and skill architecture deprecation plan
- **sylveste-xspv** Auto-revert timeout for pending forge code changes
- **Sylveste-y6rl** Nothing stops a commit from adding a tracked dotfiles path with no declaration
- **sylveste-ya2** F2: Auraken idea capture via /idea command _(blocked)_
- **sylveste-ye7y** F4: Drift detection — sample-based + version-triggered _(blocked)_
- **sylveste-yrc** clavain-cli not on PATH after monorepo clone
- **sylveste-ysny** Skill calibration: signal density too low to trust scoring — gate autonomy on it
- **sylveste-yxk8** F6: North Star integration + observation methodology + Goodhart breaker _(deferred)_
- **sylveste-z55b** Refactor Clavain SessionStart into cached read model plus hook health ledger

### upstream-sync
- **Sylveste-ie6.11** sp-lab: tombstone dead slack-messaging skill + vendor new windows-vm skill

### v6-candidate
- **sylveste-2h3o** Phase 3-4 bootstrap spec — initial governance policy + handoff criteria
- **sylveste-9um7** Routing-decision evidence schema for Ockham + Clavain + intercept
- **sylveste-aon0** Cross-source evidence independence test
- **sylveste-xq0t** Per-tier demotion latency bounds

---

## P3 - Later

### auraken
- **sylveste-2l1.7** Arctic Shift extraction for niche subreddits
- **Sylveste-8p3** AURAKEN_BOOTSTRAP=off builder bypass for onboarding arc

### clavain
- **sylveste-kogm** /context-restore + structured WIP-commit metadata (parked)
- **Sylveste-u59** Config adoption pass: fallbackModel chain, Tool(param:value) permission rules, sandbox.credentials/deniedDomains

### interfer
- **sylveste-7hxm** Route-heuristic-coverage interlab campaign
- **Sylveste-uk3** OpenRouter stream usage block omits reasoning_tokens — gen_tps/cost telemetry undercounts on bvh

### interfere
- **sylveste-1zh** Experiment: StreamingLLM attention sinks for infinite context
- **sylveste-308** Autoresearch: SSD page cache pre-fetching for 397B streaming _(blocked)_
- **sylveste-37g** Experiment: Mixture of Depths (MoD) dynamic layer routing
- **sylveste-3uy** Autoresearch: Metal compute shader optimization _(blocked)_
- **sylveste-4wl** Autoresearch: adaptive batching parameters for concurrent agents _(blocked)_
- **sylveste-8v3** Benchmark Kimi K2.5 3-bit (1T, 32B active) _(blocked)_
- **sylveste-9tc** Autoresearch: LayerSkip exit threshold tuning _(blocked)_
- **sylveste-bpg** Benchmark GLM-5 4-bit (744B, 40B active) _(blocked)_
- **sylveste-f0k** Experiment: reservoir computing readout for task routing
- **sylveste-i8u** Experiment: custom Metal compute shaders for mlx-lm
- **sylveste-ji6** Experiment: Multi-head Latent Attention (MLA) for KV compression _(deferred)_
- **sylveste-naj** BHQ speed optimization via autoresearch _(deferred)_
- **sylveste-uln** Benchmark DeepSeek V3.2 4-bit (672B, ~37B active) _(blocked)_
- **sylveste-xc8** Experiment: memory wiring and page cache optimization for SSD streaming _(blocked)_

### interflux
- **sylveste-9lp.25** P3: Learned orchestration from run history — requires labeled negative data
- **sylveste-9lp.26** P3: Query decomposition for complex research — confirmed v2, focus on exploratory+onboarding types
- **sylveste-9lp.27** P3: Domain-specific research agents — flux-gen equivalent for research side
- **sylveste-9lp.28** P3: Per-finding sycophancy detection — architecture ready in reaction.yaml, deferred until fleet grows
- **sylveste-9lp.29** P3: Triage subagent — offload Steps 1.0-1.2 from host context
- **sylveste-9lp.32.6.10** BP-C1.B.drift: migrate fluxbench-drift.sh registry writes (needs flock restructure)
- **sylveste-9lp.32.6.11** BP-C1.B.discover: migrate discover-merge.sh registry writes (needs add-model primitive)
- **sylveste-fyo3.10** P3: Weekly discovery agent automation — run fluxbench-discover.md on cron schedule _(blocked)_
- **sylveste-fyo3.11** P3: Oracle cross-AI review integration — enable non-Claude peer review via Oracle binary
- **sylveste-fyo3.7** P2: Interspect overlay activation — promote from progressive enhancement to default

### interproof
- **sylveste-ayl** Manual-driven feature validation plugin

### interspect
- **sylveste-sfhq.4** Tool-remediation canary + revert plumbing (sfhq.3 follow-up)
- **Sylveste-uiw** Ingest OTEL workflow.run_id + agent_id/parent_agent_id span attribution as routing evidence

### interstat
- **Sylveste-xvt** Investigate hash-ID fallback: 70% of subagent rows have unparseable agent_name

### routing
- **Sylveste-23w** Propagate verify_frontmatter.py + routing-drift workflow to sibling subrepos
- **Sylveste-7zi** Investigate fd-architecture/fd-systems opus-vs-sonnet disagreement

### scoping
- **Sylveste-s10** Small-local-model (sub-10B) workload candidates after microrouter cluster close

### sylveste
- **Sylveste-05t** Research spike: self-speculative decoding via native MTP heads on downloaded MoE checkpoints
- **Sylveste-0fd** interchart: regenerate-and-deploy.sh doesn't deploy — only pushes to GitHub
- **Sylveste-0ww** Research spike: null-test graph/lens retrieval vs naive baseline on real Auraken/lattice queries
- **sylveste-1h0b** Build Komoroske profile via proven pipeline (return from deferral) _(blocked)_
- **sylveste-22oi.6** Reconcile stale non-dist SKILL.md duplicate in Auraken Hermes tree
- **Sylveste-31v** Run install-macos.sh on Mac to restore claude-plugin-cleanup.sh + LaunchAgent _(blocked)_
- **sylveste-3rod** Sylveste Mythos launch readiness — 3-month focus + launch-on-drop trigger _(blocked)_
- **sylveste-3xl3.5** Audit fd-* and researcher agent definitions for teammate-role reuse
- **sylveste-3xl3.6** Plan-approval teammate mode → quality-gates / authz framework integration
- **sylveste-3xl3.8** flux-explore --teams Approach 3: full team-driven exploration _(blocked)_
- **Sylveste-46v** Clavain: clean stale publish_state rows + audit cross-marketplace drift
- **Sylveste-4b5.17** Rimsky (3kol) topology doc-hygiene: record flat-fan-out structural rule
- **Sylveste-4b5.18** Cache-aware effective-cost term in B2 routing (child of xka6, gated on enforce) _(blocked)_
- **Sylveste-4b5.19** Contamination-resistant benchmark re-pin (deferred, gated on harness consuming a routing decision)
- **Sylveste-4b5.20** VerifyLoop feasibility — self-generated-oracle iteration vs TDD baseline (research spike) _(blocked)_
- **Sylveste-4b5.21** interrank benchmark source-provenance ranking input (child of s3z6, gated on s10) _(blocked)_
- **Sylveste-4b5.22** Local lint-triage classifier feasibility (s10 child, measure-only, likely-moot)
- **Sylveste-4b5.23** CoAgent live-external-state concurrency watch-item (gated, self-limiting, kill-dated)
- **Sylveste-4b8** Research spike: LLM-judge reliability harness for interflux + cross-model consensus test
- **sylveste-4epi** Interlab observability audit — masaq METRIC wrappers (dxzr successor)
- **sylveste-52ys** Rao profile (self-referential essay-chain test) _(blocked)_
- **sylveste-55hj** Agent fitness decay (finding->commit integration rate)
- **sylveste-5va** Auto-generate graph edges from content themes + lineage fields
- **sylveste-6zy** xterm.js slide-out panel component for project pages
- **sylveste-7aj8.6** interspect skillcal: tune-overlays — skill_tune action + overlay format _(blocked)_
- **sylveste-7aj8.7** interspect skillcal: canary + autonomy — regression trigger + safe-list _(blocked)_
- **Sylveste-8ew7** Generators run on --help instead of printing usage
- **sylveste-8g69** Thompson profile or substitute (analytical-framework consistency test) _(blocked)_
- **sylveste-8qk** F8: Philosophy amendment + documentation
- **Sylveste-8rpw** zklw: delete the phantom ~/projects/Demarch tree (needs mk's go)
- **Sylveste-942** Fix /Users/arouth hardcoded path in com.arouth.claude-plugin-cleanup.plist
- **sylveste-9prl** Wei profile (rare-frame detection test) _(blocked)_
- **sylveste-9xyh** beads: bd dolt status errors with 'not supported in embedded mode' but bd dolt help lists it unconditionally under Server lifecycle
- **sylveste-a4oj.10** Phase 3 — Infrastructure-class improvements (M+ difficulty bundle)
- **sylveste-a4oj.12** Memory depth-tiered archiving: project_status frontmatter + close-off depth automation
- **sylveste-a4oj.14** M-01 follow-up: per-project user-scope MCP server suppression (mcpProfile-equivalent)
- **sylveste-a4oj.9.3.1** Semantic-embedding dup detection (extends 9.3 lexical baseline)
- **sylveste-amcz** F2: interserve-py adapter framework _(blocked)_
- **Sylveste-aso** Umbrella gitignore: docs/research/*/ rule is leaky for nested content
- **Sylveste-bgj** Unify docs/prd/ and docs/prds/ directory structure
- **sylveste-c231** Add quarantined-worktree disposal runbook to Sylveste docs (generic version of elf-revel solutions doc)
- **sylveste-dxt7** intercore gate-rule registry (OS-layer extensibility)
- **sylveste-e20** /intersite:publish with atomic swap deploy
- **Sylveste-e7m3** sylveste-vision.md links to docs/sylveste-reference.md, which does not exist
- **sylveste-esjb** Bootstrap or retire the 16 beads DBs with no local database
- **sylveste-fba8** Hardware-aware model recommendations in interrank (1ifn successor)
- **sylveste-fdn** 301 redirect: blog.generalsystemsventures.com to /blog/
- **sylveste-fj1w** Clavain peer-coexistence B′ — peer-aware using-clavain + peers.yaml registry (gated on telemetry)
- **sylveste-gaid** Auraken: SKILL.md cross-model voice portability — potential research finding
- **sylveste-gw6** WebSocket PTY relay service at apps/intersite-relay/
- **sylveste-h4mw** F1: interserve plugin scaffold _(blocked)_
- **sylveste-hfmh** Retire interscout plugin (deprecated 2026-04-27)
- **sylveste-hvmc** intermute live transport v1.5: active-probe readiness check (replaces 2s staleness)
- **Sylveste-i3h** Research spike: expert-activation traces → Belady-approximating cache policy for flash-moe
- **sylveste-jciw** clavain-cli sprint-init gate diverges from bd doctor (false-positive '1 error(s)')
- **sylveste-jp1l** interjawn MCP server fails to start — Prisma ESM export error
- **sylveste-jsyc** F6: Big-bang cutover — remove legacy mcpServers entries _(blocked)_
- **sylveste-lbkd** Sprint v2 artifact bus + progress trackers (lta9 successor)
- **sylveste-lgci** A:L4 — evaluate skill-selection calibration as a 4th autonomy loop (post-v0.7)
- **sylveste-liiu** Per-hook preamble byte telemetry for automatic regression detection
- **sylveste-lpnd** ATTP attestation protocol for interweave (e1mi successor)
- **Sylveste-lsh8** Post the drafted bd export -o upstream report to gastownhall/beads
- **Sylveste-m3wd** interlore is on master, not main, against the estate convention
- **sylveste-m5g** intersite-relay: xterm.js dev panel + WebSocket PTY relay
- **sylveste-nr6x.12** Infra: install signal-cli + register hassease Signal account
- **Sylveste-ns0m** dotfiles .claude/CLAUDE.md — last file of the retired root tree, carved out for a sibling session
- **sylveste-nxfq** sprint: automated import-graph assertion from plan's structural requirements
- **Sylveste-omz** Research spike: temporal fact-invalidation (t_valid/t_invalid) for intermem
- **sylveste-ovux** Upstream Hermes skill frontmatter aliases (support /ak for /auraken natively)
- **sylveste-oyrf** Longitudinal cost-calibration + Mythos launch artifacts
- **sylveste-oyrf.3** 90s self-building asciicast per fd-demo-artifact-authenticity shot list
- **Sylveste-oz7o** interchart artefact still machine-dependent after the case fix
- **sylveste-p2yj** Go benchmark-driven optimization for Skaffen hot paths (0pvp successor)
- **Sylveste-r5t** Clavain: investigate skill-precedence — ~/.claude/skills/ override didn't beat cached plugin SKILL.md
- **sylveste-rm8w** lattice: function diagnostic property mismatch (families.py vs diagnostics.py)
- **sylveste-rsj.3.4** Permaconsequence visibility: make cross-session evidence compounding visible in Garden Salon UX
- **sylveste-rsj.3.6** GameDevBench integration: add game-building benchmark alongside SWE-bench for complex multi-file evaluation
- **Sylveste-ry3** Research spike: orchestrator-visibility safety audit (hidden dispatch vs dissent suppression)
- **sylveste-sn7.11** Separate UI chrome (borders, status lines) from content in output
- **sylveste-sn7.12** Add channel-selective encoding — callers choose which attributes to include
- **sylveste-sn7.13** Add session-local dictionary for repeated content patterns
- **sylveste-sn7.15** Add generative encoding for structured UI — template+data instead of full render
- **sylveste-sn7.16** Add information hierarchy (L0/L1/L2/L3) to all output modes
- **sylveste-sn7.17** Add multi-pane marshalling — named pane composition for tmux/splits
- **sylveste-sn7.18** Add task-adapted rendering profiles (interactive/content/structure)
- **sylveste-sn7.19** Add agent backchanneling — LLM negotiates detail level
- **sylveste-sn7.20** Add color semantics lookup table for common terminal applications
- **sylveste-sn7.21** Explore occlusion culling — skip background content behind modal dialogs
- **sylveste-sn7.22** Document vision token cache disadvantage for multi-turn agent sessions
- **sylveste-sn7.6** Add motif/summary LOD level (L0) for polling tasks
- **sylveste-sn7.7** SVG CSS class dictionary — deduplicate repeated class/color attributes
- **sylveste-sn7.8** Add diff/delta mode with auto-refresh every 5 turns
- **sylveste-sn7.9** Add semantic role annotations (ARIA-like) for terminal elements
- **Sylveste-sox** xp7-c: investigate why Claude Code plugin auto-loader silently drops interlock hooks
- **Sylveste-tpc** Research spike: lens authoring-drift pairs (sylveste-05rf) as semantic versioning
- **sylveste-tsvw** intercore coordination quota/fairness (pre-scale insurance)
- **sylveste-u6fj** F7: interkasten migration + archival _(blocked)_
- **Sylveste-va4** Research spike: M5 Neural Accelerator prefill/decode asymmetry measurement
- **sylveste-w4sj** v1.0 roadmap artifact publishing (enxv successor)
- **sylveste-wdf2.3** L3+L4: /schedule routines for floor refresh and monthly audit
- **sylveste-y6m7** Audit + clean parent-epic depends_on edges in b1ha (and other epics)
- **sylveste-z0pc** Skill-description boilerplate standardization via interskill:audit
- **sylveste-z1sq** interline statusline: scope next_bead to session lane (tmux name)

### upstream-sync
- **Sylveste-ie6.4** compound-refresh: staleness audit for docs/solutions KB
- **Sylveste-ie6.5** ce-ideate-style pre-brainstorm idea generation+critique stage
- **Sylveste-ie6.6** product-pulse: read-side user-outcome telemetry loop

---

## P4 - Someday

### interfere
- **sylveste-0zc** Experiment: ANE (Apple Neural Engine) offload for attention _(deferred)_
- **sylveste-c57** Experiment: ant colony optimization for expert routing paths _(deferred)_
- **sylveste-eka** Experiment: thermodynamic-inspired annealing for expert selection _(deferred)_

### observability
- **Sylveste-9ve** Explore subagent dispatches stopped 2026-04-21 — verify whether workflow shift or instrumentation gap

### routing
- **Sylveste-10p** Add pre-commit hook layer for frontmatter drift (light gate)
- **Sylveste-vft** Drift baseline ratcheting — committed .routing-drift-baseline file

### sylveste
- **sylveste-wdf2.4** L5 (deferred): Substrate-independent external replay
- **sylveste-yofd** Clavain peer-coexistence C′ — full rig manager (profiles, lockfile, per-skill priorities, rig CLI)
- **sylveste-zfsj** intermute live transport v2: cross-host (SSH + tmux orchestration)
