# Bigend Section-Level Dirty Row Tracking — Implementation Plan
**Phase:** executing (as of 2026-02-23T16:21:32Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Skip 90%+ of dashboard re-rendering on stable frames by caching each section's lipgloss output and only re-rendering when its source data changes.

**Architecture:** Add a `sectionCache` map to `Model` keyed by `sectionID` (6 dashboard sections). Each entry stores the rendered string and an FNV-64 hash of the source data. On `View()` → `renderDashboard()`, each section checks its hash before rendering. Cache is invalidated on resize. Map keys are sorted before hashing to ensure deterministic output.

**Tech Stack:** Go stdlib (`hash/fnv`, `encoding/binary`, `sort`), Bubble Tea, lipgloss. No new dependencies.

---

### Task 1: Section cache types and hash helpers

**Files:**
- Create: `apps/autarch/internal/bigend/tui/section_cache.go`
- Test: `apps/autarch/internal/bigend/tui/section_cache_test.go`

**Step 1: Write the failing test**

Create `section_cache_test.go` with tests for hash stability and sensitivity:

```go
package tui

import (
	"testing"
	"time"

	"github.com/mistakeknot/autarch/internal/bigend/aggregator"
	"github.com/mistakeknot/autarch/internal/icdata"
)

func TestSectionHashStability(t *testing.T) {
	// Same input must produce the same hash.
	state := aggregator.State{
		Sessions: []aggregator.TmuxSession{
			{Name: "a", UnifiedState: icdata.StatusActive},
			{Name: "b", UnifiedState: icdata.StatusWaiting},
		},
		Agents: []aggregator.Agent{
			{Name: "agent-1", Program: "claude"},
		},
	}
	h1 := hashSessions(state.Sessions, 5)
	h2 := hashSessions(state.Sessions, 5)
	if h1 != h2 {
		t.Errorf("same input produced different hashes: %d vs %d", h1, h2)
	}

	h3 := hashAgents(state.Agents, 5)
	h4 := hashAgents(state.Agents, 5)
	if h3 != h4 {
		t.Errorf("same agent input produced different hashes: %d vs %d", h3, h4)
	}
}

func TestSectionHashSensitivity(t *testing.T) {
	// Different input must produce different hashes.
	s1 := []aggregator.TmuxSession{{Name: "a", UnifiedState: icdata.StatusActive}}
	s2 := []aggregator.TmuxSession{{Name: "b", UnifiedState: icdata.StatusActive}}
	s3 := []aggregator.TmuxSession{{Name: "a", UnifiedState: icdata.StatusWaiting}}

	h1 := hashSessions(s1, 5)
	h2 := hashSessions(s2, 5)
	h3 := hashSessions(s3, 5)

	if h1 == h2 {
		t.Error("different session names produced same hash")
	}
	if h1 == h3 {
		t.Error("different session statuses produced same hash")
	}
}

func TestSectionHashWidthSensitivity(t *testing.T) {
	// Width changes must produce different stats hashes.
	state := aggregator.State{
		Sessions: []aggregator.TmuxSession{{Name: "a"}},
	}
	h1 := hashStats(state, 80)
	h2 := hashStats(state, 120)
	if h1 == h2 {
		t.Error("different widths produced same stats hash")
	}
}

func TestSectionCacheHitAndMiss(t *testing.T) {
	cache := newSectionCache()
	calls := 0
	renderFn := func() string {
		calls++
		return "rendered"
	}

	// First call: miss
	result := cache.getOrRender(sectionStats, 42, renderFn)
	if result != "rendered" || calls != 1 {
		t.Errorf("expected miss: result=%q calls=%d", result, calls)
	}

	// Second call same hash: hit
	result = cache.getOrRender(sectionStats, 42, renderFn)
	if result != "rendered" || calls != 1 {
		t.Errorf("expected hit: result=%q calls=%d", result, calls)
	}

	// Third call different hash: miss
	result = cache.getOrRender(sectionStats, 99, renderFn)
	if result != "rendered" || calls != 2 {
		t.Errorf("expected miss on new hash: result=%q calls=%d", result, calls)
	}
}

func TestSectionCacheInvalidate(t *testing.T) {
	cache := newSectionCache()
	calls := 0
	renderFn := func() string {
		calls++
		return "v" + string(rune('0'+calls))
	}

	cache.getOrRender(sectionStats, 42, renderFn)
	if calls != 1 {
		t.Fatal("expected 1 render call")
	}

	cache.invalidateAll()

	result := cache.getOrRender(sectionStats, 42, renderFn)
	if calls != 2 {
		t.Errorf("expected re-render after invalidate, calls=%d", calls)
	}
	if result != "v2" {
		t.Errorf("expected fresh render, got %q", result)
	}
}

func TestHashActivities(t *testing.T) {
	now := time.Now()
	a1 := []aggregator.Activity{{Time: now, Summary: "deployed", Source: "kernel"}}
	a2 := []aggregator.Activity{{Time: now, Summary: "deployed", Source: "tmux"}}
	h1 := hashActivities(a1, 10)
	h2 := hashActivities(a2, 10)
	if h1 == h2 {
		t.Error("different activity sources produced same hash")
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -run TestSection -v`
Expected: FAIL — `hashSessions`, `hashAgents`, `hashStats`, `hashActivities`, `newSectionCache`, `sectionStats` undefined.

**Step 3: Write the implementation**

Create `section_cache.go`:

```go
package tui

import (
	"encoding/binary"
	"hash/fnv"
	"sort"

	"github.com/mistakeknot/autarch/internal/bigend/aggregator"
	"github.com/mistakeknot/autarch/internal/icdata"
)

// sectionID identifies a cacheable dashboard section.
type sectionID int

const (
	sectionStats sectionID = iota
	sectionRuns
	sectionDispatches
	sectionSessions
	sectionAgents
	sectionActivity
)

// sectionEntry holds a cached render result and its data hash.
type sectionEntry struct {
	rendered string
	hash     uint64
}

// sectionCache stores per-section render results keyed by sectionID.
type sectionCache struct {
	entries map[sectionID]sectionEntry
}

func newSectionCache() *sectionCache {
	return &sectionCache{entries: make(map[sectionID]sectionEntry, 6)}
}

// getOrRender returns cached output if hash matches, otherwise calls renderFn.
func (c *sectionCache) getOrRender(id sectionID, hash uint64, renderFn func() string) string {
	if entry, ok := c.entries[id]; ok && entry.hash == hash {
		return entry.rendered
	}
	s := renderFn()
	c.entries[id] = sectionEntry{rendered: s, hash: hash}
	return s
}

// invalidateAll clears the entire cache (used on resize, tab switch).
func (c *sectionCache) invalidateAll() {
	for k := range c.entries {
		delete(c.entries, k)
	}
}

// --- Per-section hash functions ---
// Each hashes the fields that the corresponding renderDashboard section reads.
// Width is included in stats hash since lipgloss layout depends on terminal width.

func hashStats(state aggregator.State, width int) uint64 {
	h := fnv.New64a()
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, uint64(width))
	h.Write(b)
	binary.LittleEndian.PutUint64(b, uint64(len(state.Projects)))
	h.Write(b)
	binary.LittleEndian.PutUint64(b, uint64(len(state.Sessions)))
	h.Write(b)
	binary.LittleEndian.PutUint64(b, uint64(len(state.Agents)))
	h.Write(b)
	// Count active sessions for non-kernel mode.
	var activeCount int
	for _, s := range state.Sessions {
		if s.UnifiedState == icdata.StatusActive || s.UnifiedState == icdata.StatusWaiting {
			activeCount++
		}
	}
	binary.LittleEndian.PutUint64(b, uint64(activeCount))
	h.Write(b)
	if state.Kernel != nil {
		km := state.Kernel.Metrics
		binary.LittleEndian.PutUint64(b, uint64(km.ActiveRuns))
		h.Write(b)
		binary.LittleEndian.PutUint64(b, uint64(km.ActiveDispatches))
		h.Write(b)
		binary.LittleEndian.PutUint64(b, uint64(km.BlockedAgents))
		h.Write(b)
		binary.LittleEndian.PutUint64(b, uint64(km.TotalTokensIn))
		h.Write(b)
		binary.LittleEndian.PutUint64(b, uint64(km.TotalTokensOut))
		h.Write(b)
		binary.LittleEndian.PutUint64(b, uint64(len(km.KernelErrors)))
		h.Write(b)
		// Hash has-intercore counts
		kernelCount := 0
		for _, p := range state.Projects {
			if p.HasIntercore {
				kernelCount++
			}
		}
		binary.LittleEndian.PutUint64(b, uint64(kernelCount))
		h.Write(b)
	}
	return h.Sum64()
}

func hashRuns(kernel *aggregator.KernelState, width int) uint64 {
	h := fnv.New64a()
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, uint64(width))
	h.Write(b)
	if kernel == nil {
		return h.Sum64()
	}
	// Sort map keys for deterministic hashing (Go map iteration is random).
	projects := make([]string, 0, len(kernel.Runs))
	for proj := range kernel.Runs {
		projects = append(projects, proj)
	}
	sort.Strings(projects)
	for _, proj := range projects {
		h.Write([]byte(proj))
		for _, r := range kernel.Runs[proj] {
			h.Write([]byte(r.ID))
			h.Write([]byte(r.Status))
			h.Write([]byte(r.Phase))
			h.Write([]byte(r.Goal))
		}
	}
	return h.Sum64()
}

func hashDispatches(kernel *aggregator.KernelState, width int) uint64 {
	h := fnv.New64a()
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, uint64(width))
	h.Write(b)
	if kernel == nil {
		return h.Sum64()
	}
	// Sort map keys for deterministic hashing (Go map iteration is random).
	projects := make([]string, 0, len(kernel.Dispatches))
	for proj := range kernel.Dispatches {
		projects = append(projects, proj)
	}
	sort.Strings(projects)
	for _, proj := range projects {
		h.Write([]byte(proj))
		for _, d := range kernel.Dispatches[proj] {
			h.Write([]byte(d.ID))
			h.Write([]byte(d.Status))
			h.Write([]byte(d.AgentType))
			binary.LittleEndian.PutUint64(b, uint64(d.InTokens))
			h.Write(b)
			binary.LittleEndian.PutUint64(b, uint64(d.OutTokens))
			h.Write(b)
		}
	}
	return h.Sum64()
}

func hashSessions(sessions []aggregator.TmuxSession, limit int) uint64 {
	h := fnv.New64a()
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, uint64(len(sessions)))
	h.Write(b)
	for i, s := range sessions {
		if i >= limit {
			break
		}
		h.Write([]byte(s.Name))
		h.Write([]byte(s.AgentName))
		h.Write([]byte(s.ProjectPath))
		binary.LittleEndian.PutUint64(b, uint64(s.UnifiedState))
		h.Write(b)
	}
	return h.Sum64()
}

func hashAgents(agents []aggregator.Agent, limit int) uint64 {
	h := fnv.New64a()
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, uint64(len(agents)))
	h.Write(b)
	for i, a := range agents {
		if i >= limit {
			break
		}
		h.Write([]byte(a.Name))
		h.Write([]byte(a.Program))
		h.Write([]byte(a.ProjectPath))
	}
	return h.Sum64()
}

func hashActivities(activities []aggregator.Activity, limit int) uint64 {
	h := fnv.New64a()
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, uint64(len(activities)))
	h.Write(b)
	for i, a := range activities {
		if i >= limit {
			break
		}
		h.Write([]byte(a.Summary))
		h.Write([]byte(a.Source))
		h.Write([]byte(a.AgentName))
		ts := a.Time.UnixNano()
		binary.LittleEndian.PutUint64(b, uint64(ts))
		h.Write(b)
	}
	return h.Sum64()
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -run TestSection -v`
Expected: All PASS.

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -run TestHash -v`
Expected: All PASS.

**Step 5: Commit**

```bash
git add apps/autarch/internal/bigend/tui/section_cache.go apps/autarch/internal/bigend/tui/section_cache_test.go
git commit -m "feat(bigend): add section cache types and FNV hash helpers for dirty tracking"
```

---

### Task 2: Integrate section cache into Model

**Files:**
- Modify: `apps/autarch/internal/bigend/tui/model.go` (Model struct, New(), applyResize())

**Step 1: Add `dashCache` field to Model struct**

In `model.go`, add to the `Model` struct (after `resizeCoalescer`):

```go
	dashCache       *sectionCache
```

**Step 2: Initialize cache in New()**

In the `New()` function, add to the returned struct literal:

```go
		dashCache:       newSectionCache(),
```

**Step 3: Run existing tests to verify no breakage**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -v -count=1`
Expected: All existing tests PASS.

**Step 4: Commit**

```bash
git add apps/autarch/internal/bigend/tui/model.go
git commit -m "feat(bigend): add dashCache field to Model"
```

---

### Task 3: Wire section cache into renderDashboard

**Files:**
- Modify: `apps/autarch/internal/bigend/tui/render_dashboard.go`
- Test: `apps/autarch/internal/bigend/tui/section_cache_test.go` (add integration test)

**Step 1: Write the integration test**

Append to `section_cache_test.go`:

```go
func TestDashboardCacheSkipsReRender(t *testing.T) {
	// Two consecutive renderDashboard calls with identical state
	// should produce identical output (basic sanity).
	agg := &fakeAggStatus{state: aggregator.State{
		Sessions: []aggregator.TmuxSession{
			{Name: "s1", UnifiedState: icdata.StatusActive, ProjectPath: "/proj"},
		},
		Agents: []aggregator.Agent{
			{Name: "a1", Program: "claude", ProjectPath: "/proj"},
		},
	}}
	m := New(agg, "test")
	m.width = 120
	m.height = 40

	out1 := m.renderDashboard()
	out2 := m.renderDashboard()
	if out1 != out2 {
		t.Error("identical state produced different dashboard output")
	}
}
```

**Step 2: Run test to verify it passes (it should pass now since output is deterministic)**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -run TestDashboardCache -v`
Expected: PASS (this is a sanity test; the real value is confirming cache doesn't break output).

**Step 3: Refactor renderDashboard to use section cache**

Replace `renderDashboard()` in `render_dashboard.go` with cached versions. The key change: each section block is wrapped with `m.dashCache.getOrRender()`:

```go
func (m Model) renderDashboard() string {
	state := m.agg.GetState()
	width := m.width

	// Stats row (cached)
	statsRow := m.dashCache.getOrRender(sectionStats, hashStats(state, width), func() string {
		return m.renderStatsRow(state, width)
	})

	sections := []string{statsRow, ""}

	// Active Runs (cached)
	if state.Kernel != nil {
		runsSection := m.dashCache.getOrRender(sectionRuns, hashRuns(state.Kernel, width), func() string {
			return m.renderRunsSection(state.Kernel)
		})
		if runsSection != "" {
			sections = append(sections, runsSection, "")
		}
	}

	// Dispatches (cached)
	if state.Kernel != nil {
		dispSection := m.dashCache.getOrRender(sectionDispatches, hashDispatches(state.Kernel, width), func() string {
			return m.renderDispatchesSection(state.Kernel)
		})
		if dispSection != "" {
			sections = append(sections, dispSection, "")
		}
	}

	// Recent Sessions (cached)
	sessSection := m.dashCache.getOrRender(sectionSessions, hashSessions(state.Sessions, 5), func() string {
		return m.renderRecentSessions(state.Sessions)
	})
	sections = append(sections, sessSection, "")

	// Registered Agents (cached)
	agentsSection := m.dashCache.getOrRender(sectionAgents, hashAgents(state.Agents, 5), func() string {
		return m.renderRecentAgents(state.Agents)
	})
	sections = append(sections, agentsSection, "")

	// Activity Feed (cached)
	if len(state.Activities) > 0 {
		actSection := m.dashCache.getOrRender(sectionActivity, hashActivities(state.Activities, 10), func() string {
			return m.renderActivityFeed(state.Activities)
		})
		sections = append(sections, actSection)
	}

	return lipgloss.JoinVertical(lipgloss.Left, sections...)
}
```

**Step 4: Extract render sub-functions**

Add each extracted sub-function to `render_dashboard.go`. These are pure extractions of existing code — no logic changes:

```go
func (m Model) renderStatsRow(state aggregator.State, width int) string {
	statsStyle := PanelStyle.Copy().Width(width/5 - 2)

	projectCount := len(state.Projects)
	projectLabel := "Projects"
	if state.Kernel != nil && len(state.Kernel.Metrics.KernelErrors) > 0 {
		kernelCount := 0
		for _, p := range state.Projects {
			if p.HasIntercore {
				kernelCount++
			}
		}
		okCount := kernelCount - len(state.Kernel.Metrics.KernelErrors)
		projectLabel = fmt.Sprintf("Projects (%d/%d)", okCount, kernelCount)
	}
	projectStats := statsStyle.Render(
		TitleStyle.Render(fmt.Sprintf("%d", projectCount)) + "\n" +
			LabelStyle.Render(projectLabel),
	)
	sessionStats := statsStyle.Render(
		TitleStyle.Render(fmt.Sprintf("%d", len(state.Sessions))) + "\n" +
			LabelStyle.Render("Sessions"),
	)
	agentStats := statsStyle.Render(
		TitleStyle.Render(fmt.Sprintf("%d", len(state.Agents))) + "\n" +
			LabelStyle.Render("Agents"),
	)

	var runsStats, dispatchStats string
	if state.Kernel != nil {
		km := state.Kernel.Metrics
		runsStats = statsStyle.Render(
			TitleStyle.Render(fmt.Sprintf("%d", km.ActiveRuns)) + "\n" +
				LabelStyle.Render("Active Runs"),
		)
		blockedStyle := LabelStyle
		if km.BlockedAgents > 0 {
			blockedStyle = StatusError
		}
		dispatchStats = statsStyle.Render(
			TitleStyle.Render(fmt.Sprintf("%d", km.ActiveDispatches)) + "\n" +
				blockedStyle.Render(fmt.Sprintf("Dispatches (%d blocked)", km.BlockedAgents)),
		)
	} else {
		activeCount := 0
		for _, s := range state.Sessions {
			if s.UnifiedState == icdata.StatusActive || s.UnifiedState == icdata.StatusWaiting {
				activeCount++
			}
		}
		runsStats = statsStyle.Render(
			TitleStyle.Render(fmt.Sprintf("%d", activeCount)) + "\n" +
				LabelStyle.Render("Active"),
		)
		dispatchStats = ""
	}

	statsItems := []string{projectStats, sessionStats, agentStats, runsStats}
	if dispatchStats != "" {
		statsItems = append(statsItems, dispatchStats)
	}
	if state.Kernel != nil {
		km := state.Kernel.Metrics
		totalTokens := km.TotalTokensIn + km.TotalTokensOut
		if totalTokens > 0 {
			tokenStats := statsStyle.Render(
				TitleStyle.Render(formatTokens(totalTokens)) + "\n" +
					LabelStyle.Render(fmt.Sprintf("%s in / %s out",
						formatTokens(km.TotalTokensIn), formatTokens(km.TotalTokensOut))),
			)
			statsItems = append(statsItems, tokenStats)
		}
	}
	return lipgloss.JoinHorizontal(lipgloss.Top, statsItems...)
}

func (m Model) renderRunsSection(kernel *aggregator.KernelState) string {
	runsTitle := SubtitleStyle.Render("Active Runs")
	var runLines []string
	for projPath, runs := range kernel.Runs {
		projName := filepath.Base(projPath)
		for _, r := range runs {
			if r.Status == "" || r.Status == "done" || r.Status == "cancelled" {
				continue
			}
			goal := r.Goal
			if len(goal) > 40 {
				goal = goal[:37] + "..."
			}
			id := r.ID
			if len(id) > 8 {
				id = id[:8]
			}
			line := fmt.Sprintf("  %s %s %s %s %s",
				shared.UnifiedStatusSymbol(shared.UnifyStatusForRender(r.Status)),
				LabelStyle.Render(id),
				projName,
				TitleStyle.Render(r.Phase),
				goal,
			)
			runLines = append(runLines, line)
		}
	}
	if len(runLines) > 0 {
		return runsTitle + "\n" + strings.Join(runLines, "\n")
	}
	return runsTitle + "\n" + LabelStyle.Render("  No active runs")
}

func (m Model) renderDispatchesSection(kernel *aggregator.KernelState) string {
	dispTitle := SubtitleStyle.Render("Dispatches")
	type dispEntry struct {
		projName string
		d        icdata.Dispatch
		us       icdata.UnifiedStatus
	}
	var entries []dispEntry
	for projPath, dispatches := range kernel.Dispatches {
		pn := filepath.Base(projPath)
		for _, d := range dispatches {
			entries = append(entries, dispEntry{pn, d, icdata.UnifyStatus(d.Status)})
		}
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].us != entries[j].us {
			return entries[i].us < entries[j].us
		}
		return entries[i].d.CreatedAt > entries[j].d.CreatedAt
	})
	var dispLines []string
	for i, e := range entries {
		if i >= 10 {
			break
		}
		id := e.d.ID
		if len(id) > 8 {
			id = id[:8]
		}
		agent := e.d.DisplayName()
		if len(agent) > 16 {
			agent = agent[:16]
		}
		line := fmt.Sprintf("  %s %-8s %-16s %s",
			shared.UnifiedStatusSymbol(e.us),
			LabelStyle.Render(id),
			agent,
			e.us.String(),
		)
		dispLines = append(dispLines, line)
	}
	if len(dispLines) > 0 {
		return dispTitle + "\n" + strings.Join(dispLines, "\n")
	}
	return ""
}

