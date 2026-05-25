# Handoff — A2A outbound shipped; pick up `.4` (OAuth2 RI) or pivot

**Date:** 2026-05-25
**From:** sleeper-service (laptop session)
**To:** zklw (dedicated dev server)
**Parent bead arc:** `sylveste-ewy3.4.1` — A2A native transport for Intercom
**Status at handoff:** `.1`, `.2`, `.3` closed and pushed; `.4` is the last open sub-bead

---

## TL;DR

Three of four A2A sub-beads are landed and pushed. The wire is now symmetric — inbound, task store, SSE streaming, and outbound peer-to-peer delivery all work. The remaining sub-bead is **`.4` OAuth2 Resource Indicators**, which is gated on **`sylveste-ewy3.3` (Gridfire-v1 design)** that hasn't been scoped yet. Two clean pickup paths on zklw:

1. **Scope ewy3.3 first** (Gridfire-v1 token broker design) → then implement .4
2. **Pivot to another Tier-1 P0** while .4 waits on its dependency

Recommended pickup: option 2 (scoping a security/auth bead deserves a fresh session, and there are unblocked P0s sitting in the queue).

---

## State at handoff

### Commits to pull on zklw

```
cd /home/mk/projects/Sylveste && git pull --rebase
cd apps/Intercom && git pull --rebase
```

| Repo | Head SHA | Subject |
|------|----------|---------|
| `Sylveste` | `1099c011` | beads: close sylveste-ewy3.4.1.3 — outbound A2A client landed |
| `Sylveste/apps/Intercom` (nested) | `1b4514c` | feat(transport/a2a): outbound A2A client (sylveste-ewy3.4.1.3) |

Both pushed to `main`. Branch protection bypassed via the existing rule on `mistakeknot/Sylveste` and `mistakeknot/intercom` — no PR needed.

### Bead state

```
sylveste-ewy3.4.1 — Implement A2A native transport          [P0 · IN_PROGRESS]
├── .1 SSE streaming + per-task event broker                [P1 · CLOSED]
├── .2 Task store + GET/POST /tasks endpoints               [P1 · CLOSED]
├── .3 Outbound A2A client (Send to remote A2A peers)       [P1 · CLOSED] ← just landed
└── .4 OAuth2 Resource Indicators on /messages + /tasks     [P1 · OPEN]
    └─ depends on sylveste-ewy3.3 (Gridfire-v1 implementation)
```

Parent `ewy3.4.1` stays `in_progress` until `.4` lands.

---

## What `.3` actually shipped

Files in `apps/Intercom/go/internal/transport/a2a/`:

| File | What |
|------|------|
| `outbound.go` (NEW, 172 LOC) | `Resolver` interface + `MapResolver`; `WithBearerToken` ctx helper; Agent Card cache with TTL (`DefaultAgentCardTTL=5m`); `sendOutbound` and `fetchAgentCard` |
| `outbound_test.go` (NEW, 242 LOC) | Co-hosted Server↔Server round-trip; 8 edge cases (no resolver, unknown recipient, bearer present/absent, peer non-2xx, cache hits, TTL expiry, sentinel wrapping) |
| `server.go` (modified) | `Config` gains `Resolver` / `OutboundHTTP` / `AgentCardTTL`; `Server` gains `resolver` / `httpClient` / `cardCache`; `Send` body replaced; `ErrOutboundNotImplemented` deleted |
| `server_test.go` (modified) | Removed obsolete `TestSendReturnsOutboundNotImplemented` |
| `stream_test.go` (modified) | Drive-by fix for `TestStreamUntilFinal_ExitOnClientCancel` flake — poll for `defer Unsubscribe` instead of asserting immediately after client cancel |
| `AGENTS.md` | Added `outbound.go` / `outbound_test.go` to file table; status note now reflects `.3` landed |

**Tests:** 34/34 a2a pass under `-race`. Full suite (`go test ./...` from `apps/Intercom/go/`) is green.

**Key design points:**
- **Resolver decoupling.** `Resolver` is an interface so `MapResolver` works in tests / small static deployments while production wires a registry-backed resolver (separate bead later). Unknown recipients return wrapped `ErrUnknownRecipient` — caller detects with `errors.Is`.
- **Card cache is best-effort.** `fetchAgentCard` failures are non-fatal in `sendOutbound`; the `/messages` POST is the load-bearing call. Capability negotiation against the card lives in a future bead.
- **Bearer-token pass-through, not acquisition.** `WithBearerToken(ctx, token)` puts a token on the request context; the outbound POST emits `Authorization: Bearer <token>`. Full OAuth2 client_credentials + Resource Indicators acquisition is the `.4` work.
- **Wire is symmetric.** Same `extractSenderURI` path handles both inbound peer messages and the round-trip from this outbound client; tests verify this directly via two co-hosted `Server`s.

---

## Pickup options

### Option A — Scope `sylveste-ewy3.3` then implement `.4`

`.4` is blocked on Gridfire-v1 (canonical OAuth2 broker for cross-agent token confusion prevention via RFC 8707 Resource Indicators). Steps to unblock:

