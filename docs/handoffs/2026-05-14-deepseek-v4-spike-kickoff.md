---
date: 2026-05-14
session: unknown
topic: DeepSeek V4 spike kickoff
beads: [Sylveste-py7, Sylveste-9il, Sylveste-0gi, Sylveste-0gi.2]
---

## Session Handoff — 2026-05-14 DeepSeek V4 spike kickoff

### Directive

> Your job is to start **day 1** of the DeepSeek V4 → flash-moe feasibility spike (Sylveste-0gi.2). Start by reading the pre-committed kill-criteria doc at `/Users/sma/projects/flash-moe/docs/spikes/2026-05-13-deepseek-v4-spike.md` end-to-end (it overrides any urge to start coding). Day-1 deliverable is the architecture-delta document, NOT code.

**Day-1 plan (read the spike doc first; this is just orientation):**

1. `cd /Users/sma/projects/flash-moe && env -u GIT_INDEX_FILE git checkout -b spike/deepseek-v4` — branch isolation is mandatory. Mainline Qwen autoresearch loop stays on `main` untouched.
2. **Reconnaissance for the trusted DeepSeek V4 baseline** (the day-3 parity comparison needs one). Candidates in preference order: (a) upstream DeepSeek V4 reference Python impl, (b) recent MLX-LM release that supports `deepseek_v4` arch (last known check failed — verify if a newer release fixed this), (c) layer-by-layer NumPy parity against raw safetensors as last resort. Treat this as day-1 work because it can blow the schedule.
3. **Start the architecture delta doc** at `flash-moe/docs/spikes/deepseek-v4-architecture-delta.md`. Cover: CSA vs Qwen MHA, HCA, MoE routing (V4: 13B/284B vs Qwen3.5: 17B/397B), FP4-mixed quant, tokenizer/special-token surface.
4. **Day-2 success gate is the doc itself being complete + actionable.** If by EOD day 2 the doc is incomplete or has unbounded "unknown" items in the critical path, **STOP**. This is a written kill rule, not a guideline.

**Pre-committed kill rules (do not relax mid-spike without user re-approval):**
- EOD day 2: incomplete architecture delta → STOP.
- EOD day 5: logit cosine sim < 0.999 on top-10 vs trusted baseline → STOP.
- Any day: novel component encountered that wasn't in day-2 delta → STOP for re-scoping.
- Calendar day 5 hard stop. Wall-clock, not effort-days.

**Beads:**
- `Sylveste-0gi.2` — open, P2, spike bead (start by marking in_progress when work begins)
- `Sylveste-0gi` — open, P2, parent decision bead. Stays open until spike produces go/no-go on Phase 2.
- `Sylveste-rkm` — P3 open, cosmetic `policy: record failed` noise on every `bd-push-dolt` (clavain-cli policy CLI surface was removed; not blocking)

**Debate record:** `/tmp/debate-output-sylveste-0gi.md` is the Round-2 synthesis. The full Round-1 commentary streamed to terminal but the dispatch.sh wrapper only persists Round 2 to disk. If `/tmp` rotated, the synthesis is also archived as a note on Sylveste-0gi.2.

### Dead Ends

