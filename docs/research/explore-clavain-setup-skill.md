# Clavain Setup Skill and Ecosystem-Only Plugins — Complete Analysis

**Date:** 2026-02-23  
**Analysis Scope:** clavain:setup command, modpack-install.sh automation, ecosystem-only plugin classification (interlock, interphase)

---

## 1. The clavain:setup Command

### Location & Purpose

**File:** `/home/mk/projects/Demarch/os/clavain/commands/setup.md`

The `clavain:setup` command is a comprehensive bootstrap workflow that transforms a fresh Claude Code install into a fully-configured Clavain engineering rig. It runs in phases:

| Phase | Purpose | Key Outputs |
|-------|---------|------------|
| **Step 1** | Verify Clavain is installed | Confirms plugin presence in cache |
| **Step 2** | Install required & recommended plugins | Auto-installs via `modpack-install.sh` |
| **Step 2b** | Present optional plugins | User selects which to install via AskUserQuestion |
| **Step 3** | Disable conflicting plugins | Removes competing review/workflow plugins |
| **Step 4** | Verify MCP servers | context7, qmd, Oracle health checks |
| **Step 5** | Initialize beads | Offers `bd init` for git-native issue tracking |
| **Step 6** | Final verification | Python script reads settings.json, verifies state |
| **Step 7** | Summary & next steps | Reports counts, suggests demo commands |

### Invocation

```bash
/clavain:setup                        # Full setup
/clavain:setup --check-only           # Verify without changes
/clavain:setup --scope=interlock      # Intermute service only
/clavain:setup --scope=clavain        # Full Clavain modpack (default)
/clavain:setup --scope=all            # Force both interlock + clavain
```

---

## 2. The Modpack Install Architecture

### The Problem It Solves

Prior to this design:
- `setup.md` contained 20+ hardcoded `claude plugin install` commands
- Users had to copy-paste each command manually
- Plugin lists in setup.md and `agent-rig.json` could diverge (duplication = staleness risk)
- No automation of optional plugin discovery or conflict management

### Design Pattern: agent-rig.json as Single Source of Truth

**File:** `/home/mk/projects/Demarch/os/clavain/agent-rig.json`

The manifest defines all plugins in hierarchical categories:

```json
{
  "plugins": {
    "core": {
      "source": "clavain@interagency-marketplace"
    },
    "required": [
      { "source": "context7@claude-plugins-official", "description": "..." },
      { "source": "explanatory-output-style@claude-plugins-official", "description": "..." }
    ],
    "recommended": [
      { "source": "interdoc@interagency-marketplace", "description": "AGENTS.md generation" },
      { "source": "interflux@interagency-marketplace", "description": "Multi-agent review engine" },
      { "source": "interphase@interagency-marketplace", "description": "Phase tracking, gates, discovery" },
      { "source": "interlock@interagency-marketplace", "description": "Multi-agent file coordination" },
      // ... 10 more recommended
    ],
    "optional": [
      { "source": "interfluence@interagency-marketplace", "description": "Voice profile adaptation" },
      // ... 11 more optional
    ],
    "infrastructure": [
      { "source": "gopls-lsp@claude-plugins-official", "description": "Go language server" },
      // ... 3 more language servers
    ],
    "conflicts": [
      { "source": "code-review@claude-plugins-official", "reason": "Duplicates Clavain review agents" },
      // ... 7 more conflicts
    ]
  }
}
```

### The Automation Script: modpack-install.sh

**File:** `/home/mk/projects/Demarch/os/clavain/scripts/modpack-install.sh`

A bash script that reads `agent-rig.json` at runtime and automates the entire install flow.

#### Usage

```bash
scripts/modpack-install.sh [--dry-run] [--check-only] [--quiet] [--category=CATEGORY]
```

**Categories:**
- `core` — Install the Clavain core plugin
- `required` — Install must-have plugins (context7, explanatory-output-style)
- `recommended` — Install recommended companions (interdoc, interflux, interphase, interlock, intercheck, etc.)
- `optional` — Detect available optional plugins (not auto-installed, only reported)
- `infrastructure` — Language servers (gopls, pyright, typescript-lsp, rust-analyzer)
- `conflicts` — Disable conflicting plugins (code-review, pr-review-toolkit, etc.)
- `all` — Run full workflow in sequence

