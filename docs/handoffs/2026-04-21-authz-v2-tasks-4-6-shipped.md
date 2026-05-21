---
date: 2026-04-21
session: 2a2f9314
topic: authz v2 tasks 4-6 shipped
beads: [sylveste-qdqr.28]
---

## Session Handoff — 2026-04-21 authz v2 Tasks 4-6 shipped

### Directive
> Your job is to finish `/clavain:sprint sylveste-qdqr.28` by shipping Tasks 7 and 8. Start by pushing the two unpushed commits (`os/Clavain@8e59827`, `core/intercore@55f334b`), then pick up Task 7 at `docs/plans/2026-04-21-auto-proceed-authz-v2.md:830`. Verify each task with its `<verify>` block before committing.
- Bead: `sylveste-qdqr.28` — in_progress, phase:executing, sprint=true. Tasks 1-6 ✓; 7 (bootstrap+docs, ~3 files) and 8 (e2e script, 20 scenarios) remain.
- Task 7 verify: `bash os/Clavain/scripts/authz-init.sh --with-token-demo 2>&1 | grep -c 'Demo token issued'` == 1 ; `grep -c '^## .*[Tt]oken' os/Clavain/README.md` ≥ 1.
- Task 8 verify: new `os/Clavain/tests/authz-v2-e2e_test.sh` tail contains "PASS"; `tests/authz-v15-e2e_test.sh` tail still contains "PASS".
- Fallback (if pushed off scope): Fix pre-existing baseline failures (see Context) as their own bead — they are NOT in Task 7/8's verify scope.

### Dead Ends
- Naming the test helper `captureStdout` — collides with `os/Clavain/cmd/clavain-cli/intent.go:18`. Use `captureTokenStdout` (or local-scoped name) for future test-stdout captures in that package.
- Adding `--vetting-via=<value>` to `policy record` inside Task 5/6 scope — deferred because the adoption-gate telemetry query relies on `ConsumeToken`'s vetting JSON alone for the token path; marker/authz-record rows stay untagged until a follow-on bead adds the flag. Do NOT try to back-fill this in Task 7.

### Context
- `core/intercore/internal/publish/state.go` now has `func (s *Store) DB() *sql.DB` (added this session). `engine.Publish` calls `e.store.DB()` to share the connection pool with the token-consume path — `MaxOpenConns=1` serialization invariant depends on the same handle. Don't bypass with a second `sql.Open`.
- Auth-failure exit 4 must hard-fail in THREE places: CLI (`os/Clavain/cmd/clavain-cli/authz_token.go` `reportTokenErr` → `tokenExit` → `main.go` ExitCoder), gate wrapper (`scripts/gates/_common.sh` `gate_token_consume` returns 1), approval (`internal/publish/approval.go` returns `(true, ViaNone)`). Any new consumer must replicate this.
- `cmd/ic/publish.go` reads `CLAVAIN_AUTHZ_TOKEN` + `CLAVAIN_AGENT_ID` once at the composition root and immediately `os.Unsetenv("CLAVAIN_AUTHZ_TOKEN")` so child procs don't inherit. Token value lives only in `PublishOpts` after that call.
- `config/routing.yaml` in `os/Clavain` has parallel-session WIP — keep NOT staging it. Commit Task 7/8 files explicitly by path.
- Go binary at `/usr/local/go/bin/go` — not on default PATH. Prefix every go command with `export PATH="/usr/local/go/bin:$PATH" && GOTOOLCHAIN=local`.
- Smoke test (`scripts/gates/gates-smoke_test.sh`) no-ops if `cmd/clavain-cli/clavain-cli` binary missing. Build it first: `cd os/Clavain/cmd/clavain-cli && go build -o clavain-cli .`. Supports `--focus=legacy|token|all`.
- Pre-existing baseline failures (confirmed on `ff83ab8`, NOT caused by this session): `internal/db/TestMigrator_V22ToV23_AuditTraceID` expects `applied == 11` but gets 12 — migration 034 (Task 2) added but test assertion at `migrator_test.go:121-122` + comment at line 125 not bumped. Also `internal/event/TestAddDispatchEvent_DefaultEnvelope` + `TestListEvents_CausalReconstructionByTraceID` fail with `trace_id = "..." want run-env`. Task 7/8 verify is scoped narrowly; these don't block, but file a separate bead.
- Plan path: `/home/mk/projects/Sylveste/docs/plans/2026-04-21-auto-proceed-authz-v2.md` (r3, 985 lines). Tasks 7 + 8 are at lines 830 and 898 respectively. Task 8 explicitly references the `testfault` build tag for its fault-injection scenario — `core/intercore/pkg/authz/token_faultinject_test.go` already has the hook wired.
- oklog/ulid/v2 is now an indirect dep in `os/Clavain/cmd/clavain-cli/go.mod` (added this session via `go mod tidy` under `GOTOOLCHAIN=local`). Pin stayed at `go 1.22`.