- **Trying to commit from `os/Clavain` without `env -u GIT_INDEX_FILE`** — the user's per-shell git wrapper pins `GIT_INDEX_FILE` to the Sylveste root index whenever cwd is anywhere under `/Users/sma/projects/Sylveste`. Subrepo commits SILENTLY commit to the wrong index. Always prefix subrepo git ops with `env -u GIT_INDEX_FILE`. See `feedback_git_index_file_pollution.md`.
- **`ic publish --patch` after a previous failure** — does NOT auto-force, despite the error message saying "re-run to force". You must delete the stale row in `~/.clavain/intercore.db` table `publish_state` where `phase != 'done'`. Recipe documented at `/Users/sma/.claude/projects/-Users-sma-projects-solwend/memory/reference_intercore_publish_stuck_locks.md`.
- **`bd create --parent=sylveste-0gi`** (lowercase) — fails with "parent not found" even though `bd show Sylveste-0gi` works fine. Must use canonical mixed-case ID `--parent=Sylveste-0gi`. Failed create attempts still reserve a child suffix, so `Sylveste-0gi.1` was burned on a failed attempt; the actual spike bead is `Sylveste-0gi.2`.
- **`bash debate.sh` before installing Codex CLI** — exits 127 (`codex: command not found`). The clavain debate skill needs both Claude and Codex. Codex CLI is OpenAI's package: `npm install -g @openai/codex` (37s, installs at `~/.npm-global/bin/codex`). Now installed (`codex-cli 0.130.0`).
- **`gh repo create --source --remote` flag combination** — created the new repo and added it as remote `interstream` correctly. Don't conflate with `gh repo fork` which forces upstream-fork semantics.
- **`git push` from flash-moe to `origin`** — denied 403; `origin` is `Anemll/flash-moe` (you don't own it). The fork is now at `mistakeknot/interstream` (private) as a *second* remote. `origin` still points at Anemll — don't change that, you may want upstream pulls.

### Context

- **flash-moe lives at `/Users/sma/projects/flash-moe`** — separate Sylveste-orbit repo (not in monorepo). NEW second remote `interstream` → `https://github.com/mistakeknot/interstream.git` (private, just-created, `main` now backed up there with 11 commits + the spike doc as `4f54dd2`). Two untracked items in the worktree are not mine (`autoresearch/cache_sweep.py`, `autoresearch/results/`) — leave alone.
- **flash-moe is Qwen3.5-397B-A17B-shaped to the bone.** `repack_experts.py`, `expert_index.json`, `metal_infer/export_vocab.py` all assume Qwen MoE topology and BPE byte-level encoding. Codex flagged in the debate that Qwen-specific runtime paths are likely hardcoded beyond just the chat template. Trust this when scoping the architecture delta.
- **V4 MLX model is at `/Users/sma/Models/DeepSeek-V4-Flash-4bit-mlx/`** (141GB, 33 shards). Includes `chat_template.jinja` and `config.json`. The "encoding_dsv4.py" mentioned in the 0gi bead notes may be partly solved upstream by the MLX repack — verify on day 1.
- **Phase 2 (Metal kernels) is OUT of scope for the spike.** Codex insisted on this and it's in the kill-criteria doc. Even Outcome A (go) only means "Phase 2 is *justified*" — Phase 2 scoping is a separate decision made AFTER spike with calibrated estimates as input.
- **Today's /handoff command shipped trimmed** — version 0.6.252 of clavain only writes ONE dated file (no auto-memory write, no `latest.md` symlink, no clipboard fenced block). User confirmed the bypass behavior; this handoff follows the new behavior even though the loaded skill content shows the old version (session-start cache).
- **`Sylveste-6f0` was already closed 2026-05-05** — the stale `handoff_6f0_validation.md` memory and `docs/handoffs/2026-05-03-...-validation-running.md` (still untracked in Sylveste root) are orphan paperwork. Per parallel-session premise-drift discipline either delete or mark SUPERSEDED next session if you encounter them.
- **`/Users/sma/.codex/config.toml`** is pre-configured for `gpt-5.5` with `model_reasoning_effort = "xhigh"` — the debate uses this. If a future debate is unexpectedly slow or expensive, that's why.
- **Sylveste-bov (5 vs 12.9 tok/s flash-moe perf regression)** is orthogonal to the V4 spike. Don't bundle it. If V4 spike goes No-go, bov is a clean fallback for the next session.
- **`policy: record failed` noise on every `bd-push-dolt`** — cosmetic, op succeeded. Tracked under Sylveste-rkm. Ignore unless it becomes blocking.
- **Three commits this session, three repos**: Clavain `b60de5f` + 0.6.252 publish (pushed), interfer `eaee6ea` (pushed), flash-moe `4f54dd2` (pushed to new `interstream` remote, NOT to origin/Anemll).