**Flags:**
- `--dry-run` / `--check-only` — Show what would change without installing
- `--quiet` — Suppress stderr progress, emit JSON only
- `--category=X` — Restrict to specific category

#### Detection Logic

For each plugin, the script:

1. **Check if installed:** Scans `~/.claude/plugins/cache/<marketplace>/<name>/plugin.json`
2. **Check if disabled:** Reads `~/.claude/settings.json` for `enabledPlugins[plugin_source] = false`
3. **Install or skip:** Runs `claude plugin install <source>` or reports already-present
4. **Track results:** Accumulates installed, already_present, failed arrays
5. **For conflicts:** Runs `claude plugin disable <source>` and tracks disabled array

#### JSON Output

```json
{
  "installed": [
    "interdoc@interagency-marketplace",
    "interflux@interagency-marketplace",
    "interphase@interagency-marketplace"
  ],
  "already_present": ["clavain@interagency-marketplace"],
  "failed": [],
  "disabled": ["code-review@claude-plugins-official"],
  "already_disabled": ["pr-review-toolkit@claude-plugins-official"],
  "optional_available": [
    "interfluence@interagency-marketplace",
    "interject@interagency-marketplace",
    "internext@interagency-marketplace",
    "interstat@interagency-marketplace",
    "interkasten@interagency-marketplace",
    "interlens@interagency-marketplace",
    "intersearch@interagency-marketplace",
    "interserve@interagency-marketplace",
    "interpub@interagency-marketplace",
    "tuivision@interagency-marketplace",
    "intermux@interagency-marketplace"
  ]
}
```

**In dry-run mode:** Returns `would_install` instead of `installed`.

#### Integration with setup.md

setup.md calls the script in three places:

1. **Step 2 (Required):** `result=$("$INSTALL_SCRIPT" --quiet)`
   - Parses JSON, reports installed count + names
   - Reports already_present count
   - Reports any failed plugins (with warnings)

2. **Step 2b (Optional):** `optional=$("$INSTALL_SCRIPT" --dry-run --quiet --category=optional | jq -r '.optional_available[]')`
   - Gets list of available optional plugins
   - Presents via AskUserQuestion (multi-select)
   - For each selected plugin: `claude plugin install <selected-plugin>`

3. **Step 3 (Conflicts):** Already handled by Step 2
   - Script disables conflicts automatically
   - setup.md just reports what was disabled

#### Fallback Mechanism

If `jq` is unavailable or script fails, setup.md still has inline documented lists (marked with `<!-- agent-rig:begin/end -->` comments) for manual guidance.

---

## 3. Ecosystem-Only Plugins: interlock & interphase

### Conceptual Classification

From the dual-mode plugin architecture document (`docs/brainstorms/2026-02-20-dual-mode-plugin-architecture-brainstorm.md`), plugins are assessed for **standalone value** (how useful they are alone) vs **integrated value** (how they enhance the ecosystem):

| Plugin | Standalone % | Classification | Reason |
|--------|-------------|-----------------|--------|
| tldr-swinton | 100% | Standalone | Token-efficient code context works perfectly alone |
| interfluence | 95% | Standalone | Voice profile adaptation is generally useful |
| interflux | 90% | Standalone | Multi-agent code review works without ecosystem |
| interject | 70% | Standalone | Ambient discovery works, findings less useful without beads |
| interwatch | 75% | Standalone | Doc drift detection useful alone |
| interstat | 70% | Standalone | Token measurement works without sprint context |
| **interline** | 40% | Borderline | Statusline renderer, limited value without bead context |
| **interlock** | **30%** | **Ecosystem-Only** | File coordination requires intermute service (not standalone) |
| **interphase** | **20%** | **Ecosystem-Only** | Phase tracking requires beads for state storage |

### interlock: File Reservation & Agent Coordination

**Location:** `/home/mk/projects/Demarch/interverse/interlock/`

**plugin.json:**
```json
{
  "name": "interlock",
  "version": "0.2.2",
  "description": "MCP server for intermute file reservation and agent coordination. 11 tools: reserve, release, conflict check, messaging, agent listing, negotiation. Companion plugin for Clavain.",
  "mcpServers": {
    "interlock": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERMUTE_SOCKET": "/var/run/intermute.sock",
        "INTERMUTE_URL": "http://127.0.0.1:7338"
      }
    }
  },
  "skills": [
    "./skills/conflict-recovery",
    "./skills/coordination-protocol"
  ],
  "commands": [
    "./commands/join.md",
    "./commands/leave.md",
    "./commands/setup.md",
    "./commands/status.md"
  ]
}
```

