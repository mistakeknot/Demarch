# Plan: Dashboard Views Local File Fallback

**Bead:** iv-gax

## Problem

All three Autarch dashboard views (Gurgeh, Coldwine, Pollard) fetch data exclusively through the Intermute HTTP API (`autarch.Client` → `http://127.0.0.1:7338`). If Intermute is not running, all views show errors and are unusable. The local data files (`.gurgeh/`, `.tandemonium/`, `.pollard/`) contain the same information but are never read by the TUI directly.

## Solution

Add a `DataSource` interface to `pkg/autarch/` for read operations. Implement two backends: `HTTPSource` (existing client logic) and `LocalSource` (reads dot-directories). The `Client` gains a session-level fallback flag: on first dial failure, switch to `LocalSource` for the remainder of the session. Views see a `InFallbackMode() bool` to display a status indicator.

**Key design decisions from review:**
- **Graceful degradation with notice**, not transparent fallback — user always knows their data source
- **Session-level fallback flag** — once in fallback, stay there until restart (prevents split-brain renders)
- **Dial failures only** — do NOT fall back on timeout (server may be alive but slow)
- **Short probe timeout** — 2-3s connection probe, separate from 30s operational timeout
- **`LocalSource` lives in `internal/autarch/local/`** — cannot live in `pkg/autarch/` (would import `internal/` packages)

## Architecture

```
View.loadSpecs() → Client.ListSpecs()
                      │
                      ├── fallbackActive == false
                      │     └── HTTPSource.ListSpecs()  (2s dial probe)
                      │           ├── success → return data
                      │           └── dial error → set fallbackActive=true, fall through ↓
                      │
                      └── fallbackActive == true
                            └── LocalSource.ListSpecs()
                                  └── reads .gurgeh/specs/*.yaml

Client.InFallbackMode() → checked by footer renderer → shows [offline] badge
```

## Tasks

- [x] **1. Define `DataSource` interface in `pkg/autarch/source.go`**
  - `DataSource` interface with `ListSpecs`, `ListEpics`, `ListStories`, `ListTasks`, `ListInsights`
  - `HTTPSource` wraps existing client HTTP methods (extracted from `client.go`)
  - Keep `Client` as the public API; it delegates to whichever `DataSource` is active

- [x] **2. Create `internal/autarch/local/source.go`** — file-based reader
  - `LocalSource` struct with `projectPath string`
  - `NewLocalSource(projectPath string) *LocalSource`
  - **ListSpecs**: delegates to `specs.LoadAllPRDs(projectPath)`, converts via mapping below
  - **ListEpics/Stories/Tasks**: opens `.tandemonium/state.db` with fresh `sql.DB` (NOT `OpenShared`), `defer db.Close()`. Guard with `PRAGMA table_info(epics)` — return empty slice if table absent (MigrateV2 not applied)
  - **ListInsights**: reads `.pollard/insights/*.yaml` via existing loader
  - **Error contract**: missing dot-directory → `([]T{}, nil)`. I/O or parse error → `(nil, err)`
  - **Legacy paths**: `.praude/` for Gurgeh (via `specs.LoadAllPRDs` which already handles this)

- [x] **3. Field mapping (explicit)**

  | Local type | Field | → autarch type | Field | Notes |
  |------------|-------|----------------|-------|-------|
  | `specs.PRD` | `.Version` | `Spec` | `.ID` | Synthetic ID (e.g. "mvp"), distinct from UUID |
  | `specs.PRD` | `.Title` | `Spec` | `.Title` | Direct |
  | `specs.PRD` | `.CreatedAt` (string) | `Spec` | `.CreatedAt` | Parse RFC3339, NOT `time.Now()` |
  | `specs.PRD` | `.UpdatedAt` (string) | `Spec` | `.UpdatedAt` | Parse RFC3339 |
  | `specs.PRD` | `.Status` | `Spec` | `.Status` | Via `mapPRDStatusToSpecStatus` |
  | `storage.Epic` | `.FeatureRef` | `Epic` | `.SpecID` | Different namespace — documented |
  | `storage.Epic` | `.Title/.Status` | `Epic` | `.Title/.Status` | Direct |
  | `insights.Insight` | `.Sources[0].Type` | `Insight` | `.Source` | Guard: empty → `"local"` |
  | `insights.Insight` | `.Sources[0].URL` | `Insight` | `.URL` | Guard: empty → `""` |
  | `insights.Insight` | (none) | `Insight` | `.Body` | `""` — not available locally |

