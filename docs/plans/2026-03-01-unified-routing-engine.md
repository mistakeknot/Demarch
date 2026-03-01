# Unified Routing Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build a unified routing engine in intercore that answers "given this task, which model/agent should handle it?" using cost-aware capability matching, then retire the interserve plugin.

**Architecture:** A new `core/intercore/internal/routing/` Go package absorbs the routing logic currently split across lib-routing.sh (928 lines of bash YAML parsing), interserve classify.go (keyword matching), and agent-roles.yaml (safety floors). The `ic route` CLI command exposes it. lib-routing.sh becomes a thin shell wrapper calling `ic route` for backward compatibility (strangler-fig pattern). interserve is retired after consumers migrate.

**Tech Stack:** Go (intercore), Bash (lib-routing.sh wrapper), YAML (routing.yaml, agent-roles.yaml, costs.yaml)

## Prior Learnings

- **Safety floor enforcement** (MEMORY.md): Namespace stripping is critical — `_ROUTING_SF_AGENT_MIN` cache is keyed by short names, but callers pass namespaced IDs like `interflux:review:fd-safety`. Must strip prefix for lookup. Also: YAML parser ordering dependency — `min_model:` must appear before `agents:` in each role block.
- **Static routing table PRD** (docs/prds/2026-02-21-static-routing-table.md): Two-namespace schema (subagents: Claude aliases, dispatch: Codex tier names). Nested-inheritance resolution: `overrides > phases[current].categories > phases[current].model > defaults.categories > defaults.model`.
- **Routing experiments** (iv-jocaw): B1 + safety floors is Pareto-optimal. B2 complexity routing increases cost 20%. fd-safety on Haiku 47%, fd-correctness 26% — quality risk confirms safety floors are mandatory.
- **Cost-aware scheduling PRD** (docs/prds/2026-02-20-cost-aware-agent-scheduling.md): Phase-granularity writeback, not real-time. `FLUX_BUDGET_REMAINING` env var. Fleet registry fallback chain: interstat (≥3 runs) → fleet-registry → budget.yaml defaults.

---

### Task 1: Create routing package with config parser

**Files:**
- Create: `core/intercore/internal/routing/routing.go`
- Create: `core/intercore/internal/routing/config.go`
- Create: `core/intercore/internal/routing/config_test.go`

**Step 1: Write the failing test for config parsing**

```go
// config_test.go
package routing

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadConfig_SubagentDefaults(t *testing.T) {
	dir := t.TempDir()
	routingYAML := filepath.Join(dir, "routing.yaml")
	os.WriteFile(routingYAML, []byte(`
subagents:
  defaults:
    model: sonnet
    categories:
      research: haiku
      review: sonnet
  phases:
    brainstorm:
      model: opus
      categories:
        research: haiku
    executing:
      model: sonnet
  overrides:
    interflux:review:fd-safety: sonnet
dispatch:
  tiers:
    fast:
      model: gpt-5.3-codex-spark
      description: Scoped read-only tasks
    deep:
      model: gpt-5.3-codex
      description: Generative tasks
  fallback:
    fast: deep
`), 0644)

	cfg, err := LoadConfig(routingYAML, "")
	if err != nil {
		t.Fatalf("LoadConfig: %v", err)
	}
	if cfg.Subagents.Defaults.Model != "sonnet" {
		t.Errorf("default model = %q, want sonnet", cfg.Subagents.Defaults.Model)
	}
	if cfg.Subagents.Defaults.Categories["research"] != "haiku" {
		t.Errorf("default research = %q, want haiku", cfg.Subagents.Defaults.Categories["research"])
	}
	if cfg.Subagents.Phases["brainstorm"].Model != "opus" {
		t.Errorf("brainstorm model = %q, want opus", cfg.Subagents.Phases["brainstorm"].Model)
	}
	if cfg.Dispatch.Tiers["fast"].Model != "gpt-5.3-codex-spark" {
		t.Errorf("fast tier = %q, want gpt-5.3-codex-spark", cfg.Dispatch.Tiers["fast"].Model)
	}
	if cfg.Dispatch.Fallback["fast"] != "deep" {
		t.Errorf("fast fallback = %q, want deep", cfg.Dispatch.Fallback["fast"])
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd core/intercore && go test ./internal/routing/... -v -run TestLoadConfig`
Expected: FAIL — package doesn't exist yet

**Step 3: Write config types and YAML parser**