**Why Ecosystem-Only:**

1. **Hard dependency on intermute** — The MCP server wraps `intermute` HTTP API or Unix socket. Without intermute running, all 11 tools fail immediately. Intermute is a separate service (`core/intermute/`) not auto-started.

2. **No standalone value** — File reservation means nothing without multi-agent coordination. A single user has no one to coordinate with. The features (conflict detection, messaging, negotiation) only work when multiple agents are managing files.

3. **Constellation dependency** — interlock requires:
   - Intermute service running (`core/intermute/`)
   - Clavain or another agent dispatcher
   - Pre-edit hook configured to use interlock's PreToolUse:Edit hook
   - Multiple agents in the same project to have conflicts worth resolving

4. **Marketplace confusion risk** — If a user installs interlock alone, they get a non-functional plugin with cryptic "connection refused" errors. The plugin marketplace listing can't adequately explain this without describing the entire Intercore architecture.

**How It's Delivered:**

- **Not published to standalone marketplace** — Listed only in `agent-rig.json` under `recommended`
- **Bundled with Clavain modpack** — Installed automatically by `modpack-install.sh` alongside other companions
- **Optional in marketplace, but auto-installed with Clavain** — Users who install Clavain get interlock automatically; standalone users don't see it

### interphase: Phase Tracking & Lifecycle Gates

**Location:** `/home/mk/projects/Demarch/interverse/interphase/`

**plugin.json:**
```json
{
  "name": "interphase",
  "version": "0.3.3",
  "description": "Phase tracking, gate validation, and work discovery for the Beads issue tracker. Companion plugin for Clavain — adds lifecycle state management on top of the core beads plugin.",
  "skills": [
    "./skills/beads-workflow"
  ]
}
```

**Why Ecosystem-Only:**

1. **Hard dependency on beads** — Phase tracking without beads has nowhere to store state. The library functions in `hooks/lib-phase.sh`, `hooks/lib-gates.sh` require beads as the state store. Without beads, you can display phase but can't persist it.

2. **No independent value** — A user installing interphase alone gets a skill that talks about phases but has no backing data structure. Gate enforcement requires both interphase (the rules) and beads (the storage).

3. **Constellation dependency** — interphase requires:
   - Beads (`bd` command available)
   - Clavain (for bead creation workflows, though interphase works with raw beads)
   - Sprint state (optional but intended use case)
   - Optional: Intercore for phase-driven gate enforcement

4. **Marketplace confusion** — A user installing interphase sees "phase tracking" but has no way to actually track phases in isolation. They need to understand the full Clavain ecosystem to see why phase tracking matters.

**Integration Points:**

- **Beads state storage** — Phase data lives in `.beads/` directory (git-native)
- **Statusline integration** — interline reads phase state from sideband files written by interphase
- **Clavain shim pattern** — Clavain's hooks source interphase's library functions (`lib-phase.sh`, `lib-gates.sh`)

**How It's Delivered:**

- **Not published to standalone marketplace**
- **Bundled with Clavain modpack** — Installed by `modpack-install.sh` automatically
- **Soft dependency in recommended list** — always installed with Clavain, treating it as essential infrastructure for the engineering rig

---

## 4. Required & Recommended Plugin Categories

### Required Plugins (must have; installed in Step 2)

```
context7@claude-plugins-official          → Runtime doc fetching via MCP
explanatory-output-style@claude-plugins-official  → Educational output formatting
```

### Recommended Plugins (should have; auto-installed in Step 2, skip available)

**Core engineering:**
- `interdoc@interagency-marketplace` — AGENTS.md generation
- `interflux@interagency-marketplace` — Multi-agent review engine (flux-drive)
- `interphase@interagency-marketplace` — Phase tracking, gates, discovery ★ ECOSYSTEM-ONLY
- `interline@interagency-marketplace` — Dynamic statusline renderer
- `interpath@interagency-marketplace` — Product artifact generation
- `interwatch@interagency-marketplace` — Doc freshness monitoring
- `interlock@interagency-marketplace` — Multi-agent file coordination ★ ECOSYSTEM-ONLY
- `intercheck@interagency-marketplace` — Code quality guards and session health