func (m Model) renderRecentSessions(sessions []aggregator.TmuxSession) string {
	recentTitle := SubtitleStyle.Render("Recent Sessions")
	var recentSessions []string
	for i, s := range sessions {
		if i >= 5 {
			break
		}
		name := s.Name
		if s.AgentName != "" {
			name = s.AgentName
		}
		line := fmt.Sprintf("  %s %s %s",
			shared.UnifiedStatusIndicator(s.UnifiedState),
			name,
			LabelStyle.Render(filepath.Base(s.ProjectPath)),
		)
		recentSessions = append(recentSessions, line)
	}
	if len(recentSessions) == 0 {
		recentSessions = append(recentSessions, LabelStyle.Render("  No sessions"))
	}
	return recentTitle + "\n" + strings.Join(recentSessions, "\n")
}

func (m Model) renderRecentAgents(agents []aggregator.Agent) string {
	agentsTitle := SubtitleStyle.Render("Registered Agents")
	var recentAgents []string
	for i, a := range agents {
		if i >= 5 {
			break
		}
		line := fmt.Sprintf("  %s %s • %s",
			AgentBadge(a.Program),
			a.Name,
			LabelStyle.Render(filepath.Base(a.ProjectPath)),
		)
		recentAgents = append(recentAgents, line)
	}
	if len(recentAgents) == 0 {
		recentAgents = append(recentAgents, LabelStyle.Render("  No agents registered"))
	}
	return agentsTitle + "\n" + strings.Join(recentAgents, "\n")
}

