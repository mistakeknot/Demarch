Below is a substantive review of **AGENTS.md** against the canonical terminology in `docs/glossary.md` (pillars vs layers) and the architectural framing in `docs/architecture.md`.

---

## 1) Consistency: “pillar” vs “layer” usage

### A. Using “layer” to mean “top-level directory” (incorrect per glossary)

**Problematic text**

> “Each subproject keeps its own docs at `Demarch/<layer>/<subproject>/docs/` (e.g., `interverse/interlock/docs/`, `core/intercore/docs/`).”

**Why it’s inconsistent**

* In the glossary, **Layer = L1/L2/L3** (dependency levels).
* `core/`, `os/`, `apps/`, `interverse/` are *directory groupings* / *pillar roots*, not “layers” as defined.

**Suggested fix**
Replace `<layer>` with something that matches reality and avoids collision with L1/L2/L3 terminology:

* Option 1 (most explicit):

  * “`Demarch/<pillar-root>/<subproject>/docs/` (e.g., `interverse/interlock/docs/`, `core/intercore/docs/`).”
* Option 2 (spell out the roots):

  * “`Demarch/{core|os|interverse|apps|sdk}/<subproject>/docs/` …”

If you want to connect it back to the actual layer model, add a short mapping note:

* “`core/` is primarily L1 (Intercore), `os/` + `interverse/` are L2, `apps/` is L3.”

---

### B. Mixing layer semantics into pillar labels (“OS pillar”)

**Problematic text**

> “`clavain (OS pillar)`”

**Why it’s inconsistent**

* “OS” is a **layer role (L2)** concept.
* **Clavain** is a **pillar** (one of the 5). Pillars can *live at* a layer; they aren’t “OS pillars” as a term of art in your glossary.

**Suggested fix**
Use “pillar” and “layer” together but not conflated:

* “**Clavain (pillar; L2 OS)**”
* or “**Clavain (L2 OS)**” (and omit “pillar” since that’s implied by being one of the five)

Also, your own naming convention says pillar names are capitalized; so if you mean the pillar, prefer **Clavain** rather than `clavain`.

---

### C. Interspect described as “inside Clavain” without a path, which blurs “pillar vs repo location”

**Problematic text**

> “*(inside clavain)* | Interspect | … Cross-cutting pillar, currently lives inside Clavain.”

**Why it’s inconsistent / confusing**

* It’s compatible with the glossary (“cross-cutting”), but the directory table is otherwise **path-based**.
* “inside clavain” is not a path and reads like a dependency claim, not a location claim.

**Suggested fix**
Make it a real path row (even if it’s nested), and keep the cross-cutting semantics explicit:

* Add a path like:

  * `os/clavain/<actual-interspect-path>/` | Interspect | Cross-cutting profiler (consumes L1 events; no kernel writes)

If you don’t want to commit to a concrete path in AGENTS.md, at least change the label to “**(currently housed in `os/clavain/` repo)**” to clarify it’s a repo-location detail, not an architectural dependency statement.

---

### D. “Hub” is used without definition (terminology drift risk)

**Problematic text**

> “All plugins and the hub share a single version bump engine…”

**Why it’s an issue**

* “Hub” is not defined in the glossary and could mean Clavain, root repo, marketplace, or something else.

**Suggested fix**
Replace “hub” with the specific thing you mean (likely one of: **Clavain**, **core/marketplace**, or the **root skeleton repo**), e.g.:

* “All plugins and the **core marketplace registry** share…”
* or “All plugins and **Clavain** share…”

---

## 2) Completeness: modules, descriptions, layout, relationships

### A. Overview omits two top-level areas that you later rely on

**Problematic text**

> “The repo also contains the Clavain agency (`/os`), the Autarch TUI (`/apps`), and core infrastructure (`/core`).”

**Gap**

* `sdk/` is real and listed later (`sdk/interbase/`) but not introduced.
* **Interspect** is a pillar (per your glossary) but is not mentioned in the overview at all, even as “currently housed under Clavain”.

**Suggested fix**
Update overview to include:

* `sdk/` (and what it’s for)
* Interspect (cross-cutting pillar; current location)

Example minimal change:

* “The repo contains Intercore (`/core`), Clavain (`/os`), Interverse (`/interverse`), Autarch (`/apps`), plus `sdk/` shared libraries. Interspect is a cross-cutting pillar currently housed in `os/clavain/`.”

---

### B. Directory Layout is strong, but it’s missing “layer” visibility (causes later confusion)

Right now, you list **Pillar** but not **Layer**. Given the glossary emphasis, contributors will immediately ask “what layer is this module in?”

**Suggested fix**
Add a **Layer** column to the directory table (even if some are “cross-cutting/tooling”). This also prevents the earlier “<layer> directory” mistake.

Example:

