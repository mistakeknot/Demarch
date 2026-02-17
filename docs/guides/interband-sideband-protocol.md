# Interband Sideband Protocol (v1)

## Purpose

Interband standardizes cross-plugin sideband file contracts so producers and
consumers can evolve safely without ad-hoc `/tmp` parsing.

## Default Root

- `~/.interband`
- Override with `INTERBAND_ROOT`

## Envelope Schema

All messages use this top-level envelope:

```json
{
  "version": "1.0.0",
  "namespace": "interphase",
  "type": "bead_phase",
  "session_id": "abc-123",
  "timestamp": "2026-02-17T12:00:00Z",
  "payload": {}
}
```

Rules:
- `version` MUST start with `1.` for v1 readers.
- `payload` MUST be an object.
- Writers MUST write atomically (temp file + rename).

## Active Channels (initial)

### `interphase/bead/<session_id>.json`

- `namespace`: `interphase`
- `type`: `bead_phase`
- `payload`:
  - `id` (string)
  - `phase` (string)
  - `reason` (string)
  - `ts` (unix seconds, number)

### `clavain/dispatch/<pid>.json`

- `namespace`: `clavain`
- `type`: `dispatch`
- `payload`:
  - `name` (string)
  - `workdir` (string)
  - `started` (unix seconds, number)
  - `activity` (string)
  - `turns` (number)
  - `commands` (number)
  - `messages` (number)

### `interlock/coordination/<project>-<agent>.json`

- `namespace`: `interlock`
- `type`: `coordination_signal`
- `payload`:
  - `layer` (string, currently `coordination`)
  - `icon` (string)
  - `text` (string)
  - `priority` (number)
  - `ts` (RFC3339 UTC timestamp)

## Compatibility Policy

- Readers SHOULD ignore unknown fields.
- Writers MAY add fields in `payload` without breaking v1 readers.
- Breaking envelope changes require a new major version and dual-read migration.

## Current Migration State

- Producers write interband files.
- Legacy `/tmp/clavain-*` files remain for backward compatibility.
- Legacy `/var/run/intermute/signals/*.jsonl` remains the active coordination
  stream consumed by current interline releases.
- Consumers read interband first where available, then fallback to legacy paths.
