# Naming Conventions

How modules, pillars, and standalone components are named in Demarch.

## The Rule

Names should be **two syllables**. Short enough to type, long enough to be distinct.

Examples: *De-march*, *Clav-ain*, *Grid-fire*, *Au-tarch*.

## Two Naming Tiers

### Proper nouns (pillars, standalone infrastructure)

Drawn from science fiction — specifically the canon of authors whose work explores governance, autonomy, identity, memory, and posthuman systems:

| Author | Works we draw from |
|--------|-------------------|
| **Alastair Reynolds** | Revelation Space series — factions, governance, deep time |
| **Iain M. Banks** | Culture series — infrastructure, weapons, ship minds |
| **Gene Wolfe** | Book of the New Sun — memory, identity, unreliable narration |
| **Ada Palmer** | Terra Ignota — polycentric governance, jurisdiction, consent |
| **William Gibson** | Sprawl/Bridge/Jackpot trilogies — interfaces, mediation, stubs |
| **Alastair Reynolds** | (also) House of Suns, Poseidon's Children — deep time, settling |
| **China Mieville** | Bas-Lag, Embassytown — protocols, negotiation, alien cognition |

These names are **capitalized** as proper nouns. They get their own repos, their own identity. They name things that have architectural weight — pillars, layers, or paradigm-level infrastructure.

**Current proper nouns:**

| Name | Origin | What it names |
|------|--------|--------------|
| **Demarch** | Reynolds — Demarchists (Democratic Anarchists) | The project / monorepo |
| **Clavain** | Reynolds — Nevil Clavain (protagonist) | L2 OS / workflow agency |
| **Autarch** | Wolfe — The Autarch (Book of the New Sun) | L3 TUI application |
| **Gridfire** | Banks — gridfire weapon (Consider Phlebas) | Cybernetic composition layer (brainstorm) |
| **Interspect** | Original coinage (inter- + inspect/introspect) | Cross-cutting profiler |
| **Intercore** | Original coinage (inter- + core) | L1 orchestration kernel |
| **Interverse** | Original coinage (inter- + universe) | The plugin ecosystem |

### `inter-*` modules (plugins, companions, SDK)

The `inter-*` prefix describes components that occupy the space *between* things — bridges, boundaries, and connectors. These are **always lowercase**, even in prose. Each name should still aim for two syllables after the prefix (three total): *inter-flux*, *inter-lock*, *inter-path*.

The word after `inter-` should be a plain English noun or verb that hints at what the module does. No jargon, no abbreviations.

Good: `interlock` (coordination), `interflux` (review flows), `interpath` (doc routing)
Bad: `interdbsync`, `interllmgw`, `interCfg`

## How to Pick a Name

**For a new pillar or standalone component:**

1. Two syllables, from the SF canon above
2. The name should *feel* right for the thing — evocative, not a literal mapping
3. Check for CLI conflicts: `which <name>`, `apt list <name>`, `brew search <name>`
4. Must work lowercase as a command: `gridfire run`, `demarch status`
5. Must not collide with existing names in the ecosystem

**For a new `inter-*` plugin:**

1. `inter` + one-syllable English word (two syllables total after prefix)
2. The word should hint at function without being too literal
3. Check the existing list (currently 45 modules) for conflicts
4. Must work as: `interverse/<name>/`, `github.com/mistakeknot/<name>`

## Checking for Collisions

Before choosing a name, check what's already taken:

```bash
# List all inter-* modules
ls -d interverse/inter* core/inter* sdk/inter* 2>/dev/null | xargs -I{} basename {}

# List all proper-noun modules (non inter-* dirs with their own .git)
find apps os core -maxdepth 2 -name .git -printf '%h\n' 2>/dev/null | xargs -I{} basename {} | grep -v '^inter'
```

## What Not to Do

- Don't pick a name and then justify it — if you have to explain why "Zakalwe" means "build system," the name doesn't work
- Don't theme-lock authors to architectural roles — Banks isn't "only for infrastructure"
- Don't use three-syllable proper nouns — *Severian*, *Embassytown*, *Matrioshka* are too long
- Don't abbreviate — `ctlsh` and `rcptOS` look like typos
- Don't use names that are also common English words — `gate`, `flow`, `receipt` are concepts, not module names
