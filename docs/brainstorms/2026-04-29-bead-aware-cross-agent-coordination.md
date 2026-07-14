---
artifact_type: brainstorm
bead: sylveste-kgfi
date: 2026-04-29
status: shipped
thread: GSV Discord #agent-ops / Hermes Agents aware of other agents' beads
---

# Bead-aware cross-agent coordination

## Decision

Bead-aware cross-agent coordination is **Interverse / Sylveste canon**. Hermes' operator-facing view over that substrate is an **Athenverse adapter**.

Working names:

- **Substrate:** extend `intermux` + `intermute` + `interlock` first. Do not mint a new `Inter*` plugin yet.
- **Hermes adapter:** `Athenmesh`.
- **Future substrate name:** reserve `Interlink` only if this outgrows the existing `intermux` / `intermute` / `interlock` split. `Intermesh` was assigned on 2026-07-14 to the retrieval-gated Agent Skills registry/router (`sylveste-qn2c`).

Alignment: supports Sylveste's composition-over-capability principle by wiring small existing coordination tools around a shared Beads work-state handle.

Conflict/Risk: risks creating a parallel task tracker if presence/messages begin owning task state. The rule is explicit: Beads remains the source of truth for work status, dependency, priority, and claim state.

## Problem

Hermes, Claude Code, and Codex can all use Beads, but they still need a common way to answer:

- Who is currently working on this bead?
- Which repo and files are they touching?
- Is another agent blocked, idle, or stuck?
- Can I safely dispatch another body here?
- How do I message or nudge the relevant agent without losing the Beads thread?

The current answer is scattered across Beads, tmux panes, CASS, Discord, Intermute, and occasional handoff docs. Agents discover collisions late, often when git diffs collide or a human notices two live sessions in the same repo.

## Canonical source-of-truth split

| Concern | Owner | Notes |
|---|---|---|
| Work status, priority, dependencies, claim | Beads | Canonical. Presence layers never redefine task state. |
| Live tmux/session observation | `intermux` | Derive status, cwd, branch, touched files, active bead when visible. |
| Agent registry, messages, topics, ack/read, metadata | `intermute` | Durable coordination bus and live/deferred peer messages. |
| File reservations and release negotiation | `interlock` / Agent Mail | Advisory early warning, terminal enforcement when configured. |
| Hermes/Discord operator view | `Athenmesh` | Query/summarize/route/nudge; no canonical substrate ownership. |

## Minimum presence record

Every agent body should be representable by this record, whether it is Hermes, Claude Code, Codex, Zaka-spawned, or a future Skaffen runner:

```json
{
  "agent_id": "codex-zklw-20260429-001",
  "agent_kind": "codex|claude-code|hermes|zaka|skaffen|oracle|other",
  "host": "zklw",
  "surface": "tmux:zklw:session.window.pane|discord:thread|telegram|cli",
  "repo": "/home/mk/projects/Sylveste",
  "beads_authority": "/home/mk/projects/Sylveste/.beads",
  "active_bead_id": "sylveste-kgfi",
  "active_bead_confidence": "reported|observed|inferred|stale|unknown",
  "thread_id": "sylveste-kgfi",
  "objective": "short sentence",
  "status": "starting|working|blocked|reviewing|idle|stuck|complete|unknown",
  "branch": "main",
  "files_planned": ["interverse/intermux/**", "core/intermute/**"],
  "files_touched": ["docs/brainstorms/2026-04-29-bead-aware-cross-agent-coordination.md"],
  "last_seen": "2026-04-29T03:00:00Z",
  "confidence": "reported|observed|inferred|stale",
  "links": {
    "mail_thread": "sylveste-kgfi",
    "handoff": null,
    "cass_query": null
  }
}
```

Rules:

1. `active_bead_id` is the join key across systems when present with sufficient confidence.
2. `thread_id` defaults to `active_bead_id`.
3. Presence may be stale, inferred, unknown, or ambiguous; task state still comes from Beads.
4. Ambiguous bead candidates must remain candidates, not guessed facts; merge-only metadata surfaces should receive an empty `active_bead_id`/`thread_id` plus `active_bead_confidence = unknown` to clear stale singular values.
5. File intent should come from reservations when available, otherwise from observed touched files or declared planned files.
6. Any exact external platform IDs, Discord snowflakes, or auth tokens must remain out of public docs and be stored only in appropriate local metadata if needed.

## Expected operator queries

Athenmesh should make these questions cheap from Hermes/Discord:

```text
/who <repo-or-bead>
/collide <bead-or-paths>
/nudge <agent-or-bead> <message>
/handoff <bead> --to codex|claude
/presence <repo>
```

These commands are illustrative, not committed first-party Hermes commands. The v0 Athenmesh skill can produce a compact card before any slash command exists.

## Build order

### Wave 0 — conventions only

