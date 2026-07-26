---
artifact_type: goal-charter
bead: Sylveste-e9y
complexity: 3
stage: goal-formed
---

# Goal Charter: Orchestrator Observability + Dispatch Discipline

## Why (leverage)

Three orchestrated runs this session (bo09bb6fq, b592z9h0k, bz2ryyp94) failed or
mis-reported in ways that were invisible until manually reproduced: buffered
stdout hid all progress, temp-dir cleanup destroyed failed-task artifacts, a
verdict false negative (task-9) cascaded into three wrongly-skipped tasks, two
timeouts killed agents whose work was already complete, and an executor agent
pushed a deliberately-held commit to origin. Every future orchestrated plan
execution inherits these fixes; the diagnosis loop collapses from
re-run-and-probe to read-the-log. Papercut evidence: 2026-07-19/20 journal
entries (temp-dir cleanup, verdict parser, melange stall).

## Scope

**In — Stage 1 (fix-pack; internal gate for Stage 2):**
1. Per-task persistent artifacts: prompt, Codex stdout/stderr, and verdict for
   every task written under a run directory that survives failure and cleanup.
2. Live progress: wave/task completion lines flushed to the orchestrator's
   stdout as they happen, not at exit.
3. Verdict outcome-checking: before marking a task ERROR and skipping
   dependents, cross-check observable outcomes (expected files exist, commits
   landed, task-named tests pass). Timeout-after-work-complete and
   missing-sidecar become WARN, not ERROR; dependents still run.
4. Executor no-push hard block: dispatch.sh injects a push guard (repo-local
   pre-push hook or equivalent) for the run's duration; the orchestrator owns
   all pushes.

**In — Stage 2 (gated on Stage 1 shipped):**
5. `--tmux` dispatch mode: one named window per task (`orc-<run>:<task-id>`)
   so humans can attach and watch live.
6. intermux integration: stuck/crash detection informs the orchestrator loop,
   replacing the blunt per-task timeout with no-output-movement detection.

**Out:**
- Conductor (sylveste-3kol) — **orthogonal verdict**: this goal hardens the
  current orchestrate.py/dispatch.sh pipeline; if Conductor ships it inherits
  the log/verdict contract established here. Verdict noted on the bead.
- Codex binary/model-metadata issues (upstream codex CLI, not ours).
- tuivision integration (driving harness — separate concern from monitoring).

## Acceptance criteria

1. An induced failed dispatch leaves prompt + stdout/stderr + verdict on disk
   under the run directory.
2. The orchestrator output file contains per-task progress lines while tasks
   are still running.
3. A stubbed agent that completes its work but times out (or omits its verdict
   sidecar) is not marked ERROR, and its dependents execute.
4. A `git push` attempted inside a dispatched task fails while the guard is
   active, and pushes work again after the run.
5. Tests covering 1–4 live in the Clavain suite and pass.
6. A 2-task toy manifest runs under `--tmux` with windows visible to
   intermux's agent listing and logs on disk.

## Completion condition (literal — handed to /goal)

Orchestrator observability shipped: Clavain tests covering (a) failed-task
artifacts persisted, (b) live progress flush, (c) verdict outcome-check
preventing false-negative skip cascades, (d) dispatch push-guard blocking git
push, all pass with exit 0 shown in surfaced output; a 2-task toy manifest
demonstrates --tmux mode with per-task logs on disk; all work committed to
os/Clavain and bead Sylveste-e9y closed with evidence. Or stop after 40 turns.

## Successor obligations

On close, propose a successor (auditor-enforced). Leading candidates:
interline sideband cutover (KD 11 completion) or revisiting the
sylveste-3kol Conductor verdict with the new log/verdict contract in hand.
