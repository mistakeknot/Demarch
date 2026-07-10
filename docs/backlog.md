# Sylveste Backlog - Detailed Inventory

**Companion to:** [sylveste-roadmap.md](sylveste-roadmap.md) (strategic roadmap)
**Last synced:** 2026-07-10

This file contains every live P2-P4 item in the canonical Beads tracker.
It is generated from [roadmap.json](roadmap.json); do not hand-edit it.

---

## P2 - Next

### auraken
- **sylveste-0rmf** Prompt-injection defense for external content (2-of-3 verdict combiner)
- **sylveste-2l1.4** Build anchor scenario regression suite from daily_dilemmas
- **sylveste-2l1.5** Extract REDDIT_threaded sample (5K posts) for coverage index
- **sylveste-2l1.6** AITA near-miss density analysis (270K moral dilemmas)
- **sylveste-muf** Research: ambient recommendation UX — window shopping vs. over-indexed personalization _(deferred)_

### harvest
- **Sylveste-ie6.7** Transplant Compound's Codex Writer safety logic into Clavain's Codex install path

### interfer
- **Sylveste-0gi** DeepSeek V4 Flash on flash-moe — port effort vs wait-for-hardware decision
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
- **sylveste-bpw** Phase 1: Bring up local inference pipeline
- **sylveste-m71** Publish Pareto frontier analysis: speed vs quality across local models _(blocked)_
- **sylveste-qbv** Experiment: LayerSkip / self-speculative early exit _(in progress)_

### interflux
- **sylveste-9lp.15** P2: Structured disagreement as first-class output — disagreement_profile in findings schema
- **sylveste-9lp.16** P2: Research mode parity — add peer findings, reaction round, sycophancy detection to research path
- **sylveste-9lp.17** P2: Passage-level citation in research synthesis — attribute claims to source passages, not agents
- **sylveste-9lp.18** P2: Evaluation rubrics — track finding recall, precision, coverage over time
- **sylveste-9lp.19** P2: Difficulty-aware slot ceiling — replace static formula with content-signal estimator _(blocked)_
- **sylveste-9lp.20** P2: Embedding-based dedup pass — cosine similarity on finding titles for conceptual duplicates
- **sylveste-9lp.21** P2: Typed agent-state log — JSONL per agent replacing in-prompt state tracking
- **sylveste-9lp.22** P2: Trust model diagnostics — explain low scores and feed back into prompt tuning
- **sylveste-9lp.32.7** BP-C1.C: extract scripts/_fluxbench_score.py from fluxbench-score.sh heredoc (180 lines)
- **sylveste-9lp.35.6** BP-C2.B: run_uuid quire-mark + decisions.log per-run
- **sylveste-fyo3.6** P2: Hard budget enforcement mode — test and enable blocking behavior
- **sylveste-fyo3.7** P2: Interspect overlay activation — promote from progressive enhancement to default
- **sylveste-wyoi** Brainstorm-to-roadmap lift discipline — checklist step in /interpath:roadmap

### interspect
- **sylveste-sfhq** Telemetry fusion: wire tool-time stats into interspect evidence

### interstat+galiana
- **sylveste-z7zh** Landed-work recap report (Goodhart-aware)

### microrouter
- **sylveste-5p7s** F2: D2 heuristic-baseline measurement — sibling to .19.9, parallel-runnable _(deferred)_
- **sylveste-s3z6.19.6** Privacy-routing extension — sensitive tasks always engage router _(blocked)_

### routing
- **Sylveste-2bg** Re-measure heuristic coverage after agent-roles.yaml extension _(blocked)_

### spike
- **Sylveste-0gi.2** DeepSeek V4 → flash-moe 5-day feasibility spike (C-prime)