func (m Model) renderActivityFeed(activities []aggregator.Activity) string {
	actTitle := SubtitleStyle.Render("Recent Activity")
	var actLines []string
	for i, a := range activities {
		if i >= 10 {
			break
		}
		prefix := lipgloss.NewStyle().Foreground(shared.ColorMuted).Render("[T]")
		switch a.Source {
		case "kernel":
			prefix = lipgloss.NewStyle().Foreground(shared.ColorPrimary).Render("[K]")
		case "intermute":
			prefix = lipgloss.NewStyle().Foreground(shared.ColorSuccess).Render("[M]")
		}
		ts := LabelStyle.Render(a.Time.Format("15:04:05"))
		line := fmt.Sprintf("  %s %s %s", ts, prefix, a.Summary)
		actLines = append(actLines, line)
	}
	return actTitle + "\n" + strings.Join(actLines, "\n")
}
```

**Step 5: Run all tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -v -count=1`
Expected: All PASS — the dashboard output is identical, just produced through cache now.

**Step 6: Commit**

```bash
git add apps/autarch/internal/bigend/tui/render_dashboard.go apps/autarch/internal/bigend/tui/section_cache_test.go
git commit -m "feat(bigend): wire section cache into renderDashboard for dirty tracking"
```

---

### Task 4: Resize cache invalidation

