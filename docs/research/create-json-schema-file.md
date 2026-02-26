# Analysis: Create routing-overrides.schema.json

## Task

Create the file `os/clavain/config/routing-overrides.schema.json` containing a JSON Schema for Interspect routing overrides, incorporating review feedback to add "propose" to the action enum.

## File Created

**Path:** `/home/mk/projects/Demarch/os/clavain/config/routing-overrides.schema.json`

## Schema Structure

The schema defines the `routing-overrides.json` configuration format used for agent exclusion and override configuration in the flux-drive triage pipeline. It is written by Interspect (`lib-interspect.sh`) and read by flux-drive (`SKILL.md Step 1.2a.0`).

### Top-Level Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `version` | integer (const: 1) | Yes | Schema version. Readers must reject version > 1. |
| `overrides` | array of `override` | Yes | Agent-level routing overrides. |
| `overlays` | array of objects | No | Placeholder for prompt tuning overlays (reserved for iv-6liz). |

### Definitions

**`override`** — Core override entry with required `agent` and `action` fields:
- `agent`: String matching `^fd-[a-z][a-z0-9-]*$` pattern
- `action`: Enum of `["exclude", "propose"]` — the key review feedback incorporation
- `reason`: Human-readable explanation
- `evidence_ids`: Array of Interspect evidence ID strings
- `created`: ISO 8601 date-time
- `created_by`: Origin identifier (e.g., 'interspect', 'manual')
- `confidence`: Number 0-1, snapshot of evidence strength
- `scope`: Optional `$ref` to scope definition
- `canary`: Optional `$ref` to canary_snapshot definition

**`scope`** — Optional restriction for domain/file-pattern scoping:
- `domains`: Array of domain name strings from flux-drive detection
- `file_patterns`: Array of glob patterns for file paths

**`canary_snapshot`** — Canary monitoring state at creation time:
- `status`: Enum of `["active", "passed", "failed", "expired"]`
- `window_uses`: Integer >= 1
- `expires_at`: ISO 8601 date-time

## Review Feedback Incorporated

The key review feedback was adding `"propose"` to the `action` enum. This enables a two-phase workflow:
1. **propose** — Interspect (`/interspect:propose`) marks an agent as a candidate for exclusion without immediately removing it from triage
2. **exclude** — The agent is actively removed from flux-drive triage

This separation ensures human review before exclusions take effect, preventing false positives from automatically degrading the review pipeline.

## Validation

- File parsed successfully as valid JSON via `python3 json.load()`
- Read-back confirmed all 119 lines match the specified schema exactly
- File sits alongside existing schemas in the config directory: `agency-spec.schema.json`, `fleet-registry.schema.json`

## Context in Config Directory

The `os/clavain/config/` directory already contains:
- `agency-spec.schema.json` — Agency specification schema
- `agency-spec.yaml` — Agency specification instance
- `fleet-registry.schema.json` — Fleet registry schema
- `fleet-registry.yaml` — Fleet registry instance
- `routing.yaml` — Routing configuration
- `CLAUDE.md` — Config directory conventions

The new `routing-overrides.schema.json` complements the existing `routing.yaml` by defining the schema for override data that modifies routing behavior at triage time.

## Not Committed

As requested, the file was created but not committed to git.
