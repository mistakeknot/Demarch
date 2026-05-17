---
date: 2026-05-17
session: c1673cfe
topic: DeepSeek V4 spike Day-3 CPU-ref forward
beads: [Sylveste-0gi.2, Sylveste-0gi.2.5, Sylveste-0gi.2.6, Sylveste-0gi]
prior_handoff: 2026-05-16-deepseek-v4-spike-day2-kickoff.md
---

## Session Handoff — 2026-05-17 DeepSeek V4 spike Day-3 CPU-ref forward

### Directive

> Your job is to write `python/spike/cpu_ref_forward.py` in `/Users/sma/projects/flash-moe/` on branch `spike/deepseek-v4`, then run it to capture baseline logits for the Day-3 parity comparison. Start by checking the download has completed: `du -sh /Users/sma/Models/DeepSeek-V4-Flash-upstream/` should show ~160GB and the directory should contain `model-00001-of-00046.safetensors` through `model-00046-of-00046.safetensors`. Verify completion with: `ls /Users/sma/Models/DeepSeek-V4-Flash-upstream/*.safetensors | wc -l` returns 46 AND `ls /Users/sma/Models/DeepSeek-V4-Flash-upstream/.cache/huggingface/download/*.incomplete 2>/dev/null | wc -l` returns 0.

**Script requirements (per architecture-delta §10):**
- Load weights via `transformers.AutoModelForCausalLM.from_pretrained("/Users/sma/Models/DeepSeek-V4-Flash-upstream/", torch_dtype=torch.float32, device_map="auto")` — transformers v5.8.1 ships native `DeepseekV4ForCausalLM`. Force fp32 accumulator for parity-grade precision.
- Tokenizer: `AutoTokenizer.from_pretrained` on the same dir; BOS=0, EOS=1, PAD=2.
- Prompt: hardcode a short, deterministic prompt (≤32 tokens). Suggested: `"The DeepSeek V4 architecture introduces"` for reproducibility.
- Capture: `torch.save({prompt, input_ids, logits[seq_len, vocab=129280], top_k_tokens, top_k_logprobs, model_config_hash}, "/Users/sma/Models/DeepSeek-V4-Flash-upstream/.spike-baseline-logits.pt")`. Use `torch.save` (not raw pickle) — tensors only, no arbitrary Python objects.
- DO NOT compute parity here — this script only captures the baseline. The flash-moe-port side comes later.

**Memory plan (M5 Max 128GB):**
- 160GB FP4/FP8 weights exceed unified memory. Use `device_map="auto"` with `max_memory={"cpu": "100GB"}` and disk-offload via accelerate's `offload_folder="/tmp/v4-offload/"`.
- Expected wall-clock: 5–30 min/token per recon §7.2. **Time-box: if first token doesn't emerge in 45 min, kill the run and pivot to RunPod H200 rental (~$5-10).** Do NOT let it grind for hours.
- Pre-flight memory check: `vm_stat | head -5` before starting; abort if free pages < 200,000.

**Config BC hook (closes Sylveste-0gi.2.6 verification):**
- The local MLX checkpoint uses `compress_ratios` (44-entry list); per §10 it's verified that transformers v5.8.1 `DeepseekV4Config.__post_init__` accepts this directly. For THIS script you're loading upstream FP4/FP8 weights which already use the canonical key — no patch needed. If you hit a config error, the fallback patch is documented in Sylveste-0gi.2.6's closing notes.

**Beads in flight:**
- `Sylveste-0gi.2` — in_progress, P2, parent spike bead.
- `Sylveste-0gi.2.5` — in_progress, P1, 160GB download (was ~37GB / 74 files / 14min when this handoff was written; ETA EOD 2026-05-17). Mark closed when verify above returns 46 files + 0 incomplete.
- `Sylveste-0gi.2.6` — ✓ closed Day-2, config BC verified.

**On success (logits captured):**
- Update `flash-moe/docs/spikes/deepseek-v4-architecture-delta.md` §10.7 table: add Day-3 row "Baseline logits captured ✅" with absolute path to the `.pt` file and wall-clock time.
- Create Sylveste-0gi.2.7 (P1, --force needed) for "Flash-moe port forward pass + logit parity comparison" (Day-4 work).
- Commit on `spike/deepseek-v4` (`env -u GIT_INDEX_FILE git -C /Users/sma/projects/flash-moe`). Push to `interstream/spike/deepseek-v4`. NEVER push to `origin/Anemll`.

**On failure (OOM, timeout, or any non-trivial issue):**
- Do NOT extend the wall-clock budget. Capture the error.
- Open Sylveste-0gi.2.8 (P1, --force) for "RunPod H200 rental for baseline logit capture" — write a one-page plan: pod size, weights upload strategy (RunPod has fast HF mirror), expected ~$5-10 cost.
- Pause the spike, ask user for go-ahead on cloud spend.

### Dead Ends

