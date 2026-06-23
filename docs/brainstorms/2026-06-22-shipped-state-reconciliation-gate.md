---
artifact_type: brainstorm
bead: sylveste-sk5s
stage: discover
status: FOR REVIEW — design draft, not implemented
relates: [sylveste-b1ha, sylveste-46s, sylveste-9gn9, sylveste-r3jf]
author: design-draft agent (backlog run a67c894c)
---

# Design Draft: Shipped-State Reconciliation Gate for /clavain:strategy and PRD Authoring

> **This is a FOR-REVIEW design draft.** No code is changed. It proposes a mechanical gate
> and lists the decisions the human must confirm before any implementation. The trigger bead
> is `sylveste-sk5s` (P1).

## Problem

When `/clavain:strategy` (or freehand PRD authoring) designs a new module, it does not
mechanically check whether an **in-tree epic — open OR shipped — already covers the same
architectural territory**. The result is parallel implementations and risk to sunk shipped
work. This has now happened twice:

**The canonical miss (2026-04-27).** PRD `docs/prds/2026-04-21-persona-lens-ontology.md`
(epic `sylveste-b1ha`) proposed a brand-new `ontology-queries` module on **Apache AGE /
Postgres / Cypher** for a persona/lens ontology graph. It did this without cross-referencing
`interweave` (epic `sylveste-46s`, status `open`, 87% shipped) — a catalog-of-catalogs
ontology layer **already implementing the same architecture** on SQLite + named query
templates. The overlap was caught only *after* the PRD shipped, in reconciliation bead
`sylveste-9gn9`, whose verdict (`docs/research/2026-04-27-lattice-reconciliation.md`) was
**SUBSUME**: drop AGE/Cypher, rename interweave → lattice, register persona/lens as type-family
extensions. The reconciliation cut the effort estimate from ~10.5 weeks to ~6 weeks (verified
in the reconciliation doc's effort-delta table) — i.e. ~40% of the planned epic was redundant
or misdirected and would have been built before anyone noticed.

This is the second hit of a documented failure pattern. The bead cites two memory feedback
files (`feedback_reanchor_to_pivot_memory.md`, `feedback_docs_match_codebase_not_memory.md`).
**Note for reviewer:** neither file currently exists at
`~/.claude/projects/-Users-sma-projects-Sylveste/memory/` (verified 2026-06-22). The pattern
is real and documented in the reconciliation/reflection artifacts on disk; the memory-file
references are stale or were never written. (Open question OQ-7 below.)

### Why the existing "Phase 0: Prior Art Check" does not catch this

`/clavain:strategy` already has a Phase 0 (verified at
`/Users/sma/projects/Sylveste/os/Clavain/commands/strategy.md:45-83`). But its design target
is **external** reuse, not internal overlap:

- Step 1 greps `docs/research/assess-*.md` for "adopt"/"port-partially" verdicts — these are
  assessments of *external* repos, written only when an external candidate was already found.
- Step 2 is `bd search "<keywords>"` — but it is unscoped, has no status filter for shipped
  epics, and produces no required artifact. It is a soft "surface to user" nudge, not a gate.
- Step 4 (`WebSearch`) and Step 5 (`git clone` + assess doc) are explicitly external-only.
- The terminal instruction is "Default when prior art exists: integrate, not reimplement" —
  but "prior art" here means external OSS, and nothing forces an explicit overlap verdict.

The `interweave` epic had **no** `assess-*.md` doc (it is in-tree, not an external candidate),
so Phase 0 step 1 was a guaranteed miss. A `bd search "ontology"` *might* have surfaced
`sylveste-46s`, but nothing required the author to run it, record the result, or rule on the
overlap. The brainstorm command (`brainstorm.md:81-110`) has the same external-only prior-art
check.

**Gap in one sentence:** there is no required, recorded, in-tree overlap reconciliation step
that forces an explicit `subsume | supersede | orthogonal` verdict against open-and-shipped
epics whose scope overlaps the new design.

## Survey of existing related code

All paths verified 2026-06-22.

### Authoring surfaces (where the gate must live)

| Surface | File | Current prior-art step |
|---|---|---|
| Strategy command (canonical) | `os/Clavain/commands/strategy.md:45` Phase 0 | external-only, soft nudge |
| Brainstorm command | `os/Clavain/commands/brainstorm.md:81` Phase 1.1 | external-only prior-art |
| Installed copies | `~/.claude/plugins/cache/interagency-marketplace/clavain/0.6.253/commands/{strategy,brainstorm}.md` | byte-identical to repo source (verified) |
| Gemini mirror | `.gemini/commands/clavain/strategy.toml` | mirror — out of scope for v1 |

The repo source (`os/Clavain/`) is the source of truth; the cache (`0.6.253`) is the
published artifact and is currently identical. Any change ships via the normal Clavain
publish flow (`AGENTS.md` "Release workflow").

### Data model the gate can query (verified against `.beads/issues.jsonl`)

Beads is the queryable corpus: **3,594 issues**, **3,110 closed / 447 open**. Artifacts are
stored as **labels**, not first-class fields. Distinct prefixes and counts:

```
artifact_brainstorm:   86   artifact_prd:          60   artifact_implementation: 19
artifact_plan:         70   artifact_prior-art:    51   artifact_closed:         16
artifact_reflection:   30   artifact_reconciliation: 1  (already used on sylveste-9gn9!)
```

Two facts shape the design:

1. **`artifact_brainstorm:` / `artifact_prd:` / `artifact_plan:` labels carry doc *paths*.**
   Example (`sylveste-benl.1`): `artifact_prd:docs/prds/2026-04-08-lens-go-package.md`. These
   are directly greppable for keyword overlap against the new design's title.

2. **`artifact_implementation:` carries a git SHA, NOT a file path.** Example:
   `artifact_implementation:a49dd8be7f0c...`. The bead description's `close_reason` is where the
   *shipped file paths* actually live (e.g. sylveste-benl.1's close_reason names
   `os/Skaffen/pkg/lens/{selector,loader,graph,louvain,evolution}.go`). **Implication: the bead
   text — title + description + close_reason — is the searchable surface for shipped paths, not
   the `artifact_implementation` label.** A naive "grep artifact_implementation paths" check (as
   the bead's first-draft wording suggests) would find SHAs, not modules. This is a load-bearing
   correction to the bead's proposed mechanic.

### Precedent that the gate already half-exists

- **`artifact_reconciliation:` label is already in use exactly once** — on `sylveste-9gn9`,
  pointing at the lattice reconciliation doc. The vocabulary the gate should produce already
  has a home in the schema; we are formalizing an ad-hoc label that the failure case itself
  created.
- **`clavain-cli set-artifact / get-artifact / advance-phase`** already wire artifacts into
  beads as labels (used throughout `strategy.md` Phase 0/3b and `brainstorm.md` Phase 3b).
  A `prior_implementations` artifact slots into this exact mechanism — no new storage layer.
- **Calibration-gated review model** (`sprint.md:96`, `clavain-cli review-calibration`) shows
  the established pattern for a gate that can `skip | lighten | full` based on measured
  evidence, and "fails safe to full". The reconciliation gate can borrow this shape so it
  doesn't tax trivial features.
- **interphase / clavain `lib-gates.sh`** exist (`os/Clavain/hooks/lib-gates.sh`,
  `interverse/interphase/hooks/lib-gates.sh`) — a hook-enforced variant is feasible if a
  prose gate proves insufficient (see Decision D4).

### The failure-case artifacts (ground truth for what "good" looks like)

- `docs/research/2026-04-27-lattice-reconciliation.md` — the model output: a verdict
  (`subsume`), an overlap table (PRD requirement × interweave coverage), an effort delta,
  and a concrete revision list. This is the shape the gate's `prior_implementations` field
  should aspire to (a lighter version of it, produced *before* the PRD, not after).
- `docs/reflections/2026-04-26-persona-lens-ontology-scoping-reflect.md` — names the
  "three-stores-of-the-same-thing is a tell" heuristic and the iemoto/canonical-authority
  pattern. Useful signal-words for the overlap heuristic.

## Proposed design

**Core idea:** add a required **Phase 0.5: Shipped-State Reconciliation** to `/clavain:strategy`
(and a lighter mirror in `/clavain:brainstorm`), producing a `prior_implementations` block in
the PRD frontmatter/body and a recorded `artifact_reconciliation` bead label. The phase
**cannot be marked complete** until every overlapping in-tree epic carries an explicit
`subsume | supersede | orthogonal` verdict.

### The mechanical check (3 steps, scoped and recorded)

Run after Phase 0 (external prior art), before Phase 1 (Extract Features):

**Step A — Keyword extraction.** Derive 3-6 salient keywords from the strategy/PRD title and
the brainstorm's "What We're Building" section (drop stopwords; keep domain nouns:
"ontology", "lens", "persona", "graph", "routing", "cache"…).

**Step B — In-tree overlap search.** For each keyword, search the bead corpus across BOTH
open and shipped epics, over the *text surface* (title + description + close_reason), not just
labels:

```bash
# Conceptual — exact CLI TBD (Decision D2). Searches title/desc/close_reason of epics
# (and feature-beads carrying artifact_prd / artifact_plan / artifact_implementation labels),
# status open OR closed, ranked by keyword hit count.
bd search "<kw1> <kw2> ..." --type=epic 2>/dev/null            # open + closed
grep -l "<kw>" docs/prds/*.md docs/brainstorms/*.md 2>/dev/null  # doc-path artifacts
```

Output: a candidate list `[{bead_id, title, status, shipped?, matched_keywords, doc_paths}]`.

**Step C — Verdict (the gate).** For each candidate above a hit threshold, the author MUST
record one of:

- **`orthogonal`** — overlap is keyword-only; scopes genuinely differ. One-line justification.
- **`subsume`** — the prior epic already covers this; the new work becomes an extension of it.
  Strategy **pivots**: the PRD is rewritten as extensions to the existing module (this is what
  lattice reconciliation did).
- **`supersede`** — the new design replaces the prior epic; the prior epic must be explicitly
  marked superseded (and its shipped artifacts addressed). Requires naming what happens to the
  sunk work.

If any candidate is left without a verdict, the phase is **incomplete** and strategy must not
advance to Phase 2 (Write PRD).

### Output contract (`prior_implementations`)

Added to PRD frontmatter (machine-readable) AND surfaced in the body. Proposed schema:

```yaml
prior_implementations:
  - bead: sylveste-46s
    title: "interweave: generative ontology graph for agentic platforms"
    status: open            # or closed
    shipped_pct: ~87        # optional, if knowable
    matched_keywords: [ontology, graph, lens, persona]
    verdict: subsume        # orthogonal | subsume | supersede
    rationale: "interweave already ships SQLite + named templates covering the 7 entity types;
                persona/lens become type-family extensions. Drop AGE/Cypher."
    reconciliation_doc: docs/research/2026-MM-DD-<slug>-reconciliation.md  # required iff subsume|supersede
```

- If `verdict` is `subsume` or `supersede`, a reconciliation doc is required (mirrors the
  lattice doc shape: overlap table + effort delta + revision list).
- The block is recorded onto the epic bead as `artifact_reconciliation:<doc_or_"none-found">`
  via `clavain-cli set-artifact`, reusing the label that already exists in the schema.
- Empty list (`prior_implementations: []`) is allowed ONLY after the search ran and returned no
  candidates over threshold — the search running is itself recorded (`artifact_reconciliation:none-found`)
  so a downstream reviewer can distinguish "checked, clean" from "never checked".

### Where it lives — strategy is the gate; brainstorm is the early-warning

- **`/clavain:strategy` Phase 0.5 (the enforced gate).** Strategy is the canonical PRD-authoring
  surface and already writes the PRD + creates beads, so it owns the hard gate. The
  `<BEHAVIORAL-RULES>` "Exactly 6 phases (0-5)" line must change to accommodate a new phase
  (Decision D1 covers numbering: insert as "Phase 0.5" to avoid renumbering, OR renumber to 0-6).
- **`/clavain:brainstorm` (lighter, advisory).** Add the in-tree overlap search to the existing
  prior-art step (Phase 1.1) as an advisory surface — if it finds a strong shipped-epic match,
  it warns early so the brainstorm itself can pivot. Brainstorm records nothing binding; strategy
  re-runs and enforces. This avoids the failure mode where someone authors a PRD freehand
  (skipping brainstorm) and still hits the gate at strategy.

### Calibration / cost control

Borrow the review-calibration "fail-safe to full" pattern (`sprint.md:96`). The reconciliation
search is cheap (one `bd search` + one `grep`), so v1 can run it unconditionally. If it proves
noisy on trivial features (bug fixes, UI tweaks), gate it behind the same Tier check that
already governs feature selection: **only enforce the verdict requirement for `--type=epic`
strategy runs or Tier-3 complexity**; for simple features, run the search and surface results
but don't block. (Decision D3.)

## What this is NOT (non-goals)

- Not a semantic/embedding similarity engine. v1 is keyword + status-scoped bead search +
  grep over doc-path artifacts. Embedding-based overlap detection is a possible v2 but
  out of scope (and the corpus is small enough that keyword recall is adequate).
- Not a hook that blocks edits. v1 is a prose phase in the command, consistent with how every
  other strategy phase works. A PreToolUse/Stop hook is a fallback (Decision D4), not the
  default.
- Not retroactive. It does not audit the 60 existing PRDs for missed overlaps.
- Not a change to the beads schema. It reuses the existing `artifact_reconciliation:` label.

## Decisions the human must confirm (BLOCKING — do not implement until ruled)

- **D1 — Phase numbering.** Insert as **"Phase 0.5: Shipped-State Reconciliation"** (no
  renumbering, but breaks the literal "Exactly 6 phases (0-5)" rule and the progress
  checklist), OR **renumber to Phases 0-6** (cleaner, but touches the "do not invent/append
  phases" guardrail and any structural tests asserting phase count). Recommend Phase 0.5 to
  minimize blast radius. **Confirm which.**

- **D2 — The actual search command.** The bead's first-draft mechanic ("grep epic descriptions
  and shipped artifact_implementation paths") is partly wrong: `artifact_implementation` holds a
  SHA, not a path. Confirm the search surface = **bead title + description + close_reason** (text)
  + **`artifact_prd`/`artifact_plan` doc-path labels**, scoped to `--type=epic`, status open OR
  closed. Confirm whether `bd search` supports closed-status + type filters, or whether the gate
  greps `.beads/issues.jsonl` directly (cloud-session pattern). **Confirm the corpus + command.**

- **D3 — Enforcement scope.** Hard gate (verdict required) for ALL strategy runs, OR only for
  `--type=epic` / Tier-3 complexity with advisory-only for simple features? Recommend epic/Tier-3
  hard gate, advisory otherwise. **Confirm the threshold.**

- **D4 — Prose phase vs. hook enforcement.** v1 = prose phase in `strategy.md` (model self-enforces,
  like every other phase). Is that sufficient, or does the human want a mechanical hook
  (`lib-gates.sh`) that refuses to record the `strategized` phase advance until a
  `prior_implementations` artifact exists? Prose is lighter and matches existing phases; hook is
  harder to bypass but more engineering. **Confirm which.**

- **D5 — Brainstorm mirror.** Add the advisory in-tree search to `/clavain:brainstorm` too, or
  strategy-only? Recommend both (catches freehand-PRD path), but it doubles the touched surface.
  **Confirm scope.**

- **D6 — Reconciliation-doc requirement on subsume/supersede.** Require a full reconciliation doc
  (lattice-shaped) for every subsume/supersede, or allow an inline `rationale` for small overlaps
  and reserve the full doc for large ones? Recommend: inline rationale always; full doc required
  only when verdict changes the architecture (subsume that drops a storage engine, supersede that
  abandons shipped code). **Confirm the bar.**

## Open questions (non-blocking, but flag before build)

- **OQ-1 — Keyword extraction quality.** Stopword-strip the title is crude. Does the overlap
  search need the brainstorm's "What We're Building" section too (more recall, more noise)? How
  many candidates is "too many to rule on" before the gate becomes friction theater?

- **OQ-2 — Hit threshold.** What's the minimum keyword-match count to force a verdict? Too low →
  every epic matches "system/agent/data"; too high → misses the interweave/ontology case if the
  PRD used "lattice" vocabulary the epic didn't. Needs a quick calibration pass against the
  lattice case (would the gate have caught `sylveste-46s` from the persona-lens PRD's keywords?
  worth a dry-run before shipping).

- **OQ-3 — Shipped-pct signal.** "87% shipped" for interweave was inferred from children, not a
  stored field. Can the gate cheaply compute shipped-pct (closed children / total children) to
  rank candidates, or is that scope creep?

- **OQ-4 — Closed-but-superseded epics.** Some closed epics were themselves superseded (e.g.
  microrouter .19 killed). Searching closed epics may surface dead architecture as a false
  "prior implementation". Does the gate need to skip beads labeled superseded/MOOT?

- **OQ-5 — `core/` vs `interverse/` duplication.** The lattice case noted `core/interweave/` AND
  `interverse/interweave/` both exist. The gate searches beads, not the filesystem; should it also
  do a light module-name grep over `interverse/*/CLAUDE.md` + `core/*/CLAUDE.md` (as strategy
  Phase 0 step 3 already does for plugins)?

- **OQ-6 — Cache/publish path.** The change is in `os/Clavain/commands/`, which must be published
  to the marketplace cache to take effect. Confirm the change rides the normal Clavain release,
  not a hand-edit of the `0.6.253` cache.

- **OQ-7 — Missing memory files.** The bead cites `feedback_reanchor_to_pivot_memory.md` and
  `feedback_docs_match_codebase_not_memory.md`; neither exists in the memory dir. Should this
  work also (re)create those memory files so the pattern is captured where future sessions read
  it, independent of the gate?

## Appendix — verification log (file:line)

- `os/Clavain/commands/strategy.md:45-83` — existing Phase 0 Prior Art Check (external-focused).
- `os/Clavain/commands/strategy.md:11-17` — `<BEHAVIORAL-RULES>` "Exactly 6 phases (0-5)".
- `os/Clavain/commands/brainstorm.md:81-110` — brainstorm prior-art check (external-focused).
- `docs/prds/2026-04-21-persona-lens-ontology.md:14-35` — ERRATA documenting the miss + SUBSUME.
- `docs/research/2026-04-27-lattice-reconciliation.md` — verdict `subsume`, overlap table,
  effort delta 10.5w → 6w.
- `docs/reflections/2026-04-26-persona-lens-ontology-scoping-reflect.md` — pattern heuristics.
- `.beads/issues.jsonl` — 3594 issues; 3110 closed / 447 open; `artifact_reconciliation:` used
  once (on sylveste-9gn9); `artifact_implementation:` values are git SHAs (verified on
  sylveste-benl.1), shipped paths live in `close_reason`.
- `sylveste-46s` — status `open`, type `epic` ("interweave: generative ontology graph").
- `sylveste-9gn9` — status `closed`, type `task`, carries `artifact_reconciliation:` label.
- `sylveste-r3jf` — status `closed`, type `task` (trigger F2).
- `os/Clavain/commands/sprint.md:96` — calibration-gated review model ("fails safe to full").
- `os/Clavain/hooks/lib-gates.sh`, `interverse/interphase/hooks/lib-gates.sh` — gate-lib
  precedent for a hook-enforced variant (D4).
