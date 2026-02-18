# Architecture Review: intercore PRD

**Date:** 2026-02-17
**Document:** `/root/projects/Interverse/docs/prds/2026-02-17-intercore-state-database.md`
**Reviewer:** Claude Opus 4.6 (Architecture & Design)

## Executive Summary

The intercore PRD proposes a Go CLI + SQLite database to consolidate ~15 scattered temp files in `/tmp/` under a unified state management layer. While the core problem (TOCTOU races, invisible cross-session state, pattern fragmentation) is valid, the solution exhibits **four architectural concerns** that risk creating coupling issues, boundary confusion, and accidental complexity.

**Key findings:**
1. **P0 - Boundary violation**: Plugin location mismatches foundational infrastructure role
2. **P1 - Mixed paradigm**: Schema combines generic key/value state with structured domain tables
3. **P2 - Overlap risk**: Relationship to beads (bd) is underspecified, creates dual persistence layer
4. **P2 - Feature ordering**: F4 (run tracking) should precede F2/F3 to avoid schema churn

## 1. Plugin Boundary Analysis (P0)

### Finding: Foundational Infrastructure in Companion Plugin Location

**Concern:** The PRD places intercore at `plugins/intercore/`, making it a companion plugin to Clavain. However, its role as "unified state database" for hook infrastructure means **other plugins will depend on it**.

**Evidence from architecture:**
- Multiple plugins reference temp files intercore aims to replace:
  - `interline` reads `/tmp/clavain-dispatch-$$.json` (dispatch.sh lines 58-61)
  - `interphase` reads bead phase state from `~/.interband/interphase/bead/${SID}.json` (PRD line 96)
  - Clavain hooks use 15+ temp files (`lib-sprint.sh`, `session-handoff.sh`, etc.)
- F7 "dual-write mode" explicitly names `interline` and `interband` as consumers (line 91)
- Companion plugins shouldn't be dependencies of the hub — this inverts the relationship graph

**Current Interverse module relationships** (from AGENTS.md lines 66-95):
```
clavain (hub)
├── interphase  (phase tracking)
├── interline   (statusline)
├── interflux   (review)
└── [11 other companions]

interject (MCP)    ← standalone, uses intersearch
intermute (service) ← used by interlock
```

**Proposed with intercore:**
```
clavain (hub) ──depends on──> intercore (plugin)
   ↑                             ↑
   └── interline ────────────────┘
   └── interphase ───────────────┘
```

This creates **hub-depends-on-companion**, which violates the module hierarchy principle: dependencies should flow from periphery to center, not center to periphery.

**Architectural alternatives:**

| Location | Pros | Cons |
|----------|------|------|
| `services/intercore/` | Matches intermute precedent, clear infrastructure role | Requires service management, heavier than CLI |
| `infra/intercore/` | Signals foundational role, no dependency inversion | No existing CLI precedent in `infra/` |
| `hub/clavain/lib/intercore/` | Keeps state local to hub, no external deps | Doesn't solve cross-plugin state sharing |
| `plugins/intercore/` (PRD) | Easiest installation path, follows plugin pattern | **Dependency inversion, coupling antipattern** |

**Recommendation (P0):**
1. Move to `infra/intercore/` — signals platform infrastructure, not plugin
2. Install CLI to `/usr/local/bin/ic` or `~/.local/bin/ic` (system tool, not plugin-scoped)
3. Revise installation story: binary distributed via marketplace or compiled on `git clone` (no plugin hooks needed)
4. Update plugin manifest references to `intercore` to use PATH-based discovery, not plugin dependency

**Migration path:**
- Start at `infra/intercore/` from day one (not a move, initial placement)
- Add `ic` to PATH in server setup scripts
- Document in `~/.codex/AGENTS.md` as a foundational tool (like `bd`, `jq`, `uv`)

---

## 2. Schema Design Paradigm Mix (P1)

### Finding: Generic KV Store Mixed with Structured Domain Tables

**Concern:** The schema exhibits two competing paradigms that will create maintenance confusion and migration friction.

**Evidence from PRD schema (lines 15-23, 52-63):**

**Generic paradigm (F2 - State Operations):**
```
state table:
  key, scope_id, scope_type, payload (JSON), expires_at

sentinels table:
  name, scope_id, last_fired
```

**Structured paradigm (F4 - Run Tracking):**
```
runs table:
  id, project, goal, bead_id, session_id, phase, status

agents table:
  id, run_id, type, name, pid, status

artifacts table:
  id, run_id, phase, path, type

phase_gates table:
  id, run_id, phase, entered_at
```

