---
date: 2026-05-16
session: spike-day1-close
topic: DeepSeek V4 spike — Day 2 kickoff
beads: [Sylveste-0gi.2, Sylveste-0gi.2.5, Sylveste-0gi.2.6, Sylveste-0gi]
prior_handoff: 2026-05-14-deepseek-v4-spike-kickoff.md
---

## Session Handoff — 2026-05-16 DeepSeek V4 spike Day-2 kickoff

### Directive

> Day 2 of the DeepSeek V4 → flash-moe feasibility spike (Sylveste-0gi.2). Day 1 finished with the **architecture-delta doc complete and the spike NOT killed**. Day 2 has three operational tracks running in parallel and one analytical task on the critical path. The Day-2 EOD kill-rule gate is: tensor map at 100% (✅ already), all unknowns resolved (✅ already), and kernel-level math verified well enough to write a CPU-reference forward path.

**Day-2 plan:**

1. **Kick off Sylveste-0gi.2.5 (160GB upstream weight download) FIRST.** Bandwidth-bound — will run overnight regardless of what else happens. Command:
   ```bash
   huggingface-cli download deepseek-ai/DeepSeek-V4-Flash \
     --local-dir /Users/sma/Models/DeepSeek-V4-Flash-upstream/
   ```
   Pre-check `df -h /Users/sma` has 160GB+ free. If `hf-transfer` is installed, set `HF_HUB_ENABLE_HF_TRANSFER=1` for parallel-chunk download.

2. **Sylveste-0gi.2.6: verify `compress_ratios` config BC in transformers v5.8.1.** ~30 min. Read `transformers/src/transformers/models/deepseek_v4/configuration_deepseek_v4.py:__post_init__`. Resolution paths:
   - (a) If `compress_ratios` is accepted directly → no patch needed.
   - (b) If only `compress_rate_csa` / `compress_rate_hca` accepted → write a wrapper that translates our 44-entry list into `compress_rates: {csa: 4, hca: 128}` + `layer_types` list. ~10 lines.

3. **Critical-path analytical work: read `transformers/src/transformers/models/deepseek_v4/modeling_deepseek_v4.py`** (1396 LoC per recon). Verify the following kernel-level details and update `docs/spikes/deepseek-v4-architecture-delta.md` with answers:
   - Indexer: score-then-topK exact ordering — raw scores vs softmax-then-topK?
   - Compressor `wgate` activation — SiLU vs sigmoid vs softplus?
   - HCA: exact Sinkhorn-20 normalization step — over entries or over probabilities?
   - `e_score_correction_bias`: where in the routing math is it added (pre-topK score adjustment vs post-topK normalization)?
   - Sliding window + `attn_sink`: does the sink token always attend (StreamingLLM exact), or is it learned to attend selectively?
   - HCA tensor decomposition: confirm `attn_hc.base=(24,)` decomposes as `hc_mult² + hc_mult² + hc_mult = 16+4+4` (forward mixing + inverse mixing + skip) or some other partition.

4. **Day-2 success gate (EOD 2026-05-16):**
   - ✅ Already met: tensor map 100%, no novel tensors, no unbounded unknowns.
   - 🔶 Add: kernel-level math from §3 above pinned for at least the *attention* and *MoE* paths.
   - 🔶 Add: config BC verified (Sylveste-0gi.2.6 closed).
   - 🔶 Add: 160GB download progressing.

   **If kernel reading surfaces a novel component not in the §1-§4 delta, STOP per kill rule.** This is the rule that bites if transformers' modeling_deepseek_v4.py shows something we didn't anticipate.

