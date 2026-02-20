# Dual-Mode Plugin Architecture

How Interverse modules serve two audiences — standalone Claude Code users and integrated Clavain/Intercore users — without degrading either experience.

## What We're Building

An architectural pattern and supporting infrastructure that lets each Interverse plugin work as a **standalone Claude Code plugin** (core features, genuinely useful alone) while also being a **power module** in the integrated ecosystem (phase tracking, cross-plugin coordination, sprint lifecycle, bead management, kernel events).

Plugins are ecosystem-aware: they know they're part of Interverse, suggest companions, and declare their integration surface. But their core value prop never depends on the ecosystem.

## Why This Approach

### The Tension

Today, every plugin uses ad-hoc fail-open guards (`command -v bd || return 0`, `is_joined || exit 0`, `[[ -n "$INTERMUTE_AGENT_ID" ]] || exit 0`). This works — no plugin crashes without dependencies. But it creates four compounding problems:

1. **Feature duplication** — 20+ plugins each re-implement the same guard patterns, bead query helpers, phase tracking stubs, and degradation logic. The same 15-30 lines of shell appear in every `lib.sh`.

2. **Upgrade friction** — When intercore evolves (E3 hook cutover, E6 rollback), every companion plugin's integration layer needs updating. The blast radius of a kernel change is proportional to the companion count.

3. **Discoverability gap** — A user installs interflux and gets code reviews. They don't know that installing interphase would give them phase tracking, or that interwatch would auto-trigger reviews on drift. The standalone experience silently lacks capabilities the user doesn't know exist.

4. **Testing complexity** — Each plugin must be tested in both standalone mode AND integrated mode AND various partial-integration states (beads but no ic, ic but no Clavain, etc.). The matrix grows with every new integration point.

### Design Constraints

- **Integrated-first** — The Interverse ecosystem is the primary product. Standalone is a gateway.
- **Standalone must be genuinely useful** — Not a demo version. A user who installs interflux alone should get real code reviews, not a crippled experience.
- **Ecosystem-aware** — Plugins know about Interverse. They suggest companions, declare integration surfaces, and participate in discovery.
- **Per-plugin calibration** — Some plugins are 95% standalone (tldr-swinton). Others are 30% standalone (interlock). The architecture must accommodate this range.

## Key Decisions

### 1. The Three-Layer Plugin Model

Every plugin has three conceptual layers:

**Layer 1: Standalone Core** — The plugin's primary value prop. Works with zero external dependencies. This is what a marketplace user gets.
- interflux: multi-agent code review
- interwatch: doc drift detection + scoring
- tldr-swinton: token-efficient code context
- interlock: file reservation tracking (local mode, no intermute)
- interstat: token usage measurement

**Layer 2: Ecosystem Integration** — Lights up when companions or ic/beads are detected. Adds cross-cutting capabilities.
- Phase tracking (interphase)
- Bead lifecycle (beads)
- Sprint state (intercore runs)
- Cross-plugin events (kernel event bus)
- Companion discovery + nudges

**Layer 3: Orchestrated Mode** — Full Clavain integration. The plugin participates in sprint workflows, gate enforcement, auto-advance, and multi-agent coordination.
- Sprint skill routing
- Quality gate enforcement
- Agent dispatch and tracking
- Checkpoint recovery
- Session handoff

### 2. Integration Manifest (plugin.json Extension)

Add an `"integration"` section to plugin.json that declares the plugin's ecosystem surface:

```json
{
  "integration": {
    "ecosystem": "interverse",
    "standalone_features": [
      "Multi-agent code review (fd-architecture, fd-quality, fd-correctness, fd-safety)",
      "Document review with automatic agent triage",
      "Research orchestration with parallel agents"
    ],
    "integrated_features": [
      { "feature": "Phase tracking on review completion", "requires": "interphase" },
      { "feature": "Sprint gate enforcement", "requires": "intercore" },
      { "feature": "Bead-linked review findings", "requires": "beads" },
      { "feature": "Auto-review on doc drift", "requires": "interwatch" }
    ],
    "companions": {
      "recommended": ["interphase", "interwatch"],
      "optional": ["intercore", "interstat"]
    }
  }
}
```

This serves three purposes:
- **Discoverability**: tooling (marketplace, `/doctor`, session-start) can read this and suggest missing companions
- **Documentation**: users see what they gain from each companion
- **Testing**: the integration matrix is explicit and enumerable

### 3. Shared Integration SDK (interbase)

A lightweight shell library (NOT a plugin — a shared script vendored into each plugin at publish time) that provides:

