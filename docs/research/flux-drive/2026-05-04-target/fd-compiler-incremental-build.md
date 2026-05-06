# fd-compiler-incremental-build — Incremental Compilation Review

**Reviewer**: Incremental compiler engineer perspective (TypeScript watch mode, Rust salsa, Roslyn)
**Target**: `/tmp/flux-drive-2026-05-04-target-1777878653.md`
**Date**: 2026-05-04

---

### Findings Index

| Severity | ID | Section | Title |
|----------|-----|---------|-------|
| P1 | IC-01 | Token-efficiency | Per-turn re-orientation burns full cost even when state unchanged |
| P2 | IC-02 | Token-efficiency | Module roadmap generation lacks dirty-bit propagation |
| P2 | IC-03 | Token-efficiency | Flux-drive agent triage not memoized by (target_hash, agent_hash) |
| P2 | IC-04 | Usability | Generated artifacts lack freshness headers for staleness detection |
| P2 | IC-05 | ML-routing | Bead status delta → status view is O(n) not O(delta) |
| P3 | IC-06 | Token-efficiency | Skill-compact manifest pattern exists but not generalized |

**Verdict**: needs-changes

---

### Summary

Sylveste builds clean state every turn — the incremental compilation playbook would call this "full rebuild on every keystroke." The `gen-skill-compact.sh` script already implements a correct salsa-style manifest pattern (SHA256 hashes + check_freshness), but this pattern is isolated to one use case. Key opportunities:

1. **MEMORY.md + hooks fire fully on unchanged state** (P1) — the SessionStart hook runs `bd prime`, `heal-dolt.sh`, etc. on every startup, resume, and clear regardless of whether underlying state changed since last turn.
2. **Module roadmap regeneration is O(n modules)** (P2) — `generate-module-roadmaps.sh` queries beads for ALL modules even when only one bead changed.
3. **Flux-drive agent selection re-runs full triage** (P2) — no memoization by `(target_hash, project_agents_hash)` even when reviewing the same unchanged file twice in a session.

The existing manifest pattern in `scripts/gen-skill-compact.sh:46-90` is the right model to generalize.

---

### Issues Found

#### IC-01 [P1] — Per-turn re-orientation burns full cost even when state unchanged
**Axis**: Token-efficiency

**Discipline reference**: In Rust salsa, database queries are memoized by their inputs — if the input hasn't changed, the cached result is returned instantly. In TypeScript watch mode, file watchers only trigger recompilation for files whose mtimes changed.

**Current state**:
- SessionStart hooks (`.claude/settings.json:12-23`, project settings) fire `bd prime`, `heal-dolt.sh`, `bd stats` on every `startup|resume|clear|compact` event
- MEMORY.md (132 lines, 122KB across topic files) is loaded fully every turn via Claude Code's context loader
- No dirty-bit tracking between turns — the system cannot detect "nothing changed since last tick"

**Evidence**:
```
# From project settings.json:14-19
"hooks": [
  {
    "command": "bash -c 'cd \"$PROJECT_DIR\" && ... bd stats 2>/dev/null | head -1'",
    "type": "command"
  }
]
```

**Proposal**: Implement a session-warm cache file (e.g., `.claude/session-state.json`) with:
- `last_git_sha`: HEAD at last orientation
- `last_bead_mtime`: `.beads/` directory mtime
- `last_memory_hash`: SHA256 of MEMORY.md

On SessionStart, compare current values. If unchanged, emit "Session state unchanged — skipping re-orientation" and exit early. This is the "file watcher" pattern from TypeScript watch mode.

**Estimated savings**: 500-800 tok/turn on idle /loop ticks (based on hook output + bd stats). At 20 ticks/hour in an idle loop, this is 10,000-16,000 tok/hour saved.

**Difficulty**: S (single PR — add session state file, modify SessionStart hook to check it)

**Risk**: Stale state if file watchers miss a change. Mitigate with periodic full re-orientation (every 10 ticks) or on explicit `/refresh`.

---

#### IC-02 [P2] — Module roadmap generation lacks dirty-bit propagation
**Axis**: Token-efficiency

**Discipline reference**: In incremental compilers, dependency graphs track which outputs depend on which inputs. When input A changes, only outputs downstream of A are recomputed — not the entire build.

**Current state**: `interpath/scripts/generate-module-roadmaps.sh:79-173` iterates over ALL detected modules and runs `bd list` queries for each, regardless of which beads changed:

```bash
# Line 86-89 — queries for EVERY module
open_items="$(bd list --status=open 2>/dev/null | grep -i "\b${module}\b" || true)"
in_progress_items="$(bd list --status=in_progress 2>/dev/null | grep -i "\b${module}\b" || true)"
blocked_items="$(bd blocked 2>/dev/null | grep -i "\b${module}\b" || true)"
```

**Proposal**: Add a bead-change event log. When `bd update` or `bd close` runs, append the affected module name to `.beads/changed-modules.log`. Before roadmap generation:
1. Read the change log
2. Only regenerate roadmaps for modules in the log
3. Clear the log after regeneration

