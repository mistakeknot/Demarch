---
artifact_type: probe
probe: task_completed_authority
bead: sylveste-3xl3.1.4
date: 2026-05-06
verdict: pre-veto-via-task-created
verdict_basis: documentation
docs_url: https://code.claude.com/docs/en/agent-teams
---

# F1.2 — TaskCompleted Authority Probe

**Verdict: `pre-veto-via-task-created`** — round caps CAN be enforced via hook, but the correct hook is `TaskCreated`, not `TaskCompleted` as named in the plan.

## Evidence

### Hook semantics (from agent-teams docs, "Enforce quality gates with hooks")

| Hook | When it fires | Exit-code-2 effect |
| --- | --- | --- |
| `TeammateIdle` | When a teammate is about to go idle | Sends feedback and keeps the teammate working |
| `TaskCreated` | When a task is being created | **Prevents creation** and sends feedback |
| `TaskCompleted` | When a task is being marked complete | **Prevents completion** and sends feedback |

Direct quote (TaskCreated):

> "TaskCreated: runs when a task is being created. Exit with code 2 to prevent creation and send feedback."

Direct quote (TaskCompleted):

> "TaskCompleted: runs when a task is being marked complete. Exit with code 2 to prevent completion and send feedback."

## Plan correction

Plan F4.3 says:

> "TaskCompleted backup (if F1.2=pre-veto): install a hook that vetoes Round-3+ task creation."

This is technically the wrong hook. **`TaskCompleted` exit-2 only blocks completion — it cannot prevent a new task from being created.** The hook that prevents future task creation is **`TaskCreated`** (exit code 2). The plan's intent is correct (use a hook to enforce a round cap); the hook name in the plan is incorrect.

### F4 implementation must use `TaskCreated`

The round-cap belt-and-braces hook should:

1. Read team task list from `~/.claude/tasks/{team-name}/` (or pass round count via env to the hook script).
2. On `TaskCreated`, exit 2 if the task's payload references "Round 3" or any round > N (the round cap configured for the run), with feedback "Round cap exceeded; debate is bounded to {N} rounds — synthesis pass next."
3. The hook is opt-in via env var `INTERFLUX_TEAMS_ROUND_CAP=2` (default) — disable by setting to 0.

## Implication for round-cap design

- **Primary cap (always on):** orchestrator-lead spawn prompt. The lead is told "spawn N debaters, run exactly 2 rounds, then hand off to the author." This is prompt-level discipline; it works without any hook.
- **Secondary cap (belt-and-braces):** `TaskCreated` hook installed at run-time, scoped to the team's session. This enforces the cap even if the lead's prompt discipline drifts.

The combination converts what the plan called "TaskCompleted post-only fallback" into an actual two-layer mechanism. **No design-breaking finding** — the plan's intent is achievable; only the hook name needs updating in F4 code.

## Status

No design-breaking finding. F4 cleared to proceed with `TaskCreated` (not `TaskCompleted`) for the secondary cap.

## Lifecycle limitations worth noting

The same docs section ("Limitations") includes constraints relevant to F4-F6:

- **"No session resumption with in-process teammates"** — `/resume` and `/rewind` do not restore in-process teammates. (Already documented in bead notes; reinforces the "do not use --teams inside a /sprint resume cycle" guidance.)
- **"One team per session"** — a lead can manage only one team at a time. F6 (A/B benchmark) must run subagent path and teams path in separate sessions or sequentially within one lead session, not concurrently.
- **"No nested teams"** — teammates cannot spawn their own teams. The orchestrator-lead role IS the team lead; if the design ever needed sub-teams under each debater, it isn't possible.