**Tools & analytics:**
- `tldr-swinton@interagency-marketplace` — Token-efficient code context (MCP)
- `tool-time@interagency-marketplace` — Tool usage analytics

**Infrastructure & development:**
- `interslack@interagency-marketplace` — Slack integration
- `interform@interagency-marketplace` — Design patterns and visual quality
- `intercraft@interagency-marketplace` — Agent-native architecture patterns
- `interdev@interagency-marketplace` — MCP CLI and developer tooling
- `agent-sdk-dev@claude-plugins-official` — Agent SDK development tools
- `plugin-dev@claude-plugins-official` — Plugin development tools
- `serena@claude-plugins-official` — Semantic coding tools
- `security-guidance@claude-plugins-official` — Security best practices

### Optional Plugins (presented to user in Step 2b)

```
interfluence           → Voice profile and style adaptation
interject             → Ambient discovery and research engine (MCP)
internext             → Work prioritization and tradeoff analysis
interstat             → Token efficiency benchmarking
interkasten           → Notion sync and documentation
interlens             → Cognitive augmentation lenses (FLUX podcast, MCP)
intersearch           → Shared embedding and Exa search library
interserve            → Codex spark classifier and context compression (MCP)
interpub              → Plugin publishing automation
tuivision             → TUI automation and visual testing (MCP)
intermux              → Agent activity visibility and tmux monitoring (MCP)
```

### Conflict List (disabled in Step 3)

```
code-review@claude-plugins-official           → Duplicates Clavain review agents
pr-review-toolkit@claude-plugins-official     → Duplicates Clavain PR review
code-simplifier@claude-plugins-official       → Duplicates simplicity reviewer
commit-commands@claude-plugins-official       → Duplicates commit workflow
feature-dev@claude-plugins-official           → Duplicates feature dev workflow
claude-md-management@claude-plugins-official  → Conflicts with doc management
frontend-design@claude-plugins-official       → Conflicts with design agents
hookify@claude-plugins-official               → Conflicts with hook management
```

---

## 5. MCP Servers & Infrastructure

### Declared MCP Servers

**context7** (HTTP)
```json
{
  "type": "http",
  "url": "https://mcp.context7.com/mcp",
  "description": "Runtime documentation fetching"
}
```
Used by Clavain for real-time doc lookups during code review.

**qmd** (stdio, optional)
```json
{
  "type": "stdio",
  "command": "qmd",
  "args": ["mcp"],
  "description": "Local semantic search engine"
}
```
If installed, provides semantic search across project documentation.

### Tools (Declarative, Optional)

| Tool | Install | Check | Description |
|------|---------|-------|-------------|
| oracle | `npm install -g @steipete/oracle` | `command -v oracle` | Cross-AI review via GPT-5.2 Pro |
| codex | `npm install -g @openai/codex` | `command -v codex` | OpenAI's coding agent (dispatch) |
| beads | `npm install -g @steveyegge/beads` | `command -v bd` | Git-native issue tracking |
| qmd | `go install github.com/tobi/qmd@latest` | `command -v qmd` | Semantic search across docs |

---

## 6. Verification Script (Step 6)

The setup command runs a Python script that reads `~/.claude/settings.json` to verify the final state:

**Checks:**
1. **Required plugins enabled** — All 20 plugins in the required list must be present or explicitly enabled
2. **Conflicts disabled** — All 8 conflict plugins must be explicitly set to `false`
3. **MCP servers present** — context7 found, qmd status reported
4. **Companions present** — codex dispatch, interline, oracle, interlock registration, beads config

**Output format:**
```
=== Required Plugins ===
  agent-sdk-dev@claude-plugins-official: enabled
  clavain@interagency-marketplace: enabled
  context7@claude-plugins-official: enabled
  ... (20 total)
  (20/20 enabled)

=== Conflicting Plugins ===
  code-review@claude-plugins-official: disabled
  ... (8 total)
  (8/8 disabled)

=== MCP Servers ===
context7: OK
qmd: installed

=== Companions ===
codex dispatch: OK
interline: installed
oracle: installed
interlock: installed
beads: configured
```

---

## 7. Architecture Insights