- Add this design note.
- Use `active_bead_id` as the shared presence handle in Hermes, Claude Code, and Codex prompts when the current active bead is known.
- When launching a coding agent, include: objective, bead, repo/path, planned files, and expected closeout.

### Wave 1 — `intermux` metadata enrichment

Goal: observe live sessions and publish a presence record when possible.

Likely changes:

- Parse active bead IDs from tmux pane content, prompts, environment-backed SessionStart mapping metadata, and Beads commands in recent output.
- Track cwd, branch, touched files, and status.
- Emit confidence: `reported`, `observed`, `inferred`, `stale`, or `unknown`.
- Push metadata into `intermute` under a stable agent/session key.

### Wave 2 — `intermute` read model

Goal: make presence and bead-thread messages queryable.

Status (2026-04-30): shipped in Intermute commit `0db673603ac83da377399a6121d84a8402300ff2`.
The v0 read model exposes `GET /api/agents/presence`, filtering by `project`, `repo`, and `active_bead_id`, and projects agent metadata into `agent_id`, `kind`, `status`, `last_seen`, `repo`, `files`, `objective`, `confidence`, `active_bead_id`, and `thread_id`.
Message-thread queries remain future work; bead-thread correlation is preserved by using `thread_id == active_bead_id` when present.

Likely changes:

- Store/merge agent metadata fields needed for presence.
- Add or document query paths for:
  - agents by `project` / `repo`
  - agents by `active_bead_id`
  - messages by `thread_id == active_bead_id`
  - stale ack / blocked thread summaries
- Preserve cursor-based pagination and existing ack/read semantics.

### Wave 3 — `interlock` / Agent Mail file intent

Goal: make collision checks path-aware.

Status (2026-04-30): shipped in Interlock commit `7c1daf7cc1a82d1fd3537e5b0cc030e9665a5d5a`.
The v0 reservation convention keeps Intermute-compatible reason metadata (`active_bead_id=...`, optional `bead_id=...` and `thread_id=...`) until reservations grow a first-class metadata column. `check_conflicts` now returns bead-aware collision cards with holder, project/path, reservation state, confidence, bead/thread correlation, `suggested_action`, and `hard_blocker`. Hard blockers come from Intermute's reservation conflict endpoint; list-derived reservation overlaps are advisory context only, so stale/ambiguous/same-bead evidence is surfaced without becoming canonical task state.

Likely changes:

- Standardize reservation `reason = <bead_id>`.
- Include `bead_id` in release negotiation threads.
- Provide a collision summary suitable for Hermes: holder, bead, path pattern, expiry, release/nudge path.

MCP Agent Mail may be used as prior art or an isolated bridge, but do not run its installer in a way that replaces the canonical zklw `bd` CLI. Use `--skip-beads` / `--skip-bv` if experimenting.

### Wave 4 — `Athenmesh` Hermes adapter

Goal: give Hermes a compact operator surface over the substrate.

Status (2026-04-30): shipped in Athenverse commit `46a8da9ceb5e89d3774c6c46ea90f3b25159ab50`.
Athenmesh v0.1 is a Hermes-facing Athenverse skill/adapter and coordination-card contract. It produces compact, read-only `Bead + Repo + Workers + Collision risk` cards from Beads, Intermute/Intermux presence, Interlock reservation summaries, CASS continuity evidence, and repo state. It remains operator-facing: no dispatch/controller behavior, no first-party Hermes command, and no mutation of Beads, reservations, presence, CASS, or repo state.

Athenmesh v0 should be a skill/adapter, not a dispatching controller:

- Inputs: bead ID, repo path, path patterns, or vague user prompt.
- Reads: Beads, intermute/intermux metadata, interlock reservations, CASS when historical context matters.
- Output: compact coordination card with current workers, collision risk, stale/stuck signals, and suggested next action.
- Does not claim canonical task state.
- Does not create or close beads unless explicitly asked as part of backlog management.

### Wave 5 — Hermes command-surface evaluation

Goal: decide whether Athenmesh should become a first-party Hermes command surface.

Status (2026-04-30): evaluated under `sylveste-kgfi.5`. Verdict: **no first-party command yet**.

Evidence:

- Athenmesh v0.1 dogfood held for `sylveste-kgfi.4`, but the run was still mostly Beads + repo + stale/fallback CASS evidence. It did not capture fresh Intermute/Intermux live presence or Interlock reservation summaries.
- Hermes already exposes prompt-style command seams (`/pickup`, `/prepare`, `/route`, `/reintegrate`), so `/presence` would be technically feasible, but adding it now would promote a thin adapter before enough operator demand is proven.
- The live Hermes Agent repo is not the right place for opportunistic implementation in this evaluation slice; command implementation should start from a separate Hermes bead, clean file scope, RED boundary tests, and normal review/deploy gates.