Alternatively, compute a manifest hash per module (bead IDs + statuses) and only regenerate when the hash differs from the stored manifest.

**Estimated savings**: With 63 plugins, a single-bead change currently triggers 63 × 4 = 252 `bd list | grep` invocations. With dirty-bit tracking, this drops to 1 × 4 = 4 invocations. ~95% reduction in roadmap regeneration cost.

**Difficulty**: S (single PR — add change log to bd hooks, modify generate-module-roadmaps.sh to read it)

**Risk**: Change log can grow unbounded if generation never runs. Mitigate with periodic full regeneration or log rotation.

---

#### IC-03 [P2] — Flux-drive agent triage not memoized by (target_hash, agent_hash)
**Axis**: Token-efficiency + ML-routing-replacement

**Discipline reference**: In Roslyn, incremental compilation caches semantic analysis by syntax tree hash. Re-analyzing unchanged code returns cached symbols. The salsa pattern: `memo(fn(inputs)) → if inputs unchanged, return cached output`.

**Current state**: `interflux/skills/flux-drive/SKILL.md` Phase 1 runs full agent scoring (Steps 1.2a-c) on every invocation, even when reviewing the same unchanged file multiple times in a session:

```
# Line 211-221 — scoring always recomputed
final_score = base_score(0-3) + domain_boost(0-2) + project_bonus(0-1) + domain_agent(0-1) + tier_bonus(-1 to +1)
```

There's no check for "have I already triaged this exact (target_hash, agent_roster_hash) pair?"

**Proposal**: Implement triage result caching:
1. Compute `target_hash = SHA256(target_file_content)` and `roster_hash = SHA256(sorted(agent_names + agent_mtimes))`
2. Check `.claude/flux-drive-cache/{target_hash}-{roster_hash}.json`
3. If exists and fresh (< 1 hour), skip Phase 1 entirely — load cached triage result
4. If missing or stale, run Phase 1 and write cache

This is the salsa `query` pattern — same inputs → same outputs → skip recomputation.

**Estimated savings**: Phase 1 triage is ~2,000-3,000 tokens (reading target, scoring agents, formatting table). On iterative reviews of the same document (common in /sprint cycles), caching could save 2,000+ tok/review.

**Difficulty**: M (multi-PR — add caching infrastructure to flux-drive, define cache key schema, implement cache invalidation)

**Risk**: Cache can return stale triage if agent definitions change but roster_hash uses wrong inputs. Mitigate by including agent file contents in hash, not just names.

---

#### IC-04 [P2] — Generated artifacts lack freshness headers for staleness detection
**Axis**: Usability + ML-routing-replacement

**Discipline reference**: HTTP caching uses `ETag` and `Last-Modified` headers so clients can detect stale content without re-downloading. Build systems embed input hashes in outputs so downstream consumers can detect drift.

**Current state**: Artifacts generated by interpath (`docs/roadmap.md`, `docs/vision.md`, PRDs) include only a human-readable date:

```markdown
# From generate-module-roadmaps.sh output (line 131-133)
> Auto-generated from beads on ${DATE}. Strategic context: [Project Roadmap](${roadmap_rel})
```

There's no machine-readable freshness header. When `/interpath:propagate` runs, it cannot detect "this roadmap is already fresh" vs "this roadmap needs regeneration."

**Proposal**: Add a frontmatter block to generated artifacts:
```yaml
---
generated_at: 2026-05-04T07:15:00Z
input_hash: abc123...  # SHA256 of beads state at generation time
inputs:
  - .beads/beads.jsonl:def456...
  - CLAUDE.md:789abc...
---
```

Downstream readers can compare `input_hash` against current input state to detect staleness without regenerating.

**Estimated savings**: Eliminates "regenerate just in case" token spend. With 60+ modules, periodic propagate runs could be skipping 50+ unchanged modules.

**Difficulty**: S (single PR — modify interpath generation scripts to emit frontmatter, add hash computation)

**Risk**: Frontmatter parsing complexity. Mitigate by using standard YAML frontmatter that grep/sed can extract.

---

#### IC-05 [P2] — Bead status delta → status view is O(n) not O(delta)
**Axis**: Token-efficiency + ML-routing-replacement

**Discipline reference**: In reactive UI frameworks (React, Svelte), state changes trigger only the affected components to re-render — not the entire DOM. This is "fine-grained reactivity."

**Current state**: `/clavain:status` (clavain/commands/status.md) delegates to `/interpath:interpath-status`, `/interwatch:interwatch-status`, and `/interlock:interlock-status`. Each runs a full query:

```markdown
# From status.md:17-19
For each additional scope, execute the delegated command:
  - `interpath`: `/interpath:interpath-status`
  - `interwatch`: `/interwatch:interwatch-status`
```

When one bead status changes, the entire status view is regenerated. There's no "only show what changed since last status call."