- [x] **4. Add fallback to `pkg/autarch/client.go`**
  - Add `fallback DataSource` field, `fallbackActive bool`, `probeClient *http.Client` (2s timeout)
  - `WithFallback(ds DataSource) *Client` setter — call BEFORE distributing client to views
  - `InFallbackMode() bool` — views check this for status indicator
  - `isDialError(err error) bool` — `errors.As(*net.OpError)` where `Op == "dial"` + `syscall.ECONNREFUSED`. NO timeout.
  - On first `isDialError`, set `fallbackActive = true` for session lifetime
  - All `List*` methods: if `fallbackActive`, go directly to `c.fallback.List*()`

- [x] **5. Wire fallback in `cmd/autarch/main.go`**
  - Create `LocalSource` BEFORE creating `NewUnifiedApp`
  - `client.WithFallback(local.NewLocalSource(projectPath))` before client is distributed

- [x] **6. Add offline badge to footer**
  - In the shared footer renderer, check `client.InFallbackMode()`
  - Render `[offline]` badge next to the lastUpdate timestamp
  - Write-attempt in fallback mode: return `fmt.Errorf("Intermute is not running — writes unavailable. Start with: autarch tui")` instead of raw connection error

- [x] **7. Tests**
  - `TestLocalSource_ListSpecs` — temp `.gurgeh/specs/mvp.yaml`, verify field mapping
  - `TestLocalSource_ListSpecs_Legacy` — temp `.praude/specs/mvp.yaml`, verify legacy path
  - `TestLocalSource_ListEpics` — temp `.tandemonium/state.db` with V2 schema, verify
  - `TestLocalSource_ListEpics_NoV2` — temp DB without V2 migration, verify empty slice (not error)
  - `TestLocalSource_ListInsights` — temp `.pollard/insights/test.yaml`, verify lossy mapping
  - `TestLocalSource_MissingDir` — returns `([]T{}, nil)` for missing dot-dirs
  - `TestClient_FallbackOnDialError` — mock server that refuses connections, verify fallback fires
  - `TestClient_NoFallbackOnTimeout` — mock server that hangs, verify NO fallback
  - `TestClient_SessionStickyFallback` — after first dial error, subsequent calls skip HTTP

- [x] **8. Test end-to-end** — `go test ./... -race` in autarch

## Non-Goals

- No fallback for write operations (Create/Update/Delete) — those still require Intermute
- No fallback for Session operations — sessions are Intermute-native
- No automatic sync from local files back to Intermute
- No reconnection detection (fallback persists until restart) — can add later

## Files Changed

| File | Change |
|------|--------|
| `pkg/autarch/source.go` | New — `DataSource` interface |
| `internal/autarch/local/source.go` | New — file-based `LocalSource` |
| `internal/autarch/local/source_test.go` | New — tests |
| `pkg/autarch/client.go` | Add fallback field, `isDialError`, `InFallbackMode`, probe client |
| `pkg/autarch/client_test.go` | New or extend — fallback behavior tests |
| `cmd/autarch/main.go` | Wire `WithFallback()` before view creation |
| Footer renderer (shared) | Add `[offline]` badge |

## Review Findings Addressed

| Finding | Source | Resolution |
|---------|--------|------------|
| `pkg/autarch` can't import `internal/` | fd-architecture | `LocalSource` in `internal/autarch/local/`, interface in `pkg/autarch/` |
| `epics` table only in MigrateV2 | fd-correctness | Guard with `PRAGMA table_info(epics)` |
| `FeatureRef` vs `SpecID` namespace | fd-correctness | Documented in mapping table |
| 30s timeout freeze | fd-user-product | 2-3s probe client, fallback only on dial errors |
| Split-brain renders | fd-correctness | Session-level `fallbackActive` flag |
| `mapPRDToSpec` uses `time.Now()` | fd-correctness | Parse PRD's RFC3339 timestamps |
| Spec ID blank in fallback | fd-correctness | Use `prd.Version` as synthetic ID |
| `Sources[]` → single `Source` lossy | fd-correctness | Guard empty slice, document lossy mapping |
| `OpenShared` never closes | fd-correctness | Use fresh `sql.DB` with `defer Close()` |
| No offline indicator | fd-user-product | `[offline]` footer badge |
| Write failures opaque | fd-user-product | Clear error message naming remedy |
| `ErrNotAvailable` contradiction | fd-correctness | Empty slice for missing dir, error for I/O failure |

## Reference Code

- `internal/gurgeh/specs/prd.go` — `LoadAllPRDs()` reads `.gurgeh/specs/*.yaml` (handles `.praude/` legacy)
- `internal/gurgeh/intermute/sync.go` — `mapPRDToSpec()` for field mapping reference
- `internal/coldwine/storage/epic.go` — `ListEpics()` reads from SQLite
- `internal/coldwine/storage/db.go` — `Open()` / `OpenShared()` / `MigrateV2()`
- `internal/coldwine/project/paths.go` — `StateDBPath()` → `.tandemonium/state.db`
- `internal/pollard/insights/insight.go` — YAML-based insight loader