```go
// routing.go — package declaration and core types
package routing

// ModelTier represents Claude model capability tiers.
type ModelTier int

const (
	TierUnknown ModelTier = 0
	TierHaiku   ModelTier = 1
	TierSonnet  ModelTier = 2
	TierOpus    ModelTier = 3
)

func ParseModelTier(s string) ModelTier {
	switch s {
	case "haiku":
		return TierHaiku
	case "sonnet":
		return TierSonnet
	case "opus":
		return TierOpus
	default:
		return TierUnknown
	}
}

func (t ModelTier) String() string {
	switch t {
	case TierHaiku:
		return "haiku"
	case TierSonnet:
		return "sonnet"
	case TierOpus:
		return "opus"
	default:
		return "unknown"
	}
}
```

```go
// config.go — config types and YAML loader
package routing

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Config is the unified routing configuration.
type Config struct {
	Subagents  SubagentConfig  `yaml:"subagents"`
	Dispatch   DispatchConfig  `yaml:"dispatch"`
	Complexity ComplexityConfig `yaml:"complexity"`
	Roles      RolesConfig     `yaml:"-"` // loaded from separate file
}

type SubagentConfig struct {
	Defaults  SubagentDefaults         `yaml:"defaults"`
	Phases    map[string]PhaseConfig   `yaml:"phases"`
	Overrides map[string]string        `yaml:"overrides"`
}

type SubagentDefaults struct {
	Model      string            `yaml:"model"`
	Categories map[string]string `yaml:"categories"`
}

type PhaseConfig struct {
	Model      string            `yaml:"model"`
	Categories map[string]string `yaml:"categories"`
}

type DispatchConfig struct {
	Tiers    map[string]TierConfig `yaml:"tiers"`
	Fallback map[string]string     `yaml:"fallback"`
}

type TierConfig struct {
	Model       string `yaml:"model"`
	Description string `yaml:"description"`
}

type ComplexityConfig struct {
	Mode      string                      `yaml:"mode"` // off, shadow, enforce
	Tiers     map[string]ComplexityTier    `yaml:"tiers"`
	Overrides map[string]ComplexityOverride `yaml:"overrides"`
}

type ComplexityTier struct {
	Description    string `yaml:"description"`
	PromptTokens   int    `yaml:"prompt_tokens"`
	FileCount      int    `yaml:"file_count"`
	ReasoningDepth int    `yaml:"reasoning_depth"`
}

type ComplexityOverride struct {
	SubagentModel string `yaml:"subagent_model"`
	DispatchTier  string `yaml:"dispatch_tier"`
}

// RolesConfig holds agent-roles.yaml data (safety floors).
type RolesConfig struct {
	Roles map[string]RoleEntry `yaml:"roles"`
}

type RoleEntry struct {
	Description string   `yaml:"description"`
	ModelTier   string   `yaml:"model_tier"`
	MinModel    string   `yaml:"min_model"`
	Agents      []string `yaml:"agents"`
}

// LoadConfig loads routing.yaml and optionally agent-roles.yaml.
func LoadConfig(routingPath, rolesPath string) (*Config, error) {
	cfg := &Config{}

	data, err := os.ReadFile(routingPath)
	if err != nil {
		return nil, fmt.Errorf("read routing.yaml: %w", err)
	}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse routing.yaml: %w", err)
	}

	// Initialize nil maps
	if cfg.Subagents.Phases == nil {
		cfg.Subagents.Phases = map[string]PhaseConfig{}
	}
	if cfg.Subagents.Overrides == nil {
		cfg.Subagents.Overrides = map[string]string{}
	}
	if cfg.Subagents.Defaults.Categories == nil {
		cfg.Subagents.Defaults.Categories = map[string]string{}
	}
	if cfg.Dispatch.Tiers == nil {
		cfg.Dispatch.Tiers = map[string]TierConfig{}
	}
	if cfg.Dispatch.Fallback == nil {
		cfg.Dispatch.Fallback = map[string]string{}
	}
	if cfg.Complexity.Mode == "" {
		cfg.Complexity.Mode = "off"
	}

	// Load agent-roles.yaml if path provided
	if rolesPath != "" {
		rolesData, err := os.ReadFile(rolesPath)
		if err == nil {
			var roles RolesConfig
			if err := yaml.Unmarshal(rolesData, &roles); err == nil {
				cfg.Roles = roles
			}
		}
		// Non-fatal: safety floors are a progressive enhancement
	}

	return cfg, nil
}

// SafetyFloors extracts agent → min_model mapping from roles config.
func (c *Config) SafetyFloors() map[string]string {
	floors := make(map[string]string)
	for _, role := range c.Roles.Roles {
		if role.MinModel == "" {
			continue
		}
		for _, agent := range role.Agents {
			floors[agent] = role.MinModel
		}
	}
	return floors
}
```

**Step 4: Run test to verify it passes**