* `core/intercore/` | Intercore | **L1** | Orchestration kernel
* `core/intermute/` | Intercore | **L1** | Coordination service used by L2 interlock
* `interverse/interflux/` | Interverse | **L2 driver** | Review + research engine
* `sdk/interbase/` | Interverse | **L2 support** | Shared SDK
* `docs/`, `scripts/` | — | **tooling/meta** | …

This also forces you to resolve ambiguous entries like **interbench** (see next item).

---

### C. Potential layer inversion: Intercore tooling depending on an Interverse driver (needs clarification)

**Problematic text**

> “`core/interbench/` | Intercore | Eval harness for tldr-swinton capabilities”

If Interbench is “Intercore (L1)” in the architectural sense, “eval harness for a driver” can read like L1 depends on L2.

**Suggested fix**
Clarify that this is *developer tooling* and cross-layer dependencies are allowed for tooling/evals, e.g.:

* “Eval harness for driver capabilities (tooling; may depend on L2 plugins)”

Or reclassify it in the table as “— / tooling” instead of Intercore pillar if it’s not truly part of the kernel pillar.

---

### D. Module Relationships section reads like a filesystem tree, but describes dependencies

**Problematic text**

```text
clavain (OS pillar)
├── interphase
├── interline
...
```

**Why it’s a problem**

* The visual tree (`├──`) strongly implies “these are inside clavain” (physically).
* But your directory layout shows these are **separate repos under `interverse/`**.

**Suggested fix**
Switch the representation to a dependency diagram syntax:

* “**Clavain (L2 OS) uses drivers:** interphase, interline, interflux, …”
* Or arrows:

  * `os/clavain → interverse/interphase`
  * `os/clavain → interverse/interlock → core/intermute`

This is not a style nit; it prevents contributors from looking in the wrong repo.

---

### E. `sdk/interbase/` is listed but absent from relationships

**Problematic omission**

* Directory layout includes:

  > “`sdk/interbase/` | Interverse | Shared integration SDK for dual-mode plugins”
* Module Relationships never mentions it.

**Suggested fix**
Add it explicitly as a shared dependency:

* `interbase (sdk lib) ← used by multiple dual-mode drivers (list the concrete ones if true)`

If it’s not used yet, say so (“intended for …”) to prevent incorrect assumptions.

---

## 3) Stale content and internal inconsistencies

### A. Marketplace path mismatch: `infra/marketplace` vs `core/marketplace`

**Problematic text**

> “Release is complete only when both pushes succeed:
>
> * plugin repo push
> * `infra/marketplace` push”

But elsewhere:

* Glossary: “Marketplace … at `core/marketplace/`”
* Directory Layout: `core/marketplace/`

**Suggested fix**
Replace `infra/marketplace` with `core/marketplace` everywhere, and if “infra” was a legacy name, call that out once:

* “marketplace repo push (`core/marketplace/`, formerly `infra/marketplace/`)”

---

### B. Post-bump hooks table header is wrong (misleads readers)

**Problematic text**

> “Modules with extra work… use `scripts/post-bump.sh`:
> | **Interverse** | Post-bump action |
> | `os/clavain/` | Runs `gen-catalog.py` … |”

**Why it’s an issue**

* `os/clavain/` is not Interverse.
* This is the kind of small inconsistency that causes people to run hooks in the wrong place.

**Suggested fix**
Rename the column header to “Module” (or “Repo”), and optionally add pillar/layer columns:

* `Module` | `Pillar` | `Post-bump action`

---

### C. “Not a git monorepo” contradicts later “root has a .git”

**Problematic text (Overview)**

> “Each module keeps its own `.git` — this is not a git monorepo…”

Later (Development Workflow):

> “The root `Demarch/` directory also has a `.git` for the monorepo skeleton…”

**Why it’s stale/inconsistent**

* Functionally, this *is* a git repo at root plus nested repos.
* New contributors will not know whether this is: submodules, nested clones, or something else.

**Suggested fix**
Make the repo model explicit:

* “Demarch is a **workspace-style monorepo**: a root skeleton repo plus **nested independent repos (often via git submodules)**. Git operations apply to the nearest repo; check `git rev-parse --show-toplevel`.”

If it’s *not* submodules, say what it is (and how to clone it) — see Actionability.

---

### D. Beads version references feel mid-migration

You reference:

* “Beads 0.51 Upgrade” guide
* “bd sync … (0.50.x syncs, 0.51+ no-op)”
* “Use bd … (v0.52.0)”

This might all be true, but it reads like multiple eras coexisting.

**Suggested fix**
Add one authoritative statement near the top of Beads sections:

* “Current supported `bd` version: **0.52.x**. Older notes exist for migration history; follow commands in this doc.”

And if the 0.51 upgrade is complete, mark the guide as historical:

* “(historical; keep for reference)”

---

## 4) Actionability: can a new contributor or AI agent start work?

You have a lot of operational detail, but there are a few **missing “first 30 minutes” primitives**.