**Proposal**: Track last-status state and emit diffs:
1. Store last status snapshot in `.claude/last-status.json`
2. On `/clavain:status`, compute current state and diff against snapshot
3. Emit only changed sections: `[+] bead-123: open → in_progress` instead of full table

This is the "virtual DOM diffing" pattern — compare old and new, emit minimal updates.

**Estimated savings**: Full status output is 500-800 tokens. Delta output for a single-bead change could be 50-100 tokens — 80% reduction.

**Difficulty**: M (multi-PR — add state snapshot, implement diff logic, modify all status commands to support delta mode)

**Risk**: Delta mode can be confusing if user expects full state. Mitigate with `--full` flag for explicit full regeneration.

---

#### IC-06 [P3] — Skill-compact manifest pattern exists but not generalized
**Axis**: Token-efficiency (infrastructure)

**Discipline reference**: This is an internal observation — the right pattern EXISTS in the codebase but isn't generalized.

**Current state**: `scripts/gen-skill-compact.sh:46-90` implements correct salsa-style freshness checking:

```bash
# Line 46-60 — compute SHA256 manifest of all source files
compute_manifest() {
    local skill_dir="$1"
    local manifest="{}"
    for f in "$skill_dir"/SKILL.md "$skill_dir"/phases/*.md ...; do
        hash=$(sha256sum "$f" | cut -d' ' -f1)
        manifest=$(echo "$manifest" | jq --arg k "$relpath" --arg v "$hash" '. + {($k): $v}')
    done
    echo "$manifest" | jq -S '.'
}

# Line 63-91 — compare current vs saved manifest
check_freshness() {
    local current=$(compute_manifest "$skill_dir")
    local saved=$(cat "$manifest_path")
    if [[ "$current" == "$saved" ]]; then
        echo "FRESH: $skill_dir"
        return 0
    else
        echo "STALE: $skill_dir"
        return 1
    fi
}
```

This is the RIGHT pattern. But it's only used for SKILL-compact.md generation — not generalized to roadmaps, flux-drive triage, or status generation.

**Proposal**: Extract `compute_manifest` and `check_freshness` into a shared library (`lib-freshness.sh`) and apply it to:
- `generate-module-roadmaps.sh` (IC-02)
- `flux-drive` triage cache (IC-03)
- `interpath` artifact generation (IC-04)

**Estimated savings**: Indirect — enables all the other improvements.

**Difficulty**: S (extract existing code into library, update callers)

**Risk**: Low — pattern is already proven to work.

---

### Improvements

1. **Generalize the manifest pattern** — Extract `scripts/gen-skill-compact.sh:46-90` into `lib-freshness.sh` and apply to all artifact generation. This is the highest-leverage change because it enables IC-02, IC-03, and IC-04.

2. **Add session-warm mode** — Implement `.claude/session-state.json` with git SHA, bead mtime, and memory hash. SessionStart hooks check this file and skip re-orientation if unchanged. This directly addresses the P1 finding (IC-01).

3. **Implement flux-drive triage cache** — Add `.claude/flux-drive-cache/` with (target_hash, roster_hash) keyed JSON files. Cache TTL of 1 hour. This addresses the iterative-review token waste in /sprint cycles.

4. **Add freshness headers to generated artifacts** — Modify interpath scripts to emit YAML frontmatter with `input_hash`. Downstream consumers can detect staleness without regenerating.

5. **Consider ML-based staleness prediction** — For IC-05 (delta status), an embedding-based classifier could predict "likely changed since last status" based on recent commit messages and bead activity. This fits Axis 3 (ML-routing-replacement) — replace LLM-based status regeneration with a cheap classifier that predicts "regenerate: yes/no."

---

### Dependency Graph (MEMORY.md example)

```
MEMORY.md
    ↓ (read by)
Claude Code context loader
    ↓ (triggers)
CLAUDE.md mentions check
    ↓ (triggers)
/interpath:propagate roadmaps
    ↓ (regenerates)
docs/roadmap.md (all 60+ modules)
```

When MEMORY.md changes, the entire downstream graph re-executes. With dirty-bit tracking:

```
MEMORY.md (hash: abc → def)
    ↓ (diff: +1 line in "Active Projects")
Only regenerate roadmaps for modules mentioned in diff
    ↓
1 roadmap regenerated (not 60)
```

---

### Quantified Over-Invalidation Cost

| Trigger | Current Cost | With Dirty-Bit | Savings |
|---------|-------------|----------------|---------|
| SessionStart (idle) | 500-800 tok | 50-100 tok | 450-700 tok/turn |
| `/interpath:propagate` | 60 modules × 300 tok = 18,000 tok | 1-3 modules × 300 tok = 900 tok | ~17,000 tok |
| `/flux-drive` same file | 2,500 tok (full Phase 1) | 100 tok (cache hit) | 2,400 tok |
| `/clavain:status` | 800 tok | 100 tok (delta) | 700 tok |

At 20 /loop ticks/hour on an idle session: **9,000-14,000 tok/hour** saved from SessionStart alone.

---

<!-- flux-drive:complete -->