Run: `cd core/intercore && go test ./internal/routing/... -v -run TestLoadConfig`
Expected: PASS

**Step 5: Commit**

```bash
cd core/intercore && git add internal/routing/
git commit -m "feat(routing): add config types and YAML parser for unified routing engine"
```

---

### Task 2: Implement the routing resolver

**Files:**
- Create: `core/intercore/internal/routing/resolve.go`
- Create: `core/intercore/internal/routing/resolve_test.go`

**Step 1: Write the failing tests**

```go
// resolve_test.go
package routing

import (
	"testing"
)

func testConfig() *Config {
	return &Config{
		Subagents: SubagentConfig{
			Defaults: SubagentDefaults{
				Model:      "sonnet",
				Categories: map[string]string{"research": "haiku", "review": "sonnet"},
			},
			Phases: map[string]PhaseConfig{
				"brainstorm": {Model: "opus", Categories: map[string]string{"research": "haiku"}},
				"executing":  {Model: "sonnet"},
			},
			Overrides: map[string]string{
				"interflux:review:fd-safety": "sonnet",
			},
		},
	}
}

func TestResolveModel_DefaultFallback(t *testing.T) {
	r := NewResolver(testConfig())
	got := r.ResolveModel(ResolveOpts{})
	if got != "sonnet" {
		t.Errorf("ResolveModel() = %q, want sonnet", got)
	}
}

func TestResolveModel_PhaseOverride(t *testing.T) {
	r := NewResolver(testConfig())
	got := r.ResolveModel(ResolveOpts{Phase: "brainstorm"})
	if got != "opus" {
		t.Errorf("ResolveModel(brainstorm) = %q, want opus", got)
	}
}

func TestResolveModel_PhaseCategoryOverride(t *testing.T) {
	r := NewResolver(testConfig())
	got := r.ResolveModel(ResolveOpts{Phase: "brainstorm", Category: "research"})
	if got != "haiku" {
		t.Errorf("ResolveModel(brainstorm,research) = %q, want haiku", got)
	}
}

func TestResolveModel_AgentOverride(t *testing.T) {
	r := NewResolver(testConfig())
	got := r.ResolveModel(ResolveOpts{Agent: "interflux:review:fd-safety", Phase: "executing"})
	if got != "sonnet" {
		t.Errorf("ResolveModel(fd-safety) = %q, want sonnet", got)
	}
}

func TestResolveModel_SafetyFloor(t *testing.T) {
	cfg := testConfig()
	cfg.Roles = RolesConfig{
		Roles: map[string]RoleEntry{
			"reviewer": {MinModel: "sonnet", Agents: []string{"fd-safety", "fd-correctness"}},
		},
	}
	// Default category "research" = haiku, but fd-safety has sonnet floor
	r := NewResolver(cfg)
	got := r.ResolveModel(ResolveOpts{Agent: "fd-safety", Category: "research"})
	if got != "sonnet" {
		t.Errorf("ResolveModel(fd-safety,research) = %q, want sonnet (clamped by floor)", got)
	}
}

func TestResolveModel_SafetyFloor_NamespaceStrip(t *testing.T) {
	cfg := testConfig()
	cfg.Roles = RolesConfig{
		Roles: map[string]RoleEntry{
			"reviewer": {MinModel: "sonnet", Agents: []string{"fd-safety"}},
		},
	}
	r := NewResolver(cfg)
	// Namespaced agent ID should still hit the floor via short-name lookup
	got := r.ResolveModel(ResolveOpts{Agent: "interflux:review:fd-safety", Category: "research"})
	if got != "sonnet" {
		t.Errorf("ResolveModel(namespaced fd-safety) = %q, want sonnet", got)
	}
}

func TestResolveModel_InheritSkipped(t *testing.T) {
	cfg := testConfig()
	cfg.Subagents.Overrides["fd-test"] = "inherit"
	r := NewResolver(cfg)
	got := r.ResolveModel(ResolveOpts{Agent: "fd-test"})
	if got != "sonnet" {
		t.Errorf("inherit should fall through to default, got %q", got)
	}
}

func TestResolveDispatchTier(t *testing.T) {
	cfg := testConfig()
	cfg.Dispatch.Tiers = map[string]TierConfig{
		"fast": {Model: "gpt-5.3-codex-spark"},
		"deep": {Model: "gpt-5.3-codex"},
	}
	cfg.Dispatch.Fallback = map[string]string{"fast": "deep"}
	r := NewResolver(cfg)

	got := r.ResolveDispatchTier("fast")
	if got != "gpt-5.3-codex-spark" {
		t.Errorf("ResolveDispatchTier(fast) = %q, want gpt-5.3-codex-spark", got)
	}

	got = r.ResolveDispatchTier("unknown-tier")
	if got != "" {
		t.Errorf("ResolveDispatchTier(unknown) = %q, want empty", got)
	}
}

func TestResolveBatch(t *testing.T) {
	cfg := testConfig()
	cfg.Roles = RolesConfig{
		Roles: map[string]RoleEntry{
			"reviewer": {MinModel: "sonnet", Agents: []string{"fd-safety", "fd-correctness"}},
		},
	}
	r := NewResolver(cfg)

	agents := []string{"fd-safety", "fd-architecture", "best-practices-researcher"}
	result := r.ResolveBatch(agents, "executing")

	if result["fd-safety"] != "sonnet" {
		t.Errorf("fd-safety = %q, want sonnet", result["fd-safety"])
	}
	if result["best-practices-researcher"] != "haiku" {
		t.Errorf("researcher = %q, want haiku", result["best-practices-researcher"])
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd core/intercore && go test ./internal/routing/... -v -run TestResolve`
Expected: FAIL — functions don't exist

