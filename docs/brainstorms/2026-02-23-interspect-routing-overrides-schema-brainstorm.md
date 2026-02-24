# Brainstorm: Interspect F1 — routing-overrides.json Schema + Flux-Drive Reader

**Bead:** iv-r6mf
**Date:** 2026-02-23
**Parent:** iv-nkak (Routing overrides Type 2 — CLOSED), iv-sksfx (Interspect Phase 2 epic)

## Context

The routing overrides system already exists in two layers:
1. **Writer side (Clavain):** `lib-interspect.sh` has full CRUD — `_interspect_apply_routing_override()`, `_interspect_revert_routing_override()`, `_interspect_read_routing_overrides()`, all with flock atomicity, canary monitoring, and evidence tracking.
2. **Reader side (flux-drive):** SKILL.md Step 1.2a.0 documents the read protocol — parse JSON, check version, exclude agents, warn on cross-cutting exclusions.

**The gap:** There is no formal JSON Schema defining the `routing-overrides.json` format. The structure is implicitly defined by what `_interspect_apply_override_locked()` writes (via jq) and what SKILL.md Step 1.2a.0 expects to read. This works today but creates three risks:

1. **Schema drift** — writer and reader can diverge silently (no validation contract)
2. **Extensibility** — adding overlay support (iv-6liz) or trust scores (iv-3r6q) requires both sides to agree on shape
3. **Tooling** — no automated validation, no IDE autocomplete, no CI checks

Additionally, today's routing experiment analysis (iv-jocaw) showed the **hypothesis was inverted** — B2 complexity routing _increases_ costs by 20%. The real value isn't in model-switching but in **agent exclusion** (routing overrides). This elevates the importance of getting the schema right: it's the mechanism that actually saves tokens.

## What Already Works

| Component | File | Status |
|-----------|------|--------|
| Writer (apply override) | `os/clavain/hooks/lib-interspect.sh:604` | Working — flock + atomic write + git commit + canary |
| Writer (revert override) | `os/clavain/hooks/lib-interspect.sh:813` | Working — removes entry, git commits, closes canary |
| Reader (flux-drive triage) | `interverse/interflux/skills/flux-drive/SKILL.md:263` | Documented — Step 1.2a.0 protocol |
| Reader helper | `os/clavain/hooks/lib-interspect.sh:510` | Working — `_interspect_read_routing_overrides()` |
| Evidence DB | `.clavain/interspect/interspect.db` | Working — SQLite, evidence + modifications + canary tables |
| Commands | `os/clavain/commands/interspect-*.md` | 6 commands — propose, revert, status, evidence, correction, unblock |
| Config | `os/clavain/config/routing.yaml` | Working — B1 static + B2 shadow + safety floors |

## What's Missing

### 1. Formal JSON Schema (routing-overrides.schema.json)

The current implicit format (from `_interspect_apply_override_locked`):

```json
{
  "version": 1,
  "overrides": [
    {
      "agent": "fd-perception",
      "action": "exclude",
      "reason": "Agent consistently wrong on Go codebases — 5/6 corrections were agent_wrong",
      "evidence_ids": ["ev-abc123", "ev-def456"],
      "created": "2026-02-23T10:30:00Z",
      "created_by": "interspect"
    }
  ]
}
```

**Design question:** What more does the schema need for v1?

### 2. Flux-Drive Actually Reading It

SKILL.md documents the protocol but the actual reading happens in the LLM's head (flux-drive is a skill/prompt, not compiled code). The "reader" in this context means:
- The SKILL.md instructions being precise enough to work
- A test/validation path to verify the file is well-formed
- Error handling for corruption, version mismatch, unknown agents

### 3. Schema Validation Tooling

Currently no CI or hook validates that `routing-overrides.json` conforms to any schema. Corruption would be caught at read time (flux-drive logs a warning and moves file to `.corrupted`), but there's no pre-commit check.

## Design Options

### Option A: Minimal Schema — Formalize What Exists

Write a JSON Schema for the current structure. Don't add new fields. Just document and validate what `_interspect_apply_override_locked()` already writes.

**Pros:** Zero risk. No code changes. Immediate value (validation, autocomplete).
**Cons:** Doesn't add extensibility for overlays (iv-6liz), trust scores (iv-3r6q), or scope limits.

### Option B: Extensible Schema v1 — Add Planned Fields

Formalize current structure PLUS add fields that downstream beads need:

