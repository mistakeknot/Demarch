# Design Token System for Autarch TUI

**Bead:** iv-0jfz
**Date:** 2026-02-23
**Complexity:** 2/5 (simple — port from NTM reference)
**Reference:** `research/ntm/internal/tui/styles/tokens.go`

## Overview

Port the design token system from NTM into Autarch's `pkg/tui/` package. Design tokens provide named constants for spacing, sizing, typography, layout, animation, and breakpoints — replacing magic numbers with semantic values. Four presets (Compact, Default, Spacious, UltraWide) auto-select based on terminal width via `TokensForWidth()`.

## Architecture

The token system layers cleanly on top of the existing infrastructure:

```
Tier 1: theme.Theme        (raw palette colors) — SHIPPED (iv-2d5g)
Tier 2: theme.SemanticPalette (role-based colors) — SHIPPED (iv-2d5g)
Tier 3: tui.DesignTokens   (spacing/layout/sizing) — THIS PR
Tier 4: tui.Tiers           (width bucketing)      — SHIPPED (iv-jse3)
```

Tokens live in `pkg/tui/tokens.go` alongside the existing `tiers.go`, `colors.go`, and `styles.go`. They are independent of theme colors — tokens handle spatial dimensions, themes handle colors.

## Tasks

### Task 1: Create `pkg/tui/tokens.go` — Token Types and Presets

Port from NTM `tokens.go` lines 1-445, adapting for Autarch:

**Types to port:**
- `Spacing` struct (None/XS/SM/MD/LG/XL/XXL)
- `Size` struct (XS/SM/MD/LG/XL/XXL)
- `Typography` struct (SizeXS-XXL + LineHeight variants)
- `LayoutTokens` struct (margins, padding, component/list/table/modal/dashboard dims)
- `AnimationTokens` struct (tick intervals + frame counts)
- `Breakpoints` struct (XS/SM/MD/LG/XL/Wide/UltraWide)
- `DesignTokens` aggregate struct

**Functions to port:**
- `DefaultTokens()` — returns the standard preset
- `Compact()` — space-constrained preset
- `Spacious()` — roomy preset
- `UltraWide()` — optimized for 200+ col displays
- `TokensForWidth(width int) DesignTokens` — auto-selects preset by terminal width
- `LayoutMode` enum + `GetLayoutMode(width int) LayoutMode`
- `AdaptiveCardDimensions(totalWidth, minCardWidth, maxCardWidth, gap int) (cardWidth, cardsPerRow int)`

**Adaptations from NTM:**
- Remove `BorderRadius` and `ZIndex` types (irrelevant for terminal — NTM has them for conceptual completeness but they're never used)
- Change package from `styles` to `tui` (matches Autarch conventions)
- Remove NTM's `theme` import — Autarch tokens are color-independent
- Align `TokensForWidth` breakpoints with existing `tiers.go` thresholds where possible

**Do NOT port:** Style builder functions (lines 508-692) — NTM's style builders reference NTM's `theme.Current()`. Autarch already has its own style builders in `styles.go` and `theme/semantic.go`. These will be migrated to use tokens in a separate bead.

### Task 2: Create `pkg/tui/tokens_test.go` — Tests

Test coverage:
- `TestDefaultTokens` — verify all defaults are non-zero where expected
- `TestCompact` — verify compact values are <= default values for spacing/size
- `TestSpacious` — verify spacious values are >= default values
- `TestUltraWide` — verify ultra-wide values are >= spacious values
- `TestTokensForWidth` — verify breakpoint routing:
  - width < 40 → Compact
  - width 60 → Default
  - width 150 → Spacious
  - width 250 → UltraWide
- `TestGetLayoutMode` — verify mode enum matches `TokensForWidth`
- `TestAdaptiveCardDimensions` — verify grid calculations:
  - Normal case: 120 width, 25 min, 40 max, 2 gap → reasonable card count
  - Edge case: width < minCardWidth → returns (width, 1)
  - Edge case: zero/negative inputs → returns (1, 1)
  - Max clamping: cardWidth doesn't exceed maxCardWidth

### Task 3: Wire `TokensForWidth` into existing tier system

In `tiers.go`, add a convenience bridge:

```go
// TokensForTier returns design tokens appropriate for the given tier.
func TokensForTier(t Tier) DesignTokens {
    switch t {
    case TierNarrow:
        return Compact()
    case TierSplit:
        return DefaultTokens()
    case TierWide:
        return Spacious()
    case TierUltra, TierMega:
        return UltraWide()
    default:
        return DefaultTokens()
    }
}
```

This allows existing code that already tracks `Tier` to get tokens without re-evaluating width.

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `apps/autarch/pkg/tui/tokens.go` | Create | ~310 |
| `apps/autarch/pkg/tui/tokens_test.go` | Create | ~150 |
| `apps/autarch/pkg/tui/tiers.go` | Edit (add bridge) | +15 |

## Out of Scope

- **Migrating existing magic numbers** — `styles.go` has ~39 hardcoded padding values. These will be migrated to use tokens in a follow-up bead, not this one. This PR only establishes the token definitions.
- **Style builder functions** — NTM's `PanelStyle()`, `HeaderStyle()` etc. are NTM-specific. Autarch has its own style system. Migration is a separate concern.
- **Runtime token switching** — No dynamic preset changes mid-session. Token preset is selected once at startup (or on resize via existing tier system).

## Verification

```bash
cd apps/autarch && go test -race ./pkg/tui/ -run Token
cd apps/autarch && go test -race ./pkg/tui/ -run AdaptiveCard
cd apps/autarch && go build ./cmd/autarch/
```