### sylveste
- **sylveste-00qu** beads: 3 UX/correctness issues (bd dolt push help-on-no-remote, missing embedded-DB bootstrap from issues.jsonl, persistent 0755 permission warning)
- **sylveste-05rf** Auraken lens cleanup: cross-referencing pairs that may be authoring drift not distinct lenses
- **sylveste-06yf** Refactor interfer onto MCP SDK or scope out of consolidation (prereq for sylveste-7505)
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
- **sylveste-1zei** F4: User discrimination tracker — profile schema + advancement logic
- **sylveste-22oi.3** Auraken v0.2: GPG signing pipeline for checksums.txt.asc
- **sylveste-22oi.7.3** Cognitive profile: extraction pipeline (trajectory + conversation -> entities) _(blocked)_
- **sylveste-22oi.7.4** Cognitive profile: auraken-profile MCP server (mirror auraken-lens) _(blocked)_
- **sylveste-22oi.7.5** Cognitive profile: epistemic engine (promotion + half-life decay + harpoon test) _(blocked)_
- **sylveste-22oi.7.7** Cognitive profile: pattern-awareness SKILL behaviors (Journeys 2/7/21 + harpoon hook) _(blocked)_
- **sylveste-2xzz** Thinker-profile schema v1 (YAML + validation harness)
- **sylveste-301b** Diagnose interstat tool_selection_events ↔ agent_runs session_id join gap
- **sylveste-34r2** F5.2: Go-Python persistent worker bridge _(blocked)_
- **sylveste-35x5** Migrate interlens to high-level MCP TS SDK (prereq for sylveste-7505)
- **sylveste-39p5** F5: TypeScript plugin adapters (interfluence,interlens,interrank,tuivision) _(blocked)_
- **sylveste-3a2r** QDAIF diverse perspectives in synthesis (rsj.5 successor)
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
- **Sylveste-407** Research spike: holdout register as first-class primitive across calibration loops
- **Sylveste-4b5.10** LLM-judge bias doc-hygiene + gate-hardening rider (no new judge epic)
- **Sylveste-4b5.11** Make the close-gate parallel-safe: forbid green against a SHARED runtime (false-green guard) _(blocked)_
- **Sylveste-4b5.12** Audit-plane correlation layer (deferred, three-feed + consumer gated)
- **Sylveste-4b5.13** Trust-card: glanceable per-task human review surface from existing evidence
- **Sylveste-4b5.14** ACE coding-skill playbook vs compound-baseline bake-off (measurement-gated spike) _(blocked)_
- **Sylveste-4b5.15** Pass@k harness extension + kill-gated test-time-compute scaling spike _(blocked)_
- **Sylveste-4b5.16** Skaffen compaction verification + context-rot working-set instrumentation _(blocked)_
- **Sylveste-4b5.5** Ground review verdict in concrete pass/fail signal (downgrade unverified 'clean') _(blocked)_
- **Sylveste-4b5.6** Wire clavain policy engine into a real fail-CLOSED PreToolUse interdiction hook _(blocked)_
- **Sylveste-4b5.7** Pre-dispatch parallelizability + cost gate folded into the 3kol Conductor spec
- **Sylveste-4b5.8** Conflict-economics telemetry on the parallel dispatcher (child of 3kol)
- **Sylveste-4b5.9** campaign.md route-to-fallback-on-verified-failure (replace blind retry/skip/abort) _(blocked)_
- **sylveste-4li0** interop: daemon adapter construction from config
- **sylveste-4uvh** F5.4: Multi-connector query templates (4 composite queries)
- **sylveste-5boi** Signal command: log (recent forge sessions)
- **sylveste-5bwp** F1: FluxBench metric definitions + local scoring engine _(blocked)_
- **sylveste-5ca9** F2: Judicial holdings format — restructure 30 DQs with condition/rationale/scope
- **sylveste-5gr4** F3: AgMoDB write-back via store-and-forward _(blocked)_
- **sylveste-5hx7** Signal command: diff (re-show pending changes)
- **sylveste-5jn8** Auraken lens_select latency: 12-20s per call is real UX cost (dogfood finding)
- **sylveste-5lla** Load-path independence audit of the evidence-infra ring
- **sylveste-6m1k** F3: interserve-ts adapter framework _(blocked)_
- **sylveste-6zhe** Add Sylveste affected-module build and test runner
- **sylveste-7aj8** Interspect skill calibration
- **sylveste-7aj8.9** interspect skillcal: collector coverage — no_redirect/tokens drop ~97% of rows
- **sylveste-7g96** F3: Prebuilt auraken-lens Go binaries for 4 platforms (v0.1.0) _(blocked)_
- **sylveste-7ps** F4: Confidence scoring + link provenance _(blocked)_
- **sylveste-8au** F6: Query-context salience _(blocked)_
- **sylveste-8mbr** Ecosystem simplification Phase 2 (jrua successor)
- **sylveste-8ucm** F5.3: Core query templates (4 pure queries) _(blocked)_
- **sylveste-92bq** F2: Qualification test fixtures with ground-truth findings
- **sylveste-9g6v** F2: Beads adapter — bidirectional bd CLI sync _(blocked)_
- **sylveste-9owj** F1: Difficulty ladder — order 30 near-miss pairs by discrimination difficulty
- **sylveste-a4oj.9** Phase 2 — Dirty-bit and routing replacement infrastructure (S-difficulty bundle)
- **sylveste-am7w** Meadows profile (validation anchor — 12 leverage points rediscovery test) _(blocked)_
- **sylveste-amcz** F2: interserve-py adapter framework _(blocked)_
- **sylveste-benl.11** Decommission Auraken Python runtime
- **sylveste-bsh1** Frame activation + scaffold integration in Auraken runtime _(blocked)_
- **Sylveste-byw** interhelm/intersight: resolve dual tracking between umbrella and standalone repos
- **sylveste-ci9m** F4: Evolution tracker (EMA, Store interface, persistence) _(blocked)_
- **sylveste-cqa** Port interblog content collections to /blog/ with one-way sync
- **sylveste-csa7** F5: Lens stack transition model — reference-frame inversion orchestration
- **sylveste-d7w** F7: Gravity-well safeguards
- **sylveste-dd6t** Rate limiting for forge code commands
- **Sylveste-dvw** Research spike: execute pre-registered F6b flux-drive triage A/B (sylveste-g939)
- **sylveste-e8te** F5: INSTALL.md + canonical two-step install path _(blocked)_
- **Sylveste-e9c** Make beads post-merge handler run 'bd import' so git pull auto-syncs Dolt (real fix behind the sync-guard advisory)
- **sylveste-ewy3.1.3** Mythos+1mo decision gate: Temporal full-migration vs. dual-path
- **sylveste-ewy3.2.3** Mythos+1mo decision gate: Langfuse primary vs SQLite + Langfuse shadow
- **sylveste-f314** Appleton profile (structure-rich corpus test) _(blocked)_
- **sylveste-fa1m** Gmail purchase import pipeline (fbz successor)
- **sylveste-fd7x.7** Resolve intersite plugin repository remote/publish target _(blocked)_
- **sylveste-feto** Working profile cold-start for new users
- **sylveste-fij2** F5: Local filesystem adapter — fsnotify, SHA-256 change detection _(blocked)_
- **sylveste-g78** Tuivision: clean install path for viral adoption
- **sylveste-gd3q** Repackage Interspect and consolidate evidence telemetry boundaries
- **sylveste-h4mw** F1: interserve plugin scaffold _(blocked)_
- **sylveste-islh** F3: Interspect activation aggregator (race-fixed cursor + dedup) _(deferred)_
- **sylveste-j0yv** F5.5: Shared resolution primitives _(blocked)_
- **sylveste-j7gy** F5: Plugin manifest annotations + 5-plugin reference adoption _(deferred)_
- **sylveste-jp1l** interjawn MCP server fails to start — Prisma ESM export error
- **sylveste-jqxf** AI Factory Wave 1 foundation (ysxe successor)
- **sylveste-jsyc** F6: Big-bang cutover — remove legacy mcpServers entries _(blocked)_
- **sylveste-jum2** Precompile interrank TypeScript at publish time (drop tsx runtime) _(blocked)_
- **sylveste-lbvq** F4: Python plugin adapters (intercache,interdeep,interfer,interject,intersearch,interseed) _(blocked)_
- **sylveste-lf3b** Rename fd-agent personas with misleading lexical-prefix collisions
- **sylveste-lfdy.1** Wire jetty.io as eval substrate for Auraken voice + behavioral signature scoring _(blocked)_
- **sylveste-lkbq** Runtime sycophancy detection in synthesis (rsj.6 successor)
- **sylveste-llen** Strengthen natural-language feedback loop for self-improvement
- **sylveste-lny4** Self-dispatch loop for AI factory (ysxe.3 successor)
- **sylveste-lon1** Cross-model dispatch scoring + integration (9lp.9 successor)
- **sylveste-lwp7** lattice: apply_lifecycle_transition mutates et.families in registered EntityType
- **sylveste-m2p** F4: Garden Salon agent bridge for interseed _(blocked)_
- **sylveste-m36b** F6: SKILL.md curation + voice-rubric.md (Mandatory Form / Permitted Variation) _(blocked)_
- **sylveste-mblb** F2: Subsystem emit helper (Go + bash) with durable session sentinel _(deferred)_
- **sylveste-mf6n** F5.1: QueryTemplate protocol + TemplateRegistry _(blocked)_
- **sylveste-mij3** Install sqlite3 CLI on zklw + re-derive cost-per-landable-change baseline
- **sylveste-nr6x.4** L4: Signal-native tool approval transport
- **sylveste-nr6x.5** L5: Skaffen integration — sovereign agent lifecycle
- **sylveste-nyx** Hidden /about page with mission/vision from GSV identity repo
- **sylveste-o8wo** Fix subagent Write permission for flux-gen-specs and docs/research/flux-* directories
- **sylveste-oej5** F10: auraken-lens Go CLI binary wrapper (cmd/auraken-lens) _(blocked)_
- **sylveste-owjn.3** Extend observation.Snapshot to a true superset (artifacts map + phase-advance history) so ic situation snapshot fully replaces lib-sprint.sh ad-hoc queries
- **sylveste-p6so** F8: GitHub release auraken-distribution/v0.1.0 + signed checksums + CHANGELOG _(blocked)_
- **sylveste-pexq** Audit Python MCP servers for lazy top-level imports _(blocked)_
- **sylveste-pf4** intersite-blog: blog fold-in + full pipeline enforcement
- **sylveste-pfi** F5: Signal feeds + graduation workflow _(blocked)_
- **sylveste-q2k** F6: Autonomy ratchet state machine _(blocked)_
- **sylveste-q588** Download Q3 GGUF for Qwen3.5-397B (l2j successor)
- **sylveste-qhn1** interverse hygiene: root go.work + 3 READMEs + DEPENDENCIES.md + HOOKS-REGISTRY.md
- **Sylveste-qm2** interlock tier-2: embedding-based semantic conflict detection in pre-edit hook
- **sylveste-qroh** F6: interrank TASK_DOMAIN_MAP FluxBench integration _(blocked)_
- **Sylveste-rgj** Research spike: null test — does multi-agent coordination beat single-strong-model on our task mix?
- **sylveste-rom** Full pipeline enforcement: MDX stripping, HMAC webhook, preview gating
- **sylveste-rsj** EPIC: Sylveste SOTA — Garden Salon Architecture
- **sylveste-rsj.3** Roguelike-Inspired Agent Architecture — structural patterns from NLE/BALROG/Arcgentica for Garden Salon
- **sylveste-rsj.3.14** Run BALROG TextWorld baseline: raw model vs Skaffen-orchestrated progression comparison
- **sylveste-rsj.3.5** Evaluate Agentica SDK as complementary agent framework — type-safe multi-agent with stateful REPL
- **sylveste-rsj.8** Stigmergic coordination substrate — pheromone fields with decay on shared documents
- **sylveste-s01c** Drop lattice->attp local-path replace (close iv-v5ayb residual)
- **sylveste-s288** F4: install.sh — atomic, gated, transmissive close _(blocked)_
- **sylveste-sn7** Tuivision: token-efficient terminal state encoding
- **sylveste-sn7.1** Add 'annotated' get_screen format with inline markers [r]error[/] _(blocked)_
- **sylveste-sn7.10** Add ROI (region-of-interest) encoding — high fidelity for active regions only
- **sylveste-sn7.11** Separate UI chrome (borders, status lines) from content in output
- **sylveste-sn7.12** Add channel-selective encoding — callers choose which attributes to include
- **sylveste-sn7.13** Add session-local dictionary for repeated content patterns
- **sylveste-sn7.14** Fix alternate screen buffer detection for cursor position
- **sylveste-sn7.15** Add generative encoding for structured UI — template+data instead of full render
- **sylveste-sn7.16** Add information hierarchy (L0/L1/L2/L3) to all output modes
- **sylveste-sn7.17** Add multi-pane marshalling — named pane composition for tmux/splits
- **sylveste-sn7.18** Add task-adapted rendering profiles (interactive/content/structure)
- **sylveste-sn7.19** Add agent backchanneling — LLM negotiates detail level
- **sylveste-sn7.2** Fix default get_screen format from 'full' (12K tokens) to 'compact'
- **sylveste-sn7.20** Add color semantics lookup table for common terminal applications
- **sylveste-sn7.21** Explore occlusion culling — skip background content behind modal dialogs
- **sylveste-sn7.22** Document vision token cache disadvantage for multi-turn agent sessions
- **sylveste-sn7.3** Add color quantization — map hex to 16 named colors _(blocked)_
- **sylveste-sn7.4** Preserve inverse boolean for selection/focus semantics _(blocked)_
- **sylveste-sn7.5** SVG span-merging — group same-styled adjacent cells _(blocked)_
- **sylveste-sn7.6** Add motif/summary LOD level (L0) for polling tasks
- **sylveste-sn7.7** SVG CSS class dictionary — deduplicate repeated class/color attributes
- **sylveste-sn7.8** Add diff/delta mode with auto-refresh every 5 turns
- **sylveste-sn7.9** Add semantic role annotations (ARIA-like) for terminal elements
- **sylveste-t5x4** auraken-thinker MCP server (sibling to auraken-lens) _(blocked)_
- **sylveste-t615** intercore ic publish: atomic publish / rollback-on-failure
- **sylveste-td2o** Brainstorm-summary feedforward into plan review (review <- plan,brainstorm)
- **sylveste-tfj7** F7: Challenger slot mechanism for unqualified candidates _(blocked)_
- **sylveste-ttwz** Triage Python MCP servers for Go port candidates (hot-path first) _(blocked)_
- **sylveste-txky** Publish 9 plugin patches carrying sylveste-ynh7 skill-desc trims to cache _(blocked)_
- **sylveste-u28h** CPVO + DWSQ domain-general north star metrics (rsj.4 successor)
- **sylveste-u74g** F7: build-dist.sh — deterministic bundle assembly _(blocked)_
- **sylveste-uhjv** audit.log producer dormant — log-tool-invocation.sh not wired into settings.json
- **sylveste-ukd3** lattice-web V0 — static browse + search at interverse/lattice/web/ _(blocked)_
- **sylveste-ung7** Reconsider sylveste-7505 consolidation given spike C findings (cold-start math doesn't favor it) _(blocked)_
- **sylveste-ungg** Local plan-phase check in /work + /execute-plan (intercore-independent)
- **sylveste-usj** F5: Tier 1 INFORM signals + pleasure signals _(blocked)_
- **sylveste-usvf** F5: Proactive model surfacing — SessionStart + weekly schedule _(blocked)_
- **sylveste-uzpo** Interface evidence instrumentation — 5 cross-subsystem signals
- **sylveste-v4t2** Meadowsyn experiment suite (jpum successor)
- **sylveste-vsi4** F6: MCP server + Claude Code plugin _(blocked)_
- **sylveste-w8zv** Rename github upstream mistakeknot/interweave → mistakeknot/lattice + update go.mod
- **sylveste-wdf2** Doc monitoring automation (replaces interscout shape)
- **sylveste-wdf2.2** L2: PreToolUse hook surfaces drift on doc access; auto-fire on Certain _(in progress)_
- **sylveste-wlk** Publish seed experiments after voice review
- **Sylveste-wrz** Clavain: restore README count line + publish project-onboard update (0.6.252)
- **Sylveste-x2c** Research spike: re-test 'MLX has no concurrent inference' premise (mlx-lm 0.18+) before sylveste-4wl burns on it
- **sylveste-x6e4** Multi-mcpServers capability spike (prereq for sylveste-7505) _(deferred)_
- **sylveste-xfsr** F3: GitHub adapter — App webhooks, Issues, PRs, repo files _(blocked)_
- **sylveste-xle6** Forge F3 artifact pipeline (sttz.3 successor)
- **sylveste-xmav** F4: Notion adapter — pages, databases, webhooks (port from interkasten) _(blocked)_
- **sylveste-xoki.1** Codex discovery hygiene: fix stale skill/frontmatter and cache noise
- **sylveste-xoki.2** Agent evidence receipts for Codex and Claude Code
- **sylveste-xoki.3** Plugin and skill architecture deprecation plan
- **sylveste-ya2** F2: Auraken idea capture via /idea command _(blocked)_
- **sylveste-ye7y** F4: Drift detection — sample-based + version-triggered _(blocked)_
- **sylveste-yrc** clavain-cli not on PATH after monorepo clone
- **sylveste-ysny** Skill calibration: signal density too low to trust scoring — gate autonomy on it _(in progress)_
- **sylveste-yxk8** F6: North Star integration + observation methodology + Goodhart breaker _(deferred)_

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
- **Sylveste-rkm** Policy-engine audit — bd-push-dolt safety semantics + dead audit/sign surface

### interfer
- **sylveste-7hxm** Route-heuristic-coverage interlab campaign
- **Sylveste-uk3** OpenRouter stream usage block omits reasoning_tokens — gen_tps/cost telemetry undercounts on bvh _(in progress)_

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

### interproof
- **sylveste-ayl** Manual-driven feature validation plugin

### interspect
- **sylveste-sfhq.4** Tool-remediation canary + revert plumbing (sfhq.3 follow-up) _(in progress)_

### interstat
- **Sylveste-xvt** Investigate hash-ID fallback: 70% of subagent rows have unparseable agent_name

### routing
- **Sylveste-23w** Propagate verify_frontmatter.py + routing-drift workflow to sibling subrepos
- **Sylveste-7zi** Investigate fd-architecture/fd-systems opus-vs-sonnet disagreement

### scoping
- **Sylveste-s10** Small-local-model (sub-10B) workload candidates after microrouter cluster close _(in progress)_

### sylveste
- **Sylveste-05t** Research spike: self-speculative decoding via native MTP heads on downloaded MoE checkpoints
- **Sylveste-0ww** Research spike: null-test graph/lens retrieval vs naive baseline on real Auraken/lattice queries
- **sylveste-1h0b** Build Komoroske profile via proven pipeline (return from deferral) _(blocked)_
- **sylveste-22oi.6** Reconcile stale non-dist SKILL.md duplicate in Auraken Hermes tree
- **Sylveste-31v** Run install-macos.sh on Mac to restore claude-plugin-cleanup.sh + LaunchAgent _(blocked)_
- **sylveste-3x5** Interject discovery pipeline: submit lens discoveries
- **sylveste-3xl3.5** Audit fd-* and researcher agent definitions for teammate-role reuse
- **sylveste-3xl3.6** Plan-approval teammate mode → quality-gates / authz framework integration
- **sylveste-3xl3.8** flux-explore --teams Approach 3: full team-driven exploration _(blocked)_
- **Sylveste-46v** Clavain: clean stale publish_state rows + audit cross-marketplace drift
- **Sylveste-4b5.17** Conductor (3kol) topology doc-hygiene: record flat-fan-out structural rule
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
- **sylveste-8g69** Thompson profile or substitute (analytical-framework consistency test) _(blocked)_
- **sylveste-8qk** F8: Philosophy amendment + documentation
- **Sylveste-942** Fix /Users/arouth hardcoded path in com.arouth.claude-plugin-cleanup.plist
- **sylveste-9prl** Wei profile (rare-frame detection test) _(blocked)_
- **sylveste-9xyh** beads: bd dolt status errors with 'not supported in embedded mode' but bd dolt help lists it unconditionally under Server lifecycle
- **sylveste-a4oj.10** Phase 3 — Infrastructure-class improvements (M+ difficulty bundle)
- **sylveste-a4oj.12** Memory depth-tiered archiving: project_status frontmatter + close-off depth automation
- **sylveste-a4oj.14** M-01 follow-up: per-project user-scope MCP server suppression (mcpProfile-equivalent)
- **sylveste-a4oj.9.3.1** Semantic-embedding dup detection (extends 9.3 lexical baseline)
- **sylveste-ai8c** Mutation engine — mutation types in campaign YAML (vd1 successor)
- **Sylveste-aso** Umbrella gitignore: docs/research/*/ rule is leaky for nested content
- **sylveste-b06** Migrate ~/dotfiles to yadm with host-conditional alternates
- **Sylveste-bgj** Unify docs/prd/ and docs/prds/ directory structure
- **sylveste-c231** Add quarantined-worktree disposal runbook to Sylveste docs (generic version of elf-revel solutions doc)
- **sylveste-dxt7** intercore gate-rule registry (OS-layer extensibility)
- **sylveste-e20** /intersite:publish with atomic swap deploy
- **sylveste-fba8** Hardware-aware model recommendations in interrank (1ifn successor)
- **sylveste-fdn** 301 redirect: blog.generalsystemsventures.com to /blog/
- **sylveste-fj1w** Clavain peer-coexistence B′ — peer-aware using-clavain + peers.yaml registry (gated on telemetry)
- **sylveste-gaid** Auraken: SKILL.md cross-model voice portability — potential research finding
- **sylveste-gw6** WebSocket PTY relay service at apps/intersite-relay/
- **sylveste-hfmh** Retire interscout plugin (deprecated 2026-04-27)
- **sylveste-hvmc** intermute live transport v1.5: active-probe readiness check (replaces 2s staleness)
- **Sylveste-i3h** Research spike: expert-activation traces → Belady-approximating cache policy for flash-moe
- **sylveste-jciw** clavain-cli sprint-init gate diverges from bd doctor (false-positive '1 error(s)')
- **sylveste-lbkd** Sprint v2 artifact bus + progress trackers (lta9 successor)
- **sylveste-lgci** A:L4 — evaluate skill-selection calibration as a 4th autonomy loop (post-v0.7)
- **sylveste-liiu** Per-hook preamble byte telemetry for automatic regression detection
- **sylveste-lpnd** ATTP attestation protocol for interweave (e1mi successor)
- **sylveste-m5g** intersite-relay: xterm.js dev panel + WebSocket PTY relay
- **sylveste-nr6x.12** Infra: install signal-cli + register hassease Signal account
- **sylveste-nxfq** sprint: automated import-graph assertion from plan's structural requirements
- **Sylveste-omz** Research spike: temporal fact-invalidation (t_valid/t_invalid) for intermem
- **sylveste-ovux** Upstream Hermes skill frontmatter aliases (support /ak for /auraken natively)
- **sylveste-p2yj** Go benchmark-driven optimization for Skaffen hot paths (0pvp successor)
- **Sylveste-r5t** Clavain: investigate skill-precedence — ~/.claude/skills/ override didn't beat cached plugin SKILL.md
- **sylveste-rm8w** lattice: function diagnostic property mismatch (families.py vs diagnostics.py)
- **sylveste-rsj.3.4** Permaconsequence visibility: make cross-session evidence compounding visible in Garden Salon UX
- **sylveste-rsj.3.6** GameDevBench integration: add game-building benchmark alongside SWE-bench for complex multi-file evaluation
- **Sylveste-ry3** Research spike: orchestrator-visibility safety audit (hidden dispatch vs dissent suppression)
- **Sylveste-sox** xp7-c: investigate why Claude Code plugin auto-loader silently drops interlock hooks
- **Sylveste-tpc** Research spike: lens authoring-drift pairs (sylveste-05rf) as semantic versioning
- **sylveste-tsvw** intercore coordination quota/fairness (pre-scale insurance)
- **sylveste-u6fj** F7: interkasten migration + archival _(blocked)_
- **Sylveste-va4** Research spike: M5 Neural Accelerator prefill/decode asymmetry measurement
- **sylveste-w4sj** v1.0 roadmap artifact publishing (enxv successor)
- **sylveste-wdf2.3** L3+L4: /schedule routines for floor refresh and monthly audit
- **Sylveste-xci** interverse/interweave: untrack committed __pycache__ files
- **sylveste-xdsu** Meta-improvement campaigns — mutation store MCP tools (7xm8 successor)
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
- **Sylveste-10p** Add pre-commit hook layer for frontmatter drift (light gate) _(in progress)_
- **Sylveste-vft** Drift baseline ratcheting — committed .routing-drift-baseline file

### sylveste
- **sylveste-wdf2.4** L5 (deferred): Substrate-independent external replay
- **sylveste-yofd** Clavain peer-coexistence C′ — full rig manager (profiles, lockfile, per-skill priorities, rig CLI)
- **sylveste-zfsj** intermute live transport v2: cross-host (SSH + tmux orchestration)
