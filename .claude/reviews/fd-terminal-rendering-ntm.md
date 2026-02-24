# Terminal Rendering Patterns: ntm Analysis for Autarch

**Source:** `/home/mk/projects/Demarch/research/ntm/`
**Target:** `/home/mk/projects/Demarch/apps/autarch/`
**Date:** 2026-02-22
**Type:** Flux-drive intermediate findings (research review)

---

## Executive Summary

ntm implements a mature, production-grade TUI rendering system across ~40 files in `internal/tui/`. The architecture separates concerns into five clean layers: theme, styles/tokens, components, layout, and dashboard. Several patterns are directly adoptable by Autarch's Bubble Tea apps (Bigend, Gurgeh, Coldwine, Pollard) with minimal adaptation.

The strongest patterns to adopt: the three-tier icon fallback system, the semantic color palette abstraction, the design token system, the layout tier hysteresis, and the animated gradient/shimmer rendering. The weakest areas to avoid: the dashboard model's monolithic state struct (500+ fields) and the duplicated layout breakpoint definitions.

---

## 1. Theme and Color System

### 1.1 Catppuccin Theme Struct (ADOPT)

**Files:**
- `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` (lines 14-60)
- `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/semantic.go` (lines 8-67)

The `Theme` struct defines all Catppuccin palette colors as typed `lipgloss.Color` fields -- Base, Mantle, Crust, Surface0-2, Text, Subtext, Overlay, plus all 14 accent colors. Pre-built theme instances exist for Mocha, Macchiato, Latte, Nord, and Plain (no-color).

**Key pattern -- Semantic palette bridge:**

```go
type SemanticPalette struct {
    BgPrimary, BgSecondary, BgTertiary lipgloss.Color
    FgPrimary, FgSecondary, FgTertiary lipgloss.Color
    BorderDefault, BorderFocused       lipgloss.Color
    StatusSuccess, StatusWarning, StatusError lipgloss.Color
    AgentClaude, AgentCodex, AgentGemini     lipgloss.Color
    Accent1, Accent2, Accent3, Accent4       lipgloss.Color
    // ... 50+ semantic mappings
}

func (t Theme) Semantic() SemanticPalette { ... }
```

Components never reference raw Catppuccin names -- they go through `theme.Semantic().StatusSuccess` etc. This means swapping the underlying theme (Mocha -> Nord -> Latte) requires zero component changes.

**Why Autarch should adopt:** Autarch apps currently hardcode lipgloss colors. Switching to this pattern makes theme switching trivial and ensures visual consistency across Bigend/Gurgeh/Pollard.

### 1.2 Agent-Specific Colors (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` (lines 51-55)

Each theme defines per-agent colors: Claude (Mauve/purple), Codex (Blue), Gemini (Yellow), User (Green). These are semantically meaningful -- `t.Claude`, `t.Codex` -- not generic color names.

The semantic palette exposes `AgentColor(agentType string) lipgloss.Color` for dynamic lookup (line 165-178 of semantic.go).

### 1.3 NO_COLOR and Dark/Light Auto-Detection (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` (lines 310-400)