Recommendation:

- Decline `/mesh` for v1. The name implies substrate ownership and now conflicts directly with Intermesh, the skill-registry/router project; Athenmesh remains the coordination adapter.
- Do not add `/presence` in this slice. Continue using Athenmesh as a mounted Hermes skill/operator workflow.
- If repeated dogfood proves that a native command materially lowers operator friction, create a separate Hermes implementation bead and prefer `/presence` as a prompt-style, read-only command that invokes Athenmesh and cannot dispatch, reserve files, or mutate Beads.

Operator workflow without a command:

1. Ask Hermes for an Athenmesh card by bead, repo, or file area.
2. Hermes loads Athenmesh and returns a compact `Bead + Repo + Workers + Presence + Collision risk + Next action` card.
3. The card may read Beads, Intermute/Intermux presence, Interlock reservations, CASS freshness, and repo state, but it does not mutate any of them.
4. Beads remains canonical task state; Interlock remains the hard-blocker/reservation lane; Intermute/Intermux presence remains advisory/read-model state.

Revisit trigger: implement `/presence` only after at least two more real coordination dogfoods show repeated command-shaped demand or fresh live presence/reservation evidence that the skill-only path is too slow.

### Future substrate — only then consider `Interlink`

Mint a new `Inter*` plugin only if at least two of these become true:

- Cross-repo / cross-host agent presence needs a substrate beyond `intermux` metadata.
- Coordination requires a stable public API that is not naturally owned by `intermute`, `intermux`, or `interlock`.
- Multiple non-Hermes clients need the same coordination read model.
- The integration starts accumulating code that would otherwise be duplicated across existing plugins.

Until then, `Interlink` remains a reserved future name, not a repo. `Intermesh` is no longer reserved here; its separate skill-routing ownership does not change the coordination boundaries in this document.

## Follow-up beads

1. **`sylveste-kgfi.1` — `[intermux] Publish active_bead_id and files_touched in agent metadata`**
   - Parse/reconcile bead ID from environment, recent pane output, and working directory Beads context.
   - Push confidence-scored metadata to Intermute.

2. **`sylveste-kgfi.2` — `[intermute] Add bead presence read model and queries`**
   - Query live agents by bead and repo.
   - Return agent id, kind, status, last_seen, and metadata confidence.
   - Blocked by `sylveste-kgfi.1` so the read model follows the published metadata contract.

3. **`sylveste-kgfi.3` — `[interlock] Standardize bead-keyed reservation summaries`**
   - Ensure reservations carry bead ID in reason/metadata.
   - Add an agent-readable collision card.

4. **`sylveste-kgfi.4` — `[Athenverse] Bootstrap Athenmesh Hermes coordination adapter`**
   - Status: shipped in Athenverse commit `46a8da9ceb5e89d3774c6c46ea90f3b25159ab50` with local bead `Athenverse-4gj` closed.
   - Hermes-facing coordination card: workers, collisions, stale/stuck signals, suggested next action.
   - Dogfood record: `docs/cujs/athenmesh-v0.1-sylveste-kgfi4-dogfood.md` in Athenverse.
   - Blocked by `sylveste-kgfi.2` and `sylveste-kgfi.3`.

5. **`sylveste-kgfi.5` — `[Hermes] Evaluate prompt-style /presence command after Athenmesh dogfood`**
   - Status: evaluated 2026-04-30. Verdict: no first-party command yet; keep Athenmesh as the mounted skill/operator workflow.
   - `/mesh` declined for v1 because it implies substrate ownership.
   - `/presence` remains the preferred future command name if repeated dogfood proves native command demand.
   - Prompt-style read/summarize behavior only; no direct dispatch in v1.
   - Blocked by `sylveste-kgfi.4`.

## Non-goals

- Do not replace Beads.
- Do not make Discord channel history the coordination source of truth.
- Do not require every agent to use Hermes.
- Do not require every coding agent to run in tmux forever; tmux observation is a high-value v0 path, not the universal identity model.
- Do not build a new coordination `Inter*` plugin before the existing trio proves insufficient.

## Open questions

1. Should `active_bead_id` be primarily reported by launch wrappers (`Zaka`, Hermes handoff packets) or inferred by `intermux` from pane output?
   - Recommendation: both. Reported beats inferred; inferred keeps old sessions visible.
2. Should presence records live as `intermute` agent metadata or as first-class records?
   - Recommendation: metadata in v0; first-class table only if query pressure justifies it.
3. Should Athenmesh expose `/mesh`, `/presence`, or no command initially?
   - Resolved 2026-04-30 and clarified 2026-07-14: no first-party command initially. Keep Athenmesh as the skill/operator workflow. If repeated dogfood later proves native command demand, prefer `/presence` for read-only clarity; `/mesh` remains declined because Intermesh now names the skill-routing substrate.
