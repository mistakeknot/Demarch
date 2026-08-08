# f-084 verdict — fd-provenance-drift

**Verdict: CONFIRMED** (with refined scope). All three legs of f-084 hold:

1. **Auto-refresh executes the installer from the GitHub clone.** `codex-auto-refresh.sh:18-19` defaults `CLAVAIN_DIR=~/.codex/clavain` and `CLAVAIN_REPO_URL=https://github.com/mistakeknot/Clavain.git`; after `git pull --ff-only` from GitHub origin (:76) it runs `install-codex-interverse.sh` from that clone (:46-47, :51-52). The Sylveste tree is never consulted. (Restates upheld f-085 — still present, unremediated.)
2. **Drift checks compare snapshots against GitHub origin, not the canonical tree.** `check-install-updates.sh:150-158` (`repo_remote_diff_status`) resolves each repo's drift via `git ls-remote origin`; for the 38 `~/.codex/<plugin>` snapshots origin is GitHub. No code path anywhere compares an installed snapshot against `Sylveste/interverse/<plugin>` (71 nested plugin checkouts, each a live git repo).
3. **zklw is now probed** — and it replicates the pattern, with a wrinkle: 46 `~/.agents/skills` links route to `~/.codex/<plugin>` snapshots (interlock snapshot stale since 2026-07-04); `~/.codex/clavain` is absent; the `clavain` skill points to a standalone `~/projects/Clavain` clone (2026-08-01) — a third, undeclared Clavain lineage. No scheduler runs codex-auto-refresh there either.

## Intentional or accidental?

Both. GitHub-as-exemplar is **intentional as a distribution channel**: `install.sh` proves the intended design — `find_local_clavain_source()` (install.sh:95) prefers the local checkout and falls back to GitHub clones only in curl-pipe mode (install.sh:505,595,655,700), and `README.codex.md` documents GitHub clones for standalone Codex users. It is **accidental as the standing default** on machines that have the canonical tree: every override hook exists (`CLAVAIN_DIR`, `CLAVAIN_REPO_URL`, `--source`, `--clone-root`) but no script, scheduler, or doc ever sets them to Sylveste, so the distribution default silently becomes the operating exemplar. In stemmatics terms: the apograph was meant for readers without access to the archetype, yet the scriptorium copies from the apograph even with the archetype on the shelf.

## Doctrine contradiction

Project doctrine (`~/projects/AGENTS.md`): zklw canonical, git-only sync. Sylveste's own AGENTS.md: work isn't landed until `git push`. In practice Sylveste's origin is GitHub on both machines and both sit at the same 2026-08-05 commit — so for the Sylveste repo itself, GitHub is the sync transport and doctrine holds. The contradiction is confined to the **plugin-install layer**: canonical plugin sources live in `Sylveste/interverse/<plugin>` and `Sylveste/os/Clavain`, but install/refresh/drift machinery treats 38+ per-plugin GitHub clones as the exemplar, producing the settled symptoms (f-029 stale symlinks, snapshots 23/38 behind with update_count 0). The correct exemplar declaration per doctrine: **Sylveste tree on the local machine is the exemplar; GitHub is transport for machines without it; zklw's Sylveste is canonical among Sylveste checkouts.**

## Fix sizing

Not one chokepoint, but a small, bounded set — one shared helper plus three call sites (~60–90 lines total):

1. **New shared helper** (e.g. in `lib/installer-common.sh` or a new `os/Clavain/scripts/lib-exemplar.sh`): `clavain_exemplar_root` / `interverse_exemplar_root` — detect the local Sylveste checkout (logic already exists in `check-install-updates.sh:100-117` `discover_sylveste_root` and `install.sh:95` `find_local_clavain_source` — consolidate), overridable via one env var (`SYLVESTE_EXEMPLAR_ROOT`).
2. **`install-codex-interverse.sh`** (`ensure_repo` :898-915, `plugin_repo_url` :322-324): when an exemplar root is detected and contains `interverse/<plugin>` (or `os/Clavain`), install/link from that checkout instead of cloning from GitHub; fall back to GitHub when absent. This is the fleet-wide chokepoint — every companion install flows through `ensure_repo`.
3. **`codex-auto-refresh.sh`** (:18-19): default `CLAVAIN_DIR` to the detected Sylveste `os/Clavain` when present; keep GitHub clone as fallback. (Moot on this Mac until f-052's scheduling is fixed — the loop has never run.)
4. **`check-install-updates.sh`** (`repo_remote_diff_status` :150-158 + full mode :307-318): add a canonical-drift check comparing `~/.codex/<plugin>` HEAD against `Sylveste/interverse/<plugin>` HEAD (both local, no network), so "snapshot behind canonical" is reported even when GitHub origin is equally stale. This would have caught the settled "23/38 behind with update_count 0" anomaly.

Secondary, cheap: decide the zklw `clavain` skill lineage (standalone `~/projects/Clavain` vs `Sylveste/os/Clavain`) and encode the answer in the same exemplar helper, so both machines resolve identically.

REMEDIATION: Introduce a single `SYLVESTE_EXEMPLAR_ROOT` detection helper and route `install-codex-interverse.sh::ensure_repo`, `codex-auto-refresh.sh`, and `check-install-updates.sh` through it — local Sylveste tree first, GitHub clone only as distribution fallback; add a local canonical-vs-snapshot drift check that requires no network.

## Convergence note

f-084 should be tracked as the umbrella for the upheld cluster f-085 (installer self-transmission), f-052 (dead refresh automation), and the snapshot-drift leg of f-029 — one remediation (exemplar routing + scheduling + canonical drift check) closes all four.