**Analysis:**

The `state` table is a generic key/value store with scope discriminators — this is a document database pattern (MongoDB, DynamoDB). The `runs/agents/artifacts` tables are normalized relational design — this is an RDBMS pattern (PostgreSQL, MySQL).

**Why this is an anti-pattern:**

1. **Query complexity:** Run tracking queries will need to join structured tables, while state queries will parse JSON payloads. Two query styles in one codebase.

2. **Schema evolution:** Adding a new run-tracking field requires migration (ALTER TABLE). Adding a new state key requires no migration (just payload structure). Different change management strategies.

3. **Type safety:** Structured tables enforce column types at write time. JSON payloads defer validation to application logic (or don't validate at all).

4. **Indexing:** Structured tables can index on columns directly. JSON payloads require JSON path indexes (SQLite `json_extract` in WHERE clause), which are slower and harder to maintain.

**Concrete example from the PRD:**

F2 acceptance criteria (line 31): `ic state set <key> <scope_id> '<json>'`
F4 acceptance criteria (line 56): `ic run create --project=<path> --goal=<text>`

These are **two different data models for the same operational domain** (tracking work state). The `state` table could store run metadata as `key=run, scope_id={run_id}, payload={project, goal, phase}`. Or the `runs` table could absorb all state operations as structured columns. But doing both creates **dual persistence** with no clear boundary.

**Evidence of future confusion:**

Open Question #2 (line 120): "Does intercore subsume interband, or does interband become a read-through cache/view?"

This question exists **because the schema is underspecified**. If intercore is a generic state store, interband should be replaced entirely. If intercore is a structured run tracker, interband remains the generic layer. The PRD leaves this unresolved, guaranteeing rework.

**Recommendation (P1):**

**Option A: Commit to structured domain model**
- Remove `state` table entirely
- Add `metadata JSONB` column to `runs` table for extensible fields
- Map all temp file use cases to domain tables:
  - `/tmp/clavain-dispatch-$$.json` → `dispatches` table (structured)
  - `/tmp/clavain-bead-${SID}.json` → `runs` table (phase column)
  - Sentinel touch files → `sentinels` table (already structured)

**Option B: Commit to generic KV store**
- Remove `runs/agents/artifacts/phase_gates` tables
- Use `state` table with well-known key patterns:
  - `key=run_meta, scope_id={run_id}, payload={project, goal, phase, agents: [], artifacts: []}`
  - `key=dispatch, scope_id={session_id}, payload={name, workdir, activity, turns}`
- Add `state_views` table for materialized indexes on common query patterns

**Option C: Separate responsibilities (recommended)**
- Keep `sentinels` table for throttle guards (F3) — this is pure infrastructure, no domain logic
- Keep `state` table for **ephemeral session state** only (TTL'd temp file replacements)
- Move run tracking (F4) to a **separate database** (e.g., `runs.db`) or **separate CLI** (e.g., `bd` extensions)
- Justify the split: ephemeral vs. permanent, infrastructure vs. domain

**Why Option C is cleanest:**

| Concern | State DB (ephemeral) | Run Tracking (permanent) |
|---------|---------------------|--------------------------|
| Scope | Session-local temp files | Cross-session orchestration history |
| TTL | Aggressive (prune after session end) | Conservative (historical analysis) |
| Schema stability | High churn (every new temp file) | Low churn (stable domain model) |
| Consumers | Hooks, bash scripts | Agents, dashboards, analytics |
| Ownership | Infrastructure layer | Domain layer |

Mixing these creates **entanglement** — schema migrations for ephemeral state affect permanent data queries, and vice versa.

---

## 3. Relationship to Beads (P2)

### Finding: Overlap Risk with Existing Issue Tracker State

**Concern:** The PRD non-goal (line 103) says "beads remains authoritative issue tracker and permanent phase store," but F4 run tracking duplicates phase and dependency tracking that beads already provides.

**Evidence from beads capabilities** (bd CLI help, lines in bash commands):

```bash
bd set-state "$sprint_id" "phase=brainstorm"        # lib-sprint.sh:72
bd state "$sprint_id" phase                          # lib-sprint.sh:83
bd set-state "$sprint_id" "sprint_artifacts={}"     # lib-sprint.sh:76
bd create --title="..." --type=epic --priority=2    # lib-sprint.sh:56
bd update "$sprint_id" --status=in_progress         # lib-sprint.sh:79
bd gate ...                                          # bd --help
```

**Beads already provides:**
- State storage (`set-state`, `state` commands) — key/value per bead
- Phase tracking (via state dimensions)
- Status lifecycle (`in_progress`, `closed`, `cancelled`)
- Dependencies (`bd dep add`)
- Gates (`bd gate`, `bd merge-slot`)

**Intercore F4 proposes:**
- `runs` table with `phase` column
- `phase_gates` table with `entered_at` timestamps
- `agents` table with `run_id` foreign key
- `artifacts` table with `run_id, phase, path` columns

**Overlap analysis:**

| Capability | Beads | Intercore F4 | Conflict? |
|------------|-------|--------------|-----------|
| Phase tracking | `bd set-state {id} phase={p}` | `ic run phase {id} {p}` | **YES** — dual write required |
| Run metadata | `bd create --type=epic` | `ic run create --goal={g}` | **YES** — which is source of truth? |
| Agent tracking | `bd agent ...` | `ic agent add {run_id}` | **YES** — separate namespaces |
| Artifact tracking | `bd set-state {id} artifacts={json}` | `ic artifact add {run_id} --path={p}` | **YES** — structured vs JSON |
| Gates | `bd gate`, `bd merge-slot` | `phase_gates` table | **YES** — gate logic duplicated |

**Why this is a problem:**

1. **Dual write burden:** Every phase transition must update both beads state AND intercore `phase_gates` table. If one write fails, they diverge.

2. **Query ambiguity:** Which is authoritative? If beads and intercore disagree on phase, which wins?

3. **Migration trap:** Existing hooks use `bd state` extensively (lib-sprint.sh, session-handoff.sh). F4 requires rewriting all of them to use `ic run phase`, or maintaining dual writes forever.

4. **Discovery confusion:** Beads has `bd ready` for work discovery. Intercore F4 has `ic run list --status=active`. Two discovery surfaces for the same domain.

**Evidence of underspecification:**

PRD line 103: "beads remains the authoritative issue tracker and permanent phase store."

But F4 line 57: "`ic run phase <run_id> <phase>` updates the phase, records in phase_gates."

These are contradictory. If beads is authoritative for phase, why does intercore have a `phase` column? If intercore is authoritative for orchestration runs, why use beads at all?

**Recommendation (P2):**

**Option A: intercore as beads view layer**
- Remove F4 entirely
- Add `ic bead phase {id}` as a wrapper for `bd state {id} phase`
- Add `ic bead run {id}` as a wrapper for `bd show {id} | jq .state`
- intercore becomes a **read-through cache** for beads queries, not a separate data store

**Option B: beads as intercore backend**
- Extend beads with `--json` output for all commands
- Use `bd` as the persistence layer for run tracking
- intercore becomes a **bash library** on top of beads, not a separate DB

**Option C: Clear domain split (recommended)**
- **Beads:** Long-lived issues, dependencies, cross-session planning (permanent)
- **intercore:** Ephemeral session state, throttle guards, temp file replacement (TTL'd)
- **Remove F4 from intercore** — run tracking belongs in beads, not a separate system
- Add `bd run create` to beads CLI instead (structured run metadata as a beads extension)

**Why Option C is architecturally sound:**

| Layer | Responsibility | Lifetime | Storage |
|-------|---------------|----------|---------|
| Beads | Issue tracking, dependencies, phases | Permanent (git JSONL) | `.beads/issues.jsonl` |
| intercore | Session temp files, sentinels | Ephemeral (TTL) | `intercore.db` (pruned) |

No overlap, clean separation of concerns, single source of truth for each domain.

---

## 4. Feature Scoping and Ordering (P2)

### Finding: F4 Should Precede F2/F3 to Avoid Schema Churn

**Concern:** The PRD orders features as F1 (scaffold) → F2 (state ops) → F3 (sentinels) → F4 (run tracking). This ordering guarantees schema churn because F4 introduces new domain concepts that will reshape how F2/F3 are used.

**Evidence from acceptance criteria flow:**

**F2 (State Operations) uses generic keys:**
```bash
ic state set <key> <scope_id> '<json>'  # Line 31
ic state get <key> <scope_id>            # Line 33
```

**F4 (Run Tracking) introduces structured domains:**
```bash
ic run create --project=<path> --goal=<text>  # Line 56
ic agent add <run_id> --type=<type>           # Line 59
ic artifact add <run_id> --phase=<p>          # Line 61
```

**Concrete example of churn:**

After implementing F2, hooks will start using:
```bash
ic state set dispatch "$SESSION_ID" '{"name":"vet","workdir":"/path",...}'
ic state set bead_phase "$BEAD_ID" '{"phase":"architect",...}'
```

After implementing F4, these become:
```bash
ic run create --project=/path --goal="..." --session="$SESSION_ID"  # New pattern
ic run phase "$RUN_ID" "architect"                                   # Structured
```

**Migration cost:**

- All F2 consumers (hooks, bash libs) must be rewritten to F4 patterns
- Or: dual-write compatibility layer forever (technical debt)
- Or: abandon F4 structured tables, stick with F2 generic KV (wasted effort)

**Why this ordering exists (hypothesis):**

The PRD follows "simplest first" ordering — generic KV (F2) is simpler than structured domain model (F4). But in architecture, **domain model drives storage schema**, not the reverse. If run tracking is the primary use case, its schema should be designed first, and ephemeral state (F2) should be secondary.

**Evidence from Interverse patterns:**

Intermute service (services/intermute/) designed domain tables first:
```
agents table → reservations table → messages table
```

No generic `state` table exists — all storage is domain-driven.

tldr-swinton plugin (plugins/tldr-swinton/) uses FAISS index + structured metadata:
```
Embedding vectors → Chunk metadata → Symbol references
```

No generic KV layer — storage follows domain needs.

**Recommendation (P2):**

**Reorder features:**
1. **F1:** Scaffold + empty schema (no tables yet)
2. **F4:** Run tracking domain model (design structured tables first)
3. **F2:** Ephemeral state for temp file replacement (design around F4 schema)
4. **F3:** Sentinels (independent of F2/F4)
5. **F5:** Bash library (wraps F2/F3/F4)
6. **F6:** Mutex consolidation (independent)
7. **F7:** Backward compat (after all features stabilize)

**Why this ordering is better:**

- F4 domain model **constrains** F2 generic state — avoids overlap
- F2 can reference F4 tables (e.g., `state.scope_id` foreign key to `runs.id`)
- F3 can reference F4 tables (e.g., `sentinels.scope_id` foreign key to `runs.id`)
- No rework — each feature builds on stable foundation from prior features

**Alternative (if F4 is removed per Section 3 recommendation):**

1. **F1:** Scaffold
2. **F3:** Sentinels (core infrastructure, no dependencies)
3. **F2:** Ephemeral state (temp file replacement only, no run tracking)
4. **F5:** Bash library
5. **F6:** Mutex consolidation
6. **F7:** Backward compat

This ordering assumes F4 is handled by extending beads, not adding to intercore.

---

## 5. Additional Concerns (P3-P4)

### 5.1 Dual-Write Complexity (P3)

**Finding:** F7 (backward compatibility) introduces dual-write mode that creates permanent technical debt.

**Evidence:** PRD lines 94-99 specify exact legacy paths:
```bash
--legacy-compat writes to:
- /tmp/clavain-dispatch-$$.json
- /tmp/clavain-bead-${SID}.json
- ~/.interband/interphase/bead/${SID}.json
- /tmp/clavain-stop-${SID}
```

**Problem:** This is **write amplification** — every state update hits both intercore DB AND 4+ file paths. If any write fails, state diverges. Atomic dual-write across SQLite + filesystem is impossible without 2PC (two-phase commit), which is overkill for temp files.

**Better migration strategy:**

1. **Read-through phase:** intercore reads from legacy files if DB is empty
2. **Write-only phase:** intercore writes only to DB, legacy consumers read from DB
3. **Delete phase:** Remove legacy file writes after consumers migrate

This is **read-through caching**, not dual-write. Much simpler, no divergence risk.

### 5.2 WAL Mode Configuration (P3)

**Finding:** F1 acceptance criteria (line 23) says "WAL mode enabled by default with configurable busy_timeout (default 5s)."

**Problem:** WAL mode is correct for concurrency, but `busy_timeout` should be **per-transaction**, not global. Hook scripts should fail fast (100ms timeout) so they don't block Claude Code. Long-running scripts (dispatch.sh) can use longer timeouts (5s).

**Recommendation:**
- Default `busy_timeout` = 100ms (fail-fast for hooks)
- Add `ic --timeout=5000ms state set ...` flag for override
- Document in bash library: `intercore_state_set` uses default, `intercore_state_set_blocking` uses 5s

### 5.3 Mutex Design (P4)

**Finding:** F6 (mutex consolidation) uses `mkdir`-based locks but adds owner metadata files.

**Evidence:** PRD lines 82-87 specify `/tmp/intercore/locks/<category>/<id>/owner` files.

**Problem:** Writing `owner` file is **not atomic** with `mkdir`. This race condition exists:
```
Process A: mkdir /tmp/intercore/locks/foo/bar (succeeds)
Process B: mkdir /tmp/intercore/locks/foo/bar (fails)
Process A: echo $PID > .../owner (delayed)
Process B: reads owner file (doesn't exist yet, or has stale PID)
```

**Recommendation:**
- Keep `mkdir` for lock creation (atomic)
- Encode owner in **directory name** instead of file: `/tmp/intercore/locks/<category>/<id>.<pid>.<timestamp>`
- `ic lock list` parses directory names, no file reads needed
- Cleanup uses `find` + PID checks, no race conditions

### 5.4 Schema Versioning (P3)

**Finding:** F1 line 22 says "schema migrations run automatically on first use and on version bumps."

**Problem:** No migration **rollback** strategy specified. If a schema migration fails halfway (e.g., ALTER TABLE succeeds, CREATE INDEX fails), the DB is in an inconsistent state.

**Recommendation:**
- Use `PRAGMA user_version` to track schema version
- Wrap each migration in `BEGIN IMMEDIATE; ... COMMIT;` transaction
- On migration failure, log error and **exit** (don't continue with half-migrated schema)
- Add `ic migrate --dry-run` for testing migrations before applying

---

## 6. Dependency Direction Violations (P1)

### Finding: Circular Dependency Risk with Interphase

**Evidence from module relationships** (AGENTS.md):
```
clavain (hub)
├── interphase  (phase tracking, gates, work discovery)
```

**If intercore is a plugin:**
```
clavain → interphase (companion)
clavain → intercore (for temp file state)
interphase → intercore (for phase state, per PRD line 96)
```

This creates:
```
clavain → interphase → intercore
   └────────┬──────────┘
            circular
```

**Problem:** Circular plugin dependencies prevent cold starts. If intercore needs interphase for phase gate logic, and interphase needs intercore for state storage, which initializes first?

**Recommendation:**
- Move intercore to `infra/` (per Section 1) — breaks cycle by removing from plugin graph
- OR: interphase embeds its own state storage, doesn't depend on intercore
- OR: intercore has no phase logic, only generic state — interphase owns all phase domain logic

---

## 7. Simplicity Violations (P2)

### Finding: Premature Abstraction in State Scopes

**Evidence:** F2 acceptance criteria (line 31) introduces `scope_type` and `scope_id`:
```bash
ic state set <key> <scope_id> '<json>'  # scope_type inferred or specified
```

**Problem:** No concrete use case in the PRD requires `scope_type` polymorphism. All examples use **session ID** as scope:
- Dispatch state: `scope_id = $SESSION_ID`
- Bead phase: `scope_id = $BEAD_ID`
- Sentinel checks: `scope_id = $SESSION_ID`

**YAGNI violation:** `scope_type` is speculative future-proofing. It adds:
- Extra column in `state` table (storage cost)
- Extra CLI parameter (UX complexity)
- Extra validation logic (code complexity)

**When to add abstractions:**
- **After** two real use cases need different scope types
- **Not before** as a "what if we need X later" hedge

**Recommendation:**
- Remove `scope_type` from F2
- Use `scope_id` as opaque string (could be session, bead, agent, anything)
- Add `scope_type` in a future feature **if and when** polymorphic queries are needed (e.g., "list all state for scope_type=session")

### Finding: Excessive CLI Surface in F4

**Evidence:** F4 introduces 8 new commands (lines 56-63):
```
ic run create, run phase, run status, run list, run current
ic agent add, agent update
ic artifact add
```

**Problem:** This is **CRUD boilerplate**. Most of these commands will be used once (run create) or never (artifact add). The CLI surface should reflect **actual user workflows**, not database schema 1:1.

**Better design (workflow-driven):**
```bash
ic run start --goal="..." --project=/path       # Creates run, sets phase=brainstorm
ic run next                                      # Advances phase, records gate
ic run agent vet --pid=$$                        # Registers agent for current run
ic run done /path/to/artifact.md                 # Adds artifact, maybe advances phase
```

**Difference:**
- PRD commands are **data-centric** (run create, agent add)
- Workflow commands are **action-centric** (run start, run next)

Workflow commands encode domain logic (phase transitions, gate rules). Data commands require callers to know the schema.

---

## Summary of Recommendations

| Finding | Severity | Recommendation | Effort |
|---------|----------|----------------|--------|
| Plugin boundary violation | **P0** | Move to `infra/intercore/`, install to PATH | Medium — PRD rewrite, no code exists yet |
| Mixed schema paradigm | **P1** | Commit to structured domain model OR separate DBs | High — requires design decision |
| Beads overlap | **P2** | Remove F4, extend beads for run tracking | Medium — beads extension design needed |
| Feature ordering | **P2** | Reorder F4 before F2/F3, or remove F4 entirely | Low — PRD rewrite only |
| Dependency cycle risk | **P1** | Break cycle via `infra/` move or ownership clarification | Low — follows from P0 fix |
| Simplicity - scope_type | **P2** | Remove `scope_type` until proven necessary | Low — feature reduction |
| Simplicity - CLI surface | **P2** | Design workflow commands, not schema CRUD | Medium — requires domain modeling |
| Dual-write complexity | **P3** | Use read-through migration, not dual-write | Low — strategy change only |
| WAL timeout config | **P3** | Per-transaction timeout, not global | Low — config design tweak |
| Mutex owner race | **P4** | Encode owner in directory name | Low — implementation detail |
| Schema migration safety | **P3** | Add rollback strategy, dry-run mode | Medium — migration engine design |

---

## Verdict

**Proceed with revisions.**

The core problem (temp file fragmentation, TOCTOU races) is valid and worth solving. However, the proposed solution has **three critical flaws** that must be addressed before implementation:

1. **Wrong abstraction layer** — intercore is foundational infrastructure, not a companion plugin
2. **Unclear relationship to beads** — overlapping responsibilities will cause dual-write burden and migration pain
3. **Premature feature set** — F4 (run tracking) either belongs in beads, or should drive the entire schema design from day one

**Recommended next steps:**

1. **Decide on scope:** Is intercore an ephemeral state layer (temp files only), or a domain model for orchestration (runs/agents/artifacts)? These are two different products.

2. **Clarify beads relationship:** If intercore is ephemeral, beads handles permanent state (dependencies, phases, history). If intercore is the domain model, explain why beads is insufficient and justify dual persistence.

3. **Revise PRD with:**
   - Location: `infra/intercore/` (not `plugins/`)
   - Schema: Structured domain model (Option A from Section 2) OR pure KV (Option B), not both
   - Features: Either F1-F3+F5-F7 (ephemeral state only) OR F1+F4+F5 (domain model only)
   - Migration: Read-through caching (not dual-write)

4. **Prototype F3 (sentinels) first:** This is the highest-value feature (fixes TOCTOU races) and has no dependencies on F2/F4 schema decisions. Ship it, validate with real hooks, then design the rest.

---

## Appendix: Reference Architecture

**If intercore is ephemeral state layer:**

```
┌─────────────────────────────────────────┐
│ Beads (bd)                              │
│ - Issues, dependencies, phases          │
│ - Permanent storage (.beads/*.jsonl)    │
│ - Cross-session queries                 │
└─────────────────────────────────────────┘
                  ▲
                  │ reads permanent state
                  │
┌─────────────────┴───────────────────────┐
│ intercore (ic)                          │
│ - Temp file replacement (TTL)           │
│ - Sentinels (throttle guards)           │
│ - Session-local state                   │
│ - SQLite WAL (intercore.db)             │
└─────────────────────────────────────────┘
                  ▲
                  │ writes ephemeral state
                  │
┌─────────────────┴───────────────────────┐
│ Hooks (bash scripts)                    │
│ - lib-sprint.sh, dispatch.sh            │
│ - session-start.sh, auto-publish.sh     │
└─────────────────────────────────────────┘
```

**If intercore is domain model (NOT RECOMMENDED):**

```
┌─────────────────────────────────────────┐
│ intercore (ic)                          │
│ - Runs, agents, artifacts, phases       │
│ - Sentinels, ephemeral state            │
│ - All orchestration state               │
│ - SQLite WAL (intercore.db)             │
└─────────────────────────────────────────┘
                  ▲
                  │
┌─────────────────┴───────────────────────┐
│ Beads (bd) — DEMOTED TO ISSUE TRACKER   │
│ - Issues, dependencies only             │
│ - No phase tracking (moved to intercore)│
└─────────────────────────────────────────┘
```

This second architecture requires **beads migration** and **dual persistence elimination**. High risk, unclear value.

---

**End of Review**
