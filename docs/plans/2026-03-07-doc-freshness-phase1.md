# Plan: Activate interwatch drift hook + fix sync script

**Bead:** iv-fkjam | **Epic:** iv-nqj56

---

## Discovery

The drift-check Stop hook is **already installed** in Clavain's `auto-stop-actions.sh` (merged as iv-rn81). It uses `lib-signals.sh` to detect work signals and triggers `/interwatch:watch` at weight >= 3. The example file in `interwatch/examples/hooks/` is the historical predecessor.

**Remaining work is only the sync script fix:**

The `iv-ey5wb` roadmap restructure moved P2/P3 items from `docs/demarch-roadmap.md` to `docs/backlog.md`. The `sync-roadmap-json.sh` script's `collect_interverse_roadmap_from_markdown()` only reads the root roadmap, so it now misses the detailed inventory.

## Tasks

### Task 1: Update sync-roadmap-json.sh to scan backlog.md
**File:** `scripts/sync-roadmap-json.sh`
**Action:** In `collect_interverse_roadmap_from_markdown()`, after scanning the root roadmap file, also scan `docs/backlog.md` using the same parsing logic. The backlog file uses the same markdown format (`- [module] **iv-xxx** description`).

Specifically: after the `done < "$source_file"` on line 478, add a second pass over `$ROOT_DOCS_DIR/backlog.md` if it exists.

### Task 2: Verify roadmap.json regeneration
**Action:** Run `scripts/sync-roadmap-json.sh` and verify the output includes items from both the root roadmap and backlog.md. Compare item counts before/after.

## Verification
- [ ] `scripts/sync-roadmap-json.sh` completes without error
- [ ] `docs/roadmap.json` contains P2/P3 items that now live in `docs/backlog.md`
- [ ] Existing Now items from root roadmap still present
- [ ] No duplicate items
