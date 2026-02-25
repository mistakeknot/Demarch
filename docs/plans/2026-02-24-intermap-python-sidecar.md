# Intermap Python Sidecar Plan

**Bead:** iv-3wmf2
**Phase:** executing (as of 2026-02-25T06:34:14Z)
**Brainstorm:** docs/brainstorms/2026-02-24-intermap-python-sidecar-brainstorm.md

## Phase 1: Python Sidecar Mode

### Task 1.1: Add `--sidecar` mode to Python `__main__.py`
- [x] Add `--sidecar` flag to argparse
- [x] When `--sidecar`, enter a read-stdin/write-stdout loop:
  ```python
  while True:
      line = sys.stdin.readline()
      if not line:
          break  # EOF — Go side closed
      req = json.loads(line)
      try:
          result = dispatch(req["command"], req["project"], req.get("args", {}))
          resp = {"id": req["id"], "result": result}
      except Exception as e:
          resp = {"id": req["id"], "error": {"type": type(e).__name__, "message": str(e)}}
      sys.stdout.write(json.dumps(resp) + "\n")
      sys.stdout.flush()
  ```
- [x] Keep existing `--command/--project/--args` CLI mode working (backward compat)
- [x] Use `python3 -u` (unbuffered) in Go spawn to avoid stdout buffering deadlocks

### Task 1.2: Test sidecar mode in isolation
- [x] Add `python/tests/test_sidecar.py`:
  - Start sidecar as subprocess
  - Send 3 JSON-RPC requests on stdin
  - Verify correct JSON responses on stdout
  - Send EOF, verify clean exit
  - Test error handling (bad JSON, unknown command)

## Phase 2: Go Bridge Sidecar

### Task 2.1: Refactor `Bridge` to manage a persistent subprocess
- [x] Add fields to `Bridge` struct:
  ```go
  type Bridge struct {
      pythonPath string
      timeout    time.Duration
      mu         sync.Mutex     // serializes requests
      proc       *exec.Cmd
      stdin      io.WriteCloser
      stdout     *bufio.Scanner
      nextID     int64
  }
  ```
- [x] Add `Bridge.start(ctx)` method: spawns `python3 -u -m intermap --sidecar` with PYTHONPATH set, captures stdin/stdout pipes
- [x] Add `Bridge.stop()` method: closes stdin (triggers Python EOF exit), waits for process
- [x] Modify `Bridge.Run()`:
  1. Lock mutex (serial access)
  2. If proc is nil or exited → call `start()`
  3. Write JSON request line to stdin
  4. Read JSON response line from stdout
  5. If read fails (EOF/error) → proc died, set proc=nil, retry once via `start()` + resend
  6. Match response ID, unmarshal result
  7. Unlock
- [x] Keep 60-second timeout per request via context

### Task 2.2: Add lifecycle management
- [x] Add `Bridge.Close()` method (calls `stop()`)
- [x] Wire `Bridge.Close()` into MCP server shutdown — call from `main.go` via deferred cleanup
- [x] Add respawn backoff: if sidecar crashes 3 times within 10 seconds, fall back to per-call subprocess mode (existing behavior) and log a warning

### Task 2.3: Test Go bridge sidecar
- [x] Add `internal/python/bridge_test.go`:
  - Test `Run()` with real Python sidecar subprocess
  - Test crash recovery: kill Python process mid-request, verify auto-respawn
  - Test graceful shutdown: call `Close()`, verify Python exits cleanly
  - Test timeout: send request to slow command, verify context cancellation

## Phase 3: Cleanup and Polish

### Task 3.1: Update CLAUDE.md
- [x] Document sidecar architecture in intermap CLAUDE.md
- [x] Add sidecar test command to quick commands section

### Task 3.2: Commit and push
- [x] Run full test suite: `go test ./...` and `PYTHONPATH=python python3 -m pytest python/tests/ -v`
- [x] Commit with conventional format

## Files Changed

### Python (python/intermap/)
- `__main__.py` — add `--sidecar` loop mode
- `tests/test_sidecar.py` — **new**, sidecar integration tests

### Go (internal/python/)
- `bridge.go` — persistent subprocess management, Run() rewrite
- `bridge_test.go` — **new**, sidecar bridge tests

### Go (cmd/intermap-mcp/)
- `main.go` — add `defer bridge.Close()` for graceful shutdown

### Docs
- `CLAUDE.md` — document sidecar architecture