Implements the NO_COLOR standard (https://no-color.org/) with NTM-specific override. Auto-detection uses `termenv.HasDarkBackground()` with an important SSH guard:

```go
// Skip OSC queries over SSH - responses may arrive late due to
// network latency, causing escape sequences to leak into TUI text
// input components.
if os.Getenv("SSH_CONNECTION") != "" || os.Getenv("SSH_TTY") != "" {
    return true // Default to dark theme over SSH
}
```

The Plain theme uses empty `lipgloss.Color("")` values (terminal defaults) and adds `Reverse(true)` for selection and `Underline(true)` for warnings/errors -- ensuring accessibility when colors are disabled.

### 1.4 Pre-Built Style Factory (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` (lines 405-570)

`NewStyles(t Theme) Styles` creates a complete set of pre-built lipgloss styles from a theme. The `Styles` struct has categorized fields: App, Header, Title, Divider, Normal, Bold, Dim, Highlight, Success/Warning/Error/Info, Box/BoxTitle, Claude/Codex/Gemini/User, Button/ButtonActive, Input/InputFocused, Help, StatusBar.

This eliminates per-component style creation. Every component calls `theme.DefaultStyles()` once.

### 1.5 Theme Gradient Helper (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` (lines 572-591)

```go
func (t Theme) Gradient(steps int) []lipgloss.Color {
    colors := []lipgloss.Color{t.Blue, t.Sapphire, t.Lavender, t.Mauve, t.Pink}
    // ... repeat colors if more steps needed
}
```

Returns theme-aware gradient stops. All gradient effects pull from the current theme rather than hardcoding hex values.

---

## 2. Design Token System

### 2.1 Spacing, Size, and Typography Tokens (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/tokens.go` (full file, ~400 lines)

A comprehensive design token system organized into named structs:

```go
type Spacing struct { None, XS, SM, MD, LG, XL, XXL int }
type Size struct { XS, SM, MD, LG, XL, XXL int }
type Typography struct { SizeXS..SizeXXL, LineHeightTight..Loose int }
type LayoutTokens struct { MarginPage, PaddingCard, IconWidth, ... int }
type AnimationTokens struct { TickFast, TickNormal, TickSlow, FramesFast.. int }
type Breakpoints struct { XS, SM, MD, LG, XL, Wide, UltraWide int }
```

**Key insight:** Four preset token configurations: `DefaultTokens()`, `Compact()`, `Spacious()`, `UltraWide()`. Selection is automatic based on terminal width via `TokensForWidth(width int)`.

### 2.2 Responsive Breakpoints (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/tokens.go` (lines 175-190)

Default breakpoints: XS=40, SM=60, MD=80, LG=120, XL=160, Wide=200, UltraWide=240. These drive both token selection and layout mode switching.

### 2.3 Adaptive Card Dimensions (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/tokens.go` (lines 370-400)

```go
func AdaptiveCardDimensions(totalWidth, minCardWidth, maxCardWidth, gap int) (cardWidth, cardsPerRow int)
```

Calculates optimal card width and count for grid layouts. Directly applicable to Autarch's dashboard card rendering.

---

## 3. Layout and Resize System

### 3.1 Layout Tiers with Hysteresis (STRONGLY ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/layout/layout.go` (lines 1-110)

Five tiers: Narrow (<120), Split (120-199), Wide (200-239), Ultra (240-319), Mega (>=320). The critical pattern is **hysteresis** to prevent flickering on resize:

```go
const HysteresisMargin = 5

func TierForWidthWithHysteresis(width int, prevTier Tier) Tier {
    newTier := TierForWidth(width)
    if newTier == prevTier { return newTier }
    // Stay in current tier if within margin of boundary
    switch prevTier {
    case TierSplit:
        if width >= SplitViewThreshold-HysteresisMargin &&
           width < WideViewThreshold+HysteresisMargin {
            return TierSplit
        }
    // ... similar for each tier
    }
    return newTier
}
```

Without hysteresis, dragging a terminal window across a breakpoint causes rapid tier toggling. This is a subtle but important UX detail Autarch should adopt.

### 3.2 Proportional Panel Splitting (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/layout/layout.go` (lines 300-360)

Three layout functions for multi-panel splits:

```go
func SplitProportions(total int) (left, right int)         // 40/60 split
func UltraProportions(total int) (left, center, right int) // 25/50/25
func MegaProportions(total int) (p1, p2, p3, p4, p5 int)  // 18/28/20/17/17
```

Each accounts for border/padding budget (subtracts 6-10 cols before dividing). Autarch should use this pattern rather than ad-hoc percentage math.

### 3.3 Dashboard Responsive Layout (ADOPT PATTERN, NOT EXACT VALUES)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/layout.go` (lines 30-160)

The `CalculateLayout` function returns a `LayoutDimensions` struct with calculated widths, column visibility flags, and a hidden-column count for the header:

```go
type LayoutDimensions struct {
    Mode           LayoutMode
    ListWidth, DetailWidth int
    CardWidth, CardsPerRow int
    BodyHeight     int
    ShowStatusCol, ShowContextCol, ShowModelCol bool
    HiddenColCount int
}
```

Progressive column revelation: Status shows at 60+ cols, Context at 100+, Model/Age at 140+, Command at 180+. The `HiddenColCount` lets the header show "(+3 cols)" to hint at content available if the terminal is wider.

### 3.4 Pane Title Truncation (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/layout/layout.go` (lines 260-310)

`TruncatePaneTitle` preserves the agent suffix when truncating long pane names:

```go
// "destructive_command_guard__cc_1" (width 20) -> "destructive...cc_1"
// Not the naive: "destructive_comma..."
```

It finds the `__<agent>_<number>` suffix, reserves space for it, then truncates only the prefix. Also `TruncateMiddle` which preserves both start and end (1/3 start, 2/3 end), useful when the end contains distinguishing info.

---

## 4. Animated Visual Effects

### 4.1 Gradient Text Rendering (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` (lines 95-140)

Per-character color interpolation using RGB lerp:

```go
func GradientText(text string, colors ...string) string {
    // Parse hex colors, calculate position per rune,
    // find segment + local position, lerp between colors,
    // emit ANSI 24-bit color per character
    result.WriteString(fmt.Sprintf("\x1b[38;2;%d;%d;%dm%c\x1b[0m", c.R, c.G, c.B, r))
}
```

Supports multi-stop gradients. Used for banner logos, dividers, borders, and progress bars.

### 4.2 Shimmer Animation (STRONGLY ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` (lines 175-220)

```go
func Shimmer(text string, tick int, colors ...string) string {
    // Same as GradientText but with a time-based offset
    offset := float64(tick%40) / 40.0  // ~10s full cycle at 4 FPS
    pos = (float64(i)/float64(n) + offset)
    pos = pos - float64(int(pos)) // Wrap around
}
```

The shimmer slides the gradient across text over time. Used for: banner logos, selected items, progress bars, section titles, status indicators. The effect is subtle and elegant.

**Reduced motion support:**
```go
func reducedMotionEnabled() bool {
    v := os.Getenv("NTM_REDUCE_MOTION")
    // "1", "true", "yes", "on" -> true
}
```

When enabled, `Shimmer` falls back to static `GradientText`. This is an accessibility pattern Autarch should adopt.

### 4.3 Pulse Effect (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` (lines 230-245)

```go
func Pulse(baseColor string, tick int) lipgloss.Color {
    brightness := 0.7 + 0.3*math.Sin(float64(tick)*0.1)
    // Apply brightness to RGB channels
}
```

A sine-wave brightness oscillation for pulsing status indicators.

### 4.4 Gradient Border Box (ADOPT SELECTIVELY)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` (lines 145-175)

Creates boxes where the border characters themselves have gradient colors. The top/bottom borders use `GradientText` on the `"---"` line, and vertical borders get colored independently. Visually striking but expensive for large boxes.

### 4.5 Animated Status Dots (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` (lines 370-378)

```go
func StatusDot(color lipgloss.Color, animated bool, tick int) string {
    dots := []string{"○", "◔", "◑", "◕", "●", "◕", "◑", "◔"}
    return lipgloss.NewStyle().Foreground(color).Render(dots[tick%len(dots)])
}
```

A pie-chart-style filling animation for status dots. Eight frames cycling from empty circle to full, then back.

---

## 5. Component Library

### 5.1 Three-Tier Icon Fallback (STRONGLY ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/icons/icons.go` (full file, ~350 lines)

Three complete icon sets: `NerdFonts` (rich glyphs), `Unicode` (standard symbols), `ASCII` (pure ASCII). A `WithFallback` method uses reflection to chain them:

```go
func (i IconSet) WithFallback(fallback IconSet) IconSet {
    // For each string field, if empty in i, use fallback value
}

// Usage:
NerdFonts.WithFallback(Unicode).WithFallback(ASCII)
```

Detection is layered: explicit env var (`NTM_ICONS=nerd`), then heuristics (Powerlevel10k config, terminal program detection, Kitty/WezTerm env vars). Default is **ASCII** to avoid width drift issues -- a deliberately conservative choice.

The `IconSet` struct has 50+ named fields covering Navigation, Status, Objects, Actions, Branding, Categories, and Decorations. Components reference `icons.Current().Check` not raw strings.

### 5.2 Box Component with Builder Pattern (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/components/box.go` (full file)

Fluent builder API:

```go
NewBox().
    WithTitle("Panel Title").
    WithContent(content).
    WithSize(60, 0).
    WithBorderColor(t.Blue).
    WithStyle(BoxRounded).
    Render()
```

Five border styles: Rounded, Double, Thick, Normal, Hidden. Title insertion into the border uses `ansi.Cut` for ANSI-aware string slicing (preserves escape sequences). Convenience functions: `SimpleBox`, `InfoBox`, `SuccessBox`, `ErrorBox`, `WarningBox`.

### 5.3 State Rendering Components (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/components/state.go` (full file)

Unified rendering for Empty, Loading, Error, and Retrying states. The `EmptyStateOptions` struct supports contextual icons (Waiting, Empty, External, Success, Unknown), title, description, and suggested action:

```go
RenderEmptyState(EmptyStateOptions{
    Icon:        IconWaiting,
    Title:       "No metrics yet",
    Description: "Data will appear when agents start working",
    Width:       60,
    Centered:    true,
})
```

The `RetryState` function tracks attempt counts: "Attempt 3 of 5".

### 5.4 Scroll State and Indicators (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/components/scroll.go` (full file)

Clean scroll state tracking:

```go
type ScrollState struct {
    FirstVisible, LastVisible, TotalItems int
}
```

Three rendering modes by available width:
- Wide (25+): "Showing 1-5 of 20"
- Medium (15+): "(1-5/20)"
- Narrow: "(5/20)"

Plus directional arrows (up/down/both) styled with theme colors.

### 5.5 Progress Bar with Terminal Capability Fallback (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/components/progress.go` (full file)

Two progress bar types: determinate (`ProgressBar`) and indeterminate (`IndeterminateBar`). Both check terminal capabilities:

```go
if terminal.SupportsTrueColor() {
    if p.Animated {
        filledStr = styles.Shimmer(barText, p.AnimationTick, p.GradientColors...)
    } else {
        filledStr = styles.GradientText(barText, p.GradientColors...)
    }
} else {
    // Fallback to solid primary color
    filledStr = lipgloss.NewStyle().Foreground(theme.Current().Primary).Render(barText)
}
```

ASCII fallback uses `=` and `-` instead of `block` and `shade` characters.

The indeterminate bar implements a bouncing animation:
```go
pos := b.Tick % period
if pos >= b.Width-barWidth {
    pos = period - pos // Bounce back
}
```

### 5.6 Freshness Indicators (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/components/freshness.go`

`RenderFreshnessIndicator` shows "Updated Xs ago" with automatic staleness detection (2x the refresh interval). `RenderStaleBadge` produces a yellow "STALE" badge. Used in panel footers.

### 5.7 Badge System (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/badges.go` (full file, ~600 lines)

A comprehensive badge library with fixed-width support for alignment:

- `AgentBadge(agentType)` - Claude/Codex/Gemini badges with per-agent colors
- `StatusBadge(status)` - Success/Running/Idle/Error/Blocked badges
- `PriorityBadge(priority)` - P0-P4 with color-coded severity
- `RankBadge(rank)` - Gold/Silver/Bronze medal colors
- `ModelBadge(model)` - Parses "claude-3-opus" to show "opus" with Claude colors
- `MiniBar(value, width)` - Compact inline bar graphs for tables
- `TokenVelocityBadge`, `MemoryUsageBadge`, `AlertSeverityBadge`

Width constants keep badges aligned in columns:
```go
const (
    ModelBadgeWidth    = 8
    PriorityBadgeWidth = 3
    StatusBadgeWidth   = 10
)
```

---

## 6. Terminal Capability Detection

### 6.1 Capability Caching (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/terminal/caps.go` (full file)

Detects TrueColor support (COLORTERM, TERM, known terminal programs) and Unicode block character support (locale settings, terminal type). Results are cached in a package-level pointer with `ResetCache()` for testing.

The conservative detection approach is notable: it does not assume truecolor just because 256-color is supported. Only explicit indicators (COLORTERM=truecolor, known terminal names) trigger truecolor mode.

---

## 7. Command Palette

### 7.1 Multi-Phase Palette Model (ADOPT PATTERN)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/palette/model.go` (lines 1-100)

The palette uses a phase state machine: Command -> Target -> Confirm (or XFSearch -> XFResults). Each phase has its own `update*Phase` and `view*Phase` methods.

```go
type Phase int
const (
    PhaseCommand Phase = iota
    PhaseTarget
    PhaseConfirm
    PhaseXFSearch
    PhaseXFResults
)
```

This keeps the main Update/View switch clean. Each phase transition sets up the next phase's focus/blur state.

### 7.2 Session Selector with Animated Selection (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/palette/selector.go` (full file)

The selector uses shimmer on the selected item's pointer and gradient text on the selected session name. Number keys (1-9) provide quick selection. An animated attached-session dot pulses between green and teal.

The help bar at the bottom uses themed key badges:
```go
keyStyle := lipgloss.NewStyle().
    Background(t.Surface0).Foreground(t.Text).Bold(true).Padding(0, 1)
```

---

## 8. Dashboard Architecture

### 8.1 Panel Interface (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/panels/panel.go` (lines 1-100)

Clean panel abstraction:

```go
type Panel interface {
    tea.Model
    SetSize(width, height int)
    Focus()
    Blur()
    Config() PanelConfig
    Keybindings() []Keybinding
}
```

`PanelConfig` includes priority levels (Critical/High/Normal/Low), refresh intervals, min dimensions, and collapsibility. `PanelBase` provides common functionality (focused state, dimensions, last-update tracking).

### 8.2 Sparkline and MiniBar Rendering (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/layout.go` (lines 205-250)

`RenderSparkline` uses Unicode block characters (`" "`, `"▏"`, `"▎"`, `"▍"`, `"▌"`, `"▋"`, `"▊"`, `"▉"`, `"█"`) for smooth sub-character-width progress. Nine levels of granularity within a single character cell.

`RenderContextMiniBar` adds shimmer to high-usage warnings (>=80% shimmer in yellow, >=90% shimmer in red), making critical states visually attention-grabbing without being annoying.

### 8.3 Adaptive Tick Rate (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/dashboard.go` (lines 65-72)

```go
type ActivityState int
const (
    StateActive ActivityState = iota
    StateIdle
)
```

When idle, the tick rate drops to save CPU. When user interacts or output flows, it switches back to active rate. This prevents the dashboard from burning CPU when idle.

---

## 9. Output Formatting

### 9.1 Dual-Format Detection (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/output/format.go` (full file)

Auto-detects output format: explicit --json flag > NTM_OUTPUT_FORMAT env > pipe detection (non-terminal defaults to JSON) > text for interactive. This makes `ntm status | jq .` work automatically.

### 9.2 Step Progress for CLI Operations (ADOPT)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/output/progress.go` (lines 1-150)

```go
steps := NewSteps().SetTotal(5)
steps.Start("Checking config").Done()
steps.Start("Building agent").Fail()
steps.Start("Optional step").Skip()
```

Outputs `[1/5] Checking config... check-mark` with colored status icons and automatic NO_COLOR fallback to `[OK]`/`[FAIL]`/`[SKIP]` text.

---

## 10. Anti-Patterns to Avoid

### 10.1 Monolithic Dashboard Model (AVOID)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/dashboard.go` (lines 300-560)

The `Model` struct has 100+ fields spanning: pane state, agent counts, health data, mail integration, CASS search, ensemble modes, checkpoint status, handoff status, cost tracking, Ollama cache, spawn state, pending rotations, and more. This is a maintenance liability.

**Recommendation for Autarch:** Compose the dashboard from typed sub-models (one per concern), each with their own Init/Update/View. The `Panel` interface in `panels/panel.go` is the right direction -- but the parent `Model` still aggregates raw data fields instead of delegating to panels.

### 10.2 Duplicated Layout Breakpoints (AVOID)

Two different breakpoint systems exist:
- `internal/tui/styles/tokens.go` defines `DefaultBreakpoints` at 40/60/80/120/160/200/240
- `internal/tui/layout/layout.go` defines tier thresholds at 120/200/240/320
- `internal/tui/dashboard/layout.go` defines yet another set at 60/100/140/180

These overlap but don't align perfectly. The comment in `layout/layout.go` acknowledges this: "These thresholds are aligned with the design tokens..." but the dashboard's layout.go uses its own values.

**Recommendation for Autarch:** Single source of truth for breakpoints. Define once in design tokens, reference everywhere.

### 10.3 Raw ANSI Escapes in Gradient Functions (CAUTION)

**File:** `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` (line 130)

```go
result.WriteString(fmt.Sprintf("\x1b[38;2;%d;%d;%dm%c\x1b[0m", c.R, c.G, c.B, r))
```

Gradient/shimmer functions emit raw ANSI instead of using lipgloss styles. This bypasses lipgloss's color profile handling (the automatic 256->16 color downgrade for limited terminals). The `terminal.SupportsTrueColor()` check in `progress.go` is the guard, but gradient text/shimmer functions themselves do not check.

**Recommendation for Autarch:** Wrap gradient output in a truecolor check, or use lipgloss's `ColorProfile` to downgrade gracefully.

### 10.4 Large File (6700+ lines dashboard.go) (AVOID)

The main `dashboard.go` is 6716 lines. Even with good separation of panels, the parent orchestrator file is too large to navigate or maintain. Split Update into per-message-type files, split View into per-section files.

---

## 11. Specific Patterns Worth Copying Verbatim

1. **Icon fallback chain** (`icons/icons.go`): NerdFonts -> Unicode -> ASCII with reflection-based field merging and conservative default (ASCII).

2. **Shimmer function** (`styles/styles.go:175-220`): Time-offset gradient that wraps around. Simple, beautiful, 40-line implementation.

3. **Layout tier hysteresis** (`layout/layout.go:80-110`): 5-column margin prevents flicker. Trivial to implement, significant UX improvement.

4. **Semantic palette** (`theme/semantic.go`): 50+ role-based color names mapped from raw theme colors. The `StatusColor(status string)` and `AgentColor(agentType string)` lookup methods.

5. **Design token presets** (`styles/tokens.go`): Compact/Default/Spacious/UltraWide token sets with `TokensForWidth(width int)` selector.

6. **Panel interface** (`panels/panel.go`): `SetSize(w,h)`, `Focus()`, `Blur()`, `Config()`, `Keybindings()` on top of `tea.Model`. Priority-based layout.

7. **Adaptive card dimensions** (`styles/tokens.go:370-400`): Grid layout calculator that optimally fills available width.

8. **Step progress CLI output** (`output/progress.go`): Clean step-by-step progress with automatic color/no-color fallback.

9. **Scroll indicators** (`components/scroll.go`): Width-adaptive format (wide/medium/narrow) with directional arrows.

10. **SSH theme detection guard** (`theme/theme.go:375-380`): Prevents OSC response race conditions over SSH.

---

## 12. Adoption Priority for Autarch

| Priority | Pattern | Effort | Impact |
|----------|---------|--------|--------|
| P0 | Theme struct + semantic palette | Medium | High -- enables theming across all apps |
| P0 | Icon fallback system | Low | High -- fixes rendering in limited terminals |
| P0 | Layout tier hysteresis | Low | Medium -- prevents resize flicker |
| P1 | Design token system | Medium | High -- consistent spacing/sizing |
| P1 | Shimmer/gradient rendering | Low | Medium -- visual polish |
| P1 | Badge system | Medium | Medium -- consistent status rendering |
| P1 | Panel interface | Medium | High -- composable dashboard architecture |
| P2 | Progress bars with terminal fallback | Low | Low -- nice to have |
| P2 | State rendering (empty/loading/error) | Low | Medium -- consistent UX |
| P2 | CLI step progress output | Low | Low -- nice for spawn/setup commands |
| P3 | Sparkline rendering | Low | Low -- dashboard-specific |
| P3 | Gradient borders | Low | Low -- decorative |

---

## 13. Integration Notes

- ntm uses `github.com/charmbracelet/lipgloss`, `github.com/charmbracelet/bubbletea`, `github.com/charmbracelet/glamour`, and `github.com/muesli/termenv` -- the same stack as Autarch.
- The theme/styles/icons packages have no external dependencies beyond lipgloss and could be extracted into a shared `pkg/tui` package in Demarch.
- ntm's `terminal/caps.go` and `icons/icons.go` are self-contained and could be copied directly.
- The shimmer/gradient code (~200 lines in `styles/styles.go`) is pure math + ANSI output -- trivially portable.
