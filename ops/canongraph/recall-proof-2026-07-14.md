# Recall unification proof — 5 questions, per-lane vs unified (2026-07-14, goal mk-1pd.4)

Method: each question was run against all four lanes live (canongraph MCP queries, qmd
lex+vec, memory-file index, `bd memories`) on 2026-07-14. "✅" = lane produced a usable
answer; "—" = lane silent (correctly or not).

| # | Question | Graph (C3) | qmd (C4) | Memory files (C5) | bd (C5) | Unified outcome |
|---|----------|-----------|----------|-------------------|---------|-----------------|
| 1 | What did we decide about jawncloud auth? | ✅ 4 decisions w/ rationale, dates, made_by (sole-SSO, Supabase→Clerk, subdomain-over-satellite, Google-only beta) | — | — | ~ (one tangential run memory) | **Graph-only.** Any file-lane recall would have missed all four ratified calls. |
| 2 | Where does oodacademy live and what is it? | ✅ description + canonical_home + hosted_on zklw | — | ✅ rehome detail (Neon+Pages frozen as rollback, pg :5440, B2) | — | **Merge required.** Graph has the live shape; memory has the migration rationale/rollback. Neither alone is complete. |
| 3 | What are the beads/Dolt setup gotchas? | — (correctly silent: pattern, not entity) | ✅ sprint transcript (shared data dir, port confusion, 0.93) | ✅ reference_zklw_beads_new_repo (shared :3308 server, bd init unreliable) | n/a (bd is the subject) | **qmd+memory combine**; graph stays out of its lane. |
| 4 | Who is Joe and what's our relationship to his project? | ✅ person (github, role) + works_on + upstream_of + adopt/PR decisions | — | ✅ PR-watch action pointer | — | **Graph primary**, memory adds the "watch PR #1" action. |
| 5 | How do I copy text out of tmux on macOS Terminal? | — (correctly silent) | — | ✅ Option-drag; OSC 52 dropped by Terminal.app, works in Ghostty/iTerm2 | — | **Memory-file-only.** Graph/qmd-first recall without the file lane would fail. |

## Verdict

- Best single lane answers **3/5** (memory files); graph alone 3/5; qmd alone 1/5; bd alone 0/5.
- Unified fan-out answers **5/5**, and on Q2/Q4 produces a *better* answer than any lane alone (live-state + rationale merged).
- Lane-discipline held: the graph was silent exactly where it should be (patterns, behavioral how-tos), confirming the memory-lanes capture policy is producing separable, complementary lanes rather than copies.

Shipped in `/clavain:recall` (C3 graph step 1.5, qmd-preferred legacy, bd step 4.5,
provenance-ranked merge) — Clavain 52d5237; lane map in `recall-lanes.md`.

## Re-run 2026-07-15 (post lane-migration, goal mk-1ei)

After migrating 38 world-fact memory files into graph documents (files → pointers,
MEMORY.md 152→72 lines): **unified 5/5 maintained.**
- Q1 graph decisions unchanged (4 jawncloud auth decisions w/ rationale).
- Q2 now answers **graph-complete**: `project_card` (live shape) + `search` (rehome
  rationale/rollback from migrated doc) — previously required the file lane.
- Q3/Q5 unchanged: how-do-I files (`reference_zklw_beads_new_repo`,
  `reference_tmux_copy_macos_terminal`) deliberately NOT migrated — the file lane
  keeps behavioral/how-to content per memory-lanes policy.
- Q4 graph gained the `works_on` Joe Vattimo→canongraph edge; watch file kept.
- Consumer fix shipped same day: recall step 1.5 gained the `mcp__canongraph__search`
  document-lane call (Clavain 0.6.274) — without it, migrated content was invisible
  to unified recall.