**Step 3: Write the resolver**

```go
// resolve.go
package routing

import "strings"

// Resolver performs model resolution using loaded config.
type Resolver struct {
	cfg    *Config
	floors map[string]string // agent short name → min model
}

// NewResolver creates a resolver from config.
func NewResolver(cfg *Config) *Resolver {
	return &Resolver{
		cfg:    cfg,
		floors: cfg.SafetyFloors(),
	}
}

// ResolveOpts specifies the resolution context.
type ResolveOpts struct {
	Phase    string
	Category string
	Agent    string
}

// ResolveModel resolves the model for a given context.
// Resolution order (highest priority first):
//   overrides[agent] > phases[phase].categories[cat] > phases[phase].model >
//   defaults.categories[cat] > defaults.model > "sonnet"
// Then applies safety floor clamping.
func (r *Resolver) ResolveModel(opts ResolveOpts) string {
	result := ""

	// 1. Per-agent override
	if opts.Agent != "" {
		if v, ok := r.cfg.Subagents.Overrides[opts.Agent]; ok && v != "inherit" {
			result = v
		}
	}

	// 2. Phase-specific category
	if result == "" && opts.Phase != "" && opts.Category != "" {
		if phase, ok := r.cfg.Subagents.Phases[opts.Phase]; ok {
			if v, ok := phase.Categories[opts.Category]; ok && v != "inherit" {
				result = v
			}
		}
	}

	// 3. Phase-level model
	if result == "" && opts.Phase != "" {
		if phase, ok := r.cfg.Subagents.Phases[opts.Phase]; ok {
			if phase.Model != "" && phase.Model != "inherit" {
				result = phase.Model
			}
		}
	}

	// 4. Default category
	if result == "" && opts.Category != "" {
		if v, ok := r.cfg.Subagents.Defaults.Categories[opts.Category]; ok && v != "inherit" {
			result = v
		}
	}

	// 5. Default model
	if result == "" && r.cfg.Subagents.Defaults.Model != "" && r.cfg.Subagents.Defaults.Model != "inherit" {
		result = r.cfg.Subagents.Defaults.Model
	}

	// 6. Ultimate fallback
	if result == "" || result == "inherit" {
		result = "sonnet"
	}

	// Safety floor clamping
	if opts.Agent != "" {
		result = r.applyFloor(opts.Agent, result)
	}

	return result
}

// ResolveDispatchTier resolves a dispatch tier name to a model ID.
// Follows the fallback chain up to 3 hops.
func (r *Resolver) ResolveDispatchTier(tier string) string {
	for hops := 0; hops < 3; hops++ {
		if t, ok := r.cfg.Dispatch.Tiers[tier]; ok {
			return t.Model
		}
		if fb, ok := r.cfg.Dispatch.Fallback[tier]; ok {
			tier = fb
		} else {
			break
		}
	}
	return ""
}

// ResolveBatch resolves models for a list of agent short names.
// Returns map[agentShortName]model. Infers category from agent name patterns.
func (r *Resolver) ResolveBatch(agents []string, phase string) map[string]string {
	result := make(map[string]string, len(agents))
	for _, agent := range agents {
		category := inferCategory(agent)
		model := r.ResolveModel(ResolveOpts{
			Phase:    phase,
			Category: category,
			Agent:    inferAgentID(agent),
		})
		result[agent] = model
	}
	return result
}

// applyFloor clamps model up to the safety floor if one exists.
// Handles namespaced agent IDs by stripping to short name.
func (r *Resolver) applyFloor(agent, model string) string {
	// Try full agent ID first
	floor, ok := r.floors[agent]
	if !ok && strings.Contains(agent, ":") {
		// Strip namespace: "interflux:review:fd-safety" → "fd-safety"
		parts := strings.Split(agent, ":")
		short := parts[len(parts)-1]
		floor, ok = r.floors[short]
	}
	if !ok {
		return model
	}

	modelTier := ParseModelTier(model)
	floorTier := ParseModelTier(floor)
	if floorTier == TierUnknown || modelTier >= floorTier {
		return model
	}
	return floor
}

// inferCategory determines routing category from agent name patterns.
func inferCategory(agent string) string {
	if strings.HasSuffix(agent, "-researcher") || agent == "repo-research-analyst" {
		return "research"
	}
	if strings.HasPrefix(agent, "fd-") {
		return "review"
	}
	return ""
}

// inferAgentID maps short agent names to namespaced IDs for override lookup.
func inferAgentID(agent string) string {
	if strings.HasSuffix(agent, "-researcher") || agent == "repo-research-analyst" {
		return "interflux:research:" + agent
	}
	if strings.HasPrefix(agent, "fd-") {
		return "interflux:review:" + agent
	}
	return agent
}
```

