# Backlog Judgment Digest — 2026-06-22

Autonomous backlog run. 213 ready (unblocked, leaf) items triaged by an 8-agent workflow:

| Bucket | Count | Disposition |
|---|---|---|
| **auto-executable** | 14 | Executing now (execute→verify, commit-on-PASS) — separate report |
| **needs-judgment** | 112 | **This document — your call** |
| too-large | 43 | Real multi-day features; need scoping/planning, not execution |
| blocked-in-disguise | 35 | Hidden deps on unfinished work |
| epic-or-meta | 9 | Tracking shells, no direct work |

The 112 judgment items are clustered by *the kind of decision required*. Most need a yes/no, a taste call, or a scope decision — not implementation labor.

---

## ⚡ Quick wins hiding in "judgment" — verify & close (4)
These were flagged because the triage agents found the spec **already satisfied in shipped code** (`core/interweave/templates/protocol.py`). They likely just need you (or me, with your OK) to confirm-and-close rather than implement:
- **sylveste-foui** (P1) — per-source freshness timestamps: `data_freshness` already ships
- **sylveste-rrn4** (P1) — template version attribute: `version`/`template_version` already ship
- **sylveste-t6ti** (P1) — canonical-crosswalk-ID contract: already documented + enforced in `validate()`
- **Sylveste-aso** (P3) — gitignore leaky-rule (verify the rule's current behavior)

→ **Decision:** want me to verify each against the code and close the ones that are genuinely done? (Low risk; reversible.)

---

## 🎨 Product / UX / branding — pure taste (7)
Your aesthetic and product instincts, not mine:
- **sylveste-cnxf** (P1) — gsvdotcom ACRNM-inspired visual redesign
- **sylveste-33y** (P1) — annotated format spec (escaping/composition/versioning conventions)
- **sylveste-lf3b** (P2) — rename fd-agent personas (misleading lexical prefixes)
- **sylveste-05rf** (P2) — Auraken lens cleanup: which cross-ref pairs are drift vs distinct
- **sylveste-e8te / g78 / s288** (P2) — install-path UX ("viral adoption", "transmissive close")

---

## 🧭 Strategy / decision / tradeoff (3 explicit + others)
Binary calls only you can make:
- **Sylveste-0gi** (P2) — DeepSeek V4 Flash port: invest effort now vs wait for hardware
- **sylveste-ewy3.2.3** (P2) — Mythos+1mo gate: Langfuse primary vs SQLite+Langfuse
- **sylveste-q588** (P2) — download Q3 GGUF for Qwen3.5-397B (disk/time commit)
- **Sylveste-byw** (P2) — interhelm/intersight dual-tracking: pick one source of truth (repo restructure)

---

## 🔬 Research / evaluate / spike (16)
"Study X / benchmark Y / decide whether to adopt" — output is a recommendation, not a verifiable diff. Many are interfer/local-model experiments (ANE offload, MLA, speculative decoding, ant-colony expert routing). **These are good `/sprint` or `/interlab` candidates** if you want them pursued; otherwise they sit.
- Notable P1s: **sylveste-krop** (lazy MCP enablement spike), **sylveste-rcn8** (companion-agent research: Soren/Pi/Replika)

---

## ⚠️ Irreversible — publish / external / mutation (17)
I deliberately won't auto-do these (publish, external provisioning, repo mutation). Each needs your go:
- **sylveste-ewy3.1.1** (P1) — Temporal Cloud account/namespace + credentials (external signup)
- **sylveste-agr2** (P1) — Signal `undo` command (does `git revert` on user repos)
- **Sylveste-wrz / txky / p6so / w4sj** — publish actions (plugin patches, GitHub release, roadmap artifact)
- **sylveste-hfmh** (P3) — retire interscout plugin (deprecation)
- **sylveste-b06** (P3) — migrate dotfiles to yadm

---

## 🏗️ Design / schema / contract (26)
Interface and schema decisions with downstream blast radius — need an architectural call before code:
- P0/P1: **sylveste-248r** (onboarding intake protocol), **sylveste-te7b** (interflux↔intersynth synthesis contract), **sylveste-clha** (office-hours adversarial gate), **sylveste-sk5s** (shipped-state reconciliation gate), **sylveste-4wq6** (lens trajectory schema)
- Many v6-candidate Ockham schema items (P2): `9um7`, `aon0`, `2xzz`, etc.

---

## 🛡️ Governance / policy / trust (6)
Trust-lifecycle and policy design — strategic, abstract:
- **sylveste-4rwh** (P1) — add "Break" stage to trust lifecycle (Earn→Compound→Break→Epoch)
- **sylveste-v3ck** (P1) — demotion-rehearsal as M3+ promotion precondition
- **sylveste-2o0s** (P1) — flux-review ephemeral read-only mode + cost controls

---

## 🔎 Investigation / root-cause (9)
Open-ended "diagnose X" — no fix specified; could go several ways. Good `/clavain:repro-first-debugging` candidates:
- **Sylveste-bov** (P2, interfer decode regression 5 vs 20 tok/s), **sylveste-jp1l** (interjawn Prisma ESM start failure), **Sylveste-wfz** (TurboQuant test failure), **sylveste-301b** (interstat session-join gap)

---

## 🔧 Upstream tool (bd / external) (4)
Fixes that live in the external `bd` tool or other upstreams — not local edits:
- **Sylveste-e9c**, **sylveste-00qu** (bd UX/correctness), **sylveste-w8zv** (rename github upstream), **sylveste-ovux** (Hermes frontmatter aliases)

---

## How I'd suggest triaging this
1. **Cheapest win:** approve the 4 "verify & close" — likely already done.
2. **Highest leverage that needs you:** the design/contract P0/P1s (`248r`, `te7b`, `sk5s`) — they unblock downstream work and only need a direction from you, after which I can execute.
3. **Batch-defer:** the 16 research spikes and 43 too-large items — these want dedicated `/sprint` sessions, not this autonomous pass.
4. **Tell me which clusters to pursue** and I'll spin up scoped workflows (e.g., "do the verify-&-close batch", "draft the synthesis contract for your review").

Full machine-readable clustering: `$CLAUDE_JOB_DIR/tmp/backlog-run/judgment-clusters.json`
