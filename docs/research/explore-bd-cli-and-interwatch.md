# Exploration: bd (Beads) CLI and Interwatch Drift Signals

**Date:** 2026-02-23  
**Scope:** Analysis of beads CLI capabilities (federation, audit, listing) and interwatch drift signal architecture

---

## Part 1: bd (Beads) CLI Analysis

### Installation & Binary

- **Location:** `/home/mk/.local/bin/bd`
- **Type:** ELF 64-bit statically compiled Go binary with debug symbols
- **Source:** Not found locally (appears to be pre-installed binary, not from this repo)

### Key Subcommand Overview

The beads CLI has 50+ subcommands across multiple categories. Relevant findings for federation/cross-database queries:

#### 1. Audit Capability — `bd audit`

**Exists:** YES

**Purpose:**
- Append-only JSONL audit trail at `.beads/interactions.jsonl`
- Records agent interactions and labeling events
- Intended for: auditing agent decisions, dataset generation (SFT/RL fine-tuning)

**Subcommands:**
- `bd audit record` — append interaction entry
- `bd audit label` — add label referencing parent interaction

**Key Flag:** `--actor` — identify actor in audit trail

**Validation Signal:** Audit exists as append-only append infrastructure but is NOT a general validation/audit command (not for checking issue template compliance, etc.)

#### 2. Listing & Querying — `bd list` vs. `bd query` vs. `bd show`

**Pattern:** The CLI DOES support cross-rig queries but NOT via list:

| Command | Cross-Database | How It Works |
|---------|----------------|-------------|
| `bd list` | YES, limited | `--rig gastown` / `--rig gt-` / `--rig gt` suffix flag to query peer rig |
| `bd query` | NO | Query language (field=value, AND/OR/NOT, dates) but NO rig parameter |
| `bd show` | YES | Can display issue details by ID, no explicit rig flag visible in help |
| `bd federation` | YES | `add-peer`, `list-peers`, `remove-peer`, `sync` |

**Key Discovery — bd list --rig Flag:**
```bash
bd list --rig gastown     # Query different rig's database
bd list --rig gt-         # Prefix match (any rig starting with gt-)
bd list --rig gt          # Exact match or contains
```

**bd list Filters (All Single-Rig):**
- `--status` (open, in_progress, blocked, deferred, closed)
- `--label` (AND logic — must have ALL), `--label-any` (OR logic)
- `--label-pattern` (glob), `--label-regex`
- `--priority`, `--type`, `--assignee`, `--parent`
- `--created-after`, `--closed-before`, `--updated-after` (date ranges)
- `--all` (include closed, overrides default filter)
- `--spec` (filter by spec_id prefix)

**Limitation Found:**
- No single `bd list` call can aggregate results across multiple rigs
- Must call `bd list --rig <rig1>`, then `bd list --rig <rig2>` separately and merge
- No `--all-databases` or federated listing flag exists

**bd query Advantages:**
- Supports compound boolean filters: `(status=open OR status=blocked) AND priority<2`
- Field types: `status`, `priority`, `type`, `assignee`, `label`, `created`, `updated`, `closed`, `id`, `spec`, `pinned`, `ephemeral`, `template`, `parent`, `mol_type`
- Date values: relative (`7d`, `24h`), absolute (`2025-01-15`), natural language (`tomorrow`)
- **LIMITATION:** No `--rig` parameter; query is single-rig only

**bd show Behavior:**
- Takes issue ID as argument: `bd show bd-1 bd-5 bd-10`
- Supports `--as-of <commit>` (Dolt only) — time-travel to past state
- Supports `--refs` — reverse lookup (who references this issue?)
- Supports `--short`, `--thread`, `--children`
- **Does NOT show rig in output**, but can show federated peer issues if properly synced

#### 3. Federation & Sync — `bd federation`

**Exists:** YES

**Subcommands:**
- `bd federation add-peer` — register peer town (with optional SQL credentials)
- `bd federation list-peers` — show configured peers
- `bd federation remove-peer` — unregister peer
- `bd federation status` — sync health check
- `bd federation sync` — pull/push updates from peer

**Key Insight:**
- Federation is peer-to-peer via Dolt remotes
- Each "Gas Town" (rig) maintains its own Dolt database
- Updates are shared via git-like remotes
- **Problem:** No automatic cross-rig ID resolution in list/query
  - Must manually call `bd federation sync` first to sync peer data into local database
  - Then `bd list` on LOCAL database includes synced peer issues
  - No way to query peer database directly without local sync

#### 4. What's Missing — Analysis of Gaps