### A. Missing: how to obtain/clone the repo layout

Given the nested `.git` situation and mention of `.gitmodules`:
**What’s missing**

* Is the intended bootstrap:

  * `git clone --recurse-submodules …` ?
  * or a custom script that clones each module repo into place?
  * or something else?

**Suggested fix**
Add a short **Bootstrap** section near “Overview”, with the one true setup path. Example content:

* “Clone root skeleton”
* “Initialize/update submodules”
* “Verify nested repos are present”
* “Common failure modes (detached HEAD in submodules, etc.)”

Without this, an external contributor cannot reliably reproduce the directory layout you document.

---

### B. Missing: how to build/run the kernel CLI (`ic`)

Your architecture docs make `ic` “the contract,” but AGENTS.md doesn’t tell contributors how to get it running.

**Suggested fix**
Add a “Kernel (Intercore) build/run” snippet under “Running and testing by module type”, parallel to intermute/interbench. Even a minimal pointer helps:

* `cd core/intercore && go test ./... && go build ...`
* where the binary ends up / expected name

---

### C. The doc assumes direct push access (not valid for many OSS contributors)

**Problematic text**

> “YOU must push … NEVER stop before pushing … resolve and retry until it succeeds”

For open-source contributors, “push to upstream” may be impossible/undesired; the correct workflow is fork + PR.

**Suggested fix**
Gate it:

* “If you have direct push access: follow the mandatory workflow below.”
* “If you do not: push to your fork and open a PR; still run gates and keep bead tracking updated.”

This is not style—without this, the instructions are operationally wrong for a large portion of contributors.

---

### D. Too many absolute server paths; lacks portable equivalents

Examples:

> `cd /root/projects/Demarch/...`
> `bash /root/projects/Demarch/interverse/interchart/scripts/...`

**Suggested fix**
Prefer repo-relative commands:

* `cd interverse/interflux`
* `bash interverse/interchart/scripts/...`

If you want to keep server paths (useful internally), show both once:

* “On the shared server the repo lives at `/root/projects/Demarch`, but all commands below assume you’re at repo root.”

---

### E. MCP server testing instructions are partial/inconsistent

You list MCP server plugins:

> “(interkasten, interlock, interject, tldr-swinton, tuivision, interflux)”

…but the build/test examples only cover interkasten/interlock/tldr-swinton. A new contributor won’t know the build entrypoints for interject/tuivision/interflux.

**Suggested fix**
Either:

* Provide a generic pattern (“look for `server/` or `scripts/build.sh`”), plus **one concrete command per MCP module**, or
* Explicitly say: “Build/test commands differ; see each module’s local AGENTS.md.”

Right now it’s in an ambiguous middle state.

---

## 5) Structure: organization changes that improve correctness and reduce drift

### A. Two Beads sections duplicate commands and rules

You have:

* “Bead Tracking” (earlier)
* “Beads Workflow Integration” (later, long, with repeated commands)

**Suggested fix**
Make one canonical Beads section and have the other be a short pointer:

* Keep the longer one, but remove repeated shorter bullets, or vice versa.
* Or move the viewer-specific section (`beads_viewer`) into `docs/guides/` and keep AGENTS.md focused on CLI commands.

This reduces drift (e.g., one section gets updated, the other doesn’t).

---

### B. “Cross-Cutting Lessons / Research References” are valuable but don’t belong in AGENTS.md’s critical path

These sections contain deep operational lore and research notes (compression papers, BM25, etc.). They will age quickly and make it harder for new agents to find the rules that matter.

**Suggested fix**
Move these to:

* `docs/solutions/…` (for environment lessons)
* `docs/research/…` (for papers / techniques)

Then leave **AGENTS.md** with links plus a 3–5 bullet “gotchas” list.

This is a structural change that improves long-term correctness, not style.

---

### C. Add a “Quickstart for new agents/contributors” at the top

Right now, the doc starts with overview/terminology, but doesn’t give an immediate “do this first” path.

**Suggested fix**
Add a short ordered list (5–8 steps), including:

* read root + local AGENTS
* run `bd ready`
* identify module repo boundary (`git rev-parse --show-toplevel`)
* run module gates
* where to find architecture glossary

This materially improves actionability.

---

## Highest priority fixes (most impact / least effort)

1. **Replace `infra/marketplace` → `core/marketplace`** (hard correctness bug).
2. Fix terminology collisions:

   * change `Demarch/<layer>/...` docs convention
   * change `clavain (OS pillar)` wording
3. Clarify repo model (“nested repos/submodules + root skeleton repo”) and add bootstrap instructions.
4. Rework Module Relationships to show **dependencies**, not a faux directory tree.
5. Add missing kernel (`ic`) build/run entrypoint and remove/guard “must push” for OSS contributors.

If you want, I can propose an edited patch (diff-style) for just the above items, keeping the rest of the document intact.