**Step 4: Run tests to verify they pass**

Run: `cd core/intercore && go test ./internal/routing/... -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
cd core/intercore && git add internal/routing/resolve.go internal/routing/resolve_test.go
git commit -m "feat(routing): implement model resolver with safety floors and batch resolution"
```

---

### Task 3: Add cost table and cost-aware ranking

**Files:**
- Create: `core/intercore/internal/routing/costs.go`
- Create: `core/intercore/internal/routing/costs_test.go`

**Step 1: Write the failing test**

```go
// costs_test.go
package routing

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadCostTable(t *testing.T) {
	dir := t.TempDir()
	costsYAML := filepath.Join(dir, "costs.yaml")
	os.WriteFile(costsYAML, []byte(`
models:
  opus:
    input_per_mtok: 15.00
    output_per_mtok: 75.00
  sonnet:
    input_per_mtok: 3.00
    output_per_mtok: 15.00
  haiku:
    input_per_mtok: 0.25
    output_per_mtok: 1.25
  gpt-5.3-codex-spark:
    input_per_mtok: 1.50
    output_per_mtok: 6.00
  gpt-5.3-codex:
    input_per_mtok: 3.00
    output_per_mtok: 12.00
`), 0644)

	table, err := LoadCostTable(costsYAML)
	if err != nil {
		t.Fatalf("LoadCostTable: %v", err)
	}
	if table.Models["opus"].OutputPerMTok != 75.00 {
		t.Errorf("opus output = %f, want 75.00", table.Models["opus"].OutputPerMTok)
	}
}

func TestCheapestCapable(t *testing.T) {
	table := &CostTable{
		Models: map[string]ModelCost{
			"opus":   {InputPerMTok: 15.0, OutputPerMTok: 75.0},
			"sonnet": {InputPerMTok: 3.0, OutputPerMTok: 15.0},
			"haiku":  {InputPerMTok: 0.25, OutputPerMTok: 1.25},
		},
	}

	// All capable, cheapest is haiku
	got := table.CheapestCapable([]string{"opus", "sonnet", "haiku"})
	if got != "haiku" {
		t.Errorf("CheapestCapable = %q, want haiku", got)
	}

	// Only opus and sonnet
	got = table.CheapestCapable([]string{"opus", "sonnet"})
	if got != "sonnet" {
		t.Errorf("CheapestCapable = %q, want sonnet", got)
	}

	// Empty list
	got = table.CheapestCapable(nil)
	if got != "" {
		t.Errorf("CheapestCapable(nil) = %q, want empty", got)
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd core/intercore && go test ./internal/routing/... -v -run TestCost`

**Step 3: Write the cost table**

```go
// costs.go
package routing

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// CostTable holds per-model pricing data.
type CostTable struct {
	Models map[string]ModelCost `yaml:"models"`
}

// ModelCost holds pricing per million tokens.
type ModelCost struct {
	InputPerMTok  float64 `yaml:"input_per_mtok"`
	OutputPerMTok float64 `yaml:"output_per_mtok"`
}

// EffectiveCost returns a blended cost assuming the project's 15:1 output:input ratio.
func (mc ModelCost) EffectiveCost() float64 {
	return mc.InputPerMTok + 15.0*mc.OutputPerMTok
}

// LoadCostTable loads a costs.yaml file.
func LoadCostTable(path string) (*CostTable, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read costs.yaml: %w", err)
	}
	var table CostTable
	if err := yaml.Unmarshal(data, &table); err != nil {
		return nil, fmt.Errorf("parse costs.yaml: %w", err)
	}
	if table.Models == nil {
		table.Models = map[string]ModelCost{}
	}
	return &table, nil
}

// CheapestCapable returns the model with the lowest effective cost from the capable list.
func (ct *CostTable) CheapestCapable(capable []string) string {
	if len(capable) == 0 {
		return ""
	}
	best := ""
	bestCost := -1.0
	for _, model := range capable {
		mc, ok := ct.Models[model]
		if !ok {
			continue
		}
		cost := mc.EffectiveCost()
		if bestCost < 0 || cost < bestCost {
			best = model
			bestCost = cost
		}
	}
	return best
}
```