| Need | Available? | How |
|------|-----------|-----|
| Cross-database listing (aggregated) | NO | Must call `bd list --rig <each>` separately |
| Cross-database query (aggregated) | NO | `bd query` has no rig parameter |
| Federated show (ID resolution across rigs) | PARTIAL | `bd show <id>` can find federated issues IF synced locally, but no rig-aware resolution |
| Audit/validation of template compliance | YES, but limited | `bd lint` checks for missing template sections; `bd audit` is append-only interaction log (not validator) |
| Deterministic database selector | NO | `--db` flag exists but requires exact path, not rig name |

### Audit Subcommand Details

**Why `bd audit record` != General Validation:**
- Records interaction: who did what, when, decision context
- Label parent interactions: tag decisions for analysis
- **NOT for validating:** issue templates, mandatory fields, consistency rules

**Example Use Case:**
```bash
bd audit record --actor agent-1 "Closed issue due to duplicate"
bd audit label <parent-id> "false-positive"
```

---

## Part 2: Interwatch Drift Signals Architecture

### Overview

Interwatch is a doc freshness monitoring plugin with:
- 1 skill: `doc-watch`
- 3 commands: `watch.md`, `status.md`, `refresh.md`
- Organized in phases: detect → assess → refresh
- Signal-based scoring with confidence tiers

### Existing Drift Signals

**Total:** 10 signal types

| Signal | Detection Method | Cost | Weight Range | Category |
|--------|-----------------|------|--------------|----------|
| `bead_closed` | `bd list --status=closed` vs. snapshot | Free (bd CLI) | 1-3 | Probabilistic |
| `bead_created` | `bd list --status=open` vs. snapshot | Free (bd CLI) | 1-2 | Probabilistic |
| `version_bump` | `plugin.json` version vs. doc header | Free (file read) | 2-3 | **Deterministic** |
| `component_count_changed` | glob count vs. doc claims | Free (glob) | 2-3 | **Deterministic** |
| `file_renamed` | `git diff --name-status` since doc mtime | Free (git) | 2-3 | Probabilistic |
| `file_deleted` | `git diff --name-status` since doc mtime | Free (git) | 2-3 | Probabilistic |
| `file_created` | `git diff --name-status` since doc mtime | Free (git) | 1-2 | Probabilistic |
| `commits_since_update` | `git rev-list --count` since doc mtime | Free (git) | 1 | Probabilistic |
| `brainstorm_created` | `find docs/brainstorms/ -newer $DOC` | Free (find) | 1 | Probabilistic |
| `companion_extracted` | plugin cache search for new companions | Free (find) | 2-3 | Probabilistic |

**Deterministic vs. Probabilistic:**
- **Deterministic:** Version/count mismatches = **Certain** confidence (doc is objectively wrong)
- **Probabilistic:** Contributing to weighted score; drift is likely but not guaranteed

### How Drift Signals Are Defined

**Location:** Signal registry in 3 places (cascading)

1. **Signal Catalog** — `/interwatch/skills/doc-watch/references/signals.md`
   - Defines signal types, detection methods, weight ranges
   - Not executable; documentation of available signals

2. **Watchables Registry** — Project-specific `config/watchables.yaml`
   - Declarative list: which documents to watch
   - Which signals apply to each document
   - Weights and staleness thresholds per watchable

3. **Bash Library** — `/interwatch/hooks/lib-watch.sh`
   - Implements 10 utility functions for signal detection
   - All prefixed `_watch_*` to avoid namespace collisions
   - Functions: `_watch_file_mtime`, `_watch_plugin_version`, `_watch_file_changes`, `_watch_commits_since`, `_watch_newer_brainstorms`, etc.

### Drift Check Format & Phases

**No single "drift check" file; instead, organized as skill phases:**

```
SKILL.md (orchestrator)
  ├─ phases/detect.md   (Signal evaluation & scoring)
  │  └─ Calls bash functions from lib-watch.sh
  ├─ phases/assess.md   (Confidence tier calculation)
  │  └─ Maps drift_score + staleness → Confidence (Green/Blue/Yellow/Orange/Red)
  └─ phases/refresh.md  (Generator dispatch)
     └─ Routes to interpath (product docs) or interdoc (code docs)
```

**Detection Logic (Example: file_renamed):**
```bash
doc_mtime=$(stat -c %Y "$DOC_PATH" 2>/dev/null || echo 0)
doc_commit=$(git log -1 --format=%H --until="@$doc_mtime" 2>/dev/null || echo "HEAD~20")
git diff --name-status "$doc_commit"..HEAD -- skills/ commands/ agents/ 2>/dev/null
```

### Confidence Tiers

| Score | Staleness | Confidence | Color | Action |
|-------|-----------|------------|-------|--------|
| 0 | < threshold | Green | Current — no action |
| 1-2 | < threshold | Blue | Low drift — report only |
| 3-5 | any | Yellow | Medium drift — suggest via AskUserQuestion |
| 6+ | any | Orange | High drift — auto-refresh + note |
| any | > threshold | Orange | Stale — auto-refresh + note |
| **Deterministic** | any | Red | **Certain** — auto-refresh silently |