**Files:**
- Modify: `apps/autarch/internal/bigend/tui/model.go` (applyResize)
- Test: `apps/autarch/internal/bigend/tui/section_cache_test.go` (add invalidation tests)

> **Note:** Tab-switch invalidation was removed during plan review — dashboard sections only render when `activeTab == TabDashboard`, so the cache is never consulted on other tabs. Clearing it on tab switch would be a no-op waste.

**Step 1: Write the failing test**

Append to `section_cache_test.go`:

```go
func TestResizeInvalidatesCache(t *testing.T) {
	agg := &fakeAggStatus{state: aggregator.State{
		Sessions: []aggregator.TmuxSession{
			{Name: "s1", ProjectPath: "/proj"},
		},
	}}
	m := New(agg, "test")
	m.width = 120
	m.height = 40

	// Prime the cache
	m.renderDashboard()

	// Verify cache has entries
	if len(m.dashCache.entries) == 0 {
		t.Fatal("cache should have entries after render")
	}

	// Simulate resize
	m = m.applyResize(tea.WindowSizeMsg{Width: 80, Height: 30})

	// Cache should be empty
	if len(m.dashCache.entries) != 0 {
		t.Errorf("cache should be empty after resize, has %d entries", len(m.dashCache.entries))
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -run TestResizeInvalidates -v`
Expected: FAIL — `applyResize` doesn't yet call `invalidateAll()`.

