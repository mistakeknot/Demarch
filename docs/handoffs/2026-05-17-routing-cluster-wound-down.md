---
date: 2026-05-17
session: 900667a0
topic: Routing cluster wound down + V4 Day-2 shipped
beads: [Sylveste-onp, Sylveste-0gi.2.5, Sylveste-0gi.2.6, Sylveste-0gi.2, sylveste-s3z6.19.5, sylveste-s3z6.19.6, Sylveste-zge, Sylveste-23w, Sylveste-vft, Sylveste-10p, Sylveste-9ve]
---

## Session Handoff — 2026-05-17 Routing cluster wound down + V4 Day-2 shipped

### Directive

> Your job is to kick off **V4 spike Day-3 (CPU-reference forward path)**. Calendar kill-rule: EOD 2026-05-19, so ~2 working days left. Start by reading `/Users/sma/projects/flash-moe/docs/spikes/deepseek-v4-architecture-delta.md` §10 (Day-2 kernel-math closure) and §7.2 (Day-3 forward-path plan), then build `python/spike/cpu_ref_forward.py` in the flash-moe spike branch that loads `/Users/sma/Models/DeepSeek-V4-Flash-upstream/` via `transformers v5.8.1 + accelerate device_map="auto"`, runs ONE short prompt (≤32 tokens), and writes the `(seq_len, vocab=129280)` logits at FP32 to disk via safetensors. Verify by re-running the same prompt under the flash-moe port and computing top-K cos-sim (target ≥0.999).

- **Active beads:** Sylveste-0gi.2 (in_progress, spike epic, P2). All its prereqs are CLOSED (.2.5 download, .2.6 config BC).
- **No active processes** — download finished cleanly (149GB on disk, exit 0, 46/46 shards).
- **Memory pressure on M5 Max is the day's primary risk** — 149GB FP4/FP8 exceeds 128GB unified memory. Disk-page locally first; if intolerably slow, rent RunPod H200 (~$5-10 for one forward pass). Decide AFTER benchmarking local paging.
- **Fold §10.8 doc corrections** into the architecture-delta doc before or alongside Day-3 work: (a) §1.1 + §8 say "StreamingLLM" for `attn_sink` — wrong, it's GPT-OSS pattern (§10.5); (b) §6.4 partition labels need tightening; (c) §6.5 `wgate` is softmax-over-window not GLU; (d) "HCA" is overloaded — disambiguate compressor vs HC mixer.

**Fallback work if Day-3 stalls or you choose to pivot:**
- Sylveste-9ve (P4): investigate whether Explore subagent dispatches stopped on 2026-04-21 due to workflow shift or instrumentation regression. 30 min check.
- Sylveste-benl epic (P0): Auraken→Skaffen Go migration, several P1 children open.
- F5 query-result-metadata cluster (7 P1 beads under various parents).
- Hassease (sylveste-nr6x, P0, in_progress).

### Dead Ends

- **`huggingface-cli` from Homebrew** — `/opt/homebrew/bin/huggingface-cli` Python 3.11 env was broken (missing `certifi`, then `pyyaml`). Fix: `python3.11 -m pip install --user certifi pyyaml`. Now works.
- **`bd update Sylveste-0gi.2.5 --status in_progress` from interfer subrepo** — `bd` is cwd-scoped to monorepo `.beads/`. Always `cd /Users/sma/projects/Sylveste` before `bd` commands.
- **Believing the .19 epic cancellation note** — it claimed .19.5 and .19.6 "remain useful as routing.yaml hygiene work." Re-read 2026-05-17: both beads are 100% microrouter-integration scaffolding (port 8422, shadow-mode logging, fall-through tables) with no salvageable hygiene content. Closed as superseded.
- **Looking for spike work in `interfer` subrepo** — wrong repo. The flash-moe spike lives at `/Users/sma/projects/flash-moe` (separate Sylveste-orbit repo, `origin`=Anemll/flash-moe, second remote `interstream`=mistakeknot/interstream where our work goes). Already on branch `spike/deepseek-v4`.
- **`huggingface-cli download` Bash chaining with `cd` then `cd back`** — cwd doesn't persist across Bash tool calls. Use subshells `( cd … && cmd )` or absolute paths every time.

### Context

- **Microrouter/SLM/routing cluster has zero open beads after this session.** .19 epic was already closed 2026-05-09; its last 2 open children (.19.5, .19.6) closed today, and the conditional successor Sylveste-zge closed MOOT after measurement (post-0zy agreement on `core-builtin-general` = 89.6%, above 85% trigger). Whole arc — heuristic baseline → LoRA kill → declaration hygiene → CI gate → conditional successor measurement — is a closed loop. Any future learned-routing question needs a fresh scoping bead written against then-current workload.
- **Sylveste-9ve finding:** Explore subagent dispatches in `~/.claude/interstat/metrics.db` stopped on 2026-04-21 (had n=132 in April-only Sylveste-2bg window, now zero). Either workflow shift to direct grep/Read or instrumentation regression — not yet diagnosed.
- **V4 architecture-delta doc structure:** §1-§4 are the original delta sections; §6 was "Unknowns" (mostly ✅ by Day-1 EOD); §7 is baseline-recon (transformers v5.8.1 native `DeepseekV4ForCausalLM` + upstream FP4/FP8 weights); §8 tensor-map (100% mapped, 0 novel); §9 next-steps (all done); §10 (new this session) is Day-2 kernel-math closure with line-cited evidence.
- **Local MLX 4-bit checkpoint at `/Users/sma/Models/DeepSeek-V4-Flash-4bit-mlx/`** is NOT loadable by transformers (uses `.biases`/`.scales` keys transformers can't dequantize). The baseline side of parity comparison uses upstream FP4/FP8 at `/Users/sma/Models/DeepSeek-V4-Flash-upstream/`; the flash-moe-port side validates against the local MLX dir.
- **Routing-drift CI gate is live on interflux `main`** (commit 76bbd5f, pushed yesterday). GitHub Actions workflow `.github/workflows/routing-drift.yml` fires on changes to `agent-roles.yaml`, `agents/**/*.md`, the script, or itself. Strict mode exits 1 on any drift; round-trip verified.
- **interflux is its own GitHub repo, NOT a submodule.** Sibling subrepo coverage (Sylveste-23w, P3) was the followup — copies of `verify_frontmatter.py` + `routing-drift.yml` need to land in os/Clavain, interverse/intersynth, interverse/intercraft, interverse/intertrace, interverse/interfluence, interverse/interdeep before they're covered.
- **Parallel-session staged content in monorepo to leave alone:** `docs/brainstorms/2026-05-11-microrouter-heuristic-rerun.md` has a staged rewrite by another session that removes the Sylveste-0zy Addendum; deleted handoffs are also staged. Do NOT touch — per MEMORY rule on parallel-session-premise-drift.
- **Patched baseline script for post-0zy measurement** lives at `/tmp/baseline_zge.py` (with `WHERE timestamp >= '2026-05-12T00:00:00Z'` filter). Output saved to `docs/research/microrouter-phase1/baseline-2026-05-17-zge-trigger-check.txt`. Original unpatched script at `docs/research/microrouter-phase1/baseline.py`.
- **Filed followup beads (open, not addressed today):** Sylveste-23w (P3, sibling subrepo CI coverage), Sylveste-vft (P4, drift-baseline ratcheting), Sylveste-10p (P4, pre-commit hook layer), Sylveste-9ve (P4, Explore dormancy diagnosis).
