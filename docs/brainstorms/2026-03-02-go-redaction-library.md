**Bead:** iv-r6u9q

# Brainstorm: Go Redaction Library for Autarch/Intercore

## Context

The bead assumes we need to build a Go redaction library from scratch by porting Hermes's Python `redact.py`. However, **a comprehensive Go redaction library already exists** at `core/intercore/internal/redaction/` (784 LOC, 28 patterns, 17 categories, full test suite). It was ported from NTM's redaction module, not Hermes.

The real work is threefold:
1. **Promote** the library from `internal/` to a shared package so autarch can import it
2. **Add missing patterns** from Hermes that the NTM port doesn't cover
3. **Wire redaction** into persistence paths that currently skip it

## What Exists (core/intercore/internal/redaction/)

### API Surface
- `ScanAndRedact(input string, cfg Config) Result` — main entry, mode-driven (off/warn/redact/block)
- `Scan(input string, cfg Config) []Finding` — read-only detection
- `Redact(input string, cfg Config) (string, []Finding)` — convenience redaction
- `ContainsSensitive(input string, cfg Config) bool` — boolean check
- `AddLineInfo(input string, findings []Finding)` — enriches findings with line/column

### Pattern Categories (17)
Provider-specific (7): OpenAI (3 variants), Anthropic, GitHub (2 variants), Google API
Cloud (3): AWS access key (AKIA/ASIA), AWS secret key
Auth (3): JWT, Bearer token, Private key (RSA/DSA/EC/OPENSSH)
Connection (1): Database URL (postgres/mysql/mongodb/redis)
Demarch-specific (4): Notion (2 variants), Slack (3 variants), HuggingFace, Exa
Generic (3): Password, Generic API key, Generic secret

### Features
- Priority-based pattern matching (30-100 scale)
- Overlap deduplication (higher priority wins)
- Configurable allowlist (regex-based)
- Extra pattern injection at runtime
- Disabled category support
- Deterministic placeholders: `[REDACTED:CATEGORY:hash8]`

### Integration
- Used by `internal/audit/audit.go` — all audit payloads auto-redacted before INSERT
- NOT used by `internal/event/store.go` — events written without redaction
- NOT available to autarch (Go `internal/` visibility rules)

## What's Missing

### Hermes patterns not in NTM port
1. **Telegram bot tokens** — `(\d{8,}):[-A-Za-z0-9_]{30,}`
2. **Perplexity API keys** — `pplx-[A-Za-z0-9]{10,}`
3. **Fal.ai keys** — `fal_[A-Za-z0-9_-]{10,}`
4. **Firecrawl keys** — `fc-[A-Za-z0-9]{10,}`
5. **BrowserBase keys** — `bb_live_[A-Za-z0-9_-]{10,}`
6. **Codex encrypted tokens** — `gAAAA[A-Za-z0-9_=-]{20,}`
7. **ENV assignment patterns** — `KEY=value` where KEY contains secret-like keywords
8. **Authorization header patterns** — `Authorization:\s*Bearer\s+\S+`

Note: #7 and #8 overlap with existing generic patterns but are separate in Hermes for different masking behavior.

### Persistence gaps (P0 from fd-security-patterns review)
1. `core/intercore/internal/event/store.go` — phase events, dispatch events, coordination events, review events, replay inputs — all written without redaction
2. `apps/autarch/pkg/events/store.go` — event payloads persisted without redaction
3. Coldwine, Gurgeh, Pollard data dirs — session/transcript files may contain credentials

## Options

### A: Promote to pkg/ in intercore
Move `internal/redaction/` → `pkg/redaction/` within intercore. Autarch already depends on intercore via `replace` directive in go.mod.

- **Pro:** Minimal change, no new module, uses existing dependency graph
- **Con:** Check if autarch actually has a replace directive to intercore (it doesn't currently — it has one to intermute only)
- **Con:** Couples autarch's redaction to intercore's release cycle

### B: Extract to sdk/interbase/go/redaction/
Create a new package under the shared SDK. Both autarch and intercore add `replace` directives.

- **Pro:** Architecturally clean — shared SDK is the right layer for cross-cutting concerns
- **Pro:** Independent versioning
- **Con:** Need to check if sdk/interbase/go/ has a Go module already
- **Con:** More plumbing (two replace directives to add)

### C: Copy to autarch, keep both
Duplicate the package into autarch with autarch-specific additions.

- **Pro:** Zero coupling
- **Con:** Drift risk — two copies to maintain
- **Con:** Violates DRY

### D: Promote to pkg/ in intercore + add autarch replace directive
Combines A with adding the missing intercore dependency to autarch.

- **Pro:** One canonical location, minimal new infrastructure
- **Pro:** intercore is L1 (kernel) — security utilities belong at L1
- **Con:** Still couples autarch to intercore

## Recommendation

**Option D** — promote to `pkg/redaction/` within intercore and add a `replace` directive in autarch's go.mod. Rationale:

1. The library already lives in intercore — promotion is a one-line move
2. Intercore is L1 (kernel layer) — security primitives belong here by architecture
3. Autarch already uses `replace` directives for monorepo dependencies (intermute)
4. Adding another `replace` is standard monorepo Go practice
5. No new module or SDK infrastructure needed — minimize blast radius

If a third module needs redaction later, that's when to consider SDK extraction.

## Work Items

1. **Move** `internal/redaction/` → `pkg/redaction/` in intercore
2. **Update** imports in `internal/audit/audit.go`
3. **Add** `replace github.com/mistakeknot/intercore => ../../core/intercore` to autarch's go.mod
4. **Add** missing Hermes patterns (Telegram, Perplexity, Fal, Firecrawl, BrowserBase, Codex, ENV assignments)
5. **Wire** redaction into intercore's `internal/event/store.go` (all event INSERT paths)
6. **Wire** redaction into autarch's `pkg/events/store.go`
7. **Add** tests for new patterns
8. **Verify** all existing tests still pass after move

## Estimated Effort

- Pattern promotion + import updates: ~30 min
- New patterns + tests: ~1 hour
- Persistence wiring (intercore events): ~1 hour
- Persistence wiring (autarch events): ~1 hour
- Total: ~3.5 hours (half day)