```json
{
  "version": 1,
  "$schema": "./routing-overrides.schema.json",
  "overrides": [
    {
      "agent": "fd-perception",
      "action": "exclude",
      "reason": "...",
      "evidence_ids": ["ev-abc123"],
      "created": "2026-02-23T10:30:00Z",
      "created_by": "interspect",
      "scope": {
        "domains": ["claude-code-plugin"],
        "file_patterns": ["interverse/**"]
      },
      "canary": {
        "status": "active",
        "window_uses": 20,
        "expires_at": "2026-03-09T10:30:00Z"
      },
      "confidence": 0.85
    }
  ],
  "overlays": []
}
```

New fields:
- **`scope`** — limit override to specific domains/paths (not all projects)
- **`canary`** — inline canary status (currently only in SQLite DB)
- **`confidence`** — evidence strength (from Interspect threshold calculation)
- **`overlays`** — placeholder array for prompt tuning (iv-6liz future)

**Pros:** Forward-compatible. Downstream beads can start building against the schema.
**Cons:** Scope and canary fields aren't consumed by anything yet. Over-engineering risk.

### Option C: Schema v1 + Validation Hook

Option B plus a pre-commit hook or `bd doctor` check that validates `routing-overrides.json` against the schema.

**Pros:** Catches corruption before commit. Full confidence in file integrity.
**Cons:** Adds a dependency on a JSON Schema validator (e.g., `ajv-cli` or Python `jsonschema`).

## Recommendation: Option B (Extensible Schema v1)

- The schema is small — adding future-proof fields costs almost nothing
- `scope` is valuable even if not consumed yet (it documents intent)
- `canary` inline status lets flux-drive display monitoring status without DB access
- `overlays: []` is a placeholder that costs zero bytes when empty
- Skip the validation hook for now (Option C) — `_interspect_read_routing_overrides()` already validates JSON structure

## Flux-Drive Reader: What Needs to Change

The reader protocol in SKILL.md Step 1.2a.0 is already documented. What's needed:

1. **Tighten the schema reference** — add `$schema` field so the file is self-documenting
2. **Handle new fields gracefully** — reader should ignore unknown fields (forward-compat)
3. **Scope filtering** — when `scope` is present, only exclude agent for matching domains/paths
4. **Canary display** — show `[canary: active, 12/20 uses]` in triage table for excluded agents
5. **Compact SKILL reference** — update `SKILL-compact.md` to match

## Implementation Scope

### Must-Have (this bead)
- [ ] `routing-overrides.schema.json` — formal JSON Schema in `os/clavain/config/` or `.claude/`
- [ ] Update `_interspect_apply_override_locked()` to write new fields (scope, confidence, canary inline)
- [ ] Update `_interspect_read_routing_overrides()` to validate against schema
- [ ] Update flux-drive `SKILL.md` Step 1.2a.0 to handle scope and canary display
- [ ] Update flux-drive `SKILL-compact.md` to match

### Nice-to-Have (defer to downstream beads)
- [ ] Scope-based filtering (partial excludes) — iv-6liz
- [ ] Trust scoring integration — iv-3r6q
- [ ] Overlay support in schema — separate bead
- [ ] Pre-commit validation hook — iv-8fgu or standalone

## Open Questions

1. **Where does the schema file live?** Options:
   - `os/clavain/config/routing-overrides.schema.json` — Clavain owns the format
   - `.claude/routing-overrides.schema.json` — co-located with the data file
   - Both (schema in Clavain, `$schema` reference in data file)

2. **Should canary status be inlined?** Currently canary lives only in SQLite. Inlining it in JSON means:
   - Pro: flux-drive can display it without DB access
   - Con: canary state is mutable (uses increment) — JSON becomes stale
   - Compromise: inline read-only summary, DB remains source of truth

3. **Backward compatibility:** If we add new required fields, existing `routing-overrides.json` files (if any exist in the wild) will be invalid. Use `additionalProperties: true` + `required` only for existing fields.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Schema too restrictive, breaks existing files | Low | Medium | additionalProperties: true, only require version + overrides |
| Scope filtering adds complexity to flux-drive SKILL.md | Medium | Low | Scope is optional — reader ignores it until iv-6liz ships |
| Inline canary goes stale | Medium | Low | Mark as "snapshot" in schema description, DB is authoritative |
| Schema file location causes import confusion | Low | Low | `$schema` relative reference resolves this |

## Dependencies

```
iv-r6mf (this bead)
  ← iv-8fgu (F2: pattern detection + propose flow — needs schema to propose against)
  ← iv-6liz (F5: manual routing override support — needs scope in schema)
  ← iv-3r6q (agent trust scoring — needs confidence field in schema)
```

All downstream beads can start once the schema is published and the reader handles it.