```bash
# interbase.sh — vendored into each plugin's hooks/ directory

# --- Guards ---
ib_has_ic()    { command -v ic &>/dev/null; }
ib_has_bd()    { command -v bd &>/dev/null; }
ib_has_companion() { [[ -d "${HOME}/.claude/plugins/cache/"*"/$1/"* ]] 2>/dev/null; }

# --- Ecosystem context ---
ib_ecosystem_file() { echo "${HOME}/.clavain/ecosystem.json"; }
ib_in_ecosystem()   { [[ -f "$(ib_ecosystem_file)" ]]; }
ib_get_bead()       { echo "${CLAVAIN_BEAD_ID:-}"; }
ib_in_sprint()      { [[ -n "${CLAVAIN_BEAD_ID:-}" ]] && ib_has_ic && ic run current --project=. &>/dev/null; }

# --- Phase tracking (no-op without interphase) ---
ib_phase_set() {
    local bead="$1" phase="$2" reason="${3:-}"
    ib_has_bd || return 0
    bd set-state "$bead" "phase=$phase" >/dev/null 2>&1 || true
}

# --- Nudges ---
ib_nudge_companion() {
    local name="$1" benefit="$2"
    ib_has_companion "$name" && return 0
    echo "[interverse] Tip: install $name for $benefit" >&2
}

# --- Event emission (no-op without ic) ---
ib_emit_event() {
    local run_id="$1" event_type="$2" payload="${3:-'{}'}"
    ib_has_ic || return 0
    ic events emit "$run_id" "$event_type" --payload="$payload" >/dev/null 2>&1 || true
}
```

**Why vendored, not a plugin dependency:**
- No install-order problem — the file ships inside each plugin
- Version-locked to the plugin's release — no compatibility matrix
- Updated via `interbump` at publish time (pulls latest interbase.sh from a canonical location)
- Standalone users never know it exists — it's just an internal implementation file

**Why not a separate plugin:**
- Claude Code has no plugin dependency resolution
- A separate plugin adds install friction for standalone users
- Vendoring is the npm/Go pattern for this exact problem

### 4. Companion Nudge Protocol

When a plugin detects it could do more with a missing companion, it emits a one-time nudge:

```
[interverse] interflux works standalone, but install interphase for automatic phase tracking after reviews.
```

Rules:
- Nudge once per session, not per invocation
- Only nudge for `recommended` companions (from integration manifest)
- Nudge via stderr (hook output), never block workflow
- Track nudge state in a session temp file to avoid repeats

### 5. Testing Architecture

The integration manifest enables a standardized test matrix:

```bash
# test-standalone.sh — runs in CI with NO ecosystem tools installed
# Verifies: all standalone_features work, no errors from missing deps

# test-integrated.sh — runs with full ecosystem
# Verifies: all integrated_features activate correctly

# test-degradation.sh — runs with partial ecosystem (each companion individually)
# Verifies: each integration point degrades gracefully when its specific companion is absent
```

The `interbase.sh` guards are the single point of failure isolation — if they work correctly, all plugins degrade correctly. Test interbase once, trust it everywhere.

### 6. Per-Plugin Standalone Assessment

| Plugin | Standalone % | Core Value (standalone) | Power Features (integrated) |
|--------|-------------|------------------------|----------------------------|
| tldr-swinton | 100% | Token-efficient code context | None needed |
| interflux | 90% | Multi-agent code review | Phase tracking, sprint gates, bead-linked findings |
| interwatch | 75% | Doc drift detection + scoring | Auto-refresh via interpath, bead filing |
| interfluence | 95% | Voice profile adaptation | Session context from Clavain |
| interject | 90% | Ambient discovery + research | Bead creation for findings |
| interstat | 70% | Token usage measurement | Sprint budget integration, ic token writeback |
| interlock | 30% | Local file tracking | Multi-agent coordination via intermute |
| interphase | 20% | Phase state display | Gate enforcement, sprint integration, Clavain shims |
| interline | 40% | Basic statusline | Bead context, phase display, agent count |

Plugins below 50% standalone need work to raise their standalone value prop. interlock should have a meaningful local-only mode (track your own file edits across sessions, even without coordination). interphase should provide lightweight phase tracking even without beads.

## Open Questions

1. **Should interbase.sh be a separate repo or live in a canonical location within Interverse?** Leaning toward `infra/interbase/` in the monorepo, with `interbump` copying it into each plugin at publish time.

2. **How aggressive should nudges be?** A single stderr line per session is unobtrusive. Should session-start hooks also emit a richer "ecosystem status" showing what's installed vs available?

3. **Should the integration manifest be a Claude Code plugin.json extension or a separate file?** plugin.json extension is cleaner but risks schema conflicts with future Claude Code updates. A separate `integration.json` is safer but adds file bloat.

4. **How do we handle the interlock problem?** Interlock at 30% standalone is a poor marketplace experience. Options: (a) don't publish it standalone, (b) build a meaningful local-only mode, (c) mark it as "ecosystem-only" in the marketplace.

5. **Version pinning for vendored interbase.sh** — When a plugin ships interbase.sh v1.2 but the ecosystem has moved to v1.5, do we handle version skew? Or is "each plugin ships what it ships" sufficient?