### 1. **Modpack as Opinionated Collection**

The "Clavain modpack" is:
- All plugins listed in `agent-rig.json` (required + recommended)
- 20+ companion plugins designed to work together
- NOT a monolithic mega-plugin; each is still independent
- Installed as a coordinated set, verified as a unit
- Curated to avoid conflicts and duplication

### 2. **Ecosystem-Only as Non-Publishing Category**

"Ecosystem-only" means:
- Plugin is essential to the Clavain ecosystem
- Plugin has near-zero standalone value (< 50%)
- Plugin is auto-installed with the modpack (visible to Clavain users)
- Plugin is NOT published to the standalone marketplace
- User confusion prevented by not offering it as a standalone choice

### 3. **Single Source of Truth Pattern**

- `agent-rig.json` is the **canonical manifest** of all plugins
- `scripts/modpack-install.sh` reads it at runtime
- `commands/setup.md` points to the script, not hardcoded lists
- Inline lists in setup.md are fallback documentation only
- Plugin categories update agent-rig.json only → automatic sync

### 4. **Automated Conflict Management**

Rather than warn users about conflicts, the setup:
1. Automatically disables conflicting plugins
2. Reports what was disabled
3. Explains why (feature duplication)
4. User can manually re-enable if they choose

---

## 8. File Manifest

| File | Purpose |
|------|---------|
| `os/clavain/commands/setup.md` | Main setup command (7-step workflow) |
| `os/clavain/agent-rig.json` | Canonical plugin manifest (core/required/recommended/optional/infrastructure/conflicts) |
| `os/clavain/scripts/modpack-install.sh` | Automation script (reads agent-rig.json, installs/detects/disables) |
| `interverse/interlock/.claude-plugin/plugin.json` | Interlock plugin definition (MCP server, commands) |
| `interverse/interphase/.claude-plugin/plugin.json` | Interphase plugin definition (skills) |
| `docs/plans/2026-02-23-iv-frqh-modpack-auto-install.md` | Original modpack design spec |
| `docs/brainstorms/2026-02-20-dual-mode-plugin-architecture-brainstorm.md` | Ecosystem-only classification rationale |

---

## 9. Key Design Decisions (Do Not Re-Ask)

1. **Ecosystem-only plugins are bundled, not marketplace-published** — Prevents misleading listings and user confusion
2. **agent-rig.json is single source of truth** — No duplication between manifest and setup.md docs
3. **Automation via external script** — Allows testing, versioning, and runtime updates
4. **Dry-run mode for setup verification** — `--check-only` flag lets users preview changes
5. **Fallback inline documentation** — If script unavailable, setup.md provides manual guidance
6. **Scoped installation** — `--scope=interlock|clavain|all` lets users install modpack or just intermute service

---

## 10. Usage Examples

### Fresh Install Setup
```bash
/clavain:setup
# → Installs required + recommended plugins
# → Asks which optional plugins to install
# → Disables conflicts
# → Verifies MCP servers
# → Initializes beads (optional)
# → Reports summary
```

### Verify Without Changes
```bash
/clavain:setup --check-only
# → Same flow as above, but:
# → Shows what WOULD be installed
# → Makes no actual changes
# → Useful for audit/troubleshooting
```

### Intermute Service Only
```bash
/clavain:setup --scope=interlock
# → Installs intermute service
# → Registers interlock plugin
# → Verifies socket/HTTP connectivity
# → Skips full Clavain modpack
```

### Repair Existing Setup
```bash
/clavain:setup
# → If run on already-configured system:
# → Skips already-installed plugins
# → Repairs missing ones
# → Updates disabled conflicts if they were re-enabled
# → Full idempotent repair
```

---

## Conclusion

The Clavain setup skill implements a sophisticated modpack installation pattern that:

1. **Automates away manual configuration** via `modpack-install.sh` driven by `agent-rig.json`
2. **Manages ecosystem-only plugins** (interlock, interphase) by bundling them with Clavain rather than publishing standalone
3. **Provides fallback mechanisms** (inline docs) when automation unavailable
4. **Enables verification workflows** (`--check-only`) for auditing configuration drift
5. **Prevents conflicts automatically** rather than requiring user intervention

This is a reference pattern for how to manage complex plugin ecosystems at scale, especially when plugins have hard dependencies on each other or shared services (intermute, beads).