1. `bd show sylveste-ewy3.3` — read the existing strategic bead
2. Read `docs/canon/intercom-transport-target.md` §Authentication and the Gridfire research notes (search for "Gridfire" under `docs/research/`)
3. Brainstorm a v1 design: where does the token broker live (intercomd? separate service?), how do agents present their identity for client_credentials grant, what's the resource-indicator format
4. Write design doc → file bead(s) for the implementation
5. Then `.4` becomes implementing the wire-level token verification against the broker

This is real architecture work. Worth a fresh session and probably some external research (Anthropic's recent MCP OAuth spec, A2A spec §7).

### Option B — Pivot to another Tier-1 P0

Untouched P0s with no blocking dependencies:

| Bead | Title | Notes |
|------|-------|-------|
| `sylveste-22oi` | Auraken → Hermes overlay strategic epic | **Structurally unblocked by `ewy3.4.1` work** — Hermes is the Sylveste agent the A2A transport will carry. This is the natural follow-on if you want to push the Hermes pivot forward. |
| `sylveste-iaqg` | Pre-Launch Readiness epic | Big-picture readiness work for the Mythos launch |
| `sylveste-myyw` | Autonomy A:L3 calibration loops | Calibration infrastructure for safer agent autonomy |
| `sylveste-oyrf` | Longitudinal cost-calibration + Mythos launch artifacts | Cost tracking work; touches `interstat`/`cass` analytics |
| `sylveste-bzg5` | Promote `fd-safety` to mandatory | Promotes the safety reviewer to a required step in flux-drive review |

**Recommended:** `sylveste-22oi` (Hermes overlay) — directly leverages what just shipped and unblocks the broader Mythos arc.

### Option C — Step back to strategic review

After 3 substantial sub-beads landed, it may be worth running `/clavain:reflect` or `/clavain:sprint-status` on zklw to capture the arc, then pick the next epic with a fresh assessment.

---

## Zklw environment notes (gotchas hit this session)

These bit me on the laptop and might bite on zklw if not anticipated:

1. **Go binary path.** `go` is not in `$PATH`; the binary lives at `/usr/local/go/bin/go`. Either add to PATH in shell profile or alias. Check first: `which go || ls /usr/local/go/bin/go`.
2. **Nested git repos.** `apps/Intercom/` is its own git repo (`git@github.com:mistakeknot/intercom.git`), not a submodule of Sylveste. `git status` from `apps/Intercom/` doesn't see Sylveste outer-repo changes and vice versa. Always be explicit about which repo you're committing in. Per memory `feedback_explicit_pathspec_commits.md`: use `git commit -- <paths>` to avoid bundling parallel-session work.
3. **`bd` CLI works on zklw** (not a cloud session), so the full beads workflow applies: `bd update --status in_progress` before code, `bd close` after, `bd backup sync` before push (auto-runs every 5m but force before push).
4. **JSONL state.** `.beads/issues.jsonl` is already committed with `.3` closed (in commit `1099c011`). Pulling will give you the up-to-date bead state.
5. **Branch protection.** Both repos warn "Changes must be made through a pull request" on push, but the rule is bypassed for the configured identity — pushes land. Treat the warning as advisory.
6. **`bd backup sync` quirk.** On this machine it printed help text rather than running — workaround: `bd export -o /tmp/x.jsonl` forces a JSONL refresh. The auto-sync at 5min still works regardless. Probably env-specific; try `bd backup sync` first on zklw.
7. **System reminders nag about TaskCreate.** Ignore them — project rule is all work in beads, no TodoWrite/TaskCreate.

---

## First commands on zklw

```bash
# 1. Sync both repos
cd /home/mk/projects/Sylveste && git pull --rebase
cd apps/Intercom && git pull --rebase

# 2. Verify tests still green on zklw
cd /home/mk/projects/Sylveste/apps/Intercom/go && go test ./... -count=1 -race | tail -20

# 3. Confirm bead state
cd /home/mk/projects/Sylveste
bd show sylveste-ewy3.4.1.3   # should show CLOSED
bd show sylveste-ewy3.4.1.4   # should show OPEN, P1
bd dep tree sylveste-ewy3.4.1 # see the full sub-bead arc

# 4. Pick a path
#    A: bd show sylveste-ewy3.3 && less docs/canon/intercom-transport-target.md
#    B: bd show sylveste-22oi
#    C: /clavain:sprint-status
```

---

## What to tell the next session

If starting fresh in Claude Code on zklw, paste this into the first message:

> Read `docs/handoffs/2026-05-25-a2a-outbound-shipped-zklw-handoff.md` and pick up from the "First commands on zklw" section. I want to [option A / option B / option C — pick one].

If you choose option B with `sylveste-22oi`, also point the agent at the relevant memory entry: `project_auraken_hermes_pivot.md`.

---

## Memory entries worth re-reading before next session

- `feedback_auto_proceed_vetted_flow.md` — auto-proceed gate for bead-close
- `feedback_explicit_pathspec_commits.md` — `git commit -- <paths>` in shared monorepos
- `feedback_dont_clobber_through_symlink.md` — `ln -sf` for `latest.md`, never `cat >` or Write
- `intercom.md` — Intercom-specific gotchas
- `project_auraken_hermes_pivot.md` — if pivoting to option B
- `beads-workflow.md` — full beads workflow reference