### Watchables Registry Format

Not examined in detail, but inferred from skill documentation:
- YAML file with list of documents to monitor
- Each watchable specifies:
  - Document path
  - Applicable signals
  - Weight per signal
  - Staleness threshold (days)
  - Generator plugin (interpath vs. interdoc)

### State Tracking

Per-project state in `.interwatch/` (gitignored):
- `drift.json` — current drift scores per watchable
- `history.json` — refresh history (when, what, confidence tier)
- `last-scan.json` — snapshot of signal counts for delta detection

### How New Signals Are Added

**Process (inferred from architecture):**

1. **Add detection logic** → `hooks/lib-watch.sh` (new `_watch_*` function)
2. **Register signal** → `skills/doc-watch/references/signals.md` (documentation)
3. **Add to watchables** → Project's `config/watchables.yaml` (enable for specific docs)
4. **Update detect phase** → `phases/detect.md` (explain evaluation method)

**Example Addition (hypothetical `file_permissions_changed`):**
```bash
# In lib-watch.sh
_watch_file_perms_changed() {
    git diff --name-status -p <commit>..HEAD -- <path> | grep "^old mode\|^new mode"
}

# In signals.md
| `file_permissions_changed` | git diff mode change | Free (git) | 1-2 | Probabilistic |

# In detect.md
### file_permissions_changed
Compare git mode bits before/after doc mtime cutoff.
```

---

## Summary: Key Findings

### bd CLI

1. **`bd audit` EXISTS** — append-only interaction log, NOT a general validation tool
2. **No `--all-databases` flag** — `bd list --rig <rig>` queries one rig at a time
   - Workaround: loop over rigs, merge results
3. **Federation exists but requires sync** — peer data only queryable after `bd federation sync`
4. **`bd show` can resolve IDs but not rig-aware** — finds federated issues if synced locally
5. **`bd query` does NOT support cross-rig** — single-rig query language only

### Interwatch

1. **10 drift signals defined** — 2 deterministic (version/count), 8 probabilistic (git, beads, files)
2. **Signals are bash library functions** — `/hooks/lib-watch.sh` with `_watch_*` prefix
3. **Declarative watchables registry** — `config/watchables.yaml` enables signals per document
4. **Three phases:** detect (bash functions) → assess (confidence scoring) → refresh (generator dispatch)
5. **State in `.interwatch/`** — `drift.json`, `history.json`, `last-scan.json` (gitignored)
6. **Confidence tiers drive action** — Certain (auto-fix), High (auto-fix+note), Medium (suggest), Low (report)

---

## Recommendations for Future Integration

### If Federated Drift Signals Needed

- **Current limitation:** Interwatch only detects drift in local project
- **Federated approach:** Extend `detect.md` to call `bd federation sync` before `bd list --rig`, then aggregate signal counts across rigs
- **New signal:** `peer_bead_closed` (requires federation awareness)

### If Cross-Database Audit Needed

- **Current limitation:** `bd audit` is append-only, not a validator
- **Approach:** Extend `bd audit label` to include validation tags (e.g., `template-compliant`, `fields-valid`)
- **Alternative:** Use `bd lint` for template validation; pair with audit for decision logging

### If Dynamic Signal Addition Needed

- **Current limitation:** Signals are hardcoded in `lib-watch.sh`
- **Approach:** Load signals from `config/signals.yaml` dynamically, with bash script snippets inline
- **Precedent:** Similar pattern in bd's `formula` subcommand for workflow templates

---

## Files Referenced

**Beads CLI:**
- `/home/mk/.local/bin/bd` — compiled binary (no source in Demarch repo)

**Interwatch Plugin:**
- `/home/mk/projects/Demarch/interverse/interwatch/AGENTS.md` — dev guide
- `/home/mk/projects/Demarch/interverse/interwatch/CLAUDE.md` — quick reference
- `/home/mk/projects/Demarch/interverse/interwatch/skills/doc-watch/SKILL.md` — orchestrator
- `/home/mk/projects/Demarch/interverse/interwatch/skills/doc-watch/phases/detect.md` — signal detection
- `/home/mk/projects/Demarch/interverse/interwatch/skills/doc-watch/phases/assess.md` — confidence scoring
- `/home/mk/projects/Demarch/interverse/interwatch/skills/doc-watch/references/signals.md` — signal catalog
- `/home/mk/projects/Demarch/interverse/interwatch/hooks/lib-watch.sh` — bash signal detection library
- `/home/mk/projects/Demarch/interverse/interwatch/.claude-plugin/plugin.json` — plugin manifest (v0.1.4)

