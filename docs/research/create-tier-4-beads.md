# Create Tier 4 (Polish) Beads — Autarch/TUI Intercore Integration

**Date:** 2026-02-25
**Parent Epic:** iv-ip4zr
**Tier 1 Dependency:** iv-cl86n (Go wrapper)

## Summary

Created 3 Tier 4 (Polish) feature beads for the Autarch TUI's Intercore integration layer. All are P3 priority, depend on the Go wrapper bead (iv-cl86n), and are children of the parent epic (iv-ip4zr).

## Beads Created

| ID | Title | Type | Priority |
|----|-------|------|----------|
| **iv-79apc** | [autarch/tui] Chat-driven sprint and dispatch commands | feature | P3 |
| **iv-2haqz** | [autarch/tui] Wire Intercore events into signals overlay | feature | P3 |
| **iv-np7ng** | [autarch/tui] Gurgeh-to-Coldwine spec handoff flow | feature | P3 |

## Dependency Graph

```
iv-ip4zr (parent epic)
├── depends on iv-79apc (chat-driven sprint commands)
│   └── depends on iv-cl86n (Go wrapper)
├── depends on iv-2haqz (Intercore events → signals overlay)
│   └── depends on iv-cl86n (Go wrapper)
└── depends on iv-np7ng (Gurgeh-to-Coldwine handoff)
    └── depends on iv-cl86n (Go wrapper)
```

## Bead Descriptions

### iv-79apc — Chat-driven sprint and dispatch commands
Enable slash commands in any chat handler: `/sprint create 'title'`, `/sprint advance`, `/sprint status`, `/dispatch task-id to agent-type`, `/research spec-id`. Routes through existing ChatHandler interface. Provides keyboard-free workflow for power users who prefer typing over menu navigation.

### iv-2haqz — Wire Intercore events into signals overlay
Subscribe to Intercore's event stream (`ic events`) via the Go wrapper and surface events in the signals overlay: sprint phase changes, dispatch completions, gate failures, budget warnings. Real-time notifications without polling. Complements the structured dispatch monitoring in Bigend.

### iv-np7ng — Gurgeh-to-Coldwine spec handoff flow
After PRD generation in Gurgeh, prompt "Generate epics for this spec?" and automatically transition to Coldwine with the spec context pre-loaded. Run epic generation (GenerateEpics), then offer "Create sprint?" to complete the spec-to-sprint pipeline. Eliminates manual tab switching and context re-entry.

## Commands Executed

```bash
# Create beads
bd create --title="[autarch/tui] Chat-driven sprint and dispatch commands" --type=feature --priority=3
bd create --title="[autarch/tui] Wire Intercore events into signals overlay" --type=feature --priority=3
bd create --title="[autarch/tui] Gurgeh-to-Coldwine spec handoff flow" --type=feature --priority=3

# Wire dependencies on Go wrapper
bd dep add iv-79apc iv-cl86n
bd dep add iv-2haqz iv-cl86n
bd dep add iv-np7ng iv-cl86n

# Wire as children of parent epic
bd dep add iv-ip4zr iv-79apc
bd dep add iv-ip4zr iv-2haqz
bd dep add iv-ip4zr iv-np7ng
```