**Step 4: Run tests**

Run: `cd core/intercore && go test ./internal/routing/... -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
cd core/intercore && git add internal/routing/costs.go internal/routing/costs_test.go
git commit -m "feat(routing): add cost table with cheapest-capable ranking"
```

---

### Task 4: Add `ic route` CLI command

**Files:**
- Create: `core/intercore/cmd/ic/route.go`

**Step 1: Write the CLI command**

```go
// route.go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/mistakeknot/intercore/internal/routing"
)

func cmdRoute(ctx context.Context, args []string) int {
	if len(args) == 0 {
		fmt.Fprintf(os.Stderr, "ic: route: usage: ic route model [--phase=P] [--category=C] [--agent=A]\n")
		fmt.Fprintf(os.Stderr, "       ic route batch --phase=P --agents=a,b,c\n")
		fmt.Fprintf(os.Stderr, "       ic route dispatch --tier=T\n")
		fmt.Fprintf(os.Stderr, "       ic route table\n")
		return 3
	}

	switch args[0] {
	case "model":
		return cmdRouteModel(ctx, args[1:])
	case "batch":
		return cmdRouteBatch(ctx, args[1:])
	case "dispatch":
		return cmdRouteDispatch(ctx, args[1:])
	case "table":
		return cmdRouteTable(ctx, args[1:])
	default:
		slog.Error("route: unknown subcommand", "subcommand", args[0])
		return 3
	}
}

func loadResolver() (*routing.Resolver, error) {
	// Find routing.yaml: CLAVAIN_ROUTING_CONFIG > relative paths > well-known locations
	routingPath := os.Getenv("CLAVAIN_ROUTING_CONFIG")
	if routingPath == "" {
		candidates := []string{
			filepath.Join(os.Getenv("CLAVAIN_SOURCE_DIR"), "config", "routing.yaml"),
			filepath.Join(os.Getenv("CLAVAIN_DIR"), "config", "routing.yaml"),
		}
		for _, c := range candidates {
			if c != "" {
				if _, err := os.Stat(c); err == nil {
					routingPath = c
					break
				}
			}
		}
	}
	if routingPath == "" {
		return nil, fmt.Errorf("routing.yaml not found (set CLAVAIN_ROUTING_CONFIG)")
	}

	// Find agent-roles.yaml
	rolesPath := os.Getenv("CLAVAIN_ROLES_CONFIG")
	if rolesPath == "" {
		// Try interflux config relative to routing.yaml
		dir := filepath.Dir(filepath.Dir(routingPath)) // config/ -> clavain/
		candidates := []string{
			filepath.Join(dir, "..", "interverse", "interflux", "config", "flux-drive", "agent-roles.yaml"),
			filepath.Join(dir, "config", "agent-roles.yaml"),
		}
		for _, c := range candidates {
			if _, err := os.Stat(c); err == nil {
				rolesPath = c
				break
			}
		}
	}

	cfg, err := routing.LoadConfig(routingPath, rolesPath)
	if err != nil {
		return nil, err
	}
	return routing.NewResolver(cfg), nil
}

func cmdRouteModel(ctx context.Context, args []string) int {
	opts := routing.ResolveOpts{}
	for _, arg := range args {
		switch {
		case strings.HasPrefix(arg, "--phase="):
			opts.Phase = strings.TrimPrefix(arg, "--phase=")
		case strings.HasPrefix(arg, "--category="):
			opts.Category = strings.TrimPrefix(arg, "--category=")
		case strings.HasPrefix(arg, "--agent="):
			opts.Agent = strings.TrimPrefix(arg, "--agent=")
		}
	}

	r, err := loadResolver()
	if err != nil {
		slog.Error("route model", "error", err)
		return 2
	}

	model := r.ResolveModel(opts)
	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(map[string]string{
			"model":    model,
			"phase":    opts.Phase,
			"category": opts.Category,
			"agent":    opts.Agent,
		})
	} else {
		fmt.Println(model)
	}
	return 0
}

func cmdRouteBatch(ctx context.Context, args []string) int {
	var phase, agentsCSV string
	for _, arg := range args {
		switch {
		case strings.HasPrefix(arg, "--phase="):
			phase = strings.TrimPrefix(arg, "--phase=")
		case strings.HasPrefix(arg, "--agents="):
			agentsCSV = strings.TrimPrefix(arg, "--agents=")
		}
	}

	if agentsCSV == "" {
		slog.Error("route batch: --agents is required")
		return 3
	}

	r, err := loadResolver()
	if err != nil {
		slog.Error("route batch", "error", err)
		return 2
	}

	agents := strings.Split(agentsCSV, ",")
	for i := range agents {
		agents[i] = strings.TrimSpace(agents[i])
	}
	result := r.ResolveBatch(agents, phase)

	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(result)
	} else {
		for agent, model := range result {
			fmt.Printf("%s=%s\n", agent, model)
		}
	}
	return 0
}

func cmdRouteDispatch(ctx context.Context, args []string) int {
	var tier string
	for _, arg := range args {
		if strings.HasPrefix(arg, "--tier=") {
			tier = strings.TrimPrefix(arg, "--tier=")
		}
	}
	if tier == "" {
		slog.Error("route dispatch: --tier is required")
		return 3
	}

	r, err := loadResolver()
	if err != nil {
		slog.Error("route dispatch", "error", err)
		return 2
	}

	model := r.ResolveDispatchTier(tier)
	if model == "" {
		slog.Error("route dispatch: tier not found", "tier", tier)
		return 1
	}

	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(map[string]string{"model": model, "tier": tier})
	} else {
		fmt.Println(model)
	}
	return 0
}

func cmdRouteTable(ctx context.Context, args []string) int {
	r, err := loadResolver()
	if err != nil {
		slog.Error("route table", "error", err)
		return 2
	}

	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(r.Config())
	} else {
		fmt.Println("Routing table:")
		fmt.Printf("  Default: %s\n", r.Config().Subagents.Defaults.Model)
		for cat, model := range r.Config().Subagents.Defaults.Categories {
			fmt.Printf("  Category %s: %s\n", cat, model)
		}
		for name, phase := range r.Config().Subagents.Phases {
			fmt.Printf("  Phase %s: %s\n", name, phase.Model)
		}
		for agent, model := range r.Config().Subagents.Overrides {
			fmt.Printf("  Override %s: %s\n", agent, model)
		}
		floors := r.Config().SafetyFloors()
		if len(floors) > 0 {
			fmt.Println("  Safety floors:")
			for agent, floor := range floors {
				fmt.Printf("    %s: >= %s\n", agent, floor)
			}
		}
	}
	return 0
}
```