- **`Skill` tool cannot invoke `/clavain:work` or `/clavain:handoff`.** Both are slash commands, not registered Skills. Read `~/.claude/plugins/cache/interagency-marketplace/clavain/0.6.252/commands/{work,handoff}.md` and execute the workflow inline. Same applies to most other `/clavain:*` commands.
- **MLX checkpoint at `/Users/sma/Models/DeepSeek-V4-Flash-4bit-mlx/` is NOT loadable by transformers v5.8.1.** MLX's `.biases`/`.scales` quantization layout is opaque to HF's loader. Use ONLY upstream `/Users/sma/Models/DeepSeek-V4-Flash-upstream/` for the baseline. The MLX dir is reserved for the flash-moe port side of the parity comparison.
- **`bd create --parent=Sylveste-0gi.2`** without `--force` fails: `prefix mismatch: database uses 'sylveste-' but ID 'Sylveste-0gi.2.N' doesn't match`. Always pass `--force`. Failed attempts burn child suffixes permanently (`.3` and `.4` are dead slots).
- **Day-1 hypothesis: compressor `wgate` = SiLU/sigmoid GLU.** WRONG. It's softmax over the window axis with learned position bias (§10.2). Same parameter shape, different operation. Don't infer operation from shape alone.
- **Day-1 hypothesis: `attn_sink` = StreamingLLM position-based always-attend.** WRONG. It's a per-head learnable softmax-overflow scalar (GPT-OSS pattern, §10.5). Simpler than StreamingLLM — concat scalar to logits, softmax, drop the sink result.
- **Day-1 hypothesis: `attn_hc.base=(24,)` = `[16, 4, 4]` (forward + inverse mixing + skip).** WRONG. It's `[4, 4, 16]` = `[pre_scalars, post_scalars, comb_mixer]`. `pre`/`post` are per-stream scalars, not matrices. No inverse mixing exists. See §10.6.

### Context

- **Background download is detached and headless.** Original shell wrapper PID 40871 exited; `huggingface-cli` child process keeps running. Progress is checkable only via `du -sh` + `ls` on `/Users/sma/Models/DeepSeek-V4-Flash-upstream/`. Throughput observed: ~44 MB/s sustained. No log rotation; `/tmp/sylveste-0gi.2.5-download/stderr.log` is the live progress stream.
- **The "parallel agent" you may see in intermute (`solwend-platform-design`) is the USER's autogen identity, not another AI session.** 431 agents share this name in intermute history. `bccd1ff` was the user themselves writing §10 manually after reading transformers source. No coordination friction; user IS the orchestrator. Don't waste time investigating intermute reservations — none exist on flash-moe files.
- **`/Users/sma/projects/flash-moe` is a SEPARATE git repo from Sylveste monorepo.** Always use `env -u GIT_INDEX_FILE git -C /Users/sma/projects/flash-moe ...` for git ops there (see [[feedback-git-index-file-pollution]]). The `git` shell function pins `GIT_INDEX_FILE` to Sylveste's index whenever cwd is under `/Users/sma/projects/Sylveste`.
- **Spike branch `spike/deepseek-v4` HEAD = `7596ba1`**, pushed to `interstream/spike/deepseek-v4`. Origin (Anemll/flash-moe) is read-only — DO NOT push there.
- **Two pre-existing untracked files in flash-moe**: `autoresearch/cache_sweep.py`, `autoresearch/results/`. Leave alone — they predate this work entirely.
- **Architecture-delta doc** (`/Users/sma/projects/flash-moe/docs/spikes/deepseek-v4-architecture-delta.md`) is the spike's primary artifact. §10 (Day-2 kernel-math closure) contains exact source-line citations into `transformers/src/transformers/models/deepseek_v4/modeling_deepseek_v4.py` for every kernel component. Reference these when writing the script — they're the contract for what the forward pass actually does.
- **MTP head is NOT instantiated by transformers v5.8.1** (§10 §7.1). Even though `num_nextn_predict_layers=1` in config and the upstream weights include MTP tensors, the modeling code loads-and-ignores them. Our local MLX checkpoint stripped MTP entirely. Net: parity comparison is apples-to-apples on the main logits path — both sides ignore MTP.
- **Homebrew `huggingface-cli` Python 3.11 needs `certifi` + `pyyaml` installed manually** before first download on any new Mac context. See [[feedback-huggingface-cli-python311-certifi]]. Already installed on this machine (current session); not a blocker for Day-3.
- **Kill rules (do NOT relax without user re-approval, per spike pre-commitment):**
  - EOD calendar day 5 (2026-05-19): logit cosine sim < 0.999 on top-10 vs trusted baseline → STOP.
  - Any day: novel component not in Day-2 §10 delta → STOP for re-scoping.
  - Calendar day 5 is a HARD WALL-CLOCK stop, not effort-days.
- **Sylveste-bov (5 vs 12.9 tok/s flash-moe perf regression)** remains the no-go fallback. If V4 spike fails Day-5 parity gate, drop to bov.
- **Codex Round-2 debate synthesis** at `/tmp/debate-output-sylveste-0gi.md` may have rotated by Day-3; the synthesis is archived in Sylveste-0gi.2's notes if needed for re-scoping decisions.
