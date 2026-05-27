# Routing Contract — interflux ↔ interspect

Defines the shared schema for `.claude/routing-overrides.json` so that
**interspect** (which writes the file) and **interflux** (which reads it
during agent triage) cannot drift apart silently.

Contract version: **1**

## File location

```
<project root>/.claude/routing-overrides.json
```

Path override: `FLUX_ROUTING_OVERRIDES_PATH` env var (used by both
plugins).

The file is **per-project**, committed to the repo, and treated as a
cross-repo contract artifact.

## File shape

```json
{
  "version": 1,
  "overrides": [
    { /* override entry — see below */ }
  ]
}
```

The top-level `version` field declares which schema variant this file
follows. Both interspect (writer) and interflux (reader) MUST honor it.

## Override entry schema

```json
{
  "agent": "fd-architecture",
  "action": "exclude",
  "reason": "Repeatedly low-quality outputs on Go microservices",
  "evidence_ids": [123, 456, 789],
  "created": "2026-05-27T17:00:00Z",
  "created_by": "interspect:propose",
  "confidence": 0.85,
  "canary": { /* optional, see below */ },
  "scope":  { /* optional, see below */ }
}
```

### Required fields

| Field | Type | Meaning |
|---|---|---|
| `agent` | string | Agent identifier (e.g., `fd-architecture`, `fd-correctness`). Matches the agent name used in interflux's triage. |
| `action` | enum | One of `exclude`, `propose`, `promote`. See semantics below. |
| `reason` | string | Human-readable justification. Free text. |
| `evidence_ids` | int[] | IDs into interspect's evidence DB that support this override |
| `created` | string (ISO 8601 UTC) | When the entry was created |
| `created_by` | string | Source: `interspect:propose`, `interspect:correction`, `human`, etc. |
| `confidence` | float [0,1] | Writer's confidence the override is correct |

### Optional fields

`canary` — monitoring window for an active override:
```json
{
  "canary": {
    "started": "2026-05-20T00:00:00Z",
    "window_uses": 20,
    "window_days": 14,
    "alert_threshold_pct": 20,
    "status": "monitoring"
  }
}
```

`scope` — restrict the override to a subset of inputs:
```json
{
  "scope": {
    "domains": ["web-api", "data-pipeline"],
    "file_patterns": ["src/**/*.go", "cmd/**/*.go"]
  }
}
```

When both `domains` and `file_patterns` are present, semantics are
**AND** (both must match for the override to apply). Patterns containing
`..` or starting with `/` MUST be rejected by readers (path-traversal
prevention).

### Action semantics

| Action | Reader behavior |
|---|---|
| `exclude` | Remove this agent from the triage candidate pool entirely |
| `propose` | Informational only — show in triage notes, do NOT exclude |
| `promote` | Boost this agent's score (writer-defined boost magnitude) |

## Reader contract (interflux)

interflux's `flux-engine` skill MUST, at Step 1.2a.0 (Routing Overrides):

1. Read `.claude/routing-overrides.json` if it exists. If not, treat as
   no-op (no warning).
2. **Check the `version` field.** If absent OR not in the set of
   supported versions, emit a one-line warning to stderr and treat the
   file as empty (fail open):
   ```
   routing-overrides: unsupported schema version <v> (interflux supports: 1). Ignoring.
   ```
3. For each entry, validate it has the required fields. Skip malformed
   entries with a one-line warning. Do NOT block triage on validation
   errors.
4. Apply scope filtering with AND semantics per the schema above.
5. Reject `scope.file_patterns` containing `..` or starting with `/`.
6. For `action == "exclude"`: remove agent from candidate pool.
7. For `action == "propose"`: include agent normally; surface the
   proposal in triage notes.
8. For `action == "promote"`: include agent with boosted score.

## Writer contract (interspect)

interspect's library (`hooks/lib-interspect.sh`) MUST:

1. Always write `version: 1` at the top of new files.
2. Use atomic write (temp file + rename) to avoid partial reads.
3. Hold a file lock (`_interspect_flock_git`) for cross-process safety.
4. Validate the resulting JSON parses before renaming over the live
   file.
5. Deduplicate entries by `agent` (last write wins for that agent's
   metadata).

## Versioning policy

- **v1 (current)**: this document
- **Compatibility**: adding new optional fields to an override entry is
  a non-breaking change (readers must ignore unknown fields). Removing
  fields or changing types is breaking and requires a `version: 2` bump.
- **When a writer wants to ship a breaking change**: increment
  `version`, ship the writer + the reader update together as a paired
  PR. Readers MUST fail closed on unknown versions per the reader
  contract above.

## Implementation references

- Writer: [interspect/hooks/lib-interspect.sh](../../interverse/interspect/hooks/lib-interspect.sh) — search for `routing-overrides.json` (write paths)
- Reader: [interflux/skills/flux-engine/SKILL.md](../../interverse/interflux/skills/flux-engine/SKILL.md) — Step 1.2a.0

## Future evolution (out of scope for v1)

- Migration tooling (`interspect:migrate-overrides --to-version=N`)
- Schema registration in a central plugin contract registry (when
  enough cross-plugin contracts exist to justify it)
- Auto-validation in CI for repos that commit `routing-overrides.json`