Note: Add `Config()` getter to `Resolver` in resolve.go:
```go
func (r *Resolver) Config() *Config { return r.cfg }
```

And register the command in main.go — find the command switch and add:
```go
case "route":
    return cmdRoute(ctx, args[1:])
```

**Step 2: Build and test**

Run: `cd core/intercore && go build -o ic ./cmd/ic/ && ./ic route model --phase=brainstorm`
Expected: `opus`

Run: `./ic route batch --phase=executing --agents=fd-safety,fd-architecture,best-practices-researcher --json`
Expected: JSON with model per agent

**Step 3: Commit**

```bash
cd core/intercore && git add cmd/ic/route.go internal/routing/resolve.go
git commit -m "feat(routing): add ic route CLI command (model, batch, dispatch, table)"
```

---

### Task 5: Create costs.yaml with current model pricing

**Files:**
- Create: `core/intercore/config/costs.yaml`

**Step 1: Create the cost table**

```yaml
# Model cost table for routing decisions.
# Prices are per million tokens (USD).
# Updated: 2026-03-01
#
# Source: Anthropic pricing page, OpenAI Codex pricing
# The effective_cost column uses 15:1 output:input ratio (from interstat baseline).
#
# To update: edit this file and rebuild ic. No code changes needed.

models:
  opus:
    input_per_mtok: 15.00
    output_per_mtok: 75.00
    # effective: 15 + 15*75 = $1140/M tokens blended

  sonnet:
    input_per_mtok: 3.00
    output_per_mtok: 15.00
    # effective: 3 + 15*15 = $228/M tokens blended

  haiku:
    input_per_mtok: 0.25
    output_per_mtok: 1.25
    # effective: 0.25 + 15*1.25 = $19/M tokens blended

  gpt-5.3-codex-spark:
    input_per_mtok: 1.50
    output_per_mtok: 6.00
    # effective: 1.5 + 15*6 = $91.5/M tokens blended

  gpt-5.3-codex:
    input_per_mtok: 3.00
    output_per_mtok: 12.00
    # effective: 3 + 15*12 = $183/M tokens blended

  gpt-5.3-codex-spark-xhigh:
    input_per_mtok: 2.00
    output_per_mtok: 8.00

  gpt-5.3-codex-xhigh:
    input_per_mtok: 4.00
    output_per_mtok: 16.00
```