5. **Day-3 prep (begins after Day-2 EOD success gate):** start drafting the CPU-reference forward path in a sandbox script (NOT in flash-moe yet — keep flash-moe's C++/Metal path clean of Python). Goal: stand up `python/spike/cpu_ref_forward.py` that imports `transformers` + `safetensors`, loads our local MLX checkpoint via a wrapper that dequantizes on-the-fly into something transformers can use OR loads upstream weights via standard `from_pretrained`, runs one prompt through, captures logits.

**Pre-committed kill rules (unchanged from Day 1):**
- EOD day 2: incomplete architecture delta OR unbounded unknown in critical path → STOP.
- EOD day 5: logit cosine sim < 0.999 on top-10 vs trusted baseline → STOP.
- Any day: novel component encountered that wasn't in day-2 delta → STOP for re-scoping.
- Calendar day 5 hard stop (started 2026-05-15, ends EOD 2026-05-19).

**Beads:**
- `Sylveste-0gi.2` — in_progress, P2, spike bead. Notes contain Day-1 EOD rollup.
- `Sylveste-0gi.2.5` — open, P1, 160GB upstream weight download.
- `Sylveste-0gi.2.6` — open, P2, transformers v5.8.1 compress_ratios BC check.
- `Sylveste-0gi` — open, P2, parent decision bead. Stays open until spike produces go/no-go.
- `Sylveste-rkm` — P3 open, cosmetic policy-record-failed noise. Ignored.

### Dead Ends (discovered this session, in addition to prior handoff)

- **`bd create --parent=Sylveste-0gi.2`** without `--force` fails with "prefix mismatch: database uses 'sylveste-' but ID 'Sylveste-0gi.2.N' doesn't match." Database internal prefix is lowercase; CLI canonical IDs are mixed-case. Add `--force` to override. Failed child-suffix attempts (`.3`, `.4`) are burned forever; this session's children landed at `.5` and `.6`. Add to global Sylveste lessons.
- **The `transformers_version` field in V4's MLX config.json (4.46.3) is stamped by the conversion tool, not meaningful for loading.** Don't trust it as a "what version supports this arch" signal — it's pre-V4 by construction.
- **The local MLX 4-bit checkpoint CANNOT be loaded by transformers** even with the v5.8.1 native `DeepseekV4ForCausalLM`. MLX 4-bit uses `.biases`/`.scales` keys for grouped quant that transformers' loader doesn't understand. **For the parity baseline we MUST use the upstream FP4/FP8 weights**, not the local MLX dir. The flash-moe-port-being-validated uses the local MLX dir; the BASELINE uses upstream — they're different sides of the comparison.
- **The bead-note reference to `encoding_dsv4.py` was wrong.** V4 ships a standard HF tokenizer (`tokenizer.json` + `tokenizer_config.json`, BPE + ByteLevel). No Python encoder needed. Update bead notes if you encounter this misconception elsewhere.
- **`mlx_lm` does NOT mainline `deepseek_v4` arch as of 2026-05-15.** Issue ml-explore/mlx-lm#1233 open, no PR. The local MLX repack came from unmerged `jundot/omlx` fork with a known buggy MTP patch (omlx#1133) — **never trust the MLX-LM path blindly for parity**, even if it lands mainline this week. The upstream transformers baseline is the only credible ground truth.

### Context

- **flash-moe `spike/deepseek-v4` branch is at `f93d11c`**, pushed to `interstream/spike/deepseek-v4`. Local main is unchanged. Two untracked files (`autoresearch/cache_sweep.py`, `autoresearch/results/`) remain — leave alone, pre-existing.
- **The 4 spike-branch commits** (6d2345d → 5021035 → f49d2ce → f93d11c) are all docs-only against `docs/spikes/deepseek-v4-architecture-delta.md`. Day-2 will add at least one more commit (kernel-math closure section).
- **The architecture-delta doc is the spike's primary artifact.** Its §1-§5 enumerate deltas, §6 lists unknowns (all resolved as of Day-1 EOD), §7 has baseline recon + Day-3 plan, §8 has tensor-map coverage, §9 has next-steps and Day-1 done-list.
- **Codex's Round-2 debate synthesis** is still at `/tmp/debate-output-sylveste-0gi.md` (assuming /tmp hasn't rotated since Day-0). Re-read if Day-2 work surfaces a re-scoping question that touches the Phase-2 commitment.
- **Sylveste-bov (5 vs 12.9 tok/s perf regression on flash-moe Qwen mainline)** remains orthogonal. If V4 spike goes No-go EOD Day 5, bov is the clean fallback.
- **M5 Max 128GB memory will be the Day-3 problem.** 160GB upstream FP4/FP8 weights exceed unified memory — expect either heavy disk-paging or RunPod H200 rental (~$5-10 for one forward pass). Don't decide ahead of time; benchmark local disk-paging on Day-3 morning then choose.
- **`/Users/sma/.codex/config.toml`** is preconfigured for gpt-5.5 with model_reasoning_effort = "xhigh" — if a future debate runs slow/expensive, that's why.
- **Three child beads now exist under Sylveste-0gi.2 in addition to .5 and .6**: the burned `.3` and `.4` slots are inaccessible but not active. Treat as deleted.
