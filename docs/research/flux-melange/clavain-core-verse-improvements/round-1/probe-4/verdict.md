# fd-provenance-drift — Verdict (round 1, probe 4)

Fusion: fd-lifecycle-drift × fd-scriptorium-transmission.
Charter: `.claude/flux-gen-specs/clavain-core-verse-improvements-fusion-1.json`.

## What the intersection revealed that neither parent saw

The parents' contradiction — lifecycle trusts the upgrade machinery to converge
copies toward truth; transmission theory holds the machinery itself is the
drift vector — is not a tension to be resolved here; it is a **division of
labor the ecosystem has already chosen, badly**. Every transmission channel I
traced works flawlessly by lifecycle standards (green doctors, `behind=0`
clones, guarded overwrites, version parity inside each repo) while
systematically converging its copies toward the **wrong exemplar**, a
**renamed colophon**, or a **pointer that has advanced past the truth**. The
drift is not in the texts; it is in what the machinery certifies *about* the
texts. Lifecycle alone sees green dashboards. Stemmatics alone sees divergent
copies but cannot name the certifier. Only the fusion sees that in this fleet
**the certifier and the copyist are the same machine** — the install/sync
scripts both transmit the text and issue the attestation that the
transmission succeeded, with no independent witness (no content hashes, no
cross-repo version compare, no recorded deletions).

Three structural patterns emerged that are invisible to either parent alone:

1. **Exemplar capture**: the install machinery declares the exemplar by
   constant (`plugin_repo_url` → github.com/mistakeknot, `git archive HEAD`),
   and that declaration silently overrides the ecosystem's documented canon
   (Sylveste/zklw as canonical). Copies converge — to a frozen published line.
2. **Colophon fragility**: every guard reads provenance marks literally
   (`sylveste-managed` grep, BEGIN/END markers, version strings copied inside
   the payload they vouch for), so a renamed regime, an undated marker, or an
   un-bumped version each converts the safety mechanism into the freeze
   mechanism.
3. **Erasure of negative events**: deletions and deprecations are the
   transmissions the machinery cannot make — upstream deletions fall out of
   the diff window as `lastSyncedCommit` advances, `deletedLocally` is wired
   to nothing, and the deprecated sync engine is still the one on the weekly
   cron.

## Top 2 findings

1. **P1 — ~/.codex snapshot fleet converges on GitHub-as-exemplar**
   (`install-codex-interverse.sh:322`). 20 of 37 plugin snapshots behind
   their Sylveste source (interwatch 0.3.3 vs 0.6.1), all reporting
   `behind=0`, with `~/.agents/skills` routing every agent harness into the
   snapshots. Highest leverage because one fix — exemplar declaration plus a
   content/version witness at the symlink boundary — repairs a whole class of
   drift across all three harnesses at once.

2. **P1 — Upstream deletions never propagate; the sync pointer advances over
   them** (`sync-upstreams.sh:750` + `:953`). The weekly CI keeps certifying
   convergence while fossil folios accumulate and the catalog can never
   shrink. Fixing the machinery (propagate deletions into `deletedLocally`
   instead of silently skipping) fixes deletion-amnesia for every future
   sync, not just the 39 current dead targets.

## Regions covered

- `os/Clavain/upstreams.json` (full) — 39/65 dead fileMap targets verified on disk
- `os/Clavain/scripts/sync-upstreams.sh` (full, read-only; NO mutating commands run)
- `os/Clavain/scripts/clavain_sync/` (`__main__.py`, `classify.py`)
- `os/Clavain/scripts/pull-upstreams.sh`, `install-kimi.sh` (full),
  `install-codex.sh` (first 1000 lines), `install-codex-interverse.sh`
  (key sections), `codex-auto-refresh.sh`, `bump-version.sh`,
  `check-versions.sh`, `lib-fleet.sh` (full), `scan-fleet.sh` (header)
- `os/Clavain/.github/workflows/sync.yml` (full)
- `os/Clavain/config/fleet-registry.yaml` + ghost-agent spot checks
  (voice-analyzer, mycroft, interflux fd-* fleet — no true ghosts found)
- `os/Clavain/kimi.plugin.json`, `agent-rig.json` (structure + plugin resolution)
- `~/scripts/sync-secret-scan-baseline.sh` (full), `gen-kimi-manifests.py`
  (version-copy section), `intercheck-versions.sh` (header)
- `~/.codex/inter*` — all 39 clones: git status, last-commit dates, behind
  counts; full version+content drift matrix vs `Sylveste/interverse` (37 plugins)
- `~/.agents/skills` symlink routing (49 links, mixed regime: most →
  `~/.codex` clones, alwe → Sylveste source directly)
- gitleaks-validator fleet: all 47 copies hashed; PHILOSOPHY.md fleet: ~70
  copies hashed (all distinct — per-repo texts, no propagation claim made)

## Regions skipped / not pursued

- `core/intercore` Go internals (owned by fd-kernel-contract per anti_overlap)
- `.worktrees/`, `node_modules`, `.git`, dist/build per scope rule
- `interverse/_shared` and sdk/ plugins not in the `~/.codex` profile path
- The remaining ~534 lines of `install-codex.sh` (doctor tail) — pattern
  already established from the Kimi twin
- zklw-side copies of the same machinery (single-host probe; the GitHub-vs-
  canonical finding implies a second host would show the mirror image)

## Note on the dry verdict clause

The intersection was NOT dry: 10 findings, including two P1s. The charter's
headline P1 hypothesis (sync resurrects 39 deleted files) was refuted — the
`SKIP:not-present-locally` guard holds in both engines — but the refutation
surfaced the deeper finding: resurrection is prevented only by an incidental
filesystem check, while the designed mechanism (`deletedLocally`) is wired to
nothing, and the symmetric failure (deletions never propagate) is live.

REMEDIATION: Add a content hash and source-commit witness to every transmitted copy (starting with the `~/.agents/skills` symlink targets and the secret-scan template fleet) and make each install/sync channel verify the witness against its declared exemplar before attesting freshness, so no machine both copies a text and certifies its own copy.