**Step 3: Add cache invalidation to applyResize**

In `model.go`, at the start of `applyResize()`, add:

```go
	m.dashCache.invalidateAll()
```

(Place it right after the function signature, before `m.width = msg.Width`.)

**Step 4: Run all tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/bigend/tui/ -v -count=1 -race`
Expected: All PASS with no race conditions.

**Step 5: Run full package build**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/...`
Expected: Builds cleanly.

**Step 6: Commit**

```bash
git add apps/autarch/internal/bigend/tui/model.go apps/autarch/internal/bigend/tui/section_cache_test.go
git commit -m "feat(bigend): invalidate section cache on resize"
```

---

## Notes for the implementer

- **Do NOT change aggregator types.** All caching lives in `internal/bigend/tui/`. The `aggregatorAPI` interface and `aggregator.State` are untouched.
- **Map iteration order:** `hashRuns` and `hashDispatches` sort map keys before hashing to ensure deterministic output. Without sorting, Go map iteration randomness would produce different hashes on identical data, killing cache effectiveness for kernel sections.
- **Test with `-race`:** The Model is single-threaded (Bubble Tea serializes Update/View), but test with `-race` per project convention.
- **`discovery.Project.HasIntercore`:** Used in the stats hash. Check that the import for `discovery` is available or accessed through `state.Projects[i].HasIntercore` (it's on the `discovery.Project` type which is what `State.Projects` holds).
