# Update Intercore Vision Doc Shipped Status

**Bead:** iv-b5cq
**Date:** 2026-02-22
**Complexity:** 1/5 (trivial)

## Goal

Update the Intercore vision doc (v1.7 → v1.8) to reflect that portfolio orchestration, lane-based scheduling, and cost-aware scheduling are now shipped. The doc body already marks portfolio as shipped (line 247), but the "Not yet shipped" section (line 796) and the success horizon table (line 838) still list them as upcoming.

## Changes

### 1. Version bump (line 3)
- `**Version:** 1.7` → `**Version:** 1.8`
- `**Date:** 2026-02-19` → `**Date:** 2026-02-22`

### 2. "Not yet shipped" section (lines 796-801)
Move shipped items out, leaving only genuinely unshipped items:

**Before:**
```
**Not yet shipped:**
- Multi-project portfolio runs (E8)
- Lane-based scheduling
- Sandbox spec enforcement
- Cost reconciliation
- Capability tokens for write-path enforcement
```

**After:**
```
**Shipped after v1.5:**
- Multi-project portfolio runs with cross-project event relay, dependency graph, and composite gate evaluation (E8, schema v10)
- Lane-based scheduling with priority lanes, fair scheduling, and velocity tracking
- Cost-aware scheduling with token budgets, budget enforcement, and reconciliation (schema v12)

**Not yet shipped:**
- Sandbox spec enforcement (schema for specs exists; enforcement by drivers pending)
- Capability tokens for write-path enforcement
```

### 3. Success horizon table (lines 836-839)
Update v1.5 and v2 rows:

- **v1.5 row:** Add portfolio, lanes, and cost-aware scheduling to shipped items
- **v2 row → v2 "Shipped":** Mark as shipped with portfolio, lanes, cost reconciliation
- Add new **v2.5 "Next"** row for remaining items (sandbox specs, Pollard/Gurgeh integration)
- **v3 row:** Keep sandbox _enforcement_ here but note specs already exist

### 4. Add shipped-after-v1.5 CLI commands (after line 794)
Add the `ic` commands that shipped with these features:
- `ic run create --projects=...` (portfolio)
- `ic lane create/list/assign/velocity` (lanes)
- `ic run budget/tokens` (cost-aware, already listed but verify)

## Verification

After edits:
1. Grep for "Not yet shipped" — should list only sandbox enforcement and capability tokens
2. Grep for "portfolio" — all mentions should say shipped
3. Grep for "lane" — scheduling mentions should say shipped
4. Check that the version number is consistently 1.8