**Step 2: Commit**

```bash
cd core/intercore && git add config/costs.yaml
git commit -m "feat(routing): add model cost table (costs.yaml)"
```

---

### Task 6: Wire lib-routing.sh to call `ic route` (strangler-fig)

**Files:**
- Modify: `os/clavain/scripts/lib-routing.sh`

This is the critical migration task. The approach is **strangler-fig**: keep the existing shell API but add an `ic route` fast path. If `ic` is available, delegate to it. If not, fall back to the existing bash YAML parsing.

**Step 1: Add ic-route fast path to routing_resolve_model**

At the top of `routing_resolve_model()` (after `_routing_load_cache`), add:

```bash
# Fast path: if ic binary is available, delegate to compiled router
if command -v ic >/dev/null 2>&1; then
    local ic_args=()
    [[ -n "$phase" ]]    && ic_args+=(--phase="$phase")
    [[ -n "$category" ]] && ic_args+=(--category="$category")
    [[ -n "$agent" ]]    && ic_args+=(--agent="$agent")
    local ic_result
    ic_result=$(ic route model "${ic_args[@]}" 2>/dev/null) || ic_result=""
    if [[ -n "$ic_result" ]]; then
        echo "$ic_result"
        return 0
    fi
    # Fall through to bash implementation on failure
fi
```

Apply the same pattern to `routing_resolve_agents` (use `ic route batch`) and `routing_resolve_dispatch_tier` (use `ic route dispatch`).

**Step 2: Test**

Run: `source os/clavain/scripts/lib-routing.sh && routing_resolve_model --phase brainstorm`
Expected: `opus` (from ic route if available, or bash parser fallback)

Run: `routing_resolve_agents --phase executing --agents "fd-safety,fd-architecture"`
Expected: JSON map with models

**Step 3: Commit**

```bash
cd os/clavain && git add scripts/lib-routing.sh
git commit -m "feat(routing): add ic route fast path to lib-routing.sh (strangler-fig)"
```

---

### Task 7: Disable interserve plugin

**Files:**
- Modify: `~/.claude/settings.json` — set `"interserve@interagency-marketplace": false`

**Step 1: Disable in settings**

Edit `~/.claude/settings.json` to set interserve to false.

**Step 2: Verify no session-breaking side effects**

Run: `claude plugin list 2>&1 | grep interserve`
Expected: interserve shows as disabled or absent

Check that interflux flux-drive still works by verifying Method 2 fallback:
- The slicing.md phase explicitly falls back to keyword matching when interserve MCP is unavailable
- No code change needed in interflux

**Step 3: Commit**

```bash
# No code commit needed — settings.json is local config
# Document the deprecation
echo "# interserve deprecated 2026-03-01 — routing moved to intercore" > interverse/interserve/DEPRECATED.md
cd interverse/interserve && git add DEPRECATED.md && git commit -m "chore: mark interserve as deprecated — routing moved to intercore"
```

---

### Task 8: Build, install, and smoke test

**Files:**
- Build: `core/intercore/cmd/ic/`

**Step 1: Run full test suite**

Run: `cd core/intercore && go test ./... -count=1`
Expected: ALL PASS (including new routing tests)

**Step 2: Build and install**

Run: `cd core/intercore && go build -o ic ./cmd/ic/ && cp ic ~/.local/bin/ic`

**Step 3: Smoke test `ic route`**

```bash
# Set env for config discovery
export CLAVAIN_SOURCE_DIR=/home/mk/projects/Demarch/os/clavain

ic route model --phase=brainstorm
# Expected: opus

ic route model --phase=executing --category=research
# Expected: haiku

ic route batch --phase=executing --agents=fd-safety,fd-architecture,best-practices-researcher --json
# Expected: {"fd-safety":"sonnet","fd-architecture":"sonnet","best-practices-researcher":"haiku"}

ic route dispatch --tier=fast
# Expected: gpt-5.3-codex-spark

ic route table
# Expected: formatted routing table
```

**Step 4: Test lib-routing.sh fast path**

```bash
source /home/mk/projects/Demarch/os/clavain/scripts/lib-routing.sh
routing_resolve_model --phase brainstorm
# Expected: opus (from ic route)
```
