# PRD: Interspect Routing Overrides Schema + Flux-Drive Reader

**Bead:** iv-r6mf

## Problem

The routing-overrides.json format is defined implicitly by what `_interspect_apply_override_locked()` writes and what flux-drive SKILL.md Step 1.2a.0 reads. No formal schema exists, so writer and reader can drift silently, downstream beads (iv-8fgu, iv-6liz, iv-3r6q) have no contract to build against, and there's no automated validation.

## Solution

Define a formal JSON Schema for routing-overrides.json (v1) with extensible fields for downstream features. Update the writer to populate new fields, add schema-aware validation to the reader, and update flux-drive's SKILL.md to display scope and canary information during triage.

## Features

### F1: JSON Schema Definition
**What:** Create `routing-overrides.schema.json` defining the v1 format with current fields plus extensibility hooks (scope, canary snapshot, confidence, overlays placeholder).
**Acceptance criteria:**
- [ ] Schema file exists at `os/clavain/config/routing-overrides.schema.json`
- [ ] Schema validates the current implicit format (version, overrides array with agent/action/reason/evidence_ids/created/created_by)
- [ ] Schema includes optional fields: `scope` (domains + file_patterns), `canary` (status + window_uses + expires_at), `confidence` (number 0-1)
- [ ] Schema includes optional `overlays` array (empty placeholder for iv-6liz)
- [ ] `additionalProperties: true` at root and override level for forward-compat
- [ ] Only `version` and `overrides` are required at root; only `agent` and `action` required per override

### F2: Writer Update
**What:** Update `_interspect_apply_override_locked()` in lib-interspect.sh to write `confidence` and `canary` snapshot fields when applying overrides.
**Acceptance criteria:**
- [ ] `confidence` field written as float (0.0-1.0) computed from evidence strength (agent_wrong_pct / 100)
- [ ] `canary` object written with `status`, `window_uses`, `expires_at` fields matching the new canary record
- [ ] Existing fields (agent, action, reason, evidence_ids, created, created_by) unchanged
- [ ] `scope` field NOT written by default (writer doesn't know domain context — deferred to iv-6liz)
- [ ] Backward-compatible: files written by old code still pass validation

### F3: Reader Validation
**What:** Update `_interspect_read_routing_overrides()` to validate JSON structure against schema expectations (lightweight — not full jsonschema, just jq checks).
**Acceptance criteria:**
- [ ] Reader checks `version` field exists and is ≤ 1
- [ ] Reader checks `overrides` is an array
- [ ] Reader checks each override has `agent` (string) and `action` (string)
- [ ] Unknown fields are ignored (forward-compat)
- [ ] Malformed JSON handling unchanged (already returns empty structure + warning)
- [ ] Validation errors logged to stderr, never block flux-drive dispatch

### F4: Flux-Drive SKILL.md Update
**What:** Update Step 1.2a.0 in both SKILL.md and SKILL-compact.md to handle scope filtering and canary display.
**Acceptance criteria:**
- [ ] SKILL.md Step 1.2a.0 updated to describe scope-aware exclusion (when `scope` present, only exclude for matching domains/paths; when absent, exclude globally)
- [ ] SKILL.md Step 1.2a.0 updated to display canary status in triage table: `[canary: <status>, <uses_remaining>/<window_uses>]`
- [ ] SKILL-compact.md updated to match the new protocol
- [ ] Existing behavior unchanged when scope/canary fields are absent

## Non-goals

- **Scope-based filtering logic** — schema defines the field; actual filtering is iv-6liz
- **Overlay implementation** — schema includes placeholder array; content format is a separate bead
- **Trust scoring** — schema includes confidence field; scoring algorithm is iv-3r6q
- **Pre-commit validation hook** — deferred; reader-side validation is sufficient for v1
- **B2 complexity routing changes** — iv-jocaw proved B1+floors is optimal; no changes here

## Dependencies

- `lib-interspect.sh` (Clavain) — writer lives here, must be edited
- `flux-drive/SKILL.md` (interflux) — reader protocol lives here, must be edited
- `flux-drive/SKILL-compact.md` (interflux) — compact reference, must stay in sync
- No external library dependencies (schema is reference documentation, validation is jq-based)

## Open Questions

1. ~~Where does the schema file live?~~ **Resolved: `os/clavain/config/`** — Clavain owns the write contract, so the schema lives with the writer. `$schema` field in data files provides a relative reference.
2. **Canary staleness:** Inline canary snapshot goes stale as uses accumulate. Mitigated by marking it as a "snapshot at creation time" in schema description. DB remains source of truth for live canary state.
